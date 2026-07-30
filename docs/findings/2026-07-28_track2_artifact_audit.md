# Track-2 artifact audit — what is actually backed by a committed result file

**Date:** 2026-07-28 · **Method:** every number read directly from `docs/findings/track2_runs/*.json`,
not from prose. Provenance strings in `2026-07-19_results_matrix.md` were checked for existence.

## Backed by a committed artifact

| finding | measured value | artifact |
|---|---|---|
| Emulator invents negative iron | **4.51%** vs v05 control **1.89e-07** | `physics_3d.json` |
| … Chl1 / PIC / POC positivity | 0.0446→0.2515 · 0.1252→0.1775 · 0.0059→0.0805 | `physics_3d.json` |
| Deep ensemble, monthly 3-D | 0.43218 → **0.48371** (+0.0515) | `de3d_ensemble.json` |
| Deep ensemble, daily eqpac | 0.30387 → **0.44540** (+0.1415) | `de_eqpac_ensemble.json` |
| Ensemble calibration (spread/RMSE) | 0.2309 (3-D) · 0.2852 (eqpac) | same two |
| Metric-space collapse, daily eqpac | 0.29997 linear vs **0.03614** log (−88%) | `eqpac_ctl_{linear,log}.json` |
| Metric-space survival, monthly 3-D | **0.36492** log | `d3_ctl_log.json` |
| Δt-scaled rollout, 1 step | +0.4948 vs persistence, neg 0.0, mass 1.009 | `rollout_dtscale.json` |
| Flagship rollout, 1 step | +0.5827 vs persistence, +0.2402 vs climatology | `rollout_flagship_ctl.json` |

## NOT backed — cited provenance does not exist

Searched the worktree and the main checkout. **Six files referenced in the results matrix are absent:**

| missing artifact | what it backs |
|---|---|
| `diff_surf.json` | EDM diffusion surface, −0.020 |
| `diff_3d.json` | EDM diffusion 3-D, −0.026 |
| `diff_daily_eqpac.json` | diffusion calibration 0.375 |
| `matched_k1.json` / `matched_k8.json` | the entire k1-vs-k8 horizon table (§3) |
| `opt_physics.json` | architecturally-diverse ensemble calibration 0.240 |

**Every diffusion number in this project is currently unbacked.** So is the matched horizon table.

## Partially backed — real but not in `track2_runs/`

| finding | status |
|---|---|
| Log-space global fix (30.41%→0.00%, log-range 0.359→0.891, slope 0.23→0.81) | AICR job 204877; numbers live in STATUS.md, **no committed JSON** |
| Seasonal AR(1) −0.161 ± 0.015, 4 seeds | `2026-07-23_emulator_multiseed.md`; document-only |

## Consequence for the workshop decision

The **"diffusion adds no skill"** paper aimed at *AI for Stochastic Dynamics* rests on four missing
artifacts. It cannot be written honestly without re-running EDM diffusion and committing the results.

The **"metrics are blind to invalidating defects"** paper is fully backed on its two load-bearing
legs — `physics_3d.json` gives the 4.51%-vs-1.89e-07 contrast with a control column, and the
metric-space controls are committed and matched.

**Recommendation reverses to CCAI**, unless diffusion is re-run.
