"""Loader for PACE OCI Level-3 mapped ocean biogeochemistry products.

PACE OCI launched 2024-02-08; v3.1 reprocessing complete August 2025. The
publicly available L3m products in 2026-05 are listed in
``docs/findings/modis_arc/phase1_data_scouting.md``. Most relevant for
DarwinDiff:

  - **carbon_phyto** (OC_BGC suite, Provisional, mg m^-3): total phytoplankton
    carbon. NEW independent biomass observation -- not available in MODIS
    heritage. Could anchor Biggrow/Smallgrow directly without going through
    chl-to-carbon conversion.
  - **chlor_a** (OC_BGC suite, Provisional, mg m^-3): total chlorophyll-a.
    Existing analog in Darwin v05; minimal new value.
  - **poc** (OC_BGC suite, Provisional, mg m^-3): particulate organic carbon.
    Useful as independent cross-check on Darwin v05's POC.

Critical from Phase 1 scouting (PACE V3.x reprocessing notes PDF):
  - **PIC is NOT in v3.1.** Future v3.2 release, no timeline. For PIC use
    MODIS-Aqua via :mod:`modis_pic_loader` until v3.2 ships.
  - **MOANA picoplankton (Pro/Syn/picoeuk) is Atlantic-only.** Covers
    natlsubpolar AOI but NOT eqpac. Asymmetric anchor only.
  - **Monthly composites are sparse**: only Apr/May/Jun 2024 exist for
    carbon_phyto v3.1; daily is much more populated. 8-day and rolling-32-day
    composites also available.

File naming convention (OB.DAAC L3m):
    PACE_OCI.YYYYMMDD_YYYYMMDD.L3m.{DAY,8D,MO,R32}.{SUITE}.V3_1.{var}.{4km,0p1deg}.nc

Each granule has dims (lat, lon) plus a (rgb, eightbitcolor) palette variable
for the OB.DAAC viewer. The main variable is float32 in mg m^-3.

Typical AOI coverage at 0.1deg, monthly:
  eqpac:        ~95.7% finite cells (carbon_phyto, April 2024)
  natlsubpolar: ~97.7% finite cells (carbon_phyto, April 2024)

Quick usage::

    from darwindiff.pace_loader import build_aoi_carbon_phyto
    from darwindiff.ecco_darwin_loader import EQUATORIAL_PACIFIC_AOI

    cphyto, mask = build_aoi_carbon_phyto(
        r"D:\\pace_data",
        EQUATORIAL_PACIFIC_AOI,
        period="MO",
    )
    # cphyto shape (21, 51) at 1deg, in mg m^-3.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import numpy as np
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI

# Convert PACE carbon_phyto mg m^-3 -> DarwinDiff's internal mmol C / m^3.
# 1 mol C = 12.011 g C -> 1 mg C / m^3 = 1/12.011 mmol C / m^3.
MG_C_PER_M3_TO_MMOL_C_PER_M3 = 1.0 / 12.011

# PACE_OCI.YYYYMMDD_YYYYMMDD.L3m.<PERIOD>.<SUITE>.V<ver>.<var>.<res>.nc
_PACE_FILENAME_RE = re.compile(
    r"PACE_OCI\.(\d{8})_(\d{8})\.L3m\."
    r"(DAY|8D|MO|R32|SNSP|R\d+)\.(\w+)\."
    r"V(\d+)_(\d+)\.(\w+)\.(4km|0p1deg|9km)\.nc"
)


def _parse_filename(path: Path) -> dict:
    """Extract structured metadata from a PACE L3m filename."""
    m = _PACE_FILENAME_RE.search(path.name)
    if m is None:
        raise ValueError(f"not a PACE L3m filename: {path.name}")
    return {
        "start": datetime.strptime(m.group(1), "%Y%m%d"),
        "end": datetime.strptime(m.group(2), "%Y%m%d"),
        "period": m.group(3),
        "suite": m.group(4),
        "version": f"{m.group(5)}.{m.group(6)}",
        "variable": m.group(7),
        "resolution": m.group(8),
    }


def open_pace(path: str | Path) -> xr.Dataset:
    """Open a PACE OCI L3m granule, stamp the time coord from filename.

    Args:
        path: filesystem path to a ``PACE_OCI.*.L3m.*.nc`` file.

    Returns:
        ``xr.Dataset`` with dims ``(time, lat, lon)`` (time length 1).
    """
    path = Path(path)
    meta = _parse_filename(path)
    midpoint = meta["start"] + (meta["end"] - meta["start"]) / 2
    ds = xr.open_dataset(path)
    ds = ds.expand_dims(time=[np.datetime64(midpoint, "ns")])
    ds.attrs.update({
        "darwindiff_filename": path.name,
        "darwindiff_period": meta["period"],
        "darwindiff_suite": meta["suite"],
        "darwindiff_variable": meta["variable"],
        "darwindiff_resolution": meta["resolution"],
        "darwindiff_version": meta["version"],
    })
    return ds


def discover_granules(
    pace_dir: str | Path,
    variable: str,
    period: Literal["DAY", "8D", "MO", "R32"] = "MO",
    resolution: str = "0p1deg",
    start_year: int | None = None,
    end_year: int | None = None,
    version: str = "3.1",
) -> list[Path]:
    """List PACE L3m granules in a directory matching the requested filters.

    Args:
        pace_dir: directory containing downloaded PACE granules.
        variable: e.g. ``"carbon_phyto"``, ``"chlor_a"``, ``"poc"``.
        period: temporal composite tag. Default ``"MO"`` (monthly).
        resolution: ``"0p1deg"`` (default), ``"4km"``, or ``"9km"``.
        start_year, end_year: inclusive year range; ``None`` means no bound.
        version: target version string e.g. ``"3.1"``. Defaults to v3.1 (the
            only fully active release as of 2026-05).

    Returns:
        Sorted list of matching granule paths.
    """
    pace_dir = Path(pace_dir)
    out: list[Path] = []
    for p in sorted(pace_dir.glob("PACE_OCI.*.L3m.*.nc")):
        try:
            meta = _parse_filename(p)
        except ValueError:
            continue
        if meta["period"] != period:
            continue
        if meta["resolution"] != resolution:
            continue
        if meta["variable"] != variable:
            continue
        if meta["version"] != version:
            continue
        if start_year is not None and meta["start"].year < start_year:
            continue
        if end_year is not None and meta["start"].year > end_year:
            continue
        out.append(p)
    return out


def open_climatology(
    pace_dir: str | Path,
    variable: str,
    period: Literal["DAY", "8D", "MO", "R32"] = "MO",
    resolution: str = "0p1deg",
    start_year: int | None = None,
    end_year: int | None = None,
) -> xr.Dataset:
    """Concatenate every matching PACE granule along time.

    Args:
        pace_dir: directory of downloaded PACE granules.
        variable: e.g. ``"carbon_phyto"``.
        period, resolution, start_year, end_year: passed to
            :func:`discover_granules`.

    Returns:
        ``xr.Dataset`` with dims ``(time, lat, lon)``, sorted ascending in time.

    Raises:
        FileNotFoundError: if no matching granules are found.
    """
    paths = discover_granules(
        pace_dir, variable, period, resolution, start_year, end_year
    )
    if not paths:
        raise FileNotFoundError(
            f"no PACE granules matching variable={variable!r}, period={period!r}, "
            f"resolution={resolution!r}, years=[{start_year}, {end_year}] in {pace_dir}"
        )
    return xr.concat([open_pace(p) for p in paths], dim="time").sortby("time")


def subset_aoi_pace(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Clip a PACE L3m dataset to an AOI (handles descending lat)."""
    lat = ds["lat"].values
    if lat[0] > lat[-1]:
        lat_slice = slice(aoi.lat_max, aoi.lat_min)
    else:
        lat_slice = slice(aoi.lat_min, aoi.lat_max)
    return ds.sel(lat=lat_slice, lon=slice(aoi.lon_min, aoi.lon_max))


