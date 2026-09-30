# Dataset builder: grids, channels, store, daily download, split, calendar

> **Agent-drafted design part, banked verbatim from the 2026-09-30 design workflow** (six agents, read-only, physicsnemo@536553a, earth2studio@2067756d). Labels inside: [V] read at source, [I] inferred, [U] unverified. **Nothing here was executed through the physicsnemo trainer or earth2studio.** Where this part conflicts with `critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md`.

## Summary

I designed the dataset builder from the repo's loaders and checked it against the local mirror, the grid, and the upstream recipe code at pinned commits (physicsnemo 536553a, earth2studio 2067756). The recommendations below rest on those measurements.

**Fine grid:** 0.25 degree cell-centred, latitude -80 to 80, 640x1440. Both sides divide by 16, which the recipe's default U-Net needs (SongUNetPosEmbd, 5 levels). Pixels are an area-weighted mean of the native ocean cells inside them; ocean pixels with no native cell take the nearest native value. That is one sparse operator: 0.2 s to build, about 3 ms per field.

- The oversampling is measured: 184,557 of 626,173 ocean pixels (29.5%) contain no native cell centre and are copies of a neighbour.
- A 1/3 degree grid is more faithful (only 4.7% copies) but 540x1080 does not divide by 16, so it would need padding. It is the second choice.
- I cut the Arctic above 80N because the recipe's loss mask is on/off only (`trainer.py:530-564`). It cannot carry area weights, so over-sampled polar pixels would dominate the loss.

**Coarse grid:** 1 degree (180x360, cell edges on whole degrees) as the main input and 2 degrees as an ablation. Both are area-weighted from native cells and both nest exactly with the fine grid. For bilinear upsampling the coarse field gets land filled from the nearest ocean cell and a one-cell wrap-around border, 182x362. This matches earth2studio's non-periodic bilinear and passes its grid-bounds check.

**Land and time:** land is `Depth > 0`, which is identical to surface `hFacC > 0` (546,695 ocean cells). The layout needs no special handling: binning uses each cell's centre, so the Arctic face works for scalars.

- Time comes only from the iteration number at 1200 s. Every monthly file is stamped at a month end, so iter 2232 is the January 1992 mean.
- `rollout_verify.py:60-66` labels that record February, and `build_daily_surface_cube.py:229` labels daily records one day late. The builder labels records by the period they average.

**Sample counts on the monthly mirror:**
- With the 9 physics fields, there are 310 months: 164 train, 22 valid, 101 test.
- Per tracer it is 268 to 308 months.
- Requiring all BGC channels at once leaves only 97 months and 12 train pairs.
- Channels therefore get their own availability masks (the recipe supports per-channel masks), and models are trained per tracer or per tracer group.

**Transforms:**
- **asinh with a fixed scale** for FeT, PIC, POC and total chlorophyll (Chl1+2+3+5). Measured at the surface, 11.8-17.8% of total-chlorophyll cells and 16.5% of PIC cells are zero or negative, so a plain log would clip a lot.
- **log10** for mixed-layer depth.
- **Linear** for DIC, ALK and pCO2, where the log range is tiny.

**Storage:**
- float32 zarr (format 2), one chunk per timestep, land as NaN.
- Stats are computed on the training split only, area-weighted, and saved in both the physicsnemo layout and earth2studio's `stats.json`. float16 is ruled out: near DIC's 2,000 its step is 1-2 mmol/m3, as large as the monthly anomalies.

| product | 640x1440 fine | 1 degree coarse |
|---|---|---|
| monthly (323 steps, 17 fine channels) | 20.2 GB | 0.68 GB |
| daily (9,861 days, 9 core channels) | 327 GB | 10.4 GB |

**Daily download** (12 core 2-D variables): SST, SSSanom, wspeed, SIarea, SIheff, surfChl1/2/3/5, apCO2 (which is seawater pCO2 in the daily tree), CO2_flux and O2_flux.

- **Size:** at most 448.6 GB. That is about 25 hours at the 5 MB/s this machine gets, or about 48 minutes at the 2,481 files/min recorded on AICR.
- **Skip:** surfChl4, surfPCO2 (a byte copy of pCO2) and the full 50-level pCO2/pH files, which are about 5 TB.
- **pH:** its surface level alone is 37.4 GB if HTTP range requests work. I could not test that: the sandbox timed out connecting to data.nas.nasa.gov. The spec gives the exact curl test.

**Split:** train 1992-2005, gap 2006, valid 2007-2008, gap 2009, test 2010 to the end of the record. The test period matches the pre-registered one.

**Builder cost on this machine:** about 15-20 minutes and under 3 GB RAM for monthly, measured at 51-95 ms per surface read from D:. Build the daily set on AICR.

**Things you should know:**
- `POC.0000208152.data` is truncated to 120,001,674 bytes. Its surface level is intact.
- The monthly gaps may exist on the portal itself, not just in the mirror: the portal's Chl1 listing shows the same 289 data files you have. The spec gives a quick HEAD-request test.
- `diffusion_emulator.py:535` computes its normalization over all months, including validation, before splitting at line 538. That is a small leak. The new builder uses the training split only.

## Decisions

- **Fine target grid** → 0.25 deg cell-centred, lat -80..80, 640x1440 (q025). Keep 1/3 deg (540x1080, padded to 544x1088) as the native-respecting alternative, and 720x1440 only with a custom area-weighted loss.
  - why: 640 and 1440 both divide by 16, which SongUNetPosEmbd's 5-level channel_mult needs (song_unet.py:893 @536553a), with no padding tricks. The cost is measured: 29.5% of ocean pixels are nearest-native copies, so fine-scale spectra must stop at the native scale. 1/3 deg only needs 4.7% copies but is not divisible by 16. Dropping north of 80N matters because the recipe's mask is binary (trainer.py:530-564), so over-sampled polar pixels could not be down-weighted.
