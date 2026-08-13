"""How often does our primary test fire on nothing? A sham-split calibration, at zero GPU cost.

WHY. Every evidentiary move in the manuscript is an arm-vs-arm count comparison at n=50 (flagship
25/50 vs global-scalar 0/50; anchor-on vs anchor-off; width arms; epoch arms), and the repo has
twice watched such an effect die on a fresh submission. CLAUDE.md's three-check rule exists because
of it. But nothing measures the FALSE-POSITIVE RATE of the comparison battery itself, and a referee
asking "how often does your primary test fire on nothing, given you scan parameters x poolers x
bands?" currently has no answer.

WHY NO GPU IS NEEDED. A sham pair is two arms differing by nothing except which seeds they drew.
Any n=100 arm already on disk contains an unlimited supply of them: split its 100 seeds into two
disjoint halves of 50 at random and compare. Under the null the two halves are exchangeable by
construction, so every "significant" difference is a false positive.

This resamples 10,000 random disjoint 50/50 splits per arm and reports:
  * the per-cell false-positive rate across parameters x poolers x bands, with a Wilson CI
  * the per-split rate of "at least one cell significant", which is the quantity that matters when
    a result is found by scanning rather than pre-registered
  * the analytic reference: two-sided Fisher exact at 50 vs 50 has type-I error <= 0.0352 for ANY
    underlying rate p (computed here by full enumeration, not assumed), maximised near p = 0.5.
    A conservative test firing BELOW nominal 0.05 is expected; firing above it is not.

Run: python scripts/analysis/sham_split_false_positive_rate.py --runs <dir> [<dir> ...] --out <json>
"""
from __future__ import annotations

import argparse
import glob
import json
import re
from pathlib import Path

import numpy as np
from scipy.stats import fisher_exact

PARAMS = ["alpfe", "scav_rat", "R_PICPOC", "diatomgraz", "Smallgrow", "Biggrow"]
POOLERS = {
    "arithmetic": "joint_cellweighted_abs_rel_offset",
    "aoiweighted": "joint_aoiweighted_abs_rel_offset",
    "joint": "joint_abs_rel_offset",
}
BANDS = [0.20, 0.30, 0.40]


def load_arm(run_dir: str) -> dict[str, dict[int, float]]:
    """seed -> {param: relative offset} for each pooler field we can find."""
    out: dict[str, dict[int, float]] = {p: {} for p in PARAMS}
    for f in sorted(glob.glob(str(Path(run_dir) / "*.json"))):
        m = re.search(r"_seed(\d+)_", Path(f).name)
        if not m:
            continue
        seed = int(m.group(1))
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        params = d.get("params") or {}
        for p in PARAMS:
            e = params.get(p) or {}
            v = e.get("joint_abs_rel_offset")
            if v is not None:
                out[p][seed] = float(v)
    return out


def analytic_type_i(n: int = 50, alpha: float = 0.05) -> dict:
    """Exact type-I error of two-sided Fisher at n vs n, by enumeration over both binomials."""
    from math import comb
    res = {}
    for p in (0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5):
        pmf = np.array([comb(n, k) * p**k * (1 - p)**(n - k) for k in range(n + 1)])
        tot = 0.0
        for a in range(n + 1):
            if pmf[a] < 1e-15:
                continue
            for b in range(n + 1):
                if pmf[b] < 1e-15:
                    continue
                if fisher_exact([[a, n - a], [b, n - b]])[1] < alpha:
                    tot += pmf[a] * pmf[b]
        res[p] = tot
    return res


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", nargs="+", required=True)
    ap.add_argument("--n-splits", type=int, default=10000)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    print("Analytic reference: exact type-I of two-sided Fisher at 50 vs 50\n")
    an = analytic_type_i(alpha=args.alpha)
    for p, t in an.items():
        print(f"  underlying rate p={p:<5} -> type-I = {t:.4f}")
    ceiling = max(an.values())
    print(f"\n  CEILING over the grid = {ceiling:.4f}  (nominal alpha = {args.alpha})")
    print("  The test is CONSERVATIVE by construction; firing near 0.05 would be the anomaly.\n")

    report = {"analytic_type_i": an, "analytic_ceiling": ceiling, "arms": {}}
    rng = np.random.default_rng(20260812)

    for run in args.runs:
        vals = load_arm(run)
        seeds = sorted(set.intersection(*[set(vals[p].keys()) for p in PARAMS if vals[p]])) \
            if any(vals[p] for p in PARAMS) else []
        if len(seeds) < 100:
            print(f"[skip] {run}: only {len(seeds)} seeds (need 100 for disjoint 50/50)")
            continue
        seeds = np.array(seeds)
        mat = {p: np.array([vals[p][s] for s in seeds]) for p in PARAMS}

        cells_total = 0
        cells_sig = 0
        split_any = 0
        per_param_sig = {p: 0 for p in PARAMS}

        for _ in range(args.n_splits):
            perm = rng.permutation(len(seeds))
            A, B = perm[:50], perm[50:100]
            any_sig = False
            for p in PARAMS:
                for band in BANDS:
                    ka = int((mat[p][A] <= band).sum())
                    kb = int((mat[p][B] <= band).sum())
                    pv = fisher_exact([[ka, 50 - ka], [kb, 50 - kb]])[1]
                    cells_total += 1
                    if pv < args.alpha:
                        cells_sig += 1
                        per_param_sig[p] += 1
                        any_sig = True
            if any_sig:
                split_any += 1

        fpr = cells_sig / cells_total
        lo, hi = wilson(cells_sig, cells_total)
        anyrate = split_any / args.n_splits
        alo, ahi = wilson(split_any, args.n_splits)
        print(f"=== {run}  ({len(seeds)} seeds, {args.n_splits} sham splits) ===")
        print(f"  per-cell FPR          {fpr:.4f}   Wilson 95% [{lo:.4f}, {hi:.4f}]   "
              f"({cells_sig}/{cells_total} cells)")
        print(f"  P(>=1 of {len(PARAMS)*len(BANDS)} cells significant per split)  "
              f"{anyrate:.4f}   Wilson [{alo:.4f}, {ahi:.4f}]")
        print("  by parameter:", {p: round(per_param_sig[p] / (args.n_splits * len(BANDS)), 4)
                                  for p in PARAMS})
        print()
        report["arms"][run] = {
            "n_seeds": len(seeds), "n_splits": args.n_splits,
            "per_cell_fpr": fpr, "per_cell_wilson": [lo, hi],
            "cells_sig": cells_sig, "cells_total": cells_total,
            "p_any_significant": anyrate, "p_any_wilson": [alo, ahi],
            "per_param_rate": {p: per_param_sig[p] / (args.n_splits * len(BANDS)) for p in PARAMS},
        }

    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
