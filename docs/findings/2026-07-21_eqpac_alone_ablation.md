# eqpac-alone ablation — per-cell win is not a missing-physics artifact (2026-07-21)

Rebuts red-team rebuttal_diff #4: *the per-cell win may be per-cell absorbing missing
nutrient/light physics in natl+SO (only eqpac is genuinely HNLC — the box has iron + constant light,
no N/P/Si co-limitation).* Pure re-grade of the n=50 per-seed per-AOI records
(`scripts/analysis/grade_single_aoi.py`), no new fit. Arms: `n50e2k_percell_trio` vs
`n50e2k_global_scalar` (both `verify_run` exit 0).

## Per-single-AOI Cal+ recovery (out of 50 seeds)

| AOI | alpfe pc / gl | scav_rat pc / gl | R_PICPOC pc / gl |
|---|---|---|---|
| **eqpac** (iron-limited year-round) | 43 / 50 | **7 / 0** | **46 / 0** |
| natlsubpolar | 49 / 50 | 20 / 0 | 50 / 0 |
| southernoceanpac | 49 / 50 | 49 / 0 | 40 / 0 |

pc = per-cell DINN, gl = global-scalar. Cal+ = rel-offset ≤ 0.40 vs Carroll.

## Verdict — confound rebutted, with an honest nuance

- **In eqpac alone, per-cell strictly beats global-scalar** on both non-alpfe trio params:
  scav_rat 7 vs 0, R_PICPOC **46 vs 0**. The per-cell advantage therefore is **not** an artifact of
  absorbing the physics the box omits outside eqpac — the Southern Ocean is a canonical HNLC region
  too, but the box carries iron + constant light only, so it misses North-Atlantic seasonal macronutrient
  drawdown and Southern-Ocean deep-mixing light limitation. R_PICPOC's eqpac win is decisive and clean.
- **alpfe** recovers in both arms in every AOI (method-independent / magnitude-pinned), as expected.
- **Nuance (report it):** scav_rat's per-cell recovery is **region-dependent** — weak in eqpac
  (7/50), moderate in natl (20/50), strong in SO (49/50). The strong SO/natl counts are where the
  manuscript's own l.392 confound is live (both are HNLC, but the box omits North-Atlantic seasonal
  macronutrient drawdown and Southern-Ocean deep-mixing light limitation, which the iron knob can
  absorb). So scav_rat is the weakest, most confounded leg (consistent with its 25/50 per-AOI ≥2-of-3
  headline), while R_PICPOC's per-cell necessity is clean across all three AOIs including eqpac.

**Bottom line:** the load-bearing per-cell claim survives the eqpac-alone decomposition (direction is
metric- and region-independent), but the manuscript should attribute scav_rat's *strength* to SO/natl
and note its eqpac recovery is weak — which sharpens, not weakens, the parameter-specific thesis.
