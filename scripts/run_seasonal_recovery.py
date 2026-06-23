"""Minimal transient-seasonal Carroll-6 recovery on real ECCO-Darwin v05 1-deg data.

Drives ``carroll6_5pft_2layer_integrate_seasonal`` end to end on the 1-degree
``bin_average`` product (already on disk): a per-cell DINN predicts static Carroll-6
params from annual-mean SST, the box is integrated through a transient annual cycle
with **monthly** SST/SSS/wind forcing, and the 12 month-end phytoplankton fields are
fit (z-scored, pattern-only) to Darwin's 12-month Chl1-5 climatology. ``--mode
time-mean`` runs the existing single-block integrator on the same data for a
head-to-head.

This is the **laptop-scale prototype** of the seasonal experiment; the
native-resolution / multi-GPU version is the AICR proposal.

**Batched + compiled + verifiable (the AICR-readiness path, #115/#119).** ``--n-seeds
S`` trains S independently-seeded DINNs in ONE graph (the box is per-cell, so the seed
axis folds into the spatial dims -- proven seed-independent in
``tests/test_seasonal_batch.py``), and ``--compile`` ``torch.compile``'s the per-step to
cut the kernel-launch overhead that otherwise leaves the B200 launch-bound. Every run
writes one per-seed JSON in the schema ``scripts/verify_run.py`` recomputes against, so
the first cluster fit is gateable by the verified loop instead of emitting nothing.

**Scope (honest):** a Chl-only loss constrains the growth (Smallgrow/Biggrow),
grazing (diatomgraz), and iron (alpfe/scav_rat via growth) params. **R_PICPOC is
NOT constrained here** -- it only enters PIC/DIC/ALK, and ``bin_average`` carries no
PIC. The R_PICPOC seasonal test needs a monthly PIC target (PIC is in the native
``output/monthly/`` tree, not ``bin_average``) -- the immediate follow-on.

**Prototype caveats (vs the Darwin-IC v3.0 trainer):** this driver uses a single
constant initial state (not per-cell Darwin pickup ICs) and constant carbonate
forcing (``PCO2_ATM_DEFAULT``, not Darwin ``apCO2``); time-mean mode integrates at
mean-over-months forcing (a nonlinear-Jensen approximation of the annual mean). So
DIC/ALK/PIC and absolute recovery numbers here are a lower bound, not directly
comparable to the trainer.

Run with the project environment (``uv run``, or the repo ``.venv`` python). A bare
``python`` on PATH may resolve an editable ``darwindiff`` install from a stale
worktree and ImportError or run old code, so prefer::

    uv run python scripts/run_seasonal_recovery.py --aoi eqpac --epochs 600
    uv run python scripts/run_seasonal_recovery.py --aoi natlsubpolar --mode time-mean --epochs 600
    # batched + compiled (WSL/cluster), then gate the artifacts:
    uv run python scripts/run_seasonal_recovery.py --aoi eqpac --n-seeds 10 --compile \
        --out-dir runs/seasonal/eqpac
    uv run python scripts/verify_run.py runs/seasonal/eqpac
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES, PARAM_BOUNDS, PARAM_NAMES, bounded_params
from darwindiff.carroll6_5pft_2layer import (
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_integrate_seasonal,
    carroll6_5pft_2layer_step,
)
from darwindiff.ecco_darwin_loader import (
    AOI_BY_KEY,
    monthly_climatology,
    ocean_mask,
    open_bin_average,
    subset_aoi,
    time_mean,
)
from darwindiff.networks import DINN
from darwindiff.seasonal import (
    constant_state0,
    seasonal_chl_loss_batched,
    seed_recovery_json,
    timemean_chl_loss_batched,
    zscore_masked,
)

DT = 0.25
DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
BIN_AVG = DATA_ROOT / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc"


def _load_aoi(aoi_key: str, device: torch.device):
    """Return (env, forcing_monthly, chl_target_z, mask) for one AOI."""
    if not BIN_AVG.exists():
        raise FileNotFoundError(f"bin_average product not found at {BIN_AVG} "
                                "(set DARWIN_DATA_ROOT)")
    if aoi_key not in AOI_BY_KEY:
        raise ValueError(f"unknown AOI '{aoi_key}'; choose from {sorted(AOI_BY_KEY)}")

    ds = subset_aoi(open_bin_average(BIN_AVG), AOI_BY_KEY[aoi_key])
    mask_np = ocean_mask(ds).values.astype(bool)
    mask = torch.tensor(mask_np, device=device)

    # DINN input: annual-mean SST, z-scored over ocean (static -> static params).
    sst_mean = time_mean(ds)["SST"].values.astype(np.float32)
    sst_t = torch.tensor(np.nan_to_num(sst_mean, nan=15.0), device=device)
    env = zscore_masked(sst_t, mask)[None]  # [1, H, W]
    assert env.ndim == 3 and env.shape[0] == 1, f"env must be [1,H,W], got {tuple(env.shape)}"

    # Monthly forcing for the transient cycle (land NaNs -> finite fill, masked out).
    mc = monthly_climatology(ds)

    def _force(name: str, fill: float) -> torch.Tensor:
        arr = mc[name].values.astype(np.float32)  # [12, H, W]
        return torch.tensor(np.nan_to_num(arr, nan=fill), device=device)

    forcing = {
        "T_monthly": _force("SST", 15.0),
        "S_monthly": _force("SSS", 35.0),
        "wind_monthly": _force("windSpeed", 7.0),
    }

    # Targets: Darwin Chl1-5, 12 monthly maps, z-scored per (month, PFT) over ocean.
    chl_z = torch.zeros(12, 5, *mask.shape, device=device)
    for p in range(5):
        chl_m = torch.tensor(
            np.nan_to_num(mc[f"Chl{p + 1}"].values.astype(np.float32), nan=0.0),
            device=device,
        )  # [12, H, W]
        for m in range(12):
            chl_z[m, p] = zscore_masked(chl_m[m], mask)
    return env, forcing, chl_z, mask


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--aoi", default="eqpac", choices=sorted(AOI_BY_KEY))
    parser.add_argument("--mode", default="seasonal", choices=["seasonal", "time-mean"])
    parser.add_argument("--epochs", type=int, default=600)
    parser.add_argument("--lr", type=float, default=5e-3)
    parser.add_argument("--steps-per-month", type=int, default=122)
    parser.add_argument("--spinup-cycles", type=int, default=0)
    parser.add_argument("--n-steps", type=int, default=200, help="time-mean mode step count")
    parser.add_argument("--seed", type=int, default=0, help="base seed; seed i uses base+i")
    parser.add_argument("--n-seeds", type=int, default=1,
                        help="seeds trained together in ONE batched (optionally compiled) graph")
    parser.add_argument("--compile", action="store_true",
                        help="torch.compile the per-step (Linux/WSL; eager fallback on failure)")
    parser.add_argument("--out-dir", default=os.environ.get("OUTPUT_DIR"),
                        help="dir for per-seed verify_run JSON "
                             "(default $OUTPUT_DIR, else runs/seasonal/<aoi>_<mode>)")
    parser.add_argument("--no-json", action="store_true", help="skip JSON write (print only)")
    args = parser.parse_args(argv)
    if args.n_seeds < 1:
        parser.error("--n-seeds must be >= 1")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    env, forcing, chl_z, mask = _load_aoi(args.aoi, device)
    shape = tuple(mask.shape)
    n_seeds = args.n_seeds
    print(f"AOI {args.aoi}: grid {shape}, {int(mask.sum())} ocean cells, mode={args.mode}, "
          f"seeds={n_seeds} (base={args.seed}), device={device.type}")

    bounds = PARAM_BOUNDS.to(device)
    # One independently-seeded DINN per seed; their per-cell outputs stack into a
    # [6, n_seeds, H, W] tensor so all seeds train in ONE graph. The box is per-cell,
    # so the seed axis is just folded into the spatial dims -- proven seed-independent
    # in tests/test_seasonal_batch.py.
    nets: list[DINN] = []
    for i in range(n_seeds):
        torch.manual_seed(args.seed + i)
        nets.append(DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device))
    state0 = constant_state0((n_seeds, *shape), device)  # [15, n_seeds, H, W]
    opt = torch.optim.Adam([p for net in nets for p in net.parameters()], lr=args.lr)

    # Optional torch.compile of the per-step (mirrors run_v3.0_joint_multi_aoi.py). The
    # rollout stays a Python loop; compiling the tight inner step fuses its elementwise
    # ops and cuts kernel-launch overhead -- the launch-bound bottleneck on B200.
    step_fn = carroll6_5pft_2layer_step
    if args.compile:
        try:
            step_fn = torch.compile(carroll6_5pft_2layer_step, mode="default")
            print("torch.compile applied to per-step (mode='default').")
        except Exception as e:  # any inductor/compile failure -> eager fallback
            print(f"torch.compile failed ({e}); falling back to eager per-step.")
            step_fn = carroll6_5pft_2layer_step
    compiled = args.compile and step_fn is not carroll6_5pft_2layer_step

    def _params_batched() -> torch.Tensor:
        # [6, n_seeds, H, W]: stack each seed's per-cell DINN output along a seed axis.
        return torch.stack([bounded_params(net(env), bounds) for net in nets], dim=1)

    t0 = time.perf_counter()
    loss_vec = torch.zeros(n_seeds, device=device)
    for epoch in range(args.epochs):
        opt.zero_grad()
        params = _params_batched()  # [6, n_seeds, H, W]
        if args.mode == "seasonal":
            snaps = carroll6_5pft_2layer_integrate_seasonal(
                state0, params, DT, forcing["T_monthly"], forcing["S_monthly"],
                forcing["wind_monthly"], steps_per_month=args.steps_per_month,
                n_spinup_cycles=args.spinup_cycles, step_fn=step_fn,
            )
            loss_vec = seasonal_chl_loss_batched(snaps, chl_z, mask)  # [n_seeds]
        else:
            state = carroll6_5pft_2layer_integrate(
                state0, params, DT, args.n_steps,
                T=forcing["T_monthly"].mean(0), S=forcing["S_monthly"].mean(0),
                wind=forcing["wind_monthly"].mean(0), step_fn=step_fn,
            )
            loss_vec = timemean_chl_loss_batched(state, chl_z, mask)  # [n_seeds]
        # Per-seed losses are independent (each depends only on its own net), so the
        # summed objective hands each seed its own correct gradient.
        loss_vec.sum().backward()
        opt.step()
        if (epoch + 1) % 100 == 0 or epoch == 0:
            lm = float(loss_vec.mean().detach())
            print(f"  epoch {epoch + 1:4d}  loss(mean/{n_seeds})={lm:.4e}")
    elapsed = time.perf_counter() - t0
    print(f"trained {n_seeds} seeds x {args.epochs} epochs in {elapsed:.1f}s "
          f"({elapsed / n_seeds:.1f}s amortized/seed) "
          f"[{'compiled' if compiled else 'eager'}]")

    # --- Recovery + per-seed JSON in the verify_run.py schema ---
    out_dir: Path | None = None
    if not args.no_json:
        base = args.out_dir or str(Path("runs") / "seasonal" / f"{args.aoi}_{args.mode}")
        out_dir = Path(base)
        out_dir.mkdir(parents=True, exist_ok=True)

    carroll = [float(c) for c in CARROLL_VALUES]
    records: list[dict] = []
    with torch.no_grad():
        params = _params_batched()  # [6, n_seeds, H, W]
        for i in range(n_seeds):
            rec = params[:, i][:, mask].mean(dim=1).cpu()  # [6] ocean-mean per param
            record = seed_recovery_json(
                seed=args.seed + i,
                recovered=[float(v) for v in rec],
                aoi=args.aoi,
                carroll=carroll,
                param_names=PARAM_NAMES,
                n_seeds_in_batch=n_seeds,
                loss_final=float(loss_vec[i].detach()),
                extra={
                    "mode": args.mode,
                    "n_epochs": args.epochs,
                    "lr": args.lr,
                    "steps_per_month": args.steps_per_month if args.mode == "seasonal" else None,
                    "n_steps": args.n_steps if args.mode == "time-mean" else None,
                    "spinup_cycles": args.spinup_cycles,
                    "compiled": compiled,
                    "elapsed_s_total_batch": elapsed,
                    "device": device.type,
                    # Chl-only pattern loss does NOT constrain R_PICPOC (PIC absent from
                    # bin_average) -- flagged so the science read excludes it. See module docstring.
                    "r_picpoc_unconstrained": True,
                    "loss_kind": "chl_zscore_pattern",
                },
            )
            records.append(record)
            if out_dir is not None:
                fname = f"run_seasonal_{args.aoi}_{args.mode}_seed{args.seed + i}.json"
                with (out_dir / fname).open("w", encoding="utf-8") as f:
                    json.dump(record, f, indent=2, allow_nan=False)

    # Print the per-param table for the first seed (representative of the batch).
    r0 = records[0]
    print(f"\n=== Recovered Carroll-6 ({args.aoi}, {args.mode}, seed {r0['seed']}) ===")
    print(f"{'param':<11}{'recovered':>13}{'carroll':>13}{'rel.err':>9}  grade")
    for name in PARAM_NAMES:
        pp = r0["params"][name]
        note = "  (unconstrained: Chl-only)" if name == "R_PICPOC" else ""
        print(f"{name:<11}{pp['joint_recovered']:>13.4g}{pp['joint_carroll_published']:>13.4g}"
              f"{pp['joint_abs_rel_offset']:>8.0%}  {pp['joint_band']}{note}")
    ks = [r["n_cal_grade"] for r in records]
    print(f"\nseed {r0['seed']}: {r0['n_cal_grade']}/6 Cal-grade+; batch k-by-seed={ks} "
          "(R_PICPOC excluded from the science read -- needs a monthly PIC target).")
    if out_dir is not None:
        print(f"wrote {len(records)} per-seed JSON to {out_dir}\n"
              f"  verify: python scripts/verify_run.py \"{out_dir}\"")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
