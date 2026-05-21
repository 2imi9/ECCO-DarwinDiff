# Data

Local data cache. All contents gitignored; fetch separately. Loaders in `src/darwindiff/` resolve paths via env vars (`DARWIN_DATA_ROOT`, `GLODAP_DATA_ROOT`); see `darwindiff.ecco_darwin_loader` for defaults.

Raw third-party data is never mirrored to GitHub or Hugging Face. Hosting decision rationale at the bottom.

## Active datasets

### ECCO-Darwin v05 — surface diagnostics (1° NetCDF)

Surface fields from the Carroll 2022 (GBC) calibrated v05 run. Single 1.74 GB NetCDF, monthly 1995–2017.

| Property | Value |
|---|---|
| Variables | `CO2_flux`, `pCO2`, `apCO2`, `mldDepth`, `SST`, `SSS`, `windSpeed`, `seaIceArea`, `Chl1`–`Chl5` |
| Canonical URL | https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC90/ECCO-Darwin/ |
| NAS mirror | https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/v05_ECCO-Darwin_bin_average_1x1_deg.nc |
| Auth | None |
| Loader | `darwindiff.ecco_darwin_loader.open_bin_average` |

### ECCO-Darwin v05 — native LLC270 monthly tracers

Depth-resolved BGC tracers in MITgcm mds binary tile format (`.data` + `.meta`). One subdirectory per tracer. Each tracer ≈ 50 GB across ~600 monthly snapshots × 50 depth levels × 13 LLC270 tiles. ~1.9 TB total for ~30 tracers.

| Property | Value |
|---|---|
| Canonical URL | https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/ECCO-Darwin_extension/ |
| NAS mirror | https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/ |
| Auth | Optional Earthdata token (recommended for bulk transfers) |
| Loader | `darwindiff.llc270_loader.open_llc270_tracer` (xmitgcm) |

The companion **LLC270 grid metadata** (~494 MB) is required by xmitgcm and lives at https://data.nas.nasa.gov/ecco/llc_270/grid/.

### GLODAPv2.2016b — mapped climatology

1°×1° gridded BGC (DIC, alkalinity, NO₃, PO₄, Si, O₂, S, T). 213 MB tarball, ~1.4 GB extracted, 14 NetCDFs.

| Property | Value |
|---|---|
| Source | NOAA NCEI accession 0162565, https://glodap.info |
| Auth | None |
| Loader | `darwindiff.glodap_loader` |

### GEOTRACES IDP2025 — iron and co-measured BGC bottle data

Depth-resolved bottle data including dissolved iron, nutrients, DIC, ALK.

| Property | Value |
|---|---|
| DOI | `10.5285/42c92148-8d03-8be6-e063-7086abc09f0c` |
| Source | https://www.geotraces.org/idp2025/ |
| Auth | Registration required (free) |
| Loader | `src/darwindiff/geotraces_loader.py`, tests in `tests/test_geotraces_loader.py`, fetch helper at `scripts/fetch/geotraces.sh` |

### NASA GHG Center — ECCO-Darwin v5 air–sea CO₂ flux GeoTIFFs

36 monthly Cloud Optimized GeoTIFFs, 2020–2022, ~285 MB total. Same v05 run as the bin_average product; CO₂ flux only.

| Property | Value |
|---|---|
| Source | https://earth.gov/ghgcenter/data-catalog/eccodarwin-co2flux-monthgrid-v5 |
| Auth | None |
| Use | CO₂ flux validation |

### WOA23 — winter SST climatology

0.25° gridded SST, 1.1 GB. Fallback / comparison source.

| Property | Value |
|---|---|
| Source | https://www.ncei.noaa.gov/products/world-ocean-atlas |
| Auth | None |

## Planned integrations

Each unblocks a specific limitation of current results. Listed in priority order.

| Dataset | Source | Unblocks |
|---|---|---|
| **GLODAPv2.2023** (merged + mapped) | merged: https://glodap.info/index.php/merged-and-adjusted-data-product-v2-2023/ · mapped: https://glodap.info/index.php/mapped-data-product/ | Refines carbonate signal in hybrid fits; recalibrated against v2.2016b |
| **Ocean color** (PFT-resolved Chl) | NASA OB.DAAC https://oceancolor.gsfc.nasa.gov/ · ESA OC-CCI | `Smallgrow` target ambiguity (Pro-HL-specific Chl independent of Carroll's group-mean) |
| **BGC-Argo** (depth-resolved profiles) | https://biogeochemical-argo.org/data-access.php | Time-resolved + depth-resolved fitting (`argopy` Python client in deps) |
| **MODIS-Aqua PIC** | NASA OB.DAAC | Shelved with v3.1 leapfrog phase. Loader at `src/darwindiff/modis_pic_loader.py`. |
| **PACE carbon_phyto** | NASA OB.DAAC | Shelved with v3.1 leapfrog phase. Loader at `src/darwindiff/pace_loader.py`. |
| **SOCAT 2025** (Surface Ocean CO₂ Atlas) | https://socat.info/index.php/version-2025/ | Refines surface CO₂ flux loss term |
| **WOD** (raw bottle T/S, nutrients, O₂) | https://www.ncei.noaa.gov/products/world-ocean-database | Background forcing |
| **WOA** (gridded climatology) | https://www.ncei.noaa.gov/products/world-ocean-atlas | Background; monthly nutrient products limited to upper few hundred metres |

## Reference (not data — model setup)

- **MITgcm-contrib `ecco_darwin` source** — Darwin source code. Cloned to `references/ecco_darwin/` (gitignored). Used to verify v04 ↔ v05 parameter inheritance and read namelist values. Not used at runtime. Source: https://github.com/MITgcm-contrib/ecco_darwin.

## Local layout

The `data/` directory is gitignored apart from this README and `.gitkeep`. Files >100 MB live outside the repo entirely (typically on a separate drive); set `DARWIN_DATA_ROOT` / `GLODAP_DATA_ROOT` env vars to your local paths. Loaders are Linux/Windows-portable.

## Hosting decision (why not GitHub or Hugging Face for raw data)

- **GitHub** size limits (100 MB single-file, ~1 GB repo warning) make it unusable for the ~1.7 TB total. `.gitignore` enforces this.
- **Hugging Face** would technically fit the larger files but raw third-party data should not be mirrored: licensing/redistribution policies (GEOTRACES especially), canonical-source citation expectations, version drift. Hugging Face is the right home for *derived* artifacts (trained model weights, processed AOI subsets, results CSVs) when the project hits a publishable milestone — never for raw upstream data.

## Notes

- **v04 ↔ v05 parameter inheritance.** ECCO-Darwin v04 (Carroll 2020, JAMES) and v05 (Carroll 2022, GBC) use bit-identical Carroll-6 calibrated values. The project standardizes on v05 because it is the publicly-accessible output.
- **Per-seed checkpoint artifacts** (`notebooks/nb17_results/seedA_*.npz`, `seedB_*.npz`) are gitignored and regeneratable from the owning notebook. Summary JSONs and figures are committed.
