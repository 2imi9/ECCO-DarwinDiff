# The Manchester Earth-2 air-pollution recipe is not a Track-2 lever, and Track 2 stays in this repo

**Date:** 2026-09-30 · **Cost:** literature plus a read-only repo measurement; one nine-agent workflow
(six research agents, then a hostile fit reviewer, a citation auditor and a repo-split skeptic), no
cluster · **Prompted by:** NVIDIA blog, 2026-09-15, "University of Manchester Uses NVIDIA Earth-2 to
Forecast Air Pollution Across the UK" (<https://blogs.nvidia.com/blog/uk-air-pollution-research-earth-2/>),
raised as a candidate Track-2 emulator direction, together with the question of moving Track 2 to its
own repository.

> **This note PARTLY SUPERSEDES two map statements.**
> (1) "The Earth-2 stack has zero ocean/BGC models" (`docs/research_notes/2026-07-23_3d_emulator_earth2studio_design.md`)
> is too strong. Earth-2 has **no biogeochemistry**, but it does carry ocean physics: DLESyM couples an
> SST ocean model (NVIDIA blog, 2025-07-11) and NVIDIA published DLESyM-Ocean (upper ocean and sea ice)
> in August 2026.
> (2) "Still uncontested, stated narrowly: iron; ... emulation of a data-assimilating BGC state
> estimate" (`docs/findings/2026-09-19_samudrabgc_m2lines_now_does_bgc.md`) is too strong item by item.
> AI-GOMS (Xiong et al., arXiv 2308.03152, 2023) already predicts iron, nitrate and four phytoplankton
> classes, trained on the NASA Ocean Biogeochemical Model, which assimilates satellite chlorophyll, at
> 1°, with no baseline. Each of those two ingredients has been touched; what stays uncontested is the
> **conjunction** (a data-assimilating state estimate, with iron **and** the carbonate system **and**
> calcite), validation against independent dated observations, and identifiability.

> **DECISION, same day (2026-09-30): the owner is building the recipe anyway, and the reason is sound.**
> Every ECCO-Darwin parameter change or scenario needs a full rerun, so a complex scenario needs many
> reruns. A fast emulator is worth having for that, and the evidence below does not argue against speed.
> What the evidence below does decide is **how the build is graded**:
>
> - **Deterministic skill comes from the regression stage** (§2). The diffusion stage is judged on what it
>   is known to buy: calibrated spread, CRPS and spectra. Those matter for many-run uncertainty work.
> - **Every number carries its nulls** (§5).
> - **Changing a parameter needs training runs in which that parameter changes.** A model trained on the
>   single v05 run cannot predict the effect of a parameter change it never saw. The map already settles
>   that we can generate such runs ourselves:
>   - v05 runs on Explorer's `short` partition with no NASA account and no new allocation
>     (`docs/findings/2026-07-25_surrogate_to_gcm_validation.md`,
>     `docs/findings/2026-07-31_no_nasa_account_needed_v05_is_already_built.md`);
>   - a 17-deck perturbation recipe exists (`docs/findings/2026-07-23_v05_perturbation_recipe.md`).
>
> **Correction to §3, made the same day.** The daily archive is **not** limited to variables SamudraBGC
> already covers. SamudraBGC carries no pCO2, pH or air-sea CO2 flux, and the daily archive has all three.
> The daily task's raw sample count (9,463 days in the saved cubes) also matches Manchester's (about 8,760
> hourly). So "data binds" holds for the **monthly** task (158 to 313 samples), **not** for the daily
> surface task. Effective sample size is unmeasured for both, and hourly air quality is autocorrelated too.
>
> **Data state as of 2026-09-30:**
> - **Cubes that survive** are in AICR `/work/neu/p2026_0089_neu/cubes/`, which is snapshotted and not
>   purged:
>   - `daily_global_1deg_cube.npz`: 9,463 days × {surfChl1, 2, 3, 5} plus forcing {SST, wspeed},
>     171×360;
>   - `daily_global_halfdeg_cube.npz`: the same at 341×720, which gives a ready 1° → 0.5° pair;
>   - `global3d_L10_cube.npz`: 158 months × {DIC, ALK, PIC, POC, FeT, Chl1} × 10 levels, 680×1440.
> - **Lost to the purge:** the raw AICR `/scratch` daily, monthly and v05-build trees.
> - **Blocked today:** `data.nas.nasa.gov:443` is unreachable from the workstation, AICR and Explorer,
>   while `www.nas.nasa.gov` answers. So daily pCO2, pH and CO2 flux cannot be downloaded today.
> - **Still available:** the local monthly mirror has pCO2, CO2_flux and all the physical fields.

