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
    Chl5  -> TRAC31    O2    -> TRAC23    PIC   -> TRAC17    POC   -> TRAC12

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
    "PIC": "TRAC17",
    "POC": "TRAC12",
    "POSi": "TRAC16",
    "PO4": "TRAC05",
    "SiO2": "TRAC07",
    "primProd": "PP",
    # 2-D surface physics / flux diagnostics (NATIVE_RES covariates). These are
    # NOT Darwin TRAC tracers — the value is the .meta fldList name. They are
    # single-level (nDims=[2]); see _2D_VARS for the dim handling in
    # open_llc270_tracer. fldList names verified against the on-disk .meta files.
    "SST": "THETA",
    "mldDepth": "MXLDEPTH",
    "wspeed": "EXFwspee",
    "apCO2": "EXFapco2",
    "CO2_flux": "fluxCO2",
}

# Friendly names whose on-disk field is 2-D (single level, nDims=[2]). For these
# open_llc270_tracer registers xmitgcm extra_variables with dims ["j","i"]
# instead of ["k","j","i"]; surface_layer() then no-ops (no "k" dim to pick).
_2D_VARS: set[str] = {"SST", "mldDepth", "wspeed", "apCO2", "CO2_flux"}

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
    "TRAC17": {"long_name": "Particulate inorganic carbon", "units": "mmol C / m^3"},
    "TRAC12": {"long_name": "Particulate organic carbon", "units": "mmol C / m^3"},
    "TRAC16": {"long_name": "Particulate biogenic silica", "units": "mmol Si / m^3"},
    "PP": {"long_name": "Primary production", "units": "mmol C / m^3 / s"},
    # 2-D surface physics / flux diagnostics (NATIVE_RES covariates).
    "THETA": {"long_name": "Sea surface temperature (potential)", "units": "degC"},
    "MXLDEPTH": {"long_name": "Mixed-layer depth", "units": "m"},
    "EXFwspee": {"long_name": "10 m wind speed", "units": "m / s"},
    "EXFapco2": {"long_name": "Atmospheric pCO2", "units": "uatm"},
    "fluxCO2": {"long_name": "Air-sea CO2 flux", "units": "mol C / m^2 / s"},
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

    # Register BOTH the MITgcm internal name (TRAC06) AND the file prefix
    # name (FeT) in extra_variables. Single-iter loads only need the TRAC name
    # (.meta fldList lookup), but multi-iter loads also probe the prefix name
    # somewhere in xmitgcm's setup path and error with "Couldn't find metadata
    # for variable FeT" if it isn't registered too. Registering both is harmless
    # for single-iter and required for multi-iter.
    attrs = _TRACER_ATTRS.get(trac_name, {"long_name": variable})
    # 2-D diagnostics (SST/MLD/wind/apCO2/CO2_flux) are single-level: register
    # with ["j","i"] so xmitgcm matches the .meta nDims=[2]; 3-D tracers use k.
    var_dims = ["j", "i"] if variable in _2D_VARS else ["k", "j", "i"]
    extra_vars = {
        trac_name: dict(dims=var_dims, attrs=attrs),
        variable: dict(dims=var_dims, attrs=attrs),
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
        # Required when loading multiple iters: xmitgcm can't auto-detect the
        # dtype across many .meta files and errors out with "Cannot find the
        # dtype associated to ...". The on-disk .meta files all say
        # `dataprec = [ 'float32' ]` so we hardcode np.float32 here.
        default_dtype=np.float32,
        # Some Darwin monthly .meta files have a multi-element fldList that
        # references TRAC numbers we don't have friendly names for in
        # TRAC_MAPPING (observed: TRAC12 in POC's meta). With the default
        # ignore_unknown_vars=False, xmitgcm raises KeyError on those. The
        # tracers we actually request via prefix=[variable] are correctly
        # registered above; ignoring the rest is safe.
        ignore_unknown_vars=True,
    )

    # Normalize to the friendly variable name. Three observed cases depending
    # on whether single or multiple iters were requested (xmitgcm's internal
    # path differs):
    #   - single iter: only TRAC06 in data_vars  -> rename TRAC06 -> FeT
    #   - multi iter:  both TRAC06 AND FeT in data_vars (xmitgcm loads the
    #                  same data under both registered names) -> drop TRAC06
    #   - hypothetical: only FeT -> already correct
    has_trac = trac_name in ds.data_vars
    has_friendly = variable in ds.data_vars
    if has_trac and has_friendly:
        ds = ds.drop_vars(trac_name)
    elif has_trac:
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


