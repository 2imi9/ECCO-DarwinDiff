# Data

Local data cache. Contents are gitignored — fetch separately before running anything. Notebook 09+ assume the files below are present.

All datasets are pulled from their canonical hosts and live OUTSIDE the repo. Paths are configured via env vars (`DARWIN_DATA_ROOT`, `GLODAP_DATA_ROOT`, …) — see `darwindiff.ecco_darwin_loader` for defaults. Hugging Face is bookmarked for our derived artifacts (trained model weights, processed AOI subsets, results CSV) at v3.0 stabilization, NOT for raw third-party data.

## Sources

### Primary — in active use (notebooks 09–29)

- **ECCO-Darwin v05 `bin_average` 1° NetCDF** — surface diagnostics from the Carroll 2022 (GBC) calibrated v05 run. Single 1.74 GB NetCDF, 23 yr monthly (Jan 1995 – Dec 2017). Variables include `CO2_flux`, `pCO2`, `apCO2`, `mldDepth`, `SST`, `SSS`, `windSpeed`, `seaIceArea`, `Chl1`–`Chl5` (per-PFT chlorophyll). Used by notebooks 10–29 as both target (Chl, FeT, POC, PIC, DIC, ALK) and covariate input (SST, MLD, wind).
  - **Jon's canonical URL** (authoritative): <https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC90/ECCO-Darwin/>
  - NAS mirror (what we used in 2026-05): <https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/v05_ECCO-Darwin_bin_average_1x1_deg.nc>
  - Public, no Earthdata auth required. Single `curl` / `wget` download.
  - Loader: `darwindiff.ecco_darwin_loader.open_bin_average`.

- **ECCO-Darwin v05 native LLC270 monthly tracers** — depth-resolved BGC tracer fields in MITgcm mds binary tile format (`.data` + `.meta` sidecars). One subdirectory per tracer (`ALK/`, `DIC/`, `NO3/`, `FeT/`, etc.); each tracer is ~50 GB across ~600 monthly snapshots × 50 depth levels × 13 LLC270 tiles. ~1.9 TB total on disk for ~30 tracers. Used by notebooks 13, 14, 15, 16 as fit targets.
  - **Jon's canonical URL** (authoritative): <https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/ECCO-Darwin_extension/>
  - NAS mirror (what we used): <https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/>
  - Public; recursive `wget -r -np` works. Total ~1+ TB if you pull every tracer. Earthdata creds optional (recommended for token-based auth on large multi-file downloads). Some tracers (`Chl1/`, `CO2_flux/`) only had 2 files in the NAS mirror as of 2026-05 — re-pull from Jon's canonical JPL URL if needed.
  - Loader: `darwindiff.llc270_loader.open_llc270_tracer` (xmitgcm-based). Requires `xmitgcm` package.

- **LLC270 grid metadata** — companion to the monthly tracers; xmitgcm needs the grid for proper geometry. ~494 MB.
  - NAS mirror: <https://data.nas.nasa.gov/ecco/llc_270/grid/>
  - Public.

