"""Loader for the Xu & Weber (2021) Al-inverse soluble deposition field — the SOURCE anchor
for the alpfe (dust-Fe solubility) leg of the two-anchor iron inversion.

Xu & Weber 2021 (GBC, doi:10.1029/2021GB007049) "Ocean Dust Deposition Rates Constrained in a
Data-Assimilation Model of the Marine Aluminum Cycle" inverts GEOTRACES IDP2017 dissolved-Al
sections for the soluble-Al deposition flux, over 60 model configurations (12 dust patterns x
circulation ensemble). Because the pattern is disciplined by IN-OCEAN Al data, it decouples the
alpfe anchor from atmospheric-dust-model spread (the red-team's key recommendation,
docs/findings/2026-07-22_two_anchor_redteam.md).

Data: BCO-DMO 922468 (CC-BY-4.0), cached at ``data/xu_weber_2021/`` (gitignored).
Fields as flat CSV:
- ``Aldep.txt``  : soluble Al deposition, mmol Al/m^2/yr, serialized
  [91 lat x (180 lon * 60 configs)].
- ``grid/x.txt`` : longitude centres, 0..360 convention, 180 pts (~2 deg).
- ``grid/y.txt`` : latitude centres, -89..89, 91 pts (~2 deg).
- ``mod_names.txt``: the 60 configuration names (the ensemble the per-cell spread comes from).

**Al -> soluble Fe conversion.** The anchor needs soluble-FE deposition; Xu & Weber give soluble Al.
Convert by the soluble Fe:Al molar ratio of deposited aerosol. Default 0.15 (from Xu & Weber's
37.2 Gmol soluble Al/yr = 1.0 Tg Al/yr vs GESAMP soluble-Fe deposition 0.17-0.42 Tg Fe/yr =>
molar Fe:Al ~0.08-0.20; midpoint ~0.15). This ratio is the dominant absolute-scale uncertainty and
should be refined regionally from GEOTRACES GA03 aerosol solubility (Phase-1). It sets the
absolute alpfe value; the anchor's identifiability leverage comes from the PATTERN, which is
ratio-independent.
Citation caution: 37.2 +/- 11 Gmol/yr in Xu & Weber is soluble ALUMINUM, not Fe.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from darwindiff.ecco_darwin_loader import AOI

DEFAULT_XW_DIR = Path(__file__).resolve().parents[2] / "data" / "xu_weber_2021"

# soluble Fe:Al molar ratio of deposited aerosol (see module docstring). Default midpoint; the
# plausible range 0.08-0.20 propagates to the alpfe absolute scale, not its identifiability.
DEFAULT_FE_AL_MOLAR = 0.15
FE_AL_MOLAR_RANGE = (0.08, 0.20)


def load_aldep_field(xw_dir: str | Path = DEFAULT_XW_DIR):
    """Load the soluble-Al deposition ensemble.

    Returns (mean, std, lat, lon) on the native 2-deg grid.
    mean/std are [91, 180] mmol Al/m^2/yr over the 60 configurations (std = the ensemble spread that
    becomes the per-cell prior variance). lon is normalized to -180..180 and the arrays rolled to be
    monotonically increasing in lon. NaN over land / no-deposition cells.
    """
    d = Path(xw_dir)
    lon = np.loadtxt(d / "grid" / "x.txt", delimiter=",").astype(np.float64)  # 0..360, 180
    lat = np.loadtxt(d / "grid" / "y.txt", delimiter=",").astype(np.float64)  # -89..89, 91
    nlat, nlon = lat.shape[0], lon.shape[0]
    # Aldep: 91 lines, each 180*60 = 10800 values -> reshape [lat, lon, config]
    rows = [ln for ln in (d / "Aldep.txt").read_text().splitlines() if ln.strip()]
    arr = np.array([[float(v) for v in ln.split(",") if v != ""] for ln in rows], dtype=np.float64)
    n_cfg = arr.shape[1] // nlon
    ald = arr.reshape(nlat, nlon, n_cfg)          # [lat, lon, 60]
    import warnings
    with warnings.catch_warnings():  # all-NaN land columns -> NaN mean/std is intended
        warnings.simplefilter("ignore", RuntimeWarning)
        mean = np.nanmean(ald, axis=2)
        std = np.nanstd(ald, axis=2)
    # normalize lon 0..360 -> -180..180 and sort
    lon180 = ((lon + 180) % 360) - 180
    order = np.argsort(lon180)
    return mean[:, order], std[:, order], lat, lon180[order]


def soluble_fe_deposition_aoi(
    aoi: AOI,
    *,
    xw_dir: str | Path = DEFAULT_XW_DIR,
    fe_al_molar: float = DEFAULT_FE_AL_MOLAR,
    lat_res: float = 1.0,
    lon_res: float = 1.0,
):
    """Soluble-Fe deposition on an AOI's integer-degree 1-deg grid + its ensemble spread.

    Bilinearly regrids the 2-deg Al-inverse mean/std onto the AOI grid (integer-degree
    centres, matching ``darwindiff.llc270_loader.bin_to_1deg_grid`` / the box caches), then
    converts Al -> soluble Fe by ``fe_al_molar``. Returns (dfe_dep [ny,nx], dfe_spread [ny,nx],
    lats, lons) in mmol Fe/m^2/yr.

    The ensemble spread is the per-cell 1-sigma the source-anchor prior should use (down-weight
    cells where between-config spread is large, per the red-team). ``fe_al_molar`` scales both
    mean and spread.
    """
    from scipy.interpolate import RegularGridInterpolator

    mean, std, lat, lon = load_aldep_field(xw_dir)
    # RegularGridInterpolator needs finite values; fill NaN with 0 (no deposition) to interpolate,
    # then re-mask cells that interpolate from all-NaN neighbourhoods via a coverage field.
    cov = np.isfinite(mean).astype(np.float64)
    mean0 = np.nan_to_num(mean, nan=0.0)
    std0 = np.nan_to_num(std, nan=0.0)
    f_mean = RegularGridInterpolator((lat, lon), mean0, bounds_error=False, fill_value=0.0)
    f_std = RegularGridInterpolator((lat, lon), std0, bounds_error=False, fill_value=0.0)
    f_cov = RegularGridInterpolator((lat, lon), cov, bounds_error=False, fill_value=0.0)

    lats = np.arange(aoi.lat_min, aoi.lat_max + 0.5, lat_res)
    lons = np.arange(aoi.lon_min, aoi.lon_max + 0.5, lon_res)
    lat2d, lon2d = np.meshgrid(lats, lons, indexing="ij")
    pts = np.column_stack([lat2d.ravel(), lon2d.ravel()])
    dep = f_mean(pts).reshape(lat2d.shape)
    spread = f_std(pts).reshape(lat2d.shape)
    covg = f_cov(pts).reshape(lat2d.shape)
    dep = np.where(covg > 0.5, dep, np.nan)
    spread = np.where(covg > 0.5, spread, np.nan)
    # Al -> soluble Fe (molar ratio; deposition is mmol/m^2/yr so the molar ratio applies directly)
    return dep * fe_al_molar, spread * fe_al_molar, lats, lons
