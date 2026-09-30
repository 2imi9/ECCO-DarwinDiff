# Paired physics: critic's verification, ranking and next action

> **Agent-drafted, banked verbatim from the 2026-09-30 paired-physics workflow** (three sweeps and a critic, read-only, no credentials). Status labels per product. Where this conflicts with `paired_physics_critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md` §5.

## Summary

Short answer: MIT does run Darwin on several MITgcm physics solutions. But no public product gives daily physics exactly paired with the v05 biogeochemistry beyond the five surface fields v05 already wrote (SST, SSSanom, wspeed, SIarea, SIheff). The one complete route to exactly paired daily physics is to re-run v05 (MITgcm + Darwin together) with extra daily diagnostics, and to use the BGC from that same re-run as the training target.

WHAT I CHECKED MYSELF (read-only, 2026-09-30, no credentials)
- v05/llc270 input/data.diagnostics on GitHub master:
  - Daily streams 8-12 are EXFwspee, SIarea, SIheff, THETA level 1 and SALTanom level 1.
  - Stream 18 is a daily MXLDEPTH to diags/daily/mldDepth.
  - Monthly 3-D fields: THETA, SALTanom, UE_VEL_C, VN_VEL_C, WVEL, PAR. Monthly 2-D: MXLDEPTH, oceQsw, oceQnet.
  - Stream 73 is the budget stream (ETAN, TFLUX, SFLUX and more).
  - All 90 streams are used, and code_darwin/DIAGNOSTICS_SIZE.h sets numlists=90 and numperlist=90.
- v05/llc270/readme.txt: darwin3 checkout 24885b71; the run covers 1992-2023. Section 3 uses era_xx (the header points to ECCO Drive Version5/Alpha/era_xx) plus xx*42 controls (a to2023 path on Pleiades). Section 3.1 uses era_xx_it42_v2 (header points to ECCO Drive ECCO2/LLC270).
- Darwin options: no radtrans and no light-heating option is set, and data.darwin sets darwin_useQsw=.TRUE. So the coupling looks one-way, physics driving BGC (inferred).
- v05/1deg on GitHub:
  - input_darwin_v4r4/data.traits is byte-identical to the LLC270 file (5,334 B).
  - data.darwin differs only in the iron-dust file.
  - BUT it builds from jahn/darwin3 branch darwin_ckpt68d_at_c66g on V4r4 inputs at /nobackup/hzhang1/pub/Release4. That is different Darwin code from 24885b71.
- CMR (public):
  - ECCO_L4_TEMP_SALINITY_LLC0090GRID_DAILY_V4R4 = C1991543736-POCLOUD, DOI 10.5067/ECL5D-OTS44.
  - MIXED_LAYER_DEPTH LLC90 daily = C1991543734-POCLOUD.
  - TEMP_SALINITY 0.5 deg daily = C1990404821-POCLOUD.
  - Each has 9,497 granules and a temporal range of 1992-01-01 to 2018-01-01.
  - Keyword hits for LLC270, ECCO-Darwin, 'ECCO Darwin' and V4r5 are all 0.
- Zenodo:
  - 10.5281/zenodo.10934678 is an ECCO-LLC270 output set for the Southern Ocean evaluation (THETA.zip 23,328,672,162 B, UVELMASS.zip 24,950,257,942 B). It points to ECCO Drive Version5/Alpha.
  - Nakayama GMD 17:8613 text (read from a local copy): 'iteration 50 of ECCO LLC270, which is similar to iteration 42 used in ECCO-Darwin'.
  - 10.5281/zenodo.18854567 (Heiser & Wagner) holds v5 monthly fields for 1992-2019, daily surface Chl for 2019, and daily full-column T/S for May 2019 (Fram_llc270_TS.mat, 194,620,644 B).
  - 10.5281/zenodo.17317011 is the Savelli riverine-input V4r5 set (.mat files).
