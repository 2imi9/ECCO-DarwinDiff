# Paired physics 3: other MIT Darwin runs with their own physics

> **Agent-drafted, banked verbatim from the 2026-09-30 paired-physics workflow** (three sweeps and a critic, read-only, no credentials). Status labels per product. Where this conflicts with `paired_physics_critic.md`, the critic wins; see `../2026-09-30_topping_recipe_build_spec.md` §5.

## Summary

SHORT ANSWER. Yes, MIT runs Darwin on several MITgcm physical states. But only ONE family has the same biogeochemistry as ECCO-Darwin v05: the ECCO-Darwin v05 configurations run on OTHER physics. Everything else is a different ecosystem model, so it is a different target.

HOW TO READ THE PAIRING FIELD. `pairing` compares a product's PHYSICS with the physics that drove v05 (LLC270 iter42, era_xx / era_xx_it42_v2):
- exact = the same physical solution
- same_family = an ECCO-family state, but a different one
- different_physics = physics outside ECCO

Whether the BGC matches v05 is stated separately in each row.

1) SAME BGC AS v05, DIFFERENT PHYSICS. This is the only group that is safe to mix into training as a physics perturbation. Verified from github.com/MITgcm-contrib/ecco_darwin:
- v05/1deg runs Darwin 3 on ECCO V4r4 (LLC90, 1992-2017) and on V4r5 (1992-2024). I diffed its namelists against v05/llc270/input:
  - data.traits is byte-identical.
  - data.darwin is identical except the llc90 iron-dust file. It carries ALPFE 0.92831, SCAV_RAT 6.02502315E-7, smallgrow 0.66098, biggrow 0.43148, diatomgraz 0.83003, val_R_PICPOC 0.04245.
  - DARWIN_SIZE.h is identical (nplank 7, nPhoto 5, PTRACERS_num 31).
  - It writes the same daily and monthly diagnostics as v05.
- Its paired physics is PUBLIC. ECCO V4r4 is on PO.DAAC as daily and monthly fields, native LLC90 and 0.5 deg, 1992-01-01 to 2018-01-01. CMR ids were verified. Download needs an Earthdata login. The v05/1deg run should match V4r4 up to reproduction roundoff (inferred).
- The v05/1deg BGC OUTPUT is not public anywhere I could find. Re-running it needs three non-public NAS /nobackup directories, which the repo already found.
- Other LLC270 variants use the identical BGC namelists (verified): ECCO v5r1 physics (1992-2025), a 1985-2022 back-extension, repeat-year 1995 and 1999 forcing runs, and JRA55-do runoff. None has public output. Zenodo 10.5281/zenodo.13259496 holds code only.
- Savelli et al. 2026 GMD ran ECCO-Darwin on LLC90 V4r5 for 1992-2019. It released derived PP, pCO2, CO2 flux and SIarea (Zenodo 10.5281/zenodo.17317011, 3.14 GB). The paper counts 39 prognostic variables, while v05 has 31 tracers, so its exact configuration is unverified.

2) SAME PHYSICS AS v05, DIFFERENT BGC.
- v04 (Carroll 2020) uses the same LLC270 iter42 physics with Darwin 1. The public NAS listing, captured Feb 2025, shows input/ only.
- v06 (unreleased) uses the same nbp19 + era_xx_it42_v2 inputs, but a new ecosystem: 6 phytoplankton + 4 zooplankton, 36 tracers, radtrans, vent iron.
- Neither is the v05 target.

3) DIFFERENT BGC AND DIFFERENT PHYSICS. Mixing these in as ECCO-Darwin would hurt, because they are different models.
- CBIOMES-global alpha: 1992-2011, not 1992-2017. It runs pkg/gud with 35 phytoplankton + 16 zooplankton and radiative transfer, on ECCO v4 release-2 LLC90. Only the monthly climatology is public: Zenodo 10.5281/zenodo.5598417, 229 MB, CC-BY. The native-grid Dropbox link has expired, and engaging-opendap is unreachable.
- Darwin v0.2 cs510: the same 35+16 ecosystem on ECCO2 18 km, 3-day, 1994-2015. CMAP holds BGC only, with no physics.
- ECCO2-Darwin v02/v03 (Brix 2015): Darwin 1, R_PICPOC 0.133, ECCO2 adjoint iter22/26 + JRA-25 physics, 2009-2013.
- Manizza 2019: ECCO2 CS510 monthly BGC PLUS paired physics (THETA, SALTanom, ETAN, MXLDEPTH, oceQnet, sea ice, wind, PAR). The archived listing totals about 1.93 TB. The host was down on 2026-09-30.
- Dutkiewicz RadTrans runs on ECCO-GODAE 1 deg: monthly physics for one climatological year, plus daily 1994-2006 surface Chl and RRS.
- IGSM climate runs: 2 x 2.5 deg, 1991-2100, free-running.
- Darwin3 31+16+3 runs: annual or surface means only.
- The new offline ECCOv4r6 Darwin: 6 phytoplankton + 4 zooplankton, no output.
- These are useful only for physics-encoder pretraining, or with a model-identity token. They are never the same target.