def bin_to_1deg_grid(
    xc: np.ndarray,
    yc: np.ndarray,
    values: np.ndarray,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
) -> np.ndarray:
    """Bin scattered native-cell (xc, yc, value) triples onto a 1° lat/lon grid.

    Edges are placed at ``lat_min - 0.5`` to ``lat_max + 0.5`` and similarly for
    longitude, so the resulting grid has integer-degree cell centers spanning
    the AOI inclusive of both endpoints (e.g. AOI ``5°S–15°N`` → 21 lat bins
    centered at ``-5, -4, …, +15``). This matches the ECCO-Darwin v05
    ``bin_average`` product's grid convention, enabling direct alignment with
    bin_average covariates (SST, MLD, Chl, CO₂ flux, pCO₂) in joint-loss fits.

    Args:
        xc, yc: cell-center longitude / latitude arrays, same shape as values.
        values: scalar values to average per bin (e.g. surface tracer field).
        lat_min, lat_max, lon_min, lon_max: AOI bounds in degrees,
            ``-180..180`` longitude convention.

    Returns:
        ``np.ndarray`` of shape ``(n_lat, n_lon)`` where
        ``n_lat = lat_max - lat_min + 1`` and likewise for longitude. NaN at
        bins with no native cells (land / outside the dataset coverage).

    Raises:
        ValueError: if input arrays have mismatched shape.
    """
    from scipy.stats import binned_statistic_2d

    if not (xc.shape == yc.shape == values.shape):
        raise ValueError(
            f"shape mismatch: xc={xc.shape}, yc={yc.shape}, values={values.shape}"
        )
    lat_edges = np.arange(lat_min - 0.5, lat_max + 0.5 + 1.0e-3, 1.0)
    lon_edges = np.arange(lon_min - 0.5, lon_max + 0.5 + 1.0e-3, 1.0)
    binned, _, _, _ = binned_statistic_2d(
        yc.ravel(),
        xc.ravel(),
        values.ravel(),
        statistic="mean",
        bins=[lat_edges, lon_edges],
    )
    return binned


def bin_native_tracer_to_1deg(
    monthly_root: str | Path,
    grid_dir: str | Path,
    variable: str,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    iters: int | list[int] | str = "all",
    config: LLC270Config = DEFAULT_CONFIG,
) -> np.ndarray:
    """Load LLC270 monthly tracer, time-mean surface field, bin-average to 1°.

    The full nb20-class loader: open the native tracer via
    :func:`open_llc270_tracer`, take ``k=0`` (surface), reduce over time with
    NaN-safe mean (climatology), AOI-mask via ``xc/yc`` cell centers, and
    bin-average onto the 1° lat/lon grid via :func:`bin_to_1deg_grid`.

    Result aligns with the ``bin_average`` product's 1° grid, so callers can
    stack it alongside bin_average covariates (SST, MLD, wind, Chl, CO₂_flux,
    pCO₂) for joint-loss fits without further regridding.

    Replaces the inline ``load_native_tracer`` cell in nb19 — nb20+ can call
    this directly.

    Args:
        monthly_root: parent ``monthly/`` directory.
        grid_dir: LLC270 grid metadata directory.
        variable: friendly TRAC name registered in :data:`TRAC_MAPPING`
            (e.g. ``"FeT"``, ``"DIC"``, ``"ALK"``, ``"POC"``, ``"PIC"``).
        lat_min, lat_max, lon_min, lon_max: AOI bounds in degrees.
        iters: passed to :func:`open_llc270_tracer`. ``"all"`` (default)
            loads every available iteration via
            :func:`list_available_iterations` and averages over them — the
            natural climatology behaviour used by nb11+.
        config: :class:`LLC270Config`.

    Returns:
        ``np.ndarray`` of shape ``(n_lat, n_lon)`` — surface time-mean tracer
        field bin-averaged onto the AOI's 1° grid. NaN at land / no-data cells.

    Raises:
        FileNotFoundError: if ``iters="all"`` and no iterations are on disk.
    """
    if iters == "all":
        iters = list_available_iterations(monthly_root, variable)
        if not iters:
            raise FileNotFoundError(
                f"no iterations available for {variable!r} under {monthly_root}"
            )

    ds = open_llc270_tracer(
        monthly_root, grid_dir, variable, iters=iters, config=config,
    )
    surf = surface_layer(ds)
    mean_field = surf[variable].mean(dim="time", skipna=True).values
    xc = surf.XC.values
    yc = surf.YC.values

    # Mask: inside AOI + finite + non-zero. The non-zero check excludes the
    # MITgcm land-fill (0.0 on land cells in mds binary), which otherwise
    # would skew the bin mean toward zero at coastal bins.
    aoi_good = (
        aoi_mask_from_xc_yc(xc, yc, lat_min, lat_max, lon_min, lon_max)
        & np.isfinite(mean_field)
        & (mean_field != 0)
    )

    return bin_to_1deg_grid(
        xc[aoi_good], yc[aoi_good], mean_field[aoi_good],
        lat_min, lat_max, lon_min, lon_max,
    )


