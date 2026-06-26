# DarwinDiff — Research Decision Log

A pause before notebook 09 (real-data fit) to capture the decisions that have shaped the project so far. Organised by category, not chronology. Each entry: the decision, the rationale, and the consequences for downstream work. Updated as the project evolves.

!!! warning "2026-06-26 update — the forward-looking conclusions below are superseded"
    This is a **dated log** (Track 1 v1.5 close, 2026-05-09); its design-decision *history* is accurate, but its *forward-looking* conclusions (sections F4–F6 and "next priority") have since been overturned:

    - **`R_PICPOC` was recovered** at the box scale by anchoring to a real, Darwin-independent CP:PP ratio (Daniels 2018, ≥2-AOI 50/50). The "needs the DIC+ALK / calcite port + native resolution" thesis is **refuted** — the port gives a flat box-scale PIC:POC and native resolution does not unblock it.
    - **The iron pair is real-data validated** vs GEOTRACES IDP2025; the (`alpfe`, `scav_rat`) "degeneracy" is a **loss-weighting artifact**, not structural (FIM/profile: `alpfe` 0.103 full-loss vs 0.9997 ≈Carroll under real iron).
    - The **active** cluster is **NU Explorer (H200)**, not MIT ORCD.

    Read the original entries below as 2026-05 history. Current state: [Project Status](status.md).

---

## A. Scientific scope

### A1. Test target: the six Carroll et al. 2020 (JAMES) parameters

**Decision.** Track 1's evaluation target is exactly the six parameters Carroll calibrated through Green's functions in the original ECCO-Darwin paper:

- `alpfe` (iron dust solubility)
- `scav_rat` (iron scavenging rate)
- `Smallgrow` (small phytoplankton growth rate)
- `Biggrow` (large phytoplankton growth rate)
- `diatomgraz` (diatom palatability)
- `R_PICPOC` (PIC/POC ratio)

**Rationale.** Confirmed via discussion with the ECCO-Darwin team. These are the parameters the team operationally calibrates; matching them with autodiff is the cleanest way to demonstrate DarwinDiff replicates Green's-functions on its own ground before extending. Carroll's published values give a known optimum to score against.

**Consequences.** Recovery numbers in notebooks 05/06/07 report against these six specifically. The 0-D box model in `src/darwindiff/carroll6.py` is built around these names. The Carroll 2020 paper is the bibliographic anchor for any future paper.

**Don't conflate** with BINN's 21-parameter target or with the ~103 independent scalars in the full Darwin 1 build — the six is specifically the Green's-functions calibration subset.

### A2. Implementation backend: Darwin 3 (ECCO-Darwin v5), not Darwin 1

**Decision.** DarwinDiff implements against Darwin 3 — the BGC core used by ECCO-Darwin v5 — not Darwin 1, the version Carroll 2020 ran.

**Rationale.** Darwin 3 is namelist-driven (parameters in `data.darwin` and `data.traits` rather than hardcoded Fortran), which makes parameter override at runtime tractable. Darwin 1's parameters live in `code_darwin/init_fixed.F` and require recompilation to change. Confirmed via the ECCO-Darwin team that v5 uses Darwin 3 — that's the production target.

**Consequences.** The Carroll-six parameter *names* are the science target, but their Darwin 3 namelist mapping is a separate engineering exercise. Notebook 08 documents the verified mapping (4 of 6 closed; `scav_tau` units and `PALAT[5,?]` predator index still open). Carroll's Darwin 1 *values* are still the published anchor for benchmarking, but production fits will produce Darwin 3 namelist values, which may differ from Carroll's optima after the Darwin 1 → Darwin 3 algorithmic changes.

### A3. Areas of interest: Mid-Atlantic + Pacific

**Decision.** The two AOIs for the real-data fit are the Mid-Atlantic and the Pacific.

