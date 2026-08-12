#!/usr/bin/env python
"""Re-grade a run under all three collapse statistics (poolers), not just the arithmetic one.

Every per-cell fit is collapsed to one number per AOI before it is compared to Carroll, and
until 2026-08-03 the project only ever read the ARITHMETIC collapse. Two headline results died
that day because the arithmetic mean of a log-scale field rewards dispersion rather than
accuracy: for a lognormal field of log-sd sigma,

    arithmetic = geometric x exp(sigma^2 / 2)

and the Cal band is +/-40% RELATIVE, so once sigma > sqrt(2 ln 1.4) = 0.8203 the collapse
choice alone moves a perfectly geom-centred field out of (or into) the band. `scav_rat` spans
two decades and routinely carries sigma > 1, so for that parameter the choice is decisive.

The three statistics are computed from the SAME fit -- same seed, same weights, same per-cell
field -- so this is an exactly PAIRED comparison, not an A/B across arms. That makes McNemar
the right test between poolers, and it is the one reported here.

WHAT THIS SCRIPT REFUSES TO DO
------------------------------
The collapse keys were added on 2026-07-29 (commit c4323ae). Runs predating that carry only
`per_aoi_recovered`. This script does NOT fall back to the arithmetic key when the others are
missing: it reports `<absent>` and exits 2. An absent key is unknown, not equal -- silently
substituting is precisely how a pooling artifact gets published as an accuracy result.

Usage:
    python scripts/analysis/pooler_audit.py RUN_DIR [--null NULL_DIR] [--band 0.40]
                                            [--params scav_rat,alpfe] [--json OUT.json]
"""
import argparse
import glob
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, "src")
from darwindiff.diagnostics import band_of
from darwindiff.grading import required_legs

CAL = {"Excellent", "Cal-grade"}

#: The three collapses, in the order they are reported. The first is what every published
#: number in this project used; the other two have been on disk, unread, since 2026-07-29.
POOLERS = (
    ("arithmetic", "per_aoi_recovered"),
    ("geometric", "per_aoi_recovered_geom"),
    ("median", "per_aoi_recovered_median"),
)

#: Above this per-cell log-sd the arithmetic collapse alone clears the +/-40% Cal band,
#: because exp(sigma^2/2) - 1 > 0.40. Below ~0.3 the choice cannot matter.
SIGMA_DECISIVE = math.sqrt(2 * math.log(1.4))


def grade(run_dir, band=None, params_filter=None):
    """-> legs[pooler][param][aoi], majority[pooler][param], per-seed pass sets, log_sd, n, aois.

    `band` overrides the Cal-grade threshold for band-sensitivity checks; None uses the
    canonical `band_of` classification.
    """
    legs = {p: defaultdict(lambda: defaultdict(int)) for p, _ in POOLERS}
    majority = {p: defaultdict(int) for p, _ in POOLERS}
    #: Every parameter seen, so a 0/n result is REPORTED as 0 rather than vanishing from
    #: the table. A silently missing row reads as "not measured"; 0/50 is a measurement.
    seen = set()
    #: seed -> set of params that reached a majority, per pooler. Needed for paired McNemar.
    seed_pass = {p: defaultdict(set) for p, _ in POOLERS}
    log_sd = defaultdict(lambda: defaultdict(list))
    missing = set()
    aois, n = [], 0

    for f in sorted(glob.glob(os.path.join(run_dir, "*.json"))):
        try:
            with open(f, encoding="utf-8") as stream:
                d = json.load(stream)
        except (OSError, json.JSONDecodeError):
            continue
        if "params" not in d:
            continue
        seed = d.get("seed", n)
        n += 1
        for name, pv in d["params"].items():
            if params_filter and name not in params_filter:
                continue
            pub = pv.get("joint_carroll_published")
            if pub in (None, 0):
                continue
            seen.add(name)
            for pooler, key in POOLERS:
                pa = pv.get(key)
                if not pa:
                    missing.add(key)
                    continue
                if not aois:
                    aois = sorted(pa)
                ok = {}
                for a, v in pa.items():
                    rel = abs(v - pub) / abs(pub)
                    ok[a] = rel <= band if band is not None else band_of(rel) in CAL
                for a, good in ok.items():
                    legs[pooler][name][a] += int(good)
                if sum(ok.values()) >= required_legs(len(ok)):
                    majority[pooler][name] += 1
                    seed_pass[pooler][seed].add(name)
            for a, v in (pv.get("per_aoi_log_sd") or {}).items():
                log_sd[name][a].append(v)
    return legs, majority, seed_pass, log_sd, n, aois, missing, seen