- **Regridding method** → One sparse operator per grid: RAC-weighted mean of native ocean cell centres per pixel, nearest native ocean cell for empty ocean pixels, land = pixel whose centre's nearest native cell is land (Depth>0). Longitude is wrapped modulo, never dropped. Build coarse grids from native cells, not from the fine grid.
  - why: Conservative at 1 and 2 deg, a pure native resample at 0.25 deg, never smears across land, and independent of the LLC face layout (the Arctic facet needs nothing special for scalars). Measured at 0.2 s to build and 3 ms per field. The existing binned_statistic_2d paths are unweighted, leave about 30% holes at 0.25 deg, and build_daily_surface_cube drops the 179.5-180 strip.
- **Coarse (CorrDiff input) grid** → 1 deg primary (180x360, edges on whole degrees), 2 deg ablation. Store land-filled (nearest ocean) with a 1-cell periodic/pole halo (182x362) for bilinear upsampling.
  - why: Both nest the fine grid exactly (4x, 8x). The halo makes earth2studio's non-periodic, clamped bilinear (interp.py:43-103) correct at the dateline and passes CorrDiff's grid-bounds check (corrdiff.py:388-421). Filling land removes NaN poisoning of the bilinear.
- **Transform of positive-definite, wide-range tracers** → asinh(x/s) with fixed s (FeT 1e-5, PIC 1e-4, POC 1e-3, CHL 1e-2), log10 for mldDepth, linear for DIC/ALK/pCO2/physics. Offer 'logfloor' only for parity with emulator_poc.
  - why: Measured surface fractions <=0: total Chl 11.8-17.8%, PIC 16.5%, POC 2.6%, so a log would clip heavily. asinh is exactly invertible, log-like above s, and a fixed s leaks nothing from validation or test. DIC/ALK/pCO2 have p99/p1 of only 1.25-2.23.
- **Chlorophyll channel** → CHL = Chl1+Chl2+Chl3+Chl5; per-PFT channels optional.
  - why: Chl4 is <=0 in 83.9% of surface cells, and requiring it cuts the physics-joint intersection from 183 to 163 months. Total chlorophyll is the observable MODIS measures.
- **Handling the monthly availability gaps** → Store the full calendar axis with per-channel avail flags and per-channel loss masks. Train per tracer (or per group: carbonate, particles) rather than all 8 BGC channels jointly. A sample is valid only if all its INPUT channels are present.
  - why: Measured with the 9 physics fields: 310 months total, 268-308 per tracer, but only 97 months (12 train pairs) for all 8 jointly. The recipe supports (C,H,W) masks (dataset.py:42-54), and the full calendar axis makes gap-bridging pairs impossible.
- **Storage precision and format** → float32 zarr (zarr_format=2, consolidated), chunks (1, C, H, W), Blosc zstd-3, land as NaN, normalization applied in the Dataset. bf16 only as training AMP.
  - why: float16 spacing is 1-2 mmol/m3 for DIC/ALK, the size of monthly anomalies. Format 2 opens with both zarr-python 2 and 3 (the repo venv has 3.2.0). One chunk per timestep means one read per sample, and parallel workers can write without locks.
- **Normalization statistics** → Per channel, per split, TRAIN only, ocean pixels only, area-weighted, in transformed space. Write both npy (regional_weather_diffusion) and stats.json (earth2studio). Input stats are computed on the UPSAMPLED coarse field.
  - why: earth2studio normalizes after interpolation (corrdiff.py:975-986). diffusion_emulator.py:535 computes stats over all months including validation, which the new builder must not repeat.
- **StormCast background** → Primary: physics(t+dt) plus physics(t) plus day-of-year(t+dt). Ablation: physics(t) only, as in the StormCast paper.
  - why: Offline Darwin is driven by known ECCO physics, so forcing at t+dt is legitimate. The t-only ablation separates step skill from same-time diagnosis. HRRR uses the background at input time (data_loader_hrrr_era5.py:364-368).
- **Split** → std12: train 1992-2005, gap 2006, valid 2007-2008, gap 2009, test 2010 to end. Also rev12 and 6/24-month-gap variants, each with its own stats.
  - why: The test period is identical to the pre-registered diagnostic (2026-09-30 finding line 148). 12-month gaps exceed the ENSO-scale memory and the daily lag-1 e-folding.
- **Calendar labelling** → Label each record by its averaging window from the iteration number (end = iter*1200 s; month = month containing end-1s; day = end-1d), assert every stamp is a boundary, and store raw iter.
  - why: rollout_verify.py:60-66 labels the January record as February, and build_daily_surface_cube.py:229 labels daily records one day late. All 323 local monthly stamps are exact month ends (measured), so the assert would catch any 900 s regression.
- **Daily download scope and location** → 12 core 2-D vars (448.6 GB max) downloaded and built on AICR inside a Slurm job. Skip surfChl4, surfPCO2 and full 50-level pCO2/pH. Take pH level 0 by HTTP range only after the 206 test passes, and pCO2 level 0 only if it differs from daily apCO2.
  - why: AICR measured 2,481 files/min against about 5 MB/s locally (about 25 h). Full 50-level files are about 5 TB for one needed level. D: is a USB HDD with 1,007 GB free.
- **Where the builder code lives** → src/darwindiff/e2data/ in the main package (numpy/scipy/zarr only). The physicsnemo Dataset classes and the earth2studio CorrDiff subclass go in track2/. The zarr + stats.json + manifest are the interface between them.
  - why: The builder needs no physicsnemo or earth2studio import, so it does not hit the netCDF4<1.7.3 conflict, runs where the raw data is (Windows D: for monthly), and stays under the main CI.

## Risks

