"""Loader for the Cochran et al. GP15 ²¹⁰Po/²¹⁰Pb disequilibrium dataset.

The US GEOTRACES Pacific Meridional Transect (GP15, cruise RR1814, R/V Roger
Revelle, Sep–Oct 2018) sampled the ~152°W meridian from the Alaskan margin
(56°N) south to Hawaii (20°N). Cochran and co-workers measured the
**²¹⁰Po / ²¹⁰Pb radioactive disequilibrium** on those stations — the
canonical *source-free* particle-scavenging / POC-export proxy — which is
exactly the absolute-scale scavenging anchor the two-anchor inversion needs to
pin ``scav_rat`` (the complement of the Daniels/MODIS calcite anchor for
``R_PICPOC`` and the GEOTRACES iron anchor for ``alpfe``).

**Why ²¹⁰Po/²¹⁰Pb is a *source-free* scavenging proxy.** ²¹⁰Pb (t½ ≈ 22.2 yr)
is supplied to the surface ocean from the atmosphere (²²²Rn decay) *and* in situ
from its own parent ²²⁶Ra, so its budget carries a source term that is hard to
close. ²¹⁰Po (t½ ≈ 138.4 d) has **no significant atmospheric or riverine
source** — in the water column it is produced *only* by decay of ²¹⁰Pb. Because
²¹⁰Po is strongly bio-reactive (it substitutes for sulphur, concentrates in
cytoplasm, and rides sinking biogenic particles), surface waters run a ²¹⁰Po
**deficit** relative to ²¹⁰Pb. That deficit is set purely by scavenging onto
exported particles, with the source term removed by construction — hence
"source-free". At steady state, ignoring physical transport,

    dA_Po/dt = λ_Po (A_Pb − A_Po) − J_Po = 0   ⟹   J_Po = λ_Po (A_Pb − A_Po),

where ``A`` is an activity (mBq/kg), ``λ_Po`` the ²¹⁰Po decay constant, and
``J_Po`` the net scavenging-export flux of ²¹⁰Po. The activity ratio
``AR = A_Po / A_Pb`` (< 1 under net scavenging) and the decay-weighted deficit
``λ_Po·(A_Pb − A_Po)`` are the two derived observables this loader exposes.

**Two source datasets (both open, BCO-DMO, CC-BY 4.0).** They cover Leg 1
(Seattle → Hilo) of GP15 and share the ``Station_ID / lat / lon / depth``
key:

  * ``leg1_dissolved_total_po_pb.csv`` — BCO-DMO **883724**
    (DOI 10.26008/1912/bco-dmo.883724.1). Dissolved (0.45 µm filtered) and
    total (unfiltered) ²¹⁰Po and ²¹⁰Pb from Niskin bottles. The **total**
    columns exist only at the surface (depth 0 m, 5 stations) — those are the
    surface disequilibrium the scavenging proxy is built from. The
    **dissolved** columns are depth-resolved (a cast per station) and give the
    vertical profile.
  * ``gp15_1814_particulate_po_pb.csv`` — BCO-DMO **892348**
    (DOI 10.26008/1912/bco-dmo.892348.1). In-situ-pump particulate ²¹⁰Po and
    ²¹⁰Pb in two size classes: **LPT** (large, >51 µm) and **SPT** (small,
    1–51 µm), plus **TP** (total particulate = LPT + SPT), depth-resolved.

**Real schema (inspected 2026-07-22 from the downloaded CSVs — not assumed).**
Both files are comma-delimited with a single header row. Empty cells = missing
(→ NaN). Every measured quantity ships as a value / ``SD1_`` (1σ) / ``Flag_``
triple. BCO-DMO appends a random 6-char suffix to each measurement column
(e.g. ``Po_210_T_CONC_BOTTLE_owadoh``); those suffixes are **instance-specific**
and would change on a re-serve, so this loader addresses columns by their stable
*prefix* (:func:`_resolve_column`), never by the full suffixed name.

    Shared key columns (both files):
        Station_ID              station number (float; e.g. 18.3 = a repeat)
        Start_ISO_DateTime_UTC  ISO-8601 UTC start of collection
        Start_Latitude          °N
        Start_Longitude         °E  (already −180..180; GP15 is ~−152)
        Sample_Depth            m
        Event_ID, Sample_ID     GEOTRACES event / sample numbers
        (particulate file also carries Cast_number)

    Measurement column prefixes → canonical variable (all activities mBq/kg):
        dissolved_total file
            Pb_210_T_CONC_BOTTLE   → "Pb_210_T"   total (unfiltered) ²¹⁰Pb
            Po_210_T_CONC_BOTTLE   → "Po_210_T"   total (unfiltered) ²¹⁰Po
            Pb_210_D_CONC_BOTTLE   → "Pb_210_D"   dissolved ²¹⁰Pb
            Po_210_D_CONC_BOTTLE   → "Po_210_D"   dissolved ²¹⁰Po
        particulate file
            Po_210_LPT_CONC_PUMP   → "Po_210_LPT" large-particulate ²¹⁰Po
            Po_210_SPT_CONC_PUMP   → "Po_210_SPT" small-particulate ²¹⁰Po
            Po_210_TP_CONC_PUMP    → "Po_210_TP"  total-particulate ²¹⁰Po
            Pb_210_LPT_CONC_PUMP   → "Pb_210_LPT" large-particulate ²¹⁰Pb
            Pb_210_SPT_CONC_PUMP   → "Pb_210_SPT" small-particulate ²¹⁰Pb
            Pb_210_TP_CONC_PUMP    → "Pb_210_TP"  total-particulate ²¹⁰Pb

    QC flag convention: ``1 = good data`` (SeaDataNet-style integer flag, NOT
    the ASCII-char codes GEOTRACES IDP2025 uses). Default keep {1}.

**Unit convention.** Activities are reported as **mBq per kg of seawater**.
DarwinDiff's box model works per **m³**, so — exactly as
``darwindiff.geotraces_loader`` does for iron — activities are multiplied by
``RHO_SW`` (1025 kg/m³) to reach mBq/m³. The derived scavenging flux
``λ_Po·(A_Pb − A_Po)`` is therefore mBq/m³/day after conversion; the activity
ratio is dimensionless and unit-invariant. ``RHO_SW`` is kept equal to
``darwindiff.geotraces_loader.RHO_SW`` / ``darwindiff.glodap_loader.RHO_SW`` by
convention.

**Grid.** Surface fields bin onto the **shared** integer-degree 1° grid via
``darwindiff.llc270_loader.bin_to_1deg_grid`` (edges at ``min−0.5 .. max+0.5``,
integer-degree cell centres), so the scavenging anchor lands cell-for-cell on
the same grid as the DB-1 iron forcing, DB-2 velocity, the Daniels calcite
target, and the GEOTRACES iron anchor.

Source: Cochran, J.K. et al., US GEOTRACES GP15 (RR1814).
    BCO-DMO 883724  https://www.bco-dmo.org/dataset/883724
    BCO-DMO 892348  https://www.bco-dmo.org/dataset/892348
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import NamedTuple

import numpy as np

from darwindiff.ecco_darwin_loader import AOI

# --------------------------------------------------------------------------- #
# Physical constants
# --------------------------------------------------------------------------- #
RHO_SW: float = 1025.0
"""Seawater density (kg/m³) for the mBq/kg → mBq/m³ conversion. Kept equal to
``darwindiff.geotraces_loader.RHO_SW`` and ``darwindiff.glodap_loader.RHO_SW``
deliberately."""

_MBQ_PER_KG_TO_MBQ_PER_M3: float = RHO_SW  # 1 mBq/kg × 1025 kg/m³ = 1025 mBq/m³

HALFLIFE_PO210_DAYS: float = 138.376
"""²¹⁰Po half-life (days). The short half-life is what makes the Po deficit a
*seasonal-timescale* scavenging integrator."""

HALFLIFE_PB210_YEARS: float = 22.20
"""²¹⁰Pb half-life (years) — informational; ²¹⁰Pb decay is negligible over the
Po-deficit response time, so ²¹⁰Pb is treated as the constant parent."""

LAMBDA_PO210_PER_DAY: float = np.log(2.0) / HALFLIFE_PO210_DAYS
"""²¹⁰Po decay constant λ_Po (1/day) ≈ 0.00501 — the steady-state weight that
turns the activity deficit (A_Pb − A_Po) into a scavenging-export flux."""

# QC: BCO-DMO integer flag, 1 = good data. Default keep {1}.
QC_GOOD_VALUE: int = 1
QC_GOOD: tuple[int, ...] = (QC_GOOD_VALUE,)

# --------------------------------------------------------------------------- #
# Canonical variable → stable column-name prefix (suffix stripped; see docstring)
# --------------------------------------------------------------------------- #
DISSOLVED_TOTAL_VARS: dict[str, str] = {
    "Pb_210_T": "Pb_210_T_CONC_BOTTLE",
    "Po_210_T": "Po_210_T_CONC_BOTTLE",
    "Pb_210_D": "Pb_210_D_CONC_BOTTLE",
    "Po_210_D": "Po_210_D_CONC_BOTTLE",
}
PARTICULATE_VARS: dict[str, str] = {
    "Po_210_LPT": "Po_210_LPT_CONC_PUMP",
    "Po_210_SPT": "Po_210_SPT_CONC_PUMP",
    "Po_210_TP": "Po_210_TP_CONC_PUMP",
    "Pb_210_LPT": "Pb_210_LPT_CONC_PUMP",
    "Pb_210_SPT": "Pb_210_SPT_CONC_PUMP",
    "Pb_210_TP": "Pb_210_TP_CONC_PUMP",
}
VAR_MAP_BY_KIND: dict[str, dict[str, str]] = {
    "dissolved_total": DISSOLVED_TOTAL_VARS,
    "particulate": PARTICULATE_VARS,
}

# Default on-disk file names under ``data/cochran_gp15_po_pb/``.
DEFAULT_DATA_DIR = Path("data/cochran_gp15_po_pb")
DEFAULT_FILE_BY_KIND: dict[str, str] = {
    "dissolved_total": "leg1_dissolved_total_po_pb.csv",
    "particulate": "gp15_1814_particulate_po_pb.csv",
}


# --------------------------------------------------------------------------- #
# Flat per-sample container (mirrors darwindiff.daniels_loader.DanielsPoints)
# --------------------------------------------------------------------------- #
class GP15Points(NamedTuple):
    """Flat per-sample arrays parsed from one GP15 Po/Pb CSV.

    ``lat``/``lon``/``depth``/``station`` share shape ``(n_samples,)``.
    ``activity`` maps each canonical variable name (keys of the relevant
    :data:`VAR_MAP_BY_KIND` entry) to a ``(n_samples,)`` array in **mBq/kg**,
    with missing cells as ``NaN``; ``sd`` and ``flag`` hold the matching
    1σ-uncertainty and QC-flag arrays. ``kind`` records which file this is
    (``"dissolved_total"`` or ``"particulate"``).
    """

    lat: np.ndarray
    lon: np.ndarray
    depth: np.ndarray
    station: np.ndarray
    activity: dict[str, np.ndarray]
    sd: dict[str, np.ndarray]
    flag: dict[str, np.ndarray]
    kind: str


def _to_float(cell: str) -> float:
    """Parse one CSV cell to float; empty / non-numeric → NaN."""
    cell = cell.strip()
    if not cell:
        return np.nan
    try:
        return float(cell)
    except ValueError:
        return np.nan


def _resolve_column(header: list[str], prefix: str) -> str | None:
    """Return the single header column starting with ``prefix`` (else None).

    BCO-DMO appends an instance-specific random suffix to measurement columns,
    so we match by the stable prefix rather than the full name. Raises if the
    prefix is ambiguous (more than one match), which would signal a schema
    change worth surfacing rather than silently picking one.
    """
    matches = [c for c in header if c.startswith(prefix)]
    if not matches:
        return None
    if len(matches) > 1:
        raise ValueError(
            f"ambiguous column prefix {prefix!r} matched {matches!r}; "
            "schema may have changed"
        )
    return matches[0]


# --------------------------------------------------------------------------- #
# Load / parse
# --------------------------------------------------------------------------- #
def load_gp15_points(
    path: str | Path | None = None,
    *,
    kind: str = "dissolved_total",
) -> GP15Points:
    """Parse one GP15 Po/Pb CSV into flat per-sample arrays.

    Columns are addressed by canonical name → stable prefix (see module
    docstring); the random BCO-DMO suffixes are resolved at load time so a
    re-download with different suffixes still parses.

    Args:
        path: CSV path. Defaults to
            ``data/cochran_gp15_po_pb/<file for kind>``.
        kind: ``"dissolved_total"`` (BCO-DMO 883724) or ``"particulate"``
            (BCO-DMO 892348).

    Returns:
        :class:`GP15Points`.

    Raises:
        ValueError: if ``kind`` is unknown.
        FileNotFoundError: if the CSV is not found.
        KeyError: if none of the expected measurement columns are present.
    """
    if kind not in VAR_MAP_BY_KIND:
        raise ValueError(
            f"unknown kind {kind!r}; known: {sorted(VAR_MAP_BY_KIND)}"
        )
    if path is None:
        path = DEFAULT_DATA_DIR / DEFAULT_FILE_BY_KIND[kind]
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"GP15 {kind} CSV not found: {path}\n"
            "Download with:\n"
            "  mkdir -p data/cochran_gp15_po_pb\n"
            "  curl -sSL -o data/cochran_gp15_po_pb/"
            f"{DEFAULT_FILE_BY_KIND[kind]} \\\n"
            f'    "https://www.bco-dmo.org/dataset/'
            f'{"883724" if kind == "dissolved_total" else "892348"}"'
        )

    var_map = VAR_MAP_BY_KIND[kind]
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = [r for r in reader if r and any(c.strip() for c in r)]

    def col_idx(name: str) -> int:
        try:
            return header.index(name)
        except ValueError as exc:
            raise KeyError(f"expected key column {name!r} missing") from exc

    i_lat = col_idx("Start_Latitude")
    i_lon = col_idx("Start_Longitude")
    i_depth = col_idx("Sample_Depth")
    i_station = col_idx("Station_ID")

    # Resolve each measurement column (value / SD1_ / Flag_) by prefix.
    resolved: dict[str, dict[str, int | None]] = {}
    for var, prefix in var_map.items():
        val_col = _resolve_column(header, prefix)
        sd_col = _resolve_column(header, f"SD1_{prefix}")
        flag_col = _resolve_column(header, f"Flag_{prefix}")
        resolved[var] = {
            "val": header.index(val_col) if val_col else None,
            "sd": header.index(sd_col) if sd_col else None,
            "flag": header.index(flag_col) if flag_col else None,
        }
    if all(r["val"] is None for r in resolved.values()):
        raise KeyError(
            f"no expected measurement columns for kind {kind!r} in header "
            f"{header!r}"
        )

    lat, lon, depth, station = [], [], [], []
    activity: dict[str, list[float]] = {v: [] for v in var_map}
    sd: dict[str, list[float]] = {v: [] for v in var_map}
    flag: dict[str, list[float]] = {v: [] for v in var_map}

    for row in rows:
        lat.append(_to_float(row[i_lat]))
        lon.append(_to_float(row[i_lon]))
        depth.append(_to_float(row[i_depth]))
        station.append(_to_float(row[i_station]))
        for var, cols in resolved.items():
            activity[var].append(
                _to_float(row[cols["val"]]) if cols["val"] is not None else np.nan
            )
            sd[var].append(
                _to_float(row[cols["sd"]]) if cols["sd"] is not None else np.nan
            )
            flag[var].append(
                _to_float(row[cols["flag"]]) if cols["flag"] is not None else np.nan
            )

    f64 = lambda a: np.asarray(a, dtype=np.float64)  # noqa: E731
    return GP15Points(
        lat=f64(lat),
        lon=f64(lon),
        depth=f64(depth),
        station=f64(station),
        activity={v: f64(a) for v, a in activity.items()},
        sd={v: f64(a) for v, a in sd.items()},
        flag={v: f64(a) for v, a in flag.items()},
        kind=kind,
    )


# --------------------------------------------------------------------------- #
# Derived observables
# --------------------------------------------------------------------------- #
def activity_ratio(points: GP15Points, phase: str = "T") -> np.ndarray:
    """Per-sample ²¹⁰Po/²¹⁰Pb activity ratio for a phase (dimensionless).

    ``AR < 1`` ⇒ ²¹⁰Po deficit ⇒ net scavenging/export. Unit-invariant, so no
    density conversion is applied.

    Args:
        points: parsed samples.
        phase: ``"T"`` (total/unfiltered), ``"D"`` (dissolved), or a
            particulate phase ``"TP"``/``"LPT"``/``"SPT"``.

    Returns:
        ``(n_samples,)`` ratio, ``NaN`` where either activity is missing or
        ²¹⁰Pb ≤ 0.
    """
    po = points.activity.get(f"Po_210_{phase}")
    pb = points.activity.get(f"Pb_210_{phase}")
    if po is None or pb is None:
        raise KeyError(
            f"phase {phase!r} not available for kind {points.kind!r}; "
            f"have {sorted(points.activity)}"
        )
    with np.errstate(divide="ignore", invalid="ignore"):
        r = po / pb
    r[~np.isfinite(r) | (pb <= 0)] = np.nan
    return r


def scavenging_flux(
    points: GP15Points, phase: str = "T", *, to_volumetric: bool = True
) -> np.ndarray:
    """Per-sample steady-state ²¹⁰Po scavenging-export flux ``λ_Po·(A_Pb − A_Po)``.

    This is the *source-free* scavenging rate: the decay-weighted activity
    deficit of ²¹⁰Po below its ²¹⁰Pb parent. Positive ⇒ net removal onto
    exported particles.

    Args:
        points: parsed samples.
        phase: ``"T"`` (surface total; the primary anchor) or ``"D"``.
        to_volumetric: if True (default) convert mBq/kg → mBq/m³ via
            :data:`RHO_SW`, matching DarwinDiff's per-m³ convention → flux in
            **mBq/m³/day**. If False, **mBq/kg/day**.

    Returns:
        ``(n_samples,)`` flux, ``NaN`` where either activity is missing.
    """
    po = points.activity.get(f"Po_210_{phase}")
    pb = points.activity.get(f"Pb_210_{phase}")
    if po is None or pb is None:
        raise KeyError(
            f"phase {phase!r} not available for kind {points.kind!r}; "
            f"have {sorted(points.activity)}"
        )
    deficit = pb - po  # mBq/kg
    flux = LAMBDA_PO210_PER_DAY * deficit
    if to_volumetric:
        flux = flux * _MBQ_PER_KG_TO_MBQ_PER_M3
    return flux


# --------------------------------------------------------------------------- #
# AOI subset
# --------------------------------------------------------------------------- #
def subset_aoi(points: GP15Points, aoi: AOI) -> GP15Points:
    """Filter samples to those inside an AOI bounding box (endpoints inclusive).

    Args:
        points: parsed samples (lon already in −180..180).
        aoi: AOI in −180..180 convention.

    Returns:
        A new :class:`GP15Points` with every array subset along the sample axis.
    """
    keep = (
        (points.lat >= aoi.lat_min)
        & (points.lat <= aoi.lat_max)
        & (points.lon >= aoi.lon_min)
        & (points.lon <= aoi.lon_max)
    )
    return GP15Points(
        lat=points.lat[keep],
        lon=points.lon[keep],
        depth=points.depth[keep],
        station=points.station[keep],
        activity={v: a[keep] for v, a in points.activity.items()},
        sd={v: a[keep] for v, a in points.sd.items()},
        flag={v: a[keep] for v, a in points.flag.items()},
        kind=points.kind,
    )


# --------------------------------------------------------------------------- #
# Vertical profile (the "vertical scavenging-rate profile" for the inversion)
# --------------------------------------------------------------------------- #
class ScavengingProfile(NamedTuple):
    """Depth-sorted vertical profile of the scavenging observables.

    All arrays share shape ``(n_levels,)`` and are sorted by increasing depth.
    ``activity_ratio`` is dimensionless; ``scavenging_flux`` is in mBq/m³/day
    (volumetric) unless the caller requested per-kg.
    """

    depth: np.ndarray
    activity_ratio: np.ndarray
    scavenging_flux: np.ndarray
    po: np.ndarray
    pb: np.ndarray


def scavenging_profile(
    points: GP15Points,
    *,
    phase: str = "D",
    aoi: AOI | None = None,
    to_volumetric: bool = True,
) -> ScavengingProfile:
    """Build the depth-sorted scavenging profile from a phase's activities.

    The dissolved (``"D"``) phase is depth-resolved down each cast, so it is the
    natural phase for the *vertical* scavenging-rate profile the two-anchor
    inversion consumes; the total (``"T"``) phase is surface-only. Samples with
    a missing ²¹⁰Po or ²¹⁰Pb activity are dropped.

    Args:
        points: parsed samples.
        phase: activity phase (default ``"D"``).
        aoi: optional AOI to restrict to before profiling.
        to_volumetric: convert flux to mBq/m³/day (default True).

    Returns:
        :class:`ScavengingProfile` sorted by depth.
    """
    if aoi is not None:
        points = subset_aoi(points, aoi)
    ar = activity_ratio(points, phase)
    flux = scavenging_flux(points, phase, to_volumetric=to_volumetric)
    po = points.activity[f"Po_210_{phase}"]
    pb = points.activity[f"Pb_210_{phase}"]
    keep = np.isfinite(po) & np.isfinite(pb) & np.isfinite(points.depth)
    order = np.argsort(points.depth[keep])
    return ScavengingProfile(
        depth=points.depth[keep][order],
        activity_ratio=ar[keep][order],
        scavenging_flux=flux[keep][order],
        po=po[keep][order],
        pb=pb[keep][order],
    )


# --------------------------------------------------------------------------- #
# Grid to the shared 1° grid
# --------------------------------------------------------------------------- #
class GriddedScavenging(NamedTuple):
    """A surface scavenging field binned to the shared 1° grid.

    ``field``/``count``/``spread`` are all ``(n_lat, n_lon)`` =
    ``(lat_max−lat_min+1, lon_max−lon_min+1)``. ``field`` is the per-cell mean
    of the requested observable (``NaN`` where no samples fell), ``count`` the
    number of samples averaged, ``spread`` their per-cell standard deviation
    (0 where a single sample, ``NaN`` where empty). ``lat``/``lon`` are the
    integer-degree cell centres.
    """

    field: np.ndarray
    count: np.ndarray
    spread: np.ndarray
    lat: np.ndarray
    lon: np.ndarray
    units: str


def _select_surface_values(
    points: GP15Points, observable: str, phase: str, depth_max: float,
    qc_flags: tuple[int, ...], to_volumetric: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lon, lat, value) for finite, QC-passing, surface samples."""
    if observable == "activity_ratio":
        vals = activity_ratio(points, phase)
    elif observable == "scavenging_flux":
        vals = scavenging_flux(points, phase, to_volumetric=to_volumetric)
    else:
        raise ValueError(
            f"unknown observable {observable!r}; "
            "use 'activity_ratio' or 'scavenging_flux'"
        )
    # QC: require good flags on BOTH Po and Pb of this phase where flags exist.
    keep = np.isfinite(vals) & (points.depth <= depth_max)
    for sp in (f"Po_210_{phase}", f"Pb_210_{phase}"):
        fl = points.flag.get(sp)
        if fl is not None and len(qc_flags) > 0:
            has_flag = np.isfinite(fl)
            keep &= (~has_flag) | np.isin(fl, np.asarray(qc_flags, dtype=fl.dtype))
    return points.lon[keep], points.lat[keep], vals[keep]


