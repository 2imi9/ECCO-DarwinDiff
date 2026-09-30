# Paired physics 1: what the v05 run itself wrote, and a re-run with daily physics

> **Agent-drafted, banked verbatim from the 2026-09-30 paired-physics workflow** (three sweeps and a critic, read-only, no credentials). Status labels per product. Where this conflicts with `paired_physics_critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md` §5.

## Summary

I found no published daily physics for the LLC270 iteration-42 solution. The v05 run itself published five daily physical fields, all at the surface. It published richer physics only as monthly means. Every daily ECCO physics product I found comes from a different solution. So the only daily physics that exactly matches the v05 biogeochemistry is what a v05 re-run with extra diagnostics would write.

(1) THE RUN CONFIGURATION (verified). I read MITgcm-contrib/ecco_darwin at master commit e39a22a27c70c5e2099524d825fadbbf32866f06 (2026-09-28). Files read: v05/llc270/input/data.diagnostics, input2/data.diagnostics, input_1985/data.diagnostics, metadata/data.diagnostics, input_v5r1/data.diagnostics, readme.txt, readme2.txt, readme_v5r1.txt, useful/diags_organize.txt, results/STDOUT.0000, code_darwin/DIAGNOSTICS_SIZE.h and metadata/available_diagnostics.log. Local copies are in C:\Users\Frank\AppData\Local\Temp\claude\C--Users-Frank-OneDrive-Desktop-Github-ecco-darwindiff\b9d5a7a9-6b05-4538-98d0-9e15bcf9debc\scratchpad\v05\.
The physics is not read from a file. Carroll et al. 2022 (GBC, doi 10.1029/2021GB007162, via PMC9286438) says the LLC270 circulation 'is used at each time step (1200 s)' to drive Darwin online. So any physical diagnostic the v05 run writes is exactly paired with its biogeochemistry.
- DAILY (86400 s means): physical fields are EXFwspee (wspeed), SIarea, SIheff, THETA at level 1 (SST), SALTanom at level 1 (SSSanom) and MXLDEPTH (mldDepth). MXLDEPTH has been in every version since 2020-07, and the 2022 STDOUT.0000 shows 'Creating Output Stream: diags/daily/mldDepth'. Daily BGC fields are fluxCO2, gDICsurf, gO2surf, apCO2, surfChl1-5 at level 1, and pH and pCO2 with no level restriction, so they are 3-D.
- 3-HOURLY: fluxCO2 only.
- MONTHLY (2635200 s means): 3-D fields are THETA, SALTanom, UE_VEL_C, VN_VEL_C, WVEL and PAR. 2-D fields are SST, SSSanom, MXLDEPTH, oceQsw, oceQnet, EXFwspee, SIarea and SIheff.
- MONTHLY budget streams (diags/budget): ETAN, TFLUX, SFLUX, oceQsw, oceFWflx, oceSPflx, UVELMASS, VVELMASS, WVELMASS, and full THETA and SALT with their advective and diffusive fluxes. Also monthly snapshots of ETAN, THETA and SALT.
- Never written at any cadence: UVEL, VVEL, oceTAUX/Y, EXF atmospheric state, PHIBOT, SIhsnow and ice velocities. KPPhbl does not exist because v05 uses GGL90, not KPP. GGL90Kr is available but not written.
The portal archive does not match any GitHub version exactly. It has surfPCO2, a daily apCO2 whose field is surfpCO2, and no mldDepth. So statements about the published run based on GitHub alone are inferred.

(2) WHAT WAS ACTUALLY PUBLISHED (verified from local listing snapshots, read-only). D:\ecco_darwin_v5\filelists and output\daily\*\index.html.tmp were captured 2026-06-20. The daily directory has 17 subdirectories. The only physical ones are SST, SSSanom, wspeed, SIarea and SIheff, running 1992-01-02 to 2018-12-31. A 2-D file is 3,790,800 B. Daily pCO2, pH and surfPCO2 are 50-level files of 189,540,000 B. That contradicts the map's settled answer that daily v5 is 'surface-2D only'.
The local monthly mirror is complete for 2-D physics (320-323 of 324 months). The 3-D fields are partial: THETA 282, SALTanom 287, uVel_C 293, vVel_C 280, wVel 284 and PAR 292 of 324.
I could not confirm whether the budget streams or daily mldDepth are on the portal. data.nas.nasa.gov timed out today, and the Wayback CDX service was offline.