- **GLODAPv2.2016b mapped climatology** — 1°×1° gridded BGC (DIC, alkalinity, NO₃, PO₄, Si, oxygen, salinity, temperature). 213 MB tarball, ~1.4 GB extracted, 14 NetCDFs. Used by notebook 22 (PR #36, the v2.1 Phase 1 hybrid fit). **Jon's email recommends GLODAPv2.2023** — 7 yrs newer with recalibration. Upgrade is a planned refinement (see Planned section below).
  - Source: NOAA NCEI accession 0162565, <https://glodap.info>
  - Public, no auth.
  - Loader: `darwindiff.glodap_loader` (cherry-picked into both PR #36 and PR #37 by design).

### Planned integrations (Jon's email 2026-05-11)

These datasets are on the roadmap. Each unblocks a specific limitation of the current 4/6 calibration-grade result. URLs are decoded from Jon's `.eml` and recorded in `memory/reference_training_datasets.md`.

| # | Dataset | Canonical URL | Unblocks | Priority |
|---|---|---|---|---|
| 1 | **GEOTRACES IDP2025** — iron + co-measured nutrients/DIC/ALK, depth-resolved bottle data via DOI `10.5285/42c92148-8d03-8be6-e063-7086abc09f0c` | <https://www.geotraces.org/idp2025/> | **alpfe** (confirmed structurally stuck at 0.80–0.94 off Carroll across 25 experiments incl. Wave 3 follow-ups; raw_fet w=0.01 moved it to 0.392 but broke scav_rat; PINN drift cancels the raw_fet effect — classic identifiability degeneracy needs an absolute-units iron observation to fix) | **Loader landed in PR #39** (`src/darwindiff/geotraces_loader.py`, tests in `tests/test_geotraces_loader.py`, fetch helper at `scripts/fetch/geotraces.sh`). Data not yet on disk. |
| 2 | **GLODAPv2.2023** (merged + mapped) — 7 yrs newer than the v2.2016b we currently use | merged: <https://glodap.info/index.php/merged-and-adjusted-data-product-v2-2023/> · mapped: <https://glodap.info/index.php/mapped-data-product/> | Refines the carbonate signal in nb22-style hybrid fits | Step 2 (low-risk refinement) |
| 3 | **Ocean color** — PFT-resolved Chl via remote sensing; Jon did NOT link a specific source ("we could also think about bringing in ocean color"). Likely NASA OB.DAAC or ESA OC-CCI for PFT decomposition | NASA OB.DAAC: <https://oceancolor.gsfc.nasa.gov/> (user-suggested; ask Jon to confirm) | **Smallgrow** target ambiguity — gives Pro-HL-specific Chl independent of Carroll's group-mean 0.661 | Step 3 |
| 4 | **BGC-Argo** — autonomous floats with depth-resolved BGC profiles (upper ~1 km) | <https://biogeochemical-argo.org/data-access.php> | Wave 4 (time-resolved fitting + depth structure). `argopy` Python client already in deps | Step 4 |
| 5 | **SOCAT 2025** — Surface Ocean CO₂ Atlas (carbon, alkalinity, pH at surface, high spatial/temporal coverage) | <https://socat.info/index.php/version-2025/> | Refines surface CO₂ flux loss term; mostly overlaps with GLODAP for our purposes | Step 5 |
| 6 | **WOD** (raw bottle) — T/S, nutrients, oxygen | <https://www.ncei.noaa.gov/products/world-ocean-database> | Background; T/S forcing mostly covered by bin_average | Step 6 |
| 7 | **WOA** (gridded climatology) — Jon noted monthly nutrient products limited to upper few hundred metres, full-depth only annual | <https://www.ncei.noaa.gov/products/world-ocean-atlas> | Background; only WOA23 winter SST currently on disk | Step 7 |

### Secondary — on disk but not in active use

- **NASA GHG Center ECCO-Darwin v5 air–sea CO₂ flux GeoTIFFs** — 36 monthly Cloud Optimized GeoTIFFs covering Jan 2020 – Dec 2022, ~285 MB total. Same v05 run as `bin_average`, only the CO₂ flux derivative variable. Useful for future CO₂-flux validation.
  - Source: <https://earth.gov/ghgcenter/data-catalog/eccodarwin-co2flux-monthgrid-v5>
  - Public, no auth.

- **WOA23 winter SST climatology** — 0.25° gridded SST, 1.1 GB. Held locally as a fallback/comparison source.
  - Source: <https://www.ncei.noaa.gov/products/world-ocean-atlas>
  - Public.

### Reference (model setup, not output)

- **MITgcm-contrib `ecco_darwin` source** — Darwin source code repository. Cloned to `references/ecco_darwin/` (gitignored). Used to verify the v04 (Carroll 2020) ↔ v05 (Carroll 2022) parameter inheritance and to read namelist values directly. Not used at runtime.
  - Source: <https://github.com/MITgcm-contrib/ecco_darwin>

- **Jon's `xesmf` LLC→regular-lat-lon regridding workflow** — Jon offered to share when needed. Not yet requested.

## Local layout

The `data/` directory is gitignored apart from this README and `.gitkeep`. Files larger than a few hundred MB live outside the repo entirely (e.g. on a separate drive); see `memory/reference_training_datasets.md` for the canonical local paths used during development on Lucas's machine.

`DARWIN_DATA_ROOT` env var override is the supported way to point at a different cluster path — see notebooks 22+ for the pattern, and `scripts/phase2_p4_p5_check.py` (post-`7d24791` fix) for the canonical Linux/Windows-portable form.

## Hosting decision (why not GitHub or HuggingFace for raw data)

- **GitHub** size limits (100 MB single-file, ~1 GB repo warning) make it unusable for our 1.7+ TB total. `.gitignore` rules in this repo enforce that data never accidentally lands in git.
- **Hugging Face** would technically fit the larger files but raw third-party data should not be mirrored: licensing/redistribution policies (GEOTRACES especially), canonical-source citation expectations, and version drift all argue against it. HF is the right home for our DERIVED artifacts at v3.0+ (trained model weights, the 22-experiment results CSV, AOI-trimmed processed subsets) — NOT for raw upstream data.

## Notes

- **ECCO-Darwin v04 ↔ v05 inheritance**: v04 (Carroll 2020, JAMES) and v05 (Carroll 2022, GBC) use bit-identical Carroll-6 calibrated values; see `STATUS.md` finding 1. We standardize on v05 because it's the publicly-accessible output.
- **Jon's service-down note** (2026-05-11) referred to the JPL `ecco.jpl.nasa.gov/drive` host. The NAS mirror at `data.nas.nasa.gov` was used as a fallback for the initial bulk download.
- **Notebooks 17 (per-seed ensemble) on**: per-seed checkpoints (`notebooks/nb17_results/seedA_*.npz`, `seedB_*.npz`) are gitignored — regeneratable from the owning notebook. Summary JSONs and figures ARE committed.
