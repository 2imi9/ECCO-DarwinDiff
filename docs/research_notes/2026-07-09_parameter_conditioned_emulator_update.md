# Parameter-conditioned differentiable emulators — a 2026-07-09 update to the shelving decision

**Why this note.** `NEXT_SESSION.md` action 1 asks to "dive on parameter-conditioned
differentiable emulators for gradient-based calibration (BINN, NeuralGCM, neural-operator
conditioning, amortized / simulation-based inference)." The prior note
[`2026-07-08_fno_neural_operator_emulator_decision.md`](2026-07-08_fno_neural_operator_emulator_decision.md)
already ran the FNO-family decision and **shelved the black-box emulator**
(`FNO(state, Carroll-6) → next`) in favour of the mechanistic UDE, on two blockers: (1) no
affordable perturbed-parameter Darwin ensemble, and (2) measured dirty parameter gradients whose
fix presupposes a differentiable solver (the UDE).

This note does two things the 07-08 pass did not: it **re-tests that verdict against the newest
primary sources** (three ocean/operator papers that post-date it), and it **adds the BINN lineage**
— the established biology-PDE tradition that DarwinDiff's UDE-closure-plus-symbolic-distillation
method actually sits in, and which the 07-08 note omitted. Verdict is unchanged; the new material
is forward-useful design guidance and a genuine methodological anchor, not a reopening.

> Honesty guardrail: this is a **literature scoping** note. External numbers are quoted from the
> primary sources; nothing here is re-benchmarked on ECCO-Darwin. Track-2 remains synthetic
> self-twin until the E2 gate (held-out real-data R² > 0 with transport) is built.

---

## 1. The newest ocean/operator sources do not move the verdict — but two sharpen it

### NeuralOGCM (arXiv:2512.11525) — end-to-end learnable physics on *one real* trajectory
A differentiable OGCM: `y_{t+Δt} = y_t + Δt·G_phys(y_t; θ_p) + Δt·G_neural(y_t, F_t; θ_n)`, physics
core (advection, Coriolis, horizontal diffusion) plus an attention-bottleneck NN corrector,
trained **end-to-end on real GLORYS12 reanalysis** (1993–2020, 1.5°, 23 levels; held-out temporal
split; 8×A100). The learnable *physical* parameters are the two horizontal diffusion coefficients
`{ν_momentum, ν_tracer}`, passed through softplus for non-negativity and optimized jointly with the
NN. Stable 90–120-day rollouts (120-day RMSE 1.574 vs FourCastNet 3.332), no non-physical drift.

*Why it does not un-shelve our emulator.* It learns **two global scalars**, not a spatially-varying
6-parameter field, and it fits a **dense, fully-observed reanalysis** — the opposite of DarwinDiff's
regime (one v05 trajectory, ~14 sparse iron cells). It is a strong existence proof for *hybrid
physics-core + NN-corrector on real ocean data* (which **is** the UDE shape, not the black-box
emulator), and its single-step (non-BPTT) training is a caution: it never demonstrates
long-window backprop, which is exactly what our E2 trainer needs.

### Differentiable VEROS (arXiv:2511.17427) — independent corroboration of *parameter-specific* identifiability
VEROS made **JAX-differentiable** through its dynamical core; the calibration demo recovers **two
params** — lateral viscosity `Ah` and bottom friction `rbot` — from a **synthetic twin** (barotropic
streamfunction of an idealized ACC), "very close to reference" (no numeric error reported). Two
remarks are directly load-bearing for us:
- **Sensitivity anisotropy:** "the loss exhibits stronger sensitivity to `Ah` than to `rbot`." This
  is the same phenomenon as DarwinDiff's headline Track-1 result — **identifiability is
  parameter-specific** (iron pair recovers, `diatomgraz` is profile-flat). An independent ocean
  group hitting the same wall is corroboration worth citing in Paper #2.