(3) OTHER PHYSICS PRODUCTS.
- ECCO LLC270 'V5 Alpha' on ECCO Drive (Version5/Alpha) is iteration 45 (Zhang, Menemenlis and Fenty 2018 report, hdl 1721.1/119821) or iteration 50 (Nakayama et al. 2024, GMD 17:8613). It is not iteration 42. Its only documented output is nctiles_monthly. The Zenodo mirror (10.5281/zenodo.10934678 and 10.5281/zenodo.10935131) is verified monthly: each annual SIarea file holds 12 records, 1992-2017. I found no reference to a daily directory.
- ECCO Drive answers 401 without login today. A NumericalEarth.jl README note (added 2026-08-20) says files/ECCO2/ now answers 403 even to valid accounts. That would block era_xx_it42_v2, the ECCO-Darwin_extension (monthly to 2025-05) and ECCO2 cube92 daily. Version5 still works in that report. This is secondary evidence.
- CMR has 0 LLC270 or ECCO-Darwin collections. The only daily ECCO physics in CMR is V4r4 on the LLC90 grid (1992-2017) and the regional SASSIE llc1080 product. Both are different physics.
- The iter42 physics-only forward run (v04 readme_physics) and the v5r1 (iteration 70) configuration both write monthly only. I found no public output from either.
- Neither Carroll 2020 JAMES nor Carroll 2022 GBC points to any separate physics product. Both data statements point to data.nas.nasa.gov/ecco.
- The 'nbp19_dmenemen_public_llc270' tree, which the repo calls not public, is almost certainly public. Commit ec32be1107 (2025-06-05) swapped three links into it. They were /nobackupp19/dmenemen/public/llc_270/{iter42/input, ecco_darwin_v5/input/darwin_initial_conditions, darwin_forcing}, which are the trees the readme says are on data.nas.nasa.gov. So the only input that is truly gated is the atmospheric forcing.

(4) RE-RUNNING v05 FOR DAILY PHYSICS. Use the readme.txt §3 route: era_xx from ECCO Drive Version5/Alpha/era_xx (needs Earthdata login), plus the xx*42 controls through pkg/ctrl, plus the NAS iter42/input and ecco_darwin_v5/input trees. Avoid §3.1 and readme2, which need era_xx_it42_v2 under the ECCO2 directory.
Add daily streams (frequency=86400.):
- 2-D: ETAN, MXLDEPTH, oceQsw, oceQnet, oceFWflx, oceTAUX, oceTAUY, TFLUX, SFLUX, SIhsnow, PHIBOT.
- 2-D atmospheric: EXFatemp, EXFaqh, EXFswdn, EXFlwdn, EXFpreci, EXFuwind, EXFvwind.
- 3-D, optionally cut with levels(1:20,n) (level 10 is about 100 m, level 20 about 323 m): THETA, SALTanom, UE_VEL_C, VN_VEL_C, WVEL, GGL90Kr, PAR.
Every name above appears in the v05 available_diagnostics.log.
Two hard constraints. First, DIAGNOSTICS_SIZE.h sets numlists=90 and the file already uses all 90 streams. So either raise numlists and rebuild, or drop streams such as the 3-hourly CO2 stream or budget streams 73-90. Second, storage has room: 8,788 of numDiags=15,025 levels are allocated.
Volume per variable over 1992-2018 (~9,861 days): about 37 GB for each 2-D field and about 1.87 TB for each full-depth 3-D field (0.75 TB for the top 20 levels).
MITgcm results change with the rank decomposition and the compiler. So write the biogeochemistry daily from the same re-run, and pair against that, not against the published archive.

## Products

### ECCO-Darwin v05 published DAILY archive (NAS ECCO Data Portal ecco_darwin_v5/output/daily)

