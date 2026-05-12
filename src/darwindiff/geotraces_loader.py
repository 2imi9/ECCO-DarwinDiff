"""Loader for the GEOTRACES IDP2025 discrete-bottle iron observations.

GEOTRACES IDP (Intermediate Data Product) is the authoritative compilation
of trace-element observations from research cruises worldwide. IDP2025 is
the latest release (June 2025), containing 23,912 dissolved iron values
across the global ocean — the **absolute-units, depth-resolved iron data**
that resolves the alpfe ↔ scav_rat identifiability degeneracy left
unresolved by the v2.2 closeout.

**Why GEOTRACES specifically.** Across 22 v2.2 experiments + 3 Wave 3
follow-ups (2026-05-12), ``alpfe`` sat at 0.80–0.94 off Carroll regardless
of loss design — except one configuration (``raw_fet w=0.01`` standalone)
which moved alpfe to 0.392 but broke scav_rat to 2.556. The structural
explanation: z-scored FeT loss normalizes away the absolute iron
magnitude that alpfe controls (dust solubility coefficient × atmospheric
dust flux). Adding GEOTRACES iron in absolute units (nmol/kg) as an
additional loss term ties the recovered DFe field to a real scale,
breaking the alpfe-scav_rat degeneracy without sacrificing one for the
other.

**Data product.** IDP2025 distributes in ASCII, NetCDF (ODV), and Ocean
Data View collection formats via DOI ``10.5285/42c92148-8d03-8be6-e063-7086abc09f0c``.
We use the NetCDF ODV format because it preserves the discrete-bottle
schema (irregular cruise stations at lat/lon/depth/time), unit metadata,
and per-cruise provenance the ASCII tables strip.

**Format.** Unlike GLODAP's regular 1°×1° gridded climatology, GEOTRACES
bottle data is **discrete and irregular**: each row is one bottle sample
on one cruise at one (lat, lon, depth, time). For DarwinDiff's
AOI-on-regular-grid fits, this loader provides three layers:

    1. ``open_geotraces_bottle``   — raw discrete dataset, all stations.
    2. ``subset_aoi_geotraces``    — filter to an AOI lat/lon box.
    3. ``bin_to_grid``             — bin discrete observations to a 1°
                                     regular grid for AOI-compatible fits.

**Variable naming.** GEOTRACES uses ``<Param>_<Type>_CONC_<Phase>``:

    Fe_D_CONC_BOTTLE   — Dissolved Fe from bottle samples (nmol/kg)
    Fe_T_CONC_BOTTLE   — Total Fe from bottle samples (nmol/kg)
    Fe_S_CONC_BOTTLE   — Soluble Fe from filtered bottle samples
    Fe_TP_CONC_PUMP    — Total particulate Fe from pump samples

Only dissolved Fe (``Fe_D_CONC_BOTTLE``) is mapped here at v2.5; other
phases can be added when the v2.6+ loss extends to particulate iron.

**Unit convention.** GEOTRACES reports concentrations as **nmol per kg
of seawater**. DarwinDiff's box model uses **mmol per m³**. Conversion at
surface seawater density (ρ_sw ≈ 1025 kg/m³):

    1 nmol/kg = 1e-6 mmol/kg × 1025 kg/m³ = 1.025 × 10⁻³ mmol/m³

Or equivalently multiply GEOTRACES by ``RHO_SW * 1e-6`` to get our
internal units. Same ``RHO_SW`` constant as ``darwindiff.glodap_loader``
and ``darwindiff.carbonate``, kept in sync deliberately.

**Schema assumptions.** The loader is built against the documented GEOTRACES
IDP variable-naming conventions (IDP2014/2017/2021/2025). The schema may
be refined in v2.5.1 once IDP2025 NetCDFs are on disk and the exact
variable names + coordinate conventions are confirmed against the data.
Tests use a synthetic fixture matching the documented schema; the opt-in
``test_real_idp2025_iron`` test gates on the real download to validate
against actual bytes.

Source: GEOTRACES Standards and Intercalibration Committee, IDP2025
        https://www.geotraces.org/idp2025/
        DOI: 10.5285/42c92148-8d03-8be6-e063-7086abc09f0c
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI

# Friendly DarwinDiff name → GEOTRACES IDP variable name. Add new phases
# as the loss surface extends. Names follow the standard IDP naming
# convention; verify against the actual IDP2025 NetCDF metadata when the
# data is downloaded.
GEOTRACES_VAR_MAP: dict[str, str] = {
    "Fe_D":  "Fe_D_CONC_BOTTLE",   # Dissolved iron, nmol/kg — alpfe target
    "Fe_T":  "Fe_T_CONC_BOTTLE",   # Total iron, nmol/kg
    "Fe_S":  "Fe_S_CONC_BOTTLE",   # Soluble iron, nmol/kg
    "Fe_TP": "Fe_TP_CONC_PUMP",    # Total particulate iron from pump
}

RHO_SW: float = 1025.0
"""Seawater density (kg/m³) for the nmol/kg → mmol/m³ unit conversion. Same
constant ``darwindiff.glodap_loader.RHO_SW`` and ``darwindiff.carbonate.RHO_SW``
use, kept in sync deliberately."""

_NMOL_PER_KG_TO_MMOL_PER_M3: float = RHO_SW * 1.0e-6


def open_geotraces_bottle(
    geotraces_path: str | Path,
) -> xr.Dataset:
    """Open the IDP2025 bottle-data NetCDF, normalize coordinates.

    Standardizes longitude to ``-180..180`` (DarwinDiff's AOI convention).
    GEOTRACES IDP files use either ``-180..180`` or ``0..360`` depending on
    the cruise; we detect and normalize.

    Args:
        geotraces_path: path to the IDP2025 NetCDF (e.g.
            ``GEOTRACES_IDP2025_v1_Discrete_Sample_Data.nc``).

    Returns:
        ``xr.Dataset`` with discrete-sample observations along an ``N_SAMPLES``
        dimension; coordinates ``Latitude``, ``Longitude``, ``DEPTH`` (or
        ``Pressure``), ``time``; variables include the iron measurements
        listed in :data:`GEOTRACES_VAR_MAP` (those present in this file).

    Raises:
        FileNotFoundError: if the NetCDF is not at the given path.
    """
    path = Path(geotraces_path)
    if not path.is_file():
        raise FileNotFoundError(f"GEOTRACES IDP file not found: {path}")
    ds = xr.open_dataset(path)
    # Normalize longitude to -180..180 if needed.
    if "Longitude" in ds and float(ds.Longitude.max()) > 180.0:
        ds = ds.assign_coords(
            Longitude=(((ds.Longitude + 180) % 360) - 180)
        )
    return ds


def subset_aoi_geotraces(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Filter discrete bottle samples to those inside an AOI box.

    GEOTRACES bottle data is irregular (samples at arbitrary lat/lon along
    cruise tracks), so AOI subsetting is a boolean filter on the sample
    dimension rather than a ``sel`` slice.

    Args:
        ds: GEOTRACES dataset with ``Latitude`` and ``Longitude`` coords
            (already normalized to ``-180..180`` via :func:`open_geotraces_bottle`).
        aoi: AOI in ``-180..180`` convention.

    Returns:
        ``xr.Dataset`` filtered to samples inside the AOI bounding box.
    """
    in_lat = (ds.Latitude >= aoi.lat_min) & (ds.Latitude <= aoi.lat_max)
    in_lon = (ds.Longitude >= aoi.lon_min) & (ds.Longitude <= aoi.lon_max)
    return ds.where(in_lat & in_lon, drop=True)


def bin_to_grid(
    ds: xr.Dataset,
    variable: str,
    aoi: AOI,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
    depth_max: float = 50.0,
) -> xr.DataArray:
    """Bin discrete GEOTRACES samples to a regular 1°×1° grid in an AOI.

    Aggregates all bottle samples within each (lat, lon) bin and shallower
    than ``depth_max`` (default 50 m surface mixed layer) by simple mean.
    Empty bins are NaN. The output grid matches the DarwinDiff AOI
    convention (1° cell centers offset by 0.5°).

    Args:
        ds: pre-AOI-subset GEOTRACES dataset (use :func:`subset_aoi_geotraces`).
        variable: friendly name from :data:`GEOTRACES_VAR_MAP`.
        aoi: AOI matching the desired output grid.
        lat_res, lon_res: grid resolution in degrees. Default 1°.
        depth_max: maximum sample depth in meters to include in the surface
            average. Default 50 m. Set to ``np.inf`` for full water column.

    Returns:
        ``xr.DataArray`` shape ``(n_lat, n_lon)``, units **nmol/kg**
        (still raw GEOTRACES — convert with :func:`to_mmol_per_m3` for the
        DarwinDiff box-model unit).

    Raises:
        KeyError: if ``variable`` is not registered in :data:`GEOTRACES_VAR_MAP`.
        ValueError: if the dataset lacks ``Latitude``/``Longitude``/depth coords
            or the variable column.
    """
    if variable not in GEOTRACES_VAR_MAP:
        raise KeyError(
            f"unknown GEOTRACES variable {variable!r}; "
            f"known: {sorted(GEOTRACES_VAR_MAP)}"
        )
    geotraces_var = GEOTRACES_VAR_MAP[variable]
    if geotraces_var not in ds:
        raise ValueError(
            f"variable {geotraces_var!r} (friendly: {variable!r}) not "
            f"present in dataset; available: {sorted(ds.data_vars)}"
        )

    depth_coord = "DEPTH" if "DEPTH" in ds else "Pressure"
    if depth_coord not in ds:
        raise ValueError(
            f"dataset missing depth coordinate (expected 'DEPTH' or 'Pressure'); "
            f"available coords: {sorted(ds.coords)}"
        )

    # Surface-MLD subset.
    surface_mask = ds[depth_coord] <= depth_max
    ds_surf = ds.where(surface_mask, drop=True)

    # Build the target 1° grid: cell centers at integer + 0.5° offset.
    lat_centers = np.arange(
        aoi.lat_min + lat_res / 2.0,
        aoi.lat_max + lat_res / 2.0,
        lat_res,
    )
    lon_centers = np.arange(
        aoi.lon_min + lon_res / 2.0,
        aoi.lon_max + lon_res / 2.0,
        lon_res,
    )

    grid = np.full((len(lat_centers), len(lon_centers)), np.nan, dtype=np.float64)
    values = ds_surf[geotraces_var].values.flatten()
    lats = ds_surf.Latitude.values.flatten()
    lons = ds_surf.Longitude.values.flatten()
    finite = np.isfinite(values) & np.isfinite(lats) & np.isfinite(lons)
    values, lats, lons = values[finite], lats[finite], lons[finite]

    lat_idx = np.floor((lats - aoi.lat_min) / lat_res).astype(np.int64)
    lon_idx = np.floor((lons - aoi.lon_min) / lon_res).astype(np.int64)
    in_bounds = (
        (lat_idx >= 0) & (lat_idx < len(lat_centers))
        & (lon_idx >= 0) & (lon_idx < len(lon_centers))
    )
    lat_idx, lon_idx, values = lat_idx[in_bounds], lon_idx[in_bounds], values[in_bounds]

    # Mean per bin via numpy accumulation; bins with no samples stay NaN.
    sum_grid = np.zeros_like(grid)
    count_grid = np.zeros_like(grid, dtype=np.int64)
    for li, lo, v in zip(lat_idx, lon_idx, values):
        sum_grid[li, lo] += v
        count_grid[li, lo] += 1
    nonzero = count_grid > 0
    grid[nonzero] = sum_grid[nonzero] / count_grid[nonzero]

    return xr.DataArray(
        grid,
        dims=("lat", "lon"),
        coords={"lat": lat_centers, "lon": lon_centers},
        name=variable,
        attrs={
            "units": "nmol/kg",
            "source": f"GEOTRACES IDP2025 ({geotraces_var}), bin-mean to 1°",
            "depth_max_m": depth_max,
            "n_samples_aggregated": int(count_grid.sum()),
        },
    )


def to_mmol_per_m3(da_nmol_per_kg: xr.DataArray) -> xr.DataArray:
    """Convert nmol/kg → mmol/m³ via ρ_sw = 1025 kg/m³.

    Matches the unit convention DarwinDiff uses internally for the iron
    tracer (and other concentration tracers). GEOTRACES reports per-kg-of-
    seawater in nmol; we convert at the loader I/O boundary so downstream
    code stays in mmol/m³.

    Args:
        da_nmol_per_kg: GEOTRACES DataArray in nmol/kg.

    Returns:
        DataArray in mmol/m³, with metadata preserved + updated ``units``
        attribute.
    """
    converted = da_nmol_per_kg * _NMOL_PER_KG_TO_MMOL_PER_M3
    converted.attrs = dict(da_nmol_per_kg.attrs)
    converted.attrs["units"] = "mmol / m^3"
    converted.attrs["unit_conversion"] = (
        f"GEOTRACES nmol/kg × ρ_sw ({RHO_SW} kg/m³) × 1e-6 = mmol/m³"
    )
    return converted
