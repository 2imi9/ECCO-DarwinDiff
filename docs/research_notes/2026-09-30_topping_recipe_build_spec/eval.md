# Grading: nulls, metrics, pre-registration, speed benchmark, verify gate

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

This is a grading design for the Earth-2 replication (CorrDiff super-resolution, a StormCast monthly/daily time-stepper, and the Stage-0 physics-to-BGC diagnostic that is already registered). All three go through one scorer in the separate `track2/` uv project. A gate that needs only numpy (`scripts/verify_e2_run.py`) lives in the main repo. The design follows the repo's rules: every null is computed inside the same job, the one deterministic skill claim is made for the regression stage, and the diffusion stage is licensed only by probabilistic metrics measured against a dressed-regression null and a deep-ensemble null.

The pass rule mirrors the §5 pre-test. On at least 2 of {DIC, ALK, FeT, PIC}, the model must beat the best free per-cell null with a space×time block-bootstrap CI lower bound above 0. It must also hold under the G12, G6, G24 and REV12 splits and replicate in a separate sbatch run with fresh seeds, submitted only after the discovery verdict is committed.

StormCast is graded by a useful horizon H*. The pre-registered targets are H* ≥ 3 months for the monthly model and H* ≥ 30 days for the daily model. The nulls are persistence, climatology, trend-climatology, seasonal AR(1) k-step, and an information-matched ARX(1) that gets the same true physics background. Physics checks use `physics_verify.physics_report` checks A, B and C with a v05 truth control column. Check D (stoichiometry) is excluded. DIC/ALK drift is measured with a new inventory-drift check, weighted by cell area and layer thickness (`rollout_verify`'s mass_ratio is an unweighted sum over all channels, not a budget).

Speed is benchmarked per simulated year. It is printed as a speedup only when the ECCO-Darwin reference cost is known and H* passes. The reference cost is not in the repo, so it is a collaborator ask.

New facts measured read-only on the local mirror today:
- Every monthly file stamp is iter×1200 s from 1992-01-01 and lands at 00:00 on the 1st of a month. So the month label must be the stamp minus 1 s: `rollout_verify.month_of_year` labels every month one month late, though its binning is consistent.
- The `.meta` `timeInterval` start is always floor(end/2,635,200 s)×2,635,200 s. It is an artifact of the nominal 30.5-day output frequency and cannot certify averaging windows.
- The mirror has mismatched `.data`/`.meta` pairs (DIC: 45 metas with no data, 5 data files with no meta).
- Forward-split month counts per target with physics (train/val/test) are about 145/28-32/86-95. All six tracers plus physics give only 81/15/50. Consecutive one-month pairs: 51-67 for all six, 224 for DIC alone.

## Decisions

- **Which stage carries the deterministic skill claim** → The regression-stage 5-seed ensemble mean (N6). Report the CorrDiff/StormCast ensemble mean beside it with a no-harm check (skill against N6 ≥ −0.02).
  - why: It is settled that a diffusion ensemble mean does not beat its own regression stage (CorrDiff Table 1; the 2026-09-30 finding, lines 60-80). Grading the diffusion mean for skill would count credit that belongs to the regression stage.
- **Probabilistic null for licensing the diffusion stage** → Dressed regression (N6 plus Gaussian noise with per-cell σ fit on val) and a 5-seed deep ensemble, both scored with fair CRPS. Do not compare the ensemble CRPS against the UNet MAE.
  - why: Any ensemble with nonzero spread beats the MAE of a point forecast, and CorrDiff Table 1 makes exactly that comparison. Deep ensembling is this repo's settled lever. Fair CRPS corrects for the different member counts (5 vs 32).
- **Strongest free null for CorrDiff super-resolution** → Add the delta (change-factor) method, U0(x_c) plus the zero-block-mean sub-grid pattern of the train climatology, and trend-climatology, alongside the requested conservative/bilinear, climatology and per-cell ridge nulls. The +0.10 margin is measured against trend-climatology.
  - why: The coarse input already carries each month's anomaly, so beating plain climatology is trivial. The anthropogenic DIC trend across the 2009 gap biases a 1992-2005 climatology low.
- **Calendar** → Month label = 1992-01-01 + iter×1200 s − 1 s, and assert the stamp is at 00:00 on the 1st. Never use _season_bin, rollout_verify.month_of_year labels or the .meta timeInterval.
  - why: Verified on the mirror: all 318/318/321 stamps are 1st-of-month ends of the averaging window. rollout_verify labels every month one month late. The timeInterval start is floor(end/30.5 d)×30.5 d, a metadata artifact.
- **Held-out design** → G12 (primary): train 1992-01..2005-12, val 2006-2008, gap 2009, test 2010-01..2018-11. Plus G6, G24 and REV12. All fits on train, all selection on val, at most 3 configs scored on the G12 test.
  - why: This matches the already-registered §5 pre-test. It separates selection from test and limits reuse of the test set. diffusion_emulator.zscore currently normalises over val too.
- **StormCast background** → Physics at t+1 from v05 truth (offline-BGC mode), with an information-matched per-cell ARX(1) null. A coarse copy of the target at t+1 is forbidden unless a null gets it too; the gate exits INTEGRITY otherwise.
  - why: Conditioning on a box average of the future truth would count super-resolution as forecasting. Every input the model sees must also be available to at least one null.
- **What counts as replication** → A separate sbatch run with fresh seeds, submitted only after the discovery verdict is committed. It recomputes its nulls in-job, and they must match the discovery nulls bitwise. The pass rule is re-applied to the replication alone.
  - why: CLAUDE.md requires a separate submission and comparisons within a job. Bitwise-equal nulls also test the data and harness for determinism.
- **Where the scorer and gate live** → The scorer goes in track2/ (its own pyproject and lock, path dependency on darwindiff, pinned physicsnemo 536553ac and earth2studio 2067756d). The gate goes in scripts/verify_e2_run.py in the main repo, using numpy and json only, with tests in tests/.
  - why: The netCDF4 conflict (earth2studio needs <1.7.3; uv.lock pins 1.7.4). The gate must run in the main CI and in the research-map workflow without GPU dependencies.
- **Recompute from raw** → Store per-(field, space, lead, predictor, spatial block, time block) sums of SSE, SAE, weights, fair CRPS and ensemble variance in a sha256-pinned sums.npz. The gate recomputes every number and CI from it.
  - why: This mirrors verify_run.py's 'never trust a stored number'. Full ensembles are too large to keep (roughly 48 GB for CorrDiff at 32 members).
- **Spread-skill and spectra definitions** → SSR = sqrt((N+1)/N)·sqrt(mean var, ddof=1)/RMSE(ens mean), also recording earth2studio's uncorrected ratio. Compute PSDs on fixed fully-ocean 48×48 tiles, not on the full field.
  - why: deep_ensemble_eval uses mean(std)/RMSE, which is biased low and not comparable. The existing radial_spectrum and the physicsnemo example compute full-domain FFTs that include land.
- **Physics checks** → Use physics_verify.physics_report checks A, B and C with a truth control column. Drop check D. Add new area×thickness-weighted inventory drift for DIC/ALK (0-100 m) and a proposed air-sea flux-consistency check for the daily model.
  - why: The finding says check D is badly designed. rollout_verify's mass_ratio is an unweighted sum over all channels. The daily archive has no DIC/ALK.
- **Log floors** → Use a per-tracer floor of 1e-3 × the train median, score log space only where truth exceeds the floor, and have the gate flag an excluded fraction above 1%.
  - why: The 1e-4 default in rollout_verify, physics_verify and deep_ensemble_eval is comparable to surface FeT (about 5e-4 mmol m-3), and v05 PIC is partly negative.
- **Speed reporting** → Report seconds and GPU-hours per simulated year for the emulator and for the free nulls. Print a speedup only when the ECCO-Darwin reference is known and H* passes, labelled with H* and the fraction of the state emulated.
  - why: 'Speed - measured, and irrelevant' is settled: speed is worthless past the useful horizon. The reference cost is not in the repo.
- **Counted fields and the multiplicity rule** → Require at least 2 of {DIC, ALK, FeT, PIC} (daily: pCO2, CO2_flux, O2_flux, log surfChl1), the same fields at every lead up to H*. POC and Chl1 are reported only. Never pool across fields.
  - why: This mirrors the §5 pre-registration. The PIC/POC 'mechanical headroom' lesson showed a pooled number carried by two tracers.

## Risks

- The data is too small for diffusion. Under G12 each target with physics has about 145 train, 28-32 val and 86-95 test months; all six tracers plus physics have only 81/15/50. Consecutive one-month pairs number 51-67 for all six and 224 for DIC alone, which is the regime where denoisers memorise (N ≤ 100). The memorisation flag will likely fire.
- Statistical power is low: about 9 test years means about 9 time blocks, so the CIs will be wide. A real but small effect may fail the rule. This is accepted, not a defect.
- The self-coarsened super-resolution task has no user (finding :113-115). BGC fields may be smooth at 1/3°, so the residual-variance fraction may be tiny and every method ties.
- The true averaging windows of the v05 monthly files cannot be verified from the metadata. If some months are partial averages (for example after restarts), climatologies carry extra noise.
- The local mirror is inconsistent: DIC has 45 .meta files with no .data and 5 .data files with no .meta, and physics variables have 4-6 orphans. A build that globs only .data or only .meta will silently differ (measured: 152 vs 125 months for all six plus physics).
- The daily archive is not on disk. pCO2, pH and surfPCO2 are 50-level files of 180.8 MB each, about 1.8 TB per variable over about 9,860 days. Extract k0 inside a Slurm job and delete the full files.
- earth2studio's StormCast wrapper is hardwired to HRRR, so a custom PrognosticModel wrapper is needed. regional_weather_diffusion exists on physicsnemo main only and its API may move. Pin commits, not releases.
- physics_verify.py imports diffusion_emulator at module load (line 42), so importing physics_report from track2/ pulls in torch and the FNO. Also, build_public_release.py ships physics_verify without diffusion_emulator (finding :232-235).
- Anthropogenic trends confound DIC/pCO2 skill against plain climatology. The trend-climatology null is mandatory, or the skill is inflated.
- Offline-BGC mode makes the StormCast model a physics-driven BGC emulator, not a standalone forecaster. It must not be described as forecasting, and its speedup excludes the physics it consumes.
- Repeated test scoring across variants (forking paths). The ledger cap of 3 configs is only an advisory flag unless the owner makes it a hard gate.
- Windows 5090 has no multi-process CUDA, so local discovery and replication runs must be serial, separately invoked runs. Prefer AICR for both to hold hardware constant.

## Unknowns

- ECCO-Darwin v05 cost per simulated year is not in the repo: wall-clock, core count, node type and system. Pleiades was decommissioned 2026-01-07. The '768 cores' in the brief has no repo source that I could find (unverified). This is a collaborator ask.
- Whether each v05 monthly .data file is a full calendar-month average. The .meta timeInterval is a nominal-frequency artifact and cannot tell.
- Whether LLC270 bin-averaged onto a 1/3° regular grid covers at least 99% of ocean bins, which decides 1/3° vs 1/2°. Not measured.
- What fraction of surface FeT (and PIC/POC) lies below a 1e-4 or a 1e-3×median floor. Not measured.
- Whether earth2studio CorrDiff's grid checks (_check_grid_spacing, _check_grid_bounds) accept a global 1/3°→1° pair with land masking, and whether earth2studio.run.ensemble can drive a custom StormCast-style wrapper with a time-varying background. Neither was tested.
- Whether regional_weather_diffusion's dataset interface handles a background at t+1 plus a static ocean mask the way the README describes. Read from the README only.
- Whether StormCast reports CRPS. My WebFetch summary listed RMSE, FSS, SER, PSD and histograms but not CRPS. The CorrDiff speed figures (22× vs 652×) also came back inconsistent in the summary, so quote neither until the exact sentence is read.
- The reference salinity for SSSanom/SALTanom, needed if the carbonate closure is extended to actual T/S. Unverified.
- Darwin's actual air-sea gas-exchange formula, for the proposed flux-consistency check. Unverified; the truth control column is meant to absorb any mismatch.
- Which horizons real users need (seasonal vs annual vs multi-decadal). The targets H* ≥ 3 months (monthly) and ≥ 30 days (daily) are my proposal and need the owner's sign-off before the pre-registration is committed.

## Spec

# Grading spec: Earth-2 CorrDiff / StormCast on ECCO-Darwin v05 (read-only design; nothing created)

## 0. Frame and staging
- Every number compares the emulator with the ECCO-Darwin v05 model's own output, never with observations (docs/findings/2026-07-19_emulator_honest_bounds.md:13-16). Every metric carries its space label, linear or log10 (same doc :141-151).
- Stages share one scorer and one gate:
  - **S0** is the already-registered physics-to-BGC diagnostic, `hy_physics_to_bgc_diagnostic_beats_climatology` (docs/findings/2026-09-30_earth2_air_pollution_recipe_is_not_a_track2_lever.md:136-165). It runs with the regression U-Net only.
  - **S1** is CorrDiff super-resolution (CD-SR).
  - **S2** is StormCast, monthly (SC-M) and daily (SC-D).
  - S0's STOP rule (same doc :160-163) stays binding on the wording. If S0 stops, S1/S2 verdicts print as "DESCRIPTIVE - direction closed by S0".
- Settled constraints this design obeys:
  - The ensemble mean of a diffusion model does not beat its own regression stage (CorrDiff Table 1; same finding :60-80).
  - The next-step bar is a per-cell seasonal AR(1).
  - There is no positive Lyapunov exponent (docs/findings/2026-07-20_rollout_ceiling_mechanism.md:57-81), so diffusion earns only probabilistic credit.

## 1. Shared foundations

### 1.1 Data manifest (`e2_build_truth.py`)
- A month is usable for a variable only when both files exist:
  - `<var>.<iter>.data` with the exact size: 2-D is 3,790,800 B (270×3510×4); 3-D is 189,540,000 B (×50).
  - `<var>.<iter>.meta` with a matching timeStepNumber and dimList.
- Measured today on `D:\ecco_darwin_v5\output\monthly`:

| variable | .data | .meta | meta without data | data without meta |
|---|---|---|---|---|
| DIC | 278 | 318 | 45 | 5 |
| SST | 320 | 318 | 3 | 5 |
| mldDepth | 323 | 319 | 0 | 4 |
| oceanQsw | 322 | 317 | 1 | 6 |

- Re-fetch the missing .meta files before building.
- Record `(var, iter, bytes, mtime)` in `manifest.json` and put its sha256 in the results file.

### 1.2 Calendar
- Month label = `(np.datetime64('1992-01-01T00:00:00') + iter*1200 s - 1 s).astype('datetime64[M]')`. Daily data uses day resolution.
- Assert that iter×1200 s lands at 00:00 on the 1st of a month (monthly) or at 00:00 (daily).
- **Verified today:** all 318 DIC, 318 SST and 321 Chl1 stamps satisfy this. They map to unique months from 1992-01 to 2018-11, and the stamp marks the end of the averaging window.
- Constants: `src/darwindiff/llc270_loader.py:169-170` (`delta_t=1200`, `ref_date="1992-01-01"`).
- Never use:
  - `_season_bin` (`scripts/analysis/emulator_baselines_v2.py:104-109`, known bug).
  - `rollout_verify.month_of_year` (`scripts/rollout_verify.py:60-68`). It labels by the stamp, so every monthly mean is tagged one month late. Its bins are internally consistent, but its labels are wrong.
  - The `.meta` `timeInterval`. Its start equals floor(end/2,635,200 s)×2,635,200 s in all 318/318/321 files checked. That is the nominal 30.5-day frequency, and the implied window lengths are 0.5-31 days, so it certifies nothing.

### 1.3 Grids
- earth2studio needs a lat/lon grid regridded upstream (`src/darwindiff/e2s/datasource.py:5-10`).
- **Fine grid G_f:** regular 1/3°, built by the same LLC→regular bin-average as `scripts/emulator_poc.py:467-469` (`--grid-res`).
  - Data-only pre-check: at least 99% of ocean bins must hold one or more LLC cell centres. Otherwise fall back to 1/2° fine and 1.5° coarse.
- **Coarse grid G_c:** an exact 3×3 block mean of G_f, weighted by area and ocean fraction, so it is conservative by construction.
- Declare `task_realism: "self_coarsened"` (finding :113-115).
- **Weights:** exact cell area, R²Δλ(sinφ2−sinφ1).
- **Scoring mask:** finite jointly over the truth and every predictor, following the `emulator_baselines_v2.py:439-447` pattern.

### 1.4 Fields and spaces
- **Counted fields F4 = {DIC, ALK, FeT, PIC}**, as in §5 :155-157. POC is reported. Chl1 is a control and never counts.
- **Primary spaces:**
  - DIC and ALK are scored in linear space.
  - FeT, PIC, POC and Chl1 are scored in log10 with a per-tracer floor f_v = 1e-3 × the train-period area-weighted median.
  - Do not use the 1e-4 default in `rollout_verify.py:78`, `physics_verify.py:133` or `deep_ensemble_eval.py:48`. FeT is in mmol m-3, and surface FeT is about 5e-4 (`docs/archive/findings/v2.8_darwin_ic_poc_sub.md:41`), so a 1e-4 floor may clip oligotrophic iron. That fraction is unmeasured.
- In log space, score only cells where truth > f_v. Record the excluded fraction; the gate flags it above 1%.
- The secondary space is always reported. A verdict that flips between spaces raises SPACE_DEPENDENT.
- **Daily counted fields F_D** = {pCO2 k0, CO2_flux, O2_flux, log10 surfChl1}. pH k0 and surfChl2-5 are reported only.

### 1.5 Splits (inclusive month labels; daily uses the same boundaries by day)

| split | train | val | gap | test |
|---|---|---|---|---|
| G12 (primary) | 1992-01..2005-12 | 2006-01..2008-12 | 2009-01..2009-12 | 2010-01..2018-11 |
| G6 | same | same | 2009-01..06 | 2009-07..2018-11 |
| G24 | same | same | 2009-01..2010-12 | 2011-01..2018-11 |
| REV12 | 2005-01..2018-11 | 2002-01..2004-12 | 2001 | 1992-01..2000-12 |

Measured usable months under G12 (non-empty .data, all 7 physics present), train/val/test:

| target | train | val | test |
|---|---|---|---|
| DIC | 145 | 28 | 86 |
| ALK | 145 | 30 | 90 |
| FeT | 148 | 30 | 93 |
| PIC | 147 | 28 | 87 |
| POC | 145 | 31 | 95 |
| Chl1 | 147 | 32 | 90 |
| all six + physics | 81 | 15 | 50 |

- The all-six total is 152 months, or 125 if a matching .meta is also required.
- Consecutive one-month pairs: 51-67 for all six, 224 for DIC alone.

### 1.6 What is fit where
- **TRAIN only:** normalisation statistics, climatologies, trends, φ, and the ridge/ARX coefficients.
- **VAL only:** ridge λ, checkpoint/epoch selection, dressing σ and sampler settings.
- **TEST:** touched once per config. At most 3 distinct configs may be scored on the G12 test set; a ledger enforces this.
- Do not reuse `scripts/diffusion_emulator.py:57-65 zscore`: it normalises over all T, including val.

### 1.7 Metrics
All metrics are per field and per space, area-weighted, and pooled over test months (and over starts for rollouts).
- **RMSE and MAE.** Skill S(M|B) = 1 − RMSE_M/RMSE_B, the repo convention (`emulator_baselines_v2.py:47`).
- **ACC:** centred, area-weighted correlation of anomalies against the TRAIN monthly climatology.
- **Fair CRPS** = (1/N)Σ|x_j−y| − ΣΣ|x_j−x_k|/(2N(N−1)).
  - This is earth2studio `statistics.crps(fair=True)`, `crps.py:172-173` at 2067756d. For a deterministic predictor, CRPS = MAE.
  - CRPSS = 1 − CRPS_M/CRPS_B.
- **SSR** = sqrt((N+1)/N) · sqrt(Σw·s²/Σw) / RMSE(ensemble mean), with s² at ddof=1 (Fortin et al. 2014, J. Hydrometeor. 15:1708).
  - earth2studio `spread_skill_ratio` (`rmse.py:342-345` at 2067756d) omits the (N+1)/N factor. Record both.
  - `deep_ensemble_eval.py:96,108` uses mean(std)/RMSE, which is a different, biased-low quantity. The old 0.240/0.375 calibration numbers are not comparable.
- **Rank histogram:** N+1 bins, computed on every 4th cell; report χ²/dof and the out-of-range fraction against 2/(N+1).
- **Spectra:** radially averaged PSD on a pre-registered, fixed list of fully-ocean 48×48 tiles of G_f with |lat| ≤ 50°.
  - Apply a linear detrend and a 2-D Hann taper, then average over tiles, months and members.
  - Report LSD (dB) = 10·sqrt(mean_k (log10 P_M/P_T)²), which is the earth2studio `lsd.py` definition.
  - Report the mean of |P_M/P_T − 1| over wavelengths shorter than 2 coarse cells.
  - Do not FFT whole fields. `diffusion_emulator.py:310-321` zero-fills land, and physicsnemo `examples/weather/regional_weather_diffusion/utils/spectrum.py` at 536553ac computes over the full domain.
- **Tails:** area-weighted q01, q50, q99 and q99.9 with members pooled.
  - Tail error = |q99.9_M − q99.9_T| / (q99.9_T − q50_T).
  - W1 distance divided by the truth IQR.
- **Memorisation (diffusion only):** median d(generated, nearest TRAIN field) ÷ median d(test truth, nearest TRAIN field). Flag MEMORIZATION if the ratio is below 0.8.

### 1.8 Uncertainty
- Use a paired space×time block bootstrap computed from stored block sums.
  - **Spatial blocks** are 15°×36° (45×108 cells of G_f), matching the v2 defaults at `emulator_baselines_v2.py:304-305`.
  - **Time blocks** are calendar years of the target, or of the start for rollouts.
  - Resample spatial and time blocks independently, with replacement. B=2000, seed 20261001, 95% percentile CI.
- The best free null is chosen on the full sample (v2 :481-483); skill is then bootstrapped against it.
- Only about 9 test years exist, so the CIs will be wide. That is expected and honest.

### 1.9 Self-tests in every job (the job is VOID if either fails)
- **ORACLE** = truth + N(0, (0.5·RMSE_bestnull)²). It must PASS rule D.
- **YEAR-SHUFFLE** = the model's own test predictions permuted across years within each calendar month. It must FAIL, meaning its ACC CI includes 0.
- If the unshuffled model's ACC is not above the shuffled one, flag CLIMATOLOGY_ONLY. This is the failure mode where the model learned only the climatology (finding :126-127).

## 2. CorrDiff (S1 = CD-SR; S0 = physics-to-BGC)

**CD-SR task**
- Inputs at month t:
  - x_c(t) on G_c;
  - coarse {SST, SSSanom, mldDepth, wspeed, oceanQsw, oceanQnet, SIarea} at t;
  - invariants: mask, bathymetry, sin/cos lat and lon.
- Output: the fine target on G_f at t.
- Inference runs through earth2studio `models/dx/corrdiff.py` at 2067756d:
  - `inference_mode` ∈ {"regression","both"} (L125, L176). "regression" produces the regression-alone null through the same code path.
  - `number_of_samples=32`, `number_of_steps=18`; solver and seed are recorded. `load_model` reads `metadata.json` (L690-710).
- For S0, the inputs are fine physics only, with no coarse BGC. Its nulls are N4 and N5′ (ridge on physics anomalies). Seasonal AR(1) is reported only, marked as information-advantaged. Pass and stop follow §5 exactly.

**Nulls (all in the same job)**
- **N1 conservative:** piecewise-constant upsample U0(x_c).
- **N2 bilinear:** ocean-aware normalised convolution, with land weight 0.
- **N3 delta:** U0(x_c) + [C_f(m) − U0(A·C_f(m))]. This is the train climatology's sub-grid pattern, which has zero block mean, so N3 is exactly coarse-consistent. It is the strongest free null.
- **N4:** the fine per-cell monthly climatology (train).
- **N4T:** N4 + b_i(t − t̄_train), with b_i from train OLS. It is required because the anthropogenic DIC/pCO2 trend across the gap biases N4 low.
- **N5 per-cell ridge:** y_i − C_f,i(m) regressed on [U2(x_c − A·C_f(m))_i, 7 coarse-physics anomalies at the parent cell, 1].
  - One global λ from 10^-3..10^3, chosen on val for each field; fit on train.
  - Its declared inputs must include every time-varying input the model gets; the gate checks this.
- **N6 regression stage:** the ensemble mean of seeds 0-4.
- **N7 dressed regression:** N6 + N(0, σ_i²), where σ_i is the std of N6's residual over VAL months at cell i, box-smoothed 3×3. 32 draws.
- **N8 deep ensemble:** the 5 regression seeds used as members (honest_bounds :174-196).

**Extra diagnostics**
- CCE = RMSE(A·ŷ − x_c) / std(x_c anomaly). It is 0 by construction for N1 and N3.
- Residual-variance fraction RVF = var(y − U0·x_c) / var(y − C_f). It shows how much is left to predict.

**Rules**
- **D** (the only skill claim, made for N6): on at least 2 of F4, in the primary space, both must hold:
  - S(N6 | best of {N1, N2, N3, N5}) has a CI lower bound above 0;
  - S(N6 | N4T) ≥ +0.10 with a CI lower bound above 0.
  - This must hold under G12, G6, G24 and REV12, and must replicate.
- **D-noharm:** S(CorrDiff ensemble mean | N6) ≥ −0.02. Otherwise flag DIFFUSION_DEGRADES.
- **P** (evaluated only if D passes) licenses the diffusion stage. On at least 2 of F4:
  - CRPSS against the better of N7 and N8 has a CI lower bound above 0;
  - SSR is within [0.7, 1.3];
  - the sub-coarse PSD error is below 0.20 and below N6's;
  - the tail error is below N6's.
- **Physics** (truth is the control column), using `physics_verify.physics_report` (`physics_verify.py:57-102`):
  - A: negative fraction ≤ truth + 1e-4.
  - B: in-band fraction ≥ truth − 0.01.
  - C: fraction physical ≥ truth − 0.01.
  - Check D (stoichiometry, :105-120) is excluded (honest_bounds :248-254).
  - CCE ≤ 0.25.
- **STOP** closes the direction, including any diffusion variant:
  - N6 is not above the best of {N1, N2, N3, N5} on 3 or more of F4; or
  - D passes at one split only.

## 3. StormCast (S2)

**SC-M (monthly)**
- State: {DIC, ALK, FeT, PIC, POC, Chl1} on G_f, levels k0..k9 (0-100 m, which the inventory check needs).
- Background: the 7 surface physics fields at t+1, taken from v05 truth. This is offline-BGC mode.
- Every train and eval pair must be exactly one calendar month apart; the gate asserts it. The old cube's 1-to-7-month pairs (honest_bounds :76-95) are forbidden.
- Per-tracer models are allowed. n_train_pairs is recorded, and LOW_N is flagged below 100.

**SC-D (daily, after re-download)**
- State: {pCO2 k0, pH k0, CO2_flux, O2_flux, surfChl1-5}.
- Background at t+1: {SST, SSSanom, wspeed, SIarea, SIheff, apCO2}.

**Background rule:** a coarse copy of the target at t+1 is forbidden unless an information-matched null receives it too. Otherwise the gate exits INTEGRITY.

**Nulls (per cell, all in the same job)**
- Persistence.
- Seasonal climatology: 12 monthly means for SC-M; mean + 3 annual harmonics per cell for SC-D.
- Trend-climatology.
- Seasonal AR(1) k-step: C(m_{t+k}) + φ_i^k·(x_i(t) − C(m_t)).
  - φ_i is fit on train pairs exactly one step apart and clipped to (−0.999, 0.999). This generalises v2 A1s (:423).
- ARX(1), information-matched: â(t+k) = φ_i·â(t+k−1) + γ_i·p′_i(t+k), with the same true background anomalies at every step. Ridge-fit on train, λ chosen on val.
- Regression-only rollout, 5 seeds (for attribution).
- Dressed regression rollout, with σ_i(L) from VAL-period rollouts, capped at the climatological std.
- Deep-ensemble rollout.

**Leads, starts and free runs**
- Scored leads: SC-M {1, 2, 3, 6, 12, 24} months; SC-D {1, 2, 5, 10, 30, 90, 180, 365} days.
- SC-M starts: every test month where the background exists at every step and the truth exists at every scored lead. Excluded starts are recorded.
- SC-D starts: the 1st of every test month (every 3rd month for the 365-day lead).
- Free run: one trajectory per member to the end of test (about 106 steps for SC-M, about 3,285 for SC-D). It is scored only for physics and climate fidelity.

**Useful horizon H\***
- H* is the largest scored lead L such that, at every lead ≤ L, on the same 2 or more fields of F4 (F_D for daily), S(model | best of {persistence, climatology, trend-climatology, seasonal AR(1), ARX(1)}) has a CI lower bound above 0.
- The model here is the regression-stage deep-ensemble mean. The diffusion ensemble mean is reported beside it.
- Pre-registered targets: SC-M H* ≥ 3 months, which is beyond the settled ~2-month ceiling (honest_bounds :301-305); that ceiling had no physics conditioning. SC-D H* ≥ 30 days.
- Long-lead value is never judged by skill against persistence (`rollout_verify.py:8-13`).

**Physics checks, per lead and along the free run (truth control column)**
- physics_report A; B and C for SC-M.
- Inventory I(t) = Σ_i Σ_k A_i·dz_k·hFacC·x, and drift = I_M/I_T − 1, averaged over starts.
  - DIC and ALK must hold |drift| ≤ 0.1% at 12 months and ≤ 0.5% at the free-run end. The log-space run already held DIC/ALK under 0.1% over 6 steps (map row "Did the log-space fix give the emulator mass conservation?").
  - The other tracers are reported only.
  - Do not reuse `rollout_verify.py:178-180` mass_ratio: it is an unweighted sum across all channels.
- **SC-D flux consistency (proposed):** CO2_flux ≈ α(1−SIarea)·k(wspeed)·(pCO2 − apCO2), with α and k fit on TRAIN truth.
  - The model's residual RMS must be ≤ 1.5× the truth's.
  - The functional form is unverified against Darwin's code; the truth control column absorbs the mismatch.
- Any non-finite value is a FAIL.

**Climate fidelity** (last 36 months of the free run, 2015-12..2018-11)
- Compare the free run's per-cell monthly climatology with the truth's over the same months.
- Report skill against N4 and against the extrapolated trend-climatology, the seasonal-amplitude ratio (must fall in [0.8, 1.25]), and the inventory-trend ratio.
- It passes if S against trend-climatology has a CI lower bound above 0 on 2 or more fields. Otherwise report "no climate information beyond trend-climatology".

**Rules**
- **R:** H* ≥ its target under all four splits, replicated.
- **P:** the same as CorrDiff, at every lead ≤ H*.
- **Physics** must pass at every lead ≤ H* and along the whole free run.
- **STOP:**
  - The regression rollout at lead 1 is not above the best free null on 3 or more of F4; or
  - ARX(1) is within the CI of the model at lead 1 on 3 or more of F4; or
  - it passes at one split only.

## 4. Held-out period and replication
- **Job A (discovery):** one sbatch on AICR B200 with account p2026_0089_neu.
  - Split G12; regression seeds 0-4, diffusion seed 0, sampler seeds 0-31.
  - All nulls and self-tests run inside the job. Its JSON records `SLURM_JOB_ID` and the submit time.
- **Job B (replication):** a separate sbatch, submitted only after Job A's gate verdict and research-map row are committed.
  - Fresh seeds: regression 100-104, diffusion 100, sampler 1000-1031.
  - It runs on G12, plus G6, G24 and REV12, each with its own in-job nulls.
  - The nulls on G12 must reproduce Job A's block sums bitwise (to a relative tolerance of 1e-9). If not, the gate reports DISCREPANCY.
  - Job B passes only on its own numbers, never pooled with Job A.
- Splitting one array in half is not replication (CLAUDE.md). On the local 5090 (serial CUDA only), "separate submission" means a separate invocation with its own run_id, launched after the discovery commit.
- Build environments inside a Slurm job, not on the login node.

## 5. Speed benchmark (`e2_bench.py`)
- **Measurement protocol:** synchronise CUDA around the timed region, run 3 warm-up iterations, then take the median and IQR of 5 repeats.
  - Record batch 1 and the largest batch that fits.
  - Record fp32 vs bf16, `torch.compile` on or off, and the number of network evaluations per step (NFE; Heun with 18 steps is about 35).
- **Report per task:**
  - seconds per simulated year per member, and for the whole ensemble;
  - GPU-hours per simulated year;
  - NVML energy per simulated year, if available;
  - numbers with and without I/O;
  - the same numbers for the ridge, AR(1) and ARX(1) nulls on CPU.
  - A simulated year is 12 monthly steps (CD, SC-M) or 365 daily steps (SC-D).
- **Hardware:** RTX 5090 (local), B200, H200.
- **What the repo knows about the reference:**
  - `delta_t` = 1200 s (`llc270_loader.py:169`), i.e. 72 steps/day (honest_bounds :58-62) and 26,280 steps per 365-day year.
  - The "768 cores" figure is from the brief; I found no repo source for it (unverified).
  - Pleiades was decommissioned 2026-01-07. The current systems are Athena, Aitken and Electra, and the repo already says a baseline must be benchmarked before budgeting (`docs/findings/2026-07-23_v05_perturbation_recipe.md:193`).
  - Prior emulator timing is 7.45 ms per global monthly step, 2.29 GB, for the old FNO (honest_bounds :331-339).
  - External anchor: SamudraBGC takes about 6 min per model-year on one GPU against about 4 h on 896 cores (research-map row, `docs/findings/2026-09-19_samudrabgc_m2lines_now_does_bgc.md`).
- **Collaborator ask:** wall-clock hours, core count, node type and system per simulated year for the v05 LLC270 Darwin run, including I/O. Also whether the physics is run inline, and what share of the cost is the BGC.
- **Gate rule:** a speedup prints only when the reference is known AND R passes. It must be labelled "at useful horizon H\*, emulating <channels> of Darwin's fields, requires v05 physics as background". Otherwise the gate prints "speed measured; no speedup claimed" (honest_bounds: "Speed - measured, and irrelevant").

## 6. Results JSON (`results.json` plus a `sums.npz` sidecar; schema `darwindiff.e2eval/1`)

```
{schema, task: "s0_diag"|"cd_sr"|"sc_monthly"|"sc_daily", role: "discovery"|"replication",
 run: {run_id, slurm_job_id, submit_utc, start_utc, end_utc, host, gpu{name,count,driver},
       python, torch, physicsnemo_commit, earth2studio_commit, darwindiff_commit, track2_commit, git_dirty:bool},
 prereg: {md_path, md_sha256, yaml_path, yaml_sha256, commit, commit_utc},
 config: {sha256, resolved:{...}, seeds:{regression:[..], diffusion:[..], sampler:[..]}},
 data: {root, manifest_path, manifest_sha256, delta_t_s:1200, epoch:"1992-01-01T00:00:00",
        month_label_rule:"stamp_minus_1s", grid:{fine:{res_deg, shape}, coarse:{res_deg, shape}, coverage_frac},
        mask_sha256, weights:"cell_area_m2", task_realism},
 calendar: [{iter, label}],
 split: {name, gap_months, train:[labels], val:[labels], test:[labels]},
 fits: {normalization:{months}, climatology:{months}, trend:{months}, ar1:{pairs}, ridge:{months, lambda_grid, lambda:{field:val}, selected_on:"val"},
        checkpoint:{selected_on:"val", metric}, dressing:{fit_on:"val"}},
 fields: [{name, level, counted:bool, space_primary, log_floor, frac_truth_below_floor}],
 predictors: [{id, kind:"model"|"null"|"selftest", stage, seeds, n_members, sampler:{steps,solver,nfe}, inputs:[..], info_matched_to:null|id}],
 leads: [..], starts: {used:[..], excluded:[{start, reason}]},
 blocks: {spatial:{rows,cols,n}, temporal:{unit:"year", n}, bootstrap:{B:2000, seed:20261001, ci:0.95}},
 sums: {path:"sums.npz", sha256, layout:["field","space","lead","predictor","sblock","tblock"],
        arrays:["sse","sae","wsum","crps_fair","ens_var","n_members"]},
 rank_hist, spectra:{tiles:[[i0,j0,48]], k_cut, psd:{pred:[..]}}, tails, memorization,
 physics: {pred_or_truth:{lead:physics_report_dict}}, inventory:{tracer:{pred:{lead:drift}}}, flux_consistency,
 climate_fidelity, selftests:{oracle:{pass}, year_shuffle:{acc_ci}},
 reported: {skill:{field:{space:{lead:{best_null, vs:{null:{point,lo,hi}}}}}}, crpss, ssr, lsd_db, psd_relerr,
            acc, cce, rvf, h_star, verdict:{rule:"PASS"|"FAIL"|"STOP"|"VOID", per_rule:{..}}},
 speed: {hardware, emulator:{..}, nulls:{..}, reference:{cores:null, wallclock_h_per_sim_year:null, source:"UNKNOWN"}, speedup:null},
 test_ledger_count}
```

## 7. Gate `scripts/verify_e2_run.py` (main repo; numpy/json only)

Structure and exit codes follow `verify_run.py:30-40,475-476`:

| exit | status | condition |
|---|---|---|
| 0 | VERIFIED | numbers are trustworthy; the verdict prints separately as PASS/FAIL/STOP |
| 2 | DISCREPANCY | a recomputed number differs from the stored one by more than 1e-6, or replication nulls are not bitwise equal |
| 3 | INCOMPLETE | seeds or members are missing |
| 4 | CRASHED_NO_JSON | a log exists but no JSON |
| 5 | NO_DATA | no artifacts |
| 6 | NO_BASELINE | any required null for the task is missing, or the truth control column is missing |
| 7 | UNGRADED | the sums sidecar is absent or fails its sha256 |
| 8 | INTEGRITY | leak, calendar, prereg, information or cross-job violation, or a VOID self-test |
| 9 | NO_REPLICATION | only with `--require-replication` |

Checks, in order:
1. Schema and required keys.
2. Recompute the calendar labels from `iters`, and assert the 1st-of-month stamps.
3. Split integrity:
   - train ∩ val ∩ test = ∅; the gap is at least the declared length;
   - every fit's months ⊆ train; every selection's months ⊆ val;
   - every rollout trajectory ⊆ test;
   - monthly pairs are exactly one month apart.
4. The prereg sha256 matches the committed file, and its commit time is before `run.submit_utc` (`git log -1 --format=%cI`).
5. All predictors share one `slurm_job_id` and one manifest sha.
6. Information matching: the model's time-varying inputs ⊆ the inputs of its information-matched null (N5 for CD, ARX(1) for SC). No background from the target at t+1.
7. Recompute every RMSE, skill, best null, CRPSS and SSR from the sums, plus the CIs with the recorded seed. Compare with `reported`.
8. Re-derive the verdict from the prereg YAML thresholds.
9. Advisory flags, printed but not exit-gating (the same logic that keeps STRADDLE advisory):
   - THRESHOLD_EDGE: the verdict flips within ±0.05 of the +0.10 margin, of the SSR band or of the PSD 0.20 threshold, or between 90% and 99% CIs.
   - SPACE_DEPENDENT, LOW_N, MEMORIZATION, CLIMATOLOGY_ONLY, DIFFUSION_DEGRADES.
   - TEST_REUSE when the ledger count exceeds 3; MANIFEST_NOT_REVERIFIED when `--data-root` is absent.
   - The gate refuses to print any skill pooled across fields.
10. `--replication DIR` checks:
    - the replication has a different job id, the same prereg and config sha (except seeds), and disjoint seeds;
    - its submit time is after the discovery verdict commit;
    - the G12 null sums are bitwise equal;
    - the rule passes on the replication alone.

Tests (`tests/test_verify_e2_run.py`), on synthetic data:
- an oracle passes;
- a year-shuffled model fails;
- a leaked normalisation exits 8;
- a tampered stored skill exits 2;
- a missing N3 exits 6;
- a missing sidecar exits 7.

## 8. Draft scorer outline (`track2/scripts/e2_eval.py`; separate uv project `track2/`)
- earth2studio needs netCDF4<1.7.3, while the root lock pins 1.7.4, so `track2/` has its own uv project (finding §6).
- `track2/pyproject.toml` depends on `darwindiff` by path via `tool.uv.sources`. physicsnemo and earth2studio are pinned by commit.

```python
# e2_eval.py  (subcommands: build-truth | fit-nulls | infer | score | bench)
CAL_EPOCH = np.datetime64("1992-01-01T00:00:00"); DT_S = 1200
def month_labels(iters) -> np.ndarray            # stamp - 1 s -> datetime64[M]; asserts 1st-of-month 00:00
def build_manifest(root, vars) -> dict            # .data exact size + .meta present; sha256 of manifest
def load_split(prereg_yaml, name) -> Split        # train/val/gap/test label sets
def build_truth(task, split, grid) -> TruthStore  # LLC->G_f bin-average (emulator_poc path); A() 3x3 conservative -> G_c; zarr
def fit_nulls(truth, split, task) -> dict[str, Null]
    # clim(train) | trend_clim | conservative U0 | bilinear U2 (normalized conv) | delta | ridge (batched normal eqs, lambda on val)
    # seasonal_ar1 (phi per cell, 1-step train pairs, k-step phi**k) | arx1 (info-matched) | persistence
def run_model(package, inputs, mode: Literal["regression","both"], n_samples, seed)  # earth2studio CorrDiff.load_model(package)
def run_stormcast(ckpts, x0, background_iter, leads, members, seed)                  # custom PrognosticModel wrapper (earth2studio's is HRRR-bound)
class Accumulator:  # streaming; never holds all members in RAM
    def update(self, field, space, lead, pred_id, yhat_or_members, truth, w, sblock, tblock)  # sse, sae, wsum, crps_fair, ens_var
    def to_npz(self, path) -> sha256
def spectra(fields, tiles, k_cut) -> dict        # fixed ocean-only 48x48 tiles, Hann + detrend
def tails(...), rank_hist(...), memorization(gen, train_bank, test_truth)
def physics(pred_phys, truth_phys, mask, names) -> dict   # imports physics_verify.physics_report by path; records file sha256
def inventory_drift(x, area, dz, hfac) -> float           # NEW; area x thickness weighted
def flux_consistency(pco2, apco2, wspeed, siarea, flux, fit) -> dict  # NEW, SC-D
def selftests(acc_inputs) -> dict                # oracle must pass; year-shuffle must fail
def bootstrap(sums, B=2000, seed=20261001) -> dict ; def verdict(prereg, cis) -> dict
def write_results(run_dir, meta, sums_path, reported)     # results.json + sums.npz + append test_ledger.jsonl
```

Commands:

```
uv run --project track2 python track2/scripts/e2_eval.py build-truth --task cd_sr --split G12 --data-root D:/ecco_darwin_v5/output/monthly --out $RUN
uv run --project track2 python track2/scripts/e2_eval.py fit-nulls --run $RUN
uv run --project track2 python track2/scripts/e2_eval.py infer --run $RUN --package $PKG --mode regression --members 1 --seeds 0-4
uv run --project track2 python track2/scripts/e2_eval.py infer --run $RUN --package $PKG --mode both --members 32 --seed 0
uv run --project track2 python track2/scripts/e2_eval.py score --run $RUN && uv run --project track2 python track2/scripts/e2_eval.py bench --run $RUN
python scripts/verify_e2_run.py $RUN --require-baseline [--replication $RUN_B --require-replication] [--data-root D:/...] [--json]
```

- Inference writes per-member zarr through an earth2studio IO backend. The free runs are scored in process and never stored.
- After a verdict: add the map row in the same commit, then run `python scripts/research_map_db.py check`.

## 9. Pre-registration text
Commit as `docs/findings/2026-10-XX_prereg_earth2_generative_grading.md` with `track2/configs/prereg_e2.yaml`, before any training.

> # Pre-registration: grading the Earth-2 CorrDiff/StormCast replication on ECCO-Darwin v05
>
> **Submitted before any model is trained or scored.** · Gate: `scripts/verify_e2_run.py` · Scorer: `track2/scripts/e2_eval.py` · Thresholds: `track2/configs/prereg_e2.yaml` (sha256 ___).
>
> **1. What is tested.**
> (i) Whether a CorrDiff-style model (regression U-Net + EDM residual) turns self-coarsened (1° box-mean) v05 surface BGC into 1/3° fields better than free per-cell baselines.
> (ii) Whether a StormCast-style model (regression + diffusion step, conditioned on v05 physics at the target time) rolls v05 BGC forward better than free per-cell baselines, to set horizons.
> Every number is agreement with the v05 model, not with observations. The diffusion stage is not expected to add deterministic skill (settled; CorrDiff Table 1). It can earn credit only through CRPS, calibration, spectra and tails.
>
> **2. Stage 0 first.** `hy_physics_to_bgc_diagnostic_beats_climatology` runs through this harness with the regression U-Net only. Its pass and stop rules are unchanged. If it stops, the CorrDiff/StormCast results are reported as descriptive.
>
> **3. Data and split.**
> - Month = the calendar month ending at the file stamp (iter × 1200 s from 1992-01-01, minus 1 s).
> - A month counts only if both its .data (exact size) and .meta exist.
> - Primary split G12: train 1992-01..2005-12, val 2006-01..2008-12, gap 2009, test 2010-01..2018-11. Robustness: G6, G24 and REV12.
> - All fits use train only. All selection uses val only. At most 3 configs are scored on the G12 test.
>
> **4. Predictions, stated so they cannot be retro-fitted.** None is a pass criterion, and both outcomes of each are reportable.
> - P1: N6 beats interpolation on FeT and PIC (log), but its margin over the delta method is small.
> - P2: the CorrDiff ensemble mean is within ±2% of N6's RMSE.
> - P3: ARX(1) is the binding null for SC-M.
> - P4: the diffusion SSR is below 1.
> - P5: MEMORIZATION fires for SC-M.
>
> **5. Decision rules fixed in advance.**
> - Counted fields: {DIC, ALK, FeT, PIC} (daily: {pCO2, CO2_flux, O2_flux, log surfChl1}). DIC and ALK are scored linear, the rest log10. Wins are per field, never pooled.
> - **D:** N6 must beat the best of {conservative, bilinear, delta, per-cell ridge}, with a 95% space×time block-bootstrap CI lower bound above 0, on at least 2 counted fields. On those same fields it must also beat the trend-climatology by at least +0.10 skill with a CI lower bound above 0.
> - **R (StormCast):** H* is the largest scored lead with that same win, on the same fields at every shorter lead, against the best of {persistence, climatology, trend-climatology, seasonal AR(1), ARX(1) with the same background}. Targets: SC-M H* ≥ 3 months, SC-D H* ≥ 30 days.
> - **P (licenses diffusion, only after D or R):** on at least 2 counted fields, fair CRPSS against the better of {dressed regression, 5-seed deep ensemble} has a CI lower bound above 0, SSR is within [0.7, 1.3], and the sub-coarse PSD error is below 0.20 and below N6's.
> - **Physics, against a v05 truth control:** the negative fraction is at most truth + 1e-4. ALK:DIC-band and carbonate-closure fractions are at most 0.01 below the truth's. DIC and ALK inventory drift is within 0.1% at 12 months and 0.5% at the end of the free run.
> - Every rule must hold under G12, G6, G24 and REV12.
> - **STOP** (closes the direction, including any diffusion variant): the regression stage is not above the best free null on 3 or more counted fields at lead 1 or in the diagnostic, or the result passes at one split only.
> - Band sensitivity: ±0.05 on each threshold, and 90%/99% CIs. A verdict that flips is reported as THRESHOLD_EDGE, not as a result.
>
> **6. Void conditions.** The oracle self-test must pass. The year-shuffled self-test must fail. The nulls must be bitwise identical between the discovery and replication jobs. If any of these fails, no conclusion is drawn.
>
> **7. Replication.**
> - Discovery is job A (G12, seeds 0-4).
> - Replication is job B, a separate sbatch submitted only after A's gate verdict and map row are committed. It uses fresh seeds 100-104 and runs all four splits, each with its own nulls.
> - Nothing is a result until B passes on its own numbers. Splitting one job in halves is not replication.
>
> **8. Reported regardless of outcome:** every null, every field, both spaces, every split, every lead, physics with the truth control, the self-tests, the test-reuse count, and speed. The ECCO-Darwin reference is marked UNKNOWN until a collaborator supplies it, and no speedup is claimed without both it and a passing H*.
>
> **9. Not in this submission:** observational validation (#163); depth below 100 m; any test-set tuning.

## 10. Upstream pins (read today)
- **physicsnemo** main `536553acf5b03b68ec7283975ba7276d60056a36` (2026-09-30T14:15Z), `examples/weather/regional_weather_diffusion/README.md`:
  - CorrDiff = conditions `["background"]`; StormCast = `["state","background"]`.
  - An optional per-sample `"mask"` (1,H,W) acts as a per-pixel loss weight.
  - PyTorch ≥ 2.10 is required.
  - `inference.py` supports only ERA5-HRRR and recommends earth2studio for custom data.
- **earth2studio** main `2067756d489ad9195cf9e1ed52e074a4f8588ca4` (2026-09-30T17:41Z):
  - `statistics/{crps.py (fair), rmse.py (spread_skill_ratio), lsd.py, rank.py}`.
  - `models/dx/corrdiff.py` (`inference_mode`, `number_of_samples`, `load_model` / `metadata.json`).
- **Papers**, read through a WebFetch summary, not verbatim:
  - arXiv 2309.15214v4: 32-member CRPS; baselines are ERA5 interpolation, RF and the UNet; train 2018-2020, test 2021 (205 random times), no gap; spectra and PDFs; ensembles under-dispersive.
  - arXiv 2408.10958: RMSE, FSS, SER = std/RMSE, PSD relative error < 20%; baselines are HRRR and regression-only; leads 1-12 h; 5 members; train 2018-07..2021-12, val 2022, test spring 2024.
