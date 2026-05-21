---
name: darwin-v05-loader
description: >
  Load ECCO-Darwin v05 outputs for a given Area of Interest (AOI), build
  initial-condition caches from Darwin pickup files, and build time-averaged
  target caches for parameter-recovery comparison. Use when working with
  ECCO-Darwin v05 fields (PIC, POC, DIC, DFe, Chl1-5, etc.), setting up a new
  AOI for forward/inverse modeling, building IC caches needed by Carroll-6
  parameter recovery, or comparing Darwin output to GLODAP/GEOTRACES/SOCAT
  observations. Triggers: "load Darwin v05", "build IC cache", "define new
  AOI", "ECCO-Darwin output", "Darwin pickup file", "subset v05 to region".
---

# ECCO-Darwin v05 Loader

Wraps `src/darwindiff/ecco_darwin_loader.py` so researchers can pull Darwin
v05 outputs, define new AOIs, and build the IC + target caches that
parameter-recovery workflows (DINN, Green's-functions, hybrid PINN) expect.

## What is ECCO-Darwin v05?

ECCO-Darwin is a global ocean biogeochemistry (BGC) simulation produced by
MIT (Carroll et al. 2020 JAMES, 2022 GBC). Version 05 covers 1992–2020 at
LLC270 resolution (~1/3 degree), monthly-averaged. Outputs include:

- **Tracers**: PIC, POC (1 + 2-layer), DIC, alkalinity, DFe, NO3, PO4, SiO3,
  O2, DOC, DON, DOP, DOFe
- **Plankton (5 PFT)**: pro-low-light, pro-high-light, syn, diatom (with chl
  per PFT), lge-eukaryote
- **Physics**: SST, SSS, MLD, wind speed, ice fraction

Default data root on this machine: `D:\ecco_darwin_v5\`. Set via
`DARWIN_DATA_ROOT` env var.

## Available AOIs (canonical)

Defined in `AOI_BY_KEY` (src/darwindiff/ecco_darwin_loader.py):

| Key | Region | Lat / Lon |
|---|---|---|
| `eqpac` | Equatorial Pacific (HNLC, iron-limited) | 5°S–5°N / 180°–250°E |
| `natlsubpolar` | North Atlantic subpolar (deep mixing, iron-replete) | 45°–60°N / 295°–340°E |
| `southernoceanpac` | Southern Ocean Pacific sector | 60°–45°S / 180°–270°E |
| `narrowL2` | Narrow Eq Pacific test slice | (smaller box for fast iteration) |

For a new AOI, define a `bbox = (lat_min, lat_max, lon_min, lon_max)` and
add to `AOI_BY_KEY`.

## Common workflows

### 1. Load Darwin v05 fields for an AOI

```python
from darwindiff.ecco_darwin_loader import (
    AOI_BY_KEY, open_bin_average, subset_aoi, time_mean
)

aoi = AOI_BY_KEY["eqpac"]
# open monthly fields, time-average, subset to AOI
mean_2d = open_bin_average("PIC", year_start=2015, year_end=2017)
pic_eqpac = subset_aoi(mean_2d, aoi)  # shape: (lat, lon) in AOI bbox
```

### 2. Build an IC cache for a new AOI

IC cache = initial conditions sampled from a Darwin pickup file at the AOI's
ocean cells. Required by parameter-recovery training so the model starts
from realistic state.

```bash
# CACHE_NAME determines the output file; DARWIN_AOI keys AOI_BY_KEY.
CACHE_NAME=darwin_ic_cache_<aoi>.npz \
DARWIN_AOI=<aoi_key> \
python scripts/build_darwin_ic_cache.py
```

Result: `scripts/darwin_ic_cache_<aoi>.npz` with all tracer ICs at AOI cells.

### 3. Build a target cache

Target cache = time-averaged Darwin v05 outputs at the AOI, used as the
"truth" against which a DINN is calibrated. Lives at:
`D:\ecco_darwin_v5\cache\eqpac_targets_<aoi_descriptor>.pt`

Built lazily by `run_v3.0_with_modis_pic.py` and `run_v3.0_joint_multi_aoi.py`
on first use; subsequent runs hit the cache.

### 4. Add a new AOI

1. Add bbox to `AOI_BY_KEY` in `src/darwindiff/ecco_darwin_loader.py`.
2. Add IC cache name to `IC_CACHE_NAME` dict in
   `scripts/run_v3.0_with_modis_pic.py` and `scripts/run_v3.0_joint_multi_aoi.py`.
3. Build IC cache (see workflow 2).
4. First training run lazily builds the target cache.

## Reference files

- `src/darwindiff/ecco_darwin_loader.py` — AOI defs, subset utilities, time-averaging
- `scripts/build_darwin_ic_cache.py` — IC cache builder
- `scripts/run_v3.0_joint_multi_aoi.py` — example consumer (joint 2-AOI)
- `scripts/run_v3.0_with_modis_pic.py` — example consumer (3-AOI + optional satellite)

## Reference data sources

- ECCO-Darwin v05 product description:
  https://github.com/darwinproject/darwin3 (the model source)
- Carroll et al. 2022 (GBC): https://doi.org/10.1029/2021GB007162
- Carroll et al. 2020 (JAMES): https://doi.org/10.1029/2020MS002390

## Common gotchas

- **Pickup files** are large (~30 GB per snapshot). Build IC cache once per
  AOI; don't load pickup from scratch each run.
- **GEOTRACES POC + bSi** in-AOI bin counts can be 0 for some regions (e.g.
  Southern Ocean Pacific has no GEOTRACES POC). Use Darwin POC anchor
  (`POC_ABS_W`) instead.
- **Path length on Windows**: filename tags can exceed MAX_PATH=260 when
  multiple lever tags accumulate. Use short OUTPUT_DIR prefixes (e.g.
  `D:\runs\bcr_<stamp>\`).
- **Target cache filenames** all start with `eqpac_targets_` regardless of
  AOI — that's a historical naming quirk; the AOI is in the suffix.
