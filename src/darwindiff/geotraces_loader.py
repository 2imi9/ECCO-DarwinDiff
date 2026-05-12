"""Loader for the GEOTRACES IDP2025 discrete-bottle iron observations.

GEOTRACES IDP (Intermediate Data Product) is the authoritative compilation
of trace-element observations from research cruises worldwide. IDP2025 is
the June 2025 release, containing **23,912 dissolved iron observations**
across the global ocean — the absolute-units, depth-resolved iron data
that resolves the alpfe ↔ scav_rat identifiability degeneracy left
unresolved by the v2.2 closeout and Wave 3 follow-ups.

**Why GEOTRACES specifically.** Across 25 experiments (v2.2 + Wave 3),
``alpfe`` sat at 0.80–0.94 off Carroll regardless of loss design —
except one configuration (``raw_fet w=0.01`` standalone) which moved
alpfe to 0.392 but broke scav_rat to 2.556. The structural explanation:
z-scored FeT loss normalizes away the absolute iron magnitude that
alpfe controls (dust solubility coefficient × atmospheric dust flux).
Adding GEOTRACES iron in absolute units (nmol/kg) as an additional loss
term ties the recovered DFe field to a real scale, breaking the
alpfe-scav_rat degeneracy without sacrificing one for the other.

**Real schema (validated against the IDP2025 NetCDF, 2026-05-12).** The
v2.5 scaffold loader (PR #39) assumed an IDP2017-style schema with
``_BOTTLE``/``_PUMP`` suffixes and 1D ``(N_SAMPLES,)`` structure. The
real IDP2025 NetCDF is different:

    Dims:   N_STATIONS = 4094, N_SAMPLES = 698 (per-station bottles)
    Coords: latitude, longitude (lowercase, per-station, 0..360 lon)
            date_time (per-station, datetime64)
            Bot_Depth (per-station, m)
    Per-sample: DEPTH (N_STATIONS, N_SAMPLES) in meters
    Iron vars: Fe_D_CONC, Fe_II_D_CONC, Fe_S_CONC, Fe_TP_CONC,
              Fe_TPL_CONC, Fe_TPR_CONC, Fe_LPT_CONC, Fe_MPT_CONC,
              Fe_SPT_CONC, Fe_SPL_CONC, Fe_56_54_D_DELTA, Fe_CELL_CONC
              all shape (N_STATIONS, N_SAMPLES), units nmol/kg
              (Fe_56_54_D_DELTA is per-mil isotope ratio, Fe_CELL_CONC
              is amol/cell)
    Companions: each iron var has *_err (1σ uncertainty) and *_qc
              (quality-control flag) of the same shape
    Fill value: -1.0e10 (replaced with NaN in the loader)
    QC flag convention (SeaDataNet, stored as ASCII char codes — NOT
    plain integer flags as the older GEOTRACES IDPs used):
        48 = '0' = no_quality_control
        49 = '1' = good_value          ← default keep
        50 = '2' = probably_good_value ← default keep
        51 = '3' = probably_bad_value
        52 = '4' = bad_value
        53 = '5' = changed_value
        54 = '6' = value_below_detection
        55 = '7' = value_in_excess
        56 = '8' = interpolated_value
        57 = '9' = missing_value
        65 = 'A' = value_phenomenon_uncertain
        66 = 'B' = nominal_value
        81 = 'Q' = value_below_limit_of_quantification

Iron values are SPARSE — only ~0.8% of the (N_STATIONS × N_SAMPLES)
grid has Fe_D_CONC measured. The loader unpacks to flat sample arrays
before AOI subsetting and grid binning.

**Format chosen.** NetCDF (ODV-style) from the bulk-download DOI
``10.5285/42c92148-8d03-8be6-e063-7086abc09f0c``. ASCII and ODV
collection formats also distributed but are awkward for the discrete-
bottle schema; the NetCDF preserves cruise/station provenance, unit
metadata, and per-station coordinates cleanly.

**Unit convention.** GEOTRACES reports concentrations as **nmol per kg
of seawater**. DarwinDiff's box model uses **mmol per m³**. Conversion
at surface seawater density (ρ_sw ≈ 1025 kg/m³):

    1 nmol/kg = 1e-6 mmol/kg × 1025 kg/m³ = 1.025 × 10⁻³ mmol/m³

Or equivalently multiply GEOTRACES by ``RHO_SW * 1e-6`` to get our
internal units. Same ``RHO_SW`` constant as ``darwindiff.glodap_loader``
and ``darwindiff.carbonate``, kept in sync deliberately.

Source: GEOTRACES Standards and Intercalibration Committee, IDP2025
        https://www.geotraces.org/idp2025/
        DOI: 10.5285/42c92148-8d03-8be6-e063-7086abc09f0c
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI

# Friendly DarwinDiff name → GEOTRACES IDP2025 variable name.
#
# IDP2025 drops the ``_BOTTLE``/``_PUMP`` suffixes the older IDPs used —
# the sampling method is recorded in per-station metadata
# (``Sampling_Devices``) but not the variable name. Each entry below is
# validated against the real ``GEOTRACES_IDP2025_Seawater.nc`` schema.
GEOTRACES_VAR_MAP: dict[str, str] = {
    "Fe_D":  "Fe_D_CONC",      # Dissolved iron, nmol/kg — primary alpfe target
    "Fe_S":  "Fe_S_CONC",      # Soluble iron, nmol/kg
    "Fe_TP": "Fe_TP_CONC",     # Total particulate iron, nmol/kg
    "Fe_II_D": "Fe_II_D_CONC", # Dissolved Fe(II), nmol/kg
}

RHO_SW: float = 1025.0
"""Seawater density (kg/m³) for the nmol/kg → mmol/m³ unit conversion. Same
constant ``darwindiff.glodap_loader.RHO_SW`` and ``darwindiff.carbonate.RHO_SW``
use, kept in sync deliberately."""

_NMOL_PER_KG_TO_MMOL_PER_M3: float = RHO_SW * 1.0e-6

# IDP2025 fill value: any value at or below this threshold is missing.
# The NetCDF declares ``_FillValue = -1.00000e+10`` for float arrays.
FILL_VALUE_THRESHOLD: float = -1.0e9

# Good-quality QC flags. IDP2025 stores SeaDataNet QC codes as ASCII
# character codes: 49 = '1' = good_value; 50 = '2' = probably_good_value.
# Default filter to {49, 50}; everything else is excluded unless caller
# opts in via the ``qc_flags`` argument. See module docstring for the
# full code table.
QC_GOOD_VALUE: int = 49
QC_PROBABLY_GOOD_VALUE: int = 50
QC_GOOD: tuple[int, ...] = (QC_GOOD_VALUE, QC_PROBABLY_GOOD_VALUE)


def open_geotraces_bottle(geotraces_path: str | Path) -> xr.Dataset:
    """Open the IDP2025 Seawater NetCDF, normalize longitude, mask fill values.

    Reads the canonical IDP2025 NetCDF (``GEOTRACES_IDP2025_Seawater.nc``)
    and performs three boundary normalizations so downstream code sees a
    well-conditioned dataset:

    - Longitude rolled from 0..360 to -180..180 (DarwinDiff's AOI
      convention).
    - Fill-value sentinels (``-1.0e10``) on iron + depth variables
      replaced with ``NaN`` so finite-mask filtering works naturally.
    - Iron variables kept on 2D ``(N_STATIONS, N_SAMPLES)`` shape; AOI
      subsetting and grid binning unpack to 1D internally.

    Args:
        geotraces_path: path to the IDP2025 NetCDF (e.g.
            ``D:\\geotraces\\GEOTRACES_IDP2025_Seawater.nc``).

    Returns:
        ``xr.Dataset`` with the IDP2025 schema preserved (dims
        ``N_STATIONS``, ``N_SAMPLES``), longitude normalized to
        ``-180..180``, fill values replaced with NaN on iron + depth
        variables.

    Raises:
        FileNotFoundError: if the NetCDF is not at the given path.
    """
    path = Path(geotraces_path)
    if not path.is_file():
        raise FileNotFoundError(f"GEOTRACES IDP file not found: {path}")
    ds = xr.open_dataset(path)
    # Roll longitude 0..360 → -180..180.
    if "longitude" in ds and float(ds.longitude.max()) > 180.0:
        ds = ds.assign_coords(
            longitude=(((ds.longitude + 180) % 360) - 180)
        )
    # Mask fill values on iron + depth variables. Iron variables follow
    # the ``Fe...`` or ``L*Fe...`` naming pattern (which matches the
    # companion ``*_err`` and ``*_qc`` fields too — that's intentional;
    # they're numeric and a -1e10 sentinel would propagate the same way).
    # DEPTH is the per-sample depth coordinate. Character-typed metadata
    # vars (cruise_id, station_id, etc.) don't match these prefixes and
    # are left alone.
    for v in ds.data_vars:
        if (v.startswith("Fe_") or v.startswith("L1Fe_") or v.startswith("L2Fe_")
                or v.startswith("LFe_") or v == "DEPTH"):
            ds[v] = ds[v].where(ds[v] > FILL_VALUE_THRESHOLD)
    return ds


def subset_aoi_geotraces(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Filter discrete bottle samples to those inside an AOI box.

    GEOTRACES is per-station — coordinates are stored once per station,
    and each station holds up to 698 bottle samples down a cast. AOI
    subsetting filters STATIONS by their (lat, lon) and keeps every
    sample on those stations.

    Args:
        ds: GEOTRACES dataset (already opened via :func:`open_geotraces_bottle`,
            so longitude is in ``-180..180`` convention).
        aoi: AOI in ``-180..180`` convention.

    Returns:
        ``xr.Dataset`` filtered along the ``N_STATIONS`` dimension.
        Stations outside the AOI are dropped; all samples on retained
        stations are kept.
    """
    in_lat = (ds.latitude >= aoi.lat_min) & (ds.latitude <= aoi.lat_max)
    in_lon = (ds.longitude >= aoi.lon_min) & (ds.longitude <= aoi.lon_max)
    return ds.isel(N_STATIONS=(in_lat & in_lon).values)


