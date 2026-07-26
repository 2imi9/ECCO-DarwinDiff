"""Box-vs-Darwin forward fidelity at the TRUE Carroll-6 params (no fitting).

Pre-scale-up question (audit 2026-06-18, point d): can the 2-layer box even
reproduce Darwin v05's 1-degree fields when handed Carroll's *published* params? If
not, native-resolution recovery would be precise-but-wrong — the gap is forward-model
physics, not resolution, and native res alone won't close it.

For each AOI we load the cached Darwin targets (raw binned fields + forcing), run
``carroll6_5pft_2layer_integrate`` at ``CARROLL_VALUES`` to quasi-steady state, then
report, over ocean cells:
  * z-scored spatial pattern correlation r (box vs Darwin) per field, and
  * the surface PIC:POC ratio (box vs Darwin) — what the single R_PICPOC scalar must
    reproduce across AOIs (Darwin's ratio spans ~23x: eqpac ~0.03, natl ~0.7).

Run:  uv run python scripts/box_vs_darwin_fidelity.py
"""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1,
    I_ALK_2,
    I_DFE_1,
    I_DFE_2,
    I_DIATOM,
    I_DIC_1,
    I_DIC_2,
    I_LGE,
    I_PIC_1,
    I_PIC_2,
    I_POC_1,
    I_POC_2,
    I_PROHL,
    I_PROLL,
    I_SYN,
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
)
from darwindiff.diagnostics import safe_pearson_r
from darwindiff.safe_load import safe_torch_load

DT = 0.25
N_STEPS = 200
CACHE_DIR = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"
CACHES = {
    "eqpac": "eqpac_targets_equatorial_pacific.pt",
    "natlsubpolar": "eqpac_targets_north_atlantic_subpolar.pt",
    "southernoceanpac": "eqpac_targets_southern_ocean_pacific.pt",
}
# Darwin field name -> box state index (surface layer). NOTE the per-field r below is
# a pattern diagnostic only and is NOT reported as a result: the Chl rows correlate
# Darwin chlorophyll (mg Chl a/m^3) against box phyto BIOMASS (mmol C/m^3) with no
# Chl:C conversion, and the DIC/ALK/FeT rows are confounded by the Darwin-field IC.
# The load-bearing result is the PIC:POC ratio (see docs/findings/pre_scaleup_verification.md).
FIELD_TO_IDX = {
    "Chl1": I_DIATOM, "Chl2": I_LGE, "Chl3": I_SYN, "Chl4": I_PROLL, "Chl5": I_PROHL,
    "POC": I_POC_1, "PIC": I_PIC_1, "FeT": I_DFE_1, "DIC": I_DIC_1, "ALK": I_ALK_1,
}


def _zr(box: np.ndarray, dar: np.ndarray, mask: np.ndarray) -> float:
    """Pattern r over ocean cells via the audited safe_pearson_r, which drops any
    NaN-inside-mask pairs and flags constant inputs (vs np.corrcoef silently
    returning NaN when a per-field NaN survives the shared mask)."""
    return safe_pearson_r(box[mask], dar[mask]).r


def _fid_for_aoi(key: str, fname: str) -> dict:
    cache = safe_torch_load(CACHE_DIR / fname)
    darwin = {
        "Chl1": cache["chl_per_pft"]["Chl1"], "Chl2": cache["chl_per_pft"]["Chl2"],
        "Chl3": cache["chl_per_pft"]["Chl3"], "Chl4": cache["chl_per_pft"]["Chl4"],
        "Chl5": cache["chl_per_pft"]["Chl5"], "POC": cache["poc_binned"],
        "PIC": cache["pic_binned"], "FeT": cache["fet_binned"],
        "DIC": cache["dic_binned"], "ALK": cache["alk_binned"],
    }
    sst, sss, wind = cache["sst"], cache["sss"], cache["wind"]
    mask = np.isfinite(sst) & np.isfinite(darwin["PIC"]) & np.isfinite(darwin["POC"])

    def fill(a, v):
        return torch.tensor(np.nan_to_num(a.astype(np.float32), nan=v))

    # Initialise the box near Darwin's surface state (both layers); it relaxes to the
    # box's own steady state at the Carroll params, which is what we compare.
    shp = sst.shape
    state0 = torch.zeros(N_TRACERS_2LAYER, *shp)
    state0[I_DFE_1] = fill(darwin["FeT"], 1e-4)
    for idx in (I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL):
        state0[idx] = 0.1
    state0[I_POC_1] = fill(darwin["POC"], 1.0)
    state0[I_PIC_1] = fill(darwin["PIC"], 0.05)
    state0[I_DIC_1] = fill(darwin["DIC"], 2000.0)
    state0[I_ALK_1] = fill(darwin["ALK"], 2300.0)
    state0[I_DFE_2] = fill(darwin["FeT"], 1e-4)
    state0[I_POC_2] = fill(darwin["POC"], 1.0)
    state0[I_PIC_2] = fill(darwin["PIC"], 0.05)
    state0[I_DIC_2] = fill(darwin["DIC"], 2000.0)
    state0[I_ALK_2] = fill(darwin["ALK"], 2300.0)

    final = carroll6_5pft_2layer_integrate(
        state0, CARROLL_VALUES, DT, N_STEPS,
        T=fill(sst, 15.0), S=fill(sss, 35.0), wind=fill(wind, 7.0),
    ).numpy()

    rs = {f: _zr(final[idx], darwin[f].astype(np.float32), mask) for f, idx in FIELD_TO_IDX.items()}
    box_poc = float(np.nanmean(final[I_POC_1][mask]))
    dar_poc = float(np.nanmean(darwin["POC"][mask]))
    box_ratio = float(np.nanmean(final[I_PIC_1][mask]) / box_poc) if box_poc > 0 else float("nan")
    dar_ratio = float(np.nanmean(darwin["PIC"][mask]) / dar_poc) if dar_poc > 0 else float("nan")
    return {"key": key, "rs": rs, "box_picpoc": box_ratio, "darwin_picpoc": dar_ratio}


def main() -> int:
    print(f"Box-vs-Darwin fidelity at CARROLL_VALUES (R_PICPOC={float(CARROLL_VALUES[5]):.4f}), "
          f"{N_STEPS} steps\n")
    rows = [_fid_for_aoi(k, f) for k, f in CACHES.items() if (CACHE_DIR / f).exists()]
    fields = list(FIELD_TO_IDX)
    hdr = "AOI".ljust(17) + "".join(f.rjust(7) for f in fields)
    print(hdr)
    for r in rows:
        print(r["key"].ljust(17) + "".join(f"{r['rs'][f]:7.2f}" for f in fields))
    print("\nSurface PIC:POC ratio-of-means (box at Carroll vs Darwin) — one scalar vs the spread:")
    for r in rows:
        fit = "OK" if 0.5 < r["box_picpoc"] / r["darwin_picpoc"] < 2.0 else "MISMATCH"
        print(f"  {r['key']:<17} box={r['box_picpoc']:.4f}  darwin={r['darwin_picpoc']:.4f}"
              f"  box/darwin={r['box_picpoc'] / r['darwin_picpoc']:.2f}x  {fit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
