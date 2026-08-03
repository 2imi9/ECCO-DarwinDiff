# Per-(parameter, AOI) weights derived from information, and what they say about the flagship

**Date:** 2026-08-03 · **Status:** derived, not yet trained on
**Script:** `scripts/analysis/emit_routing_rule.py` · **Pre-registration:**
`docs/findings/2026-08-03_prereg_per_parameter_routing.md`

## The rule

Per parameter *j* and AOI *a*, `w[j][a] ∝ I_jj(a; θ₀) · width_j²`, where `I_jj` is the Fisher
diagonal over **the cells that AOI's loss is actually scored on**, evaluated at **θ₀ = the prior
midpoint**. Nothing reads `CARROLL_VALUES`; the script asserts it.

θ₀ matters. Every Fisher result in this repo to date was evaluated at a fitted optimum or at
Carroll's values — `observation_design.py` scales by `|theta_Carroll|`. Neither is available before
a fit, and using either leaks the answer into a rule whose entire purpose is to be answer-free. The
prior midpoint is also exactly where `bounded_params` maps a zero-output untrained network, so it is
the information available at the initialisation the optimiser really starts from.

| parameter | eqpac | natlsubpolar | southernoceanpac | most informative | contrast |
|---|---|---|---|---|---|
| `alpfe` | 0.386 | **0.174** | **0.440** | southernoceanpac | 2.53× |
| `scav_rat` | 0.394 | **0.177** | **0.430** | **southernoceanpac** | 2.43× |
| `diatomgraz` | **0.633** | 0.367 | 0.0001 | eqpac | 5905× |
| `R_PICPOC` | **0.567** | 0.433 | **0.000** | eqpac | **∞** |

## Three things fall out, none of which used the answer

**1. The rule predicts the measured recovery.** It says the Southern Ocean is the most informative
basin for `scav_rat`. Measured, across every build and learning rate tested: sopac 98–100%, natl
0–38%, eqpac 2–16%. This is a pre-fit prediction from the observation design alone, confirmed by
post-fit measurement, and it is independent support for the 2026-07-30 result that `scav_rat` is
*locally* identifiable in the Southern Ocean.

**And it is not a sampling-density artifact.** sopac has **half** eqpac's subsurface-iron cells (14
vs 28) and still wins. Per cell it is **2.2× more informative** (0.0307 vs 0.0141); natl is 0.0136.
The Southern Ocean's iron observations are individually better at constraining scavenging, not
merely more numerous.

**2. The flagship up-weights the least informative basin.** `AOI_W = {eqpac 1, natl 2, sopac 2}`
applies uniformly to all six parameters. But natlsubpolar is the **least** informative basin for
*every* parameter (0.174–0.433), and it carries a weight of 2. Nothing chose that; the weights were
set per-AOI, never per-parameter, so they cannot express that eqpac owns `R_PICPOC` and `diatomgraz`
while sopac owns the iron pair. **This is a concrete, derived, testable improvement to the flagship
configuration, and it is the first one this project has had that did not come from a sweep.**

**3. `R_PICPOC` recovers 80% in a basin with exactly zero information about it.** sopac has **no
Daniels cells and no bSi cells** — the contrast is infinite because the denominator is a true zero,
not a floor. Yet `R_PICPOC` grades 40/50 there in the flagship. That recovery cannot be evidence
about the Southern Ocean; it is the shared DINN propagating a value fitted from eqpac and natl.

That is worth stating plainly, because it cuts against the metric we grade on: **a per-AOI leg can
score highly in a basin that contains no information about the parameter.** The per-AOI ≥2-of-3 rule
treats such a leg as independent evidence when it is inherited. It was already known that
`R_PICPOC` "generalises" to sopac; what is new is that the generalisation is into a basin of
*exactly zero* observational constraint, which makes it a property of the estimator, not a finding
about the ocean.

## Honest limits

- **It ranks observation sets, not input channels.** MLD changes the parameterisation, not the
  information, so it never enters the Fisher. The MLD-vs-Darwin-pattern conflict is only half
  addressable this way; the other half needs `PER_PARAM=1`.
- **Computed at θ₀, and the box is nonlinear.** The ranking could differ at θ\*. But θ\* is not
  available before a fit, which is the whole point — a rule that needs the answer is not a rule.
- **An earlier version of this script averaged over all ocean cells and got a flat answer**
  (1.00–1.07× for every parameter). That is a statement about where the *box* is sensitive, not
  where the *data* constrains it, and it is wrong for this purpose. The support matters more than
  the model here, which is itself the argument for spending on observations rather than optimisation.

## What to run next

The pre-registration's `pp_route` arm now has a committed, answer-free weight matrix to route by.
The cheapest decisive test is not the full ladder, though — it is to replace the flagship's uniform
`AOI_W = {1,2,2}` with these per-parameter weights and see whether the trio moves. That is one arm,
n=50, against the flagship's own untrained null.
