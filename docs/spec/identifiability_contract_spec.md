# spec — identifiability contract API (issue #210)

Shared state for the three-loop build (Andrew Ng's model, DeepLearning.AI "The Batch").
Amended at every gate. Location note: the skill puts `spec.md` in the project root; this repo
keeps specs under `docs/spec/`, so it lives here and is the same artifact.

**Phase 0 gate decisions were recorded, not asked.** The user is AFK for ~6h with a standing
instruction not to block on questions. Each decision below is marked with what would have been
asked and what was chosen.

---

## Vision

A scientist declares an **unknown** and gets back a **contract**: a machine-readable statement of
what is inferable about it from the declared observables, computed *before* any fit is run.

This is the half that ADCME (Xu & Darve) does not have. Their slide 38 gives a four-way taxonomy of
inverse problems and no identifiability column; their own NNFWI slide shows two visibly different
velocity models *at the same loss function value* and never names it. DarwinDiff already computes
every ingredient of the missing column; none of it sits behind a declaration.

## Success criteria

1. `Unknown` expresses all six current registry parameters with no loss of information.
2. `contract(unknown, evidence)` returns a `ContractReport` with exactly four clauses.
3. **A missing clause reads as `UNAVAILABLE`, never as `PASS`.** This is the ethos of the whole
   project rendered in code: a gap we name is not a gap that gets used against us.
4. The report has an exit code mirroring `verify_run`'s discipline, so it is usable as a CI gate.
5. The `relation` row (learned closures) is representable and correctly reports that the
   band-based clauses are `NOT_APPLICABLE`, replacing structural with the aliasing gate.
6. Round-trips: report → JSON → report.
7. Tests green.

## Verify strategy

**`tests`.** This is a library API with no UI and no dataset of its own, so "done" is a green suite
plus the success criteria above. (Gate question that would have been asked: browser / eval / tests.
Chosen `tests` because there is nothing to look at and nothing to benchmark; the clauses are
computed from evidence produced elsewhere.)

## The four clauses

| clause | question | needs | inapplicable when |
|---|---|---|---|
| `prior_contamination` | does the prior already satisfy the pass band? | bounds, reference, band, init sd | no reference (relation row) |
| `measured_null` | what does an UNTRAINED network of this architecture score? | a measured baseline rate at some n | never; every row needs a null |
| `structural` | is the unknown in the null space of the observable? | Fisher information under its identifying observable | never |
| `practical` | is it constrained tightly enough to matter? | CRLB or a profile-likelihood verdict | never |

## Design decisions taken at the Phase-0 gate

- **Q: should `contract()` compute the clauses, or consume evidence computed elsewhere?**
  **Chosen: consume.** The Fisher computation needs torch, the box model, real observations and a
  GPU. Making the contract depend on all that would make it untestable and unimportable. It
  therefore takes an `Evidence` object that the existing scripts populate. The contract's job is
  the *verdict logic*, which is what actually needs pinning down.
- **Q: should a missing clause block, or degrade?**
  **Chosen: degrade loudly.** `UNAVAILABLE` is distinct from `PASS` and from `FAIL`, and the
  overall verdict is `INCOMPLETE` if any clause is unavailable. Exit code 7.
- **Q: numeric thresholds — fixed or configurable?**
  **Chosen: fixed defaults, overridable.** Defaults come from measured project facts (Cal band
  0.40; aliasing gate 0.95 from the calibrated symbolic-distillation probe, NOT the 0.30-dex span
  which has already failed at aliasing 0.9908).
- **Q: relation row now or later?**
  **Chosen: now, as representation only.** The row must be expressible or the schema is just the
  registry with extra fields. Its clauses report `NOT_APPLICABLE` with a reason rather than
  pretending a band applies to a learned function.

## Open questions (carried, not resolved)

- The relation row needs a **chance-rate analogue**: what N free weights buy on n_val cells by
  luck. Does not exist anywhere today. Until it does, `measured_null` on a relation unknown is
  `UNAVAILABLE` by construction, which the API states rather than hides.
- `--require-baseline` is enforceable but not enforced by default in `verify_run`. Same gap here:
  the contract can be *checked* in CI but nothing yet forces it to be.
- Wiring `contract()` into `verify_run` is deliberately out of scope for this loop.

## Iteration log

- **iter 0** — spec written, gate decisions recorded (user AFK).