- Sample count, not compute, binds. Monthly per-tracer training sets are 144-164 months (122-159 one-month pairs), and the all-BGC joint set is 51 months. The settled findings say the diffusion stage memorises at N<=100 and cannot add deterministic skill over its regression stage, so the grading must lead with the regression U-Net against the nulls.
- 0.25 deg oversampling. 184,557 of 626,173 ocean pixels (29.5%) are nearest-native copies, so any spectral or 'sharpness' metric above the native wavenumber (about 0.32 deg) is an artifact of the regridding.
- The CorrDiff task is super-resolution of a box average of the same run (2026-09-30 finding section 4), so the 'coarse upsampled + climatological fine-scale residual' null is mandatory. Without it, apparent downscaling skill is mostly static fine-scale pattern.
- earth2studio's generic CorrDiff takes all inputs on ONE grid (corrdiff.py:936-988). Serving coarse BGC + fine physics needs a subclass. If training and serving upsample differently the model silently degrades, hence the parity test.
- regional_weather_diffusion's mask is binary (trainer.py:530-564), so the loss is unweighted by area. Including polar rows (q025g) would over-weight the Arctic, which is why the default domain stops at 80N.
- Monthly gaps may be archive-side. The portal's Chl1 listing (D:\ecco_darwin_v5\filelists_monthly\Chl1.txt) shows 289 .data, equal to the local count, which contradicts the handoff's 'mirroring accident' reading. If they are archive gaps, no refill will raise the counts.
- POC.0000208152.data is truncated (120,001,674 of 189,540,000 bytes). Its level 0 is intact, but a strict size check will drop the month; the builder must record the choice.
- HTTP range support is untested. If the portal ignores Range, pH level 0 costs a full 1.66-1.87 TB download, and a 200 response without --max-filesize would silently pull 190 MB per file.
- Daily physics lacks MLD, Qsw and Qnet, and the daily archive has no DIC/ALK/FeT/PIC/POC. The daily variant therefore only covers chlorophyll, pCO2 and fluxes, which SamudraBGC already contests. Daily lag-1 r of about 0.995 makes persistence and seasonal AR(1) very strong nulls.
- Daily apCO2 is seawater pCO2 but monthly apCO2 is atmospheric (handoff:183-185). Routing daily through llc270_loader.TRAC_MAPPING mislabels it; the builder must assert the fldList.
- float16 storage would quantize DIC/ALK at 1-2 mmol/m3, the size of the monthly signal.
- Disk. C: has 48 GB free; D: is a USB 3.0 HDD with 1,007 GB free, so a local daily build (raw 449 GB + zarr) would use most of it. /scratch on AICR purges after 30 days and the persistent path is unrecovered.
- diffusion_emulator.py:535-538 z-scores over all months before splitting (validation leaks into the stats). Earlier cubes also used an unweighted, hole-leaving 0.25 deg binning. Numbers from those paths must not serve as baselines for the new dataset without re-running.
- GPU memory for a 640x1440 SongUNet on the 5090 is not measured. Plan the local smoke run on a 256x512 crop.

## Unknowns

- Whether data.nas.nasa.gov honours HTTP Range (a 206 response). The sandbox could not connect (TCP timeout on 443), so this is unverified; the spec gives the curl test.
- Whether the roughly 11% missing monthly .data files exist on the portal (HEAD each missing month-end iter: 200 vs 500).
- The exact fldList of the daily apCO2 files, and whether daily pCO2 level 0 is bitwise equal to daily apCO2. Monthly surfPCO2 equals pCO2 level 0 by quantiles (measured), but daily is unverified.
- True per-variable daily file counts. The local listings are truncated (SIarea stops at iter 460,296); the only recorded counts are surfChl1 9,796, SST 9,794 and wspeed 9,791 from the 2026-07-30 finding.
- The persistent (non-purged) AICR storage path; the handoff marks it UNRECOVERED.
- Current download throughput from AICR to the portal (2,481 files/min was measured in July 2026).
- Actual zarr compression ratio on these fields (45-55% is an estimate).
- Whether SongUNetPosEmbd strictly requires divisibility by 16, inferred from channel_mult length 5 and not run.
- Memory and throughput of the regional_weather_diffusion U-Net at 640x1440 on the 5090 and B200.
- Whether asinh scale constants tuned per variable would change skill; the chosen s values are design choices, not tuned.
- Daily negative-value fractions for surfChl1/2/3/5 in total. The handoff gives per-PFT daily fractions at the median step (surfChl1 9.4%, surfChl2 26.5%, surfChl3 39.7%, surfChl5 41.3%), but the daily summed total was not measured.

## Spec

DATASET BUILDER SPEC for the Earth-2 CorrDiff / StormCast replication on ECCO-Darwin v05
(read-only design; nothing in the repo was modified; measurements run from scratchpad scripts against D:\ecco_darwin_v5)

