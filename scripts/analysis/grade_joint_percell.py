#!/usr/bin/env python3
"""Re-grade n=50 per-seed JSONs: cell-weighted vs per-AOI >=2-of-3 co-recovery.

Reconciles the flagship joint number (red-team #1). Reads the raw per-seed
params[param]['per_aoi_recovered'] and joint_cellweighted_band, grades against
Carroll via the canonical band thresholds, and prints both metrics from ONE dataset.
"""
import json, sys, glob, os
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from darwindiff.grading import required_legs  # noqa: E402

CAL_MAX = 0.40  # Cal-grade+ ceiling (diagnostics.BAND_CAL_GRADE_MAX)
TRIO = ["alpfe", "scav_rat", "R_PICPOC"]

def band_ok(recovered, carroll):
    if carroll == 0 or recovered is None:
        return False
    rel = abs(recovered - carroll) / abs(carroll)
    return rel <= CAL_MAX

def grade_dir(d):
    files = sorted(glob.glob(os.path.join(d, "*.json")))
    seeds = []
    for f in files:
        r = json.load(open(f))
        if "params" not in r:
            continue
        seeds.append(r)
    n = len(seeds)
    # per-param counts
    cw_count = defaultdict(int)          # cell-weighted Cal-grade+ per param
    aoi2of3_count = defaultdict(int)     # per-AOI >=2-of-3 per param
    aoi_present = defaultdict(set)
    joint_cw = 0                         # all trio cell-weighted
    joint_aoi = 0                        # all trio per-AOI >=2-of-3
    for r in seeds:
        p = r["params"]
        cw_ok = {}
        aoi_ok = {}
        for param in TRIO:
            pv = p[param]
            carroll = pv["joint_carroll_published"]
            # cell-weighted
            cwb = pv.get("joint_cellweighted_band", pv.get("joint_band"))
            cw_ok[param] = cwb in ("Excellent", "Cal-grade")
            if cw_ok[param]:
                cw_count[param] += 1
            # per-AOI >=2-of-3
            per_aoi = pv["per_aoi_recovered"]
            aoi_present[param] |= set(per_aoi.keys())
            n_ok = sum(1 for a, v in per_aoi.items() if band_ok(v, carroll))
            aoi_ok[param] = (n_ok >= required_legs(len(per_aoi)))
            if aoi_ok[param]:
                aoi2of3_count[param] += 1
        if all(cw_ok[t] for t in TRIO):
            joint_cw += 1
        if all(aoi_ok[t] for t in TRIO):
            joint_aoi += 1
    print(f"\n=== {os.path.basename(d)}  (n={n}) ===")
    print(f"{'param':<10} {'cell-wtd':>9} {'per-AOI>=2/3':>13}   AOIs")
    for param in TRIO:
        print(f"{param:<10} {cw_count[param]:>7}/{n} {aoi2of3_count[param]:>11}/{n}   {sorted(aoi_present[param])}")
    print(f"{'JOINT trio':<10} {joint_cw:>7}/{n} {joint_aoi:>11}/{n}")
    return {"n": n, "cw": dict(cw_count), "aoi": dict(aoi2of3_count),
            "joint_cw": joint_cw, "joint_aoi": joint_aoi}

if __name__ == "__main__":
    for d in sys.argv[1:]:
        grade_dir(d)
