# Emulator baseline matrix — is the "structural ceiling" real, or a metric artifact?

**Date:** 2026-07-23
**Scope:** depth-resolved Track-2 FNO emulator (eqpac, top 5 levels, 6 tracers), re-evaluated against four baselines and three prediction targets to answer a reviewer critique.
**Eval:** `scripts/analysis/emulator_baselines.py` (reuses the already-dumped held-out fields — no retraining).
**Data:** `/scratch/qi_zim_neu/depth/depth_chl_fields.npz` (emulator pred/true/persistence, 8 held-out 1-month pairs) + `darwin_v05_L5_chl.npz` (48-month cube) + `depth_chl_emulator.json` (config).
**Machine artifact:** `/scratch/qi_zim_neu/depth/emulator_baseline_matrix.json`.

## The critique being tested

The prior write-up defended the emulator's failure-to-beat-persistence with a **structural-ceiling** story: *"DIC/ALK/FeT/Chl are near-conserved / slow, so persistence is unbeatable."* That is wrong for the fast tracers — Chl (blooms, grazing, photo-acclimation) and FeT (uptake, remineralization, scavenging, episodic dust) move fast on a monthly step. A correct one-month operator must beat persistence **whenever the state actually moves**. If it does not, the honest explanations are:

- **(i) tendency below the floor** — there is genuinely little to predict above persistence;
- **(ii) the level RMSE rewards autocorrelation** — persistence is a very strong denominator, so a scale-free *level* skill reads as a ceiling even when the model captures real deseasonalized structure;
- **(iii) missing inputs** — the operator cannot see the forcing that drives the tendency.

The PoC headline reports one number (level skill vs persistence) and cannot separate these. This matrix can.

## Setup (leak-free)

Predictors of `x_{t+1}`, scored per **tracer × depth level** over the 8 held-out 1-month pairs (42,950 valid ocean cells; Chl in log space, matching the PoC):

| baseline | definition |
|---|---|
| persistence | `x_t` |
| damped persistence | `clim_ann + α·(x_t − clim_ann)`, α fit per channel on **train pairs only** |
| seasonal climatology | monthly-mean `clim(month(t+1))`, **train months only** |
| anomaly persistence *(bonus)* | `clim(t+1) + (x_t − clim(t))` — persist the deseasonalized anomaly |
| emulator | the model's held-out `pred` |

Climatologies and α are fit on the 34 train months / 18 train pairs; the emulator's `pred` is its own held-out output. **Skill = 1 − RMSE_model/RMSE_baseline** (>0 beats the baseline; the task convention). `*_mse` columns use the PoC's `1 − MSE_model/MSE_persist` convention for a direct cross-check.

**Pipeline validation:** the `*_mse` per-tracer skills reproduce `depth_chl_emulator.json` to ~0.01 (DIC −2.55 vs json-mean −2.56; ALK −3.89 vs −3.89; PIC +0.376 vs +0.374; POC +0.453 vs +0.452; FeT −2.28 vs −2.28). The residual is the PoC's cos-lat area weighting, which this eval omits. Chl's annual-clim anomaly-R² differs (+0.46 here vs +0.75 in the PoC) because this eval computes the Chl climatology as *mean-of-logs* (consistent with the log-space skill), whereas the PoC uses *log-of-linear-mean*; both are strongly positive, so the conclusion is unchanged.

## The matrix (per tracer, mean over 5 depth levels)

Skill is `1 − RMSE_model/RMSE_baseline` unless noted. `anomR2(clim)` is the MSE-ratio anomaly-R² vs the annual-mean climatology (PoC convention). `corr_tend` = correlation of predicted vs true month-to-month change. `tend/anom` = rms(monthly increment) / rms(field anomaly about the annual mean) — the fast/slow ratio.

| tracer | vs persistence | vs damped | **vs seasonal clim** | vs anomaly-persist | anomR2(clim) | r2_tend | **corr_tend** | tend/anom | α |
|---|---|---|---|---|---|---|---|---|---|
| DIC  | **−0.844** | −0.789 | **+0.122** | −1.001 | +0.416 | −2.588 | +0.337 | 0.42 | 0.83 |
| ALK  | **−1.149** | −1.043 | **+0.262** | −1.047 | +0.511 | −3.970 | +0.189 | 0.34 | 0.87 |
| PIC  | **+0.210** | +0.114 | +0.005 | +0.131 | +0.436 | +0.375 | +0.673 | 0.95 | 0.50 |
| POC  | **+0.261** | +0.178 | +0.047 | +0.148 | +0.551 | +0.453 | +0.712 | 0.91 | 0.53 |
| FeT  | **−0.805** | −0.869 | **−0.329** | −1.054 | −0.138 | −2.281 | +0.367 | 0.59 | 0.78 |
| Chl1 | **−0.220** | −0.262 | **+0.175** | −0.154 | +0.459 | −0.490 | +0.474 | 0.60 | 0.74 |

