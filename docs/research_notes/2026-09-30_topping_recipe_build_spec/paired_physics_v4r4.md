# Paired physics 2: ECCO V4r4 (and V4r5) as a physical-ocean source

> **Agent-drafted, banked verbatim from the 2026-09-30 paired-physics workflow** (three sweeps and a critic, read-only, no credentials). Status labels per product. Where this conflicts with `paired_physics_critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md` §5.

## Summary

Bottom line: ECCO V4r4 is the only public DAILY physical product in the same family as v05. It is the same MITgcm/ECCO 4D-Var machinery, it uses the same 50 vertical levels, and it also started from 6-hourly ERA-Interim. But it is a separately optimised solution, not the physics that drove v05. So it can supply more physical channels, but it is not an exact pair.

The only exactly paired physics is v05's own diagnostics:
- daily: SST, SSSanom, wspeed, SIarea, SIheff;
- monthly: 3-D THETA/SALT/velocities, mldDepth, Qsw, Qnet, PAR.

Research map: `settled v4r4` returned nothing, so this is new work.

**1. What exists (verified, CMR queried 2026-09-30, unauthenticated)**
- CMR lists 90 POCLOUD collections: 80 V4r4 and 10 V4r4b (V4r4b is an errata release for SSH/OBP/GMAP/SBO).
- Every daily collection has 9,497 granules covering 1992-01-01 to 2017-12-31. The daily means run midnight to midnight; the model itself starts 1992-01-01T12:00.
- Every monthly collection has 312 granules.
- Each variable group comes on two grids: 0.5° lat-lon and native LLC90 (13 tiles of 90x90, 50 levels, 22-110 km spacing).
- Variables were read from the UMM-Var records:
  - SSH: SSH, SSHIBC, SSHNOIBC, plus ETAN on native
  - MLD: MXLDEPTH
  - T/S: THETA, SALT (3-D)
  - Velocity: EVEL/NVEL/WVEL (0.5°) or UVEL/VVEL/WVEL (native)
  - Heat flux: oceQnet, oceQsw, EXFqnet, EXFhl, EXFhs, EXFlw/sw, SIatmQnt, TFLUX
  - Freshwater flux: oceFWflx, EXFempmr, EXFevap, EXFpreci, EXFroff, SFLUX, SIatmFW
  - Stress: oceTAUE/N and EXFtaue/n
  - Sea ice: SIarea, SIheff, SIhsnow, sIceLoad
  - Atmosphere: EXFatemp, EXFaqh, EXFewind/nwind, EXFwspee, EXFpress
  - Density: RHOAnoma, DRHODR, PHIHYD
- Exact volumes come from summing UMM-G SizeInBytes of the .nc files. The CMR echo 'granule_size' field is unreliable for these collections: about half the granules report the size of the .sha512 checksum file.

| Set | 2-D physics | 3-D T/S + velocity | Total |
|---|---|---|---|
| Daily, 0.5° | 112.9 GB | 619.6 GB | 732.5 GB |
| Daily, native LLC90 | 409.6 GB | 456.5 GB | 866.1 GB |
| Monthly, 0.5° | 3.6 GB | 20.3 GB | 23.9 GB |
| Monthly, native LLC90 | 13.4 GB | 15.0 GB | 28.4 GB |

**Access**
- Files need an Earthdata login. The protected archive redirects to urs.earthdata.nasa.gov with a 302, OPeNDAP also redirects to login, and ECCO Drive returns 401.
- Tools (PyPI versions checked today): earthaccess 0.19.0, podaac-data-subscriber 1.15.2, ecco-access 0.3.1.
- The V4r4 synopsis says the complete daily set is also on NAS (llc_90/ECCOv4/Release4). NAS was unreachable today.
- podaac.jpl.nasa.gov dataset pages timed out from here.

**Newer releases**
- V4r5 (1992-2019, LLC90, MERRA-2 first guess) is not in CMR: zero hits for V4r5 or V4r6.
- It is on ECCO Drive under Version4/Release5 (Earthdata login). The ecco_access tutorial says v4r5 works only in its in-cloud S3 modes (s3_open, s3_get, s3_get_ifspace). A monthly subset is public on Zenodo (10.5281/zenodo.10930853).

