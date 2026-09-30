# earth2studio side: loading, wrappers, grid, first end-to-end run

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

I read earth2studio at main commit 2067756d489ad9195cf9e1ed52e074a4f8588ca4 (v0.19.0a0) and physicsnemo at main commit 536553acf5b03b68ec7283975ba7276d60056a36 (this includes the regional_weather_diffusion recipe), along with the repo's src/darwindiff/e2s and tests. I executed nothing. Everything below comes from reading the source, and anything marked "traced" means I followed the call chain by hand.

(1) earth2studio's generic CorrDiff class cannot load a regional_weather_diffusion checkpoint. It drives the old ("legacy") physicsnemo API, calling `net(x=, img_lr=)` for regression and `net(x, x_lr, t)` for diffusion. The new recipe saves a StormCastUNet (`forward(x)`) and an EDMPreconditioner(ConcatConditionWrapper(SongUNet)) (`forward(x, t, condition=)`). Renaming the files lets them load, but the first call fails. The deprecated corrdiff recipe (UNet + EDMPrecondSuperResolution) is the one the generic class was written for. The fix is a small subclass, DarwinCorrDiff(CorrDiff). It keeps the generic package layout and `__call__`/sample loop and overrides `_validate_grid_format`, `_interpolate`, `normalize_input`, `postprocess_output`, `_forward` (new-API sampling) and `load_model`.

(2) The stock StormCast wrapper is hardwired to HRRR. A standalone DarwinStormCast is needed, modelled on stormcast.py. It fetches the physical background on every `__call__` with `fetch_data(source, time, lead_time)` at the valid time of the input state (t), then normalises, runs the regression on cat(state, background, invariant), runs EDM on cat(state, regression, invariant) and adds the two. This matches the recipe, which also takes the background at the input time.

(3) earth2studio's convention is lat 90 to -90 and lon [0, 360). The standard 721x1440 grid gives interoperability at the plumbing level: no interpolation, and DiagnosticWrapper skips regridding when the grids are identical. The ocean science does not come with it. Also, 721 rows fail SongUNet's divisibility check. So all grids should be exact subsets of the 0.25 degree lattice: high-res 720x1440, prognostic and low-res 176x360 at 1 degree.

(4) run.diagnostic cannot write CorrDiff's 'sample' dimension. The chain to use is run.deterministic or run.ensemble with DiagnosticWrapper(px, dx) (traced). The first run is that chain on toy checkpoints produced by 10 steps of the real recipe, with the nulls (Persistence and an interpolation-only diagnostic) run through the same pipeline in the same job.

(5) Problems in the existing wrapper:
- The 30-day step drifts against calendar months.
- The clamp to non-negative is applied to every channel.
- Inputs are not masked for NaN, and one NaN spreads everywhere through an FNO.
- `@batch_func` is applied twice.
- The `None` branch in `output_coords` cannot be reached under the real decorator.
- There are no front/rear hooks and no Package loading.
- The DataSource loads the whole npz eagerly and refuses the cubes that actually exist.

## Decisions

- **How to serve the CorrDiff-style 'resolution booster' in earth2studio** → Subclass earth2studio's CorrDiff as DarwinCorrDiff. Keep its package layout (the 7 files), __call__, input/output_coords and the sample dimension. Override _validate_grid_format, _interpolate, normalize_input, postprocess_output, _forward (new-API EDMPreconditioner sampling) and load_model. If subclass coupling proves brittle, fall back to a standalone class modelled on CorrDiffEra5Hrrr (dx/corrdiff_era5_hrrr.py:630-736).
  - why: The generic class calls legacy signatures (legacy_generate.py:90-92; legacy.py:927-933). regional_weather_diffusion saves StormCastUNet and EDMPreconditioner(ConcatConditionWrapper) (nn.py:84-100), so it fails at the first call. The subclass reuses the tested time and sample loop and the file loader.
- **How to build the StormCast-style time-stepper** → Write a standalone DarwinStormCast(nn.Module, AutoModelMixin, PrognosticMixin) that mirrors stormcast.py. Fetch the background on every __call__ through fetch_data at the input state's valid time plus a background_offset recorded in metadata (default 0). Refuse off-lattice sources. Build conditions in metadata order: regression [state, background, invariant], diffusion [state, regression, invariant]. Add a mode='regression' switch.
  - why: The stock wrapper is HRRR-hardwired (stormcast.py:182, 210-260; data/utils.py:307) and loads the legacy EDMPrecond. Both the recipe and E2S take the background at the input time (data_loader_hrrr_era5.py:364-368; stormcast.py:456-464), so matching that keeps training and serving consistent.
- **Which earth2studio workflow chains prognostic and diagnostic** → Use run.deterministic (and run.ensemble with Zero perturbation) on DiagnosticWrapper(px, dx). Do not use run.diagnostic.
  - why: run.diagnostic takes its IO coordinates from the prognostic only (run.py:252-273), so CorrDiff's 'sample' dimension cannot be written (io/zarr.py:225-259). DiagnosticWrapper exposes the dx coordinates, sample included (dxwrapper.py:177-204, 461-482). This was traced by reading, not executed.
- **Grid** → Use exact subsets of the E2S 0.25 degree lattice, lat descending, lon [0,360), built from integer x step. High-res: 720x1440 (lat 90 to -89.75). Low-res and StormCast: 176x360 at 1 degree (lat 90 to -85) with a 4-level SongUNet. Wrap longitude periodically inside the dx interpolation.
  - why: 721 rows fail SongUNet's multiple-of-2^(N-1) check (song_unet.py:348, 560-572). Lattice subsets pass handshake_coords (exact ==) and map_coords slicing (coords.py:255-265). Identical grids skip DiagnosticWrapper interpolation (dxwrapper.py:153). Integer-built coordinates avoid map_coords' silent nearest-neighbour fallback (coords.py:297-309).
- **Time step and cadence** → Run the StormCast analog daily (dt=24h). Run the monthly CorrDiff diagnostic per month with nsteps=0 over a list of month stamps. Never use dt=30 days inside run.*.
  - why: E2S lead times are fixed timedeltas (run.py:105-110; data/utils.py:83-99). A 30-day step mislabels calendar months, and after about 3 years the nearest-month lookup (datasource.py:141) verifies against the wrong month.
