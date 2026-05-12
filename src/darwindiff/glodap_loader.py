"""Loader for the GLODAPv2.2016b mapped-climatology NetCDFs.

GLODAPv2.2016b is a 1°×1° gridded BGC climatology produced by NOAA's Global
Ocean Data Analysis Project. Used by DarwinDiff v2.1+ when calibrating
against **real ocean observations** instead of ECCO-Darwin model output —
the path to a "DarwinDiff parameters beat Carroll's parameters at matching
observations" claim that the v2.0 fit-against-Darwin-output result alone
cannot support.

Variables on disk (after extracting `GLODAPv2.2016b_MappedClimatologies.tar.gz`):

    TCO2          — Dissolved inorganic carbon (DIC), µmol/kg
    TAlk          — Total alkalinity, µmol/kg
    NO3           — Nitrate, µmol/kg
    PO4           — Phosphate, µmol/kg
    silicate      — Silicate, µmol/kg
    oxygen        — Dissolved oxygen, µmol/kg
    temperature   — Potential temperature, °C
    salinity      — Practical salinity, PSU
    pHts25p0      — pH on total scale at 25 °C, 0 dbar
    pHtsinsitutp  — pH on total scale at in-situ T, P
    Cant          — Anthropogenic CO₂, µmol/kg
    PI_TCO2       — Pre-industrial DIC, µmol/kg
    OmegaA        — Aragonite saturation state (dimensionless)
    OmegaC        — Calcite saturation state (dimensionless)

Grid:

    - lon: 360 cells centered on integer °E + 0.5 offset (range ~20.5–379.5,
      i.e. 0–360 convention with a roll). Normalized here to −180..180.
    - lat: 180 cells centered −89.5..+89.5.
    - depth_surface: 33 vertical levels, 0 = shallowest (~0 m), 32 = ~5500 m.

Source: NOAA NCEI accession 0162565
        https://www.ncei.noaa.gov/data/oceans/ncei/ocads/data/0162565/mapped/

Unit convention note: GLODAP reports concentrations as µmol per kg of
seawater. The DarwinDiff box model uses mmol per m³. At surface seawater
density (ρ_sw ≈ 1025 kg/m³):

    1 µmol/kg × 1025 kg/m³ = 1025 µmol/m³ = 1.025 mmol/m³

Equivalently, multiply GLODAP values by ``RHO_SW * 1e-3 = 1.025`` to get
our internal units. That conversion factor is the same as the one used
inside ``darwindiff.carbonate``.
"""

from __future__ import annotations

from pathlib import Path

import xarray as xr

from darwindiff.ecco_darwin_loader import AOI

# Friendly DarwinDiff name → GLODAP file basename (the bit between
# ``GLODAPv2.2016b.`` and ``.nc``). Add new entries as we wire more variables
# into the loss; current usage covers what nb22+ needs.
GLODAP_VAR_MAP: dict[str, str] = {
    "DIC":      "TCO2",
    "ALK":      "TAlk",
    "NO3":      "NO3",
    "PO4":      "PO4",
    "Si":       "silicate",
    "O2":       "oxygen",
    "T":        "temperature",
    "S":        "salinity",
    "pH":       "pHtsinsitutp",
    "Cant":     "Cant",
    "OmegaA":   "OmegaA",
    "OmegaC":   "OmegaC",
}

RHO_SW: float = 1025.0
"""Seawater density (kg/m³) for the µmol/kg → mmol/m³ unit conversion. Same
constant ``darwindiff.carbonate.RHO_SW`` uses for the carbonate-system unit
conversions, kept in sync deliberately."""

_UMOL_PER_KG_TO_MMOL_PER_M3: float = RHO_SW * 1.0e-3


def open_glodap_variable(
    glodap_root: str | Path,
    variable: str,
) -> xr.Dataset:
    """Open one GLODAPv2.2016b variable NetCDF, normalize coordinates.

    Standardizes longitude to ``-180..180`` (DarwinDiff's AOI convention).
    GLODAP's raw grid uses a rolled ``0..360`` convention ranging ~20.5–379.5.

    Args:
        glodap_root: path to the extracted ``GLODAPv2.2016b_MappedClimatologies/``
            directory containing the per-variable NetCDFs.
        variable: friendly name from :data:`GLODAP_VAR_MAP` (e.g. ``"DIC"``,
            ``"ALK"``, ``"NO3"``).

    Returns:
        ``xr.Dataset`` with the requested variable + diagnostic fields
        (``<var>_error``, ``Input_mean``, ``Input_std``, ``Input_N``,
        ``<var>_relerr``), dims ``(depth_surface, lat, lon)``, with lon
        normalized to ``-180..180``.

    Raises:
        KeyError: if ``variable`` is not registered in :data:`GLODAP_VAR_MAP`.
        FileNotFoundError: if the corresponding NetCDF isn't under ``glodap_root``.
    """
    if variable not in GLODAP_VAR_MAP:
        raise KeyError(
            f"unknown GLODAP variable {variable!r}; "
            f"known: {sorted(GLODAP_VAR_MAP)}"
        )
    glodap_var = GLODAP_VAR_MAP[variable]
    path = Path(glodap_root) / f"GLODAPv2.2016b.{glodap_var}.nc"
    if not path.is_file():
        raise FileNotFoundError(f"GLODAP file not found: {path}")

    ds = xr.open_dataset(path)
    # Normalize longitude from GLODAP's rolled 0–360 to -180..180. The
    # transform `((lon + 180) % 360) - 180` is the standard recipe.
    if float(ds.lon.max()) > 180.0:
        ds = ds.assign_coords(lon=(((ds.lon + 180) % 360) - 180)).sortby("lon")
    return ds


def surface_layer_glodap(ds: xr.Dataset) -> xr.Dataset:
    """Pick the shallowest depth level (``depth_surface=0``, ~0 m)."""
    if "depth_surface" in ds.dims:
        return ds.isel(depth_surface=0).drop_vars("depth_surface", errors="ignore")
    return ds


def subset_aoi_glodap(ds: xr.Dataset, aoi: AOI) -> xr.Dataset:
    """Subset GLODAP dataset to an AOI in ``-180..180`` longitude convention.

    Requires the dataset to have lon/lat coordinates already in ``-180..180``
    (use :func:`open_glodap_variable` first, which does the normalization).
    """
    return ds.sel(
        lat=slice(aoi.lat_min, aoi.lat_max),
        lon=slice(aoi.lon_min, aoi.lon_max),
    )


def to_mmol_per_m3(da_umol_per_kg: xr.DataArray) -> xr.DataArray:
    """Convert µmol/kg → mmol/m³ via ρ_sw = 1025 kg/m³.

    Matches the unit convention DarwinDiff uses internally for DIC, ALK, NO₃,
    and other concentration tracers. GLODAP reports per-kg-of-seawater; we
    convert at the loader I/O boundary so downstream code stays in mmol/m³.

    Args:
        da_umol_per_kg: GLODAP DataArray in µmol/kg.

    Returns:
        DataArray in mmol/m³, with the original metadata preserved + an
        updated ``units`` attribute.
    """
    converted = da_umol_per_kg * _UMOL_PER_KG_TO_MMOL_PER_M3
    converted.attrs = dict(da_umol_per_kg.attrs)
    converted.attrs["units"] = "mmol / m^3"
    converted.attrs["unit_conversion"] = (
        f"GLODAP µmol/kg × ρ_sw ({RHO_SW} kg/m³) × 1e-3 = mmol/m³"
    )
    return converted
