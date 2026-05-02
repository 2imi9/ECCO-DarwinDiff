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
| Hardcoded per-phyto identity traits (`physize`, `phyto_esd`, `phyto_vol`, `diacoc`, `diazotroph`, `nsource`, `ap_type` × 5 types) | ~35 | `darwin_generate_phyto.F` |
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

## Caveats

- Numbers are for **Darwin 1**, the version used by Carroll 2020 (`v04` in the repo).
- The repo's `v05` and `v06` use **Darwin 3**, a major rework with restructured parameters. Likely a similar order of magnitude, but counts have not been verified separately.
- "Independent tunable" excludes derived equalities, dead-code parameters, unit conversions, and per-phyto identity classifications.
- "Tunable" is partly a judgment call (what counts as scientifically meaningful to tune). Stricter or looser definitions could shift the 103 by ±10–20.

## Provenance

Audit performed 2026-05-02 via shallow clone of `MITgcm-contrib/ecco_darwin` (master branch). All four source files above read in full or grep-scanned for assignments. Classifications cross-checked against `DARWIN_OPTIONS.h` `#ifdef` flags. Temp clone deleted after audit; numbers are reproducible by anyone running the same procedure.