- **Land and NaN policy** → The DataSource serves land as 0.0 plus a separate ocean mask shipped in each package. Wrappers apply nan_to_num and the mask in normalised space and write zeros on land. Clamp to non-negative per variable only. No regridding inside E2S (do not define interp_method).
  - why: The current wrapper standardises NaN inputs (prognostic.py:264-267), and in an FNO one NaN spreads everywhere. E2S weighted statistics multiply by weights, and 0 x NaN = NaN. run.* interpolates only when interp_method exists (run.py:137-142).
- **How to grade the E2S side honestly** → Run every null through the identical pipeline in the same Slurm job: Persistence (px/persistence.py), climatology via DataReplay over a train-only climatology source, an interpolation-only dx, and the dx in inference_mode='regression'. Write truth through DataReplay. Fix seeds per (base_seed, time, lead, member, sample). Score with lat_weight x mask weights.
  - why: CLAUDE.md requires comparisons within a job. The settled finding says the diffusion stage adds no deterministic skill, so the regression-only mode is the deciding control. A fixed base seed with seed+i (corrdiff.py:1073-1084) makes ensemble spread zero.
- **Environment** → A separate track2/ uv project pinned to earth2studio 2067756 and physicsnemo 536553a, with torch 2.11 cu128. Vendor the recipe at 536553a. Train and serve in the same environment, built in a Slurm job on AICR.
  - why: earth2studio pins netCDF4<1.7.3 against the repo's 1.7.4. The recipe is main-only and needs torch>=2.10. .mdlus files are loaded by class, so using one physicsnemo commit avoids class-resolution drift.

## Risks

- The training and serving paths may disagree on normalisation, log transform and floors, land fill, condition order, low-res to high-res interpolation, or background time offset. Any such mismatch produces plausible-looking wrong fields rather than an error. Mitigate with shared darwin_e2s.norm and darwin_e2s.regrid modules, a metadata.json written from the training config, and a regression-mode parity test against the recipe's inference.py:142-167.
- physicsnemo diffusion API churn: E2S generic CorrDiff still imports the legacy modules (corrdiff.py:47-61). The recipe uses the new API. The subclass depends on both existing in one physicsnemo commit. Both exist at 536553a, but the combination has not been run.
- The recipe's utils/nn.py imports DiT at module level (nn.py:30) and requirements.txt lists natten. Building natten for sm_100 with torch 2.11 may fail even for UNet-only training (unverified).
- The DiagnosticWrapper + run.deterministic chain, including sample-dimension IO, was traced by reading only. The Stage 0 smoke run exists to prove it.
- map_coords silently nearest-maps numeric coordinates it cannot find (utils/coords.py:297-309). Grids that are off by floating-point noise will be quietly resampled unless built from integers and checked with np.isin before mapping.
- The daily archive is not on disk, and data.nas was unreachable on 2026-09-30. The StormCast analog (Stage 2) is blocked on the re-download, and daily physics lack MLD and Qsw.
- Compute and memory: a 720x1440 diffusion pass with S samples and 18 Heun steps is 36 network evaluations per sample per step. It fits on a B200. On the 32 GB 5090 it may run out of memory for large model_channels (unverified). Windows install of E2S core (pygrib) is unverified.
- Scientific ceiling (settled): the diffusion stage does not add deterministic skill over its regression UNet, and monthly data binds. E2S plumbing success must not be reported as skill.

## Unknowns

- Whether EDMNoiseScheduler.init_latents or physicsnemo.diffusion.samplers.sample accept a torch.Generator. The draft uses torch.random.fork_rng + manual_seed as a fallback. Unverified.
- The exact file base name save_checkpoint gives the recipe's diffusion model (assumed EDMPreconditioner.0.<step>.mdlus from _get_checkpoint_filename, PNM physicsnemo/utils/checkpoint.py:570-637). Unverified.
- Whether the deprecated corrdiff recipe's checkpoints load and run end to end through E2S generic CorrDiff. The signatures match by reading; this was not executed.
- Whether latlon_interpolation_regular handles descending lat. It is bypassed by overriding _interpolate, so this is unverified but moot.
- Grid and variables of SamudrACE's ocean outputs, and whether they could act as a ForecastSource background for the StormCast analog. Unverified.
- Whether the ECCO-Darwin 1 degree bin_average product on data.nas is aligned with the E2S lattice. It is probably cell-centred at -89.5..89.5, in which case regrid from LLC270 instead. Unverified.
- Whether the daily pCO2, pH and surfPCO2 files (50 levels) are needed beyond level k=0 for a surface-state StormCast.
- The time-stamp convention of the monthly mirror (start, middle or end of month) that the calendar-month resolver must honour.

## Spec

DRAFT DESIGN, READ-ONLY. Nothing below was executed. Every code block is a DRAFT.

PINS AND SOURCES
- E2S = NVIDIA/earth2studio main @ 2067756d489ad9195cf9e1ed52e074a4f8588ca4 (2026-09-30, __version__ 0.19.0a0). Base URL: https://github.com/NVIDIA/earth2studio/blob/2067756d489ad9195cf9e1ed52e074a4f8588ca4/
- The compare 3400b69...2067756 is 120 commits ahead. In it, models/px/base.py, models/dx/base.py, models/batch.py, run.py, utils/coords.py and io/zarr.py show +0/-0, and data/base.py shows +4. So the repo's conformance result (tests/test_e2s_conformance.py:11, verified at 3400b69) still holds at main.
- PNM = NVIDIA/physicsnemo main @ 536553acf5b03b68ec7283975ba7276d60056a36. Base URL: https://github.com/NVIDIA/physicsnemo/blob/536553acf5b03b68ec7283975ba7276d60056a36/
- Recipe path: examples/weather/regional_weather_diffusion (abbreviated RWD below).
- The deprecated examples/weather/corrdiff is still in the tree at this commit.

======================================================================
Q1. CAN earth2studio's GENERIC CorrDiff LOAD A regional_weather_diffusion CHECKPOINT?
======================================================================

What CorrDiff.load_model(package, device, sigma_min, sigma_max) expects (E2S earth2studio/models/dx/corrdiff.py:624-854):

