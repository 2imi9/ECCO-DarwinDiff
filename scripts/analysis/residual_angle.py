#!/usr/bin/env python3
"""Measure the residual angle phi per observable block at the recovered optimum.

Why. `docs/research_notes/2026-07-27_hierarchical_inversion_design.md` leans on Wedin's
perturbation bound, whose second term carries `kappa^2 * tan(phi)` where phi is the angle
between the data vector and the range of the Jacobian. tan(phi) is load-bearing across
three sections of that document and was never measured, despite being one forward pass.

Definition used here, per observable block b:

    sin(phi_b) = ||r_b|| / ||d_b||          r_b = model(theta_hat) - d_b
    tan(phi_b) = sin / sqrt(1 - sin^2)

phi ~ 0  => a nearly-consistent block; the kappa^2 term is dormant and plain kappa governs.
phi -> 90 deg => a large-residual block; the kappa^2 term dominates and conditioning bites
                 quadratically. For a 0-D box against a 3-D model, large residuals are
                 EXPECTED -- that is the surrogate gap, and it is exactly why the design
                 document's use of the bound needs checking rather than asserting.

Reads the ALREADY-recovered per-AOI parameter means from a completed run's per-seed JSONs
(the same source `integrator_stationarity_check.py` uses) and the same cached AOI targets.
No refitting.

Run:
    DARWIN_DATA_ROOT=D:/ecco_darwin_v5 python scripts/analysis/residual_angle.py D:/rt/n50
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import PARAM_NAMES
from darwindiff.safe_load import safe_torch_load
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1, I_DFE_1, I_DIC_1, I_PIC_1, I_POC_1,
    N_TRACERS_2LAYER, carroll6_5pft_2layer_integrate,
)

DT, N_STEPS = 0.25, 200
CACHE_FILES = {
    "eqpac": "eqpac_targets_equatorial_pacific.pt",
    "natlsubpolar": "eqpac_targets_north_atlantic_subpolar.pt",
    "southernoceanpac": "eqpac_targets_southern_ocean_pacific.pt",
}
# observable block -> (cache key, box state index)
BLOCKS = {
    "FeT": ("fet_binned", I_DFE_1),
    "POC": ("poc_binned", I_POC_1),
    "PIC": ("pic_binned", I_PIC_1),
    "DIC": ("dic_binned", I_DIC_1),
    "ALK": ("alk_binned", I_ALK_1),
}


def recovered_params(run_dir: Path, aoi: str) -> torch.Tensor | None:
    """Mean per-AOI recovered vector across seeds."""
    vecs = []
    for f in sorted(glob.glob(str(run_dir / "*.json"))):
        try:
            d = json.loads(Path(f).read_text(encoding="utf-8"))
        except Exception:
            continue
        params = d.get("params")
        if not isinstance(params, dict):
            continue
        # params[<name>]["per_aoi_recovered"][<aoi>] -> float
        row = []
        for name in PARAM_NAMES:
            per = (params.get(name) or {}).get("per_aoi_recovered") or {}
            v = per.get(aoi)
            if not isinstance(v, (int, float)):
                row = []
                break
            row.append(float(v))
        if row:
            vecs.append(row)
    if not vecs:
        return None
    return torch.tensor(np.mean(np.asarray(vecs, dtype=np.float64), axis=0))


def run_aoi(cache_dir: Path, aoi: str, theta: torch.Tensor) -> dict:
    c = safe_torch_load(cache_dir / CACHE_FILES[aoi])
    sst, sss, wind = c["sst"], c["sss"], c["wind"]
    mask = np.isfinite(sst) & np.isfinite(c["pic_binned"]) & np.isfinite(c["poc_binned"])

    def fill(a, v):
        return torch.tensor(np.nan_to_num(np.asarray(a, dtype=np.float64).astype(np.float32), nan=v))

    s0 = torch.zeros(N_TRACERS_2LAYER, *sst.shape)
    s0[I_DFE_1] = fill(c["fet_binned"], 1e-4)
    for i in (1, 2, 3, 4, 5):
        s0[i] = 0.1
    s0[I_POC_1] = fill(c["poc_binned"], 1.0)
    s0[I_PIC_1] = fill(c["pic_binned"], 0.05)
    s0[I_DIC_1] = fill(c["dic_binned"], 2000.0)
    s0[I_ALK_1] = fill(c["alk_binned"], 2300.0)
    s0[10] = fill(c["fet_binned"], 1e-4); s0[11] = fill(c["poc_binned"], 1.0)
    s0[12] = fill(c["pic_binned"], 0.05); s0[13] = fill(c["dic_binned"], 2000.0)
    s0[14] = fill(c["alk_binned"], 2300.0)

    final = carroll6_5pft_2layer_integrate(
        s0, theta.to(torch.float32), DT, N_STEPS,
        T=fill(sst, 15.0), S=fill(sss, 35.0), wind=fill(wind, 7.0),
    ).numpy()

    out = {}
    for name, (key, idx) in BLOCKS.items():
        d = np.asarray(c[key], dtype=np.float64)
        m = mask & np.isfinite(d)
        if m.sum() < 10:
            continue
        dv, mv = d[m], final[idx][m].astype(np.float64)
        nd = float(np.linalg.norm(dv))
        nr = float(np.linalg.norm(mv - dv))
        if nd <= 0:
            continue
        s = min(nr / nd, 1.0 - 1e-12)
        out[name] = {"n": int(m.sum()), "norm_d": nd, "norm_r": nr,
                     "sin_phi": s, "tan_phi": s / math.sqrt(1.0 - s * s),
                     "phi_deg": math.degrees(math.asin(s))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    cache = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"

    report = {}
    print(f"{'AOI':18s} {'block':6s} {'n':>6s} {'sin phi':>9s} {'tan phi':>10s} {'phi deg':>8s}")
    for aoi in CACHE_FILES:
        th = recovered_params(Path(a.run_dir), aoi)
        if th is None:
            print(f"{aoi:18s} no recovered params found"); continue
        r = run_aoi(cache, aoi, th)
        report[aoi] = r
        for b, v in r.items():
            print(f"{aoi:18s} {b:6s} {v['n']:6d} {v['sin_phi']:9.4f} {v['tan_phi']:10.4f} {v['phi_deg']:8.2f}")
    if a.out:
        Path(a.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
