"""Compare Lueker vs Mehrbach K1/K2 parameter-recovery at POSi_W=1.0.

Reads the JSONs produced by ``run_v3.0_joint_multi_aoi.py`` for two sweep
configurations (baseline Lueker, USE_MEHRBACH_K1K2=1 Mehrbach) and prints a
side-by-side Cal-grade / Excellent count for each Carroll-6 parameter.

Usage:
    python scripts/compare_mehrbach_vs_lueker.py
"""
from __future__ import annotations

import glob
import json
from collections import Counter
from pathlib import Path

PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]

BASE_TAG = "_pocsubW3.0_geopocW0.5_aoiid_hd32_w-natlsubpolar2.0_posiW1.0"

def load_runs(suffix_tag: str) -> list[dict]:
    pattern = f"data/legacy/scripts_json_archive/run_v3.0_joint_eqpac-natlsubpolar_seed*_surf0.3_sub1.0_pinn3.0{BASE_TAG}{suffix_tag}.json"
    paths = sorted(glob.glob(pattern))
    return [json.load(open(p, encoding="utf-8")) for p in paths]

def summarize(runs: list[dict]) -> dict:
    counts = {p: Counter() for p in PARAMS}
    for r in runs:
        for p in PARAMS:
            band = r["params"][p].get("joint_cellweighted_band") or r["params"][p].get("joint_band")
            counts[p][band] += 1
    return counts

def print_table(label: str, counts: dict, n: int) -> None:
    print(f"\n== {label}  (n={n}) ==")
    print(f"{'param':12s} {'Excellent':>10s} {'Cal-grade':>10s} {'Approx':>8s} {'Loose':>6s}")
    for p in PARAMS:
        c = counts[p]
        exc = c.get("Excellent", 0)
        cal = c.get("Cal-grade", 0)
        appx = c.get("Approximate", 0)
        loose = c.get("Loose", 0)
        print(f"{p:12s} {exc:>10d} {cal:>10d} {appx:>8d} {loose:>6d}")

def print_median_offsets(label: str, runs: list[dict]) -> None:
    from statistics import median
    print(f"\n-- {label} median |rel offset| (lower = closer to Carroll) --")
    print(f"{'param':12s} {'median':>10s} {'min':>10s} {'max':>10s}")
    for p in PARAMS:
        offs = []
        for r in runs:
            o = r["params"][p].get("joint_cellweighted_abs_rel_offset")
            if o is None:
                o = r["params"][p].get("joint_abs_rel_offset")
            if o is not None:
                offs.append(o)
        if offs:
            print(f"{p:12s} {median(offs):>10.4f} {min(offs):>10.4f} {max(offs):>10.4f}")

def main() -> None:
    base = load_runs("")
    mehr = load_runs("_mehrbach")
    n_base = len(base); n_mehr = len(mehr)
    print(f"Baseline (Lueker)  JSONs: {n_base}")
    print(f"Mehrbach           JSONs: {n_mehr}")
    if n_base == 0 and n_mehr == 0:
        print("No JSONs found -- did the sweep run?")
        return
    if n_base > 0:
        print_table("Lueker (baseline)", summarize(base), n_base)
        print_median_offsets("Lueker", base)
    if n_mehr > 0:
        print_table("Mehrbach K1/K2",   summarize(mehr), n_mehr)
        print_median_offsets("Mehrbach", mehr)
    # Aggregate scores
    if n_base > 0 and n_mehr > 0:
        cal_b = sum((b["n_cal_grade"] >= 5) for b in base)
        cal_m = sum((m["n_cal_grade"] >= 5) for m in mehr)
        exc_b = sum((b["n_excellent"] >= 5) for b in base)
        exc_m = sum((m["n_excellent"] >= 5) for m in mehr)
        print(f"\nSeeds at 5+ Cal:   Lueker {cal_b}/{n_base}  vs  Mehrbach {cal_m}/{n_mehr}")
        print(f"Seeds at 5+ Excel: Lueker {exc_b}/{n_base}  vs  Mehrbach {exc_m}/{n_mehr}")
        # Per-seed 6/6
        six_b = sum((b["n_cal_grade"] == 6) for b in base)
        six_m = sum((m["n_cal_grade"] == 6) for m in mehr)
        print(f"Seeds at 6/6 Cal:  Lueker {six_b}/{n_base}  vs  Mehrbach {six_m}/{n_mehr}")

if __name__ == "__main__":
    main()
