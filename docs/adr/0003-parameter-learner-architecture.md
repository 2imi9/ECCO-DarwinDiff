# ADR-0003: Parameter-learner architecture after the per-parameter trunk result

**Status:** Proposed
**Date:** 2026-08-03
**Deciders:** Lucas Qi (implementer). Science framing to be sanity-checked with Jon Lauderdale.
**Supersedes nothing.** Related: [0001](0001-differentiable-darwin-calcite-port.md),
[docs/dinn_design.md](../dinn_design.md)

## Context

The per-cell DINN maps an environmental input to six Carroll parameters at every grid cell.
Three architectural questions were open, and 2026-08-03 closed two of them.

**Forces at play**

- `scav_rat` is the binding leg of every joint count, and the only observable still moving.
- `alpfe` and `R_PICPOC` are at ceiling (100/100 and 100/100 at n=100). Any change must be
  judged on whether it holds them there, not on whether it improves them.
- `diatomgraz` is 0/100 at the honest band. Architecture is not its problem.
- Untrained baselines are **architecture-dependent** — untrained `alpfe` reads 10/50 at width
  16, 13/50 per-parameter, 15/50 widened. Every arm needs its own null or the comparison
  inflates in exact proportion to the change under test.
- The project's own significance bar is **P < 0.01**, and n=50 has repeatedly proven too small
  to defend an effect of ~10 seeds.

## Decision

**Do not adopt per-parameter trunks. Adopt nothing else until job 258439 reports.** Keep the
shared-trunk per-cell DINN as the production architecture, and treat trunk *width* as the one
live architectural lever, pending a within-job measurement.

## Options considered

### Option A — per-parameter trunks (`PER_PARAM=1`), one independent trunk per parameter

| Dimension | Assessment |
|---|---|
| Complexity | Medium — implemented, tested (`PerParamDINN`), gradient isolation verified |
| Cost | **~4.7x the weights of the flagship trunk, ~2x wall clock** |
| Evidence | **Rejected at n=100** |
| Risk | Trades basins: natl +11, sopac −5 |

**Pros:** removes representation sharing, which was a genuinely untested rung of the ladder
(0 of 3000 prior artifacts had used it); isolates each parameter's gradient.
**Cons:** the effect **does not replicate**. Seeds 0–49 gave 45/50 vs 34/50 (P = 0.0128);
fresh seeds 50–99 gave **38/50 vs 38/50, P = 1.0000**. Pooled P = 0.0897.

### Option B — widen the shared trunk (width 16 → 39)

| Dimension | Assessment |
|---|---|
| Complexity | **Trivial** — one env var, no new code |
| Cost | ~4.6x weights, modest wall clock |
| Evidence | **Strongest surviving candidate, not yet established within a job** |
| Risk | Larger nets score higher untrained; needs a matched null |

**Pros:** width 39 reaches `scav_rat` **72/100** where the published width-16 flagship is 25/50,
and it is the arm that reaches a clean **100/100** in the Southern Ocean. Consistent with the
4000-epoch result (25 → 41/50 on identical data), which is also an optimisation effect.
**Cons:** the 72/100-vs-25/50 comparison is **cross-job**, and this session established that
cross-job comparison here is unsafe — 14 recorded keys differ against the older artifact and
every one is `<absent>`, including `lr`. Absent is unknown, not equal.

### Option C — keep the flagship width-16 shared trunk

**Pros:** it is what every published number was measured on; zero risk.
**Cons:** leaves `scav_rat` at 25/50 when a one-variable change plausibly doubles it.

### Option D — adequacy-based loss masking (`FET_AOI_W`)

| Dimension | Assessment |
|---|---|
| Complexity | Low — implemented, default is a bit-identical no-op |
| Cost | Zero |
| Evidence | **Primary hypothesis rejected; the diagnostic itself is validated** |

Zeroing the Darwin-pattern FeT term in the basin whose residual exceeds its signal moved
`scav_rat` **20/50 → 21/50** — inert. The falsifier arm (dropping the *most adequate* block)
behaved as predicted and hurt badly, which means the measure correctly identifies which blocks
carry the recovery. Removing an inadequate block simply frees nothing.

## Trade-off analysis

The real trade-off is not between architectures; it is between **capacity and evidence**. Every
intervention that has moved `scav_rat` — 4000 epochs, width 39, per-parameter trunks — adds
optimisation budget or parameters, and the only one tested at n=100 lost its effect entirely
once the budget was matched. That pattern says the remaining gains are optimisation, not
representation, and that the correct architectural move is the cheapest one that adds capacity.

It also says something sharper about `eqpac`: **11/100 in both arms, identical to the seed.**
It has now resisted capacity, epochs, information weighting, representation sharing, and
adequacy masking. No estimator-side change should be expected to move it.

## Consequences

**Easier:** architecture selection is now a one-variable question (width), testable in one job.
**Harder:** every future architectural claim needs n=100 and its own null — n=50 has now
produced one effect (P = 0.0128) that evaporated on replication, so it is not a defensible
sample size for this metric.
**To revisit:** if 258439 shows width is also inert, then `scav_rat`'s remaining gap is not
addressable on the estimator side at all, and the next move is observational (a real
`234Th`/`210Po` scavenging anchor) rather than architectural.

## Action items

1. [x] Test per-parameter trunks at n=100 — **done, rejected** (job 258256).
2. [x] Test adequacy masking with a falsifier — **done, primary rejected** (job 258314).
3. [ ] **Job 258439**: width 16 vs width 39, shared trunk, same job, n=100, each with its own
       architecture-matched null. This decides Option B vs Option C.
4. [ ] If Option B wins, re-run the flagship tuple at width 39 and update the canonical
       numbers registry in `tests/test_canonical_numbers.py` in the same commit.
5. [ ] Either way, record `dinn_hidden_dim` as a first-class reported variable — it is already
       in the artifact, but no published table carries it.
