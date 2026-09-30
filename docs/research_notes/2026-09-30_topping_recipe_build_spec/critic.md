# Critic: first-run failures, one fix list, ordered build plan

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

I reviewed the five spec parts as a critic and checked the load-bearing claims against the pinned upstream code (physicsnemo 536553a, earth2studio 2067756d) and the repo. As written, the combined spec will not work on the first real run. Five problems block it:

**1. Grids.** The five parts use five incompatible grids:
- recipe: 341x720 cube, padded to 344x736;
- e2s: descending node-registered 720x1440 and 176x360;
- data: ascending cell-centred 640x1440 and 180x360 (182x362 with halo);
- eval: 1/3 deg fine with a 3x3 block-mean coarse grid;
- the cubes themselves: -80..89.75 at 0.998538 deg, not 1 deg (handoff:188-189).

**2. Splits.** The three split schemes disagree. The recipe's validation years 2010-2011 fall inside the pre-registered test period (finding:183).

**3. Background leak.** The eval's daily StormCast background includes apCO2 at t+1. The daily apCO2 file is seawater surfpCO2, which is the target (handoff:183-185).

**4. Model chain.** The CorrDiff-then-StormCast chain cannot be wired as specified:
- DiagnosticWrapper passes only the prognostic's output to the diagnostic, then selects diagnostic variables by name (dxwrapper.py:158-167). The data spec's CorrDiff background needs fine physics and day-of-year, and the prognostic emits neither.
- CorrDiff probably receives valid_time=None inside the chain, because @batch_func folds time into batch before the time key is read (corrdiff.py:1107-1159). This is inferred from the code, not run.
- The recipe's first pair of runs does not compose into a chain: 0.5 deg forecasting plus 1 to 0.5 deg downscaling.

**5. Normalisation.** Three different transforms and three stats.json schemas are in play. The recipe feeds raw invariants to the network (trainer.py:357-364), while earth2studio CorrDiff normalises invariants from stats (corrdiff.py:483-491, 812-818).

**Silent bugs I found:**
- The recipe's `_finish` runs `np.nan_to_num(z, nan=0.0)` before its infinity check. That call turns inf into float max, so the check can never fire.
- The recipe's builder labels days by window end (times_days, emulator_poc.py:509). The E2S DataSource looks up by window start, so the two disagree by one day.
- The eval mask ("finite jointly") would score land once the wrappers write land as 0.
- Physics check A becomes vacuous once outputs are clamped.
- The per-PFT surfChl targets planned for the first runs are 26-41% negative (handoff:178-181). A log10 floor would turn about 40% of surfChl3/5 into a constant.

**Resolved from the risk lists:**
- natten is an OptionalImport at 536553a (checked with gh api), so the UNet path does not need it.
- The recipe's infinite validation sampler wraps around (parallel.py:153-170), so small monthly validation sets do not produce zero batches.

**Plan.** Adopt one lattice: cell-centred, ascending, lat -80..80.
- High-res grid: 0.25 deg, 640x1440.
- Low-res grid: 1 deg, 160x360, built as an exact 4x4 block mean of the high-res grid.
- Split: the eval's G12 split.
- Transforms and layout: one owner, a module in the main package.
- Stores: one zarr store read by both training and serving.
- The prognostic passes physics and day-of-year through to the diagnostic.

Run S0, the pre-registered physics-to-BGC diagnostic, first at 1 deg. Treat the AICR cubes as plumbing and probe data only.

## Decisions

- **Canonical grid** → Cell-centred, ascending lat -80..80, lon [0,360). HR 0.25 deg is 640x1440 with a 16-column periodic halo in training (image 640x1472). LR 1 deg is 160x360, an exact 4x4 area x ocean-fraction block mean of HR. Keep grid_bounds_margin 0.375 and do the LR halo and land-fill inside DarwinCorrDiff.
  - why: It satisfies SongUNet divisibility (verified song_unet.py:561-571). Base CorrDiff accepts ascending 1-D grids (corrdiff.py:285-298). The px output equals the dx input bitwise, so DiagnosticWrapper skips interpolation (dxwrapper.py:153). Exact nesting makes the N1/N3 nulls and CCE exact. It removes the four other grids.
