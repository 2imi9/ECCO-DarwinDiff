# ECCO-Darwin v06 research (automated, adversarially verified)

> Produced 2026-07-22 by the `ecco-darwin-v06-research` workflow: 6 parallel web-search agents ->
> 16-claim adversarial verify pass -> synthesis (23 agents, ~1.35M tokens). Every factual claim is
> URL-sourced; unverifiable claims are flagged. See also STATUS Track-2 + the covariate experiment.

# ECCO-Darwin v06: Verified Status and Implications for the Parameter-Learner

*Internal research note — 2026-07-22. Every factual claim below is tied to a source URL. Claims I could not verify are called out explicitly in Section 3.*

## 1. Bottom line

**v06 exists, but it is NOT released. It is an actively-developed, code-stage configuration — not a published, evaluated state estimate.** v05 remains the officially published/released solution and the one we should keep targeting.

Two independent authoritative sources establish this:

- **The ECCO-Darwin team lead says so directly.** Hong Zhang (JPL, core developer), replying on the MIT ecco-support list on 2026-02-17: run "Darwin v05 which is optimized/published," while v06 "is still in optimization." (https://mailman.mit.edu/pipermail/ecco-support/2026-February/000832.html)
- **The public data product is still v5.** The NASA GHG Center serves "Air-Sea CO2 Flux, ECCO-Darwin Model v5" as the only ECCO-Darwin collection; no v6 product is listed. (https://earth.gov/ghgcenter/api/stac/collections/eccodarwin-co2flux-monthgrid-v5)

But it is **not a stale placeholder** — it is under active 2026 development. The v06 directory in the canonical repo received commits as recently as 2026-06-04 ("cleanup for v4r6"), plus 2026-05-06 "Update iron dust forcing file" and 2026-04-16 "Use #define DARWIN_ALLOW_CONS." by Dustin Carroll, and the build pins to MITgcm code c69e (2025/05/20). (https://github.com/MITgcm-contrib/ecco_darwin/commits/master/v06)

## 2. What is actually changing vs v05 (sourced only)

### Repo structure
v06 exists as a top-level directory in the canonical MITgcm-contrib/ecco_darwin repo with **two configurations**:
- `/1deg`: 1-degree solution based on ECCO **V4r5** (v05's 1deg used V4r4/V4r5 — so the 1deg physics moves to V4r5).
- `/llc270`: v05 llc270 plus the upgrade stack below.

(https://raw.githubusercontent.com/MITgcm-contrib/ecco_darwin/master/readme.txt)

### Headline llc270 changes over v05 (verbatim from repo README)
"v05 llc270 w/ Darwin upgrades and new ecosystem, BGC runoff, RADI sediment model, pH fix and updated solver, hydrothermal vent iron forcing, and radiative transfer package." (https://github.com/MITgcm-contrib/ecco_darwin)

Broken out:
- New Darwin **ecosystem** model
- **BGC (riverine) runoff**
- **RADI sediment** model
- **pH fix** + updated solver
- **Hydrothermal-vent iron forcing** (new)
- **Radiative-transfer** package

### Grid / resolution
The llc270 config **retains the LLC270 grid** — resolution is NOT increased; the upgrades are all BGC/ecosystem/physics, not grid. (https://github.com/MITgcm-contrib/ecco_darwin)

### Run window
v06 llc270 targets the **1992-2024** period (per `v06/llc270/readme_darwin.txt`), extended vs v05's published coverage. (https://raw.githubusercontent.com/MITgcm-contrib/ecco_darwin/master/v06/llc270/readme_darwin.txt)

### Backend / forcing
Still **Darwin 3** (via `git clone .../darwinproject/darwin3`); latest MITgcm code **c69e (2025/05/20)**; **ERA-XX** (`era_xx_it42_v2`) atmospheric forcing; **OASIM** optics forcing. (https://github.com/MITgcm-contrib/ecco_darwin/blob/master/v06/llc270/readme_darwin.txt)

### The one peer-reviewed piece of the v06 line
The v06 `/1deg` (V4r5, LLC90) lineage is documented in a **published 2026 GMD paper** — Savelli, Carroll, Menemenlis, Lauderdale et al., "Implementing riverine biogeochemical inputs in ECCO-Darwin," Geosci. Model Dev. 19, 867-885, 26 Jan 2026 (DOI 10.5194/gmd-19-867-2026). It introduces the new 1-degree V4r5 ECCO-Darwin with daily riverine runoff (1992-2019) — the concrete manifestation of the "BGC runoff" feature. (https://gmd.copernicus.org/articles/19/867/2026/) First appeared as EGUsphere preprint egusphere-2025-1707 (2025). (https://egusphere.copernicus.org/preprints/2025/egusphere-2025-1707/)

Crucially, **that GMD paper reuses v05-era parameters** — it states it uses "the same initial conditions, parameter settings, and forcings as in Carroll et al. (2020)." So it documents **no revised Carroll-6 values**. (https://gmd.copernicus.org/articles/19/867/2026/)

## 3. What could NOT be verified (honest gaps)

These are real limits of the evidence — do not let downstream summaries overstate v06.

- **No v06 release paper, DOI, or announced release date.** No JAMES/GBC/Biogeosciences paper names or describes "ECCO-Darwin v06." As a named version it exists only in the repo source + readmes, not in a formal publication. No GitHub Release object, no conference abstract using the literal "v06" string.
- **No revised parameter values.** I could NOT extract v06-specific numeric values of `alpfe`, `scav_rat`, `R_PICPOC`, `diatomgraz`, or the growth pair. The raw namelist files (`data.darwin`, `data.gchem`, `data.traits`) returned only header/block fragments on fetch. Whether v06 retunes any Carroll-6 parameter is **unknown from public sources** — those values live in `input_darwin` config files, not a paper.
- **No documented calcite/rain-ratio or coccolithophore revision.** The "new ecosystem" is described only generically. No source states v06 changes the PIC:POC (`R_PICPOC`) formulation. No commit in visible history names "calcite" specifically.
- **The 2024 Carroll "Development Update" deck could not be text-parsed** (binary/image PDF). It likely holds the v06 roadmap but its contents are unverified.
- **"In optimization" is the most recent status word (Feb 2026); no target release date** was found anywhere authoritative.

## 4. Implications for our work

**Near-term: none of our footing moves. Keep building on v05.** v05 is still the published/optimized solution the team itself recommends, and it is the only distributed data product. Our parameter-learner target (Carroll-N / v05, Darwin 3) is unchanged and correct.

**The Carroll-6 set is not invalidated — but v06 adds a new iron pathway that will matter eventually.** v06 introduces **hydrothermal-vent iron forcing** as a third iron input alongside dust solubility (`alpfe`) and scavenging (`scav_rat`). In Darwin3 this is a separate mechanism (vent Fe solubility / He3-scaled flux), not a retuning of `alpfe`. Implication: the iron-cycle identifiability picture we've mapped (the alpfe/scav_rat degeneracy, the native-vs-1° iron-pair selection) is defined on a **two-source** iron budget. A v06 with a third, spatially-structured (vent-located, deep) iron source could **change the iron covariate structure** and potentially break or shift the alpfe/scav_rat degeneracy — because a deep, geographically-fixed source adds spatial information the 0-D box currently homogenizes away. This is the single most relevant v06 change for our identifiability story. It is a **future** consideration, not an action item now.

**The covariate/environment experiment: v06 broadens the environment, in the direction our findings already point.** v06 adds riverine BGC runoff (coastal nutrient/DOM forcing), RADI sediment/benthic return fluxes, and a radiative-transfer package (spectral light → chlorophyll/bloom timing). Our own results already say identifiability comes from **real absolute spatial anchors** and that the surrogate gap is dimensional. v06's new environmental drivers (rivers, sediments, spectral optics) are exactly the kind of spatial-structure covariates that could sharpen — or complicate — which parameters are recoverable. Notably the radtrans/OASIM optics coupling is the machinery for ocean-color/PACE assimilation, which connects to our shelved satellite-anchor line.

**What does NOT change which parameters matter (as far as we can verify):** there is no evidence v06 retunes Carroll-6 values or revises the rain-ratio/calcite closure. So our current parameter framing, denominators, and the `R_PICPOC`-via-real-calcite-anchor result stand. Any claim that "v06 changes the parameters" would be **unsupported** — the config files may differ, but nothing public confirms it.

**Recommended posture:** stay on v05 as the release target; treat v06 as a monitored moving target. The two things worth watching for a future re-baseline are (1) whether a v06 evaluation/release paper appears with retuned parameters, and (2) how hydrothermal-vent iron + riverine forcing reshape the iron and coastal-nutrient covariate structure our identifiability results depend on.

---
**Key sources:** ecco-support list, Zhang 2026-02-17 (https://mailman.mit.edu/pipermail/ecco-support/2026-February/000832.html) · repo README/readme.txt (https://github.com/MITgcm-contrib/ecco_darwin) · v06 llc270 readme_darwin.txt (https://raw.githubusercontent.com/MITgcm-contrib/ecco_darwin/master/v06/llc270/readme_darwin.txt) · v06 commit history (https://github.com/MITgcm-contrib/ecco_darwin/commits/master/v06) · GHG Center v5 collection (https://earth.gov/ghgcenter/api/stac/collections/eccodarwin-co2flux-monthgrid-v5) · Savelli et al. 2026 GMD (https://gmd.copernicus.org/articles/19/867/2026/) · EGUsphere preprint (https://egusphere.copernicus.org/preprints/2025/egusphere-2025-1707/)