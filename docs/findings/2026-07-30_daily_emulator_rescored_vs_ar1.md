# The daily emulator re-scored: AR(1) was never the threat, log space was, and the clipping is the model's own

**Date:** 2026-07-30 · **Job:** 236516 (re-score) + 236529 (clipping audit) ·
**Artifacts:** `/work/neu/p2026_0089_neu/daily_rescore/` ·
**Verdict: `+0.408` does not survive. It is a linear-space number, and the daily emulator loses to
plain persistence in log space even after every clipped cell is removed. One channel, `surfChl5`,
survives cleanly and is the only positive result here.**

`2026-07-30_daily_emulator_artifact_is_contaminated.md` established that the pre-existing artifact
could not settle the daily question and named the work needed. That work is done. This is a **new
measurement**, not a correction of the old one, and it was run without retraining.

## The reload is exact, so everything below rests on the same model

`emulator_poc.py` could save a checkpoint but never load one, so re-scoring previously meant
retraining. `--load-model` now restores weights and standardization statistics and skips training.
Its first job was to reproduce the original run, and it does:

| | `daily_train.json` (2026-07-14) | this re-score |
|---|---|---|
| overall skill vs persistence | 0.40769555 | **+0.4077** |
| surfChl1 | 0.52207930 | +0.5221 |
| surfChl2 | 0.46082444 | +0.4608 |
| surfChl3 | 0.40156667 | +0.4016 |
| surfChl4 | -606.9265815 | -606.9266 |
| surfChl5 | 0.20795820 | +0.2080 |

Rollout step MSEs match as well, and the guard reports the standardization reproduced to
**2.20e-07 sigma**. The loader verifies rather than patches: if a run cannot reconstruct the z-space
the model was trained in, it aborts instead of scoring the model against the wrong space.

## 1. The AR(1) hypothesis was right, and it did not matter

The prior note suggested `+0.408` had a real chance of surviving, because daily lag-1 r of 0.994 to
0.996 means persistence and AR(1) nearly coincide, unlike monthly where the gap flipped `+0.48` to
`-0.161`. **That is confirmed.** Tendency-normalized error of per-cell annual AR(1), where 1.000 is
exactly persistence:

| tracer | AR(1) | AR(1) seasonal | seasonal clim |
|---|---|---|---|
| surfChl1 | **0.974** | 0.996 | 2.934 |
| surfChl2 | **0.982** | 1.015 | 3.295 |
| surfChl3 | **1.002** | 1.110 | 14.546 |
| surfChl5 | **0.995** | 1.057 | 4.582 |

AR(1) is at most 2.6% better than persistence, and the seasonal baselines are far worse than both.
Overall, skill vs persistence is **-4.0031 [-4.9470, -3.2036]** and skill vs AR(1) is
**-4.0940 [-5.0561, -3.3212]**. The baseline upgrade costs 0.09. **AR(1) is not what kills this
model.**

## 2. The calendar contamination does not touch this comparison, measured not assumed

Both scorings were run, one on the cube's own pre-fix time axis and one with time rederived from
`iters` at `delta_t = 1200 s`. The overall numbers are **bitwise identical**.

That is a property of the result, not a failed flag. The seasonal baselines do move, substantially:
`seasonal_clim` normalized error shifts by -0.11 to -0.68, and `ar1_seasonal_percell` by +0.013 to
+0.046. But `persistence` and `ar1_percell` are calendar-free by construction and come back
identical to the last digit, and since **`ar1_percell` is the winning baseline everywhere**, the
headline cannot move. The correction was necessary to check and turns out not to bind here.

## 3. Log space is what kills it, and the clipping is a model defect

Scoring logged channels as `log(clip(x, 1e-12))` sends any non-positive cell to -27.6 while a
typical surface Chl1 sits near -4.7. Each clipped cell is therefore **20 to 25 log units** from the
median, contributing a squared residual of order 500 against typical residuals near 0.01.

The audit decomposes which array is responsible, on the 26,237,250 scored cell-pairs per channel:

| channel | pred non-positive | **true** non-positive | persistence non-positive |
|---|---|---|---|
| surfChl1 | **2.211%** | 0.085% | 0.086% |
| surfChl2 | **1.010%** | 0.085% | 0.085% |
| surfChl3 | **5.853%** | 0.040% | 0.040% |
| surfChl5 | 0.000% | 0.000% | 0.000% |

**The emulator emits non-physical chlorophyll 26 to 146 times more often than v05 does.** This is
the same failure `physics_verify.py` found on iron, where the model invented 4.5% negative values
while scoring +0.43. Skill is blind to it; log space is not.

## 4. Removing every clipped cell is generous to the model, and it still loses

Restricting to cells where prediction, truth and persistence are all strictly positive removes
exactly the cells the model got most wrong, so it is a favourable subset. Even so:

| channel | log skill, all cells | **log skill, strictly positive** | linear skill, same subset |
|---|---|---|---|
| surfChl1 | -33.97 | **-1.71** | +0.5224 |
| surfChl2 | -16.51 | **-2.49** | +0.4609 |
| surfChl3 | -226.57 | **-12.43** | +0.4066 |
| surfChl4 | undefined | undefined (100% clipped) | -606.11 |
| surfChl5 | +0.1253 | **+0.1454** | +0.2073 |

Two things follow. The published all-cell log numbers, including the `-4.00` overall, are
**dominated by clipped cells and must not be quoted as skill**. And the collapse is still real
without them: three of four channels lose to persistence in log space by a wide margin.

## 5. One channel survives, cleanly

`surfChl5` has **zero** non-positive values in prediction, truth or persistence. Its log skill is
`+0.1253` on all cells and `+0.1454` on the strictly-positive subset, which is the same set. Against
the strongest free baseline it is **+0.060 [+0.028, +0.084]**, a block-bootstrap CI clear of zero,
and it is the only channel where that holds. It is also the only channel whose positivity was never
in question, which is unlikely to be a coincidence.

## A tool defect this exposed

`emulator_baselines_v2.py` clips at a hard `LOG_EPS = 1e-12`, with a comment saying this matches
`emulator_poc.LOG_EPS`. It no longer does. `emulator_poc.py` moved to a **percentile-based
per-channel floor** (`log_floors`, `--log-floor-pct`, default p1) precisely because the fixed floor
"inflated the log-space std by 1.72x and compressed the real signal". The scorer kept the
superseded convention, so its log-space numbers are systematically harsher than the trainer's for
any channel with non-positive cells. Filed as an issue.

## What this does and does not close

**Closed.** This artifact does not support a daily MAKE. It is contaminated four ways as previously
found, and now the headline itself is shown to be a linear-space number that does not survive a
log-space reading on its own held-out set.

**Not closed.** The daily *question* for Track 2. This model was **trained in linear space**, and
`--log-transform` is the known fix for both the metric artifact and positivity, since it cannot emit
non-positive output at all. A log-space-trained daily emulator has never been run. What is now
measured is that the existing one fails for a reason with a known remedy, and that AR(1) is not the
obstacle it was expected to be.

**Carry forward.** `surfChl4` should never appear as a target again: 99.6% of its predictions and
100% of its truth values are non-positive, so log space is undefined for it and its linear skill of
-606 is a division by noise.
