"""Loader for the Rufas et al. 2024 sediment-trap + ²³⁴Th POC-flux compilation.

This is the **Darwin-independent, observational** anchor for the *magnitude of
remineralisation* — the depth-attenuation of the sinking particulate-organic-
carbon (POC) flux that the Carroll-6 box's export/remineralisation term sets.
Where :mod:`darwindiff.daniels_loader` anchors the surface **rain ratio**
(``R_PICPOC`` = calcite:organic production), this dataset anchors the
**flux-through-the-mesopelagic**: how much of the euphotic-zone export survives
to ~1000 m. Together they are the two absolute anchors the two-anchor inversion
ties the recovered DFe/carbon fields to (a real production ratio + a real flux
magnitude), pinning scales that z-scored surrogate losses homogenise away.

Two quantities per location feed the inversion:

- **POC export flux** at the base of the euphotic zone (``z_eu``), the
  numerator of the biological pump — units **mmol C m⁻² d⁻¹** in the
  DarwinDiff convention (the compilation stores it in mg C m⁻² d⁻¹; see the
  unit note below).
- **Transfer efficiency** ``Teff`` = flux(z_meso ≈ 1000 m) / flux(z_eu), the
  dimensionless fraction of export reaching the deep mesopelagic — a direct,
  absolute constraint on the remineralisation length scale.

Dataset
-------
Citation: A. Rufas, S. Khatiwala, K. M. Bisson, A. P. Martin, H. A. Bouman
(2024), "Can We Constrain Geographical Variability in the Biological Carbon
Pump's Transfer Efficiency from Observations?" (submitted to *GRL*). Code +
processed data: https://doi.org/10.5281/zenodo.14173801 (v1.1.1), CC-BY-4.0.

The compilation covers **six time-series stations** (verified against the
shipped ``timeseries_station_information.mat`` — ordering is load-bearing and
matches the metric arrays cell-for-cell):

    idx  name         tag         lat      lon      biome
    0    EqPac        eqpac        0.0°N  -140.0°E  equatorial Pacific upwelling
    1    OSP          osp         50.0°N  -145.0°E  HNLC subpolar NE Pacific
    2    PAP-SO       papso       49.0°N   -16.5°E  subpolar NE Atlantic
    3    BATS/OFP     batsofp     31.6°N   -64.2°E  subtropical NW Atlantic
    4    HOT/ALOHA    hotaloha    22.5°N  -158.0°E  subtropical NE Pacific
    5    HAUSGARTEN   hausgarten  79.0°N     4.3°E  polar Atlantic-Arctic

**Only the processed files ship.** The raw master compilation
(``dataset_s0_trap_and_radionuclide_compilation.xlsx``) is withheld — it holds
third-party data not in a preservation repository. This loader therefore reads
the processed products the paper's own scripts emitted:

    processed/bcpmetrics_classic.mat          <- primary source (this loader)
    processed/timeseries_station_information.mat  <- station geography
    processed/dataset_s2_figure4.csv          <- human-readable mirror (Dataset S2)
    processed/dataset_s1_figureS3.csv         <- Martin's b / z* fit scenarios

**Real schema of ``bcpmetrics_classic.mat``** (validated 2026-07-22 against the
shipped MATLAB v5 .mat; loaded via :func:`scipy.io.loadmat`):

    classic                    struct
      .teff.ave     (6,)       transfer efficiency, dimensionless
      .teff.stdevupp (6,)      +1σ (Monte-Carlo error propagation)
      .teff.stdevlow (6,)      −1σ
      .martinb.ave  (6,)       Martin's b (attenuation exponent), for reference
      .zstar.ave    (6,)       remin length scale z* [m], for reference
    classicAnnualDhAvg  (3,6)  POC flux at 3 depth horizons × 6 stations
    classicAnnualDhErrTot (3,6) total (systematic+random) flux error

    Depth-horizon rows of classicAnnualDhAvg (from
    calculateBcpMetricsFromTrapAndRadCompilation.m, arrayFlux dim 1):
        row 0 = base of euphotic zone (z_eu)   -> POC EXPORT flux
        row 1 = base of mesopelagic (z_meso ≈ 1000 m)
        row 2 = inflexion point (deeper)
    and Teff = flux(row 1) / flux(row 0).

**Unit note (critical).** ``classicAnnualDhAvg`` is stored in **mg C m⁻² d⁻¹**:
``processPocFluxFromTrapAndRadCompilation.m:285`` multiplies the native
mmol C m⁻² d⁻¹ by ``MOLAR_MASS_CARBON = 12.011`` before caching. This loader
divides it back out to return **mmol C m⁻² d⁻¹** (DarwinDiff's flux
convention), matching the mmol/m³-family units the box model and the other
observational loaders use. ``Teff`` is a flux ratio and is dimensionless — no
conversion. Set ``to_mmol=False`` to keep the native mg C m⁻² d⁻¹.

Sparse-coverage reality
-----------------------
Six point stations. Any single AOI box contains **0 or 1** station, so the
gridded field is almost entirely NaN with at most one populated 1° cell. That
is expected and honest — the grid path exists to register the anchor on the
**shared integer-degree 1° grid** (:func:`darwindiff.llc270_loader.bin_to_1deg_grid`)
cell-for-cell with the DB-1/DB-2/Daniels targets, exactly as
:func:`darwindiff.geotraces_loader.dfe_aoi_1deg_grid` does. For the scalar
per-AOI anchor the inversion actually consumes, use
:func:`two_anchor_values`, which returns the (flux, Teff) pair for the station
inside the AOI (or NaN when the AOI has no station). Of the project AOIs, three
map cleanly: ``eqpac``←EqPac, ``npac``←OSP, ``npsg``←HOT/ALOHA.

Quick usage::

    from darwindiff.rufas2024_poc_flux_loader import two_anchor_values
    from darwindiff.ecco_darwin_loader import AOI_BY_KEY

    anchor = two_anchor_values(AOI_BY_KEY["eqpac"])
    # anchor.poc_export_flux ~ 12.5 mmol C m⁻² d⁻¹, anchor.teff ~ 0.057 at EqPac
"""