## 1. What the post establishes, and what it does not

The blog is the **only first-hand account**. It was read verbatim, and it links no paper, preprint,
repository or dataset. OpenAlex, arXiv, GitHub and Hugging Face searches on 2026-09-30 found none.

| | stated in the post? |
|---|---|
| models | Earth-2 **CorrDiff** (generative downscaling) and Earth-2 **StormCast** (time-stepping) |
| training data | "a year's worth of U.K. pollution data simulated at hourly intervals" from existing chemistry-climate simulations; about 8,760 samples if hourly, but no count is given |
| resolution | "2-3 square kilometers" (unit as written) |
| compute | one eight-GPU GH200 node on Isambard-AI, about two days (384 GPU-hours). **The post does not say which of the two models this covers**; treat it as the budget for the whole workflow |
| chemistry model, species, CorrDiff inputs, StormCast conditioning, split | **not stated** |
| skill number, baseline | **none**. The only performance statement is that the model "worked on the first attempt", which says the code ran |
| code and data | release is a stated plan only |

**It is a collaboration announcement, not independent reporting.** The NVIDIA spokesperson quoted,
Niall Robinson, co-authored with Topping in 2021 (doi 10.3389/frsc.2021.786563) and holds a Manchester
PhD.

**The closest inspectable relative has baselines, and they say the diffusion stage is not where the
skill is.** `github.com/envdes/code_CMAQ_CorrDiff_Germany_2019` (Zhonghua Zheng's group; Zheng
co-supervises Hao Zhang; created 2026-09-14; no licence; unpublished manuscript) applies CorrDiff to
CMAQ PM2.5 over Germany, 36 km to 4 km. Inputs are coarse PM2.5 plus nine ERA5 fields, bilinearly
upsampled. Unweighted mean of its 12 monthly PM2.5 RMSEs (our arithmetic on the repo's CSV):

| bilinear | regression U-Net | CorrDiff | plain diffusion |
|---|---|---|---|
| 4.14 | 2.96 | 2.81 | 3.62 |

Most of the gain over interpolation comes from the deterministic U-Net; the diffusion stage adds about
5%. For O3, CorrDiff is **worse** than its own regression stage (2.52 vs 2.44) while restoring
fine-scale spectral energy. It is not the UK work, and the link between the two is ours to infer.

The best available clue to the UK chemistry model is an N8 Bede project page (PI Congbo Song, NCAS
Manchester) that trains StormCast on **WRF-EMEP** simulations with ground observations. That this is the
same work as the blog is an inference.

## 2. The diffusion stage does not buy deterministic skill

This is the decisive external fact, verified against primary sources:

- **CorrDiff paper** (Mardani et al., arXiv 2309.15214v4; Commun Earth Environ 6, 124, 2025),
  Table 1, ensemble-mean MAE vs the regression UNet: radar 2.54 vs 2.51, t2m 0.65 vs 0.64, u10m 1.08
  vs 1.10, v10m 1.19 vs 1.21. The paper calls the slight degradation expected. The gain is in CRPS,
  spectra and tails, and the ensembles are under-dispersive.
- **Fotiadis et al.** (arXiv 2410.19814): RMSE within about 0-3% of the UNet.
- **StormCast** (Pathak et al., arXiv 2408.10958): justifies diffusion by under-sampled, **chaotic**
  km-scale convection that blurs a deterministic forecast. This repo measured **no positive Lyapunov
  exponent** in the BGC emulator (`docs/findings/2026-07-20_rollout_ceiling_mechanism.md`), so the
  premise does not hold here. StormCast is compared against HRRR only (no persistence or climatology),
  is evaluated to 12 hourly steps, and does not address conservation.

This agrees with the settled row "Does EDM diffusion add emulator skill? No". That row's artifacts are
absent (`docs/findings/2026-07-28_project_evidence_matrix.md`), so the **external** evidence carries the
verdict on its own. Mechanistically the result is task-agnostic: the ensemble mean of a residual sampler
converges to the regression mean, which `scripts/diffusion_emulator.py`'s own docstring predicted.

`scripts/diffusion_emulator.py` **already is** the CorrDiff two-stage design (FNO regression mean plus
an EDM residual conditioned on `[x_t, mu]`). What the repo has never tried is the **task**: a diagnostic
or downscaling mapping with physical conditioning. The design is not new; the task would be.

## 3. Compute is not the binding constraint; what binds is variation in the data, not volume

> **Reconciled 2026-09-30 with a settled row.** The map already settles that the monthly emulator's
> learning curve is **flat from n≈55** (+0.4700 at n=55, +0.4701 at n=82, +0.4657 at n=110;
> `docs/findings/2026-07-19_two_negatives.md`). So "data binds", in the sense that more samples of the
> same run would raise deterministic skill, is **wrong** and is not claimed here.
>
> What the table below shows is narrower:
>
> - **Memorisation risk.** The sample count is two orders below what published diffusion recipes train on,
>   which is a memorisation risk for a diffusion stage.
> - **What is missing is variation.** For the owner's use case, predicting the effect of a parameter change
>   or a scenario, the data has **no** variation at all, and no amount of volume supplies it. See
>   `docs/research_notes/2026-09-30_topping_recipe_build_spec.md` §1.

| | training samples | compute |
|---|---|---|
| CorrDiff, Taiwan (paper) | 24,154 | about 21,504 H100 GPU-hours |
| StormCast (paper) | 30,660 | 120 h on 64 H100 (7,680 GPU-hours, our arithmetic) |
| NVIDIA's own rule of thumb (PhysicsNeMo CorrDiff README) | at least 50,000 | |
| Manchester | about 8,760 if one hourly year (not stated) | 384 GPU-hours |
| **ECCO-Darwin v05 monthly, prognostic** | **158 steps** (76 truly monthly pairs) | |
| **v05 monthly, same-time diagnostic** (computed from the local mirror) | **313** (7 surface physics fields); **268-283** (physics plus one BGC tracer); **152** (all six current tracers); **123** (plus 3-D T and S) | |
| v05 daily | 9,392 shared steps, but lag-1 r 0.994-0.996, surface only, **no DIC, ALK, PIC, POC or FeT** | |

The AICR allocation (B200, QOS cap 32 GPUs) covers Manchester's budget in hours (using NVIDIA's
unbenchmarked "3x over H100" figure). **Extra compute cannot buy samples.** Diffusion denoisers memorise
their training set at N of 100 or fewer and are transitional near 1,000 (Kadkhodaie et al., arXiv
2310.02557; transfer to conditional residual diffusion is our inference). The only v05 regime with
CorrDiff-scale raw counts is the daily archive. It is surface-only, and its physical inputs are thin: SST,
SSSanom, wspeed and sea ice, with no MLD and no shortwave. It does include pCO2, pH and air-sea CO2 flux,
which SamudraBGC does not carry. (An earlier version of this sentence said the daily archive held only
variables SamudraBGC already covers; that was wrong about pCO2. See the correction at the top.)