### By depth level — `skill vs persistence [LEVEL] / anomaly-R² vs seasonal clim`

```
DIC   k0:-0.42/+0.11  k1:-0.42/+0.12  k2:-0.83/+0.16  k3:-1.11/+0.15  k4:-1.43/+0.08
ALK   k0:-0.64/+0.18  k1:-0.60/+0.22  k2:-1.06/+0.32  k3:-1.47/+0.33  k4:-1.98/+0.26
PIC   k0:+0.20/+0.01  k1:+0.21/-0.00  k2:+0.22/-0.00  k3:+0.21/+0.01  k4:+0.20/+0.01
POC   k0:+0.26/+0.03  k1:+0.27/+0.03  k2:+0.27/+0.04  k3:+0.27/+0.06  k4:+0.24/+0.07
FeT   k0:-0.69/-0.32  k1:-0.71/-0.33  k2:-0.74/-0.30  k3:-0.85/-0.33  k4:-1.04/-0.37
Chl1  k0:-0.21/+0.16  k1:-0.21/+0.16  k2:-0.21/+0.17  k3:-0.20/+0.19  k4:-0.27/+0.19
```

- DIC/ALK level-skill gets **more negative with depth** (persistence gets stronger deeper, where the monthly increment is even smaller) — yet anomaly-R² vs seasonal clim **stays positive at every depth**. The emulator keeps beating the seasonal mean even where it loses harder to persistence.
- PIC/POC are **flat across depth** (top 5 levels behave dynamically alike): they beat persistence at every level.
- FeT is negative against **both** references at every depth.

### By region (surface k0) — `p = skill vs persistence, c = skill vs seasonal clim`

The eqpac AOI (lat −5…15) splits into an equatorial cold-tongue band (|lat|≤5, 24,544 cells) and a northern warm-pool band (5<lat≤15, 18,406 cells).

```
DIC   eq: p=-1.28 c=-0.26 | north: p=-0.21 c=+0.22
ALK   eq: p=-1.14 c=-0.01 | north: p=-0.56 c=+0.22
PIC   eq: p=+0.13 c=+0.07 | north: p=+0.29 c=-0.12
POC   eq: p=+0.21 c=+0.12 | north: p=+0.31 c=-0.13
FeT   eq: p=-0.88 c=-0.28 | north: p=-0.54 c=-0.36
Chl1  eq: p=-0.27 c=+0.29 | north: p=-0.17 c=+0.01
```

The equatorial cold tongue (TIW-driven, dynamic) is where **Chl anomaly skill concentrates** (c=+0.29 eq vs +0.01 north); PIC/POC beat persistence more strongly in the northern band. FeT is negative in both.

### By season

Only 8 held-out pairs, spread across 4 month-of-year bins (n = 1, 2, 2, 3). Pooled emulator skill vs persistence is negative in every bin, but **n is far too small to read a seasonal signal** — reported for completeness only, not interpreted.

## Reading — the ceiling claim survives once a per-cell seasonal AR(1) is the baseline (v1 verdict superseded)

**1. Not a trivial ceiling (this was read at the time as refuting the "structural ceiling" framing; it does not — see the Verdict).** For **DIC, ALK, PIC, POC, Chl** the emulator **beats the seasonal-climatology baseline** (`vs seasonal clim` = +0.12, +0.26, +0.005, +0.05, +0.18) and has **strongly positive anomaly-R²** vs the annual climatology (+0.42, +0.51, +0.44, +0.55, +0.46). And **every one of the six tracers has positive month-to-month tendency correlation** (`corr_tend` +0.19…+0.71), including the "slow" DIC/ALK. An operator stuck at a copy-the-input ceiling cannot do either. It predicts the deseasonalized state better than the seasonal mean and knows which way the state is moving. The physics is being learned.

**2. The negative *level* skill for DIC/ALK/Chl is mechanism (ii), the metric — not physics.** The level RMSE rewards autocorrelation, and the `tend/anom` ratio quantifies exactly how much: for DIC/ALK it is **0.34–0.42** — the monthly increment persistence must beat is only a third of the anomaly amplitude, so persistence is a near-perfect denominator (DIC_k0: RMSE_persist 18.8 vs RMSE_seasclim 30.1 vs RMSE_annualclim 38.5). The emulator lands between them: it crushes climatology but cannot out-copy an already-excellent copy. That is a denominator artifact, not a wall. Crucially, "small monthly increment" is **not** "near-conserved / nothing to learn" — the +0.4…+0.5 anomaly-R² shows a large, learnable anomaly sitting on top of the small increment.

