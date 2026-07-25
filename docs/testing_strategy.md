# Testing strategy — targeting silent corruption

*Written 2026-07-25 after six bugs of the same class were found in one day. The suite was
311 tests across 40 files at the time and caught none of them. This document says why, and
what to add.*

## The failure class that actually bites this repo

Every bug found on 2026-07-25 has the same shape: **a function that guesses instead of
failing, returning plausible output for an input it could not actually serve.**

| # | Bug | What it returned instead of failing |
|---|---|---|
| 1 | `log_vars` default applied to linear checkpoints | forecasts with log/exp applied to four channels trained in linear space |
| 2 | `LOG_EPS=1e-12` clip floor | z-scores whose std was inflated 1.72×, compressing real signal to ±0.58 |
| 3 | climatology as `log(mean x)` not `mean(log x)` | a baseline displaced +0.39σ, inflating skill-vs-climatology |
| 4 | missing `lats`/`lons` | an ocean grid labelled with array indices `0..H-1` |
| 5 | no calendar | every datetime resolved to month 0, labelled with the requested date |
| 6 | out-of-range datetime | the nearest edge month wearing the requested timestamp |
| 7 | `_forward` assuming rank 4 | log transform and land mask applied to the **time** axis |

None raised. None produced NaN. Every one produced a number a scientist would plot.

**A 500-test suite that only asks "is the output right?" cannot catch these**, because the
output *is* a valid-looking array. The question that catches them is "does this function
refuse inputs it cannot honestly serve?"

## What the suite structurally could not catch

### Gap 1 — no "refuse to guess" contract tests

Assertion census at the time: **397** `==`, **114** `.shape`, **71** `allclose`, **55**
`approx`, but only **60** `pytest.raises` across 40 files. The suite is overwhelmingly
value-oriented. Bugs 4, 5 and 6 are *absences* of a raise; there was no test anywhere
asserting that an under-specified input must fail.

**Add:** for every function that resolves, looks up, defaults, or infers, one test that
asserts it **raises** when the information it needs is absent or out of range.

### Gap 2 — no-op shims made conformance untestable

`src/darwindiff/e2s/prognostic.py` falls back to shim `batch_func` / `handshake_*` when
earth2studio is absent. The shims **validate nothing**. Bug 7 survived because with the
shim active, tensors keep whatever rank the test used, so the suite proved the code *ran*,
never that it *conformed*.

**Add:** a conformance module that runs against the real dependency and skips explicitly
when absent (`tests/test_e2s_conformance.py`), plus a comment at the shim making the
limitation impossible to miss. **A green CI run is not evidence of conformance** when the
dependency is optional — record that in the PR template rather than assuming.

### Gap 3 — no invariant / metamorphic tests on the numerical core

Bugs 1, 2 and 3 are all *estimator* errors: the pipeline computed a well-defined quantity
that was the wrong quantity. Value tests cannot see this, because the value is correct for
the formula that was written.

**Add:** property tests that hold regardless of data —
- `destandardize(standardize(x)) ≈ x` for every log/linear configuration,
- `mean(log x) ≤ log(mean x)` with equality only for constant `x` (Jensen), asserted at
  the call site so the two orderings can never be swapped again,
- statistics computed with a floor must not shift when out-of-range values are moved
  *further* out of range (bug 2's signature: they did, by 1.72×).

### Gap 4 — no cross-implementation agreement check

The `scav_rat` count was disputed for hours because three separate audits each re-derived
it by hand and one propagated a wrong answer. The canonical `scripts/grade_recovery.py`
settled it in one run.

**Add:** where two implementations of one quantity exist, a test that they agree. Never
hand-derive a number the repo already has a tool for.

### Gap 5 — canonical numbers live only in prose

`scav_rat 26/50` drifted into twelve documents with no mechanism to detect it. Verified
results are stored as English sentences, and English does not fail CI.

**Add:** `tests/test_canonical_numbers.py` — the verified fact set as executable constants,
scanning tracked docs for contradictions. This is unusual for a test suite and correct for
this repo, because documentation *is* a deliverable here.

## Coverage targets, by risk

| Area | Type | Target |
|---|---|---|
| Numerical transforms (`standardize`, log floors, climatology) | property + round-trip | every configuration, both orderings |
| External adapters (`e2s/`, loaders) | refuse-to-guess + conformance | every resolve/default path raises when under-specified |
| Verified result numbers | golden constants + doc scan | every number quoted in STATUS/README |
| Graders | cross-implementation agreement | ad-hoc vs canonical must match |
| Box model, carbonate | existing value tests | unchanged, these were never the problem |

## What NOT to add

Coverage percentage as a goal. The suite was already at 311 tests and 0/7 on this bug
class. More value assertions would not have helped; different *kinds* of assertion did.

Also skip: tests for the plotting scripts' aesthetics, and any test that pins a number the
`verify_run` gate already re-derives from raw output.

## The one rule

**If a function can return something when it does not have what it needs, write the test
that makes it raise instead.** Six of seven bugs today die to that single rule.