## 4. Which settled negatives bind which task

| settled negative | binds a prognostic step operator | binds a diagnostic mapping |
|---|---|---|
| EDM diffusion adds no skill | yes | the mechanism transfers, and CorrDiff's own Table 1 confirms it |
| rollout ceiling about 1 monthly step, chaos absent | yes | no (no rollout), but it removes StormCast's reason for diffusion |
| depth emulator -0.161 ± 0.015 vs seasonal AR(1) | yes | the number does not; the rule does (beat the strongest free per-cell baseline, CI clear of zero) |
| daily archive surface-only, lag-1 r about 0.995 | yes | yes, through the data |
| linear probe "recovers a map, not a time evolution" (`docs/findings/2026-07-19_two_negatives.md`) | | in spirit: raw R² will be mostly static pattern, so a per-cell climatology null is **mandatory** |

**Downscaling has no user.** The only coarse/fine pairs are block averages of the same native run at
4x linear (`emulator_poc.py --grid-res`). There is no coarse ECCO-Darwin run whose output anyone needs
downscaled, so this is super-resolution of a box average, not CorrDiff's model-to-model setting.

## 5. What survives: a deterministic physics-to-BGC diagnostic, not yet run

**Prior art**: close ingredients exist, but not the conjunction.

- **AI-GOMS** (arXiv 2308.03152): iron, nitrate and chlorophyll classes from a physical backbone, trained
  on a chlorophyll-assimilating model, 1°, no baseline.
- **Ehmen, Mackay and Watson**: temperature, salinity and atmospheric CO2 mapped to interior DIC, with
  ECCO-Darwin as a test bed. This is an EGUsphere preprint under review for Biogeosciences
  (doi 10.5194/egusphere-2026-3396), not a published paper.
- **Skakala** (arXiv 2508.10178): shelf-sea carbon pools; the model "mostly learned the free run
  climatology" and fails on DIC.
