# DarwinDiff — Project Status

*Living doc. Update as things ship.*

**Last updated:** 2026-05-13 (Track 1 **v2.6 — GEOTRACES hybrid result** on main: GEOTRACES IDP2025 absolute-units iron loss breaks the alpfe + Smallgrow degeneracy claimed structural in v2.2 closeout. Honest multi-seed numbers at GEOTRACES_W=0.3, n=10: **9/10 seeds Cal-grade on Smallgrow (4/10 Excellent), mean offset 0.095 ± 0.116** — project-first reproducible Cal-grade recovery (the earlier "5/5 Excellent at 0.040 ± 0.040" framing was an n=5 result; the n=10 distribution is wider, retracted below). Aggregate 4/6 Cal-grade reproducibly. Stuck pair shifts from `(alpfe, Smallgrow)` → `(scav_rat ~0.92 off, R_PICPOC ~2.78 off)`, both identified as HNLC-region structural limits consistent with the post-GEOTRACES community view (Tagliabue, Achterberg, Ye, Somes). PR state on main: #37 v2.2 closeout merged; #38 doc reformat merged; #39 GEOTRACES scaffold merged; #40 v2.6 GEOTRACES hybrid + loader fix merged (e883248); #36 v2.1 GLODAP closed in favour of #41; #41 v2.1 Phase 1 re-land merged (786b567). **#42 v2.7 2-layer box** open at this writing — corrected iron budget after Greptile P1; alpfe Excellent claim retracted, real contribution is preserving v2.6-grade biology recovery with a vetted 2-layer integrator.)

## Where we are in one line

Track 1 (parameter recovery) at **v2.6 — GEOTRACES hybrid era** — DarwinDiff is a gradient-based replacement for ECCO-Darwin's Green's-functions calibration at the same parameter scope (Carroll's 6). 5-PFT training runs ~80 sec on RTX 5090 Laptop. Cumulative arc:

- **v2.0 (merged, tag `v2.0`):** carbonate-extended 7-tracer box + joint loss recovers iron pair to 1.1% (`alpfe`) / 40% (`scav_rat`) of Carroll's published in the 2-PFT proxy.
- **v2.1 Phase 1 (PR #36 closed, re-landed and merged as PR #41 at 786b567):** nb22 swaps Darwin DIC + ALK for GLODAPv2.2016b real-obs hybrid; `R_PICPOC` 360% → 74% off Carroll; iron pair degrades under obs swap. PR #36 became DIRTY when PR #37 independently cherry-picked CONTRIBUTING.md; the v2.1 Phase 1 work was re-landed cleanly via PR #41 from a fresh branch off main without the conflict.
- **v2.2 closeout (PR #37 merged):** 22 experiments + Wave 3 follow-up. v2.4 PINN drift w=3.0 hits 4/6 on seed=0 BUT multi-seed shows seed=0 was lucky on Biggrow + R_PICPOC. Robust multi-seed result: alpfe (0.86 ± 0.02) and Smallgrow (1.22 ± 0.32) consistently broken — *claim at the time was these are structurally stuck*.
- **v2.5 GEOTRACES scaffold (PR #39 merged):** initial loader built against documented IDP conventions. Validated 2026-05-12 against real IDP2025 NetCDF — found 3 schema differences (no `_BOTTLE`/`_PUMP` suffixes; lowercase coords; SeaDataNet ASCII QC codes 49/50 not 1/2). Rewrite landed in PR #40 (merged at e883248).
- **v2.6 — GEOTRACES hybrid (merged on main as PR #40 at e883248):** added GEOTRACES IDP2025 dissolved-iron absolute-units MSE loss term on 26 populated 1° bins in Eq Pacific. Weight sweep + Wave 5 + Wave 6 (10-seed robustness + isolation + extreme PINN) = 21+ experiments. **Headline (corrected to n=10): GEOTRACES_W=0.3 + PINN drift w=3.0 reaches 4/6 Cal-grade reproducibly across 10 seeds, with Smallgrow at 9/10 Cal-grade (4/10 Excellent), mean offset 0.095 ± 0.116 off Carroll** — project-first reproducible Cal-grade recovery on Smallgrow. (The earlier session-notes framing of "5/5 Excellent at 0.040 ± 0.040" was the n=5 number; the n=10 distribution is wider and worth reporting honestly: seed=5 was the first to give Cal-grade but not Excellent.) alpfe lands Cal-grade (mean 0.549, off 0.408); scav_rat (4.65e-8, off 0.923) and R_PICPOC (0.166, off 2.92) become the new stuck params. **Reframes v2.2's "alpfe + Smallgrow are structurally stuck" claim — they are NOT, they're recoverable under GEOTRACES; scav_rat + R_PICPOC are the HNLC-region structural limits** (Eq Pacific iron loss is biology-dominated → scav_rat underconstrained; PIC/POC ratio re-equilibrates with iron pair without independent PIC observations).
- **v2.7 — 2-layer box model (PR #42 open, post-fix):** extends Carroll-6 to a 2-layer (0–50 m + 50–1000 m) box with sinking-POC iron + Kz + subsurface remineralisation; adds a second GEOTRACES MSE loss on the 50–1000 m bin. Greptile caught an iron double-count in the initial integrator (`fe_uptake` + explicit sinking-POC term were both subtracting iron from DFe_1, then crediting it twice to L2). With the fix in place, the corrected v2.7 result is **NOT a leap over v2.6**: aggregate 3-4/6 Cal-grade, the same range. The pre-fix "3/3 Excellent alpfe at 0.011 off" headline is retracted as a bug artifact. The real contribution is a vetted 2-layer integrator + empirical confirmation that subsurface DFe anchoring alone does NOT unblock scav_rat (still drifted at ~0.87 off Carroll regardless of subsurface weight). v2.8 will move to depth-resolved POC observations as the realistic scav_rat unblock.

**raw_fet + GEOTRACES combos rejected** (Wave 5) — two iron-magnitude pins conflict, drop to 1/6. **PINN drift w=5.0 + GEOTRACES_W=0.3** gives 3/6 with TWO Excellent (Smallgrow 0.028, diatomgraz 0.043) — interesting but doesn't help iron-sink params.

**Fine sweep at finer GEOTRACES_W resolution (0.15 / 0.20 / 0.25) confirms no sweet spot.** scav_rat sits at 0.89–0.92 off Carroll across all weights from 0.15 to 1.0; the alpfe-scav_rat tradeoff is genuinely structural, not a weight-tuning artifact. w=0.25 produces equivalent results to w=0.30 (Smallgrow Excellent, alpfe cal-grade, 4/6). The realistic local-GPU ceiling for Eq Pacific surface + 5-PFT box + surface-iron observation is **4/6 with Smallgrow Excellent** — period. Pushing past requires methodology change: cross-basin (non-HNLC, cluster-gated), multi-layer box model (~1 week refactor), or independent PIC observations.

**Track 1 closed locally on a single GPU**; B200 cluster burn-in pitch sent to MIT ORCD 2026-05-10 — cross-basin (non-HNLC, e.g., N Atlantic) is the cluster-gated path to recover scav_rat. Cluster prep documented in [`docs/cluster_setup.md`](docs/cluster_setup.md).

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

18. **v2.2.1 per-PFT K_FE hypothesis REJECTED — alpfe regression is NOT a shared-K_FE aliasing artifact (nb25).** Refactored `carroll6_5pft.py` to optionally take per-PFT iron half-saturations; ran nb25 with literature-plausible K_FE values (Pro-HL 5 nM → diatoms 100 nM). DINN baseline goal check: `alpfe` 0.891 → 0.851 off Carroll (essentially flat); `Biggrow` regressed Cal-grade → Loose (0.326 → 0.888 off); `diatomgraz` improved Cal-grade → **Excellent** (0.282 → 0.062 off). 2 of 6 at calibration-grade — WORSE than nb23's 3/6. **What this tells us:** per-PFT K_FE wasn't the alpfe aliasing source. Working hypothesis for the actual root cause: the 11-target loss is 7:1 weighted toward carbonate/Chl signals (5 Chl_i + POC + PIC + DIC + ALK vs 1 FeT target), starving the iron-pair capacity. v2.2.2 candidate fix is **loss weighting** (upweight FeT). nb23 (3/6) was the best result until v2.4.

19. **v2.4 PINN drift constraint hits 4/6 cal-grade — new project best (nb29).** Overnight 20-experiment sweep across z-scored / raw-FeT / PINN balance / PINN drift / GLODAP / per-PFT K_FE / combo settings. Best is `29_v2_4_pinn_drift_eqpac_w3.0.ipynb`: 4 of 6 Carroll-6 params at calibration-grade — `scav_rat` 0.345 ✓, `Biggrow` 0.314 ✓, `diatomgraz` 0.299 ✓, `R_PICPOC` 0.358 ✓. PINN drift (penalize `|dDFe/dt| / DFe`) is the physically-cleaner of the two PINN variants and works at high weight (w=3.0). The 4/6 win comes from PINN pulling `R_PICPOC` into cal-grade (0.738 nb23 → 0.358 nb29) while keeping nb23's wins.

20. **alpfe confirmed STRUCTURALLY stuck at 0.80–0.94 off Carroll across 20 interventions.** Z-scored, FeT-upweighted, raw-FeT (w=0.05–3.0), PINN balance, PINN drift, GLODAP hybrid, per-PFT K_FE, combos — none moved alpfe out of Loose band. Single exception: `raw_fet w=0.01` got alpfe to 0.392 but broke `scav_rat` to 2.556 (iron-pair tradeoff swapped roles). Methodology improvements alone cannot close the alpfe gap; remaining unblockers are (a) Carroll's initial-condition fields (Jon Q2 in tonight's email), (b) 50-day integration window may be too short for iron-pool steady-state, or (c) GEOTRACES IDP iron observations for absolute-magnitude constraint. **Multi-seed of nb23 (seeds 0–4) confirms alpfe sits at 0.841–0.891 off across all seeds (std ≈ 0.020) — robustly reproducible structural finding.**

21. **Tonight's bug log (honest):** introduced two bugs and caught both. **Bug 1 (v2.4 PINN):** referenced `mu_lge`, `mu_proHL`, `alpfe`, `scav_rat` in the PINN block but those names exist only in the integrator's `step()` scope — must extract from `params` tensor in the training scope. Wave 1 lost 8 of 15 experiments to this NameError; Wave 2 reran all 8 successfully after the fix (commit `45ae539`). **Bug 2 (filename routing):** the v2.5 combo case (raw_fet + PINN both > 0) collapsed to the same filename as pure-PINN runs, causing 2 combo files to overwrite their pure-PINN counterparts in Wave 2. Fix routes combos to `..._w{pinn_w}_rawfet{raw_fet_w}.ipynb`. The lost pure-PINN drift w=0.3 and w=1.0 data is recoverable via re-run but not blocking v2.2's deliverable.

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
| **25** | **Equatorial Pacific** | **11-target 5-PFT + per-PFT K_FE** | **DINN baseline (v2.2.1)** | *2 / 6 cal-grade* | *v2.2.1 hypothesis rejected — alpfe regression persists; diatomgraz to Excellent (0.062 off); Biggrow lost cal-grade* |
| **26** | **Equatorial Pacific** | **11-target 5-PFT + FET_W=3 z-scored** | **DINN baseline (v2.2.2)** | *2 / 6 cal-grade* | *scav_rat to Excellent (0.028 off); alpfe still 0.833 off; not a path forward* |
| **27** | **Equatorial Pacific** | **11-target 5-PFT + raw-FeT magnitude term** | **DINN baseline (v2.3, w sweep)** | *1–3 / 6 cal-grade across w∈{0.01..3.0}* | *w=0.05 sweet spot 3/6; w=0.01 anomalous alpfe 0.392 at cost of scav_rat 2.556* |
| **28** | **Equatorial Pacific** | **11-target 5-PFT + PINN strict balance** | **DINN baseline (v2.4)** | *1–3 / 6 cal-grade* | *w=1.0 gives Biggrow Excellent 0.103; alpfe still 0.882 off* |
| **29** | **Equatorial Pacific** | **11-target 5-PFT + PINN drift constraint** | **DINN baseline (v2.4)** | ***4 / 6 cal-grade at w=3.0*** | ***New project best.*** *Biggrow + diatomgraz + scav_rat + R_PICPOC all cal-grade; alpfe unchanged at 0.888* |

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
- [x] **154-test test suite** covering all of the above (plus 5 opt-in real-data tests, skipped by default)
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
- [x] **25** — 5-PFT + per-PFT K_FE half-saturations (Track 1 v2.2.1) — **hypothesis REJECTED**, 2/6 calibration-grade vs nb23's 3/6; `alpfe` regression unchanged; `diatomgraz` to Excellent (0.062 off); `Biggrow` regressed; root cause is loss-balance not K_FE-aliasing
- [x] **26** — 5-PFT + FET-weighted z-score loss 3.0× (Track 1 v2.2.2) — 2/6 cal-grade; FET upweighting alone does not break alpfe
- [x] **27** — 5-PFT + raw-FeT magnitude-preserving loss (Track 1 v2.3, 7 weights: 0.01/0.05/0.1/0.3/0.5/1.0/3.0) — at w=0.05: 3/6 cal-grade + 1 Excellent (best of the sweep). At w=0.01: alpfe alone moves to **0.392 off Carroll** (within cal-grade band) but scav_rat catastrophically broken to 2.556 — the alpfe-scav_rat identifiability degeneracy explicitly observed
- [x] **28** — 5-PFT + PINN iron mass-balance loss (Track 1 v2.4 "balance" type, w=0.3, w=1.0) — best 3/6 at w=1.0; balance type underperforms drift
- [x] **29** — 5-PFT + PINN iron drift loss (Track 1 v2.4 "drift" type, w=0.05, w=0.3, w=1.0, w=3.0, plus combo and lumped variants) — **v2.4 PINN drift w=3.0 reaches project-first 4/6 calibration-grade** (scav_rat, Biggrow, diatomgraz, R_PICPOC); lumped-mapping variant rejected at 2/6; full record at [`docs/findings/v2.2_phase2.md`](docs/findings/v2.2_phase2.md)

### Decisions and scope locked

- [x] Active calibration target = Carroll 2022 / Darwin 3 / v05 (publicly-accessible run; Carroll 2020 / Darwin 1 / v04 retained as historical reference, calibrated values are identical anyway)
- [x] AOIs = Mid-Atlantic + North Pacific + Equatorial Pacific
- [x] Per-cell architecture (1×1 conv backbone) for Track 1 — preserves the structural argument cleanly
- [x] Box model stays as 5-tracer carroll6 proxy (no carbonate chemistry, no separate PFTs) for Track 1; extension is now a higher-priority follow-up given nb15's box-model-bias finding

## In progress / next

### Closing v2.2 — DONE, awaiting merge

- [x] **All 22 v2.2 experiments executed and aggregated** in [`docs/findings/v2.2_overnight_summary.{md,csv}`](docs/findings/v2.2_overnight_summary.md). Headline: v2.4 PINN drift w=3.0 at **4/6 cal-grade**.
- [x] **PR #37 open** at https://github.com/2imi9/ECCO-DarwinDiff/pull/37 with all v2.2 work — Greptile cleared at 5/5 on `5c37e1a`. Four Greptile follow-up fixes pushed: P1 lumped_mapping in carroll6_5pft snapshot branch (`7d24791`), P2 DARWIN_DATA_ROOT env-var guard (`7d24791`), build_nb23.py seed_suffix in all routing branches (`5795e4f`), eval rollout lumped_mapping consistency (`5c37e1a`). data/README.md updated with Jon's canonical URLs (`207841f`); Wave 3 runner added (`6968b19`).
- [x] **PR #36 (v2.1 Phase 1 GLODAP)** — closed 2026-05-12 after going DIRTY against PR #37's CONTRIBUTING.md cherry-pick. Work re-landed cleanly as **PR #41**, merged at `786b567`.

### Wave 3 — 6/6 push experiments (DONE 2026-05-12, ~15 min total)

Three sequential experiments via [`scripts/wave3_alpfe_push.ps1`](scripts/wave3_alpfe_push.ps1) targeting the alpfe-scav_rat identifiability degeneracy uncovered in nb27 (raw_fet w=0.01 moved alpfe to 0.392 but broke scav_rat to 2.556). All 3 completed in ~5 min each.

| Config | Cal-grade | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC |
|---|---|---|---|---|---|---|---|
| **Baseline winner (nb29 PINN drift w=3.0)** | **4/6** | 0.888 | 0.345 | 1.251 | 0.314 | 0.299 | 0.358 |
| Wave 3 #1: raw_fet 0.005 + PINN drift 3.0 | 2/6 | 0.852 | 0.339 | 1.131 | 1.323 | 0.113 | 2.856 |
| Wave 3 #2: raw_fet 0.01 + PINN drift 3.0 | 2/6 | 0.839 | **3.842** | 1.435 | 0.025 | 0.010 | 0.879 |
| Wave 3 #3: PINN drift 5.0 alone | 3/6 | 0.882 | 0.360 | 1.236 | 0.074 | 0.304 | 1.993 |

**Conclusion: alpfe-scav_rat is structural under z-scored loss.** None of 3 alpfe-push experiments beat the 4/6 baseline. Adding PINN drift cancels the raw_fet effect on alpfe (compare Wave 3 #2 alpfe=0.839 vs the standalone `raw_fet w=0.01` from earlier at 0.392 — PINN drift damps the alpfe drop). Higher PINN drift weight (w=5.0) doesn't move alpfe either — sweeps 0.05/0.3/1.0/3.0/5.0 all converge to alpfe ≈ 0.86–0.89.

**Implication:** the path to 6/6 is now confirmed to require **external real-iron absolute-units observations** — z-scored loss alone cannot break the alpfe-scav_rat degeneracy regardless of loss-design tricks. PR #38 (GEOTRACES IDP2025 loader) is the right next move.

- [x] raw_fet w=0.005 + PINN drift w=3.0 — 2/6
- [x] raw_fet w=0.01 + PINN drift w=3.0 — 2/6 (scav_rat catastrophic)
- [x] PINN drift w=5.0 alone — 3/6 (Biggrow → Excellent, R_PICPOC out)

### Next-PR pipeline

- [x] **PR #39 — GEOTRACES IDP2025 loader scaffold** merged at `55d0f58`. Schema bugs (`_BOTTLE` suffix, lowercase coords, SeaDataNet QC) caught against the real NetCDF and fixed in PR #40.
- [x] **PR #40 — v2.6 GEOTRACES hybrid experiment + corrected loader** merged at `e883248`. 4/6 Cal-grade across 10 seeds; alpfe + Smallgrow + diatomgraz consistently Cal-grade; scav_rat + R_PICPOC HNLC-structural.
- [x] **PR #41 — v2.1 Phase 1 GLODAP re-land** merged at `786b567`. Carbonate-side baseline durable on main.
- [ ] **PR #42 — v2.7 2-layer Carroll-6 box (corrected after Greptile P1)** open. Aggregate 3-4/6 Cal-grade; the pre-fix alpfe Excellent claim retracted. Real contribution: vetted 2-layer integrator + empirical evidence subsurface anchoring alone doesn't unblock scav_rat.
- [ ] **v2.8 — depth-resolved POC observation** (next research arc, branch `v2.8-depth-resolved-poc` in flight). Realistic scav_rat unblock by bounding L2 POC_2.
- [ ] **Ocean color loader (Smallgrow target)** — exact URL pending from Jon.
- [ ] **GLODAPv2.2023 mapped upgrade** — refinement vs v2.2016b currently used; bundle with v2.8 or follow-up.

### Methodology stages not yet applied to v2.2

- [ ] **Block CV on nb23 / nb25** — mirror nb21. Currently no spatial-CV evidence for Phase 2; the "3 of 6" headline could be Eq-Pacific-specific.
- [ ] **Multi-seed robustness** — re-run with seeds 0–4; report mean ± std. All Phase 2 runs are seed=0.
- [ ] **Cross-basin** — train Eq Pacific, test Mid-Atl + N Pacific (AOIs already in `ecco_darwin_loader`).
- [ ] **Prognostic validation (Brenowitz & Bretherton 2018 § 3.4)** — run learned Carroll-6 back through forward Darwin v05 on cluster; check long-term stability + R² vs real ocean. Cluster-gated (Phase 3).
- [ ] **Multi-time-step loss (Brenowitz & Bretherton 2018 § 3.2)** — Eq. 4 mass-weighted norm over T forward-Euler steps. Gate for Track 2 emulator if integrators become unstable.
- [ ] **Uncertainty quantification** — multi-seed + bred-vector ensemble (Mahesh et al. 2025 SFNO recipe) → distribution over each Carroll-6 param, not just a point estimate.
- [ ] **Formal identifiability analysis** — Fisher info / SVD on loss surface; which 6 params are truly identifiable from the 11-target loss vs underconstrained vs optimizer-stuck.
- [ ] **Verification-setup consistency audit (Gupta et al. 2026 HealDA)** — small changes in `|Δ|/Carroll` definition (mean vs median, ocean_mask, z-score stats) can shift band assignments. Document the chosen protocol and stick to it.

### Datasets shared by Jon to add (priority order, URLs decoded from `.eml` 2026-05-12)

- [ ] **GEOTRACES IDP2025** — alpfe unblocker (real-iron absolute-units obs). URL: https://www.geotraces.org/idp2025/ — **Step 1 / PR #38**.
- [ ] **GLODAPv2.2023 upgrade** — 7 yrs newer than the v2.2016b we currently use. Bottle: https://glodap.info/index.php/merged-and-adjusted-data-product-v2-2023/ · Mapped: https://glodap.info/index.php/mapped-data-product/ — **Step 2** (refinement, low-risk).
- [ ] **Ocean color** — Smallgrow target validation via PFT-specific Chl. Jon did NOT link a specific source ("we could also think about bringing in ocean color"); likely NASA OB.DAAC https://oceancolor.gsfc.nasa.gov/ or ESA OC-CCI for PFT decomposition — **Step 3** (ask Jon for preference).
- [ ] **BGC-Argo** — Wave 4 (time-resolved + depth-resolved). URL: https://biogeochemical-argo.org/data-access.php — Step 4. `argopy` already in `pyproject.toml`.
- [ ] **SOCAT v2025** — surface CO₂ refinement. URL: https://socat.info/index.php/version-2025/ — Step 5.
- [ ] **WOD / WOA** — Background T/S + nutrients. WOD: https://www.ncei.noaa.gov/products/world-ocean-database · WOA: https://www.ncei.noaa.gov/products/world-ocean-atlas — Steps 6 / 7. Jon flagged WOA's monthly nutrient products are limited to the upper few hundred metres (full-depth annual only).
- [x] **ECCO-Darwin LLC90 1° baseline** — Jon's canonical URL: https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC90/ECCO-Darwin/. We pulled from the NAS mirror data.nas.nasa.gov in 2026-05; bin_average (1.9 GB) on disk. LLC270 extension: https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/ECCO-Darwin_extension/ (1.9 TB on disk from NAS mirror).

### Track 2 emulator — PhysicsNeMo reading queue (do AFTER v2.2 closeout)

Tier 1 (must-read, ~3 h): `physicsnemo.models` → FNO, AFNO, GraphCastNet, HEALPixRecUNet, + `physicsnemo.sym` intro + one PINN tutorial.
Tier 2 (if Tier 1 has a gap, ~1 h): MeshGraphNet + one concrete weather example (e.g. AFNO Earth-2 forecasting).
Tier 3 (cross-cutting, ~2 h): "How to Write Your Own PhysicsNeMo Model" + "Converting PyTorch Models" + `physicsnemo.distributed`.

DarwinDiff fit: Track 1 stays as pure PyTorch. Track 2 emulator replaces `carroll6_5pft_integrate` with FNO/AFNO that learns the state-transition map. No shipped ocean-BGC examples in PhysicsNeMo → we'd be pioneer users in this domain.

### Reference papers worth keeping on hand

- ✓ **Carroll 2020 (JAMES)**, **Carroll 2022 (GBC)** — `CARROLL_VALUES` source; the active recovery target.
- ✗ **Dutkiewicz et al. 2009 (GBC)** — Darwin's core BGC paper with per-PFT equations. Paywalled; needed to refine v2.2.1's literature-plausible per-PFT K_FE to Darwin-exact.
- ✓ **Brenowitz & Bretherton 2018 (GRL)** — prognostic-validation framework + multi-step loss. Anchor for Track 2 + cluster-gated Phase 3 forward validation.
- ✓ **Mahesh et al. 2025 (GMD Parts 1+2)** — SFNO huge ensembles; UQ recipe via bred-vector + multi-checkpoint.
- ✓ **Gupta et al. 2026 (arXiv 2601.17636, HealDA)** — ML-based DA; verification-setup-sensitivity finding. Same NVIDIA / Brenowitz ecosystem that ships PhysicsNeMo.
- ✗ **Darwin 3 v05 `data.traits` namelist** — would give Darwin-exact per-PFT half-saturations / mortalities / quotas. Ask Jon when next exchanging email.

## Open questions worth tracking

- **Why does Mid-Atl NO₃ underperform Mid-Atl Chl?** (0.61 vs 0.72 — opposite of N Pacific where NO₃ wins.) Working hypothesis: Mid-Atl NO₃ pattern is dominated by Gulf Stream + mesoscale eddy structure that SST-only DINN can't capture; Chl is more directly SST-coupled. nb15-style multi-covariate input would test this.
- **Iron-pair `scav_rat` identifiability.** Recovered values are 1.8–3× off Carroll's `6.03e-7` in every fit, including DINNDeep (which actually got *worse* than DINN baseline at 1.88e-6). Consistent with literature view that surface iron observations alone underconstrain scavenging — likely needs depth-resolved iron + POC export observations to fully constrain.
- **Box-model bias structure.** Recovered Carroll-6 means show the same systematic offsets vs Carroll in every basin AND in DINNDeep with much more capacity (`alpfe` ~0.5–0.7×, `scav_rat` ~2–3×, `Smallgrow` ~1.4–2.3×, `Biggrow` ~2.6–3.1×, `R_PICPOC` ~2×). nb15 confirms this isn't fixable by network capacity. The 5-tracer simplification has predictable effects relative to full Darwin 3 — extending the box model is the path to closing the gap.
- **Are DINNDeep's r=1.000 fits scientifically meaningful or just memorization?** With 9.4K params and 1071 cells × 6 outputs = 6.4K unknowns, the network approaches parameter parity. Cross-validation experiments (held-out cells, held-out time periods) would tell us whether the recovered Carroll-6 maps generalize or are just a high-capacity interpolant.

## Project arc

- **Track 1** (parameter recovery via differentiable physics) — at **v2.6 on main, v2.7 in PR review, v2.8 in flight**. Per-cell DINN baseline fits the spatial pattern where global-scalar produces a constant prediction; DINNDeep saturates fit quality with degenerate per-cell recovery (nb15, nb18); cross-validation confirms DINNDeep is interpolation-only (nb16); ensemble disagreement detects extreme errors but not extrapolation territory (nb17); 4-tracer joint loss partially collapses degeneracy with 3/6 closer (nb19). **v2.0 contribution:** carbonate-extended box + 7-tracer joint loss (nb20-21) moves the iron pair to within 1.1% (alpfe) / 40% (scav_rat) of Carroll's published in the 2-PFT proxy. **v2.1 Phase 1** (nb22, merged via PR #41 at `786b567`): GLODAPv2.2016b DIC/ALK real-obs hybrid; R_PICPOC dramatic improvement (360% → 74% off); iron pair degraded under the obs swap. **v2.2** (nb23-29, PR #37): full 5-PFT box matching Darwin v05 + 22 experiments; v2.4 PINN drift w=3.0 reaches 4/6 calibration-grade locally (alpfe + Smallgrow stuck at the time). **v2.6 (PR #40 merged at `e883248`)**: GEOTRACES IDP2025 absolute-units iron loss breaks the v2.2 "alpfe + Smallgrow stuck" claim. Honest n=10 numbers: **9/10 Cal-grade on Smallgrow (4/10 Excellent, mean offset 0.095 ± 0.116); 4/6 aggregate Cal-grade across seeds**. New stuck pair `(scav_rat ~0.92, R_PICPOC ~2.92)` identified as HNLC-region structural limits. **v2.7 (PR #42 open, post-fix)**: 2-layer box (0–50 + 50–1000 m) with subsurface GEOTRACES loss; Greptile caught an iron double-count in the initial integrator; after the fix, the corrected v2.7 is roughly comparable to v2.6 (3-4/6 Cal-grade), the pre-fix Excellent-alpfe headline is retracted, real contribution is biology-recovery preservation under the new architecture. **v2.8 (branch in flight)**: depth-resolved POC observations from LLC270 native output, the realistic scav_rat unblock. Cluster ask still pending response from MIT ORCD (sent 2026-05-10).
- **Track 2** (neural surrogate emulator) — not started; gated on cluster compute access + time-resolved fitting machinery from Track 1 follow-ups.