- Local listings:
  - D:\ecco_darwin_v5\filelists has 17 daily lists and no mldDepth.
  - The pCO2 index snapshot shows 923 entries of '180.76 M', which is 50 levels x 947,700 x 4 B, so daily pCO2 is 3-D.
  - The last SST record is iteration 709992, which is 2018-12-31.
  - The local daily directories contain ZERO .data files (listings only).
  - The local monthly mirror has THETA 282/324 and mldDepth 323 files. The 1-deg bin_average is 1,866,050,011 B.
- Hosts: ECCO Drive Version5/Alpha answered 401. data.nas.nasa.gov did not respond.

RANKING, USE (a): TRAINING CONDITIONING FOR A DAILY CorrDiff/StormCast MODEL WITH v05 BGC TARGETS
1. v05's own daily surface physics: SST, SSSanom, wspeed, SIarea, SIheff. Exact pairing. But the raw daily files are NOT local; the local tree has listings only. Re-download needs data.nas, which is down today. Derived SST and wspeed cubes are said to survive on AICR /work (sweep claim, not verified).
2. v05's own monthly 3-D and 2-D physics, interpolated in time to daily as a slowly varying channel. Covers THETA, SALTanom, uVel_C, vVel_C, wVel, PAR, mldDepth, oceanQsw, oceanQnet. Exact source, temporally smoothed. Mostly local, with gaps in the 3-D fields.
3. Items to request from JPL (Carroll/Zhang):
   - the configured daily mldDepth (stream 18), which is absent from the portal;
   - the daily 3-D T/S behind Heiser & Wagner's May 2019 file;
   - the monthly budget streams (ETAN, TFLUX, SFLUX).
   All would be exact or near-exact. But 2019 is past the published 2018 end, so that data comes from the extended 1992-2023 run. Whether that run matches the published archive bit for bit is unknown.
4. A v05 re-run with added daily diagnostics (see below). Exact against its own BGC.
5. v05/1deg on V4r4. Its BGC is paired with its own physics, and it uses the same BGC namelists as v05, but it is a different run: different grid, physics and Darwin code checkpoint. Its BGC output is not public. It could serve as augmentation or a second domain with a model-identity token, never as the v05 target.
6. Do NOT use for training:
   - ECCO V4r4 daily (PO.DAAC);
   - the LLC270 iter50 Zenodo set (monthly, and redundant with v05 monthly);
   - ECCO2 cube92;
   - CBIOMES, Darwin cs510, Manizza, IGSM (these also have a different BGC).

Why mismatched physics silently teaches the wrong mapping: the network learns p(BGC | physics). V4r4 is a different solution at about 1 deg with prescribed wind stress, its own controls and a 3600 s time step. Its fronts, upwelling, ice edge and MLD differ from those that actually drove each v05 chlorophyll or pCO2 value. The network then fits BGC variance to physics that did not cause it. This is errors-in-variables: the physics-to-BGC sensitivities are pulled toward zero, and wherever the mismatch is systematic the network absorbs it as a spurious correlation. Validation on the same mismatched pairs still looks fine, so nothing flags it. For v05 the damage lands where it matters most: Zhang & Menemenlis's 2024 slides (secondary) show that swapping the physics under the same Darwin configuration changes Southern Ocean CO2 flux.

RANKING, USE (b): INFERENCE-TIME BACKGROUND FOR SCENARIO RUNS
1. ECCO V4r4 daily at 0.5 deg or native LLC90, 1992-2017. The collections are listed publicly in CMR; downloads need an Earthdata login, and the user must supply that account. It is the natural coarse, different-model background.
2. ECCO V4r5. Not in CMR; ECCO Drive or in-cloud only; the public Zenodo 10.5281/zenodo.10930853 subset is monthly.
3. ECCO2 cube92 daily at 0.25 deg (secondary; the ECCO2 tree is reportedly 403).
4. LLC270 iter50 monthly (Zenodo).
5. Free-running MITgcm/IGSM physics for true future scenarios.

