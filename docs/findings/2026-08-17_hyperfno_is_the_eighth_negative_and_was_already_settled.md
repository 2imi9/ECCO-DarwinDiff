# HyperFNO: the eighth architecture negative, and the first one that was already answered before it was asked

**Date:** 2026-08-17
**Status:** live
**Verdict:** **DEAD-END.** Do not open an arm, do not add a hypernetwork ablation, do not cite
it as motivation in the workshop write-up.
**Compute:** none.

## The short answer

No. And the process point matters more than the verdict: **this was settled, and I re-derived it
from the literature instead of querying the map.** `python scripts/research_map_db.py settled
"parameter-conditioned emulator"` returns **four rows, all "No, shelved"**. Under CLAUDE.md §1 the
correct response was to quote those rows and stop.

## What HyperFNO actually is

A hypernetwork that **generates the weights of an FNO conditioned on the PDE's physical parameter
vector λ** — including the spectral kernels `R^l`, the spatial convolutions `W^l`, the lift `P`
and both projections `Q, Q'`. Trained by meta-learning over a distribution `p(λ)`; at inference
it emits a full FNO for a new λ zero-shot. It also states an inverse mode
(`λ* = argmin_λ ‖u − f(ψ_λ, x)‖²` by gradient descent through the frozen hypernetwork), but
**presents no inverse-problem experiment** — Section 3 reports forward MSE only.

> **⚠️ Citation hygiene.** HyperFNO has **no arXiv ID and no DOI.** It is a 4-page non-archival
> workshop paper — Alesiani, Takamoto & Niepert, ML4PS @ NeurIPS 2022, paper #89, at
> `https://ml4physicalsciences.github.io/2022/files/NeurIPS_ML4PS_2022_89.pdf`. An arXiv full-text
> search returns zero hits and OpenAlex has no record. **Any arXiv id or DOI ever attached to
> "HyperFNO" is fabricated.** The only citable locator is that PDF URL. Do not confuse it with
> `HyperNOs` (arXiv:2503.18087), which is a hyperparameter-optimisation library, not a
> hypernetwork method.

## Why it is dead here, in one line

**N_λ = 1.** HyperFNO's entire contribution is the map λ → FNO weights, and DarwinDiff has **one
v05 trajectory at one parameter setting**. At `p(λ) = δ(λ₀)` the `diag(λ)` modulation terms
receive no gradient signal in λ at all. The conditioning axis is not sparse, it is *empty*, and
the method degenerates to a plain FNO carrying extra unidentifiable weights. That is sufficient
on its own; it is arithmetic, not an experiment.

## Confirmation already in the repo

1. **Settled four times.** The parameter-conditioned *calibration* emulator route is shelved on a
   missing perturbed-parameter Darwin ensemble, plus SC-FNO's measured plain-FNO parameter-gradient
   **R² = 0.21–0.82** at forward-accurate solutions (0.998 with sensitivity labels). Scope note is
   exact and HyperFNO sits inside it.
2. **The mechanism was pre-registered.** `docs/research_notes/2026-07-07_param_conditioned_emulator_decision.md`
   already names *"FiLM … or a HYPERNETWORK, NOT broadcast-concatenation"* as the design default
   for that route. So HyperFNO is not a new idea failing on mechanism — it is one of the two
   already-chosen mechanisms inside an already-shelved route. Two consequences: do **not** argue
   against it with "just concatenate λ, it is cheaper" (this repo rates concatenation the weak
   option), and do **not** read the pre-registration as endorsement (it is contingent on a PPE that
   does not exist, and FiLM is the preferred half of the pair).
3. **Track 1 is covered twice over, independently of the PPE.** `ded77`: no architecture can fix
   structural non-identifiability. And settled: five independent estimators (EnKF, CES/EKI, history
   matching, KOH GP emulator, SINDy) all hit the same rank-1 `alpfe`↔`scav_rat` null. A surrogate
   swap is inside that negative. On Track 1 a learned operator would stand in for `carroll6.py`,
   which is **already exact, differentiable and fast** — so it can only add error, and that error
   lands on the null direction where it would *manufacture* apparent `scav_rat` recovery.