RECOMMENDATION.
- The best new source of paired physics plus same-model BGC is v05/1deg on V4r4: its public daily physics (PO.DAAC) plus its BGC, which must be requested from Carroll/Zhang at JPL.
- Next, ask for the LLC270 physics-variant runs (v5r1, 1985 back-extension, repeat-year). These are a same-target physics ensemble.
- For daily 3-D physics exactly paired with v05 itself, the route is a physics-only LLC270 re-run with extra daily diagnostics. The v04 and v06 readme_physics files give the recipe. It needs era_xx_it42_v2 and nbp19 from ECCO Drive, which is up but Earthdata-gated.
- Heiser & Wagner (Zenodo 10.5281/zenodo.18854567) published daily full-column v05 T/S for May 2019 (Fram region). That suggests JPL holds daily 3-D v05 physics diagnostics (inferred).

ACCESS CHECKS ON 2026-09-30:
- data.nas.nasa.gov, engaging-opendap.mit.edu:8080 and the podaac.jpl.nasa.gov landing page did not respond (my probe; the task reported a 200 for the PO.DAAC archive). The APDRC ECCO2 paths returned 404.
- ECCO Drive returned 401.
- Zenodo, Harvard Dataverse, CMAP docs, GitHub and CMR all responded.

Nothing in the repo was edited. Scratch files are under the session scratchpad only.

## Products

### ECCO-Darwin v05 1deg (Darwin 3 on ECCO V4r4 / V4r5, LLC90)

- **producer:** Carroll, H. Zhang, Jahn (JPL/MIT); config MITgcm-contrib/ecco_darwin v05/1deg
- **physics_source:** The physics is computed online from an ECCO V4r4 reproduction setup (code_v4r4 + Release4 input_bin/input_forcing; readme_darwin_v4r4.txt), or from ECCO V4r5 (Release5; readme_darwin_v4r5.txt). This is NOT the physics that drove v05 LLC270, which is LLC270 iter42 era_xx. The BGC IS the v05 model: I diffed data.traits against v05/llc270/input and it is byte-identical. data.darwin is identical except 'llc90_Mahowald_2009_soluble_iron_dust.bin'. DARWIN_SIZE.h is identical and PTRACERS_num is 31; the only option difference is DARWIN_DIAG_PERTYPE. Its paired physics is the ECCO V4r4 release on PO.DAAC; that the run matches it up to reproduction roundoff is inferred, not bitwise.
- **grid_resolution:** LLC90 (~1 deg), 50 levels; V4r4 PO.DAAC physics also on 0.5 deg lat-lon
- **period:** V4r4 run 1992-2017; V4r5 run 1992-2024 per readme (Savelli 2026 GMD analysed Jan 1992-Dec 2019). PO.DAAC V4r4 physics 1992-01-01 to 2018-01-01 (CMR).
- **cadence:** Same diagnostics set as v05 LLC270: 3-hourly CO2 flux; daily 2-D surface; monthly 3-D. PO.DAAC V4r4 physics is daily and monthly.
- **physical_variables:** The run itself writes daily SST, SSSanom, wspeed, SIarea, SIheff and mldDepth, and monthly THETA, SALTanom, uVel_C, vVel_C, wVel, oceanQsw, oceanQnet and mldDepth. The public V4r4 daily physics on PO.DAAC includes temperature/salinity, velocities, mixed-layer depth, heat and freshwater flux, wind stress, atmospheric state, sea-ice concentration and thickness, SSH, bottom pressure, and 3-D T/S/volume fluxes. Example CMR ids:
- ECCO_L4_TEMP_SALINITY_LLC0090GRID_DAILY_V4R4 = C1991543736-POCLOUD
- ECCO_L4_OCEAN_VEL_LLC0090GRID_DAILY_V4R4 = C1991543808-POCLOUD
- ECCO_L4_MIXED_LAYER_DEPTH_LLC0090GRID_DAILY_V4R4 = C1991543734-POCLOUD
- ECCO_L4_HEAT_FLUX_LLC0090GRID_DAILY_V4R4 = C1991543712-POCLOUD
- ECCO_L4_SEA_ICE_CONC_THICKNESS_LLC0090GRID_DAILY_V4R4 = C1991543763-POCLOUD
- ECCO_L4_STRESS_LLC0090GRID_DAILY_V4R4 = C1991543704-POCLOUD
- **bgc_variables:** Identical to v05: DIC, ALK, NO3, NO2, NH4, PO4, FeT, SiO2, DOC, DON, DOP, DOFe, POC, PON, POP, POSi, POFe, PIC, O2, Chl1-5, 5 phytoplankton + 2 zooplankton, daily surfChl1-5, pCO2, pH and CO2_flux. Carroll-6 values: ALPFE 0.92831, SCAV_RAT 6.02502315E-7, smallgrow 0.66098, biggrow 0.43148, diatomgraz 0.83003, val_R_PICPOC 0.04245.
- **access:** The config is public at https://github.com/MITgcm-contrib/ecco_darwin/tree/master/v05/1deg.
- BGC output: no public archive found. The archived data.nas llc_90 listing shows only ECCOv4.
- Derived LLC90-V4r5 surface fields (PP, pCO2, CO2flux, SIarea as .mat) are at Zenodo 10.5281/zenodo.17317011 (CC-BY-4.0, reachable, no auth).
- V4r4 physics: PO.DAAC POCLOUD, Earthdata login required.
- Re-running needs the jahn/darwin3 fork plus non-public NAS dirs (/nobackup/dcarrol2/pub/1deg/v05/V4r4, apCO2 NOAA_MBL, hzhang1 Release4).
- **size:** Savelli Zenodo record 3,139,818,356 bytes; the V4r4 physics volume was not measured
- **pairing:** same_family
- **status:** verified_primary

