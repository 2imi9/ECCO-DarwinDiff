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

---

## Update — TPOSE publishes dissolved iron (loop Q2c)

**Verified 2026-07-28.** TPOSE is coupled to **N-BLING** (the nitrogen-enabled BLING variant, not
plain BLING), and its published output includes **dissolved inorganic carbon, alkalinity, oxygen,
nitrate, phosphate, iron, and chlorophyll**
([ecco.ucsd.edu/tpose.html](https://ecco.ucsd.edu/tpose.html)).

**This is the first unambiguously positive result in the independent-validation scoping.** It means
the iron *field* comparison is viable in the one basin that matters most:

| requirement | status |
|---|---|
| covers `eqpac` (5°S–15°N, 160–110°W) | **yes**, whole tropical Pacific |
| finer than our 1° grid | **yes**, 1/3° |
| publishes dissolved Fe | **yes** |
| overlaps v05 daily (ends 2018-12-31) | **yes**, 2010–2019 → ~9 yr |
| independent BGC model | **yes**, N-BLING not Darwin |

`eqpac` is where `scav_rat` recovers only 7/50 and stays at 6/50 even at 4000 epochs. An independent
estimate of the dissolved-Fe *field* there is exactly the external check that distinguishes "Darwin's
iron is right and our surrogate cannot recover it" from "Darwin's iron is itself unconstrained".

**Caveat that must be carried:** N-BLING's iron cycle is ligand-mediated and structurally different
from Darwin's (see `2026-07-28_bling_comparability.md`). Agreement or disagreement in the *field*
is interpretable; nothing about the *parameters* transfers.

**Prior art surfaced and worth reading:**
[Tagliabue et al. 2016, *GBC*](https://doi.org/10.1002/2015gb005289) — *"How well do global ocean
biogeochemistry models simulate dissolved iron distributions?"* A multi-model intercomparison of
exactly the field we would be comparing. Read before framing any Fe-field result as novel.

**Revised next step for the independent-validation route:** TPOSE dissolved Fe vs Darwin v05 DFe over
`eqpac`, 2010–2018. That is a concrete, bounded, download-and-compare experiment — and unlike the
Po/Pb route it needs no new observations at all.
