# FNO / neural-operator canon vs the DarwinDiff emulator route — a cited decision (2026-07-08)

**Question.** Does the Fourier-neural-operator family (FNO, Neural-Operator framework, Geo-FNO, PINO,
GINO, AFNO/FourCastNet, U-FNO) or NVIDIA's PhysicsNeMo / Earth2Studio change the earlier decision to
**shelve the parameter-conditioned black-box emulator** (`FNO(state, Carroll-6) → next state`, as a
differentiable surrogate for gradient-based calibration) in favour of the mechanistic **UDE** (prescribe
v05 transport, learn small closures)?

**Verdict (verified, unanimous).** **No — keep the emulator shelved.** Across nine topics researched
against primary sources and adversarially re-checked, eight *reinforce shelving* and one (PINO) *accelerates
the UDE*. The neural-operator literature does not remove either blocker that shelved the emulator, and its
own "cure" for the decisive one points straight back at the UDE. The forward-useful payoff is a **toolbox of
components to layer onto the UDE**, not a reason to rebuild the surrogate.

> Method: 9 topics × (grounded web research → adversarial verify) + this synthesis. Every load-bearing claim
> below cites a URL fetched during the pass. A verify pass flagged minor citation-hygiene overstatements
> (venue attributions, one grid-dim, GINO mesh counts, U-FNO layer config); those are hedged or dropped here.
> The substance — data scarcity, dirty gradients, PINO's data-reduction — is solidly sourced.

---

## The two blockers, and why no FNO variant removes them

The emulator was shelved for (1) **data scarcity** — an `FNO(state, params)` surrogate must be *trained* on a
perturbed-parameter Darwin **ensemble** (tens–hundreds of GCM runs spanning the 6 Carroll params), and only
**one** v05 output point exists; and (2) **dirty parameter gradients** — a black-box surrogate can be
solution-accurate yet give inaccurate `∂u/∂p`, so its calibration gradients are unreliable.

### Blocker 1 — data scarcity is intrinsic to operator learning, not an architecture choice

Every operator surrogate in the canon is data-driven and needs an **ensemble of full solves spanning the
input distribution**. The numbers, from primary sources:

- **GINO** — the most geometry-capable, most data-frugal variant — still trained on **~500 full CFD solves**
  (500 train + 51 val Ahmed-body; 500 train + 111 val ShapeNet-Car). [arXiv:2309.00583]
- **U-FNO** — the closest real *carbon* analogue (CO₂ geological storage) — used **4,500 ECLIPSE reservoir
  simulations** (5,500 total, 9/1/1 split) for a far simpler 2-D radial problem than ECCO-Darwin.
  [arXiv:2109.03697]
- **FourCastNet** — the flagship black-box Earth-system emulator — rests on **ERA5: ~37 years of hourly
  global fields** (train 1979–2015) and **~1024 A100-GPU-hours**. [arXiv:2202.11214]

DarwinDiff has one v05 trajectory and cannot afford a perturbed-Carroll-6 GCM ensemble. **No architecture
(GINO, Geo-FNO, AFNO, U-FNO) manufactures that ensemble** — FNO *is* the thing that consumes it. AFNO is only
an efficient token-mixer (quasi-linear Fourier attention), not a data-efficiency trick. [arXiv:2111.13587]

### Blocker 2 — dirty gradients are measured, and the only fix presupposes the UDE

**SC-FNO** (Sensitivity-Constrained FNO) quantifies the exact failure mode behind the shelving: a vanilla FNO
with accurate *forward* solutions still had **parameter-gradient R² of only 0.21–0.82** (0.72–0.78 on a
5-parameter PDE, 0.21–0.82 on a 4-parameter PDE). Accurate forward predictions give **no guarantee** of
accurate `∂u/∂p`. [arXiv:2505.08740]

The remedy is unanimous across the derivative-informed literature and **theorem-backed**: to get calibration-
grade gradients the surrogate must be **trained on true Jacobian/sensitivity labels** —
`Ls = (1/M)Σ‖∂û/∂p − ∂u/∂p‖²`, where "∂u/∂p is the true Jacobian derived from precise **differentiable
numerical solvers** or known analytical solutions." With such labels SC-FNO reaches inversion **R²=0.998**
(vs 0.905 for plain FNO) and holds R²>0.94 across 5 parameters. [arXiv:2505.08740] **DINO** (derivative-
informed neural operator) learns the operator *and* its Fréchet derivative for exactly this purpose, at
"16–25× lower cost in training-sample generation." [arXiv:2206.10745, arXiv:2403.08220]

The catch for Track 2: producing those Jacobian labels needs *either* an adjoint / differentiable solver
(*which is the UDE*) **or** finite-difference sensitivities — and finite differences mean re-running the GCM at
perturbed parameters, i.e. the **same perturbed-parameter ensemble (PPE) Track 2 cannot afford**. So the
dirty-gradient defect does not independently rescue the emulator: its fix collapses back onto the *decisive*
blocker — **the missing PPE (data scarcity)** — or onto the mechanistic route. (This corrects an earlier
overstatement that the fix "only" needs a differentiable solver; the A-vs-B decision note's verifier confirmed
finite-difference sensitivities match autodiff, so the real, confirmed blocker for (A) is the unaffordable PPE,
not a gradient-accuracy fix.)

---

## PINO — the DarwinDiff thesis in miniature (accelerates the UDE)

PINO is the one topic that flips positive, and it argues **for** the UDE, not the emulator. Its flagship
result: adding a **known-PDE residual loss** drops the data requirement to "**few to no data**" (zero data on
Burgers/Darcy), while beating data-driven FNO by ~7% relative error and retaining the ~400× solver speedup.
[arXiv:2111.03794] This is direct empirical evidence that **imposing known physics substitutes for the
missing ensemble** — precisely DarwinDiff's low-data strategy.

