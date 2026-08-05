# The flagship does not reproduce, and this time the config is not why

**Date:** 2026-08-02 · **Job:** 255511 (30/30 COMPLETED) · **Status:** falsifier FIRED, cause NOT established
**Pre-registration:** `docs/findings/2026-07-31_prereg_flagship_window_sweep.md`

## The reading

The pre-registration's falsifier: `fs_w200` re-runs the published flagship configuration and must
reproduce `alpfe` 49/50, `scav_rat` 25/50, `R_PICPOC` 50/50 within seed noise, or **no window
conclusion may be drawn.**

| arm | alpfe | scav_rat | diatomgraz | R_PICPOC |
|---|---|---|---|---|
| **`fs_w200`** (the falsifier) | **50/50** | **1/50** | 13/50 | **45/50** |
| `fs_w100` | 50/50 | 0/50 | 0/50 | 21/50 |
| `fs_w400` | 44/50 | 0/50 | 31/50 | 43/50 |
| `fs_null_w100/200/400` (untrained) | 10/50 | 0/50 | 32/50 | 0/50 |
| *published flagship* | *49/50* | ***25/50*** | *—* | *50/50* |

**`scav_rat` 1/50 against a published 25/50. The falsifier has fired for the second time, and job
255511 licenses no window conclusion either.**

## This time it is not the recipe

Everything the 2026-08-01 failure was blamed on is demonstrably correct here. Every task logged
`[prov] POSI_W=1 USE_EPPLEY_T=1 AOI_W={1,2,2}`, identical across all 30, and the run-time assertion
did not fire. `verify_run.py` returns **exit 0 VERIFIED** on 50/50 seeds with no inert-term
discrepancy. The arms are internally consistent: the untrained nulls are identical at all three
windows (correct — with `NB23_LR=0` no training occurs, so the readout cannot depend on the
integration window), `alpfe` 50/50 against a null of 10/50 and `R_PICPOC` 45/50 against a null of
0/50 are both real signal.

Diffing the recorded config against the published flagship run
(`/scratch/qi_zim_neu/logscale/ctrl_n50`, located by its per-AOI signature `eqpac` 8 / `natl` 19 /
`sopac` 49, and corroborated by `confirm/ep4k_n50` matching the documented 4000-epoch variant
`natl` 40 / `eqpac` 6 / `sopac` 48) gives **no substantive config difference**. Of 15 differing keys,
12 are fields the runner did not record in July and now does. The three real differences are
outcomes, not settings:

```
elapsed_s_total_batch   flagship 4890.6   vs   fs_w200 1895.1     (flagship 2.6x SLOWER)
loss_final              flagship   39.66  vs   fs_w200   58.68
per_aoi_loss_final      eqpac  6.25 -> 22.69   natl 11.69 -> 12.72   sopac 5.02 -> 5.28
```

## Where the failure actually is

The per-AOI breakdown localises it precisely:

```
fs_w200  scav_rat per-AOI:  eqpac 1/50   natlsubpolar 0/50   southernoceanpac 50/50
flagship scav_rat per-AOI:  eqpac 8/50   natlsubpolar 19/50  southernoceanpac 49/50
```

**The Southern Ocean leg reproduces perfectly (49 -> 50). The North Atlantic leg collapses from
19/50 to 0/50 and eqpac from 8/50 to 1/50.** Since the per-AOI rule needs 2 of 3 legs, losing natl
alone is enough to take the count from 25 to 1. And eqpac is exactly where the loss inflated 3.6x.

This is consistent with the independently-established result that `scav_rat`'s Southern Ocean
recovery is genuine and local (30/50 vs untrained 0/50, P=3.15e-24). What has not reproduced is the
*other two* basins — which is to say, the part of the flagship count that was always the weakest.

## What this rules in and out

- **Not the config.** Identical on every recorded key, and the three appendix omissions are
  positively confirmed applied.
- **Not the gate.** `verify_run` exit 0, no inert terms, 50/50 seeds.
- **Not seed noise.** 1/50 vs 25/50 is not a 5-seed band.
- **Not nondeterminism.** The measured run-to-run drift is ~1.7% and flips no grades.
- **Not the window.** `fs_w200` *is* the published window.

What remains is something the artifact does not record. The flagship ran **2026-07-28 14:01**, and
**five commits have touched `scripts/run_v3.0_joint_multi_aoi.py` since** (`6bb6f2b`, `c64216a`,
`b83eb49`, `c4323ae`, `67ef8d7`, then `d37862b`, `9c67de2`). `c4323ae` is the largest (+77 lines) but
its runner hunks are self-described as "pure REPORTING -- it is not in the loss", so it is not an
obvious culprit and **the cause is not established.** The candidates are a changed runner default
that `flagship_geo1.sh` does not pin, or a changed loss/normalisation path.

**The decisive experiment is cheap:** check out `scripts/run_v3.0_joint_multi_aoi.py` at its
2026-07-28 state, re-run `fs_w200` (5 tasks, 10 seeds each), and see whether 25/50 returns. If it
does, the flagship is bound to a code build and every published count needs a commit SHA. If it does
not, the cause is an unrecorded input and the search moves to environment.

## The structural lesson

`flagship_geo1.sh` was built by reading values **back out of a verified artifact**. That is the best
available method and it is still not sufficient, because *an artifact can only record what the runner
chose to write*. Two of the four observables' anchor cell counts (`n_geo_surf_cells_per_aoi`,
`n_geo_sub_cells_per_aoi`) were not recorded until `67ef8d7` on 2026-07-30 — **after** the flagship
ran — so they cannot be compared against it at all. Any input the runner reads and does not record is
invisible to reconstruction, and no amount of config discipline recovers it after the fact.

**Nothing records which code produced which number.** That is the gap, and it is larger than the
config gap that was closed this morning.

## Consequence for the manuscript

The flagship trio `25/50` and `scav_rat` `25/50` **cannot currently be reproduced from the committed
repository**. Until the cause is found, they should be treated as unverified. The two legs that do
reproduce cleanly are `alpfe` (50/50 vs null 10/50) and `R_PICPOC` (45/50 vs null 0/50), plus the
Southern Ocean `scav_rat` leg (50/50), which is separately gated and published.