**2. How V4r4 relates to the LLC270 iter42 physics behind v05**
Verified from Carroll et al. 2020 (JAMES, 10.1029/2019MS001888), Carroll et al. 2022 (GBC, PMC9286438), the ecco_darwin v05/llc270 namelists and the ECCO-v4-Configurations Release 4 namelists.

Shared:
- MITgcm with ECCO adjoint (4D-Var) optimisation of initial T/S, 3-D mixing fields (GM, Redi, diapycnal) and 14-day atmospheric adjustments.
- Identical delR: the same 50 levels, 10 m thick at the surface.
- Similar observation types assimilated: altimetry, GRACE, daily SST, SSM/I sea ice, Argo, WOA09.
- Carroll 2020: "ECCO LLC270 is built upon two previous ECCO efforts, ECCO v4 ... and ECCO2."

Different:
- **Grid:** LLC270 is 1/3° (about 18 km at high latitudes) versus about 1° for LLC90. Different bathymetry files (bathy270_filled_noCaspian_r4 vs bathy_eccollc_90x50_min2pts).
- **Time step and code:** deltaT 1200 s versus 3600 s. MITgcm checkpoint66g for V4r4 versus darwin3 24885b71 for v05, with v05 reverting to pre-2018 sea-ice defaults.
- **Wind forcing:** v05 uses bulk formulae on raw ERA-Interim 10-m winds (useAtmWind=.TRUE.). V4r4 prescribes adjusted wind stress (useAtmWind=.FALSE., eccov4r4_ustr/vstr).
- **Other forcing:** v05's other fields are ERA-Interim plus ECCO **v4r1** adjustments (EIG_*_plus_ECCO_v4r1_ctrl), then its own iter42 controls. V4r4 has its own adjusted forcing and adds atmospheric pressure loading after the fact; v05's data.exf has no pressure file.
- **Optimisation:** LLC270 iter42 is "not fully optimized" (42 iterations, 85% cost reduction). The V4r4 synopsis warns that its estimation "does not directly control daily variations" because forcing is adjusted only at biweekly intervals.

**3. Would V4r4 daily fields condition a v05-trained BGC model? Only approximately.**
- Likely to match: the large-scale seasonal cycle and basin-scale interannual (ENSO-scale) anomalies of SST, SSH, sea-ice extent and climatological MLD. Both solutions are fitted to the same kinds of observations.
- Likely to differ: front and western-boundary-current positions, equatorial and coastal upwelling, the sea-ice edge, deep-convection MLD, vertical velocity (strongly grid-dependent) and day-to-day synoptic variability. The different wind formulations and 14-day adjustments drive the synoptic difference.
- Eddies are not really the issue: neither run resolves them, and both parameterise them with GM/Redi. The problem is sharper structure at 1/3°.

**4. Published comparisons**
- No published daily V4r4-vs-LLC270 field comparison was found.
- Zhang & Menemenlis (ECCO annual meeting slides, March 2024): the same Darwin configuration driven by LLC270-alpha, V4r4 and V4r5 gives different Southern Ocean CO2 flux. LLC270-alpha and V4r4 are "more similar"; V4r5 is "much more different". The mechanism they show runs from sea ice to MLD to pCO2 upwelling. So swapping the physical solution measurably changes the BGC.
- Nakayama et al. 2024 (GMD, 10.5194/gmd-17-8613-2024) compares V4r5 with LLC270 **iteration 50**, which it calls "similar to iteration 42" used in ECCO-Darwin, not V4r4. It finds similar Southern Ocean means (ACC about 149 ± 11 Sv across the four reanalyses), excessive warming trends in all of them, and V4r5 best for sea ice.

