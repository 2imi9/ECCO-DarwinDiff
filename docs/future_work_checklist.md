# DarwinDiff future-work checklist

Living list of stages / datasets / refs / framework adoptions we've identified
but not yet applied. Updated as new gaps surface. Tick boxes as items land.

## Methodology stages not yet applied to v2.2

- [ ] **Block cross-validation on nb23 / nb25** — mirror v2.0 nb21. Train on N-1 spatial blocks, test on the held-out block, confirm Carroll-6 means stable across folds. Without this, the "3 of 6 calibration-grade" headline could be an Eq-Pacific-specific artifact. ~3 h on RTX 5090 or queue for cluster.
- [ ] **Multi-seed robustness** — re-run nb23 / nb25 with seeds 0, 1, 2, 3, 4; report mean ± std of recovered Carroll-6 means. Currently all Phase 2 runs are seed=0; we have no evidence the result isn't seed-dependent.
- [ ] **Cross-basin / held-out AOI** — train on Eq Pacific, test on Mid-Atlantic and North Pacific (the other DarwinDiff AOIs already configured in `ecco_darwin_loader`). Confirms recovered params generalize spatially. ~6 h GPU (3 AOIs × 2 networks).
- [ ] **Prognostic validation (Brenowitz & Bretherton 2018 § 3.4)** — run learned Carroll-6 parameters back through actual forward Darwin v05 on the cluster; check long-term stability + R² against real ocean fields. Cluster-gated (Phase 3 work).
- [ ] **Multi-time-step loss (Brenowitz & Bretherton 2018 § 3.2)** — if Track 2 emulator becomes numerically unstable, replace terminal-state-z-score with mass-weighted loss over T forward-Euler steps. Their Eq. 4. Not blocking for Track 1; gate for Track 2.
- [ ] **Uncertainty quantification on recovered parameters** — multi-seed + bred-vector ensemble (Mahesh et al. 2025 SFNO recipe) to produce a *distribution* over each Carroll-6 parameter rather than a point estimate. Confidence intervals on alpfe, scav_rat, etc.
- [ ] **Formal identifiability analysis** — Fisher information / SVD on the loss surface around the recovered optimum. Tells us which of the 6 Carroll-6 parameters are truly identifiable from the 11-target loss set vs. which are loose because they're under-constrained vs. loose because of optimizer/architecture issues.
- [ ] **Verification-setup consistency audit (Gupta et al. 2026 HealDA)** — they show small verification changes shift apparent skill by 12–24 h in weather forecasting. Equivalent for us: small differences in how we compute `|Δ|/Carroll` (mean over AOI vs. median, ocean_mask definition, z-score statistics) could shift band assignments. Document the chosen verification protocol explicitly and stick to it.

## Datasets shared by Jonathan not yet wired in

In rough priority order for the v2.2 → v2.3 arc.

- [ ] **GEOTRACES IDP2025** — direct iron + co-measured nutrients/DIC/ALK. Phase 3 candidate. Directly attacks the iron-pair degradation surfaced in nb22 / nb23 / nb25 — would let us train `alpfe` and `scav_rat` against real-ocean iron instead of Darwin's internal iron field. URL: https://www.geotraces.org/ (verified).
- [ ] **Ocean color satellite Chl** — per-PFT Chl validation via MODIS Aqua / GlobColour retrievals. Phase 2.1 candidate. Cross-check the inferred Chl1=diatoms…Chl5=Pro-HL mapping against retrieved species. URL pending from Jon.
- [ ] **SOCAT v2025** — surface ocean pCO₂ real-obs. Phase 4 candidate. Independent validation of forward-Darwin pCO₂ patterns once Carroll-6 is recovered. URL: https://www.socat.info/ (verified).
- [ ] **BGC-Argo autonomous floats** — depth-resolved DIC/O₂/Chl from ~5K floats. Phase 5 candidate. Lets us train against time-resolved sparse obs, not just climatology means. `argopy` already in `pyproject.toml`. URL: https://biogeochemical-argo.org/ (verified).
- [ ] **WOD / WOA** — temperature/salinity/nutrients/oxygen. Backup — partly redundant with GLODAP but with different corrections (Jon flagged this). URL: https://www.ncei.noaa.gov/products/world-ocean-atlas (verified).
- [ ] **ECCO-Darwin LLC90 1° baseline** — Jon's URL still pending (service was down at email time; ECCO portal in maintenance 2026-05-11 / 12). Re-request after Tuesday.

