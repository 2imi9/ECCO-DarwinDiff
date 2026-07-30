# Pre-registration: is scav_rat's Southern Ocean recovery local, or inherited?

**Written 2026-07-30 BEFORE the run, with zero JSONs on disk for either arm.**
**Jobs:** submitted below. **Grading:** `verify_run` exit 0 then
`scripts/analysis/per_aoi_vs_null.py`.

## The observation this tests

`2026-07-30_per_aoi_legs_vs_their_own_null.md` measured that in every observations-only arm,
`scav_rat` recovers in the Southern Ocean and nowhere else:

| arm | eqpac | natlsubpolar | southernoceanpac | untrained |
|---|---|---|---|---|
| `obsonly_mld_litic` | 0/50 | 0/50 | **42/50** | 0/50 |
| `obsonly_mld` | 0/50 | 0/50 | **39/50** | 0/50 |
| `obsonly_litic` | 0/50 | 0/50 | **50/50** | 0/50 |

The 0/50 majority is an artifact of the 2-of-3 rule, not a measurement that nothing was learned.
But there are two incompatible explanations and the 3-AOI runs cannot separate them.

**H_local.** The Southern Ocean genuinely constrains the scavenging rate. It is the iron-limited
HNLC region where the sink is the dominant term in the iron budget, so the rate is exposed there
in a way it is not in the other two basins.

**H_pooled.** The Southern Ocean leg carries no independent information and is inheriting
magnitude from the other two basins through the shared DINN, exactly as R_PICPOC's Southern Ocean
leg was shown to do (it recovers with zero Daniels cells and collapses to 13.06x Carroll when the
anchor is pulled from the other two basins).

H_pooled is the prior expectation, because the R_PICPOC precedent is established and because the
degeneracy argument is global: at steady state a source scalar over a sink rate sets concentration,
and nothing about the Southern Ocean changes that algebra.

## The design

A **single-AOI** run on `southernoceanpac` alone. With no other basins in the fit there is nothing
to pool from, so the shared network cannot import magnitude. Whatever `scav_rat` does is then
local by construction.

- **Trained arm** `so_only`: the exact `OBSONLY` configuration
  (`GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0 DANIELS_RPICPOC_W=1.0 POSI_W=1.0 DARWIN_PATTERN_W=0.0
  POC_SUB_W=0.0 CHL1_W_EXTRA=0.0 NB23_PINN_WEIGHT=0.0 POSI_DARWIN_W=0.0 NB23_N_EPOCHS=2000`)
  plus `MLD_CHANNEL=1 DARWIN_IC=0`, with `AOIS=southernoceanpac`. n=50 seeds.
- **Untrained baseline** `prior_so_only`: byte-identical configuration at `NB23_LR=0`,
  `NB23_N_EPOCHS=1`, n=50. Required: no count is reportable without its architecture-matched null.

Note this run is only gradable because of today's fix. A single-AOI run needs the 1-of-1 rule, and
four graders hardcoded `>= 2` until this morning, which would have returned 0/50 for every
parameter regardless of what was recovered.

## Decision rule, fixed now

Let `k` be `scav_rat`'s recovered count in `so_only` out of 50, and `p` the recovered rate in
`prior_so_only` (with the rule-of-three floor 3/50 = 0.060 if the null count is zero).

- **LOCAL IDENTIFIABILITY** if `k >= 25` **and** `P(X >= k | n=50, p) < 0.01`.
- **POOLING** if `k` is not above `p` at `P < 0.05`.
- **AMBIGUOUS** otherwise, and it will be reported as ambiguous rather than rounded to either.

## What each outcome means, written before seeing it

**If LOCAL.** Scavenging is regionally identifiable and the global degeneracy is broken by Southern
Ocean data specifically. That is a genuinely new statement, it changes the note to Jon from
"scavenging does not recover" to "scavenging recovers in the Southern Ocean", and it tells the
iron-closure UDE where to aim. It would also mean the 4-observable denominator understates what is
recoverable, since `scav_rat` would be recoverable subject to a regional qualifier.

**If POOLING.** The Southern Ocean leg is inherited, `scav_rat` is genuinely unrecovered from
observations alone, and the existing framing stands unchanged. This is the expected outcome and it
is publishable: it would be the second parameter shown to inherit through the shared network, which
strengthens the pooling mechanism from one instance to two and makes the DOF-ladder story tighter.

**Either way the result is reportable**, which is why it is worth the GPU hours.

## Pre-registered secondary reads

1. `alpfe` should stay high in the SO-only run. It recovers in all three basins independently
   (50/50 in each against untrained 14 to 16), so removing the other basins should not hurt it. If
   `alpfe` also collapses, the run is broken rather than informative, and that is the control that
   tells us so.
2. `R_PICPOC` should collapse. The Southern Ocean has **zero** Daniels cells, so with no other
   basin to inherit from there is no calcite anchor at all. A high `R_PICPOC` here would mean
   something is wrong with the anchor gating.
3. `diatomgraz` is uninformative in this run and will not be quoted from it. Its untrained rate is
   0.64 to 0.72, so a single-basin count carries almost no discriminating power.
