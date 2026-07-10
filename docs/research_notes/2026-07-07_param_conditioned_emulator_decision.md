# DECISION NOTE — Closing DarwinDiff's E2 Surrogate Gap: Parameter-Conditioned Emulator (A) vs. Mechanistic UDE (B) vs. SBI

**Date:** 2026-07-07
**Author:** Lead architect (Track 2 / Paper #2)
**Scope:** The single decision — what spatially-resolved differentiable forward model do we backprop the Carroll-6 calibration loss through to clear the E2 gate (held-out real-data R² > 0), cost-first, no local GPU.

---

## TL;DR — the ranked call

1. **BUILD (B), the mechanistic UDE, as the calibration engine. It is the only route not blocked at the source.** Its differentiable foundation is **already merged on `main` (#177)**: `src/darwindiff/transport.py::column_tendency` is already `f(Carroll-6, forcing) -> dstate`, differentiable w.r.t. the six params and mass-conserving by construction (no-flux flux-difference form, lines 93–150). It needs **zero new GCM runs** because it prescribes v05's own velocities (MITgcm-offline). Every verifier verdict that touched the data question rated this asymmetry **CONFIRMED** — the one un-downgraded verdict in the bundle.

2. **SHELVE (A), the parameter-conditioned FNO, for calibration. Repurpose it later to forward rollout only.** (A) is **data-blocked**: it must be trained on a perturbed-parameter ensemble (PPE) of the full ECCO-Darwin GCM spanning the Carroll-6 box, and **DarwinDiff has exactly one v05 run** (a single point in parameter space) with no budget/disk to multiply it (STATUS.md L164; one pickup on disk; ~5 TB/run vs 1.43 TB free). This is not a tuning problem, it is a missing-dataset problem. Even Carroll/Menemenlis declined to densely sample the 6-D space because full GCM runs are too expensive — that is the exact wall.

3. **Do NOT stand up SBI as a separate route now. Fold amortized-posterior UQ onto whichever forward model wins, later.** SBI's genuine advantages (no simulator gradients; free calibrated posteriors) are real, but it **shares (A)'s expensive Darwin-run-generation step** (it needs the same PPE we don't have), and its robust-misspecification fixes (RoPE/FRISBI) require known-ground-truth parameter labels DarwinDiff **structurally cannot provide** (Carroll's values are the unknown). The bundle's headline SBI feasibility anchor (WOMBAT) was **REFUTED by the verifier as not-even-SBI** — it is a GP-surrogate+MCMC result, i.e. route (A)-style. Down-weight accordingly.

**One-line rationale:** (A) and SBI both presuppose a Darwin PPE that does not exist and that the project cannot afford; (B) presupposes only v05's archived velocities, which we have, and its core function is already written and tested. Cost-first, this is not close.

---

## 1. The decision, defended

### Why (B) first — and it is already half-built

The decisive repo fact, **CONFIRMED** by the verifier with no downgrade: route (A) cannot be *trained* without tens-to-hundreds of new full ECCO-Darwin integrations spanning Carroll-6, and route (B) needs none. Grounding it in the actual files:

- `transport.py::bgc_tendency_field(state, params, ...)` (line 36) reads the six params by name off the frozen `carroll6.P` registry (`P.alpfe`, `P.scav_rat`, `P.R_PICPOC`, `P.Smallgrow`, `P.Biggrow`, `P.diatomgraz`, lines 61–66) and is autograd-clean w.r.t. them. Wrapping it in `column_tendency` (line 121) with `vertical_diffusion` + `vertical_advection` **is already the spatially-resolved differentiable forward map** `f(Carroll-6, forcing) -> state` that the "seam" in `NEXT_SESSION.md` (lines 37–42) asks for. Building a parameter-conditioned FNO to do the same job *duplicates code we merged in #177* while adding the PPE blocker.
- Mass conservation — DarwinDiff's hard decadal gate — is structural here, not learned: the no-flux flux-difference operators (transport.py lines 100–104, 114–118) make each column-summed tracer conserved to machine precision, and the Phase-1 brief upgrades this to backward-Euler Thomas diffusion that stays A-stable and exactly conservative. A black-box autoregressive emulator would need extra machinery just to *not* violate the gate that (B) satisfies by construction (hybrid-GCM angle; **high** confidence).

The mechanistic-decoder lineage independently argues (B) is the more *identifiable* route, not just the cheaper one. **ScIReN** (the direct BINN successor) ran essentially this A-vs-B contrast on synthetic carbon-cycle data: a black-box hybrid matched observed-output fit yet **collapsed on latent-parameter recovery** while the structured mechanistic decoder recovered them. **Read the corrected numbers, not the bundle's headline** — the verifier marked the original claim **PARTIAL** and fixed a column mix-up: the honest parameter-recovery contrast is **R² = 0.989 (structured) vs 0.226 / 0.721 (black-box variants)**, *not* "0.999 vs 0.226"; and all methods **tie at real-data R² ≈ 0.58**. Two caveats the verifier flagged that we must carry: (i) much of ScIReN's edge comes from its *interpretable encoder*, not the mechanistic decoder alone — the paper's own plain-NN-encoder + mechanistic-decoder ("Blackbox-Hybrid," the nearest analog to our bounded-NN UDE) recovered params *poorly*; and (ii) correct recovery is proven only on **synthetic twins with dense labels**, never on real sparse obs. So ScIReN supports (B) directionally but is **not** real-data proof for our ~14-cell regime.

### Why (A) is shelved, not killed

(A) is a legitimate, citable paradigm — parameter-conditioned neural-operator inversion exists (PE-FNO, Conditional-FNO/INO, the geophysics permeability-inversion pipelines at ~2000 sims). It is not shelved because it is unsound; it is shelved because **its training set does not exist and cannot be cheaply produced**, and because even if built it would relocate the surrogate gap rather than escape it (see §3). If a v05 PPE ever materializes (a decision that belongs to Jon + the Explorer PI, not to us), reconsider (A) — but only in the guarded, sensitivity-supervised form of §2, and even then its first justified use is **century-scale forward rollout speed**, not calibration.

### Why SBI is not a separate track now

SBI's structural appeal is real and correctly stated in the bundle: NPE needs no simulator gradients, sidestepping the surrogate-gradient-bias worry that motivates both A and B, and it returns calibrated 6-param posteriors — the exact "Carroll's values are under-constrained" deliverable we want. But three things sink it as a *near-term* route:

- **It consumes (A)'s cost, not (B)'s.** SBI-on-the-box inherits the surrogate gap as catastrophic, overconfident misspecification (the same failure that gives Track 1 negative held-out R²), so it *must* run on spatially-resolved Darwin — i.e. it needs the PPE we don't have. SBI-on-a-learned-emulator means SBI *consumes* route (A) rather than replacing it.
- **The robust-misspecification fix is blocked for us.** RoPE/FRISBI need a calibration set of real observations paired with *known true parameters*; DarwinDiff structurally cannot supply this (**verified**). We'd be forced onto weaker RNPE-style error-modeling.
- **The bundle's affordability anchor was refuted.** The "WOMBAT ~1,024-run / 13-param SBI precedent" is, per the verifier, **not SBI at all** — it is a **GP-surrogate + emcee MCMC** calibration (methodologically route A). The verifier also corrected the budget: successful *SBI* typically needs *a few thousand* sims, not "a few hundred to ~1,000." So the one concrete number that made SBI look cheap doesn't support SBI.

Correct disposition: SBI is a **later UQ layer**, bolted onto (B)'s differentiable forward model once E2 is cleared (a differentiable simulator improves SBI sample efficiency), giving honest Carroll-6 posteriors for Paper #2's headline claim — not a competing forward-model build.

---

## 2. If (A) is on the table: architecture and the honest data blocker

For completeness, if a PPE ever exists, here is the only defensible build — and the blocker that decides it.

**Conditioning mechanism:** **FiLM (feature-wise affine modulation) or a hypernetwork, NOT broadcast-concatenation.** Carroll-6 varies *weakly* near Carroll's optimum, and a concatenated parameter channel is documented to be ignored by deeper layers → gradient collapse exactly where we need signal. FiLM conditions uniformly across the hierarchy; a hypernetwork most strictly decouples the scalar params from the spatial field. (conditioning angle, **high** confidence.)

**Non-negotiable second ingredient — a sensitivity loss.** Forward-reconstruction accuracy does **not** certify invertibility: a standard FNO reaches R² ≈ 0.986 on the *state field* but only **R² ≈ 0.21–0.82 on d(state)/d(parameter)**, and multi-parameter inversion collapses below R² 0.64. The fix is SC-FNO / Derivative-Informed FNO style training that supervises the Jacobians. **Important verifier correction (marked PARTIAL):** this supervision does **NOT** require differentiable Darwin — SC-FNO shows *finite-difference* sensitivities (re-running the *existing* non-differentiable GCM at perturbed params) match autodiff sensitivities. So (A) does not reduce to (B)'s hard part; it substitutes a *different* hard part — **the perturbed-parameter ensemble** — which is precisely the cost we can't pay.

**The honest data blocker — is it fatal? For now, yes.** Training FNO(state, Carroll-6) requires simulations that *sample* the 6-D box. DarwinDiff has one v05 point; a coarse Latin-hypercube would need **tens-to-hundreds** of full GCM integrations at minimum (published parametric-FNO training sets run 1,000–30,000 sims for far cheaper PDEs, so this is if anything an underestimate — verifier). We have neither the compute budget nor the disk (~5 TB/run). Two degenerate escape hatches the verifier named and dismissed: (i) generate cheap PPE data *from the 0-D box* — inherits the box's surrogate gap, the very defect (A) is meant to cure; (ii) reuse Carroll's ~6 archived one-at-a-time Green's-function perturbations — far too sparse and linearized to fit a nonlinear operator, and not on our disk. **Conclusion: the blocker is fatal at current budget; it is a data-staging decision for Jon, not an architecture we can unblock ourselves.**

---

## 3. Does each route ESCAPE the surrogate gap, or relocate it? (the decisive test)

This is the test that actually separates the routes. The surrogate gap has **two components** — a *dimensional* gap (the 0-D box has no spatial structure) and a *support* gap (the forward model is only trustworthy where its training/physics is valid). A route "escapes" only if it closes the dimensional gap without reopening an equally-fatal support gap.

| Route | Dimensional gap (box homogenizes) | Support gap (untrustworthy off-support) | Verdict |
|---|---|---|---|
| **(B) UDE** | **Escaped** — prescribed 3-D transport injects the spatial structure the box lacks; iron is *transported*, so which-cell-has-how-much becomes a physical consequence of v05 velocities, not a guess. | **Bounded, not eliminated** — the *closure NN* can still extrapolate garbage off its visited support (implementation brief line 60: "off-support is where the NN extrapolates garbage"). But fixed physics + structural conservation *bound* the extrapolation, and the repo already has the cure: bounded Monod-anchored closures + offline Fisher excitation design + symbolic-distillation go/no-go. Known, managed risk. | **Escapes the dimensional gap; relocates a *smaller, bounded* support gap onto the closure — which the merged infra already targets.** |
| **(A) FNO** | **Escaped** (if genuinely spatially coupled). | **Reopened, and worse** — a frozen emulator is trustworthy *only on its PPE support*, and gradient-based inversion **actively drives the optimizer off-support** (offline-MBO surrogate-overestimation; neural-adjoint needs a boundary loss precisely because unconstrained descent exploits surrogate error). This is the *spatial re-incarnation* of the box's negative-R² trap: "emulator can't be trusted where the data isn't." (Verifier note: "provably steers" is overstated — it's empirical/structural distributional shift, not a theorem — but the failure mode is canonical.) | **Escapes the dimensional gap but relocates the support gap onto the emulator, and the calibration optimizer walks straight into it.** Requires trust-region loss + re-verify-against-true-Darwin + de-biasing + surrogate-aware UQ to be trustworthy. Strictly more moving parts. |
| **SBI** | Escaped **only** if the simulator is spatially-resolved Darwin (needs the PPE). | **Reopened as model misspecification** — documented **>40% parameter bias and 95%→<60% coverage collapse under "minor" mismatch**; robust fix needs ground-truth labels we lack. | **Relocates the gap to misspecification, with the robustness fix blocked.** |

**The decisive point:** neither route conjures information from 14 iron cells — the Data Processing Inequality caps identifiability at what the data carry regardless of forward model (verifier, on the SBI/calibration claims). What a spatially-resolved forward model *can* add is a **better forward operator** (spatial coupling), which is exactly the thing that could turn the box's negative held-out R² positive — and that is not forbidden by DPI. **(B) adds that operator with the smallest, most-bounded new support gap. (A) adds it with the largest, optimizer-seeking support gap.** That is why (B) wins the decisive test, not just the cost test.

---

## 4. The single cheapest go/no-go experiment

**The "does-transport-help" 2-column probe.** Runnable on **CPU or one short H200 job. No local GPU. No new GCM runs. No full build. Reuses only already-merged code** (`transport.py::column_tendency`, `integrators.py`).

**Setup:**
1. Take two adjacent water columns at **fixed Carroll parameters**. Drive them with **different prescribed v05 iron forcing / velocities** (different `dust`/`w` kwargs already supported at transport.py lines 68, 107) so they hold **distinct DFe magnitudes** — the minimal analog of real Darwin's O(1) spatial CV that the 0-D box lacks (box CV ~4e-5).
2. **Hold out one column's iron "obs."** Fit the free params/closure to the *other* column's DFe by backprop through the mass-conserving transport.
3. **Measure held-out R²** on the withheld column's DFe.

**Decision rule:**
- **R² > 0 on the held-out column (where the 0-D box gives negative R², STATUS.md #163)** → transport is the fix, **(B) is green-lit**. Proceed to the Phase-1 build order (integrator `f(t,x)` edit → excitation design → symbolic-distillation gate → Thomas diffusion), all local-5090-gated per the implementation brief.
- **R² ≤ 0** → spatial coupling *alone* is insufficient from this data, and **neither (A) nor (B) will clear E2 from 14 cells.** Redirect effort to **data-staging** (the dense Darwin POSi/TRAC16 target already noted in STATUS.md) *before* any large model build — and in that world, revisit whether a PPE for (A)/SBI is worth commissioning.

This probe is decisive because it isolates the *one* variable that separates (B) from the failed Track-1 box — spatial transport — for a few CPU-hours, and its result gates the entire spatially-resolved-calibration program.

---

## 5. Questions for Jon (domain science) vs. what we decide ourselves

**We decide ourselves (engineering/method calls — do not spend Jon's time):**
- Route ranking (B > A > SBI), conditioning mechanism if (A) ever revives (FiLM/hypernet), the 2-column probe design, the Phase-1 build order, the symbolic-distillation go/no-go gate, windowed-BPTT / short-window-anchor loss design. All self-contained on the synthetic twin + merged infra.

**Genuinely needs Jon (domain science — Paper #2-defining):**

1. **Is a v05 perturbed-parameter ensemble ever affordable?** The one fact that could un-shelve (A)/SBI. How many full ECCO-Darwin integrations across Carroll-6 are realistically obtainable on Explorer/AICR, and at what disk cost? If the answer is "≈0," (A) and SBI stay shelved by physics of budget, not preference.

2. **Which closure is the primary Paper #2 target — iron-limitation or calcification — and what mechanistically drives calcification?** This sets what the UDE's bounded NN replaces and which absolute anchor (GEOTRACES iron vs Daniels/MODIS ratio) carries the identifiability. His call per the NEXT_SESSION prep list.

3. **What real forcing climatology should drive the excitation?** Our excitation is currently synthetic-drawdown (light-driven, offline-Fisher-designed). Moving from a methods result to a real-data claim needs the *real* seasonal light/dust amplitudes for the target AOI. Data question, not a Phase-1 blocker, but it gates the E2 real-data claim.

4. **What counts as "independent validation = discovery" for him?** The held-out-real-data-R²>0 E2 gate is our internal bar; we need Jon's agreement that clearing it (vs Carroll's own under-constrained values) constitutes an independent inversion, not just a consistency check — this is the line between Paper #1's framing and Paper #2's.

5. **Are v05's archived 3-D velocity + vertical-mixing fields on disk for the target AOI?** (B)'s "zero new GCM runs" presumes the standard Darwin3-offline velocity archive is available at the resolution we need — a data-availability confirmation, the one input (B) does depend on.

---

## Key citations (carried from the bundle; verifier-flagged items marked)

- **SC-FNO** — *Sensitivity-Constrained Fourier Neural Operators for Forward and Inverse Problems in Parametric Differential Equations*, arXiv:2505.08740 (2025, ICLR). Forward-vs-gradient decoupling (state R²≈0.986 vs Jacobian R²≈0.21–0.82; multi-param inversion <0.64); sensitivity loss restores >0.94. **Verifier correction (PARTIAL): the sensitivity supervision uses finite differences, so it does NOT require differentiable Darwin — (A)'s real cost is the PPE, not (B)'s hard part.**
- **Derivative-Informed FNO (DINO)** — arXiv:2512.14086 (2025) / O'Leary-Roseberry & Ghattas arXiv:2206.10745. Alternative derivative-informed operator; note "only known fix" was overstated by the verifier.
- **ScIReN** — *Scientifically-Interpretable Reasoning Network*, arXiv:2506.14054 (v4, AAAI 2026); code github.com/gomes-lab/ScIReN. Direct BINN successor; A-vs-B contrast. **Verifier correction (PARTIAL): honest parameter-recovery R² = 0.989 (structured) vs 0.226/0.721 (black-box), real-data tie ≈0.58; edge partly from the interpretable encoder; synthetic-twin only.**
- **BINN** — Xu et al., *Biogeochemistry-Informed Neural Network*, arXiv:2502.00672 (2025) + EGUsphere egusphere-2025-3282. Positional-encoder spatial parameter map (matched per-site Bayesian at 0.86 corr). Cheap orthogonal DINN upgrade; but its forward model is laterally decoupled 1-D soil columns → not proof a point forward model recovers transported-tracer structure.
- **UDE** — Rackauckas et al., *Universal Differential Equations for Scientific Machine Learning*, arXiv:2001.04385 (v4, 2021). Closure-inside-mechanism recovery from limited data.
- **UDE identifiability** — arXiv:2510.14140 (2025), functional/parametric identifiability for UDEs (already cited in the repo recipe); warns a universal approximator can compromise mechanistic identifiability.
- **UDE systems-biology review** — PMC12398592 (2025). "NN absorbs the system" non-identifiability trap; mass-conservation constraint "dramatically improved interpretability"; sparse-data floor.
- **Neural-adjoint** — Ren, Padilla, Malof, NeurIPS 2020, arXiv:2009.12919. Boundary loss required so gradient descent doesn't exploit surrogate error; re-verify against true simulator.
- **Conservative Objective Models** — Trabucco et al., ICML 2021. Offline-MBO surrogate overestimation. **Verifier note: "provably steers off-support" is overstated — empirical/structural, not a theorem.**
- **INO** — *Inverse Neural Operator for ODE Parameter Optimization*, arXiv:2603.11854 (2026). Stiff-regime Jacobian instability of backprop-through-surrogate; amortized inverse avoids it. (id uncertain per bundle; medium confidence.)
- **WOMBAT-lite** — Buchanan et al., *Optimization of WOMBAT using surrogate ML methods*, Biogeosciences 22:5349 (2025). **Verifier REFUTED as SBI precedent: it is GP-surrogate + emcee MCMC (route-A-style), ~512 sims — supports (A), not SBI. Do not cite as an SBI feasibility anchor.**
- **SBI Practical Guide** — arXiv:2508.12939 (2025). No param-count/sim-count correlation; "most successful SBI needs at least a few thousand simulations."
- **SBI misspecification** — Ward et al. (2022) RNPE; ICLR-2026 blogpost. >40% bias, 95%→<60% coverage collapse under minor mismatch.
- **RoPE / FRISBI** — Wehenkel et al. ICML 2025 (arXiv:2405.08719); Senouf et al. (2025). Robust SBI needs known-ground-truth calibration labels — **unavailable for DarwinDiff (verified)**.
- **Calibrate-Emulate-Sample** — Cleary, Garbuno-Inigo, Lan, Schneider, Stuart, JCP 2021, arXiv:2001.03689. Gradient-free emulator-in-the-loop UQ; the clean way to add posteriors later.
- **Veros-JAX** — *Towards fully differentiable neural ocean model with Veros*, arXiv:2511.17427 (2025). AD through a 4-yr FV rollout recovers physical params — direct (B) ocean precedent (synthetic twin, 2 params, no identifiability analysis).
- **NeuralGCM** — Kochkov et al., Nature 2024 (s41586-024-07744-y); precip-obs online training arXiv:2412.11973; heatwave storylines arXiv:2506.10660. Short-window (5–11 day) calibration only → calibration loss must be short-window absolute anchors, not decadal pattern-matching.
- **SamudrACE** — arXiv:2509.12490 (2025). Coupled emulator with an explicit BGC hole; conditions on nothing parameter-like → no emulator to port; parameter-conditioned ocean-BGC forward model is first-of-kind regardless.
- **Learned multiphysics inversion / SURGIN** — arXiv:2304.05592 (TLE 42(7) 2023); arXiv:2509.13189 (2025). Geophysics precedent for freeze-emulator-then-invert at ~2000 sims — the only domain where (A)'s invert-half is precedented.
- **ICON-A tuning** — Watson-Parris et al., GMD 18:3681 (2025). PPE + emulator calibration "introduces additional uncertainty related to the emulator's generalizability outside the training set" — the support gap, named.

**Repo files referenced:** `src/darwindiff/transport.py` (`bgc_tendency_field` L36, `column_tendency` L121, no-flux conservation L100–118), `src/darwindiff/integrators.py`, `docs/NEXT_SESSION.md` (the "seam" open thread L37–42), `docs/research_notes/2026-07-06_ude_phase1_implementation_brief.md` (off-support-garbage L60, build order), `docs/research_notes/2026-07-06_ude_phase1_design_brief.md`, `STATUS.md` (single v05 run, #163 negative held-out R², Track 2 / #177).

---

## Appendix — repo-claims verification (main-loop check, 2026-07-07)

The synthesis agent's load-bearing repo claims were independently re-checked against `HEAD` + the
uncommitted working tree before this note was landed:

- **`transport.py` structure — VERIFIED.** `bgc_tendency_field` is at L36 and reads all six params by name
  off the frozen `carroll6.P` registry (L61–66); `column_tendency` at L121 composes BGC + `vertical_diffusion`
  + `vertical_advection`; the no-flux flux-difference operators (L100–104, L114–118) conserve the
  column-summed tracer by construction. So `column_tendency` **is** the spatially-resolved, autograd-clean,
  mass-conserving `f(Carroll-6, forcing) → dstate` the note claims — route (B)'s core is genuinely merged.
- **`dust` / `light` forcing kwargs — VERIFIED** (L131–132, broadcastable), so the §4 go/no-go probe can
  impose distinct per-column DFe via `dust` on the merged code with no new plumbing.
- **One correction to §4's probe recipe:** `w` (vertical velocity) is currently a **scalar** (`w: float`,
  L127) applied uniformly, guarded by `if w != 0.0` (L148) — so per-column *velocity* variation is **not**
  yet supported and would need a small generalization (tensor `w` + mask). This does not affect the probe:
  per-column *dust* variation alone imposes the distinct DFe magnitudes the test needs. Noted so the probe
  script drives spatial contrast through `dust`, not `w`.
- **The `f(t, x)` time-aware forcing edit is present as UNCOMMITTED working-tree WIP** (integrators.py +
  transport.py `dust`/`light`), tested green (12/12 in `tests/test_integrators.py`). It is Round-1 §1 of the
  implementation brief and is effectively done; it is not yet committed on this branch.