def scavenging_1deg_grid(
    points: GP15Points,
    aoi: AOI,
    *,
    observable: str = "activity_ratio",
    phase: str = "T",
    depth_max: float = 30.0,
    qc_flags: tuple[int, ...] = QC_GOOD,
    to_volumetric: bool = True,
) -> GriddedScavenging:
    """Bin a surface scavenging observable onto the **shared** integer-degree 1° grid.

    Uses :func:`darwindiff.llc270_loader.bin_to_1deg_grid` for the per-cell mean
    (identical edges/centres to the iron forcing, velocity, Daniels calcite, and
    GEOTRACES iron targets), and reproduces those exact edges to attach a
    per-cell sample count and standard-deviation spread.

    Args:
        points: parsed samples (pass the whole transect; AOI clipping happens
            here).
        aoi: target AOI (−180..180 lon).
        observable: ``"activity_ratio"`` (dimensionless, default) or
            ``"scavenging_flux"`` (λ_Po·deficit).
        phase: activity phase — default ``"T"`` (surface total), the
            disequilibrium the proxy is defined on.
        depth_max: surface cut (m). Default 30 m; the ``"T"`` samples sit at
            0 m so any small cut selects them.
        qc_flags: QC flags to accept (default ``(1,)`` = good). Empty tuple
            disables QC filtering.
        to_volumetric: for ``scavenging_flux``, convert to mBq/m³/day
            (default True).

    Returns:
        :class:`GriddedScavenging`.
    """
    from scipy.stats import binned_statistic_2d

    from darwindiff.llc270_loader import bin_to_1deg_grid

    lon, lat, vals = _select_surface_values(
        subset_aoi(points, aoi), observable, phase, depth_max, qc_flags,
        to_volumetric,
    )

    # Per-cell mean via the shared binner (source of truth for the grid).
    field = bin_to_1deg_grid(
        lon, lat, vals, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max
    )

    # Reproduce the SAME edges for count + spread.
    lat_edges = np.arange(aoi.lat_min - 0.5, aoi.lat_max + 0.5 + 1.0e-3, 1.0)
    lon_edges = np.arange(aoi.lon_min - 0.5, aoi.lon_max + 0.5 + 1.0e-3, 1.0)
    if len(vals) > 0:
        count, _, _, _ = binned_statistic_2d(
            lat, lon, vals, statistic="count", bins=[lat_edges, lon_edges]
        )
        spread, _, _, _ = binned_statistic_2d(
            lat, lon, vals, statistic="std", bins=[lat_edges, lon_edges]
        )
    else:
        shape = (len(lat_edges) - 1, len(lon_edges) - 1)
        count = np.zeros(shape, dtype=np.float64)
        spread = np.full(shape, np.nan, dtype=np.float64)
    spread[count == 0] = np.nan

    lat_centers = 0.5 * (lat_edges[:-1] + lat_edges[1:])
    lon_centers = 0.5 * (lon_edges[:-1] + lon_edges[1:])
    if observable == "activity_ratio":
        units = "dimensionless (210Po/210Pb activity ratio)"
    else:
        units = "mBq/m^3/day" if to_volumetric else "mBq/kg/day"

    return GriddedScavenging(
        field=field,
        count=count.astype(np.int64),
        spread=spread,
        lat=lat_centers,
        lon=lon_centers,
        units=units,
    )


def load_scavenging_anchor(
    aoi: AOI,
    *,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    observable: str = "activity_ratio",
    depth_max: float = 30.0,
) -> GriddedScavenging:
    """One-call entry point: surface ²¹⁰Po/²¹⁰Pb scavenging anchor on the shared grid.

    Loads the dissolved+total CSV, keeps the surface **total** phase, and bins
    the chosen observable to the AOI's 1° grid — the field the two-anchor
    inversion pairs with the Daniels/MODIS calcite anchor.

    Args:
        aoi: target AOI (e.g. ``AOI_BY_KEY["npac"]``).
        data_dir: directory holding the downloaded CSVs.
        observable: ``"activity_ratio"`` (default) or ``"scavenging_flux"``.
        depth_max: surface cut (m).

    Returns:
        :class:`GriddedScavenging` for the ``"T"`` (surface total) phase.
    """
    points = load_gp15_points(
        Path(data_dir) / DEFAULT_FILE_BY_KIND["dissolved_total"],
        kind="dissolved_total",
    )
    return scavenging_1deg_grid(
        points, aoi, observable=observable, phase="T", depth_max=depth_max
    )
