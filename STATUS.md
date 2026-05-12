# DarwinDiff — Project Status

*Living doc. Update as things ship.*

**Last updated:** 2026-05-11 (Track 1 **v2.2 Phase 2** — 5-PFT box-model extension. v2.0 shipped to main + tagged. v2.1 Phase 1 GLODAP-hybrid open as PR #36 with P1/P2 review-bot fixes pushed. v2.2 Phase 2 lives on branch `v2.2-5pft-box` — nb23 + nb24 executed; v2.2.1 nb25 with per-PFT K_FE training as of this writing).

## Where we are in one line

Track 1 (parameter recovery) at **v2.2 Phase 2 in flight** — DarwinDiff is a gradient-based replacement for ECCO-Darwin's Green's-functions calibration at the same parameter scope (Carroll's 6). Locally-runnable end-to-end on a single GPU in ~70 min per training run. **v2.0 (merged to main, tag `v2.0`):** carbonate-extended 7-tracer box + 7-tracer joint loss recovers the iron pair to calibration-grade against Carroll's published Green's-functions optima (`alpfe` 1.1%, `scav_rat` 40% off Carroll); other 4 parameters drift because the 2-PFT box averages across species with very different physical rates. **v2.1 Phase 1 (PR #36 open):** nb22 swaps Darwin DIC + ALK for GLODAPv2.2016b real ocean observations as a hybrid target. `R_PICPOC` moves from 360% off Carroll to 74% off (most dramatic single-parameter improvement on the project); iron pair degrades against Carroll (real Darwin-vs-reality coupling artifact). **v2.2 Phase 2 (branch `v2.2-5pft-box`, 8 commits ahead of main):** nb23 replaces the 2-PFT box with a 5-PFT box matching Darwin 3 v05 (diatoms, other large euks, Synechococcus, Pro-LL, Pro-HL); each Carroll-6 parameter now governs one specific PFT instead of an average. nb23 hits **3 of 6 Carroll-6 params at calibration-grade** (`Biggrow`, `diatomgraz`, `scav_rat`) but `alpfe` regresses out of calibration-grade — suspected shared-K_FE aliasing. nb24 (Phase 2 + GLODAP combo) degraded (1/6); combo rejected for Eq Pacific. v2.2.1 nb25 tests per-PFT K_FE half-saturations; results pending. Coverage: 3 basins × 11 targets (FeT + 5 separate Chl_i + POC + PIC + DIC + ALK + CO₂_flux). **Track 1 closed locally on a single GPU**; B200 cluster burn-in pitch sent to MIT ORCD 2026-05-10 (Jonathan Lauderdale); cluster work scales the same scope to global resolution + Track 2 emulator (gated on PhysicsNeMo adoption — see [`docs/future_work_checklist.md`](docs/future_work_checklist.md)).

## Most important findings so far

1. **Carroll 2022 inherited Carroll 2020's calibrated 6-parameter values.** Verified against the v04 (Darwin 1, JAMES paper) and v05 (Darwin 3, GBC paper) source namelists — all six numbers `(alpfe=0.92831, scav_rat=6.025e-7, Smallgrow=0.66098, Biggrow=0.43148, diatomgraz=0.83003, R_PICPOC=0.04245)` are bit-for-bit identical between the two versions.

2. **Structural-ceiling argument is universal.** In every fit (notebooks 09–14), the global-scalar Green's-functions parametric class produces a constant prediction (`r = undefined`, mathematically inevitable for one parameter vector + uniform initial state). DINN per-cell finds a non-trivial r in every fit. Not target-specific or basin-specific.

3. **N Pacific NO₃ is the strongest single-fit result among the SST-only DINN baseline** — `r = 0.979`, loss ratio Global / DINN = **23.8×**. Demonstrates that the structural ceiling can be quantitatively dramatic in regions with smooth, SST-coupled BGC.

4. **Cross-basin parameter consistency.** Recovered Carroll-6 values are stable across basins (within ~25% across Mid-Atl + N Pacific + Eq Pacific). The same systematic offsets appear vs Carroll's published optima in every basin — suggests the 5-tracer box-model proxy creates basin-independent biases (not random fitting noise). Stronger claim than any individual fit because it shows reproducibility.

5. **`alpfe` converges on Carroll's published 0.928** as we use targets that better constrain the iron pair. Eq Pacific FeT global-scalar fit recovers `alpfe = 0.959` (3% off Carroll). Iron-replete-basin Chl fits recovered `alpfe ≈ 0.5–0.6` (much further off) because Chl pattern in those basins doesn't depend on iron parameters.

6. **Best target depends on basin physics**, not just on Carroll's calibration choices. Mid-Atl: Chl `r=0.72` > NO₃ `r=0.61`. N Pacific: NO₃ `r=0.98` > Chl `r=0.97`. Likely reflects Mid-Atl NO₃ being dominated by Gulf Stream / mesoscale eddy structure that an SST-only DINN can't capture.

7. **Network capacity ≠ better Carroll-6 recovery (nb15).** Multi-channel input (SST + MLD + wind + lat) into a deeper network (DINNDeep, ~9.4K params, 21× the baseline) drives Eq Pacific FeT r from 0.337 → **1.000** and reduces loss ~3000×. But recovered Carroll-6 means are NOT closer to Carroll's published values (some are worse). The fit memorizes the FeT pattern via degenerate parameter sets that produce the right field but don't match the published calibration. **The recovery ceiling is the box-model proxy simplification, not the network architecture.**

8. **DINNDeep's r=1.000 is interpolation, not extrapolation (nb16).** Cross-validation confirms: random 80/20 hold-out gives held-out r=**0.995** (passes — interpolating gaps works), but block hold-out (western 2/3 train, eastern 1/3 test) gives held-out r=**0.301** (fails — can't extrapolate to unseen spatial blocks). DINNDeep is not memorizing in the trivial sense, but it IS learning a function that's smooth across the training set without extrapolating beyond it. **For cross-basin claims (e.g., training on Mid-Atl, applying to N Pacific), DINNDeep is unreliable; the SST-only DINN baseline is the more honest tool because it has less interpolation capacity to lean on.**

9. **Ensemble disagreement is a tail-detector, not an extrapolation-flag (nb17).** A 10-seed DINNDeep ensemble on full Eq Pacific FeT shows Pearson r(per-cell stdev, |error|) = **+0.87** — high-disagreement cells coincide with high-error cells (useful outlier flag). But Spearman ρ = **−0.42** — opposite sign — meaning within the well-predicted bulk, rank order between stdev and |error| is inverted. Practical takeaway: ensemble stdev is a usable *flag for cells with extreme errors*, not a fine-grained quality ranking. A separate 5-seed ensemble trained on western 2/3 only (replicating nb16's block-CV) shows held-out stdev is only **1.17×** training stdev (Mann-Whitney p=1.4e-10, significant but tiny effect) — **the ensemble is overconfident in extrapolation territory.** nb16's r=0.301 is highly reproducible across these 5 seeds (per-seed: 0.278, 0.288, 0.301, 0.330, 0.358) — not noise. **Cheap solutions (more seeds, more capacity) do NOT rescue the cross-basin gap.**

10. **DINNDeep saturation generalises across (AOI × target); per-parameter recovery direction is target-specific (nb18).** Repeated the nb15 head-to-head on N Pacific Chl (DINN baseline r=0.966 from nb11). DINNDeep saturates r=1.000 with ~3000× lower loss, matching the nb15 saturation pattern qualitatively. But recovered Carroll-6 means are mixed: **3 closer** to Carroll's published, **3 further** — not uniformly degenerate as in Eq Pacific FeT. The single-parameter offsets vary with the dominant physics of the basin × target combination. Refines the v1.4 finding from "box-model proxy is the universal ceiling" to "the ceiling exists, and the specific recovery biases depend on which tracer is fit."

11. **Multi-tracer joint loss partially collapses parameter degeneracy (nb19).** Added 4 Darwin tracer fields as simultaneous loss surfaces (FeT + Chl_total + POC + PIC, using carroll6's existing 5-tracer state vector — no box-model extension required). All 4 tracers fit nearly perfectly: DINNDeep per-tracer r = (FeT 1.000, Chl 1.000, POC 0.998, PIC 0.998), confirming the box IS capable of producing the joint Darwin tracer state. Carroll-6 recovery vs nb15's single-target FeT: **3 of 6 parameters closer** to Carroll's published values (Smallgrow, Biggrow, R_PICPOC — directly constrained by the new tracer fields), **3 of 6 not** (alpfe, scav_rat, diatomgraz — iron-pair and grazing parameters lacking direct new constraints). Iron pair `alpfe` and `scav_rat` remain 2–3× off Carroll regardless. Implication: multi-tracer joint loss is an effective tool for parameters with direct tracer evidence; iron-pair identifiability needs depth-resolved observations OR carbonate extension to add CO₂-flux as a constraint.

12. **Carbonate cycle resolves the iron-pair underconstraint (nb20 — v2.0 headline).** New `darwindiff.carbonate` module (Follows-2006 iterative solver + Wanninkhof 2014 air-sea flux, autograd-clean, 15 tests) + new `carroll6_carbonate_integrate` (7-tracer extension `[DFe, Ps, Pl, POC, PIC, DIC, ALK]` with DIC↔PIC↔ALK couplings + air-sea CO₂ flux on DIC, 8 conservation-law tests). 7-tracer joint loss (FeT + Chl + POC + PIC + DIC + ALK + CO₂_flux) trained with DINN baseline as headline (SST-only, ~400 params — can't saturate, recovery is meaningful) and DINNDeep as secondary (4-channel, ~9.4K params — saturates, ceiling demo). **DINN baseline result vs nb14 (DINN baseline + FeT only):** `alpfe` 0.033 → **0.011** off Carroll (CLOSER, within 1.1%); `scav_rat` 0.798 → **0.401** off Carroll (CLOSER, halves the 80% gap). Other 4 parameters drift (joint loss redistributes degeneracy from iron pair onto Smallgrow/Biggrow/diatomgraz/R_PICPOC). **DINNDeep result vs nb19 (DINNDeep + 4-tracer):** scav_rat 2.117 → 0.550 off (CLOSER, matches DINN-baseline direction); 3/6 closer overall. **The scav_rat-moves-closer signal is reproducible across BOTH architectures** — that's a robust scientific finding, not network noise. The structural-ceiling argument from v1.4-v1.8 still holds for the 4 non-iron parameters: with a 5-tracer simplified box trying to fit 7 Darwin fields, the inverse problem is over-determined; the optimizer trades parameters away. Full v2.0 record at [`docs/findings/v2_track1_closeout.md`](docs/findings/v2_track1_closeout.md).

13. **Carbonate also closes the spatial-extrapolation gap from nb16 (nb21).** Block cross-validation on the same 7-tracer carbonate setup (western 2/3 train, eastern 1/3 test, target z-scores from train cells only) gives DINNDeep held-out test r = **0.637 on FeT** — more than doubling nb16's r = 0.301 baseline with single-target FeT. Mean test r across all 7 tracers = **0.745**. DIC and ALK extrapolate near-perfectly (test r > 0.97 with train-test gap < 0.02). DINN baseline can't extrapolate even with the extra signals (test mean r = −0.273) — its ~400 params are too small to learn a generalizable function from the train block. **The v1.5 "DINNDeep is interpolation only" finding was specific to single-target FeT loss; with the broader 7-tracer carbonate loss, DINNDeep's extrapolation is meaningfully better.** Two architectures, two roles: DINN baseline = calibration-grade parameter recovery (nb20); DINNDeep = fit quality + spatial generalization (nb21). **Carbonate constraints provide BOTH identifiability AND generalization.**

14. **GLODAP real-obs DIC + ALK target dramatically improves `R_PICPOC` recovery but degrades the iron pair (nb22 / v2.1 Phase 1, PR #36).** Swapped Darwin's internal DIC + ALK for GLODAPv2.2016b mapped-climatology real ocean observations as a hybrid target (FeT + Chl + POC + PIC + CO₂_flux stay on Darwin output; DIC + ALK come from GLODAP). `R_PICPOC` moves from **360% off Carroll's published value → 74% off** — the most dramatic single-parameter improvement on the project so far. But `scav_rat` simultaneously degrades from 40% off → 92% off Carroll. Three coupled phenomena (full breakdown in [`docs/findings/v2.1_phase1_glodap.md`](docs/findings/v2.1_phase1_glodap.md) — on PR #36 branch): (a) GLODAP ALK is a stronger CaCO₃ constraint than Darwin's internal ALK, pulling `R_PICPOC` toward Carroll; (b) the box-model carbonate-iron coupling that v2.0's `scav_rat` recovery implicitly relied on differs between Darwin and reality, breaking the iron-pair calibration against Carroll; (c) DIC + ALK per-tracer fit quality drops (0.985→0.942 on DIC; 0.986→0.963 on ALK) — real fields have spatial structure the 5-tracer box can't reproduce as cleanly as Darwin's smooth self-consistent fields. **Phase 1 does NOT fix the box; the box-model bottleneck v2.0 exposed is still the binding constraint.**

15. **5-PFT box-model extension recovers 3 of 6 Carroll-6 params at calibration-grade — but `alpfe` regresses (nb23 / v2.2 Phase 2).** Replaced the 2-PFT lumped phytoplankton (`Ps` + `Pl`) with 5 distinct functional types matching Darwin 3 v05 (state vector 7 → 10); each Carroll-6 parameter now governs one specific PFT instead of an average over multiple species (`Smallgrow`→Pro-HL, `Biggrow`→other-large-euks, `diatomgraz`→diatoms). 11-target z-scored loss (FeT + Chl1..Chl5 separately + POC + PIC + DIC + ALK + CO₂_flux). **DINN baseline goal check vs Carroll's published Green's-functions:** `alpfe` 0.891 off (Loose, regressed from v2.0's 1.1%); `scav_rat` 0.300 off (✓ Calibration-grade); `Smallgrow` 1.244 off (Drifted); `Biggrow` 0.326 off (✓ Cal-grade, moved up from Drifted in v2.0); `diatomgraz` 0.282 off (✓ Cal-grade, moved up from Loose); `R_PICPOC` 0.738 off (Loose, moved up from Drifted). **3 of 6 at calibration-grade.** The structural fix moved 3 of the 4 v2.0-drifted parameters toward Carroll, but the shared `K_FE` simplification across PFTs aliases the iron-pair recovery — Pro-HL (47% biomass, oligotrophic Fe specialist) and diatoms (30% biomass, Fe-demanding) being forced to share one half-saturation pushes `alpfe` off-optimum. Full v2.2 record at [`docs/findings/v2.2_phase2.md`](docs/findings/v2.2_phase2.md).

16. **5-PFT + GLODAP hybrid combo does NOT compound — interventions conflict on this AOI (nb24).** Stacked Phase 2 (5-PFT box) + Phase 1 (GLODAP DIC + ALK target). DINN baseline got only **1 of 6** params to calibration-grade vs nb23's 3 of 6. Direction of failure: `scav_rat` lost cal-grade status, `Biggrow` regressed dramatically, `R_PICPOC` regressed. The one big win was `diatomgraz` jumping to **Excellent (0.5–8% off Carroll, DINNDeep at 0.005)** — the best single-parameter recovery on this project. GLODAP ALK lit up the diatom-grazing-driven calcification signal, but Darwin-Chl and GLODAP-carbonate are incompatible constraints on the same parameter set. **Phase 2 + Phase 1 combo strategy rejected for Eq Pacific.**

17. **Methodology rules locked in tonight.** Two project-level decisions captured to auto-memory + `CONTRIBUTING.md` for future sessions: (a) **Recovery analyses compare against Carroll's published Green's-functions optima — not against prior notebooks.** The headline is "did the parameter learner catch the goal?" not "did v2.2 beat v2.0?" Inter-notebook deltas are supplementary methodology context, never the headline. (b) **From v2.2.x onward, train DINN baseline only — drop DINNDeep.** DINNDeep saturates trivially (r→1.0 on biomass tracers) and recovers fewer calibration-grade Carroll-6 params than the baseline; halves wall-clock from ~70 min to ~35 min per notebook. The nb20/nb21 dual-network framing was right for the v2.0 saturation-ceiling argument but stops adding value at the Phase 2 recovery-quality question.

## Headline results table

All fits use a 1500-epoch DINN per-cell network (1×1 conv backbone, no spatial coupling) versus a global-scalar Green's-functions baseline, against z-scored Darwin (or GLODAP) target over a Mid-Atlantic-sized AOI. Hyperparameters held constant (Adam lr=5e-3, 200 forward-Euler integration steps, identical box model).

| Notebook | AOI | Target | Network | DINN r | Loss ratio Global / DINN |
|---|---|---|---|---|---|
| 09 | Mid-Atlantic | GLODAP −NO₃ (proxy) | DINN (SST) | 0.691 | 1.71× |
| 10 | Mid-Atlantic | Darwin Chl | DINN (SST) | 0.724 | 1.81× |
| 11 | Mid-Atlantic | Darwin Chl | DINN (SST) | 0.724 | 1.81× |
| 11 | North Pacific | Darwin Chl | DINN (SST) | 0.966 | 14.6× |
| 13 | Mid-Atlantic | Darwin −NO₃ | DINN (SST) | 0.607 | 1.27× |
| **13** | **North Pacific** | **Darwin −NO₃** | DINN (SST) | **0.979** | **23.8×** |
| 14 | Equatorial Pacific | Darwin FeT | DINN (SST) | 0.337 | 1.13× |
| 15 | Equatorial Pacific | Darwin FeT | DINN baseline (SST) | 0.337 | — |
| **15** | **Equatorial Pacific** | **Darwin FeT** | **DINNDeep (4-channel)** | **1.000** | — *(saturated, see caveat)* |
| **18** | **North Pacific** | **Darwin Chl** | **DINNDeep (4-channel)** | **1.000** | — *(saturated, see caveat)* |
| **19** | **Equatorial Pacific** | **FeT + Chl + POC + PIC (joint)** | **DINNDeep + multi-tracer** | **all 4 ≥ 0.998** | — *(saturated, see caveat)* |
| **20** | **Equatorial Pacific** | **7-tracer carbonate joint** | **DINN baseline + carbonate** | *poor (-0.36 to 0.62)* | *iron pair within 1.1%/40% of Carroll — v2.0 headline recovery* |
| **20** | **Equatorial Pacific** | **7-tracer carbonate joint** | **DINNDeep + carbonate** | *all ≥ 0.88* | *scav_rat closer to Carroll in both architectures (robust)* |
| **22** | **Equatorial Pacific** | **7-tracer hybrid (GLODAP DIC + ALK)** | **DINN baseline + carbonate** | *R_PICPOC 360%→74% off Carroll* | *v2.1 Phase 1 headline — most dramatic single-param improvement; iron pair degraded* |
| **23** | **Equatorial Pacific** | **11-target 5-PFT box (Darwin)** | **DINN baseline (5-PFT)** | *3 / 6 calibration-grade* | *v2.2 Phase 2 — Biggrow + diatomgraz + scav_rat hit ≤ 40% off Carroll; alpfe regressed* |
| **24** | **Equatorial Pacific** | **11-target 5-PFT + GLODAP DIC/ALK combo** | **DINN baseline (5-PFT, hybrid)** | *1 / 6 cal-grade; diatomgraz to 0.5% off* | *combo rejected; conflict between Darwin-Chl and GLODAP-carbonate constraints* |
| **25** | **Equatorial Pacific** | **11-target 5-PFT + per-PFT K_FE** | **DINN baseline (v2.2.1)** | *executing as of this writing* | *tests whether per-PFT K_FE breaks the shared-K_FE aliasing pushing alpfe off-optimum* |

## Done — checklist

### Code

- [x] 5-tracer Carroll-6 box model with autograd-traced integrator
- [x] Sigmoid bounding into Carroll's published parameter ranges
- [x] DINN per-cell architecture (1×1 conv) and DINNRegional (MLP) for Track 1 v1.0–1.3
- [x] **DINNDeep** — multi-channel input, deeper / wider, GELU + per-cell LayerNorm + residual connections, for Track 1 v1.4 production fits
- [x] NaN-safe Pearson r diagnostic with constant-prediction detection
- [x] Compute / memory budget calculators
- [x] Loaders for both available ECCO-Darwin v5 product types (1° rectified bin_average + native LLC270 monthly tracer tiles)
- [x] AOI presets for Mid-Atlantic, North Pacific, Equatorial Pacific
- [x] **104-test test suite** covering all of the above
- [x] **Cluster portability prep** — env-var-driven `DARWIN_DATA_ROOT` pattern across all data-loading notebooks (default unchanged on local Windows; cluster overrides via env); SLURM job templates in [`scripts/slurm/`](scripts/slurm/); compute / dataset-transfer spec in [`docs/cluster_setup.md`](docs/cluster_setup.md); `xmitgcm` runtime dep added to `pyproject.toml` (was previously implicit and missing from a fresh-venv install)

### Notebooks (all on main)

- [x] **05** — scalar Carroll-6 recovery from synthetic data
- [x] **06** — ML vs Green's-functions head-to-head, synthetic two-regime
- [x] **07** — 2-D per-cell on synthetic 128×128
- [x] **08** — pre-cluster scoping doc
- [x] **09** — methodology demo on real GLODAP NO₃ proxy
- [x] **10** — Carroll-6 recovery against real Darwin Chl in Mid-Atl (Track 1 v1.0)
- [x] **11** — cross-basin Mid-Atl + N Pacific Chl (Track 1 v1.1)
- [x] **12** — LLC270 native tracer loader infrastructure
- [x] **13** — cross-basin Mid-Atl + N Pacific NO₃ (Track 1 v1.3)
- [x] **14** — iron-pair recovery via FeT in Eq Pacific (Track 1 v1.2)
- [x] **15** — DINNDeep architecture upgrade test on Eq Pacific FeT (Track 1 v1.4)
- [x] **16** — Cross-validation honesty check on DINNDeep (Track 1 v1.5)
- [x] **17** — Ensemble disagreement as inference-time trust map (Track 1 v1.6) — full v1.6 record at [`docs/findings/2026_05_10.md`](docs/findings/2026_05_10.md)
- [x] **18** — Cross-basin DINNDeep on N Pacific Chl (Track 1 v1.7) — DINNDeep saturation generalises; per-parameter recovery direction is target-specific
- [x] **19** — Multi-tracer joint loss on Eq Pacific (Track 1 v1.8) — 4-tracer constraint partially collapses degeneracy (3/6 Carroll-6 parameters closer to published); iron pair stays underconstrained without depth-resolved observations
- [x] **20** — Carbonate-extended box + 7-tracer joint loss on Eq Pacific (**Track 1 v2.0 headline**) — iron pair moves to within 1.1%/40% of Carroll's published; reproducible across DINN baseline + DINNDeep architectures; full record at [`docs/findings/v2_track1_closeout.md`](docs/findings/v2_track1_closeout.md)
- [x] **21** — Block-CV check on the 7-tracer carbonate setup (Track 1 v2.0) — tests whether carbonate extension reduces nb16's r=0.301 extrapolation gap
- [x] **22** — GLODAPv2.2016b real-obs DIC + ALK hybrid (Track 1 v2.1 Phase 1, PR #36) — `R_PICPOC` dramatic improvement (360% → 74% off Carroll); iron pair degraded; full record at [`docs/findings/v2.1_phase1_glodap.md`](docs/findings/v2.1_phase1_glodap.md)
- [x] **23** — 5-PFT box-model extension (Track 1 v2.2 Phase 2) — 3 of 6 Carroll-6 params at calibration-grade against Carroll's published optima; `alpfe` regressed (shared-K_FE aliasing)
- [x] **24** — 5-PFT + GLODAP DIC/ALK combo (Track 1 v2.2) — 1 of 6 cal-grade; combo strategy rejected for Eq Pacific; `diatomgraz` to 0.5% off Carroll (best single-param recovery on project)
- [ ] **25** — 5-PFT + per-PFT K_FE half-saturations (Track 1 v2.2.1) — executing as of this writing; tests whether per-PFT differentiation restores `alpfe` to calibration-grade

### Decisions and scope locked

- [x] Active calibration target = Carroll 2022 / Darwin 3 / v05 (publicly-accessible run; Carroll 2020 / Darwin 1 / v04 retained as historical reference, calibrated values are identical anyway)
- [x] AOIs = Mid-Atlantic + North Pacific + Equatorial Pacific
- [x] Per-cell architecture (1×1 conv backbone) for Track 1 — preserves the structural argument cleanly
- [x] Box model stays as 5-tracer carroll6 proxy (no carbonate chemistry, no separate PFTs) for Track 1; extension is now a higher-priority follow-up given nb15's box-model-bias finding

## In progress / next

See [`docs/future_work_checklist.md`](docs/future_work_checklist.md) for the full prioritized backlog (methodology stages not yet applied, Jon-shared datasets not yet wired in, PhysicsNeMo reading queue for Track 2, reference papers).

### Highest priority — closing v2.2

- [ ] **nb25 execution** — 5-PFT box + per-PFT K_FE half-saturations (v2.2.1). Training as of this writing. Tests whether per-PFT differentiation breaks the shared-K_FE aliasing that pushed `alpfe` off-optimum in nb23. Success criterion: 4+ of 6 Carroll-6 params at calibration-grade.
- [ ] **PR #36 (v2.1 Phase 1) merge decision** — P1 + P2 review-bot fixes pushed (`43173f7` on `claude/v2.1-glodap-real-obs`); awaiting re-review and user merge call.
- [ ] **v2.2-5pft-box PR** — open once nb25 result is in. Branch is 8 commits ahead of main.

### Methodology gaps to apply to v2.2

- [ ] **Block CV on nb23 / nb25** — mirror v2.0 nb21. Currently no spatial CV evidence for Phase 2; the "3 of 6 cal-grade" headline could be an Eq-Pacific-specific artifact. ~3 h on RTX 5090 or queue for cluster.
- [ ] **Multi-seed robustness** — re-run nb23 / nb25 with seeds 0–4; report mean ± std. All Phase 2 runs are seed=0; no evidence the result isn't seed-dependent.
- [ ] **Cross-basin** — train on Eq Pacific, test on Mid-Atlantic + N Pacific (existing AOIs).

### Datasets shared by Jon to add (priority order, see checklist for full reasoning)

- [ ] **GEOTRACES IDP2025** — direct iron obs; Phase 3 candidate; directly attacks the alpfe/scav_rat regression.
- [ ] **Ocean color satellite Chl** — per-PFT Chl validation; URL pending from Jon.
- [ ] **SOCAT v2025** — surface pCO₂; Phase 4 candidate (forward Darwin CO₂ flux validation).
- [ ] **BGC-Argo** — depth-resolved sparse-obs; Phase 5 candidate.
- [ ] **ECCO-Darwin LLC90 1° baseline** — URL pending; ECCO portal in maintenance 2026-05-11/12.

### Track 2 emulator (gated on cluster + PhysicsNeMo)

- [ ] **PhysicsNeMo reading queue** — Tier 1 (FNO, AFNO, GraphCastNet, HEALPixRecUNet, `physicsnemo.sym`) + Tier 3 (custom-model authoring + PyTorch conversion + multi-GPU). ~6 h focused. See [`docs/future_work_checklist.md`](docs/future_work_checklist.md). Do AFTER v2.2 closeout.
- [ ] **Prognostic validation (Brenowitz & Bretherton 2018)** — run learned Carroll-6 parameters back through actual forward Darwin v05 on the cluster; check long-term stability + R² against real ocean fields. Cluster-gated.
- [ ] **Time-resolved fitting** — use all available monthly snapshots instead of climatology. Required for Track 2 emulator (must learn temporal dynamics).

## Open questions worth tracking

- **Why does Mid-Atl NO₃ underperform Mid-Atl Chl?** (0.61 vs 0.72 — opposite of N Pacific where NO₃ wins.) Working hypothesis: Mid-Atl NO₃ pattern is dominated by Gulf Stream + mesoscale eddy structure that SST-only DINN can't capture; Chl is more directly SST-coupled. nb15-style multi-covariate input would test this.
- **Iron-pair `scav_rat` identifiability.** Recovered values are 1.8–3× off Carroll's `6.03e-7` in every fit, including DINNDeep (which actually got *worse* than DINN baseline at 1.88e-6). Consistent with literature view that surface iron observations alone underconstrain scavenging — likely needs depth-resolved iron + POC export observations to fully constrain.
- **Box-model bias structure.** Recovered Carroll-6 means show the same systematic offsets vs Carroll in every basin AND in DINNDeep with much more capacity (`alpfe` ~0.5–0.7×, `scav_rat` ~2–3×, `Smallgrow` ~1.4–2.3×, `Biggrow` ~2.6–3.1×, `R_PICPOC` ~2×). nb15 confirms this isn't fixable by network capacity. The 5-tracer simplification has predictable effects relative to full Darwin 3 — extending the box model is the path to closing the gap.
- **Are DINNDeep's r=1.000 fits scientifically meaningful or just memorization?** With 9.4K params and 1071 cells × 6 outputs = 6.4K unknowns, the network approaches parameter parity. Cross-validation experiments (held-out cells, held-out time periods) would tell us whether the recovered Carroll-6 maps generalize or are just a high-capacity interpolant.

## Project arc

- **Track 1** (parameter recovery via differentiable physics) — at **v2.0**. Per-cell DINN baseline fits the spatial pattern where global-scalar produces a constant prediction; DINNDeep saturates fit quality with degenerate per-cell recovery (nb15, nb18); cross-validation confirms DINNDeep is interpolation-only (nb16); ensemble disagreement detects extreme errors but not extrapolation territory (nb17); 4-tracer joint loss partially collapses degeneracy with 3/6 closer (nb19). **v2.0 contribution:** carbonate-extended box + 7-tracer joint loss (nb20) moves the iron pair to within 1.1% (alpfe) / 40% (scav_rat) of Carroll's published values — reproducible across DINN baseline AND DINNDeep architectures. Other 4 parameters trapped by 5-tracer box-model proxy (cluster work + 5-PFT extension addresses). **Track 1 closed locally on a single GPU**; cluster ask sent to MIT ORCD 2026-05-10 for May B200 burn-in window. Cluster transfer prep documented in [`docs/cluster_setup.md`](docs/cluster_setup.md).
- **Track 2** (neural surrogate emulator) — not started; gated on cluster compute access + time-resolved fitting machinery from Track 1 follow-ups.