=====================================================================
0. PINNED UPSTREAM + WHAT THE BUILDER MUST SATISFY
=====================================================================
physicsnemo main @ 536553acf5b03b68ec7283975ba7276d60056a36 (2026-09-30), examples/weather/regional_weather_diffusion:
- datasets/dataset.py:23-60  StormCastDataset contract: __getitem__ -> {"background": (Cb,H,W), "state": x or [x_t, x_t+1], optional "mask"}; the mask broadcasts to (C_state,H,W), so per-channel masks (C,H,W) and (C,1,1) are allowed. Outputs must be ALREADY normalized.
- README.md:126-129  CorrDiff = conditions ["background"] (+"regression" for the diffusion stage); StormCast = ["state","background"]; "invariant" via get_invariants().
- datasets/data_loader_hrrr_era5.py:32-61 (zarr per year under train/valid/test), :94-109 (means.npy/stds.npy per channel), :127-142 (invariants.zarr), :302-317 (missing_samples list), :364-368 (background is interpolated to the STATE grid at the INPUT time). So the background must arrive at (H,W) of the state: the coarse field is upsampled inside the Dataset.
- utils/trainer.py:524-564  mask -> invalid = mask < 0.5; weight = 1 - invalid. The mask is BINARY, so area weights cannot go through it.
- config/model/stormcast.yaml: model_type SongUNetPosEmbd; physicsnemo/models/diffusion_unets/song_unet.py:893 default channel_mult [1,2,2,2,2] (4 downsamplings) -> H and W must be divisible by 16 (inferred from the architecture).
- requirements.txt: torch>=2.10 (the AICR ~/dd_venv has 2.11). README.md:229: amp-bf16 is fine for U-Nets.
earth2studio main @ 2067756d489ad9195cf9e1ed52e074a4f8588ca4:
- earth2studio/models/dx/corrdiff.py:240-298  lat/lon must be 1-D and INCREASING. :388-421 output grid must lie inside the input grid (grid_bounds_margin default 0). :690-745 metadata.json + stats.json {"input":{v:{mean,std}},"output":{...},"invariants":{...}} + output_latlon_grid.nc. :753-772 input_latlon_grid.nc or latlon_res. :776-818 invariants.nc. :936-988 ALL inputs are interpolated from ONE input grid, then invariants are concatenated, then (x-mean)/std. Mixed coarse+fine inputs therefore need a subclass that overrides _interpolate/preprocess_input (the docstring at :902-906 invites this).
- earth2studio/utils/interp.py:43-103  latlon_interpolation_regular = bilinear, NON-periodic, index-clamped; any NaN neighbour poisons the output. Inputs must be NaN-free and carry a periodic halo.

=====================================================================
1. GRIDS AND REGRIDDING
=====================================================================
Native facts (measured from D:\ecco_darwin_v5\grid, compact 270x3510 big-endian f32, 947,700 cells):
- Ocean: Depth>0 == hFacC[k=0]>0 == 546,695 cells (identical sets); land 401,005 cells, exactly 0.0 in data files (DIC and SST checked: 401,005/401,005; 0 ocean zeros for DIC).
- sqrt(RAC): about 35.5 km at the equator (~0.32 deg in both directions), 26 km at 30-57N, 14.8 km at 60-80S (dlat about 0.13 deg, dlon about 0.33 deg), 14.2 km in the Arctic. Ocean YC runs -78.45 to 89.91.
- Arctic facet (compact rows 1620:1890): 52,533 ocean cells, YC 68.07-89.91, XC spanning -180..180.
So 1/3 deg matches native spacing in the tropics. 0.25 deg OVERSAMPLES low latitudes and zonal spacing everywhere, while it still averages 1-2 native rows meridionally poleward of about 50 deg.

Candidate target grids (cell-centred, edges at lat0 + k*res and -180 + k*res), measured with the operator below:
| name | res | lat range | HxW | ocean px | hole-filled (no native centre) | /16 |
| q025 (RECOMMENDED fine) | 0.25 | -80..80 | 640x1440 | 626,173 | 184,557 (29.5%) | yes (40, 90) |
| q025g | 0.25 | -90..90 | 720x1440 | 680,347 | 222,594 (32.7%) | yes |
| t3 (native-respecting alt) | 1/3 | -90..90 | 540x1080 | 384,102 | 18,211 (4.7%) | no: pad to 544x1088 (periodic lon wrap, masked) |
| c1 (RECOMMENDED coarse) | 1 | -90..90 | 180x360 | 44,346 | 284 (polar) | n/a |
| c2 (ablation coarse) | 2 | -90..90 | 90x180 | 11,545 | 8 | n/a |
Do NOT use earth2studio's point-registered 721x1440. 721 is odd, and our output grid is declared in our own output_latlon_grid.nc anyway.

Method (one function, used for every grid and every scalar field):
- W = sparse CSR (n_pix x 947,700), rows row-normalised.
- (a) Every native OCEAN cell goes to the pixel containing its centre (lat floor; lon floor modulo nlon, so there is no dateline seam) with weight RAC. This is an area-weighted mean.
- (b) An ocean pixel with no native centre gets weight 1 on the nearest native ocean cell (cKDTree on unit-sphere xyz).
- (c) A pixel is ocean iff the nearest native cell (land or ocean) to its centre is ocean, OR it received (a).
- Apply: fine = W @ native_k0 (float64), NaN outside valid. Measured: build 0.2 s, apply 2.9 ms (q025), nnz 713,364.
- This is conservative for coarse targets and a nearest-native resample for fine targets. It never interpolates across land, and the LLC face layout is irrelevant for scalars.
- Vectors (uVel_C/vVel_C, not in the channel lists) must be rotated first: u_e = AngleCS*u - AngleSN*v, v_n = AngleSN*u + AngleCS*v (AngleCS/SN.data present in the grid dir).
- Coarse grids are built from NATIVE cells with the same W construction (not from the fine grid). The builder reports blockavg(fine) - coarse as a diagnostic.
- Coarse input for upsampling: fill land by nearest ocean (scipy.ndimage.distance_transform_edt indices, lon wrapped by 3 columns before the transform), then add a halo: 1 periodic column each side and 1 replicated row at each pole. c1 becomes 182x362 (lat -90.5..90.5, lon -180.5..180.5), c2 becomes 92x182. Bilinear to the fine centres uses the exact interp.py:43-103 arithmetic, reimplemented in numpy/torch and parity-tested in the track2 env.