from __future__ import annotations

from pathlib import Path
from typing import NamedTuple

import numpy as np

from darwindiff.ecco_darwin_loader import AOI

# Default on-disk path. The processed .mat files are gitignored under
# data/rufas2024_poc_flux/processed/; anchored to the repo via __file__ so it
# resolves regardless of the process CWD, mirroring the Daniels/GLODAP loaders.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUFAS_DIR: Path = _REPO_ROOT / "data" / "rufas2024_poc_flux" / "processed"

# Shipped processed products consumed here.
_BCPMETRICS_FILE = "bcpmetrics_classic.mat"
_STATION_INFO_FILE = "timeseries_station_information.mat"

# Molar mass of carbon used by the paper to convert mmol->mg
# (processPocFluxFromTrapAndRadCompilation.m:51). We divide it back out to
# return the DarwinDiff-convention mmol C m⁻² d⁻¹.
MOLAR_MASS_CARBON: float = 12.011
"""g C / mol — the exact constant the compilation used for mg⇄mmol, kept in
sync deliberately so the round-trip is lossless."""

# Depth-horizon row indices into classicAnnualDhAvg (see module docstring).
_ROW_EXPORT_ZEU: int = 0    # base of euphotic zone -> POC export flux
_ROW_ZMESO: int = 1         # base of mesopelagic (~1000 m)
_ROW_INFLEXION: int = 2     # deeper inflexion point


class RufasStation(NamedTuple):
    """One time-series station's POC-flux BCP metrics.

    Fluxes are in **mmol C m⁻² d⁻¹** (DarwinDiff convention) unless the loader
    was called with ``to_mmol=False`` (then native mg C m⁻² d⁻¹). ``teff`` and
    its ±σ bounds are dimensionless. NaN where the compilation has no fit for
    that station (e.g. HAUSGARTEN z*).
    """

    name: str                    # e.g. "EqPac"
    tag: str                     # e.g. "eqpac"
    lat: float                   # deg N
    lon: float                   # deg E, -180..180
    poc_export_flux: float       # flux at base of euphotic zone (z_eu)
    poc_export_flux_err: float   # total (sys+rand) error, same units
    flux_zmeso: float            # flux at base of mesopelagic (~1000 m)
    flux_zmeso_err: float
    teff: float                  # flux_zmeso / poc_export_flux, dimensionless
    teff_stdev_upp: float        # +1σ
    teff_stdev_low: float        # −1σ
    martinb: float               # Martin's b (attenuation exponent), reference
    zstar: float                 # remin length scale z* [m], reference


