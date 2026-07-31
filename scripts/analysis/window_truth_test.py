#!/usr/bin/env python
"""Are the v05 'monthly' files true monthly means, or the short window their .meta declares?

Two independently staged trees (local mirror and AICR monthly_v5) agree that the declared
averaging window shrinks from about 28 days in 1994 to about 10 days in 2018, at -0.71 d/yr,
always ending at the month boundary. That settles that the metadata is not a mirroring
artifact. It does NOT settle whether the DATA are short-window means or the metadata is
simply wrong, and those have very different consequences: if the data really are ~10-day
end-of-month means in the later years, every time-mean target the parameter learner uses is
progressively biased toward the end of each month.

This is decidable without any regridding or external product, because the daily archive and
the monthly archive carry the SAME field. Daily surfChl1 and monthly Chl1 are both TRAC27.
So for a given month, build from daily files:

    A = mean over the FULL calendar month
    B = mean over the LAST `w` days, where w is the window the monthly .meta declares

and compare each against the monthly file. Whichever matches is the answer. A late month,
where the declared window is ~10 days, discriminates hardest; an early month, where it is
~28 days, is the control where A and B nearly coincide and both should match.
"""
import glob
import json
import os
import re
import sys

import numpy as np

DAILY = "/scratch/qi_zim_neu/daily_v5/surfChl1"
MONTHLY = "/scratch/qi_zim_neu/monthly_v5/Chl1"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/work/neu/p2026_0089_neu/meta_audit/window_truth.json"
NX, NY = 270, 3510
DT = 1200.0
PAT = re.compile(r"timeInterval\s*=\s*\[([^\]]*)\]", re.I)


def interval(meta):
    g = PAT.search(open(meta, errors="ignore").read())
    if not g:
        return None
    n = [float(x) for x in g.group(1).split()]
    return (n[0] / 86400.0, n[1] / 86400.0) if len(n) >= 2 else None


def read2d(path):
    """Surface level of an LLC270 record, big-endian float32."""
    a = np.fromfile(path, dtype=">f4", count=NX * NY)
    if a.size < NX * NY:
        return None
    return a.reshape(NY, NX)


daily = {}
for m in sorted(glob.glob(os.path.join(DAILY, "*.meta"))):
    it = int(os.path.basename(m).split(".")[1])
    iv = interval(m)
    d = m[:-5] + ".data"
    if iv and os.path.isfile(d):
        daily[it] = (iv[0], iv[1], d)   # (t_start, t_end) in days
print(f"daily records with data: {len(daily)}", flush=True)

months = []
for m in sorted(glob.glob(os.path.join(MONTHLY, "*.meta"))):
    it = int(os.path.basename(m).split(".")[1])
    iv = interval(m)
    d = m[:-5] + ".data"
    if iv and os.path.isfile(d):
        months.append((it, iv[0], iv[1], d))
print(f"monthly records with data: {len(months)}", flush=True)

# pick a hard case (short declared window, late) and a control (long window, early)
months_sorted = sorted(months, key=lambda r: r[2])
cands = [r for r in months_sorted if (r[2] - r[1]) < 12]           # ~10-day declared
ctrl = [r for r in months_sorted if (r[2] - r[1]) >= 28]           # full-month declared
picks = ([("HARD late, ~10d declared", r) for r in cands[-3:]] +
         [("CONTROL early, >=28d declared", r) for r in ctrl[:2]])

results = []
for label, (it, t0, t1, dpath) in picks:
    M = read2d(dpath)
    if M is None:
        print(f"  skip iter {it}: monthly read failed", flush=True)
        continue
    w = t1 - t0
    # daily records whose averaging window ENDS inside (t1 - 31, t1]
    full = [v for k, v in daily.items() if t1 - 31.0 < v[1] <= t1 + 1e-6]
    short = [v for k, v in daily.items() if t1 - w - 1e-6 < v[1] <= t1 + 1e-6]
    if len(full) < 20 or len(short) < 3:
        print(f"  skip iter {it}: daily coverage {len(full)} full / {len(short)} short", flush=True)
        continue

    def stack_mean(recs):
        acc, n = None, 0
        for _, _, p in recs:
            a = read2d(p)
            if a is None:
                continue
            acc = a.astype(np.float64) if acc is None else acc + a
            n += 1
        return acc / n if n else None

    A = stack_mean(full)      # true monthly mean
    B = stack_mean(short)     # declared-window mean
    ok = np.isfinite(M) & np.isfinite(A) & np.isfinite(B) & (M != 0)
    if ok.sum() < 1000:
        print(f"  skip iter {it}: too few valid cells", flush=True)
        continue

    def rms_rel(x, y):
        return float(np.sqrt(np.nanmean(((x[ok] - y[ok]) / np.maximum(np.abs(y[ok]), 1e-20)) ** 2)))

    rA, rB = rms_rel(A, M), rms_rel(B, M)
    verdict = ("DATA IS A TRUE MONTHLY MEAN (metadata is wrong)" if rA < rB / 2
               else "DATA MATCHES THE DECLARED SHORT WINDOW (metadata is right)" if rB < rA / 2
               else "AMBIGUOUS")
    rec = {"label": label, "iter": it, "declared_window_d": round(w, 2),
           "n_daily_full_month": len(full), "n_daily_short_window": len(short),
           "rel_rms_vs_full_month_mean": rA, "rel_rms_vs_short_window_mean": rB,
           "n_cells": int(ok.sum()), "verdict": verdict}
    results.append(rec)
    print(f"  [{label}] iter {it} w={w:.1f}d  full-month rel-rms={rA:.4e}  "
          f"short-window rel-rms={rB:.4e}  -> {verdict}", flush=True)

os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump({"daily_dir": DAILY, "monthly_dir": MONTHLY, "results": results}, open(OUT, "w"), indent=2)
print(f"wrote {OUT}", flush=True)
