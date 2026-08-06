# Fixing the endpoint-vs-time-mean mismatch relocates recovery to the equatorial Pacific — and breaks the iron pair there

**Date:** 2026-08-06 · **Job:** 287072 (`dd-tmloss`, 15 array tasks) ·
**Artifacts:** `/scratch/qi_zim_neu/tmloss/{tm_ctrl,tm_mean,tm_null}` · **Lever:** `TIME_MEAN_LOSS` ·
**Config:** `scripts/configs/flagship_geo1.sh` sourced, nine-value runtime assert passed ·
`verify_run` **exit 0** on all three arms · **Pre-registered:**
[`2026-08-06_prereg_time_mean_loss.md`](2026-08-06_prereg_time_mean_loss.md), before results.

**Verdict: comparing the model's time mean to the time-mean target instead of its end state does
NOT improve the headline — it RELOCATES recovery. The aggregate trio goes 21/7/17 → 0/0/0 because
natlsubpolar and southernoceanpac fall back to their untrained values. But in the equatorial
Pacific both iron parameters recover together: `scav_rat` 50/50 within ±30% of Carroll under all
three collapses against a null of 0/50, and `alpfe` 50/50 at 0.986× Carroll — NOT at its bound.
That is the alpfe↔`scav_rat` pair jointly identified in one basin without bound geometry, which
this project has not previously achieved anywhere. One submission, no replication.**

## 1. The pre-registered falsifier, answered honestly

The prereg said: if `tm_ctrl` does not reproduce the flagship trio (~25/50 arithmetic, ~12/50
geometric), the submission is void.

`tm_ctrl` gives trio **21 / 7 / 17**. Strictly that is not 25/12.

But it is an excellent reproduction of the *other* recent submission at the same config. Against
job 270032's `fs3_w200` arm, a different job on a different day:

| | trio arith | trio geom | `scav_rat` eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|---|---|
| `fs3_w200` (job 270032) | 20 | 7 | 0.425x | 0.433x | 0.881x |
| `tm_ctrl` (job 287072) | 21 | 7 | **0.429x** | **0.432x** | **0.881x** |

The per-basin medians agree to three decimals across two independent submissions. So the control is
behaving reproducibly; what neither reproduces is the **published** 25/12.

**Reading applied here:** the within-job comparison (`tm_ctrl` vs `tm_mean`, same code, same job,
control present) is licensed and is the only comparison this document makes. The gap to the
published flagship is a separate, real reproducibility question that two jobs now agree on, and it
is not resolved here.

## 2. What the lever did

Per-AOI median recovered value as a multiple of Carroll, `per_aoi_recovered_geom`, n=50:

**`scav_rat`** (Carroll 6.025e-7, band [0.60x, 1.40x]):

| arm | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| untrained null | 2.330x | 2.454x | 2.469x |
| `tm_ctrl` endpoint | 0.429x | 0.432x | **0.881x** |
| `tm_mean` time-mean | **0.806x** | 2.243x | 2.184x |

**`alpfe`** (Carroll 0.9283, upper bound 1.0 = **1.077x**):

| arm | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| untrained null | 0.543x | 0.544x | 0.543x |
| `tm_ctrl` endpoint | 1.069x | 1.077x | 1.076x |
| `tm_mean` time-mean | **0.986x** | 0.364x | 0.574x |

Read those two tables together and the result is unambiguous:

- Under the **endpoint** loss, `alpfe` sits **at the bound in all three basins** (1.069–1.077x
  against a bound at 1.077x) and `scav_rat` is inside the band only in the Southern Ocean.
- Under the **time-mean** loss, natlsubpolar and southernoceanpac barely move from the null for
  `scav_rat` (2.454 → 2.243, 2.469 → 2.184) — they are close to untrained. Meanwhile eqpac moves a
  long way and lands on target: 2.330x → 0.806x for `scav_rat`, 0.543x → 0.986x for `alpfe`.
- `alpfe` in eqpac comes **off the bound**: 0.986x Carroll is 91.5% of the ceiling, where the
  control sits at 99.7%.

## 3. The equatorial Pacific result, with both required checks