- **producer:** Carroll, Menemenlis et al. (JPL); config MITgcm-contrib/ecco_darwin v05/llc270 (commit e39a22a27c70c5e2099524d825fadbbf32866f06)
- **physics_source:** The v05 run's own online MITgcm physics: ECCO LLC270 iteration-42 initial pickup, GM/Redi/diffkr fields and xx_*42 atmospheric-control adjustments on era_xx forcing, dt=1200 s. Carroll 2022 GBC: LLC270 circulation used at each 1200 s step to drive Darwin. This is the SAME physics that drove v05.
- **grid_resolution:** native LLC270 (13 tiles of 270x270 = 947,700 columns, ~1/3 deg); physical fields 2-D surface only
- **period:** 1992-01-02 to 2018-12-31 (iterations 72 to 709992, ~9,861 daily means)
- **cadence:** daily mean (frequency 86400 s)
- **physical_variables:** SST (THETA level 1), SSSanom (SALTanom level 1), wspeed (EXFwspee), SIarea, SIheff. Nothing else physical: no ETAN, no heat/freshwater flux, no velocities, no 3-D T/S; daily mldDepth is configured but absent from the portal listing (separate row)
- **bgc_variables:** CO2_flux, O2_flux (gO2surf), surfDIC_tend, pH and pCO2 (both 3-D, 50 levels), surfPCO2 (50-level byte duplicate of pCO2 per repo note), apCO2 (fldList surfpCO2 per repo note), surfChl1-5 (TRAC27-31 level 1)
- **access:** https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/daily/ ; no auth; NOT reachable 2026-09-30 (curl timeout at 15 s). Listing snapshots at D:\ecco_darwin_v5\filelists\*.txt and D:\ecco_darwin_v5\output\daily\*\index.html.tmp (2026-06-20). Surviving derived cubes on AICR /work/neu/p2026_0089_neu/cubes (SST, wspeed + surfChl1/2/3/5 at 1 and 0.5 deg); raw /scratch tree purged
- **size:** 2-D file 3,790,800 B (3.62 MiB), about 37 GB per 2-D variable over the era; 3-D pCO2/pH file 189,540,000 B (180.76 MiB); whole 17-directory daily tree 2.9 TB on AICR (repo note)
- **pairing:** exact
- **status:** verified_primary

### ECCO-Darwin v05 published MONTHLY archive (ecco_darwin_v5/output/monthly)

- **producer:** Carroll, Menemenlis et al. (JPL)
- **physics_source:** same online v05 physics as above (exact)
- **grid_resolution:** native LLC270, 50 levels (10 m at surface to 457 m at depth)
- **period:** 1992-01 to 2018-12 (324 months on portal; local mirror partial)
- **cadence:** monthly mean (frequency 2635200 s)
- **physical_variables:** 3-D: THETA, SALTanom, uVel_C (UE_VEL_C), vVel_C (VN_VEL_C), wVel (WVEL), PAR (Darwin light). 2-D: SST, SSSanom, mldDepth (MXLDEPTH), oceanQsw, oceanQnet, wspeed, SIarea, SIheff. Local counts: THETA 282, SALTanom 287, uVel_C 293, vVel_C 280, wVel 284, PAR 292, 2-D 320-323 of 324
- **bgc_variables:** 31 Darwin tracers (DIC, NO3, NO2, NH4, PO4, FeT, SiO2, DOC/DON/DOP/DOFe, POC/PON/POP/POFe/POSi, PIC, ALK, O2, c1-c7, Chl1-5), primProd, CO2_flux, O2_flux, fugCO2, pCO2, surfPCO2, apCO2
- **access:** local D:\ecco_darwin_v5\output\monthly (read-only check) and Explorer /projects/schultz/qi.zim/ecco_darwin_v5/output/monthly; portal https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/ unreachable today
- **size:** 3-D file 189,540,000 B; 2-D file 3,790,800 B; local THETA 51G, SALTanom 52G, uVel_C 53G, vVel_C 50G, wVel 51G, PAR 52G, each 2-D field 1.6G
- **pairing:** exact
- **status:** verified_primary

### ECCO-Darwin v05 DAILY mldDepth (MXLDEPTH) stream

