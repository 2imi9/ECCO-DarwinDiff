# DarwinDiff — Project Status

*Living doc. Update as things ship.*

**Last updated:** 2026-05-10 (after cluster prep — notebook path-refactor + SLURM templates + v1.6 consolidated findings doc).

## Where we are in one line

Track 1 (parameter recovery) at **v1.6** — Carroll-6 recovery demonstrated against real ECCO-Darwin v5 output across 3 targets (Chl, NO₃, FeT) and 3 basins (Mid-Atlantic, North Pacific, Equatorial Pacific). Structural-ceiling argument holds in every fit. nb15 showed network capacity is not the recovery ceiling — box-model proxy bias is. nb16 cross-validation showed DINNDeep's r=1.000 is INTERPOLATION ONLY: random hold-out r=0.995 (passes), block hold-out r=0.301 (fails extrapolation). **nb17 tested ensemble disagreement (10 seeds full-AOI + 5 seeds block-CV) as an inference-time trust map — works as an outlier flag (Pearson +0.87 with |error|) but FAILS as an extrapolation detector (held-out stdev only 1.17× training stdev). nb16's r=0.301 is highly reproducible across seeds (0.278–0.358).** Cheap solutions (more seeds, more capacity) do NOT rescue the cross-basin gap; physics-constrained next phase is required. Track 2 (neural emulator) not started; Track 1 closed on local hardware, awaiting MIT cluster decision.

## Most important findings so far

1. **Carroll 2022 inherited Carroll 2020's calibrated 6-parameter values.** Verified against the v04 (Darwin 1, JAMES paper) and v05 (Darwin 3, GBC paper) source namelists — all six numbers `(alpfe=0.92831, scav_rat=6.025e-7, Smallgrow=0.66098, Biggrow=0.43148, diatomgraz=0.83003, R_PICPOC=0.04245)` are bit-for-bit identical between the two versions.

2. **Structural-ceiling argument is universal.** In every fit (notebooks 09–14), the global-scalar Green's-functions parametric class produces a constant prediction (`r = undefined`, mathematically inevitable for one parameter vector + uniform initial state). DINN per-cell finds a non-trivial r in every fit. Not target-specific or basin-specific.

3. **N Pacific NO₃ is the strongest single-fit result among the SST-only DINN baseline** — `r = 0.979`, loss ratio Global / DINN = **23.8×**. Demonstrates that the structural ceiling can be quantitatively dramatic in regions with smooth, SST-coupled BGC.

4. **Cross-basin parameter consistency.** Recovered Carroll-6 values are stable across basins (within ~25% across Mid-Atl + N Pacific + Eq Pacific). The same systematic offsets appear vs Carroll's published optima in every basin — suggests the 5-tracer box-model proxy creates basin-independent biases (not random fitting noise). Stronger claim than any individual fit because it shows reproducibility.

5. **`alpfe` converges on Carroll's published 0.928** as we use targets that better constrain the iron pair. Eq Pacific FeT global-scalar fit recovers `alpfe = 0.959` (3% off Carroll). Iron-replete-basin Chl fits recovered `alpfe ≈ 0.5–0.6` (much further off) because Chl pattern in those basins doesn't depend on iron parameters.

6. **Best target depends on basin physics**, not just on Carroll's calibration choices. Mid-Atl: Chl `r=0.72` > NO₃ `r=0.61`. N Pacific: NO₃ `r=0.98` > Chl `r=0.97`. Likely reflects Mid-Atl NO₃ being dominated by Gulf Stream / mesoscale eddy structure that an SST-only DINN can't capture.

7. **Network capacity ≠ better Carroll-6 recovery (nb15).** Multi-channel input (SST + MLD + wind + lat) into a deeper network (DINNDeep, ~9.4K params, 21× the baseline) drives Eq Pacific FeT r from 0.337 → **1.000** and reduces loss ~3000×. But recovered Carroll-6 means are NOT closer to Carroll's published values (some are worse). The fit memorizes the FeT pattern via degenerate parameter sets that produce the right field but don't match the published calibration. **The recovery ceiling is the box-model proxy simplification, not the network architecture.**

