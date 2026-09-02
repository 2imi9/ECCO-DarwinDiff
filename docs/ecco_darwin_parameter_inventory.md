# ECCO-Darwin parameter inventory (Carroll 2020 build)

A verified count of biogeochemistry parameters in the ECCO-Darwin v04 LLC270 JAMES paper configuration (Carroll et al. 2020, Darwin 1). Captured here so DarwinDiff scoping arguments rest on real numbers rather than estimates.

> **Note (2026-05-09):** Carroll 2022 (v05, Darwin 3) **inherits Carroll 2020's six calibrated values bit-for-bit** — verified directly by reading `v04/llc270_JAMES_paper/code_darwin/{darwin_init_fixed.F, darwin_generate_phyto.F}` and `v05/llc270/input/data.darwin`. The numbers in this doc are therefore current for both Carroll 2020 and Carroll 2022 setups. The DarwinDiff project's active recovery target is Carroll 2022 / v05 (publicly-accessible), but the underlying parameter inventory is unchanged. See `docs/findings/2026_05_09.md` finding 8 and `docs/research_log.md` §F1.

## Method

Read three files line-by-line from a fresh clone of [`MITgcm-contrib/ecco_darwin`](https://github.com/MITgcm-contrib/ecco_darwin) at master, scoped to `v04/llc270_JAMES_paper/code_darwin/`:

- `DARWIN_OPTIONS.h` (111 lines), to determine which `#ifdef` blocks are active in the compiled binary.
- `darwin_init_fixed.F` (390 lines), with every parameter assignment classified.
- `darwin_generate_phyto.F` (782 lines), grep-confirmed as mostly mechanical derivation from the `init_fixed.F` scalars.
- `darwin_plankton.F` (1711 lines), the dynamics integrator. It uses parameters defined elsewhere; no new independent parameters introduced.

## Active compile-time flags (Carroll 2020 build)

From `DARWIN_OPTIONS.h`:

- **Active**: `ALLOW_CARBON`, `GEIDER`, `DYNAMIC_CHL`, `MINFE`, `IRON_SED_SOURCE`, `IRON_SED_SOURCE_VARIABLE`, `PART_SCAV`, `NINE_SPECIES_SETUP`, `TEMP_VERSION 2`, `USE_QSW`, `USE_EXFWIND`, `USE_EXFCO2`, `PORT_RAND`, `CALC_RATE_TOTALS`
- **Inactive**: `WAVEBANDS`, `OASIM`, `OLD_GRAZE`, `ALLOW_DIAZ`, `ALLOW_DENIT`, `ALLOW_MUTANTS`, all `DAR_DIAG_*`, `RELAX_NUTS`, `FLUX_NUTS`

Denitrification, diazotrophy, spectral radiative transfer, and most diagnostics are not in the compiled binary for this run.

## Model dimensions (`DARWIN_SIZE.h`)

- 5 phytoplankton functional types (`npmax = 5`; the `NINE_SPECIES_SETUP` flag name is historical)
- 2 zooplankton functional types (`nzmax = 2`)
- 4 elemental components per zooplankton (`nCompZooMax = 4`: P, N, Fe, Si)
- 39 prognostic tracers total, matching Carroll 2020 §2.3

## Verified parameter counts

| Class | Count | Source file |
|---|---|---|
| **Independent active tunable scalars** | **103** | `darwin_init_fixed.F` |
| Derived equalities (`Kpremin_N = Kpremin_P`, `wn_sink = wp_sink`, etc.) | 6 | `darwin_init_fixed.F` |
| Dead in this build (#ifdef inactive: denit, diaz, mutants, diagnostics) | 11 | `darwin_init_fixed.F` |
| Unit conversions (`parconv`, `permil`, `Pa2Atm`) | 3 | `darwin_init_fixed.F` |
| Hardcoded per-phyto identity traits (`physize`, `phyto_esd`, `phyto_vol`, `diacoc`, `diazotroph`, `nsource`, `ap_type` × 5 types) | **35** (7 traits × 5 phyto types, exact) | `darwin_generate_phyto.F` |
| New independent parameters | 0 | `darwin_plankton.F` |

The 35 hardcoded per-phyto traits are *classifications* (small vs large, diatom vs cocco vs other, etc.) that define the identity of each phytoplankton type, not adjustable knobs. The kinetic per-phyto arrays (`mu`, `ksatPO4`, `R_NP`, `wsink`, ...) are derived from the 103 `init_fixed.F` scalars by simple assignment or arithmetic (for example `ksatNO3(np) = ksatPO4(np) * R_NP(np)`).

**Headline: ~103 independent tunable scalar knobs.**

## Parameters tuned via Green's functions in Carroll 2020

Six. Source values verified directly in the Carroll 2020 build, with paper Table 1 cross-reference:

| # | Source variable | File:line | Optimized value | Paper Table 1 name |
|---|---|---|---|---|
| 1 | `alpfe` | `init_fixed.F:83` | 0.92831 | Scalar on the already-soluble Fe deposition flux (Darwin's legacy label "iron dust solubility"; **not** a solubility) |
| 2 | `scav_rat` | `init_fixed.F:101` | 10.41124 × 0.005 / 86400 | Iron scavenging rate |
| 3 | `Smallgrow` | `init_fixed.F:161` | 0.66098 | Small phytoplankton growth rate |
| 4 | `Biggrow` | `init_fixed.F:162` | 0.43148 | Large phytoplankton growth rate |
| 5 | `diatomgraz` | `init_fixed.F:272` | 0.83003 | Diatom palatability |
| 6 | `R_PICPOC` | `generate_phyto.F:484` | 0.04245 | PIC/POC ratio |

Each parameter has its pre-optimization default visible in a commented-out line nearby (for example `cswd  scav_rat=0.005 _d 0/(86400.0 _d 0)` at line 99). The Green's functions workflow literally edits these constants in source and recompiles per experiment — the "labor-intensive" cycle this project replaces with autograd.

## What this means for DarwinDiff

**Calibration coverage gap: 6 / 103 ≈ 5.8 %.** The other ~94 % of independently tunable knobs sit at expert or literature defaults applied uniformly across the global ocean. Many are single global scalars: `Kdop = 2 / (100 × 86400)` controls DOC remineralization rate everywhere on Earth, `kgrazesat = 0.085` is one number for grazing half-saturation across all ocean conditions, `phytoTempOptimum` is one curve per phytoplankton class with no spatial variation. Replacing such scalars with MLP-predicted spatial fields, which is what DarwinDiff's parameter-learner
does, removes the **cost** barrier that confines Green's functions to a handful of parameters at a
time: an additional parameter costs an extra channel on the MLP head rather than a fresh ensemble of
recompiled forward runs. **Whether that converts into more *recovered* parameters is unproven.**

DarwinDiff has so far only targeted the same Carroll-6, and its own results characterize a structural
ceiling there: no single config recovers all four observables, and the trade-off is structural rather
than an optimization limit ([STATUS.md](../STATUS.md), jobs 185779 + 192298). Identifiability is
parameter-specific rather than uniformly cheap. Measured on real observations at n=50, `alpfe` and
`R_PICPOC` recover decisively while `scav_rat` collapses to 0/50 and the joint trio to 0/50 once
Darwin's own output is dropped as a target
([2026-07-28 evidence log](findings/2026-07-28_session_evidence_log.md) §G5). And a recovery count is
not self-interpreting: against a *measured* untrained-network baseline, `diatomgraz` scores 0.640 with
no training at all, so its counts largely track its bounds rather than any observational constraint
(§G1, §G4).

Extending past the six is a scoping hypothesis and a multi-year follow-on direction, **not a
demonstrated capability**. This distinction matters most for the UDE proposal, where a learned closure
replaces one scalar with tens to hundreds of free weights: `ScavClosure` carries 67 free parameters
against `scav_rat`'s 1, and the calcite closure as actually run carries 353 against `R_PICPOC`'s 1.
The cost argument survives that substitution unchanged. The identifiability argument does not, and our
own stress test says why: a learned closure reached 0.0065 relative error on the DFe band the
trajectory visited and **2.877 on the full range**, identically across all four regularization
configurations, because a regularizer cannot manufacture information about states the trajectory never
enters (`docs/findings/ude_stress_2026-07-21/`).

Savelli et al. 2026 explicitly flagged the 100-day fixed DOC remineralization (`Kdop` in the source)
as a real limitation. Other parameters in the 94 % likely sit in the same shape: known to be uncertain
and plausibly important. Whether Green's functions leave them unreached because of **cost** or because
they are **unidentifiable** is not something we have measured. We have identifiability results for six
parameters and none for the other ~97, so this document should not assert either.

## Darwin 3 (v06/llc270) — also audited

Darwin 3 is the version used in the repo's `v05` and `v06` setups. It is a **major architectural rework** of Darwin 1: most parameters are now exposed via namelist files in `input_darwin/` rather than hardcoded in local `code_darwin/` source. The `code_darwin/` directory in v06/llc270 contains only headers (`DARWIN_OPTIONS.h`, `DARWIN_SIZE.h`, etc.); the kinetic source lives upstream in `MITgcm/pkg/darwin/`.

### Model dimensions (`v06/llc270/code_darwin/DARWIN_SIZE.h`)

- `nplank = 10` — total plankton types (was 5 phyto + 2 zoo = 7 in Darwin 1)
- `nGroup = 7` — functional groups: PicoCyano, PicoEuk, Cocco, Diazo, Diatom, Dino, Zoo
- `nPhoto = 6` — phototroph types
- `nopt = 12` — optical types
- `nlam = 1` — wavebands (RADTRANS not active in this build)

### Active compile-time flags

From `v06/llc270/code_darwin/DARWIN_OPTIONS.h` (174 lines):

- **Active** (21 flags): `DARWIN_ALLOW_CHLQUOTA`, `DARWIN_ALLOW_CDOM`, `DARWIN_ALLOW_CARBON`, `DARWIN_ALLOW_DENIT`, `DARWIN_BOTTOM_SINK`, `DARWIN_ALLOW_GEIDER`, `DARWIN_GEIDER_RHO_SYNTH`, `DARWIN_DIAG_IOP`, `DARWIN_TEMP_VERSION 4`, `DARWIN_MINFE`, `DARWIN_PART_SCAV`, `DARWIN_IRON_SED_SOURCE_VARIABLE`, `DARWIN_DIAG_PERTYPE`, `DARWIN_ALLOW_CONS`, `DARWIN_DIAG_TENDENCIES`, `DARWIN_ALLOW_RADIv2`, `DARWIN_NUTRIENT_RUNOFF`, `DARWIN_SOLVESAPHE`, `DARWIN_TOTALPHSCALE`, `DARWIN_ALLOW_HYDROTHERMAL_VENTS`, `DARWIN_CDOM_UNITS_CARBON`
- **Inactive** (21 flags): `DARWIN_ALLOW_NQUOTA`, `PQUOTA`, `FEQUOTA`, `SIQUOTA`, `EXUDE`, `NITRATE_FELIMIT`, `AVPAR`, `CHL_INIT_LEGACY`, `SCATTER_CHL`, `GRAZING_SWITCH`, `ALLOMETRIC_PALAT`, `NOZOOTEMP`, `NOTEMP`, `TEMP_RANGE`, `IRON_SED_SOURCE_POP`, `DEBUG`, `PART_SCAV_POP`, `RANDOM_TRAITS`, `TWO_SPECIES_SETUP`, `NINE_SPECIES_SETUP`, `ALLOW_DIAZ`

Notable: denitrification is **on** in Darwin 3 (was off in Carroll 2020), diazotrophy is still off, the Darwin 1 random-trait code path is fully replaced by the new allometric trait machinery.

### Verified tunable parameter counts (from namelists)

Read in full: `data.darwin` (267 lines) and `data.traits` (93 lines). Each namelist counted by listing every distinct LHS name.

| Namelist | Tunable parameter names | Total names | Notes |
|---|---|---|---|
| `&DARWIN_FORCING_PARAMS` | **20** | 71 | 12 input scaling factors (`darwin_inscal_*`) + 8 stoichiometric ratios for runoff (`R_*_runoff`). Excludes file paths, dates, periods, 3 boolean toggles. |
| `&DARWIN_INTERP_PARAMS` | 0 | 28 | Interpolation grid metadata only. |
| `&DARWIN_PARAMS` (kinetic core) | **29** | 37 | iron (8: `alpfe`, `freefemax`, `depthfesed`, `scav_tau`, `ligand_tot`, `scav_POC_wgt`, `scav_PSi_wgt`, `scav_PIC_wgt`), DOM remin (4: `kdoc`/`kdop`/`kdon`/`kdofe`), POM remin (5: `kPOC`/`kPOP`/`kPON`/`kPOFe`/`kPOSi`), sinking (6: `wC_sink`/`wN_sink`/`wP_sink`/`wFe_sink`/`wSi_sink`/`wPIC_sink`), plus `phygrazmin`, `hollexp`, `tempCoeffArr`, `PARmin`, `SURFDICMIN`, `SURFALKMIN`. Excludes 5 numerical-config (`darwin_chlIter0`, `darwin_pickupSuff`, `darwin_chlInitBalanced`, `darwin_seed`, `darwin_disscSelect`) and 1 dead (`diaz_ini_fac`, `ALLOW_DIAZ` undef). 2 more (`selectPHsolver`, `selectK1K2const`) are commented out. |
| `&DARWIN_CDOM_PARAMS` | **5** | 5 active | `fracCDOM`, `cdomdegrd`, `CDOMbleach`, `PARCDOM`, `CDOMcoeff`. 3 more (`R_NP_CDOM`, `R_FeP_CDOM`, `R_CP_CDOM`) commented out. |
| `&DARWIN_RADTRANS_PARAMS` | **10** (7 scalars + 3 array names) | 14 | scalar tunables: `darwin_Sdom`, `darwin_aCDOM_fac`, `darwin_part_size_P`, `darwin_rCDOM`, `darwin_RPOC`, `darwin_absorpSlope`, `darwin_bbbSlope`. 3 spectral arrays of 13 values each: `darwin_scatSwitchSizeLog`, `darwin_scatSlopeSmall`, `darwin_scatSlopeLarge`. Excludes 3 file paths and 1 boolean (`darwin_allomSpectra`). |
| `&DARWIN_RANDOM_PARAMS` | 0 | 0 | empty namelist |
| `&DARWIN_TRAIT_PARAMS` | **28** | 48 | excludes `grp_names` (identity), 16 group classification flags (`grp_nplank`, `grp_photo`, `grp_pred`, `grp_prey`, `grp_hasSi`, `grp_hasPIC`, `grp_DIAZO`, `grp_useNH4`, `grp_useNO2`, `grp_useNO3`, `grp_combNO`, `grp_bacttype`, `grp_aerobic`, `grp_denit`, `grp_tempMort`, `grp_tempMort2`, `grp_aptype`), and 2 boolean/select configs (`darwin_effective_ksat`, `darwin_select_kn_allom`). Most tunables are arrays at size `nGroup=7`, `nPhoto=6`, or `nplank=10`; some (e.g. `a_PCmax(1..6)`) are set per index. |
| `data.traits` `&DARWIN_TRAITS` | **8** | 8 | `EXPORTFRACMORT`, `EXPORTFRACMORT2`, `PALAT` (10×10 matrix), `ASSEFF` (10×10), `GRAZEMAX`, `EXPORTFRACPREYPRED` (10×10), `MORT`, `MORT2`. |

**Darwin 3 distinct tunable parameter names: exactly 100.**

| Counting basis | Count |
|---|---|
| Distinct tunable parameter names (across all namelists in `data.darwin` + `data.traits`) | **100** |
| Individual tunable values, arrays expanded over plankton, groups, and matrix dimensions | **657** |

Breakdown of the 657 individual values:

| Source | Values | How counted |
|---|---|---|
| `&DARWIN_FORCING_PARAMS` | 20 | 20 scalars × 1 |
| `&DARWIN_PARAMS` | 29 | 29 scalars × 1 |
| `&DARWIN_CDOM_PARAMS` | 5 | 5 scalars × 1 |
| `&DARWIN_RADTRANS_PARAMS` | 46 | 7 scalars + 3 arrays × 13 |
| `&DARWIN_TRAIT_PARAMS` | 207 | sum of array sizes per name (10+6+6+6+6+6+1+1+7+7+7+6+6+7+7+7+6+1+1+1+7+7+7+7+7+7+7+49) |
| `&DARWIN_TRAITS` | 350 | 10+10+100+100+10+100+10+10 |
| Total | **657** | |

### Architectural difference that matters for DarwinDiff

**Darwin 1**: parameters hardcoded in source (`code_darwin/`); each Green's functions experiment recompiles a different binary. Tunable knobs ≈ 103 scalars in `init_fixed.F`.

**Darwin 3**: parameters exposed via namelist files (`input_darwin/data.darwin`, `data.traits`). Tunable knobs ≈ 101 distinct names at the namelist level, with most being arrays. **No recompile needed to vary them.**

This means Darwin 3 is structurally a better target for DarwinDiff. Spatially-varying parameter learning (the DarwinDiff approach) would write per-cell parameter fields rather than per-class scalars; the namelist-driven architecture makes it cheaper to plug in MLP-predicted values without source modifications.

### Darwin 3 caveats not yet verified

- Default values for parameters NOT explicitly overridden in v06/llc270 namelists live upstream in `MITgcm/pkg/darwin/` source; that code is not in `MITgcm-contrib/ecco_darwin` and was not audited here. There may be additional parameters with literature defaults that the v06 setup inherits silently.
- The `&DARWIN_RADTRANS_PARAMS` namelist is read even though the active flag set does not include `ALLOW_RADTRANS` per the readme. Worth checking whether those parameters affect the v06 binary or are dead.

## Caveats

- Darwin 1 numbers are exact for the Carroll 2020 build (`v04/llc270_JAMES_paper`). All three key source files read line-by-line.
- Darwin 3 numbers are exact for the namelist content of v06/llc270 (`data.darwin`, `data.traits`). The upstream MITgcm `pkg/darwin/` source (where defaults live for unset parameters) was not audited.
- "Independent tunable" excludes derived equalities, dead-code parameters, unit conversions, identity classifications, file-path and date strings, and pure numerical-config parameters.
- "Tunable" is partly a judgment call. Stricter or looser definitions could shift the counts by ±10–20.

## Provenance

Audit performed 2026-05-02 via shallow clone of `MITgcm-contrib/ecco_darwin` (master branch).

- Darwin 1 (`v04/llc270_JAMES_paper/code_darwin/`): `DARWIN_OPTIONS.h` (111 lines), `DARWIN_SIZE.h` (131 lines), `darwin_init_fixed.F` (390 lines), `darwin_generate_phyto.F` (782 lines) all read in full. `darwin_plankton.F` (1711 lines) grep-scanned for top-level assignments.
- Darwin 3 (`v06/llc270/`): `code_darwin/DARWIN_OPTIONS.h` (174 lines), `code_darwin/DARWIN_SIZE.h` (34 lines), `input_darwin/data.darwin` (267 lines), `input_darwin/data.traits` (93 lines) all read in full.

Classifications cross-checked against `DARWIN_OPTIONS.h` `#ifdef` flags in each version. Temp clone deleted after audit; all numbers are reproducible by anyone running the same procedure.

---

## Appendix A — Darwin 1 (`darwin_init_fixed.F`) full parameter list

123 distinct named parameters total. Categories below sum to that.

**A.1 Independent active tunable scalars (103)**

*Light + attenuation (6):* `k0`, `kc`, `parfrac`, `chlpmax`, `chlpmin`, `istar`

*Iron cycle (11):* `alpfe` ★, `scav`, `ligand_tot`, `ligand_stab`, `freefemax`, `depthfesed`, `fesedflux`, `fesedflux_pcm`, `scav_rat` ★, `scav_inter`, `scav_exp`

*Nitrification + O₂ (4):* `O2crit`, `Knita`, `Knitb`, `PAR0`

*GEIDER growth scalars (4):* `Smallgrow` ★, `Biggrow` ★, `Smallgrowrange`, `Biggrowrange`

*GEIDER chlorophyll + quantum yield (8):* `smallchl2cmax`, `smallchl2cmaxrange`, `Bigchl2cmax`, `Bigchl2cmaxrange`, `smallmQyield`, `smallmQyieldrange`, `BigmQyield`, `BigmQyieldrange`

*Other phyto (2):* `aphy_chl_ave`, `inhibcoef_geid_val`

*Dynamic chlorophyll (1):* `acclimtimescl`

*Mortality + sinking scalars (8):* `Smallmort`, `Bigmort`, `Smallmortrange`, `Bigmortrange`, `Smallexport`, `Bigexport`, `SmallSink`, `BigSink`

*Temperature (8):* `tempcoeff1`, `tempcoeff2_small`, `tempcoeff2_big`, `tempcoeff3`, `tempmax`, `temprange`, `tempnorm`, `tempdecay`

*Phosphate half-saturation per phyto class (8):* `SmallPsat`, `BigPsat`, `ProcPsat`, `UniDzPsat`, `SmallPsatrange`, `BigPsatrange`, `ProcPsatrange`, `UniDzPsatrange`

*Other nutrient (8):* `ksatNH4fac`, `ksatNO2fac`, `sig1`, `sig2`, `sig3`, `ngrowfac`, `ilight`, `val_ksatsi`

*Elemental ratios — active (5):* `val_R_SiP_diatom`, `val_R_NP`, `val_RFeP`, `val_R_PC`, `val_R_PICPOC`

*Grazing (14):* `kgrazesat`, `phygrazmin`, `GrazeFast`, `GrazeSlow`, `GrazeEfflow`, `GrazeEffmod`, `GrazeEffhi`, `palathi`, `palatlo`, `diatomgraz` ★, `coccograz`, `olargegraz`, `ExGrazfracbig`, `ExGrazfracsmall`

*Zooplankton mortality + export (4):* `ZoomortSmall`, `ZoomortBig`, `ZooexfacSmall`, `ZooexfacBig`

*Phyto biomass threshold (1):* `phymin`

*DOM remineralisation (3):* `Kdop`, `Kdon`, `KdoFe`

*POM remineralisation + sinking, independent (3):* `Kpremin_P`, `Kpremin_Si`, `wp_sink`

*Carbon system, ALLOW_CARBON active (5):* `R_OP`, `Kdoc`, `Kpremin_C`, `Kdissc`, `wpic_sink`

★ = tuned by Carroll 2020 Green's functions (5 of 103 in `init_fixed.F`; the 6th `R_PICPOC` override lives in `generate_phyto.F:484`).

**A.2 Derived equalities (6)**

`Kpremin_N` (= `Kpremin_P`), `Kpremin_Fe` (= `Kpremin_P`), `wn_sink` (= `wp_sink`), `wfe_sink` (= `wp_sink`), `wsi_sink` (= `wp_sink`), `wc_sink` (= `wp_sink`).

**A.3 Dead in this build (11)**

- `ALLOW_DENIT` undef: `depthdenit`, `denit_np`
- `ALLOW_DIAZ` undef: `diaz_growfac`, `val_R_NP_diaz`, `val_RFeP_diaz`
- `ALLOW_MUTANTS` undef: `prochlPsat` (commented "used only for mutants")
- `DAR_DIAG_DIVER` undef: `diver_thresh0`, `diver_thresh1`, `diver_thresh2`, `diver_thresh3`, `diver_thresh4`

**A.4 Unit conversions / physical constants (3)**

`parconv` (W/m² → µEin), `permil` (1/1024.5, density conversion), `Pa2Atm` (Pa → atm).

## Appendix B — Darwin 1 (`darwin_generate_phyto.F`) hardcoded per-phyto identity traits

7 distinct trait arrays × 5 phyto types = **35 individual values**:

`physize(np)`, `phyto_esd(np)`, `phyto_vol(np)`, `diacoc(np)`, `diazotroph(np)`, `nsource(np)`, `ap_type(np)`.

Plus one inline Green's-functions override at line 484: `R_PICPOC(np) = 0.04245` for `np = 2, 3, 8` (only `np = 2, 3` valid since `npmax = 5`).

## Appendix C — Darwin 3 (`v06/llc270` namelists) full parameter list

100 distinct tunable parameter names total.

**C.1 `&DARWIN_FORCING_PARAMS` (20)**

`darwin_inscal_iron`, `darwin_inscal_ventHe3`, `darwin_inscal_DOCrunoff`, `darwin_inscal_DONrunoff`, `R_DOFe_DOP_runoff`, `darwin_inscal_DOPrunoff`, `R_NO3_DIN_runoff`, `R_NO2_DIN_runoff`, `R_NH4_DIN_runoff`, `darwin_inscal_DINrunoff`, `R_DFe_DIP_runoff`, `R_DIP_IP_runoff`, `darwin_inscal_IPrunoff`, `darwin_inscal_DSirunoff`, `darwin_inscal_POCrunoff`, `R_POFe_POP_runoff`, `darwin_inscal_POPrunoff`, `darwin_inscal_PONrunoff`, `R_ALK_DIC_runoff`, `darwin_inscal_DICrunoff`.

**C.2 `&DARWIN_PARAMS` (29)**

`tempCoeffArr`, `PARmin`, `alpfe`, `freefemax`, `depthfesed`, `scav_tau`, `ligand_tot`, `scav_POC_wgt`, `scav_PSi_wgt`, `scav_PIC_wgt`, `kdoc`, `kdop`, `kdon`, `kdofe`, `kPOC`, `kPOP`, `kPON`, `kPOFe`, `kPOSi`, `phygrazmin`, `hollexp`, `wC_sink`, `wN_sink`, `wP_sink`, `wFe_sink`, `wSi_sink`, `wPIC_sink`, `SURFDICMIN`, `SURFALKMIN`.

**C.3 `&DARWIN_CDOM_PARAMS` (5)**

`fracCDOM`, `cdomdegrd`, `CDOMbleach`, `PARCDOM`, `CDOMcoeff`.

**C.4 `&DARWIN_RADTRANS_PARAMS` (10)**

Scalars (7): `darwin_Sdom`, `darwin_aCDOM_fac`, `darwin_part_size_P`, `darwin_rCDOM`, `darwin_RPOC`, `darwin_absorpSlope`, `darwin_bbbSlope`.

Spectral arrays of 13 values each (3): `darwin_scatSwitchSizeLog`, `darwin_scatSlopeSmall`, `darwin_scatSlopeLarge`.

**C.5 `&DARWIN_TRAIT_PARAMS` (28)**

`a_R_PICPOC`, `a_Xmin`, `a_phytoTempAe`, `a_mQyield`, `a_chl2cmax`, `a_acclimtimescl`, `logvolbase`, `logvolinc`, `logvol0ind`, `a_biosink`, `b_biosink`, `a_PCmax`, `a_PCmax_denom`, `b_PCmax`, `a_Qpmin`, `a_Qpmax`, `grp_ExportFracPreyPred`, `a_R_ChlC`, `a_grazemax`, `b_grazemax`, `a_phytoTempExp2`, `a_R_PC`, `a_R_FeC`, `a_R_NC`, `a_R_SiC`, `a_kgrazesat`, `b_kgrazesat`, `grp_ass_eff`.

**C.6 `&DARWIN_TRAITS` from `data.traits` (8)**

`EXPORTFRACMORT`, `EXPORTFRACMORT2`, `PALAT`, `ASSEFF`, `GRAZEMAX`, `EXPORTFRACPREYPRED`, `MORT`, `MORT2`.

**C.7 Excluded from the 100 tunables (for the record)**

- *File paths, dates, periods (51 in `&DARWIN_FORCING_PARAMS`):* `ironFile`, `ironPeriod`, `pCO2File`, `pCO2startdate1`, `pCO2startdate2`, `pCO2period`, `ventHe3File`, `ventHe3Period`, the 12 runoff `*file`/`*startdate1`/`*startdate2`/`*period` quartets (48 names), `darwin_useEXFwind`, `darwin_useQsw`, `darwin_useSEAICE` (3 booleans).
- *Interpolation grid metadata (28 in `&DARWIN_INTERP_PARAMS`):* 10 `*_interpMethod` flags, 18 `lon0`/`lon_inc`/`lat0`/`lat_inc`/`nlon`/`nlat` for ventHe3, iron, pCO2.
- *Numerical config in `&DARWIN_PARAMS` (8):* `darwin_chlIter0`, `darwin_pickupSuff`, `darwin_chlInitBalanced`, `diaz_ini_fac` (dead, `ALLOW_DIAZ` undef), `darwin_seed`, `darwin_disscSelect`, plus 2 commented-out: `selectPHsolver`, `selectK1K2const`.
- *Commented-out CDOM stoichiometric ratios (3):* `R_NP_CDOM`, `R_FeP_CDOM`, `R_CP_CDOM`.
- *RADTRANS file paths + boolean (4):* `darwin_waterabsorbFile`, `darwin_phytoabsorbFile`, `darwin_particleabsorbFile`, `darwin_allomSpectra`.
- *TRAIT_PARAMS identity + classification (20):* `grp_names`, `grp_nplank`, `grp_photo`, `grp_pred`, `grp_prey`, `grp_hasSi`, `grp_hasPIC`, `grp_DIAZO`, `grp_useNH4`, `grp_useNO2`, `grp_useNO3`, `grp_combNO`, `grp_bacttype`, `grp_aerobic`, `grp_denit`, `grp_tempMort`, `grp_tempMort2`, `grp_aptype`, `darwin_effective_ksat`, `darwin_select_kn_allom`.
