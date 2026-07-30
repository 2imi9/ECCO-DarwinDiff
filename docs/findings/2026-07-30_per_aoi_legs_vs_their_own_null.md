# Grading each AOI leg against its own null: scavenging is regionally identifiable, and the diatom qualification is too pessimistic

**Date:** 2026-07-30 · **Tool:** `scripts/analysis/per_aoi_vs_null.py` ·
**Artifacts:** `/work/neu/p2026_0089_neu/coverage/*.json` · **Baselines:** `prior_mld_n50` for the
MLD arms, `prior_ctrl_n50` for the flagship, both n=50 untrained ·
**Verdict: two statements in the 2026-07-30 note to Jon need revising, and one of them makes the
result stronger rather than weaker.**

## Why the aggregate count cannot settle this

A parameter reaches a per-AOI majority two different ways, and they are indistinguishable in the
headline:

- **coverage**: every AOI carries information and every leg beats its own chance rate;
- **pooling**: one or two AOIs carry it and the shared DINN exports the magnitude to AOIs that
  have none. This is exactly what the R_PICPOC Southern Ocean leg was already shown to do, since
  it recovers with zero Daniels cells and collapses when the anchor is pulled from the other two
  basins.

They differ **per AOI, against a per-AOI null**. So each leg is graded against the same leg of the
architecture-matched untrained run, with an exact binomial P. A leg that does not clear its own
null is not evidence, however good the aggregate looks. Format below is trained/untrained, and
`*` marks a leg that beats its own untrained rate at P<0.05.

## The strict observations-only arm, `obsonly_mld_litic`

| parameter | majority | eqpac | natlsubpolar | southernoceanpac | legs above own null |
|---|---|---|---|---|---|
| alpfe | 50/50 | 50/14 * | 50/15 * | 50/16 * | **3 of 3** |
| diatomgraz | 50/50 | 50/36 * | 42/34 * | 50/32 * | **3 of 3** |
| R_PICPOC | 43/50 | 5/0 . | 50/0 * | 42/0 * | 2 of 3 |
| scav_rat | **0/50** | 0/0 . | 0/0 . | **42/0 \*** | 1 of 3 |
| Smallgrow | 6/50 | 2/8 . | 25/7 * | 17/8 * | 2 of 3 |
| Biggrow | 3/50 | 5/0 . | 12/0 * | 16/0 * | 2 of 3 |

## 1. Scavenging is not unrecoverable. It is regionally identifiable, in the Southern Ocean

The note to Jon says "Scavenging does not, which follows from the degeneracy." The 0/50 majority is
correct, but the reason is not that nothing was recovered. It is that recovery happens in **exactly
one** AOI, so a 2-of-3 majority can never form.

| arm | eqpac | natlsubpolar | **southernoceanpac** |
|---|---|---|---|
| `obsonly_mld_litic` | 0/50 | 0/50 | **42/50 \*** |
| `obsonly_mld` | 0/50 | 0/50 | **39/50 \*** |
| `obsonly_litic` | 0/50 | 0/50 | **50/50 \*** |
| flagship `ctrl_n50` | 8/50 * | 19/50 * | **49/50 \*** |

Against an untrained rate of 0/50 in every case. This is consistent and it is mechanistically
sensible: the Southern Ocean is the iron-limited HNLC region where the scavenging sink is the
dominant term, so it is where the sink rate is most exposed. The degeneracy argument still holds
globally, since a source scalar over a sink rate sets concentration. What the per-AOI split adds is
that the Southern Ocean apparently breaks it, and the other two basins do not.

**Say to Jon:** scavenging recovers in the Southern Ocean at 39 to 50 of 50 across every
observations-only arm and nowhere else, so the 0-of-50 headline is an artifact of the 2-of-3
majority rule rather than a measurement that nothing was learned. That is a stronger and more
interesting statement than "scavenging does not recover", and it points the UDE at a specific
basin rather than at the global closure.

**Do not over-read it.** A single AOI clearing its null is one basin, not a validated regional
result, and the mechanism is unestablished. The candidates are that the SO genuinely constrains the
sink rate, or that the SO leg is inheriting magnitude through the shared network as R_PICPOC's does.
Those are distinguishable by the same anchor-off control that settled R_PICPOC, and it has not been
run for scav_rat.

## 2. The diatom qualification is too pessimistic for the arm it describes

The note says "with the model pattern term removed most cells carry no gradient, so the diatom
result leans on a small set of informative cells rather than good coverage."

In `obsonly_mld_litic`, the arm that statement describes, **diatomgraz clears its own null in all
three AOIs** (50/36, 42/34, 50/32). It is not leaning on one basin. The 96.1% zero-gradient figure
is about *cells*, and it is correct, but it does not imply the recovery is concentrated in one
region, and per AOI it demonstrably is not.

The qualification is right for a different arm. Without the MLD channel:

| arm | eqpac | natlsubpolar | southernoceanpac | legs above null |
|---|---|---|---|---|
| `obsonly_mld_litic` (MLD on) | 50/36 * | 42/34 * | 50/32 * | 3 of 3 |
| `obsonly_litic` (**MLD off**) | 50/36 * | 33/34 . | 0/32 . | **1 of 3** |
| flagship `ctrl_n50` | 36/33 . | 2/32 . | 2/31 . | **0 of 3** |

So MLD is what gives diatomgraz its coverage, matching the earlier finding that adding the MLD
channel takes diatomgraz from 3/10 to 10/10 by fixing the Southern Ocean. Without it the result is
a single-basin eqpac result, which is what the qualification describes.

**Say to Jon:** the coverage caveat applies to the no-MLD configuration, not to the arm being
reported. In the MLD arm every basin clears its own null independently. Note also that diatomgraz
carries the highest chance rate of any parameter, 0.64 to 0.72 untrained, because its prior midpoint
sits at rel 0.367 inside the 0.40 band. So 50/50 is a real result but the honest baseline is 32 to
36 of 50, not zero, and that must be quoted with it.

## 3. R_PICPOC fails in the one basin that has the anchor

In the strict arm R_PICPOC is 43/50 overall but **5/50 in eqpac**, which does not clear its null,
while natlsubpolar is 50/50 and southernoceanpac 42/50. eqpac is one of the two AOIs that carries
Daniels coverage, with 34 cells against natlsubpolar's 26 and the Southern Ocean's zero.

So in the observations-only configuration the anchored basin is the one that fails, and the
unanchored basin recovers. The flagship does not do this: there R_PICPOC is 47/50 in eqpac. The
difference between the two is the Darwin-pattern term. That term is Darwin's own output and is
exactly the part being removed to make the arm independent, so this is not a small detail.

**This is unexplained and should not be reported as a result until it is.** It is the sharpest open
question the audit produced.

## 4. The growth pair behaves as expected

`Smallgrow` and `Biggrow` reach 6/50 and 3/50 with legs at or below their nulls in the anchored
basin. Nothing here disturbs their exclusion from the denominator, which rests on the separate and
settled circularity argument rather than on these counts.

## What to do next

1. Run the anchor-off control for `scav_rat`'s Southern Ocean leg, exactly as was done for
   R_PICPOC, to separate genuine regional identifiability from inherited pooling. This is the
   single highest-value follow-up and it gates whether claim 1 can be published.
2. Explain the eqpac R_PICPOC failure before the manuscript quotes 43/50.
3. Aim the iron-closure UDE at the Southern Ocean specifically, since that is where the sink rate
   is exposed.