8. **DINNDeep's r=1.000 is interpolation, not extrapolation (nb16).** Cross-validation confirms: random 80/20 hold-out gives held-out r=**0.995** (passes — interpolating gaps works), but block hold-out (western 2/3 train, eastern 1/3 test) gives held-out r=**0.301** (fails — can't extrapolate to unseen spatial blocks). DINNDeep is not memorizing in the trivial sense, but it IS learning a function that's smooth across the training set without extrapolating beyond it. **For cross-basin claims (e.g., training on Mid-Atl, applying to N Pacific), DINNDeep is unreliable; the SST-only DINN baseline is the more honest tool because it has less interpolation capacity to lean on.**

9. **Ensemble disagreement is a tail-detector, not an extrapolation-flag (nb17).** A 10-seed DINNDeep ensemble on full Eq Pacific FeT shows Pearson r(per-cell stdev, |error|) = **+0.87** — high-disagreement cells coincide with high-error cells (useful outlier flag). But Spearman ρ = **−0.42** — opposite sign — meaning within the well-predicted bulk, rank order between stdev and |error| is inverted. Practical takeaway: ensemble stdev is a usable *flag for cells with extreme errors*, not a fine-grained quality ranking. A separate 5-seed ensemble trained on western 2/3 only (replicating nb16's block-CV) shows held-out stdev is only **1.17×** training stdev (Mann-Whitney p=1.4e-10, significant but tiny effect) — **the ensemble is overconfident in extrapolation territory.** nb16's r=0.301 is highly reproducible across these 5 seeds (per-seed: 0.278, 0.288, 0.301, 0.330, 0.358) — not noise. **Cheap solutions (more seeds, more capacity) do NOT rescue the cross-basin gap; the next phase has to be physics constraints (carbonate-extended box model + multi-tracer joint loss + cluster compute), not more network capacity.**

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

### Decisions and scope locked

- [x] Active calibration target = Carroll 2022 / Darwin 3 / v05 (publicly-accessible run; Carroll 2020 / Darwin 1 / v04 retained as historical reference, calibrated values are identical anyway)
- [x] AOIs = Mid-Atlantic + North Pacific + Equatorial Pacific
- [x] Per-cell architecture (1×1 conv backbone) for Track 1 — preserves the structural argument cleanly
- [x] Box model stays as 5-tracer carroll6 proxy (no carbonate chemistry, no separate PFTs) for Track 1; extension is now a higher-priority follow-up given nb15's box-model-bias finding

## In progress / next

### Highest priority (nb15 reordered the queue)

- [ ] **Box-model extension** to add DIC + ALK + carbonate chemistry. nb15 showed that network architecture is no longer the recovery ceiling — the 5-tracer simplification is. Extending the box model is the path to actually matching Carroll's published values rather than producing degenerate solutions that fit the FeT field. Enables fitting Darwin's air-sea CO₂ flux pattern directly (closer to what Carroll 2022 was actually calibrated against).
- [ ] **Multi-tracer joint loss** (NO₃ + Chl + DIC + FeT simultaneously). Should reduce the degeneracy nb15 exposed by giving DINN multiple loss surfaces to satisfy at once.

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

- **Track 1** (parameter recovery via differentiable physics) — at **v1.6**, four basin-target combinations validated, structural-ceiling argument established, architecture upgrade tested + cross-validated, ensemble-disagreement trust map evaluated (works as outlier flag, fails as extrapolation detector — nb17). **Closed on local hardware**; pending MIT cluster decision before next phase (box-model carbonate extension + multi-tracer joint loss + Track 2). Cluster transfer prep documented in [`docs/cluster_setup.md`](docs/cluster_setup.md).
- **Track 2** (neural surrogate emulator) — not started; gated on cluster compute access + time-resolved fitting machinery from Track 1 follow-ups.