**5. Recommendations**
- **Condition on v05's own fields wherever they exist.**
- **Measure the mismatch before adopting any V4r4 channel.** Five v05 daily physical fields have direct V4r4 counterparts (SST vs THETA top level, SSSanom vs SALT top level, wspeed vs EXFwspee, SIarea, SIheff), and the v05 daily files are already local. Monthly THETA/velocity/MLD can be compared against a 24-28 GB V4r4 monthly pull.
- **Ask the producers two things:**
  - Where is v05's daily mldDepth? It has been requested in v05's data.diagnostics since commit 797e496 (2020-12-15), but the NAS daily listing measured 2026-06-20 does not include it.
  - Is the V4r4-driven 1-degree ECCO-Darwin run published? The ecco_darwin repo builds it (v05/1deg), and Carroll's 2024 slides say both LLC 90 V4r4/V4r5 and LLC 270 versions are available. It would be an exact physics-BGC pair at 1°.
- An LLC270 physical product closer to v05 is public on Zenodo (10934678 and 10935131): iteration 50, monthly by file size. But v05's own monthly fields already cover it.

## Products

### ECCO V4r4 daily-mean, 0.5-degree lat-lon (10 physical collections)

- **producer:** ECCO Consortium (JPL/MIT/UT Austin/AER), distributed by NASA PO.DAAC
- **physics_source:** ECCO Version 4 Release 4: MITgcm checkpoint66g on LLC90, adjoint-optimised, 6-hourly ERA-Interim first guess with V4r4 adjustments, prescribed wind stress (useAtmWind=.FALSE.), pressure loading added after the fact. Same model/optimisation family as the LLC270 iter42 physics that drove ECCO-Darwin v05, but NOT the same solution: different grid, bathymetry, time step (3600 vs 1200 s), wind formulation, control adjustments and code checkpoint.
- **grid_resolution:** 0.5-degree regular lat-lon, interpolated from native LLC90; 3-D fields on 50 z-levels with delR identical to v05 LLC270 (10 m at the surface)
- **period:** 1992-01-01 to 2017-12-31 (9,497 daily granules per collection)
- **cadence:** daily mean (midnight to midnight; the model starts 1992-01-01T12:00)
- **physical_variables:** The size column is total GB / mean MB per granule, from UMM-G SizeInBytes.

| Collection | Concept ID | Variables | Size |
|---|---|---|---|
| ECCO_L4_SSH_05DEG_DAILY_V4R4 | C1990404813-POCLOUD | SSH, SSHIBC, SSHNOIBC | 9.8 GB / 1.0 MB |
| ECCO_L4_MIXED_LAYER_DEPTH_05DEG_DAILY_V4R4 | C1990404810 | MXLDEPTH | 3.6 GB / 0.4 MB |
| ECCO_L4_TEMP_SALINITY_05DEG_DAILY_V4R4 | C1990404821 | THETA, SALT (3-D) | 195.2 GB / 20.6 MB |
| ECCO_L4_OCEAN_VEL_05DEG_DAILY_V4R4 | C1990404811 | EVEL, NVEL, WVEL (3-D) | 424.4 GB / 44.7 MB |
| ECCO_L4_HEAT_FLUX_05DEG_DAILY_V4R4 | C1990404788 | oceQnet, oceQsw, EXFqnet, EXFhl, EXFhs, EXFlwnet, EXFswnet, EXFswdn, EXFlwdn, SIatmQnt, TFLUX, SIaaflux | 37.1 GB / 3.9 MB |
| ECCO_L4_FRESH_FLUX_05DEG_DAILY_V4R4 | C1990404818 | oceFWflx, EXFempmr, EXFevap, EXFpreci, EXFroff, SFLUX, SIatmFW, SIacSubl, SIrsSubl, SIsnPrcp, SIfwThru | 26.4 GB / 2.8 MB |
| ECCO_L4_STRESS_05DEG_DAILY_V4R4 | C1990404808 | oceTAUE, oceTAUN, EXFtaue, EXFtaun | 14.1 GB / 1.5 MB |
| ECCO_L4_SEA_ICE_CONC_THICKNESS_05DEG_DAILY_V4R4 | C1990404815 | SIarea, SIheff, SIhsnow, sIceLoad | 4.0 GB / 0.4 MB |
| ECCO_L4_ATM_STATE_05DEG_DAILY_V4R4 | C1990404801 | EXFatemp, EXFaqh, EXFewind, EXFnwind, EXFwspee, EXFpress | 17.9 GB / 1.9 MB |
| ECCO_L4_DENS_STRAT_PRESS_05DEG_DAILY_V4R4 | C1990404793 | RHOAnoma, DRHODR, PHIHYD | 322.1 GB / 33.9 MB |

