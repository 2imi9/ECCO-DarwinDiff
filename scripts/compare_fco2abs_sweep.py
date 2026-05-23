"""Side-by-side compare F_CO2_ABS_W sweep against the POSi-only baseline.

Scans the JSONs produced by ``run_v3.0_joint_multi_aoi.py`` at the canonical
PR #57-best + POSI_W=1.0 config across F_CO2_ABS_W variants, prints per-param
recovery bands and median offsets.

Usage:
    python scripts/compare_fco2abs_sweep.py
"""
from __future__ import annotations

import glob
import json
from collections import Counter
from statistics import median

PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
BASE_PREFIX = "data/legacy/scripts_json_archive/run_v3.0_joint_eqpac-natlsubpolar_seed"
BASE_MIDDLE = "_surf0.3_sub1.0_pinn3.0_pocsubW3.0_geopocW0.5_aoiid_hd32_w-natlsubpolar2.0_posiW1.0"

def load_runs(suffix: str) -> list[dict]:
    pattern = f"{BASE_PREFIX}*{BASE_MIDDLE}{suffix}.json"
    return [json.load(open(p, encoding="utf-8")) for p in sorted(glob.glob(pattern))]

def summarize(runs: list[dict]) -> dict:
    counts = {p: Counter() for p in PARAMS}
    for r in runs:
        for p in PARAMS:
            band = r["params"][p].get("joint_cellweighted_band") or r["params"][p].get("joint_band")
            counts[p][band] += 1
    return counts

def offsets(runs: list[dict], param: str) -> list[float]:
    out = []
    for r in runs:
        o = r["params"][param].get("joint_cellweighted_abs_rel_offset")
        if o is None:
            o = r["params"][param].get("joint_abs_rel_offset")
        if o is not None:
            out.append(o)
    return out

CONFIGS = [
    ("Baseline (POSi only)", ""),
    ("+ F_CO2 abs W=0.01",   "_fco2absW0.01"),
    ("+ F_CO2 abs W=0.1",    "_fco2absW0.1"),
    ("+ F_CO2 abs W=0.3",    "_fco2absW0.3"),
    ("+ F_CO2 abs W=1.0",    "_fco2absW1.0"),
]

def main() -> None:
    all_runs = {}
    for label, suffix in CONFIGS:
        runs = load_runs(suffix)
        if runs:
            all_runs[label] = runs
            print(f"{label:30s} n={len(runs):>2d}")
        else:
            print(f"{label:30s} (none)")

    # Per-param Cal+Excellent count per config
    print("\n== Cal+Excellent count (out of n) per param ==")
    header = f"{'param':12s} " + " ".join(f"{label[:18]:>18s}" for label in all_runs)
    print(header)
    for p in PARAMS:
        row = [f"{p:12s}"]
        for label, runs in all_runs.items():
            c = summarize(runs)[p]
            cal_plus = c.get("Cal-grade", 0) + c.get("Excellent", 0)
            row.append(f"{cal_plus:>3d}/{len(runs):<2d}".rjust(18))
        print(" ".join(row))

    print("\n== Median |rel offset| per param (lower = closer to Carroll) ==")
    print(header)
    for p in PARAMS:
        row = [f"{p:12s}"]
        for label, runs in all_runs.items():
            offs = offsets(runs, p)
            m = median(offs) if offs else float("nan")
            row.append(f"{m:>18.4f}")
        print(" ".join(row))

if __name__ == "__main__":
    main()
