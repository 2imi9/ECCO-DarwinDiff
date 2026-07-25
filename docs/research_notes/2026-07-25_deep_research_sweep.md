# Overnight deep-research report — ECCO-DarwinDiff

**Date:** 2026-07-25 · **Checkout:** `C:/Users/Frank/OneDrive/Desktop/Github/ecco-darwindiff`, branch `feat/research-scripts-and-loaders` (HEAD `f665c14`) · **Scope:** four independent research lines (identifiability literature, emulator field position, code-bug hunt, statistical rigor), four of the five lines passed through a grounded verify pass. **The reproducibility line (§5) did NOT** — its verifier died on an API stall, so treat §5 as unverified leads rather than confirmed findings. Three findings were amended or partly refuted by the verifier and are marked as such. Blocker B4 was **corrected after the sweep** by re-grading the raw records; see the verification note at the end. Nothing in `docs/paper/**` was modified; no git state was changed.

**Read this first:** two of the five blockers are *unforced errors* — a fabricated quotation and a statistic that was never defined — and both are fixable in under an hour. The scientific results survive every finding in this report. What does not survive is a set of specific numbers and one literature claim.

---

## 1. Blockers — fix before this goes to collaborators

Ordered by how badly each one damages credibility if a reader finds it first.

### B1. A fabricated quotation is sitting in the Kriest 2017 citation

The phrase attributed to Kriest et al. 2017 — that constraining zooplankton mortality against dissolved inorganic tracers is "difficult, if not impossible" — **is not in the paper**. The full open-access PDF (DOI 10.5194/gmd-10-127-2017, all 28 pages extracted in-session from `gmd.copernicus.org/articles/10/127/2017/gmd-10-127-2017.pdf`) contains **zero** occurrences of "impossible" and zero occurrences of the attributed phrase. All 48 occurrences of "zooplankton" were inspected.

What Kriest actually supports: parameters acting on large space/time scales are determined earliest and with the least spread, while surface-biology parameters are hardest; and the search for optimum zooplankton parameters benefits from good prior bounds. That is a materially weaker and differently-directed claim.

**Action:** delete the quotation. Cite Kriest only for the verified large-scale-versus-surface-biology result. This is a five-minute fix and it is the single highest-priority item in this report — a referee who opens Kriest and does not find the sentence will discount everything else in the literature review.

### B2. `rel_span` is not a calibrated identifiability threshold, and it depends on a modelling choice

Every FLAT / SHALLOW / CURVED verdict in the paper comes from `rel_span = (max_grid_loss − best)/best` with hardcoded cut points 0.05 and 0.5 (`scripts/identifiability_sloppiness.py`, working copy `:814` formula, `:836`/`:838` thresholds; committed HEAD version `:468`, `:490-495`). Two independent defects:

- **(a) It is bounds-dependent.** The profile grid is `torch.logspace(log10(lo), log10(hi))` over `PARAM_BOUNDS` (`:769`, HEAD `:423-424`). Widening the *physical prior* mechanically raises `rel_span` and can flip FLAT to CURVED with no new data. The repo already documents this fragility: `docs/findings/iron_scav_rat_profile.json:112-117` reports the flat-band multiple as 25× / 32× / 100× at thresholds 0.01 / 0.02 / 0.05 and notes the specific multiple is not threshold-independent.
- **(b) It has no distributional meaning.** Raue's classification is a *threshold-crossing* test against Δ_α = χ²(α, df) on a calibrated likelihood. Our objective is a weighted MSE with AOI weights plus ratio and positivity terms — not a likelihood with a specified error model — so no χ² quantile is available. Schartau et al. 2017 (DOI 10.5194/bg-14-1647-2017, Sect. 5) further warn that even a proper χ² threshold is optimistic in marine ecosystem models unless effective degrees of freedom and error correlations are right.

**Minimum viable fix:** state an explicit error model, report Δ_α-crossing and the resulting CI endpoints (finite / −∞ / +∞) per parameter, and demote `rel_span` to a descriptive statistic. Do not delete the diagnostic — see §3, where the profile itself is an asset.

### B3. Every CI and p-value is over random seeds on one dataset, and the paper never says so

All 21 Wilson intervals and all 5 Fisher tests treat the **random seed** as the unit of replication. Seeds 0–49 run on one fixed geo1 configuration: one 23-yr climatology, one GEOTRACES IDP2025 snapshot, one Daniels anchor, three fixed AOIs (`docs/paper/main.tex:1157-1180`, `:1182-1187`). The intervals therefore estimate *the probability that a random initialization of this optimizer lands in-band on this dataset* — a statement about optimizer reliability, not identifiability or generalization. **The data-level replication count is 1.**

A negative grep across `main.tex` finds no acknowledgment of this anywhere; the only near-hits are "across-seed spread" at `:564` and `:574`, which make a different point. Meanwhile `main.tex:591-593` presents the n=10 → n=50 upgrade as "a far tighter statement of the same effect." It tightens a nuisance quantity while the scientific uncertainty stays unquantified and unmentioned. A referee will read this as precision theatre.

**Fix (cheap, changes no number):** state once in Methods that seeds are the replication unit and that all intervals are conditional on a single data realization; then move the generalization argument to the AOI decomposition already at `main.tex:637-645`, which is the only place real data-level variation appears.

### B4. The 0/50 global-scalar arm is deterministic, so the binomial framing does not apply

> **⚠️ CORRECTED 2026-07-25 after the sweep, by grading the raw records.** The original wording
> below claimed the effective sample size is 1. That is **wrong**: `n50e2k_global_scalar` gives
> **50 distinct values** (49 for `scav_rat`), so these are 50 genuine separate optimizations. The
> conclusion survives in a stronger form — `scav_rat` converges to 3.55219e-07 with sd 2.03e-10
> against Carroll's 6.025e-07, about **1200 standard deviations** away. The arm does not fail 0/50
> by chance; it converges deterministically to one wrong optimum. Drop the Wilson interval and
> state the deterministic fact plus the sigma distance. Do **not** repeat "effective n is 1".

The flagship comparison is 25/50 versus 0/50, reported with Wilson [0.00, 0.07] (`main.tex:526-527`) and a rule-of-three bound of 0.30 at n=10 (`main.tex:678-679`). But the paper *states* the global-scalar arm converges to the same point every seed: "coefficient of variation CV~0% for all three trio parameters" (`main.tex:565-570`) and "mean n_cal=4.00, sd 0" (`main.tex:611-614`).

A deterministic estimator replicated 50 times supplies **one** independent Bernoulli trial, not 50. There is no sampling variation for the binomial machinery to describe, so [0.00, 0.07] is not a defensible interval and the disjoint-intervals statement inherits the defect. A reader who puts `:567` and `:527` side by side catches this in one pass.

**The repair strengthens the paper.** Drop the binomial framing for the global arm and state the deterministic fact already in hand: the single global optimum sits 41% (`scav_rat`) and 117% (`R_PICPOC`) outside the band (`main.tex:569`). A reproducibly, deterministically out-of-band point estimate is a *cleaner* argument than a Wilson interval, and it is immune to B3.

