Read enough. The code confirms the brief's claims: `carroll6_ude_tendency` already has `ffe_closure` and `calcite_closure` hooks, `integrate()` has RK4 + `checkpoint_segment`, `relative_mass_drift` exists in integrators.py. This is a 0-D box today; Phase 1 extends the same tendency-function interface to 3-D offline transport. Here is the design brief.

---

# PHASE-1 DESIGN BRIEF â€” Differentiable Offline-Transport UDE

**Scope of Phase 1:** Take the existing 0-D `carroll6_ude_tendency` + checkpointed `integrate()` machinery to a 3-D regional AOI (one v05 subregion) with prescribed ECCO-Darwin velocities, learn **environment-conditioned closures** (iron limitation and calcite/PIC:POC), and pass three make-or-break gates: held-out real-data RÂ²>0, bounded decadal mass drift, and out-of-envelope physical realism. Everything below is the *differentiable* version of the already-proven MITgcm-offline configuration that produced v05 â€” we inherit its conservation and physics, and add only the autograd path.

---

## 1. Transport operator

**THE decision:** Operator-split, flux-form finite-volume on the prescribed v05 grid velocities, differentiated by ordinary PyTorch autograd. Concretely:
- **Advection:** explicit, flux-form **centered-2nd** + small explicit biharmonic/Laplacian horizontal diffusion for smoothing. Conservative by construction (face fluxes telescope), fully smooth for autograd, CFL-cheap. **Defer superbee/TVD.** If false extrema appear, upgrade to a *smooth, eps-guarded* limiter (tanh-blended minmod/superbee) â€” never raw `min`/`max`, never first-order upwind (too diffusive â€” it re-opens the surrogate gap we're trying to close).
- **Vertical diffusion:** semi-implicit **backward-Euler batched tridiagonal (Thomas)** over water columns, differentiated by plain autograd. This is the single highest-leverage decision: it decouples `dt` from thin-surface-layer stiffness, is unconditionally stable, and is exactly conservative with no-flux BCs.
- **Splitting:** Lie/Strang split â€” explicit advection then implicit vertical diffusion per step.
- **Velocity:** recompute vertical velocity `w` from discrete continuity given prescribed `(u,v)` per cell â€” this, not a penalty, is what actually delivers the mass gate.

**Why:** every differentiable ocean/atmosphere emulator uses flux form; conservation is a discretization property, orthogonal to autograd. Backward-Euler Thomas is a fixed differentiable op sequence needing no adjoint. This mirrors MITgcm-offline exactly, so it inherits conservation for free.

**Explicitly reject:** spectral transport cores (NeuralGCM/Dinosaur) â€” not naturally positive/mass-local and incompatible with grid-native prescribed velocities.

---

## 2. Neural closures

**THE decision:** Learn **closures/parameters, not tendencies.** Keep the full Darwin box RHS analytic and transport prescribed; replace only the two genuinely-uncertain closures via the hooks that *already exist* in `carroll6_ude_tendency`:
- `ffe_closure`: iron-limitation multiplier â†’ small MLP, sigmoid-squashed to **[0,1]**.
- `calcite_closure`: PIC production as a **bounded multiplicative modifier on organic production**, structured `PIC_prod = R0 Â· g_Î¸(env, state) Â· mort_total`, with `R0` = Carroll baseline ratio (identifiability anchor: `g_Î¸â‰¡1` recovers Paper #1's constant `R_PICPOC` exactly) and `g_Î¸` a small MLP squashed via scaled sigmoid into ~[0.1, 10].

**Architecture:** each net **small and shallow** â€” 2â€“3 layers Ã— 8â€“16 neurons, tanh/swish. Architecture is second-order; do **not** scale up the net to chase RÂ². Feed **log-transformed** tracer concentrations and a compact physically-motivated input vector, not the full raw state.

**Calcite input vector** (priority order, all offline-precomputable): **SST, Î©_calcite** (computed from prescribed v05 DIC/ALK/T/S), **Fe/nutrient-limitation factor, PAR**. This is the union of drivers across the three reference models (Darwin constant-fraction / PISCES Î©-scaled / MARBL growthÃ—limitation), and PIC:POC is physiologically a *stress* ratio â€” the net must be able to raise it in oligotrophic/high-latitude-decline regimes and lower it in fast-growing upwelling (the eqpac-low / natl-high ~23Ã— v05 contrast).

**Regularization is the dominant knob** (larger effect than architecture): first-class tunable **L2 weight decay** on closure nets, swept on a log grid *before* touching architecture, plus a **soft-prior loss** anchoring each closure to its analytic Carroll form at reference conditions (net starts as a small correction, not a free function). Add a **Lipschitz/spectral-norm bound** on the nets so they cannot inject fast unstable modes.

**Optimizer:** Adam warmup â†’ L-BFGS polish, multi-start (Latin-hypercube the closure-net scaling so some seeds start near the Carroll closure), **select on held-out validation loss**, report **nâ‰¥10 seeds with variance** per existing `verify_run.py` discipline.

---

## 3. Gradient / checkpointing strategy

**THE decision:** **Discretise-then-optimise** â€” plain PyTorch autograd through the existing checkpointed RK4 `integrate()`. This gives *exact* gradients of the actual discrete loss. **Reject continuous/backsolve adjoint** (`torchdiffeq odeint_adjoint`) as the primary path â€” it is documented unstable on stiff/PDE-like systems (exactly the advection + fast-BGC regime), and a biased/blown-up gradient directly threatens the RÂ²>0 gate.

Get memory tractability from two orthogonal levers, in order:
1. **Truncated/windowed BPTT** â€” train on many overlapping short windows (**start 30â€“90 simulated days, tune upward until gradients stop helping**) with **detached** initial conditions. Caps activation memory independent of decade span and stabilizes optimization. Add a **rollout-length curriculum** (short windows first). It's a biased estimator, so window length is a first-class hyperparameter.
2. **Nested (2-level, Revolve-style) checkpointing** *within* each window and over yearâ†’day loops for the eval rollout â€” a âˆšNÃ—âˆšN scheme turns ~3650 daily steps into ~60 stored ocean states at ~2â€“3Ã— recompute. The dominant memory cost is stored 3-D tracer **state**, not NN activations, so checkpoint at segment boundaries and recompute the cheap NN forward.

The full forward-only decade rollout is reserved for **evaluation only** (RÂ² + mass gates), sidestepping long-horizon gradient degradation entirely.

Reversible solvers (McCallumâ€“Foster) are a **Phase-2** speed/memory upgrade only, always gradient-checked against the trusted checkpointed-RK4 reference before any science claim.

---

## 4. Conservation (the make-or-break budget gate)

**THE decision:** Conservation is **structural, not penalized** â€” a two-layer guarantee plus a hard reportable number.
- **Layer 1 (transport):** flux-divergence update with face fluxes shared between adjacent cells (same tensor accumulated as +cell / âˆ’neighbor). Conserves the domain total to fp64 machine precision regardless of NN state.
- **Layer 2 (biology):** neural closures emit **non-negative reaction rates/fluxes** mapped to tracer tendencies through Darwin's **fixed stoichiometry** (`dC = AÂ·S`, A non-trainable). A single `PIC_prod` feeds **all three** of `dPIC`, `dDIC (âˆ’1Ã—)`, `dALK (âˆ’2Ã—)` â€” never three independent laws. Elemental conservation then holds exactly even mid-training.
- **Positivity is a separate axis:** softplus/exp parameterization or a conservative FCT-style limiter â€” **never `torch.clamp(min=0)`** (silently injects mass). If you must clamp for stability, *log the clamped mass into the budget* so it shows up as drift rather than being laundered away.
- **Projection layer** (closed-form mass-weighted redistribution, ~1e-6 residual, ~free per step) kept only as insurance for any term not yet expressible in flux/stoichiometric form.

**Reportable gate:** extend the existing `relative_mass_drift` (integrators.py) into a running **per-element (C, N, P, Fe)** closed-budget accumulator that tags each boundary flux (dust in, export/burial out, air-sea COâ‚‚), integrates over the rollout, and reports **relative drift/decade** *and* **absolute drift (Pg C or mol/mÂ²/yr)** vs signal magnitude â€” all sums in **fp64**. Enable **deterministic kernels** so checkpoint recompute is bit-consistent. Claim exact **linear** conservation only (RK4 preserves linear invariants, not nonlinear ones). Explicitly avoid the reporting gap of the closest prior marine-BGC emulator (arXiv 2606.27168) â€” report a hard number, not "we added a conservation loss."

---

## Biggest risks + mitigations

**Risk 1 â€” Long-horizon gradient degradation / stiff-term blow-up over decade rollouts** (the Veros paper shows gradient error grows with rollout length; stiff calcification/scavenging is where instability lives). *Mitigation:* windowed BPTT with detached ICs + curriculum for training; forward-only decade rollout for eval; semi-implicit vertical diffusion + Lipschitz/spectral bound on closure nets; never bet the gate on backsolve adjoint or reversible solvers.

**Risk 2 â€” Silent mass leak masquerading as physics** (fp32 accumulation drift ~1e-7/op over 3650 steps; `clamp(min=0)` injecting mass; non-deterministic checkpoint recompute violating the budget the forward pass respected; a time-averaged `w` from file breaking discrete non-divergence). *Mitigation:* fp64 budget accumulation, structural conservation (flux + stoichiometry), positivity via softplus not clamp, deterministic kernels, recompute `w` from continuity, conservation-residual diagnostic *in the training loop* not just final eval.

**Risk 3 â€” In-sample fit that fails out-of-envelope** (UDEs recover dampened oscillations and drive species negative under perturbation even with good in-sample loss â€” the surrogate-gap risk). *Mitigation:* make the gate **adversarial and out-of-distribution** â€” held-out real-data RÂ²>0 on an unseen region/period, bounded mass residual over a decade, and a hard non-negativity/closure-in-bounds check under *perturbed* forcing (warm/high-Fe). Reject any config that fits in-sample but drifts or goes negative, regardless of training loss. Aggressive L2 (dominant knob) + soft Carroll prior + small nets keep the closure a correction, not a free emulator.

---

## Questions genuinely needing Jon (domain science) vs. decidable ourselves

**Need Jon:**
1. **Which two closures first, and the exact analytic forms Î©_calcite / nutrient-limitation should take** â€” confirm the calcite input vector (SST, Î©, Fe-lim, PAR) is the physically defensible set for the Darwin/v05 lineage, and whether N/P limitation proxies are available or data-blocked in v05.
2. **Reference `R0` / Carroll baseline ratio and its per-AOI plausibility band** for the calcite anchor, and whether the Southern-Ocean ratio target still needs the `RATIO_MAX` sanitization when building the calcite loss (to avoid chasing the known-contaminated signal).
3. **Which AOI/region and decade for the held-out RÂ² gate**, and what real datasets (v05 vs GLODAP) constitute a legitimate held-out target vs. training data â€” the science of what "held-out" means physically.
4. **Whether freezing PIC dissolution/sinking (learning production only) is scientifically acceptable** for Phase 1, and the correct DIC(âˆ’1)/ALK(âˆ’2)-per-mole-PIC stoichiometry / boundary-flux sign conventions (dust in, export/burial out, air-sea COâ‚‚) for the budget.
5. **What absolute mass-drift magnitude is acceptable** â€” i.e., what "<< the physical trend" means in Pg C/decade for this system to count as passing.

**We decide ourselves (engineering):**
- Advection scheme choice (centered-2nd + biharmonic), splitting order, backward-Euler Thomas for vertical diffusion, `w`-from-continuity.
- Discretise-then-optimise vs adjoint; window length, curriculum schedule, nested-checkpoint level sizing, fp64 budget, deterministic kernels.
- Net size/depth/activation, bounding transforms, log-input normalization, L2 sweep grid, Adamâ†’L-BFGS + multi-start, val-based selection, nâ‰¥10 seeds.
- Structural conservation implementation (flux-share tensor, `dC=AÂ·S`), positivity via softplus, projection-as-insurance, the `relative_mass_drift` extension.
- All autograd-hygiene rules (functional kernel, 0/1 mask multiply, concatenated halos, eps-guarded divisions) and the `gradcheck` CI guard.

---

## Concrete build order for Phase 1

1. **Autograd-clean 3-D transport kernel (functional).** Flux-form centered-2nd advection + biharmonic diffusion + batched backward-Euler Thomas vertical diffusion, on prescribed `(u,v)` with `w` recomputed from continuity. Land mask as 0/1 multiply, halos by concatenation, eps-guarded divisions, no in-place writes. Same `f(state)->dstate` tendency interface the existing `integrate()` already consumes.
2. **Offline divergence check + preprocessing.** Compute per-cell divergence of the time-averaged v05 velocity; apply one-time cleanup / carry implied `w` so the field is discretely non-divergent *before* training. This proves the mass gate offline.
3. **`gradcheck` CI guard.** `torch.autograd.gradcheck` on a tiny 3Ã—3Ã—3 box through one advection + vertical-mixing step. Catches NaN/dead-gradient constructs before they cost a training run. (Extend `tests/test_integrators.py`.)
4. **Structural conservation wiring + fp64 budget accumulator.** Refactor the biology source/sink to `dC = AÂ·S` with single `PIC_prod` feeding `dPIC`/`dDIC`/`dALK`; extend `relative_mass_drift` to a per-element closed-budget accumulator with boundary-flux tagging. Verify flat budget on a *fixed-parameter* forward decade rollout (no NN yet).
5. **Precompute exogenous forcing channels.** Cache Î©_calcite (from v05 DIC/ALK/T/S), SST, PAR, Fe-limitation factor per cell/time as static input channels.
6. **Wire the two bounded closures** into `carroll6_ude_tendency` (hooks already exist): `ffe_closure` â†’ sigmoid[0,1]; `calcite_closure` â†’ `R0Â·bounded(MLP(env,state))Â·mort_total`. Confirm `g_Î¸â‰¡1` reproduces the constant-`R_PICPOC` baseline byte-for-byte.
7. **Windowed-BPTT training harness.** Detached-IC short windows (30â€“90 d) + nested checkpointing within window + rollout-length curriculum. Adamâ†’L-BFGS, multi-start, L2 as first-class swept hyperparameter + soft Carroll prior + spectral-norm bound.
8. **Adversarial three-part gate.** (a) held-out real-data RÂ²>0 on unseen region/period; (b) bounded per-element mass drift over forward-only decade rollout; (c) out-of-envelope physical-realism check (perturbed forcing, all tracers â‰¥0, closures in bounds). Report nâ‰¥10 seed variance, hard drift number, and the eqpac-low/natl-high PIC:POC contrast reproduction, gated through `verify_run.py`.

**Files touched:** `src/darwindiff/integrators.py` (budget accumulator, deterministic kernels), new `src/darwindiff/transport.py` (3-D flux-form kernel), `src/darwindiff/carroll6.py` (closure wiring â€” hooks already present, lines ~228â€“286), `tests/test_integrators.py` (gradcheck guard). Steps 1â€“4 are the critical path to the mass gate; 5â€“8 to the RÂ² and realism gates.