"""Loader for MODIS-Aqua Level-3 mapped Particulate Inorganic Carbon (PIC).

Provides AOI-clipped, 1°×1°-bin-averaged PIC fields from the MODIS-Aqua
v2022.0 L3m reprocessing. This is the independent satellite PIC anchor
that v3.0's PR #63 paired-anchor sweep was missing — the Darwin v05 PIC
field used there is the same model whose Carroll-6 calibration we're
trying to recover, making PIC_ABS against v05 PIC fundamentally circular.

MODIS-Aqua PIC algorithm: Balch & Gordon two-band approach calibrated for
coccolithophore assemblages. Coverage: 2002-07 → present. The 2017-2019
window aligns exactly with Carroll 2022's Green's-functions calibration
target, so this loader's monthly climatology is the right reference for
the recovery task.

File naming convention (OB.DAAC L3m monthly):
    AQUA_MODIS.YYYYMM01_YYYYMMDD.L3m.MO.PIC.pic.{4km,9km}.nc

Each granule is global at 9km (2160×4320) or 4km (4320×8640) regular grid
in (lat, lon). Variable ``pic`` is float32 in mol m⁻³ ("Calcite Concentration,
Balch and Gordon"). NaN cells are clouds / cloud-adjacent / sun-glint / low
solar elevation.

Typical AOI coverage at 9km, monthly:
    eqpac:       ~99.8% finite cells
    natlsubpolar:~97.1% finite cells

Quick usage::

    from darwindiff.modis_pic_loader import build_aoi_climatology
    from darwindiff.ecco_darwin_loader import EQUATORIAL_PACIFIC_AOI

    pic_field, mask = build_aoi_climatology(
        r"D:\\modis_aqua_pic",
        EQUATORIAL_PACIFIC_AOI,
        start_year=2017, end_year=2019,
    )
    # pic_field shape (20, 50) at 1° resolution; mol m^-3.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import xarray as xr

from darwindiff.ecco_darwin_loader import AOI

# Convert MODIS-Aqua PIC mol/m^3 → DarwinDiff's internal mmol C / m^3.
# PIC is CaCO_3 calcite; the carbon mole equivalent is 1:1 (one mole CaCO_3
# contains one mole C). So `1 mol/m^3 PIC = 1000 mmol C/m^3`.
MOL_PER_M3_TO_MMOL_C_PER_M3 = 1000.0

_MONTHLY_FILENAME_RE = re.compile(
    r"AQUA_MODIS\.(\d{8})_(\d{8})\.L3m\.MO\.PIC\.pic\.(4km|9km)\.nc",
)


def _parse_filename(path: Path) -> tuple[datetime, datetime, str]:
    """Extract (start, end, resolution) from an L3m PIC monthly filename."""
    m = _MONTHLY_FILENAME_RE.search(path.name)
    if m is None:
        raise ValueError(f"not a MODIS-Aqua L3m.MO.PIC filename: {path.name}")
    start = datetime.strptime(m.group(1), "%Y%m%d")
    end = datetime.strptime(m.group(2), "%Y%m%d")
    return start, end, m.group(3)


def open_modis_pic(path: str | Path) -> xr.Dataset:
    """Open one MODIS-Aqua L3m PIC monthly granule with the time coord set.

    The raw file has no time coord — just (lat, lon) — so we read the period
    midpoint from the filename and stamp it as a single-element time dim.
    This lets multiple monthly granules concatenate cleanly along ``time``.

    Args:
        path: filesystem path to an ``AQUA_MODIS.YYYYMM01_YYYYMMDD.L3m.MO.PIC.pic.{4km,9km}.nc``
            file.

    Returns:
        ``xr.Dataset`` with dims ``(time, lat, lon)``, time of length 1, the
        ``pic`` variable in mol m⁻³, and a ``palette`` variable carried through
        unchanged (used downstream only by the OB.DAAC viewer).
    """
    path = Path(path)
    start, end, _ = _parse_filename(path)
    midpoint = start + (end - start) / 2
    ds = xr.open_dataset(path)
    ds = ds.expand_dims(time=[np.datetime64(midpoint, "ns")])
    return ds


def open_climatology(
    modis_dir: str | Path,
    start_year: int = 2017,
    end_year: int = 2019,
    resolution: str = "9km",
) -> xr.Dataset:
    """Open every monthly L3m.MO.PIC granule in ``modis_dir`` for a year range.

    Concatenates along time. The 2017-2019 default matches Carroll 2022's
    Green's-functions calibration window. Not every month is present in the
    archive (high-latitude polar darkness drops some January / February
    coverage) — the time dim ends up sparse, not regular monthly.

    Args:
        modis_dir: directory containing the downloaded granules.
        start_year, end_year: inclusive year range.
        resolution: ``"9km"`` (default) or ``"4km"``. 9km is sufficient when
            the downstream bin-averages to 1° anyway.

    Returns:
        ``xr.Dataset`` with dims ``(time, lat, lon)``, time sorted ascending.
    """
    modis_dir = Path(modis_dir)
    granules: list[Path] = []
    for p in sorted(modis_dir.glob("AQUA_MODIS.*.L3m.MO.PIC.pic.*.nc")):
        try:
            start, _, res = _parse_filename(p)
        except ValueError:
            continue
        if res != resolution:
            continue
        if not (start_year <= start.year <= end_year):
            continue
        granules.append(p)
    if not granules:
        raise FileNotFoundError(
            f"no MODIS-Aqua L3m.MO.PIC.{resolution} granules in {modis_dir} "
            f"for years {start_year}-{end_year}"
        )
    parts = [open_modis_pic(p) for p in granules]
    ds = xr.concat(parts, dim="time").sortby("time")
    return ds


def subset_aoi_modis(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Clip an MODIS-Aqua L3m dataset to a rectangular AOI.

    MODIS L3m latitude is **descending** (89.95° → -89.95°), unlike the
    ECCO-Darwin v05 grid which is ascending. ``.sel(lat=slice(...))`` on a
    descending coord needs ``slice(high, low)``; this helper detects the
    direction and flips the bounds if needed so callers can always pass
    ``slice(aoi.lat_min, aoi.lat_max)`` semantics.

    Args:
        ds: dataset opened by :func:`open_modis_pic` or :func:`open_climatology`.
        aoi: target AOI.

    Returns:
        Spatially clipped dataset.
    """
    lat = ds["lat"].values
    if lat[0] > lat[-1]:
        # descending: use high-to-low slice
        lat_slice = slice(aoi.lat_max, aoi.lat_min)
    else:
        lat_slice = slice(aoi.lat_min, aoi.lat_max)
    return ds.sel(lat=lat_slice, lon=slice(aoi.lon_min, aoi.lon_max))


