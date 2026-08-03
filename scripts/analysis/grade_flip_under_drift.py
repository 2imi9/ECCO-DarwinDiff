#!/usr/bin/env python
"""Does run-to-run nondeterminism ever flip a Cal grade?

WHY THIS EXISTS
---------------
Nothing in this codebase forces determinism: there is no ``torch.use_deterministic_algorithms``,
no ``cudnn.deterministic``, no ``CUBLAS_WORKSPACE_CONFIG``. ``torch.manual_seed`` fixes
initialisation, not GPU kernel reductions, so two runs of the same config with the same seed
can and do differ -- measured at up to 1.7% in recovered parameter values.

1.7% sounds harmless against a +/-40% Cal band, but that reasoning is loose: what matters is
not the size of the drift, it is whether any *graded unit* sits closer to the band edge than
its own drift. This script measures that directly, using two directories that are the same
config and the same seeds.

Take the two runs as replicates and, for each (seed, param, AOI) unit present in both:

  * grade each side against the Cal band  (|rec - carroll| / carroll <= CAL_MAX)
  * count units where the two sides disagree                -> observed flips
  * count units whose own drift exceeds their own margin    -> units that *could* flip

Report both. An observed flip count of zero with a non-zero could-flip count means the
published counts survived this sample but are not structurally immune.

Note on the summary statistic: the maximum ``|rel_offset_A - rel_offset_B|`` over all units is
large and misleading. A unit recovered far from Carroll has a big ``rec/carroll``, so a small
*relative* change in the recovered value is a big change in its rel_offset -- while sitting
nowhere near the decision boundary. Always compare a unit's drift to its OWN margin.

USAGE
    python scripts/analysis/grade_flip_under_drift.py DIR_A DIR_B [--cal-max 0.40]

EXIT CODES
    0  no observed grade flips
    1  at least one unit graded differently between the two replicates
    2  VACUOUS: no shared units to compare
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys


def load(d: str) -> dict:
    """(seed, param, aoi) -> (recovered, carroll_published)."""
    out: dict = {}
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if "params" not in rec:
            continue
        seed = rec.get("seed", os.path.basename(path))
        for pname, entry in rec["params"].items():
            if not isinstance(entry, dict):
                continue
            carroll = entry.get("joint_carroll_published")
            per_aoi = entry.get("per_aoi_recovered")
            if not isinstance(carroll, (int, float)) or not carroll:
                continue
            if not isinstance(per_aoi, dict):
                continue
            for aoi, v in per_aoi.items():
                if isinstance(v, (int, float)):
                    out[(seed, pname, aoi)] = (float(v), float(carroll))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir_a")
    ap.add_argument("dir_b")
    ap.add_argument("--cal-max", type=float, default=0.40,
                    help="Cal-grade band on |rec - carroll| / carroll (default 0.40)")
    args = ap.parse_args()
    cal = args.cal_max

    a, b = load(args.dir_a), load(args.dir_b)
    shared = sorted(set(a) & set(b), key=str)
    print(f"A: {args.dir_a}")
    print(f"B: {args.dir_b}")
    print(f"shared (seed, param, AOI) units: {len(shared)}")
    if not shared:
        print("VACUOUS: no shared units. No robustness claim may be made from this run.")
        return 2

    def rel(v, c):
        return abs(v - c) / abs(c)

    flips, rows = [], []
    for k in shared:
        ra, rb = rel(*a[k]), rel(*b[k])
        margin = min(abs(ra - cal), abs(rb - cal))
        drift = abs(ra - rb)
        rows.append((margin, drift, k, ra, rb))
        if (ra <= cal) != (rb <= cal):
            flips.append((k, ra, rb))

    rows.sort()
    print(f"\nOBSERVED GRADE FLIPS: {len(flips)} of {len(shared)}")
    for k, ra, rb in flips[:12]:
        print(f"   {k}  relA={ra:.4f}  relB={rb:.4f}  (band {cal})")

    print("\nclosest units to the Cal boundary:")
    for margin, drift, k, ra, rb in rows[:6]:
        print(f"   margin {margin:.4f}  own drift {drift:.4f}  {k}  "
              f"relA={ra:.4f} relB={rb:.4f}")

    could = [r for r in rows if r[1] >= r[0]]
    print(f"\nunits whose OWN drift exceeds their OWN margin: {len(could)} of {len(shared)}")
    for margin, drift, k, _, _ in could[:8]:
        print(f"   margin {margin:.4f} <= drift {drift:.4f}  {k}")

    return 1 if flips else 0


if __name__ == "__main__":
    sys.exit(main())
