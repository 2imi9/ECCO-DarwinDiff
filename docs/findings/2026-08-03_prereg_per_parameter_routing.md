# Pre-registration: the 3-of-4 frontier is a parameter-sharing artifact

**Date:** 2026-08-03 · **Status:** pending · **Written with zero routed-run JSONs on disk**

## The derivation

This is not a sweep proposal. It is a chain of four things already measured, and one thing that
follows from them and has never been tested.

**1. The information is present.** The Q1 Fisher rank is **4/4** in eqpac and natlsubpolar, so the
four observables are jointly identifiable
(`docs/findings/2026-07-23_observable_frontier_config_analysis.md`).

**2. No configuration recovers all four.** `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`};
MLD-channel + heavy Daniels holds {`alpfe`, `diatomgraz`, `R_PICPOC`}. Two operating points, never
one (`docs/findings/2026-07-23_recovery_table_verified.md`).

**3. So the loss is in the estimator, not the data.** Full-rank information with sub-full recovery
locates the deficit between the observations and the estimate. That is the estimator.

**4. The estimator shares one representation across all six parameters.** `DINN` is
`self.net = nn.Sequential(*layers)` mapping environmental channels to `n_outputs=6`
(`src/darwindiff/networks.py:80-135`). One trunk, one input-channel set, six outputs. There are no
per-parameter heads.

**5. Parameter sharing has never been varied.** The parameterisation ladder is
`GLOBAL_SCALAR > POINTWISE > PER_AOI_DINN > shared DINN`
(`scripts/run_v3.0_joint_multi_aoi.py:381-397`). Every rung varies **spatial** sharing — one scalar,
per-cell free field, one network per basin. Not one rung varies **parameter** sharing. `PER_PARAM`
does not occur anywhere in `src/` or `scripts/`. Across **3000 run artifacts on the cluster, 2940
record `gating_policy=ungated` and 60 predate the field: zero used any routing.**

**H1.** The 3-of-4 frontier is an artifact of forcing six parameters through one shared
representation. Removing the sharing lifts it to 4-of-4 without new data.

The documented conflict is exactly parameter-versus-parameter and exactly representational: the MLD
channel helps `diatomgraz` and breaks `scav_rat`. An input channel cannot change the information
content of the observations — it changes what the shared trunk can represent. A shared trunk must
find one representation that serves both, and the measurements say no such representation is found.

**H0.** It does not lift, and the frontier is real in a way the rank-4 diagnostic does not capture.
That is the more interesting negative: it would mean Fisher rank at a point does not predict
recoverability, and we would have measured that rather than assumed it.

## Arms

n=50, per-AOI ≥2-of-3, three AOIs, 2000 epochs, `N_STEPS=200`, sourced from
`scripts/configs/flagship_geo1.sh`.

| arm | what it removes | status |
|---|---|---|
| `pp_ctrl` | nothing — one shared trunk. The design all 3000 runs used. | exists |
| `pp_route` | shared **gradients**: each parameter learns only from its identifying loss terms | `gating.py` exists, **never run** |
| `pp_head` | shared **representation**: per-parameter output heads on a shared trunk | **must be built** |
| `pp_surgery` | shared-gradient *conflict*, without hand-specifying routing (PCGrad) | must be built |
| `pp_null_*` | one architecture-matched untrained null per arm, never shared between arms | — |

`pp_head` is the arm that tests the derivation directly. `pp_route` and `pp_surgery` act on gradients
while the trunk stays shared, so if `pp_head` lifts the frontier and they do not, the bottleneck is
representational rather than a gradient conflict — a distinction worth separating, because the two
have different fixes and the literature (PCGrad) only addresses the second.

**Capacity control, mandatory.** `pp_head` adds parameters, so it must be compared at matched total
capacity, not matched width. Otherwise any lift is confounded with "a bigger network fits better",
which is the exact confound that made the resolution-sharpening result null on 2026-07-12. The
control is `pp_ctrl` widened to `pp_head`'s parameter count.

## The selection rule for `pp_route`, and its honest limit

For parameter *j* and configuration *c*, assign `c*(j) = argmax_c I_jj(c; θ₀) · w_j²`, where `I_jj`
is the Fisher diagonal under *c*'s declared observation set and weights and `w_j` is the registry
prior width.

