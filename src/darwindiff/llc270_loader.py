"""Loader for ECCO-Darwin v05 native LLC270 monthly tracer fields.

Source data: ``D:\\ecco_darwin_v5\\output\\monthly\\<VAR>\\<VAR>.NNNNNNNNNN.data``
plus matching ``.meta`` sidecars, in MITgcm's mds binary format. Each
``.data`` file is a single global state for one tracer at one timestep,
181 MB at full LLC270 native resolution (270 x 270 cells x 13 faces x 50
depth levels, single precision). Companion grid metadata at
``D:\\ecco_darwin_v5\\grid\\``.

Companion to :mod:`darwindiff.ecco_darwin_loader` (which handles the
``bin_average`` 1-deg NetCDF product). This module is for the much larger,
depth-resolved native-tile product that gives us the full BGC tracer
state (NO3, DIC, ALK, FeT, DOC, etc.).

**Why this is its own module.** The data format is fundamentally different
(MITgcm mds binary vs NetCDF), the spatial grid is different (LLC native
13-face tiles vs regular 1-deg lat/lon), and the access pattern is
different (one variable per directory, sparse iteration timestamps). Mixing
these into ``ecco_darwin_loader`` would muddle two API contracts.

**MITgcm field-name quirk.** Files are named ``ALK.NNNN.data`` etc., but
the ``.meta`` sidecar's ``fldList`` records the variable as a generic
``TRAC18`` (Darwin's internal tracer index). We register the TRAC names
with xmitgcm via ``extra_variables`` and rename to the friendly names
after loading.

**Tracer index mapping** (Darwin v05 / Carroll 2022 setup, extracted from
``v05/llc270/input/data.darwin`` and verified against the on-disk .meta
files):

    ALK   -> TRAC18    DIC   -> TRAC01    NO2   -> TRAC03    NO3   -> TRAC02
    NH4   -> TRAC04    PO4   -> TRAC05    FeT   -> TRAC06    SiO2  -> TRAC07
    DOC   -> TRAC08    DON   -> TRAC09    DOP   -> TRAC10    DOFe  -> TRAC11
    Chl1  -> TRAC27    Chl2  -> TRAC28    Chl3  -> TRAC29    Chl4  -> TRAC30
    Chl5  -> TRAC31    O2    -> TRAC23    PIC   -> TRAC32    POC   -> TRAC33

(The list above includes a few tracers whose monthly data may not be on
disk yet — `inspect_available_tracers` discovers what's actually present.)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import xarray as xr

# Mapping from friendly directory name to MITgcm internal TRAC variable name.
# Verified for the v05 Carroll-2022 setup against the on-disk .meta files.
# Authoritative source for any future additions: read the .meta sidecar's
# ``fldList`` field (one MITgcm var per file).
TRAC_MAPPING: dict[str, str] = {
    "ALK": "TRAC18",
    "Chl1": "TRAC27",
    "Chl2": "TRAC28",
    "Chl3": "TRAC29",
    "Chl4": "TRAC30",
    "Chl5": "TRAC31",
    "DIC": "TRAC01",
    "DOC": "TRAC08",
    "DOFe": "TRAC11",
    "DON": "TRAC09",
    "DOP": "TRAC10",
    "FeT": "TRAC06",
    "NH4": "TRAC04",
    "NO2": "TRAC03",
    "NO3": "TRAC02",
    "O2": "TRAC23",
    "PIC": "TRAC32",
    "POC": "TRAC33",
    "PO4": "TRAC05",
    "SiO2": "TRAC07",
}

# Friendly attribute metadata per tracer for xmitgcm's extra_variables. Units
# follow Darwin's mmol/m^3 convention for nutrients (alkalinity in
# meq/m^3 = mmol/m^3 in standard ocean BGC convention; check published
# Carroll 2022 supplementary if you need authoritative units).
_TRACER_ATTRS: dict[str, dict[str, str]] = {
    "TRAC01": {"long_name": "Dissolved inorganic carbon", "units": "mmol C / m^3"},
    "TRAC02": {"long_name": "Nitrate", "units": "mmol N / m^3"},
    "TRAC03": {"long_name": "Nitrite", "units": "mmol N / m^3"},
    "TRAC04": {"long_name": "Ammonium", "units": "mmol N / m^3"},
    "TRAC05": {"long_name": "Phosphate", "units": "mmol P / m^3"},
    "TRAC06": {"long_name": "Total iron", "units": "mmol Fe / m^3"},
    "TRAC07": {"long_name": "Silicate", "units": "mmol Si / m^3"},
    "TRAC08": {"long_name": "Dissolved organic carbon", "units": "mmol C / m^3"},
    "TRAC09": {"long_name": "Dissolved organic nitrogen", "units": "mmol N / m^3"},
    "TRAC10": {"long_name": "Dissolved organic phosphorus", "units": "mmol P / m^3"},
    "TRAC11": {"long_name": "Dissolved organic iron", "units": "mmol Fe / m^3"},
    "TRAC18": {"long_name": "Total alkalinity", "units": "meq / m^3"},
    "TRAC23": {"long_name": "Dissolved oxygen", "units": "mmol O2 / m^3"},
    "TRAC27": {"long_name": "Chl group 1", "units": "mg Chl a / m^3"},
    "TRAC28": {"long_name": "Chl group 2", "units": "mg Chl a / m^3"},
    "TRAC29": {"long_name": "Chl group 3", "units": "mg Chl a / m^3"},
    "TRAC30": {"long_name": "Chl group 4", "units": "mg Chl a / m^3"},
    "TRAC31": {"long_name": "Chl group 5", "units": "mg Chl a / m^3"},
    "TRAC32": {"long_name": "Particulate inorganic carbon", "units": "mmol C / m^3"},
    "TRAC33": {"long_name": "Particulate organic carbon", "units": "mmol C / m^3"},
}


@dataclass(frozen=True)
class LLC270Config:
    """Configuration for opening LLC270 monthly tracer data.

    Defaults match the ECCO-Darwin v05 (Carroll 2022) setup as documented
    in ``MITgcm-contrib/ecco_darwin/v05/llc270/``.

    Attributes:
        delta_t: MITgcm timestep in seconds. v05 LLC270 uses 900 (15 min).
        ref_date: simulation start date for converting iter -> calendar time.
            v05 starts 1992-01-01 per the v05 namelist.
        nx: horizontal tile size. LLC270 = 270.
        nz: vertical levels. v05 = 50.
    """

    delta_t: int = 900
    ref_date: str = "1992-01-01"
    nx: int = 270
    nz: int = 50


DEFAULT_CONFIG: LLC270Config = LLC270Config()


def discover_tracer_meta(monthly_root: str | Path) -> dict[str, str]:
    """Walk a monthly/ tree and read .meta sidecars to build the directory
    name -> MITgcm TRAC name mapping.

    Use this to refresh :data:`TRAC_MAPPING` if a new tracer is added or to
    sanity-check that the on-disk data matches our hardcoded mapping.

    Args:
        monthly_root: path to the parent ``monthly/`` directory containing
            per-tracer subdirs (e.g. ``D:\\ecco_darwin_v5\\output\\monthly``).

    Returns:
        ``dict`` mapping each variable directory name (e.g. ``"ALK"``) to
        its MITgcm TRAC variable name (e.g. ``"TRAC18"``).
    """
    monthly_root = Path(monthly_root)
    out: dict[str, str] = {}
    if not monthly_root.is_dir():
        raise FileNotFoundError(f"monthly_root not found: {monthly_root}")
    for entry in sorted(monthly_root.iterdir()):
        if not entry.is_dir():
            continue
        metas = sorted(p for p in entry.iterdir() if p.suffix == ".meta")
        if not metas:
            continue
        content = metas[0].read_text()
        m = re.search(r"fldList = \{\s*'(\S+)\s*'\s*\}", content)
        if m:
            out[entry.name] = m.group(1)
    return out


def list_available_iterations(monthly_root: str | Path, variable: str) -> list[int]:
    """List all iteration timestamps available on disk for a given tracer.

    Args:
        monthly_root: parent ``monthly/`` directory.
        variable: directory name (e.g. ``"ALK"``).

    Returns:
        Sorted list of iteration numbers from the ``.data`` filenames.
    """
    var_dir = Path(monthly_root) / variable
    if not var_dir.is_dir():
        raise FileNotFoundError(f"variable directory not found: {var_dir}")
    iters: list[int] = []
    pat = re.compile(rf"{re.escape(variable)}\.(\d+)\.data$")
    for p in var_dir.iterdir():
        m = pat.match(p.name)
        if m:
            iters.append(int(m.group(1)))
    return sorted(iters)


def open_llc270_tracer(
    monthly_root: str | Path,
    grid_dir: str | Path,
    variable: str,
    iters: int | list[int] | str = "first",
    config: LLC270Config = DEFAULT_CONFIG,
) -> xr.Dataset:
    """Open one LLC270 monthly tracer with xmitgcm, friendly-renamed.

    Wrapper around :func:`xmitgcm.open_mdsdataset` that:

    1. Looks up the MITgcm TRAC name for the requested variable (e.g.
       ``"ALK" -> "TRAC18"``) from :data:`TRAC_MAPPING`.
    2. Registers the TRAC name with xmitgcm's ``extra_variables`` so the
       loader doesn't reject it as unknown.
    3. Opens the dataset.
    4. Renames the loaded TRAC variable back to the friendly name.

    Args:
        monthly_root: parent ``monthly/`` directory containing per-tracer
            subdirectories (e.g. ``D:\\ecco_darwin_v5\\output\\monthly``).
        grid_dir: directory with LLC270 grid metadata (e.g.
            ``D:\\ecco_darwin_v5\\grid``).
        variable: friendly variable name (key of :data:`TRAC_MAPPING`),
            e.g. ``"ALK"``, ``"DIC"``, ``"NO3"``, ``"FeT"``.
        iters: which iteration timestamps to load. Pass an int for one,
            a list for several, ``"first"`` for the earliest available,
            or ``"all"`` for everything (large!).
        config: :class:`LLC270Config` with delta_t, ref_date, nx.

    Returns:
        ``xr.Dataset`` with dims ``(time, k, face, j, i)`` and the named
        tracer plus all LLC270 grid coordinates (XC, YC, etc.).
    """
    import xmitgcm  # heavy optional dep; import lazily

    if variable not in TRAC_MAPPING:
        raise KeyError(
            f"unknown variable {variable!r}; known: {sorted(TRAC_MAPPING)}. "
            f"To register a new variable, read its .meta sidecar's fldList "
            f"and add to TRAC_MAPPING + _TRACER_ATTRS."
        )
    trac_name = TRAC_MAPPING[variable]

    var_dir = Path(monthly_root) / variable
    if not var_dir.is_dir():
        raise FileNotFoundError(f"variable directory not found: {var_dir}")

    if iters == "first":
        all_iters = list_available_iterations(monthly_root, variable)
        if not all_iters:
            raise FileNotFoundError(f"no iterations found in {var_dir}")
        iters = [all_iters[0]]
    elif isinstance(iters, int):
        iters = [iters]

    extra_vars = {
        trac_name: dict(
            dims=["k", "j", "i"],
            attrs=_TRACER_ATTRS.get(trac_name, {"long_name": variable}),
        ),
    }

    ds = xmitgcm.open_mdsdataset(
        data_dir=str(var_dir),
        grid_dir=str(grid_dir),
        prefix=[variable],
        iters=iters,
        delta_t=config.delta_t,
        ref_date=config.ref_date,
        geometry="llc",
        nx=config.nx,
        extra_variables=extra_vars,
    )

    if trac_name in ds.data_vars:
        ds = ds.rename({trac_name: variable})

    return ds


def aoi_mask_from_xc_yc(
    xc: xr.DataArray | np.ndarray,
    yc: xr.DataArray | np.ndarray,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> np.ndarray:
    """Boolean mask of which LLC native cells fall in a lat/lon bounding box.

    LLC270 tiles are not lat/lon-rectified; each cell has its own (XC, YC)
    coordinate. AOI subset means picking the cells whose XC/YC fall in the
    requested bbox. Caller is responsible for applying the mask to data
    (e.g. ``data.where(mask, drop=False)`` or fancy indexing).

    Args:
        xc, yc: cell-center longitude / latitude arrays. Either xr.DataArrays
            (with the LLC tile dims) or plain ndarrays of matching shape.
        lat_min, lat_max, lon_min, lon_max: bbox in degrees. Use
            ``-180..180`` longitude convention to match LLC270's XC.

    Returns:
        Boolean ndarray of the same shape as xc/yc, True inside the bbox.
    """
    xc_arr = xc.values if isinstance(xc, xr.DataArray) else xc
    yc_arr = yc.values if isinstance(yc, xr.DataArray) else yc
    return (
        (yc_arr >= lat_min)
        & (yc_arr <= lat_max)
        & (xc_arr >= lon_min)
        & (xc_arr <= lon_max)
    )


def surface_layer(ds: xr.Dataset) -> xr.Dataset:
    """Pick the surface depth level (k=0) from an LLC270 tracer dataset.

    Args:
        ds: dataset returned by :func:`open_llc270_tracer` with a ``k`` dim.

    Returns:
        Dataset with ``k`` removed (or set to length 1 if xarray doesn't drop).
    """
    if "k" not in ds.dims:
        return ds
    return ds.isel(k=0).drop_vars("k", errors="ignore")