### ECCO-Darwin v05 LLC270 physics-variant runs (ECCO v5r1 physics; 1985-2022 back-extension; repeat-year 1995/1999 forcing; JRA55-do runoff)

- **producer:** Carroll / H. Zhang (JPL); ecco_darwin v05/llc270 readme_v5r1.txt, readme_1985.txt; v05/llc270_jra55do
- **physics_source:** The BGC is the same v05 model, verified by diff:
- input2 data.darwin and data.traits are identical to input.
- input_1985 and input_1995 differ only in pCO2startdate2.
- llc270_jra55do overrides only data, data.exf and data.ptracers.
The physics is perturbed relative to v05:
- ECCO v5r1 LLC270 state (input_v5r1)
- exf_1985 forcing starting 1985-01-01
- repeated-1995 or repeated-1999 atmospheric forcing, with linear-apCO2 variants
- JRA55-do point-source runoff (otherwise v05 physics)
- **grid_resolution:** LLC270 (~1/3 deg), 50 levels
- **period:** v5r1 1992-2025; back-extension and repeat-year runs 1985-2022; jra55do 1992-2023 (inferred from the base readme)
- **cadence:** Assumed to match the v05 diagnostics (daily 2-D surface, monthly 3-D). The data.diagnostics files of the variants were not diffed.
- **physical_variables:** Assumed to match the v05 archive: daily SST, SSSanom, wspeed, SIarea, SIheff; monthly THETA, SALTanom, u/v/wVel, oceanQsw, oceanQnet, mldDepth
- **bgc_variables:** Identical v05 set (Carroll-6 values unchanged)
- **access:** Configs are public on GitHub. Zenodo 10.5281/zenodo.13259496 ('v05 1985 Back-extension', CC-BY-4.0) is a code snapshot only. No public output was found for any variant; it would have to be requested from JPL (Carroll).
- **size:** code snapshot 781,230,831 bytes; output unknown
- **pairing:** same_family
- **status:** verified_primary

### ECCO-Darwin v04 (Carroll et al. 2020 JAMES, llc270_JAMES_paper)

- **producer:** Carroll, Menemenlis et al. (JPL)
- **physics_source:** This is the LLC270 iter42 forward physics (v04 readme_physics.txt: iter42 inputs, era_xx forcing plus xx_*42 adjustments to 2018). It is the same optimized physical solution that v05 uses, so it counts as the same physics.
- The BGC is Darwin 1, not Darwin 3 (the repo readme states 'v02 to v04 use Darwin 1').
- Per the repo research map, its Carroll-6 values are bit-identical to v05, but the code differs.
- **grid_resolution:** LLC270, 50 levels
- **period:** 1992-2017
- **cadence:** unknown (the output is no longer listed)
- **physical_variables:** unknown for the published archive
- **bgc_variables:** Darwin 1 tracer set (5 phytoplankton + 2 zooplankton)
- **access:** A Wayback capture of the data.nas listing for llc_270/ecco_darwin_v4/ (2025-02-12) shows only input/. No public output was found. data.nas was unreachable on 2026-09-30.
- **size:** unknown
- **pairing:** exact
- **status:** verified_primary