But PINO is **not** a route back to the emulator: (a) the physics you would impose (advection–diffusion on
prescribed v05 velocities + the Darwin biology residual) **is the UDE**; (b) its clean derivatives come from
differentiating a **known** operator — the opposite of the emulator's dirty black-box Jacobians; (c) its
*efficient* FFT-based residual assumes a **uniform grid** that LLC270's cubed-sphere is not; (d) its
conservation is a **soft penalty**, weaker than DarwinDiff's flux-form **hard** mass closure (A1–A5). Net:
adopt PINO's *idea* — a high-resolution transport-residual term + test-time closure fine-tuning against sparse
real data — as a UDE accelerant.

---

## What is genuinely reusable (for the UDE, not the emulator)

| Component | Source | Concrete reuse in DarwinDiff |
|---|---|---|
| **GINO GNO-encoder/decoder** (irregular point-cloud + SDF → regular latent FFT grid, discretization-convergent, scales to 7.2M-pt 3-D meshes) | arXiv:2309.00583 | The right machinery to run a spectral/nonlocal learned term on the **13-face LLC270** mesh, and to **ingest the ~14 sparse iron cells / denser calcite anchor** onto a latent grid — *once the UDE forward exists*. Geometry is orthogonal to the two blockers. |
| **Geo-FNO learned diffeomorphism** | arXiv:2207.05209 | Alternative geometry bridge. **Caveat:** LLC270 cubed-sphere is the *non-homeomorphic* case Geo-FNO handles only via Fourier continuation / domain decomposition — not a clean single-torus map. No mass-conservation guarantee. |
| **SC-FNO sensitivity loss / DINO Jacobian training** | arXiv:2505.08740, 2206.10745 | Drop-in for **certified-accurate closure gradients + cheap posterior UQ** — but only *after* the UDE makes the forward differentiable (it supplies the required Jacobian labels). |
| **U-FNO local U-Net path** (parallel to the Fourier kernel; cures FNO spectral bias on local/high-freq features) | arXiv:2109.03697 | Optional **closure architecture** block if a learned closure needs local high-frequency structure the spectral kernel smooths. |
| **PhysicsNeMo blocks** (FNO, GNN/GNO, PINN, Fourier-feature nets) | developer.nvidia.com/physicsnemo | Ready implementations of the above as UDE spatial components. No ocean/BGC model ships; it is a component library, not a solution. |

### Earth2Studio — not on the critical path
Earth2Studio is a **pretrained-model inference / coupling harness** (weather–climate only: FourCastNet3,
SFNO, GraphCast, Pangu, Aurora, …) with **no training, no autograd, no calibration loop, and no ocean/BGC
model**. Its `create-prognostic` extension API (implement `PrognosticModel`: `__call__`, `create_iterator`,
`input/output_coords`) plus a **grid-agnostic `CoordSystem`** ("lat-lon not required") mean it *could*
host a custom LLC270 prognostic — but only as a **rollout/IO wrapper**, after E2, never as the differentiable
calibration engine. It does not restore the ensemble or fix gradient quality. **Do not add it to the Track-2
critical path.** [nvidia.github.io/earth2studio]

---

## Recommendation

1. **Emulator stays shelved.** Cite this literature as the *justification*: data scarcity (GINO 500 /
   U-FNO 4,500 / FourCastNet ERA5-scale) + measured dirty gradients (SC-FNO R² 0.21–0.82) whose only fix
   needs a differentiable solver. Revisit an operator surrogate **only if** a perturbed-parameter Darwin
   ensemble ever becomes affordable — and then SC-FNO-style sensitivity constraints are *required*, not
   optional.
2. **Proceed with the mechanistic UDE** (the current Track-2 path). It gives exact autodiff gradients, needs
   no ensemble, rides the physical transport operator, and hard-conserves mass — the four properties the
   operator surrogates lack.
3. **Highest-value, affordable-with-H200-only + 1 GCM point next step:** build the **windowed-BPTT trainer**
   on the now-complete conservation-verified transport machinery (A1–A6 + the IMEX vertical-diffusion fix),
   toward the E2 gate. *Optionally* prototype a **GINO-style geometry encoder** as the LLC270 spatial front-end
   for the sparse iron/calcite anchors — a modest accelerant, not a dependency.
4. **Fold PINO's residual-loss idea** into the E2 trainer design (transport-residual term + test-time closure
   fine-tuning) as the principled low-data regularizer.

**Honesty note.** This is a *literature* decision, cited but not experimentally re-benchmarked on ECCO-Darwin;
the load-bearing external numbers (SC-FNO gradient R², GINO/U-FNO/FourCastNet data scale, PINO data-reduction)
are quoted from the primary sources listed. The DarwinDiff-specific blockers (one v05 point; LLC270 non-uniform
grid; hard vs soft conservation) are facts of this project.

### Primary sources
FNO arXiv:2010.08895 · Neural-Operator framework arXiv:2108.08481 · Geo-FNO arXiv:2207.05209 · PINO
arXiv:2111.03794 · GINO arXiv:2309.00583 · AFNO arXiv:2111.13587 · FourCastNet arXiv:2202.11214 · U-FNO
arXiv:2109.03697 · SC-FNO arXiv:2505.08740 · DINO arXiv:2206.10745 (+ DINO-MCMC arXiv:2403.08220) ·
PhysicsNeMo developer.nvidia.com/physicsnemo · Earth2Studio nvidia.github.io/earth2studio
