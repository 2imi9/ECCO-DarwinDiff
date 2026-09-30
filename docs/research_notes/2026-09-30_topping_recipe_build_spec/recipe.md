# PhysicsNeMo regional_weather_diffusion: training spec (CorrDiff-like and StormCast-like)

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

I've written an exact training spec for both modes against NVIDIA/physicsnemo main at 536553acf5b03b68ec7283975ba7276d60056a36 (2026-09-30), recipe examples/weather/regional_weather_diffusion. It comes with a draft dataset class, two Hydra configs, a store builder and a generation script. How far each was tested:

- **Two configs:** they pass the recipe's own pydantic check for both the regression and the diffusion stage.
- **Dataset class and store builder:** both passed end-to-end checks on synthetic stores, with a real torch DataLoader using spawn workers. The checks cover shapes, dtypes, masks, padding, the longitude halo, the split, pair gaps and the DictConfig path.
- **Not tested:** nothing ran through the physicsnemo trainer, because physicsnemo is not installed locally. The generation script is syntax-checked only.

What I found in the code:

1. **One recipe does both modes.** The dict that `__getitem__` returns and two condition lists decide the mode:
   - Downscaling: background plus invariant into the regression net, background plus regression plus invariant into the diffusion net; the dataset returns `{background, state: target}`.
   - Forecasting (StormCast): state plus background plus invariant into the regression net, state plus regression plus invariant into the diffusion net; the dataset returns `{background, state: [t, t+1]}`.
2. **Input and output grids must match.** Every input is concatenated along the channel axis. So the coarse input has to be regridded to the fine grid inside the dataset or store.
3. **The two stages are separate runs.** You pick the stage with `training.loss.type` (regression or edm), not with `model.model_name`. The handoff is `model.regression_weights` pointing at `StormCastUNet.0.<step>.mdlus`.
4. **The dataset owns normalisation, time, split and the mask.** The mask is 1 for valid pixels and becomes a per-pixel loss weight.
5. **NaN must be zero-filled after normalisation.** The loss is `weight*(pred-x0)^2`, and 0 × NaN is still NaN.
6. **There is no CorrDiff-style patch training.** Large grids rely on bf16, gradient accumulation, activation checkpointing, or domain parallelism (which needs a local batch of 1).
7. **SongUNet needs H and W to be multiples of 2^(levels−1).** A 721-row grid can never work. Use 720×1440 at 0.25°, or pad; the draft pads and adds a periodic longitude halo that is masked out of the loss.
8. **The upstream StormCast configs are broken on main.** `regression.yaml` and `diffusion.yaml` fail the recipe's own validation, because `model/stormcast.yaml` has a stray `model_type` key and `diffusion.yaml` has `use_regression_net`. I reproduced this with pydantic 2.13.5.
9. **Plain `python train.py` should fail.** Reading the code, it has no process group and so fails when it builds the device mesh. Always launch with `torchrun`, even on one GPU. This is inferred from the code, not executed.
10. **`inference.py` only works for HRRR,** so a replacement is included.
11. **The regression-to-diffusion handoff is not covered by the upstream tests** (`use_regression` is only ever False). The first smoke test has to exercise it.
12. **The old corrdiff example is not needed for training.** It matters only if you want no glue code with earth2studio's generic `CorrDiff.load_model`: that path calls legacy models with the old call signatures, which the new checkpoints (StormCastUNet and EDMPreconditioner) do not match. The old recipe also has no loss mask, so it would train on filled land.
13. **Environment:** put this in a separate uv project, pinned to this physicsnemo SHA and earth2studio 2067756d, with torch 2.11.0+cu128 and netCDF4 below 1.7.3. Train on Linux (AICR B200 or Explorer H200). natten and apex are not needed for the UNet path, and Windows distributed training is unverified.

**Recommended first runs** use the surviving AICR daily cubes, which avoids waiting on data.nas.nasa.gov (unreachable as of 2026-09-30):
- Downscaling from 1° to 0.5° on surfChl1, 2, 3 and 5.
- A one-day forecast at 0.5°, driven by SST and wspeed.

Grading follows the finding's section 5: nulls fitted on training data only, deterministic skill judged from the regression stage alone, and the diffusion stage judged only on CRPS, spread and spectra.

## Decisions

- **Which PhysicsNeMo recipe to train with** → examples/weather/regional_weather_diffusion pinned at 536553acf5b03b68ec7283975ba7276d60056a36. Keep the old examples/weather/corrdiff for reference only.
  - why: Only the new recipe has a per-pixel loss mask, which ocean land needs; the old train.py has no mask at all. It also does forecasting and downscaling with one dataset contract and is maintained. The old one is deprecated (corrdiff/README.md:4-10). Its one advantage, zero-glue loading into earth2studio's generic CorrDiff.load_model, costs a small wrapper, and so does the StormCast wrapper, which is HRRR-hardwired anyway.
- **Which network architecture** → architecture: unet with model_type SongUNet, no additive_pos_embed or SongUNetPosEmbd. Position comes from invariants (ocean mask, sin/cos lat and lon).
  - why: It is the StormCast and CorrDiff architecture. It needs no natten (DiT only, Linux wheels keyed to torch 2.10), and bf16 is fine for UNets (README.md:229). It also stays resolution-agnostic (song_unet.py:115-119), so the same net can later be tried on crops or other grids.
- **Where the model config comes from** → Write self-contained top-level configs (the drafts) that pull only training/default, sampler/edm_deterministic and hydra/default. Never include model/stormcast, and never copy regression.yaml or diffusion.yaml.
  - why: On main these fail the recipe's own pydantic validation: model/stormcast.yaml has a top-level model_type key and diffusion.yaml adds use_regression_net, both rejected by extra="forbid" (utils/config.py:24). I reproduced the failure; only the test_* configs pass.
- **How to switch between regression and diffusion** → One config per mode. Stage 2 is launched with overrides: training.loss.type=edm, model.regression_weights=<.../StormCastUNet.0.N.mdlus>, a new experiment_name, and total_train_steps.
  - why: The trainer picks the network from training.loss.type (utils/trainer.py:228-229); model.model_name is never read. Stage 2 rebuilds the regression input from cfg.model.regression_conditions, so keeping one file guarantees the lists match.
- **Grid and data for the first runs** → Start on the surviving AICR daily cubes. Downscaling: 1° to 0.5° on log10 surfChl1, 2, 3 and 5, with coarse Chl, SST and wspeed upsampled as background. Forecasting: 0.5°, one day ahead, with SST and wspeed at t+1 as background. The 341x720 grid is padded to 344 rows with an 8-column periodic longitude halo, giving 344x736. Later use 720x1440 at 0.25° (never 721 rows), with channel_mult of length 5 and padding to multiples of 16.
  - why: This needs no download: data.nas.nasa.gov was unreachable on 2026-09-30 and the raw daily data is not on disk. The daily cubes give about 9,463 samples, against 158-313 for monthly, where diffusion memorises. SongUNet requires H and W to be multiples of 2^(levels−1) (song_unet.py:558-571), and 721 is odd.
- **When the forecasting background is taken** → background_time: target, i.e. ECCO physics at t+1. "input" (StormCast literal) and "both" remain available as options.
  - why: In an offline biogeochemistry emulator the physics at t+1 is known from ECCO when a scenario runs, and it is the forcing that drives the t to t+1 change. The flag keeps the literal StormCast setup available as an ablation.
- **Data store and normalisation** → Pre-build .npy memmap stores (state, background, invariants, ocean_mask) plus stats.json in earth2studio CorrDiff format, with statistics from training years only. The dataset normalises, then zero-fills NaN, and carries land and invalid pixels in a per-channel mask.
  - why: The recipe never normalises (dataset.py:56-57). A NaN poisons weight*(pred-x0)^2 even at weight 0 (losses.py:679). Memmaps opened lazily are fast and safe with spawn workers, and stats.json can be reused unchanged when serving.
