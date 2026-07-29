#!/usr/bin/env python3
"""Grade a run directory for ALL registered parameters, against a chance baseline.

Why this exists alongside ``grade_joint_percell.py``: that script hardcodes
``TRIO = ["alpfe", "scav_rat", "R_PICPOC"]`` and reports raw counts. Two gaps:

1. **It cannot see the other parameters.** ``diatomgraz`` and the growth pair are
   graded elsewhere, by different scripts, at different n. That is how a table
   ended up comparing an n=50 real-data ensemble, an n=7 synthetic sweep and an
   n=10 prototype as if they were one experiment.

2. **A raw count is not interpretable on its own.** "Recovered" means
   ``rel <= 0.40``, and how much of a parameter's PRIOR already satisfies that
   depends entirely on its registry bounds. For ``diatomgraz`` the bounds
   (0.05, 1.0) against Carroll 0.83003 put the pass band at [0.498, 1.0] -- 53 %
   of the range -- and the range midpoint sits INSIDE the band at rel 0.367. So
   an untrained network scores it as recovered. 35/50 against that baseline is a
   very different claim from 35/50 against ``R_PICPOC``'s 0.1 %.

This script reports each count next to a chance rate, so every number is an
effect size. Pass ``--baseline DIR`` pointing at a prior-control run
(``NB23_LR=0 NB23_N_EPOCHS=1``, i.e. untrained networks scored through this same
pipeline) to use a MEASURED baseline. Without it, the analytic baseline is
computed from the registry bounds by sampling the initialisation distribution --
useful, but it assumes the init distribution rather than measuring it.

Usage:
    python scripts/analysis/grade_all_params.py RUN_DIR [RUN_DIR ...]
    python scripts/analysis/grade_all_params.py RUN_DIR --baseline PRIOR_DIR
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(
    0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src")
)

from darwindiff.carroll6 import PARAMS, PARAM_NAMES  # noqa: E402
from darwindiff.diagnostics import BAND_CAL_GRADE_MAX  # noqa: E402

CAL_MAX = BAND_CAL_GRADE_MAX  # 0.40


def band_ok(recovered, carroll) -> bool:
    """Cal-grade or better, matching diagnostics.band_of / grade_joint_percell."""
    if carroll == 0 or recovered is None:
        return False
    try:
        rel = abs(float(recovered) - carroll) / abs(carroll)
    except (TypeError, ValueError):
        return False
    return math.isfinite(rel) and rel <= CAL_MAX


def analytic_chance(n_samples: int = 200_000, seed: int = 0) -> dict[str, float]:
    """Fraction of the init distribution already inside the Cal-grade band.

    theta ~ N(0,1) mapped through the sigmoid into each parameter's bounds --
    the distribution an untrained network's outputs approximate. This is
    ARITHMETIC on the registry, not a measurement; prefer --baseline.
    """
    import random

    rnd = random.Random(seed)
    draws = [rnd.gauss(0, 1) for _ in range(n_samples)]
    out = {}
    for p in PARAMS:
        lo, hi = p.bounds
        c = p.carroll_value
        hits = 0
        for t in draws:
            v = lo + (hi - lo) / (1.0 + math.exp(-t))
            if abs(v - c) / abs(c) <= CAL_MAX:
                hits += 1
        out[p.name] = hits / n_samples
    return out


def per_aoi_2of3(run_dir: str):
    """Count per-AOI >=2-of-3 co-recovery per parameter over the seeds in run_dir."""
    files = sorted(glob.glob(os.path.join(run_dir, "*.json")))
    counts, n = defaultdict(int), 0
    aois = defaultdict(set)
    for f in files:
        try:
            r = json.load(open(f, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "params" not in r:
            continue
        n += 1
        for name, pv in r["params"].items():
            carroll = pv.get("joint_carroll_published")
            per_aoi = pv.get("per_aoi_recovered") or {}
            aois[name] |= set(per_aoi)
            if carroll is None or not per_aoi:
                continue
            if sum(1 for v in per_aoi.values() if band_ok(v, carroll)) >= 2:
                counts[name] += 1
    return counts, n, aois


def binom_ge(k: int, n: int, p: float) -> float:
    """P(X >= k) for X ~ Binomial(n, p)."""
    if n == 0:
        return float("nan")
    p = min(max(p, 1e-12), 1 - 1e-12)
    return sum(
        math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1)
    )


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Reported so a count is never read as a point estimate. Wilson rather than
    normal-approximation because these counts routinely sit at 0/50 or 50/50,
    where the normal interval is degenerate or runs outside [0, 1].
    """
    if n == 0:
        return (float("nan"), float("nan"))
    ph = k / n
    d = 1 + z * z / n
    c = (ph + z * z / (2 * n)) / d
    h = z * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument(
        "--baseline",
        default=None,
        help="prior-control run dir (untrained nets) for a MEASURED chance rate",
    )
    args = ap.parse_args()

    if args.baseline:
        b_counts, b_n, _ = per_aoi_2of3(args.baseline)
        # RULE OF THREE. A measured baseline of 0/N does NOT mean the true chance
        # rate is 0. Testing against a literal zero makes any nonzero count look
        # infinitely significant -- it reported Biggrow 6/50 as "decisive"
        # (P=1.6e-17) when the honest answer is P=0.078, not above chance.
        # With 0 events in N trials the 95% upper bound on the rate is 3/N, so
        # use that as a floor. Counts that are genuinely large (scav_rat 26/50,
        # P=5e-19 even at the floor) are unaffected; borderline ones stop being
        # overstated.
        chance = {}
        for nm in PARAM_NAMES:
            k = b_counts.get(nm, 0)
            if b_n == 0:
                chance[nm] = float("nan")
            elif k == 0:
                chance[nm] = 3.0 / b_n
            else:
                chance[nm] = k / b_n
        floored = [nm for nm in PARAM_NAMES if b_counts.get(nm, 0) == 0]
        src = (f"MEASURED from {os.path.basename(args.baseline)} "
               f"(n={b_n}, untrained)")
        if floored:
            src += (f"\n  rule-of-three floor 3/{b_n}={3.0/b_n:.3f} applied to "
                    f"zero-count baselines: {', '.join(floored)}")
    else:
        chance = analytic_chance()
        src = "ANALYTIC from registry bounds (assumes theta ~ N(0,1) init)"

    print(f"\nchance baseline: {src}")

    for d in args.dirs:
        counts, n, aois = per_aoi_2of3(d)
        print(f"\n=== {os.path.basename(d.rstrip('/\\'))}  (n={n}) ===")
        if n == 0:
            print("  no gradeable seed JSONs found")
            continue
        print(f"{'param':<12}{'per-AOI>=2/3':>13}{'rate':>8}{'95% Wilson':>16}"
              f"{'chance':>9}{'P(>=obs)':>11}   verdict")
        for nm in PARAM_NAMES:
            k = counts.get(nm, 0)
            if nm not in aois:
                continue
            rate = k / n
            lo, hi = wilson(k, n)
            ch = chance.get(nm, float("nan"))
            p = binom_ge(k, n, ch) if math.isfinite(ch) else float("nan")
            if not math.isfinite(p):
                verdict = "?"
            elif p < 1e-4:
                verdict = "decisive"
            elif p < 0.01:
                verdict = "strong"
            elif p < 0.05:
                verdict = "marginal"
            else:
                verdict = "NOT above chance"
            # Flag when the chance rate sits inside the observed interval: the
            # count is then not separable from the untrained baseline at all.
            overlap = " *" if math.isfinite(ch) and lo <= ch <= hi else ""
            print(f"{nm:<12}{f'{k}/{n}':>13}{rate:>8.2f}"
                  f"{f'[{lo:.2f},{hi:.2f}]':>16}{ch:>9.3f}"
                  f"{p:>11.2e}   {verdict}{overlap}")
        print("  * = chance rate falls INSIDE the 95% interval "
              "(count not separable from an untrained network)")


if __name__ == "__main__":
    main()
