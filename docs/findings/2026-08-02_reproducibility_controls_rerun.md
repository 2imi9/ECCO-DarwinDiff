# The reproducibility controls, re-run honestly

**Date:** 2026-08-02 · **Status:** measured · **Scripts:**
`scripts/analysis/compare_run_bitwise.py`, `scripts/analysis/grade_flip_under_drift.py`

The 2026-08-01 session ended with three open doubts about whether this project can prove what it
ran: a bitwise control that **failed** at 1.7% on an identical config, a first version of that
control that printed "BITWISE IDENTICAL" while comparing **zero** values, and a suspicion that the
earlier `so_repro` certificate shared the defect. All three are now resolved, two favourably.

## 1. The vacuous control is confirmed, and it was vacuous exactly as suspected

`grade_window_swap.sbatch` read `params[k]['joint']`. Artifacts have no such key — they store
`joint_recovered`, `joint_cellweighted_recovered`, `per_aoi_recovered` and thirteen others.
Verified against a real artifact:

```
param entry keys: joint_abs_rel_offset, joint_aoiweighted_*, joint_band, joint_carroll_published,
                  joint_cellweighted_*, joint_geom_cellweighted_recovered,
                  joint_median_pooled_recovered, joint_recovered, per_aoi_log_sd,
                  per_aoi_recovered, per_aoi_recovered_geom, per_aoi_recovered_median
has bare `joint`? False
```

Every lookup returned `None`, every value was skipped, the running maximum stayed at its `0.0`
initialiser, and the verdict line read **"max relative difference: 0.000e+00 -> BITWISE
IDENTICAL"**. A reproducibility certificate was issued on an empty set.

This is the same shape as the research map's SUPERSEDES constraint, which passed on an empty join
from the day it was written. **A check that passes on nothing is indistinguishable from a check
that passes on everything.** The fix is therefore not "read the right key" but a comparator that
treats an empty comparison as failure: `compare_run_bitwise.py` exits **2** when it compares fewer
than `--min-values` values, and prints the count on the verdict line so it cannot be read past.

## 2. `so_repro` is GENUINE — the doubt is retired

It used `per_aoi_recovered`, a field that exists, so it was never vacuous. Re-run with the new
comparator over every recorded field:

| pair | shared seeds | values compared | max rel. difference | verdict |
|---|---|---|---|---|
| `so_only` vs `so_repro` | 10 | **480** | **0.000e+00** | BITWISE IDENTICAL |
| `prior_so_only` vs `prior_so_abl` (untrained null) | 50 | **2400** | **0.000e+00** | BITWISE IDENTICAL |
| `repro_w200` vs `eq_sub` | 10 | **480** | **1.666e-02** | DIFFERS |

The depth arms' reproducibility certificate stands. The 2026-08-01 worry that it "may share the
defect" is **wrong**, and it should not be repeated.

## 3. The 1.7% is real, and it is not a config difference

Diffing the full recorded config of `repro_w200` against `eq_sub`: **all 68 substantive keys are
identical**. The only differences are `elapsed_s_total_batch` and the loss it converged to
(`loss_final` 1.5695 vs 1.5705, `per_aoi_loss_final` 0.78476 vs 0.78525). Same config, same seeds,
different answer.

The cause is that **determinism is never requested**. There is no
`torch.use_deterministic_algorithms`, no `cudnn.deterministic`, no `CUBLAS_WORKSPACE_CONFIG`
anywhere in `scripts/` or `src/`; `torch.manual_seed` fixes initialisation, not the order of GPU
reductions. So drift of this size is **expected behaviour**, and the correct reading is the
reverse of the obvious one: the *bitwise-identical* results are the lucky cases, not the norm, and
"bitwise reproducible" is not a property this project should claim.

**Honest statement: the same config and seed reproduce recovered parameter values to about 1.7%,
not bitwise.**

## 4. But it flips no grades — measured, not argued

Drift size alone cannot answer the question that matters. What matters is whether any graded unit
sits closer to the Cal boundary than its own drift. Taking the two same-config runs as replicates
and grading each side independently over 60 (seed, param, AOI) units:

- **observed grade flips: 0 of 60**
- units whose own drift exceeds their own margin: **1 of 60** — `(seed 6, diatomgraz, eqpac)`,
  margin 0.0037 against drift 0.0046. It did not flip (0.3916 and 0.3963, both inside the band),
  but it *could* have.

The one fragile unit is `diatomgraz`, which is already the parameter this project refuses to
interpret (prior midpoint 2.8% of the box width inside the Cal band, `KNOWN_PRIOR_CONTAMINATED`,
xfailed in `test_param_registry_wiring.py`). No `alpfe`, `scav_rat` or `R_PICPOC` unit came within
its own drift of the boundary.

**Do not quote the maximum `|rel_offset_A - rel_offset_B|`, which is 0.218 here.** That statistic
is dominated by units recovered far from Carroll, where a small *relative* change in the recovered
value is a large change in rel_offset while sitting nowhere near the decision boundary. Compare a
unit's drift to its own margin.

## Scope, honestly

Section 4 rests on **one pair, eqpac only, 10 seeds, `N_STEPS=200`, with a stripped loss**
(`surf0.0_sub1.0_pinn0.0`). It is not the flagship, and 60 units is a small sample for a
tail question. It supports "the measured drift did not flip a grade here", not "counts are immune
to nondeterminism". The clean way to close it is to run the flagship config twice and compare;
`grade_flip_under_drift.py` takes two directories and does exactly that.

## What changed

- `scripts/analysis/compare_run_bitwise.py` — compares every recorded field, exits 2 on a vacuous
  comparison. `tests/test_compare_run_bitwise.py` holds that behaviour, including the exact
  renamed-field case that caused this.
- `scripts/analysis/grade_flip_under_drift.py` — turns a drift measurement into a grade-flip count.
- `scripts/slurm/grade_window_swap.sbatch` — the inline vacuous comparison replaced by both.
