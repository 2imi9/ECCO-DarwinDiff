"""Loader for the Gledhill & Liu (2026) surface-ocean Fe-prime speciation product.

Gledhill & Liu's "Present day iron speciation in the surface ocean, Version 2"
(PANGAEA 993556, CC-BY-4.0) is a global calculation of **Fe-prime** — the free
inorganic Fe(III) ion concentration, ``Fe(III)'`` — in surface waters
(<100 m mean). Fe-prime is the bioavailable, kinetically labile fraction of
dissolved iron: the part not bound to organic ligands. It is computed from a
speciation equilibrium given dissolved iron (dFe), the organic-ligand pool, pH,
temperature and salinity.

**Use as an OBSERVATION OPERATOR, not an independent constraint.**
Fe-prime here is *derived* from dFe + ligands + carbonate chemistry — it is a
deterministic function of the same dissolved-iron field GEOTRACES already
constrains, not a new independent measurement of iron. Feeding the Fe-prime
*field* into the inversion as if it were an independent absolute anchor would
double-count the GEOTRACES dFe information and understate posterior variance.
The correct role is as the **observation operator** ``H: FeT -> Fe'`` that maps
the model's total dissolved iron tracer to the observable free-ion
concentration. This loader therefore exposes two things:

  1. the Fe-prime **field** (:func:`feprime_aoi_1deg_grid`) — the observable
     itself, on the shared 1-deg grid; and
  2. the per-cell **operator coefficient** ``f = Fe' / FeT``
     (:func:`operator_coeff_aoi_1deg_grid`) — the dimensionless free-ion
     partition fraction, so the two-anchor inversion can predict
     ``Fe'_model = f * FeT_model`` from a model FeT field and compare against
     an independent Fe' observation (or, symmetrically, back out the FeT that a
     measured Fe' implies).

The free-ion fraction ``f`` is small and environment-dependent: across the
global point compilation its median is ~2% (range spans several orders of
magnitude), consistent with strong organic complexation of dissolved iron.

**Real schema (validated against the PANGAEA .xlsx files, 2026-07-22).**
The product ships as four Excel workbooks (PANGAEA "Binary Object" data matrix,
not a single .tab table). Two carry the Fe-prime values this loader reads:

    B-Global Fe speciation in surface waters_v2.xlsx  (POINT compilation)
      sheet "Global Fe speciation in surface", 5977 rows x 16 cols:
        Longitude, Latitude                          (deg, -180..180 / -90..90)
        Kriged Salinity, Kriged Temperature C,
        Kriged NO3+NO2, Phosphate, Silicate,
        Kriged Dissolved organic carbon [umol kg-1]
        pH [NBS scale], pH [total scale]
        Fe [nmol kg-1]                               <- dissolved iron (dFe)
        Fe bound to DOM (Continuous model) [mol L-1]
        Fe(III)' (Continuous model) [mol L-1]        <- Fe-prime, continuous
        Saturation state wrt Fe(OH)3(s) (Continuous) <- 'Yes'/'No' string
        Fe(III)' (Discrete model) [mol L-1]          <- Fe-prime, discrete
        Saturation state wrt Fe(OH)3(s) (Discrete)   <- 'Yes'/'No' string

    D-Global_kriged_surface_ocean_values.v3.xlsx     (KRIGED 2-deg grid)
      sheet "Global_kriged_surface_ocean_val", 10700 rows x 27 cols:
        Longitude, Latitude (2-deg grid, lon -180..180 step 2, lat -84..90)
        ... kriged S/T/alk/DIC/nutrients (+ std-dev companions) ...
        Kriged log(dissolved iron [nmol kg-1])       (col 18; note LOG dFe)
        Fe(III)' (Continuous model) [mol L-1]        (col 22)
        Fe(III)' (Discrete model) [mol L-1]          (col 23)
        Limiting-nutrient predictions               (cols 24-26, string)

    (A-GA02_GP16.v3.xlsx and C-Iron Quotas...xlsx are cruise-transect and
    lab-quota tables; not used by this loader but downloaded for provenance.)

The POINT file (B) is the default source: it holds the raw observation
locations and pairs each Fe-prime with its own dFe, so the operator coefficient
``Fe'/FeT`` is well defined per point. The KRIGED file (D) is a ready-made
global field but stores dFe as ``log(dFe)`` and on a coarser 2-deg grid; it is
available via ``source="kriged"`` for a gap-free field.

**Unit convention.** The product reports Fe-prime as **mol per litre**; dFe as
**nmol per kg**. DarwinDiff's box model carries the iron tracer in **mmol per
m^3**. Conversions:

    Fe' :  mol/L  ->  mmol/m^3   x 1e6
           (1 mol/L = 1000 mol/m^3 = 1e6 mmol/m^3)
    dFe :  nmol/kg -> mmol/m^3    x RHO_SW * 1e-6
           (same RHO_SW = 1025 kg/m^3 as darwindiff.geotraces_loader /
            darwindiff.glodap_loader / darwindiff.carbonate, kept in sync)

The operator coefficient ``f = Fe'/FeT`` is dimensionless and unit-independent
once both are in the same unit system.

Source: Gledhill, M. & Liu, F. (2026). Present day iron speciation in the
        surface ocean, Version 2. PANGAEA.
        https://doi.org/10.1594/PANGAEA.993556  (CC-BY-4.0)
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from darwindiff.ecco_darwin_loader import AOI

# --- Data files (relative to the gitignored data/ cache) -------------------
DATA_SUBDIR: str = "gledhill_fe_prime"

# Point-observation compilation (default): raw locations, each Fe-prime paired
# with its own dFe.
POINT_FILE: str = "B-Global_Fe_speciation_in_surface_waters_v2.xlsx"
POINT_SHEET: str = "Global Fe speciation in surface"

# Kriged 2-deg global field: gap-free, but dFe stored as log(dFe).
KRIGED_FILE: str = "D-Global_kriged_surface_ocean_values.v3.xlsx"
KRIGED_SHEET: str = "Global_kriged_surface_ocean_val"

# --- Column names in the two source sheets ---------------------------------
# Friendly key -> exact column header. Fe-prime is given for two speciation
# models (continuous ligand distribution vs discrete ligand classes); the
# continuous model is the default. Column headers are verbatim from the .xlsx
# (including the internal spacing) so pandas resolves them exactly.
_LON_COL: str = "Longitude"
_LAT_COL: str = "Latitude"

# Fe-prime, mol/L, by model and source sheet.
FEPRIME_COL: dict[str, str] = {
    "continuous": "Fe(III)' (Continuous model) [mol L-1]",
    "discrete": "Fe(III)' (Discrete model) [mol L-1]",
}

# Dissolved iron column differs between the point (B) and kriged (D) sheets:
# B stores dFe directly (nmol/kg); D stores log10-free? -> it is natural log of
# dFe in nmol/kg (see docstring). Handled per-source in :func:`open_gledhill_fe_prime`.
_DFE_COL_POINT: str = "Fe [nmol kg-1]"
_DFE_LOG_COL_KRIGED: str = "Kriged log(dissolved iron [nmol kg-1])"

# --- Unit conversions ------------------------------------------------------
RHO_SW: float = 1025.0
"""Seawater density (kg/m^3) for nmol/kg -> mmol/m^3. Same constant as
``darwindiff.geotraces_loader.RHO_SW`` / ``darwindiff.glodap_loader.RHO_SW`` /
``darwindiff.carbonate.RHO_SW``, kept in sync deliberately."""

_NMOL_PER_KG_TO_MMOL_PER_M3: float = RHO_SW * 1.0e-6
_MOL_PER_L_TO_MMOL_PER_M3: float = 1.0e6


@dataclass(frozen=True)
class FePrimeGrid:
    """Binned Fe-prime (or operator-coefficient) field on the shared 1-deg grid.

    Attributes:
        field: ``(n_lat, n_lon)`` bin-mean values, ``NaN`` at cells with no
            coverage. Units depend on the producer:
            :func:`feprime_aoi_1deg_grid` -> mmol/m^3 (or mol/L if
            ``to_mmol=False``); :func:`operator_coeff_aoi_1deg_grid` ->
            dimensionless ``Fe'/FeT`` fraction.
        count: ``(n_lat, n_lon)`` integer count of observations per cell (0
            where uncovered).
        spread: ``(n_lat, n_lon)`` per-cell standard deviation of the binned
            values (``NaN`` where <2 observations), a coverage/uncertainty
            diagnostic for the inversion's observation-error weighting.
        units: units string for ``field``.
        source: short provenance string.
    """

    field: np.ndarray
    count: np.ndarray
    spread: np.ndarray
    units: str
    source: str


def _data_path(data_dir: str | Path, source: str) -> Path:
    """Resolve the workbook path for ``source`` under the data cache."""
    fname = POINT_FILE if source == "point" else KRIGED_FILE
    return Path(data_dir) / DATA_SUBDIR / fname


def open_gledhill_fe_prime(
    data_dir: str | Path,
    *,
    model: str = "continuous",
    source: str = "point",
) -> pd.DataFrame:
    """Open a Gledhill Fe-prime workbook into a normalized long DataFrame.

    Reads the requested source sheet and returns a tidy frame with four
    canonical columns — ``lon``, ``lat``, ``dfe_nmol_kg``, ``feprime_mol_l`` —
    so downstream AOI subsetting and grid binning are source-agnostic. The
    kriged sheet stores dFe as ``log(dFe)``; it is exponentiated back to
    nmol/kg here so both sources share the same ``dfe_nmol_kg`` convention.

    Args:
        data_dir: root of the gitignored ``data/`` cache (the file is read
            from ``<data_dir>/gledhill_fe_prime/<workbook>.xlsx``).
        model: ``"continuous"`` (default) or ``"discrete"`` — which speciation
            model's Fe-prime column to load.
        source: ``"point"`` (default; file B, raw observation locations) or
            ``"kriged"`` (file D, 2-deg global grid).

    Returns:
        ``pd.DataFrame`` with columns ``lon`` (-180..180), ``lat``,
        ``dfe_nmol_kg``, ``feprime_mol_l``. Rows with non-finite lon/lat or
        Fe-prime are dropped; dFe may be NaN (only needed for the operator
        coefficient, not the raw field).

    Raises:
        FileNotFoundError: if the workbook is not in the data cache.
        KeyError: if ``model`` or ``source`` is not recognized.
        ValueError: if an expected column is missing from the sheet.
    """
    if model not in FEPRIME_COL:
        raise KeyError(f"unknown model {model!r}; known: {sorted(FEPRIME_COL)}")
    if source not in ("point", "kriged"):
        raise KeyError(f"unknown source {source!r}; use 'point' or 'kriged'")

    path = _data_path(data_dir, source)
    if not path.is_file():
        raise FileNotFoundError(
            f"Gledhill Fe-prime workbook not found: {path}\n"
            f"Download from https://doi.org/10.1594/PANGAEA.993556 into "
            f"{path.parent}."
        )

    sheet = POINT_SHEET if source == "point" else KRIGED_SHEET
    raw = pd.read_excel(path, sheet_name=sheet)

    feprime_col = FEPRIME_COL[model]
    for needed in (_LON_COL, _LAT_COL, feprime_col):
        if needed not in raw.columns:
            raise ValueError(
                f"column {needed!r} missing from {path.name}::{sheet}; "
                f"present (first 8): {list(raw.columns)[:8]}"
            )

    out = pd.DataFrame(
        {
            "lon": pd.to_numeric(raw[_LON_COL], errors="coerce"),
            "lat": pd.to_numeric(raw[_LAT_COL], errors="coerce"),
            "feprime_mol_l": pd.to_numeric(raw[feprime_col], errors="coerce"),
        }
    )

    # Dissolved iron: direct (point) or exp(log-dFe) (kriged).
    if source == "point":
        if _DFE_COL_POINT not in raw.columns:
            raise ValueError(f"dFe column {_DFE_COL_POINT!r} missing from {path.name}")
        out["dfe_nmol_kg"] = pd.to_numeric(raw[_DFE_COL_POINT], errors="coerce")
    else:
        if _DFE_LOG_COL_KRIGED not in raw.columns:
            raise ValueError(f"log-dFe column {_DFE_LOG_COL_KRIGED!r} missing from {path.name}")
        out["dfe_nmol_kg"] = np.exp(pd.to_numeric(raw[_DFE_LOG_COL_KRIGED], errors="coerce"))

    # Longitude is already -180..180 in both sheets; normalize defensively.
    out["lon"] = ((out["lon"] + 180.0) % 360.0) - 180.0

    # Drop rows with no location or no Fe-prime (dFe may legitimately be NaN
    # for the raw-field path; it is filtered again in the operator path).
    out = out[np.isfinite(out["lon"]) & np.isfinite(out["lat"]) & np.isfinite(out["feprime_mol_l"])]
    return out.reset_index(drop=True)


def subset_aoi_gledhill(df: pd.DataFrame, aoi: AOI) -> pd.DataFrame:
    """Filter Fe-prime points to those inside an AOI box (-180..180 lon).

    Args:
        df: normalized frame from :func:`open_gledhill_fe_prime`.
        aoi: AOI in the ``-180..180`` longitude convention.

    Returns:
        Row-subset of ``df`` with points inside the inclusive AOI box.
    """
    keep = (
        (df["lat"] >= aoi.lat_min)
        & (df["lat"] <= aoi.lat_max)
        & (df["lon"] >= aoi.lon_min)
        & (df["lon"] <= aoi.lon_max)
    )
    return df[keep].reset_index(drop=True)


def _bin_mean_count_spread(
    lons: np.ndarray,
    lats: np.ndarray,
    values: np.ndarray,
    aoi: AOI,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Bin scattered points to the shared integer-degree 1-deg grid.

    Uses :func:`darwindiff.llc270_loader.bin_to_1deg_grid` for the mean field
    so the result is cell-for-cell aligned with the DB-1 iron forcing, DB-2
    velocity, GEOTRACES dFe and the Daniels calcite target (edges at
    ``min-0.5 .. max+0.5``, centres at integer degrees). Count and spread are
    computed on the identical edges via ``binned_statistic_2d`` so all three
    grids register exactly.
    """
    from scipy.stats import binned_statistic_2d

    from darwindiff.llc270_loader import bin_to_1deg_grid

    mean_grid = bin_to_1deg_grid(
        lons, lats, values, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max
    )
    # Identical edge construction to bin_to_1deg_grid (kept in lock-step).
    lat_edges = np.arange(aoi.lat_min - 0.5, aoi.lat_max + 0.5 + 1.0e-3, 1.0)
    lon_edges = np.arange(aoi.lon_min - 0.5, aoi.lon_max + 0.5 + 1.0e-3, 1.0)
    count_grid, _, _, _ = binned_statistic_2d(
        lats, lons, values, statistic="count", bins=[lat_edges, lon_edges]
    )
    spread_grid, _, _, _ = binned_statistic_2d(
        lats, lons, values, statistic="std", bins=[lat_edges, lon_edges]
    )
    # binned_statistic_2d std is 0 (not NaN) for single-count cells; mark <2.
    spread_grid = np.where(count_grid >= 2, spread_grid, np.nan)
    return mean_grid, count_grid.astype(np.int64), spread_grid