load_default_package raises NotImplementedError (corrdiff.py:585-588). Use CorrDiff.load_model(Package("/abs/dir")), which works because Package accepts a local root (models/auto/package.py:158-218).

Files in the package root:

1. diffusion.mdlus
   - Loaded with PhysicsNemoModule.from_checkpoint(strict=False) (corrdiff.py:664-666).
   - Driven through legacy diffusion_step with stochastic_sampler (corrdiff.py:1078-1088; PNM physicsnemo/diffusion/generate/legacy_generate.py:101).
   - That path calls net(x, x_lr, t, ...), which is the EDMPrecondSuperResolution / EDMPrecondSR forward(x, img_lr, sigma) (PNM physicsnemo/diffusion/preconditioners/legacy.py:927-933).

2. regression.mdlus
   - Loaded at corrdiff.py:667-669.
   - Driven through legacy regression_step, which calls net(x=zeros[1,C_out,H,W], img_lr=img_lr) (PNM legacy_generate.py:90-92).
   - That is the legacy UNet / CorrDiffRegressionUNet, which does torch.cat((x, img_lr)) (PNM physicsnemo/models/diffusion_unets/unet.py:300, :340).

3. metadata.json (corrdiff.py:690-716)
   - REQUIRED: input_variables (list; duplicates are rejected), output_variables.
   - OPTIONAL, with defaults: invariant_variables, number_of_samples=1, number_of_steps=18, solver="euler", sampler_type="stochastic", inference_mode="both" (also "regression" or "diffusion"), hr_mean_conditioning=True, seed=None, sigma_min, sigma_max, grid_spacing_tolerance=1e-5, grid_bounds_margin=0.0, latlon_res (used only if input_latlon_grid.nc is absent).
   - Trap: sampler_type="deterministic" together with hr_mean_conditioning=True raises NotImplementedError (corrdiff.py:519-523).

4. stats.json (corrdiff.py:719-741, 813-818)
   - Layout: {"input": {var: {"mean", "std"}}, "output": {var: {...}}, "invariants": {var: {...}}}.
   - Normalisation is linear only: (x-mean)/std (corrdiff.py:921-934, 990-1003).

5. output_latlon_grid.nc, with variables "lat" and "lon" (corrdiff.py:744-751).
   - 1-D grids must be ASCENDING: latitude south to north, and longitude increasing (corrdiff.py:285-298).
   - 2-D grids must be truly curvilinear (corrdiff.py:300-308).

6. input_latlon_grid.nc (corrdiff.py:753-772)
   - Optional if metadata has latlon_res; the inferred grid is ascending (corrdiff.py:856-887).
   - Spacing must be regular (corrdiff.py:352-386).
   - The output grid must lie inside the input bounds plus grid_bounds_margin (corrdiff.py:388-421).

7. invariants.nc, on the OUTPUT grid (corrdiff.py:774-818). Required only if metadata lists invariant_variables.

Runtime behaviour:
- input_coords = [batch, variable, lat, lon] (corrdiff.py:531-547).
- output_coords = [batch, sample, variable, lat, lon] (corrdiff.py:549-583). It handshakes variable/lat/lon at positions 1/2/3.
- For each batch element: bilinear interpolation from low-res to high-res, which the docstring invites you to override (corrdiff.py:889-919, override note at 902-906). Then concatenate the invariants and normalise (936-988). Then regression_step, then diffusion_step with mean_hr = the regression output. Output = regression + residual (1020-1105).
- Seeding: seed+i for sample i (corrdiff.py:1073-1084). With a fixed seed, every batch element and every call reuses the same noise.

VERDICT for regional_weather_diffusion: NO.
- RWD builds its regression net as StormCastUNet(img_in_channels=conditional_channels) (RWD utils/nn.py:95-100). Its forward is forward(x, force_fp32) (PNM unet.py:534): there is no img_lr kwarg and no zero-latent block.
- RWD builds its diffusion net as EDMPreconditioner(model=ConcatConditionWrapper(SongUNet*)) (RWD utils/nn.py:84-93). Its forward is forward(x, t, condition=None) (PNM physicsnemo/diffusion/preconditioners/preconditioners.py:454-460).
- Conditions are concatenated in config order (RWD utils/nn.py:214-217), and the diffusion target is the residual state - regression (RWD utils/nn.py:212).
- Checkpoints are written by physicsnemo.utils.save_checkpoint (RWD utils/trainer.py:1081-1097). Files are named after the class, e.g. StormCastUNet.0.<step>.mdlus (RWD config/diffusion.yaml regression_weights). The EDMPreconditioner file name is unverified.
- If you rename them to regression.mdlus and diffusion.mdlus, from_checkpoint will instantiate them (RWD inference.py:79,83 uses the class-agnostic Module.from_checkpoint). The first call then fails:
  - regression_step passes img_lr= to StormCastUNet, which raises TypeError;
  - the legacy sampler passes (x, x_lr, t) positionally to EDMPreconditioner;
  - the channel layouts also differ.
- The deprecated corrdiff recipe saves UNet + EDMPrecondSuperResolution, which is exactly what the generic class loads (CorrDiffCMIP6 does the same: corrdiff_cmip6.py:444-451). So those checkpoints are loadable in principle, given the 7 files above. That is unverified end to end, and it is not a basis for new work.
- A template for the new API already exists in E2S: CorrDiffEra5Hrrr loads EDMPreconditioner(ConcatConditionWrapper(DiT)) with sample() (earth2studio/models/dx/corrdiff_era5_hrrr.py:43-51, 630-736).

MINIMAL CUSTOM DiagnosticModel (DRAFT): subclass CorrDiff.
Inherited unchanged: package layout, _register_buffers, input_coords, output_coords (with the sample dimension), and __call__ (time handling, output allocation, per-element loop).