Why not the existing code paths:
- bin_to_1deg_grid (llc270_loader.py:378-425) and emulator_poc._bin_grid (emulator_poc.py:341-358) compute UNWEIGHTED means (binned_statistic_2d) with no hole fill. At --grid-res 0.25 (emulator_poc.py:143-145) about 30% of ocean pixels come out NaN and are then excluded by valid_mask (emulator_poc.py:505), producing Swiss-cheese targets.
- bin_native_tracer_to_1deg masks with `mean_field != 0` (llc270_loader.py:490-494), which drops real zeros (SIarea is 73.9% exact zero on ocean).
- build_daily_surface_cube.build_bin_index (build_daily_surface_cube.py:109-125) DROPS cells with XC in [179.5,180) and YC>89.5 instead of wrapping. It is also integer-centred like bin_average, which is fine but offset 0.5 deg from c1.
- Keep build_daily_surface_cube's Depth>0 mask rule (lines 61-90) and its per-file size refusal (lines 211-215).

Arctic and loss weighting: the q025 domain stops at 80N because north of it a lat-lon grid multiplies longitudes (1 deg of lon is under 10 km beyond 85N), and the recipe mask cannot down-weight them. The south loses nothing (ocean YC min -78.45). Use q025g only with a custom loss weight.

=====================================================================
2. CHANNELS (names are the zarr channel names; transform in brackets)
=====================================================================
Transforms (fixed constants, no data-dependent floors, so no leakage; all stored in the manifest):
- asinh(x/s): FeT s=1e-5 mmol/m3; PIC s=1e-4; POC s=1e-3; CHL s=1e-2 mg/m3.
  Measured surface <=0 fractions over 6 sampled months: CHL total 11.8-17.8%, PIC 16.5%, POC 2.6%, FeT 0.31%, Chl4 83.9%. log would clip these; asinh is exact-invertible and log-like above s.
- Optional --positive-transform logfloor reproduces emulator_poc (log_floors p1 of train positives, emulator_poc.py:624-648) for parity, recording the clipped fraction.
- log10: mldDepth (min 5 m, p99/p1 = 81.5).
- linear: DIC, ALK (p99/p1 = 1.25/1.29), pCO2 (2.23), physics.
- Units: pCO2/apCO2 atm x 1e6 -> uatm; CO2_flux/O2_flux mol m-2 s-1 x 8.64e7 -> mmol m-2 d-1.
- CHL = Chl1+Chl2+Chl3+Chl5. Chl4 is excluded: 83.9% of surface cells <=0, and adding it costs 20 months of intersection. Monthly surfPCO2 (2-D) is used instead of 3-D pCO2: identical k0 quantiles, 321 vs 278 files.

MONTHLY (local mirror, available now; 323 calendar months Jan 1992 - Nov 2018):
- BGC8 = [DIC, ALK, asinh_FeT, asinh_PIC, asinh_POC, asinh_CHL, pCO2(surfPCO2), CO2_flux]
- PHYS9 = [SST, SSSanom, log10_MLD(mldDepth), wspeed, oceanQsw, oceanQnet, SIarea, SIheff, apCO2(atmospheric EXFapco2)]
- TIME2 = [doy_sin, doy_cos] of the averaging-window midpoint (constant planes)
- INV7 = [ocean, ocean_frac, log10_depth, sin_lat, cos_lat, sin_lon, cos_lon]; plus cell_area_ocean (m2), stored for SCORING only.
CorrDiff monthly (downscaling at time t):
- background = up(c1 coarse of target group) + PHYS9(t) fine + TIME2
- state = target group fine(t)
- mask = ocean & avail(t, c)
- conditions: regression ["background","invariant"]; diffusion ["background","regression","invariant"]
StormCast monthly:
- state = [G(t), G(t+1)]; background = PHYS9(t+1) + PHYS9(t) + TIME2(t+1)
- sample valid iff all inputs are present at t and t+1; target channels masked per channel
- conditions ["state","background","invariant"]
- Ablation: PHYS9(t) only (StormCast-faithful). The primary run uses t+1 because offline Darwin is driven by known ECCO physics.
Target groups G, sized by the measured intersection with PHYS9 (train/valid/test months; one-month pairs):
- Per tracer (RECOMMENDED first):
  - DIC 144/20/86 (pairs 123/16/67); ALK 145/18/88; FeT 147/19/92; PIC 146/17/86; POC 144/19/94
  - surfPCO2 164/22/100; CO2_flux 164/22/98; Chl1 146/21/88; CHL(1,2,3,5) 101/14/54 (pairs 59/8/26)
- Carbonate {DIC,ALK,pCO2,CO2_flux}: 126/16/72, pairs 92/9/47
- Particle {PIC,POC}: 127/14/79, pairs 98/6/59
- All 8 at once: 51/7/31, pairs 12/1/8. Do not train this.
DAILY (after download; 9,861 records):
- BGC_D = [asinh_CHL(surfChl1+2+3+5), pCO2(daily apCO2 dir = seawater surfpCO2 per handoff:183-185), CO2_flux, O2_flux]; optional [pH_k0 (range-read), surfDIC_tend]
- PHYS_D = [SST, SSSanom, wspeed, SIarea, SIheff]. The archive has no daily MLD, Qsw, Qnet, DIC, ALK, FeT, PIC or POC.
- CorrDiff daily: background = up(c1 BGC_D) + PHYS_D(t) + TIME2; state = BGC_D(t); per-channel mask (each var misses about 0.7% of days, and different days, 2026-07-30 finding section 2).
- StormCast daily: state = [BGC_D(t), BGC_D(t+dt)]; background = PHYS_D(t+dt) + PHYS_D(t) + TIME2(t+dt); dt in {1, 5} days (lag-1 r about 0.995).