- **Role of the AICR daily cubes** → Plumbing and memory probes only. Never graded or served.
  - why: Provenance is unclear (handoff:146-147). The grid is 0.998538 deg from -80..89.75 (handoff:188-189). The cubes carry no lat/lon, their times are window-end, the calendar fix is unknown, the size is inconsistent with the stated contents, and the per-PFT targets are 26-41% negative.
- **Split** → Eval G12 plus G6/G24/REV12, from one builder-written split.json that everything reads by name.
  - why: The recipe's validation years 2010-2011 are the pre-registered test period (finding:183). G12 nests inside the pre-registered 1992-2008/2009/2010+ design.
- **Wiring the prognostic to the diagnostic** → DarwinStormCast emits the BGC state, the fetched physics background and doy as pass-through channels. CorrDiff trains only on inputs the chain can supply: up(LR BGC), up(LR physics), doy.
  - why: DiagnosticWrapper gives dx only px outputs, mapped by variable name (dxwrapper.py:158-167). CorrDiff sees valid_time=None under @batch_func (inferred), so it cannot compute its own time features.
- **Normalisation owner** → A darwindiff.e2data.transforms module in the main package, used by the dataset, the wrappers and the scorer. Invariants are stored pre-normalised with identity stats. One stats.json holds all key blocks. Training uses asinh for FeT/PIC/POC/CHL; the scoring floors are eval-only.
  - why: Three transforms and three schemas currently disagree. The recipe feeds raw invariants while E2S CorrDiff normalises them (trainer.py:357-364 vs corrdiff.py:483-491).
- **Daily background variables** → Exclude daily apCO2 from any background. The gate compares fldList and source directory between background and state.
  - why: Daily apCO2 is seawater surfpCO2, which is the target (handoff:183-185).
- **Grading rules** → The eval spec plus the finding §5 pre-test are binding. Delete recipe §8. Add an untrained step-0 network null through the identical E2S pipeline. Information-match N5 to the model's exact inputs. Mask = ocean AND avail AND finite(truth). Score physics check A before clamping.
  - why: Recipe §8 compares ensemble CRPS against the UNet MAE, which is a guaranteed pass. As written, N5 would trip the eval's own INTEGRITY check, and land written as 0 would be scored.
- **Environment** → track2 is a Linux-only uv project (environments marker) on Python 3.12: physicsnemo@536553a, earth2studio@2067756d, torch 2.11.0+cu128 from its own index, netCDF4 1.7.2, no natten. Build it in a Slurm job on /work.
  - why: earth2studio requires pygrib, which made a universal lock unsatisfiable (repo pyproject note). natten is an OptionalImport at the pin (verified). The torch index does not propagate from darwindiff.
- **First graded run** → The S0 physics-to-BGC diagnostic at LR 1 deg, regression only, before any CorrDiff or StormCast training.
  - why: The pre-registered STOP closes every CorrDiff/StormCast variant (finding:193-196). The monthly data is on disk, while the daily data is blocked.

## Risks

- If S0 stops, the whole CorrDiff/StormCast direction closes. M1 plumbing is then only engineering and must not be reported as skill.
- The CorrDiff chain probably receives valid_time=None. This is inferred from the batch_func ordering, not executed; M1 must assert it.
- The diffusion checkpoint filename and nested .mdlus reload of EDMPreconditioner(ConcatConditionWrapper(SongUNet)) are unverified; make_package globs rather than hardcoding.
- Daily graded work (SC-D, the chain) is blocked until data.nas.nasa.gov answers, and the range-request support needed for pH k0 is untested.
- Restricting to -80..80 drops Arctic ocean north of 80N. This must be declared as a pre-registration amendment before training, or S0 deviates from 'global 1 deg'.
- The monthly per-tracer sets have about 145 training months, so memorisation is likely. Checkpoint selection must use deterministic val RMSE from the scorer, not the trainer's stochastic or unnormalised val_loss.
- Diffusion inference cost at HR over about 3,286 daily test days is unmeasured and could be large.
- Nothing I have seen confirms that AICR compute nodes can reach GitHub, PyPI and download.pytorch.org to build the git-pinned env.
- A mismatch in condition order, background offset or halo between training and serving produces plausible but wrong fields; only the M1 parity test guards against it.
- The 5090 cannot run track2 natively. Local work is limited to the builder, the gate and WSL2, which is untested.