```python
# track2/src/darwin_e2s/corrdiff_dx.py   DRAFT
import torch, numpy as np
from earth2studio.models.dx.corrdiff import CorrDiff
from darwin_e2s.recipe_compat import diffusion_model_forward  # vendored verbatim from RWD utils/nn.py:264-370 (Apache-2.0), with a parity test
from darwin_e2s.regrid import lr_to_hr                        # SAME function the training dataset uses to build `background`
from darwin_e2s.norm import load_norm                          # SAME module the dataset's normalize_* uses (log vars, floors)
from physicsnemo.diffusion.noise_schedulers import EDMNoiseScheduler

class DarwinCorrDiff(CorrDiff):
    @classmethod
    def _validate_grid_format(cls, lat, lon, grid_name="grid"):
        # base insists on ascending lat (corrdiff.py:287-292); E2S convention is 90 -> -90
        if lat.ndim != 1 or lon.ndim != 1: raise ValueError("1-D lattice grids only")
        if not bool((torch.diff(lon) > 0).all()): raise ValueError("lon must increase")
        d = torch.diff(lat)
        if not (bool((d < 0).all()) or bool((d > 0).all())): raise ValueError("lat must be monotonic")

    @classmethod
    def load_model(cls, package, device=None, **kw):
        m = super().load_model(package, device=device, **kw)       # files/keys above; builds cls(...)
        meta = cls._load_json_from_package(package, "metadata.json")["darwin"]
        m.reg_conditions = meta["regression_conditions"]   # e.g. ["background","invariant"]
        m.dif_conditions = meta["diffusion_conditions"]    # e.g. ["background","regression","invariant"]
        m.norm_in, m.norm_out = load_norm(package, "input"), load_norm(package, "output")
        m._sampler_args = meta["sampler"]                  # num_steps, solver, sigma_min/max, rho, S_*
        m._sched = EDMNoiseScheduler(sigma_min=m._sampler_args["sigma_min"],
                                     sigma_max=m._sampler_args["sigma_max"], rho=m._sampler_args["rho"])
        m.register_buffer("mask_hr", torch.as_tensor(np.load(package.resolve("ocean_mask_hr.npy"))).bool())
        return m.to(device) if device else m

    def _interpolate(self, x):                 # [C, H_lr, W_lr] -> [C, H_hr, W_hr]
        return lr_to_hr(x, self.lat_input_grid, self.lon_input_grid,
                        self.lat_output_grid, self.lon_output_grid)   # periodic lon, land-aware

    def normalize_input(self, x):              # x = [B, C_in + C_inv, H, W]
        z = self.norm_in(x, n_dynamic=len(self.input_variables))      # log for log-vars, then (x-mean)/std
        return torch.nan_to_num(z) * self.mask_hr                     # land -> 0 in normalized space

    def postprocess_output(self, z):
        y = self.norm_out.inverse(z)                                  # (z*std+mean) then exp for log-vars
        y = self.norm_out.clamp_nonneg(y)                             # per-variable list, NOT all channels
        return torch.where(self.mask_hr, y, torch.zeros_like(y))

    @torch.inference_mode()
    def _forward(self, x, valid_time=None):
        img = self.preprocess_input(x, valid_time).float()           # [1, C_in+C_inv, H, W]
        n = len(self.input_variables)
        parts = {"background": img[:, :n], "invariant": img[:, n:]}
        reg = self.regression_model(torch.cat([parts[c] for c in self.reg_conditions], 1))
        parts["regression"] = reg
        outs = []
        for s in range(self.number_of_samples):
            if self.inference_mode == "regression":
                outs.append(reg); continue
            cond = torch.cat([parts[c] for c in self.dif_conditions], 1)
            res = diffusion_model_forward(self.residual_model, cond, reg.shape,
                                          scheduler=self._sched, sampler_args=self._sampler_args)
            outs.append(reg + res if self.inference_mode == "both" else res)
        return self.postprocess_output(torch.cat(outs, 0))           # [S, C_out, H, W]
```

Package contents for DarwinCorrDiff:
- The 7 generic files: output/input_latlon_grid.nc hold DESCENDING lat, which our validator allows.
- A "darwin" block in metadata.json with regression_conditions, diffusion_conditions, sampler, log_variables, log_floors, nonneg_variables, recipe_commit=536553a, earth2studio_commit=2067756, train_period, test_period and base_seed.
- ocean_mask_hr.npy.
- sampler_type must stay "stochastic" in metadata.json, otherwise the base constructor hits corrdiff.py:519-523.
- Set grid_bounds_margin to about 0.03 so that 720 high-res rows (to -89.75) fit inside a 176-row low-res grid (to -85). The extra rows are all Antarctic land and are masked.

Seeding: pass a torch.Generator seeded from hash(base_seed, time, lead_time, member, s). Whether EDMNoiseScheduler.init_latents accepts a generator is unverified; if it does not, wrap the call in torch.random.fork_rng with manual_seed. Do NOT use the base class's seed+i: fixed noise across batch elements makes ensemble spread zero.

======================================================================
Q2. StormCast-STYLE PROGNOSTIC ON A CUSTOM GLOBAL GRID
======================================================================

Why a new class: stock StormCast is HRRR-hardwired.
- HRRR.grid() at stormcast.py:182.
- hrrr_y/hrrr_x coordinates at stormcast.py:210-222 and 224-260.
- fetch_data's prep_data_array has "HARD CODE FOR STORMCAST" (data/utils.py:307).
- It loads EDMPrecond, the legacy class, from EDMPrecond.0.0.mdlus (stormcast.py:318-326), not the recipe's EDMPreconditioner.
- Its package is model.yaml plus metadata.zarr.zip (stormcast.py:315, 328).

The exact background mechanism in E2S StormCast:
a. The source is self.conditioning_data_source, a DataSource or ForecastSource. It warns if it is None at init (stormcast.py:197) and raises RuntimeError in __call__ (stormcast.py:449). The generator yields the initial condition (IC) without touching the source, and raises before step 1 if the source is missing (stormcast.py:501-512).
b. On EVERY __call__ (stormcast.py:424-497), it calls fetch_data(source, time=coords["time"], variable=conditioning_variables, lead_time=coords["lead_time"], device=x.device, interp_to=coords|{"_lat","_lon"}, interp_method="linear") (stormcast.py:456-464).
c. fetch_data (data/utils.py:101-165) behaves in one of two ways:
   - If the source's __call__ has a lead_time parameter, it is a ForecastSource and is called as source(time, lead_time, variable) (data/utils.py:147).
   - Otherwise, for each lead it calls source(time + lead, variable), expands a lead_time dimension, and re-labels time as the init time (data/utils.py:154-160).
   - Either way, the background is fetched at the valid time of the INPUT state (t0 + current lead_time).
