# The integration window, not depth, decides which basin recovers `scav_rat`

**Date:** 2026-07-31 · **Jobs:** 241109 (46 tasks) + 241127 (grade) ·
**Gate:** `verify_run` **exit 0 on all ten arms**, `GATE_FAIL=0`, every primary arm 50/50 ·
**Pre-registration:** `2026-07-31_prereg_integration_window_swap.md`, written before any window-swap
JSON existed ·
**Verdict: H_window CONFIRMED. Both 2026-07-31 depth findings are RETRACTED.**

## The result

Everything byte-identical except `N_STEPS`. The basins trade places.

| window | days | box `DFe_2` (basin-blind) | `so_sub` `scav_rat` | `eq_sub` `scav_rat` | winner |
|---|---|---|---|---|---|
| **100** | 25 | 0.4047 nM | **0/50** | **23/50** | **eqpac** |
| 200 (what every prior run used) | 50 | 0.2671 nM | **33/50** | 6/50 | sopac |
| 400 | 100 | 0.1184 nM | **35/50** | 0/50 | sopac |

Observed subsurface medians: eqpac **0.4404 nM**, southernoceanpac **0.2245 nM**.

The window whose transient sits near eqpac is the window where eqpac wins. The window whose
transient sits near the Southern Ocean is the window where the Southern Ocean wins. That is the
whole effect.

## Against the pre-registered rule

| test | P (Fisher exact, two-sided) | |
|---|---|---|
| `eq_sub@100` 23/50 vs its window-matched null 0/50 | 8.69e-09 | PASS |
| `eq_sub` 100 vs 200 (23 vs 6) | 3.23e-04 | PASS |
| `so_sub` 100 vs 200 (0 vs 33) | 6.68e-14 | PASS |
| crossing at 100: `eq_sub` 23 vs `so_sub` 0 | 8.69e-09 | PASS |

One threshold, P < 0.01, both tails, fixed in advance. **`eq_sub` rises, `so_sub` falls, both against
nulls re-measured at their own window, and the arms cross.** H_window is confirmed on every leg.

**The falsifier clears.** The surface channel is near-converged and therefore should be
window-insensitive: `alpfe` in `eq_surf` goes 49/50 at 200 steps to **50/50** at 100. The window
change did not break the run; it moved only the channel that had not converged.

## What is retracted

- `2026-07-31_scavrat_southern_ocean_signal_is_depth.md` — **RETRACTED.** "Surface iron identifies
  the source, subsurface identifies the sink" does not survive. Both halves of that claim move when
  only the integration window changes.
- `2026-07-31_depth_mechanism_does_not_replicate_in_eqpac.md` — **RETRACTED.** eqpac's
  non-replication was a window artifact. At 100 steps eqpac recovers `scav_rat` **23/50**, better
  than the Southern Ocean ever did at its own best window relative to its null.

The measured counts and the `verify_run` gates in both documents stand. Only the interpretation is
withdrawn. The apparent confirmation of the 2026-07-22 column OSSE prediction is withdrawn with it:
the OSSE predicted a depth mechanism, and what was actually measured was a transient alignment.

## Why this happened

Two defaults combined, neither ever chosen deliberately.

1. **`N_STEPS = 200` was hardcoded** and never swept. Subsurface `DFe_2` decays monotonically from
   the hardcoded initial 0.5000 nM toward a 0.0096 nM fixed point and is only **47.5%** of the way
   there at 200 steps, so it sweeps through every basin's observed median on the way down.
2. **`DARWIN_IC=0` is the default** for these arms, so `state0` is uniform in every AOI, and the box
   has no horizontal transport. Forward sensitivities are then identical across basins to four
   decimals. **The forward model has no basin difference to explain a basin difference with.**

A half-converged observable plus a basin-blind model means the loss is scoring how close a shared
transient happens to pass to each basin's data. That is a property of the integration schedule, not
of the ocean.

## An unresolved control failure, disclosed

The bitwise no-op control **did not pass.** At `N_STEPS=200` the re-run differs from job 240673 on
10 shared seeds by up to **1.7%** in `joint_recovered` and 4.1% in the derived offsets, on identical
config (same seed, weights, epochs, cell counts, `n_geo_sub_cells_per_aoi=28`).

Two things worth separating:

- The first version of this control printed "BITWISE IDENTICAL" while comparing **zero** values,
  because it read a field named `joint` when the artifacts store `joint_recovered`. A vacuous pass.
  Fixed, and the corrected comparison is the one reporting 1.7%.
- **The earlier `so_repro` control that certified the depth arms as bitwise reproducible was ad hoc
  and is not in the repo.** It may have had the same defect. Its 0.000e+00 should not be relied on
  until re-run with the corrected field names.

**This does not change the conclusion here.** The window effect is 33/50 to 0/50 and 6/50 to 23/50;
a 1.7% per-seed jitter cannot produce that. But it is an open provenance problem and it is filed.

## What this changes going forward

- **`N_STEPS` is a first-class hyperparameter**, not a constant. Every published recovery count in
  this project silently depends on it. See issue #219.
- **Any absolute anchor compared against a non-converged tracer is scoring the transient**, so the
  same question applies to the Daniels calcite anchor and the abs POC/PIC/ALK terms, not only iron.
- **The anchor-segregated per-parameter routing plan is not invalidated, but its motivating example
  is.** Routing `scav_rat` to the subsurface channel would have hard-wired this artifact. The plan
  should be re-derived once a window is chosen and justified.
- The rival "sink dominance" hypothesis (`hy083`) is **not** rescued by this. It was already refuted
  by the L2 identity, and the forward model is basin-blind here in any case.
