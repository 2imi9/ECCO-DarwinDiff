# Expert review — corrections + action plan (2026-07-23)

A domain-expert review (with real data pointers) of the identifiability findings and the bottleneck
questions. Logged here as the canonical to-do. Grouped by whether it changes the *science*, the
*validation plan*, or the *data strategy*. Points that change a claim are marked **[CLAIM FIX]**.

## A. Iron degeneracy — the algebra was stated wrong **[CLAIM FIX]**

- At steady state `C ≈ S/k`, so [DFe] constrains a **source-to-loss RATIO (alpfe/scav_rat = S/k), NOT a
  product** (alpfe × scav_rat). I wrote "combination/product" — wrong. Holding C fixed raises source AND
  loss together → the sloppy direction is **(+alpfe, +scav_rat) co-varying** (positive in log space).
- **The eigenvector computation (job 187666) then refuted my *whole* strong-degeneracy claim, and this is
  the real finding:** the surf+sub realiron GN-Fisher 2×2 {alpfe, scav_rat} is **WELL-CONDITIONED
  (cond 2.2)** with a **weak conditional correlation −0.155**, and its sloppy eigenvector is **alpfe-dominated
  (+0.98 alpfe, −0.20 scav_rat)** — not a clean co-varying ratio direction. So with the ACTUAL data (GEOTRACES
  surface AND ~13 subsurface bins/AOI), the alpfe/scav_rat pair is **largely separated, not strongly
  degenerate.** The strong degeneracy (conditional +0.999) is a **SURFACE-ONLY** phenomenon (the obs-design
  subagent's base was surface [DFe] alone); the **−0.77 I led with is the full-6 MARGINAL, inflated by
  coupling to the biology params, not the pure iron-pair number.**
- **Why:** subsurface [DFe] adds depth structure that breaks the surface source / depth-dependent sink
  symmetry (alpfe injects at the surface; scav_rat acts on the particle field with depth) — exactly the
  expert's Q3 point, and consistent with the observation-design finding that a subsurface [DFe] profile is a
  strong symmetry-breaker. **Corrected claim: surface [DFe] alone → strong alpfe/scav_rat degeneracy; adding
  subsurface [DFe] (as the real loss does) largely resolves it (cond 2.2). scav_rat's poor RECOVERY is then
  an optimization/coverage limit (identifiability ≠ recoverability), NOT a hard information degeneracy.**
- **CONFIRMED quantitatively (gap-fill job 188077, both runs reproducible):** GN-Fisher realiron, subsurface OFF
  vs ON. **Surface-only** (`GEOTRACES_SUB_W=0`): 2×2 condition **3022**, conditional corr **+0.999**, sloppy
  direction **co-varying (alpfe +0.64, scav_rat +0.77) = the S/k RATIO** (exactly the expert's algebra).
  **Surf+sub**: condition **2.2**, conditional **−0.155**, sloppy alpfe-dominated (+0.98, −0.20). So subsurface
  [DFe] improves the alpfe/scav_rat conditioning **~1400×** (3022→2.2), matching the observation-design number
  (the subsurface profile IS the symmetry-breaker). The strong degeneracy is unambiguously **surface-only**.
  Whether the conditioning gain yields improved scav_rat RECOVERY is under test (gap-fill job 188074).
- **A negative marginal correlation does NOT establish a product degeneracy** (it can arise from
  conditioning/transforms). And raw CRLBs 68 vs 78 are comparable only after nondimensionalization —
  use the eigenspectrum/profile, not the diagonal (already conceded; reiterated).
- **Frants (2016) is a partial match, not an identity.** Frants describes compensation from *overlapping
  effective* sources/sinks AND notes **spatial gradients can separate them** — not an exact algebraic
  identity. Cite it as "consistent with," not "the published result."
- **Steady-state caveat [CLAIM FIX]:** "concentration constrains only the ratio" holds for the
  steady-state projection. **Seasonal dFe inventories** under changing dust/mixing/production carry rate
  information through phase and relaxation timescales (Sedwick et al. 2023 GRL 10.1029/2022GL102594;
  Mtshali et al. 2019 GRL 10.1029/2018GL081355). So the degeneracy is **practical under steady-state
  concentration data**, NOT proven structural — repeat with time-resolved dFe before saying "structural."

## B. The surrogate is structurally MISSPECIFIED for silica **[CLAIM FIX]**

- **v05 already carries prognostic dissolved SiO₂**, applies Si limitation, cycles diatoms, and assimilated
  silicate (Carroll 2022). The missing-Si is in **our reduced 0-D box**, not the model. So:
  - The **circularity** of the bSi diagnostic is a surrogate artifact (the box back-solves bSi from its own
    diatom biomass). But — **[CORRECTED by the box-silica prototype, `2026-07-23_box_silica_feasibility.md`]**
    adding prognostic SiO₂ does NOT make diatomgraz identifiable. With growth fixed, prognostic-SiO₂ and the
    circular-bSi arm self-recover diatomgraz identically (0.829 vs 0.830); with growth marginalized, both
    show the SAME growth–grazing compensation ridge (rel_span 3.36 vs 3.31) — Si is at **parity**, because
    steady SiO₂/bSi is set by the diatom turnover flux and constrains diatomgraz only in COMBINATION with
    biomass (the channel we already use). So my "add SiO₂ → removes the rank deficiency" was itself
    overstated.
  - **Action (correctly scoped):** add prognostic SiO₂ + Si-limitation (~40 lines, new 17-tracer step; the
    IC is already in the Darwin pickup — SiO₂ record 6, POSi record 15 — so a 2-line load; but it invalidates
    all 15-tracer IC caches and forces a full recovery re-run). Sell it as a **DEFENSIBILITY win** — retires
    the reviewer M11 circularity criticism and unlocks ~630× more real observations (≈6,968 GLODAP silicate
    bottles vs 11 bSi) — **NOT** as a diatomgraz-identifiability fix. **diatomgraz stays non-identifiable on
    real data** (the growth–grazing ridge is the true obstacle; #152 stays open).
- **diatomgraz is a dimensionless palatability MULTIPLIER** on predator–prey interaction, not a realized
  grazing rate. Dilution-experiment grazing rates map to it only through a predator/temperature/
  functional-response observation operator.

## C. The surrogate→GCM validation plan — real gotchas **[all VALIDATION-PLAN]**

- **Pleiades was decommissioned 2026-01-07.** Target systems are Athena / Aitken / Electra. Benchmark one
  baseline + one perturbation on the current system before budgeting.
- **traits-override gotcha (critical):** runtime `data.traits` OVERRIDES generated R_PICPOC/PALAT/PCMAX, so
  a v05 ensemble that perturbs `val_R_PICPOC`/growth/palatability will **silently do nothing** unless the
  *loaded trait entries* are perturbed and verified in the startup output. (darwin_init_fixed.F precedence;
  v05 input/data.traits.)
- **Carroll's perturbation runs are unsuitable as local derivatives:** v4-era, mostly ONE-SIDED, and the
  scavenging perturbation is **+500%** (far too large for a local derivative near the v05 optimum — a
  nonlinearity check is mandatory). Public archival of the 3-D fields is unconfirmed anyway.
- **8 one-at-a-time runs = ONE LOCAL Jacobian**, not the global manifold; and short integrations test
  *transient* sensitivities — validating the equilibrated 1995–2017 Jacobian needs a
  **convergence-with-integration-length** demonstration. Use ≥2 symmetric FD step sizes; identical
  checkpoints/forcing/averaging.
- **The adjoint does not give the Jacobian:** one adjoint integration returns `Jᵀr` (gradient of one
  scalar objective), not the observation×parameter Jacobian a Gauss-Newton Fisher needs. For 4 controls,
  **verified central differences** are the simpler route (v05 has no turnkey Darwin-controls adjoint).
- **Validation requires the observation operators:** GCM perturbation fields must be pushed through the
  SAME depth/phase/location/timescale/uncertainty-weighted operators as the inverse problem; raw tracer
  fields alone don't validate the surrogate Fisher. Model sink diagnostics establish *implementation
  consistency* only — not independent evidence.
- **v06 ≠ the v05 four-parameter problem:** v06 replaces `scav_rat` with `scav_tau` + particle-class
  weights and uses group-specific growth/palatability/R_PICPOC. Need a physical cross-version mapping
  before treating v05/v06 as replication.

## D. Data strategy per stuck parameter — with the observation operator

- **scav_rat (iron sink):** no turnkey "234Th → Fe-scavenging-rate" product. Needs 234Th export + matched
  sinking-particle Fe:234Th + Fe inventories + advection/non-steady corrections; separate authigenic/
  biogenic Fe from (often dominant) lithogenic Fe. **Best ready compilation: Black et al. 2020, GBC,
  10.1029/2020GB006592** (prior fluxes + 100+ upper-ocean Fe residence-time estimates). Raw: GEOTRACES
  IDP2025 (BODC) + BODC radionuclide records. Darwin exposes `scvLosFe`/`scavRate` diagnostics but they're
  runtime-selected (check `data.diagnostics`) and are synthetic targets (same model), not independent.
- **R_PICPOC in the Southern Ocean:** anchors DO exist. **Great Calcite Belt — Rosengard et al. 2015**
  (BG 12:3953; 27 Atlantic/Indian stations, size-fractionated PIC/POC/bSi/234Th) and **Pacific GP19 —
  Balch et al. 2025** (GBC 10.1029/2024GB008457; PIC/POC standing stocks + **calcification:photosynthesis
  rates**). For a *production* ratio the matched **calcification:photosynthesis rate** is the correct
  observation operator; standing-stock / export ratios are altered by sinking/grazing/dissolution.
  Satellite PIC (MODIS/PACE) is a standing-stock proxy and is **biased in SO diatom/bSi waters** (bSi
  scattering mistaken for calcite; filter/ignore south of the Polar Front — Balch 2025, Li 2025) → weak
  spatial/seasonal constraint only, with paired POC + validation.
- **diatomgraz:** MAREDAT (diatom abundance/biovolume/carbon biomass); pigment-specific **dilution
  experiments** are the closest grazing evidence, incl. SO (Gutiérrez-Rodríguez et al. 2023, L&O Letters
  10.1002/lol2.10355) — but biomass ≠ palatability; mapping needs the predator/functional-response operator.
- **Smallgrow/Biggrow:** seasonality helps ONLY if observations resolve the two PFT groups. Bulk Chl / bulk
  ¹⁴C constrains an *aggregate realized* growth, confounded with grazing/limitation. Use **group-specific
  carbon/production**, bloom timing, nutrients, MLD, light, and the model's per-type PC/PP/grazing
  diagnostics. Some growth/loss params are inseparable even with annual-cycle data (Spitz et al. 1998).
  ¹⁴C is neither gross PP nor NCP (depends on incubation duration/respiration/exudation) — constrains
  biomass-weighted realized photosynthesis, not maximum growth constants (Carvalho 2017; Manning 2017).
  NOTE: these are inverted into PCmax — preserve the inverse sign.

## E. Emulator — baseline rigor **[CLAIM FIX already partly applied]**

- "A correct one-month operator cannot beat persistence" is **mathematically false** — an exact operator
  has lower error whenever the state moves. The ceiling means improvement < model/obs/sampling error.
- PIC/POC beating persistence does NOT prove "fast patchy particulate" is uniquely predictable — larger
  tendency variance mechanically creates headroom. Compare **tendency-normalized** error + skill vs
  **tracer-specific noise floors**.
- Baselines must include climatology, anomaly-persistence, **damped persistence, AR(1), advection-only**,
  on identical rolling hindcasts. Report by depth/biome/init-month/anomaly-amplitude with **block-bootstrap**
  (spatial+temporal autocorrelation). Multi-month crossover ≠ carbonate newly learnable (persistence
  auto-degrades; require beating damped+seasonal at each lead — Mogen 2023). Separate **rollout stability**
  from **horizon predictability**; don't attribute rollout error to information content.

## Net effect on Manuscript #1
The retreat is now two levels on the iron claim (ratio not product; practical-under-steady-state not
structural), the silica limitation moves from "ocean" to "our surrogate" (fixable), and the validation
plan gains hard preconditions (loaded-traits, symmetric small FD, convergence-with-length, observation
operators). None of this breaks the study — it sharpens it into an honest, correctly-scoped
identifiability-geometry + observation-design paper. The observation-design result stays the novelty,
now with the correct observation operators named for each candidate.
