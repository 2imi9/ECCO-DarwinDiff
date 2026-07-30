"""Aggregate the Daniels real-data R_PICPOC recovery (n seeds, 4 AOIs).

Metric (the one used everywhere): per-AOI >=2-AOI co-recovery — for each param, count
the seeds in which the per-AOI recovered value is Cal-grade-or-better vs Carroll in at
least 2 AOIs. Reports that rate (with seed variance) + per-AOI Cal-grade tallies, so we
can state honestly whether REAL Daniels CP:PP recovers R_PICPOC in >=2 AOIs while the
iron pair stays intact. Reads the per-seed JSONs the runner wrote; grades are
RE-DERIVED here via the canonical band_of (never trusts a stored band).
"""
from __future__ import annotations

import glob
import json
import sys
from collections import defaultdict

from darwindiff.carroll6 import CARROLL_VALUES, PARAM_NAMES
from darwindiff.diagnostics import band_of
from darwindiff.grading import required_legs

RECOVERED_BANDS = {"Excellent", "Cal-grade"}  # what counts as "recovered" per AOI


def main(run_dir: str) -> int:
    files = sorted(glob.glob(f"{run_dir}/*.json"))
    if not files:
        print(f"NO JSONs in {run_dir}")
        return 2
    carroll = {n: float(CARROLL_VALUES[i]) for i, n in enumerate(PARAM_NAMES)}
    n_seeds = len(files)
    co2 = defaultdict(int)                        # seeds with >=2-AOI recovery
    per_aoi_cal = defaultdict(lambda: defaultdict(int))
    per_aoi_vals = defaultdict(lambda: defaultdict(list))

    for f in files:
        d = json.load(open(f))
        P = d["params"]
        for n in PARAM_NAMES:
            pa = P[n]["per_aoi_recovered"]
            n_cal = 0
            for aoi, val in pa.items():
                rel = abs(val - carroll[n]) / abs(carroll[n])
                if band_of(rel) in RECOVERED_BANDS:
                    n_cal += 1
                    per_aoi_cal[n][aoi] += 1
                per_aoi_vals[n][aoi].append(val)
            if n_cal >= required_legs(len(pa)):
                co2[n] += 1

    print(f"Daniels real-data R_PICPOC recovery — n={n_seeds} seeds, AOIs from JSON")
    print(f"  metric: per-AOI >=2-AOI co-recovery (Cal-grade+ vs Carroll)\n")
    print(f"  {'param':<11}{'>=2-AOI co-rec':>16}{'  per-AOI Cal tallies'}")
    for n in PARAM_NAMES:
        tally = ", ".join(f"{a}:{per_aoi_cal[n].get(a,0)}" for a in per_aoi_vals[n])
        print(f"  {n:<11}{co2[n]}/{n_seeds:<14}  {tally}  (Carroll {carroll[n]:.4g})")
    # R_PICPOC focus: per-AOI mean recovered value across seeds
    print("\n  R_PICPOC per-AOI mean recovered (real-Daniels-anchored):")
    for a, vals in per_aoi_vals["R_PICPOC"].items():
        mu = sum(vals) / len(vals)
        print(f"    {a:<18} mean={mu:.4f}  (Carroll 0.0425)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