- **Lakra et al.** (arXiv 2602.04689): physics mapped to satellite chlorophyll, with no climatology null.

**Not found by anyone:**

- CorrDiff or StormCast applied to ocean biogeochemistry. CorrDiff has been used on ocean physics only:
  OcDiffSR (arXiv 2609.22574) uses it as a baseline for Adriatic SST, salinity and currents and beats it.
- Alkalinity or calcite diagnosed from physics in a state estimate.

**The pre-test** (recorded as hypothesis `hy_physics_to_bgc_diagnostic_beats_climatology`, open). It
runs on the local 5090 or CPU, on the monthly mirror already on disk, and needs no B200 time:

- **Inputs at month t, with no lagged BGC:**
  - SST, SSSanom, mldDepth, wspeed, oceanQsw, oceanQnet and SIarea;
  - land mask and bathymetry;
  - sin/cos latitude and longitude;
  - month-of-year from a datetime calendar with `delta_t` = 1200 s.
- **Targets at month t:** surface DIC, ALK, FeT, PIC and POC, each on its own intersection. log10 Chl1
  is a control and cannot count toward a pass.
- **Grid and split:**
  - global 1° regular grid, ocean cells only, area-weighted;
  - train 1992-2008, a 12-month gap, test 2010-2018;
  - robustness runs with 6- and 24-month gaps and with the split reversed.
- **Nulls, all fitted on train only:**
  - (a) per-cell monthly climatology;
  - (b) per-cell seasonal AR(1), reported as information-advantaged;
  - (c) per-cell ridge regression of the anomaly on the same physics anomalies;
  - (d) the regression U-Net alone, 5 seeds. **No diffusion stage.**
- **Pass (all must hold):**
  - the U-Net ensemble beats (c) with a block-bootstrap CI lower bound above 0 on at least 2 of
    {DIC, ALK, FeT, PIC};
  - on those same fields it beats (a) by at least +0.10 skill;
  - both hold under every gap and split setting.
- **Stop:**
  - (c) within CI of (d), or (d) at or below (a), or a pass at one split only.
  - A stop closes the direction, **including every CorrDiff/StormCast variant**, because a diffusion
    stage cannot add deterministic skill its regression stage lacks.
- **If it passes:** the only next step licensed is a deep ensemble of the regression model. A diffusion
  stage is licensed only for calibration, and only after the absent diffusion artifacts are re-run.

Do **not** score it with `scripts/analysis/emulator_baselines_v2.py` as-is. Its `_season_bin`
(lines 104-109) still merges January and February on `main`, and it scores (t, t+1) pairs, not
same-time mappings. `scripts/rollout_verify.py` has a correct datetime month.

