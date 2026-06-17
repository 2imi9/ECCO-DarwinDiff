"""Measured GPU-memory scaling for native-resolution / seasonal compute sizing.

**Why this exists.** The Explorer / AICR compute proposal needs defensible peak
GPU-memory numbers for reverse-mode differentiation through the box model at
native resolution (LLC90 / LLC270) and across the seasonal cycle. Rather than
*estimate* the autograd-graph overhead (the original proposal used a hand-waved
~12x), this harness *measures* the peak CUDA memory of one full
``DINN -> integrate -> loss -> backward`` pass as a function of ``(n_cells,
n_steps)``, fits ``M ~ a + b * (cells * steps)``, and extrapolates to the grids
and trajectory lengths in the proposal.

**Why synthetic inputs are valid.** Peak memory of a *fixed* autograd graph is
value-independent: the box model has no data-dependent control flow, so only
tensor SHAPES (``n_cells``) and the step COUNT (``n_steps``) drive the stored
activation footprint. Synthetic positive forcing / state therefore reproduce the
exact memory profile of a real fit at the same shapes. (Field VALUES would change
the recovered parameters, not the bytes.)

**The per-cell linearity check is itself a result.** The DINN is per-cell (1x1
convs) and the box integrates each cell independently, so memory must be linear
in ``n_cells``. Confirming that linearity empirically is what justifies the
"the ~1 TB global-native footprint shards perfectly across cells/GPUs" claim
(memory-bound -> throughput-bound).

Run::

    python scripts/measure_memory_scaling.py                  # default sweep
    python scripts/measure_memory_scaling.py --out mem.json --md docs/findings/memory_scaling.md
    python scripts/measure_memory_scaling.py --device cpu     # smoke only (no CUDA peak)
"""

from __future__ import annotations

import argparse
import json
import platform
from dataclasses import asdict, dataclass
from pathlib import Path

import torch

from darwindiff.carroll6_5pft_2layer import (
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
)
from darwindiff.networks import DINN

# --- Reference grids & trajectory lengths (the proposal ladder) --------------

DT_DAYS = 0.25
TIME_MEAN_STEPS = 200
"""Steps for a time-mean (climatology) fit: ~50-day relaxation at DT=0.25 d."""
SEASONAL_STEPS = 2000
"""Steps for a seasonal fit: ~one annual cycle (1460 steps) + short spin-up.
The load-bearing assumption in the seasonal extrapolation; documented as such."""

LLC90_CELLS = 13 * 90 * 90        # 105_300 — ECCO v4 grid (~1 degree)
LLC270_CELLS = 13 * 270 * 270     # 947_700 — ECCO-Darwin native grid (~1/3 degree)
REGIONAL_NATIVE_CELLS = 20_000    # order estimate: 3 AOIs at LLC270 spacing

# Per-tracer plausible-magnitude initial state (values are immaterial to memory;
# chosen only to keep the carbonate solve and forward-Euler steps numerically sane
# so the harness also doubles as a runs-clean smoke test). Index layout per
# carroll6_5pft_2layer module docstring.
_STATE0_BY_INDEX = (
    0.5,    # DFe_1
    0.1,    # P_diatom
    0.1,    # P_lge
    0.1,    # P_syn
    0.1,    # P_proLL
    0.1,    # P_proHL
    1.0,    # POC_1
    0.1,    # PIC_1
    2000.0,  # DIC_1
    2300.0,  # ALK_1
    0.6,    # DFe_2
    0.5,    # POC_2
    0.05,   # PIC_2
    2100.0,  # DIC_2
    2350.0,  # ALK_2
)

# Carroll-6 plausible positive ranges [lo, hi] for sigmoid bounding of DINN output
# (order: alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC).
_PARAM_BOUNDS = (
    (0.0, 0.05),
    (0.0, 2.0e-6),
    (0.0, 2.0),
    (0.0, 2.0),
    (0.0, 2.0),
    (0.0, 1.0),
)


@dataclass(frozen=True)
class MemRecord:
    """One memory measurement at a given problem size."""

    n_cells: int
    n_steps: int
    train_peak_bytes: int | None      # forward + backward (graph retained)
    forward_peak_bytes: int | None    # forward only (no_grad)
    oom: bool


