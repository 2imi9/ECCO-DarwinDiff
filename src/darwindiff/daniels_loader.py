"""Loader for the Daniels et al. 2018 coccolithophore-calcification compilation.

This is the **Darwin-independent, observational** anchor for the Carroll-6
``R_PICPOC`` parameter (the PIC:POC *rain ratio* — calcite production per unit
organic-carbon production). It is the only direct, *surface-production* ratio
dataset that matches the box model's calcite term in kind:

    dPIC/dt = R_PICPOC * mort_total          (carroll6.py)

i.e. calcite production = R_PICPOC × organic-carbon production. The Daniels
compilation reports co-located ``CaCO3 production`` (CP) and ``primary
production`` (PP), both in **mmol C / m³ / day**, from ¹⁴C/¹³C incubations of
unperturbed water samples, so the per-sample rain ratio is simply

    rain_ratio = CP / PP                      (molar, dimensionless)

Why this loader exists — breaking the circularity
-------------------------------------------------
ECCO-Darwin (Carroll 2022) carries a single GLOBAL constant
``R_PICPOC = 0.04245`` (``carroll6.py:75``) that Carroll **never tuned to
rain-ratio data** (the Green's-functions optimization used pCO2 / CO2-flux /
alkalinity / nitrate / oxygen — no calcite-production target). Grading a
recovered ``R_PICPOC`` against Darwin's own PIC field is therefore circular.
Daniels supplies a real, georeferenced, per-region target that lets us ask
"what does direct calcite-production data say about the rain ratio, per AOI?"
See ``docs/findings/2026-06-26_rainratio_real_vs_darwin.md`` for the full
provenance and the regional-variability hypothesis this dataset tests.

Dataset
-------
Citation: Poulton, Daniels, Balch, et al. (2018), "Global compilation of
coccolithophore calcification measurements from unperturbed water samples",
PANGAEA, https://doi.org/10.1594/PANGAEA.888182 — the data behind Daniels et
al. (2018), ESSD 10, 1859–1876, https://doi.org/10.5194/essd-10-1859-2018.

Format: PANGAEA tab-separated text (``...?format=textfile``). A ``/* ... */``
metadata block precedes a single TSV header line, then the data rows. The
columns we use (all ASCII-clean) are:

    Latitude                          deg N (−180..180 lon convention already)
    Longitude                         deg E, −180..180
    Depth water [m]                   sample depth, 0–150 m
    CaCO3 prod C [mmol/m**3/day]      CP — calcite (PIC) production
    PP C [mmol/m**3/day]              PP — primary (POC) production

n = 2765 rows; 2751 have finite CP & PP. ~22 % of finite pairs have **CP = 0**
(real below-detection calcification); these are excluded from the geometric
mean because log(0) is undefined *and* the box's ratio is structurally
positive (``R_PICPOC > 0``), so a zero target is unrepresentable. The excluded
count is reported by :func:`bin_to_grid` / the cache so the bias is explicit.

The rain ratio is **log-normal**, spanning ~0.0002–6 per sample (global geomean
≈ 0.027, matching the published ~0.02). We therefore bin to **geometric means**
(``exp(mean(log r))``) per 1° cell and report cell counts — sparse coverage is
expected, and many AOIs (e.g. the Southern-Ocean-Pacific and N-Pacific
subtropical-gyre boxes) have **zero** Daniels coverage, in which case the
target mask is empty and any downstream loss term simply gates off there.

Units note
----------
Unlike GLODAP (µmol/kg) or GEOTRACES (nmol/kg), no unit conversion is needed:
CP and PP share units (mmol C/m³/day) so their ratio is dimensionless and
directly comparable to the box's per-cell PIC:POC ratio.

Quick usage::

    from darwindiff.daniels_loader import build_aoi_climatology
    from darwindiff.ecco_darwin_loader import EQUATORIAL_PACIFIC_AOI

    rpicpoc, mask, counts = build_aoi_climatology(EQUATORIAL_PACIFIC_AOI)
    # rpicpoc[mask] ~ 0.035 in the Eq Pacific (geometric mean per 1° cell).
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import NamedTuple

import numpy as np

from darwindiff.ecco_darwin_loader import AOI

# Default on-disk path. The raw .tab is gitignored under data/daniels/; override
# with the ``DANIELS_DATA_PATH`` env var at the call site (e.g. the cluster copy
# under /projects/schultz/qi.zim). Anchored to the repo via __file__ so it works
# regardless of the process CWD, mirroring the GLODAP loader convention.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DANIELS_PATH: Path = (
    _REPO_ROOT / "data" / "daniels" / "Daniels_etal_2018_PANGAEA_888182.tab"
)

# Exact PANGAEA column headers (ASCII-clean — the std-dev columns carry a
# mojibake ``±`` we never read, so we address columns by these names only).
COL_LAT = "Latitude"
COL_LON = "Longitude"
COL_DEPTH = "Depth water [m]"
COL_CP = "CaCO3 prod C [mmol/m**3/day]"   # calcite (PIC) production
COL_PP = "PP C [mmol/m**3/day]"           # primary (organic-C / POC) production

# Surface restriction (m). The box is a surface mixed-layer model (H_MLD≈50 m),
# and the rain ratio shoals with light, so a surface cut keeps the target
# comparable to the box's surface PIC:POC. Matches the GEOTRACES surface cut.
DEFAULT_DEPTH_MAX = 50.0


class DanielsPoints(NamedTuple):
    """Flat per-sample arrays parsed from the Daniels compilation.

    All arrays share shape ``(n_samples,)``. ``cp`` and ``pp`` are in
    mmol C/m³/day; their ratio (:func:`rain_ratio`) is the dimensionless
    PIC:POC production ratio. Non-numeric / empty cells parse to ``NaN``.
    """

    lat: np.ndarray
    lon: np.ndarray
    depth: np.ndarray
    cp: np.ndarray
    pp: np.ndarray


def _data_start_index(lines: list[str]) -> int:
    """Return the index of the TSV header line (first line after ``*/``).

    PANGAEA textfiles wrap the metadata in a ``/* ... */`` block; the column
    header row immediately follows the closing ``*/``.
    """
    for i, line in enumerate(lines):
        if line.strip() == "*/":
            return i + 1
    # No metadata block (already-stripped TSV): assume row 0 is the header.
    return 0


def _to_float(cell: str) -> float:
    """Parse one TSV cell to float, mapping empty / non-numeric → NaN."""
    cell = cell.strip()
    if not cell:
        return np.nan
    try:
        return float(cell)
    except ValueError:
        return np.nan


def load_daniels_points(path: str | Path = DEFAULT_DANIELS_PATH) -> DanielsPoints:
    """Parse the PANGAEA .tab into flat per-sample arrays.

    Reads only the five columns we need (lat, lon, depth, CP, PP), addressed by
    header name so column-order changes in a re-download don't silently corrupt
    the parse.

    Args:
        path: path to ``Daniels_etal_2018_PANGAEA_888182.tab``.

    Returns:
        :class:`DanielsPoints` with arrays of shape ``(n_samples,)``.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        KeyError: if an expected column header is missing.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Daniels compilation not found: {path}\n"
            "Download with:\n"
            '  curl -sL "https://doi.pangaea.de/10.1594/PANGAEA.888182'
            '?format=textfile" -o '
            f'"{path}"'
        )
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()

    start = _data_start_index(lines)
    reader = csv.reader(lines[start:], delimiter="\t")
    header = next(reader)
    try:
        idx = {
            name: header.index(name)
            for name in (COL_LAT, COL_LON, COL_DEPTH, COL_CP, COL_PP)
        }
    except ValueError as exc:  # .index miss
        raise KeyError(
            f"expected Daniels column missing from header {header!r}: {exc}"
        ) from exc

    n_cols = len(header)
    lat, lon, depth, cp, pp = [], [], [], [], []
    for row in reader:
        if not row or len(row) < n_cols:
            continue  # ragged / blank trailing line
        lat.append(_to_float(row[idx[COL_LAT]]))
        lon.append(_to_float(row[idx[COL_LON]]))
        depth.append(_to_float(row[idx[COL_DEPTH]]))
        cp.append(_to_float(row[idx[COL_CP]]))
        pp.append(_to_float(row[idx[COL_PP]]))

    return DanielsPoints(
        lat=np.asarray(lat, dtype=np.float64),
        lon=np.asarray(lon, dtype=np.float64),
        depth=np.asarray(depth, dtype=np.float64),
        cp=np.asarray(cp, dtype=np.float64),
        pp=np.asarray(pp, dtype=np.float64),
    )