### B5. "Nobody else reports a seasonal-AR(1)-class baseline" is false

Smith et al. 2026 (DOI 10.3389/fmars.2026.1760162), a 3D U-Net emulator of NEMO-BAMHBI in the Black Sea, benchmarks against four nulls: pure persistence, anomaly persistence, **damped anomaly persistence** ("applies exponential decay based on decorrelation timescale"), and climatology. Damped anomaly persistence is the same algebraic family as our `ar1_seasonal_percell`, which is exactly `clim_month(t+1) + φ_s·(x_t − clim_month(t))` at `scripts/analysis/emulator_baselines_v2.py:43` (docstring) and `:374` (`A1s = S + phi_seas[None] * (P - Ssrc)`).

Do not claim novelty for the baseline; it is refutable with one citation.

**But the counterexample is weaker than it looks, and the nuance cuts toward us.** Smith et al. beat the persistence family only "after the first two forecast days." At the shortest lead their null is competitive — and one step is precisely our entire evaluation regime. Cite them as the positive control at multi-step leads while noting their short-lead behavior matches ours.

Two corrections to the original draft of this finding: the 41% chlorophyll / 58.8% phosphate RMSE improvements are relative to the **climatology** baseline, not the persistence family; and the sea-ice benchmark paper is **Niraula & Goessling** 2021, not "Niraula & Sigmond" (title and DOI 10.1029/2021JC017784 are correct).

---

## 2. Bugs found

Eight defects, all verified independently by re-running the relevant code or re-deriving the numbers from the on-disk data. Each entry gives the wrong-but-plausible output it produces.

### 2.1 `_season_bin` merges and splits calendar months — *the seasonal baselines the Track-2 deflation is scored against are mis-binned*

**`scripts/analysis/emulator_baselines_v2.py:104-109`** (v1 identical at `:123-127`)

`_season_bin` maps days-since-ref to a month index by `floor((t % 365.25) / 30.4375)`. Its docstring asserts grouping "is internally consistent: identical true calendar month -> identical bin." **That is false on the exact time axis these scripts consume.**

Re-derived independently from disk (`D:\ecco_darwin_v5\output\monthly\Chl1`, 289 `.data` files, `times_days = iter*1200/86400` → 31, 60, 91, … end-of-month stamps):

| | |
|---|---|
| Bin counts | `[23, 47, 24, 23, 25, 24, 23, 5, 36, 13, 40, 6]` |
| Bin 1 | Jan (21) + Feb (26) = **47 members** — two calendar months merged |
| Bins 7, 11 | **5** and **6** members |
| Split across two bins | Aug, Sep, Oct, Nov (leap-cycle dependent) |
| Under a pre-2026-07-19 cube (Δt=900) | all 12 months scatter across up to 4 bins each |

These bins build `clim_seas` (`:139-141`, with an undisclosed fallback to the annual climatology for an empty bin), which defines `seasonal_clim`, `anomaly_persist` and `ar1_seasonal_percell` (`:369-374`), and key the `by_init_month` breakdown (`:501-507`).

**Wrong-but-plausible output:** the published **−0.161 ± 0.015** deficit versus seasonal AR(1) is measured against a corrupted baseline. A Jan+Feb-blended climatology and two 5-member bins make the seasonal predictors *weaker* than they should be, so **the error direction is conservative — correct binning makes the emulator's deficit larger, not smaller.** The negative result survives; the specific number does not. The `by_init_month` breakdown is invalidated outright. The docstring's consistency claim is a referee-visible false statement.

**Note for STATUS.md:** `STATUS.md:91` currently says the horizon is "+0.240 vs a **correctly-binned** seasonal climatology." Given `_season_bin` is unrepaired at `:104-109`, that adjective is only true of the Δt=1200 calendar fix, not of the month binning. Either qualify it or fix the binner first.

### 2.2 GEOTRACES profile comparison fabricates the surface iron value for 538 of 1053 stations

**`scripts/analysis/v05_geotraces_iron_profile_fidelity.py:107-123`**

`interp_to_axis` calls `np.interp`, which clamps outside the data range, then NaNs **only** the deep side (`out[targets > dmax] = np.nan`) while leaving `allow_shallow_clamp=True` by default. Every station is admitted with a shallowest good sample as deep as 99 m (`SURFACE_MAX_M = 100.0` at `:63`), so the 0 m and 50 m entries of `COMMON_DEPTHS` (`:67`) are filled by copying that deep value *upward*. Both obs and model call it with the default (`:237-238`).

Re-ran the script's own filter (QC ∈ {49,50} / n≥5 / dmax>500 / dmin<100) against `D:\geotraces\GEOTRACES_IDP2025_Seawater.nc` and reproduced all four counts exactly:

| Qualifying stations | 0 m clamped from >10 m | from >25 m | both 0 m and 50 m fabricated (dmin >50 m) |
|---|---|---|---|
| 1053 | **538** | 103 | 30 |

Dissolved iron has a strong surface minimum, so the clamp **systematically inflates** the fabricated surface value. No clamp counter is emitted anywhere in the script's output.

**Wrong-but-plausible output:** the surface depth-band offset ratio, the surface-to-deep gradient statistic `obs_grad = xo[-1]/xo[0]` (`:259`), and both profile correlations are computed partly from invented data for a **majority** of stations, with nothing recording it. Any claim of the form "v05 iron is N× off at the surface" from this script is unsafe until re-run with `allow_shallow_clamp=False` plus a clamped-station count.

### 2.3 The canonical grader silently drops a corrupt seed and disables its own integrity gate

**`scripts/grade_recovery.py:123-126` and `:227-231`**

`_load_seeds` wraps `json.loads` in a bare `except Exception: continue`. The same corrupt file makes `verify_run.verify_config_dir` raise, and grade_recovery catches that too (`except Exception` → `gate_available=False`). The one artifact that should force a hard MALFORMED verdict instead **removes the integrity gate** while the science table still prints.

Reproduced end to end on real data: `D:/runs/bcr_w4_20260520_2302/a_nsteps_1000` holds 7 seed JSONs, one truncated at char 1559 (`json.JSONDecodeError: Expecting value: line 71 column 17`). Running the grader prints a complete, quotable table:

```
[a_nsteps_1000]  n=6/?   gate: unavailable
alpfe 2/6 · diatomgraz 4/6 · rho(alpfe,scav_rat)=-0.80  [ridge INTACT: scav_rat unconstrained]
```

**Wrong-but-plausible output:** a fully formed per-AOI recovery table with medians and a ridge verdict, computed over a silently reduced seed set. `EXIT=2` does fire, so the verified-experiment discipline holds — but `n=6/?` is easy to read past, and a tool whose purpose is anti-hallucination should refuse to print a tally it could not compute completely.

**Secondary:** `verify_run.py:234` builds config results in a list comprehension, so one bad file aborts verification of every sibling config dir.

### 2.4 `percell_crlb_map` fallback rebuilds lat/lon with the exact half-cell offset that commit `ac8af55` fixed

**`scripts/analysis/percell_crlb_map.py:188-198`**

