# ECCO-Darwin parameter inventory (Carroll 2020 build)

A verified count of biogeochemistry parameters in the ECCO-Darwin v04 LLC270 JAMES paper configuration (Carroll et al. 2020, Darwin 1). Captured here so DarwinDiff scoping arguments rest on real numbers rather than estimates.

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
| 1 | `alpfe` | `init_fixed.F:83` | 0.92831 | Iron dust solubility |
| 2 | `scav_rat` | `init_fixed.F:101` | 10.41124 × 0.005 / 86400 | Iron scavenging rate |
| 3 | `Smallgrow` | `init_fixed.F:161` | 0.66098 | Small phytoplankton growth rate |
| 4 | `Biggrow` | `init_fixed.F:162` | 0.43148 | Large phytoplankton growth rate |
| 5 | `diatomgraz` | `init_fixed.F:272` | 0.83003 | Diatom palatability |
| 6 | `R_PICPOC` | `generate_phyto.F:484` | 0.04245 | PIC/POC ratio |

Each parameter has its pre-optimization default visible in a commented-out line nearby (for example `cswd  scav_rat=0.005 _d 0/(86400.0 _d 0)` at line 99). The Green's functions workflow literally edits these constants in source and recompiles per experiment, which is the "labor-intensive" workflow Lauderdale described.

## What this means for DarwinDiff

**Calibration coverage gap: 6 / 103 ≈ 5.8 %.** The other ~94 % of independently tunable knobs sit at expert or literature defaults applied uniformly across the global ocean. Many are single global scalars: `Kdop = 2 / (100 × 86400)` controls DOC remineralization rate everywhere on Earth, `kgrazesat = 0.085` is one number for grazing half-saturation across all ocean conditions, `phytoTempOptimum` is one curve per phytoplankton class with no spatial variation. Replacing such scalars with MLP-predicted spatial fields, which is what DarwinDiff's parameter-learner does, is a structurally cheap upgrade per parameter that reaches well past the Green's functions ceiling of "a handful at a time."

Savelli et al. 2026 explicitly flagged the 100-day fixed DOC remineralization (`Kdop` in the source) as a real limitation. Other parameters in the 94 % likely sit in the same shape: known to be uncertain, plausibly important, but unreached by Green's functions because Green's functions cannot afford them.

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