### ECCO-Darwin v06 (unreleased; v06/llc270 and v06/1deg)

- **producer:** Carroll, Jahn, Savelli et al. (JPL/MIT)
- **physics_source:** v06/llc270 readme_physics.txt uses the same nbp19_dmenemen_public_llc270 inputs and era_xx_it42_v2 forcing as v05's unified-forcing run. The physics is therefore nominally the same as v05, but it uses the c69e code checkpoint, so it is not bitwise. v06/1deg runs on ECCO V4r5.

The BGC is DIFFERENT: DARWIN_SIZE nplank 10 and nPhoto 6 (6 phytoplankton + 4 zooplankton), 36 ptracers, radtrans + OASIM, hydrothermal vent iron, BGC runoff and RADI sediment. data.traits is 2,324 bytes against v05's 5,334.
- **grid_resolution:** LLC270 and LLC90, 50 levels
- **period:** 1992-2024 (readme)
- **cadence:** daily, monthly and 3-hourly diagnostics are configured, plus monthly IOPS, PAR and RRS
- **physical_variables:** as configured (not public)
- **bgc_variables:** v06 ecosystem, which differs from v05
- **access:** Unreleased. Configs are on GitHub. No public output.
- **size:** n/a
- **pairing:** exact
- **status:** verified_primary

### CBIOMES-global (alpha version) = Darwin_v0.1_llc90

- **producer:** Gael Forget (MIT) with the MIT Darwin Project (Dutkiewicz, Jahn); CBIOMES/global-ocean-model
- **physics_source:** ECCO version 4 (Forget et al. 2015) run online. download_input.sh pulls the ECCO v4 release-2 forcing and initial conditions (mit.ecco-group.org/ecco_for_las/version_4/release2). This is NOT the v05 physics.

