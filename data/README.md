# Data

Local data cache. Contents are gitignored — fetch separately before running anything. Notebook 09+ assume the files below are present.

## Sources

### Primary — used by current notebooks (09–16)

- **ECCO-Darwin v05 `bin_average` 1° NetCDF** — surface diagnostics from the Carroll 2022 (GBC) calibrated v05 run. Single 1.74 GB NetCDF, 23 yr monthly (Jan 1995 – Dec 2017), variables include `CO2_flux`, `pCO2`, `apCO2`, `mldDepth`, `SST`, `SSS`, `windSpeed`, `seaIceArea`, `Chl1`–`Chl5` (per-PFT chlorophyll). Used by notebooks 10, 11, 14, 15, 16 as both target (Chl) and covariate input (SST, MLD, wind).
  - Source: <https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/v05_ECCO-Darwin_bin_average_1x1_deg.nc>
  - Public, no Earthdata auth required. Single `curl` / `wget` download.
  - Loader: `darwindiff.ecco_darwin_loader.open_bin_average`.

- **ECCO-Darwin v05 native LLC270 monthly tracers** — depth-resolved BGC tracer fields in MITgcm mds binary tile format (`.data` + `.meta` sidecars). One subdirectory per tracer (`ALK/`, `DIC/`, `NO3/`, `FeT/`, etc.); each tracer is ~50 GB across ~290 monthly snapshots × 50 depth levels × 13 LLC270 tiles. Used by notebooks 13, 14, 15, 16 as fit targets (NO₃, FeT, etc.).
  - Source: <https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/>
  - Public; recursive `wget -r -np` works. Total ~1+ TB if you pull every tracer. Earthdata creds optional (recommended for token-based authentication on large multi-file downloads).
  - Loader: `darwindiff.llc270_loader.open_llc270_tracer` (xmitgcm-based). Requires `xmitgcm` package.

- **LLC270 grid metadata** — companion to the monthly tracers; xmitgcm needs the grid for proper geometry. ~494 MB.
  - Source: <https://data.nas.nasa.gov/ecco/llc_270/grid/>
  - Public.

- **GLODAPv2.2016b mapped climatology** — 1°×1° gridded BGC (DIC, alkalinity, NO₃, PO₄, Si, oxygen, salinity, temperature). 213 MB tarball, ~1.4 GB extracted, 14 NetCDFs. Used by notebook 09 (real-data methodology demo before we had ECCO-Darwin v5 access).
  - Source: NOAA NCEI accession 0162565, <https://glodap.info>
  - Public, no auth.

### Secondary — relevant but not in active use

- **NASA GHG Center ECCO-Darwin v5 air–sea CO₂ flux GeoTIFFs** — 36 monthly Cloud Optimized GeoTIFFs covering Jan 2020 – Dec 2022, ~285 MB total. Same v05 calibrated run as the bin_average product, but only the CO₂ flux derivative variable. Useful for future CO₂-flux validation once the box model is extended with carbonate chemistry.
  - Source: <https://earth.gov/ghgcenter/data-catalog/eccodarwin-co2flux-monthgrid-v5>
  - Public, no auth.

- **WOA23 winter SST climatology** — 0.25° gridded sea surface temperature, 1.1 GB. Held locally as a fallback/comparison source; not used by current notebooks.
  - Source: <https://www.ncei.noaa.gov/products/world-ocean-atlas>
  - Public.

### Reference (model setup, not output)

- **MITgcm-contrib `ecco_darwin` source** — the Darwin source code repository. Cloned to `references/ecco_darwin/` (gitignored, see `references/README.md`). Used to verify the v04 (Carroll 2020) ↔ v05 (Carroll 2022) parameter inheritance and to read namelist values directly. Not used at runtime.
  - Source: <https://github.com/MITgcm-contrib/ecco_darwin>

## Local layout

The data directory is gitignored apart from this README and `.gitkeep`. Files larger than a few hundred MB live outside the repo entirely (e.g. on a separate drive); see project memory for the canonical local paths used during development.

## Notes

- ECCO-Darwin v05 is the publicly-accessible Carroll 2022 calibrated run on the LLC270 grid. v04 (Carroll 2020) inherits the same 6-parameter calibration values bit-for-bit (verified from source); we standardize on v05 because it's the publicly-accessible output. See `STATUS.md` for the project's framing decision.
- SOCAT and BGC-Argo are not in current use. Earlier project plans listed them; current notebooks (09–16) get all observations from the Darwin v05 outputs above. Future work (notebook 17+) may revisit sparse-observation sources.