A bare `except Exception` around the target-cache load falls back to `lat = aoi.lat_min + (arange(H)+0.5)*(lat_max−lat_min)/H`. The repo convention is integer-degree centers spanning lat_min..lat_max **inclusive** (`src/darwindiff/daniels_loader.py:315-321`; `src/darwindiff/held_out_obs.py:626-644` explicitly rejects "integer+0.5 centers" as misregistering every target).

Computed for eqpac (lat −5..15, H=21): the fallback produces 21 cells of **0.95238°** starting at **−4.5238** — every axis label shifted by up to half a cell and stretched by 4.8%. The guard at `:192` checks axis *length* only, so it passes.

The strongest corroboration is the repo's own history: commit `ac8af5579fdb` describes the identical defect in `compare_v05_modis_aoi.py` — "bins 0.952 deg wide instead of the true 1.0 deg cell, shifted by up to half a cell." It was fixed there and reintroduced here as an error path.

**Wrong-but-plausible output:** on the failure path the identifiability map is generated and saved (`:303-320`) with mislabeled geography, looking entirely normal; a single console line is the only signal. Any statement about *where* information sits ("the informative cells are 10–15N") read off that npz is off by half a cell plus a 5% stretch. The guard should raise, not fabricate.

### 2.5 Two point-binners admit out-of-AOI samples one full cell past the edge

**`src/darwindiff/geotraces_loader.py:302-313`** and **`src/darwindiff/modis_pic_loader.py:219-222`**

`bin_to_grid` computes `in_bounds` as `lat_idx <= len(lat_centers)` (should be `<`), then clamps with `np.minimum(..., n-1)`. Since `lat_idx = floor(lat − lat_min)`, a sample anywhere in [lat_max, lat_max+1) yields `lat_idx = n`, passes the bounds test, and is folded into the top row. The adjacent comment (`:302-307`) states the check exists precisely so that "we don't accidentally fold out-of-AOI samples into the top bin (matters if caller skips subset_aoi_geotraces)" — **the case it explicitly anticipates is the case it fails.** `modis_pic_loader` has the identical off-by-one (`lat_bin < n_lat + 1` then `np.minimum`).

Demonstrated numerically for eqpac: GEOTRACES admits lat=15.5 and 15.99 into the top row; MODIS admits lat=16.0 and 16.4. `daniels_loader.py:287-302` gets this right and documents why.

**Wrong-but-plausible output:** silently contaminated edge rows/columns — which are where the AOI's least-sampled cells already are. **Evidence of actual harm is nil:** the standard pipelines (`dfe_aoi_1deg_grid`, `build_aoi_climatology`) subset first, so I found no reported number affected. This is a loaded gun on a public function whose docstring invites the failing call pattern.

Two adjacent defects in `modis_pic_loader`: `subset_aoi_modis` clips source pixels to [lat_min, lat_max] (`:161`) while `bin_to_1deg` builds bins spanning [lat_min−0.5, lat_max+0.5], so edge cells are averaged from roughly half their pixel footprint with no coverage flag; and the docstring at `:172` ("integer + 0.5°") contradicts the code and comment at `:203-207` (integer centers).

### 2.6 Xu-Weber regrid keeps cells diluted by land NaNs replaced with zero

**`src/darwindiff/xu_weber_loader.py:88-104`**

Land NaNs in the 2° soluble-Al field become `0.0` before `RegularGridInterpolator` (`:91`, `fill_value=0.0` at `:93-95`), with a parallel 0/1 coverage field thresholded at `covg > 0.5` (`:104`). The docstring (`:89`) says this re-masks cells that "interpolate from all-NaN neighbourhoods," but a 0.5 threshold only rejects *minority*-covered cells: a target at coverage 0.64 retains a value in which 36% of the bilinear weight came from a land cell contributing zero.

Re-ran the regrid from `data/xu_weber_2021`: source NaN fraction 11.4%; natlsubpolar keeps 491 cells of which **27 have coverage below 1.0**, the lowest at 0.64. midatl/npac is worse (65 partial, min 0.58); npsg has 42 partial.

**Wrong-but-plausible output:** ~27 coastal North Atlantic cells reporting soluble-Fe deposition biased **low by up to ~36%**, indistinguishable from clean cells in the returned array. Since this loader is the intended *source* anchor for the `alpfe` leg of the two-anchor inversion, a low-biased coastal deposition pushes `alpfe` high there.

**Currently latent** — `git grep xu_weber` returns only the loader and two docstring mentions in `black2020_fe_flux_loader.py:17,81`; no executable importer. Cheap to fix before it carries a number.

### 2.7 Kriging LOO-CV leaks the held-out point, substitutes a mean on singular solves, and reports a boundary-clamped length as a fit

**`scripts/analysis/kriging_field_reconstruction.py`** — three related issues:

1. `:148-153` — `except np.linalg.LinAlgError: pred[k] = float(vals[idx].mean())`. The prediction silently becomes the plain mean of the neighbours, **with no counter**, so a run where many solves failed is indistinguishable from a clean one.
2. `:298-304` — `vfit_obs` is fit on the full pooled set *including point k*, then used to krige point k. The LOO is not leave-one-out, which biases the kriging R² **upward**.
3. `:96` / `:108-114` — `fit_exponential_variogram` grid-searches L over `np.geomspace(20.0, 8000.0, 120)` and returns the best-r² value **with no interiority check**; a boundary-saturated value is returned as a fitted correlation length. `L_model` at `:270` comes from the same fitter, and the verdict branches on it at `:326-337`. Two hardcoded magic fallbacks of `L = 1000.0` km sit at `:303` and `:315`.