def bin_to_grid(
    ds: xr.Dataset,
    variable: str,
    aoi: AOI,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
    depth_max: float = 50.0,
    qc_flags: tuple[int, ...] = QC_GOOD,
) -> xr.DataArray:
    """Bin discrete GEOTRACES samples to a regular 1°×1° AOI grid.

    Flattens the 2D ``(N_STATIONS, N_SAMPLES)`` discrete-bottle dataset
    into a list of finite, QC-passing, surface samples and bins them to
    a regular lat/lon grid by simple mean per cell. Bin edges are aligned
    at integer degrees; cell centers are at integer + 0.5°. Empty bins
    return ``NaN``.

    Each station's (lat, lon) is broadcast to all its samples before
    binning, so multiple bottles from the same station vote into the
    same bin.

    Args:
        ds: pre-AOI-subset GEOTRACES dataset (use :func:`subset_aoi_geotraces`
            first).
        variable: friendly name from :data:`GEOTRACES_VAR_MAP` (e.g.
            ``"Fe_D"``).
        aoi: AOI matching the desired output grid.
        lat_res, lon_res: grid resolution in degrees. Default 1°.
        depth_max: maximum sample depth in meters to include in the
            surface mean. Default 50 m (typical surface-MLD scale). Set
            to ``np.inf`` for full water column.
        qc_flags: GEOTRACES SeaDataNet quality-control flags to accept.
            Default ``(49, 50)`` for ASCII-coded "good" + "probably good".
            See module docstring for the full code table. Pass empty
            tuple to disable QC filtering entirely.

    Returns:
        ``xr.DataArray`` shape ``(n_lat, n_lon)``, units **nmol/kg**.
        Convert to DarwinDiff's internal mmol/m³ via
        :func:`to_mmol_per_m3`.

    Raises:
        KeyError: if ``variable`` is not registered in :data:`GEOTRACES_VAR_MAP`.
        ValueError: if the dataset lacks ``latitude``/``longitude``/``DEPTH``
            or the resolved variable column.
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
            f"present in dataset; available Fe vars: "
            f"{sorted(v for v in ds.data_vars if v.startswith('Fe_') and not v.endswith(('_qc','_err')))}"
        )
    for needed in ("latitude", "longitude", "DEPTH"):
        if needed not in ds:
            raise ValueError(
                f"dataset missing {needed!r} coord/variable; "
                f"available: {sorted(list(ds.coords) + list(ds.data_vars))[:15]}..."
            )

    # Flatten (N_STATIONS, N_SAMPLES) to 1D using broadcasting. Each
    # station's lat/lon repeats across its samples.
    n_stations, n_samples = ds[geotraces_var].shape
    lats = np.broadcast_to(
        ds.latitude.values[:, None], (n_stations, n_samples)
    ).flatten()
    lons = np.broadcast_to(
        ds.longitude.values[:, None], (n_stations, n_samples)
    ).flatten()
    depths = ds.DEPTH.values.flatten()
    values = ds[geotraces_var].values.flatten()

    # Quality-control filter. Iron variables have a companion ``<var>_qc``
    # with the same shape; keep only specified flags when present.
    qc_var = f"{geotraces_var}_qc"
    if qc_var in ds and len(qc_flags) > 0:
        qc_values = ds[qc_var].values.flatten()
        in_qc = np.isin(qc_values, np.array(qc_flags, dtype=qc_values.dtype))
    else:
        in_qc = np.ones_like(values, dtype=bool)

    surface = depths <= depth_max
    finite = np.isfinite(values) & np.isfinite(lats) & np.isfinite(lons)
    keep = surface & finite & in_qc
    lats, lons, values = lats[keep], lons[keep], values[keep]

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
    lat_idx = np.floor((lats - aoi.lat_min) / lat_res).astype(np.int64)
    lon_idx = np.floor((lons - aoi.lon_min) / lon_res).astype(np.int64)
    # Two bin-edge cases to handle: (1) samples exactly on the lat_max /
    # lon_max boundary floor() to index n (out of [0, n-1]) — clamp these
    # into the top bin so they're not silently dropped. (2) samples beyond
    # the AOI bounds should be excluded entirely. Check bounds BEFORE
    # clamping so we don't accidentally fold out-of-AOI samples into the
    # top bin (matters if caller skips subset_aoi_geotraces).
    in_bounds = (
        (lat_idx >= 0) & (lat_idx <= len(lat_centers))
        & (lon_idx >= 0) & (lon_idx <= len(lon_centers))
    )
    lat_idx = np.minimum(lat_idx, len(lat_centers) - 1)
    lon_idx = np.minimum(lon_idx, len(lon_centers) - 1)
    lat_idx, lon_idx, values = lat_idx[in_bounds], lon_idx[in_bounds], values[in_bounds]

    # Vectorized bin accumulation via np.add.at (handles duplicate indices
    # without a Python loop).
    sum_grid = np.zeros_like(grid)
    count_grid = np.zeros_like(grid, dtype=np.int64)
    np.add.at(sum_grid, (lat_idx, lon_idx), values)
    np.add.at(count_grid, (lat_idx, lon_idx), 1)
    nonzero = count_grid > 0
    grid[nonzero] = sum_grid[nonzero] / count_grid[nonzero]

    return xr.DataArray(
        grid,
        dims=("lat", "lon"),
        coords={"lat": lat_centers, "lon": lon_centers},
        name=variable,
        attrs={
            "units": "nmol/kg",
            "source": (
                f"GEOTRACES IDP2025 ({geotraces_var}), "
                f"bin-mean to {lat_res}°×{lon_res}°, surface<={depth_max}m, "
                f"QC in {qc_flags or 'unfiltered'}"
            ),
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