- **producer:** v05 run (Carroll/Menemenlis)
- **physics_source:** same online v05 physics (exact)
- **grid_resolution:** native LLC270, 2-D
- **period:** presumably 1992-2018 like the other daily streams (not confirmed)
- **cadence:** daily mean
- **physical_variables:** MXLDEPTH
- **bgc_variables:** none
- **access:** Written, not published. It is in every v05/llc270 input/data.diagnostics version since 2020-07 (stream 18). v05/llc270/results/STDOUT.0000 (commit a9d6f88eea, 2022) shows 'Creating Output Stream: diags/daily/mldDepth'. useful/diags_organize.txt moves it to daily/mldDepth. But it is missing from the 17-directory portal daily listing (repo notes 2026-06-06 and 2026-07-30). Would have to be requested from the authors or regenerated.
- **size:** ~37 GB for 1992-2018 if it exists (3,790,800 B/day, arithmetic)
- **pairing:** exact
- **status:** inferred

### ECCO-Darwin v05 monthly budget + snapshot diagnostics (diags/budget streams 73-90)

- **producer:** v05 run (Carroll et al. 2022 DIC budget)
- **physics_source:** same online v05 physics (exact)
- **grid_resolution:** native LLC270, 2-D and 50-level 3-D
- **period:** 1992 onward (Carroll 2022 budget analysed 1995-01 to 2018-12)
- **cadence:** monthly mean, plus monthly snapshots (frequency -2635200)
- **physical_variables:** ETAN (SSH) mean and snapshot; TFLUX, SFLUX, oceQsw, oceFWflx, oceSPflx; UVELMASS, VVELMASS, WVELMASS; full THETA and SALT with ADVx/y/r and DFxE/yE/rE/rI fluxes, oceSPtnd; THETA/SALT snapshots
- **bgc_variables:** DIC, ALK, NO3, NO2, NH4, PO4, SiO2, O2, FeT budget terms; fluxCO2, gDICsurf, apCO2, apCO2sat
- **access:** Configured in v05/llc270/input/data.diagnostics. Carroll 2022 data statement: 'ECCO-Darwin model output and DIC budget diagnostics are available at the ECCO Data Portal: http://data.nas.nasa.gov/ecco/'. No budget directory appears in the repo's recorded portal listings, and the portal is unreachable today, so the path is unverified. A planned native-dataset regrouping (v05/llc270/metadata/groupings_for_native_datasets.json, Carroll 2026-03) is all AVG_MON/SNAP and not in CMR.
- **size:** unknown
- **pairing:** exact
- **status:** inferred

### v05 ECCO-Darwin 1x1 deg bin-average (v05_ECCO-Darwin_bin_average_1x1_deg.nc)

- **producer:** Carroll/Menemenlis (v05 useful/bin_average/compute_bin_average_v05_ECCO_Darwin.m)
- **physics_source:** v05 run output, bin-averaged (exact physics, degraded grid)
- **grid_resolution:** 1 deg lat-lon, 180x360, surface only
- **period:** 1995-01 to 2017-12 (276 months)
- **cadence:** monthly
- **physical_variables:** SST, SSS, mldDepth, seaIceArea, windSpeed
- **bgc_variables:** CO2_flux, pCO2, apCO2, Chl1-5
- **access:** https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/ (unreachable today); local D:\ecco_darwin_v5\bin_average\ (variables read with netCDF4)
- **size:** 1,866,050,011 B
- **pairing:** exact
- **status:** verified_primary

### ECCO LLC270 'Version 5 Alpha' state estimate (ECCO Drive Version5/Alpha; Zenodo mirror of iteration 50)

