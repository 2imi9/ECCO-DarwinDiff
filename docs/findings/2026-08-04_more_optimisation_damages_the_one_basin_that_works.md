# More optimisation damages the one basin where `scav_rat` actually works — and the metric cannot see it

**Date:** 2026-08-04 · **Job:** 258713 · **All 50 tasks rc=0; four cells of a 2×2 at n=100 each,
plus per-width nulls, in ONE submission** · **Status: corrects the standing "`scav_rat` is
optimisation-limited, not information-limited" claim.**

## What was being tested

The width result was retracted on 2026-08-03 as a pooling artifact. That left one lever standing:
**epochs**. The project's claim that `scav_rat` is *optimisation-limited rather than
information-limited* rests on 2000 → 4000 epochs raising it 25/50 → 41/50 on identical data —
carried in CLAUDE.md, in the manuscript, and in four research-map rows (`ind342`, `ind345`,
`ind353`, `ind354`).

That number was measured on the **arithmetic** per-AOI pooler, which is now known to inflate with
per-cell dispersion. This job runs the full 2×2 — width {16, 39} × epochs {2000, 4000} — with all
four cells in one submission, and grades every cell under all three poolers recorded in the
artifacts.

## The counts disagree about direction

`scav_rat` per-AOI ≥2-of-3, n=100 per cell:

| cell | arithmetic | geometric | median | natl `log_sd` |
|---|---|---|---|---|
| w16 · 2000 ep *(flagship)* | 48 | 19 | 39 | 0.936 |
| w39 · 2000 ep | 75 | 21 | 28 | 0.979 |
| w16 · 4000 ep | 85 | 28 | 33 | 0.871 |
| w39 · 4000 ep | **90** | **38** | **14** | 0.978 |

| contrast | arithmetic | geometric | median |
|---|---|---|---|
| epochs 2k→4k @ w16 | 48→85, **P = 3.8e-08** | 19→28, P = 0.182 | 39→33, P = 0.462 |
| width 16→39 @ 2k | 48→75, **P = 1.4e-04** | 19→21, P = 0.860 | 39→28, P = 0.134 |
| **both levers** | 48→90, **P = 9.9e-11** | 19→38, P = 4.6e-03 | 39→**14**, **P = 9.8e-05 (WORSE)** |

Applying both levers is **significantly better** under the arithmetic pooler and **significantly
worse** under the median pooler, on the same fits. A quantity whose three collapses disagree in
sign is not a well-defined effect.

## But the accuracy tells a consistent story once you ask per basin

Counts are nonlinear in the estimate, so the continuous measure is the honest one. Median
|relative error| in `scav_rat`, Mann-Whitney against the flagship cell:

**North Atlantic — improves, but only under two of three poolers**

| pooler | w16·2k | w39·4k | verdict |
|---|---|---|---|
| arithmetic | 0.4126 | 0.2149 | better, P = 1.5e-21 |
| geometric | 0.5616 | 0.4952 | better, P = 1.3e-12 |
| median | 0.4234 | 0.4640 | **worse**, P = 1.4e-08 |

The geometric centre genuinely improves, so this is not *purely* dispersion. But the median cell
moves the other way, so the direction is pooler-dependent and the gain cannot be stated robustly.

**Southern Ocean — degrades, under every pooler, overwhelmingly**

| pooler | w16·2k | w16·4k (epochs alone) | w39·4k (both) |
|---|---|---|---|
| arithmetic | 0.0511 | 0.0896 — **1.75×**, P = 1.5e-06 | 0.2631 — **5.14×**, P = 4.6e-29 |
| geometric | 0.1148 | 0.1600 — **1.39×**, P = 1.6e-09 | 0.3099 — **2.70×**, P = 4.1e-29 |
| median | 0.0648 | 0.1116 — **1.72×**, P = 8.6e-04 | 0.3136 — **4.84×**, P = 2.3e-23 |

**All three poolers agree.** More optimisation makes the Southern Ocean worse, and 4000 epochs
alone already costs ~1.4–1.75×.

## Why nobody noticed: the reported count is blind here

The Southern Ocean per-AOI leg, at the reported 0.40 band:

| cell | SO leg | SO accuracy |
|---|---|---|
| w16 · 2k | 99/100 | 0.0511 |
| w16 · 4k | 96/100 | 0.0896 (1.75× worse) |
| w39 · 4k | 90/100 | 0.2631 (5.14× worse) |

A **5× accuracy loss** registers as **9 seeds**, because the Southern Ocean sits far inside a 40%
band and has enormous headroom. CLAUDE.md records the 4000-epoch result as "natl 20→40, SO 49→48,
eqpac 7→6" — that SO 49→48 is one seed, and it is hiding a 1.75× degradation.

## The correction

**`scav_rat` is not shown to be optimisation-limited.** What more optimisation actually does is a
**trade**, and it goes the wrong way:

- it buys a **pooler-dependent** improvement in `natlsubpolar`, a basin where `scav_rat` has never
  been established as identifiable against its own null;
- it pays with a **pooler-invariant** degradation in `southernoceanpac`, the **one basin where
  `scav_rat` is established** — 30/50 against an untrained 0/50, P = 3.15e-24, from GEOTRACES iron
  alone with nothing to pool from;
- `eqpac` is unmoved under every pooler (0.676 → 0.630), consistent with every other experiment.

So the 25 → 41/50 headline is not evidence that the parameter becomes better determined. It is
evidence that the arithmetic count rewards moving probability mass across a threshold in one basin
while ignoring accuracy loss in another.

## What to change

1. **Do not cite 4000 epochs as evidence that `scav_rat` is optimisation-limited.** `ind342`,
   `ind345`, `ind353`, `ind354` and the CLAUDE.md bullet all need this caveat.
2. **Keep the flagship at width 16 / 2000 epochs.** It is the best cell in the 2×2 for the
   Southern Ocean under all three poolers, and the SO leg is the only `scav_rat` result with an
   established null.
3. **Report per-basin accuracy, not just the majority count**, whenever a lever is claimed to
   help — the count has now been shown blind in one direction (Southern Ocean headroom) and
   hypersensitive in the other (North Atlantic band edge).
4. The nulls behave: `scav_rat` untrained is **0/50 at both widths under both poolers**, so none
   of the above is null contamination.
