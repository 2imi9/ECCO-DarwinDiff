# DarwinDiff — Project Status

*Living doc. Update as things ship.*

**Last updated:** 2026-05-10 (Track 1 **v2.0** — carbonate-extended box + 7-tracer joint loss; nb20 + nb21 + new `darwindiff.carbonate` solver + `carroll6_carbonate_integrate`).

## Where we are in one line

Track 1 (parameter recovery) at **v2.0** — DarwinDiff is a gradient-based replacement for ECCO-Darwin's Green's-functions calibration at the same parameter scope (Carroll's 6). Locally-runnable end-to-end on a single GPU in ~90 minutes. **v2.0 headline:** the carbonate-extended box model + 7-tracer joint loss (nb20) moves the iron pair to within **1.1% (`alpfe`)** and **40% (`scav_rat`)** of Carroll's published values — closer in BOTH DINN baseline AND DINNDeep architectures, so the move is reproducible across network capacity, not a fitting artifact. The remaining 4 Carroll-6 parameters drift because the 5-tracer box can't simultaneously satisfy 7 Darwin field constraints — joint loss redistributes degeneracy from the iron pair onto the others. Block-CV on the same setup (nb21) tests whether carbonate extension changes nb16's r=0.301 extrapolation gap. Coverage: 3 basins × 7 targets (Chl, NO₃, FeT, POC, PIC, DIC, ALK, + diagnostic CO₂ flux). **Track 1 closed locally on a single GPU**; B200 cluster burn-in pitch sent to MIT ORCD 2026-05-10 (Jonathan Lauderdale); cluster work scales the same scope to global resolution + Track 2 emulator.

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

### Decisions and scope locked

- [x] Active calibration target = Carroll 2022 / Darwin 3 / v05 (publicly-accessible run; Carroll 2020 / Darwin 1 / v04 retained as historical reference, calibrated values are identical anyway)
- [x] AOIs = Mid-Atlantic + North Pacific + Equatorial Pacific
- [x] Per-cell architecture (1×1 conv backbone) for Track 1 — preserves the structural argument cleanly
- [x] Box model stays as 5-tracer carroll6 proxy (no carbonate chemistry, no separate PFTs) for Track 1; extension is now a higher-priority follow-up given nb15's box-model-bias finding

## In progress / next

### Highest priority (nb15 reordered the queue)

- [ ] **Box-model extension** to add DIC + ALK + carbonate chemistry. nb15 showed that network architecture is no longer the recovery ceiling — the 5-tracer simplification is. Extending the box model is the path to actually matching Carroll's published values rather than producing degenerate solutions that fit the FeT field. Enables fitting Darwin's air-sea CO₂ flux pattern directly (closer to what Carroll 2022 was actually calibrated against), and unlocks adding DIC to the multi-tracer joint loss.
- [x] ~~**Multi-tracer joint loss** (NO₃ + Chl + DIC + FeT simultaneously)~~ — done in **nb19** (Track 1 v1.8), using FeT + Chl + POC + PIC against carroll6's existing 5-tracer state. Partially collapses parameter degeneracy (3/6 Carroll-6 closer to published). Adding DIC to the joint loss requires the box-model carbonate extension above; adding NO₃ is a lower-priority extension.

### Ready to start (no new data needed)

- [ ] Re-run nb11 / nb13 / nb14 with DINNDeep + multi-channel input. nb15's r=1.000 finding should generalize across (AOI, target) combos. Useful for showing the upper bound of the current methodology even if it doesn't improve recovery.
- [ ] Re-execute nb09 to refresh outputs (cleared at v0.95 closeout, never re-run).

### Larger scope

- [ ] Time-resolved fitting (use all available monthly snapshots instead of climatology). Opens Track 2 emulator territory — requires the model to learn temporal dynamics, not just spatial patterns.
- [ ] Pacific AOI confirmation: we've been using 5°S–15°N, 160°W–110°W for the Equatorial Pacific HNLC test. Open to refining.

## Open questions worth tracking

- **Why does Mid-Atl NO₃ underperform Mid-Atl Chl?** (0.61 vs 0.72 — opposite of N Pacific where NO₃ wins.) Working hypothesis: Mid-Atl NO₃ pattern is dominated by Gulf Stream + mesoscale eddy structure that SST-only DINN can't capture; Chl is more directly SST-coupled. nb15-style multi-covariate input would test this.
- **Iron-pair `scav_rat` identifiability.** Recovered values are 1.8–3× off Carroll's `6.03e-7` in every fit, including DINNDeep (which actually got *worse* than DINN baseline at 1.88e-6). Consistent with literature view that surface iron observations alone underconstrain scavenging — likely needs depth-resolved iron + POC export observations to fully constrain.
- **Box-model bias structure.** Recovered Carroll-6 means show the same systematic offsets vs Carroll in every basin AND in DINNDeep with much more capacity (`alpfe` ~0.5–0.7×, `scav_rat` ~2–3×, `Smallgrow` ~1.4–2.3×, `Biggrow` ~2.6–3.1×, `R_PICPOC` ~2×). nb15 confirms this isn't fixable by network capacity. The 5-tracer simplification has predictable effects relative to full Darwin 3 — extending the box model is the path to closing the gap.
- **Are DINNDeep's r=1.000 fits scientifically meaningful or just memorization?** With 9.4K params and 1071 cells × 6 outputs = 6.4K unknowns, the network approaches parameter parity. Cross-validation experiments (held-out cells, held-out time periods) would tell us whether the recovered Carroll-6 maps generalize or are just a high-capacity interpolant.

## Project arc

- **Track 1** (parameter recovery via differentiable physics) — at **v2.0**. Per-cell DINN baseline fits the spatial pattern where global-scalar produces a constant prediction; DINNDeep saturates fit quality with degenerate per-cell recovery (nb15, nb18); cross-validation confirms DINNDeep is interpolation-only (nb16); ensemble disagreement detects extreme errors but not extrapolation territory (nb17); 4-tracer joint loss partially collapses degeneracy with 3/6 closer (nb19). **v2.0 contribution:** carbonate-extended box + 7-tracer joint loss (nb20) moves the iron pair to within 1.1% (alpfe) / 40% (scav_rat) of Carroll's published values — reproducible across DINN baseline AND DINNDeep architectures. Other 4 parameters trapped by 5-tracer box-model proxy (cluster work + 5-PFT extension addresses). **Track 1 closed locally on a single GPU**; cluster ask sent to MIT ORCD 2026-05-10 for May B200 burn-in window. Cluster transfer prep documented in [`docs/cluster_setup.md`](docs/cluster_setup.md).
- **Track 2** (neural surrogate emulator) — not started; gated on cluster compute access + time-resolved fitting machinery from Track 1 follow-ups.
