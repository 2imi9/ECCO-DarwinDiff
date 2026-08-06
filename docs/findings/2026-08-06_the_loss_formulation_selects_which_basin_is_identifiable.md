# The loss formulation selects which basin identifies `scav_rat`, and it is a trade

**Date:** 2026-08-06 · **Job:** 288619 (`dd-bxl`, 45 tasks) + 288620 (auto-graded, `afterany`) ·
**Artifacts:** `/scratch/qi_zim_neu/bxl/{eq,na,so}_{end,mean,null}` · **Design:** 3 basins ×
{endpoint, time-mean}, **single-AOI**, each against its own untrained null, n=50 per arm ·
**Config:** `flagship_geo1.sh` sourced, six-value assert · `verify_run` exit 0.

**Verdict: the endpoint-vs-time-mean choice does not improve or degrade the fit — it SELECTS WHICH
BASIN identifies `scav_rat`, and you cannot have both. Single-AOI, at the 0.40 band, all three
collapses: the equatorial Pacific goes 1/50 → 50/50 when the loss is switched to a time mean, and
the Southern Ocean goes 49/43/46 → 0/0/0 over the same switch. This is NOT a joint-fit artifact —
each basin was fitted alone, so there is no shared network, no weighting, and no gradient
competition to blame.**

## 1. The measurement

`scav_rat`, per basin, single-AOI, band 0.40, arithmetic / geometric / median, against that
basin's own untrained null:

| basin | endpoint loss | time-mean loss |
|---|---|---|
| eqpac | **1 / 1 / 1** | **50 / 50 / 50** |
| natlsubpolar | 0 / 0 / 1 | 3 / 3 / 3 |
| southernoceanpac | **49 / 43 / 46** | **0 / 0 / 0** |

`alpfe` for context — it recovers under both losses everywhere, and improves slightly under the
time mean (eqpac 47→50, natlsubpolar 45→50, southernoceanpac 50→50):

| basin | endpoint | time-mean |
|---|---|---|
| eqpac | 47 / 47 / 47 | 50 / 50 / 50 |
| natlsubpolar | 45 / 45 / 44 | 50 / 50 / 50 |
| southernoceanpac | 50 / 50 / 50 | 50 / 50 / 50 |

Median recovered values as a multiple of Carroll, showing the swap is in the VALUE and not only
in the count:

| arm | `alpfe` | `scav_rat` | `R_PICPOC` |
|---|---|---|---|
| eq_end | 0.917 | **0.322** | 1.276 |
| eq_mean | 1.069 | **0.751** | 1.417 |
| na_end | 0.837 | 0.068 | 1.240 |
| na_mean | 1.072 | 0.407 | 1.097 |
| so_end | 1.075 | **0.623** | 11.559 |
| so_mean | 0.642 | **2.078** | 17.352 |
| *any null* | 0.539 | 2.45 | 17.87 |

The Southern Ocean under the time-mean loss lands at `scav_rat` 2.078x against a null of 2.452x —
it has barely moved from untrained. The equatorial Pacific under the endpoint loss lands at 0.322x,
well past the band's lower edge. Each basin is identified under exactly one of the two losses.

## 2. Why this kills the joint-fit explanation

The joint runs (287072/287277) showed the relocation and left an obvious alternative: three basins
share one network and one optimiser at weights 1/2/2, so natlsubpolar and southernoceanpac might
be collapsing because eqpac wins a gradient competition rather than because of anything about the
basins.

**Single-AOI removes that entirely** — one basin, one network, one loss — and the pattern is
unchanged. eqpac still goes 1 → 50 and southernoceanpac still goes 49 → 0. The selection is a
property of the basin crossed with the loss, not of the joint fit.

natlsubpolar is the partial exception and is worth stating separately: alone it *improves* under
the time mean (0/50 → 3/50, median 0.068x → 0.407x, moving toward the band from below) where in
the joint fit it collapsed toward untrained. So natlsubpolar's joint-fit collapse **does** have a
joint-fit component. It just never recovers `scav_rat` under either loss on its own.

## 3. The uncomfortable reading

The endpoint loss compares the model's instantaneous state at day 50 to a **time-averaged** Darwin
target. Those are different objects in the time dimension. The time-mean loss makes them the same
kind of object. On dimensional grounds the time-mean comparison is the defensible one.

If that is right, then the direction of the trade matters enormously: **the established Southern
Ocean `scav_rat` result — the project's one regional identifiability claim — is obtained under the
dimensionally-wrong comparison and vanishes under the corrected one, while the equatorial Pacific
does the reverse.**

That is a hypothesis, not a conclusion, and the honest statement of the alternatives is:

- **(a) The correction is right.** `scav_rat` is identifiable in the equatorial Pacific, the basin
  with twice the iron data (26/28 bins vs 13/14), and the Southern Ocean result was an artifact of
  the endpoint/time-mean mismatch.
- **(b) The correction introduces its own error.** A time mean over 0–50 days of a trajectory that
  has not converged is not the same object as a Darwin climatological mean either, and the eqpac
  result is the artifact.
- **(c) Both losses are wrong in different ways** and each happens to be least wrong in one basin.

Nothing here distinguishes them. What is now established is that **the choice is load-bearing and
was never made deliberately** — the endpoint comparison was inherited, not chosen, and every
published `scav_rat` number rests on it.

## 4. What is solid

- **Replication.** The eqpac time-mean result is replicated across three independent submissions
  now: joint 287072, joint 287277 (disjoint seeds), and single-AOI 288619. The Southern Ocean
  endpoint result is reproduced here too (49/43/46 single-AOI).
- **Pooler invariance.** Both headline cells are identical under all three collapses (50/50/50 and
  0/0/0). The swap is not a collapse artifact.
- **Nulls.** Every arm has its own architecture-matched untrained null, and all three nulls agree
  (`scav_rat` 2.45x, `alpfe` 0.539x), as they must, since an untrained head does not depend on the
  loss.
- **`R_PICPOC` in the Southern Ocean is 0/50 under both losses**, which is expected and is a
  control working: the Daniels calcite anchor has **zero** coverage in that AOI.

## 5. What is not

- **One submission for the swap.** The eqpac half is replicated; the Southern Ocean destruction
  (49 → 0) is measured once.
- **No mechanism.** Two candidate mechanisms have now been tested and refuted — vertical iron
  structure, and endpoint-vs-time-mean distance per basin (the basins are indistinguishable at
  0.365–0.396, and natlsubpolar has the largest gap while behaving worst). Why the equatorial
  Pacific prefers one comparison and the Southern Ocean the other is unknown.
- **`R_PICPOC` degrades in eqpac under the time mean** (43/50 → 21/50 arithmetic), which no
  explanation here covers.

## 6. What this changes

The manuscript cannot describe `scav_rat` as "regionally identifiable in the Southern Ocean"
without stating that the claim is conditional on a comparison choice that was never deliberately
made, and that the opposite choice moves the identifiability to a different basin. That is true
whichever of (a)/(b)/(c) turns out to hold.

The next experiment is not another basin. It is deciding **which comparison is correct**, and the
cleanest route is a self-twin: generate the target from the box itself under a known parameter set,
using the same time-averaging the real target uses, and see which loss recovers the truth. A twin
has no forward-model misspecification, so it isolates the comparison question completely — and it
needs no new observations.