@dataclass(frozen=True)
class ExtrapTarget:
    label: str
    cells: int
    steps: int


EXTRAPOLATION_TARGETS: tuple[ExtrapTarget, ...] = (
    ExtrapTarget("LLC90 global  · time-mean", LLC90_CELLS, TIME_MEAN_STEPS),
    ExtrapTarget("LLC90 global  · seasonal", LLC90_CELLS, SEASONAL_STEPS),
    ExtrapTarget("LLC270 global · time-mean", LLC270_CELLS, TIME_MEAN_STEPS),
    ExtrapTarget("LLC270 global · seasonal", LLC270_CELLS, SEASONAL_STEPS),
    ExtrapTarget("3-AOI native  · seasonal (~20k cells)", REGIONAL_NATIVE_CELLS, SEASONAL_STEPS),
)


def _build_inputs(
    n_cells: int,
    n_channels: int,
    hidden_dim: int,
    device: torch.device,
    dtype: torch.dtype,
) -> tuple[DINN, torch.Tensor, torch.Tensor, dict[str, torch.Tensor]]:
    """Construct the DINN, env tensor, initial state, and forcing fields.

    Shapes use ``H=1, W=n_cells`` so the per-cell axis is explicit and the 1x1
    convolutions and box integration broadcast exactly as in production.
    """
    dinn = DINN(n_input_channels=n_channels, hidden_dim=hidden_dim, n_outputs=6).to(
        device=device, dtype=dtype
    )
    env = torch.randn(n_channels, 1, n_cells, device=device, dtype=dtype)
    state0 = torch.tensor(_STATE0_BY_INDEX, device=device, dtype=dtype).reshape(
        N_TRACERS_2LAYER, 1, 1
    ).expand(N_TRACERS_2LAYER, 1, n_cells).contiguous()
    forcing = {
        "T": torch.full((1, n_cells), 18.0, device=device, dtype=dtype),
        "S": torch.full((1, n_cells), 35.0, device=device, dtype=dtype),
        "wind": torch.full((1, n_cells), 7.0, device=device, dtype=dtype),
    }
    return dinn, env, state0, forcing


def _bounded(theta: torch.Tensor, device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    """Sigmoid-bound DINN output (shape ``[6, 1, n_cells]``) to positive ranges.

    Kept inline (rather than importing ``carroll6.bounded_params``) so the harness
    is self-contained; the bounding op is a single elementwise pass whose memory is
    negligible against the multi-step integration graph it precedes.
    """
    bounds = torch.tensor(_PARAM_BOUNDS, device=device, dtype=dtype)  # [6, 2]
    lo = bounds[:, 0].reshape(6, 1, 1)
    hi = bounds[:, 1].reshape(6, 1, 1)
    return lo + (hi - lo) * torch.sigmoid(theta)


def _peak_bytes(device: torch.device) -> int | None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)
        return int(torch.cuda.max_memory_allocated(device))
    return None


def measure_peak(
    n_cells: int,
    n_steps: int,
    *,
    n_channels: int = 3,
    hidden_dim: int = 16,
    device: torch.device | str = "cuda",
    dtype: torch.dtype = torch.float32,
) -> MemRecord:
    """Measure peak memory of one train step (and a forward-only pass) at this size.

    Returns a :class:`MemRecord`. On CPU the CUDA peak is unavailable so the byte
    fields are ``None`` but the forward/backward graph still executes (smoke path).
    OOM is caught and recorded as ``oom=True`` with ``None`` bytes.
    """
    device = torch.device(device)

    # --- forward-only peak (no graph retained) ---
    forward_peak: int | None = None
    try:
        if device.type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
        dinn, env, state0, forcing = _build_inputs(n_cells, n_channels, hidden_dim, device, dtype)
        with torch.no_grad():
            params = _bounded(dinn(env), device, dtype)
            _ = carroll6_5pft_2layer_integrate(state0, params, DT_DAYS, n_steps, **forcing)
        forward_peak = _peak_bytes(device)
        del dinn, env, state0, forcing
    except torch.cuda.OutOfMemoryError:
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return MemRecord(n_cells, n_steps, None, None, oom=True)

    # --- train peak (forward + backward, full autograd graph) ---
    try:
        if device.type == "cuda":
            torch.cuda.empty_cache()
            torch.cuda.reset_peak_memory_stats(device)
        dinn, env, state0, forcing = _build_inputs(n_cells, n_channels, hidden_dim, device, dtype)
        params = _bounded(dinn(env), device, dtype)
        final = carroll6_5pft_2layer_integrate(state0, params, DT_DAYS, n_steps, **forcing)
        loss = final.pow(2).mean()
        loss.backward()
        train_peak = _peak_bytes(device)
        del dinn, env, state0, forcing, params, final, loss
    except torch.cuda.OutOfMemoryError:
        if device.type == "cuda":
            torch.cuda.empty_cache()
        return MemRecord(n_cells, n_steps, None, forward_peak, oom=True)

    if device.type == "cuda":
        torch.cuda.empty_cache()
    return MemRecord(n_cells, n_steps, train_peak, forward_peak, oom=False)


