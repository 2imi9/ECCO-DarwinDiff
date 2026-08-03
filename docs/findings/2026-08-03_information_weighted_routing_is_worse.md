# Information-weighted per-AOI routing makes recovery worse, and it says why

**Date:** 2026-08-03 · **Status:** pre-registered, `verify_run` exit 0 · **Job:** 256953
**Pre-registration:** `docs/findings/2026-08-03_prereg_per_parameter_routing.md`
**Rule:** `docs/findings/2026-08-03_routing_rule.json` (committed before the run)

## Result: H1 rejected

Both arms n=50, same config, same learning rate, each graded against its own untrained null
measured in the same experiment. The only difference is the per-(parameter, AOI) gradient
weighting, with each parameter's **total** gradient held fixed.

| arm | `alpfe` | `scav_rat` | `diatomgraz` | `R_PICPOC` |
|---|---|---|---|---|
| flagship-config control, re-run here (published 25/50) | 49/50 | **26/50** | 2/50 | **50/50** |
| information-weighted | **50/50** | **11/50** | 1/50 | **45/50** |
| both untrained nulls | 10/50 | 0/50 | 32/50 | 0/50 |

**The weighted arm is worse.** `scav_rat` falls 26 → 11 and `R_PICPOC` 50 → 45. Only `alpfe`
moves up, by one seed. The hypothesis that redistributing gradient toward informative basins lifts
the frontier is rejected as tested.

Per-AOI, `scav_rat` fell in **all three** basins — eqpac 8→2, natl 19→11, sopac 49→47 — despite
eqpac being *up*-weighted from 1.00 to 1.97.

## Cause 1: my observable-to-parameter map was incomplete, and the run proved it

The rule gave `R_PICPOC` **zero** weight in the Southern Ocean because sopac has zero Daniels
cells, and I mapped `R_PICPOC` to the Daniels PIC/POC observable alone. That is wrong. The flagship
also runs `DARWIN_PATTERN_W=1`, `POC_SUB_W=3` and `CHL1_W_EXTRA=3`, and those Darwin-target terms
are scored over **the whole basin, sopac included**. `R_PICPOC` controls PIC production, which feeds
POC, so it has a live gradient path in sopac that has nothing to do with Daniels.

The measurement is unambiguous: zeroing that gradient took `R_PICPOC`'s sopac leg from **40/50 to
17/50**. It did not go to zero, so part of the leg really is inherited through the shared DINN — but
most of it was being actively fitted by terms my rule did not count.

**So the rule under-counted information by mapping each parameter only to its headline anchor.**
That is a defect in my instantiation, not in the idea. The fix is mechanical: derive each
parameter's observable set from the loss terms that actually carry a gradient to it, rather than
from the anchor it is named after.

## Cause 2: information is not helpfulness

Separately, and not fixed by the above: eqpac was up-weighted 1.00 → 1.97 for `scav_rat` and its leg
got **worse**, 8/50 → 2/50. More gradient from a basin the Fisher calls informative made the
estimate there worse.

A Fisher diagonal measures how *sensitive* the predicted observables are to a parameter. It says
nothing about whether the residual it will be driven against is correct. In a basin where the box is
misspecified, high sensitivity means the optimiser is pulled harder toward the wrong value. Weighting
by information alone therefore up-weights confident error.

This is the more interesting of the two, because no amount of fixing the observable map addresses
it. A weighting that helps would need to combine sensitivity with something about model adequacy —
residual structure, or an out-of-sample check — and this project has no such measure today.

## What survives

- **The derivation still predicts the single-basin result.** The rule independently identified the
  Southern Ocean as most informative for `scav_rat`, at 2.2× the information per cell of either
  other basin, and that is where `scav_rat` recovers (sopac 94–100% across every arm and learning
  rate tested). The prediction was right; acting on it by reweighting was not.
- **The flagship's uniform `AOI_W = {1, 2, 2}` is better than the information-weighted alternative**,
  which was not obvious beforehand and is now measured.
- **The negative is clean.** Pre-registered, `verify_run` exit 0, both arms against their own nulls,
  total gradient held fixed so effective learning rate is not confounded.

## What not to conclude

Do **not** read this as "per-parameter routing does not work". It tests one specific weighting —
Fisher information at the prior midpoint, over an observable map now known to be incomplete. The
stronger form in the pre-registration, `PER_PARAM=1` (an independent trunk per parameter), is
untouched by this result: it removes representation sharing rather than redistributing gradient, and
the two failure modes above do not apply to it.

## Next

1. Rebuild the observable map from the loss terms that carry gradient to each parameter, not from
   the headline anchor. Re-derive and re-run; the `R_PICPOC` collapse should disappear.
2. Run `pp_head` (`PER_PARAM=1`) with its capacity-matched control. It is the arm that tests the
   representational hypothesis, and nothing here bears on it.
3. Do not attempt a helpfulness-weighted rule until there is a model-adequacy measure that does not
   use Carroll.