- **Gradient degradation over rollouts:** "discrepancy between gradient-estimation methods increases
  with the number of time steps." A concrete caution for the windowed-BPTT E2 trainer: **window
  length is a gradient-quality knob**, not just a memory knob — pick it with a gradient-agreement
  check, not only the checkpoint budget.

### NeuralGCM (Nature 2024, Kochkov et al.) — the online-training precedent
Differentiable dynamical core + learned physics in JAX; the defining move is **online training** —
physical-model parameters optimized *together with* the ML parameters "in the context of interactions
with the governing equations." This is the template DarwinDiff already follows (DINN params learned
through the differentiable box), now at GCM scale. Precedent, not a new capability for us.

**Net for §1:** the 07-08 shelving holds. The fresh ocean sources reinforce the *UDE* shape
(physics core + learned correction, online-trained) and hand us one new design rule (window length
gates gradient quality) and one citable corroboration (parameter-specific identifiability).

---

## 2. The derivative theorem got stronger — and it points at the UDE again

**DIFNO** (Derivative-Informed FNO, arXiv:2512.14086) proves (Thm 3.2/4.3) that an FNO with smooth
activations can approximate **an operator and its Fréchet derivative simultaneously** to any ε on
compacts (and on Gaussian-measure input spaces). The motivating inequality is the one that matters
for *any* surrogate-driven calibration:

> error in the surrogate-driven optimum is bounded by **operator error + Fréchet-derivative error**;
> pointwise operator accuracy alone admits **spurious local minima** if the derivative is wrong.

This is the theorem behind the 07-08 note's empirical SC-FNO finding (forward-accurate FNO,
parameter-gradient R² as low as 0.21). Together they say: **a parameter-conditioned emulator is only
calibration-grade if it is trained on true Jacobian labels** — and those labels come from a
differentiable solver, i.e. the UDE. So the strongest new theory *re-derives* the reason the
mechanistic route wins: the UDE gives **exact** `∂output/∂θ` by construction, needing no
derivative-matching surrogate and no PPE to generate Jacobian labels.

*If* a perturbed-parameter Darwin ensemble ever becomes affordable, the conditioning mechanics are
now clear: **FiLM (feature-wise scale-and-shift per layer) beats input-concatenation by ≈ an order
of magnitude** when the parameter changes the operator (equation-aware neural operators
arXiv:2511.09729; loss-conditional PINNs arXiv:2606.04420; conditioning-on-PDE-params for chaotic
dynamics arXiv:2509.09599). Record this as the design default for a future `FNO(state, Carroll-6
field)`, contingent on the ensemble — not a reason to build it now.

---

## 3. The missing lineage: DarwinDiff's UDE **is** a BINN, and tonight's gate is its equation-discovery step

The 07-08 note never placed DarwinDiff's method in the **biologically-informed neural network** (BINN)
tradition, which is its closest established relative and a cleaner differentiation target than the
weather-FNO canon.

- **BINN, Lagergren et al. 2020** (arXiv:2005.13073, PLOS Comp Biol): an MLP surrogate for the PDE
  solution with **unknown mechanistic terms (diffusivity, growth) replaced by small NNs**, trained
  against sparse data; the learned term functions are then **visualized to conjecture the governing
  equation**. That is *exactly* the DarwinDiff UDE loop: replace the unknown iron-limitation /
  calcification closure with a bounded NN, fit through the differentiable model, then read off the
  law. The symbolic-distillation gate built tonight
  ([`scripts/symbolic_distill_probe.py`](../../scripts/symbolic_distill_probe.py)) **is** BINN's
  "visualize-and-conjecture" step, made quantitative and turned into a go/no-go on identifiability.
- **Likelihood-based BINN** (arXiv:2606.13475): learns **noise and growth dynamics simultaneously**
  via a likelihood objective — the principled upgrade path for our current squared-error closure
  loss, and a way to get calibrated uncertainty on the closure without a separate SBI stack.
