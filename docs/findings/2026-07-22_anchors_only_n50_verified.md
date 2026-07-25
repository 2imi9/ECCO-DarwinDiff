# Anchors-only (PINN-off) n=50 — VERIFIED result + anchor-vs-pattern decomposition (2026-07-22)

Coordinated cluster batch `coord_anchors_pinnOFF` (Slurm 8536393, 50/50 seeds), gated through
`scripts/verify_run.py --expect-seeds 50` → **EXIT 0** (`mean_cal=2.84`, 15 excellents, `RPICPOC_STRADDLE` flag).
Config: GEOTRACES iron + Daniels calcite anchors ON, DINN/PINN spatial pattern-loss **OFF** (`pinn_w=0.0`),
`daniels_rpicpoc_w=1.0`, ungated, joint mode cell-weighted. This isolates what the **absolute anchors alone**
recover, with no spatial-pattern term.

## Recovery, n/50 (blessed metric = per-AOI ≥2-of-3, band_of Cal+ ≤40%)
| Param | per-AOI ≥2-of-3 | cell-weighted | median recovered | vs Carroll |
|---|---|---|---|---|
| **alpfe** | **50/50** | 50/50 | 0.998 | 1.07× (Excellent, tight) |
| **R_PICPOC** | **28/50** | 28/50 | 0.059 | 1.39× (Cal-grade) |
| **scav_rat** | **0/50** | 40/50 | 3.76e-7 | 0.62× (biased low) |
| diatomgraz | 11/50 | 1/50 | — | chance-ish |
| **joint trio** (alpfe & scav_rat & R_PICPOC, per-AOI) | **0/50** | — | — | scav_rat is the sole blocker |

## The decomposition (the manuscript-relevant result)
Anchors alone (no pattern loss) cleanly split the parameters by what drives their recovery:
- **alpfe — ANCHOR-driven.** 50/50 on the real GEOTRACES iron anchor alone, no pattern term needed. Strongest
  core-claim support: absolute iron in absolute units recovers the dust-solubility scalar by itself.
- **R_PICPOC — ANCHOR-driven.** 28/50 on the real Daniels calcite anchor alone (consistent with the anchor-off
  control collapsing it to 4/50). The calcite anchor carries it.
- **scav_rat — PATTERN-driven, NOT anchor-driven.** 0/50 per-AOI on anchors alone. It only "recovers"
  cell-weighted (40/50) via a **straddle**: every one of the 50 seeds lands scav_rat Cal+ in exactly 1 of 3 AOIs
  (always southernoceanpac; eqpac + natlsubpolar Loose/Drifted), so the cell-weighted mean sits in-band while no
  2-AOI majority ever forms. The cell-weighted 40/50 therefore **overstates** it; the honest number is 0/50.
  scav_rat's genuine recovery elsewhere (25/50 per-AOI at geo1, n=50) requires the DINN/per-cell spatial pattern loss —
  confirming scav_rat needs spatial structure the absolute anchors don't supply.

## Why this matters
1. **Honesty for the manuscript:** report scav_rat as **0/50 per-AOI (anchors-only)**, flagging the cell-weighted
   40/50 as a southernoceanpac straddle — the same pathology `verify_run` guards for R_PICPOC now applies to
   scav_rat here. Do not quote the cell-weighted number as recovery.
2. **It motivates the whole scav_rat program.** Absolute anchors recover alpfe + R_PICPOC but NOT scav_rat — the
   binding leg needs spatial/vertical structure. This is exactly why the vertical-column fit
   ([[2026-07-22_column_osse_result]]) and the joint multi-type iron inversion ([[data_acquisition_roadmap]]) are
   the right path: surface absolute anchors provably can't do it.
3. Consistent with the anchor-driven framing already in the red-team backlog ([[finding_manuscript_redteam_backlog]]).

Seed variance (cell-weighted, n=50): alpfe median 0.998 [0.938–1.000], std 0.020; scav_rat 3.76e-7 [3.30–4.21e-7],
std 2.1e-8 (clusters ~0.62× Carroll); R_PICPOC 0.059 [0.053–0.067], std 0.0027 (~1.39× Carroll).
