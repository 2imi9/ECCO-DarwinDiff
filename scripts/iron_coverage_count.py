"""Committed reproducer for the iron-partitioning coverage numbers.

The iron-partitioning finding notes that co-located particulate + dissolved iron are
sparse (dense Fe_D, but few surface samples with BOTH Fe_TP/Fe_TPL and Fe_D). Those
counts were prose-only; this script regenerates them from the checksummed GEOTRACES
IDP2025 seawater file, with explicit cuts, and writes a JSON.

Co-location: Fe_D and Fe_TP(/Fe_TPL) share the (N_STATIONS, N_SAMPLES) sample grid, so a
sample is "co-located" when BOTH are finite (> 0), good-flagged, at the same station+sample.

Cuts: surface (DEPTH <= 50 m), QC in {49, 50} (good), value finite and > 0.
Ratio: pFe/DFe = Fe_TP / Fe_D (and Fe_TPL / Fe_D) where both measured; report the log10 span
and p10/p50/p90.

CPU. Needs D:\\geotraces\\GEOTRACES_IDP2025_Seawater.nc.
Run:  CUDA_VISIBLE_DEVICES=-1 python scripts/iron_coverage_count.py \
        --out docs/findings/iron_coverage_count.json
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

from darwindiff.geotraces_loader import open_geotraces_bottle

DEPTH_MAX = 50.0
QC_GOOD = (49, 50)
GEOTRACES = os.environ.get("GEOTRACES_NC", r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")
# eqpac AOI box (matches scripts/geotraces_glodap_identifiability.py REGIONS "eqpac")
EQPAC = dict(lat0=-5, lat1=15, lon0=-160, lon1=-110)


def _flat(ds, var):
    """Flatten a (N_STATIONS, N_SAMPLES) iron var to sample arrays + good/surface mask."""
    ns, nsamp = ds[var].shape
    lat = np.broadcast_to(ds.latitude.values[:, None], (ns, nsamp)).ravel()
    lon = np.broadcast_to(ds.longitude.values[:, None], (ns, nsamp)).ravel()
    dep = ds.DEPTH.values.ravel()
    val = ds[var].values.ravel()
    qc = ds[var + "_qc"].values.ravel() if (var + "_qc") in ds else np.full(val.shape, 49)
    good = (dep <= DEPTH_MAX) & np.isfinite(val) & (val > 0) & np.isin(qc, QC_GOOD)
    return lat, lon, val, good


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ds = open_geotraces_bottle(GEOTRACES)
    lat, lon, fe_d, g_d = _flat(ds, "Fe_D_CONC")
    _, _, fe_tp, g_tp = _flat(ds, "Fe_TP_CONC")
    _, _, fe_tpl, g_tpl = _flat(ds, "Fe_TPL_CONC")

    def eqpac_mask(gmask):
        return (gmask & (lat >= EQPAC["lat0"]) & (lat <= EQPAC["lat1"])
                & (lon >= EQPAC["lon0"]) & (lon <= EQPAC["lon1"]))

    def ratio_stats(g_part, fe_part):
        both = g_d & g_part
        if int(both.sum()) < 2:
            return {"n": int(both.sum()), "log10_span": None, "p10": None, "p50": None, "p90": None}
        r = np.log10(fe_part[both] / fe_d[both])
        return {"n": int(both.sum()), "log10_span": float(r.max() - r.min()),
                "p10": float(10 ** np.percentile(r, 10)), "p50": float(10 ** np.percentile(r, 50)),
                "p90": float(10 ** np.percentile(r, 90))}

    rec = {
        "description": ("Co-located particulate:dissolved iron coverage in GEOTRACES IDP2025, surface "
                        "(<=50 m), good QC {49,50}, finite>0. Co-location = Fe_D and Fe_TP(/Fe_TPL) both "
                        "present at the same station+sample. Confirms the partitioning observable is "
                        "sparse where the dissolved field is dense."),
        "cuts": {"depth_max_m": DEPTH_MAX, "qc_good": list(QC_GOOD), "eqpac_box": EQPAC},
        "surface_counts": {
            "Fe_D": int(g_d.sum()), "Fe_TP": int(g_tp.sum()), "Fe_TPL": int(g_tpl.sum()),
        },
        "colocated_surface": {
            "Fe_TP_and_Fe_D_global": int((g_d & g_tp).sum()),
            "Fe_TP_and_Fe_D_eqpac": int((eqpac_mask(g_d) & eqpac_mask(g_tp)).sum()),
            "Fe_TPL_and_Fe_D_global": int((g_d & g_tpl).sum()),
            "Fe_TPL_and_Fe_D_eqpac": int((eqpac_mask(g_d) & eqpac_mask(g_tpl)).sum()),
        },
        "ratio_pFe_over_DFe": {"Fe_TP": ratio_stats(g_tp, fe_tp), "Fe_TPL": ratio_stats(g_tpl, fe_tpl)},
    }
    print(json.dumps(rec, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(rec, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