- **CBINN** (Cancer-BINN, arXiv:2510.17920): "unknown parameter estimation **and** missing-physics
  identification" in one biology-informed model — the same two-headed goal as Track 2 (recover
  Carroll params *and* discover the calcification closure).

**Why this matters for Paper #2.** It reframes the contribution in an established lineage: DarwinDiff
extends BINN-style mechanism discovery from small in-vitro biology PDEs to a **global GCM
biogeochemistry closure**, with (a) a real differentiable-transport forward model instead of a
solution-surrogate MLP, (b) hard flux-form mass conservation, and (c) an explicit
**identifiability gate** (symbolic distillation + Fisher/profile agreement) that the BINN papers
lack. That is a sharper novelty claim than "a differentiable ocean model."

---

## 4. Amortized SBI / neural posterior estimation — still the road not taken, now for a citable reason

Amortized **neural posterior estimation** (NPE; generalized-Bayes NPE arXiv:2601.22367, and the SBI
canon) trains a normalizing-flow / density estimator that maps simulated data → posterior over
parameters, reusable across observations without a differentiable model. It is the natural
**gradient-free alternative** to everything above. It stays shelved for DarwinDiff for the reason in
project memory, now made precise by the same blocker as the emulator: **amortized NPE is
simulation-hungry** — it needs a large ensemble of `(θ, simulated-obs)` pairs spanning the prior,
which for real Darwin is the **same unaffordable perturbed-parameter GCM ensemble**. On the *box*
surrogate NPE is affordable but only re-answers the box's (already-solved) identifiability; on real
Darwin it is data-blocked. Worth one sentence in Paper #2's methods-comparison, not a build.

---

## 5. What changes in the plan

Nothing reverses; three refinements land:

1. **Keep the emulator shelved; keep building the mechanistic UDE.** The newest theory (DIFNO) and
   the newest ocean models (NeuralOGCM, VEROS) both point back to a physics-core + learned-correction,
   online-trained, differentiable model — the UDE — as the calibration-grade route without a PPE.
2. **Treat window length in the E2 windowed-BPTT trainer as a gradient-quality parameter.** VEROS's
   rollout-length gradient degradation says: choose the BPTT window with a gradient-agreement /
   `relative_mass_drift` check, not solely the checkpoint memory budget. (The time-aware integrator
   + checkpointing landed today make this cheap to probe.)
3. **Frame Paper #2 in the BINN lineage.** Cite Lagergren 2020 / likelihood-BINN / CBINN as the
   method ancestry; position the symbolic-distillation gate as the quantitative,
   identifiability-tested successor to BINN's "visualize the learned term," and the differentiable
   transport + hard conservation + identifiability gate as the three things those papers lack.
4. **Two forward options, both contingent, both recorded:** (a) if a Darwin PPE ever appears →
   FiLM-conditioned, **derivative-informed** (SC-FNO/DIFNO Jacobian labels) operator, never plain
   output-MSE; (b) a **likelihood-based** closure loss (arXiv:2606.13475) as the principled upgrade
   from squared error, giving closure uncertainty without a separate SBI stack.

---

### Primary sources (new since the 07-08 note)
NeuralOGCM arXiv:2512.11525 · differentiable VEROS arXiv:2511.17427 · NeuralGCM Nature 2024
(Kochkov et al.) · DIFNO arXiv:2512.14086 · equation-aware neural operators arXiv:2511.09729 ·
loss-conditional PINNs arXiv:2606.04420 · conditioning-on-PDE-params (chaotic) arXiv:2509.09599 ·
BINN arXiv:2005.13073 · likelihood-based BINN arXiv:2606.13475 · CBINN arXiv:2510.17920 ·
generalized-Bayes amortized NPE arXiv:2601.22367.
Prior-pass sources (SC-FNO 2505.08740, DINO 2206.10745, PINO 2111.03794, GINO 2309.00583, …) in
[`2026-07-08_fno_neural_operator_emulator_decision.md`](2026-07-08_fno_neural_operator_emulator_decision.md).