## PhysicsNeMo reading queue for Track 2 (emulator)

Do this AFTER v2.2 closeout, BEFORE Track 2 design.

### Tier 1 — must-read

- [ ] `physicsnemo.models` — **FNO** + **AFNO** subsections (workhorse for grid-based PDE emulation; SFNO is what Mahesh et al. 2025 + HealDA use)
- [ ] `physicsnemo.models` — **GraphCastNet** (the GraphCast architecture; sets the bar for global Earth-system ML)
- [ ] `physicsnemo.models` — **HEALPixRecUNet** (UNet on HEALPix grid; what HealDA uses)
- [ ] `physicsnemo.sym` introduction + one PINN tutorial — decide if Carroll-6 mass-balance constraints (carbon, ALK stoichiometry, iron) are worth embedding as PINN losses

### Tier 2 — if Tier 1 has a gap

- [ ] `physicsnemo.models` — **MeshGraphNet** (graph net on arbitrary mesh; lets us stay on Darwin's native LLC270 cubed-sphere grid instead of regridding to lat/lon)
- [ ] One concrete weather example (e.g. AFNO Earth-2 forecasting) — see what end-to-end PhysicsNeMo workflow looks like in practice

### Tier 3 — cross-cutting

- [ ] "How to Write Your Own PhysicsNeMo Model"
- [ ] "Converting PyTorch Models to PhysicsNeMo Models" — decide migration scope for our existing `DINN`, `DINNDeep`, `carroll6_5pft`
- [ ] `physicsnemo.distributed` — multi-GPU + multi-node training for the eventual cluster work

**Estimated total reading time:** ~6 h focused.

## Reference papers to keep on hand

- [x] **Carroll et al. 2020 (JAMES)** — original ECCO-Darwin Green's-functions calibration; source of `CARROLL_VALUES`. Historical baseline. Memory: `reference_carroll_2020.md`
- [x] **Carroll et al. 2022 (GBC)** — Darwin 3 / v05 target; the active recovery target. Memory: `reference_carroll_2022.md`
- [x] **Dutkiewicz et al. 2009 (GBC)** — Darwin's core BGC paper with per-PFT equations. **Paywalled — full PDF not fetched yet.** Needed to refine v2.2.1's literature-plausible per-PFT K_FE values to Darwin-exact.
- [x] **Brenowitz & Bretherton 2018 (GRL)** — prognostic-validation framework + multi-time-step loss. Anchor for Track 2 emulator + Phase 3 forward-Darwin validation.
- [x] **Mahesh et al. 2025 (GMD Parts 1 + 2)** — SFNO huge ensembles for weather forecasting. Methodology reference for UQ via bred-vector + multi-checkpoint ensembles.
- [x] **Gupta et al. 2026 (arXiv 2601.17636v2, HealDA)** — ML-based data assimilation; verification-setup-sensitivity finding (12–24 h shifts). Same NVIDIA / Brenowitz ecosystem that ships PhysicsNeMo.
- [ ] **Darwin 3 v05 `data.traits` namelist** — would give us Darwin-exact per-PFT K_FE, half-saturations, mortality, quotas. Not on disk locally; ask Jon.

## Done items (reference)

- [x] v2.0 closeout — 7-tracer carbonate box, iron pair to calibration-grade. PR #34 merged, tag `v2.0` pushed.
- [x] v2.1 Phase 1 — GLODAP DIC + ALK hybrid (nb22). PR #36 open, P1/P2 fixes pushed.
- [x] v2.2 Phase 2 — 5-PFT box-model extension (nb23, nb24, nb25 — see `docs/findings/v2.2_phase2.md`).
- [x] CONTRIBUTING.md — PR/commit/branch conventions; no Co-Authored-By trailer; no `claude/` branch prefix.