`scav_rat`, eqpac leg only, trained vs its architecture-matched untrained null:

| band | trained (arith / geom / median) | null |
|---|---|---|
| ≤0.10 | 18 / 1 / 41 | **0 / 0 / 0** |
| ≤0.20 | 47 / 28 / 49 | **0 / 0 / 0** |
| ≤0.30 | **50 / 50 / 49** | **0 / 0 / 0** |
| ≤0.40 | **50 / 50 / 50** | **0 / 0 / 0** |
| ≤0.45 | 50 / 50 / 50 | 0 / 0 / 0 |

- **Band sensitivity: passes.** At ceiling from 0.30 to 0.45, and still 47/50 arithmetic at ≤0.20.
  It does not peak at the reported threshold; it saturates well inside it.
- **Pooler invariance: passes.** 50/50/50 at 0.30 and 0.40 — identical under all three collapses.
- **Prior contamination: none.** The null's eqpac leg is empty at every band under every collapse.
- **Replication: ABSENT.** One submission. This is the check the project most often fails and the
  reason nothing here should be quoted as established.

`alpfe`'s eqpac leg is **50/50/50 at every band from 0.30 to 0.45**, so both members of the pair are
simultaneously at ceiling in that basin, in the same 50 seeds.

## 4. Why this matters more than the aggregate

The ≥2-of-3 rule reports **0/50** for `scav_rat` and the trio under `tm_mean`, because one passing
basin is not two. On the headline metric this arm is a total failure.

That is the wrong way to read it. The standing obstacle in this project is the rank-1
alpfe↔`scav_rat` degeneracy: the two parameters trade off along a ridge, and the published result
gets `alpfe` only by railing it into a bound that sits inside the pass band. Here, in one basin,
**both parameters land near Carroll at once, and `alpfe` is not at its bound.** The measured
correlation moves from ρ = −0.67 (control) to ρ = +0.58 (time-mean); both are reported by
`grade_recovery` as "ridge partially broken", and the sign flip is itself unexplained.

The equatorial Pacific is also the basin with the **most** iron data — 26 surface and 28 subsurface
GEOTRACES bins, twice the Southern Ocean's 13/14 — and it has never recovered `scav_rat` before
(7/50 at best, 12/100 in the width arms). That was a standing puzzle, attributed to forward-model
misspecification. This result offers a different explanation: the basin with the most data was the
one most damaged by comparing an endpoint to a time mean.

**A plausible mechanism, not yet tested:** the equatorial Pacific is the most dynamically active of
the three, so its state at day 50 is furthest from its own time average, and it therefore suffered
most from the mismatch. That predicts the effect should scale with each basin's internal
variability, which is measurable from the existing cubes and is the obvious next check.

## 5. What this does NOT establish

- **It is not an improvement.** Trio 21/7/17 → 0/0/0. Anyone quoting this as progress on the
  headline is misreading it.
- **natlsubpolar and southernoceanpac end up near-untrained under the time-mean loss.** That is a
  real degradation and it is not explained. Until it is, "fix the loss" is not a recommendation.
- **No replication.** Single submission, and the project's own three-check rule puts replication
  first precisely because effects of this size have died at this step before.
- **The control does not reproduce the published flagship** (21/7 vs 25/12), though it does
  reproduce job 270032 to three decimals. That gap is now seen in two independent jobs and needs
  its own investigation.
- **`diatomgraz` goes to 0/50 everywhere** under `tm_mean`, including the eqpac leg that was its
  one established regional result. Another degradation this document does not explain.

## 6. What to do next

1. **Replicate**, as a fresh submission. Nothing above is quotable until it survives that.
2. **Explain the natl/SO collapse.** If the time-mean loss flattens the gradient in slow-adjusting
   basins, that is diagnosable from the per-AOI loss histories already written to the run JSONs.
3. **Test the variability mechanism** — does the endpoint-minus-time-mean distance rank the basins
   the way the effect does?
4. **Do not change the flagship loss.** The lever stays off by default. On the project's own
   grading metric it makes things worse, and the one thing it improves is a single-basin result
   with no replication.