## Unknowns

- The actual keys, shapes, lat/lon and time basis of the AICR cubes, and why the 0.5 deg cube is 42 GB when 51.9 GiB is implied.
- Whether the AICR cubes were built before or after the 1200 s calendar fix.
- Whether netCDF4 1.7.2 cp312 manylinux wheels resolve together with the physicsnemo git pin and earth2studio in one Linux-only uv lock.
- Whether warp-lang>=1.14 runs on sm_100 under torch 2.11.0+cu128.
- The exact .mdlus filename that save_checkpoint gives the recipe's EDMPreconditioner.
- Whether EDMNoiseScheduler or sample accept a torch.Generator; the fork_rng fallback is assumed.
- Compute-node internet egress on AICR, and the AICR ~/dd_venv Python version.
- Whether data.nas.nasa.gov is reachable now and honours HTTP Range.
- Per-sample GPU memory and step time at 160x360 and 640x1472.
- Whether the S0 1 deg crop amendment is acceptable to the owner before the pre-registration commit.

## Spec

PRIORITISED FIX LIST.
Labels: [V] = I read it this session; [I] = inferred from code; [U] = unverified.
- RWD = physicsnemo@536553a examples/weather/regional_weather_diffusion
- E2S = earth2studio@2067756d
Local copies used: scratchpad pn/, e2s/.

=== P0: fails or corrupts silently on the first real run ===

F1. ONE GRID CONTRACT
Today there are five grids:
- recipe: 341x720, padded to 344x736;
- e2s: descending node-registered 720x1440 and 176x360;
- data: ascending cell-centred 640x1440 and 180x360 (182x362 with halo);
- eval: 1/3 deg fine with a 3x3 block-mean coarse grid;
- the AICR cubes: 171 rows from -80..89.75 at 0.998538 deg, and 341 rows at about 0.49926 deg [V docs/research_notes/2026-07-30_session_handoff.md:188-189]. So the recipe's inferred "-80..90, integer halving" is wrong.

Fix, one lattice for everything:
- Orientation: cell-centred, ASCENDING lat, lon in [0,360).
- HR (high-res): 0.25 deg, 640x1440. Lat centres -79.875..79.875; lon 0.125..359.875.
  - Area-weighted native remap plus hole fill, per the data spec §1.
- LR (low-res): 1 deg, 160x360. It is defined as the exact 4x4 area x ocean-fraction block mean of HR, NOT a separate native remap. This makes the eval's N1/N3 nulls exactly coarse-consistent and CCE meaningful.
- SongUNet sizes: HR allows N<=5 levels (640/16=40, with a 16-column periodic halo giving 1472/16=92). LR allows N<=4 (160/8=20, 360/8=45) [V song_unet.py:561-571].
- Why ascending: base CorrDiff accepts ascending grids without a validator override [V corrdiff.py:285-298]. Every source in the chain is ours, and handshake_coords needs only exact equality.
- The dx (diagnostic) input grid must equal the px (prognostic) output grid bitwise. Otherwise DiagnosticWrapper silently builds a LatLonInterpolation [V dxwrapper.py:148-156].
- The LR land-fill and halo (data §1) move inside DarwinCorrDiff._interpolate.
- Set metadata grid_bounds_margin >= 0.375, because the HR edge centre -79.875 lies outside the LR edge centre -79.5 (bounds check at corrdiff.py:388-421).
- S0 runs on LR 1 deg. The pre-registration says "global 1 deg" (finding:181-183), and the -80..80 crop drops the ocean north of 80N. Record this as a pre-registration amendment BEFORE training.
- Drop 721-, 720- and 1/3-deg grids, and drop row padding.