**PhysicsNeMo moved in 2026.** The CorrDiff example was deprecated on 2026-08-13 (PR #1909). Its
replacement, `examples/weather/regional_weather_diffusion` (PR #1977), exists on `main` only and not in
v2.2.2, and adds a per-pixel loss mask. `corrdiff-cosmo-era5` (2026-07-27) is a DiT that predicts the
field directly rather than a residual. Any adoption must pin a commit, not a release.

## 6. Should Track 2 move to its own repository? Measured: not now

**"Track 2" is two pieces with opposite coupling.**

| | src files | src lines | ties to Track 1 |
|---|---|---|---|
| **T2a, emulator** (`emulator.py`, `e2s/`) | 4 | 715 | **none inside the package**. At script level `scripts/emulator_poc.py` imports five shared loaders, and `iron_forcing_loader.py:57` pulls `PHI_DUST` from `carroll6` |
| **T2b, UDE / transport / closures** | 6 | 2,407 | **built on the Track-1 core**: `transport.py:21` and `closures.py:20` import from `carroll6`; the UDE hook is `carroll6.carroll6_ude_tendency` (`carroll6.py:365`); `tests/test_transport.py:34` asserts transport tendency equals the box tendency |

Other measurements (read-only, branch `docs/bgc-map-param-fields` at 28c989c):

- **Scripts and tests by track:** Track 1 has 143 scripts and 55 tests; T2a 14 and 9; T2b 41 and 9;
  shared 13 and 11. About half of these labels rest on import evidence and the rest on filenames or
  docstrings.
- **The research-map gate assumes one repo.** `research_map_db.py` builds its document list from
  `git ls-files`, so a claim that cites a document which has moved fails `check`.
  - Track-2 claims number between 80 (the map's own `track` column) and 172 (a wider emulator-plus-UDE
    keyword net).
  - They sit in 39 to 111 documents, of which only 9 to 28 are purely Track 2.
  - The `track` column (`_infer_track`, `research_map_db.py:350`) keys on emulator words only, so it
    undercounts the UDE work.
- **A uv workspace does not isolate dependencies.** Workspace members share one lock, and uv's docs say
  workspaces are "not suited for cases in which members have conflicting requirements". earth2studio
  requires `netCDF4<1.7.3`, while `uv.lock:1914-1915` pins 1.7.4, and `pyproject.toml` already explains
  why earth2studio is not a declared extra.
- **History over the last 90 days:** 470 non-merge commits. 85 touch Track-1 code and 74 touch Track-2
  code (73 of those in July, 2 in August, 4 in September). 7 touch both, and those are repo-wide chores.
- **GMD code availability** needs a frozen DOI archive, which a Zenodo snapshot of a tag provides. A
  separate repo adds nothing.

**Recommendation (a recommendation, not a measurement):**

- **Keep one repo now.** No Track-2 result exists to package, and the only surviving Track-2 idea (§5)
  needs no new dependencies.
- **Trigger 1: the first commit that needs `physicsnemo` or `earth2studio` as a real, unguarded import.**
  - Create a **separate uv project inside this repo**, for example `track2/`, with its own
    `pyproject.toml` and `uv.lock`.
  - It depends on `darwindiff` by path through `tool.uv.sources`.
  - Move `emulator.py`, `e2s/` and the emulator scripts there, and give it its own non-blocking CI job.
  - The UDE code, the docs and the research map stay where they are.
- **Trigger 2: a separate repository, made by copying files, never by rewriting history.**
  - Only when a second person commits to Track 2, or when a collaborator, funder, venue or NVIDIA asks
    for the emulator as a separately versioned package.
  - `e2s/` has no internal imports, so it can be lifted into an earth2studio pull request as it stands.

## 7. Loose ends found in passing

- **The binning bug is still there.** `scripts/analysis/emulator_baselines_v2.py:104-109` `_season_bin`
  is unchanged on `main`, although the map settled it as a bug on 2026-07-25.
- **The native-vs-1° finding cannot be reached from the checkout.** The finding "emulator skill does not
  sharpen with resolution" lives only in commit `a183dd1`
  (`docs/findings/2026-07-12_resolution_sharpening.md`). That commit is on **no branch**, and the finding
  has no map row, so neither the map gate nor a reader can reach it.
- **The -0.161 AOI label may be wrong.** The number is labelled eqpac, but its cell and block counts
  indicate the global 1° cube with 18 training pairs. This was inferred by arithmetic, not checked
  against the artifact.
- **`scripts/build_public_release.py` is stale.**
  - Its docstring says the repo "is now PRIVATE". The repo is public (checked with `gh` on 2026-09-30).
  - It ships `scripts/physics_verify.py`, whose line 42 imports `diffusion_emulator`, but it does not
    ship `diffusion_emulator.py`.
- **The vendored arXiv search script misreports its output.** `literature_search_arxiv`'s
  `search_arxiv.py` prints one JSON object per hit and nothing for zero hits, so an empty result is
  indistinguishable from a failed call.

## Sources

Opened and checked by the citation auditor (73 external claims: 71 held, 2 corrected above, none
fatal):

- **The blog and its context:**
  - the NVIDIA blog post above;
  - the NVIDIA "AI for Science: lab to frontier" webinar listing;
  - `n8cir.org.uk/bede/research-projects/manchester/`;
  - `github.com/envdes/code_CMAQ_CorrDiff_Germany_2019`;
  - doi 10.3389/frsc.2021.786563.
- **Model papers:** arXiv 2309.15214v4 and doi 10.1038/s43247-025-02042-5; arXiv 2410.19814;
  arXiv 2408.10958 and its Science Advances version; arXiv 2310.02557.
- **Code:** `github.com/NVIDIA/physicsnemo` (corrdiff and regional_weather_diffusion examples; PRs #1909,
  #1977 and #1993); `github.com/NVIDIA/earth2studio` (`models/dx/corrdiff.py`, StormCast wrapper).
- **Prior art:** arXiv 2609.22574; arXiv 2308.03152; arXiv 2508.10178; arXiv 2602.04689;
  doi 10.5194/egusphere-2026-3396.

Could not be checked:

- the BGC-UNet paper (Ocean Modelling 195, 102491; bot wall);
- the Ehmen RMSE of 15.1 µmol/kg (in a PDF not downloaded);
- the gated `nvidia/corrdiff-era5-hrrr` card;
- the content of the 2026-09-30 webinar (no recording).