class TwoAnchorValues(NamedTuple):
    """The per-AOI (flux, Teff) pair the two-anchor inversion consumes.

    All fields are scalars for the single station inside the AOI, or NaN when
    the AOI contains no Rufas station. ``station`` names which station (or is
    ``None`` when empty) so callers can log provenance.
    """

    poc_export_flux: float       # mmol C m⁻² d⁻¹ (or mg if to_mmol=False)
    poc_export_flux_err: float
    teff: float                  # dimensionless
    teff_stdev_upp: float
    teff_stdev_low: float
    station: str | None          # station name, or None if AOI has no station


def _rufas_path(rufas_dir: str | Path, filename: str) -> Path:
    """Resolve and existence-check a processed file under the cache dir."""
    path = Path(rufas_dir) / filename
    if not path.is_file():
        raise FileNotFoundError(
            f"Rufas processed file not found: {path}. Expected the Zenodo "
            f"14173801 processed products under {rufas_dir}; re-run the "
            f"downloader if the cache is missing."
        )
    return path


def open_rufas_stations(
    rufas_dir: str | Path = DEFAULT_RUFAS_DIR,
    *,
    to_mmol: bool = True,
) -> list[RufasStation]:
    """Open the processed compilation and return the six stations' BCP metrics.

    This is the "open the file" step of the loader pattern: it reads
    ``bcpmetrics_classic.mat`` (the metrics) and
    ``timeseries_station_information.mat`` (the geography), aligns them by the
    shared station ordering, converts flux units, and returns a flat list of
    :class:`RufasStation` records — one per time-series site.

    Args:
        rufas_dir: directory holding the processed ``.mat`` products (default
            :data:`DEFAULT_RUFAS_DIR`).
        to_mmol: convert the cached mg C m⁻² d⁻¹ fluxes back to
            mmol C m⁻² d⁻¹ (default True; DarwinDiff internal convention).
            Teff is unaffected (dimensionless ratio).

    Returns:
        List of six :class:`RufasStation`, in the compilation's native order
        (EqPac, OSP, PAP-SO, BATS/OFP, HOT/ALOHA, HAUSGARTEN).

    Raises:
        FileNotFoundError: if either processed .mat is missing.
    """
    from scipy.io import loadmat

    info = loadmat(
        str(_rufas_path(rufas_dir, _STATION_INFO_FILE)),
        squeeze_me=True,
        struct_as_record=False,
    )
    met = loadmat(
        str(_rufas_path(rufas_dir, _BCPMETRICS_FILE)),
        squeeze_me=True,
        struct_as_record=False,
    )

    names = [str(s) for s in info["STATION_NAMES"]]
    tags = [str(s) for s in info["STATION_TAGS"]]
    lats = np.asarray(info["LOC_LATS"], dtype=float)
    lons = np.asarray(info["LOC_LONS"], dtype=float)

    classic = met["classic"]
    teff = classic.teff
    martinb = classic.martinb
    zstar = classic.zstar
    dh_avg = np.asarray(met["classicAnnualDhAvg"], dtype=float)     # (3, 6)
    dh_err = np.asarray(met["classicAnnualDhErrTot"], dtype=float)  # (3, 6)

    n = len(names)
    scale = 1.0 / MOLAR_MASS_CARBON if to_mmol else 1.0

    export_flux = dh_avg[_ROW_EXPORT_ZEU, :] * scale
    export_err = dh_err[_ROW_EXPORT_ZEU, :] * scale
    zmeso_flux = dh_avg[_ROW_ZMESO, :] * scale
    zmeso_err = dh_err[_ROW_ZMESO, :] * scale

    teff_ave = np.asarray(teff.ave, dtype=float)
    teff_upp = np.asarray(teff.stdevupp, dtype=float)
    teff_low = np.asarray(teff.stdevlow, dtype=float)
    mb_ave = np.asarray(martinb.ave, dtype=float)
    zs_ave = np.asarray(zstar.ave, dtype=float)

    stations: list[RufasStation] = []
    for i in range(n):
        stations.append(
            RufasStation(
                name=names[i],
                tag=tags[i],
                lat=float(lats[i]),
                lon=float(lons[i]),
                poc_export_flux=float(export_flux[i]),
                poc_export_flux_err=float(export_err[i]),
                flux_zmeso=float(zmeso_flux[i]),
                flux_zmeso_err=float(zmeso_err[i]),
                teff=float(teff_ave[i]),
                teff_stdev_upp=float(teff_upp[i]),
                teff_stdev_low=float(teff_low[i]),
                martinb=float(mb_ave[i]),
                zstar=float(zs_ave[i]),
            )
        )
    return stations


