"""Loader for the Black et al. (2020) upper-ocean iron EXPORT FLUX compilation — the
SINK-side anchor for the ``scav_rat`` leg of the two-anchor iron inversion.

Black et al. 2020 (GBC, doi:10.1029/2020GB006592, "Ironing Out Fe Residence Time in the
Dynamic Upper Ocean") perform an observation-based assessment of iron export from the
upper ocean (0–300 m) using ²³⁴Th and sediment-trap data, most collected through
GEOTRACES. It compiles new (US GEOTRACES GA03/EPZT, GA01 GEOVIDE) and prior export-flux
estimates across 20 programs / three basins.

**We assimilate the FLUX, not the residence time.** The paper also reports upper-ocean Fe
residence times τ = inventory / removal, but τ is a derived ratio that reuses the *same*
DFe inventory the GEOTRACES concentration anchor already carries — assimilating τ would
double-count that inventory. The iron EXPORT FLUX ``F_tot`` (µmol Fe m⁻² day⁻¹) is the
dimensionally-new SINK rate: it is what a scavenging/export closure produces, so it
directly constrains ``scav_rat``. This loader returns the flux only.

**This is the SINK partner to** :mod:`darwindiff.xu_weber_loader` **(the SOURCE anchor).**
The source anchor (soluble-Fe deposition) and this sink anchor (Fe export) are the two legs
that lift the rank-1 (alpfe ↔ scav_rat) degeneracy into a bounded basin
(``docs/findings/2026-07-22_two_anchor_redteam.md``). Both are returned in the same units
(mmol Fe m⁻² yr⁻¹) so a per-province source/sink balance is dimensionally clean.

Real schema (what actually got downloaded)
-------------------------------------------
The genuinely-open data used here is **Table 1** of the paper ("²³⁴Th- and Sediment
Trap-Based Iron Export Studies"), transcribed from the open-access **CC-BY-4.0** PDF
(``data/black2020_fe_flux/Black_etal_2020_GBC_2020GB006592.pdf``, p.4) into
``black2020_table1_fe_export.csv``. Each row is one program/province with:

    region, program, method (ST | 234Th), dates, n (# occupations),
    export_depth_min/max_m,
    fe_export_min/max_umol_m2_day   ← the SINK-side rate (min–max over the n stations),
    dust_input_min/max_umol_m2_day  ← context (Table 1 "Predicted input from dust"),
    lat, lon                        ← REPRESENTATIVE program coords (see below),
    coord_kind (point | regional | transect), study.

The Fe export column is a per-**province** min–max range (the paper's own summary
granularity). This matches the intended assimilation target: per
``docs/data_acquisition_roadmap.md`` — *"Black τ is a per-province RATE target (not
per-cell)."* Fe export is log-normal and spans orders of magnitude within a province, so
the per-record point estimate is the **geometric mean** ``sqrt(min·max)`` and the
per-record 1σ is the half-range ``(max−min)/2``.

Coordinate provenance (read this before trusting the grid)
----------------------------------------------------------
Table 1 prints only a *text* "General location" (e.g. "Bermuda (BATS)"), never lat/lon.
The ``lat``/``lon`` columns are REPRESENTATIVE coordinates assigned from documented
cruise/time-series locations — they are metadata, not paper values, and ``coord_kind``
grades their fidelity:

  - ``point``    — fixed time-series / small area (BATS, ALOHA, DYFAMED, Gotland): exact.
  - ``regional`` — single-region program: the point is a good centroid.
  - ``transect`` — a **multi-station basin transect** (GA03 KN199-04/KN204-01, GP16 TN303,
                   GA01 GEOVIDE). A single point badly under-represents these — the GA03
                   transect, e.g., crosses the Mid-Atlantic AOI but its centroid does not
                   land in it. **These rows are exactly what the per-station Supporting
                   Information Table S1 would resolve.**

BLOCKER — the per-station Supporting Information (Table S1) is bot-blocked
-------------------------------------------------------------------------
The paper's Data Availability Statement puts the per-station georeferenced export/residence
compilation in **Supporting Information (Table S1)** on the Wiley host. That host
(``agupubs.onlinelibrary.wiley.com``) sits behind a **Cloudflare bot challenge**: every
programmatic ``downloadSupplement`` request returns HTTP 403, and a headless browser lands
on the "Just a moment…" interstitial. This is bot-detection (not a 402/paywall — the
article itself is CC-BY open access), and bot-detection is not bypassed here. Until the SI
xlsx is obtained (a browser download by a human, or via a collaborator), this loader is
built on the CC-BY Table 1 province ranges, which carry the same Fe export FLUX quantity at
the province granularity the anchor actually targets. Drop the SI table beside the CSV and
extend :func:`load_black_points` to gain within-province / per-station resolution.

The underlying *raw* GEOTRACES inputs (²³⁴Th, ²³⁸U, particle Fe:Al) are separately open on
BCO-DMO (datasets 3662, 3835/3836, 3840, 3871, 643213/643316, 668083, 670285 — listed in
the paper's Data Availability Statement) but those are the un-inverted measurements, not the
computed Fe export flux; re-deriving flux from them would mean re-running the paper's ²³⁴Th
model and is out of scope for a loader.

Unit convention
---------------
Table 1 reports **µmol Fe m⁻² day⁻¹**. DarwinDiff carries iron deposition/export as
**mmol Fe m⁻² yr⁻¹** (see :func:`darwindiff.xu_weber_loader.soluble_fe_deposition_aoi`),
so the two-anchor source and sink live in the same units. Conversion:

    1 µmol m⁻² day⁻¹ = 1e-3 mmol/µmol × 365.25 day/yr = 0.36525 mmol m⁻² yr⁻¹

Quick usage::

    from darwindiff.black2020_fe_flux_loader import fe_export_aoi_1deg_grid, fe_export_province
    from darwindiff.ecco_darwin_loader import AOI_BY_KEY

    aoi = AOI_BY_KEY["npsg"]                       # ALOHA province
    flux, spread, counts, lats, lons = fe_export_aoi_1deg_grid(aoi)   # [ny,nx] mmol/m^2/yr
    value, sigma, n = fe_export_province(aoi)      # scalar per-province target
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from darwindiff.ecco_darwin_loader import AOI

_REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_BLACK_PATH: Path = (
    _REPO_ROOT / "data" / "black2020_fe_flux" / "black2020_table1_fe_export.csv"
)

# µmol Fe m⁻² day⁻¹ → mmol Fe m⁻² yr⁻¹ (DarwinDiff convention; same units as the Xu-Weber
# SOURCE anchor so a per-province source/sink balance is dimensionally clean).
UMOL_PER_DAY_TO_MMOL_PER_YR: float = 1.0e-3 * 365.25


@dataclass
class BlackFeExport:
    """Flat, per-program arrays parsed from the Black (2020) Table 1 CSV.

    All arrays are 1-D and aligned (index i = program i). Fluxes are in
    **mmol Fe m⁻² yr⁻¹** (already converted from the CSV's µmol m⁻² day⁻¹).

    Attributes:
        lat, lon: representative program coordinates (−180..180 lon). See the module
            docstring — these are assigned metadata, graded by ``coord_kind``.
        fe_export_min, fe_export_max: reported min–max export-flux range (mmol/m²/yr).
        fe_export: per-program point estimate = geometric mean ``sqrt(min·max)``
            (Fe export is log-normal), mmol/m²/yr.
        fe_export_sigma: per-program 1σ = half-range ``(max−min)/2``, mmol/m²/yr.
        n: number of stations/occupations behind each program's range.
        method: ``"ST"`` (sediment trap) or ``"234Th"``.
        coord_kind: ``"point"`` | ``"regional"`` | ``"transect"`` (coordinate fidelity).
        region, program, study: provenance labels.
    """

    lat: np.ndarray
    lon: np.ndarray
    fe_export_min: np.ndarray
    fe_export_max: np.ndarray
    fe_export: np.ndarray
    fe_export_sigma: np.ndarray
    n: np.ndarray
    method: np.ndarray
    coord_kind: np.ndarray
    region: np.ndarray
    program: np.ndarray
    study: np.ndarray


def load_black_points(path: str | Path = DEFAULT_BLACK_PATH) -> BlackFeExport:
    """Parse the Black (2020) Table 1 CSV into flat per-program arrays.

    Reads ``black2020_table1_fe_export.csv`` (``#``-prefixed comment lines skipped),
    converts the export-flux range from µmol m⁻² day⁻¹ to mmol m⁻² yr⁻¹, and derives the
    log-normal point estimate (geometric mean) and half-range 1σ.

    Args:
        path: path to the transcribed CSV (default: ``data/black2020_fe_flux/...``).

    Returns:
        :class:`BlackFeExport` with all fields populated, fluxes in mmol Fe m⁻² yr⁻¹.

    Raises:
        FileNotFoundError: if the CSV is not present. The message points at the
            provenance PDF and the SI blocker (module docstring).
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(
            f"Black (2020) Fe-export CSV not found: {p}\n"
            "Expected the transcribed Table 1 at data/black2020_fe_flux/"
            "black2020_table1_fe_export.csv (provenance PDF sits beside it). "
            "See the module docstring for the SI Table S1 access blocker."
        )

    regions, programs, methods, coord_kinds, studies = [], [], [], [], []
    lats, lons, ns = [], [], []
    fe_min, fe_max = [], []
    with p.open("r", encoding="utf-8") as fh:
        header: list[str] | None = None
        for raw in fh:
            line = raw.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            cells = line.split(",")
            if header is None:
                header = cells
                idx = {name: i for i, name in enumerate(header)}
                continue
            regions.append(cells[idx["region"]])
            programs.append(cells[idx["program"]])
            methods.append(cells[idx["method"]])
            coord_kinds.append(cells[idx["coord_kind"]])
            studies.append(cells[idx["study"]] if "study" in idx and idx["study"] < len(cells) else "")
            lats.append(float(cells[idx["lat"]]))
            lons.append(float(cells[idx["lon"]]))
            ns.append(int(cells[idx["n"]]))
            fe_min.append(float(cells[idx["fe_export_min_umol_m2_day"]]))
            fe_max.append(float(cells[idx["fe_export_max_umol_m2_day"]]))

    fe_min_arr = np.asarray(fe_min, dtype=np.float64) * UMOL_PER_DAY_TO_MMOL_PER_YR
    fe_max_arr = np.asarray(fe_max, dtype=np.float64) * UMOL_PER_DAY_TO_MMOL_PER_YR
    # Geometric mean point estimate (Fe export is log-normal); half-range 1σ.
    fe_point = np.sqrt(fe_min_arr * fe_max_arr)
    fe_sigma = 0.5 * (fe_max_arr - fe_min_arr)

    return BlackFeExport(
        lat=np.asarray(lats, dtype=np.float64),
        lon=np.asarray(lons, dtype=np.float64),
        fe_export_min=fe_min_arr,
        fe_export_max=fe_max_arr,
        fe_export=fe_point,
        fe_export_sigma=fe_sigma,
        n=np.asarray(ns, dtype=np.int64),
        method=np.asarray(methods, dtype="U16"),
        coord_kind=np.asarray(coord_kinds, dtype="U16"),
        region=np.asarray(regions, dtype="U48"),
        program=np.asarray(programs, dtype="U48"),
        study=np.asarray(studies, dtype="U48"),
    )


def subset_aoi(points: BlackFeExport, aoi: AOI) -> BlackFeExport:
    """Keep only programs whose representative coordinate falls inside ``aoi``.

    Mirrors :func:`darwindiff.geotraces_loader.subset_aoi_geotraces` — a simple
    lat/lon box filter, here on per-program points. ``aoi`` is in the −180..180 lon
    convention (as are the CSV coordinates).

    Args:
        points: parsed programs from :func:`load_black_points`.
        aoi: target AOI.

    Returns:
        A new :class:`BlackFeExport` with the same fields filtered to the AOI box.
    """
    keep = (
        (points.lat >= aoi.lat_min) & (points.lat <= aoi.lat_max)
        & (points.lon >= aoi.lon_min) & (points.lon <= aoi.lon_max)
    )
    return BlackFeExport(
        lat=points.lat[keep],
        lon=points.lon[keep],
        fe_export_min=points.fe_export_min[keep],
        fe_export_max=points.fe_export_max[keep],
        fe_export=points.fe_export[keep],
        fe_export_sigma=points.fe_export_sigma[keep],
        n=points.n[keep],
        method=points.method[keep],
        coord_kind=points.coord_kind[keep],
        region=points.region[keep],
        program=points.program[keep],
        study=points.study[keep],
    )


def fe_export_aoi_1deg_grid(
    aoi: AOI,
    *,
    black_path: str | Path = DEFAULT_BLACK_PATH,
    to_mmol_per_yr: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Bin Black (2020) Fe export onto the **shared** integer-degree 1° AOI grid.

    Uses the same grid convention as every other DarwinDiff anchor
    (:func:`darwindiff.llc270_loader.bin_to_1deg_grid`: edges at ``min−0.5 .. max+0.5``,
    integer-degree cell centres), so this SINK field aligns cell-for-cell with the
    Xu-Weber SOURCE field, the iron forcing (DB-1), velocity (DB-2), and the Daniels
    calcite target. Empty cells (the common case — this compilation is sparse) are NaN.

    The per-cell value is the mean of the in-cell programs' geometric-mean point
    estimates. The per-cell 1σ combines within-program uncertainty (mean of the
    half-range σ²) with between-program scatter (variance of the point estimates):
    ``spread = sqrt(mean(σ_i²) + var(vᵢ))``.

    Args:
        aoi: target AOI (−180..180 lon).
        black_path: path to the Table 1 CSV.
        to_mmol_per_yr: if True (default) return mmol Fe m⁻² yr⁻¹ (DarwinDiff units);
            if False, back-convert to the source µmol Fe m⁻² day⁻¹.

    Returns:
        ``(flux, spread, counts, lats, lons)``:
          - ``flux``   ``[ny,nx]`` mean Fe export per cell (NaN where no coverage),
          - ``spread`` ``[ny,nx]`` per-cell 1σ (NaN where no coverage),
          - ``counts`` ``[ny,nx]`` int number of programs binned into each cell,
          - ``lats``   ``[ny]`` integer-degree cell-centre latitudes,
          - ``lons``   ``[nx]`` integer-degree cell-centre longitudes,
        with ``ny = lat_max−lat_min+1`` and ``nx = lon_max−lon_min+1``.
    """
    from scipy.stats import binned_statistic_2d

    from darwindiff.llc270_loader import bin_to_1deg_grid

    pts = subset_aoi(load_black_points(black_path), aoi)

    lats = np.arange(aoi.lat_min, aoi.lat_max + 1.0e-3, 1.0)
    lons = np.arange(aoi.lon_min, aoi.lon_max + 1.0e-3, 1.0)
    ny, nx = len(lats), len(lons)

    if pts.lat.size == 0:
        empty = np.full((ny, nx), np.nan, dtype=np.float64)
        return empty, empty.copy(), np.zeros((ny, nx), dtype=np.int64), lats, lons

    scale = 1.0 if to_mmol_per_yr else 1.0 / UMOL_PER_DAY_TO_MMOL_PER_YR
    values = pts.fe_export * scale
    sigmas = pts.fe_export_sigma * scale

    # Mean field via the shared helper — guarantees identical grid registration.
    flux = bin_to_1deg_grid(
        pts.lon, pts.lat, values, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max
    )

    # Counts + spread components on the SAME integer-degree edges bin_to_1deg_grid uses.
    lat_edges = np.arange(aoi.lat_min - 0.5, aoi.lat_max + 0.5 + 1.0e-3, 1.0)
    lon_edges = np.arange(aoi.lon_min - 0.5, aoi.lon_max + 0.5 + 1.0e-3, 1.0)
    counts, _, _, _ = binned_statistic_2d(
        pts.lat, pts.lon, values, statistic="count", bins=[lat_edges, lon_edges]
    )
    std_v, _, _, _ = binned_statistic_2d(
        pts.lat, pts.lon, values, statistic="std", bins=[lat_edges, lon_edges]
    )
    mean_s2, _, _, _ = binned_statistic_2d(
        pts.lat, pts.lon, sigmas ** 2, statistic="mean", bins=[lat_edges, lon_edges]
    )
    with np.errstate(invalid="ignore"):
        spread = np.sqrt(np.nan_to_num(mean_s2, nan=0.0) + np.nan_to_num(std_v, nan=0.0) ** 2)
    spread = np.where(counts > 0, spread, np.nan)

    return flux, spread, counts.astype(np.int64), lats, lons


def fe_export_province(
    aoi: AOI,
    *,
    black_path: str | Path = DEFAULT_BLACK_PATH,
    to_mmol_per_yr: bool = True,
) -> tuple[float, float, int]:
    """Per-province Fe export scalar for ``aoi`` — the anchor's native granularity.

    Collapses every program inside the AOI to a single province target: the geometric
    mean of the in-AOI point estimates (Fe export is log-normal) with a 1σ that folds in
    both the reported within-program half-ranges and the between-program scatter. This is
    the form the two-anchor inversion consumes directly (``docs/data_acquisition_roadmap
    .md``: *"Black τ is a per-province RATE target"*).

    Args:
        aoi: target AOI.
        black_path: path to the Table 1 CSV.
        to_mmol_per_yr: units of the returned scalars (default mmol Fe m⁻² yr⁻¹).

    Returns:
        ``(value, sigma, n_programs)`` — ``(nan, nan, 0)`` if the AOI has no coverage.
    """
    pts = subset_aoi(load_black_points(black_path), aoi)
    if pts.lat.size == 0:
        return float("nan"), float("nan"), 0

    scale = 1.0 if to_mmol_per_yr else 1.0 / UMOL_PER_DAY_TO_MMOL_PER_YR
    v = pts.fe_export * scale
    s = pts.fe_export_sigma * scale
    value = float(np.exp(np.mean(np.log(v))))  # geometric mean
    between = float(np.var(v)) if v.size > 1 else 0.0
    sigma = float(np.sqrt(np.mean(s ** 2) + between))
    return value, sigma, int(pts.lat.size)
