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

---

## CORRECTION — TPOSE does not *distribute* dissolved iron (2026-07-28, later)

The update above said TPOSE "publishes dissolved iron" and called the eqpac iron-field check viable.
**That was based on the documentation, not on the file listing.** Checked the actual directory:

`https://ecco.ucsd.edu/DATA/TPOSE/bgc_tp6/` — TPOSE.6-bgc, 2014–2016, monthly, domain **20°S–20°N**:

    CO2flux · DIC · O2 · O2flux · SALT · SSH · THETA · UVEL · VVEL · WVEL · pCO2

**No iron. No nitrate, phosphate, alkalinity or chlorophyll either**, despite all being listed in the
prose. The page notes "additional variables available upon request" — so iron exists in the model
(N-BLING carries it) but obtaining it is an **email to the TPOSE group**, not a download.

There is also a **forward run** at `.../bgc_fwd/` (2004–2019, ERA5-driven). That one is **not
assimilated**, so it is another model rather than an independent constraint, and it must not be used
as external validation.

### What this does and does not unblock

| test | status |
|---|---|
| eqpac **iron** field vs an independent estimate | **blocked** — needs a data request |
| eqpac **carbon** (DIC / pCO₂ / CO₂ flux) vs TPOSE | available now; DIC 372 MB, surface fields 12 MB each |
| Brix Southern-Ocean compensation | **not TPOSE** — its domain stops at 20°S; that test needs B-SOSE |

The carbon comparison is available but **does not test the misspecification prediction**. Today's
`tan φ` measurement already shows the box reproduces DIC and ALK closely (φ < 1.4°) and fails only on
iron (φ = 90°). Comparing carbon would largely confirm the half that already works.

### Honest tally

This is the third time in this scoping that I stated a capability from documentation and had to walk
it back against the artifact: GP15 coverage, BLING comparability, and now TPOSE iron availability.
The pattern is consistent — **prose describes what a system contains; the file listing describes what
you can actually have.** Check the listing.

### The prediction stands, untested

Darwin's equatorial iron differing from an independent estimate remains the falsifiable test of the
model-misspecification reading. It now requires a request to the TPOSE group for the Fe field, or an
alternative independent product. **Recorded as untested rather than quietly dropped.**

---

## CORRECTION 2 — B-SOSE iter105 stops at 29.8°S, verified from the grid file (2026-07-28)

I wrote above that B-SOSE "runs equator to 78°S" and telescopes to 2° at the equator. That came from
the **paper's model description**. The **distributed product** is different.

Downloaded `grid.nc` (427 MB) from `http://sose.ucsd.edu/SO3/ITER105/` and read it:

    dims: NZ=52, NY=294, NX=1080
    YC:  -77.965 .. -29.789        <- stops at 29.8 S, does NOT reach the equator
    XC:    0.167 .. 359.833        <- global in longitude
    lat spacing near -57 S: 0.1676, 0.1685, 0.1693, 0.1702   -> 1/6 deg, as advertised

So for the distributed iter105 BGC solution:

| our AOI | covered by B-SOSE iter105? | resolution |
|---|---|---|
| `southernoceanpac` 65–50°S | **yes** | **1/6°** — genuinely finer than our 1° |
| `eqpac` 5°S–15°N | **no** — not even partially | — |
| `natlsubpolar` 50–65°N | no (Southern Hemisphere product) | — |

The earlier "coarse eqpac sliver from B-SOSE" idea is **dead**. The 2°-at-the-equator telescoping
describes a different/fuller SOSE configuration, not this BGC product.

### What B-SOSE still gives us, and it is worth having

`bsose_i105_2008to2012_monthly_Fe.nc` (**3.8 GB**, downloading) is **dissolved inorganic iron at
1/6° over the Southern Ocean, 2008–2012**, independently assimilated. Overlap with v05 is 5 years.

That is the **control arm**: `southernoceanpac` is where `scav_rat` recovers **49/50**. If Darwin's
Southern Ocean iron agrees with B-SOSE where recovery works, while eqpac's iron cannot be reproduced
by the box at all (`tan φ` = 90°), the misspecification reading gains a matched comparison instead of
resting on eqpac alone.

It is also the product for the **Brix compensation test**, which is about Southern Ocean carbon and
was never a TPOSE question.

### Fourth walk-back, but caught the right way

GP15 coverage, BLING comparability, TPOSE iron, and now B-SOSE extent — four claims taken from prose
that the artifact contradicted. This one I caught **before** writing it up, by opening `grid.nc`
instead of trusting the paper. That is the procedure; it should have been the procedure from the
start.
