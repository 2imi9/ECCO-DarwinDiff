# The v05 monthly `timeInterval` metadata is wrong, and the data are fine

**Date:** 2026-07-30 · **Jobs:** 237808 (meta scan, AICR `monthly_v5`), 237917 (truth test) ·
**Artifacts:** `/work/neu/p2026_0089_neu/meta_audit/{aicr_monthly_v5,window_truth}.json` ·
**Verdict: the declared averaging window in every monthly `.meta` is wrong and drifts with year.
The `.data` are true full-month means. No published result is affected. Never derive a time or an
averaging window from a v05 monthly `.meta`.**

This note also retracts an alarm raised earlier the same day. The metadata defect is real and worth
recording, but the conclusion drawn from it, that time-mean targets might be progressively biased,
is false.

## 1. The metadata defect, confirmed in two independent stagings

Every monthly variable declares an averaging window that shrinks monotonically with year, always
ending at the month boundary.

| | local mirror `D:/ecco_darwin_v5/output/monthly` | AICR `/scratch/qi_zim_neu/monthly_v5` |
|---|---|---|
| variables scanned | 52 | 6 (ALK, Chl1, DIC, FeT, PIC, POC) |
| fraction declaring a full month (>= 28 d) | 10.6% | 10.3 to 10.6% |
| 1992 mean declared window | 27.27 d | 27.27 d |
| 2018 mean declared window | 10.25 d | 10.25 d |
| drift | -0.71 d/yr | **-0.710 d/yr** |

The two trees were staged independently and agree to three digits, so this is in the NASA archive
rather than in our mirroring. The very first record, `CO2_flux.0000002232`, declares
`timeInterval = [2635200, 2678400]`, a 12-hour window stamped as January 1992.

## 2. The data are full-month means

The metadata cannot say whether the arrays are short-window means or the field is simply wrong, and
those have very different consequences. It is decidable without regridding or any external product,
because the daily and monthly archives carry the same field: daily `surfChl1` and monthly `Chl1` are
both `TRAC27`.

For a given month, build two means from daily files and compare each against the monthly file:

- **A** = mean over the full calendar month
- **B** = mean over only the last `w` days, where `w` is the window the `.meta` declares

| case | declared `w` | rel-RMS vs **full-month** mean | rel-RMS vs declared-window mean |
|---|---|---|---|
| iter 705672 (2017, hard) | 10.5 d | **1.53e-07** | 40.7 |
| iter 6552 (1992, control) | 30.0 d | **3.09e-07** | 3.09e-07 |

The hard case is decisive. Where the metadata claims a 10.5-day window, the monthly array equals the
**full-month** mean to float32 round-off, and differs from the declared-window mean by a factor of
40. The control behaves exactly as it must: at a 30-day declared window the two candidate means are
the same set of daily files, so both match at machine precision. That agreement is what validates
the method rather than a weakness in it.

Two other late months returned rel-RMS near 1.6 to 1.9 against the full-month mean rather than
1e-07. That is the daily archive's own gaps, since it is missing roughly 64 of 9860 days and each
variable a different subset, so those months' full-month stacks are incomplete. It is not evidence
against the conclusion; the one month with complete daily coverage answers it exactly.

## 3. What this changes

**Nothing about any published number.** Every time-mean target the parameter learner uses is built
from the `.data`, and the `.data` are full-month means. The recovery counts, the flagship, the
observations-only arms and the DOF ladder are all untouched.

**One rule, and it is not optional.** Do not derive a time, a date, or an averaging window from a
v05 **monthly** `.meta`. Use the iteration number: `t = iter * 1200 / 86400` days after 1992-01-01,
which is exact and independently confirmed. The `timeStepNumber` field is reliable; `timeInterval`
is not.

**Note the asymmetry.** The **daily** `.meta` files are self-consistent: the last daily record
declares `timeInterval = [9860.0, 9861.0]` days, exactly one day and exactly `[prev_iter, iter]`
times 1200 s. So `timeInterval` is trustworthy in the daily tree and not in the monthly tree. The
2026-07-30 daily-era finding rests on the daily sidecars plus iteration arithmetic and stands
unchanged.

## 4. Retraction

Earlier today, on seeing the shrinking windows, this was flagged as a possible progressive bias in
every monthly target. That was wrong, and the test above is what makes it wrong. The correct
statement is narrower: a metadata field is unreliable, and code that reads it should be changed to
read `timeStepNumber` instead.

Worth keeping as a general lesson. Two independent stagings agreeing on a defect established that it
was upstream, which felt like strong confirmation, but agreement on the metadata says nothing about
the arrays. The decisive test needed a second, independent rendering of the same field, and the
daily archive already was one.