Other notes:
- ECCO_L4_SEA_ICE_VELOCITY_05DEG_DAILY_V4R4 (C1990404817) and ECCO_L4_BOLUS_05DEG_DAILY_V4R4 (C1990404807) also exist.
- There is no separate SST collection: SST is THETA at the top level, the same layer as v05's daily 'SST' diagnostic (THETA level 1).
- Static grid: ECCO_L4_GEOMETRY_05DEG_V4R4 (C2013583732, 1.8 MB).
- **bgc_variables:** none
- **access:** Collection DOIs verified in UMM-C:
- 10.5067/ECG5D-SSH44
- 10.5067/ECG5D-OML44
- 10.5067/ECG5D-OTS44
- 10.5067/ECG5D-OVE44
- 10.5067/ECG5D-HEA44
- 10.5067/ECG5D-FRE44
- 10.5067/ECG5D-STR44
- 10.5067/ECG5D-ICO44
- 10.5067/ECG5D-ATM44
- 10.5067/ECG5D-ODE44

Access routes:
- Files: https://archive.podaac.earthdata.nasa.gov/podaac-ops-cumulus-protected/<ShortName>/... needs an Earthdata login (tested: 302 to urs.earthdata.nasa.gov).
- Same-region AWS: s3://podaac-ops-cumulus-protected/.
- OPeNDAP (opendap.earthdata.nasa.gov): also redirects to login.
- Tools: earthaccess 0.19.0, podaac-data-subscriber 1.15.2, ecco-access 0.3.1.
- Metadata is public: CMR returns 200.

Reachable today with credentials; I have none and did not download any files.
- **size:** All 2-D physics (SSH, MLD, heat, freshwater, stress, sea ice, atmosphere): 112.9 GB. 3-D T/S + velocity: 619.6 GB. Those nine collections together: 732.5 GB. Minimal set (SSH + MLD + T/S + heat + sea ice): 249.7 GB. Density/stratification adds 322.1 GB. Surface-only OPeNDAP subsetting would shrink the 3-D sets but needs a login.
- **pairing:** same_family
- **status:** verified_primary

### ECCO V4r4 daily-mean, native LLC90 grid (10 physical collections plus daily snapshots)

- **producer:** ECCO Consortium, distributed by NASA PO.DAAC
- **physics_source:** The same V4r4 solution as the 0.5-degree product, on the model's native grid. Same family as v05's LLC270 iter42 physics, not the same solution.
- **grid_resolution:** LLC90: 13 tiles of 90x90 (5 faces), 22-110 km spacing, 50 z-levels (6145 m max depth), delR identical to v05 LLC270. Velocities come in model x/y and must be rotated with CS/SN from ECCO_L4_GEOMETRY_LLC0090GRID_V4R4 (C2013557893, 8.2 MB, DOI 10.5067/ECL5A-GRD44).
- **period:** 1992-01-01 to 2017-12-31 (9,497 daily granules)
- **cadence:** daily mean. Separate daily SNAPSHOT collections also exist: T/S (C1991543757, ~83 GB), SSH, sea ice, sea-ice velocity and OBP (9,496 granules each).
- **physical_variables:** Sizes from UMM-G SizeInBytes; concept IDs all end in -POCLOUD.