## No S3 carve-out

RNO earned one because conformal prediction on physics residuals is **detachable, post-hoc, and
aimed at a measured pathology**. HyperFNO has no residual loss, no calibration layer, no UQ,
nothing post-hoc. Its only separable idea is the λ-conditioning itself, which is exactly what the
missing ensemble blocks. **Live component: none.** That asymmetry with RNO should be stated
plainly rather than softened.

## Four arguments NOT to make (they are wrong and would not survive a referee)

- **"No approximator can raise I(D;λ)."** False unconditionally, and *this repo disproves it*:
  0-D box → 1-D column moved the Fisher spectrum from [800, 2.8e-14] (rank-1) to [53272, 40]
  (genuinely rank-2). Forward-model **structure** changes identifiability here. The true, narrower
  claim is that a learned surrogate *of the same map* adds no structure and is strictly lossier.
- **"S4 (the EKI run) refutes it."** Overstated. EKI establishes *estimator*-independence, not
  *forward-path*-independence — it reused the same geo1 bundles and anchors. It is corroboration.
- **The storage bill.** Do not repeat "300 TB to 22.5 PB". That prices full 1992–2023 v05 runs,
  the wrong unit. Perturbation runs are short 1–3 yr segments from the assimilated v5 pickup and
  are cheap. The blocker is a scheduling/design decision, not a physical impossibility — which
  means this idea *will* come back, and should come back under a better successor design.
- **"It inflates per-cell dispersion, so the arithmetic pooler will manufacture recovery."**
  Plausible hazard, never measured for a hypernetwork. Today's province work shows σ taking 0.379
  and 1.310 on the *same* polygon purely from fit configuration, so the direction is not
  predictable. Unknown is not a kill — and it is not evidence for adoption either.

## Why the list keeps coming out the same way

Seven Anandkumar-lab operators, then RNO, now HyperFNO — all fail for one reason: **they are all
moves along the approximator axis, and neither binding wall sits on that axis.** Track 2's wall is
information (geometry test: error spatially flat, coastal-proximity correlation ≈ 0 in all four
regions; horizon ≈ 1 step). Track 1's wall is a rank-1 structural null that five estimators failed
to break. Both are properties of the *(model, observable set)* pair, so a scan over network
families is a scan over the wrong coordinate and will return the same answer every time.

The two things that *have* moved identifiability in this repo were both non-architectural: **a new
out-of-manifold observation, and a forward-model structure change.** Independent external
confirmation, from the one systematic study of this design space: PDEInvBench (arXiv:2605.25353,
TMLR 2026) reports that increasing the diversity of **initial conditions** in training data yields
greater gains than expanding the range of **PDE parameters** — an information lever beating a
parameter-coverage lever, reproducing our own result from outside.

## The one follow-up worth logging

Not a hypernetwork, and cheap: **run the existing 1-D column path
(`transport.py::column_tendency`, already merged, zero new GCM runs) as a richer forward model and
see whether `scav_rat`'s low bias moves.** Because EKI held the geo1 box fixed, the repo currently
has evidence that changing the *estimator* leaves recovery unchanged and **no evidence about
changing the forward operator**. That is a real gap in S4's coverage and it is testable on
artifacts already on disk.

If the parameter-conditioned route is ever unblocked, note the gate is **data staging, not an
experiment**: roughly 60–600 distinct λ decks to fit a 6-D conditioning map. The planned ~17-deck
central-difference ensemble does **not** unblock it — 17 points in 6-D is an order of magnitude
short, and below HyperFNO's own 10 tasks for 1–3 parameters. And even then HyperFNO is the wrong
family member: the repo's recorded default is FiLM with true Jacobian labels, an ICLR 2026 paper
(arXiv:2607.23466) beats it by 45–49% nRMSE with lightweight shift modulation, and **its own
authors moved on to CAPE** (arXiv:2304.14118).
