"""Phase 2 prerequisite checks P4 (PFT abundance) + P5 (autograd memory budget).

P4: Time-mean Chl1..Chl5 magnitudes over the Equatorial Pacific AOI from
    bin_average. Tells us which PFT dominates - constrains the Option A
    sub-decision "which PFT does Smallgrow map to?".

P5: Peak VRAM for a per-cell autograd integration matching the eventual
    5-PFT box shape (10 tracers, 200 forward-Euler steps, [params, H, W]
    parameterization). Tells us whether the 5-PFT extension fits on the
    RTX 5090 Laptop without gradient checkpointing.

Both are one-off prereq diagnostics, not part of the package.
"""

from __future__ import annotations

import os
from pathlib import Path

import torch
import xarray as xr

from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    open_bin_average,
    subset_aoi,
    time_mean,
)

DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
BIN_AVERAGE_NC = str(DATA_ROOT / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc")


def p4_pft_abundance() -> dict[str, float]:
    """Time-mean Chl1..Chl5 over Eq Pacific (mg Chl a / m^3)."""
    print("=" * 70)
    print("P4: Eq Pacific PFT abundance (time-mean Chl1..Chl5)")
    print("=" * 70)
    print(f"AOI: {EQUATORIAL_PACIFIC_AOI.name} "
          f"({EQUATORIAL_PACIFIC_AOI.lat_min}-{EQUATORIAL_PACIFIC_AOI.lat_max} N, "
          f"{EQUATORIAL_PACIFIC_AOI.lon_min}-{EQUATORIAL_PACIFIC_AOI.lon_max} E)")

    ds = open_bin_average(BIN_AVERAGE_NC)
    print(f"  bin_average dims: {dict(ds.sizes)}")
    print(f"  data_vars (first 12): {list(ds.data_vars)[:12]}")

    aoi = subset_aoi(ds, EQUATORIAL_PACIFIC_AOI)
    print(f"  AOI dims: {dict(aoi.sizes)}")

    means: dict[str, float] = {}
    for i in range(1, 6):
        name = f"Chl{i}"
        if name in aoi.data_vars:
            val = float(aoi[name].mean().values)
            means[name] = val
            print(f"  {name}: {val:.4f} mg Chl a / m^3")
        else:
            print(f"  {name}: NOT IN DATASET")
            means[name] = float("nan")

    total = sum(v for v in means.values() if v == v)
    if total > 0:
        print(f"\n  Relative abundance (fraction of total Chl):")
        for name, val in means.items():
            if val == val:
                print(f"    {name}: {val/total*100:.1f}%")
    return means


def p5_autograd_memory() -> dict[str, float]:
    """Peak VRAM for 10-tracer x 200-step per-cell autograd integration."""
    print("\n" + "=" * 70)
    print("P5: VRAM budget for per-cell autograd integration")
    print("=" * 70)
    device = torch.device("cuda")
    total_gb = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  device: {torch.cuda.get_device_name(0)}")
    print(f"  total VRAM: {total_gb:.1f} GB")

    H, W = 20, 50
    n_steps = 200
    dt = 0.25

    K_FE, M_LIN, M_QUAD, G0_GRAZE, W_SINK, PHI_DUST, Q_FE = (
        5e-5, 0.05, 0.5, 0.3, 0.1, 5e-5, 1e-5,
    )

    def integrate_box(n_tracers: int, n_params: int) -> float:
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
        theta = torch.zeros(n_params, H, W, device=device, requires_grad=True)
        params = torch.sigmoid(theta) * 0.5 + 0.1

        init = [5.0e-4] + [1.0] * (n_tracers - 5) + [0.5, 0.025, 2100.0, 2400.0]
        # Pad to n_tracers in case the list isn't right size
        init = (init + [1.0] * n_tracers)[:n_tracers]
        state = torch.tensor(init, device=device).unsqueeze(-1).unsqueeze(-1).expand(n_tracers, H, W).contiguous()

        for _ in range(n_steps):
            DFe = state[0]
            # phyto contribute to growth + mort
            n_phyto = n_tracers - 5  # DFe + n_phyto phyto + POC + PIC + DIC + ALK
            phyto = state[1:1 + n_phyto]  # [n_phyto, H, W]
            POC = state[1 + n_phyto]
            PIC = state[2 + n_phyto]
            DIC = state[3 + n_phyto]
            ALK = state[4 + n_phyto]

            f_fe = DFe / (DFe + K_FE)
            # one growth-rate param per phyto (approximating per-PFT params)
            mu_phyto = params[:n_phyto] if n_params >= n_phyto else params[0:1].expand(n_phyto, H, W)
            growth = mu_phyto * f_fe * phyto
            mort = M_LIN * phyto + M_QUAD * phyto * phyto
            mort_total = mort.sum(0) + (params[-2] * G0_GRAZE * phyto[-1] if n_params > 1 else 0)
            fe_uptake = Q_FE * growth.sum(0)
            R_PICPOC = params[-1]

            new_DFe = DFe + dt * (params[0] * PHI_DUST - params[1] * 86400 * DFe * POC - fe_uptake)
            new_phyto = phyto + dt * (growth - mort)
            new_POC = POC + dt * (mort_total - W_SINK * POC)
            new_PIC = PIC + dt * (R_PICPOC * mort_total - W_SINK * PIC)
            new_DIC = DIC + dt * (-growth.sum(0) - R_PICPOC * mort_total)
            new_ALK = ALK + dt * (-2.0 * R_PICPOC * mort_total)

            state = torch.cat([
                new_DFe.unsqueeze(0),
                new_phyto,
                new_POC.unsqueeze(0),
                new_PIC.unsqueeze(0),
                new_DIC.unsqueeze(0),
                new_ALK.unsqueeze(0),
            ], dim=0)

        loss = state.sum()
        loss.backward()
        return torch.cuda.max_memory_allocated() / 1024**2

    print(f"\n  Per-cell fit: theta shape [n_params, {H}, {W}] = [n_params, {H*W}]")
    print(f"  Integration: {n_steps} forward-Euler steps, dt={dt} days")
    print(f"  Autograd retained activations × 200 steps\n")

    peak_7tr = integrate_box(n_tracers=7, n_params=6)
    print(f"  7-tracer  /  6-param  baseline (matches v2.0 nb20): {peak_7tr:.1f} MB")

    peak_10tr_6p = integrate_box(n_tracers=10, n_params=6)
    print(f"  10-tracer /  6-param  Phase 2 Option A:              {peak_10tr_6p:.1f} MB")

    peak_10tr_14p = integrate_box(n_tracers=10, n_params=14)
    print(f"  10-tracer / 14-param  Phase 2 Option B:              {peak_10tr_14p:.1f} MB")

    print(f"\n  Headroom on {total_gb:.1f} GB VRAM for Option A: "
          f"{(total_gb * 1024 - peak_10tr_6p) / 1024:.1f} GB free ({(1 - peak_10tr_6p/(total_gb*1024))*100:.0f}% unused)")

    return {
        "total_gb": total_gb,
        "peak_7tr_mb": peak_7tr,
        "peak_10tr_6p_mb": peak_10tr_6p,
        "peak_10tr_14p_mb": peak_10tr_14p,
    }


if __name__ == "__main__":
    p4_pft_abundance()
    p5_autograd_memory()