def bin_to_1deg(
    da: xr.DataArray,
    aoi: AOI,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin-average a high-res MODIS field to a 1°×1° AOI grid.

    Cell centers align at integer + 0.5° to match the GEOTRACES loader
    convention. NaN-cells in the input are excluded from the mean (NumPy
    ``nanmean``); cells with NO finite source values become NaN in the
    output.

    Args:
        da: 2-D ``(lat, lon)`` DataArray with NaN for cloud / glint cells.
            Can also be a 3-D ``(time, lat, lon)`` DataArray, in which case
            we time-average first (via ``nanmean``) before spatial binning.
        aoi: target AOI giving the output grid bounds.
        lat_res, lon_res: output cell size in degrees. Default 1°.

    Returns:
        Tuple ``(values, mask)`` where ``values`` has shape ``(n_lat, n_lon)``
        in the same units as ``da`` (mol m⁻³ for PIC), and ``mask`` is a
        boolean array marking finite output cells.
    """
    if da.ndim == 3:
        da = da.mean(dim="time", skipna=True)
    if da.ndim != 2:
        raise ValueError(f"expected 2-D or 3-D DataArray, got {da.ndim}-D")

    lat = da["lat"].values
    lon = da["lon"].values
    arr = da.values

    if lat[0] > lat[-1]:
        # Flip to ascending for the binning math below.
        lat = lat[::-1]
        arr = arr[::-1, :]

    # Darwin v05 convention (matches llc270_loader.bin_to_1deg_grid): cell
    # centers at integer degrees INCLUSIVE of both endpoints, with bin edges
    # at integer +/- 0.5. eqpac (-5..15) -> 21 lat bins centered at -5..15.
    lat_centers = np.arange(aoi.lat_min, aoi.lat_max + lat_res / 2.0, lat_res)
    lon_centers = np.arange(aoi.lon_min, aoi.lon_max + lon_res / 2.0, lon_res)
    n_lat = len(lat_centers)
    n_lon = len(lon_centers)
    out = np.full((n_lat, n_lon), np.nan, dtype=np.float64)

    # Each source pixel falls into the bin whose center is closest. With edges
    # at center +/- 0.5, that's the same as floor((pixel - lat_min + 0.5) / res).
    lat_bin = np.floor((lat - aoi.lat_min + lat_res / 2.0) / lat_res).astype(np.int64)
    lon_bin = np.floor((lon - aoi.lon_min + lon_res / 2.0) / lon_res).astype(np.int64)

    # In-bounds mask per axis. Pixels exactly at the top boundary should
    # still bin into the last cell (floor would push them out).
    lat_ok = (lat_bin >= 0) & (lat_bin < n_lat + 1)
    lat_bin = np.minimum(lat_bin, n_lat - 1)
    lon_ok = (lon_bin >= 0) & (lon_bin < n_lon + 1)
    lon_bin = np.minimum(lon_bin, n_lon - 1)

    finite = np.isfinite(arr)
    # 2-D broadcast of the in-bounds masks.
    ok2d = lat_ok[:, None] & lon_ok[None, :] & finite

    # Build the flat (lat_bin, lon_bin) -> value list and reduce via
    # bincount + count for a nanmean equivalent.
    yi = np.broadcast_to(lat_bin[:, None], arr.shape)[ok2d]
    xi = np.broadcast_to(lon_bin[None, :], arr.shape)[ok2d]
    vals = arr[ok2d]

    flat_idx = yi * n_lon + xi
    n_cells = n_lat * n_lon
    sums = np.bincount(flat_idx, weights=vals.astype(np.float64), minlength=n_cells)
    counts = np.bincount(flat_idx, minlength=n_cells)
    nonzero = counts > 0
    flat_out = np.full(n_cells, np.nan, dtype=np.float64)
    flat_out[nonzero] = sums[nonzero] / counts[nonzero]
    out = flat_out.reshape(n_lat, n_lon)
    return out, nonzero.reshape(n_lat, n_lon)


def build_aoi_climatology(
    modis_dir: str | Path,
    aoi: AOI,
    start_year: int = 2017,
    end_year: int = 2019,
    resolution: str = "9km",
    lat_res: float = 1.0,
    lon_res: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """End-to-end: load monthly granules, AOI clip, time-mean, bin to 1°.

    The single most-likely entry point for DarwinDiff loss-term integration.
    Output is the multi-year-mean PIC field at the AOI's 1° Darwin-grid
    geometry. Units are MODIS-native mol m⁻³ — multiply by
    :data:`MOL_PER_M3_TO_MMOL_C_PER_M3` to align with DarwinDiff's internal
    mmol C m⁻³ convention.

    Args:
        modis_dir: directory of downloaded MODIS-Aqua L3m.MO.PIC granules.
        aoi: target AOI.
        start_year, end_year: inclusive year range. Default 2017-2019 matches
            Carroll 2022's calibration window.
        resolution: ``"9km"`` (default) or ``"4km"``.
        lat_res, lon_res: output 1° grid cell size.

    Returns:
        Tuple ``(values, mask)``:
            - ``values`` shape ``(n_lat, n_lon)``: AOI 1° PIC field, mol m⁻³,
              NaN where no finite source coverage.
            - ``mask`` shape ``(n_lat, n_lon)``: True where ``values`` is finite.
    """
    ds = open_climatology(modis_dir, start_year, end_year, resolution)
    ds = subset_aoi_modis(ds, aoi)
    return bin_to_1deg(ds["pic"], aoi, lat_res, lon_res)


def save_aoi_cache(
    modis_dir: str | Path,
    aoi_by_key: dict[str, AOI],
    cache_path: str | Path,
    start_year: int = 2017,
    end_year: int = 2019,
    resolution: str = "9km",
) -> None:
    """Pre-compute PIC climatologies for multiple AOIs and save to ``.npz``.

    Mirrors the ``darwin_ic_cache_*.npz`` pattern used elsewhere in the
    repo. The output file contains one ``pic_<key>`` and one ``mask_<key>``
    array per AOI, plus metadata.

    Args:
        modis_dir: directory of MODIS-Aqua L3m.MO.PIC granules.
        aoi_by_key: mapping from short string key (e.g. ``"eqpac"``) to AOI.
        cache_path: output path for the ``.npz`` file.
        start_year, end_year: year window. Default 2017-2019.
        resolution: source MODIS resolution to bin from.
    """
    payload: dict[str, np.ndarray] = {}
    for key, aoi in aoi_by_key.items():
        values, mask = build_aoi_climatology(
            modis_dir, aoi, start_year, end_year, resolution
        )
        payload[f"pic_{key}"] = values.astype(np.float32)
        payload[f"mask_{key}"] = mask.astype(np.bool_)
    payload["start_year"] = np.int32(start_year)
    payload["end_year"] = np.int32(end_year)
    payload["resolution_native"] = np.array(resolution, dtype="U8")
    payload["units"] = np.array("mol m^-3", dtype="U16")
    payload["source"] = np.array(
        "MODIS-Aqua L3m.MO.PIC v2022.0 (Balch & Gordon)", dtype="U64"
    )
    np.savez(cache_path, **payload)