**Rationale.** Confirmed 2026-05-07 by Lucas. These regions have the densest vessel-recorded observations (ship-based pCO2, GO-SHIP repeat hydrography, GEOTRACES iron transects, BGC-Argo floats), so the loss term against vessel observations carries the strongest signal there. They also span a meaningful biogeochemistry contrast (Mid-Atl is dust-replete and productive; Pacific subtropical gyre is iron-limited and oligotrophic) — exactly the regional heterogeneity that distinguishes per-cell ML from global-scalar Green's-functions.

**Consequences.** Notebook 06's two-regime synthetic benchmark uses these AOIs as labels. Notebook 09 will subset real LLC270 output to these regions. Vessel observation acquisition (Item 5 in the pre-ORCD checklist) is scoped to these AOIs first; global expansion is later.

---

## B. Methodology

### B1. Per-cell ML predicts parameters from environmental covariates

**Decision.** The structural differentiator from Green's-functions calibration is **per-cell parameter values predicted by a neural network from local environmental covariates** (SST, MLD, dust flux, surface PAR, etc.).

**Rationale.** Green's-functions produces *one global scalar set per parameter for the entire ocean*. ECCO-Darwin's published calibration treats `alpfe`, `Smallgrow`, etc. as single numbers applied uniformly. Real biogeochemistry is heterogeneous — `alpfe` should be higher under Saharan dust and lower in the Pacific subtropical gyre, `Smallgrow` should depend on temperature, etc. A network over local covariates can represent this heterogeneity by construction; Green's-functions cannot, even given infinite compute, because the parametric class is wrong.

**Evidence.** Notebook 06 demonstrates this quantitatively: on a synthetic two-regime setup, a covariate-conditioned MLP beats the global-scalar fit by **15.2× on per-region recovery error**. The global-scalar fit's loss plateaus at the regional-mean LSE solution, which is the structural ceiling of any approach restricted to one global scalar per parameter.

**Consequences.** Every production fit beyond notebook 05 uses some form of covariate-conditioned network: MLP for regional setups (notebook 06), 1×1-conv "per-cell MLP" for spatial fields (notebook 07), and CNN-with-spatial-coupling for the LLC270 production work (notebook 09+). Network capacity stays small intentionally — the win comes from *what the parameters can be conditioned on*, not from network size.

### B2. Synthetic-truth-first validation, real-data fit later

**Decision.** Notebooks 05–08 use synthetic ground-truth (run the box model with a known parameter vector → noisy snapshots → fit the parameters back). Real ECCO-Darwin output and real vessel observations enter at notebook 09.

**Rationale.** Synthetic data lets us score recovery against a known optimum, which is impossible on real data. It validates that the algorithmic scaffold (autograd through the simulator + parameter learner + Adam) actually works before we trust it on observations where we cannot directly check correctness. This is the standard validation pattern from BINN, PINN, and other differentiable-physics work.

**Consequences.** All success metrics in 05/06/07 are recovery RMSE against synthetic truth. They demonstrate the methodology *can* work; they do not yet demonstrate it *does* work on real data. Notebook 09 is the bridge — same scaffold, same parameter learner, but observations come from ECCO-Darwin v5 output and (eventually) real vessel data.

### B3. 50-day spin-up, five trajectory snapshots — observation timing matters more than epoch count

**Decision.** Synthetic observations are sampled at five evenly-spaced times through a 50-day forward integration, not at a single steady-state endpoint. The 50-day window is short enough to keep the iron pool in transient.

**Rationale.** Notebook 05 originally used a 200-day spin-up and observed only the final state. Recovery failed for the iron pair (`alpfe`, `scav_rat`) and underperformed for the growth pair (`Smallgrow`, `Biggrow`) because at steady state, `alpfe × dust_source = scav_rat × DFe × POC` admits a continuous family of `(alpfe, scav_rat)` pairs that produce the same DFe — a product degeneracy. Observations during the iron transient (before equilibrium) constrain the *rate of approach to steady state*, which depends separately on each parameter and breaks the degeneracy. Switching from 200 days to 50 days dropped iron recovery from "stuck at midpoint init" to single-digit %.