F2. THE AICR DAILY CUBES ARE NOT A GRADED OR SERVED DATASET
- Provenance is "unclear" [V handoff:146-147].
- The grid is not 1 deg (F1), and the cubes hold no lat/lon keys [V emulator_poc.py:1401-1411].
- times_days is the window END [V emulator_poc.py:509].
- Build date versus the 1200 s calendar fix is unknown. The sibling daily artifact on that tree was built at 900 s [V memory note, 2026-07-30 contaminated finding].
- Size check: 9,463 d x 6 ch x 341x720 x 4 B = 51.9 GiB, but the file is 42 GB [V handoff:146]. So the 0.5 deg cube's channels and days are [U].
- The planned targets surfChl2/3/5 are 26.5/39.7/41.3% negative and untrusted until TRAC27-31 are resolved [V handoff:178-181].
- Use the cubes ONLY for M1/M2 plumbing and memory probes.
- If a daily run on them is ever wanted:
  1. List np.load(p).files and shapes.
  2. Derive time as iters*1200 s and assert a 72-iteration step.
  3. Audit: compare the cube's monthly-mean surfChl1 with the monthly mirror's Chl1 k0 binned to the same rows [I].
  4. Label every result "cube-derived, not graded".

F3. ONE SPLIT
- Current conflict: recipe valid 2010-2011 (that is TEST in the pre-registration, finding:183); data std12 (gap in 2006); eval G12 (val 2006-2008).
- Adopt eval G12: train 1992-01..2005-12, val 2006-01..2008-12, gap 2009, test 2010-01..end. Robustness splits: G6, G24, REV12.
- Val sits inside the pre-registered "train 1992-2008" window and nothing is fitted on it. State that in the amendment.
- The builder writes splits/<name>/split.json. The dataset, nulls and scorer take a split NAME, never year lists. Delete train_years/valid_years from the recipe configs.

F4. DAILY BACKGROUND LEAKS THE TARGET
- Eval SC-D puts apCO2(t+1) in the background and pCO2 k0 in the state. Daily apCO2 IS seawater surfpCO2 [V handoff:183-185].
- Remove apCO2 from every daily background; there is no daily atmospheric pCO2.
- Gate check 6 must compare source directories and fldList between background and state, not channel names.

F5. THE CHAIN CANNOT BE WIRED AS SPECIFIED
- DiagnosticWrapper hands dx only px_x, then map_coords selects dx variables by name [V dxwrapper.py:158-167, 504-510].
- So every dx input must be a px output. The data spec's CorrDiff background needs fine PHYS9 and TIME2, which DarwinStormCast does not emit.
- CorrDiff.__call__ is wrapped by @batch_func, which folds "time" into batch before the method reads coords["time"] [V corrdiff.py:1107-1159; I batch.py:74-130]. So valid_time is None in the chain, and day-of-year cannot be computed inside dx.
- Fix (recommended):
  - DarwinStormCast outputs [BGC state at t+dt] + [the physics background it fetched at t+dt, as pass-through channels] + [doy_sin, doy_cos].
  - The CorrDiff training background is exactly {up(LR BGC), up(LR physics), doy}, which the chain can supply.
  - Fine physics becomes a later ablation, served through a custom PrepareDxInputTensor that fetches from a DataSource using px_coords time+lead_time.
- Also: the recipe's D1 (1->0.5 deg) plus F1 (0.5 deg forecasting) cannot chain. The chain is px on LR -> dx LR->HR.

F6. BACKGROUND TIME, TRAINING VERSUS SERVING
- recipe/data/eval train with physics at t+1 (data adds t).
- E2S's own StormCast, the HRRR loader, and the e2s DarwinStormCast (bg_offset default 0) fetch at t [V stormcast.py:456-464].
- Fix: metadata background_offsets is a LIST, e.g. [dt] or [0, dt]. Background channel names carry @t0/@t1 suffixes identical to dataset._b_names. The M1 parity test fails on any mismatch.

F7. ONE NORMALISATION OWNER
- Today there are three transforms:
  - recipe: log10 with floor 1e-4;
  - data: asinh(x/s) with fixed s;
  - eval (scoring): log10 with floor 1e-3 x median.