- **sigma_data** → Keep training.loss.sigma_data at 0.5.
  - why: utils/nn.py:93 constructs EDMPreconditioner without sigma_data, so it uses its default of 0.5 (preconditioners.py:1039). Changing the config value only changes the loss weighting in the noise scheduler (utils/loss.py:60-82), which makes it inconsistent with the preconditioning. Changing it properly would need a patch to utils/nn.py.
- **How to launch** → Always torchrun --standalone --nproc_per_node=N from the recipe folder, even for one GPU, on Linux (AICR B200 or Explorer H200). Inside Slurm, run torchrun in the sbatch script and build the env inside a Slurm job.
  - why: ParallelHelper always builds a DeviceMesh, and that raises without an initialised process group (parallel.py:62-76; manager.py:476-486, 539-546). The datasets/ lookup is relative to the working directory (datasets/__init__.py:24). Windows would fall back to gloo with FSDP2, which is unverified.
- **Environment** → A separate uv project, track2/, with its own lock. Pin physicsnemo 536553a and earth2studio 2067756d by git SHA, torch 2.11.0 from the cu128 index, netCDF4>=1.7,<1.7.3, and darwindiff as an editable path dependency. Install physicsnemo with the datapipes, nn and utils extras. Leave out natten, apex, transformer-engine and the cu12/cu13 extras.
  - why: earth2studio's netCDF4<1.7.3 conflicts with the repo lock's 1.7.4 (uv.lock:1914-1915), and uv workspaces share one lock. The recipe exists only on main, so a git pin is the only reproducible choice.
- **Serving through earth2studio** → Write thin DarwinCorrDiff (DiagnosticModel) and DarwinStormCast (PrognosticModel) wrappers that call the recipe's utils/nn functions and load checkpoints with generic Module.from_checkpoint.
  - why: earth2studio's CorrDiff calls legacy samplers with the old model call signatures (corrdiff.py:1021-1100; legacy_deterministic_sampler.py:444-460), and the new checkpoints do not match. Its StormCast call order already matches the forecasting config, but it hardwires the HRRR grid (stormcast.py:182-191, 318-328).
- **Grading** → Grade against nulls fitted on training years only: persistence or upsampled-coarse, per-cell climatology, a climatology-corrected coarse field or anomaly AR(1), and per-cell ridge. The regression stage must pass first (5 seeds, block-bootstrap CI above 0, forward and reversed split). The diffusion stage is judged only on CRPS, spread-skill and spectra, with ensemble-mean RMSE allowed at most 3% worse. Everything is replicated in a fresh job.
  - why: This is the settled map row: diffusion adds no deterministic skill (CorrDiff Table 1; finding §2). It also applies the finding §5 pre-test, the per-cell climatology null that CLAUDE.md requires, and the rule that a replication must be a fresh submission.

## Risks

- The regression-to-diffusion handoff (model.regression_weights) is never exercised by upstream tests (test_training.py:116 and 207 set use_regression=[False]). The P0 smoke test on a synthetic store must run both stages before any real job.
- Plain `python train.py` on one GPU should fail at initialize_mesh, which contradicts README.md:94. That is inferred from code, not executed; torchrun is the safe path either way.
- The reference StormCast configs are broken on main (pydantic extra=forbid on model_type and use_regression_net). Anyone copying regression.yaml or diffusion.yaml fails at startup.
- Re-running with the same training.rundir silently resumes the old checkpoint (utils/trainer.py:711-753), even after a config change. Always change run_id.
- The trainer validates only the first validation_steps × batch unshuffled samples (utils/trainer.py:913-923). Without valid_stride this is January to May of the first validation year. The validation loss is also diluted by masked pixels (utils/trainer.py:970).
- Training loss is summed over pixels and divided only by channel count (utils/trainer.py:828), so its scale grows with grid size and valid-pixel count. clip_grad_norm thresholds do not transfer between grids.
- Gradients are NaN-cleaned (utils/trainer.py:857-862), so a NaN leak in the data would train silently instead of crashing. The draft dataset asserts finiteness after zero-fill, but any new dataset must as well.
- Memory estimates are my arithmetic (±2x). A CUDA out-of-memory error poisons the context, so probe each size in a separate job.
- The downscaling task is super-resolution of block averages of the same native run (finding §4: "downscaling has no user"). The coarse-upsampled plus climatology null may be very hard to beat at 1° to 0.5°.
- Monthly variants (DIC, ALK, FeT, PIC, POC) have 158-313 samples, where diffusion denoisers memorise. Treat them as data-bound.
- The builder loads whole npz members into RAM, about 56 GB for the 0.5° daily cube if float32 (arithmetic). Run it on a big-memory compute node, not the login node.
- Integer-halving grids: bilinear upsampling assumes both cubes share the same longitude origin and a -80..90 node-centred latitude axis, which is inferred from the shapes 171 and 341. Wrong axes give a silently shifted background.
- The draft generate_ecco.py and the earth2studio wrappers are untested. A condition-order mismatch between training and serving produces plausible but wrong output.
- Diffusion training re-runs the frozen regression net every step (utils/nn.py:202-212). Step time is higher than regression-only; budget for it after the probe.
- Global zero-padded convolutions leave a seam at the dateline without the periodic halo. The draft adds one, but the halo width versus receptive field has not been tuned.

## Unknowns

- The exact npz keys, dtypes, latitude axis and longitude origin of AICR daily_global_1deg_cube.npz and daily_global_halfdeg_cube.npz. Unverified; check with np.load(p).files before building stores.
- Whether FSDP2, DeviceMesh and the gloo backend work for single-GPU training on native Windows. Unverified; I recommend Linux or WSL2.
- Real per-sample GPU memory and step time at 344x736 and 720x1472 for the chosen widths. Unverified; the probe decides.
- Whether data.nas.nasa.gov is reachable now, and whether it supports HTTP Range requests, so only the surface level of the 50-level pCO2/pH files would be fetched. Unverified; I did not read D:\ecco_darwin_v5\download_daily.sh.
- Whether uv resolves earth2studio's nvidia-physicsnemo>=2.0 requirement against the 2.3.0a0 git pin without prerelease flags. Unverified.
- Python version and installed packages of the AICR ~/dd_venv (torch 2.11.0+cu128 per the brief). Not checked; no ssh per the rules.
- The effect of the double @batch_func() on DarwinBGCPrognostic.__call__ (src/darwindiff/e2s/prognostic.py:276, 282) under real earth2studio. Unverified.
- Whether ShardTensor domain parallelism needs H/k to be a multiple of 2^(levels−1) for SongUNet down-sampling. Unverified; only relevant if a full-grid sample does not fit on one GPU.
- Whether the Chl log10 floor of 1e-4 is appropriate for surfChl3 and surfChl5 minima in v05. Not measured; the builder records it in meta.json so it can be revisited.

## Spec

== DRAFT SPEC: ECCO-Darwin v05 x PhysicsNeMo regional_weather_diffusion (CorrDiff-like downscaling + StormCast-like forecasting) ==