**Consequences.** The same observation-timing principle should drive notebook 09's vessel-observation alignment: prefer time-resolved observations (BGC-Argo daily profiles, repeat ship sections) over climatologies (annual-mean GLODAP). This matches the [notebook 4 finding](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/notebooks/04_4param_identifiability.ipynb) that **identifiability is per-parameter and per-observation-type, not a global property of the model**.

### B4. Sigmoid-bounded parameter learning over physical ranges

**Decision.** Parameters are learned as unconstrained `theta ∈ ℝ^N` and mapped to physical ranges via sigmoid: `param = lo + (hi - lo) × sigmoid(theta)`.

**Rationale.** Physical parameters (rates, fractions, dimensionless ratios) are positive and bounded. Sigmoid bounding enforces this by construction without clipping or projection, and the gradient remains continuous everywhere. The bounds come from the per-parameter physically-plausible ranges (e.g. `alpfe ∈ [0.05, 1.0]`, `scav_rat ∈ [3e-8, 3e-6]`).

**Consequences.** `bounded_params` is a tiny utility used by every fit in 05/06/07. The bounds (`PARAM_BOUNDS`) live in `src/darwindiff/carroll6.py` alongside the box model. For the 2-D case (`theta` shape `[6, H, W]`), `bounded_params` broadcasts naturally — no separate function needed.

---

## C. Architecture

### C1. 0-D box model with five tracers as the canonical scaffold

**Decision.** The scaffold for notebooks 05–07 is a 0-D Fe–phyto–POC–PIC box model with five prognostic tracers (DFe, P_s, P_l, POC, PIC). Real ECCO-Darwin has 39 tracers; the box model is a deliberately simplified proxy.

**Rationale.** Each Carroll-6 parameter has a primary effect on a distinct observable in this setup: `alpfe` → DFe steady-state; `scav_rat` → DFe sensitivity to POC; `Smallgrow` → P_s; `Biggrow` → P_l; `diatomgraz` → P_l grazing loss; `R_PICPOC` → PIC/POC ratio. This is the smallest viable system that exposes the six knobs with one observable each, so identifiability is well-posed without a full 3-D model. Background defaults (mortality, grazing, sinking) match the ~94 % of Darwin parameters Carroll left at expert defaults.

**Consequences.** The box model lives in `src/darwindiff/carroll6.py`. Notebooks 05/06/07 all import and use it; notebook 09 will replace its forward integration with real ECCO-Darwin output, but the parameter targets and bounds stay the same. The five-tracer state is enough to score recovery; it is not a faithful replica of ECCO-Darwin and never claims to be.

### C2. Forward-Euler explicit integration

**Decision.** All time integration is explicit forward Euler: `state_{t+1} = state_t + dt × dstate/dt`.

**Rationale.** Forward Euler is the simplest possible integrator: every operation is element-wise, the autograd graph is transparent, and the recompute cost for gradient checkpointing is well-defined (one extra forward pass per checkpoint segment). Higher-order methods (RK4, leap-frog, implicit solvers) are deferred — they buy stability margin but complicate the autograd graph and the memory profile, which is already the binding constraint at scale.

**Consequences.** Stability is bounded by `dt × max_rate < 1` for the explicit scheme. With `max_rate ~ 0.6 /day` (set by `Smallgrow` upper bound), `dt = 0.25 day` gives a safety factor of 7×. For real ECCO-Darwin coupling (advection + sinking + reaction) the stability constraint is tighter and may force smaller `dt`, which compounds the autograd-graph depth — relevant for the memory budget in notebook 08.

### C3. Per-cell, no spatial coupling in the scaffold

**Decision.** Notebook 07's box model evolves every grid cell independently. There is no advection, no diffusion, no biological communication between cells.

