"""Loader for ECCO-Darwin v05 ``bin_average`` 1-deg lat/lon NetCDF.

Source dataset: ``v05_ECCO-Darwin_bin_average_1x1_deg.nc`` from the NASA NAS
ECCO Data Portal (``https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/``).
This is the publicly-available bin-averaged surface diagnostics product from
ECCO-Darwin v05 (Carroll 2022 / Darwin 3 calibration), covering 23 years of
monthly snapshots (Jan 1995 to Dec 2017) at 1 x 1 deg lat/lon. **Surface only.**

Variables included:

- Carbonate system: ``CO2_flux`` (mol C/m^2/s), ``pCO2`` (atm), ``apCO2`` (atm)
- Physics: ``SST`` (degC), ``SSS`` (psu), ``mldDepth`` (m), ``windSpeed`` (m/s),
  ``seaIceArea`` (fraction)
- Phytoplankton chlorophyll for the 5 Darwin 3 PFTs: ``Chl1``, ``Chl2``,
  ``Chl3``, ``Chl4``, ``Chl5`` (mg Chl a / m^3)

Variables NOT included (would require the full LLC270 native ``monthly/`` tree):
``NO3``, ``DIC``, ``ALK``, ``PO4``, ``Si``, ``O2``, depth-resolved fields.

Why this loader exists: the raw file ships with ``y, x`` as integer dimension
indices and a ``time`` coord stored as MATLAB datenum. Both are awkward for
direct ``.sel(lat=..., lon=...)`` queries and for time-aware analysis. This
module decodes time and promotes the latent 1-D lat/lon arrays to coordinates
so callers can write ``ds.sel(lat=slice(30, 50), lon=slice(-60, -30))`` and
work with proper datetime64 timestamps.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import reduce
from operator import add
from pathlib import Path

import numpy as np
import xarray as xr

# Matlab datenum reference: day 1 = January 1, year 0000 in Matlab's
# proleptic-Gregorian-with-year-0 convention. Python's datetime starts at year
# 1, so we offset by 367 days (366 days of year 0 + 1 to align with day 1).
_MATLAB_EPOCH_OFFSET_DAYS: int = 367


@dataclass(frozen=True)
class AOI:
    """Rectangular area-of-interest in ``-180..180`` lon convention.

    Attributes:
        name: human-readable label, used in plots and logs.
        lat_min, lat_max: latitude range in degrees north (negative for south).
        lon_min, lon_max: longitude range in degrees east, ``-180..180``
            convention. ``lon_min < lon_max``; for boxes that cross the
            antimeridian, split into two AOIs.
    """

    name: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def __post_init__(self) -> None:
        if not -90 <= self.lat_min < self.lat_max <= 90:
            raise ValueError(
                f"AOI {self.name!r}: invalid lat range "
                f"[{self.lat_min}, {self.lat_max}]"
            )
        if not -180 <= self.lon_min < self.lon_max <= 180:
            raise ValueError(
                f"AOI {self.name!r}: invalid lon range "
                f"[{self.lon_min}, {self.lon_max}] (use -180..180 convention; "
                f"split into two AOIs for boxes crossing the antimeridian)"
            )


# Project AOIs from the May 7 collaboration call (Mid-Atlantic confirmed,
# North Pacific proposed pending Jonathan sign-off).
MID_ATLANTIC_AOI: AOI = AOI(
    name="Mid-Atlantic",
    lat_min=30.0,
    lat_max=50.0,
    lon_min=-60.0,
    lon_max=-30.0,
)
NORTH_PACIFIC_AOI: AOI = AOI(
    name="North Pacific",
    lat_min=30.0,
    lat_max=50.0,
    lon_min=-160.0,
    lon_max=-130.0,
)
EQUATORIAL_PACIFIC_AOI: AOI = AOI(
    name="Equatorial Pacific",
    lat_min=-5.0,
    lat_max=15.0,
    lon_min=-160.0,
    lon_max=-110.0,
)


def matlab_datenum_to_datetime64(values: np.ndarray) -> np.ndarray:
    """Convert MATLAB datenums to numpy ``datetime64[ns]``.

    MATLAB datenum 1 == January 1, year 0000 (Matlab's proleptic Gregorian
    with year 0). Python ``datetime`` starts at year 1, so we shift by 367
    days (366 days of year 0 + 1 to align with day 1).

    Args:
        values: array of MATLAB datenum floats.

    Returns:
        numpy array of ``datetime64[ns]`` with the same shape.
    """
    base = datetime(1, 1, 1)
    out = np.array(
        [base + timedelta(days=float(v) - _MATLAB_EPOCH_OFFSET_DAYS) for v in values],
        dtype="datetime64[ns]",
    )
    return out


def open_bin_average(path: str | Path) -> xr.Dataset:
    """Open the ECCO-Darwin v05 bin_average NetCDF with decoded time + lat/lon coords.

    The raw file uses ``y, x`` as integer dimension indices, ``lat`` and
    ``lon`` as 2-D variables (functionally 1-D — ``lat[y, x]`` depends only on
    ``y``), and ``time`` as MATLAB datenum. This function:

    1. Extracts the latent 1-D lat and lon arrays.
    2. Renames the ``y, x`` dimensions to ``lat, lon`` and assigns them as
       coordinates, enabling ``ds.sel(lat=slice(...), lon=slice(...))``.
    3. Decodes the time coordinate from MATLAB datenum to ``datetime64[ns]``.
    4. Drops the now-redundant 2-D ``lat, lon`` data variables (the new
       coordinates carry the same information).

    Args:
        path: filesystem path to the ``v05_ECCO-Darwin_bin_average_1x1_deg.nc``
            file (use a Windows-style path on Windows; ``/d/...`` POSIX-style
            paths get re-rooted to ``C:\\d\\...`` by ``netCDF4`` and fail).

    Returns:
        ``xr.Dataset`` with dims ``(time, lat, lon)``, time coord as
        ``datetime64[ns]``, lat/lon as numeric coords in ``-180..180`` /
        ``-90..90`` convention.
    """
    raw = xr.open_dataset(path)

    # The raw lat/lon are 2-D but functionally 1-D (lat varies only with y,
    # lon only with x). Pull the 1-D representations out for use as coords.
    lat_1d = raw["lat"].values[:, 0]
    lon_1d = raw["lon"].values[0, :]

    ds = (
        raw.drop_vars(["lat", "lon"])
        .rename({"y": "lat", "x": "lon"})
        .assign_coords(lat=("lat", lat_1d), lon=("lon", lon_1d))
    )

    # Decode time from MATLAB datenum.
    decoded_time = matlab_datenum_to_datetime64(raw["time"].values)
    ds = ds.assign_coords(time=("time", decoded_time))

    return ds


def subset_aoi(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Subset an ECCO-Darwin lat/lon dataset to a rectangular AOI.

    Uses ``.sel`` with inclusive endpoints. Assumes the dataset has ``lat``
    and ``lon`` as coordinates (e.g. via :func:`open_bin_average`).

    Args:
        ds: dataset opened by :func:`open_bin_average`.
        aoi: target AOI.

    Returns:
        Subset dataset with the same dims/vars, restricted to the AOI.
    """
    return ds.sel(
        lat=slice(aoi.lat_min, aoi.lat_max),
        lon=slice(aoi.lon_min, aoi.lon_max),
    )