def subset_aoi_rufas(
    stations: list[RufasStation], aoi: AOI
) -> list[RufasStation]:
    """Filter stations to those whose (lat, lon) fall inside an AOI box.

    Mirrors :func:`darwindiff.geotraces_loader.subset_aoi_geotraces`: a station
    is kept when its coordinate lies within the AOI bounds (``-180..180`` lon
    convention). With only six global stations an AOI holds 0 or 1 of them.

    Args:
        stations: list from :func:`open_rufas_stations`.
        aoi: AOI in ``-180..180`` lon convention.

    Returns:
        The stations inside the AOI (possibly empty).
    """
    return [
        s
        for s in stations
        if aoi.lat_min <= s.lat <= aoi.lat_max
        and aoi.lon_min <= s.lon <= aoi.lon_max
    ]


def _bin_stations_to_1deg(
    stations: list[RufasStation],
    aoi: AOI,
    value_fn,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin a per-station scalar onto the shared integer-degree 1° AOI grid.

    Reuses :func:`darwindiff.llc270_loader.bin_to_1deg_grid` for the mean
    (identical edges/centers to DB-1/DB-2/Daniels), and computes a matching
    per-cell count via the same bin edges so callers get coverage alongside the
    field. ``value_fn`` maps a :class:`RufasStation` to the scalar to bin.

    Returns:
        ``(field, count)`` — both ``(n_lat, n_lon)`` with
        ``n_lat = lat_max - lat_min + 1``. ``field`` is NaN in empty cells;
        ``count`` is the integer number of stations per cell (0/1 in practice).
    """
    from darwindiff.llc270_loader import bin_to_1deg_grid

    n_lat = int(round(aoi.lat_max - aoi.lat_min)) + 1
    n_lon = int(round(aoi.lon_max - aoi.lon_min)) + 1

    if not stations:
        empty = np.full((n_lat, n_lon), np.nan, dtype=np.float64)
        return empty, np.zeros((n_lat, n_lon), dtype=np.int64)

    lats = np.array([s.lat for s in stations], dtype=float)
    lons = np.array([s.lon for s in stations], dtype=float)
    vals = np.array([value_fn(s) for s in stations], dtype=float)
    finite = np.isfinite(vals) & np.isfinite(lats) & np.isfinite(lons)
    lats, lons, vals = lats[finite], lons[finite], vals[finite]

    if lats.size == 0:
        empty = np.full((n_lat, n_lon), np.nan, dtype=np.float64)
        return empty, np.zeros((n_lat, n_lon), dtype=np.int64)

    field = bin_to_1deg_grid(
        lons, lats, vals,
        aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max,
    )
    # True per-cell station count on the *same* integer-degree edges
    # bin_to_1deg_grid uses (centers at integer degrees, edges at min-0.5 ..
    # max+0.5). statistic="count" is NaN-free, so no cast warnings.
    from scipy.stats import binned_statistic_2d

    lat_edges = np.arange(aoi.lat_min - 0.5, aoi.lat_max + 0.5 + 1.0e-3, 1.0)
    lon_edges = np.arange(aoi.lon_min - 0.5, aoi.lon_max + 0.5 + 1.0e-3, 1.0)
    count, _, _, _ = binned_statistic_2d(
        lats, lons, vals, statistic="count", bins=[lat_edges, lon_edges]
    )
    return field, count.astype(np.int64)


def poc_flux_aoi_1deg_grid(
    aoi: AOI,
    rufas_dir: str | Path = DEFAULT_RUFAS_DIR,
    *,
    horizon: str = "export",
    to_mmol: bool = True,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin the POC flux onto the shared integer-degree 1° AOI grid.

    Registers the flux anchor cell-for-cell with the DB-1 iron forcing, DB-2
    velocity, and Daniels calcite target (all on
    :func:`darwindiff.llc270_loader.bin_to_1deg_grid`'s integer-degree grid),
    exactly as :func:`darwindiff.geotraces_loader.dfe_aoi_1deg_grid` does. The
    field is almost all NaN (one station per AOI at most) by construction.

    Args:
        aoi: target AOI (``-180..180`` lon convention).
        rufas_dir: processed-cache directory (default :data:`DEFAULT_RUFAS_DIR`).
        horizon: which depth horizon to return — ``"export"`` (base of euphotic
            zone, the default) or ``"zmeso"`` (~1000 m).
        to_mmol: return mmol C m⁻² d⁻¹ (default True) vs native mg C m⁻² d⁻¹.

    Returns:
        ``(field, count)`` — both ``(n_lat, n_lon)``. ``field`` in
        mmol C m⁻² d⁻¹ (or mg if ``to_mmol=False``), NaN in empty cells;
        ``count`` is stations-per-cell.

    Raises:
        ValueError: if ``horizon`` is not ``"export"`` or ``"zmeso"``.
    """
    if horizon == "export":
        value_fn = lambda s: s.poc_export_flux  # noqa: E731
    elif horizon == "zmeso":
        value_fn = lambda s: s.flux_zmeso  # noqa: E731
    else:
        raise ValueError(
            f"horizon must be 'export' or 'zmeso', got {horizon!r}"
        )
    stations = subset_aoi_rufas(
        open_rufas_stations(rufas_dir, to_mmol=to_mmol), aoi
    )
    return _bin_stations_to_1deg(stations, aoi, value_fn)


def teff_aoi_1deg_grid(
    aoi: AOI,
    rufas_dir: str | Path = DEFAULT_RUFAS_DIR,
) -> tuple[np.ndarray, np.ndarray]:
    """Bin the dimensionless transfer efficiency onto the shared 1° AOI grid.

    Companion to :func:`poc_flux_aoi_1deg_grid` for the Teff anchor. Teff is a
    flux ratio, so no unit conversion applies.

    Args:
        aoi: target AOI (``-180..180`` lon convention).
        rufas_dir: processed-cache directory (default :data:`DEFAULT_RUFAS_DIR`).

    Returns:
        ``(field, count)`` — both ``(n_lat, n_lon)``. ``field`` is Teff
        (dimensionless), NaN in empty cells; ``count`` is stations-per-cell.
    """
    stations = subset_aoi_rufas(open_rufas_stations(rufas_dir), aoi)
    return _bin_stations_to_1deg(stations, aoi, lambda s: s.teff)


def two_anchor_values(
    aoi: AOI,
    rufas_dir: str | Path = DEFAULT_RUFAS_DIR,
    *,
    to_mmol: bool = True,
) -> TwoAnchorValues:
    """Return the scalar (POC export flux, Teff) anchor pair for an AOI.

    This is the value form the two-anchor inversion consumes directly: the
    remineralisation-magnitude anchor for the single Rufas station inside the
    AOI. When the AOI holds no station, every field is NaN and ``station`` is
    ``None`` (the caller gates the loss term off, as with an empty Daniels
    target). When more than one station somehow falls inside (not the case for
    the project AOIs), the first is returned.

    Args:
        aoi: target AOI (``-180..180`` lon convention).
        rufas_dir: processed-cache directory (default :data:`DEFAULT_RUFAS_DIR`).
        to_mmol: return flux in mmol C m⁻² d⁻¹ (default True) vs mg C m⁻² d⁻¹.

    Returns:
        :class:`TwoAnchorValues` for the AOI's station (or all-NaN if none).
    """
    inside = subset_aoi_rufas(
        open_rufas_stations(rufas_dir, to_mmol=to_mmol), aoi
    )
    if not inside:
        return TwoAnchorValues(
            poc_export_flux=float("nan"),
            poc_export_flux_err=float("nan"),
            teff=float("nan"),
            teff_stdev_upp=float("nan"),
            teff_stdev_low=float("nan"),
            station=None,
        )
    s = inside[0]
    return TwoAnchorValues(
        poc_export_flux=s.poc_export_flux,
        poc_export_flux_err=s.poc_export_flux_err,
        teff=s.teff,
        teff_stdev_upp=s.teff_stdev_upp,
        teff_stdev_low=s.teff_stdev_low,
        station=s.name,
    )