- **producer:** Zhang, Menemenlis, Fenty (JPL/ECCO); Zenodo upload by Nakayama 2024
- **physics_source:** Physics-only ECCO LLC270 state estimate at iteration 45 (Zhang et al. 2018 report) / iteration 50 (Nakayama et al. 2024 GMD 17:8613: 'similar to iteration 42 used in ECCO-Darwin'). NOT the iteration-42 physics that drove v05.
- **grid_resolution:** LLC270 nctiles, 50 levels
- **period:** 1992-2017
- **cadence:** monthly (nctiles_monthly). Zenodo SIarea_YYYY.nc verified at 45,507,104 B uncompressed = 12 x 947,700 x 4 B + header, i.e. 12 monthly records per year. No daily directory referenced anywhere I found.
- **physical_variables:** Zenodo: THETA, SALT, UVELMASS, VVELMASS, SIarea, SIheff, nctiles_grid. ECCO Drive tree reportedly also holds other nctiles_monthly fields such as PHIBOT (model-harmonics code), not verified
- **bgc_variables:** none
- **access:** https://ecco.jpl.nasa.gov/drive/files/Version5/Alpha (Earthdata login; HTTP 401 unauthenticated 2026-09-30). Zenodo no auth: https://doi.org/10.5281/zenodo.10934678 and https://doi.org/10.5281/zenodo.10935131 (range request returned 206)
- **size:** Zenodo: THETA.zip 23,328,672,162 B; UVELMASS.zip 24,950,257,942 B; SIarea.zip 148,451,077 B; SIheff.zip 165,033,049 B; nctiles_grid.zip 185,577,907 B; SALT.zip 17,825,134,352 B; VVELMASS.zip 25,067,942,343 B
- **pairing:** same_family
- **status:** verified_primary

### ECCO LLC270 iteration-42 physics-only forward re-run (v04/llc270_JAMES_paper readme_physics)

- **producer:** Menemenlis/Carroll (recipe only)
- **physics_source:** iteration-42 controls and forcing like v05, but older MITgcm code (CVS 2017-11-28 vs darwin3 24885b71), so not bitwise identical
- **grid_resolution:** LLC270
- **period:** 1992-2017 per recipe
- **cadence:** monthly only (all 17 ECCO-standard streams at 2635200 s)
- **physical_variables:** state_2d_set1 (ETAN, SIarea, SIheff, SIhsnow, MXLDEPTH, oceQnet, oceFWflx, oceTAUX/Y and more), state_3d_set1 (THETA, SALT, DRHODR), UVELMASS/VVELMASS/WVELMASS, heat/salt flux sets
- **bgc_variables:** none
- **access:** Recipe at github.com/MITgcm-contrib/ecco_darwin/blob/e39a22a27c70c5e2099524d825fadbbf32866f06/v04/llc270_JAMES_paper/readme/readme_physics.txt; the equivalent llc_hires/llc_270 input/data.diagnostics is also monthly only. No published output found.
- **size:** n/a
- **pairing:** same_family
- **status:** not_found

### ECCO-Darwin_extension (ECCO Drive ECCO2/LLC270/ECCO-Darwin_extension/monthly)

- **producer:** ECCO/JPL; known only from NumericalEarth.jl ECCO_darwin.jl
- **physics_source:** LLC270 ECCO-Darwin run extended to 2025, dt 1200 s, epoch 1992-01-01. Whether it is the iteration-42 v05 physics or a newer solution is unknown.
- **grid_resolution:** LLC270 native binaries (270x3510x50)
- **period:** 1992-01 to 2025-05 (per NumericalEarth all_dates)
- **cadence:** monthly
- **physical_variables:** THETA, SALTanom
- **bgc_variables:** DIC, ALK, PO4, NO3, DOP, POP, FeT, SiO2, O2
- **access:** ECCO Drive ECCO2/ directory. NumericalEarth README (commit 29add00ac6, 2026-08-20): drive lists only NearRealTime, Version4, Version5, and every files/ECCO2/ path answers 403 to valid accounts. Unauthenticated probe returns 401.
- **size:** unknown
- **pairing:** unknown
- **status:** secondary_only

### ECCO v5r1 (LLC270 iteration 70) physics and ECCO-Darwin v5r1 configuration

