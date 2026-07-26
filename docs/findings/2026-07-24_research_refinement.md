# Research refinement — narrative arc, observation-design prescription, paper-readiness (2026-07-24)

Integrates the overnight-session results (see [`2026-07-24_overnight_session_summary.md`](2026-07-24_overnight_session_summary.md))
into the paper's story, consolidates the forward contribution (what to measure), and assesses readiness.
Honesty-tagged; the GHG-Center motivation is from [`ghgcenter_positioning.md`](2026-07-24_ghgcenter_positioning.md).

## 1. The narrative arc as it now stands

**Motivation (refined, honest).** ECCO-Darwin is a NASA-hosted, openly-licensed, carbon-MRV-relevant
data-assimilating BGC model whose stated value rests on a Green's-functions *calibration* of its biological
parameters. A calibration is only as trustworthy as observations constrain the parameters it tuned. The global
multidecadal sink is ~2% biology (Carroll 2022), so identifiability matters not for the headline sink but for
the **credibility of the biological pump's contribution to regional/seasonal flux structure** — the Southern
Ocean, equatorial Pacific, and subpolar-bloom regimes the Carroll-6 were tuned to fix.

**Method.** A differentiable 0-D box surrogate + a per-cell neural predictor, trained by gradient descent
against real observations, with identifiability read from Fisher-information / profile-likelihood geometry.

**Results (the spine):**
1. **The per-cell architecture is load-bearing** — holds the trio {alpfe, scav_rat, R_PICPOC} where a
   global-scalar control holds 0/50 (the surrogate gap is dimensional).
2. **alpfe** recovers near its published value estimator-independently (DINN-free, Nelder-Mead, and EKI all
   agree — closing the "single-method artifact" attack).
3. **R_PICPOC** recovers only with a real calcite anchor (Daniels); anchor-off → 6/50 epoch-matched (4/50 in the 1500-epoch run).
4. **The iron pair is the published FeMIP degeneracy, reframed as sloppiness** — surface-only ill-conditioned
   (cond 3022), subsurface iron breaks it but **basin-dependently** (Southern Ocean cond 2.2; equatorial
   Pacific / North Atlantic stay ratio-degenerate at 35–51).
5. **Identifiability ≠ recoverability, and the gap decomposes** — the recoverability gap is *largely a
   closeable optimization component* (scav_rat 25→41/50 at 4000 epochs, natl 20→40) plus a *residual
   information component* (eqpac 6/50, the sole basin more compute cannot fix). **This is the night's key
   refinement to the central claim.**
6. **diatomgraz** has a non-circular handle (35/50 from Chl+MLD, bSi off) but is in a **structural trade-off**
   with the iron trio (no robust 4-of-4; full+MLD+4000ep → diatomgraz 0/10). The growth pair is
   practically non-identifiable under the time-mean (seasonal opens Smallgrow in strong-bloom basins; Biggrow
   never recovers).
7. **The binding constraint is the observing system, not the method** — leading to a concrete
   observation-design prescription (§2).

**Novelty (narrow, honest):** the *combination* — differentiable surrogate + Fisher geometry + observation
design for a non-differentiable BGC GCM — stated "to our knowledge." Parameter identifiability in marine
models is established (Spitz 1998; FeMIP/Tagliabue 2016); we frame it via sloppiness for a field that measures
the degeneracy but never names it.

## 2. Observation-design prescription — the forward contribution (what to measure next)

For each parameter that real observations do not currently pin, the specific dataset AND the observation
operator that would break its degeneracy. (Datasets from the 2026-07-23 expert review §D; each needs the named
operator, not the raw field.)

