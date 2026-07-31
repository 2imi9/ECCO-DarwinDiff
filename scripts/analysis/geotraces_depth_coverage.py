#!/usr/bin/env python
"""Per-AOI GEOTRACES iron coverage, split surface vs subsurface.

WHY. `docs/findings/2026-07-31_scavrat_southern_ocean_signal_is_depth.md` established that
`scav_rat` is identified by the VERTICAL STRUCTURE of dissolved iron, not by its surface
concentration: in `southernoceanpac`, subsurface-only iron recovers 33/50 while surface-only
recovers 14/50 (Fisher P = 2.68e-4). That result predicts something it was not fitted to explain --
that recovery across basins should track SUBSURFACE bin count and be indifferent to surface count.

This script measures the covariate for that test. It reports coverage ONLY. It does not fit, grade,
or rank anything, so it can be run before the prediction is pre-registered without contaminating it.

The binning reproduces the 1-degree path in scripts/run_v3.0_joint_multi_aoi.py (~line 1273):
surface is DEPTH <= 50 m, subsurface is 50 m <= DEPTH <= 1000 m, QC flags (49, 50), binned to the
1-degree AOI grid, and a bin counts once no matter how many bottles fall in it.

    python scripts/analysis/geotraces_depth_coverage.py

COUNTS ARE APPROXIMATE, IN BOTH DIRECTIONS. Two things differ from the runner. It drops bins where
any v05 field is non-finite (`loss_mask = (count > 0) & ocean_mask`), which only REMOVES bins; and
it lays its grid on the model's own edges rather than on the AOI corner, which can move a sample
across a boundary and ADD one. The v05 cube needed for the mask lives on the cluster, not here.

Both anchors are measured, and they disagree in sign, which is why this is a tolerance and not a
bound: southernoceanpac comes out 14/16 here against a masked 13/14 (this script HIGH by 1/2),
while eqpac comes out 25/27 against a masked 26/28 (this script LOW by 1/1). So the check is
|approx - masked| <= MASK_SLACK in either direction. An earlier version asserted approx >= masked
on the reasoning that a mask can only remove bins; eqpac falsified it.

Use these for RANKING AOIs. For any count that gets quoted as a number, take the masked value from
the run's own `GEOTRACES bins in-AOI:` log line, which is computed with the mask applied.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from darwindiff.ecco_darwin_loader import AOI_BY_KEY  # noqa: E402
from darwindiff.geotraces_loader import (  # noqa: E402
    open_geotraces_bottle,
    subset_aoi_geotraces,
)

GEOTRACES = os.environ.get("GEOTRACES_NC", r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")
QC_GOOD = (49, 50)
DEPTH_MAX_SURFACE = 50.0
SUB_DEPTH_MIN = 50.0
SUB_DEPTH_MAX = 1000.0
RES = 1.0

# Masked counts measured by the runner itself, from its `GEOTRACES bins in-AOI:` log line.
#   southernoceanpac: job 239556 (the published surface-vs-depth ablation arms)
#   eqpac:            job 240662 (the replication smoke test)
# This script runs without the mask and on a different grid origin, so it may land either side.
PUBLISHED_MASKED = {"southernoceanpac": (13, 14), "eqpac": (26, 28)}
MASK_SLACK = 3


def count_bins(ds, aoi) -> dict:
    """Surface and subsurface 1-degree bin counts for one AOI."""
    sub = subset_aoi_geotraces(ds, aoi)
    n_st, n_sa = sub.Fe_D_CONC.shape

    lats = np.broadcast_to(sub.latitude.values[:, None], (n_st, n_sa)).ravel()
    lons = np.broadcast_to(sub.longitude.values[:, None], (n_st, n_sa)).ravel()
    dep = sub.DEPTH.values.ravel()
    fe = sub.Fe_D_CONC.values.ravel()
    qc = sub.Fe_D_CONC_qc.values.ravel()

    qc_arr = np.array(QC_GOOD)
    finite = (
        np.isfinite(fe) & np.isfinite(lats) & np.isfinite(lons) & np.isfinite(dep)
        & np.isin(qc, qc_arr.astype(qc.dtype))
    )

    n_lat = int(np.ceil((aoi.lat_max - aoi.lat_min) / RES))
    n_lon = int(np.ceil((aoi.lon_max - aoi.lon_min) / RES))

    def bins(keep) -> tuple[int, int]:
        """(distinct 1-degree bins occupied, raw bottle samples)."""
        if int(keep.sum()) == 0:
            return 0, 0
        li = np.floor((lats[keep] - aoi.lat_min) / RES).astype(np.int64)
        oi = np.floor((lons[keep] - aoi.lon_min) / RES).astype(np.int64)
        li = np.clip(li, 0, n_lat - 1)
        oi = np.clip(oi, 0, n_lon - 1)
        grid = np.zeros((n_lat, n_lon), dtype=np.int64)
        np.add.at(grid, (li, oi), 1)
        return int((grid > 0).sum()), int(keep.sum())

    surf_b, surf_n = bins(finite & (dep <= DEPTH_MAX_SURFACE))
    sub_b, sub_n = bins(finite & (dep >= SUB_DEPTH_MIN) & (dep <= SUB_DEPTH_MAX))
    deeper = int((finite & (dep > SUB_DEPTH_MAX)).sum())

    return {
        "surface_bins": surf_b,
        "subsurface_bins": sub_b,
        "surface_samples": surf_n,
        "subsurface_samples": sub_n,
        "samples_below_1000m_unused": deeper,
        "grid_cells_in_aoi": n_lat * n_lon,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geotraces", default=GEOTRACES)
    ap.add_argument("--out", default="docs/findings/geotraces_depth_coverage.json")
    a = ap.parse_args()

    ds = open_geotraces_bottle(a.geotraces)
    rows = {}
    for key, aoi in AOI_BY_KEY.items():
        rows[key] = count_bins(ds, aoi)

    print(f"GEOTRACES IDP2025 Fe_D coverage, QC{list(QC_GOOD)}, 1-degree bins")
    print(f"surface: depth <= {DEPTH_MAX_SURFACE:.0f} m   "
          f"subsurface: {SUB_DEPTH_MIN:.0f}-{SUB_DEPTH_MAX:.0f} m\n")
    print(f"{'AOI':<20} {'surf bins':>10} {'sub bins':>9} {'surf obs':>9} {'sub obs':>8}")
    print("-" * 60)
    for key, r in sorted(rows.items(), key=lambda kv: -kv[1]["subsurface_bins"]):
        print(f"{key:<20} {r['surface_bins']:>10} {r['subsurface_bins']:>9} "
              f"{r['surface_samples']:>9} {r['subsurface_samples']:>8}")

    bad = []
    for key, (ms, mb) in PUBLISHED_MASKED.items():
        gs, gb = rows[key]["surface_bins"], rows[key]["subsurface_bins"]
        for label, got, pub in (("surface", gs, ms), ("subsurface", gb, mb)):
            if abs(got - pub) > MASK_SLACK:
                bad.append(f"{key} {label}: approx {got} differs from the runner's masked {pub} "
                           f"by {got - pub:+d}, exceeding MASK_SLACK={MASK_SLACK}; that is larger "
                           "than a mask trim plus a grid-origin shift, so the binning is wrong")
    if bad:
        print("\nBINNING DRIFT -- these counts are not consistent with the published arms:")
        for b in bad:
            print(f"  {b}")
        return 1
    print()
    for key, (ms, mb) in sorted(PUBLISHED_MASKED.items()):
        gs, gb = rows[key]["surface_bins"], rows[key]["subsurface_bins"]
        print(f"anchor ok: {key:<18} approx {gs}/{gb} vs runner masked {ms}/{mb} "
              f"(offset {gs - ms:+d}/{gb - mb:+d})")
    print("Counts above are APPROXIMATE IN BOTH DIRECTIONS -- use them for RANKING. "
          "Take any quoted number from the run's own log line.")

    out = Path(a.out)
    out.write_text(json.dumps({
        "source": str(a.geotraces),
        "qc_flags": list(QC_GOOD),
        "surface_depth_max_m": DEPTH_MAX_SURFACE,
        "subsurface_depth_m": [SUB_DEPTH_MIN, SUB_DEPTH_MAX],
        "grid_resolution_deg": RES,
        "coverage": rows,
    }, indent=1), encoding="utf-8")
    print(f"wrote {out.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