**Rationale.** Spatial coupling adds a sparse stencil (a 5-point Laplacian for diffusion, or upwind for advection) that needs a real velocity / mixing field. For synthetic-truth validation, element-wise evolution is sufficient: each cell's recovery is independent, and the per-cell network correctly learns the per-cell mapping. Spatial coupling enters when ECCO-Darwin's velocity / κ fields enter (notebook 09+).

**Consequences.** `carroll6_step` works batched over arbitrary trailing dimensions because every operation is element-wise. The function signature didn't have to change between notebook 05 (state shape `[5]`) and notebook 07 (state shape `[5, H, W]`) — broadcast handles it. Adding spatial coupling will require a new `carroll6_step_with_advection` or similar; the existing function stays for the no-coupling case.

### C4. 1×1 convolutions for the per-cell network in 2-D

**Decision.** The per-cell network in notebook 07 is a stack of 1×1 convolutions, equivalent to a per-cell MLP applied in parallel across the grid: `Conv2d(3, 16, 1) → Tanh → Conv2d(16, 16, 1) → Tanh → Conv2d(16, 6, 1)`.

**Rationale.** The truth in notebook 07 has each cell's parameters as a function of *that cell's* covariates, not its neighbours. 1×1 kernels match this structure exactly — no spatial smoothing, just per-cell mapping. An earlier draft used 3×3 convs; recovery failed because the 3×3 receptive field was leaking spatial info that fought the per-cell truth, and the optimiser plateaued at a "constant prediction" local minimum. Switching to 1×1 fixed this.

**Consequences.** When real ocean spatial structure enters (notebook 09+), the network architecture should be revisited — at that point per-cell may not be sufficient, and a small CNN with non-trivial receptive field (or an MLP-mixer-style architecture) may be appropriate. The 1×1 baseline is the cleanest comparison point.

### C5. Per-tracer normalized loss

**Decision.** The loss function is mean-squared error normalised by per-tracer mean: `((pred - obs) / tracer_mean) ** 2`, summed over snapshots and tracers, then meaned.

**Rationale.** The five tracers span ~5 orders of magnitude (DFe ~ 1e-4 mmol/m³; POC ~ 1 mmol/m³). Without per-tracer normalisation, the largest-magnitude tracer dominates the gradient and the optimiser ignores the others. Normalising by the truth-mean per tracer puts each tracer's residual into the same relative-error space, so each contributes comparably regardless of scale.

**Consequences.** The loss is reported as relative MSE; the noise floor for 1 % obs noise is ~1e-4. For real vessel observations the normalisation should be by observation uncertainty (so cleaner data carries more weight), not by mean — that is the standard inverse-problem cost form and an obvious upgrade for notebook 09+.

---

## D. Compute and scaling

### D1. Notebook 07 is the final CPU-vs-GPU side-by-side benchmark

**Decision.** From notebook 08 onward, all configurations are GPU-only by design.

**Rationale.** Notebook 07's benchmark at 128² grid showed GPU-vs-CPU at 1.2× — both devices are dispatch-bound at that scale (16 K cells, 64 KB tensors, kernel-launch overhead dominates). At larger scales the CPU baseline becomes infeasible (~30 min at 1024², multi-day at LLC270 spatial coupling), and CPU/GPU parity is no longer a useful question. The threshold-scale benchmark in 07 documents the dispatch-bound regime; notebook 08+ scales up on GPU only.

**Consequences.** Future notebooks will not include CPU baselines. The compute argument for ORCD lives in (a) the regime extrapolation in notebook 08's GPU per-op cost model and (b) the eventual demonstration of clean GPU wins at 1024²+ — neither of which requires running CPU comparisons.

### D2. Gradient checkpointing is required, not optional, for production fits

**Decision.** Every notebook from 09 onward uses `torch.utils.checkpoint.checkpoint_sequential` for the forward integration loop.

