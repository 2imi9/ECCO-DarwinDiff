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
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES, PARAM_BOUNDS, PARAM_NAMES, bounded_params
from darwindiff.carroll6_5pft_2layer import (
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_integrate_seasonal,
)
from darwindiff.diagnostics import band_of
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
    seasonal_chl_loss,
    timemean_chl_loss,
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
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch.manual_seed(args.seed)
    env, forcing, chl_z, mask = _load_aoi(args.aoi, device)
    shape = tuple(mask.shape)
    print(f"AOI {args.aoi}: grid {shape}, {int(mask.sum())} ocean cells, "
          f"mode={args.mode}, device={device.type}")

    dinn = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
    bounds = PARAM_BOUNDS.to(device)
    state0 = constant_state0(shape, device)
    opt = torch.optim.Adam(dinn.parameters(), lr=args.lr)

    for epoch in range(args.epochs):
        opt.zero_grad()
        params = bounded_params(dinn(env), bounds)  # [6, H, W]
        if args.mode == "seasonal":
            snaps = carroll6_5pft_2layer_integrate_seasonal(
                state0, params, DT, forcing["T_monthly"], forcing["S_monthly"],
                forcing["wind_monthly"], steps_per_month=args.steps_per_month,
                n_spinup_cycles=args.spinup_cycles,
            )
            loss = seasonal_chl_loss(snaps, chl_z, mask)
        else:
            state = carroll6_5pft_2layer_integrate(
                state0, params, DT, args.n_steps,
                T=forcing["T_monthly"].mean(0), S=forcing["S_monthly"].mean(0),
                wind=forcing["wind_monthly"].mean(0),
            )
            loss = timemean_chl_loss(state, chl_z, mask)
        loss.backward()
        opt.step()
        if (epoch + 1) % 100 == 0 or epoch == 0:
            print(f"  epoch {epoch + 1:4d}  loss={float(loss.detach()):.4e}")

    # Recovery: ocean-mean of each per-cell param vs Carroll's published values.
    with torch.no_grad():
        params = bounded_params(dinn(env), bounds)
        rec = params[:, mask].mean(dim=1).cpu()
    carroll = CARROLL_VALUES
    print(f"\n=== Recovered Carroll-6 ({args.aoi}, {args.mode}) ===")
    print(f"{'param':<11}{'recovered':>13}{'carroll':>13}{'rel.err':>9}  grade")
    n_cal = 0
    for i, name in enumerate(PARAM_NAMES):
        rel = abs(float(rec[i]) - float(carroll[i])) / abs(float(carroll[i]))
        grade = band_of(rel)  # canonical bands: Excellent<=0.05, Cal-grade<=0.40, ...
        n_cal += grade in ("Excellent", "Cal-grade")
        note = "  (unconstrained: Chl-only)" if name == "R_PICPOC" else ""
        print(f"{name:<11}{float(rec[i]):>13.4g}{float(carroll[i]):>13.4g}"
              f"{rel:>8.0%}  {grade}{note}")
    print(f"\n{n_cal}/6 Cal-grade or better. "
          "(R_PICPOC excluded from the science read here -- needs a monthly PIC target.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