**θ₀ is the prior midpoint, not Carroll and not θ\*.** Every Fisher result in this repo to date was
evaluated at a fitted optimum or at Carroll's published values (`observation_design.py:193-201`
scales by `|theta_Carroll|`). Both are unavailable before a fit, and either would leak the answer
into the rule and reproduce the contamination this design exists to avoid.

**The limit, stated plainly:** this rule ranks configurations that differ in **loss terms and
weights**. It cannot rank an **input channel**, because a channel changes the parameterisation and
not the information, so it does not enter the Fisher at all. The MLD-versus-Darwin-pattern conflict
is therefore only *half* addressable by routing — which is itself an argument for `pp_head`, where
each parameter's head sees the channels it needs without imposing them on the others.

`scripts/analysis/emit_routing_rule.py` computes the map and writes
`docs/findings/2026-08-03_routing_rule.json`. **That file is committed before any training job is
submitted, and its commit hash is quoted with the results.** If the computed map contradicts the
expectation (`scav_rat → geo1`, `diatomgraz → mld_dan8`), the computed map wins and the
disagreement is reported as a finding.

**Recorded risk:** the rank-4/4 result was computed at a different evaluation point and may not hold
at θ₀. If the Fisher is rank-deficient at θ₀, H1 loses its premise and the experiment reports that
instead.

## Grading, and why it does not use the flagship

**Every arm is graded against its own untrained null measured in the same experiment.** On
2026-08-02 the flagship failed its own reproduction falsifier — `scav_rat` 1/50 against a published
25/50, config confirmed identical, `verify_run` exit 0
(`docs/findings/2026-08-02_flagship_does_not_reproduce_and_the_config_is_not_why.md`). Until that
resolves, no experiment may take the published numbers as a baseline.

**`diatomgraz` is graded at the Excellent band (≤10%), not Cal (≤40%).** Its prior midpoint sits at
rel 0.367, *inside* the Cal band, which is why its untrained null is 32/50 and why a trained 13/50
reads as below-null. At ≤10% the prior is outside the band. This is a derivation from the bounds,
fixed here before any routed run exists, not a threshold picked to flatter a number.

## Decision rule, fixed now

Per parameter, per arm: recovered = per-AOI ≥2-of-3 at n=50, against that arm's own untrained null,
Fisher exact, both tails, **P < 0.01**.

- **H1 SUPPORTED** if any of `pp_head` / `pp_route` / `pp_surgery` clears the null on **all four** in
  the same arm while `pp_ctrl` (at matched capacity) clears at most three.
- **H1 REJECTED** if no arm clears more than three. Report as a negative naming the rank-4
  diagnostic as the thing that failed to predict recoverability.
- **PARTIAL** if the conflicted pair lifts but `alpfe` or `R_PICPOC` falls. The frontier moved rather
  than lifted; the honest claim is a trade.
- **INCONCLUSIVE** if `pp_ctrl` fails the falsifier below, or if the capacity-matched control alone
  reaches 4-of-4 — in which case the effect was capacity, not sharing.

## Falsifier for a broken run

`pp_ctrl` must reproduce the two legs that **did** reproduce on 2026-08-02: `alpfe` ≈50/50 against a
null of ≈10/50, and `R_PICPOC` ≈45/50 against a null of 0/50, each within 5/50. `scav_rat` 25/50 is
deliberately **not** a falsifier — it does not currently reproduce, and requiring it would fail every
future experiment for an unrelated reason.

## Committed interpretations

- **Per-parameter heads lift it.** The claim is that the observable frontier was a parameter-sharing
  artifact, that the information was present at rank 4/4 throughout, and that the parameterisation
  ladder had a missing rung. CLAUDE.md's two-operating-point framing becomes obsolete and should be
  rewritten, not appended to.
- **Routing lifts it but heads do not.** The bottleneck is gradient conflict, not representation, and
  PCGrad is the right literature.
- **Neither lifts it.** "More optimization will close it" is retired — it has carried weight since
  2026-07-24 — and the project redirects to observations, the only remaining lever.

## Recorded before the fact

- `gating.py` has never been executed. A null result from `pp_route` is not evidence the machinery
  works until the routed path is shown covered by its 14 unit tests.
- PCGrad is Yu et al., *Gradient Surgery for Multi-Task Learning*, NeurIPS 2020, arXiv:2001.06782.
- `alpfe` and `R_PICPOC` are expected to be unaffected and act as internal controls. If they move,
  the mechanism is not the one written here.