**Rationale.** The activation memory budget in notebook 08 shows that even an AOI patch (~1.5 M cells × 30 daily timesteps × 39 tracers, no checkpointing) lands at ~65 GB — exceeds a 5090's 24 GB. With segment-5 checkpointing it drops to ~13 GB and fits the laptop comfortably. The same pattern recurs at every scale up. Gradient checkpointing is not an optimisation; it is required for the memory budget to close.

**Consequences.** The training loop template in `src/darwindiff/training.py` (TBD) will checkpoint the forward integration by default. Reproducibility note: checkpointing does *not* change numerics — same seed, same losses to fp32 precision; it only changes memory/time tradeoff.

### D3. Multi-GPU or time-window decomposition for global multi-year autograd

**Decision.** Production global LLC270 fits over multi-year periods cannot use single-GPU autograd, even on B200 with aggressive checkpointing. The two viable paths are **multi-GPU activation parallelism** (the same autograd graph distributed across GPUs) or **time-window decomposition** (compute and accumulate gradients month-by-month, no autograd across windows).

**Rationale.** Notebook 08's corrected memory budget shows global LLC270 1-year daily autograd at ckpt@5 lands at ~214 GB, exceeding B200's 192 GB. The boundary-state count `(T/K) × state_bytes = 73 × 1.87 GB ≈ 137 GB` dominates, and the optimum K is bounded — checkpointing alone cannot rescue this scale.

**Consequences.** Architectural decision needed before the production training loop is written. Time-window decomposition is simpler infrastructure but trades off gradient signal across windows (cannot capture inter-month dependencies in the cost). Multi-GPU is more compute-flexible but adds complexity (NCCL, activation parallelism choreography). Initial recommendation: time-window decomposition for the first production run, multi-GPU when the methodology is solid.

### D4. Force CPU for small-tensor work; GPU for production scale

**Decision.** Notebooks 05 and 06 force `device = "cpu"` despite GPU availability; notebook 07 reports both; notebooks 08+ are GPU-only.

**Rationale.** At 5-element state tensors (notebooks 05, 06), every PyTorch op pays ~5 µs CUDA kernel-launch overhead while doing ~1 ns of arithmetic — GPU is 99.9 % overhead. CPU has no equivalent dispatch tax, just Python overhead which is much smaller per op. At 16 K-element tensors (notebook 07) the launch overhead amortises slightly and the gap closes to 1.2×. At 1 M+ elements GPU wins decisively because memory bandwidth dominates and GPU's HBM advantage takes over.

**Consequences.** The lesson is general: don't reach for GPU just because it's available. The right device depends on the *width of the work inside the hot loop*, and for differentiable physics the hot loop is the per-timestep box-model evaluation. Per-cell width is what wins, not network capacity or epoch count.

---

## E. Process

### E1. Inline-then-extract refactoring

**Decision.** Notebooks initially keep box-model and helper code inline; they get extracted to `src/darwindiff/` once the equations and APIs stabilise.

**Rationale.** Notebook 05's first draft had `carroll6_step` defined inline. After it was used unchanged in notebooks 06 and 07, the code was clearly stable enough to refactor — at that point `src/darwindiff/carroll6.py` was created and tested. Premature extraction (refactoring on the first use) creates churn when the API turns out to need changes for the second use case.

**Consequences.** The `src/darwindiff/` modules grow incrementally as the project finds out what's reusable. Networks (`DINNRegional` from 06's MLP, `DINN` from 07's per-cell 1×1-conv — both following the BINN-family naming convention, "Darwin-Informed Neural Network") and budget calculators (from 08) are extracted in this branch (after the third use case made the abstractions clear). Loss functions, AOI mask generators, and data loaders stay inline in notebooks until the patterns settle.

### E2. Honest scope flags over forward promises

**Decision.** Every notebook explicitly flags what it does NOT yet demonstrate, and the closing markdown of each notebook lists open scope items that block downstream work.