**Wrong-but-plausible output:** the go/no-go verdict for the spatial-prior route (issue #163) can flip between (b)-DEAD and (c)-MARGINAL on an artifact of the search range, and the upward-biased R² is conservative only while the verdict stays DEAD.

**Evidence is thin on impact:** no kriging result JSON exists under `docs/` on any branch (only a passing mention in `docs/research_notes/2026-07-08_overnight_summary.md`), so I cannot show the boundary case ever fired. This is a code-level finding, confidence medium.

### 2.8 `emulator_baselines_v2` silently substitutes hardcoded config defaults off-cluster

**`scripts/analysis/emulator_baselines_v2.py:281, 294-299`**

`cfg = json.load(open(args.emu_json))["config"] if Path(args.emu_json).is_file() else {}` — a missing config yields `{}` with **no warning**, after which `val_frac`, `adjacency_tol`, `residual` and `log_tracers` come from hardcoded literals. The default `--emu-json` is `/scratch/qi_zim_neu/depth/depth_chl_emulator.json`, a cluster path, so **off-cluster the fallback always fires.** The `log_tracers` fallback is `["Chl1"]`; `emulator_poc.py`'s own `--log-tracers` default is `Chl1,Chl2,Chl3,Chl4,Chl5,PIC,POC,FeT` (`:264-266`).

**The stated consequence was falsified, and this correction matters.** `docs/findings/2026-07-23_emulator_multiseed.md:13` (commit `6b10391`) records the training flags as `--log-transform --log-tracers Chl1`, and `emulator_poc.py:1414-1418` dumps the *resolved* stem list — so the trained config was `log_tracers=['Chl1']` and the fallback **matches it**. PIC/POC/FeT/Chl2-5 were never log-transformed. The published multiseed matrix is unaffected. `val_frac 0.3` and `adjacency_tol 1.6` also happen to match, so the split survives by luck.

**Wrong-but-plausible output (forward-looking):** anyone who retrains at `emulator_poc.py`'s own default (8 log tracers) and then runs the baseline script off-cluster gets PIC/POC/FeT/Chl2-5 residuals silently computed in linear space and z-normalized over lognormal tails — producing a complete, plausible-looking matrix either way. The script should hard-fail when the emu-json is unreadable; the config is a property of the trained model, not a preference.

---

## 3. Where we stand against the literature

### 3.1 Is the identifiability framing defensible? — Yes on substance, no on citation coverage

**The framing is right by the field's own standard.** Schartau et al. 2017 Sect. 6.1 (DOI 10.5194/bg-14-1647-2017) is unambiguous: parameter optimizations "can often improve the fit of a model by selecting unrepresentative parameter values that serve only to compensate for misfits ... It is therefore essential to check whether the resultant 'optimized' model is giving the right answer for the correct reasons." It cites Fennel 2001, Friedrichs 2006 and Ward 2010 as cases where optimization *decreased* predictive skill relative to off-the-peg priors, and Xiao & Friedrichs 2014b as achieving misfit reduction "through the adoption of extremely unrealistic parameter estimates."

**Our negative held-out R² and "consistency check, not discovery" framing are exactly the correct posture.** Citing Schartau converts an apparent weakness into demonstrated methodological literacy.

**The counterweight, and it is sharp.** Schartau Sect. 7.3 applies the same test to spatially-varying-parameter methods specifically: "However, in the absence of cross-validation experiments, their potential for improving the predictive skill of the models is not well evaluated at present." That is almost verbatim the objection our per-cell result invites. Quote it and answer it rather than wait for a referee to. The matched global-scalar control is the partial answer already in hand.

**The citation gap is severe.** A grep over `main.tex` finds `transtrum`, `raue`, `gutenkunst`, `tagliabue`, `somes` — and **zero** hits for `schartau`, `ward`, `loptien`/`loeptien`, `kriest`, `mamnun`, `beven`, or `chis`. The four that matter most:

| Missing | DOI | Why it matters |
|---|---|---|
| Schartau et al. 2017 | 10.5194/bg-14-1647-2017 | The 55-page Biogeosciences review of parameter identification in marine planktonic models. Contains the profile-likelihood section, the collinearity framework, and the cross-validation standard we currently fail. |
| Ward, Friedrichs, Anderson & Oschlies 2010 | 10.1016/j.jmarsys.2009.12.005 | The canonical "underdetermination in marine biogeochemical models" paper, 151 citations. |
| **Löptien & Dietze 2017** | 10.1002/2017GB005690 | **The direct comparator.** Same design (synthetic twin recovery), same question, opposite-polarity conclusion: for typical models and metrics "no meaningful 'best' unique parameter set exists," and "very different parameter sets" are equally consistent with synthetic historical observations. |
| Kriest et al. 2017 | 10.5194/gmd-10-127-2017 | Free supporting evidence for the growth-pair exclusion — **verified half only**, see B1. |

Not engaging Löptien & Dietze is the most likely single cause of a desk-level "the authors are unaware of the relevant literature" review.

**Three further positioning items:**

- **Sloppiness decades are contested as identifiability evidence.** We quote per-AOI iron sloppiness of 5.19 / 5.99 / 4.99 decades (`docs/findings/2026-07-24_overnight_session_summary.md:36`) while citing only the pro-sloppiness side (Gutenkunst, Transtrum). Chis, Villaverde, Banga & Balsa-Canto 2016 — literally titled *"Sloppy models can be identifiable"* (DOI 10.1016/j.mbs.2016.10.009) — argue sloppiness is not equivalent to lack of identifiability, is influenced by parameterization and noise rather than being a pure model-structure property, and that "identifiability criteria are better than sloppiness" for experimental design. White et al. 2016 (DOI 10.1371/journal.pcbi.1005227) concur. **Any sentence inferring non-identifiability *from* the decade spread should instead infer it from the profile or the posterior correlation.** State the log-parameterization explicitly so the spread is at least reproducible.
- **"Equifinality" appears 8 times with zero Beven citations** (`main.tex:396, 402, 562, 802, 848, 849, 866, 1184`; the finding originally said 7 — the case-insensitive count is 8, conclusion unchanged). The term originates with Beven & Freer 2001 (10.1016/S0022-1694(01)00421-8) and Beven 2006 (10.1016/j.jhydrol.2005.07.007). Beven's behavioural-set framing is a natural ally for our multi-seed in-band-count grading, which is closer to a behavioural-set criterion than a point estimate — the citation makes the n=50 seed ensemble look principled rather than ad hoc.
- **Spatially varying BGC parameters have direct 2025 prior art.** Mamnun, Völker, Vrekoussis & Nerger 2025 (JGR-Oceans, 10.1029/2025JC022752) estimated nine REcoM2 parameters as spatially *and* temporally varying fields via EnKF assimilation of satellite chlorophyll-a, giving "a 26% reduction in root mean square error ... compared to simulations with uniform parameters." Earlier hierarchical-Bayes precedent: Fiechter et al. 2013 (10.1016/j.ecolmodel.2013.03.003) and Leeds et al. 2013 (10.1002/env.2187), both reviewed in Schartau Sect. 7.3. **None are cited.** Our result *is* different in kind — theirs is fit improvement against data, ours is recovery against a known target with a matched global-scalar control — and that difference is the paper's strongest per-cell argument. But an uncited 2025 global-model paper showing spatially varying beats uniform is exactly the citation a referee produces to deflate a novelty claim.

**One unused asset.** Schartau Sect. 5.2: "the evaluation of a profile likelihood is impracticable for most marine ecosystem model applications, because of the associated computational costs," having been applied only "where fast evaluations of J(θ) were possible (e.g. Brun et al., 2001; Raue et al., 2009, 2011)." Our differentiable 0-D surrogate makes exactly those evaluations possible, and our implementation is a *genuine* profile — the profiled parameter is fixed on the grid and the other five are re-optimised (`identifiability_sloppiness.py:439-440`, HEAD), with convergence and bracketing guards (`:470-517`). **This is the cleanest defensible methodological novelty in Track 1 and it is not currently framed that way.** It also reframes the surrogate gap from a liability into the price of the diagnostic. Worth one sentence in the intro and one in the discussion.

**Two internal problems the literature makes worse:**

- **`alpfe` and `diatomgraz` profiles are one-sided by construction.** From `src/darwindiff/carroll6.py` PARAMS: Carroll's target sits at **log-position 0.98** of the `alpfe` box (0.05–1.0, target 0.92831) and **0.94** of the `diatomgraz` box (0.05–1.0, target 0.83003). Because the profile grid spans exactly `PARAM_BOUNDS`, the upper arm has almost no range — and Raue's classification is explicitly *two-sided*. The bracketing guard only fires when the profile *minimum* lands on an endpoint index, so it does not catch this. The other four are far less truncated (scav_rat 0.65, Smallgrow 0.63, Biggrow 0.49, R_PICPOC 0.37). **"diatomgraz FLAT → structural non-identifiability" is measured on a grid where 94% of the log-range lies below the true value**, so any flatness is dominated by the below-optimum arm. This is also the mechanism for the standing internal warning that `alpfe` reads FLAT yet recovers 9–10/10.
- **Two live, mutually inconsistent `scav_rat` verdicts are in the repo; the paper quotes one.** `docs/findings/2026-07-07_overnight_h200_identifiability_profiles.md:19-23` gives `scav_rat` rel_span 0.196 and `alpfe` 0.207, both SHALLOW = weak practical non-identifiability. `docs/findings/2026-07-23_overnight_recovery_sweep_groupA.md:31` gives per-AOI spans 3.69 / 1.30 / 1.12, all CURVED = constrained (jobs 189403/189870). Under our own thresholds these are opposite; under Raue they are different identifiability *classes*. Both documents are current, not archived. `main.tex:576-580` cites only the CURVED result. The runs differ legitimately (shared-theta global vs per-AOI), so they are reconcilable — but the paper must say which lens it reports and why, or retire the older number explicitly.

### 3.2 Is the emulator negative result publishable? — Yes, but only as a protocol contribution

**A pure "our emulator has no skill" note has no venue precedent in ocean BGC.** The accepted vehicles are benchmarks and limitations papers:

- **ChaosBench** (NeurIPS 2024 D&B, Oral; arXiv:2402.00712): "we find methods originally developed for weather-scale applications fail on S2S task: their performance simply collapse to an unskilled climatology."
- **Bonavita 2024** (GRL 51, e2023GL107377): ML forecasts "do not have the fidelity and physical consistency of physics-based models," with energy spectra notably different from the training reanalysis. Note the post-processing framing is *softer* than commonly paraphrased.
- The closest published BGC negative is a **sub-result inside a positive paper**: Skakala et al. 2026 (arXiv:2606.27168) state "the 1D CNN emulator performance in 10-day forecasting is typically worse than persistence across the full 10-day forecast period."

**The narrow place our contribution is real — and it is broader than we thought.** Every flagship ocean/atmosphere emulator was checked against primary full text, and **none reports a simple statistical null**:

| Emulator | Baselines actually reported | Persistence / climatology null? |
|---|---|---|
| Samudra (arXiv:2412.03795v1) | — | **No.** Climatology appears only in metric definitions (Niño 3.4 anomalies), not as a forecast comparison |
| Samudra 2 (arXiv:2606.02610) | original Samudra, GFDL OM4 regridded | **No** |
| SamudrACE (arXiv:2509.12490v2) | CM4 reference, uncoupled ACE2, uncoupled Samudra | **No** |
| ACE2 (arXiv:2411.11268v1) | ERA5, SHiELD, GraphCast/IFS, prior ACE-climSST | **No** |
| OceanNet (10.5194/os-21-1065-2025) | persistence, ROMS, earlier DLOP | Yes |
| Bire et al. (10.1029/2023MS004137) | "more accurate than using climatology or persistence on short-term forecasts" | Yes |

And the amendment that **strengthens** this: the assumption that BGC emulators do report a null is only half true. Skakala et al. 2023 (10.3389/fmars.2023.1058837) compares against **neither**, and Martinez Balbontin et al. 2026 (10.5194/bg-23-2601-2026) — the closest monthly global-chlorophyll analogue — compares only against GlobColour observations and the BIO4 PISCES product, **with no persistence or climatology baseline anywhere**.

**So the defensible claim is baseline *hygiene*, not baseline *invention*, and it covers 4 of 4 flagship physical emulators plus 2 of 4 BGC emulators.** Ship `emulator_baselines_v2.py` as a protocol contribution — the AR(1) null, block-bootstrap CIs, multi-seed control, plus the code. That framing is the one least exposed to the Smith et al. counterexample.

**Three things that must be stated alongside the deflation, because a referee will raise them:**

1. **Zero forcing inputs is the strongest alternative explanation for the null.** Confirmed exactly: the multiseed flag list contains no `--forcing`, and `scripts/emulator_poc.py:1211` gates forcing on `_use_forc = bool(forcings) and "forcing" in z.files and z["forcing"].ndim == 4`, with `--forcing` declared but unused at `:131` ("Empty = pure prognostic"). Meanwhile Samudra and Samudra 2 take tauuo/tauvo/hfds; Skakala 2026 takes PAR, wind components, precipitation, surface heat flux, SST, SSS, MLD; Smith 2026 takes T, S, SSH, wind speed, MLD, three velocity components, shortwave, PAR and cyclic day-of-year; Martinez Balbontin takes MLD, SSH, SST, SSS. Our own repo already says it: "The fix is an input (dust/PAR forcing channels), not a bigger network" (`docs/findings/2026-07-23_emulator_baseline_matrix.md:90`). **A prognostic-only operator losing to seasonal AR(1) is close to a foregone conclusion, because AR(1) implicitly encodes the seasonal forcing cycle the emulator cannot see.** The honest headline is *"a prognostic-only monthly BGC operator adds nothing over per-cell seasonal AR(1),"* not *"neural BGC emulation has a one-step ceiling."* (Uniqueness restricted to the five emulators whose input lists were checked — OceanNet's SSH-to-SSH setup and Bire's idealized double gyre were not.)
2. **The sample-size confound is real but the headline absolute is refuted.** Our deflation run trained on 18 input-target pairs / 34 train months. Verified comparanda: Samudra "2800 and 140 data samples"; SamudrACE 155 train years at 5-day cadence; ACE2 ~1e5 6-hourly samples; Skakala 2026 12 years daily; Skakala 2023 20 years daily; OceanNet 1993–2018 5-day. **But the claim "no comparable emulator is trained on fewer than ~4,000 samples" is FALSE.** Martinez Balbontin et al. 2026 — the single closest analogue in the set (global surface chlorophyll, monthly step, seasonal leads) — runs its primary workflow at **monthly** resolution over Jan 1998–May 2017, i.e. **~234 training timesteps**. That is ~13× ours, same order of magnitude, and below the claimed floor. Ship the weakened form ("1–2 orders below the flagship physical emulators and the daily-cadence BGC emulators, roughly one order below the closest monthly BGC analogue") — or better, kill the confound outright via §6 item 6.
3. **"One-step horizon" is not comparable to published horizons.** Samudra steps at 5-day means and rolls out ~8 years (~580 steps). OceanNet is "physically reasonable over at least a 60 d period." Skakala 2026 reports 50–60% RMSE improvement at day 10 on a daily step. Agarwal, Smith, Frolov & Slivinski 2026 (arXiv:2604.18727) adapt GraphCast to ocean-only forecasting at a 24-hour step, skillful to 10–15 days. **Our one step is one month** — roughly six Samudra steps in physical time. Report the horizon in physical time everywhere. "One step" invites the reading that the model dies after five days, which is harsher than the evidence; it must equally not read as competitive with a 60-day OceanNet horizon. (`STATUS.md:91`; note the finding originally cited `:88` — STATUS.md is uncommitted-modified and line numbers drift.)

### 3.3 Who has done adjacent work — the tracer niche is open, the wider BGC-ML field is not

**Confirmed:** the m2lines publications page lists Samudra (10.1029/2024GL114318) and SamudrACE (10.1029/2025GL119340) as its ocean emulators and contains **zero** entries on biogeochemistry, carbon, chlorophyll, nutrients, oxygen, or marine ecosystems. SamudrACE explicitly defers BGC: its framework "provides a clear pathway toward emulating a complete Earth system by incorporating additional components, such as land and biogeochemical models."

**But outside m2lines, BGC-ML emulation is active and positive-result-dominated:** Skakala 2023 (hypoxia, North Sea, R>0.9 at German Bight); Skakala 2026 (LSTM beats persistence 50–60% at day 10); Smith 2026 (Black Sea, 39–60% RMSE improvement over climatology); Martinez Balbontin 2026 (global seasonal chlorophyll); Zhang, Ito & Bracco 2026 (O2EMU, ERL 21(11), 10.1088/1748-9326/ae6fd3, reduces inter-model spread 70–75% and RMSE 50–60% across 10 CMIP6 ESMs); Ouala & Lachkar 2026 (Neural-BGC, 10.1029/2026GL123123, "often outperforms a tuned NPZD model").

**Keep two statements apart in the manuscript.** The m2lines / physical-emulator ecosystem has no BGC — a real gap. The BGC-ML literature as a whole is not empty, so any claim that BGC emulation is *intrinsically* hard must explain those six rather than ignore them. Four of the six are regional or 1-D, none emulate PIC/calcite or iron, and one (Skakala 2026) is not uniformly positive.

---

## 4. Statistical corrections

Beyond blockers B3 and B4, five mis-specified tests. All arithmetic in the existing paper was re-derived and reproduces exactly — the errors are in *specification*, not computation.

| # | Where | Mis-specified | Correct procedure |
|---|---|---|---|
| 4.1 | `main.tex:1143-1155` | Null table gives **single-draw** hit rates, but the headline metric is per-AOI **≥2-of-3**. `main.tex:1154` instructs the reader to run the wrong test. | Compound to the graded metric: 3p²(1−p)+p³ → alpfe 0.450, scav_rat **0.071**, Smallgrow 0.189, Biggrow 0.087, diatomgraz 0.543, R_PICPOC **0.0015**. Note AOI outcomes are *not* independent within a seed (one network, one fit), so the compounded value is a **bound**. |
| 4.2 | `carroll6.py:538`, `main.tex:232, 882, 1010` | The "chance" null is uniform-over-bounds, matching no procedure run. Parameters map through `lo+(hi−lo)·sigmoid(θ)` from a mid-bounds start. **`diatomgraz` is the only parameter whose initialization (0.525) falls inside its own Cal band [0.498, 1.162]** — so "recovered" and "the optimizer never moved it" are the same event, and the true null is near 1.0, not 0.53. | Run a zero-epoch / untrained control on the same 50 seeds and report that **empirical** rate as the null. |
| 4.3 | `docs/archive/research_notes/2026-06-26_holdtogether_sweep_results.md:25`; inherited at `main.tex:502-512` | "The two effects that clear Bonferroni" — **m is never stated**, and the claim is entirely family-dependent. Flagship p=0.003 → 0.021 at m=7 (survives), **0.084 at m=28 (fails)**, 0.34 at m=112. Iron-weight p=7e-4 → 0.022 at m=32, fails at m=112. Combined with the McNemar correction, the R_PICPOC anchor contrast survives no family larger than ~m=3. | Declare the family explicitly and use **Benjamini–Hochberg**, not Bonferroni — these tests are strongly positively correlated across configs, so Bonferroni is the wrong correction and BH will likely preserve both. Better: lean the anchor claim on **value convergence** (per-AOI means going from scattered 0.006/0.061/0.075 to converged 0.052/0.052/0.048), which is harder to produce by chance than a 3/10→10/10 count and is subject to no multiplicity correction at all. |
| 4.4 | `main.tex:647-661` | The "recoverability gap decomposes into optimization and information" conclusion rests on scav_rat 25/50→41/50 and North Atlantic 20/50→40/50 at doubled epochs — **with no p-value anywhere**. Seed sets are identical (`:1182-1187`), so these are paired contrasts. | **Exact McNemar.** (For scale, the wrong unpaired Fisher values are p=0.0014 and p=8.3e-5, so the effect will survive.) The companion "flat" readings are sound: eqpac 7/50→6/50 and SO 49/50→48/50 both give Fisher p=1.0, correctly called noise. |
| 4.5 | `main.tex:678-679, 686-694, 677-678` | Wilson under-covers at the 0/n and n/n boundaries where most counts live. And the Table 1 caption quotes a rule-of-three bound of **0.30** for the same 0/10 cell whose Wilson upper is given as **0.28** — two bounds for one number, the more honest one presented as an afterthought. Separately, `:677-678` calls disjoint intervals "the interval-form statement of the Fisher result"; they are not equivalent, non-overlap being strictly more conservative (Schenker & Gentleman 2001, 10.1198/000313001317097960). | **Clopper-Pearson or Jeffreys** for boundary cells so one convention covers every row: 0/10 → [0, 0.3085], 10/10 → [0.6915, 1.0]. Drop the equivalence wording. Note also that this is a comparative design with only one margin fixed, so Fisher's double conditioning is conservative and **Barnard's unconditional exact test** is the more powerful correct choice. |

**One further metric defect, not a test.** The ≥2-of-3 metric is called "co-recovery" but **requires no common AOI**. In `scripts/analysis/grade_joint_percell.py:47-57`, each trio parameter independently needs ≥2 of 3 AOIs in band and the joint is the conjunction over parameters — with no requirement that the qualifying pairs overlap. The per-AOI tallies show they systematically differ: `scav_rat`'s ≥2 is carried by SO (49/50) plus eqpac (7/50) or natl (20/50); `R_PICPOC`'s by eqpac (46/50) + natl (50/50) with SO weakest (40/50) (`main.tex:637-641`, `:634`). **A seed can count as a joint hit even if no single AOI recovers all three parameters.** A referee will read "co-recovery" as "jointly identified in the same place," which the metric does not test — and since the paper elsewhere makes exactly the spatial argument, the non-co-located metric undercuts the mechanism it is meant to support. One line in the grader fixes it; reporting both numbers would be more convincing than either alone.

---

## 5. Reproducibility gap

**What an outsider could regenerate today:** the analysis scripts themselves (`grade_recovery.py`, `identifiability_sloppiness.py`, `emulator_baselines_v2.py`, the loaders) are all committed and readable, and the statistical arithmetic in the paper reproduces exactly from the reported counts — all 21 Wilson intervals, all 5 Fisher tests, and all six uniform-null hit rates were re-derived and match.

**What an outsider could not regenerate, concretely:**

1. **The flagship n=50 headline is not re-derivable from the checkout.** `.gitignore:54` excludes `runs/`, and a repo-wide search for `per_aoi_recovered` returns **zero** JSON files. The 25/50 trio number and every per-AOI tally exist only in prose. This also blocks *us* from computing the same-AOI co-recovery number in §4 without pulling raw records off Explorer.
2. **The Track-2 deflation record is branch-local.** `docs/findings/2026-07-23_emulator_multiseed.md` — the sole document applying `ar1_seasonal` and the source of the −0.161 headline — **does not exist on the current working branch.** It lives on commit `6b10391`. `STATUS.md:79` cites it. A collaborator who clones and checks out `feat/research-scripts-and-loaders` gets a STATUS.md pointing at a file that isn't there.
3. **Line anchors are unstable.** `scripts/identifiability_sloppiness.py` is 968 lines in the working copy with `rel_span` at `:814` and thresholds at `:836`/`:838`; the committed HEAD version puts the same code at `:468` and `:490-495`. `STATUS.md` line numbers have drifted from uncommitted edits (the horizon row is `:91`, not `:88`). Re-anchor before quoting anything externally.
4. **Two internal statements of the same uncertainty differ.** `STATUS.md:79` says −0.161 ± **0.015**; the working summary says ± **0.013**. Both are correct: from the four per-seed values (−0.146, −0.150, −0.172, −0.177), mean −0.16125, sample sd (ddof=1) = 0.01552, population sd (ddof=0) = 0.01344. Pick one convention and say which.
5. **Off-cluster reruns silently change configuration.** `emulator_baselines_v2.py:281` defaults `--emu-json` to `/scratch/qi_zim_neu/depth/depth_chl_emulator.json`. Anyone outside AICR gets the hardcoded fallbacks with no warning (§2.8).
6. **Reruns can silently change n.** `grade_recovery.py:123-126` drops unparseable seeds without a message and `:227-231` disables the integrity gate on the same file (§2.3), so two runs of the "canonical grader" on the same directory can print different tables with only `n=6/?` to distinguish them.
7. **Hard data dependencies are local drives.** `D:\ecco_darwin_v5\output\monthly\*`, `D:\geotraces\GEOTRACES_IDP2025_Seawater.nc`, `D:\runs\*`. None are obtainable by a reader. (ECCO-Darwin v5 including the 1° `bin_average` product *is* wget-able from `data.nas.nasa.gov` — worth documenting that path.)
8. **No result artifact exists for `kriging_field_reconstruction.py`** anywhere under `docs/` on any branch, so its go/no-go verdict for issue #163 cannot be audited by anyone, including us.
9. **The Neural-BGC sample counts rest on one session's PDF read.** `docs/findings/2026-07-22_neuralbgc_m2lines_landscape.md:14` asserts ~16.7M dissolved-oxygen and 6.2M nitrate WOD samples. The DOI is real and the qualitative picture is independently confirmed from the Crossref abstract (WOD training, cascaded architecture, O2 and NO3 from physical state, ROMS coupling, Arabian Sea and Canary Current, "often outperforms a tuned NPZD model") — but the full text returned **HTTP 402 on both the DOI and Wiley routes**, reproducing the paywall, and the abstract does not state the counts. The open ESSD companion (10.5194/essd-18-287-2026) does not restate them either.

---

## 6. What to do next, ranked by impact / effort

### Tier 1 — do before anyone outside the project sees the draft (hours, total)

| # | Action | Effort | Impact |
|---|---|---|---|
| 1 | **Delete the fabricated Kriest quotation** (B1); keep only the verified large-scale-vs-surface-biology result | 5 min | Removes the single most damaging item in the draft |
| 2 | **Add one Methods paragraph: seeds are the replication unit; all intervals are conditional on a single data realization** (B3). Move the generalization argument to the existing AOI decomposition at `main.tex:637-645` | 30 min, zero numbers change | Closes a blocker that otherwise reads as precision theatre |
| 3 | **Drop the binomial framing for the 0/50 global arm** (B4); replace with the deterministic fact already at `main.tex:569` — the single global optimum sits 41% and 117% outside band | 30 min | Removes a fake denominator *and* produces a stronger argument immune to #2 |
| 4 | **Restate the null table on the ≥2-of-3 metric actually graded** (§4.1). Arithmetic already done. | 1 h | Corrects a wrong instruction to the reader, and the error runs in our favour: R_PICPOC's null drops 15× to 0.0015, joint-trio null ~4e-5 |
| 5 | **Report the horizon in physical time (one month) everywhere** (§3.2 item 3) | 15 min | Prevents both the harsh misreading and the flattering one |
| 6 | **Say which `scav_rat` profile lens the paper reports, or retire the 2026-07-07 SHALLOW number** (§3.1) | 30 min | Removes a contradiction a co-author will find in the supplementary record |

### Tier 2 — the two experiments that change what we can claim (a day each)

| # | Action | Effort | Impact |
|---|---|---|---|
| 7 | **Score the global 156-month config against the AR(1) null.** The deflation exists only for the 48-month eqpac depth run (18 pairs, Nval=8, 42,950 cells, 120 blocks). The global config is a different regime — 680×1441 at 0.25°, 456,873 valid cells, 156 months, skill vs persistence +0.520, seed-stable at +0.5165 ± 0.0023 across five seeds (`docs/findings/2026-07-13_global_monthly_emulator.md:19, 20, 22, 36`) — and **has never been scored against AR(1)**. | 1 day | **Highest ratio in this report.** Decisive either way: if it also loses with ~8× the training pairs, the data-starvation confound (§3.2 item 2) dies and the deflation becomes strongly publishable. If it does not, the current headline is scoped to a single 18-pair AOI and must be restated. Also the internal inconsistency most likely to be caught by a referee. |
| 8 | **Fix `_season_bin` to true calendar months and re-run the multiseed baselines** (§2.1). SST/wspeed/mldDepth are already wired. | ~half day | Repairs the number behind the entire Track-2 deflation. Error direction is conservative, so the result survives and gets *stronger* — and it removes a false docstring claim. |
| 9 | **One forcing-channel ablation** (§3.2 item 1) | 1 day | Either closes the strongest alternative explanation for the null or hardens it. Without this, "prognostic-only" is an unrebutted confound. |

### Tier 3 — literature and statistics hardening (a day, total)

| # | Action | Effort | Impact |
|---|---|---|---|
| 10 | **Add the missing citations**: Schartau 2017, Ward 2010, Löptien & Dietze 2017, Kriest 2017 (verified half), Mamnun 2025, Beven 2001/2006, Chis 2016, Fiechter 2013 / Leeds 2013 | half day | Löptien alone likely prevents a desk-level "unaware of the literature" review |
| 11 | **Quote Schartau Sect. 7.3 and answer it** with the matched global-scalar control; frame the negative held-out R² as compliance with Schartau Sect. 6.1 | 2 h | Converts the paper's weakest-looking result into demonstrated methodological literacy |
| 12 | **Frame the profile as the methodological novelty** — Schartau calls it impracticable for this model class; our surrogate makes it affordable | 1 h | Cleanest defensible novelty in Track 1, currently unstated |
| 13 | **Statistical fixes**: McNemar on the two epoch-doubling contrasts; BH not Bonferroni with m declared; Clopper-Pearson at boundary cells; drop the Fisher-equivalence wording; rewrite any sloppiness-implies-non-identifiability sentence to lean on the profile or posterior correlation instead | half day | Removes every remaining item a statistically-minded referee finds on the first pass |
| 14 | **Zero-epoch untrained control on the same 50 seeds** for the empirical null (§4.2) | 2 h | Turns "diatomgraz is at chance" into the stronger and more interesting "the fit actively drives diatomgraz out of band" |
| 15 | **Widen the profile box beyond the physical prior for `alpfe` and `diatomgraz`** (or profile in a transformed coordinate), and demote `rel_span` with an explicit error model and Δ_α-crossing CI endpoints (B2) | 1 day | B2 is a blocker on substance, but the fix is only credible *after* #15's re-run, so it lands here in sequence, not in priority |

### Tier 4 — code hygiene, cheap, do while waiting on jobs

16. **`grade_recovery.py`** — hard-fail on an unparseable seed instead of `continue`; don't let a corrupt file disable the gate (`:123-126`, `:227-231`). Make `verify_run.py:234` tolerant of one bad config dir.
17. **`percell_crlb_map.py:188-198`** — raise instead of fabricating axes; catch the specific exception, not `Exception`.
18. **Re-run `v05_geotraces_iron_profile_fidelity.py` with `allow_shallow_clamp=False`** plus a clamped-station count, and re-derive any surface-offset claim (§2.2).
19. **Off-by-one in `geotraces_loader.py:308-313` and `modis_pic_loader.py:219-222`** (`<=` → `<`); reconcile `modis_pic_loader`'s docstring at `:172` with its code at `:203-207`; add a coverage flag for the half-footprint edge cells.
20. **`xu_weber_loader.py:104`** — raise the coverage threshold to 1.0 or return the coverage array alongside the values. Latent now; fix before it carries an `alpfe` number.
21. **`kriging_field_reconstruction.py`** — refit the variogram excluding point k; count singular solves; check the L optimum is interior before returning it (§2.7).
22. **`emulator_baselines_v2.py:294`** — hard-fail when `--emu-json` is unreadable. The config is a property of the trained model, not a preference.
23. **Housekeeping:** land `docs/findings/2026-07-23_emulator_multiseed.md` onto the working branch (or fix the STATUS.md pointer); pick one sd convention for −0.161; qualify or fix "correctly-binned" at `STATUS.md:91`; pull the Neural-BGC 16.7M/6.2M counts from the PDF or drop them.

---

## Where the evidence is thin — stated plainly

- **§2.7 (kriging)** is code-level only. No result JSON exists anywhere, so I cannot demonstrate the boundary case ever fired. Confidence medium; every other bug in §2 is high.
- **§2.5 (off-by-one binners)** has **no evidence of having contaminated a reported number** — the standard pipelines subset the AOI first. It is a latent defect on a public function, not an active error.
- **§2.6 (Xu-Weber)** is fully latent: `git grep xu_weber` finds no executable importer.
- **Neural-BGC's 16.7M/6.2M sample counts** could not be re-verified this pass; the paper is paywalled (HTTP 402 reproduced on both routes). The qualitative claim is safe and abstract-corroborated; the exact counts are not.
- **Niraula & Goessling 2021** — author name and DOI verified, but the paper returned 402 and its internal argument was not independently read.
- **Bire et al. 2025** (10.1029/2023MS004137) — Wiley 402; the persistence/climatology claim was confirmed from the published record via search, not from a full read.
- **Bonavita 2024** — the published GRL version returned 402; the abstract was verified from the arXiv preprint of the same work (arXiv:2309.08473) plus published metadata.
- **Smith et al. 2026** — the "32-day window / 15-day stride" detail from an earlier note was **not** re-verified this pass.
- **Samudra 2's ~2,847 timestep count** is derived from the 1975–2013 span at 5-day cadence, not stated in-paper.
- **The forcing-uniqueness claim (§3.2 item 1)** is restricted to the five emulators whose input lists were actually checked. OceanNet's SSH-to-SSH setup and Bire's idealized double gyre were not, so "unique in the entire comparison set" is not supportable as written.
---

# Verification note — added after the sweep, by re-reading the raw records

The sweep's own adversarial pass caught one of its investigators **fabricating a
citation** (the Kriest 2017 "difficult, if not impossible" quote, which appears zero times
in that paper). That is the verification layer doing exactly its job, and it is the reason
every blocker below was re-checked by hand before being written down.

Two blockers were re-verified against the raw run records, and **one needs correcting**.

## Blocker 5, "the 0/50 denominator is inflated" — SUBSTANCE HOLDS, PHRASING TOO STRONG

The claim was that the global-scalar control's CV of ~0% means its effective *n* is 1, so a
Wilson interval on 0/50 is unjustified.

Graded from `n50e2k_global_scalar` (50 per-seed records, Explorer):

| param | mean | sd | CV | distinct values |
|---|---|---|---|---|
| `alpfe` | 0.975378 | 2.55e-4 | 0.026% | **50** |
| `scav_rat` | 3.55219e-07 | 2.03e-10 | 0.057% | **49** |
| `R_PICPOC` | 0.0923747 | 3.47e-4 | 0.376% | **50** |

The seeds produce **50 distinct values**, so they are genuinely 50 separate optimizations,
not one result copied. "Effective n is 1" is **too strong and should not be used**.

But the underlying point survives, and stated correctly it is *sharper than the paper's
current framing*. `scav_rat` converges to 3.552e-07 with sd 2.03e-10 while Carroll is
6.025e-07 — the gap is **≈1200 standard deviations**. The global-scalar arm does not fail
0/50 times *by chance*; it converges deterministically to a single wrong optimum on every
seed. A Wilson interval models binomial sampling variability that is not present here, and
reporting [0.00, 0.07] implies the true rate could be as high as 7% when the arm is in fact
reproducibly and structurally wrong.

**Recommended wording change:** replace the Wilson interval on the global-scalar arm with
the deterministic statement plus the sigma distance. It is a stronger claim, and it is the
one the data actually supports.

## Blocker 1, `rel_span` — CONFIRMED, and it is the most attackable methodological element

`scripts/identifiability_sloppiness.py` builds the profile grid from `PARAM_BOUNDS`, so
widening a physical prior mechanically raises `rel_span` and can flip a FLAT verdict to
CURVED **with no new data**. The repo already documents the fragility itself:
`docs/findings/iron_scav_rat_profile.json` reports the flat-band multiple as 25× / 32× /
100× at thresholds 0.01 / 0.02 / 0.05.

The related one-sidedness finding also explains a standing puzzle. Carroll's target sits at
log-position **0.98** of the `alpfe` box and **0.94** of the `diatomgraz` box, so the upper
arm of those two profiles has almost no range and Raue's two-sided criterion cannot be
evaluated as implemented. That is a mechanism for why `alpfe` reads FLAT yet recovers
9–10/10 — a contradiction STATUS has been carrying as an open warning.

## What was NOT verified

One agent (`verify:repro-gaps`) died on an API stall, so the reproducibility findings in
this report carry **no adversarial pass**. Treat that section as unverified leads rather
than confirmed findings.
