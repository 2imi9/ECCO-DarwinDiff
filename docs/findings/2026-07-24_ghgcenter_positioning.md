# GHG Center positioning — the honest motivational chain for the identifiability study

Date: 2026-07-24
Scope: refined positioning of DarwinDiff's parameter-identifiability study against the NASA US GHG Center's hosted ECCO-Darwin CO2-flux product. Synthesis of three research briefs (flagship ecosystem, parameter→flux linkage, validation/use-case angles). Every claim tagged; overreaches flagged.

---

## 1. Flagship context (one paragraph)

The US GHG Center (`earth.gov/ghgcenter`) hosts exactly one ocean-carbon product, **"Air-Sea CO2 Flux, ECCO-Darwin Model v5"** (`eccodarwin-co2flux-monthgrid-v5`): a single-variable monthly gridded air-sea CO2 flux at ~1/3 deg equatorial resolution, visualized over Jan 2020–Dec 2022, Cloud-Optimized GeoTIFF via STAC/Raster API, CC-BY-4.0, provided by NASA JPL from the ECCO circulation estimate plus the MIT Darwin ecosystem model (Brix et al. 2015; Carroll et al. 2020 JAMES; page published 2024-09-20) [established]. It is the same ECCO-Darwin v5 model lineage our identifiability study operates on, re-served as a derived product. The center frames it as ocean-carbon-**sink science and data assimilation** — its stated value proposition is that "issues present in the first model were addressed using data assimilation and adjustments were made to initial conditions and biogeochemical parameters," i.e. the v-series improvement is explicitly a parameter/initial-condition **calibration** story [established]. That calibration surface is exactly what our study characterizes. One hop out, the same state estimate is the substrate for emerging ocean-CDR MRV tooling (Suselj et al. 2025 JAMES build an OAE-efficiency framework on ECCO-Darwin), and the broader ECCO/MITgcm lineage underpins the first commercially verified OAE credits (Planetary/Isometric) — establishing the model's policy/MRV relevance without any claim that our work touches those products [established, with lineage caveat below].

Reconciliation note for reviewers: the portal advertises the **2020–2022** COG window; the commonly cited **-2.47 +/- 0.50 Pg C/yr (1995–2017)** time-mean sink is Carroll et al.'s multidecadal validation result, not a statistic of the 3-year visualized stack. Keep them attributed separately so the pairing cannot be called a mismatch [ours-verified].

---

## 2. The honest motivational chain

Why parameter identifiability of **this specific model** matters — stated without claiming we improve the flux:

1. **The hosted product's advertised worth is its calibration.** The GHG Center itself sells v5 as a data-assimilation improvement over the pilot, achieved by adjusting biogeochemical parameters and initial conditions [established]. A calibration is only as trustworthy as the degree to which observations actually constrain the parameters it tuned. Our study grades precisely that: which of the Carroll-6 biological parameters {`alpfe`, `scav_rat`, `R_PICPOC`, `diatomgraz`, growth pair} real observations can pin down [ours-verified].

2. **The global multidecadal sink is NOT biology-limited — so we must not overclaim there.** In ECCO-Darwin's own DIC-budget attribution, the long-term interior DIC increase primarily tracks the anthropogenic growth rate, with biology contributing ~2% (~1.4 Pg C of ~64 Pg C over 1995–2018) (Carroll 2022 GBC) [established]. In the upper 100 m the biological term is large but nearly cancelled by circulation resupply (circulation +6.3, biology -8.6, air-sea +2.6 Pg C/yr; net tendency only +0.3) [established]. And the flux is directly assimilated — Brix 2015 tuned gas-exchange coefficients and DIC/alkalinity/oxygen initial conditions via Green's functions — so even an unidentifiable ecosystem parameter need not corrupt the assimilated global flux [established]. Flux *uncertainty* is dominated upstream by gas-transfer velocity (~20% intrinsic; 44–65% across parameterizations) and pCO2-product choice (8–19% regional), not the ecosystem parameters [established].

3. **Where identifiability genuinely bites: regional and seasonal biological-pump structure.** The reason the six ecosystem parameters were tuned in the first place was regional/seasonal bias — Brix 2015's "exaggerated seasonal and synoptic variability in Southern Ocean air-sea CO2 fluxes," which Carroll 2020's optimization corrected [established]. Higher latitudes carry stronger biological seasonality (subpolar spring blooms); the equatorial Pacific dominates ENSO-driven interannual sink swings [established]. Our observables map straight onto these regimes: `alpfe`/`scav_rat` govern iron-limited HNLC productivity (Southern Ocean, equatorial Pacific), `diatomgraz` sets bloom community structure/timing, `R_PICPOC` sets the carbonate counter-pump's alkalinity partition [ours-verified]. So **where a parameter is unrecoverable, the biological contribution to that region's flux structure carries irreducible a-priori uncertainty** — a statement about the calibration's credibility, not a flux error we measured.

