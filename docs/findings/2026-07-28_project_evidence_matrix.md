# Project evidence matrix — every headline claim vs its artifact

**Date:** 2026-07-28 · **Method:** claims read from STATUS.md / results matrix, then each checked
against a committed artifact or a re-run. Not a summary of prose — a provenance audit.

Legend — **A** artifact committed · **R** re-derived this week · **D** document-only · **✗** artifact
cited but absent.

## Track 1 — parameter learner

| # | Claim | Value | Evidence | Conf |
|---|---|---|---|---|
| 1 | Flagship per-AOI recovery | alpfe **49/50** · scav_rat **25/50** · diatomgraz **3/50** · R_PICPOC **50/50** | **R** — `grade_recovery.py` re-run 2026-07-26 on 50 seeds pulled from Explorer, gate exit 0 | **High** |
| 2 | Per-AOI legs | eqpac 7 / natl 20 / sopac 49 | **R** — same run; corrected STATUS.md's 8/19 | **High** |
| 3 | Trio vs global-scalar | **25/50** vs **0/50** | **R** | **High** |
| 4 | Calcite anchor is load-bearing | R_PICPOC 50/50 → **6/50** anchor-off (epoch-matched) | **A** `n50e2k_anchor_off` on cluster | **High** |
| 5 | 4000-epoch gain | scav_rat 25 → **41/50**, natl 20→40 | **D** — `ep4k_n50` cited; not re-graded | Medium |
| 6 | Iron-block conditioning | κ(F) **2930** surface-only → **~7** with a rate observable | **A** `2026-07-23_observation_design.json` | **High** |
| 7 | Duplicate survey is useless | variance ÷2.00, κ **unchanged** | **A** same | **High** |
| 8 | Per-AOI Fisher geometry | SO κ(F) 2.2 vs eqpac/natl 35–51 | **A** `geom_probe/*.json`, `saddle_fix/fim_*.json` | **High** |
| 9 | Iron residence times | per-AOI τ | **A** `iron_residence/tau_*.json` | Medium |
| 10 | 3-of-4 frontier / basin mutex | no config holds all four | **D** + run history | Medium |
| 11 | GP15 cannot reach the flagship basins | eqpac 0 · natl 0 · sopac 0 · npac 50 · npsg 25 | **R** — `tests/test_cochran_gp15_po_pb_loader.py`, 13 tests | **High** |
| 12 | κ(J) = √κ(F) correction | κ(J) ≈ 54, not 2930 | **R** — verified at source, 2026-07-27 | **High** |

## Track 2 — forward emulator

| # | Claim | Value | Evidence | Conf |
|---|---|---|---|---|
| 13 | Skill is blind to physics | emulator FeT neg **4.51%** vs v05 control **1.89e-07** | **A** `physics_3d.json`, with control column | **High** |
| 14 | Ensembling is the lever | +0.1415 (eqpac) · +0.0515 (3-D) | **A** `de_eqpac_ensemble.json`, `de3d_ensemble.json` | **High** |
| 15 | Metric space decides the result | 0.29997 linear vs **0.03614** log | **A** `eqpac_ctl_{linear,log}.json`, matched seed+cube | **High** |
| 16 | Δt-scaled residual recovers monthly | +0.4948 @ 1 step | **A** `rollout_dtscale.json`, `dt_2x2b.json` | **High** |
| 17 | Log-space fix | 30.41% → **0.00%** non-physical; range 0.359 → 0.891 | **D** — AICR 204877; **no committed JSON** | Medium |
| 18 | Seasonal AR(1) deflation | **−0.161 ± 0.015**, 4 seeds, CI below zero | **D** `2026-07-23_emulator_multiseed.md` | Medium |
| 19 | **Diffusion adds no skill** | −0.020 / −0.026 | **✗** `diff_surf.json`, `diff_3d.json` **ABSENT** | **Not assertable** |
| 20 | **Diffusion improves calibration** | 0.375 | **✗** `diff_daily_eqpac.json` **ABSENT** | **Not assertable** |
| 21 | **k1-vs-k8 horizon table** | full §3 table | **✗** `matched_k1/k8.json` **ABSENT** | **Not assertable** |
| 22 | Diverse-ensemble calibration | 0.240 | **✗** `opt_physics.json` **ABSENT** | **Not assertable** |
| 23 | Calendar bug inflated clim-skill | +0.37 to +0.78 | **A** `cal_ab.json` | **High** |

## Observational validation

| # | Claim | Value | Evidence | Conf |
|---|---|---|---|---|
| 24 | v05 Chl vs MODIS regime split | natl −0.697 dex · eqpac −0.076 (inside 0.130 noise floor) | **A** `chl_val/*.json` (6) | **High** |
| 25 | eqpac skill is ENSO, n_eff 34 not 192 | r +0.524 active vs −0.052 neutral | **A** `chl_val/eqpac_enso_diagnostics.json` | Medium-high |
| 26 | ~2-month phase discrepancy | v05 leads at −2, MODIS +1 | **A** `chl_val/eqpac_lag_resolvability.json` | Medium |
| 27 | v05 pCO2 vs GLODAP unbiased | +0.3 µatm | **D** | Medium |

## Infrastructure

| # | Claim | Evidence | Conf |
|---|---|---|---|
| 28 | `torch.load` hardened, 26 sites | **R** — merged PR #203, AST audit 27/27, 549 tests | **High** |
| 29 | Canonical-number guards | **R** — 13 tests, demonstrated to fire | **High** |
| 30 | Earth2Studio `PrognosticModel` | **A** `src/darwindiff/e2s/` + tests | Medium-high |
| 31 | Transport conservation | **A** `ude_stress_2026-07-21/*.json` (14) | Medium |

## What this says

**Strongest evidence base:** Track-1 recovery and identifiability. Items 1–4, 6–8 and 11–12 are
either artifact-backed or re-derived this week. That is the flagship, and it is well-founded.

**Weakest:** every diffusion claim (19–22). Four cited artifacts are absent, so the whole
generative-model line is currently unassertable.

**Cheapest repairs, in order:**
1. Dump the log-space fix (17) to JSON — numbers exist, artifact does not. Near-free, hardens CCAI.
2. Commit the multiseed AR(1) result (18) as JSON.
3. Re-grade `ep4k_n50` (5) — the 4000-epoch claim appears in the AGU abstract and is document-only.
4. Re-run EDM diffusion (19–22) if the stochastic-dynamics venue is ever revisited.

**For the CCAI paper:** items 13, 14, 15 are all High and artifact-backed with controls. That is the
paper. Item 17 is its second leg and should be item 1 on the repair list.