=====================================================================
3. STORAGE (zarr) AND SIZES
=====================================================================
Layout under <out> (D:\e2data\v05_monthly locally; the persistent AICR path for daily is unverified):
  manifest.json          builder git SHA, argv, DELTA_T=1200, EPOCH=1992-01-01, grid defs, ChannelSpec list (source dir, fldList asserted, transform, scale, unit factor), per-file (path, iter, size, truncated flag), remap stats, split defs
  grid_q025.nc, grid_c1.nc, grid_c2.nc   (lat, lon float64 ascending; c* with halo) -> copied verbatim as earth2studio output_/input_latlon_grid.nc
  remap_q025.npz, remap_c1.npz, remap_c2.npz   (CSR data/indices/indptr, valid, n_binned, n_holefilled)
  fine_q025.zarr   zarr_format=2, consolidated
      bgc      (time, channel, lat, lon) float32  chunks (1, C, 640, 1440)  Blosc(zstd, clevel=3, shuffle)  NaN = land or missing
      physics  (time, channel, lat, lon) float32  chunks (1, C, 640, 1440)
      avail_bgc, avail_physics (time, channel) bool
      coords: time (window start, datetime64[ns]), window_end, iter (int64), channel (str), lat, lon
  coarse_c1.zarr   bgc_raw (time, channel, 180, 360) NaN-land;  bgc (time, channel, 182, 362) land-filled + halo;  chunks (32, C, H, W)
  coarse_c2.zarr   same with 90x180 / 92x182
  invariants_q025.zarr   invariants (channel, lat, lon) float32 [INV7] + cell_area_ocean
  splits/<name>/split.json, stats.json (earth2studio format; input stats are computed on the UPSAMPLED coarse field over fine ocean pixels, because corrdiff.py:975-986 normalizes after interpolation), means_bgc.npy, stds_bgc.npy, means_physics.npy, stds_physics.npy, means_inv.npy, stds_inv.npy (regional_weather_diffusion style), climatology_q025.zarr (12, C, H, W) monthly or harmonic (7, C, H, W) daily, ar1_phi_q025.npy (C, H, W). All computed from TRAIN only, ocean pixels only, area-weighted in transformed space.
- The full calendar axis is stored, with avail flags, so t+1 is always index+1. A missing month cannot be silently bridged: the #191 uniform-sparse class of bug is structurally impossible.
- float32 on disk. float16 spacing is 1.0 for 1024-2048 and 2.0 for 2048-4096, i.e. 1-2 mmol/m3 for DIC/ALK, the size of monthly anomalies. bf16 only as training AMP.
Uncompressed float32 sizes (float16 = half; compressed with land-NaN about 45-55% is an estimate, unverified). Per channel-step: q025 3.686 MB, q025g 4.147 MB, t3 2.333 MB, c1-halo 0.2635 MB, c2-halo 0.0670 MB.
- Monthly (323 steps; fine 17 ch = BGC8 + PHYS9; coarse 8 ch): q025 20.24 GB; q025g 22.77 GB; t3 12.81 GB; c1 0.68 GB (+0.67 GB bgc_raw); c2 0.17 GB. Climatology q025 0.75 GB.
- Daily (9,861 steps; fine core 9 ch = BGC_D + PHYS_D, full 11 with pH_k0 and surfDIC_tend; coarse 4/6 ch): q025 327.2 / 399.9 GB; q025g 368.1 / 449.9 GB; t3 207.0 / 253.1 GB; c1 10.4 / 15.6 GB; c2 2.6 / 4.0 GB. Harmonic climatology (7 coeffs x 9 ch) 0.23 GB.
- Disk: D: has 1,007 GB free but is a USB 3.0 HDD (TOSHIBA External); C: has 48 GB free. Monthly goes on D: and fits in RAM (63.5 GB) for training. Daily should be built on AICR.

=====================================================================
4. DAILY DOWNLOAD PLAN
=====================================================================
- Record grid: iter = 72k, k = 1..9,861 (72 .. 709,992). Record k averages day k-1: iter 72 = 1992-01-01 (starts at 1200 s), 709,992 = 2018-12-30 (2026-07-30 finding section 1).
- Missing files return HTTP 500. Do not scrape listings: the local D:\ecco_darwin_v5\filelists show SIarea stopping at iter 460,296, i.e. truncated.
- 2-D files: 3,790,800 B each (947,700 x f32 BE). 50-level files: 189,540,000 B.
- CORE set (12 x 2-D): SST, SSSanom, wspeed, SIarea, SIheff, surfChl1, surfChl2, surfChl3, surfChl5, apCO2, CO2_flux, O2_flux = <= 12 x 9,861 x 3,790,800 = 448.6 GB (417.8 GiB).
- Optional: surfDIC_tend 37.4 GB; pH level 0 by range 37.4 GB.
- SKIP:
  - surfChl4 (dead channel, 2026-07-30 logspace finding)
  - surfPCO2 (fldList pCO2, a 50-level byte duplicate; handoff:131-133)
  - full 50-level pCO2/pH/surfPCO2 (~4.97 TB at the listed 8,707-8,771 files each; 5.61 TB max)
  - pCO2 k0, if it equals daily apCO2 (test below)
- Throughput: local single keep-alive curl about 5 MB/s (memory note; parallel connections trip the throttle) -> about 25 h. AICR manifest method 2,481 files/min (handoff:113-114) -> 118,332 files in about 48 min. Download inside a Slurm job, not on the login node.
HTTP range test (UNVERIFIED: my HEAD request from this sandbox timed out connecting to data.nas.nasa.gov:443):
  URL=https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/daily/pH/pH.0000000144.data
  curl -sIk "$URL"   # expect 200, Accept-Ranges: bytes, Content-Length: 189540000
  curl -sk -r 0-3790799 --max-filesize 3790800 -o pH.0000000144.k0 -w '%{http_code} %{size_download}\n' "$URL"   # must print "206 3790800"; 200 = ranges ignored (max-filesize aborts the 190 MB body)
  python: a=np.fromfile('pH.0000000144.k0','>f4'); assert a.size==947700; assert (a[Depth==0]==0).all(); ocean pH in about [7.6, 8.4]
  once: full-download that one file and `cmp -n 3790800` against the .k0
  bulk: curl -sk -r 0-3790799 --max-filesize 3790800 -K pH.cfg (url=/output= pairs, one keep-alive connection); verify every file is exactly 3,790,800 B
  pCO2 redundancy: range-fetch pCO2.0000000144.data k0 and np.array_equal with daily apCO2.0000000144.data. Monthly already shows surfPCO2 == pCO2 k0 (identical quantiles, measured).