def feprime_aoi_1deg_grid(
    data_dir: str | Path,
    aoi: AOI,
    *,
    model: str = "continuous",
    source: str = "point",
    to_mmol: bool = True,
) -> FePrimeGrid:
    """Bin surface Fe-prime onto the shared integer-degree 1-deg AOI grid.

    The Fe-prime **field** — the observable ``Fe(III)'`` itself. Returns an
    ``[n_lat, n_lon]`` field plus per-cell observation count and spread,
    aligned to the shared grid via
    :func:`darwindiff.llc270_loader.bin_to_1deg_grid`.

    Args:
        data_dir: root of the ``data/`` cache.
        aoi: target AOI (``-180..180`` lon convention).
        model: ``"continuous"`` (default) or ``"discrete"`` speciation model.
        source: ``"point"`` (default) or ``"kriged"``.
        to_mmol: convert mol/L -> mmol/m^3 (default True; DarwinDiff units).

    Returns:
        :class:`FePrimeGrid` with ``field`` shape
        ``(lat_max-lat_min+1, lon_max-lon_min+1)``, ``NaN`` where no coverage.
    """
    df = subset_aoi_gledhill(
        open_gledhill_fe_prime(data_dir, model=model, source=source), aoi
    )
    vals = df["feprime_mol_l"].to_numpy(dtype=np.float64)
    if to_mmol:
        vals = vals * _MOL_PER_L_TO_MMOL_PER_M3
    mean_grid, count_grid, spread_grid = _bin_mean_count_spread(
        df["lon"].to_numpy(dtype=np.float64),
        df["lat"].to_numpy(dtype=np.float64),
        vals,
        aoi,
    )
    return FePrimeGrid(
        field=mean_grid,
        count=count_grid,
        spread=spread_grid,
        units="mmol / m^3" if to_mmol else "mol / L",
        source=f"Gledhill&Liu 2026 PANGAEA 993556 Fe(III)' ({model}, {source})",
    )


