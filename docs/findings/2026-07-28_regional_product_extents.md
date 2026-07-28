# B-SOSE / TPOSE extents and access — and a resolution claim I got wrong

**Date:** 2026-07-28 · **Loop Q2b** · **Refines:** `2026-07-27_independent_validation_scope.md`

## Verified this session

**B-SOSE** — [Verdy & Mazloff 2017, *JGR Oceans*](https://doi.org/10.1002/2016JC012650),
solution pages at [ecco.ucsd.edu](https://ecco.ucsd.edu/BSOSE_iter105_solution.html) and
[sose.ucsd.edu](http://sose.ucsd.edu/bsose_solution_Iter105.html).

- Domain: **equator to 78°S** — *broader than the "Southern Ocean" label implies.*
- Grid: Mercator poleward of 30°S (Δy = Δx); **equatorward of 30°S the meridional spacing
  telescopes out to Δy = 2° at the equator.**
- Access: THREDDS; iteration **105** confirmed published. Iteration 134 **not** confirmed.

**TPOSE** — [ecco.ucsd.edu/tpose.html](https://ecco.ucsd.edu/tpose.html),
[Verdy et al. 2017, *JTECH*](https://journals.ametsoc.org/view/journals/atot/34/7/jtech-d-16-0223.1.xml),
[Verdy et al. 2023, *JGR Oceans*](https://doi.org/10.1029/2022JC019576).

- Domain: entire tropical Pacific; 2010–2019.
- Resolution: **1/3° nominal**, with some 1/6° configurations.
- Access: NetCDF, publicly available at [ecco.ucsd.edu/tropac.html](http://www.ecco.ucsd.edu/tropac.html).
- TAO moorings were **withheld** for cross-validation — useful precedent for our own held-out design.

**ASTE-BGC** — extent still unverified. Next iteration.

## Coverage against our AOIs

| our AOI | product | covered? | resolution there |
|---|---|---|---|
| `southernoceanpac` 65–50°S | **B-SOSE** | **yes** | Mercator, fine — genuinely higher than our 1° |
| `eqpac` 5°S–15°N | **TPOSE** | **yes** | 1/3° (not 1/6°) — still finer than 1° |
| `eqpac` southern half only (5°S–0°) | B-SOSE | partial | **≈2°, COARSER than our 1°** |
| `natlsubpolar` 50–65°N | ASTE-BGC | unverified | unverified |

## The correction

My scoping note said all three products sit "at higher resolution" than our 1° grid. That is **not
uniformly true**:

- **B-SOSE's headline 1/6° is a poleward figure.** Its grid telescopes to **2° at the equator**, so
  any B-SOSE comparison in the tropics would be *coarser* than what we already have. B-SOSE is the
  right tool for `southernoceanpac` and the wrong one for `eqpac`.
- **TPOSE is 1/3° nominal**, not the 1/6° quoted on Carroll's 2024 slide. Still finer than ours, but
  the slide's figure should not be quoted as-is.

Neither changes the design; both change which product answers which question, and one of them
(B-SOSE at the equator) would have silently degraded the comparison.

## Where this leaves the route

The **Brix compensation test remains the strongest live item**: B-SOSE carries no global carbon
target, covers `southernoceanpac` at genuinely fine resolution, and can discriminate whether
Darwin's Southern Ocean bias matches the compensation Brix describes. That test is unaffected by
today's corrections and unaffected by the BLING parameter-incomparability finding, since it is a
**field** comparison.

## Still open

- ASTE-BGC extent and access.
- Whether B-SOSE iteration 134 exists (only 105 confirmed).
- Whether TPOSE's BGC fields include dissolved Fe at all — BLING carries Fe, but which variables are
  *published* per product is unverified.
