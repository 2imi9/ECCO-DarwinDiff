"""Measured wall-clock scaling for native / seasonal compute sizing.

**Why this exists.** The memory budget (`measure_memory_scaling.py`) sizes *which
machine holds a fit*; this harness answers the other half the AICR proposal needs —
*how long each fit takes*. The native wall-clock was previously ASSUMED ("~1 h/run,
~0 % GPU util") and never measured. This times one full
``DINN → integrate → loss → backward`` pass (= one optimizer epoch) as a function of
``(n_cells, n_steps)`` and decomposes it into a per-epoch cell-scaling and step-scaling.

**Why synthetic inputs are valid for *timing*** (the same argument that makes them
valid for memory, in `measure_memory_scaling.py`): the box model has **no
data-dependent control flow**, so the kernels launched and the FLOPs executed per
step depend only on tensor SHAPES (``n_cells``) and the step COUNT — not on the field
VALUES. Synthetic positive forcing/state therefore reproduce a real fit's per-step
wall-clock at matched shapes. (Values would change the *recovered parameters*, not the
compute.)

**The cell-scaling of per-step time is the load-bearing result.** Memory is capped by
trajectory length (seasonal 2000 steps → 25.7 GiB at native ⇒ OOM on a 24 GB 5090), but
*timing* is not — at 200 steps even LLC90 (105 k cells) is ~7 GiB, so a single 5090 can
sweep cells across ~50x and reveal whether wall-clock is **flat (Python-loop / kernel-
launch bound, ~0 % GPU util)** or **rising (compute bound)**. That single fact decides
whether a B200 shortens a *single* fit (compute-bound) or only the *sweep* via
concurrency (launch-bound) — the core of the throughput-vs-memory framing.

**Eager by default; ``--compile`` for the production constant.** Like the 356 B/(cell·step)
memory constant, the default sweep is an eager upper bound (``torch.compile`` needs
Linux). Pass ``--compile`` (on WSL / the cluster) to ``torch.compile`` the per-step and
measure the *compiled* per-epoch cost the production 10-seed batched path actually pays —
the number the AICR throughput ask should quote, not the eager upper bound.

Run::

    python scripts/measure_compute_time.py                       # default sweep
    python scripts/measure_compute_time.py --out t.json --md docs/findings/compute_time_scaling.md
    python scripts/measure_compute_time.py --device cpu          # smoke only
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

# Reuse the exact input construction + constants the memory harness uses, so the two
# harnesses measure the *same* graph (scripts/ is on sys.path[0] when run directly).
from measure_memory_scaling import (  # type: ignore[import-not-found]
    DT_DAYS,
    TIME_MEAN_STEPS,
    _bounded,
    _build_inputs,
)

from darwindiff.carroll6_5pft_2layer import (
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_step,
)

# --- Anchors that tie the synthetic sweep back to real measured fits ---------
# Measured 1° wall-clock (cluster_setup.md:194,197, RTX 5090):
#   1-AOI 1° 1500-epoch time-mean fit ≈ 5 min;  10-seed batched 3-AOI ≈ 7 min (compiled).
AOI_1DEG_CELLS = 2_853        # measured 3-AOI @ 1° (measure_compute_budget.py)
AOI_NATIVE_CELLS = 38_809     # measured 3-AOI @ native LLC270 (measure_compute_budget.py)
LLC90_CELLS = 13 * 90 * 90    # 105_300
LLC270_CELLS = 13 * 270 * 270  # 947_700


@dataclass(frozen=True)
class TimeRecord:
    """Median/min wall-clock of one train epoch (fwd+bwd) at a problem size."""

    n_cells: int
    n_steps: int
    train_median_s: float | None
    train_min_s: float | None
    forward_median_s: float | None
    oom: bool

    @property
    def per_step_ms(self) -> float | None:
        if self.train_median_s is None:
            return None
        return 1e3 * self.train_median_s / self.n_steps

    @property
    def per_cellstep_ns(self) -> float | None:
        if self.train_median_s is None:
            return None
        return 1e9 * self.train_median_s / (self.n_cells * self.n_steps)


def _sync(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _time_once(
    dinn, env, state0, forcing, n_steps, device, *, backward: bool, step_fn=None,
) -> float:
    """One timed forward (+backward) pass. Caller handles warmup + sync fencing."""
    _sync(device)
    t0 = time.perf_counter()
    if backward:
        params = _bounded(dinn(env), device, env.dtype)
        final = carroll6_5pft_2layer_integrate(state0, params, DT_DAYS, n_steps,
                                               step_fn=step_fn, **forcing)
        loss = final.pow(2).mean()
        loss.backward()
    else:
        with torch.no_grad():
            params = _bounded(dinn(env), device, env.dtype)
            carroll6_5pft_2layer_integrate(state0, params, DT_DAYS, n_steps,
                                           step_fn=step_fn, **forcing)
    _sync(device)
    return time.perf_counter() - t0


def measure_time(
    n_cells: int,
    n_steps: int,
    *,
    repeats: int = 5,
    warmup: int = 2,
    n_channels: int = 3,
    hidden_dim: int = 16,
    device: torch.device | str = "cuda",
    dtype: torch.dtype = torch.float32,
    use_compile: bool = False,
) -> TimeRecord:
    """Time one train epoch (fwd+bwd) and a forward-only pass at this size.

    Warmup passes absorb CUDA context init, allocator growth, cuDNN autotune, AND (with
    ``use_compile``) the first-call ``torch.compile`` trace/inductor build, so the timed
    repeats reflect steady-state per-epoch cost. OOM is recorded, not raised.
    """
    device = torch.device(device)
    # Compile the per-step (the production batched path, #119); the warmup passes below
    # absorb the one-time compile cost so the timed repeats are the compiled steady state.
    step_fn = torch.compile(carroll6_5pft_2layer_step, mode="default") if use_compile else None
    try:
        dinn, env, state0, forcing = _build_inputs(n_cells, n_channels, hidden_dim, device, dtype)

        for _ in range(warmup):
            _time_once(dinn, env, state0, forcing, n_steps, device, backward=True, step_fn=step_fn)
            dinn.zero_grad(set_to_none=True)

        train = []
        for _ in range(repeats):
            train.append(_time_once(dinn, env, state0, forcing, n_steps, device,
                                    backward=True, step_fn=step_fn))
            dinn.zero_grad(set_to_none=True)

        fwd = [_time_once(dinn, env, state0, forcing, n_steps, device,
                          backward=False, step_fn=step_fn)
               for _ in range(repeats)]

        del dinn, env, state0, forcing
        if device.type == "cuda":
            torch.cuda.empty_cache()
    except torch.cuda.OutOfMemoryError:
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return TimeRecord(n_cells, n_steps, None, None, None, oom=True)

    train_sorted = sorted(train)
    return TimeRecord(
        n_cells=n_cells,
        n_steps=n_steps,
        train_median_s=train_sorted[len(train_sorted) // 2],
        train_min_s=train_sorted[0],
        forward_median_s=sorted(fwd)[len(fwd) // 2],
        oom=False,
    )


def fit_per_step_vs_cells(records: list[TimeRecord], at_steps: int) -> dict[str, float]:
    """Fit per-epoch time ``t = a + b·cells`` at a fixed step count.

    ``b/a`` tells the regime: b·cells ≪ a across the swept range ⇒ flat / launch-bound
    (a B200 won't shorten a single fit); b·cells ≳ a ⇒ compute-bound (it will).
    """
    pts = [(r.n_cells, r.train_median_s) for r in records
           if r.n_steps == at_steps and r.train_median_s is not None]
    if len(pts) < 2:
        return {"a_s": float("nan"), "b_s_per_cell": float("nan"), "r2": float("nan"),
                "n": float(len(pts)), "at_steps": float(at_steps)}
    xs = [float(c) for c, _ in pts]
    ys = [float(t) for _, t in pts]
    n = len(xs)
    sx, sy = sum(xs), sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    denom = n * sxx - sx * sx
    if denom == 0:  # all cell counts identical (e.g. a single---cells smoke) -> slope undefined
        return {"a_s": float("nan"), "b_s_per_cell": float("nan"), "r2": float("nan"),
                "n": float(n), "at_steps": float(at_steps)}
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"a_s": a, "b_s_per_cell": b, "r2": r2, "n": float(n), "at_steps": float(at_steps)}


def _fmt(s: float | None) -> str:
    if s is None:
        return "OOM/—"
    if s < 1.0:
        return f"{s * 1e3:.1f} ms"
    if s < 90.0:
        return f"{s:.2f} s"
    return f"{s / 60:.1f} min"


def _render_markdown(records, cellfit, device_name, total_mem_gb, compiled=False) -> str:
    mode = "torch.compile'd per-step" if compiled else "eager autograd"
    lines: list[str] = []
    lines.append("# Measured wall-clock scaling — native / seasonal compute timing\n")
    lines.append(
        "Generated by `scripts/measure_compute_time.py`. Median wall-clock of one "
        f"`DINN → integrate → loss → backward` epoch ({mode}) vs problem size. "
        "Timing of a fixed graph is value-independent, so synthetic inputs reproduce a "
        "real fit's per-epoch cost at matched shapes.\n"
    )
    lines.append(f"- **Device:** {device_name}"
                 + (f" ({total_mem_gb:.1f} GB)\n" if total_mem_gb else "\n"))
    lines.append(f"- **Per-epoch cell-fit** `t = a + b·cells` @ {int(cellfit['at_steps'])} steps: "
                 f"a = {cellfit['a_s'] * 1e3:.1f} ms, "
                 f"b = {cellfit['b_s_per_cell'] * 1e9:.3g} ns/cell, "
                 f"R² = {cellfit['r2']:.4f} (n={int(cellfit['n'])}).\n")
    lines.append("\n## Measurements (one optimizer epoch = fwd + bwd)\n")
    lines.append("| cells | steps | train (median) | per-step | per-cell·step | fwd-only |")
    lines.append("|---|---|---|---|---|---|")
    for r in sorted(records, key=lambda r: (r.n_steps, r.n_cells)):
        ps = "—" if r.per_step_ms is None else f"{r.per_step_ms:.3f} ms"
        pcs = "—" if r.per_cellstep_ns is None else f"{r.per_cellstep_ns:.2f} ns"
        flag = " (OOM)" if r.oom else ""
        lines.append(f"| {r.n_cells:,} | {r.n_steps} | {_fmt(r.train_median_s)}{flag} "
                     f"| {ps} | {pcs} | {_fmt(r.forward_median_s)} |")
    lines.append("")
    return "\n".join(lines)


def _default_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--device", default=_default_device())
    # Cell sweep at fixed steps (cell-scaling) + step sweep at fixed cells (step-scaling).
    p.add_argument(
        "--cells", type=int, nargs="+",
        default=[AOI_1DEG_CELLS, 5_000, 10_000, 20_000, AOI_NATIVE_CELLS, 70_000, LLC90_CELLS],
    )
    p.add_argument("--steps", type=int, nargs="+", default=[TIME_MEAN_STEPS])
    p.add_argument(
        "--step-sweep", type=int, nargs="+", default=[50, 100, 200, 400, 800, 1600],
        help="step counts timed at --step-sweep-cells (step-linearity check)",
    )
    p.add_argument("--step-sweep-cells", type=int, default=10_000)
    p.add_argument("--repeats", type=int, default=5)
    p.add_argument("--warmup", type=int, default=2)
    p.add_argument("--hidden-dim", type=int, default=16)
    p.add_argument("--channels", type=int, default=3)
    p.add_argument("--out", type=Path, default=None)
    p.add_argument("--md", type=Path, default=None)
    p.add_argument("--compile", action="store_true",
                   help="torch.compile the per-step -> measure the COMPILED per-epoch cost "
                        "(production path, #119; Linux/WSL only, eager otherwise)")
    args = p.parse_args(argv)

    device = torch.device(args.device)
    device_name = (torch.cuda.get_device_name(device) if device.type == "cuda"
                   else f"CPU ({platform.processor() or platform.machine()})")
    total_mem_gb = (torch.cuda.get_device_properties(device).total_memory / 1024**3
                    if device.type == "cuda" else None)
    print(f"device: {device_name}" + (f" — {total_mem_gb:.1f} GB" if total_mem_gb else " (CPU)")
          + f"  [{'compiled' if args.compile else 'eager'}]")

    records: list[TimeRecord] = []

    print("cell-scaling sweep (fixed steps):")
    for n_steps in args.steps:
        for n_cells in args.cells:
            r = measure_time(n_cells, n_steps, repeats=args.repeats, warmup=args.warmup,
                             n_channels=args.channels, hidden_dim=args.hidden_dim, device=device,
                             use_compile=args.compile)
            records.append(r)
            print(f"  cells={n_cells:>7,} steps={n_steps:>4}  train={_fmt(r.train_median_s):>9}"
                  f"  per-step={'—' if r.per_step_ms is None else f'{r.per_step_ms:.3f}ms'}"
                  + ("  [OOM]" if r.oom else ""))

    print("step-scaling sweep (fixed cells):")
    for n_steps in args.step_sweep:
        r = measure_time(args.step_sweep_cells, n_steps, repeats=args.repeats, warmup=args.warmup,
                         n_channels=args.channels, hidden_dim=args.hidden_dim, device=device,
                         use_compile=args.compile)
        records.append(r)
        per_step = "—" if r.per_step_ms is None else f"{r.per_step_ms:.3f}ms"
        print(f"  cells={args.step_sweep_cells:>7,} steps={n_steps:>4}  "
              f"train={_fmt(r.train_median_s):>9}  per-step={per_step}")

    cellfit = fit_per_step_vs_cells(records, at_steps=args.steps[0])
    a, b = cellfit["a_s"], cellfit["b_s_per_cell"]
    print(f"\nper-epoch cell-fit @ {int(cellfit['at_steps'])} steps: "
          f"t = {a * 1e3:.1f} ms + {b * 1e9:.3g} ns/cell * cells   R2={cellfit['r2']:.4f}")
    if a > 0:
        cross = a / b if b > 0 else float("inf")
        regime = ("LAUNCH/PYTHON-BOUND across the swept range" if cross > LLC90_CELLS
                  else "compute-bound beyond that")
        print(f"  fixed-cost a dominates until ~{cross:,.0f} cells => {regime}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "device": device_name, "total_mem_gb": total_mem_gb, "compiled": args.compile,
            "records": [asdict(r) for r in records], "cell_fit": cellfit,
        }, indent=2), encoding="utf-8")
        print(f"wrote {args.out}")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(
            _render_markdown(records, cellfit, device_name, total_mem_gb, args.compile),
            encoding="utf-8")
        print(f"wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
