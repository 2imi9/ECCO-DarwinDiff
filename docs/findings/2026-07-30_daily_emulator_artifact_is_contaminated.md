# The pre-existing daily emulator does not settle the daily question

**Date:** 2026-07-30 · **Artifact:** `/scratch/qi_zim_neu/daily_v5/daily_train.json` (AICR),
generated 2026-07-14 · **Verdict: contaminated four ways, and it never measured the bar it needed
to clear.**

A daily emulator was trained on eqpac surface chlorophyll before any of the recent daily work began.
The handoff note called reading it a free result that would settle the emulator half of the
daily-cadence question. **That was wrong**, and this note is the correction.

## What it reports

```
"verdict": "MAKE"
"headline_overall_skill_vs_persistence": 0.4077
```

eqpac, 5 surface Chl channels, FNO2d residual, rollout-k8, single seed, 150 epochs.

## Why it does not settle anything

### 1. The calendar bug is baked into its config

```
"median_step_days": 0.75,
"dt_hours": 18.0
```

Daily files step by **72 iterations**. At the wrong `delta_t = 900 s` that is `72*900/86400 = 0.75`
days. At the true `1200 s` it is exactly **1.0**. This run predates PR #186 by six days, and the
bug's signature is recorded in its own config block.

The contamination is selective, and the split is clean:

| survives | void |
|---|---|
| `skill_vs_persistence = 0.4077` | `anomaly_r2_vs_climatology = 0.9727` |
| rollout step MSEs | `persistence_skill_vs_climatology = 0.9539` |
| positivity, mass drift | anything seasonal |

Persistence needs no time axis at all. Model and persistence use the same adjacent pairs, so
mislabeling the interval does not bias that ratio. Anything binned by month-of-year is void, because
94% of those bins were wrong.

### 2. It was never scored against seasonal AR(1)

Persistence is the only baseline in the file, and its own honesty notes flag persistence as strong.
Seasonal AR(1) is the baseline that took the monthly ensemble from **+0.48 to -0.161**.

### 3. Linear space, not log

No `--log-transform` in its `argv`. Chlorophyll spans about 2.8e6, and linear z-scoring is the known
source of the metric artifact.

### 4. One channel is dead and was trained on anyway

| channel | skill vs persistence | physical_std | frac negative in rollout |
|---|---|---|---|
| surfChl4 | **-606.9** | 2.9e-08 | **95.9%** |
| surfChl1 | +0.522 | 0.111 | 22.7% |
| surfChl3 | +0.402 | 0.013 | 16.9% |

`surfChl4` is numerically zero and should never have been a target. The monthly ensemble achieves
0% negatives; this one does not. The rollout is 6 steps of 0.75 days, so about four and a half days,
which is not a horizon in any useful sense.

## The one genuinely interesting thing in it

On monthly data, persistence and seasonal AR(1) diverge sharply, which is what flipped the sign. On
**daily** data they nearly coincide, because lag-1 r is 0.994 to 0.996 (job 235995). AR(1) nests
persistence, so skill against it is bounded above by +0.408, but here the gap should be small rather
than large.

**So +0.408 has a real chance of surviving an AR(1) comparison, unlike the monthly case.** That is
suggestive and unconfirmed, and it should not be stated more strongly.

## What settling it would cost

`scripts/analysis/emulator_baselines_v2.py` already implements the per-cell seasonal AR(1) with
block-bootstrap CIs. It needs a predictions `--fields` npz, which this run did not save, so the work
is: reload `daily_emulator_eqpac.safetensors` against the cube, dump predictions, re-score. **No
retraining.** One modest Slurm job.

Two caveats make it a new measurement rather than a correction of this one: the cube was built
pre-fix so the time axis must be rederived from `iters`, and `surfChl4` should be dropped and the
scoring done in log space.

## Bottom line

The daily question is **open for the emulator** and closed for the parameter learner (job 235995,
plus the circularity result in `2026-07-30_daily_design_workflow_recovered.md`). This artifact does
not move it either way.
