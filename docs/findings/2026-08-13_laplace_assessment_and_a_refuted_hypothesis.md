# Laplace methods for DarwinDiff: one clean refutation, one useful pole, and three different "Laplaces"

**Date:** 2026-08-13 · **Cost:** local CPU, minutes · **Script:**
`scripts/analysis/pole_structure_and_observation_window.py` · **Prompted by:** arXiv 2503.13158
and the suggestion that Laplace methods, including a "nested Laplace" on matrices, might help more
than expected.

## First: three different things share the name, and only one is that paper

| | what it is | relevance here |
|---|---|---|
| **Laplace transform** | integral transform t → s; turns d/dt into ×s **for linear systems** | arXiv 2503.13158's tool |
| **Laplace approximation** | Gaussian approximation to a posterior at its mode, covariance = inverse Hessian | **we already use it, unnamed** |
| **Integrated Nested Laplace Approximation (INLA)** | Rue, Martino & Chopin 2009, *JRSS-B* 71(2):319–392, `10.1111/j.1467-9868.2008.00700.x` — fast approximate Bayesian inference for latent Gaussian models | the likely referent of "nested Laplace"; a different method entirely |

Worth stating because the second one is not a gap at all: **our CRLB work *is* a Laplace
approximation**. Inverse-Fisher error bars are exactly the Laplace-approximation covariance. So
"Laplace" is already in the repo under another name, and the honest framing is that we use the
approximation and not the transform.

## The paper

**Zimmering, Coelho, Gupta, Maleshkova & Niggemann (2025), "Breaking Free: Decoupling Forced
Systems with Laplace Neural Networks"** (arXiv:2503.13158, v2 Sep 2025). Laplace-Net is a
decoupled, solver-free framework for **forced** systems that separates internal dynamics, external
inputs and initial values in the Laplace domain, so a model can be re-fitted quickly to new forcing.

Structurally that maps onto our box surprisingly well — internal dynamics (biology, scavenging),
external input (dust deposition `alpfe·Φ`), initial value (the Darwin IC).

## Why it cannot do the thing we actually need

**The Laplace transform cannot break the alpfe↔scav_rat degeneracy, and this is provable rather
than empirical.** `ded111` states the degeneracy as a gauge symmetry: `(alpfe, r0) → (λ·alpfe,
λ·r0)` leaves the predicted DFe field unchanged, for any `g`. The Laplace transform is a **linear,
injective** operator, so if `y(t)` is invariant under the symmetry then `Y(s) = L[y]` is invariant
too. No invertible re-representation of an observable can break a symmetry of the map that produced
it. This is the same argument that rules out covariate input channels (`ded111`, and the measured
covariate result), applied to the output side instead of the input side.

## What it *did* suggest, and the test that refuted it

The suggestive part: a transfer-function view says information lives somewhere in the s-plane —
`s → 0` is the steady state, finite `s` is the transient. And the repo has already measured
something of exactly that shape (`2026-07-31_prereg_flagship_window_sweep.md`, integrating to 3200
steps):

| observable | anchors | % converged at 200 steps (50 d) |
|---|---|---|
| DFe₁ surface | `alpfe` | 100.1% |
| PIC/POC | `R_PICPOC` | 100.0% |
| **DFe₂ subsurface** | **`scav_rat`** | **47.5%** |

plus the measured fact that `scav_rat` recovers **only** at 50 days — half and double both fail.

**Hypothesis (pre-stated in the script):** `alpfe` and `R_PICPOC` are identified from the `s → 0`
limit so their sensitivity saturates early; `scav_rat` is identified from the transient, so its
sensitivity is **non-monotone in the observation window and peaks near 50 days**, set by the slow
pole. **Falsifier:** if `scav_rat` saturates monotonically like `alpfe`, the framing adds nothing.

### Result 1 — the poles are real and the timescale match is good

Jacobian of the one-step map at Carroll truth: 13 finite decay constants, median **4.66 d**,
slowest **41.98 d**, with exactly two slow poles at **40.9 d and 42.0 d** against a flagship window
of **50 d**. The box's slowest natural timescale genuinely sits at the observation window.

### Result 2 — the hypothesis is REFUTED

Relative log-sensitivity `|d ln y / d ln θ|` of each parameter's own anchor observable:

| days | `alpfe` | `scav_rat` | `R_PICPOC` |
|---|---|---|---|
| 5 | 0.391 | 0.435 | 0.080 |
| 20 | 0.500 | 0.859 | 0.893 |
| **50** | 0.459 | **1.223** | 0.993 |
| 100 | 0.519 | **1.676** | 1.000000 |
| 200 | 0.580 | **2.614** | 1.000000 |
| 400 | 0.603 | **4.568** | 1.000000 |

`scav_rat`'s sensitivity is **monotonically increasing and nowhere near saturating** — it is 3.7×
larger at 400 d than at 50 d. There is no peak at 50 days. **H is refuted.**

Two side confirmations fall out. `R_PICPOC`'s sensitivity converges to **exactly 1.000000**, which
is `ded87` ("`R_PICPOC`'s sensitivity to PIC is exactly unity because dPIC = R_PICPOC·mort is linear
and decoupled") recovered numerically from an independent direction. And `alpfe` is nearly flat from
~20 d, matching its 100.1%-converged anchor.

## The negative result is the valuable part

**Recovery of `scav_rat` gets *worse* at longer windows while its sensitivity gets *better*.** The
window sweep found it fails at 100 d; sensitivity at 100 d is 1.68 versus 1.22 at 50 d. So the
window result **cannot be an observability or sensitivity phenomenon**, and any explanation framed
that way — including the Laplace one I proposed — is wrong.

The reconciliation is already in the repo and points the other way: as the box runs toward steady
state, **DFe₂ spatial contrast collapses** (self-twin Stage 0: DFe₂ rel-SD falls 0.0834 → 0.0101 in
eqpac and 0.2599 → 0.0636 in the Southern Ocean, both below their frozen minima). Per-cell
sensitivity rises while *across-cell contrast* dies, and recovery needs the contrast. That reframes
the 50-day window as **a compromise between a still-growing sensitivity and an already-collapsing
spatial contrast** — not as a resonance with a pole.

That is a testable, mechanistic statement the repo did not have this morning, and it arrived by
proposing a Laplace explanation and watching it fail.

## Verdict

- **Laplace transform / Laplace-Net: NO** for identifiability — provably cannot break the gauge
  symmetry — and our bottleneck is not forward modelling of forced systems (`ded77`: no architecture
  fixes structural non-identifiability). Its pole machinery is a **useful diagnostic**, and it
  earned its keep here by generating a falsifiable hypothesis that died cleanly.
- **Laplace approximation: already in use**, as inverse-Fisher CRLB. Worth *naming* it as such in
  the write-up, since that connects our error bars to a standard method reviewers know.
- **INLA / "nested Laplace": genuinely untried, and the most promising of the three** — fast
  approximate posteriors for latent Gaussian models, which is close to the per-cell spatial-field
  structure we fit. But it assumes a latent *Gaussian* field with a sparse precision matrix, and our
  per-cell parameter field is the output of a nonlinear network passed through a nonlinear box, so
  the assumption does not hold as stated. Recorded as a lead with that caveat, not as a plan.

**Nothing here changes a reported number.**