| parameter | what breaks it | dataset (ready) | observation operator (the catch) |
|---|---|---|---|
| **scav_rat** (eqpac, the residual info-limit) | an independent iron *scavenging-rate* constraint (concentration alone gives only the S/k ratio) | **Black et al. 2020, GBC** (10.1029/2020GB006592: prior fluxes + 100+ upper-ocean Fe residence-time estimates); GEOTRACES IDP2025 + BODC ²³⁴Th | ²³⁴Th export × matched sinking-particle Fe:²³⁴Th + Fe inventories + advection/non-steady correction; separate authigenic/biogenic Fe from lithogenic. No turnkey product. |
| **R_PICPOC** (Southern Ocean, no Daniels coverage) | a real SO calcite *production* ratio | **Rosengard et al. 2015** (BG 12:3953, Great Calcite Belt, 27 stations, size-fractionated PIC/POC/bSi/²³⁴Th); **Balch et al. 2025** (GBC 10.1029/2024GB008457, Pacific GP19, calcification:photosynthesis rates) | matched **calcification:photosynthesis rate** (production ratio), NOT standing-stock/export (altered by sinking/grazing/dissolution). Satellite PIC is bSi-biased south of the Polar Front — filter or ignore there. |
| **diatomgraz** | independent grazing evidence that does not route through the bSi biomass tautology | **MAREDAT** (diatom biomass); **dilution experiments** incl. SO (Gutiérrez-Rodríguez et al. 2023, L&O Letters 10.1002/lol2.10355) | biomass ≠ palatability; map dilution grazing rates to the dimensionless palatability multiplier through a predator/temperature/functional-response operator. (Our Chl+MLD handle is model-internal, not this.) |
| **Smallgrow / Biggrow** | group-resolved production + the annual cycle | group-specific ¹⁴C/carbon production, bloom timing, MLD, light | ¹⁴C is biomass-weighted realized photosynthesis, not max growth (invert into PCmax; preserve the sign). Some growth/loss params stay inseparable even with seasonality (Spitz 1998) — seasonality helps Smallgrow in strong-bloom basins only. |

**Design principle demonstrated, not asserted:** subsurface iron *sections* (not the global mean the 0-D box
homogenizes) break the surface/depth iron symmetry — verified basin-dependently. The prescription is "measure
the gradient / the rate / the production ratio," because the concentration / standing-stock / biomass fields
are exactly the ones the degeneracies leave unconstrained.

## 3. Paper-readiness assessment
- **Solid and verified (ready):** per-cell load-bearing; alpfe method-independence (+EKI); R_PICPOC anchor
  dependence; iron = FeMIP sloppiness (basin-dependent conditioning); identifiability≠recoverability with the
  optimization/information decomposition; the observation-design prescription; the chlorophyll-vs-MODIS
  regional trust map (novel).
- **Strengthened tonight:** scav_rat optimization-limit (41/50); diatomgraz non-circular handle; the
  structural 4-of-4 trade-off; estimator-independence.
- **Needs your greenlight (core-claim reframes, see summary §10):** retire "box tuning-exhausted / needs new
  obs not GPU" (H1); scav_rat classification (H2); Smallgrow softening (H3); abstract iron/diatomgraz lines
  (H4); add EKI to STATUS validation (H5); qualify the 38/40 headline (H6).
- **Still genuinely open (honest limits):** the surrogate Fisher is not the GCM's (needs the 8-run v05
  perturbation ensemble, #163); eqpac scav_rat is information-limited (needs Black-2020-style ²³⁴Th);
  diatomgraz independent-real-data recovery (dilution experiments), not just the model-internal Chl handle.

## 4. Prioritized to-do (for Lucas)
1. **Decide the H1–H6 core-claim reframes** (single greenlight batch in summary §10) — H1 (optimization is not
   a no-op) is the most consequential and the best-supported.
2. **AGU abstract:** apply the flagged iron/diatomgraz updates (H4), then submit before **Aug 5**. Iron-focused
   version recommended.
3. **Issue tracker:** #187 (scav_rat optimization-limit + EKI), #152 (diatomgraz non-circular), #85 (first
   seasonal), #188 (structural 4-of-4). I can post these on your OK.
4. **results_matrix.md** is stale (2026-07-05 verdict) — refresh to tonight's numbers (S3, held as canonical-doc
   edit).
5. **Highest-EV next experiment** (when you want to push further): the v05 perturbation ensemble (#163) to turn
   the surrogate Fisher into a GCM claim — the recipe is ready and traits-override-safe.
