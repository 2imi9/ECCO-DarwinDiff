# Scavenging is locally identifiable in the Southern Ocean, from iron alone

**Date:** 2026-07-30 · **Jobs:** 238079 (n=50 + n=50 untrained) → 238080 (grade) ·
**Gate:** `verify_run` **exit 0 (VERIFIED & COMPLETE)** on both arms ·
**Pre-registration:** `2026-07-30_prereg_scavrat_southern_ocean.md`, written with zero JSONs on
disk · **Verdict: LOCAL IDENTIFIABILITY. The pre-registered rule fires, and the expected answer was
the other one.**

## The result

A **single-AOI** fit on `southernoceanpac`. With no other basin present the shared DINN has nothing
to pool from, so whatever `scav_rat` does is local by construction.

| parameter | recovered | untrained chance | P(>= obs) | verdict |
|---|---|---|---|---|
| alpfe | 50/50 | 0.340 | 3.75e-24 | decisive |
| **scav_rat** | **30/50** | **0.060** | **3.15e-24** | **decisive** |
| diatomgraz | 50/50 | 0.720 | 7.36e-08 | decisive |
| Smallgrow | 0/50 | 0.060 | 1.00 | not above chance |
| Biggrow | 0/50 | 0.060 | 1.00 | not above chance |
| R_PICPOC | 0/50 | 0.060 | 1.00 | not above chance |

The rule was fixed in advance: **LOCAL** if `k >= 25` and `P(X >= k | n=50, p) < 0.01`. Observed
`k = 30` and `P = 3.15e-24`. Both clauses are met and neither is marginal.

### Both pre-registered controls held exactly

These were written down before the run precisely so the result could not be talked into shape.

- **`alpfe` must stay high**, otherwise the single-AOI run is broken rather than informative. It is
  **50/50** against an untrained 17/50.
- **`R_PICPOC` must collapse.** The Southern Ocean has **zero** Daniels cells, so with no other
  basin to inherit from there is no calcite anchor at all. It is **0/50**. A high value here would
  have meant the anchor gating was wrong.
- `diatomgraz` was declared uninformative in advance (untrained rate 0.72) and is not quoted.

## What was expected, and why this is the more interesting outcome

The pre-registration named **pooling** as the prior expectation, on two grounds: the R_PICPOC
precedent, where the Southern Ocean leg recovers with zero Daniels cells and collapses to 13.06x
Carroll when the anchor is pulled from the other two basins; and the degeneracy argument, which is
global, since at steady state a source scalar over a sink rate sets concentration and nothing about
the Southern Ocean changes that algebra.

The measurement says otherwise. `scav_rat` recovers in the Southern Ocean **without any other basin
present**, from GEOTRACES surface and subsurface iron alone.

Two readings are consistent with the gauge-symmetry result from the same day
(`2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`), and they are not in conflict with it:

1. The orbit is **nearly** flat, not flat. Scavenging carries about 79.7% of the steady-state
   surface iron sink at Carroll values; biological uptake and vertical exchange carry the rest and
   are not homogeneous in the rate. In the Southern Ocean, an iron-limited HNLC region where the
   sink dominates and uptake is strongly Fe-limited, that residual curvature is at its largest.
2. The subsurface GEOTRACES term contributes depth structure, and depth is exactly the axis a
   concentration-at-one-level argument discards.

**Neither is established here.** This note reports that the recovery is local. It does not
establish the mechanism.

## Pooling still adds something

The three-AOI observations-only arms give the Southern Ocean leg **42/50, 39/50 and 50/50**; alone
it is **30/50**. So the other basins do help, but they are not where the signal comes from. Both
statements are now measured rather than assumed:

- **local information exists** (30/50 with nothing to inherit from), and
- **pooling adds to it** (30/50 alone against 39 to 50 of 50 in company).

That is a different and more defensible claim than either "scavenging does not recover" or
"scavenging recovers".

## The gate caught this experiment before it was reportable

The first attempt (job 237913) produced these same counts and **failed `verify_run` at exit 2**.
The `OBSONLY` config declares `DANIELS_RPICPOC_W=1.0` and `POSI_W=1.0`, and `southernoceanpac` has
zero cells for both, so the terms were declared and silently skipped: the run was not the config it
declared. The inert-term check added 2026-07-29 caught exactly the failure it was built for, on an
experiment designed by the person it caught.

Job 238079 re-ran it with both weights at 0 so the declaration is honest. The grader included a
seed-for-seed comparison, and the result is worth recording:

> **All six parameters, all 50 shared seeds, maximum relative difference 0.000e+00. Bitwise
> identical.**

So the numbers were never wrong and the gate was still right to refuse them. A term with no cells
contributes nothing to the loss, which is precisely why the declaration had to be corrected rather
than explained away: the artifact must say what the run did.

**The live loss in this arm is GEOTRACES surface and subsurface iron only**, with MLD as an input
channel and literature initial conditions. No calcite anchor, no Darwin pattern term, no PINN. That
makes the claim narrower and cleaner than the three-AOI arms: this is iron data constraining an
iron parameter, with nothing else in the loss.

## What this changes

**For the note to Jon.** "Scavenging does not come back" is wrong as stated and should be replaced.
It comes back in the Southern Ocean, it does so with no other basin present, and the degeneracy
argument still holds globally. The right framing is that the degeneracy is a gauge symmetry that
the Southern Ocean's residual curvature partially breaks, not that the degeneracy was mistaken.

**For the observable denominator.** This does not move it from 4. `scav_rat` was already in the
denominator. What changes is the qualifier: it is recoverable **subject to a regional condition**,
and the flagship's 25/50 trio, whose sole binding leg is `scav_rat`, is carrying a basin-specific
result reported as a global one.

**For the UDE.** It sharpens where to aim. The design that survives is a gauge-fixed closure that
estimates shape while reporting the level as unidentified, and the Southern Ocean is the one basin
where there is measured local information for it to work with.

## What would strengthen it

The mechanism is unestablished. The two candidate explanations, residual curvature from the
non-homogeneous terms and depth structure from the subsurface term, are separable: refit with the
subsurface GEOTRACES term removed. If `scav_rat` survives on surface iron alone, the curvature
reading is favoured; if it collapses, depth is doing the work, which would also make the
observation-design angle from the UDE screen the more valuable direction.