| Collection | Concept ID | Variables | Size |
|---|---|---|---|
| ECCO_L4_SSH_LLC0090GRID_DAILY_V4R4 | C1991543744 | ETAN, SSH, SSHIBC, SSHNOIBC | 56.3 GB |
| ECCO_L4_MIXED_LAYER_DEPTH_LLC0090GRID_DAILY_V4R4 | C1991543734 | MXLDEPTH | 50.5 GB |
| ECCO_L4_TEMP_SALINITY_LLC0090GRID_DAILY_V4R4 | C1991543736 | THETA, SALT | 164.9 GB / 17.4 MB |
| ECCO_L4_OCEAN_VEL_LLC0090GRID_DAILY_V4R4 | C1991543808 | UVEL, VVEL, WVEL | 291.6 GB / 30.7 MB |
| ECCO_L4_HEAT_FLUX_LLC0090GRID_DAILY_V4R4 | C1991543712 | oceQnet, oceQsw, ... | 71.2 GB |
| ECCO_L4_FRESH_FLUX_LLC0090GRID_DAILY_V4R4 | C1991543820 | oceFWflx, ... | 64.5 GB |
| ECCO_L4_STRESS_LLC0090GRID_DAILY_V4R4 | C1991543704 | EXFtaux, EXFtauy, oceTAUX, oceTAUY | 56.7 GB |
| ECCO_L4_SEA_ICE_CONC_THICKNESS_LLC0090GRID_DAILY_V4R4 | C1991543763 | SIarea, SIheff, ... | 50.9 GB |
| ECCO_L4_ATM_STATE_LLC0090GRID_DAILY_V4R4 | C1991543823 | EXFuwind, EXFvwind, EXFwspee, EXFatemp, EXFaqh, EXFpress | 59.4 GB |
| ECCO_L4_DENS_STRAT_PRESS_LLC0090GRID_DAILY_V4R4 | C1991543727 | RHOAnoma, DRHODR, PHIHYD, PHIHYDcR | 296.7 GB |

Also available: daily 3-D advective/diffusive heat, salt and volume flux collections (about 150-313 GB each), momentum tendency, and bolus.
- **bgc_variables:** none
- **access:** Collection DOIs, all verified:
- 10.5067/ECL5D-SSH44
- 10.5067/ECL5D-OML44
- 10.5067/ECL5D-OTS44
- 10.5067/ECL5D-OVE44
- 10.5067/ECL5D-HEA44
- 10.5067/ECL5D-FRE44
- 10.5067/ECL5D-STR44
- 10.5067/ECL5D-ICO44
- 10.5067/ECL5D-ATM44
- 10.5067/ECL5D-ODE44

Access is the same as the 0.5° product: Earthdata login via PO.DAAC HTTPS, S3 (us-west-2) or OPeNDAP. The V4r4 synopsis says the complete daily set is also on the NAS data portal (data.nas.nasa.gov/ecco/data.php?dir=/eccodata/llc_90/ECCOv4/Release4) and on ECCO Drive Version4/Release4, which is a subset and needs a login. NAS was unreachable today.
- **size:** 2-D physics: 409.6 GB. 3-D T/S + velocity: 456.5 GB. Total: 866.1 GB. The native 2-D files are about 5-7 MB each versus about 0.4-4 MB at 0.5°; inferred cause is that every file carries the grid coordinate variables.
- **pairing:** same_family
- **status:** verified_primary

### ECCO V4r4 monthly-mean (0.5-degree and native LLC90 collections)

- **producer:** ECCO Consortium, distributed by NASA PO.DAAC
- **physics_source:** The same V4r4 solution. Same family as v05's LLC270 iter42 physics, not the same solution.
- **grid_resolution:** 0.5-degree lat-lon and native LLC90; 50 levels
- **period:** 1992-01 to 2017-12 (312 monthly granules per collection)
- **cadence:** monthly mean
- **physical_variables:** Same variable sets as the daily collections. Concept IDs (all -POCLOUD):

| Variable group | 0.5° | Native LLC90 |
|---|---|---|
| SSH | C1990404799 | C1991543813 |
| MLD | C1990404819 | C1991543741 |
| T/S | C1990404795 | C1991543728 |
| Velocity | C1990404823 | C1991543732 |
| Heat flux | C1990404812 | C1991543811 |
| Freshwater flux | C1990404792 | C1991543803 |
| Stress | C1990404796 | C1991543760 |
| Sea ice | C1990404820 | C1991543764 |
| Atmosphere | C1990404814 | C1991543805 |
| Density | C1990404798 | C1991543735 |
- **bgc_variables:** none
- **access:** Earthdata login (PO.DAAC HTTPS, S3 or OPeNDAP). Metadata is public via CMR.
- **size:** 0.5°: 2-D 3.6 GB + 3-D T/S/velocity 20.3 GB = 23.9 GB. Native: 13.4 + 15.0 = 28.4 GB. This is the cheap set for measuring V4r4-vs-v05 mismatch against v05's local monthly THETA, SALTanom, UE/VN_VEL_C, WVEL and mldDepth.
- **pairing:** same_family
- **status:** verified_primary