**Rationale.** The project is a multi-step staircase to a real-world fit, and every step has gaps that the *next* step needs to close. Hand-waving past those gaps would weaken the scientific argument. The notebook 08 memory-budget correction (after a reviewer caught a bug in the checkpointed-memory model) is a concrete example: the un-corrected version claimed LLC270 multi-year fits B200, which would have been a misleading headline for the cluster compute proposal.

**Consequences.** Every notebook ends with "What this scaffold does NOT demonstrate" and a list of open scope items. The pre-ORCD scoping in notebook 08 is the consolidated checklist of what blocks the move to real compute. This decision log itself is part of that pattern — capturing assumptions explicitly so they can be challenged.

### E3. Real-data-only code direction (post-2026-05-08)

**Decision.** With ECCO-Darwin v5 LLC270 output confirmed publicly available at `https://data.nas.nasa.gov/ecco/eccodata/llc_270/ecco_darwin_v5/`, the project transitions from synthetic-truth scaffolding to real-data fits. Code that only exists to support synthetic-recovery validation is removed from the repo.

**Removed:**

- `src/darwindiff/prototype/` — toy 1-D reaction-diffusion + synthetic NPZ scaffolding that supported notebooks 01–04. Notebooks 01–04 themselves stay in `notebooks/` with their committed outputs; their pre-cleanup commits (e.g., `8d465ce` and earlier) preserve the prototype module if anyone needs to re-run them.
- `src/darwindiff/carroll6.generate_synthetic_observations` and `train_global_recovery` — synthetic-data helpers used only for the box-model unit tests. The box-model physics functions (`carroll6_step`, `carroll6_integrate`, `bounded_params`, constants, `PARAM_BOUNDS`, `PARAM_NAMES`, `CARROLL_VALUES`) all stay.
- `tests/test_4param_recovery.py`, `test_coupled_recovery.py`, `test_multiparam_recovery.py`, `test_prototype_recovery.py` — synthetic-recovery tests for the prototype module.
- `tests/test_carroll6_recovery.py::test_carroll6_recovery_matches_published_optimum` — the single end-to-end synthetic-truth recovery test in the carroll6 file. The 4 smoke / integration / autograd / bounds tests in that file stay; they exercise the math, not synthetic observations.

**Kept (the production-relevant test suite):**

- 4 box-model smoke tests in `test_carroll6_recovery.py` (single-step finite, integration stable at truth, autograd flows to all six, bounds respected).
- 13 network tests in `test_networks.py` (DINN / DINNRegional shapes, per-cell isolation, bounded-params batched cases, autograd flow).
- 13 budget tests in `test_budget.py` (per-op cost regimes, activation-memory under checkpointing, fits-on-GPU boolean).

**Rationale.** Synthetic-recovery tests served their purpose during methodology validation (notebooks 05–07): we verified autograd works, gradients reach all parameters, the algorithm converges from a cold start, etc. With those facts established, the relevant question shifts to *does the methodology survive on real data?* — and that question is answered by notebook 09+ running against actual ECCO-Darwin output, not by synthetic-truth unit tests. Keeping dead synthetic-only code in the repo would obscure which paths are production-relevant.

**Consequences.** Notebooks 01–04 lose import support from `main` after the cleanup commit lands (their committed outputs are preserved; re-execution requires `git checkout` to a pre-cleanup commit). The `darwindiff` package focus narrows to: `carroll6` (Darwin BGC physics, the simulator), `networks` (DINN / DINNRegional, the parameter learner), `budget` (compute and memory sizing for the cluster compute proposal). Test count drops from ~30 to ~21, but every remaining test exercises code on the production path.

---

## F. Real-data fits (Track 1 v1.0 → v1.5, 2026-05-09)

### F1. Carroll 2022 / Darwin 3 / v05 chosen as active calibration target

**Decision.** Frame Track 1's recovery target as Carroll 2022 (Darwin 3, ECCO-Darwin v05), not Carroll 2020 (Darwin 1, v04). Carroll 2020 retained as historical reference.