0. PROVENANCE AND PINS
- physicsnemo main SHA 536553acf5b03b68ec7283975ba7276d60056a36 (committed 2026-09-30T14:15Z; __version__ "2.3.0a0"). Recipe commits: fada79f449 "migrate stormscast recipe (#1977)" 2026-09-10 and d25b6361e1 "Regional model recipe tweaks (#1993)" 2026-09-15. Not in the v2.2.2 tag (the contents API returns 404). PyPI latest is 2.2.2.
- earth2studio main SHA 2067756d489ad9195cf9e1ed52e074a4f8588ca4 (2026-09-30).
- Local copies I read (scratchpad, not the repo): C:\Users\Frank\AppData\Local\Temp\claude\C--Users-Frank-OneDrive-Desktop-Github-ecco-darwindiff\b9d5a7a9-6b05-4538-98d0-9e15bcf9debc\scratchpad\pn\examples\weather\{regional_weather_diffusion,corrdiff}\ and ...\scratchpad\e2s\.
- All recipe paths below are relative to examples/weather/regional_weather_diffusion/ at the pinned SHA.

1. (Q1) DOWNSCALING vs FORECASTING IN THE RECIPE
- Mode = condition lists + the dict returned by the dataset (README.md:115-137; mock.py:79-92; test_training.py:766-773).
  | mode | model.regression_conditions | model.diffusion_conditions | __getitem__ returns |
  |---|---|---|---|
  | downscaling (CorrDiff) | ["background","invariant"] | ["background","regression","invariant"] | {"background": B, "state": target, "mask": M} |
  | forecasting (StormCast) | ["state","background","invariant"] | ["state","regression","invariant"] (model/stormcast.yaml:22-23) | {"background": B, "state": [s_t, s_t+1], "mask": M} |
  Allowed values: regression ⊆ {state, background, invariant}; diffusion ⊆ {state, regression, background, invariant} (utils/config.py:32-37). List order = concatenation order (utils/nn.py:214-217).
- Meanings:
  - state: the fine field. state[1] is the training target. state[0] is the previous step and is used only if "state" is in the condition list. A single tensor becomes [None, x] (utils/nn.py:238-240).
  - background: any per-sample conditioning on the SAME grid. In StormCast it is ERA5 interpolated to the HRRR grid (datasets/data_loader_hrrr_era5.py:364-368).
  - invariant: get_invariants() -> np.ndarray (C_i,H,W), repeated to the batch; there is NO dtype cast, so return float32 (utils/trainer.py:357-364).
  - regression: output of the frozen stage-1 net. The diffusion target becomes state[1] - regression (utils/nn.py:201-212).
  - mask: a loss weight, not a condition (see section 2).
- Grid sizes CANNOT differ. Every condition is torch.cat'ed on dim 1 (utils/nn.py:217), and the UNet is built for one img_resolution = dataset.image_shape() (utils/trainer.py:439-448). A coarse input must be regridded to the fine grid by the dataset or store, as the old CorrDiff also did (corrdiff/datasets/base.py image_shape: "same for input and output").
- Stages:
  - Separate runs, regression first, then diffusion (README.md:36, 154-162).
  - The stage is chosen by training.loss.type ('regression' -> StormCastUNet; 'edm' -> EDMPreconditioner(ConcatConditionWrapper(SongUNet))) (utils/trainer.py:228-229; utils/nn.py:84-100).
  - model.model_name, model.spatial_pos_embed and model.attn_resolutions are validated but never read (grep). UNet settings go in model.hyperparameters.
  - Handoff: model.regression_weights = path to .../checkpoints_regression/StormCastUNet.0.<step>.mdlus. It is loaded with Module.from_checkpoint, set to eval, frozen, and re-run on every diffusion step (utils/trainer.py:568-595).
  - Stage 2 rebuilds the regression input from cfg.model.regression_conditions (utils/trainer.py:793), so keep that list identical to stage 1.
  - Diffusion-only: remove "regression".
  - Upstream tests never run the handoff (test_training.py:116, 207: use_regression = [False]).

2. (Q2) DATASET CONTRACT (datasets/dataset.py:23-115)
- Class: subclass StormCastDataset in a module under datasets/. Select it with dataset.name: "<module>.<Class>" (datasets/__init__.py:24-35).
  - Discovery runs pkgutil.iter_modules(["datasets"]), which is relative to CWD, so launch from the recipe folder.
  - It imports EVERY module in datasets/, so the HRRR loader's dask/xarray imports must resolve, or delete that file from your copy.
- Constructor: __init__(params, train).
  - params is a plain dict in training (utils/trainer.py:332-336, pydantic extras via __dict__; verified).
  - params is an OmegaConf DictConfig that still contains "name" in inference.py:50.
  - Use params.get / params[...] only; attribute access breaks the dict path.
- Required methods:
  - __len__
  - __getitem__ -> dict. Values are np.ndarray or torch.Tensor; unpack_batch casts background, state and mask to float32 (utils/nn.py:242-248) and lead_time_label to int64.
  - background_channels() -> list[str], whose length is C_b.
  - state_channels() -> list[str], whose length is C_s.
  - image_shape() -> (H, W).
- Optional methods:
  - get_invariants() -> np.ndarray float32 (C_i,H,W) or None.
  - scalar_condition_channels() (DiT only; a UNet raises, utils/trainer.py:375-380).
  - lead_time_steps attribute plus "lead_time_label" (UNet only).
  - normalize_/denormalize_{state,background} and latitude()/longitude(); only inference.py uses these.
- Shapes:
  - background (C_b,H,W).
  - state (C_s,H,W), or [ (C_s,H,W), (C_s,H,W) ].
  - mask broadcastable to (C_s,H,W): (1,H,W), (C_s,H,W) or (C_s,1,1), values in {0,1} (1 = valid) (dataset.py:42-54).
- Normalisation: done by the dataset and never by the trainer (dataset.py:56-57). The stats format is up to you. HRRR uses means.npy/stds.npy per channel (data_loader_hrrr_era5.py:93-109, 327-353). The draft uses stats.json in earth2studio CorrDiff's keys, {"input":{v:{mean,std}},"output":{...}} (earth2studio/models/dx/corrdiff.py:719-741), so it can be reused when serving.
- Time: the recipe has no time handling. The dataset maps idx -> sample itself (HRRR: valid_samples list, data_loader_hrrr_era5.py:271-325). inference.py indexes dataset[i + hours_since_jan_01], which is HRRR-specific (inference.py:73-75, 105).
- Split:
  - The recipe builds two instances, train=True and train=False (utils/trainer.py:335-336). HRRR splits by train_years/valid_years (data_loader_hrrr_era5.py:160-181).
  - Validation uses a fresh, UNSHUFFLED loader and only the first validation_steps batches (utils/trainer.py:913-923). The draft therefore strides the validation index (valid_stride).
- NaN and land:
  - The recipe does no NaN handling in the data path. It only runs nan_to_num on GRADIENTS (utils/trainer.py:857-862), which hides a NaN loss rather than preventing it.
  - The loss is weight*(x0_pred-x0)^2 (physicsnemo/diffusion/metrics/losses.py:679; utils/loss.py:133), and 0*NaN = NaN. So zero-fill every array AFTER normalisation and carry land in the mask.
- How the mask enters the loss (utils/trainer.py:467-566, 800-801):
  - For a UNet, weight = 1 - (mask < 0.5). It is multiplied by channel_loss_weights (1,C,1,1) (utils/trainer.py:382-399) and applied per pixel.
  - With DiT and use_nan_mask_tokens, the mask is pooled to token level.
  - Training loss = loss.sum()/C over B,H,W (utils/trainer.py:828), i.e. unnormalised by valid-pixel count.
  - Validation loss = mean over all pixels including masked ones (utils/trainer.py:970), so it is diluted by the land fraction. Do not compare val_loss across grids or masks.