def fit_cellstep_scaling(records: list[MemRecord]) -> dict[str, float]:
    """Least-squares fit ``train_peak = a + b * (cells * steps)``.

    Returns ``{a_bytes, b_bytes_per_cellstep, r2, n}``. Records with missing
    ``train_peak_bytes`` (CPU / OOM) are skipped.
    """
    xs = [float(r.n_cells * r.n_steps) for r in records if r.train_peak_bytes is not None]
    ys = [float(r.train_peak_bytes) for r in records if r.train_peak_bytes is not None]
    if len(xs) < 2:
        return {"a_bytes": float("nan"), "b_bytes_per_cellstep": float("nan"), "r2": float("nan"),
                "n": float(len(xs))}
    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxx = sum(x * x for x in xs)
    sxy = sum(x * y for x, y in zip(xs, ys, strict=True))
    denom = n * sxx - sx * sx
    b = (n * sxy - sx * sy) / denom
    a = (sy - b * sx) / n
    mean_y = sy / n
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    ss_res = sum((y - (a + b * x)) ** 2 for x, y in zip(xs, ys, strict=True))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return {"a_bytes": a, "b_bytes_per_cellstep": b, "r2": r2, "n": float(n)}


def extrapolate(fit: dict[str, float], targets: tuple[ExtrapTarget, ...]) -> list[dict[str, float]]:
    """Predict peak GB at each extrapolation target from the fitted scaling."""
    a = fit["a_bytes"]
    b = fit["b_bytes_per_cellstep"]
    out: list[dict[str, float]] = []
    for t in targets:
        pred_bytes = a + b * (t.cells * t.steps)
        out.append({"label": t.label, "cells": float(t.cells), "steps": float(t.steps),
                    "pred_bytes": pred_bytes, "pred_gb": pred_bytes / 1024**3})
    return out


def _gb(b: int | float | None) -> str:
    return "OOM/—" if b is None else f"{b / 1024**3:.2f}"


