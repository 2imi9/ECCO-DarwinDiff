# The pass band is load-bearing: `alpfe` and `R_PICPOC` are threshold-robust, `scav_rat` is a knife edge

**Date:** 2026-08-03 · **Evidence:** job 258439, arm `cap16` (flagship config: width 16, 2000
epochs, `geo1`, n=100) and its untrained null · **`verify_run` exit 0**
· **Status: a property of the project's headline METRIC, found while auditing an unrelated result.**

## How this was found

A width-capacity result looked decisive (`scav_rat` 45/100 → 77/100, P = 5.6e-06, both split
halves clearing 0.01). Re-counting the identical artifacts with only the **pass threshold** moved
showed the effect was maximal exactly at 0.40 and vanished at 0.30 and 0.50. That prompted running
the same sweep on the parameters themselves rather than on the difference between two arms.

The check costs one query over artifacts already on disk, and it overturned a document's own first
draft.

## The measurement

`cap16` is a flagship-config arm, so this is the published grading regime. Per-AOI ≥2-of-3 counts
out of 100, recomputed at each pass band:

| parameter | 0.20 | 0.30 | 0.35 | **0.40** | 0.45 | 0.50 | 0.60 | swing 0.35→0.45 |
|---|---|---|---|---|---|---|---|---|
| `alpfe` | 98 | 98 | 98 | **98** | 98 | 98 | 98 | **+0** |
| `R_PICPOC` | 33 | 89 | 96 | **99** | 100 | 100 | 100 | +4 |
| `scav_rat` | 4 | 13 | 22 | **45** | 81 | 99 | 100 | **+59** |
| `diatomgraz` | 1 | 1 | 2 | **3** | 7 | 11 | 17 | +5 |

And the architecture-matched untrained null (`cap16_null`, n=50, doubled to compare on /100):

| parameter | 0.20 | 0.30 | 0.35 | **0.40** | 0.45 | 0.50 | 0.60 |
|---|---|---|---|---|---|---|---|
| `alpfe` | 0 | 0 | 4 | **20** | 42 | 90 | 100 |
| `R_PICPOC` | 0 | 0 | 0 | **0** | 0 | 0 | 0 |
| `scav_rat` | 0 | 0 | 0 | **0** | 0 | 0 | 0 |
| `diatomgraz` | 0 | 12 | 28 | **64** | 82 | 98 | 100 |

## What this changes

### `alpfe` and `R_PICPOC` get *stronger*, and should be quoted at a tighter band

`alpfe` is **98/100 at every band from 0.20 to 0.60** — completely flat. Better still, its
untrained null is **0** at 0.20 and 0.30 but **20** at 0.40. So `alpfe` is currently reported at
the *only* band where its null is contaminated. Quoted at ≤0.30 it is **98/100 against a null of
0/100**, which is a cleaner and stronger claim than the one in the manuscript.

`R_PICPOC` is 96–100 from 0.35 upward, and **33/100 even at ≤0.20** against a null of 0 at every
band. Both parameters are threshold-robust, and that robustness is itself a result: it means their
recovery is not an artifact of where a grading line was drawn.

### `scav_rat` is a knife edge, and it is the sole binding leg

Moving the band by ±0.05 around 0.40 swings `scav_rat` from **22/100 to 81/100**. The published
headline sits at the steepest point of its own curve. Its null is 0 at every band, so it *is*
recovering something — but the **count is not a stable effect size**, and differences between
configurations measured in that count will be dominated by how much probability mass each one
happens to park near the threshold.

**CLAUDE.md records that the flagship trio count *equals* `scav_rat`'s, because it is the sole
binding leg. The joint headline therefore inherits this knife edge.** The 25/50 is not wrong; it
is one point on a steep curve, and it has been reported without the curve.

### `diatomgraz` is BOTH — locally recovered in eqpac and anti-recovered elsewhere

This is the result the band was hiding most, and it runs opposite to the `scav_rat` case: for
`scav_rat` the 0.40 band sits at the steepest point of the curve and is **over-sensitive**; for
`diatomgraz` the band is **too wide to see anything**, because its untrained null already passes
there.