3. (Q3) LARGE DOMAINS, PATCHING, MEMORY
- No CorrDiff-style patch training: no patch_shape/patch_num in the recipe (grep). physicsnemo.diffusion.multi_diffusion (RandomPatching2D, GridPatching2D, MultiDiffusionWeightedMSEDSMLoss) exists at the SHA but the recipe does not use it.
- The levers are:
  - bf16 (training.perf.fp_optimizations=amp-bf16; README.md:229 says it is fine for UNets).
  - training.batch_size_per_gpu with automatic gradient accumulation (utils/trainer.py:206-217).
  - SongUNet checkpoint_level in hyperparameters (song_unet.py:169-173, 350-354).
  - Domain parallelism via training.domain_parallel_size=k: it shards H across k GPUs, needs a local batch of 1 (utils/trainer.py:120-125) and torch>=2.10 (README.md:50, 201-211), and skips torch.compile.
- Grid-size rule: each spatial dim must be a power of 2 below 2^(N-1), or a multiple of 2^(N-1), with N = len(channel_mult) (song_unet.py:558-571).
  - 721 rows is impossible for any N >= 2.
  - 720x1440 works with N <= 5. 680x1440 (the AICR 3-D cube) works with N <= 4. 341x720 must be padded (the draft pads to 344).
  - additive_pos_embed and SongUNetPosEmbd tie the net to one H,W (song_unet.py:115-119). Keep plain SongUNet and give position through invariants.
- Dataset-level random crops are possible only without additive_pos_embed or invariants: invariants are one fixed full-grid tensor (utils/trainer.py:357-364), so crop-varying lat/lon would have to go in background. Not recommended for a first run.
- Memory (my arithmetic, unverified, +/-2x; decide with a probe):
  - 0.5° (344x736 = 0.25 M px), model_channels 64, channel_mult [1,2,2,2], num_blocks 2: about 3-6 GB per sample in bf16. Batch 16 fits one B200; a 5090 would need batch_size_per_gpu of about 4.
  - 0.25° (720x1472 with a 16-column halo = 1.06 M px), model_channels 128, [1,2,2,2,2]: about 25-50 GB per sample. Local batch 2-4 on a B200. It does not fit a 5090 without checkpoint_level and a width of 64.
  - Anchor: StormCast (512x640, SongUNet defaults) trains at local batch 1 per H100 (batch 64 on 64 GPUs; README.md:175, 227).
- Probe: run 20 steps per candidate size in SEPARATE jobs (a caught OOM poisons the CUDA context) and read "gpumem" in the progress line (utils/trainer.py:1057-1069, print_progress_freq=5).

4. (Q4) LAUNCH, OVERRIDES, OUTPUTS
- Always launch with torchrun, even on one GPU.
  - ParallelHelper always calls DistributedManager.initialize_mesh (utils/parallel.py:62-76). initialize_mesh raises when manager.distributed is False (physicsnemo/distributed/manager.py:539-546).
  - A plain `python train.py` without RANK/WORLD_SIZE falls into the "single process job" branch (manager.py:476-486), which never sets _distributed.
  - This is inferred from the code, not executed. README.md:94 shows plain python.
- Commands, run from the recipe copy:
  - 1 GPU: `torchrun --standalone --nnodes=1 --nproc_per_node=1 train.py --config-name ecco_forecasting training.run_id=s1 training.seed=1`
  - 4 GPUs: `torchrun --standalone --nnodes=1 --nproc_per_node=4 train.py --config-name ecco_forecasting training.batch_size=16`. The batch must divide by world size (README.md:195-199).
  - Stage 2: add `training.loss.type=edm training.total_train_steps=60000 model.regression_weights=<.../StormCastUNet.0.20000.mdlus> training.experiment_name=fc_diff`.
  - Upstream tests: `torchrun --standalone --nproc_per_node=1 --no-python pytest test_training.py -k "test_model_types or test_masking or test_channel_loss_weights" -x` (README.md:60-78).
  - Slurm (AICR): run torchrun inside sbatch; build the env inside a Slurm job.
- Overrides are Hydra key=value. Keys absent from the YAML need "+", e.g. `+training.scheduler.T_max=...`.
- Resume and walltime:
  - Same rundir means AUTO-RESUME from the latest checkpoint (utils/trainer.py:711-753). Change training.run_id whenever the config changes.
  - Use training.max_run_steps to chunk runs to the Slurm walltime.
- Outputs under training.rundir = ./rundir/<experiment_name>/<run_id>:
  - checkpoints_regression/StormCastUNet.0.<step>.mdlus + checkpoint.0.<step>.pt, or checkpoints_diffusion/EDMPreconditioner.0.<step>.mdlus + checkpoint.0.<step>.pt (utils/trainer.py:251-253, 1081-1095; test_training.py:185-201).
  - .mdlus is a physicsnemo Module archive holding model.pt plus constructor args, loaded with physicsnemo.core.Module.from_checkpoint. .pt holds optimizer, scheduler and metadata {val_loss} (physicsnemo/utils/checkpoint.py:534-567, 724-812).
  - images/<var>/<step>_<i>_<var>_{generated,truth,input,background_*,spec}.png (utils/plots.py:155-216). tensorboard/ (utils/logging.py:56-60).
- Inference: inference.py plus config stormcast_inference.yaml. It writes {inference.rundir}/data.zarr, ds_pred_edm.nc, ds_pred_noedm.nc, ds_targ.nc and out_{i}.png (utils/io.py:31, 227-229; inference.py:190).
  - It is HRRR-only (README.md:254): hourly indexing, HRRR vertical variables, and it requires invariants.
  - Use the draft generate_ecco.py below instead.

5. (Q5) DEPENDENCIES
- physicsnemo main: python >=3.11,<3.15; torch>=2.10.0; warp-lang>=1.14; tensordict[zarr]>=0.14; hydra-core>=1.3.2; fsspec>=2026.4.0 (pyproject.toml:13-49).
  - The README asks for extras datapipes-extras (pandas, tfrecord, dask, netCDF4, xarray>=2025.6.1, zarr>=3), nn-extras (scipy + utils-extras) and utils-extras (wandb, mlflow>=3.12, line_profiler) (pyproject.toml:288-315; README.md:46).
- Recipe requirements.txt: pyproj, pydantic, torch>=2.10, tensorboard, matplotlib, xarray, wandb, dask, natten.
  - wandb and tensorboard are imported at module level (utils/logging.py:24-25; utils/plots.py:22), so they are required even when logging is off.
  - pandas is needed by inference.py.
- natten is DiT-only and imported lazily; skip it for the UNet path. Its wheel index is keyed to torch 2.10.0 (pyproject.toml:117-127).
- earth2studio (2067756d) requires netCDF4>=1.6.4,<1.7.3 (pyproject.toml:22) and zarr>=3.1.3. Its corrdiff extra needs physicsnemo>=2.0. Its own uv sources pin physicsnemo git 426f7552 (pyproject.toml:417-419); that pin does not propagate to dependents.
- The repo pins netcdf4 1.7.4 and torch 2.11.0+cu128 (uv.lock:1914-1915, 3180-3182); darwindiff needs python <3.14 and netcdf4>=1.7 (pyproject.toml:10, 39). So create a SEPARATE uv project, per docs/findings/2026-09-30_earth2_air_pollution_recipe_is_not_a_track2_lever.md:246-251:
  track2/pyproject.toml (draft): requires-python ">=3.12,<3.14"; dependencies = [darwindiff, torch==2.11.0, nvidia-physicsnemo[datapipes-extras,nn-extras,utils-extras], pydantic>=2, hydra-core>=1.3.2, tensorboard, matplotlib, wandb, dask, xarray, pyproj, pandas, netCDF4>=1.7,<1.7.3]; optional serve = [earth2studio]; [tool.uv.sources] darwindiff={path="..",editable=true}, nvidia-physicsnemo={git="https://github.com/NVIDIA/physicsnemo",rev="536553acf5b03b68ec7283975ba7276d60056a36"}, earth2studio={git="https://github.com/NVIDIA/earth2studio",rev="2067756d489ad9195cf9e1ed52e074a4f8588ca4"}, torch={index="pytorch-cu128"}; index pytorch-cu128 = https://download.pytorch.org/whl/cu128 (explicit).
  Copy the recipe folder at the SHA into track2/regional_weather_diffusion/ and add datasets/ecco_darwin.py plus the two configs.