- And three stats schemas: CorrDiff {input,output,invariants}; DarwinStormCast {state,background,invariants}; recipe npy.
- The recipe passes raw invariants [V trainer.py:357-364], but CorrDiff normalises invariants with stats["invariants"] [V corrdiff.py:483-491, 812-818].
- Fix: create darwindiff.e2data.transforms in the MAIN package (numpy/torch only). It holds:
  - ChannelSpec forward/inverse (asinh FeT/PIC/POC/CHL, log10 MLD, linear otherwise, per data §2);
  - normalize/denormalize;
  - layout/crop (the lon halo);
  - fill_and_mask.
- The RWD dataset, DarwinStormCast, DarwinCorrDiff and the scorer all import it.
- Invariants are stored already normalised, with identity stats (mean 0, std 1).
- One stats.json carries every key block.
- The eval's log floors apply to SCORING only, computed on denormalised physical values.

F8. NaN/inf GUARD BUG
- The recipe's `_finish` calls np.nan_to_num(z, nan=0.0), which maps +/-inf to float max, and only then checks isfinite. So its FloatingPointError can never fire [V by numpy semantics]. torch.nan_to_num in the e2s drafts has the same flaw.
- Fix: raise on np.isinf(z).any() BEFORE filling, then call nan_to_num(nan=0, posinf=0, neginf=0).
- Add an assertion that |z| < 50 after normalisation.

F9. ONE STORE
- The recipe dataset reads .npy memmaps; the data builder writes zarr v2; the e2s DataSource reads zarr.
- Use the data §3 zarr layout for both training and serving. The dataset opens it lazily per worker and never pickles the handle.
- Channel names are physical ("DIC", "CHL"), with the transform recorded in the manifest. Training-space names like "log10_surfChl1" must never reach E2S variable coords.
- validation_plot_variables uses the physical names.

F10. CALENDAR LABEL
- The recipe builder uses times_days, which is the window end, one day late for daily data [V emulator_poc.py:509].
- data/eval/e2s use the window start (stamp minus 1 s), and EccoDarwinZarr looks up by exact date. Mixing the two gives a KeyError or a silent 1-day shift.
- Fix: the builder derives time from iters only (e2data.calendar.window), stores window_start as the time coord and raw iter alongside, and asserts boundaries.

F11. SCORING MASK
- The E2S wrappers write land as 0, so the eval's "finite jointly" mask would score land.
- Use mask = ocean_mask AND avail(t,c) AND finite(truth), taken from the store.

F12. PHYSICS CHECK A IS VACUOUS AFTER CLAMPING
- The wrappers clamp to non-negative, while truth has 11-18% negative CHL and 16.5% negative PIC (data §2).
- Score check A on pre-clamp output, and do not clamp asinh channels.

F13. MONTHLY STORMCAST (SC-M)
- E2S cannot step calendar months (fixed timedelta; e2s Q5.1).
- The eval wants 10 levels (k0..k9), but the builder makes k0 only.
- SC-M is therefore scored by the track2 scorer's own calendar-month loop, surface only. Label the inventory drift "not measured".
- The E2S chain is daily only; the monthly dx runs via nsteps=0 per month (e2s Q4).

F14. GRADING RULES CONFLICT
- The recipe §8 and eval rules differ:
  - deterministic pass: recipe needs >=2 of 4 Chl; eval needs >=2 of {DIC,ALK,FeT,PIC} plus +0.10 over N4T under G12/G6/G24/REV12;
  - diffusion pass: recipe uses "CRPS < regression MAE", which the eval rightly rejects;
  - SSR band: [0.8,1.2] versus [0.7,1.3];
  - diffusion seeds: 3 versus 1.
- The eval rules plus the finding §5 pre-test are the pre-registration. Delete recipe §8.
- Daily counted fields F_D = {CHL, pCO2(daily apCO2 dir), CO2_flux, O2_flux} need the raw download, so no daily verdict is possible from the cubes.

