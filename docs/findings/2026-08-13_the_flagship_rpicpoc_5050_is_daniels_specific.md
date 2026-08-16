# The flagship's `R_PICPOC` 50/50 is Daniels-specific, and the Southern Ocean leg was passing because it was unmeasured

**Date:** 2026-08-13 · **Jobs:** 356756 (3 arms × 50 seeds) + 356757 (grading, chained) ·
**Gate:** `verify_run` **exit 0** on both trained arms, 50/50 seeds each

An A/B of the rain-ratio anchor on the **3-AOI flagship**: Daniels 2018 (the compilation every
published `R_PICPOC` number uses) against Marsh 2025 (its direct successor, expanding the same
Poulton 2018 isotopic-tracer database). One shared untrained null, since a null at `lr = 0` is
independent of loss-side levers.

Cell counts confirmed from the artifacts: Daniels `{eqpac 34, natl 26, sopac 0}`, Marsh
`{34, 33, 12}`.

## Headline: the successor compilation makes the headline number worse

Per-AOI ≥2-of-3, n=50 each, against the shared null:

| parameter | Daniels (control) | Marsh | Fisher |
|---|---|---|---|
| **`R_PICPOC`** | **50/50** | **30/50** | **1.8e-07** |
| `scav_rat` | 26/50 | 18/50 | 0.158 |
| `alpfe` | 49/50 | 48/50 | 1.000 |
| `diatomgraz` | 2/50 | 4/50 | 0.678 |

`R_PICPOC` falls from a perfect 50/50 to 30/50, decisively (P = 1.8e-07). **The flagship's
`R_PICPOC` result is specific to the Daniels compilation.**

That is a limitation the manuscript must state, because the naive reading — "more and better data
should help" — is exactly backwards here.

## Why, and this is the interesting part

The count grades agreement with **Carroll's global constant**, not with the observations. So the
right question is not "did recovery get worse" but "where did the estimate move". Median recovered
`R_PICPOC` relative to Carroll (median collapse):

| AOI | Daniels | Marsh | cells (Daniels → Marsh) |
|---|---|---|---|
| eqpac | 1.25× | **1.04×** | 34 → 34 |
| natlsubpolar | 1.15× | 1.35× | 26 → 33 |
| **southernoceanpac** | **1.17×** | **1.57×** | **0 → 12** |

Three things fall out, and they point the same way.

**1. Where the data is the same, Marsh is better.** eqpac has an *identical* 34 cells in both arms,
and the recovered value moves from 1.25× to **1.04× Carroll** — nearly exact. Same coverage,
different values, much better agreement. Marsh's equatorial Pacific numbers are an improvement.

**2. Where Marsh adds data, the estimate moves away from Carroll.** natl gains 7 cells (26 → 33)
and moves 1.15× → 1.35×.

**3. The Southern Ocean is the decisive case.** With Daniels it has **zero cells**, so its 1.17×
is **inherited through the shared DINN, not measured** — and it *passes* the ±40% band. Give it 12
real observations and it moves to **1.57×**, and its leg reads **0/50 under every collapse**.

**So the Southern Ocean leg was passing precisely because nothing was measuring it.** The inherited
value sat near Carroll because the other basins pulled it there; the moment real local data arrives,
the basin disagrees with the global constant.

## What this confirms, from a new direction

This is independent support for `ind247` / `ded86` — *"Carroll's single global `R_PICPOC` is
under-constrained and mis-specified against a regionally variable rain ratio."* Previously that
rested largely on our own cached comparisons. Here it falls out of a controlled A/B: fit a single
global constant to three basins, give one of them real data for the first time, and that basin
refuses the constant.

The regional spread in the Marsh arm (1.04× / 1.35× / 1.57×) is itself the regional variability the
claim asserts.

## Honest limits

1. **This does not retract the published 50/50.** That number is correct *for the Daniels anchor*,
   which is what it was always computed against. What changes is that it must be reported as
   anchor-conditional, exactly as `R_PICPOC` is already reported as anchor-*dependent*
   (anchor-off → 6/50).
2. **It does not establish that Marsh is "right".** Where coverage is identical (eqpac) Marsh agrees
   with Carroll far better, which is evidence for it; where it adds coverage, it disagrees. Both are
   consistent with regional variability *and* with a compilation difference. Distinguishing them
   needs work this run did not do.
3. **The `scav_rat` drop (26 → 18) is not significant** (P = 0.158) and must not be reported as an
   effect. Its direction matches the single-AOI finding that a calcite anchor costs `scav_rat`, but
   at this n it is indistinguishable from noise.
4. **`alpfe` is unaffected** (49 → 48), as expected — it does not touch the calcite anchor.
5. The Marsh arm's `verify_run` raised a `RARE_EVENT` flag (a seed at ≥5/6) and larger straddle
   warnings than the control (`R_PICPOC` 17/50 seeds straddling, versus none flagged for the
   control). Both are reasons to read the per-AOI column only, which is what is quoted above.

## Consequence

- Report `R_PICPOC` 50/50 as **Daniels-conditional**, alongside the anchor-off 6/50 control.
- `ind330` ("the SO leg is inherited") is **confirmed and sharpened**: not only is it inherited, but
  *its passing grade depended on being inherited*. Measuring it makes it fail.
- The regional mis-specification claim gains a controlled experiment instead of a comparison.