Level 0 = first 947,700 floats because k is outermost (iron_forcing_loader.py:136-154, emulator_poc.py:390-394).
Monthly refill test: for each missing month-end iter, `curl -sIk -o /dev/null -w '%{http_code}'` on .../output/monthly/<var>/<var>.<iter>.data. 200 = recoverable (surface-only via range: about 237 x 3.79 MB = 0.9 GB instead of 41.8 GiB); 500 = archive gap.

=====================================================================
5. CALENDAR AND SPLIT
=====================================================================
- DELTA_T = 1200 s, 72 iters/day (llc270_loader.py:169; build_daily_surface_cube.py:57, 247-253). Never 900, and never stored times_days.
- Monthly: end = EPOCH + iter*1200 s. The averaged month is the month containing end - 1 s. All 323 local monthly stamps are exact month boundaries (measured: 0 off-boundary within 1992-2018): iter 2232 = Jan 1992, last = Nov 2018. apCO2 carries 12 extra 2019 records, which are dropped.
- The builder raises if a stamp is not a boundary, which a 900 s regression would trip immediately.
- Split "std12" by averaging-window date (year lists, like hrrr_era5.yaml train_years/valid_years):
  - train 1992-01 .. 2005-12
  - GAP 2006
  - valid 2007-01 .. 2008-12
  - GAP 2009
  - test 2010-01 .. 2018-11 monthly / 2018-12-30 daily
  The test matches the pre-registered diagnostic in docs/findings/2026-09-30_earth2_air_pollution_recipe_is_not_a_track2_lever.md:148.
- Robustness splits: "rev12" (train 2010-2018, test 1992-2005), gaps 6 and 24 months. Stats and climatology are recomputed per split.
- Daily std12: 5,114 train days, 731 valid, 3,286 test.

=====================================================================
6. BUILDER MODULE (draft outline)
=====================================================================
Location: src/darwindiff/e2data/ in the MAIN package (needs only numpy/scipy/zarr/xarray, all already declared: pyproject.toml:34,40). The physicsnemo Dataset classes live in track2/ (the copied regional_weather_diffusion folder, own uv.lock). The zarr + stats.json + manifest are the contract between them.

e2data/calendar.py
  DELTA_T_S=1200.0; ITERS_PER_DAY=72; EPOCH=np.datetime64('1992-01-01')
  def window(it:int, cadence:str)->tuple[np.datetime64,np.datetime64]   # monthly: (floor_month(end-1s), end); daily: (end-1d, end); raises on non-boundary
  def month_end_iters(first='1992-01', last='2018-11')->np.ndarray      # 323 iters
  def daily_iters()->np.ndarray                                          # 72*arange(1, 9862)
  def doy_features(start, end)->tuple[float,float]
  def self_check()  # 2232->1992-01; 709992->2018-12-30; 86400/1200==72

e2data/grids.py
  @dataclass(frozen=True) class TargetGrid(name:str, res:float, lat0:float, lat1:float, halo:int=0)
      nlat, nlon, lat, lon (float64 ascending centres), cell_area (m2)
  GRIDS = {'q025':TargetGrid('q025',0.25,-80,80), 'q025g':(...,-90,90), 't3':(1/3,-90,90), 'c1':(1.0,-90,90,halo=1), 'c2':(2.0,-90,90,halo=1)}
  @dataclass class NativeGeom(xc, yc, rac, depth, ocean, angle_cs, angle_sn)   # flat [947700]
  def load_native_geometry(grid_dir)->NativeGeom      # asserts ocean count 546,695 and Depth>0 == hFacC[0]>0
  @dataclass class RemapOp(W:csr_matrix, valid:np.ndarray, grid:TargetGrid, n_binned:int, n_holefilled:int, ocean_frac:np.ndarray)
      def apply(self, native:np.ndarray)->np.ndarray   # (nlat,nlon) float64, NaN outside valid
  def build_remap(geom, grid, hole_fill:bool=True)->RemapOp
  def fill_land_nearest(field, valid, wrap_cols:int=3)->np.ndarray
  def add_halo(field, grid)->np.ndarray                 # periodic lon col, replicated pole rows
  def upsample_bilinear(coarse_h, lat_h, lon_h, lat_f, lon_f)->np.ndarray  # exact interp.py:43-103 arithmetic
  def rotate_uv(u, v, geom)->tuple                       # only if velocities are added

e2data/channels.py
  @dataclass(frozen=True) class ChannelSpec(name, sources:tuple[str,...], kind:Literal['2d','3d_k0','sum'], fldlist:tuple[str,...], transform:Literal['linear','log10','asinh','logfloor'], scale:float=1.0, unit_factor:float=1.0, role:Literal['bgc','physics'], cadence:Literal['monthly','daily'])
      def forward(self, x)->np.ndarray;  def inverse(self, z)->np.ndarray
  MONTHLY_BGC8, MONTHLY_PHYS9, DAILY_BGC, DAILY_PHYS   (as in section 2; the daily 'pCO2' reads dir apCO2 and asserts its fldList is the seawater field)

e2data/sources.py
  @dataclass class FileRec(var, iter, path, size, status:Literal['ok','truncated_deep','short'])
  def scan(root, specs, iters)->dict[str, dict[int, FileRec]]  # 2d needs ==3,790,800; 3d needs ==189,540,000; >=3,790,800 -> 'truncated_deep' (e.g. POC.0000208152.data = 120,001,674 B: k0 usable, logged); never trusts .meta timeInterval
  def assert_fldlist(root, spec)                               # reads the first .meta, mirrors llc270_loader.discover_tracer_meta (llc270_loader.py:178-207)
  def read_k0(path)->np.ndarray                                # np.fromfile('>f4', count=947700); raise on a short read
  def availability(recs, specs, iters)->np.ndarray[T, C] bool  # a 'sum' channel is available only if all its parts are