- Windows, all unverified:
  - natten has no Windows build path in the pins.
  - apex (optional) needs a source build.
  - Do not use the cu12/cu13 RAPIDS extras.
  - The runtime needs torch.distributed + DeviceMesh + FSDP2 fully_shard even on one GPU. On Windows the backend falls back to gloo (manager.py:303-308), and I have not verified FSDP2 on gloo with CUDA.
  - torch.compile needs triton.
  - Train on Linux (AICR B200 / Explorer H200, or WSL2). Use the 5090 for the dataset and builder unit tests only.

6. (Q6) OLD examples/weather/corrdiff
- Deprecated banner (corrdiff/README.md:4-10), but still present on main; its imports resolve at the SHA (static check). It is not needed for training. The delta:
  | | old corrdiff | regional_weather_diffusion |
  |---|---|---|
  | nets | CorrDiffRegressionUNet + EDMPrecondSuperResolution (corrdiff/train.py:37-38, 220) | StormCastUNet + EDMPreconditioner(ConcatConditionWrapper(SongUNet/DiT)) |
  | dataset | DownscalingDataset (corrdiff/datasets/base.py): tuple (img_clean, img_lr[, lead_time_label]), ChannelMetadata, time() | StormCastDataset dict |
  | loss mask | none (no "mask" in corrdiff/train.py) | per-pixel + per-channel |
  | patching | RandomPatching2D, hp.patch_shape_x/y, patch_num (corrdiff/train.py:260-282) | none; domain parallel |
  | forecasting | no | yes |
  | duration | samples (hp.training_duration) | steps (total_train_steps) |
  | earth2studio CorrDiff.load_model | callable path | not callable |
- Why the new checkpoints are not callable by earth2studio CorrDiff:
  - load_model reads a package {diffusion.mdlus, regression.mdlus, metadata.json, stats.json, output_latlon_grid.nc, [input_latlon_grid.nc]} (corrdiff.py:626-770). It then calls legacy regression_step (net(x=..., img_lr=...), legacy_generate.py:90-92) and legacy samplers (net(x, x_lr, sigma, class_labels) unless net is the legacy EDMPrecond, legacy_deterministic_sampler.py:444-460).
  - The new models take forward(x) (StormCastUNet) and forward(x, t, condition=) (EDMPreconditioner), and the new EDMPreconditioner is not an EDMPrecond subclass (legacy.py:566).
  - So serve with a small subclass or wrapper instead:
    - DarwinCorrDiff (earth2studio DiagnosticModel): reuse CorrDiff's grid, stats and package handling; override _forward (corrdiff.py:1021-1100) to call the recipe logic, i.e. regression_model_forward, build_network_condition_and_target and diffusion_model_forward (utils/nn.py:160-392).
    - DarwinStormCast (earth2studio PrognosticModel): copy earth2studio/models/px/stormcast.py _forward (lines 369-420). Its concat order (state, background, invariant) -> (state, regression, invariant) matches the forecasting config. Load both nets with generic Module.from_checkpoint instead of EDMPrecond.from_checkpoint (stormcast.py:318-323), and drop the HRRR grid (stormcast.py:182-191).
  - Both wrappers must zero-fill normalised NaN, undo the halo and padding, and re-mask land exactly as in training.
- Use the old recipe only if zero-glue earth2studio CorrDiff loading or patch training becomes a hard requirement.

7. ECCO-DARWIN BUILD PLAN
- Data today (finding doc:45-55): the surviving cubes are on AICR /work/neu/p2026_0089_neu/cubes/ (snapshotted, not purged):
  - daily_global_1deg_cube.npz: 9,463 days x {surfChl1,2,3,5} + {SST, wspeed}, 171x360.
  - daily_global_halfdeg_cube.npz: the same at 341x720.
  - global3d_L10_cube.npz: 158 months, 680x1440.
  - Raw daily data is not on disk, and data.nas.nasa.gov:443 was unreachable on 2026-09-30.
  - The npz keys and the lat/lon origin are UNVERIFIED. Check np.load(p).files first. emulator_poc --dump-cube writes state, valid_mask, forcing, times_days, iters, chan_names, forc_names, grid_shape and n_z, with no lats/lons (scripts/emulator_poc.py:1401-1411).
  - The shape 341 implies -80..90 at 0.5° (inferred).
- First runs: D1 downscaling 1°->0.5°, with background = 6 coarse channels bilinearly upsampled NaN-aware and state = log10 surfChl1,2,3,5; F1 forecasting at 0.5°, t -> t+1 day, with background = SST, wspeed at t+1. Grid 341x720 -> 344x736 (pad 3 rows; lon halo 8 each side, which is mask 0).
- Later runs:
  - Add pCO2, pH, CO2_flux, O2_flux, SSSanom, SIarea, SIheff and apCO2 once the daily archive downloads. Per the brief, pCO2, pH and surfPCO2 are 50-level files of 180.8 MB each; I did not read download_daily.sh.
  - Move to a 0.25° 720x1440 grid with channel_mult length 5, pad_to_multiple 16 and lon_halo 16.
  - Monthly DIC, ALK, FeT, PIC, POC runs are data-bound (158-313 samples; finding §3).
- Split: train 1992-2008, gap 2009, valid 2010-2011, test 2012 onward. Test years are never passed to the trainer. Robustness: reversed split and 6/24-month gaps (finding §5).
- Phases:
  - P0 (AICR, 1 GPU): build the env in a Slurm job; run the upstream tests (section 4); run a smoke on a synthetic store for BOTH stages. Stage 2 with model.regression_weights covers the untested handoff; use total_train_steps=20, batch_size=2, print_progress_freq=5, checkpoint_freq=10, validation_freq=10.
  - P1: build the stores with build_store.py on a big-RAM CPU node. npz members load fully, so allow about 1x the cube size, which is 56 GB for the 0.5° cube (arithmetic). Put the stores on /work.
  - P2: memory and step-time probe (section 3).
  - P3: regression, 5 seeds, then deterministic grading. STOP if it fails.
  - P4: diffusion, 3 seeds (each on its own regression seed), then probabilistic grading.
  - P5: earth2studio wrappers.

8. GRADING (pre-register; all nulls fitted on train years only; score ocean cells, cos(lat)-weighted, in log10 AND physical units; nulls and models in the SAME grading job on identical test indices)
- Downscaling nulls:
  - N0: the upsampled coarse field itself.
  - N1: per-cell day-of-year climatology (±15 d).
  - N2: N0 + per-cell climatological (fine - upsampled coarse).
  - N3: per-cell ridge of fine on upsampled coarse.
- Forecasting nulls:
  - P0: persistence.
  - P1: per-cell day-of-year climatology.
  - P2: per-cell AR(1) on anomalies.
  - P3: per-cell ridge on (anomaly_t, physics_t+1 anomalies).
- Deterministic PASS: the regression UNet (5-seed mean) beats the strongest null, with a block-bootstrap CI lower bound above 0 (30-day blocks, 1,000 resamples), on at least 2 of 4 Chl channels, in both the forward and the reversed split. Otherwise stop the direction, including the diffusion stage (settled: diffusion adds no deterministic skill; finding §2).
- Diffusion PASS, all of:
  - ensemble CRPS (fair, M=16) below the regression MAE, with CI above 0;
  - spread-skill ratio in [0.8, 1.2];
  - ensemble-mean RMSE within +3% of the regression;
  - high-k spectral ratio closer to 1 than the regression's.
