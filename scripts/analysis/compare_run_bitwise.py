#!/usr/bin/env python
"""Compare two recovery-run directories value by value, and refuse to pass vacuously.

WHY THIS EXISTS
---------------
The bitwise no-op control in `scripts/slurm/grade_window_swap.sbatch` read
``params[k].get('joint')``. Artifacts have no such key -- they store ``joint_recovered``,
``joint_cellweighted_recovered``, ``per_aoi_recovered`` and so on. Every lookup returned
``None``, every value was skipped, the running maximum stayed at its ``0.0`` initialiser, and
the script printed **"max relative difference: 0.000e+00 -> BITWISE IDENTICAL"** having
compared nothing at all.

That is the same failure the research map's SUPERSEDES constraint had: a check that passes on
an empty set reads exactly like a check that passes on a full one. So the contract here is:

    comparing zero values is a FAILURE, not a pass.

`--min-values` (default 1) is the floor, and the count of compared values is printed on the
verdict line so it cannot be read past.

USAGE
    python scripts/analysis/compare_run_bitwise.py DIR_A DIR_B [--tol 0] [--params a,b]

EXIT CODES
    0  compared >= min-values and every difference <= tol
    1  a real difference exceeded tol
    2  VACUOUS: too few values compared (missing field, no shared seeds, empty dirs)
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys

# Fields worth comparing. Each is a scalar under params[<name>], except the per-AOI dicts,
# which are expanded to one value per AOI. Anything absent from an artifact is reported as a
# missing field rather than silently skipped.
SCALAR_FIELDS = (
    "joint_recovered",
    "joint_cellweighted_recovered",
    "joint_aoiweighted_recovered",
    "joint_geom_cellweighted_recovered",
    "joint_median_pooled_recovered",
)
DICT_FIELDS = ("per_aoi_recovered", "per_aoi_recovered_geom", "per_aoi_recovered_median")


def load(d: str) -> dict:
    """seed -> {(param, field) -> float} for every artifact in a directory."""
    out: dict = {}
    for path in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            rec = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if "params" not in rec:
            continue
        flat: dict = {}
        for pname, entry in rec["params"].items():
            if not isinstance(entry, dict):
                continue
            for f in SCALAR_FIELDS:
                v = entry.get(f)
                if isinstance(v, (int, float)):
                    flat[(pname, f)] = float(v)
            for f in DICT_FIELDS:
                sub = entry.get(f)
                if isinstance(sub, dict):
                    for aoi, v in sub.items():
                        if isinstance(v, (int, float)):
                            flat[(pname, f"{f}[{aoi}]")] = float(v)
        out[rec.get("seed", os.path.basename(path))] = flat
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dir_a")
    ap.add_argument("dir_b")
    ap.add_argument("--tol", type=float, default=0.0,
                    help="max allowed relative difference (default 0 = bitwise)")
    ap.add_argument("--params", default="",
                    help="comma-separated parameter names; default all")
    ap.add_argument("--min-values", type=int, default=1,
                    help="fail with exit 2 if fewer values than this were compared")
    args = ap.parse_args()

    want = {p.strip() for p in args.params.split(",") if p.strip()}
    a, b = load(args.dir_a), load(args.dir_b)
    shared = sorted(set(a) & set(b), key=str)

    print(f"A: {args.dir_a}  ({len(a)} artifacts)")
    print(f"B: {args.dir_b}  ({len(b)} artifacts)")
    print(f"shared seeds: {len(shared)}")

    worst: dict = {}
    n_compared = 0
    only_a, only_b = set(), set()
    for s in shared:
        ka, kb = set(a[s]), set(b[s])
        only_a |= ka - kb
        only_b |= kb - ka
        for key in sorted(ka & kb, key=str):
            pname, field = key
            if want and pname not in want:
                continue
            va, vb = a[s][key], b[s][key]
            denom = max(abs(va), abs(vb), 1e-30)
            rel = abs(va - vb) / denom
            worst[key] = max(worst.get(key, 0.0), rel)
            n_compared += 1

    if only_a or only_b:
        print(f"[warn] fields only in A: {sorted(map(str, only_a))[:4]}")
        print(f"[warn] fields only in B: {sorted(map(str, only_b))[:4]}")

    by_param: dict = {}
    for (pname, field), rel in worst.items():
        by_param[pname] = max(by_param.get(pname, 0.0), rel)
    for pname in sorted(by_param):
        rel = by_param[pname]
        flag = "identical" if rel == 0.0 else ("within tol" if rel <= args.tol else "*** DIFFERS ***")
        print(f"  {pname:<12} max relative difference {rel:.3e}  {flag}")

    # The vacuity guard. This is the whole point of the script: a comparison that examined
    # nothing must not be reportable as agreement.
    if n_compared < args.min_values:
        print(f"\nVACUOUS: compared {n_compared} values (< --min-values {args.min_values}). "
              "No reproducibility claim may be made from this run. Check that the field names "
              "still exist and that the two directories share seeds.")
        return 2

    overall = max(by_param.values()) if by_param else 0.0
    verdict = "BITWISE IDENTICAL" if overall == 0.0 else (
        "WITHIN TOLERANCE" if overall <= args.tol else "DIFFERS")
    print(f"\ncompared {n_compared} values across {len(shared)} shared seeds")
    print(f"max relative difference: {overall:.3e}  ->  {verdict}")
    return 0 if overall <= args.tol else 1


if __name__ == "__main__":
    sys.exit(main())
