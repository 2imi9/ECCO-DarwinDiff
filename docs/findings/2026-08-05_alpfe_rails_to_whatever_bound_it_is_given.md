# `alpfe` rails to whatever bound it is given, so its 49/50 is largely the bound's doing

**Date:** 2026-08-05 · **Job:** 276927 (4 arms x 50 seeds) + 276928 (graded) ·
**Artifacts:** `/scratch/qi_zim_neu/alpfebound/{ab_ctrl,ab_wide,ab_null_ctrl,ab_null_wide}` ·
**Lever:** `DD_ALPFE_HI`, added in [#234](https://github.com/2imi9/ECCO-DarwinDiff/pull/234) ·
**Config:** `scripts/configs/flagship_geo1.sh`, six-way non-vacuity gate passed on every task.

**Verdict: `alpfe` carries NO upper-side information. The fit sits at 99.7% of a 1.0 bound and
99.6% of a 1.6 bound. The ~8% we have been quoting as a precision is the distance from the bound
to Carroll and nothing else. Widening the bound takes the count from 49/50 to 0/50 while the
UNTRAINED null rises from 10/50 to 50/50.**

## 1. The measurement

Four arms in one submission. Two bounds, each with its own architecture-matched untrained null.

| arm | upper bound | `alpfe` median | % of bound | vs Carroll | per-AOI >=2-of-3 |
|---|---|---|---|---|---|
| `ab_ctrl` | 1.0 | 0.9967 | **99.7%** | 1.074x | **49/50** |
| `ab_wide` | 1.6 | 1.5940 | **99.6%** | 1.717x | **0/50** |
| `ab_null_ctrl` | 1.0 | 0.5014 | 50.1% | 0.540x | 10/50 |
| `ab_null_wide` | 1.6 | 0.7865 | 49.2% | 0.847x | **50/50** |

Carroll is 0.92831. The Cal band is 0.40.

Two things read straight off that table.

**The trained fit rails.** 99.7% and 99.6% of bound. It does not stop near Carroll when given room;
it goes to the ceiling, wherever the ceiling is. The pre-registered reading was "runs on to ~1.4
implies no upper-side information". It ran to 1.594.

**The nulls sit at their midpoints**, 50.1% and 49.2%, exactly as an untrained sigmoid should. That
is the control working.

## 2. Why the nulls were not optional

Widening the bound moves the untrained prior midpoint from 0.525 to 0.825. Against Carroll that is
rel 0.434 and rel 0.111 respectively. The second is inside the 0.40 band.

So at the wider bound **an untrained network scores 50/50 and the trained one scores 0/50.** The
network is beaten by its own initialisation.

Run the wide arm alone and the honest-looking conclusion would have been "widening the bound breaks
`alpfe`". It does not. It moves the prior into the band and moves the fit out of it, and those are
different facts. This is the `diatomgraz` 35/50 failure mode in a new place, caught this time
because the bound-matched null was in the same submission.

## 3. What this costs the headline

`alpfe`'s upper bound sits at rel **0.077** from Carroll, well inside the 0.40 band. A fit that
rails to that bound therefore scores as recovered **whatever the data says**. The 49/50 is
substantially measuring where we put the bound.

What survives, and it is not nothing: at bound 1.0 the trained arm is 49/50 against a null of
10/50. Training moves `alpfe`, and it moves it **up**. The direction is data. The value is not.

**Permitted:** "the observations say `alpfe` is high, and say so decisively against an untrained
control".
**Not permitted, from today:** "`alpfe` is recovered to about 8%", "`alpfe` = 0.93", or any reading
of the 49/50 as an accuracy.

## 4. The generalisation, which needs no compute

A recovery count can be a rail-to-bound artifact exactly when a bound lies inside the pass band.
That is arithmetic on the registry:

| parameter | rel(lower) | rel(upper) | verdict |
|---|---|---|---|
| `alpfe` | 0.946 | **0.077** | **AT RISK** — confirmed by this experiment |
| `diatomgraz` | 0.940 | **0.205** | **AT RISK** — untested |
| `scav_rat` | 0.950 | 3.979 | safe |
| `Smallgrow` | 0.849 | 2.026 | safe |
| `Biggrow` | 0.768 | 3.635 | safe |
| `R_PICPOC` | 0.882 | 34.336 | safe |

**`R_PICPOC` is exonerated by arithmetic.** Its bounds are 0.88 and 34.3 band-units from Carroll, so
no railed fit can land inside the band. Its 50/50 cannot be bound geometry, and no experiment is
needed to say so. That matters, because `R_PICPOC` is the other half of the "two recovered
globally" claim and this result does not touch it.

`diatomgraz` is the remaining exposure. It already fails the contract on prior contamination and
sits below its own null, so this would be a third independent reason rather than a new one.

Shipped as `contract.bound_proximity_risk`, beside `rescale_is_admissible`.

## 5. What this does not say

It does not say the bound is wrong. Whether 1.0 is a hard physical ceiling for a scalar on
already-soluble iron deposition is a physics question, put to J. Lauderdale on 2026-08-05 and open.
If 1.0 is physical then railing to it is the fit correctly reporting "at least this high, and the
data cannot see further". If it is arbitrary then the bound is an unstated prior.

It does not touch the estimator-independence result. EKI and backprop agreeing on `scav_rat` is a
separate measurement on a separate parameter.

It does not retract the *signal*. 49/50 against 10/50 is a real difference. Only the reading of it
as a precision is retracted.

## 6. Supersedes

Retires the phrasing "`alpfe` recovers to within about 8%" wherever it appears, and the standing
instruction in CLAUDE.md not to quote 7.6% as an accuracy is now upgraded from caution to a
measured fact.

## 7. Reproduce

```bash
# on AICR, from ~/emulator_poc
sbatch --array=0-19%6 /scratch/qi_zim_neu/ab.sbatch          # 4 arms x 5 chunks x 10 seeds
sbatch --dependency=afterany:<jobid> /scratch/qi_zim_neu/ab_grade.sbatch
```

The lever is inert unless set: `DD_ALPFE_HI` absent reproduces the registry exactly, which the
sbatch asserts per task before training, in both directions.