Caveat: StormCast's background is large-scale context for a prognostic state. Here the physics is the DRIVER of the BGC, so a background shift matters more. Two ways to handle it:
- train the background channel on coarsened exact v05 physics, then swap V4r4 in at inference;
- or measure the V4r4-vs-v05 shift on the five overlapping daily fields and the monthly 3-D fields before trusting scenario output.

SINGLE BEST PATH TO DAILY PHYSICS EXACTLY PAIRED WITH v05 BGC
Yes, it requires re-running v05. Specifically:
- Run the FULL ECCO-Darwin v05 (darwin3 24885b71, readme section 3 route) with extra daily streams, and take BOTH physics and BGC from that one run.
  - 2-D: ETAN, MXLDEPTH, oceQsw, oceQnet, oceFWflx, oceTAUX/Y, SIhsnow, EXF atmospheric state.
  - 3-D, top 20 levels: THETA, SALTanom, UE/VN_VEL_C, WVEL, GGL90Kr, PAR.
  - Plus daily 3-D DIC, ALK, PIC, POC and FeT if wanted.
- A physics-only run is cheaper, but it is not safe to pair against the PUBLISHED BGC. LLC270 is eddy-permitting, so any rebuild, rank-count or compiler difference grows into mesoscale divergence over 27 years.
- numlists=90 is not a real obstacle. The re-run needs a build anyway, so raise numlists. Or pack several fields into one stream (numperlist=90).
- Inputs:
  - NAS iter42/input and ecco_darwin_v5/input (public, down today).
  - ECCO Drive Version5/Alpha/era_xx (Earthdata; the user's own account).
  - xx*42 controls to 2018 or later, and the NOAA MBL apCO2 file. These are Pleiades /nobackup paths in the readme, and their public copies are unverified.
- Cost is large: about 27 model-years at LLC270 with 31 tracers. Storage is about 37 GB per 2-D daily field and about 0.75 TB per 20-level 3-D field (arithmetic).

CONCRETE NEXT ACTION
Lucas sends one email to Carroll and H. Zhang at JPL (I have not sent anything). It asks:
- (i) for the daily mldDepth stream;
- (ii) whether daily 3-D physics exists for the v05 or extended run (the Heiser & Wagner May 2019 file shows some does);
- (iii) whether they could re-run v05 on Pleiades, where all inputs already live, with a supplied data.diagnostics diff;
- (iv) for the public locations of xx*42 to2018/to2023 and apCO2.

Meanwhile, start the CorrDiff/StormCast work on exact pairs only: the v05 daily surface fields plus v05 monthly 3-D physics interpolated to daily. Separately, have the user pull V4r4 daily SST, SSS, SIarea, SIheff and wspeed to measure the inference-time domain shift.

## Products

### ECCO-Darwin v05 published DAILY archive (data.nas ecco_darwin_v5/output/daily)

- **producer:** Carroll, Menemenlis et al. (JPL); config MITgcm-contrib/ecco_darwin v05/llc270
- **physics_source:** The v05 run's own online MITgcm physics (LLC270 iter42 pickup and controls, era_xx forcing, darwin3 24885b71). This IS the physics that drove v05.
- **grid_resolution:** native LLC270, 13x270x270. Physical fields are level 1 only. Daily pCO2, pH and surfPCO2 are 50-level.
- **period:** 1992-01-02 to 2018-12-31. The last SST iteration is 709992 = 9,861 days. The listing holds about 9,786 SST records, so a few days are missing, and SIarea has markedly fewer (about 6,345).
- **cadence:** daily mean
- **physical_variables:** SST (THETA level 1), SSSanom (SALTanom level 1), wspeed (EXFwspee), SIarea, SIheff. The config also writes daily MXLDEPTH (stream 18), but it is absent from the portal listing.
- **bgc_variables:** CO2_flux, O2_flux, surfDIC_tend, apCO2, surfChl1-5 (2-D); pCO2, pH, surfPCO2 (50-level, 180.76 MiB per file per the pCO2 index snapshot)
- **access:** https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/daily/ ; no auth; NOT reachable 2026-09-30. Local D:\ecco_darwin_v5 holds listings only: 0 .data files in every daily dir (verified).
- **size:** 2-D file 3,790,800 B, about 37.4 GB (decimal) per variable over 9,861 days; 3-D file 189,540,000 B
- **pairing:** exact
- **status:** verified_primary

### ECCO-Darwin v05 published MONTHLY archive (physics subset)

- **producer:** Carroll, Menemenlis et al. (JPL)
- **physics_source:** The same online v05 physics (exact)
- **grid_resolution:** native LLC270, 50 levels
- **period:** 1992-01 to 2018-12 (324 months on the portal)
- **cadence:** monthly mean
- **physical_variables:** 3-D: THETA, SALTanom, uVel_C, vVel_C, wVel, PAR. 2-D: SST, SSSanom, mldDepth, oceanQsw, oceanQnet, wspeed, SIarea, SIheff. Local counts verified: THETA 282/324, mldDepth 323/324.
- **bgc_variables:** 31 Darwin tracers, primProd, CO2/O2 flux, pCO2, fugCO2, apCO2
- **access:** local D:\ecco_darwin_v5\output\monthly (verified present); portal down today
- **size:** 3-D file 189,540,000 B; about 50 GB per local 3-D variable (sweep 1)
- **pairing:** exact
- **status:** verified_primary

### v05 monthly budget/snapshot streams (stream 73+: ETAN, TFLUX, SFLUX, UVELMASS/VVELMASS/WVELMASS, full THETA/SALT fluxes)

- **producer:** v05 run
- **physics_source:** The same online v05 physics (exact)
- **grid_resolution:** LLC270, 2-D and 3-D
- **period:** presumably 1992 onward
- **cadence:** monthly mean plus snapshots
- **physical_variables:** ETAN, TFLUX, SFLUX, oceQsw, oceFWflx, U/V/WVELMASS, THETA, SALT and their advective and diffusive fluxes
- **bgc_variables:** budget terms for DIC, ALK, nutrients, O2, FeT
- **access:** Configured (verified in data.diagnostics; the readme creates diags/budget). Not in the local mirror or the recorded portal listings. Request from JPL.
- **size:** unknown
- **pairing:** exact
- **status:** inferred

### v05 extended-run daily full-column T/S subset (Heiser & Wagner 2026)

- **producer:** Heiser, Wagner (from ECCO-Darwin v5 output)
- **physics_source:** ECCO-Darwin v5 physics. The dates (1992-2019 monthly; May 2019 daily) run past the published 2018 end, so this comes from the extended 1992-2023 run. Whether that run is bitwise identical to the published 1992-2018 archive is unknown.
- **grid_resolution:** LLC270, Fram Strait region subset
- **period:** daily May 2019 (T/S); daily 2019 surface Chl; monthly 1992-2019 surface fields
- **cadence:** daily and monthly
- **physical_variables:** potential temperature and salinity, full column (Fram_llc270_TS.mat); monthly SST, SSS, sea-ice concentration
- **bgc_variables:** daily surface Chl (v05_ECCO-Darwin_daily_chl.nc, 3,048,323,714 B); monthly Chl, PO4, NO3
- **access:** https://doi.org/10.5281/zenodo.18854567 , no auth, record metadata read 2026-09-30. It shows that JPL holds daily 3-D v05 physics for at least part of the extended run.
- **size:** Fram_llc270_TS.mat 194,620,644 B; record about 20 GB in total
- **pairing:** exact
- **status:** verified_primary

### v05 1x1 deg bin-average

- **producer:** Carroll/Menemenlis
- **physics_source:** v05 output, bin-averaged (exact physics, degraded grid)
- **grid_resolution:** 1 deg, surface
- **period:** 1995-01 to 2017-12 (sweep 1)
- **cadence:** monthly
- **physical_variables:** SST, SSS, mldDepth, seaIceArea, windSpeed (sweep 1)
- **bgc_variables:** CO2_flux, pCO2, apCO2, Chl1-5
- **access:** local D:\ecco_darwin_v5\bin_average (verified 1,866,050,011 B)
- **size:** 1,866,050,011 B
- **pairing:** exact
- **status:** verified_primary

### Re-run of ECCO-Darwin v05 (full MITgcm+Darwin) with added daily physics diagnostics

- **producer:** to be run: by JPL on Pleiades (preferred), or Explorer/AICR
- **physics_source:** The identical v05 configuration (darwin3 24885b71, readme section 3 route). It is exact against its OWN BGC, not bitwise equal to the published archive, so the BGC target must come from the same re-run.
- **grid_resolution:** LLC270; 3-D fields optionally limited to levels 1-20
- **period:** 1992 onward (the config runs to 2023)
- **cadence:** daily (any fields)
- **physical_variables:** 2-D: ETAN, MXLDEPTH, oceQsw, oceQnet, oceFWflx, oceTAUX/Y, SIhsnow, EXF atmospheric state. 3-D: THETA, SALTanom, UE/VN_VEL_C, WVEL, GGL90Kr, PAR.
- **bgc_variables:** existing daily Darwin streams, plus daily 3-D DIC/ALK/PIC/POC/FeT if added
- **access:** Inputs:
- NAS iter42/input and ecco_darwin_v5/input (public; down today).
- era_xx at ECCO Drive Version5/Alpha (Earthdata; 401 unauthenticated).
- xx*42 controls and NOAA MBL apCO2: Pleiades /nobackup per the readme; public copies unverified.
numlists=90 with all 90 used (verified): raise it at build, or pack fields (numperlist=90).
- **size:** about 37 GB per 2-D daily field; about 0.75 TB per 3-D field at 20 levels (arithmetic)
- **pairing:** exact
- **status:** inferred

### ECCO V4r4 daily physics (PO.DAAC, native LLC90 and 0.5 deg)

- **producer:** ECCO Consortium / PO.DAAC
- **physics_source:** The ECCO V4r4 solution on LLC90: same MITgcm/4D-Var family, but a different optimisation, grid, wind formulation and time step. NOT the v05 physics.
- **grid_resolution:** LLC90 (~1 deg) native, or 0.5 deg lat-lon; 50 levels
- **period:** 1992-01-01 to 2018-01-01 (CMR temporal; 9,497 granules, verified)
- **cadence:** daily mean (also monthly)
- **physical_variables:** T/S, velocity, SSH, MLD, heat/freshwater flux, stress, sea ice, atmospheric state, density. Verified ids: TEMP_SALINITY LLC90 daily C1991543736-POCLOUD (10.5067/ECL5D-OTS44); MLD LLC90 daily C1991543734-POCLOUD; TEMP_SALINITY 0.5 deg daily C1990404821-POCLOUD (10.5067/ECG5D-OTS44).
- **bgc_variables:** none
- **access:** Metadata via public CMR. Files need an Earthdata login (the user's own account). Best inference-time background; not for training v05 targets.
- **size:** per sweep 2 (UMM-G sums, not re-checked): 0.5 deg daily 2-D 112.9 GB, T/S + velocity 619.6 GB; LLC90 daily 866 GB
- **pairing:** different_physics
- **status:** verified_primary

### ECCO-Darwin v05 1deg (Darwin 3 on ECCO V4r4 / V4r5)

- **producer:** ECCO-Darwin team (JPL); MITgcm-contrib/ecco_darwin v05/1deg
- **physics_source:** The V4r4 reproduction (c66g, /nobackup/hzhang1/pub/Release4) or V4r5, computed online. The BGC namelists match v05: data.traits is byte-identical and data.darwin differs only in the iron file (verified). But the Darwin CODE differs: jahn/darwin3 darwin_ckpt68d_at_c66g vs darwinproject 24885b71. So its BGC fields are a different dataset from the v05 target.
- **grid_resolution:** LLC90, 50 levels
- **period:** 1992-2017 (V4r4 readme)
- **cadence:** 3-hourly, daily and monthly diagnostics
- **physical_variables:** its own diagnostics, plus the PO.DAAC V4r4 fields (near-exact to its own physics, inferred)
- **bgc_variables:** v05 tracer set (31 ptracers)
- **access:** Config public on GitHub. BGC output: no public archive found; request from JPL.
- **size:** unknown
- **pairing:** same_family
- **status:** verified_primary

### ECCO LLC270 physical state estimate, iteration 50 (Zenodo, Nakayama 2024)

- **producer:** JPL ECCO (Zhang, Menemenlis, Fenty); Zenodo deposit by Nakayama
- **physics_source:** LLC270 iteration 50: 'similar to iteration 42 used in ECCO-Darwin' (GMD 17:8613, verified text). Not the v05 physics.
- **grid_resolution:** LLC270 nctiles, 50 levels
- **period:** 1992-2017
- **cadence:** monthly (from file size, sweep 1)
- **physical_variables:** THETA, SALT, UVELMASS, VVELMASS, SIarea, SIheff, grid
- **bgc_variables:** none
- **access:** https://doi.org/10.5281/zenodo.10934678 (verified) and 10.5281/zenodo.10935131; no auth. Fuller set on ECCO Drive Version5/Alpha (401). Redundant with v05 monthly for training.
- **size:** Part 1 files: THETA.zip 23,328,672,162 B; UVELMASS.zip 24,950,257,942 B; SIarea.zip 148,451,077 B; SIheff.zip 165,033,049 B; nctiles_grid.zip 185,577,907 B
- **pairing:** same_family
- **status:** verified_primary

### Savelli et al. ECCO-Darwin on V4r5 with riverine inputs (derived fields)

- **producer:** Savelli et al.
- **physics_source:** ECCO V4r5 (LLC90). The BGC includes riverine inputs, so it differs from v05.
- **grid_resolution:** LLC90
- **period:** 1992-2019 (sweep 3)
- **cadence:** derived .mat fields
- **physical_variables:** SIarea only
- **bgc_variables:** PP, pCO2, CO2flux
- **access:** https://doi.org/10.5281/zenodo.17317011 (verified; no auth)
- **size:** PP 569,118,191 B; CO2flux 379,210,887 B; pCO2 316,912,431 B; code 1,849,120,764 B
- **pairing:** same_family
- **status:** verified_primary

### ECCO-Darwin_extension (ECCO Drive ECCO2/LLC270, monthly to 2025-05)

- **producer:** ECCO/JPL
- **physics_source:** Unknown whether this is iter42 v05 extended or v5r1
- **grid_resolution:** LLC270
- **period:** 1992-2025 (secondary)
- **cadence:** monthly
- **physical_variables:** THETA, SALTanom (secondary)
- **bgc_variables:** DIC, ALK, nutrients, O2 (secondary)
- **access:** ECCO Drive ECCO2/ directory; reported 403 even with an account (NumericalEarth README, secondary)
- **size:** unknown
- **pairing:** unknown
- **status:** secondary_only

### ECCO2 cube92 0.25 deg daily

- **producer:** ECCO2/JPL
- **physics_source:** ECCO2 CS510 solution; different physics
- **grid_resolution:** 0.25 deg, 50 levels
- **period:** 1992 to 2019 or 2024 (sources conflict)
- **cadence:** daily
- **physical_variables:** T, S, U, V, W, SSH, MLD, sea ice, fluxes (archived listing, secondary)
- **bgc_variables:** none
- **access:** data.nas cs_510 (down); ECCO Drive ECCO2 (reportedly 403)
- **size:** unknown
- **pairing:** different_physics
- **status:** secondary_only

## Unknowns

- Contradiction (research map vs data): the settled answer 'Daily v5 is surface-2D only' is wrong. The local pCO2 index snapshot shows 923 files of 180.76 MiB (50 levels x 947,700 x 4 B). pH and surfPCO2 are the same per sweep 1. Map correction pending (read-only task).
- Contradiction (sweep 2 vs disk): sweep 2 says the v05 daily files are 'already local'. D:\ecco_darwin_v5\output\daily holds 0 .data files in every directory, only listings. Re-acquiring daily v05 physics needs data.nas, which is down today, or the AICR derived cubes (unverified).
- Contradiction (sweep 3 vs sweep 1): sweep 3 labels v04 and v06 physics 'exact'. v04 uses older CVS code and v06 uses the c69e checkpoint with era_xx_it42_v2 unified forcing. Neither is bitwise v05, so both are same_family at best, as sweep 1 treats the iter42 physics-only run.
- Contradiction on the re-run forcing route: sweep 3 says era_xx_it42_v2 + nbp19 from ECCO Drive are required. Sweep 1 says the readme section 3 route (Version5/Alpha/era_xx + NAS inputs) avoids the ECCO2 tree. The readme (verified) documents both. Which route produced the published archive is unknown, and it matters for bitwise reproduction.
- Contradiction on v05/1deg: sweep 2 says pairing unknown and secondary_only; sweep 3 says 'the BGC IS the v05 model'. I verified identical data.traits and data.darwin apart from the iron file, but a different Darwin code checkpoint (jahn/darwin3 darwin_ckpt68d_at_c66g vs 24885b71). So it is the same namelists, a different code, and a different output.
- Contradiction on Heiser & Wagner: sweep 3 reads it as evidence of daily 3-D v05 physics. The record covers 1992-2019 and May 2019, past the published 2018 end, so it comes from the extended 1992-2023 run. Whether that run matches the published archive is unknown.
- Minor: daily 2-D volume of 37 GB (sweep 1) vs 34.6 GB (sweep 2) is decimal GB vs GiB (3,790,800 B x 9,861). Daily mldDepth 'since 2020-07' (sweep 1) vs 'since 797e496, 2020-12-15' (sweep 2) is not resolved by me. The LLC270 Zenodo set is iteration 45 or 50 per sweep 1; I verified iteration 50 in the Nakayama text only.
- Sweep 1 calls numlists=90 a hard constraint. It is verified that all 90 streams are used, but any re-run needs a build anyway, and numperlist=90 lets fields be packed. So it is not a blocker.
- Whether the physics is strictly one-way coupled, so that a physics-only LLC270 run reproduces v05 physics exactly under identical code, compiler and 767-rank decomposition. The Darwin options show no radtrans or light heating (inferred one-way). But eddy-permitting chaos makes any build difference grow, so a physics-only run cannot be assumed paired to the PUBLISHED BGC.
- Public availability of the xx*42 controls to 2018/2023 and of the NOAA MBL apCO2 forcing (Pleiades /nobackup paths in the readme); whether an ordinary Earthdata account can read ECCO Drive Version5/Alpha/era_xx; and the wall-clock cost of a 27-year LLC270+Darwin re-run.
- Whether daily mldDepth, daily 3-D physics, or budget streams exist at JPL for the published run. This needs a direct ask to Carroll/Zhang, which Lucas must send.
- The size of the V4r4-vs-v05 physics mismatch on the five overlapping daily fields and the monthly 3-D fields is unmeasured. It needs an Earthdata pull by the user, plus v05 daily files re-acquired.