def bin_to_1deg(
    da: xr.DataArray,
    aoi: AOI,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
    valid_min: float | None = None,
    valid_max: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin-average a PACE high-res field to a 1° Darwin-aligned grid.

    Uses the same convention as :func:`darwindiff.modis_pic_loader.bin_to_1deg`
    and :func:`darwindiff.llc270_loader.bin_to_1deg_grid`: integer-degree cell
    centers inclusive of both endpoints, edges at ±0.5°.

    Optionally clip out values outside ``[valid_min, valid_max]`` before
    averaging (PACE granules expose these as NetCDF attrs; pass them to mask
    fill-saturation outliers).

    Args:
        da: 2-D ``(lat, lon)`` or 3-D ``(time, lat, lon)`` DataArray. 3-D
            inputs are time-averaged first.
        aoi: target AOI.
        lat_res, lon_res: output cell size in degrees. Default 1°.
        valid_min, valid_max: optional inclusive bounds. Cells outside the
            range are treated as NaN before binning.

    Returns:
        Tuple ``(values, mask)``, same shapes/conventions as the MODIS loader.
    """
    if da.ndim == 3:
        da = da.mean(dim="time", skipna=True)
    if da.ndim != 2:
        raise ValueError(f"expected 2-D or 3-D DataArray, got {da.ndim}-D")

    lat = da["lat"].values
    lon = da["lon"].values
    arr = da.values.astype(np.float64)

    if lat[0] > lat[-1]:
        lat = lat[::-1]
        arr = arr[::-1, :]

    if valid_min is not None:
        arr = np.where(arr < valid_min, np.nan, arr)
    if valid_max is not None:
        arr = np.where(arr > valid_max, np.nan, arr)

    lat_centers = np.arange(aoi.lat_min, aoi.lat_max + lat_res / 2.0, lat_res)
    lon_centers = np.arange(aoi.lon_min, aoi.lon_max + lon_res / 2.0, lon_res)
    n_lat = len(lat_centers)
    n_lon = len(lon_centers)

    lat_bin = np.floor((lat - aoi.lat_min + lat_res / 2.0) / lat_res).astype(np.int64)
    lon_bin = np.floor((lon - aoi.lon_min + lon_res / 2.0) / lon_res).astype(np.int64)
    lat_ok = (lat_bin >= 0) & (lat_bin < n_lat + 1)
    lat_bin = np.minimum(lat_bin, n_lat - 1)
    lon_ok = (lon_bin >= 0) & (lon_bin < n_lon + 1)
    lon_bin = np.minimum(lon_bin, n_lon - 1)

    finite = np.isfinite(arr)
    ok2d = lat_ok[:, None] & lon_ok[None, :] & finite
    yi = np.broadcast_to(lat_bin[:, None], arr.shape)[ok2d]
    xi = np.broadcast_to(lon_bin[None, :], arr.shape)[ok2d]
    vals = arr[ok2d]
    flat_idx = yi * n_lon + xi
    n_cells = n_lat * n_lon
    sums = np.bincount(flat_idx, weights=vals, minlength=n_cells)
    counts = np.bincount(flat_idx, minlength=n_cells)
    nonzero = counts > 0
    flat_out = np.full(n_cells, np.nan, dtype=np.float64)
    flat_out[nonzero] = sums[nonzero] / counts[nonzero]
    return flat_out.reshape(n_lat, n_lon), nonzero.reshape(n_lat, n_lon)


def build_aoi_carbon_phyto(
    pace_dir: str | Path,
    aoi: AOI,
    period: Literal["DAY", "8D", "MO", "R32"] = "MO",
    resolution: str = "0p1deg",
    start_year: int | None = None,
    end_year: int | None = None,
    valid_max: float | None = 900.0,
) -> tuple[np.ndarray, np.ndarray]:
    """End-to-end: load PACE carbon_phyto granules, AOI clip, time-mean, bin.

    ``valid_max=900.0`` clips fill-saturation outliers (the variable's
    ``valid_max`` attribute is 1000.0 mg m^-3 but real ocean values rarely
    exceed a few hundred; values close to 1000 are usually retrieval artifacts
    near clouds / glint).

    Args:
        pace_dir: directory of downloaded PACE granules.
        aoi: target AOI.
        period, resolution, start_year, end_year: see :func:`discover_granules`.
        valid_max: drop values above this threshold (mg m^-3). ``None`` to
            disable.

    Returns:
        ``(values, mask)``: ``values`` shape ``(n_lat, n_lon)``, mg m^-3 (PACE
        native units); ``mask`` boolean.
    """
    ds = open_climatology(
        pace_dir, "carbon_phyto", period, resolution, start_year, end_year
    )
    ds = subset_aoi_pace(ds, aoi)
    return bin_to_1deg(ds["carbon_phyto"], aoi, valid_max=valid_max)


def save_aoi_cache(
    pace_dir: str | Path,
    aoi_by_key: dict[str, AOI],
    cache_path: str | Path,
    variable: str = "carbon_phyto",
    period: Literal["DAY", "8D", "MO", "R32"] = "MO",
    resolution: str = "0p1deg",
    start_year: int | None = None,
    end_year: int | None = None,
    valid_max: float | None = 900.0,
) -> None:
    """Cache PACE AOI climatology like the MODIS-Aqua loader does.

    Output is a ``.npz`` with ``{variable}_{key}`` and ``mask_{key}`` arrays.
    """
    payload: dict[str, np.ndarray] = {}
    for key, aoi in aoi_by_key.items():
        if variable == "carbon_phyto":
            values, mask = build_aoi_carbon_phyto(
                pace_dir, aoi, period, resolution, start_year, end_year, valid_max
            )
        else:
            ds = subset_aoi_pace(
                open_climatology(pace_dir, variable, period, resolution,
                                 start_year, end_year),
                aoi,
            )
            values, mask = bin_to_1deg(ds[variable], aoi, valid_max=valid_max)
        payload[f"{variable}_{key}"] = values.astype(np.float32)
        payload[f"mask_{key}"] = mask.astype(np.bool_)
    payload["variable"] = np.array(variable, dtype="U32")
    payload["period"] = np.array(period, dtype="U4")
    payload["resolution"] = np.array(resolution, dtype="U8")
    payload["units"] = np.array("mg m^-3", dtype="U16")
    payload["source"] = np.array(f"PACE OCI L3m.{period}.{variable} v3.1", dtype="U64")
    np.savez(cache_path, **payload)
