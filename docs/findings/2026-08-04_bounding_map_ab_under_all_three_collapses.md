# "Keep linear" survives a valid statistic — but it is underpowered, not null

**Date:** 2026-08-04 · **Job:** 264591, n=50 × 4 arms in ONE submission, `NB23_LR` pinned 5e-3
· **Arms:** `logscale3/{ctrl_n50, logsr_n50, prior_ctrl_n50, prior_logsr_n50}`, 20/20 tasks
COMPLETED · **Pre-registered** in the sbatch header before launch.

## Why this was re-run at all

[`2026-07-30_param_log_scale_resolved.md`](2026-07-30_param_log_scale_resolved.md) graded job
227773 and decided **"keep linear, do not re-run"**: the trio went 25/50 → 31/50, but paired exact
McNemar gave **P = 0.3075** (15 gains, 9 losses).

That decision was never disputed. What changed is the **statistic** it used. The 2026-08-04 pooler
audit showed the arithmetic per-AOI collapse mis-ranks `scav_rat` specifically — on the flagship
twin it flips 13 seeds one way and 0 the other. And the mechanism bites *here* in particular: the
bounding map changes the per-cell field, therefore `log_sd`, therefore the `exp(σ²/2)` inflation,
so the arithmetic collapse can treat the two arms **unequally**. All four arms of 227773 predate
the 2026-07-29 instrumentation and carry no collapse keys, so this needed the fit re-run.

**Pre-registered H0:** the trio McNemar stays non-significant under geometric and median too.
**H1:** sign or significance changes, and the 2026-07-30 decision rested on an artifact.

## The answer: H0 holds

Paired exact McNemar, same 50 seeds in both arms:

| statistic | linear | geometric map | ctrl-only | logsr-only | **P** |
|---|---|---|---|---|---|
| **trio, arithmetic** | 25/50 | 31/50 | 9 | 15 | **0.3075** |
| **trio, geometric** | 12/50 | 22/50 | 7 | 17 | **0.0639** |
| **trio, median** | 23/50 | 26/50 | 14 | 17 | **0.7201** |

**Not significant under any collapse.** "Keep linear" stands, now on a statistic that is valid for
the parameter it is about. The question is closed at n=50.

**The arithmetic row reproduces job 227773 exactly** — 25 vs 31, 9 ctrl-only, 15 logsr-only,
P = 0.3075, five days later on a different code build. That is a genuine cross-job replication of
the earlier finding, and it is worth more than the re-run's own headline.

## But the recorded *reason* is now wrong

2026-07-30 concluded the map "moves individual fits a great deal while leaving the aggregate where
it was." Under the geometric collapse the aggregate does **not** stay where it was:

- the trio goes **12/50 → 22/50**, an 83% relative gain, against 25 → 31 (24%) under arithmetic
- P moves **0.3075 → 0.0639**
- the split is 7 against 17, versus 9 against 15

So the effect is **larger and more one-sided** under the correct collapse, and the result is
**underpowered rather than absent**. The honest statement is not "the bounding map does nothing"; it
is "at n=50 we cannot distinguish it from noise, and the arithmetic collapse was understating it."

That is the same direction as every other finding in this audit: the arithmetic collapse
compressed a real difference in `scav_rat`.

## The `R_PICPOC` cost is also partly an arithmetic artifact

The 2026-07-30 doc's second reason to keep linear was that the geometric map **costs `R_PICPOC`**,
50/50 → 45/50 (p = 0.056). Under the geometric collapse that cost shrinks:

| collapse | linear | geometric map | losses | P |
|---|---|---|---|---|
| arithmetic | 50/50 | 45/50 | 5 | 0.0625 |
| **geometric** | 50/50 | **48/50** | **2** | 0.50 |
| median | 50/50 | 47/50 | 3 | 0.25 |

`R_PICPOC` is pooler-invariant in the *flagship* configuration (`log_sd` ≤ 0.21), so this is not the
`scav_rat` mechanism — it is that the two arms differ, and grading the difference arithmetically
overstates it. Either way the surviving cost is 2 seeds, not 5.

`alpfe` is 49/50 → 50/50 under all three collapses. Invariant, as everywhere else.

## Per-parameter, for the record

| parameter | collapse | linear | geometric map | P |
|---|---|---|---|---|
| `scav_rat` | arithmetic | 26/50 | 35/50 | 0.108 |
| `scav_rat` | geometric | 13/50 | 22/50 | 0.093 |
| `scav_rat` | median | 24/50 | 28/50 | 0.585 |

**Read the trio, not this row.** The geometric bounding map raises `scav_rat`'s *untrained* rate
from 0/50 to 8/50 (measured again here, and pooler-invariant at 8/8/8), so part of any marginal
gain is prior rather than learning. The trio is immune: its untrained baseline is **0/50 in both
arms under all three collapses**.

## What to do

**Keep the linear bounding map.** Nothing here justifies changing the flagship.

**If anyone wants to revisit it, the experiment is n=100 under the geometric collapse**, not
another n=50. P = 0.064 with a consistent direction and a 7-versus-17 split is the shape of an
underpowered real effect, and it would cost one job to settle. That is a different recommendation
from "do not re-run", and it exists only because the collapse was changed.

## Method notes

- All four arms in **one submission**, so no cross-job pooling caveat.
- `NB23_LR` pinned to 5e-3. It was an unpinned default on both the flagship and 227773, which cost
  a retracted finding on 2026-08-03.
- The first attempt (job 263466) lost 4 of 20 tasks to a 4-hour wall. Those tasks were **not hung**
  — they reached epoch 1000 of 2000 while siblings finished all 2000 in 4,778 s, i.e. ~6× slower on
  nodes `b0003`/`b0021`. Re-run at a 10-hour wall; 20/20 COMPLETED.
- Priors from the *failed* job 263466 completed and already replicated the 227773 baselines
  (`alpfe` 10/50, `scav_rat` 0/50 linear and 8/50 geometric, trio 0/50). Job 264591 reproduces them
  again.