def binom_ge(k, n, p):
    if n == 0:
        return float("nan")
    p = min(max(p, 1e-12), 1 - 1e-12)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def rule_of_three(k, n):
    """Chance floor when the null count is zero: 3/n, the usual upper 95% bound."""
    return max(k / n, 3.0 / n) if n else float("nan")


def mcnemar(seed_pass_a, seed_pass_b, param, seeds):
    """Exact two-sided McNemar for one parameter across paired seeds. -> (b, c, P)."""
    b = sum(1 for s in seeds
            if param in seed_pass_a.get(s, ()) and param not in seed_pass_b.get(s, ()))
    c = sum(1 for s in seeds
            if param not in seed_pass_a.get(s, ()) and param in seed_pass_b.get(s, ()))
    nd = b + c
    if nd == 0:
        return b, c, 1.0
    tail = sum(math.comb(nd, i) for i in range(min(b, c) + 1)) / (2 ** nd)
    return b, c, min(1.0, 2 * tail)


def median(xs):
    xs = sorted(xs)
    if not xs:
        return float("nan")
    m = len(xs) // 2
    return xs[m] if len(xs) % 2 else 0.5 * (xs[m - 1] + xs[m])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir")
    ap.add_argument("--null", help="architecture-matched untrained run for a per-pooler null")
    ap.add_argument("--band", type=float, default=None,
                    help="override the Cal threshold (default: canonical 0.40 via band_of)")
    ap.add_argument("--params", help="comma-separated subset")
    ap.add_argument("--legs", action="store_true", help="per-AOI leg counts under each pooler")
    ap.add_argument("--json", dest="out")
    a = ap.parse_args()
    pf = set(a.params.split(",")) if a.params else None

    legs, maj, seed_pass, log_sd, n, aois, missing, seen = grade(a.run_dir, a.band, pf)
    print(f"RUN  : {a.run_dir}  n={n}  AOIs={aois}")
    band_desc = "canonical band_of (Cal <= 0.40)" if a.band is None else f"custom <= {a.band}"
    print(f"BAND : {band_desc}")

    if missing:
        print(f"\n  *** POOLER KEYS ABSENT: {sorted(missing)}")
        print("  This run predates the collapse instrumentation (2026-07-29, c4323ae).")
        print("  Absent is UNKNOWN, not equal. The arithmetic number cannot be pooler-checked")
        print("  from this artifact; it needs a re-run with current code. Refusing to guess.")
        print("  The table below reports what IS recorded; the exit code carries the refusal.")

    nullmaj = nulln = None
    null_missing = set()
    if a.null:
        _, nullmaj, _, _, nulln, _, nmiss, _ = grade(a.null, a.band, pf)
        null_missing = nmiss
        print(f"NULL : {a.null}  n={nulln}" + (f"  (missing {sorted(nmiss)})" if nmiss else ""))

    names = sorted(seen)
    print()
    hdr = f"{'param':<12}" + "".join(f"{p:>22}" for p, _ in POOLERS)
    print(hdr)
    print("-" * len(hdr))
    summary = {}
    for name in names:
        row = f"{name:<12}"
        rec = {}
        for pooler, key in POOLERS:
            # `<absent>` means the KEY is not in the artifact; 0/n means it is and the
            # parameter scored zero. Conflating the two is the error this audit exists for.
            if key in missing:
                row += f"{'<absent>':>22}"
                rec[pooler] = None
                continue
            k = maj[pooler].get(name, 0)
            cell = f"{k}/{n}"
            if nullmaj is not None:
                kn = nullmaj[pooler].get(name, 0)
                pv = binom_ge(k, n, rule_of_three(kn, nulln))
                cell += f" vs {kn} P={pv:.2g}"
                rec[pooler] = {"count": k, "n": n, "null": kn, "P": pv}
            else:
                rec[pooler] = {"count": k, "n": n}
            row += f"{cell:>22}"
        print(row)
        summary[name] = rec

    # The joint trio is the manuscript's headline and its sole binding leg is scav_rat,
    # so it has to be recomputed per pooler rather than inferred from the rows above.
    trio = ("alpfe", "scav_rat", "R_PICPOC")
    if seen.issuperset(trio) and not missing:
        print()
        cells = []
        for pooler, _ in POOLERS:
            k = sum(1 for s in seed_pass[pooler] if set(trio) <= seed_pass[pooler][s])
            cells.append(f"{k}/{n}")
            summary.setdefault("_trio", {})[pooler] = {"count": k, "n": n}
        print(f"{'trio ' + '+'.join(trio):<12}"[:12] + "".join(f"{c:>22}" for c in cells))
        print(f"  (joint {'+'.join(trio)}; binding leg is whichever is lowest above)")

    # Paired McNemar: same seeds, same fit, different collapse. This is the test the
    # arithmetic-vs-geometric comparison actually calls for.
    seeds = sorted(set(seed_pass["arithmetic"]) | set(seed_pass["geometric"]))
    if seeds and not missing:
        print("\npaired McNemar, arithmetic vs geometric (same seeds, same fits)")
        for name in names:
            b, c, pv = mcnemar(seed_pass["arithmetic"], seed_pass["geometric"], name, seeds)
            if b or c:
                print(f"  {name:<12} arith-only {b:>3}   geom-only {c:>3}   P={pv:.3g}")

    # Per-AOI legs. The majority count hides WHICH basin the pooler moves, and for
    # scav_rat the basins disagree in direction, so the aggregate alone is misleading.
    if a.legs and not missing:
        print("\nper-AOI legs (arithmetic / geometric / median)")
        for name in names:
            parts = []
            for aoi in aois:
                trio_cells = "/".join(str(legs[p][name].get(aoi, 0)) for p, _ in POOLERS)
                parts.append(f"{aoi[:9]}={trio_cells}")
            print(f"  {name:<12} " + "   ".join(parts))

    print("\nper-cell log-sd (median over seeds); arith/geom = exp(sigma^2/2)")
    print(f"  sigma > {SIGMA_DECISIVE:.3f} means the collapse alone can clear the +/-40% band")
    for name in names:
        if name not in log_sd:
            continue
        parts = []
        for aoi in aois:
            s = median(log_sd[name].get(aoi, []))
            flag = "!" if s > SIGMA_DECISIVE else " "
            parts.append(f"{aoi[:9]}={s:.3f}{flag} (x{math.exp(s * s / 2):.2f})")
        print(f"  {name:<12} " + "  ".join(parts))
        summary.setdefault(name, {})["log_sd"] = {
            aoi: median(log_sd[name].get(aoi, [])) for aoi in aois}

    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        with open(a.out, "w", encoding="utf-8") as stream:
            json.dump({"run": a.run_dir, "null": a.null, "n": n, "aois": aois,
                       "band": a.band, "params": summary}, stream, indent=2)
        print(f"\nwrote {a.out}")
    # Both sides of the comparison must carry the same audited collapses. Treating an absent
    # null key as zero would manufacture significance just as surely as falling back to the
    # fitted arm's arithmetic key.
    return 2 if missing or null_missing else 0


if __name__ == "__main__":
    sys.exit(main())