d. The result is reordered to [time, lead_time, variable, lat, lon], repeated over batch (stormcast.py:477), and handshaked on lead_time and time only (stormcast.py:485-486).
e. The loop does x[i,j,k:k+1] = _forward(x[i,j,k:k+1], cond[i,j,k:k+1]).
f. _forward (stormcast.py:370-420):
   - normalise the conditioning with conditioning_means/stds;
   - regression on cat(x, cond, invariants) (stormcast.py:382);
   - diffusion condition cat(x, regression_out, invariants) (stormcast.py:387);
   - EDMNoiseScheduler plus sample(solver="edm_stochastic_heun");
   - out += edm (stormcast.py:416), then denormalise.
g. The generator runs front_hook -> __call__ -> rear_hook (stormcast.py:518-522; PrognosticMixin in models/px/utils.py).

Training side matches this:
- The RWD StormCast defaults are regression_conditions ["state","background","invariant"] and diffusion_conditions ["state","regression","invariant"] (RWD config/model/stormcast.yaml).
- The dataset takes the background at the input time: ds_inp.sel(time=ts_inp) (RWD datasets/data_loader_hrrr_era5.py:364-368), with target = inp + dt (data_loader_hrrr_era5.py:400-408).
- Dataset outputs are already normalised (RWD datasets/dataset.py docstring). So normalisation must be reproduced exactly at serve time.

DarwinStormCast (DRAFT, standalone; mirrors stormcast.py):

```python
# track2/src/darwin_e2s/stormcast_px.py   DRAFT
from collections import OrderedDict
import json, numpy as np, torch, xarray as xr
from physicsnemo.core import Module
from physicsnemo.diffusion.noise_schedulers import EDMNoiseScheduler
from earth2studio.data import fetch_data
from earth2studio.models.auto import AutoModelMixin, Package
from earth2studio.models.batch import batch_coords, batch_func
from earth2studio.models.px.utils import PrognosticMixin
from earth2studio.utils import handshake_coords, handshake_dim
from earth2studio.utils.coords import map_coords
from darwin_e2s.recipe_compat import diffusion_model_forward
from darwin_e2s.norm import load_norm

class DarwinStormCast(torch.nn.Module, AutoModelMixin, PrognosticMixin):
    def __init__(self, regression, diffusion, state_vars, bg_vars, lat, lon, norm_state, norm_bg,
                 invariants, ocean_mask, background_source=None, dt=np.timedelta64(24, "h"),
                 bg_offset=np.timedelta64(0, "h"), reg_conditions=("state", "background", "invariant"),
                 dif_conditions=("state", "regression", "invariant"), sampler=None, mode="both", base_seed=0):
        super().__init__()
        self.regression, self.diffusion = regression.eval(), diffusion.eval()
        self.state_vars, self.bg_vars = np.array(state_vars), np.array(bg_vars)
        self.lat, self.lon = np.asarray(lat), np.asarray(lon)     # built as 90 - i*d, j*d (bitwise-equal to E2S lattice)
        self.norm_state, self.norm_bg = norm_state, norm_bg        # nn.Modules holding stats buffers
        self.register_buffer("invariants", torch.as_tensor(invariants, dtype=torch.float32)[None])  # normalized
        self.register_buffer("mask", torch.as_tensor(ocean_mask, dtype=torch.bool))
        self.background_source, self.dt, self.bg_offset = background_source, dt, bg_offset
        self.reg_conditions, self.dif_conditions = list(reg_conditions), list(dif_conditions)
        self.sampler = sampler or {"num_steps": 18, "solver": "heun", "sigma_min": 0.002, "sigma_max": 800.0,
                                   "rho": 7.0, "S_churn": 0.0}          # = RWD config/sampler/edm_deterministic.yaml
        self._sched = EDMNoiseScheduler(sigma_min=self.sampler["sigma_min"],
                                        sigma_max=self.sampler["sigma_max"], rho=self.sampler["rho"])
        self.mode, self.base_seed = mode, base_seed                 # mode "regression" = deterministic control

    def input_coords(self):
        return OrderedDict(batch=np.empty(0), time=np.empty(0), lead_time=np.array([np.timedelta64(0, "h")]),
                           variable=self.state_vars.copy(), lat=self.lat.copy(), lon=self.lon.copy())

    @batch_coords()
    def output_coords(self, input_coords):
        tgt = self.input_coords()
        for i, k in enumerate(tgt):
            if k in ("batch", "time"): continue
            handshake_dim(input_coords, k, i)
            if k != "lead_time": handshake_coords(input_coords, tgt, k)
        oc = tgt.copy()
        oc["batch"], oc["time"] = input_coords["batch"], input_coords["time"]
        oc["lead_time"] = input_coords["lead_time"] + self.dt
        return oc

    def _background(self, coords, device):
        if self.background_source is None:
            raise RuntimeError("DarwinStormCast needs background_source (physics DataSource/ForecastSource)")
        bg, bgc = fetch_data(self.background_source, time=coords["time"], variable=self.bg_vars,
                             lead_time=coords["lead_time"] + self.bg_offset, device=device, interp_to=None)
        # map_coords silently nearest-maps numeric coords (utils/coords.py:297-309): refuse off-grid sources
        if not (np.isin(self.lat, bgc["lat"]).all() and np.isin(self.lon, bgc["lon"]).all()):
            raise ValueError("background source is not on the model lattice; regrid upstream, never here")
        tgt = OrderedDict(time=bgc["time"], lead_time=bgc["lead_time"], variable=self.bg_vars, lat=self.lat, lon=self.lon)
        bg, _ = map_coords(bg, bgc, tgt)                            # reorder only (exact values present)
        return bg                                                   # [T, L, Cb, H, W]

    @torch.inference_mode()
    def _forward(self, x, bg, seed):
        m = self.mask[None, None]
        parts = {"state": torch.nan_to_num(self.norm_state(x)) * m,
                 "background": torch.nan_to_num(self.norm_bg(bg)) * m,
                 "invariant": self.invariants}
        reg = self.regression(torch.cat([parts[c] for c in self.reg_conditions], 1))
        out = reg
        if self.mode == "both":
            parts["regression"] = reg
            cond = torch.cat([parts[c] for c in self.dif_conditions], 1)
            with torch.random.fork_rng(devices=[x.device] if x.is_cuda else []):
                torch.manual_seed(seed)
                out = reg + diffusion_model_forward(self.diffusion, cond, reg.shape,
                                                    scheduler=self._sched, sampler_args=self.sampler)
        y = self.norm_state.clamp_nonneg(self.norm_state.inverse(out))   # per-variable
        return torch.where(m, y, torch.zeros_like(y))

    @torch.inference_mode()
    @batch_func()
    def __call__(self, x, coords):
        bg = self._background(coords, x.device)
        oc = self.output_coords(coords)
        y = x.clone()
        for i in range(x.shape[0]):
            for j in range(x.shape[1]):
                for k in range(x.shape[2]):
                    seed = hash((self.base_seed, int(coords["time"][j].astype("int64")),
                                 int(coords["lead_time"][k].astype("int64")), i)) % 2**31
                    y[i, j, k:k + 1] = self._forward(x[i, j, k:k + 1], bg[j, k:k + 1], seed)
        return y, oc

    @batch_func()
    def _default_generator(self, x, coords):
        coords = coords.copy(); self.output_coords(coords)
        yield x, coords
        while True:
            x, coords = self.front_hook(x, coords)
            x, coords = self.__call__(x, coords)
            x, coords = self.rear_hook(x, coords)
            yield x, coords.copy()

    def create_iterator(self, x, coords):
        yield from self._default_generator(x, coords)

    @classmethod
    def load_default_package(cls):
        raise NotImplementedError

    @classmethod
    def load_model(cls, package: Package, background_source=None, device=None):
        meta = json.load(open(package.resolve("metadata.json")))
        reg = Module.from_checkpoint(package.resolve("regression.mdlus"))   # StormCastUNet, as RWD inference.py:79
        dif = Module.from_checkpoint(package.resolve("diffusion.mdlus"))    # EDMPreconditioner, as RWD inference.py:83
        with xr.open_dataset(package.resolve("grid.nc")) as g:
            lat, lon, mask = g["lat"].values, g["lon"].values, g["ocean_mask"].values.astype(bool)
        with xr.open_dataset(package.resolve("invariants.nc")) as g:
            inv = np.stack([g[v].values for v in meta["invariant_variables"]])  # stored normalized
        m = cls(reg, dif, meta["state_variables"], meta["background_variables"], lat, lon,
                load_norm(package, "state"), load_norm(package, "background"), inv, mask, background_source,
                dt=np.timedelta64(int(meta["dt_hours"]), "h"),
                bg_offset=np.timedelta64(int(meta.get("background_offset_hours", 0)), "h"),
                reg_conditions=meta["regression_conditions"], dif_conditions=meta["diffusion_conditions"],
                sampler=meta["sampler"], base_seed=meta.get("base_seed", 0))
        return m.to(device) if device else m
```