The BGC is a DIFFERENT model: pkg/gud (git://gud.mit.edu/gud-dev2, branch 'cube92'), with nplank 51 (35 phytoplankton + 16 zooplankton), 106 ptracers, and radiative transfer in 13 wavebands (GUD_SIZE.h, PTRACERS_SIZE.h). That pkg/gud is the predecessor of darwin3 pkg/darwin is inferred.
- **grid_resolution:** LLC90 (~1 deg), 50 levels; the public climatology is interpolated to 0.5 deg
- **period:** 1992-2011 (docs index.rst; data.cal start 1992-01-01)
- **cadence:** The model writes monthly diagnostics (frequency 2635200 s). The public product is a monthly CLIMATOLOGY only.
- **physical_variables:** The run writes monthly THETA, SALT, DRHODR, UVELMASS, VVELMASS, WVELMASS, GM_PsiX/Y, ETAN, MXLDEPTH, oceQnet, oceFWflx, oceTAUX/Y, SIarea, SIheff, SIhsnow, PAR (13 bands), Rirr and rmud. Which of these are in the public climatology is not verified.
- **bgc_variables:** All 106 tracers, PP, Nfix and Denit. The CMAP Darwin_clim tables carry DIC, ALK, NO3, NO2, NH4, PO4, SiO2, FeT, DOC/DON/DOP/DOFe, POC/PON/POSi/POFe, PIC, O2, CDOM, and plankton c01-c51.
- **access:** Zenodo 10.5281/zenodo.5598417 ('Interpolated Climatology, surface variables', CC-BY-4.0) is reachable with no auth. CMAP Darwin_clim needs a free CMAP API key. engaging-opendap.mit.edu:8080 was unreachable on 2026-09-30. The native-grid Dropbox folder link has EXPIRED (verified). The setup is MIT-licensed on GitHub (Zenodo 10.5281/zenodo.2653669).
- **size:** Zenodo climatology tarball 228,924,528 bytes; native output unknown
- **pairing:** same_family
- **status:** verified_primary

### Darwin v0.2 cs510 (GUD CS510 18 km interannual; CMAP 'Darwin 3 Day Averaged Model')

- **producer:** MIT Darwin Project (Dutkiewicz, Jahn); Kuhn et al. JGR
- **physics_source:** ECCO2 (Menemenlis et al. 2008), CS510 cubed sphere at 18 km, run online. CMAP says 'ECCO2 synthesis covers 1992-2015'. The cube iteration is not stated; cube92-family is inferred. This is NOT the v05 physics.

The BGC is DIFFERENT: 35 phytoplankton + 16 zooplankton, Monod kinetics, radtrans, CDOM (after Dutkiewicz 2015 and Ward 2012).
- **grid_resolution:** native CS510 (~18 km), 50 levels; CMAP 0.5 deg with 50 depth levels; Dataverse 1/5 deg
- **period:** CMAP 1994-01-03 to 2015-12-30; a secondary source says 1992-2016 on the MIT OPeNDAP server
- **cadence:** 3-day means
- **physical_variables:** NONE in the CMAP tables. Paired physics must come from the ECCO2 archive separately.
- **bgc_variables:** CMAP tables:
- tblDarwin_Nutrient: FeT, PO4, DIN, SiO2, O2
- tblDarwin_Ecosystem: Shannon diversity, total phytoplankton, zooplankton, CHL, depth-integrated PP
- tblDarwin_Ocean_Color: irradiance reflectance wavebands 3 and 7
- tblDarwin_Phytoplankton: diatom, coccolithophore, mixotrophic dinoflagellate, picoeukaryote, picoprokaryote
Dataverse: 3-daily surface biomass of all 35 types for year 2000.
- **access:** CMAP (simonscmap.com) needs a free API key. Harvard Dataverse doi:10.7910/DVN/1HGIV8 (CC0, reachable). The full output is on engaging-opendap.mit.edu:8080 ('Darwin v0.2 cs510'), which was unreachable on 2026-09-30.
- **size:** Dataverse 1HGIV8: 122 files, 27.68 GB; CMAP volume unknown
- **pairing:** same_family
- **status:** verified_primary

### ECCO2 cube92 physical state (0.25 deg lat-lon product of CS510)

- **producer:** JPL ECCO2 (Menemenlis, H. Zhang)
- **physics_source:** The ECCO2 Green's-function-optimized solution cube92 (archived data.nas readme). It is the likely physics of the Darwin v0.2 cs510 run (inferred). It is NOT the physics of ECCO2-Darwin v02/v03 or Manizza (adjoint iter22/26 ICs) and NOT the v05 physics.
- **grid_resolution:** native CS510 ~18 km, 50 levels; distributed at 0.25 deg (1440x720)
- **period:** 1992-01-01 to 2019-03-31 per the archived NAS readme. An APDRC page snippet (secondary) claims daily data to 2024-12-31; the two conflict.
- **cadence:** daily and monthly
- **physical_variables:** Directory names in the archived NAS listing: THETA, SALT, UVEL, VVEL, WVEL, SST, SSS, SSH, PHIBOT, MXLDEPTH, SIarea, SIheff, SIhsnow, oceQnet_daily, oceQsw_daily, oceTAUX_daily, oceTAUY_daily, oceFWflx_daily
- **bgc_variables:** none
- **access:** https://data.nas.nasa.gov/ecco/eccodata/cs_510/ needs no auth normally but was unreachable on 2026-09-30. The APDRC mirror (apdrc.soest.hawaii.edu ECCO2 paths) returned 404 on 2026-09-30. ECCO Drive needs Earthdata (not tested).
- **size:** ~23.6 GB/yr 3-D + 1.5 GB/yr 2-D (APDRC per search snippet, secondary only)
- **pairing:** same_family
- **status:** verified_primary

### ECCO2-Darwin v02/v03 (Brix et al. 2015 Ocean Modelling; CMS Flux pilot)

- **producer:** Brix, Menemenlis (UCLA/JPL); ecco_darwin v02/cs510_Brix, v03/cs510_latest
- **physics_source:** ECCO2-CS510 ver.2 adjoint iter22 (Jan 2009-Apr 2010), then JRA-25; v03 uses ICBC_2009_iter26 + JRA-25. This is NOT cube92 and NOT the v05 physics.

The BGC is Darwin 1 (MITgcm_contrib/darwin, 2011) with 5 phytoplankton (Dutkiewicz setup). R_PICPOC was Green's-function-tuned to 0.133 and the piston factor to 0.34822, so this is a different BGC version and parameters.
- **grid_resolution:** CS510 ~18 km, 50 levels
- **period:** v02 2009-2010; v03 2009-2013
- **cadence:** monthly averages (v02 NetCDF global attributes)
- **physical_variables:** unknown for the distributed product
- **bgc_variables:** Darwin 1 set: DIC, ALK, nutrients, 5 phytoplankton, CO2 flux
- **access:** The output was originally at ftp://ecco.jpl.nasa.gov/ECCO2/Darwin/CarbFlux_v2 (per the readme). Its current location is presumably ECCO Drive, Earthdata-gated; not verified.
- **size:** unknown
- **pairing:** same_family
- **status:** verified_primary

### ECCO2_darwin_MMGBC19 (Manizza et al. 2019 GBC, ECCO2-Darwin AO simulation)

- **producer:** Manizza, Menemenlis (JPL); ecco_darwin v02/cs510_Manizza_AO
- **physics_source:** The physics is ECCO2 CS510 with ICBC_2009_iter26 + JRA-25 (readme). The run writes its OWN physics fields, so the BGC and physics are paired within this product. It is not the v05 physics. The period is inferred as ~2004-2013 from the restart dir 'rest_2004_2013_run1' and 124 monthly records.

The BGC is Darwin 1 (5 phytoplankton Phy01-05, 2 zooplankton) plus N2O, Ar and O2 components, so it is not v05.
- **grid_resolution:** native CS510 (510x6x510, 50 levels; 297.66 MB per 3-D record)
- **period:** ~2004-2013 (inferred); 124 records per variable, iterations 2232-271656
- **cadence:** monthly
- **physical_variables:** THETA, SALTanom, ETAN, MXLDEPTH, oceQnet, SIarea, SIheff, EXFwspee (wind speed), PAR. No velocities.
- **bgc_variables:** ALK, DIC, NO3, NO2, NH4, PO4, FeT, SiO2, O2, DOC, DON, DOP, DOFe, POC, PON, POP, POSi, POFe, PIC, CHL1-5, Phy01-05, ZOOC1-2 and ZOO N/P/Fe/Si, PP, NCP, pCO2, pH, and CO2/O2/N2O/Ar fluxes
- **access:** https://data.nas.nasa.gov/ecco/eccodata/cs_510/ECCO2_darwin_MMGBC19/ needs no auth normally but the host was unreachable on 2026-09-30. The listing was verified via a Wayback capture (2024-10-30).
- **size:** 17,034 files, ~1.93 TB (summed from the archived listing)
- **pairing:** same_family
- **status:** verified_primary

### Dutkiewicz et al. 2015 RadTrans run ('size163_9spec_radtrans') on ECCO-GODAE

- **producer:** Dutkiewicz, Hickman, Jahn et al. (MIT); Harvard Dataverse 'darwin' / MONOD_RADTRANS; BCO-DMO
- **physics_source:** ECCO-GODAE state estimate at 1 deg. The 23-level count comes from the sibling 31+16+3 records and is inferred for this run. It is an older ECCO product, not the v05 physics.

The BGC is DIFFERENT: 9 phytoplankton types, radtrans, Monod kinetics.
- **grid_resolution:** 1 deg x 1 deg, 23 levels (inferred)
- **period:** Climatological: the 10th simulation year for 3-D monthly fields. Interannual: 1994-2006 daily surface (360-day years).
- **cadence:** monthly for 3-D; daily for surface Chl and RRS
- **physical_variables:** DVN/NZQEGJ physics file: temperature, salinity, velocities, mixed-layer depth and PAR to 160 m (monthly, one climatological year)
- **bgc_variables:** monthly nutrients and plankton biomass to 160 m; daily 1994-2006 surface Chl, satellite-like derived Chl, RRS 450/475/500/550
- **access:** Harvard Dataverse doi:10.7910/DVN/NZQEGJ and doi:10.7910/DVN/NWR1QY (CC0, reachable); code in doi:10.7910/DVN/R12GTM; BCO-DMO dataset 676534 (CC-BY-4.0)
- **size:** NZQEGJ 1.20 GB (physics file 226,718,580 bytes); NWR1QY 78 files 9.51 GB; BCO-DMO ~446 MB (secondary)
- **pairing:** same_family
- **status:** verified_primary

### Dutkiewicz 2019 ocean-colour climate run and GUD IGSM 51-plankton runs (MIT IGSM physics)

- **producer:** Dutkiewicz, Monier, Cael, Bardon et al. (MIT); Harvard Dataverse MONOD_RADTRANS_IGSM and GUD IGSM
- **physics_source:** The ocean is the MITgcm component of the MIT Integrated Global System Model: 2 deg x 2.5 deg, 22 levels, forced by the IGSM intermediate-complexity atmosphere under a business-as-usual scenario (~RCP8.5). It is free-running, so ENSO is not phased to real years. This physics is outside ECCO, not v05.

The BGC is DIFFERENT: the 2019 run has 8 phytoplankton + 2 grazers with radtrans; GUD IGSM has 51 plankton.
- **grid_resolution:** 2 x 2.5 deg, 22 levels
- **period:** 1991-2100 (GUD IGSM); 1995-2100 archived for the 2019 run
- **cadence:** monthly surface environment and biomass; annual for others
- **physical_variables:** LQH9PX: monthly 0-10 m SST, SSS and surface PAR
- **bgc_variables:** surface NO3, PO4, Fe, SiO2, group biomass, depth-integrated biomass, PP; 2019 run: surface Chl, CDOM, detritus, 6 phytoplankton biomasses, RRS in 13 bands
- **access:** Harvard Dataverse (CC0, reachable): 10.7910/DVN/08OJUV, 10.7910/DVN/LQH9PX, 10.7910/DVN/RPL6PT, 10.7910/DVN/LWHQNS, 10.7910/DVN/5CEWCL, 10.7910/DVN/91LPNJ; code 10.7910/DVN/UE8OS1, 10.7910/DVN/UA8VNU
- **size:** 08OJUV 0.26 GB; LQH9PX 0.95 GB; RPL6PT 0.96 GB; LWHQNS 0.63 GB
- **pairing:** different_physics
- **status:** verified_primary

### Darwin3 31+16+3 family (Follett 2022; Dutkiewicz 2023/2024 Interactions; Archibald; plus Mattei 2024, Serra-Pompei 2023, Sharoni 2026)

- **producer:** MIT Darwin Project (Dutkiewicz, Jahn, Follett, Mattei, Serra-Pompei, Sharoni)
- **physics_source:** MITgcm constrained to ECCO-GODAE, 1 x 1 deg, 23 levels (Zenodo 7779369 text). Climatological forcing is inferred. This is not the v05 physics.

The BGC is DIFFERENT: darwin3 with 31 phytoplankton + 16 grazers + 3 bacteria. The Mattei, Serra-Pompei and Sharoni setups were not inspected.
- **grid_resolution:** 1 deg, 23 levels
- **period:** climatological / equilibrium years (inferred)
- **cadence:** annual or climatological means in the published files
- **physical_variables:** none published in the 31+16+3 Dataverse records
- **bgc_variables:** surface or depth-integrated biomass of 50 types, PP, P budget (Dataverse); other records not inspected
- **access:** Dataverse doi:10.7910/DVN/FEWXB4, 10.7910/DVN/5YRVHO, 10.7910/DVN/KVCK1Q (CC0). Zenodo 10.5281/zenodo.7779369 (code), 10.5281/zenodo.14283389, 10.5281/zenodo.7829180, 10.5281/zenodo.20522983 (CC-BY-4.0). All reachable.
- **size:** FEWXB4 0.02 GB; 5YRVHO 0.23 GB; KVCK1Q 0.20 GB; Zenodo 14283389 185,729,861 B; 7829180 ~10.29 GB; 20522983 2,844,609,152 B
- **pairing:** same_family
- **status:** verified_primary

### Offline ECCO-Darwin on ECCOv4r6 physics (ecco_darwin/offline/V4r6_darwin_offline)

- **producer:** ECCO-Darwin team (checked in 2026-08-27); derived from Dutkiewicz's 1-deg offline config
- **physics_source:** A daily-mean physical archive written by an ECCOv4r6 forward run (LLC90, GGL90 mixing) and read by pkg/offline. This is ECCO-family physics, not v05.

The BGC is DIFFERENT from v05: 6 phytoplankton + 4 zooplankton, 36 tracers, OASIM + radtrans.
- **grid_resolution:** LLC90, 50 levels
- **period:** 1992-2025
- **cadence:** daily-mean physics archive feeding the offline run
- **physical_variables:** The forward run adds 11 daily streams needed offline; the recipe is only in the repo.
- **bgc_variables:** v06-like 6P+4Z ecosystem
- **access:** Recipe only (GitHub). No public output.
- **size:** n/a
- **pairing:** same_family
- **status:** verified_primary

### ED-SBS regional ECCO-Darwin (Southeastern Beaufort Sea / Mackenzie plume; Bertin et al. 2025 BG)

- **producer:** Clement Bertin et al.
- **physics_source:** A regional MITgcm with open boundaries (data.obcs in the run dir). The repo's regions/mac_delta has LLC270 and LLC4320 cut-outs; the exact parent and resolution were not verified. The BGC looks v05-derived Darwin 3 plus CDOM modifications (data.traits 5.3 kB, the same size as v05); this is inferred.
- **grid_resolution:** regional, high resolution (not verified)
- **period:** not verified
- **cadence:** daily diag files (iteration step 72)
- **physical_variables:** not inspected (only the zip preview)
- **bgc_variables:** carbon and other diags; 5 experiments (ctrl, full, lin, light, noriv)
- **access:** Zenodo 10.5281/zenodo.17429496 (CC-BY-4.0, reachable, no auth)
- **size:** 30,577,596,616 bytes (5 run zips of ~6.1 GB each)
- **pairing:** same_family
- **status:** inferred

### Heiser & Wagner 2026 v05 subsets (Greenland Sea blooms)

- **producer:** Heiser, Wagner
- **physics_source:** This IS ECCO-Darwin v05, so the physics is exactly v05's. It is a re-publication, not new physics. It includes 'daily full-column fields for May 2019' (potential temperature and salinity, Fram region). That suggests daily 3-D v05 physics diagnostics exist at JPL (inferred).
- **grid_resolution:** LLC270 (subset / regridded)
- **period:** monthly 1992-2019; daily 2019 surface Chl; daily May 2019 full-column T/S
- **cadence:** monthly and daily
- **physical_variables:** SST, SSS, sea-ice concentration (monthly); T/S full column (May 2019, Fram_llc270_TS.mat)
- **bgc_variables:** surface Chl, PO4, NO3 (monthly); daily 2019 surface Chl
- **access:** Zenodo 10.5281/zenodo.18854567 (CC-BY-4.0, reachable, no auth)
- **size:** 19,990,402,457 bytes
- **pairing:** exact
- **status:** verified_primary

### LLC270 iter42 physics-only forward run (ECCO LLC270; the physical twin of v05)

- **producer:** H. Zhang, Menemenlis (JPL)
- **physics_source:** The same physical solution that drives v05. v04 readme_physics.txt is 'llc270 physical simulation without Darwin' (iter42 inputs, era_xx, xx_*42). v06 readme_physics.txt uses nbp19_dmenemen_public_llc270 + era_xx_it42_v2. A re-run can write any daily 3-D diagnostics.
- **grid_resolution:** LLC270, 50 levels
- **period:** 1992-2017 (v04 recipe); 1992-2024 (v06 recipe)
- **cadence:** user-configurable via data.diagnostics
- **physical_variables:** any MITgcm diagnostic (THETA, SALT, U/V/W, MXLDEPTH, Qsw, Qnet, KPP/GGL90 diffusivity, etc.)
- **bgc_variables:** none
- **access:** Inputs: iter42/input on data.nas (unreachable 2026-09-30). era_xx_it42_v2 and nbp19 are on ECCO Drive (Earthdata; HTTP 401 today). A published physics OUTPUT archive was not found in this search.
- **size:** unknown
- **pairing:** exact
- **status:** inferred

## Unknowns

- Whether the v05/1deg BGC output (ECCO V4r4 1992-2017 or V4r5) exists in a shareable form at JPL. Savelli et al. 2026 evidently ran an LLC90 V4r5 ECCO-Darwin. No public archive was found, and re-running needs non-public NAS /nobackup dirs.
- How closely the v05/1deg physics reproduces the released ECCO V4r4 fields on PO.DAAC. The run uses the V4r4 reproduction setup, but MITgcm is not bitwise reproducible across compilers and decompositions.
- The exact configuration of Savelli's LLC90 V4r5 run: the GMD paper cites 39 prognostic variables, while v05 PTRACERS_num is 31.
- Whether the v05 physics-variant runs (v5r1, 1985 back-extension, repeat-year 1995/1999, JRA55-do) have output JPL would share, and whether their data.diagnostics match v05 (not diffed).
- Which ECCO2 iteration drove Darwin v0.2 cs510 (cube92 is inferred), and the end date of the ECCO2 cube92 archive (NAS readme says 2019-03-31; an APDRC snippet says 2024-12-31).
- Whether the full-depth Darwin v0.2 cs510 and CBIOMES native-grid outputs still exist anywhere. engaging-opendap.mit.edu:8080 was unreachable and the CBIOMES Dropbox link has expired.
- Current availability of the data.nas.nasa.gov ECCO holdings: v04 output appears removed (Feb 2025 capture shows input/ only); the Manizza cs_510 set and the cube92 fields could not be checked live on 2026-09-30.
- The Manizza MMGBC19 simulation period (inferred ~2004-2013 from a restart dir name and 124 monthly records).
- Whether an ordinary Earthdata account can read the ECCO Drive trees needed for a physics-only LLC270 re-run (era_xx_it42_v2, nbp19_dmenemen_public_llc270). ECCO Drive answers 401.
- Where JPL keeps the daily full-column v05 T/S that Heiser & Wagner used for May 2019, and whether it covers the full period.
- The ED-SBS regional configuration: parent grid, resolution, period, and whether its Darwin namelists match v05 (inferred from file sizes only).
- Volumes of the CMAP Darwin_3day tables and of the PO.DAAC V4r4 daily physics (not measured).
- No MIT Darwin run forced by CMIP6 ocean physics with public output was found.