- Also:
  - Downscaling coarse-consistency: RMS of the block-average of the generated field against the coarse input.
  - Forecasting 30-step rollout with true physics: skill per lead against P0 and P1, and the lead where skill against climatology crosses 0.
  - Replicate in a fresh job.
  - Record the result in docs/research_map (CLAUDE.md).

9. DRAFT FILES (tested only as stated in section 10; scratchpad copies at ...\scratchpad\draft\)

--- datasets/ecco_darwin.py (DRAFT) ---
```python
# DRAFT -- not run end to end. Written against NVIDIA/physicsnemo
# examples/weather/regional_weather_diffusion at commit
# 536553acf5b03b68ec7283975ba7276d60056a36 (main, 2026-09-30).
# Drop this file into the COPIED recipe folder as datasets/ecco_darwin.py.
# Select it with   dataset.name: ecco_darwin.EccoDarwinDataset
"""ECCO-Darwin v05 dataset for the regional_weather_diffusion recipe.

* "downscaling": {"background": coarse-on-fine-grid [C_b,H,W], "state": fine target [C_s,H,W], "mask": [C_s,H,W]}
* "forecasting": {"background": physics [C_b,H,W], "state": [state_t, state_t+dt], "mask": [C_s,H,W]}

Store layout under params["store"] (written by build_store.py):
    meta.json  {"lat":[H],"lon":[W],"times":[ISO8601 x T],"state_channels":[...],"background_channels":[...],
                "invariant_channels":[...],"dt_seconds":int,"transforms":{ch:"log10"|"none"}}
    state.npy float32 (T,C_s,H,W) transformed units, NaN=land   background.npy float32 (T,C_b,H,W) on the fine grid
    invariants.npy float32 (C_i,H,W) NaN-free   ocean_mask.npy bool (H,W)
    stats.json {"input":{ch:{"mean","std"}},"output":{ch:{...}},"fit_years":[...]}  (earth2studio CorrDiff keys)
Contract facts: params is a dict in training (utils/trainer.py:333-336) but a DictConfig in inference.py:50;
outputs must be normalised (datasets/dataset.py:56-57); NaN must not reach weight*(x0_pred-x0)**2
(physicsnemo/diffusion/metrics/losses.py:679), so zero-fill after normalisation and carry land in mask;
H,W multiples of 2**(len(channel_mult)-1) (physicsnemo/models/diffusion_unets/song_unet.py:558-571).
"""
from __future__ import annotations

import json
import os
from collections.abc import Mapping
from datetime import datetime

import numpy as np
import torch

from .dataset import StormCastDataset


def _get(params, key, default=None):
    """dict / DictConfig agnostic getter; converts ListConfig to list."""
    val = params.get(key, default) if hasattr(params, "get") else default
    if val is None:
        return default
    if hasattr(val, "__iter__") and not isinstance(val, (str, bytes, Mapping)):
        try:
            return list(val)
        except TypeError:
            return val
    return val


def _select(all_names: list[str], wanted) -> list[int]:
    if wanted in (None, "all"):
        return list(range(len(all_names)))
    missing = [w for w in wanted if w not in all_names]
    if missing:
        raise KeyError(f"channels {missing} not in store channels {all_names}")
    return [all_names.index(w) for w in wanted]


class EccoDarwinDataset(StormCastDataset):
    """params: store, mode ("downscaling"|"forecasting"), train_years, valid_years, state_channels,
    background_channels ("all"|list), dt_steps, dt_tolerance_s [lo,hi] seconds, background_time
    ("target"|"input"|"both", forecasting), pad_to_multiple (8 for 4 levels, 16 for 5), lon_halo
    (periodic columns each side, mask 0), per_channel_mask, valid_stride (train=False only; 1 for TEST)."""

    lead_time_steps: int = 0

    def __init__(self, params, train: bool):
        self.root = str(_get(params, "store"))
        self.mode = str(_get(params, "mode", "downscaling"))
        if self.mode not in ("downscaling", "forecasting"):
            raise ValueError(f"mode must be downscaling|forecasting, got {self.mode!r}")
        self.train = bool(train)
        with open(os.path.join(self.root, "meta.json")) as f:
            self.meta = json.load(f)
        with open(os.path.join(self.root, "stats.json")) as f:
            self.stats = json.load(f)

        s_all = list(self.meta["state_channels"])
        b_all = list(self.meta["background_channels"])
        self._s_idx = _select(s_all, _get(params, "state_channels", "all"))
        self._b_idx = _select(b_all, _get(params, "background_channels", "all"))
        self._s_names = [s_all[i] for i in self._s_idx]
        b_names = [b_all[i] for i in self._b_idx]
        self.background_time = str(_get(params, "background_time", "target"))
        if self.mode == "forecasting" and self.background_time == "both":
            self._b_names = [f"{n}@t0" for n in b_names] + [f"{n}@t1" for n in b_names]
        else:
            self._b_names = b_names

        # Normalisation stats: TRAIN-YEAR ONLY, computed by the store builder.
        self._s_mean = np.array([self.stats["output"][n]["mean"] for n in self._s_names], np.float32)
        self._s_std = np.array([self.stats["output"][n]["std"] for n in self._s_names], np.float32)
        self._b_mean = np.array([self.stats["input"][n]["mean"] for n in b_names], np.float32)
        self._b_std = np.array([self.stats["input"][n]["std"] for n in b_names], np.float32)
        if self.mode == "forecasting" and self.background_time == "both":
            self._b_mean = np.concatenate([self._b_mean, self._b_mean])
            self._b_std = np.concatenate([self._b_std, self._b_std])
        for arr, what in ((self._s_std, "state"), (self._b_std, "background")):
            if not np.all(np.isfinite(arr)) or np.any(arr <= 0):
                raise ValueError(f"non-positive or non-finite {what} std in stats.json")

        # Grid layout: [periodic lon halo | core | halo] then zero-pad bottom/right; halo+pad are mask 0.
        self.lat = np.asarray(self.meta["lat"], np.float64)
        self.lon = np.asarray(self.meta["lon"], np.float64)
        self.H0, self.W0 = len(self.lat), len(self.lon)
        self.halo = int(_get(params, "lon_halo", 0))
        if not 0 <= self.halo <= self.W0:
            raise ValueError("lon_halo must be in [0, W]")
        mult = int(_get(params, "pad_to_multiple", 8))
        self.H = -(-self.H0 // mult) * mult
        self.W = -(-(self.W0 + 2 * self.halo) // mult) * mult
        ocean = np.load(os.path.join(self.root, "ocean_mask.npy")).astype(bool)
        if ocean.shape != (self.H0, self.W0):
            raise ValueError(f"ocean_mask {ocean.shape} != grid {(self.H0, self.W0)}")
        self._ocean_core = ocean[None].astype(np.float32)
        self._ocean = self._layout(self._ocean_core, zero_halo=True)
        self.per_channel_mask = bool(_get(params, "per_channel_mask", True))
        inv = np.load(os.path.join(self.root, "invariants.npy")).astype(np.float32)
        if inv.ndim != 3 or inv.shape[1:] != (self.H0, self.W0):
            raise ValueError(f"invariants shape {inv.shape} does not match grid")
        if not np.all(np.isfinite(inv)):
            raise ValueError("invariants.npy must be NaN-free (fill land before saving)")
        self._inv = self._layout(inv)

        # Calendar and split (times from iteration numbers with delta_t = 1200 s, never 900 s).
        self.times = [datetime.fromisoformat(t) for t in self.meta["times"]]
        years = set(int(y) for y in _get(params, "train_years" if train else "valid_years", []))
        if not years:
            raise ValueError("train_years / valid_years must be non-empty")
        self.dt_steps = int(_get(params, "dt_steps", 1))
        base = float(self.meta.get("dt_seconds", 0)) * self.dt_steps
        lo, hi = _get(params, "dt_tolerance_s", [base, base])
        in_split = [t.year in years for t in self.times]
        if self.mode == "downscaling":
            self.index = [i for i, ok in enumerate(in_split) if ok]
        else:
            self.index = []
            for i in range(len(self.times) - self.dt_steps):
                j = i + self.dt_steps
                gap = (self.times[j] - self.times[i]).total_seconds()
                if in_split[i] and in_split[j] and float(lo) <= gap <= float(hi):
                    self.index.append(i)
        if not train:
            # trainer validates the FIRST validation_steps*batch samples, unshuffled (utils/trainer.py:913-923)
            self.index = self.index[:: int(_get(params, "valid_stride", 1))]
        if not self.index:
            raise ValueError(f"no samples for split train={train} (years={sorted(years)})")
        self._state = None  # memmaps opened lazily, once per worker process
        self._bg = None

    def __len__(self) -> int:
        return len(self.index)

    def background_channels(self) -> list[str]:
        return list(self._b_names)

    def state_channels(self) -> list[str]:
        return list(self._s_names)

    def image_shape(self) -> tuple[int, int]:
        return (self.H, self.W)

    def get_invariants(self) -> np.ndarray | None:
        return self._inv.copy()  # float32 (C_i,H,W); trainer.py:357-364 does no dtype cast

    def latitude(self) -> np.ndarray:
        lat = np.full(self.H, np.nan)
        lat[: self.H0] = self.lat
        return np.repeat(lat[:, None], self.W, axis=1)

    def longitude(self) -> np.ndarray:
        h = self.halo
        core = self.lon
        if h:
            core = np.concatenate([self.lon[-h:] - 360.0, self.lon, self.lon[:h] + 360.0])
        lon = np.full(self.W, np.nan)
        lon[: core.size] = core
        return np.repeat(lon[None, :], self.H, axis=0)

    def crop(self, x):
        """Undo halo and padding: (..., H, W) -> (..., H0, W0)."""
        return x[..., : self.H0, self.halo : self.halo + self.W0]

    def __getitem__(self, idx: int) -> dict:
        state, bg = self._arrays()
        i = self.index[idx]
        s_tar_raw = np.asarray(state[i + (self.dt_steps if self.mode == "forecasting" else 0), self._s_idx], np.float32)
        valid = np.isfinite(s_tar_raw)
        s_tar = self._finish(self.normalize_state(s_tar_raw))
        if self.mode == "forecasting":
            s_in_raw = np.asarray(state[i, self._s_idx], np.float32)
            valid &= np.isfinite(s_in_raw)
            s_in = self._finish(self.normalize_state(s_in_raw))
            if self.background_time == "input":
                b_raw = np.asarray(bg[i, self._b_idx], np.float32)
            elif self.background_time == "target":
                b_raw = np.asarray(bg[i + self.dt_steps, self._b_idx], np.float32)
            else:
                b_raw = np.concatenate([bg[i, self._b_idx], bg[i + self.dt_steps, self._b_idx]], axis=0).astype(np.float32)
            item = {"background": None, "state": [s_in, s_tar]}
        else:
            b_raw = np.asarray(bg[i, self._b_idx], np.float32)
            item = {"background": None, "state": s_tar}
        item["background"] = self._finish(self.normalize_background(b_raw))
        if self.per_channel_mask:
            item["mask"] = self._layout(valid.astype(np.float32) * self._ocean_core, zero_halo=True)
        else:  # only safe if the store has no time-varying NaN over ocean
            item["mask"] = self._ocean.copy()
        return item

    def normalize_state(self, x):
        return self._affine(x, self._s_mean, self._s_std, forward=True)

    def denormalize_state(self, x):
        return self._affine(x, self._s_mean, self._s_std, forward=False)

    def normalize_background(self, x):
        return self._affine(x, self._b_mean, self._b_std, forward=True)

    def denormalize_background(self, x):
        return self._affine(x, self._b_mean, self._b_std, forward=False)

    def time_of(self, idx: int) -> tuple[datetime, datetime]:
        i = self.index[idx]
        j = i + (self.dt_steps if self.mode == "forecasting" else 0)
        return self.times[i], self.times[j]

    @staticmethod
    def _affine(x, mean, std, forward: bool):
        shape = (-1, 1, 1)
        if isinstance(x, torch.Tensor):  # not hasattr(x,"device"): NumPy>=2 arrays have .device too
            m = torch.as_tensor(mean, device=x.device, dtype=x.dtype).reshape(shape)
            s = torch.as_tensor(std, device=x.device, dtype=x.dtype).reshape(shape)
        else:
            m, s = mean.reshape(shape), std.reshape(shape)
        return (x - m) / s if forward else x * s + m

    def _layout(self, x: np.ndarray, zero_halo: bool = False) -> np.ndarray:
        h = self.halo
        if h:
            x = np.concatenate([x[..., -h:], x, x[..., :h]], axis=-1)
            if zero_halo:
                x[..., :h] = 0.0
                x[..., h + self.W0 :] = 0.0
        c, hh, ww = x.shape
        out = np.zeros((c, self.H, self.W), np.float32)
        out[:, :hh, :ww] = x
        return out

    def _finish(self, z: np.ndarray) -> np.ndarray:
        z = np.nan_to_num(z, nan=0.0)
        if not np.all(np.isfinite(z)):
            raise FloatingPointError("inf after normalisation; check transforms/stats")
        return self._layout(z)

    def _arrays(self):
        if self._state is None:
            self._state = np.load(os.path.join(self.root, "state.npy"), mmap_mode="r")
            self._bg = np.load(os.path.join(self.root, "background.npy"), mmap_mode="r")
            if self._state.shape[0] != len(self.times) or self._bg.shape[0] != len(self.times):
                raise ValueError("state/background time axis does not match meta.json times")
        return self._state, self._bg

    def __getstate__(self):  # spawn-safe: never pickle the memmaps
        d = self.__dict__.copy()
        d["_state"] = None
        d["_bg"] = None
        return d
```