def operator_coeff_aoi_1deg_grid(
    data_dir: str | Path,
    aoi: AOI,
    *,
    model: str = "continuous",
    source: str = "point",
) -> FePrimeGrid:
    """Bin the Fe-prime observation-operator coefficient onto the shared grid.

    The coefficient is the dimensionless free-ion partition fraction
    ``f = Fe' / FeT`` (both converted to mmol/m^3 first, so the ratio is
    unit-independent). It is the observation operator the two-anchor inversion
    applies to a model total-iron field: ``Fe'_model = f * FeT_model``. Because
    ``f`` is derived from the same dFe the field is, it must be used as this
    operator, **not** as a second independent iron constraint (see module
    docstring).

    Points with non-positive or non-finite dFe are dropped (the ratio is
    undefined). ``f`` is computed per point, then bin-averaged per cell.

    Args:
        data_dir: root of the ``data/`` cache.
        aoi: target AOI.
        model: ``"continuous"`` (default) or ``"discrete"``.
        source: ``"point"`` (default) or ``"kriged"``.

    Returns:
        :class:`FePrimeGrid` with a dimensionless ``field`` (``Fe'/FeT``),
        per-cell ``count`` and ``spread``.
    """
    df = subset_aoi_gledhill(
        open_gledhill_fe_prime(data_dir, model=model, source=source), aoi
    )
    dfe = df["dfe_nmol_kg"].to_numpy(dtype=np.float64)
    feprime = df["feprime_mol_l"].to_numpy(dtype=np.float64)
    # Convert both to mmol/m^3 (ratio is unit-independent, but be explicit).
    dfe_mmol = dfe * _NMOL_PER_KG_TO_MMOL_PER_M3
    feprime_mmol = feprime * _MOL_PER_L_TO_MMOL_PER_M3
    valid = np.isfinite(dfe_mmol) & (dfe_mmol > 0.0) & np.isfinite(feprime_mmol)
    frac = feprime_mmol[valid] / dfe_mmol[valid]
    mean_grid, count_grid, spread_grid = _bin_mean_count_spread(
        df["lon"].to_numpy(dtype=np.float64)[valid],
        df["lat"].to_numpy(dtype=np.float64)[valid],
        frac,
        aoi,
    )
    return FePrimeGrid(
        field=mean_grid,
        count=count_grid,
        spread=spread_grid,
        units="dimensionless (Fe'/FeT)",
        source=f"Gledhill&Liu 2026 PANGAEA 993556 Fe'/FeT operator ({model}, {source})",
    )


def load(
    data_dir: str | Path,
    aoi: AOI,
    *,
    model: str = "continuous",
    source: str = "point",
) -> dict[str, FePrimeGrid]:
    """Load both products the two-anchor inversion consumes, on the shared grid.

    Convenience wrapper returning the Fe-prime **field** (the observable) and
    the **operator coefficient** ``Fe'/FeT`` (the map from model FeT), both
    binned to the shared 1-deg AOI grid.

    Args:
        data_dir: root of the ``data/`` cache.
        aoi: target AOI.
        model: ``"continuous"`` (default) or ``"discrete"``.
        source: ``"point"`` (default) or ``"kriged"``.

    Returns:
        ``{"feprime": FePrimeGrid (mmol/m^3),
           "operator_coeff": FePrimeGrid (dimensionless Fe'/FeT)}``.
    """
    return {
        "feprime": feprime_aoi_1deg_grid(data_dir, aoi, model=model, source=source),
        "operator_coeff": operator_coeff_aoi_1deg_grid(
            data_dir, aoi, model=model, source=source
        ),
    }
