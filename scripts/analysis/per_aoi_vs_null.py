#!/usr/bin/env python
"""Per-AOI legs graded against their OWN untrained baseline.

Lucas told Jon of the observations-only arm: "with the model pattern term removed most cells
carry no gradient, so the diatom result leans on a small set of informative cells rather than
good coverage." That qualification is currently prose with no number behind it.

The aggregate per-AOI >=2-of-3 count cannot settle it, because a parameter can reach a
majority two different ways:
  - genuine coverage: every AOI carries information and every leg beats its own chance rate;
  - pooling: one or two AOIs carry the information and the shared DINN exports the magnitude
    to AOIs that have none, which is what the R_PICPOC Southern Ocean leg was shown to do.

Those look identical in the headline. They differ per AOI, against a per-AOI null. This
script computes, for every parameter and every AOI, the leg count in the trained arm and the
leg count in the architecture-matched UNTRAINED arm, plus an exact binomial P of the trained
leg against the untrained leg rate. A leg that does not clear its own null is not evidence,
however good the aggregate looks.
"""
import glob
import json
import math
import os
import sys
from collections import defaultdict

sys.path.insert(0, "src")
from darwindiff.diagnostics import band_of  # noqa: E402
from darwindiff.grading import required_legs  # noqa: E402

CAL = {"Excellent", "Cal-grade"}


def legs(run_dir):
    """-> {param: {aoi: n_cal}}, {param: n_majority}, n_seeds, aois"""
    per = defaultdict(lambda: defaultdict(int))
    maj = defaultdict(int)
    aois, n = [], 0
    for f in sorted(glob.glob(os.path.join(run_dir, "*.json"))):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if "params" not in d:
            continue
        n += 1
        for name, pv in d["params"].items():
            pa = pv.get("per_aoi_recovered") or {}
            pub = pv.get("joint_carroll_published")
            if not pa or pub in (None, 0):
                continue
            if not aois:
                aois = sorted(pa)
            ok = {a: band_of(abs(v - pub) / abs(pub)) in CAL for a, v in pa.items()}
            for a, good in ok.items():
                per[name][a] += int(good)
            if sum(ok.values()) >= required_legs(len(ok)):
                maj[name] += 1
    return per, maj, n, aois


def binom_ge(k, n, p):
    if n == 0:
        return float("nan")
    p = min(max(p, 1e-12), 1 - 1e-12)
    return sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1))


def rule_of_three(k, n):
    """Chance floor when the null count is zero: 3/n, the usual upper 95% bound."""
    return max(k / n, 3.0 / n) if n else float("nan")


trained_dir, null_dir = sys.argv[1], sys.argv[2]
tp, tm, tn, aois = legs(trained_dir)
np_, nm, nn, _ = legs(null_dir)

print(f"TRAINED : {trained_dir}  n={tn}")
print(f"UNTRAINED: {null_dir}  n={nn}")
print(f"AOIs: {aois}\n")

hdr = f"{'param':<12}{'majority':>10}"
for a in aois:
    hdr += f"{a[:9]:>11}"
print(hdr + "     per-AOI verdict")
print("-" * (len(hdr) + 30))

summary = {}
for p in sorted(tp):
    row = f"{p:<12}{str(tm[p]) + '/' + str(tn):>10}"
    verdicts = []
    for a in aois:
        k, kn = tp[p][a], np_[p].get(a, 0)
        rate = rule_of_three(kn, nn)
        pv = binom_ge(k, tn, rate)
        mark = "*" if pv < 0.05 else "."
        row += f"{str(k) + '/' + str(kn) + mark:>11}"
        verdicts.append((a, k, kn, rate, pv, pv < 0.05))
    above = sum(1 for v in verdicts if v[5])
    row += f"     {above}/{len(aois)} legs above their own null"
    print(row)
    summary[p] = {
        "majority": tm[p], "n": tn,
        "legs": {a: {"trained": k, "untrained": kn, "chance_rate": rate, "P_ge": pv,
                     "above_null": bool(sig)} for a, k, kn, rate, pv, sig in verdicts},
        "n_legs_above_null": above,
    }

print("\nformat: trained/untrained per AOI.  * = leg beats its own untrained rate at P<0.05.")
print("A parameter whose majority rests on legs that do NOT clear their own null is pooling,")
print("not coverage. That is a real mechanism and a publishable one, but it is not the same")
print("claim, and the manuscript must not report it as though every AOI carried information.\n")

for p, s in summary.items():
    if s["majority"] > 0 and s["n_legs_above_null"] < len(aois):
        weak = [a for a, v in s["legs"].items() if not v["above_null"]]
        print(f"  QUALIFY {p}: majority {s['majority']}/{s['n']} but legs {weak} do not clear their own null")

out = sys.argv[3] if len(sys.argv) > 3 else None
if out:
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump({"trained": trained_dir, "untrained": null_dir, "n_trained": tn,
               "n_untrained": nn, "aois": aois, "params": summary}, open(out, "w"), indent=2)
    print(f"\nwrote {out}")