### ECCO V4r4b errata collections (SSH, OBP, GMAP, SBO)

- **producer:** ECCO Consortium / PO.DAAC
- **physics_source:** V4r4b, described in UMM-C as "an errata for ECCO Version 4, Release 4 (V4r4)". Same solution family as V4r4.
- **grid_resolution:** 0.5-degree and LLC90
- **period:** 1992-2017
- **cadence:** daily and monthly (SSH/OBP); snapshot time series (GMAP/SBO)
- **physical_variables:** SSH_05DEG_DAILY_V4R4B (C2129181904, DOI 10.5067/ECG5D-SSH4B), SSH_05DEG_MONTHLY (C2129189405), SSH_LLC0090GRID_DAILY (C2129186341), SSH_LLC0090GRID_MONTHLY (C2129189870), plus OBP (C2129192243, C2129193421, C2129195053, C2129197196), GMAP (C2133160276) and SBO (C2133162585). If SSH is used, prefer V4r4b.
- **bgc_variables:** none
- **access:** Earthdata login via PO.DAAC
- **size:** Per-granule sizes are similar to the V4r4 SSH collections (about 1 MB daily at 0.5°); exact totals were not summed.
- **pairing:** same_family
- **status:** verified_primary

### ECCO V4r5 (Version 4 Release 5)

- **producer:** ECCO Consortium (JPL)
- **physics_source:** V4r5 on LLC90, hourly MERRA-2 first-guess forcing (Nakayama et al. 2024), sea-ice thermodynamics in the adjoint, static ice-shelf cavities. It is further from v05 than V4r4: Zhang & Menemenlis (2024 ECCO meeting slides) report that Darwin driven by V4r5 gives 'much more different' Southern Ocean CO2 flux than LLC270-alpha or V4r4.
- **grid_resolution:** LLC90 (~1 degree), 50 levels
- **period:** 1992-2019 optimised (Nakayama 2024); extended '2020-near present' per Zhang & Menemenlis 2024 slides
- **cadence:** The Nakayama Zenodo subset is monthly. The ECCO 2023 meeting talk (Fukumori; seen only as a search snippet) says release 5 includes daily output, but I did not verify that daily files are distributed publicly.
- **physical_variables:** Zenodo subset: THETA, SALT, UVEL, VVEL, SSH, SIarea, SIheff monthly means. Full list on ECCO Drive not checked (401).
- **bgc_variables:** none
- **access:** - Not in NASA CMR: 0 hits for 'V4r5' and 'ECCO V4r5' on 2026-09-30.
- ECCO Drive https://ecco.jpl.nasa.gov/drive/files/Version4/Release5 returns 401 and needs an Earthdata/WebDAV login.
- The ecco_access tutorial says 'v4r5' works only in s3_open, s3_get and s3_get_ifspace modes (in-cloud). A requester-pays s3://ecco-model-granules/ bucket appeared only in a search snippet and was not verified.
- Public Zenodo monthly subset: https://doi.org/10.5281/zenodo.10930853, no auth.
- **size:** Zenodo record 10930853: 15.4 GB total. The full product size is unknown.
- **pairing:** same_family
- **status:** verified_primary

### ECCO LLC270 physical state estimate, iteration 50 ('LLC270-alpha'), Zenodo copy from Nakayama et al. 2024

