#!/usr/bin/env python
"""per_pft_picpoc_validate.py -- validate Jon's per-functional-type calcite
hypothesis against Darwin v05's REAL per-AOI calcifier fractions.

Jon (2026-06-28): only some Darwin PFTs calcify ("other large eukaryotes" = Chl2,
the coccolithophore pool; Synechococcus = Chl3 may), so bulk PIC:POC should vary
in space, while a PER-CALCIFIER ratio should be more consistent.

The test: under coccolith-only calcite, bulk PIC:POC = r_calc * f_calc, where
f_calc is the calcifier share of the community. If Jon is right, the IMPLIED
per-calcifier ratio r = (observed bulk PIC:POC) / (real calcifier fraction)
should be roughly CONSTANT across basins -- the basin spread is then just the
calcifier-fraction spread, not a spread in the underlying rain ratio.

Calcifier fraction is computed from the real v05 surface time-mean Chl1..Chl5
(D:/ecco_darwin_v5 bin_average). Bulk PIC:POC ratio-of-means per AOI are the
established v05 values (as emailed to Jon).
"""
from __future__ import annotations
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import xarray as xr

from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI, NORTH_ATLANTIC_SUBPOLAR_AOI,
    SOUTHERN_OCEAN_PACIFIC_AOI, subset_aoi,
)

DATA_ROOT = os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")
NC = os.path.join(DATA_ROOT, "bin_average", "v05_ECCO-Darwin_bin_average_1x1_deg.nc")

# Established v05 surface PIC:POC ratio-of-means per AOI (as emailed to Jon).
BULK = {"eqpac": 0.033, "natl": 0.676, "SO": 0.0067}
AOIS = {"eqpac": EQUATORIAL_PACIFIC_AOI, "natl": NORTH_ATLANTIC_SUBPOLAR_AOI,
        "SO": SOUTHERN_OCEAN_PACIFIC_AOI}


def aoi_chl_fractions(ds, aoi):
    # lat/lon are 2-D (y,x) fields here, not dim-coords, so subset with a mask.
    lat, lon = ds["lat"].values, ds["lon"].values
    mask = ((lat >= aoi.lat_min) & (lat <= aoi.lat_max)
            & (lon >= aoi.lon_min) & (lon <= aoi.lon_max))
    chl = {}
    for i in range(1, 6):
        field = ds[f"Chl{i}"].mean("time").values   # (y,x) surface time-mean
        chl[f"Chl{i}"] = float(np.nanmean(field[mask]))
    tot = sum(chl.values())
    frac = {k: v / tot for k, v in chl.items()}
    return chl, frac


def main():
    print("=" * 72)
    print("VALIDATE Jon's per-PFT calcite hypothesis vs REAL Darwin v05 Chl fractions")
    print("=" * 72)
    ds = xr.open_dataset(NC)

    rows = {}
    for name, aoi in AOIS.items():
        chl, frac = aoi_chl_fractions(ds, aoi)
        # calcifier proxies: Chl2 (other large euks) alone, and Chl2+Chl3 (+Syn)
        f_calc2 = frac["Chl2"]
        f_calc23 = frac["Chl2"] + frac["Chl3"]
        rows[name] = {"chl": chl, "frac": frac, "f_calc2": f_calc2, "f_calc23": f_calc23,
                      "bulk": BULK[name]}

    print(f"\n{'AOI':7s} {'bulk PIC:POC':>12s} {'Chl2 frac':>10s} {'Chl2+3 frac':>12s} "
          f"{'r=bulk/Chl2':>12s} {'r=bulk/Chl23':>13s}")
    for name in ("eqpac", "natl", "SO"):
        r = rows[name]
        r_c2 = r["bulk"] / max(r["f_calc2"], 1e-9)
        r_c23 = r["bulk"] / max(r["f_calc23"], 1e-9)
        rows[name]["r_c2"], rows[name]["r_c23"] = r_c2, r_c23
        print(f"{name:7s} {r['bulk']:12.4f} {r['f_calc2']*100:9.2f}% {r['f_calc23']*100:11.2f}% "
              f"{r_c2:12.4f} {r_c23:13.4f}")

    # Constancy of the implied per-calcifier ratio across basins.
    def cv(vals):
        a = np.array(vals); return float(a.std() / a.mean())
    cv_bulk = cv([rows[n]["bulk"] for n in AOIS])
    cv_r2 = cv([rows[n]["r_c2"] for n in AOIS])
    cv_r23 = cv([rows[n]["r_c23"] for n in AOIS])

    print("\n" + "-" * 72)
    print("Across-basin spread (coefficient of variation; lower = more consistent):")
    print(f"  bulk PIC:POC          CV = {cv_bulk*100:6.1f}%   (the single-scalar closure problem)")
    print(f"  per-calcifier r (Chl2)   CV = {cv_r2*100:6.1f}%")
    print(f"  per-calcifier r (Chl2+3) CV = {cv_r23*100:6.1f}%")
    best_cv = min(cv_r2, cv_r23)
    print(f"\n  collapse factor: bulk CV / best per-calcifier CV = {cv_bulk/best_cv:.1f}x")
    print("-" * 72)
    if best_cv < cv_bulk / 2:
        print("VERDICT: moving the ratio onto the calcifier PFT SUBSTANTIALLY collapses the")
        print("across-basin spread -> Jon's per-PFT mechanism is supported by the real Chl data.")
    else:
        print("VERDICT: per-calcifier ratio is NOT clearly more constant than bulk -> the")
        print("Chl2 standing-stock fraction alone does not explain the basin spread (report honestly).")
    print("\nNOTE: calcifier fraction uses Chl standing stock as a proxy for the calcifier")
    print("share of POC production; a production-weighted fraction is the rigorous follow-up.")


if __name__ == "__main__":
    main()