**Rationale.** Verified by reading the source namelists at `MITgcm-contrib/ecco_darwin/v04/llc270_JAMES_paper/code_darwin/{darwin_init_fixed.F, darwin_generate_phyto.F}` and `v05/llc270/input/data.darwin`: the 6 calibrated values are **bit-for-bit identical** between v04 and v05 (`alpfe=0.92831, scav_rat=6.025e-7, Smallgrow=0.66098, Biggrow=0.43148, diatomgraz=0.83003, R_PICPOC=0.04245`). The v05 setup uses Darwin 3 with new ecosystem features but inherits Carroll 2020's calibration unchanged. Choosing v05 as the framing target lets us reference the publicly-accessible run (NASA NAS portal serves only v05) without giving up any calibration accuracy.

**Consequences.** All notebook 10+ work fits against v05 outputs. Carroll 2020 / Darwin 1 / v04 gets a single mention in `STATUS.md` and `reference_carroll_2020.md`; everything active points at Carroll 2022 / v05.

### F2. Per-cell architecture is the structural-argument-preserving choice

**Decision.** All Track 1 fits use 1×1 conv backbones (no spatial coupling between cells). Larger receptive fields (3×3+, attention) are deferred to Track 2.

**Rationale.** The DarwinDiff scientific claim is structural: a single global parameter vector cannot reproduce spatial heterogeneity in ocean BGC, but per-cell parameters can. Quantifying that claim cleanly requires the comparison "global-scalar (0 spatial info) vs DINN per-cell (1 cell of spatial info)" — adding receptive field would let the DINN cheat by averaging neighbours, conflating the parametric-class advantage with a smoothing advantage.

**Consequences.** Notebooks 09–16 all use 1×1 conv. The DINN baseline (~454 params, SST input only) and DINNDeep upgrade (~9.4K params, 4-channel input) both keep this constraint. ViT / FNO / graph-net architectures are reserved for Track 2 emulator work where spatial coupling is physically required (advection / diffusion).

### F3. Three-AOI cross-basin validation as the reproducibility argument

**Decision.** Validate Track 1 across Mid-Atlantic (30–50°N, 60–30°W), North Pacific (30–50°N, 160–130°W), and Equatorial Pacific (5°S–15°N, 160°W–110°W) AOIs.

**Rationale.** Three basins with different physics (Gulf Stream complexity vs gyre interior vs HNLC equatorial upwelling) test whether the recovery methodology is regionally idiosyncratic or genuinely reproducible. Eq Pacific specifically targets iron-pair (`alpfe`, `scav_rat`) identifiability that's structurally absent in iron-replete basins.

**Consequences.** Notebooks 11 (Mid-Atl + N Pacific Chl), 13 (same two basins, NO₃ target), 14 (Eq Pacific FeT) cover the matrix. Cross-basin parameter consistency emerged as a stronger scientific argument than any single fit — recovered Carroll-6 means stay within ~25% across basins with the same systematic offsets vs Carroll's published values, suggesting box-model proxy bias is basin-independent.

### F4. Box-model proxy bias is the recovery ceiling, not network capacity (nb15)

**Decision.** Highest-priority follow-up is extending the 5-tracer carroll6 box model with carbonate chemistry (DIC + ALK), not further architecture work.

**Rationale.** Notebook 15 trained DINNDeep (~9.4K params, 4-channel input — 21× the baseline DINN) on Eq Pacific FeT. r jumped from 0.337 to **1.000** with ~3000× lower loss, but recovered Carroll-6 means did NOT get closer to Carroll's published values (some got worse). The network finds *a* per-cell parameter set that reproduces Darwin's FeT field, but it's a degenerate solution — many (alpfe, scav_rat) pairs produce the same surface DFe at steady state. The ceiling on Carroll-6 recovery is the 5-tracer simplification (which collapses Darwin 3's 5 PFTs + 2 zoo + DOM + carbonate chem into Ps + Pl + POC + PIC + DFe), not the network's representational capacity.