- **producer:** JPL (H. Zhang, D. Menemenlis, I. Fenty); Zenodo deposit by Y. Nakayama
- **physics_source:** The ECCO LLC270 solution family that drove ECCO-Darwin v05, but iteration 50 rather than iteration 42. Nakayama 2024 calls iter50 'similar to iteration 42 used in ECCO-Darwin'. First guess: 6-hourly ERA-Interim. Closest public physical match to v05, but not bit-for-bit.
- **grid_resolution:** LLC270 (nominal 1/3 degree, ~15-18 km at high latitudes), 50 levels, global. Global coverage is inferred from file size: SIarea is 45.5 MB per year = 12 x 13 x 270^2 x 4 B.
- **period:** 1992-2017 (one file per year, 1992-2017)
- **cadence:** monthly (inferred from the 12-record-per-year file size)
- **physical_variables:** THETA, SALT, UVELMASS, VVELMASS, SIarea, SIheff, plus nctiles_grid
- **bgc_variables:** none
- **access:** Public Zenodo, no auth (record metadata read today; files not downloaded). The record says the fuller set is on ECCO Drive https://ecco.jpl.nasa.gov/drive/files/Version5/Alpha, which returns 401 and needs a login; that tree also holds v05's era_xx forcing. For monthly work it is redundant: v05's own local monthly THETA/SALTanom/velocities are the exact iter42 fields.
- **size:** Part 1 (10.5281/zenodo.10934678): 48.8 GB (THETA.zip 23.3 GB, UVELMASS.zip 25.0 GB, SIarea 0.15 GB, SIheff 0.17 GB, grid 0.19 GB). Part 2 (10.5281/zenodo.10935131): SALT.zip 17.8 GB, VVELMASS.zip 25.1 GB.
- **pairing:** same_family
- **status:** verified_primary

### ECCO-Darwin v05 LLC270 own physical diagnostics (daily and monthly)

