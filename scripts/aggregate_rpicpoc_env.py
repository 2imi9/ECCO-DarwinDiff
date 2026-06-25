"""Aggregate per-AOI co-recovery across the RATIO_MAX / env-rain-ratio fit seeds.

Reads the per-seed run_v3.0 JSONs in one or more runs dirs and reports the rigorous
recovery metrics for the 6/6 question:

  * per-param JOINT recovery (aoiweighted): mean +/- seed std, # seeds Cal-grade.
  * per-param PER-AOI co-recovery: # seeds with the param Cal-grade in >=2 AOIs
    (guards against the cell-weighted straddling artifact, alk_anchor_rpicpoc_mutex).
  * headline: # seeds achieving 6/6 (all 6 params) on BOTH the joint and the
    per-AOI >=2 metric.

Bands: Excellent rel<=0.05, Cal-grade rel<=0.40 (diagnostics.band_of), rel =
abs(recovered - Carroll)/abs(Carroll).

Usage:  python scripts/aggregate_rpicpoc_env.py <runs_dir> [<runs_dir> ...]
"""

from __future__ import annotations

import glob
import json
import sys

PARAMS = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
CAL = 0.40
EXC = 0.05


def _rel(rec: float, pub: float) -> float:
    return abs(rec - pub) / abs(pub) if pub != 0 else float("inf")


def _load(runs_dir: str) -> list[dict]:
    seeds = {}
    for path in sorted(glob.glob(f"{runs_dir}/*.json")):
        try:
            d = json.load(open(path))
        except Exception:
            continue
        if "params" not in d or "seed" not in d:
            continue
        seeds[d["seed"]] = d  # de-dup by seed (last wins)
    return list(seeds.values())


def report(runs_dir: str) -> None:
    runs = _load(runs_dir)
    if not runs:
        print(f"\n### {runs_dir}: no seed JSONs found")
        return
    aois = runs[0]["aois"]
    n = len(runs)
    print(f"\n{'='*78}\n### {runs_dir}   (n={n} seeds: {sorted(r['seed'] for r in runs)})")
    print(f"{'param':<11}{'joint mean':>12}{'+/-std':>9}{'Carroll':>10}"
          f"{'jCal':>6}{'jExc':>6}   per-AOI Cal (>=2 AOI co-rec)")
    joint_cal_per_seed = {r["seed"]: 0 for r in runs}
    peraoi_cal_per_seed = {r["seed"]: 0 for r in runs}
    for p in PARAMS:
        pub = runs[0]["params"][p]["joint_carroll_published"]
        jvals = [r["params"][p]["joint_aoiweighted_recovered"] for r in runs]
        mean = sum(jvals) / n
        std = (sum((v - mean) ** 2 for v in jvals) / n) ** 0.5
        jcal = jexc = 0
        peraoi_corec = 0
        aoi_cal_tally = {a: 0 for a in aois}
        for r in runs:
            entry = r["params"][p]
            jrel = _rel(entry["joint_aoiweighted_recovered"], pub)
            if jrel <= CAL:
                jcal += 1; joint_cal_per_seed[r["seed"]] += 1
            if jrel <= EXC:
                jexc += 1
            n_aoi_cal = 0
            for a in aois:
                arel = _rel(entry["per_aoi_recovered"][a], pub)
                if arel <= CAL:
                    n_aoi_cal += 1; aoi_cal_tally[a] += 1
            if n_aoi_cal >= 2:
                peraoi_corec += 1; peraoi_cal_per_seed[r["seed"]] += 1
        tally_str = " ".join(f"{a[:4]}={aoi_cal_tally[a]}" for a in aois)
        print(f"{p:<11}{mean:>12.4g}{std:>9.2g}{pub:>10.4g}"
              f"{jcal:>5}/{n}{jexc:>5}/{n}   {peraoi_corec}/{n} [{tally_str}]")
    n_joint_6 = sum(1 for s in joint_cal_per_seed if joint_cal_per_seed[s] == 6)
    n_peraoi_6 = sum(1 for s in peraoi_cal_per_seed if peraoi_cal_per_seed[s] == 6)
    print(f"  --> 6/6 JOINT (all 6 Cal, aoiweighted):      {n_joint_6}/{n} seeds")
    print(f"  --> 6/6 PER-AOI (all 6 Cal in >=2 AOIs):      {n_peraoi_6}/{n} seeds")
    dist = sorted(joint_cal_per_seed.values(), reverse=True)
    print(f"      joint cal-count per seed: {dist}")


def main() -> int:
    dirs = sys.argv[1:]
    if not dirs:
        print(__doc__)
        return 1
    for d in dirs:
        report(d)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