def _render_markdown(
    records: list[MemRecord],
    fit: dict[str, float],
    extrap: list[dict[str, float]],
    device_name: str,
    total_mem_gb: float | None,
) -> str:
    lines: list[str] = []
    lines.append("# Measured GPU-memory scaling — native / seasonal compute sizing\n")
    lines.append(
        "Generated by `scripts/measure_memory_scaling.py`. Peak memory of one "
        "`DINN → integrate → loss → backward` pass (eager autograd, **pre-checkpointing**) "
        "vs problem size. Memory of a fixed graph is value-independent, so synthetic "
        "inputs reproduce a real fit's footprint at matched shapes.\n"
    )
    lines.append(f"- **Device:** {device_name}"
                 + (f" ({total_mem_gb:.1f} GB total)\n" if total_mem_gb else "\n"))
    lines.append(f"- **Box:** {N_TRACERS_2LAYER}-tracer 2-layer, DT={DT_DAYS} d, "
                 "DINN (per-cell 1x1 conv).\n")
    lines.append(
        f"- **Fit** `peak = a + b·(cells·steps)`: "
        f"a = {fit['a_bytes'] / 1024**2:.1f} MB, "
        f"b = {fit['b_bytes_per_cellstep']:.3g} B per cell·step, "
        f"R² = {fit['r2']:.5f} (n={int(fit['n'])}).\n"
    )

    lines.append("\n## Measurements\n")
    lines.append("| cells | steps | train peak (GB) | forward-only (GB) | AD overhead x |")
    lines.append("|---|---|---|---|---|")
    for r in sorted(records, key=lambda r: (r.n_cells, r.n_steps)):
        if r.train_peak_bytes and r.forward_peak_bytes:
            ovh = f"{r.train_peak_bytes / r.forward_peak_bytes:.1f}"
        else:
            ovh = "—"
        flag = " (OOM)" if r.oom else ""
        lines.append(f"| {r.n_cells:,} | {r.n_steps} | {_gb(r.train_peak_bytes)}{flag} "
                     f"| {_gb(r.forward_peak_bytes)} | {ovh} |")

    lines.append("\n## Extrapolation to the proposal grids\n")
    lines.append(f"Seasonal assumes ~{SEASONAL_STEPS} steps (one annual cycle at DT="
                 f"{DT_DAYS} d ≈ 1460 + spin-up); time-mean ~{TIME_MEAN_STEPS}. "
                 "Pre-checkpointing peak = the upper bound to size hardware against.\n")
    lines.append("| target | cells | steps | predicted peak (GB) |")
    lines.append("|---|---|---|---|")
    for e in extrap:
        lines.append(f"| {e['label']} | {int(e['cells']):,} | {int(e['steps'])} "
                     f"| {e['pred_gb']:.1f} |")
    lines.append("")
    return "\n".join(lines)


def _default_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", default=_default_device(), help="cuda | cpu")
    parser.add_argument("--cells", type=int, nargs="+",
                        default=[2_000, 4_000, 8_000, 16_000, 32_000])
    parser.add_argument("--steps", type=int, nargs="+", default=[50, 100, 200, 400])
    parser.add_argument("--hidden-dim", type=int, default=16)
    parser.add_argument("--channels", type=int, default=3)
    parser.add_argument("--out", type=Path, default=None, help="write raw results JSON here")
    parser.add_argument("--md", type=Path, default=None, help="markdown findings table out")
    args = parser.parse_args(argv)

    device = torch.device(args.device)
    device_name = (torch.cuda.get_device_name(device) if device.type == "cuda"
                   else f"CPU ({platform.processor() or platform.machine()})")
    total_mem_gb = (torch.cuda.get_device_properties(device).total_memory / 1024**3
                    if device.type == "cuda" else None)
    print(f"device: {device_name}"
          + (f" — {total_mem_gb:.1f} GB" if total_mem_gb else " (no CUDA peak)"))

    records: list[MemRecord] = []
    for n_cells in args.cells:
        for n_steps in args.steps:
            rec = measure_peak(n_cells, n_steps, n_channels=args.channels,
                               hidden_dim=args.hidden_dim, device=device)
            records.append(rec)
            print(f"  cells={n_cells:>7,} steps={n_steps:>4}  "
                  f"train={_gb(rec.train_peak_bytes)} GB  "
                  f"fwd={_gb(rec.forward_peak_bytes)} GB"
                  + ("  [OOM]" if rec.oom else ""))

    fit = fit_cellstep_scaling(records)
    extrap = extrapolate(fit, EXTRAPOLATION_TARGETS)

    print(f"\nfit: peak = {fit['a_bytes'] / 1024**2:.1f} MB "
          f"+ {fit['b_bytes_per_cellstep']:.3g} B/(cell·step)  R²={fit['r2']:.5f}")
    print("extrapolation:")
    for e in extrap:
        print(f"  {e['label']:<40} {e['pred_gb']:8.1f} GB")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps({
            "device": device_name,
            "total_mem_gb": total_mem_gb,
            "records": [asdict(r) for r in records],
            "fit": fit,
            "extrapolation": extrap,
        }, indent=2), encoding="utf-8")
        print(f"\nwrote {args.out}")
    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        args.md.write_text(_render_markdown(records, fit, extrap, device_name, total_mem_gb),
                           encoding="utf-8")
        print(f"wrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