The chain in one line: the product's worth is its calibration → the calibration leans on biological parameters observations constrain unevenly → the unconstrained ones sit in the biological pump, whose leverage is on **regional/seasonal** flux structure, not the headline sink → our study says which parameters those are and what would fix them. We do not fit, correct, or improve the CO2-flux product.

---

## 3. Refined "why it matters" sentences (intro / AGU abstract)

Each honesty-checked; pick per venue.

- **(motivational, tightest)** "ECCO-Darwin's air-sea CO2 flux is a NASA-hosted, openly licensed carbon-cycle product whose stated value rests on a data-assimilation calibration of its biogeochemical parameters; we ask which of those parameters real observations can actually constrain — an identifiability question, not a re-fitting of the flux." [ours-verified]

- **(scoping the leverage honestly)** "The global multidecadal sink is set by assimilated physics, the anthropogenic air-sea gradient, and gas transfer, with biology contributing roughly 2% of the long-term DIC increase (Carroll 2022); parameter identifiability instead bounds the credibility of the biological pump's contribution to regional and seasonal flux structure — the Southern Ocean, equatorial Pacific, and subpolar regimes that ECCO-Darwin's own Green's-function tuning targeted." [ours-verified]

- **(the observing-system payoff)** "Our central result is that the binding constraint on recovering these parameters is the observing system, not the inversion method: we identify which measurements — GEOTRACES iron section gradients, subsurface dissolved iron, a real calcite/rain-ratio anchor — break which degeneracy, turning a calibration audit into a concrete recommendation for what to measure next." [ours-verified]

---

## 4. Concrete, defensible validation/positioning angles

Ranked by defensibility. Each is validation/motivation/observing-system, never "we improved the product."

- **A. Regionalized trust map from two independent obs validations.** v05 surface pCO2 is globally unbiased vs GLODAPv3 (+0.3 uatm; carbonate.py r=1.000 vs GLODAP CO2SYS), while chlorophyll vs MODIS-Aqua is regime-split — within the retrieval noise floor at the equator (-0.076 dex vs 0.130 floor) but ~5x low in the subpolar N. Atlantic bloom (-0.697 dex), bloom ending ~2 months early. Message for an MRV user: the flux-relevant surface field is trustworthy globally, but attributing the sink to **biological** drivers deserves more caution in high-latitude blooms. Chlorophyll is novel — not evaluated in ECCO-Darwin's own white paper [ours-verified].

- **B. Identifiability as an a-priori uncertainty budget on the calibration.** Grade the tuned biological parameters by constraint: `alpfe` method-independent (recovers DINN-free + Nelder-Mead); `scav_rat` the weak leg (25/50 → 41/50 with more optimization, eqpac most degenerate); `R_PICPOC` global value under-constrained and mis-specified vs a regionally variable rain ratio; `diatomgraz` input-limited (35/50 via a non-bSi Chl+MLD handle); growth pair unobservable by construction (`Biggrow`; `Smallgrow` is non-identifiable from time-mean observables only) [ours-verified]. This is an a-priori budget, not a delivered flux-error number.

