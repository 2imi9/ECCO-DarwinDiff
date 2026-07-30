# R_PICPOC's per-AOI bias tracks the inverse large-phytoplankton fraction, in the two basins that carry the anchor

> ## ⚠ PARTLY SUPERSEDED the same day by `2026-07-30_rain_ratio_which_value_is_live.md`
>
> This note assumed the calcifying fraction is `Chl1 + Chl2` (diatoms plus large eukaryotes).
> Darwin 3 source says otherwise: `data.traits:36` gives `0.0, 2*4.1886E-2, 4*0.0`, so the
> calcifiers are types **2 and 3**, which in our box's ordering are **large eukaryotes and
> Synechococcus**, `Chl2 + Chl3`. One of the two is picoplankton.
>
> With the correct grouping the quantitative fit is worse. `natlsubpolar` still lands almost
> exactly (1/f 1.043 against a measured bias of 1.029) but `eqpac` **overshoots by about 2.9x**
> (1/f 4.329 against 1.518).
>
> **Survives:** the offset is systematic and tightly converged, not noise; the anchor constrains a
> product; the box applies the ratio to more types than Darwin does.
> **Does not survive:** that `1/f` predicts the magnitude. It fit better under the wrong grouping,
> which is what post-hoc matching on two points does.
>
> Also note the live ratio is **0.041886**, not the published 0.04245, and chlorophyll fraction is
> a proxy for production share rather than equal to it. Read that note first.

**Date:** 2026-07-30 · **Arms:** `obsonly_mld_litic` (n=50, verify_run exit 0), caches
`/home/qi_zim_neu/dd_data/ecco_darwin_v5/cache/*.pt` ·
**Verdict: supportive of the R_PICPOC times f_calc hypothesis and NOT statistically established,
because there are three AOIs and one of them has no anchor. Report as a mechanism with a
consistent sign, not as a fit.**

## What prompted this

`2026-07-30_per_aoi_legs_vs_their_own_null.md` flagged that in the strict observations-only arm
R_PICPOC is 43/50 overall but only 5/50 in eqpac, the basin with the most Daniels coverage, and
called it unexplained. It is not a failure. It is a precise, systematically biased estimate.

| AOI | median recovered / Carroll | median rel offset | IQR | seeds below Carroll |
|---|---|---|---|---|
| eqpac | **1.518** | 0.518 | [0.0615, 0.0654] | 0 of 50 |
| southernoceanpac | 1.268 | 0.268 | [0.0491, 0.0586] | 4 of 50 |
| natlsubpolar | **1.029** | 0.056 | [0.0420, 0.0464] | 15 of 50 |

Every seed in eqpac lands above Carroll and the IQR is 6% wide. The fit is converging tightly to a
value about 1.5x Carroll, which is just outside the 0.40 Cal band. The Cal-grade count of 5/50 is
therefore reporting a band edge, not a failure to converge.

## The hypothesis being tested

The one already put to Jon: the Daniels calcite anchor constrains the **product**
`R_PICPOC * f_calc`, where `f_calc` is the share of production done by calcifying types. Darwin
restricts calcification to 2 of 7 types; the 0-D box applies `R_PICPOC` to all 5. If the box must
reproduce an observed absolute PIC:POC with a calcifying fraction larger than Darwin's, it
compensates by inflating `R_PICPOC`, and the inflation should scale like `1 / f_calc` **locally**.

That predicts a spatial pattern, which is testable.

## Community composition per AOI, from the target caches

Mean chlorophyll fraction by PFT (Chl1 diatoms, Chl2 large eukaryotes, Chl3 Syn, Chl4 Pro-LL,
Chl5 Pro-HL):

| AOI | Chl1 | Chl2 | Chl3 | Chl4 | Chl5 | large (Chl1+Chl2) | regime |
|---|---|---|---|---|---|---|---|
| eqpac | 0.297 | 0.215 | 0.016 | 0.000 | **0.472** | 0.512 | picoplankton dominated |
| natlsubpolar | 0.030 | **0.889** | 0.070 | 0.000 | 0.012 | 0.918 | large-eukaryote bloom |
| southernoceanpac | **0.840** | 0.156 | 0.002 | 0.000 | 0.002 | 0.996 | diatom dominated |

## The result

Among the **two basins that actually carry Daniels cells**:

| AOI | Daniels cells | 1 / f_large | measured bias |
|---|---|---|---|
| eqpac | 34 | **1.955** | **1.518** |
| natlsubpolar | 26 | **1.089** | **1.029** |

Both the sign and the magnitude line up. The basin with roughly half its production in
picoplankton carries about half again as much R_PICPOC inflation; the basin that is nearly all
large cells carries almost none. The two quantities are the same size, order 1 to 2, which is what
a fraction-based mechanism predicts and is very different from the roughly 24x that a whole-model
structural mismatch would imply.

### The third basin is not a counterexample, it is not a test

`southernoceanpac` has `1/f_large = 1.004` yet a bias of 1.268, which looks like it breaks the
relationship. It has **zero Daniels cells**. Its R_PICPOC is not anchored locally at all; it is
inherited through the shared DINN from the two anchored basins, which is the already-established
pooling mechanism. An unanchored basin cannot test a hypothesis about what the anchor constrains,
so it is excluded on stated grounds rather than because it disagrees.

Including it, the correlation across all three is +0.83, which with n=3 is not significant and
should not be quoted.

## What can and cannot be said

**Can be said.** The R_PICPOC offset is systematic, spatially ordered, and in the two anchored
basins its size tracks the inverse local large-phytoplankton fraction. This is consistent with the
calcite anchor constraining `R_PICPOC * f_calc` rather than `R_PICPOC`, and it is a second,
independent line of support for that reading alongside the composition argument in
`2026-07-29_calcite_pooling_artifact.md`.

**Cannot be said.** That the relationship is established. Two anchored points cannot fit a
one-parameter law, let alone confirm it. There is no untrained baseline for a bias magnitude, only
for a count.

**Also worth recording, and it may matter more.** The observed PIC:POC in the target caches varies
enormously between basins: **0.0065 in southernoceanpac, 0.0308 in eqpac, 0.722 in
natlsubpolar**, a spread of about 111x, against Carroll's single published `R_PICPOC = 0.04245`.
So the anchor is being asked to reproduce a quantity whose observed value spans two orders of
magnitude across the three AOIs with one parameter. That is a stronger statement about the
identifiability of a scalar rain ratio than anything in the bias analysis, and it is measured
rather than inferred.

## What would settle it

The clean test is a third and fourth **anchored** AOI spanning a different community composition,
so the relationship has more than two points. Failing that, the composition question put to Jon is
the decisive one: if Darwin's calcifying set and its `f_lge` are known, the predicted inflation is
computable in advance rather than fitted after the fact.