The eqpac leg alone, trained (n=100) against its own untrained null (n=50):

| band | trained | untrained | Fisher P |
|---|---|---|---|
| 0.05 | 20/100 | 0/50 | 2.0e-04 |
| 0.10 | 40/100 | 0/50 | 5.5e-09 |
| 0.15 | 54/100 | 0/50 | 3.3e-13 |
| 0.20 | 59/100 | 1/50 | 3.0e-13 |
| 0.30 | 71/100 | 4/50 | 6.4e-14 |
| **0.40 (reported)** | **75/100** | **33/50** | **0.254 — cannot separate** |

**At the reported band the effect is invisible. At every tighter band it is overwhelming.**
Training moves the eqpac median relative error from 0.379 to **0.141**; the 40% band simply
cannot resolve that, because 0.379 is already inside it.

The other two basins are genuinely dead and genuinely anti-recovered: at band 0.20 both score
**1/100** trained, and at 0.40 both fall *below* their own nulls (natl 2/100 vs 32/50, sopac
3/100 vs 31/50, both P < 1e-4), with medians pushed from 0.38 out to 0.79 and 0.86.

So the correct statement is **regional, exactly as it already is for `scav_rat`**:

> `scav_rat` is locally identifiable in the **Southern Ocean**.
> `diatomgraz` is locally identifiable in the **equatorial Pacific** — 20/100 at ≤5% and 40/100
> at ≤10% against an untrained 0/50 — and is driven *away* from Carroll in the other two basins.

The aggregate ≥2-of-3 count at band 0.40 reports **3/100** and conveys neither half of that.
This also settles `ded1` affirmatively with a clean measurement: "diatomgraz carries no
observational signal" is not merely unsupported, it is **false**.

### The ≥2-of-3 aggregate also hides per-leg DAMAGE

Separately from the band, the majority rule conceals harm to individual legs, because a
parameter only needs two. Comparing width 16 against width 39 leg by leg:

| parameter · leg | cap16 | cap39 | Fisher P | |
|---|---|---|---|---|
| `alpfe` · eqpac | 84/100 | **68/100** | 0.0125 | **degraded** (median 0.076 → 0.098) |
| `diatomgraz` · eqpac | 75/100 | **56/100** | 0.0072 | **degraded** (median 0.141 → 0.225) |
| `R_PICPOC` · sopac | 87/100 | 100/100 | 0.0002 | improved |
| `scav_rat` · natl | 35/100 | 74/100 | <1e-4 | improved (band-amplified) |

`alpfe`'s **aggregate is 98/100 in both arms** and shows none of this. So "the controls are
undamaged" — which this session wrote before checking — is true only at the aggregate level,
which is precisely the level that cannot see it. **Report per-leg counts against per-leg nulls,
not just the majority.**

## Recommended practice

1. **Report the band sweep, not a single band.** For each parameter, publish the count at
   0.30/0.40/0.50 with its null at each. A flat row is a strong result; a steep row is a warning.
2. **Quote each parameter at a band where its own null is 0.** `alpfe` at ≤0.30, `R_PICPOC` at any
   band, `scav_rat` at any band. `diatomgraz` has no such band.
3. **Add band sensitivity to the house standard.** Alongside the split-half, every reported effect
   must be re-counted at ±0.05 and must not peak at the reported threshold. The capacity result
   passed the split-half convincingly and still failed this one, so the two are not redundant.

## What this does NOT say

It does not retract `scav_rat`'s recovery: the null is 0/100 at every band, so the parameter is
genuinely being constrained. It says the *count* is a poor measure of how much, and that
comparisons between configurations expressed in that count can be dominated by threshold geometry
rather than by accuracy.

It also does not touch `alpfe`'s or `R_PICPOC`'s standing, which it strengthens.

## Immediate consequence for the manuscript

The identifiability study's cleanest claims (`alpfe`, `R_PICPOC` point-identified given an anchor)
survive this and improve under it. The claim that needs restating is any quantitative comparison
carried by `scav_rat`'s count — including the joint trio number, which is the same number.