- **C. Observing-system recommendation (highest-value output for mCDR-MRV).** GEOTRACES **section gradients** (not the global mean) break the iron `alpfe`/`scav_rat` degeneracy; **subsurface** DFe breaks the surface-only ratio degeneracy; a **real calcite anchor** (Daniels CP:PP, MODIS PIC) makes `R_PICPOC` identifiable. These map onto mCDR efficacy monitoring — OIF efficacy hinges on the `alpfe`/`scav_rat` residence-time pair (Tagliabue's FeMIP problem: DFe residence roams 3.7–626 yr while concentration stays pinned at 0.58 +/- 0.14 nM); the PIC:POC rain ratio governs the carbonate counter-pump [ours-verified; the mCDR-efficacy transfer is speculation — see §5].

- **D. R_PICPOC regional mis-specification is a genuine carbon-cycle point.** Carroll's single global `R_PICPOC` (0.0425) is under-constrained, and the real rain ratio is regionally variable (Daniels eqpac ~0.039, ~1.6x the global mean). The rain ratio sets the alkalinity/DIC partition of export, so a global scalar is a known simplification whose regional error is exactly the kind of structural assumption an MRV user should be able to see. Scope: about the parameterization, not a flux error we measured [ours-verified].

- **E. ENSO / equatorial interannual variability.** v05 captures 0.89x the observed ENSO chlorophyll sensitivity at the correct sign, with a ~2-month phase discrepancy (v05 leads Nino-3.4; MODIS lags; n_eff ~14–34). Worth flagging in the region that controls interannual sink swings — as a model–observation phase discrepancy of unestablished cause, not a diagnosed flux defect [ours-verified].

**Overclaims to avoid (hard rules):**
1. We do not fit, correct, or improve the CO2-flux product.
2. Parameter uncertainty is NOT a quantified flux uncertainty here — no forward UOSSE propagates Carroll-6 posteriors to a Pg-C/yr regional sink error. Angle B is a-priori; the parameter→flux magnitude link is qualitative.
3. Do not call the flux product "wrong" in the N. Atlantic — the 5x-low result is a **chlorophyll/biological-state** finding; pCO2, the flux-relevant field, is globally unbiased. Different quantities.
4. We do not validate the flux against independent obs — the GHG Center grid is model output, not an observation; that would be the model validating itself. Our anchors are pCO2 vs GLODAPv3 and chl vs MODIS.
5. No "first global BGC operator" / "beats persistence" / "made Darwin differentiable" claims.
6. mCDR-efficacy relevance is a transfer/analogy argument, not a demonstrated mCDR result.
7. The 2020–2022 GHG grid is NOT data we used — it is non-overlapping (our daily window ends 2018-12-31) and regridded off native LLC270. The motivation is the shared lineage, not that grid.

---

## 5. Adversarial-verify table

| # | Claim | Tag | Verify note / overreach flag |
|---|-------|-----|------------------------------|
| 1 | GHG Center hosts one ocean product, ECCO-Darwin v5 air-sea CO2 flux; ~1/3 deg, monthly, 2020–2022 shown, COG/STAC, CC-BY-4.0 | [established] | **CONFIRMED against the live STAC collections API (2026-07-24): 29 collections total, `eccodarwin-co2flux-monthgrid-v5` is the SOLE ocean/marine one** (all others land/atmosphere/methane/biomass — CASA-GFED, CarbonTracker-CH4, EMIT, EPA, GEDI, mangroves). ECCO-Darwin is the ocean pillar of the center. (Earlier the JS-SPA page returned an empty shell to fetchers; the STAC API resolves it.) |
| 2 | Center frames v5 as DA-improved calibration of BGC parameters + initial conditions | [established] | Direct product-page language. This is the pivot of our motivation. |
| 3 | -2.47 +/- 0.50 Pg C/yr is 1995–2017 multidecadal validation, distinct from the 2020–2022 COG window | [ours-verified] | Reconciliation of two correctly-sourced numbers; keep attributed separately. |
| 4 | Biology ~2% of long-term DIC increase; upper-100m biology term nearly cancelled by circulation | [established] | Carroll 2022 GBC, open access. Load-bearing for "we do not move the headline sink." |
| 5 | Flux is directly assimilated (Brix 2015 GF on gas-exchange coeffs + DIC/ALK/O2 ICs); flux uncertainty dominated by gas transfer + pCO2 product | [established] | Brix 2015 + gas-transfer literature. Supports "unidentifiable param need not corrupt assimilated flux." |
| 6 | Ecosystem params were tuned to fix regional/seasonal (esp. Southern Ocean) bias | [established] | Brix 2015 → Carroll 2020. Where identifiability genuinely bites. |
| 7 | Carroll-6 param roles (alpfe=Fe dust solubility scalar, scav_rat=scavenging, R_PICPOC=rain ratio, diatomgraz=palatability, growth pair) | [established] | From Menemenlis-2019 Table S1 registry; NOT re-confirmed against the paywalled Carroll 2020 PDF. Minor sourcing caveat, not an overreach. |
| 8 | Our recovery grades: alpfe method-independent; scav_rat 25→41/50; diatomgraz 35/50 (Chl+MLD); R_PICPOC needs real calcite anchor; growth pair unobservable | [ours-verified] | STATUS.md + docs/findings/2026-07-2*. Reproducible via verify_run.py gate. |
| 9 | pCO2 globally unbiased +0.3 uatm vs GLODAPv3; chl regime-split (equator OK, N. Atlantic ~5x low, bloom ~2mo early) | [ours-verified] | finding_v05_obs_pco2_baseline; 2026-07-19 chl vs MODIS. Angle A backbone. |
| 10 | Observing system (not method) is the binding constraint; section gradients / subsurface DFe / real calcite anchor break specific degeneracies | [ours-verified] | STATUS.md; Tagliabue 2016; Somes 2021. Central result. |
| 11 | Suselj 2025 builds OAE/mCDR-efficiency tooling ON ECCO-Darwin; explicitly cites MRV | [established] | doi:10.1029/2024MS004847. Bridge is real but one hop out — do not say we contribute to it. |
| 12 | ECCO/MITgcm lineage underpins first verified OAE credits (Planetary/Isometric) | [established, caveat] | Sources say "ECCO/MITgcm," NOT confirmed as the GHG-Center v5 COG product. Frame as lineage, never "our hosted product issued credits." |
| 13 | Same params (alpfe/scav_rat, R_PICPOC) that govern our identifiability also govern OIF efficacy + carbonate counter-pump for mCDR | [speculation] | Transfer/analogy argument. It makes the identifiability map *useful* to mCDR-MRV; it is NOT a quantified mCDR result. Must stay tagged. |
| 14 | Parameter identifiability → a quantified regional flux-error budget in Pg C/yr | [speculation] | NOT done — requires a forward UOSSE not yet run. State as qualitative/a-priori only; the strongest published bound is the ~2% (row 4). Flagged as the single easiest place to overreach. |
| 15 | R_PICPOC regionally variable (Daniels eqpac ~0.039 ~1.6x global 0.0425); global scalar is a known simplification | [ours-verified] | docs/archive/findings/2026-06-26_rainratio_real_vs_darwin.md. About parameterization, not a measured flux error. |
| 16 | ENSO: v05 0.89x observed chl sensitivity, correct sign, ~2mo phase lead | [ours-verified] | STATUS.md, n_eff ~14–34. Report as phase discrepancy of unestablished cause. |

**Biggest overreach risks (do not cross):** rows 13 and 14 — any sentence that quantifies a mCDR intervention or converts parameter posteriors into a flux-error number without the OSSE. Row 12 — attributing verified OAE credits to the hosted product rather than the modeling lineage. Row 3 — pairing the two sink numbers without their separate attributions.

---

## Sources

- US GHG Center — `eccodarwin-co2flux-monthgrid-v5` catalog page + v5 User Notebook / Data Flow / Processing & Verification Report (us-ghg-center.github.io/ghgc-docs); CC-BY-4.0 [established]. See also docs/findings/2026-07-23_data_sources_ghgcenter_earthmover.md.
- Carroll et al. 2020, JAMES, doi:10.1029/2019MS001888; Carroll et al. 2022, GBC (open access, PMC9286438); Brix et al. 2015, Ocean Modelling, doi:10.1016/j.ocemod.2015.07.008 [established].
- Suselj et al. 2025, JAMES, doi:10.1029/2024MS004847 (OAE/mCDR efficiency on ECCO-Darwin) [established]; Isometric / Planetary Technologies first verified OAE credits (ECCO/MITgcm lineage) [established, lineage caveat].
- Gas-transfer velocity uncertainty (Ocean Science 2016, os.copernicus.org/articles/12/1091/2016); SeaFlux (ESSD 2021, essd.copernicus.org/articles/13/4693/2021) [established].
- Tagliabue et al. 2016, GBC, doi:10.1002/2015GB005289; Somes et al. 2021, doi:10.1029/2021GB006948 (FeMIP iron degeneracy); Parekh, Follows & Boyle 2005, GBC (Darwin iron model); Daniels et al. 2018 (CP:PP rain-ratio anchor) [established].
- Identifiability results, R_PICPOC regional mis-specification, observing-system recommendation, ENSO sensitivity: STATUS.md; docs/findings/2026-07-2*; docs/archive/findings/2026-06-26_rainratio_real_vs_darwin.md [ours-verified].
- pCO2 vs GLODAPv3: memory finding_v05_obs_pco2_baseline; chl vs MODIS: docs/findings/2026-07-19_v05_chlorophyll_vs_modis.md, 2026-07-19_eqpac_chlorophyll_vs_modis.md, 2026-07-21_chl_binning_recompute.md [ours-verified].