def total_chlorophyll(ds: xr.Dataset, groups: Iterable[int] | None = None) -> xr.DataArray:
    """Sum chlorophyll across the specified Darwin 3 phytoplankton groups.

    Darwin 3 has 5 phytoplankton functional types in v05; the bin_average
    file exposes them as ``Chl1`` through ``Chl5``. Per Carroll 2022 abstract:
    "five large-to-small phytoplankton functional types (diatoms, other large
    eukaryotes, Synechococcus, and low- and high-light adapted Prochlorococcus)".

    Args:
        ds: dataset with ``Chl1..Chl5`` data vars.
        groups: which group indices (1..5) to sum. ``None`` sums all five.

    Returns:
        ``xr.DataArray`` with dims ``(time, lat, lon)``, units ``mg Chl a / m^3``,
        named ``"Chl_total"``.
    """
    if groups is None:
        groups = range(1, 6)
    names = [f"Chl{i}" for i in groups]
    missing = [n for n in names if n not in ds.data_vars]
    if missing:
        raise KeyError(f"Chlorophyll groups not found in dataset: {missing}")
    # ``reduce(add, ...)`` instead of ``sum(... )`` so the start value isn't a
    # plain int, which would type-narrow the result to ``DataArray | int``.
    total: xr.DataArray = reduce(add, (ds[n] for n in names))
    total.name = "Chl_total"
    total.attrs["long_name"] = f"Total chlorophyll ({'+'.join(names)})"
    total.attrs["units"] = "mg Chl a / m^3"
    return total


def monthly_climatology(ds: xr.Dataset) -> xr.Dataset:
    """Reduce a monthly time series to a 12-month climatology.

    Groups by month-of-year and averages across all years in the dataset.
    Useful for "the average July field" rather than "every July field
    individually". Resulting time dimension has length 12.

    Args:
        ds: dataset opened by :func:`open_bin_average`, with ``time`` coord.

    Returns:
        Dataset with the time dimension replaced by ``month`` of length 12.
    """
    return ds.groupby("time.month").mean(dim="time", skipna=True)


def time_mean(ds: xr.Dataset) -> xr.Dataset:
    """Reduce a time series to a single time-mean snapshot.

    Args:
        ds: dataset with a ``time`` dim.

    Returns:
        Dataset with ``time`` collapsed to a single mean.
    """
    return ds.mean(dim="time", skipna=True)


def ocean_mask(ds: xr.Dataset, reference_var: str = "SST") -> xr.DataArray:
    """Build a boolean ocean mask from a reference variable's NaN pattern.

    Land cells in the bin_average product carry NaN consistently across all
    variables; any time-varying variable can be used to derive the mask. SST
    is a safe default (always populated for ocean cells).

    Args:
        ds: dataset (typically AOI-subset).
        reference_var: variable name to read the NaN pattern from.

    Returns:
        Boolean DataArray with dims ``(lat, lon)``, True at ocean cells.
    """
    if reference_var not in ds.data_vars:
        raise KeyError(f"reference_var {reference_var!r} not in dataset")
    da = ds[reference_var]
    if "time" in da.dims:
        # Use the first timestep — land mask is time-invariant.
        da = da.isel(time=0)
    return da.notnull()