Package for DarwinStormCast:
- metadata.json keys: state_variables, background_variables, invariant_variables, dt_hours, background_offset_hours, regression_conditions, diffusion_conditions, sampler, log_variables, log_floors, nonneg_variables, base_seed, recipe_commit, earth2studio_commit, train_period, test_period.
- stats.json: {"state": {v: {mean, std}}, "background": {...}, "invariants": {...}}, with stats in the TRANSFORMED space.
- grid.nc: lat (descending), lon, ocean_mask.
- invariants.nc.
- regression.mdlus (renamed StormCastUNet.0.N.mdlus).
- diffusion.mdlus (renamed EDMPreconditioner.0.N.mdlus).

The training dataset (RWD StormCastDataset subclass) and the wrapper must import the same darwin_e2s.norm and darwin_e2s.regrid. Condition order and background_offset must be read from one config that is written into metadata.json.

Ensembles: run.ensemble with perturbation Zero (earth2studio/perturbation/zero.py). run.ensemble repeats the IC over members (run.py:497-499), and __call__ loops over the flattened batch, so each member gets its own seed.

======================================================================
Q3. GRID
======================================================================

E2S conventions:
- Lat runs north to south, 90 to -90; lon runs [0, 360).
- Evidence: SFNO np.linspace(90,-90,721) / np.linspace(0,360,1440,endpoint=False) (models/px/sfno.py:188-189); FCN3 (fcn3.py:211-212); ARCO ERA5 (data/arco.py:79-80); SamudrACE flips its model grid to north-to-south "Public Earth2Studio convention" (models/px/samudrace.py:282-289).
- The generic CorrDiff contradicts this and requires ascending lat (corrdiff.py:287-292).
- map_coords can reverse or subset via its roll/slice/generic-fallback branches (utils/coords.py:247-289).
- For numeric coords NOT present in the input, map_coords SILENTLY maps to the nearest value (utils/coords.py:297-309).

What the standard 721x1440 grid buys: plumbing, not science.
- Any E2S DataSource or model on that lattice passes handshake_coords, which uses exact == (utils/coords.py:83-130).
- map_coords becomes a no-op.
- DiagnosticWrapper skips interpolation when the arrays are identical (models/px/dxwrapper.py:153).
- run.* regrids at fetch time only when the model has an interp_method attribute (run.py:137-142). Do NOT define that attribute; serve on-grid data instead, which avoids coastal NaN or zero bleed.

Limits:
- E2S atmosphere sources (ERA5, GFS) do not carry MLD, ocean Qsw or BGC. ECCO v4 forcing is not ERA5, so an ERA5 background at inference would shift the distribution unless the model is trained on ERA5.
- SamudrACE (px/samudrace.py) is an E2S ocean-physics prognostic that could in principle become a ForecastSource background. Its grid and variables are unverified.
- LLC270 cannot be regridded inside E2S. map_coords refuses 2-D grids (utils/coords.py:241-245), and the curvilinear path in prep_data_array assumes one structured 2-D array, not 13 LLC faces. Regrid upstream (xESMF conservative or an ECCO bin average) into Zarr.