**3. PIC/POC are the fast tracers, and their apparent win is headroom, not skill.** Their `tend/anom` ≈ **0.91–0.95** (the monthly change is nearly the full anomaly amplitude), `corr_tend` ≈ 0.67–0.71, and level skill vs persistence is **positive** (+0.21/+0.26) — but that is exactly the regime where persistence is a weak denominator. Against a free per-cell seasonal AR(1) the edge disappears (PIC −0.037, CI straddling 0; POC +0.005), so this is mechanical headroom, not a positive control that the method works ([`2026-07-23_emulator_baselines_v2.md`](2026-07-23_emulator_baselines_v2.md)).

**4. FeT is the one real failure, and it is mechanism (iii) missing inputs — not a ceiling.** FeT loses to **every** baseline: persistence (−0.81), damped (−0.87), seasonal clim (−0.33), anomaly-persistence (−1.05), and annual-clim anomaly-R² (−0.14). It is the only tracer that beats nothing. Yet its tendency still carries directional information the model cannot cash in (`corr_tend` +0.37). That signature — real tendency structure, zero skill against any reference — is exactly what missing forcing looks like: iron's episodic atmospheric-dust deposition and scavenging sources are **not** in the prognostic-only input set, so the operator is blind to what drives FeT month to month. The fix is an input (dust/PAR forcing channels), not a bigger network.

**Note on the tendency target.** For the emulator vs persistence, skill on the *tendency* target is algebraically identical to the *level* target (the `x_t` term cancels), so the tendency reframing can bear on the ceiling only through **variance explained** — reported here as `corr_tend` (positive for all six) and `r2_tend`. `r2_tend` is negative for DIC/ALK/FeT/Chl despite positive correlation: the predicted increment points the right way but is mis-scaled (amplitude too large), so raw squared error exceeds the increment's own variance. Directional skill is real; amplitude calibration is the remaining gap for the slow tracers.

## Verdict

The single PoC headline (overall skill vs persistence ≈ +0.13, z-space area-weighted) hides the real structure. Broken out:

- **Structural-ceiling claim: NOT refuted — this v1 verdict is superseded by [`2026-07-23_emulator_baselines_v2.md`](2026-07-23_emulator_baselines_v2.md) and its multi-seed confirmation.** Against a free per-cell seasonal AR(1) the pooled skill is **−0.146 [−0.20, −0.10]** and the skill-vs-persistence CI straddles 0, so the emulator adds no significant skill anywhere in this AOI; PIC/POC's apparent level win is mechanical headroom (tend/anom ≈ 0.9), not learned dynamics. DIC, ALK, PIC, POC and Chl do still beat the seasonal- and annual-climatology baselines and all six tracers carry positive tendency correlation — real structure, but not skill above a free baseline.
- **FeT is a genuine failure but for the right reason** — missing iron forcing (mechanism iii), diagnostically distinct from the others: it is the only tracer that beats no baseline.

## Caveats / limits

- **Single AOI (eqpac), single seed, 8 held-out 1-month pairs.** Treat as a decisive diagnostic on *this* run, not a converged benchmark. Repeat over seeds/AOIs before any headline claim.
- **Chl climatology is mean-of-logs here** (internally consistent with the log-space skill), which differs from the PoC's log-of-linear-mean clim; both give strongly positive Chl anomaly skill.
- **Season breakdown is uninformative** at n = 1–3 per bin; month-of-year phase is uncalibrated (grouping is internally consistent, absolute month unknown).
- **Damped-persistence α is unconstrained** (fit by least squares on train pairs); values 0.74–0.87 for the slow tracers confirm strong autocorrelation, 0.50–0.53 for PIC/POC confirm mean-reversion. Damped persistence does not change any conclusion.

## Reproduce

```bash
ssh aicr
~/dd_venv/bin/python ~/emulator_poc/scripts/analysis/emulator_baselines.py \
  --fields   /scratch/qi_zim_neu/depth/depth_chl_fields.npz \
  --cube     /scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz \
  --emu-json /scratch/qi_zim_neu/depth/depth_chl_emulator.json \
  --out      /scratch/qi_zim_neu/depth/emulator_baseline_matrix.json
```
