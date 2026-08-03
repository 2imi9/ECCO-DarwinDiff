# There was no regression. It was a learning rate, and the evidence was on my screen

**Date:** 2026-08-03 · **Status:** resolved · **Job:** 256342 (16-way bisect)
**Retracts:** `docs/findings/2026-08-03_the_flagship_is_bound_to_a_code_build.md`

## The answer

`scripts/configs/flagship_geo1.sh` did not pin `NB23_LR`. The runner default is **5e-3**. The
flagship never set it, so it trained at 5e-3. The window-sweep pre-registration specified **1e-3**,
and both job 244487 and job 255511 ran at 1e-3.

| run | code | lr | `scav_rat` | natl leg | `R_PICPOC` sopac |
|---|---|---|---|---|---|
| published flagship | 2026-07-28 build | (default) | 26/50 (52%) | 19/50 (38%) | 40/50 (80%) |
| bisect **t15 = HEAD** | **today** | **5e-3** | **7/10 (70%)** | **6/10 (60%)** | **8/10 (80%)** |
| `fs_w200` | today | **1e-3** | 1/50 (2%) | 0/50 (0%) | 0/50 (0%) |

**Today's code reproduces the flagship.** All sixteen bisect trees do, from `34513bc` through HEAD.
There is no code regression, and the `R_PICPOC` Southern-Ocean "collapse" reported this morning is
retracted — at the correct learning rate it is 80%, matching the published 40/50 exactly.

The pre-registered falsifier was right both times. My configuration was wrong both times, in two
different ways: first the three appendix omissions (`POSI_W`, `USE_EPPLEY_T`, the per-AOI weights),
then the learning rate.

## The evidence was in the diff I ran, and I filtered it out

On 2026-08-02 I diffed `fs_w200` against the flagship and reported "no substantive config
difference — 12 of 15 differing keys are fields the runner did not record in July." That output
contained, in full:

```
  lr:
      A = <absent>
      B = 0.001
```

I saw it. I classified it with the other `<absent>` rows as a schema addition and moved on, then
spent the next several hours inferring a code regression, staging a 2026-07-26 tree, launching a
20-seed reproduction and a 16-way bisect, and committing a finding that was wrong.

The heuristic that did the damage: **"absent on the old side means a newly-recorded field, therefore
not a difference."** That is true for `n_steps`, `dt_days`, `global_scalar` and nine others. It is
catastrophically false for `lr`, because a value absent from the old artifact is *unknown*, not
*equal*. Absence of a record is not evidence of agreement — the same fallacy as a check that passes
on an empty set, which this repo has now hit four times.

`compare_run_bitwise.py` refuses to report agreement over zero values. The config diff had no such
rule, and it should: a key present on one side and absent on the other must be reported as
**UNKNOWN and blocking**, never folded into a "no substantive difference" summary.

## The guard I shipped that morning asserted seven variables and not this one

`tests/test_flagship_config_guard.py`, committed 2026-08-02, pins `POSI_W`, `USE_EPPLEY_T`, the
three per-AOI weights, `DANIELS_RPICPOC_W`, `RATIO_W` and `GLOBAL_SCALAR`. The sbatch asserts the
same seven at run time and exits 3 on drift.

It passed `fs_w200` cleanly, because the learning rate was not on the list. The guard was built from
the *previous* failure's list of omissions rather than from the set of variables that can change the
answer, so it hardened the perimeter and left the centre open. A run that was wrong in the single
most important optimisation lever passed a bespoke config guard, `verify_run` at exit 0, and a green
753-test suite.

`NB23_LR=5e-3` is now pinned in `flagship_geo1.sh` and asserted by the guard, negative-controlled by
setting it to 1e-3 and confirming the test fails.

## What this costs and what it buys

Cost: two 30-task arrays and one 16-way bisect, plus a committed finding that had to be retracted
the same day.

Buys, and this is the part worth keeping:

- **The flagship reproduces on current code.** `scav_rat` 26/50, `alpfe` 49/50, `R_PICPOC` 50/50 and
  the Southern-Ocean legs all stand. Nothing in the manuscript needs re-deriving on that account.
- **`scav_rat` recovery is strongly learning-rate dependent outside the Southern Ocean.** natl goes
  38% → 0% between 5e-3 and 1e-3 while sopac stays at 98–100%. That is a real, new, and unclaimed
  result: the Southern Ocean leg is robust to the optimiser and the other two are not, which is
  independent support for the finding that `scav_rat` is *locally* identifiable there and
  optimisation-limited elsewhere.
- The canonical flagship artifacts are still missing (`n50e2k_percell_trio` exists nowhere), so the
  published tuple still cannot be re-graded from its own run. That remains open and is now the only
  live provenance defect of the three claimed today.

## Corrections to make elsewhere

- `docs/findings/2026-08-02_flagship_does_not_reproduce_and_the_config_is_not_why.md` — its title is
  now false. The config *is* why. Banner it.
- The window-sweep pre-registration specified `1e-3` with no stated reason. Any future sweep must
  justify a deviation from the flagship's optimiser settings or inherit them.
- `test_canonical_numbers.py` records `scav_rat: 25`, but the official grader on the nearest
  surviving reproduction gives **26/50**, with 25/50 being the *iron-pair joint* count. The
  marginal and the joint are being conflated. Separate open item.