--- config/ecco_downscaling.yaml (DRAFT) ---
```yaml
# DRAFT -- CorrDiff-like DOWNSCALING, regional_weather_diffusion @ 536553acf5b03b68ec7283975ba7276d60056a36
# Do NOT add model/stormcast to defaults: its `model_type` key (and diffusion.yaml's `use_regression_net`)
# fail the recipe's own pydantic validation (utils/config.py:24, extra="forbid").
# Stage 1: torchrun --standalone --nnodes=1 --nproc_per_node=1 train.py --config-name ecco_downscaling \
#            training.experiment_name=ds_reg training.run_id=s1 training.seed=1
# Stage 2: torchrun --standalone --nnodes=1 --nproc_per_node=1 train.py --config-name ecco_downscaling \
#            training.loss.type=edm training.total_train_steps=60000 \
#            model.regression_weights=rundir/ds_reg/s1/checkpoints_regression/StormCastUNet.0.20000.mdlus \
#            training.experiment_name=ds_diff training.run_id=s1 training.seed=1
defaults:
  - training/default
  - sampler/edm_deterministic
  - hydra/default
  - _self_

dataset:
  name: ecco_darwin.EccoDarwinDataset
  store: /work/neu/p2026_0089_neu/rwd_stores/ds_daily_1to05deg   # built by build_store.py
  mode: downscaling
  train_years: [1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000,
                2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008]
  valid_years: [2010, 2011]        # 2009 = gap year; 2012 onward = TEST, never given to the recipe
  state_channels: all              # fine-grid targets, e.g. log10_surfChl1,2,3,5
  background_channels: all         # coarse fields bilinearly upsampled to the fine grid
  pad_to_multiple: 8               # = 2**(len(channel_mult)-1); 341x720 store -> 344x736 image
  lon_halo: 8                      # periodic dateline context, mask 0 in the halo
  per_channel_mask: true
  valid_stride: 5                  # trainer validates the first validation_steps*batch_size valid samples

model:
  model_name: regression           # informational only; the trainer keys on training.loss.type
  architecture: unet
  regression_conditions: ["background", "invariant"]               # order = concat order
  diffusion_conditions: ["background", "regression", "invariant"]  # CorrDiff residual sees low-res input + regression mean
  regression_weights: null         # stage 2 sets this to the stage-1 .mdlus
  hyperparameters:
    model_type: SongUNet           # SongUNetPosEmbd/additive_pos_embed tie the net to one grid size
    model_channels: 64
    channel_mult: [1, 2, 2, 2]
    num_blocks: 2
    attn_resolutions: []
    bottleneck_attention: true
    checkpoint_level: 0            # raise (1-3) only if the memory probe says so

training:
  outdir: rundir
  experiment_name: ds_reg
  run_id: "0"
  num_data_workers: 4
  log_to_tensorboard: true
  log_to_wandb: false
  seed: 1
  batch_size: 16
  batch_size_per_gpu: auto
  total_train_steps: 20000
  clip_grad_norm: -1
  print_progress_freq: 100
  checkpoint_freq: 1000
  validation_freq: 1000
  validation_steps: 8
  validation_plot_variables: ["log10_surfChl1"]   # MUST be state channel names (utils/plots.py:182)
  validation_plot_background_channels: []
  perf:
    fp_optimizations: amp-bf16
    torch_compile: false
    use_apex_gn: false
    allow_tf32: false
  optimizer:
    name: adam
    lr: 4.0e-4
  scheduler:
    name: CosineAnnealingLR
    lr_rampup_steps: 1000
  loss:
    type: regression               # stage 2: edm
    sigma_distribution: lognormal
    sigma_data: 0.5                # KEEP 0.5: utils/nn.py:93 builds EDMPreconditioner with its default 0.5; a different value here only reweights the loss
    P_mean: -1.2
    P_std: 1.2
    track_sigma_bin_loss: true
```

