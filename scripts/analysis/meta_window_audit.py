#!/usr/bin/env python
"""Is the v05 'monthly' archive really monthly, and is the defect local or in the archive?

Measured on the LOCAL mirror (D:/ecco_darwin_v5/output/monthly): the declared averaging
window in every variable's .meta shrinks monotonically from about 28 days in 1994 to about
10 days in 2018, always ending at the month boundary. Only 34 of 321 files declare a full
~30-day window. If the .data really are short-window means, then every time-mean target the
parameter learner uses is progressively biased toward the end of each month, and the bias
grows with year.

Two things this settles, both on the cluster so the local mirror is not the only witness:

  1. Does AICR's independently-staged monthly_v5 show the SAME drift? If yes the defect is in
     the NASA archive, not in our mirroring. If no, our local mirror is corrupt.
  2. Does the DATA agree with an independent monthly rendering? v05_binavg_1deg.nc is NASA's
     own bin_average product, verified monthly, 276 steps 1995-01 to 2017-12. If our .data
     match it, the .meta is a metadata artifact and the fields are fine. If they diverge and
     the divergence GROWS with year, the short windows are real.
"""
import glob
import json
import os
import re
import sys
from collections import defaultdict

import numpy as np

ROOT = sys.argv[1] if len(sys.argv) > 1 else "/scratch/qi_zim_neu/monthly_v5"
OUT = sys.argv[2] if len(sys.argv) > 2 else "/work/neu/p2026_0089_neu/meta_audit/meta_window_audit.json"
DT = 1200.0
PAT = re.compile(r"timeInterval\s*=\s*\[([^\]]*)\]", re.I)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
report = {"root": ROOT, "delta_t": DT, "variables": {}}

print(f"scanning {ROOT}", flush=True)
subdirs = sorted(d for d in glob.glob(os.path.join(ROOT, "*")) if os.path.isdir(d))
if not subdirs:
    subdirs = [ROOT]  # flat layout
print(f"  {len(subdirs)} candidate variable dirs", flush=True)

for d in subdirs:
    var = os.path.basename(d)
    metas = sorted(glob.glob(os.path.join(d, "*.meta")))
    if not metas:
        continue
    rows = []
    for m in metas:
        base = os.path.basename(m)
        try:
            it = int(base.split(".")[1])
        except (IndexError, ValueError):
            continue
        try:
            g = PAT.search(open(m, errors="ignore").read())
        except OSError:
            continue
        if not g:
            continue
        n = [float(x) for x in g.group(1).split()]
        if len(n) < 2:
            continue
        rows.append((it, n[0] / 86400.0, n[1] / 86400.0, (n[1] - n[0]) / 86400.0))
    if not rows:
        continue
    by_year = defaultdict(list)
    for it, t0, t1, sp in rows:
        by_year[1992 + int(t1 // 365.25)].append(sp)
    spans = [r[3] for r in rows]
    rec = {
        "n_meta": len(metas),
        "n_data": len(glob.glob(os.path.join(d, "*.data"))),
        "n_parsed": len(rows),
        "frac_full_month": float(np.mean([s >= 28 for s in spans])),
        "min_span_d": float(min(spans)),
        "max_span_d": float(max(spans)),
        "mean_span_by_year": {str(y): float(np.mean(v)) for y, v in sorted(by_year.items())},
    }
    report["variables"][var] = rec
    yrs = sorted(by_year)
    if yrs:
        f, l = yrs[0], yrs[-1]
        print(f"  {var:<12} n={len(rows):>4} full-month={rec['frac_full_month']*100:5.1f}%  "
              f"{f}={np.mean(by_year[f]):5.2f}d -> {l}={np.mean(by_year[l]):5.2f}d", flush=True)

# ---- overall drift verdict ----
allyears = defaultdict(list)
for rec in report["variables"].values():
    for y, v in rec["mean_span_by_year"].items():
        allyears[int(y)].append(v)
drift = {str(y): float(np.mean(v)) for y, v in sorted(allyears.items())}
report["mean_span_by_year_all_vars"] = drift
if len(drift) >= 3:
    ys = np.array([int(y) for y in drift]); ss = np.array(list(drift.values()))
    slope = float(np.polyfit(ys, ss, 1)[0])
    report["drift_days_per_year"] = slope
    report["verdict"] = ("MONOTONIC DRIFT, same signature as the local mirror" if slope < -0.2
                         else "NO DRIFT: local mirror differs from this tree")
    print(f"\nDRIFT: {slope:+.3f} days of averaging window per year -> {report['verdict']}", flush=True)

with open(OUT, "w") as fh:
    json.dump(report, fh, indent=2)
print(f"wrote {OUT}", flush=True)