**Consequences.** Future architecture work for Track 1 has diminishing returns — we're at the proxy ceiling. Box-model extension to add DIC + ALK + carbonate equilibria + Wanninkhof flux unblocks the path to actually matching Carroll's published values AND enables fitting Darwin's air–sea CO₂ flux pattern directly. Tracked in STATUS.md "next" section as the top priority.

### F5. DINNDeep generalises by interpolation, not extrapolation (nb16)

**Decision.** DINNDeep is the production architecture WITHIN a single AOI; SST-only DINN baseline remains the honest tool for cross-basin claims.

**Rationale.** Notebook 16 cross-validation: DINNDeep trained on 80% random subset of Eq Pacific cells gives held-out r=0.995 (interpolation passes) but trained on western 2/3 with eastern 1/3 held out gives held-out r=0.301 (extrapolation fails). The network learns a function smooth across the training set without extrapolating to unseen spatial blocks. Random hold-out works because every held-out cell has neighbours in the train set; block hold-out fails because the eastern third's environment occupies regions of feature space the network never trained on.

**Consequences.** Cross-basin DINNDeep results would need their own per-basin training; cannot assume DINNDeep trained in Mid-Atl applies to N Pacific without separate validation. For the broad cross-basin reproducibility argument, the lower-capacity DINN baseline (notebooks 11, 13) is more honest because it has less interpolation slack to mask extrapolation failure.

### F6. Stop on local single-GPU at Track 1 v1.5; cluster compute needed for next phase

**Decision.** Track 1 closes on local RTX 5090 hardware after notebook 16. Box-model carbonate extension, multi-tracer joint loss at LLC270 native resolution, time-resolved fitting, and Track 2 emulator all require cluster compute (MIT ORCD or similar).

**Rationale.** A 1500-epoch DINN per-cell training run on a 1° AOI (~600–1000 cells) takes 7–8 minutes on the 5090. Scaling to LLC270 native (11.7× more cells per AOI) gives ~80 min per fit. Multi-tracer joint loss is 4–8× per-epoch cost. Time-resolved fitting (all 285 monthly snapshots) is 285× single-snapshot cost per epoch. Combinatorially these will saturate the 5090.

**Consequences.** Track 1 status is "v1.5 closed locally, awaiting cluster decision". Next phase deliverables (box-model extension validation, multi-tracer joint loss, Track 2 emulator) are listed in STATUS.md "next" section and are gated on cluster access. The next-phase compute proposal — consolidated nb10–16 results plus cluster allocation request — is the next external action.

---

## Open items not yet decided

- **Multi-covariate + temporal input experiments** for the next round. SST + MLD + wind + lat in nb15 was a chosen quartet; other natural additions are SSS, irradiance (PAR), bathymetry, sea-ice fraction, distance-to-coast. The marginal improvement per added channel is unknown.
- **Loss function for sparse vessel observations.** Future GEOTRACES iron-section fits will need a sparse-tensor or masked-MSE form. Not blocking current work.
- **`scav_tau` units in Darwin 3.** Resolved for v05 (still `scav_rat`, same name as v04). Open for v06 setup, which uses `scav_tau`. Defer until/unless we target v06.
- **`PALAT[5, ?]` predator index for `diatomgraz`.** Resolved for v05 (`diatomgraz` is a direct scalar, no PALAT-matrix decoding needed). Same v06 deferral applies.
- **Multi-GPU vs time-window decomposition** for LLC270 native fits — gated on cluster access decision.
- **First-iteration optimiser for production fits.** Adam at lr=5e-3 has worked across 09–16. Adam → LBFGS fine-tune pattern is standard but adds a training-loop phase; defer until cluster fits start.

---

*Last updated: 2026-05-09, after notebook 16 cross-validation (Track 1 v1.5 close on local hardware).*
