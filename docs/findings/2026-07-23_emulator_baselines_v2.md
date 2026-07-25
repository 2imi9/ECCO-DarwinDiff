# Emulator baseline evaluation v2: AR(1), tendency-normalization, block-bootstrap CIs

Date: 2026-07-23
Script: `scripts/analysis/emulator_baselines_v2.py`
Output JSON: `/scratch/qi_zim_neu/depth/emulator_baseline_matrix_v2.json` (AICR)
Inputs (reused, no retraining): `depth_chl_fields.npz` + `darwin_v05_L5_chl.npz` + `depth_chl_emulator.json`
Config: AOI eqpac, 6 tracers x 5 levels (30 ch), 34 train months / 8 val pairs, Chl1 log-space, residual=False.

## Why v2 exists

v1 (`emulator_baselines.py`) established that the depth emulator loses to persistence on the
near-conserved tracers (DIC/ALK/FeT/Chl) but "beats" it on PIC/POC. A domain expert raised three
objections v1 could not answer:

1. **Persistence is a weak straw man.** Add stronger free baselines, in particular a per-cell
   **AR(1)** (the optimal lag-1 linear predictor) and a per-cell linear trend.
2. **PIC/POC's win may be mechanical headroom.** PIC/POC have large monthly tendency variance
   relative to total field variability, so persistence RMSE (the ratio's denominator) is large and
   the skill ratio flatters the emulator. Test with **tendency-normalized error**
   (RMSE_model / rms(true tendency)) and by scoring against the **best** free baseline, not the weakest.
3. **No uncertainty.** Attach **block-bootstrap CIs** (resample spatial blocks, not cells, so the CI
   respects spatial autocorrelation) to every headline number.

## What v2 computes

Predictors of x(t+1), all leak-free (climatologies, damping alpha, AR(1) phi, and trend coefficients
fit on train months only, evaluated on held-out val pairs):

- persistence `P = x_t`; damped `clim_ann + alpha*(x_t-clim_ann)` (per-channel alpha, v1);
  seasonal clim `S`; annual clim `CA`; anomaly persistence `S + (x_t - S_src)` (v1)
- **NEW** AR(1) per cell `clim_ann + phi_cell*(x_t-clim_ann)` (phi fit per cell, clipped to (-1,1))
- **NEW** AR(1) per cell seasonal `S + phi_s*(x_t - S_src)` (per-cell damped anomaly persistence)
- **NEW** linear trend per cell `a_cell + b_cell*t_target`
- emulator `E = pred`

Skill = `1 - RMSE_model/RMSE_base` (task convention). Residuals are z-normalized per channel by the
train std before pooling a tracer's 5 levels, so levels contribute evenly. CIs are 95% spatial
block-bootstrap: the H x W grid is tiled into 120 blocks (15 rows x 36 cols), blocks are resampled
with replacement B=1000 times, and paired RMSE ratios are recomputed each draw. Per-channel skills
(z-invariant) reproduce v1 and `emulator_poc.json` (PIC +0.210, POC +0.261 to 3 dp; PIC_k0
MSE-ratio 0.3645 -> `1-sqrt(1-0.3645)=0.203` matches the RMSE-ratio 0.210).

## Headline result

| tracer | skill vs persistence | skill vs AR(1) percell | skill vs BEST free baseline | NE(emu) | tend/anom |
|---|---|---|---|---|---|
| DIC  | -0.701 [-0.87, -0.55] | -0.638 [-0.79, -0.50] | -0.989 [-1.14, -0.85] (anomPers) | 1.70 | 0.44 |
| ALK  | -0.942 [-1.14, -0.79] | -0.849 [-1.02, -0.71] | -1.044 [-1.24, -0.86] (anomPers) | 1.94 | 0.37 |
| **PIC**  | **+0.210 [+0.11, +0.29]** | **+0.102 [+0.02, +0.16]** | **-0.037 [-0.097, +0.016] (AR1-seas)** | 0.79 | 0.94 |
| **POC**  | **+0.261 [+0.20, +0.31]** | **+0.169 [+0.11, +0.22]** | **+0.005 [-0.056, +0.065] (AR1-seas)** | 0.74 | 0.90 |
| FeT  | -0.799 [-0.99, -0.65] | -0.859 [-1.05, -0.71] | -1.051 [-1.20, -0.93] (anomPers) | 1.80 | 0.59 |
| Chl1 | -0.218 [-0.29, -0.15] | -0.222 [-0.28, -0.16] | -0.260 [-0.32, -0.20] (damped) | 1.22 | 0.60 |

`NE(emu)` = tendency-normalized error `RMSE_emu / rms(true tendency)`; < 1 beats persistence.
`tend/anom` = rms(monthly tendency) / rms(field anomaly), unit-free, work space.

**Overall pooled (30 ch):** skill vs persistence **+0.068 [-0.033, +0.143]** (CI straddles 0, so the
`emulator_poc.json` headline "beats persistence" is **not significant** under the RMSE-ratio +
z-pooling + block-bootstrap treatment); skill vs best free baseline **-0.146 [-0.201, -0.099]**
(significantly worse than a free per-cell seasonal AR(1)); NE(emu) 0.932 [0.856, 1.031] straddles 1.

## The mechanical-headroom check (tendency-normalized error of the FREE baselines)

Values < 1 mean that cheap, free baseline *also* beats persistence, i.e. persistence is weak there.

| tracer | persist | damped | seasClim | annClim | anomPer | AR1 | AR1-seas | trend |
|---|---|---|---|---|---|---|---|---|
| DIC  | 1.00 | 1.01 | 1.94 | 2.28 | 0.86 | 1.04 | 1.01 | 2.12 |
| ALK  | 1.00 | 1.04 | 2.63 | 2.82 | 0.95 | 1.05 | 1.13 | 2.34 |
| **PIC** | 1.00 | 0.89 | **0.79** | 1.05 | 0.91 | 0.88 | **0.76** | 1.12 |
| **POC** | 1.00 | 0.90 | **0.78** | 1.10 | 0.87 | 0.89 | **0.74** | 1.15 |
| FeT  | 1.00 | 0.96 | 1.35 | 1.69 | 0.88 | 0.97 | 0.96 | 1.60 |
| Chl1 | 1.00 | 0.97 | 1.48 | 1.66 | 1.06 | 1.00 | 1.09 | 1.63 |

For PIC/POC nearly every free baseline has NE < 1: seasonal climatology (0.79/0.78) and per-cell
seasonal AR(1) (0.76/0.74) both beat persistence by *more* than the emulator (0.79/0.74). PIC/POC also
have tend/anom ~ 0.9, meaning the monthly tendency is nearly as large as the whole field's anomaly.
This is the mechanical headroom: PIC/POC swing so much month to month that persistence is a trivially
weak denominator, and any cheap seasonal/autoregressive predictor exploits the same headroom.

## Breakdowns (all with block-bootstrap CIs)

**By biome.** The apparent PIC/POC advantage is largest in the northern biome, but that is exactly
where a free seasonal climatology beats the emulator:

- PIC northern (n=18406): vs persistence +0.315, but **vs best free -0.077 [-0.163, -0.002]**
  (seasonal_clim wins, CI clear of 0).
- POC northern (n=18406): vs persistence +0.342, but vs best free -0.071 [-0.158, +0.015] (straddles 0).
- PIC/POC equatorial: vs best free -0.022 / +0.048 (both straddle 0).
- DIC/ALK/FeT/Chl1: strongly negative vs both persistence and best free in both biomes.

**By init month** (pooled across tracers; 1-3 val pairs per bin, so spatial CI only, time-sampling is
thin). Skill vs best free baseline is negative in every bin: bin4 -0.280, bin5 -0.349, bin6 -0.206,
bin8 -0.124, bin10 +0.063 (only bin10 straddles 0). No initialization month shows genuine skill.

**By depth level.** PIC/POC skill vs best free is ~0.00 to -0.05 uniformly across all 5 levels (no
level adds skill). DIC/ALK are strongly negative and worsen with depth (ALK k4 -1.98).

## Verdict

- **Does the emulator survive AR(1) + tendency-normalization + bootstrapped CIs?** Overall, **no.**
  The pooled skill vs persistence is not significant (CI straddles 0), and the emulator is
  significantly *worse* than a free per-cell seasonal AR(1) (-0.146 [-0.20, -0.10]). Only PIC and POC
  keep a CI clear of zero against persistence and against the annual AR(1).
- **Is PIC/POC's win genuine or mechanical?** **Mechanical.** Against the strongest free baseline
  (per-cell seasonal AR(1)), PIC's edge vanishes (-0.037, CI straddles 0) and POC merely ties
  (+0.005, CI straddles 0). Their high skill-vs-persistence is explained by tend/anom ~ 0.9
  (persistence is a weak straw man) and by free seasonal/AR(1) baselines capturing the same headroom.
  In the northern biome the emulator is actively beaten by a seasonal climatology.

**Honest framing for the manuscript:** the depth emulator does not add skill beyond a per-cell
seasonal AR(1) anywhere in this AOI. The PIC/POC "beats persistence" claim from v1 should be retired
or heavily qualified: it is mechanical headroom from large monthly tendency variance, not learned
dynamics. This strengthens the structural-ceiling conclusion rather than weakening it.

## Caveats

- The "best free baseline" is selected on the same val sample it is scored on (a mild optimism for the
  baseline). Because AR(1)-seasonal is consistently best across PIC/POC/overall, this is a stable
  choice, not noise; the direction is conservative toward the emulator (it makes the emulator's bar
  higher, which is what an adversarial test wants).
- Block bootstrap resamples space, not time. With only 8 val pairs the time dimension is not
  bootstrapped; init-month CIs therefore reflect spatial sampling only and should be read as lower
  bounds on total uncertainty.
- Absolute season phase is uncalibrated (inherited from v1); month-of-year *grouping* is internally
  consistent (same true month -> same bin), which is all the breakdowns require.
- Skill is in each tracer's working space (log for Chl1, linear otherwise), z-normalized per channel
  before pooling. Per-channel skills (z-invariant) reproduce v1 and `emulator_poc.json`.
