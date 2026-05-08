# DarwinDiff — Research Decision Log

A pause before notebook 09 (real-data fit) to capture the decisions that have shaped the project so far. Organised by category, not chronology. Each entry: the decision, the rationale, and the consequences for downstream work. Updated as the project evolves.

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

**Rationale.** Confirmed on the 2026-05-07 call with Jonathan Lauderdale. These are the parameters the ECCO-Darwin team operationally calibrates; matching them with autodiff is the cleanest way to demonstrate DarwinDiff replicates Green's-functions on its own ground before extending. Carroll's published values give a known optimum to score against.

**Consequences.** Recovery numbers in notebooks 05/06/07 report against these six specifically. The 0-D box model in `src/darwindiff/carroll6.py` is built around these names. The Carroll 2020 paper is the bibliographic anchor for any future paper.

**Don't conflate** with BINN's 21-parameter target or with the ~103 independent scalars in the full Darwin 1 build — the six is specifically the Green's-functions calibration subset.

### A2. Implementation backend: Darwin 3 (ECCO-Darwin v5), not Darwin 1

**Decision.** DarwinDiff implements against Darwin 3 — the BGC core used by ECCO-Darwin v5 — not Darwin 1, the version Carroll 2020 ran.

**Rationale.** Darwin 3 is namelist-driven (parameters in `data.darwin` and `data.traits` rather than hardcoded Fortran), which makes parameter override at runtime tractable. Darwin 1's parameters live in `code_darwin/init_fixed.F` and require recompilation to change. Verified 2026-05-07 with Jonathan: ECCO-Darwin v5 uses Darwin 3, and that's the production target.

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

**Consequences.** The `src/darwindiff/` modules grow incrementally as the project finds out what's reusable. Networks (CarrollMLP from 06, CarrollCNN from 07) and budget calculators (from 08) are extracted in this branch (after the third use case made the abstractions clear). Loss functions, AOI mask generators, and data loaders stay inline in notebooks until the patterns settle.

### E2. Honest scope flags over forward promises

**Decision.** Every notebook explicitly flags what it does NOT yet demonstrate, and the closing markdown of each notebook lists open scope items that block downstream work.

**Rationale.** The project is a multi-step staircase to a real-world fit, and every step has gaps that the *next* step needs to close. Hand-waving past those gaps would weaken the scientific argument. The notebook 08 memory-budget correction (after a reviewer caught a bug in the checkpointed-memory model) is a concrete example: the un-corrected version claimed LLC270 multi-year fits B200, which would have been a misleading headline for the ORCD pitch.

**Consequences.** Every notebook ends with "What this scaffold does NOT demonstrate" and a list of open scope items. The pre-ORCD scoping in notebook 08 is the consolidated checklist of what blocks the move to real compute. This decision log itself is part of that pattern — capturing assumptions explicitly so they can be challenged.

---

## Open items not yet decided

- **Loss function for sparse vessel observations.** The current per-tracer-normalised MSE assumes dense observation grids. Real GEOTRACES / GO-SHIP data is sparse and irregular; the loss needs a sparse-tensor or masked-MSE form. Decision should land before notebook 09 codes the real-observation loss.
- **`scav_tau` units in Darwin 3.** The v06/llc270 namelist value is `1.0`, but Carroll's `scav_rat = 6.026e-7 /s` doesn't match under any obvious unit conversion. Resolution: grep `pkg/darwin/` for where `scav_tau` is consumed.
- **`PALAT[5, ?]` predator index for `diatomgraz`.** Diatom is prey index 5; Carroll's `diatomgraz` mapped to a specific zooplankton predator that needs source-reading to identify in Darwin 3's 10-plankton system.
- **Multi-GPU vs time-window decomposition** for LLC270 multi-year. Both are viable; the choice depends on what ORCD allocation looks like and how much engineering effort is available.
- **First-iteration optimiser for production fits.** Adam at lr=5e-3 worked for 06/07 with bounds and noise. For real data the Adam → LBFGS / quasi-Newton fine-tune pattern is standard but adds a phase to the training loop.

---

*Last updated: 2026-05-08, after notebook 08 (pre-ORCD scoping) and the checkpointed-memory correction.*
