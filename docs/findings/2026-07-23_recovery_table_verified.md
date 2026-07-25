# Verified per-AOI parameter-recovery table (2026-07-23)

Read-only grading of already-completed recovery runs on the AICR cluster with the
validated tool `scripts/grade_recovery.py`. No training was launched and no shared
files were modified. Every row below passed the `verify_run.py` anti-hallucination
gate (exit 0) before any count was read.

## Framing (per CLAUDE.md)

- **Observable denominator is 4**: `{alpfe, scav_rat, diatomgraz, R_PICPOC}`.
- The growth pair `{Smallgrow, Biggrow}` is **unobservable by construction** — excluded,
  not failed — so it is not scored here.
- The headline metric is the **honest per-AOI count**: for each of the 10 seeds, a
  parameter counts only if it lands Cal+ (≤40% off Carroll's published value) in
  **≥2 of the 3 AOIs** (eqpac / natlsubpolar / southernoceanpac). Reported as `x/10`.
- The **joint cell-weighted (cw)** count is shown only where it **overstates** the honest
  per-AOI count; those cases are flagged **STRADDLE** (the cell-weighted mean straddles
  Carroll while no single AOI actually recovers). Joint-cw is not a substitute for the
  honest number.

**Grader invocation:** `grade_recovery.py --expect-seeds 10 --params alpfe,scav_rat,diatomgraz,R_PICPOC`
(defaults `--cal-max 0.40`, `--n-aoi-min 2`).
**Carroll targets:** alpfe 0.9283 · scav_rat 6.025e-07 · diatomgraz 0.83 · R_PICPOC 0.04245.
**AOIs:** eqpac, natlsubpolar, southernoceanpac (joint, 3-AOI).

## Config legend

All runs are the v3.0 joint 3-AOI DINN recovery. Levers that vary across the runs:
MLD input channel (on/off), any extra env channels, the Daniels R_PICPOC anchor weight
(`dan_w`), and the dust-solubility anchor weight (`dust_w`).

| run | MLD chan | extra chan | dan_w | dust_w | source dir |
|---|---|---|---|---|---|
| arm0_sst† | no | none (empty) | 1 | 0 | `covar/n10/arm0_sst` |
| arm1_mld | **yes** | none | 1 | 0 | `covar/n10/arm1_mld` |
| arm2_wind | no | wind | 1 | 0 | `covar/n10/arm2_wind` |
| arm3_mld_wind | **yes** | wind | 1 | 0 | `covar/n10/arm3_mld_wind` |
| arm4_full | **yes** | wind,SSS,pCO2atm,CO2flux | 1 | 0 | `covar/n10/arm4_full` |
| ctrl_aoiid | no | AOI-ID channel | 1 | 0 | `covar/n10/ctrl_aoiid` |
| arm0_sss | no | SSS | 1 | 0 | `covar2/n10/arm0_sss` |
| arm1_pco2 | no | pCO2atm | 1 | 0 | `covar2/n10/arm1_pco2` |
| arm2_co2flux | no | CO2flux | 1 | 0 | `covar2/n10/arm2_co2flux` |
| arm0_mld_dan3 | **yes** | none | **3** | 0 | `covar_protect/n10/arm0_mld_dan3` |
| **arm1_mld_dan8** | **yes** | none | **8** | 0 | `covar_protect/n10/arm1_mld_dan8` |
| arm2_mldwind_dan3 | **yes** | wind | **3** | 0 | `covar_protect/n10/arm2_mldwind_dan3` |
| arm3_mldwind_dan8 | **yes** | wind | **8** | 0 | `covar_protect/n10/arm3_mldwind_dan8` |
| A_dustW0 | no | none | 1 | 0 | `dust_ab/n10/A_dustW0` |
| B_dustW5 | no | none | 1 | **5** | `dust_ab/n10/B_dustW5` |

† `arm0_sst` was intended as an SST-channel arm but its recorded `env_extra_channels`
is empty, so it ran as the plain base config. Its per-seed outputs are byte-identical to
`A_dustW0` (the dust-anchor-off base). Treat the two as the same base reference.

## Results — honest per-AOI counts (all gate-VERIFIED, n=10)

Each observable cell is the **per-AOI honest** count out of 10 seeds. The `scav_rat`
column also carries its joint-cw count and straddle inflation `(cw N, +Δ)` because
`scav_rat` straddles in every arm. Extra straddles on other params are listed in the
last column.

| run | gate | alpfe | scav_rat (honest / cw) | diatomgraz | R_PICPOC | obs≥7/10 | iron-pair ρ | other straddles |
|---|---|---|---|---|---|---|---|---|
| arm0_sst† | VERIFIED | 10/10 | 0/10 (cw 8, +8) | 3/10 | 6/10 | 1/4 | −0.13 | R_PICPOC cw7 +1; RPICPOC gate |
| arm1_mld | VERIFIED | 10/10 | 0/10 (cw 8, +8) | **10/10** | 5/10 | 2/4 | +0.52 | — |
| arm2_wind | VERIFIED | 10/10 | 0/10 (cw 9, +9) | **10/10** | 0/10 | 2/4 | +0.06 | — |
| arm3_mld_wind | VERIFIED | 10/10 | 2/10 (cw 10, +8) | **10/10** | 0/10 | 2/4 | +0.45 | — |
| arm4_full | VERIFIED | 10/10 | 0/10 (cw 9, +9) | 7/10 | 0/10 | 2/4 | +0.47 | — |
| ctrl_aoiid | VERIFIED | 10/10 | 0/10 (cw 9, +9) | 6/10 | 0/10 | 1/4 | −0.37 | — |
| arm0_sss | VERIFIED | 10/10 | 1/10 (cw 9, +8) | 7/10 | 0/10 | 2/4 | +0.79‡ | diatomgraz cw9 +2 |
| arm1_pco2 | VERIFIED | 10/10 | 0/10 (cw 10, +10) | 8/10 | 3/10 | 2/4 | +0.28 | RPICPOC gate |
| arm2_co2flux | VERIFIED | 10/10 | 1/10 (cw 10, +9) | **10/10** | 0/10 | 2/4 | +0.36 | R_PICPOC cw2 +2; RPICPOC gate |
| arm0_mld_dan3 | VERIFIED | 10/10 | 0/10 (cw 10, +10) | **10/10** | 9/10 | 3/4 | +0.22 | R_PICPOC cw10 +1; RPICPOC gate |
| **arm1_mld_dan8** | VERIFIED | **10/10** | 1/10 (cw 10, +9) | **10/10** | **10/10** | **3/4** | +0.02 | — |
| arm2_mldwind_dan3 | VERIFIED | 10/10 | 0/10 (cw 8, +8) | **10/10** | 0/10 | 2/4 | +0.45 | — |
| arm3_mldwind_dan8 | VERIFIED | 10/10 | 0/10 (cw 7, +7) | **10/10** | 0/10 | 2/4 | +0.13 | — |
| A_dustW0† | VERIFIED | 10/10 | 0/10 (cw 8, +8) | 3/10 | 6/10 | 1/4 | −0.13 | R_PICPOC cw7 +1; RPICPOC gate |
| B_dustW5 | VERIFIED | 10/10 | 0/10 (cw 7, +7) | 3/10 | 8/10 | 2/4 | +0.54 | RPICPOC gate |

`obs≥7/10` = number of the 4 observables recovered per-AOI in a strong majority of seeds
(≥7/10). alpfe is 10/10 everywhere. `scav_rat` is **never** recovered honestly (0–2/10)
even though its cell-weighted count is 7–10/10 in every arm — the single most important
straddle in the whole table. ‡ `arm0_sss` iron-pair ρ=+0.79 flags the alpfe↔scav_rat
ridge as INTACT (scav_rat unconstrained); other arms partially break it.

## STRADDLE callouts (explicit)

- **`scav_rat` straddles in all 15 runs.** Joint cell-weighted reads 7/10 to 10/10, honest
  per-AOI is 0–2/10. Any headline that quotes the joint `scav_rat` number overstates
  recovery by +7 to +10 seeds. `scav_rat` is not identifiable per-AOI in any config here.
- **`R_PICPOC` straddles** in the low-Daniels-weight base arms (arm0_sst/A_dustW0 +1,
  arm2_co2flux +2) and marginally in arm0_mld_dan3 (+1). It stops straddling only when the
  Daniels anchor is heavy: **arm1_mld_dan8 recovers R_PICPOC 10/10 honest with no straddle.**
- **`diatomgraz` straddles** once (arm0_sss, +2).

## Incomplete / not gradeable (recorded honestly)

| run | status |
|---|---|
| `covar2/n10/arm3_mld_dan2` | 0/10 seeds — job cancelled at epoch ~250/2000 (SIGNAL Terminated) |
| `covar2/n10/arm4_wind_dan2` | 0/10 seeds — job cancelled at epoch ~250/2000 (SIGNAL Terminated) |
| `covar2/n10/arm5_full_dan2` | 0/10 seeds — job cancelled at epoch ~250/2000 (SIGNAL Terminated) |

`dust_ab/n5/{A_dustW0, B_dustW5}` also exist as **n=5 superseded duplicates** of the n=10
dust arms (both gate-VERIFIED at n=5, same qualitative result: alpfe 5/5, scav_rat 0/5,
R_PICPOC 3/5 → 5/5 with dust anchor). They are omitted from the main table in favor of the
n=10 versions.

## Honest reading — best defensible config

**`arm1_mld_dan8`** (MLD input channel + Daniels R_PICPOC anchor up-weighted to 8, dust
anchor off) is the single best-defensible configuration: it holds
**{alpfe, diatomgraz, R_PICPOC} at 10/10/10 per-AOI honest**, cleanly, with no straddle on
any of the three. That is a **3-of-4 observable frontier**, not a 4/4 — `scav_rat` remains
the one observable that does not recover per-AOI (1/10 honest; its 10/10 joint count is a
+9 straddle and should never be reported as recovery). `arm0_mld_dan3` is the only near-rival
(3/4, but R_PICPOC 9/10 with a +1 straddle and an RPICPOC gate flag), so the heavier
Daniels weight is what cleanly closes R_PICPOC. The lever story is consistent across the
table: the **MLD channel** is what lifts diatomgraz (3/10 → 10/10), a **heavy Daniels weight**
is what lifts R_PICPOC (5/10 → 10/10), and adding **wind on top of MLD wrecks R_PICPOC back
to 0/10** (arm2/arm3_mldwind); the **dust anchor** (B_dustW5) nudges R_PICPOC 6→8 but cannot
substitute for the MLD channel on diatomgraz.