- **producer:** H. Zhang (JPL); readme_v5r1.txt commit 0d92bbd4aa 'from v5r1 (iter70) solution', 2026-05-25
- **physics_source:** newer LLC270 state estimate (iteration 70, 1992-2025, darwin_ckpt68g, shelfice) — different physics from the iteration-42 physics behind v05
- **grid_resolution:** LLC270
- **period:** 1992-2025 per readme
- **cadence:** physics data.diagnostics (input_v5r1) is monthly only; the Darwin variant copies input2/data.diagnostics (daily surface + monthly)
- **physical_variables:** monthly ECCO-standard sets plus exf_zflux sets (EXFswdn, EXFlwdn, EXFatemp, EXFaqh, EXFpreci, EXFtaux/y, EXFhs, EXFhl, EXFqnet)
- **bgc_variables:** as v05 when run with Darwin
- **access:** Inputs at /nobackup/hzhang1/pub/llc270_FWD/v5r1 on NASA Pleiades (not public). No public output or CMR entry found.
- **size:** n/a
- **pairing:** same_family
- **status:** not_found

### ECCO V4r4 native-grid daily physics (PO.DAAC)

- **producer:** ECCO Consortium / JPL PO.DAAC
- **physics_source:** ECCO V4 Release 4 state estimate on LLC90 (~1 deg); different optimisation, forcing adjustments and resolution — not the LLC270 iteration-42 physics
- **grid_resolution:** LLC90 native (13 tiles 90x90x50); 0.5 deg interpolated variants also exist
- **period:** 1992-01-01 to 2018-01-01 (CMR)
- **cadence:** daily mean (also monthly)
- **physical_variables:** T/S, velocity, SSH, MLD, heat and freshwater fluxes, stress, sea ice, atmospheric state, density/stratification, 3-D volume/heat/salt fluxes
- **bgc_variables:** none
- **access:** CMR concept ids verified: TEMP_SALINITY C1991543736-POCLOUD; OCEAN_VEL C1991543808-POCLOUD; SSH C1991543744-POCLOUD; MIXED_LAYER_DEPTH C1991543734-POCLOUD; HEAT_FLUX C1991543712-POCLOUD; FRESH_FLUX C1991543820-POCLOUD; STRESS C1991543704-POCLOUD; SEA_ICE_CONC_THICKNESS C1991543763-POCLOUD; ATM_STATE C1991543823-POCLOUD; DENS_STRAT_PRESS C1991543727-POCLOUD. Metadata public; data download needs Earthdata login.
- **size:** not checked
- **pairing:** different_physics
- **status:** verified_primary

### ECCO2 cube92 0.25 deg daily (ECCO Drive ECCO2/cube92_latlon_quart_90S90N/daily)

- **producer:** ECCO2 / JPL
- **physics_source:** ECCO2 cube-sphere solution — different physics
- **grid_resolution:** 0.25 deg lat-lon (1440x720x50)
- **period:** 1992 to 2024-12-31 per NumericalEarth all_dates
- **cadence:** daily
- **physical_variables:** T, S, velocities and others (per NumericalEarth variable map; not verified)
- **bgc_variables:** none
- **access:** ECCO Drive ECCO2/ directory, reportedly 403 to authenticated accounts since at least 2026-08-20 (NumericalEarth README); 401 unauthenticated
- **size:** unknown
- **pairing:** different_physics
- **status:** secondary_only

### SASSIE ECCO llc1080 daily (regional Arctic)

- **producer:** SASSIE / ECCO (PO.DAAC)
- **physics_source:** regional llc1080 sea-ice/ocean model with initial and boundary conditions and forcing from ECCO V5 Alpha (LLC270) — different physics, regional only
- **grid_resolution:** llc1080 regional
- **period:** 2014-01-15 to 2021-02-07 (per user guide, secondary)
- **cadence:** daily mean and snapshots
- **physical_variables:** T/S, velocity, SSH/OBP, KPP boundary-layer depth and mixing, heat/freshwater fluxes, stress, sea ice, 3-D fluxes
- **bgc_variables:** none
- **access:** 22 'SASSIE ECCO ... llc1080 Grid (Version 1 Release 1)' collections found in CMR keyword search; Earthdata login for data
- **size:** not checked
- **pairing:** different_physics
- **status:** verified_primary

### Re-run of ECCO-Darwin v05 with added daily physical diagnostics (Explorer)