- **producer:** ECCO-Darwin team (Carroll, Menemenlis, Zhang; JPL)
- **physics_source:** The exact LLC270 iter42 physics that drove the v05 BGC. Per the ecco_darwin v05 readme and namelists:
- forcing: era_xx EIG_*_plus_ECCO_v4r1_ctrl for T2m, q, precip, SW and LW, raw ERA-Interim 10-m winds (useAtmWind=.TRUE.), plus xx_*42 14-day controls and 3-D kapgm/kapredi/diffkr;
- deltaT 1200 s;
- darwin3 at 24885b71.
- **grid_resolution:** native LLC270, 50 levels (delR identical to ECCO v4)
- **period:** daily archive about 1992-2018 (9,790 records per the repo's own 2026-06-20 measurement); monthly 1992-2017+, extended to 2023 on ECCO Drive
- **cadence:** daily and monthly
- **physical_variables:** Daily, in data.diagnostics and on the NAS mirror:
- SST (THETA level 1)
- SSSanom (SALTanom level 1)
- wspeed (EXFwspee)
- SIarea
- SIheff

data.diagnostics has ALSO requested daily MXLDEPTH -> diags/daily/mldDepth since commit 797e496aff (2020-12-15; still present on master), but the repo's 2026-06-20 listing of the NAS daily directory does not include it.

Monthly: 3-D THETA, SALTanom, UE_VEL_C, VN_VEL_C, WVEL, PAR, plus mldDepth, oceQsw, oceQnet, ETAN/TFLUX/SFLUX and more.
- **bgc_variables:** Daily: surfChl1-5, pCO2 (3-D), pH (3-D), surfPCO2 (3-D), CO2_flux, O2_flux, surfDIC_tend, apCO2. Monthly: TRAC01-31, PP, fluxCO2, pH and more.
- **access:** NAS https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/ (no auth) is unreachable today. ECCO Drive ECCO2/LLC270/ECCO-Darwin_extension needs a login. Most of it is already local.
- **size:** Daily 2-D about 34.6 GB per variable (14 x 2-D is about 490 GB); 3-D daily about 1.5 TB each (repo memory note). The monthly mirror is already local.
- **pairing:** exact
- **status:** verified_primary

### ECCO-Darwin v05 1-degree (LLC90) run driven by ECCO V4r4 physics

- **producer:** ECCO-Darwin team (MITgcm-contrib/ecco_darwin v05/1deg)
- **physics_source:** Exactly the V4r4 physics: it is built from the V4r4 setup (c66g, /nobackup/hzhang1/pub/Release4 input_bin/input_forcing). Paired with V4r4 physical fields exactly, but it is a DIFFERENT BGC run from the LLC270 v05 target (different resolution; Savelli et al. 2026 say the 1-degree lineage reuses Carroll 2020 parameters).
- **grid_resolution:** LLC90 (~1 degree), 50 levels
- **period:** 1992-2017 (readme_darwin_v4r4.txt)
- **cadence:** The config makes diags/3hourly, daily and monthly directories; which daily fields are written was not checked
- **physical_variables:** V4r4 physics, exactly as in the PO.DAAC V4r4 collections
- **bgc_variables:** Darwin 3 tracers (same ecosystem family as v05); published outputs unknown
- **access:** Only the configuration is public (github.com/MITgcm-contrib/ecco_darwin/tree/master/v05/1deg). I found no public data location for the output. Carroll's 2024 ECCO-meeting slides say 'Both LLC 90 V4r4/V4r5 and LLC 270 versions now available' without a data URL. The repo's data/README cites ECCO Drive ECCO2/LLC90/ECCO-Darwin, which returns 401 and could not be checked.
- **size:** unknown
- **pairing:** unknown
- **status:** secondary_only

### SASSIE ECCO LLC1080 V1R1 (regional Arctic)

- **producer:** ECCO / SASSIE project, PO.DAAC
- **physics_source:** A separate regional high-resolution ECCO/MITgcm Arctic solution; not related to the v05 LLC270 physics
- **grid_resolution:** LLC1080 (regional Arctic)
- **period:** 2014-01-15 to 2021-02-08
- **cadence:** daily and snapshot
- **physical_variables:** T/S, velocity, SSH/OBP, heat/freshwater flux, stress, sea ice, KPP boundary layer and more (short names such as SASSIE_ECCO_L4_TEMP_SALINITY_LLC1080GRID_DAILY_V1R1, C3689031924-POCLOUD)
- **bgc_variables:** none
- **access:** PO.DAAC with Earthdata login (listed in CMR)
- **size:** not assessed
- **pairing:** different_physics
- **status:** verified_primary

## Unknowns

- No published DAILY field-by-field comparison of ECCO V4r4 against LLC270 iter42 (or the v05 run) was found. The only direct evidence is the Zhang & Menemenlis 2024 ECCO-meeting slides, a presentation not a paper, which show qualitatively different Southern Ocean CO2 flux when the same Darwin configuration is driven by LLC270-alpha, V4r4 and V4r5. The actual SST/MLD/current mismatch must be measured by comparing V4r4 daily SST/SSS/SIarea/SIheff/wspeed with v05's local daily fields and V4r4 monthly (24-28 GB) with v05 monthly.
- Whether v05's daily mldDepth exists anywhere. It has been in v05/llc270/input/data.diagnostics since 2020-12-15 (diags/daily/mldDepth), but the repo's 2026-06-20 NAS daily listing does not include it. It may be on Pleiades or ECCO Drive, which needs a login; ask Carroll or Zhang.
- What ECCO Drive Version5/Alpha holds (the LLC270 physical tree): which iterations (42 vs 50), whether daily 3-D or MLD fields exist, and sizes. It returned 401 today.
- Whether the V4r4-driven 1-degree ECCO-Darwin run (v05/1deg) has published BGC output. That would be an exactly paired physics-BGC dataset at 1 degree.
- The contents of the Zhang, Menemenlis & Fenty 2018 LLC270 technical note (MIT DSpace hdl 1721.1/119821). The PDF sits behind a CAPTCHA, which I did not bypass. The first-guess forcing details were verified instead from v05's data.exf file names (EIG_*_plus_ECCO_v4r1_ctrl and raw EIG_u10m/v10m).
- Whether LLC270 cells nest exactly 3x3 inside LLC90 cells, which would allow conservative remapping without interpolation error. This is inferred from the LLC construction, not verified.
- Monthly-collection DOIs were not fetched individually; only the daily and geometry DOIs above are verified.
- Whether V4r5 daily output is or will be distributed on PO.DAAC. It is absent from CMR today; the ecco_access docs say v4r5 is cloud-only.
- The size of the iteration 42 vs 50 difference in the LLC270 solution. Nakayama 2024 only says they are 'similar'.
- Whether v05's SALTanom reference value matches for comparison against V4r4 absolute SALT (the offset was not checked).
- PO.DAAC dataset landing pages (podaac.jpl.nasa.gov/dataset/...) timed out from this host today, so the collection facts come from the CMR UMM-C, UMM-G and UMM-Var records instead.
