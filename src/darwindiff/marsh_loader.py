"""Loader for the Marsh et al. 2025 coccolithophore-calcification compilation.

The **updated successor to Daniels/Poulton et al. 2018** (:mod:`darwindiff.daniels_loader`):
same direct, Darwin-independent PIC:POC *production*-ratio measurements (co-located CaCO3
production `CP` and primary production `PP` from ¹⁴C incubations of unperturbed water),
but with **+400 new CP measurements** (n = 3165 vs 2765) and co-located ancillary
carbonate chemistry / hydrography. This is the load-bearing data upgrade for the E2 gate:
more non-circular calcite points directly attack the `n_train` sparsity that made the
learned closure over-fit the held-out env band.

Citation: Marsh, N.L.J. et al. (2025), "Updated global compilation of coccolithophore
calcification measurements from unperturbed water samples including ancillary data",
PANGAEA, https://doi.org/10.1594/PANGAEA.987673 (paper: Biogeosciences 22, 3681-3697,
https://doi.org/10.5194/bg-22-3681-2025).

Format: identical PANGAEA tab-separated structure to Daniels (a ``/* ... */`` metadata
block, then a TSV header, then rows), so this loader **reuses the Daniels binning
machinery unchanged** — it only parses the (renamed) columns into the shared
:class:`darwindiff.daniels_loader.DanielsPoints` and hands them to
:func:`darwindiff.daniels_loader.build_aoi_climatology` via its ``points=`` hook. The
per-AOI geometric-mean rain ratio, mask, and counts come out on the *same* 1° grid as
Daniels, so this is a drop-in target swap for :func:`darwindiff.held_out_obs.held_out_calcite_obs`.

**Units note (the crux):** Marsh reports CP and PP in **µmol** C/m³/day (Daniels used
**mmol**). The rain ratio ``CP/PP`` is **dimensionless**, so the µmol-vs-mmol difference
**cancels** and the geometric-mean rain ratio is directly comparable to Daniels' — no
conversion needed. Columns are addressed by robust name-prefix (not the exact µ-unicode
header) so a re-download or an encoding wobble in the ``[µmol/m**3/day]`` unit string does
not silently break the parse.
"""
from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from darwindiff.daniels_loader import (
    DanielsPoints,
    _data_start_index,
    _to_float,
    build_aoi_climatology as _daniels_build,
)
from darwindiff.ecco_darwin_loader import AOI

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MARSH_PATH: Path = (
    _REPO_ROOT / "data" / "marsh" / "Marsh_etal_2025_coccolith_calcification.tab"
)


def _find_col(header: list[str], *, startswith: str, exclude: str | None = None) -> int:
    """Index of the first header cell starting with ``startswith`` (excluding ``exclude``).

    Robust to the µmol-unit unicode and to std-dev companion columns: e.g. CP is the
    ``CaCO3 prod C [µmol/m**3/day]`` column, matched by the ``"CaCO3 prod C"`` prefix while
    excluding the adjacent ``"CaCO3 prod C std dev [±]"`` via ``exclude="std"``.
    """
    for i, name in enumerate(header):
        n = name.strip()
        if n.startswith(startswith) and (exclude is None or exclude not in n):
            return i
    raise KeyError(
        f"expected Marsh column starting {startswith!r} (exclude {exclude!r}) not in "
        f"header {header!r}"
    )


def load_marsh_points(path: str | Path = DEFAULT_MARSH_PATH) -> DanielsPoints:
    """Parse the Marsh 2025 PANGAEA .tab into the shared :class:`DanielsPoints`.

    ``cp`` / ``pp`` are returned in the file's native µmol C/m³/day (the ratio is
    dimensionless, so downstream geomean binning matches Daniels' mmol exactly). Columns
    are located by name-prefix so the parse survives the µ-unicode / std-dev-column layout.

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        KeyError: if an expected column prefix is missing from the header.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"Marsh compilation not found: {path}\n"
            'Download (PANGAEA, public):\n'
            '  curl -sL "https://doi.pangaea.de/10.1594/PANGAEA.987673?format=textfile" '
            f'-o "{path}"'
        )
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()

    start = _data_start_index(lines)
    reader = csv.reader(lines[start:], delimiter="\t")
    header = next(reader)
    i_lat = _find_col(header, startswith="Latitude")
    i_lon = _find_col(header, startswith="Longitude")
    i_depth = _find_col(header, startswith="Depth water")
    i_cp = _find_col(header, startswith="CaCO3 prod C", exclude="std")
    i_pp = _find_col(header, startswith="PP C", exclude="std")
    n_cols = len(header)

    lat, lon, depth, cp, pp = [], [], [], [], []
    for row in reader:
        if not row or len(row) < n_cols:
            continue
        lat.append(_to_float(row[i_lat]))
        lon.append(_to_float(row[i_lon]))
        depth.append(_to_float(row[i_depth]))
        cp.append(_to_float(row[i_cp]))
        pp.append(_to_float(row[i_pp]))

    return DanielsPoints(
        lat=np.asarray(lat, dtype=np.float64),
        lon=np.asarray(lon, dtype=np.float64),
        depth=np.asarray(depth, dtype=np.float64),
        cp=np.asarray(cp, dtype=np.float64),
        pp=np.asarray(pp, dtype=np.float64),
    )


def build_aoi_climatology(
    aoi: AOI,
    marsh_path: str | Path = DEFAULT_MARSH_PATH,
    depth_max: float = 50.0,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
    points: DanielsPoints | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-AOI geometric-mean rain-ratio target on the shared 1° grid (Marsh 2025).

    Signature-compatible with :func:`darwindiff.daniels_loader.build_aoi_climatology`
    (returns ``(values, mask, counts)``) so it is a drop-in target swap. Delegates the
    binning to the Daniels machinery with Marsh-parsed points.
    """
    if points is None:
        points = load_marsh_points(marsh_path)
    return _daniels_build(
        aoi, depth_max=depth_max, lat_res=lat_res, lon_res=lon_res, points=points,
    )