- **producer:** DarwinDiff (to be run)
- **physics_source:** Identical configuration to v05 (darwin3 24885b71, iteration-42 pickup/controls, era_xx forcing via pkg/ctrl per readme.txt section 3). Not bitwise equal to the published archive if ranks (767) or compiler differ, so pair against the re-run's own BGC.
- **grid_resolution:** native LLC270; 3-D optionally cut to levels 1-10 (~100 m) or 1-20 (~323 m)
- **period:** 1992-01-01 onward from the 1992 pickup (27 model-years to reach 2018-12-31)
- **cadence:** daily (frequency 86400 s), any fields chosen
- **physical_variables:** Proposed: 2-D ETAN, MXLDEPTH, oceQsw, oceQnet, oceFWflx, oceTAUX, oceTAUY, TFLUX, SFLUX, SIhsnow, PHIBOT, EXFatemp, EXFaqh, EXFswdn, EXFlwdn, EXFpreci, EXFuwind, EXFvwind; 3-D THETA, SALTanom, UE_VEL_C, VN_VEL_C, WVEL, GGL90Kr (no KPPhbl: v05 uses GGL90), PAR. All present in v05 metadata/available_diagnostics.log.
- **bgc_variables:** keep the existing daily Darwin streams; optionally add daily 3-D DIC/ALK/PIC/POC/FeT for full pairing
- **access:** Inputs: NAS iter42/input and ecco_darwin_v5/input (public, no auth; unreachable today; AICR staged copy purged). era_xx at https://ecco.jpl.nasa.gov/drive/files/Version5/Alpha/era_xx (Earthdata login). era_xx_it42_v2 (readme2 and section 3.1) is under ECCO2/, reportedly 403. Build limit: DIAGNOSTICS_SIZE.h numlists=90 and all 90 streams are used, so raise numlists and rebuild, or drop streams (3-hourly CO2, budget 73-90). Storage has room: 8,788 of 15,025 levels allocated in the 2022 STDOUT.
- **size:** arithmetic over 9,861 days: ~37.4 GB per 2-D field; ~1.87 TB per full-depth 3-D field (0.75 TB at 20 levels, 0.37 TB at 10)
- **pairing:** exact
- **status:** inferred

## Unknowns

- Whether data.nas.nasa.gov exposes daily/mldDepth or a budget directory (monthly ETAN, UVELMASS, full SALT, flux terms). The portal timed out on 2026-09-30 and the Wayback CDX API was offline. The repo's recorded listings show 17 daily dirs and no mldDepth.
- Which data.diagnostics commit and forcing route (readme.txt §3 era_xx+pkg/ctrl vs §3.1 or readme2 era_xx_it42_v2) produced the published archive. The portal's daily surfPCO2 dir, and an apCO2 whose fldList is surfpCO2, match no GitHub version examined (checked 797e496aff, 5598739b88, ceb0ffdad4, 6f69ff6e15, 296c8f7251, 4a104d1787 and master).
- Whether an Earthdata account can read ECCO Drive Version5/Alpha/era_xx today, and whether it covers 2018. The claim that files/ECCO2/ now returns 403 to valid accounts comes only from the NumericalEarth.jl README (2026-08-20).
- Whether ECCO Drive Version5/Alpha contains any daily (nctiles_daily) output. I found only nctiles_monthly, nctiles_grid, era_xx, input_* and XX referenced. A web-search summary asserting nctiles_daily there had no traceable source.
- Whether ECCO-Darwin_extension (ECCO2/LLC270, monthly to 2025-05) is the v05 iteration-42 run extended or a v5r1 (iteration 70) based run.
- Whether the NAS iter42/input xx_*.0000000042.data controls cover through 2018. The v04 recipe copied 'to2018' files; the v05 readme links 'to2023' on Pleiades.
- Walltime cost of a 27-model-year LLC270+Darwin re-run on Explorer, and how far a non-767-rank or non-Intel build drifts from the published v05 fields.
- Inferred only, from commit ec32be1107's diff: that nbp19_dmenemen_public_llc270 is the NAS public iter42/input + darwin_initial_conditions + darwin_forcing trees. The research map currently says it is NOT PUBLIC. Worth confirming against a file list when the portal returns, then correcting the map.
- Research-map correction (not made; read-only task): the settled answer 'Daily v5 is surface-2D only' is wrong for pCO2, pH and surfPCO2, which are 50-level files (189,540,000 B each per the portal index snapshots).