e2data/stats.py
  class AreaWelford: update(x2d, w2d); mean; std
  def split_indices(labels, split_def)->dict[str, np.ndarray]
  def channel_stats(arr, idx, avail, w)->(mean[C], std[C])
  def upsampled_input_stats(coarse, idx, fine_grid, w)->(mean, std)
  def monthly_climatology(arr, labels, idx)->(12, C, H, W)
  def harmonic_climatology(arr, doy, idx, n_harm=3)->(7, C, H, W)
  def seasonal_ar1_phi(arr, clim, pair_idx)->(C, H, W)
  def write_e2s_stats_json(path, input_names, in_mean, in_std, output_names, out_mean, out_std, inv_names, inv_mean, inv_std)

e2data/build.py (CLI)
  python -m darwindiff.e2data.build monthly --raw D:\ecco_darwin_v5\output\monthly --grid D:\ecco_darwin_v5\grid --out D:\e2data\v05_monthly --fine q025 --coarse c1,c2 --splits std12,rev12 [--positive-transform asinh|logfloor] [--crop R0,C0,H,W] [--limit 24] [--workers N]
  python -m darwindiff.e2data.build daily   --raw <daily_root> --grid <grid> --out <out> --fine q025 --coarse c1,c2 --splits std12 [--with pH_k0,surfDIC_tend]
  python -m darwindiff.e2data.build verify  --out <out>
  Flow:
  1. calendar.self_check
  2. load_native_geometry
  3. build_remap for fine and coarse
  4. scan + assert_fldlist + availability
  5. per timestep (workers own disjoint time chunks): read_k0 each source -> sum parts -> unit_factor -> RemapOp.apply (fine, coarse) -> forward transform (NaN stays NaN) -> write chunk; coarse also fill_land_nearest + add_halo
  6. per split: stats, climatology, AR(1) phi, e2s stats.json, npy stats
  7. manifest
  verify:
  - remap of ones == 1 on valid
  - area-weighted global mean native vs fine within 1e-3 relative
  - blockavg(fine) vs coarse residual reported
  - 401,005 land cells exactly 0 in one sampled file per var
  - inverse(forward(x)) == x to 1e-6
  - every stamp maps to a boundary
  - no NaN in coarse halo arrays
  - chunk count == T
  - upsample parity vs earth2studio (track2 env only)

track2 side (outline only): regional_weather_diffusion/datasets/ecco_darwin.py
  - class EccoDarwinDownscale(StormCastDataset) and class EccoDarwinStep(StormCastDataset).
  - params: location, fine, coarse, split, bgc_channels, physics_channels, time_features, invariants, dt, crop.
  - __getitem__ z-scores with the split stats, sets NaN->0 AFTER z, upsamples coarse via e2data.grids.upsample_bilinear, and returns mask (C,H,W) float32 = ocean & avail.
  - image_shape (640,1440) or crop. For a 5090 smoke test use crop 256x512, e.g. lat 20-84N, lon 80W-48E.
  - Serving: class DarwinCorrDiff(earth2studio CorrDiff) overrides _interpolate to upsample only the coarse channels with the same function.

Nulls to be graded against (inputs stored by the builder, all fitted on train only):
- persistence (StormCast)
- per-cell climatology
- per-cell seasonal AR(1)
- the upsampled coarse input itself (CorrDiff)
- upsampled coarse + climatological fine-scale residual, clim_fine - up(blockavg(clim_fine)): the strong null for super-resolving a box average
Spectral metrics stop at the native scale: about 30% of q025 ocean pixels are nearest-native copies, so power above that wavenumber is artifact.

=====================================================================
7. RUNTIME AND MEMORY (local; Core Ultra 9 275HX, 24 threads, 63.5 GB RAM)
=====================================================================
- Measured: level-0 read 51-95 ms per 3.79 MB file from D: (USB HDD); remap build 0.2 s; apply 2.9 ms (q025), about 1 ms (c1); KD-tree 0.2 s.
- Monthly: 323 x about 20 source reads = about 6,460 reads (24.5 GB read) -> about 9 min I/O + about 1-2 min compute + writing about 8-20 GB to D: (2-4 min) + stats pass (about 3 min) = about 15-20 min single process. Peak RSS < 3 GB (float64 climatology accumulators 12x17x921,600 = 1.5 GB dominate).
- Daily: 118,332 reads (449 GB). On the local HDD about 2-3 h read + about 30-40 min write (build + raw about 750-800 GB of D:'s 1,007 GB free). On AICR Lustre with 8-16 CPU workers about 1 h (inferred). Peak RSS < 4 GB per worker (streaming Welford + harmonic normal equations).
- No GPU needed. Multi-process CPU is fine on Windows; only multi-process CUDA is not.

Repo citations for the reused conventions:
- llc270_loader.py:54-91 (TRAC_MAPPING, _2D_VARS), :139-169 (delta_t 1200), :378-425, :428-499, :502-568, :571-582
- ecco_darwin_loader.py:200-241 (bin_average open), :322-342
- build_daily_surface_cube.py:55-90, :109-143, :196, :229, :247-253
- emulator_poc.py:143-145, :197-207, :263-291, :317-358, :371-434, :437-521 (times_days at :509), :527-599, :607-683
- diffusion_emulator.py:44-54 (load_cube), :57-65 and :535-538 (stats computed over ALL months before the split = leakage), :541-566 (48% of old-cube pairs not one month), :495-496
- rollout_verify.py:60-66 (month label one month late)
