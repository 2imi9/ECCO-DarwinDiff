"""The iron information wall, made explicit: dissolved-iron CONCENTRATION constrains only a
COMBINATION of the source (alpfe) and sink (scav_rat), not the scavenging rate itself.

The identifiability map (geotraces_glodap_identifiability.py) showed DFe concentration is
env-predictable but argued -- from Tagliabue 2016 + Track-1 -- that concentration
under-constrains the scavenging RATE. This script demonstrates that directly through the real
prescribed-transport model: sweep a 2-D grid over (alpfe, scav_rat), forward-roll DFe to
(quasi-)steady state, and score the misfit. Because steady-state DFe ~ alpfe*dust /
(scav_rat*POC + ...), the good-fit region is a DEGENERATE RIDGE (alpfe/scav_rat ~ const):
many (source, sink) pairs reproduce the same concentration; profiling out alpfe leaves the
scav_rat likelihood FLAT -> the rate is not identifiable from concentration. The wall.

Two targets:
- ``twin`` (default): target = model DFe at Carroll on the real observing footprint. Isolates
  the STRUCTURAL source/sink degeneracy (the wall) from the iron-starvation confound.
- ``geotraces``: real GEOTRACES DFe. Note the model is iron-starved with the real (low) DB-1
  dust -- a distinct DB-1 transport-supply issue that dominates that fit.

Compute is small + launch-bound (a few hundred forward rollouts, no training), so it runs the
same speed on any GPU. To keep it OFF the local GPU, either force CPU (``CUDA_VISIBLE_DEVICES=``)
or run it on Explorer H200 from a pre-built input bundle:

    # locally, CPU only (no GPU touch): build the small bundle
    python scripts/iron_scav_rat_profile.py --build-bundle /tmp/iron_bundle.pt
    # on Explorer H200 (sbatch): run the sweep from the bundle
    python scripts/iron_scav_rat_profile.py --bundle iron_bundle.pt

The bundle carries only small AOI tensors (u/v/w/dust/ic/target/mask), never the ~TB native
tree -- the data-discipline pattern. (AICR B200 is interactive-only / Duo-gated, so it is not
an automation target; reference_aicr_usage.)
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES, P
from darwindiff.safe_load import safe_torch_load
from darwindiff.trainer import TransportConfig, rollout_field

DX = DY = 1.11e5
N_Z = 6
DZ = 10.0
EPS = 1e-12
GEOTRACES = os.environ.get("GEOTRACES_NC", r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")


def build_inputs() -> dict:
    """Compute the small AOI input tensors on CPU (heavy native-data loaders; no GPU).

    Returns a device-agnostic dict for the sweep: barotropic div-free (u, v, w), surface dust,
    5-tracer IC, the real GEOTRACES log-DFe target + coverage mask, and Carroll params. Only
    imported here so the cluster-side (bundle) path does not need the native loaders/data.
    """
    from darwindiff.ecco_darwin_loader import EQUATORIAL_PACIFIC_AOI as EQ
    from darwindiff.geotraces_loader import dfe_aoi_1deg_grid
    from darwindiff.iron_forcing_loader import (
        IRONFILE_NAME,
        coverage_mask,
        iron_flux_aoi_grid,
        phi_dust_surface_field,
    )
    from darwindiff.velocity_loader import (
        depth_mean,
        divfree_barotropic_velocity,
        velocity_aoi_grid,
    )
    root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    monthly, grid = root / "output" / "monthly", root / "grid"
    iron = root / "input" / IRONFILE_NAME
    cache = root / "cache" / "eqpac_targets_equatorial_pacific.pt"
    dt64 = torch.float64

    vel = velocity_aoi_grid(monthly, grid, EQ, n_z=N_Z)
    u, v, w = divfree_barotropic_velocity(depth_mean(vel["u"]), depth_mean(vel["v"]),
                                          DX, DY, DZ, N_Z, dtype=dt64)
    areal = iron_flux_aoi_grid(iron, grid, EQ)
    dust = phi_dust_surface_field(areal, DZ, N_Z, dtype=dt64)
    dfe_obs = dfe_aoi_1deg_grid(GEOTRACES, EQ)
    cov = np.isfinite(dfe_obs) & (dfe_obs > 0) & coverage_mask(areal)

    c = safe_torch_load(cache)

    def f(k, fb):
        a = torch.as_tensor(np.asarray(c[k], np.float64), dtype=dt64)
        return torch.nan_to_num(a, nan=fb, posinf=fb, neginf=fb).clamp_min(1e-6)
    dfe, poc, pic = f("fet_binned", 1e-4), f("poc_binned", 0.1), f("pic_binned", 1e-3)
    ny, nx = dfe.shape
    small = torch.full((ny, nx), 0.1, dtype=dt64)
    ic = torch.stack([dfe, small, small, poc, pic], dim=-1).unsqueeze(-2).expand(ny, nx, N_Z, 5).contiguous()
    return {
        "u": u, "v": v, "w": w, "dust": dust, "ic": ic,
        "tgt_geo": torch.as_tensor(np.log(np.where(cov, dfe_obs, 1.0)), dtype=dt64),
        "mask": torch.as_tensor(cov, dtype=torch.bool),
        "base": torch.tensor([CARROLL_VALUES[i] for i in range(6)], dtype=dt64),
    }


def run(inp: dict, mode: str, n_steps: int = 100, out: str | None = None) -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float32 if device.type == "cuda" else torch.float64
    to = lambda t: t.to(device=device, dtype=(torch.bool if t.dtype == torch.bool else dtype))
    u, v, w, dust, ic, mask, base = (to(inp[k]) for k in ("u", "v", "w", "dust", "ic", "mask", "base"))
    tgt_geo = to(inp["tgt_geo"])
    tc = TransportConfig(dx=DX, dy=DY, dz=DZ, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w, dust=dust)
    print(f"[iron-wall] device={device} dtype={dtype} covered cells={int(mask.sum())}")

    if mode == "twin":
        with torch.no_grad():
            twin = rollout_field(ic, base, tc, n_steps)
        tgt = torch.log(twin[..., 0, 0].clamp_min(EPS)).detach()
        print(f"[iron-wall] mode=TWIN (target = model DFe at Carroll alpfe={float(base[P.alpfe]):.3f}, "
              f"scav_rat={float(base[P.scav_rat]):.1e}) -> shows the (alpfe,scav_rat) DEGENERACY")
    else:
        tgt = tgt_geo
        print("[iron-wall] mode=GEOTRACES (real DFe; model iron-starved with real DB-1 dust)")

    alpfe_g = np.geomspace(0.03, 12.0, 25)
    scav_g = np.geomspace(1e-7, 1e-5, 21)
    misfit = np.full((len(scav_g), len(alpfe_g)), np.nan)

    @torch.no_grad()
    def fit(alpfe, scav):
        p = base.clone()
        p[P.alpfe] = float(alpfe)
        p[P.scav_rat] = float(scav)
        field = rollout_field(ic, p, tc, n_steps)
        logdfe = torch.log(field[..., 0, 0].clamp_min(EPS))
        d = (logdfe - tgt)[mask]
        return float((d * d).mean())

    for i, s in enumerate(scav_g):
        for j, al in enumerate(alpfe_g):
            misfit[i, j] = fit(al, s)

    best = np.unravel_index(np.nanargmin(misfit), misfit.shape)
    print(f"\n[iron-wall] best fit at alpfe={alpfe_g[best[1]]:.3f}, scav_rat={scav_g[best[0]]:.2e} "
          f"(misfit {misfit[best]:.4f})")
    prof = np.nanmin(misfit, axis=1)
    within = scav_g[prof <= prof.min() + 0.02]          # near-best (log-MSE units)
    print("\n[iron-wall] scav_rat PROFILE (min misfit over alpfe at each scav_rat):")
    print(f"  {'scav_rat':>10s}  {'profiled misfit':>15s}  {'best alpfe':>10s}")
    for i, s in enumerate(scav_g):
        ja = int(np.nanargmin(misfit[i]))
        star = "  <- flat" if s in within else ""
        print(f"  {s:10.2e}  {prof[i]:15.4f}  {alpfe_g[ja]:10.3f}{star}")
    if len(within) >= 2:
        print(f"\n[iron-wall] WALL: scav_rat unidentifiable across {within.max()/within.min():.0f}x "
              f"({within.min():.1e}..{within.max():.1e}) -- profiled misfit flat (<=+0.02) because "
              f"alpfe (source) compensates the sink. Concentration constrains the source/sink "
              f"COMBINATION, not the rate.")
    ridge_alpfe = np.array([alpfe_g[int(np.nanargmin(misfit[i]))] for i in range(len(scav_g))])
    on = prof <= prof.min() + 0.02
    if on.sum() >= 2:
        print(f"[iron-wall] over the flat band, best alpfe rises "
              f"{ridge_alpfe[on].min():.2f} -> {ridge_alpfe[on].max():.2f} to offset the scav_rat "
              f"change: the source compensates the sink, so the RATE is unidentifiable from "
              f"concentration (a compensating source/sink ridge, not a clean constant ratio).")

    def _band(thr):
        w = scav_g[prof <= prof.min() + thr]
        return float(w.max() / w.min()) if len(w) >= 2 else 1.0

    if out:
        rec = {
            "description": ("scav_rat profile-likelihood through the prescribed-transport model on the "
                            "eqpac footprint: dissolved-Fe CONCENTRATION constrains the alpfe/scav_rat "
                            "source/sink COMBINATION, not the rate (the information wall). The flat-band "
                            "multiple is threshold- and grid-sensitive, so it is reported at several "
                            "log-MSE thresholds, not as a single number."),
            "mode": mode, "n_steps": int(n_steps), "n_cells": int(mask.sum()),
            "grid": {"scav_rat": [float(x) for x in scav_g], "alpfe": [float(x) for x in alpfe_g],
                     "n_scav": len(scav_g), "n_alpfe": len(alpfe_g),
                     "scav_step_ratio": float(scav_g[1] / scav_g[0])},
            "best_fit": {"alpfe": float(alpfe_g[best[1]]), "scav_rat": float(scav_g[best[0]]),
                         "misfit": float(misfit[best])},
            "profile_misfit": [float(x) for x in prof],
            "best_alpfe_ridge": [float(x) for x in ridge_alpfe],
            "flat_band_multiple": {"thr_0.01": _band(0.01), "thr_0.02": _band(0.02),
                                   "thr_0.05": _band(0.05)},
            "note": ("the headline '32x' band is the +0.02-threshold value; the qualitative wall "
                     "(concentration constrains the source/sink combination, not the rate) is "
                     "threshold-independent, the specific multiple is not."),
        }
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        Path(out).write_text(json.dumps(rec, indent=2))
        print(f"\n[iron-wall] wrote {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--build-bundle", type=str, default=None, help="compute inputs on CPU, save, exit")
    ap.add_argument("--bundle", type=str, default=None, help="load inputs from a bundle + run")
    ap.add_argument("--mode", choices=("twin", "geotraces"), default="twin")
    ap.add_argument("--n-steps", type=int, default=100)
    ap.add_argument("--out", default=None, help="write the profile + threshold-band JSON here")
    args = ap.parse_args()
    if args.build_bundle:
        torch.save(build_inputs(), args.build_bundle)
        print(f"[iron-wall] bundle saved: {args.build_bundle}")
        return 0
    inp = safe_torch_load(args.bundle) if args.bundle else build_inputs()
    return run(inp, args.mode, args.n_steps, args.out)


if __name__ == "__main__":
    raise SystemExit(main())