--- config/ecco_forecasting.yaml (DRAFT) ---
Identical to ecco_downscaling.yaml except for the lines below. Header and stage commands use --config-name ecco_forecasting with experiment names fc_reg and fc_diff.
```yaml
dataset:
  name: ecco_darwin.EccoDarwinDataset
  store: /work/neu/p2026_0089_neu/rwd_stores/fc_daily_05deg
  mode: forecasting
  train_years: [1992, 1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000,
                2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008]
  valid_years: [2010, 2011]
  state_channels: all              # prognostic BGC, e.g. log10_surfChl1,2,3,5 (+ pCO2, pH once downloaded)
  background_channels: all         # ECCO physics, e.g. SST, wspeed (+ SSSanom, SIarea, SIheff, apCO2)
  background_time: target          # physics at t+1 is known offline; "input" = StormCast literal, "both" = t and t+1
  dt_steps: 1
  dt_tolerance_s: [86400, 86400]   # exactly one day; monthly stores use [2419200, 2678400]
  pad_to_multiple: 8               # = 2**(len(channel_mult)-1); 341x720 store -> 344x736 image
  lon_halo: 8
  per_channel_mask: true
  valid_stride: 5
model:
  model_name: regression
  architecture: unet
  regression_conditions: ["state", "background", "invariant"]   # = earth2studio stormcast.py _forward order
  diffusion_conditions: ["state", "regression", "invariant"]
  regression_weights: null
  hyperparameters: {model_type: SongUNet, model_channels: 64, channel_mult: [1, 2, 2, 2], num_blocks: 2,
                    attn_resolutions: [], bottleneck_attention: true, checkpoint_level: 0}
training:
  experiment_name: fc_reg
  # every other training.* key exactly as in ecco_downscaling.yaml
```
(The full-length file is in the scratchpad at draft\config\ecco_forecasting.yaml, 88 lines.)

--- build_store.py (DRAFT, numpy only) ---
Full text: ...\scratchpad\draft\build_store.py (146 lines). What it does:
- Loads the fine and coarse npz cubes. It reads each member once and streams channel by channel into np.lib.format.open_memmap state.npy and background.npy.
- Transform: log10 with floor 1e-4 for surfChl*/Chl*; NaN is kept on land.
- Downscaling: builds separable linear-interpolation matrices, periodic in longitude (interp_matrix), and does NaN-aware bilinear upsampling (num/den einsum; NaN where there is no ocean support). This is exact at coincident nodes (tested).
- Invariants: [ocean*2-1, sin lat, cos lat, sin lon, cos lon].
- stats.json uses TRAIN years only; meta.json records times from times_days (days since 1992-01-01), dt_seconds = median step, and the transforms.
- Command: `python build_store.py --mode downscaling --fine daily_global_halfdeg_cube.npz --coarse daily_global_1deg_cube.npz --fit-years 1992 ... 2008 --lon0 <first lon of the cubes> --out /work/.../rwd_stores/ds_daily_1to05deg`. Forecasting: `--mode forecasting --fine daily_global_halfdeg_cube.npz`.

--- generate_ecco.py (DRAFT, UNTESTED; replaces the HRRR-only inference.py) ---
Full text: ...\scratchpad\draft\generate_ecco.py (78 lines). What it does:
- Builds EccoDarwinDataset(valid_years=TEST years, valid_stride=1, train=False).
- Loads both nets with physicsnemo.core.Module.from_checkpoint.
- mu = utils.nn.regression_model_forward(reg, s_in, bg, inv, condition_list=reg_conds).
- cond = build_network_condition_and_target(..., condition_list=diff_conds, regression_condition_list=reg_conds), repeated M times.
- res = diffusion_model_forward(dif, cond, shape=(M,C,H,W), scheduler=EDMNoiseScheduler(0.002, 800, 7), sampler_args={num_steps:18, solver:"heun"}); ens = mu + res.
- Then crop, denormalise and set land to NaN, and append to zarr {ensemble(time,member,channel,lat,lon), regression, truth} in chunks along time.
- Run from the recipe folder; it needs no torchrun.

10. WHAT I VERIFIED
- The two configs compose with Hydra 1.3.7 and pass the recipe's MainConfig with pydantic 2.13.5, for stage 1 and stage 2 overrides, per-channel sigma_data, and batch_size_per_gpu (5/5 OK).
- The dataset kwargs arrive as a plain dict with list values (checked).
- The same check reproduces the upstream breakage: regression.yaml, diffusion.yaml, regression_lite and diffusion_lite FAIL, with "model.model_type Unexpected keyword argument" plus model.use_regression_net; only the test_* configs pass.
- Dataset on synthetic stores (repo venv torch 2.11, read-only use): both modes; shapes, float32 dtypes, finiteness; land, pad and halo masked; time-varying NaN masked per channel; pair-gap rejection across a missing day; year split; background_time=both; torch/numpy normalise round trip; torch DataLoader with 2 spawn workers plus collate; DictConfig params; lon-halo wrap and crop equal the unhaloed result.
- Builder on synthetic cubes: both modes build and load.
- Not verified:
  - Anything that needs physicsnemo installed (a trainer run, the generation script, memory, step time).
  - Windows distributed behaviour.
  - The AICR cube keys and origin.

LOOSE END FOUND IN PASSING: src/darwindiff/e2s/prognostic.py:276 and :282 both decorate __call__ with @batch_func(), i.e. twice. The effect under real earth2studio is unverified; fix it before the serving wrapper reuses this class.