def rain_ratio(points: DanielsPoints) -> np.ndarray:
    """Per-sample PIC:POC rain ratio CP/PP (NaN where either is NaN / PP≤0)."""
    with np.errstate(divide="ignore", invalid="ignore"):
        r = points.cp / points.pp
    r[~np.isfinite(r)] = np.nan
    return r


def valid_surface_mask(
    points: DanielsPoints,
    depth_max: float = DEFAULT_DEPTH_MAX,
    require_positive: bool = True,
) -> np.ndarray:
    """Boolean mask of usable surface samples.

    Keeps samples with finite lat/lon, ``depth <= depth_max``, and finite CP &
    PP. With ``require_positive`` (default), additionally requires CP>0 and
    PP>0 — the precondition for the log-space geometric mean. Samples with
    CP=0 (below-detection calcification) are dropped from the geomean but can
    be counted separately by the caller via ``require_positive=False``.
    """
    base = (
        np.isfinite(points.lat)
        & np.isfinite(points.lon)
        & np.isfinite(points.depth)
        & (points.depth <= depth_max)
        & np.isfinite(points.cp)
        & np.isfinite(points.pp)
    )
    if require_positive:
        base = base & (points.cp > 0) & (points.pp > 0)
    return base


def bin_to_grid(
    points: DanielsPoints,
    lat_centers: np.ndarray,
    lon_centers: np.ndarray,
    depth_max: float = DEFAULT_DEPTH_MAX,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bin per-sample rain ratios to **geometric means** on an explicit grid.

    The grid is given by 1-D cell-center arrays (e.g. an AOI's
    ``darwin_lats`` / ``darwin_lons``), with bin edges at center ± res/2 —
    the exact convention the GEOTRACES point-binning in
    ``run_v3.0_joint_multi_aoi.py`` uses, so a Daniels target lands on the same
    cells as the iron target.

    Geometric mean per cell is ``exp(mean(log r))`` accumulated in log space,
    which is the natural average for the log-normal rain ratio.

    Args:
        points: parsed samples.
        lat_centers, lon_centers: 1-D, monotonically increasing cell centers.
        depth_max: surface cut (m).

    Returns:
        ``(values, mask, counts)``:
            - ``values`` ``(n_lat, n_lon)``: per-cell geometric-mean rain ratio,
              NaN where no positive-ratio samples fell in the cell.
            - ``mask`` ``(n_lat, n_lon)`` bool: True where ``values`` is finite.
            - ``counts`` ``(n_lat, n_lon)`` int: number of samples per cell.
    """
    lat_centers = np.asarray(lat_centers, dtype=np.float64)
    lon_centers = np.asarray(lon_centers, dtype=np.float64)
    n_lat = len(lat_centers)
    n_lon = len(lon_centers)
    lat_res = float(lat_centers[1] - lat_centers[0]) if n_lat > 1 else 1.0
    lon_res = float(lon_centers[1] - lon_centers[0]) if n_lon > 1 else 1.0
    lat_lo = lat_centers[0] - lat_res / 2.0
    lon_lo = lon_centers[0] - lon_res / 2.0
    lat_hi = lat_centers[-1] + lat_res / 2.0
    lon_hi = lon_centers[-1] + lon_res / 2.0

    # Unlike the modis / GEOTRACES binners (which receive data already clipped
    # to the AOI), this is fed the GLOBAL point cloud, so we must restrict to
    # the grid's bounding box explicitly — index-clipping alone would fold every
    # out-of-box sample into the edge cells. Endpoints inclusive (a sample on
    # the top edge floors to the last cell after the clip below).
    keep = valid_surface_mask(points, depth_max, require_positive=True)
    keep = (
        keep
        & (points.lat >= lat_lo) & (points.lat <= lat_hi)
        & (points.lon >= lon_lo) & (points.lon <= lon_hi)
    )
    lats = points.lat[keep]
    lons = points.lon[keep]
    log_r = np.log(points.cp[keep] / points.pp[keep])

    lat_idx = np.floor((lats - lat_lo) / lat_res).astype(np.int64)
    lon_idx = np.floor((lons - lon_lo) / lon_res).astype(np.int64)
    # A sample exactly on the top/right edge floors to n; clamp it into the
    # last cell (everything outside the box was already dropped above).
    lat_idx = np.clip(lat_idx, 0, n_lat - 1)
    lon_idx = np.clip(lon_idx, 0, n_lon - 1)

    log_sum = np.zeros((n_lat, n_lon), dtype=np.float64)
    counts = np.zeros((n_lat, n_lon), dtype=np.float64)
    np.add.at(log_sum, (lat_idx, lon_idx), log_r)
    np.add.at(counts, (lat_idx, lon_idx), 1.0)

    mask = counts > 0
    values = np.full((n_lat, n_lon), np.nan, dtype=np.float64)
    values[mask] = np.exp(log_sum[mask] / counts[mask])
    return values, mask, counts.astype(np.int64)


def _aoi_centers(
    aoi: AOI, lat_res: float = 1.0, lon_res: float = 1.0
) -> tuple[np.ndarray, np.ndarray]:
    """1° cell centers for an AOI (integer-degree centers, Darwin convention)."""
    lat_centers = np.arange(aoi.lat_min, aoi.lat_max + lat_res / 2.0, lat_res)
    lon_centers = np.arange(aoi.lon_min, aoi.lon_max + lon_res / 2.0, lon_res)
    return lat_centers, lon_centers


def build_aoi_climatology(
    aoi: AOI,
    daniels_path: str | Path = DEFAULT_DANIELS_PATH,
    depth_max: float = DEFAULT_DEPTH_MAX,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
    points: DanielsPoints | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """End-to-end: load samples, bin to the AOI's 1° grid (geometric means).

    The single most-likely entry point for DarwinDiff loss-term integration
    (mirrors ``modis_pic_loader.build_aoi_climatology``). Output is the per-AOI
    real ``R_PICPOC`` target field at the AOI's 1° geometry.

    Args:
        aoi: target AOI.
        daniels_path: path to the .tab (ignored if ``points`` is given).
        depth_max: surface cut (m). Default 50 m.
        lat_res, lon_res: output grid cell size in degrees.
        points: pre-parsed :class:`DanielsPoints` (avoids re-reading the file
            when building several AOIs in a loop).

    Returns:
        ``(values, mask, counts)`` — see :func:`bin_to_grid`.
    """
    if points is None:
        points = load_daniels_points(daniels_path)
    lat_centers, lon_centers = _aoi_centers(aoi, lat_res, lon_res)
    return bin_to_grid(points, lat_centers, lon_centers, depth_max)


def save_aoi_cache(
    aoi_by_key: dict[str, AOI],
    cache_path: str | Path,
    daniels_path: str | Path = DEFAULT_DANIELS_PATH,
    depth_max: float = DEFAULT_DEPTH_MAX,
) -> None:
    """Pre-compute per-AOI ``R_PICPOC`` targets and save to ``.npz``.

    Mirrors ``modis_pic_loader.save_aoi_cache``. The output file contains, per
    AOI key, ``rpicpoc_<key>`` (geometric-mean rain ratio), ``mask_<key>``, and
    ``count_<key>`` (samples per cell), plus dataset metadata.

    Args:
        aoi_by_key: mapping short key (e.g. ``"eqpac"``) → AOI.
        cache_path: output ``.npz`` path.
        daniels_path: path to the .tab.
        depth_max: surface cut (m).
    """
    points = load_daniels_points(daniels_path)
    payload: dict[str, np.ndarray] = {}
    for key, aoi in aoi_by_key.items():
        values, mask, counts = build_aoi_climatology(
            aoi, depth_max=depth_max, points=points
        )
        payload[f"rpicpoc_{key}"] = values.astype(np.float32)
        payload[f"mask_{key}"] = mask.astype(np.bool_)
        payload[f"count_{key}"] = counts.astype(np.int32)
    payload["depth_max"] = np.float32(depth_max)
    payload["units"] = np.array("dimensionless (mol PIC-C / mol POC-C)", dtype="U48")
    payload["source"] = np.array(
        "Daniels et al. 2018 CP:PP (PANGAEA 888182)", dtype="U48"
    )
    np.savez(cache_path, **payload)