UNet constraint:
- SongUNet requires H and W to be powers of 2 or multiples of 2**(N-1) (PNM physicsnemo/models/diffusion_unets/song_unet.py:348, 560-572).
- SongUNetPosEmbd has channel_mult [1,2,2,2,2] by default, so N=5 and dimensions must be multiples of 16 (song_unet.py:893). 721 fails.

RECOMMENDED lattice, with every grid an exact subset of the E2S 0.25 degree lattice and built from integers so that == holds bitwise:
- HR (CorrDiff target): lat = 90 - 0.25*np.arange(720) (90 to -89.75; drops only the south-pole row, which is land), lon = 0.25*np.arange(1440). 720/16 and 1440/16 are integers. map_coords can slice this out of 721x1440 (utils/coords.py:255-265).
- LR and StormCast grid (1 degree): lat = 90 - np.arange(176.0) (90 to -85; every dropped row is Antarctic land), lon = np.arange(360.0). Use SongUNet channel_mult of length 4 (N=4, multiples of 8): 176/8=22 and 360/8=45.
- 1 degree is about 16x cheaper per sample than 0.25 degree. For scale, StormCast's 512x640 domain needed 64 H100s for about 120 h (RWD README).
- The dx interpolation must wrap longitude periodically (359 to 360) and be land-aware. That is our lr_to_hr, not E2S interp.

======================================================================
Q4. THE FIRST END-TO-END RUN (DRAFT)
======================================================================

Why not run.diagnostic:
- It builds the IO coordinates only from the PROGNOSTIC's keys (run.py:252-273), so CorrDiff's "sample" dimension is never added.
- ZarrBackend.write then raises "Coordinate dimension sample not in zarr store" (io/zarr.py:225-259).
- The E2S CorrDiff example uses a hand-written loop for exactly this reason (examples/03_downscaling/01_corrdiff_inference.py).

Why DiagnosticWrapper + run.deterministic (traced, not executed):
- DiagnosticWrapper.output_coords returns the dx coordinates, sample included (dxwrapper.py:461-482, 177-204). run.deterministic therefore allocates time, lead_time, sample, lat, lon (run.py:98-117).
- The dx runs on every prognostic step, including step 0 = the IC (dxwrapper.py:516-548).
- The grid-identity check skips interpolation (dxwrapper.py:153).

STAGE 0, the first run: the full chain on real recipe checkpoints from a 10-step toy training.
- Goal: validate every interface the trained run will use, before any GPU money is spent.
- Where: AICR, inside a Slurm job with the track2 environment.
- Inputs: a 1 degree / 0.25 degree Zarr regridded from the monthly mirror; the recipe's config/test_diffusion_unet.yaml sizes (model_channels 32, channel_mult [1,2], sampler num_steps 2).
- Two recipe runs, 10 steps each: regression with regression_conditions [state, background, invariant], then diffusion with [state, regression, invariant]. Then package the files. For the dx, the same with [background, invariant] / [background, regression, invariant].

```python
# track2/scripts/e2s_stage0_chain.py   DRAFT
from collections import OrderedDict
import numpy as np, torch, zarr
from earth2studio.run import deterministic
from earth2studio.io import ZarrBackend
from earth2studio.models.auto import Package
from earth2studio.models.px import Persistence
from earth2studio.models.px.dxwrapper import DiagnosticWrapper
from darwin_e2s import EccoDarwinZarr, DarwinStormCast, DarwinCorrDiff

phys  = EccoDarwinZarr("/scratch/$USER/dd/v05_1deg.zarr", cadence="monthly", land_value=0.0)  # background
state = EccoDarwinZarr("/scratch/$USER/dd/v05_1deg.zarr", cadence="monthly", land_value=0.0)  # BGC IC
px = DarwinStormCast.load_model(Package("/scratch/$USER/dd/pkg_px_toy"), background_source=phys)
dx = DarwinCorrDiff.load_model(Package("/scratch/$USER/dd/pkg_dx_toy"))
dx.number_of_samples = 2
dev = torch.device("cuda:0")
times = ["2012-01-01"]

deterministic(times, 3, DiagnosticWrapper(px, dx), state,
              ZarrBackend("/scratch/$USER/dd/s0_model.zarr", backend_kwargs={"overwrite": True}), device=dev)
null = Persistence(variable=list(px.state_vars),
                   domain_coords=OrderedDict(lat=px.lat, lon=px.lon), dt=np.timedelta64(24, "h"))
deterministic(times, 3, DiagnosticWrapper(null, dx), state,           # null through the IDENTICAL pipe, same job
              ZarrBackend("/scratch/$USER/dd/s0_null.zarr", backend_kwargs={"overwrite": True}), device=dev)

g = zarr.open("/scratch/$USER/dd/s0_model.zarr")
v = dx.output_variables[0]
assert g[v].metadata.dimension_names == ("time", "lead_time", "sample", "lat", "lon")
assert g[v].shape == (1, 4, 2, 720, 1440)
assert (g["lead_time"][:] == np.arange(4) * np.timedelta64(24, "h")).all()
mask = np.load("/scratch/$USER/dd/pkg_dx_toy/ocean_mask_hr.npy")
a = g[v][:]
assert np.isfinite(a[..., mask]).all() and (a[..., ~mask] == 0).all()
```

Also add to track2/tests:
- The same script on a 32x64 toy grid, as the real-E2S counterpart to tests/test_e2s_conformance.py.
- A parity test: the recipe's own inference path (RWD inference.py:142-167) and DarwinStormCast._forward, run on the same normalised sample in mode="regression", must agree to 1e-5.

Stage 1, the first trained run, on the monthly data already on disk: the dx alone, run per month.
- Command: run.deterministic(time=<test-period month stamps>, nsteps=0, prognostic=DiagnosticWrapper(DataReplay(lr_source, lr_vars, OrderedDict(lat=..., lon=...), step=np.timedelta64(24,"h")), dx), ...).
- DataReplay replays a DataSource as a prognostic (models/px/datareplay.py). nsteps=0 writes step 0 only (run.py:171-185).
- Same job:
  - inference_mode="regression" (the deterministic control);
  - an interpolation-only dx (the naive-upsample null);
  - a climatology null via DataReplay over a train-only climatology DataSource;
  - truth via DataReplay(state_source), into the same Zarr layout.