F15. NULL INFORMATION MATCHING, AND A MISSING NULL
- Eval N5 (ridge) uses coarse physics at the parent cell while the model gets fine physics, so the eval's own gate check 6 would exit 8.
- Make N5's inputs exactly the model's time-varying input set at the pixel.
- ADD an untrained-network null: the step-0 (initialised) checkpoint, run through the IDENTICAL E2S pipeline in the same job. Its skill against N1 must be <= 0 CI. This catches truth leaking through the background or the pipeline, and it is the repo's untrained-null habit.

F16. PACKAGE WRITER IS MISSING
- No part says how a rundir becomes an E2S package. Add track2/scripts/make_package.py. It:
  - resolves the Hydra config;
  - globs checkpoints_{regression,diffusion}/*.0.<step>.mdlus (the directory is named by net_name [V trainer.py:229, 251-253]; the diffusion class filename is [U]);
  - picks <step> by the scorer's deterministic val-period RMSE, not the trainer's val_loss. The diffusion val_loss is stochastic, and training loss is only divided by channel count [V trainer.py:828];
  - writes metadata.json (conditions, background_offsets, transforms, halo, grid_bounds_margin, sampler_type "stochastic" [V corrdiff.py:519-523 trap], commits, split, seeds), stats.json, grid nc files (ascending), normalised invariants.nc and the ocean mask.

F17. ENVIRONMENT
- earth2studio core requires pygrib [V e2s pyproject dependencies], and the repo pyproject says declaring earth2studio made `uv lock` unsatisfiable across target environments.
- track2/pyproject: [tool.uv] environments = ["sys_platform=='linux' and platform_machine=='x86_64'"]; requires-python ==3.12.*. track2 is Linux-only.
- The main package (builder, gate) stays usable on Windows.
- darwindiff's [tool.uv.sources] torch index does not propagate, so track2 declares its own cu128 index.
- netCDF4 is effectively 1.7.2 (darwindiff needs >=1.7; earth2studio needs <1.7.3). cp312 manylinux wheels [U].
- Remove natten from requirements: physicsnemo/nn/functional/natten.py uses OptionalImport("natten") [V gh api @536553a]. jaxtyping is a core dependency [V pn pyproject:41].
- warp-lang>=1.14 on sm_100 [U]; the M1 smoke test covers it.
- Build in a Slurm job. UV_CACHE_DIR and the venv go on /work (/scratch purges after 30 days). Compute-node egress to GitHub, PyPI and download.pytorch.org [U].
- Train and serve in the same environment so .mdlus class resolution matches.

=== P1: correctness and cost ===

F18.
- Launch with torchrun only; change run_id on every config change (auto-resume).
- Monthly per-tracer training has about 145 months; batch 16 for 20k steps is about 2,200 epochs. Select by val and expect the MEMORIZATION flag.

F19. Fix the double @batch_func [V src/darwindiff/e2s/prognostic.py:276, 282] before any reuse.

F20.
- E2S EccoDarwinZarr draft: add the `prep_data_inputs` import; never resolve to the nearest time.
- Serve land=0 only because the mask is applied after the transform (asinh(0)=0 is safe; log would not be).

F21. Diffusion inference budget [U]: 3,286 daily test days x 32 members x about 35 NFE at 640x1472. Measure it in M2. If needed, pre-register a test-day stride for the probabilistic metrics only.

F22. The HF `datasets` package must not be installed in track2, because the recipe discovers datasets/ relative to CWD [I]. Also delete data_loader_hrrr_era5.py from the copy, or keep its dask/xarray imports resolvable.

=== RAW LLC270 -> run.deterministic: WHAT HAS TO EXIST (items 1, 3, 5, 6, 7 and 8 are in no current spec as a concrete artifact) ===
1. darwindiff.e2data: calendar, grids (HR/LR above), RemapOp, transforms, stats, splits, climatology, AR(1) phi, `build monthly|daily|verify` (data §6), plus the F7 transforms module.
2. Zarr store on D: (monthly) and on AICR /work (daily).
3. track2/regional_weather_diffusion/datasets/ecco_darwin.py: the recipe draft rewritten onto zarr + e2data. Modes: S0 (downscaling mode, background = physics+doy, no coarse BGC), CD-SR, SC.
4. Configs, per the recipe drafts, with split name and physical channel names.
5. make_package.py (F16).
6. darwin_e2s: EccoDarwinZarr, DarwinStormCast (pass-through outputs per F5, background_offsets per F6), DarwinCorrDiff (ascending grids, internal LR halo/land-fill, identity invariant stats), and recipe_compat (vendored diffusion_model_forward with a parity test).
7. Parity tests:
   (a) the dataset sample through RWD regression_model_forward versus the wrapper _forward in mode="regression", within 1e-5;
   (b) e2data.upsample_bilinear versus the E2S interp arithmetic.
8. Scorer (eval §8) that reads the E2S zarr, and the gate scripts/verify_e2_run.py (eval §7), with the F11/F15 changes.

=== ORDERED BUILD PLAN ===

M0: local Windows, CPU, main package.
- Tasks: e2data builder on the monthly mirror; `build verify`; gate skeleton plus synthetic tests; pre-registration amendment committed (grid F1, split F3, F4, F14, F15 untrained null, S0 at LR).
- Done when:
  - verify passes: 2232 maps to 1992-01; 546,695 ocean cells; land exactly 0; A(HR)==LR exact; inverse(forward) within 1e-6; no NaN in the LR halo; split sets disjoint; gap respected;
  - tests/test_verify_e2_run.py passes;
  - the amendment commit time precedes any sbatch. Availability counts are printed by the builder, never copied from the specs.

M1: AICR B200, 1 GPU, one Slurm job.
- Tasks: build the track2 env in-job; run the upstream tests (README.md:60-78 command); synthetic-store smoke of BOTH stages, including model.regression_weights (untested upstream, test_training.py:116, 207); make_package; parity tests 7a/7b; E2S Stage-0 chain (run.deterministic(DiagnosticWrapper(px, dx))) on a 32x64 toy and on the real LR/HR grids with 10-step checkpoints, plus the Persistence and untrained nulls through the same pipe.
- Done when:
  - zarr dims are (time, lead_time, sample, lat, lon);
  - land is 0 and ocean is finite;
  - parity holds within 1e-5;
  - everything runs in one job id. Plumbing only, no skill numbers.

M2: AICR, SEPARATE jobs per size.
- Task: 20-step probes at LR 160x360 and HR 640x1472 for the candidate widths, plus a diffusion inference timing. Cube data is allowed here.
- Done when there is a gpumem and s/step table. It is budgeting, not a result.

M3: AICR (track2 is Linux-only; the pre-registration's "5090 or CPU" becomes WSL2 at most) [U].
- Task: S0 physics-to-BGC diagnostic, regression only, 5 seeds, per tracer, LR 1 deg, G12, Job A with all nulls in-job.
- Done when:
  - verify_e2_run exits 0 and the verdict prints;
  - the research-map row is committed;
  - THEN Job B (fresh seeds 100-104, G6/G24/REV12) is submitted and passes on its own numbers.
- STOP closes CD/SC entirely (finding:193-196); M1 plumbing remains engineering only.

M4: AICR. Only if M3 passes.
- Task: CD-SR monthly LR->HR regression, per tracer group, rule D, Job A then B.

M5: AICR. Only if D passes.
- Task: diffusion stage, rule P against the dressed-regression and deep-ensemble nulls; the dx is served via run.deterministic with nsteps=0 per month over DataReplay.

M6: AICR, CPU Slurm, when data.nas answers.
- Tasks: curl 206 range test (data §4); download the 12 core 2-D variables; `build daily` to /work; verify.
- Done when every file is 3,790,800 B and verify passes.

M7: AICR.
- Task: SC-D daily prognostic regression on LR with physics(t+1) background (no apCO2). Nulls: persistence, climatology, trend-climatology, seasonal AR(1), ARX(1), untrained. Compute H*, Job A/B.

M8: AICR.
- Task: the chain, run.deterministic and run.ensemble(DiagnosticWrapper(DarwinStormCast, DarwinCorrDiff)) over test inits, with the nulls through the identical pipeline; gate.

M9: bench (eval §5; speedup stays UNKNOWN until the reference cost arrives); map rows plus `research_map_db.py check` in the same commit.