def native_tracer_cells(
    monthly_root: str | Path,
    grid_dir: str | Path,
    variable: str,
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    iters: int | list[int] | str = "all",
    config: LLC270Config = DEFAULT_CONFIG,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Like :func:`bin_native_tracer_to_1deg` but KEEP native cells (no 1° bin).

    The building block for the native-resolution (``NATIVE_RES=1``) recovery
    path. Identical load → surface → time-mean → AOI/finite/non-zero mask as
    :func:`bin_native_tracer_to_1deg`, but instead of bin-averaging onto the 1°
    grid it returns the surviving native surface cells directly.

    ``flat_idx`` is each kept cell's index into the *raveled* native field. It
    is the **canonical alignment key**: because every monthly variable shares
    the identical LLC270 geometry, a cell with a given ``flat_idx`` is the same
    physical location in every variable. Callers reindex targets, covariates,
    and the IC onto one reference variable's ``flat_idx`` so all per-cell arrays
    line up cell-for-cell (a cell missing/non-finite in some variable becomes
    NaN there and is dropped by the combined mask).

    Args:
        monthly_root, grid_dir, variable, lat_min, lat_max, lon_min, lon_max,
        iters, config: as in :func:`bin_native_tracer_to_1deg`.

    Returns:
        ``(values, xc, yc, flat_idx)`` — four 1-D arrays of equal length
        ``n_cells`` (in-AOI, finite, non-zero surface cells): the time-mean
        tracer value, cell-center longitude, cell-center latitude, and the
        raveled-grid flat index of each cell.

    Raises:
        FileNotFoundError: if ``iters="all"`` and no iterations are on disk.
    """
    if iters == "all":
        iters = list_available_iterations(monthly_root, variable)
        if not iters:
            raise FileNotFoundError(
                f"no iterations available for {variable!r} under {monthly_root}"
            )

    ds = open_llc270_tracer(
        monthly_root, grid_dir, variable, iters=iters, config=config,
    )
    surf = surface_layer(ds)
    mean_field = surf[variable].mean(dim="time", skipna=True).values
    xc = surf.XC.values
    yc = surf.YC.values
    flat_idx = np.arange(mean_field.size).reshape(mean_field.shape)

    aoi_good = (
        aoi_mask_from_xc_yc(xc, yc, lat_min, lat_max, lon_min, lon_max)
        & np.isfinite(mean_field)
        & (mean_field != 0)
    )

    return (
        mean_field[aoi_good],
        xc[aoi_good],
        yc[aoi_good],
        flat_idx[aoi_good],
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