Stage 2 (after the daily archive is re-downloaded): the StormCast-analog run.
- Command: run.ensemble(time=[init dates in the test years], nsteps=30, nensemble=8, prognostic=DarwinStormCast (dt=24h), data=state, io=ZarrBackend, perturbation=Zero(), batch_size=4).
- Baselines: Persistence and climatology through the same pipeline.

Stage 3: the chain (Stage 0 with trained packages).

Scoring:
- earth2studio.statistics rmse or crps with weights = lat_weight x ocean_mask (statistics/rmse.py:52-69, crps.py:68-85, weights.py:25-50).
- Land must be 0, not NaN: 0 x NaN = NaN.

======================================================================
Q5. WHAT THE EXISTING e2s WRAPPER GETS WRONG OR LACKS
======================================================================

src/darwindiff/e2s/prognostic.py:
1. DEFAULT_DT = 30 days (prognostic.py:29).
   - E2S lead-time arithmetic is fixed timedelta: dt*i (run.py:105-110) and t+lead (data/utils.py:83-99, 154).
   - Calendar months drift about 5 days per year. EccoDarwinV05 resolves to the nearest month (datasource.py:141), so after about 3 years, verification pulls the wrong month.
   - Monthly rollouts cannot be expressed in run.*. Use daily dt, or nsteps=0 per month.
2. torch.clamp(min=0) on ALL channels (prognostic.py:270).
   - This is wrong for THETA below 0 degC, SSSanom, SALTanom, CO2_flux, O2_flux and surfDIC_tend.
   - Make it a per-variable list.
3. No input masking.
   - NaN or land fill is standardised and fed to the model (prognostic.py:264-267); only the output is masked (271-273).
   - In an FNO a single NaN poisons the whole spectrum.
   - Use nan_to_num and the mask in normalised space, matching training.
4. @batch_func() is applied twice on __call__ (prognostic.py:276 and 282).
   - Harmless: re-compressing a batch-first 6-D tensor is idempotent (batch.py:122-130).
   - Remove one.
5. The output_coords(None) branch (prognostic.py:207) cannot be reached under the real @batch_coords.
   - _compress_batch calls len(coords) first (batch.py:324), which raises on None. SFNO has the same dead branch (sfno.py:216).
   - It only "works" through the shim.
6. _default_generator (prognostic.py:287-295) has no front_hook/rear_hook and no PrognosticMixin (compare stormcast.py:518-522).
7. No AutoModelMixin/Package loading. from_config (prognostic.py:157-188) takes tensors in memory, so there is no packaged metadata or stats.
8. No background or conditioning source, so it cannot express StormCast forcing. It is also deterministic only, with no ensemble or sample path.
9. Tests use lat -80..80 ascending (tests/test_e2s.py:25) and lat -5..15 with lon -160..-110 (tests/test_e2s_conformance.py:36-37).
   - They pass protocol checks but never meet an E2S-convention source.
   - No test runs run.deterministic with a real DataSource and ZarrBackend.

src/darwindiff/e2s/datasource.py:
10. Eager np.asarray(d["state"]) on the whole npz (datasource.py:49-50). A global 0.25 degree daily run cannot fit.
11. Raises for cubes without lats/lons (datasource.py:58-64). emulator_poc --dump-cube does not write them, so no existing cube can be served.
12. Positional int time and nearest-month resolution (datasource.py:88-98, 114-141). Neither is E2S semantics; resolve by exact date (daily) or calendar month (monthly), never nearest.
13. No async fetch. DataSource is @runtime_checkable with __call__ and fetch (data/base.py:28-83), so isinstance(ds, DataSource) is False. It is not enforced by run.py, and the E2S example omits it too (examples/08_extend/03_custom_datasource.py).

Replacement DataSource (DRAFT):

```python
class EccoDarwinZarr:   # DRAFT
    def __init__(self, store, cadence="daily", land_value=0.0):
        self.ds = xr.open_zarr(store)               # dims (time, lat, lon); lat 90->-90, lon [0,360)
        self.cadence, self.land_value = cadence, land_value
    def __call__(self, time, variable):
        time, variable = prep_data_inputs(time, variable)
        keys = [np.datetime64(t, "D") if self.cadence == "daily"
                else np.datetime64(np.datetime64(t, "M"), "D") for t in time]    # exact or calendar-month
        missing = [k for k in keys if k not in self.ds.indexes["time"]]
        if missing:
            raise KeyError(f"not in archive: {missing[:3]}")                      # never nearest
        da = (self.ds[list(variable)].sel(time=keys).to_array("variable")
              .transpose("time", "variable", "lat", "lon").fillna(self.land_value).astype("float32"))
        return da.assign_coords(time=np.array(time, dtype="datetime64[ns]")).load()
    async def fetch(self, time, variable):
        return self(time, variable)
```

======================================================================
ENVIRONMENT (per docs/findings/2026-09-30_earth2_air_pollution_recipe_is_not_a_track2_lever.md section 6)
======================================================================

- track2/pyproject.toml, a separate uv project with its own uv.lock:
  - earth2studio @ git+https://github.com/NVIDIA/earth2studio@2067756d489ad9195cf9e1ed52e074a4f8588ca4 (no model extras; E2S core pins netCDF4>=1.6.4,<1.7.3, pyproject.toml:22, and needs zarr>=3.1.3);
  - nvidia-physicsnemo @ git+https://github.com/NVIDIA/physicsnemo@536553acf5b03b68ec7283975ba7276d60056a36 (the E2S corrdiff extra needs >=2.0);
  - torch>=2.10 (RWD README; AICR ~/dd_venv has 2.11.0+cu128);
  - pydantic, hydra-core, tensordict, xarray, dask;
  - darwindiff by path through [tool.uv.sources].
- Vendor RWD at 536553a into track2/recipe/ (copy-the-folder), adding datasets/ecco_darwin.py (a StormCastDataset subclass that imports darwin_e2s.norm and darwin_e2s.regrid).
- Train and serve in the SAME environment, so that .mdlus class resolution matches.
- Build the environment inside a Slurm job on AICR. The Windows install of E2S core (pygrib) is unverified.
