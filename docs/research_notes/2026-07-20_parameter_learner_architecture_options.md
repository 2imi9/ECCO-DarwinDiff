# Is there an architectural way to improve the parameter learner? — literature scan

Prompted by the question: Track-1 was the original ask, it sits at ~57%, and `diatomgraz` is not
recovered. Is there genuinely no architectural fix, or have we just not looked?

Searched 2026-07-20. **Inline WebSearch, no agent fan-out** (see memory
`feedback_workflow_cost_discipline`).

---

## 1. The honest framing first: two of these are not architecture problems

**No architecture can fix structural non-identifiability.** If the observations carry no information
about a parameter, that is information-theoretic. A better network cannot recover what is not there.
That part of the wall is real.

**But we no longer know which wall we are looking at.** As of 2026-07-19 our own data shows
`alpfe` is FLAT by the profile-likelihood diagnostic (span 0.0235) *and* recovers 9–10/10. So the
diagnostic cannot currently separate *structural* from *practical* non-identifiability, and we do
not actually know which one `diatomgraz` has. **The binding gap right now is diagnostic, not
architectural** — which is why the FIM re-run matters more than any new model.

---

## 2. What the literature says, and what actually transfers

The nearest literature is on **hybrid neural ODEs (HNODEs)** — a mechanistic ODE with an embedded
neural network. Its headline result:

> **There is a fundamental expressiveness–identifiability trade-off.** Embedding a neural network in
> a dynamical model can compromise the identifiability of the mechanistic parameters, because the
> network absorbs signal the parameters should have explained.
> ([npj Syst Biol Appl 2024](https://www.nature.com/articles/s41540-024-00460-3);
> [bioRxiv preprint](https://www.biorxiv.org/content/10.1101/2024.06.04.597372v2.full))

**Important caveat on transfer.** That pathology is about a network *added as a term* in the
dynamics. Our Track-1 DINN does not do that — it **parameterises** the box model (per-cell → 6
Carroll params), so there is no separate learned term competing with the parameters. The literature's
central failure mode therefore applies to **Track-2's UDE**, not directly to Track-1.

What transfers to Track-1 is narrower but sharper:

### (a) Global vs local optimisation — directly implicated, and we already have evidence

> Model calibration in mechanistic models usually relies on **global optimization** to explore the
> parameter space, while training hybrid models necessitates **local, gradient-based** methods.

This is exactly the mismatch that bit us on 2026-07-19: `theta_star` was fit with 600 Adam steps
from a **single** initialisation (Carroll), and the profile search — which starts from `theta_star`
and runs further — beat it by 10.5%. We patched it with a bounded refinement loop
(`--max-refine`, commit `1b93922`), but the literature-standard answer is **multi-start / global
search**, which we have never run. This is the cheapest concrete improvement available and it is a
*fitting* change, not an architecture change.

### (b) Amortised inference / neural posterior estimation — the paradigm-level option

[SBI/NPE](https://arxiv.org/html/2405.08719v2) learns a conditional density estimator from
(parameter, simulated-data) pairs and returns an approximate **posterior** rather than a point
estimate. It has been applied to ocean-adjacent water-quality inversion
([R. Soc. Open Sci. 2025](https://royalsocietypublishing.org/rsos/article/12/5/241471/235831/Simulation-based-inference-advances-water-quality)).

**Why this fits DarwinDiff unusually well.** STATUS.md already frames Track 1 as a
*surrogate-to-model identifiability study* — "which parameters are identifiable, which are not, and
why" — **not** a recovery chase. A posterior *is* that answer: a wide posterior is the
non-identifiability result, stated in the natural language of the question, with uncertainty instead
of a pass/fail recovery rate. It would also replace `n≥10 seeds` bookkeeping with a single
calibrated object.

The closest published match to our setup is
**[InVAErt networks](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12105793/)** — amortised inference
*and* identifiability analysis for **lumped-parameter** models. Our box model is exactly a
lumped-parameter model. This is the single most on-point reference found.

### (c) Regularisation / sparsification — Track-2, not Track-1

Proposed HNODE fixes include penalising the network's contribution, decorrelating network output
from the mechanistic part, [structure-aware sparsification](https://arxiv.org/html/2505.18996v1), and
[bounded neural correction classes with Gronwall-type guarantees](https://www.biorxiv.org/content/10.1101/2024.12.08.627408v2).
These are the right toolbox for the **UDE closure** work (#176), where a learned term genuinely
competes with mechanistic parameters. They do not address `diatomgraz`.

---

## 3. Recommendation, ordered by cost

| # | Move | Cost | What it buys |
|---|---|---|---|
| 1 | **Multi-start `theta_star`** in `identifiability_sloppiness.py` | ~1 line + GPU-h | Removes the optimisation confound entirely; literature-standard; we already know our single-start fit was under-converged |
| 2 | **Finish the FIM re-run** with the fixed step budget | ~6 GPU-h | Tells us whether `diatomgraz` is structurally or practically unidentifiable — currently unknown |
| 3 | **NPE / amortised posterior** pilot on the box model | days | Reframes the deliverable from "recovered / not recovered" to a calibrated posterior, matching how the project already describes itself |
| 4 | Sparsification / bounded-correction | weeks | Track-2 UDE only |

**1 and 2 are prerequisites for 3.** Building an amortised posterior on top of a fitting procedure
we know is under-converged would inherit the same defect in a more expensive package.

---

## 4. The answer to the question as asked

*Is there really no architectural way to improve the parameter learner?*

**There is no architectural fix for the part that is structural, and we do not yet know how much of
our wall is structural** — our own diagnostic just failed its convergence check, and it calls a
parameter we demonstrably recover (`alpfe`) "FLAT". The most defensible next step is not a new
architecture: it is **multi-start fitting plus a valid re-run of the identifiability diagnostic**,
after which the question can be asked properly.

If we then want an architectural change, the literature-supported one that matches how this project
already describes itself is **amortised posterior inference (NPE / InVAErt)** — not a bigger or
different predictor network.
