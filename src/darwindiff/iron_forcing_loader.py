"""Loader for the ECCO-Darwin v05 spatial soluble-iron deposition forcing (DB-1).

Track-2 replaces the 0-D box's **constant scalar** ``PHI_DUST = 5e-5`` with the
**spatial** soluble-iron deposition field that ECCO-Darwin v05 is actually forced
by -- the Mahowald-2009 product ``llc270_Mahowald_2009_soluble_iron_dust.bin``.
This is the load-bearing forcing fix from the 2026-07-07 Jon+Schultz meeting:
"ECCO-Darwin already contains the spatial variability [in the forcing field]" --
so the spatial iron structure belongs in the *forcing*, while ``alpfe`` stays a
(near-unity) global scalar. See
``docs/findings/2026-07-07_jon_schultz_meeting_capture.md`` and STATUS.md Track 2.

**The file.** v05 ``data.darwin`` sets::

    ironfile          = 'llc270_Mahowald_2009_soluble_iron_dust.bin'
    ironperiod        = -12       # 12 monthly-climatology records (repeating year)
    darwin_inscal_iron= 1000.     # multiply the raw field on read
    iron_interpMethod = 0         # step function, no temporal interpolation

So the binary is an MITgcm LLC270 **compact** forcing file: ``12`` monthly records,
each a 2-D surface field of ``13`` faces x ``270`` x ``270`` cells, single-precision
**big-endian** (``>f4``). ``12 * 13 * 270 * 270 * 4 B = 45.5 MB``.

**The unit chain (the crux -- verified against the Darwin3 iron docs).** Darwin's
surface DFe source is

    S_Fe = delta_{k,1} * (alpfe / (dr_F * hFacC)) * F_Fe        [mmol Fe / m^3 / s]

where ``F_Fe`` is the *areal* deposition flux **after** ``darwin_inscal_iron``
scaling, ``dr_F`` the surface-layer thickness (``DRF[0] = 10 m`` for LLC270 v05),
and ``hFacC`` the fractional cell height (**exactly 1** at the LLC270 open-ocean
surface -- verified: surface ``hFacC in {0, 1}``, no partial surface cells). The
raw file is in ``mol Fe/m^2/s``; ``inscal = 1000`` converts to ``mmol Fe/m^2/s``.

Matching the box's ``dDFe/dt = alpfe * PHI_DUST - ...`` [mmol/m^3/d] gives the
identity ``PHI_DUST == F_Fe / dz`` (per-time), with ``alpfe`` applied separately.
The **areal flux ``F_Fe`` is grid-independent** (it is a flux per unit *area*), so
this loader returns the areal flux and lets the transport layer divide by *its own*
surface-layer thickness ``dz`` via :func:`flux_to_phi_dust` -- rather than baking in
Darwin's 10 m. ``hFacC`` is dropped (== 1 for the box's full surface cell).

**Ocean masking.** Unlike the tracer loader (which drops land via ``field != 0``),
a *forcing* field can be legitimately near-zero over remote ocean, so ``!= 0`` would
drop real low-deposition cells and bias bin means high. This loader masks ocean via
the grid's **surface ``hFacC > 0``** (the correct land/sea mask), preserving genuine
low-deposition ocean cells.

Binning reuses :func:`darwindiff.llc270_loader.bin_to_1deg_grid` with the *same* bin
edges as the DFe/PIC targets, so the returned AOI field aligns cell-for-cell with the
recovery targets and drops straight into ``transport.grid_tendency(dust=...)``.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from darwindiff.carroll6 import PHI_DUST
from darwindiff.ecco_darwin_loader import AOI
from darwindiff.llc270_loader import aoi_mask_from_xc_yc, bin_to_1deg_grid

# --- file / grid constants (v05 data.darwin + LLC270 geometry) ---------------
IRONFILE_NAME: str = "llc270_Mahowald_2009_soluble_iron_dust.bin"
IRON_INSCAL: float = 1000.0        # darwin_inscal_iron: raw mol Fe/m^2/s -> mmol Fe/m^2/s
IRON_N_RECORDS: int = 12           # ironperiod=-12 -> 12 monthly-climatology records
LLC270_NX: int = 270
LLC270_NFACE: int = 13
LLC_COMPACT_DTYPE: str = ">f4"     # MITgcm mds/compact: big-endian single precision
SECONDS_PER_DAY: float = 86400.0

# Canonical source: PUBLIC on the NAS ECCO portal (no Earthdata login), in the
# input/darwin_forcing/ subdir (confirmed from MITgcm-contrib/ecco_darwin
# v05/llc270/readme.txt). See scripts/fetch/iron_forcing.sh.
IRON_SOURCE_URL: str = (
    "https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/input/darwin_forcing/"
    + IRONFILE_NAME
)


def read_llc270_compact(
    path: str | Path,
    *,
    n_records: int = 1,
    nx: int = LLC270_NX,
    nface: int = LLC270_NFACE,
    dtype: str = LLC_COMPACT_DTYPE,
) -> np.ndarray:
    """Read an MITgcm LLC270 **compact** binary into a numpy array.

    The compact layout stacks the ``nface`` faces (each ``nx x nx``) contiguously
    per 2-D level/record, big-endian ``float32``. Returns ``(nface, nx, nx)`` for a
    single record or ``(n_records, nface, nx, nx)`` for several (the ironfile's 12
    monthly records). The file-size check catches a wrong ``nx``/``dtype``/record
    count loudly rather than silently mis-reshaping.

    Args:
        path: path to the ``.data`` / ``.bin`` compact file.
        n_records: number of stacked 2-D records (1 for a grid field like ``XC``,
            12 for the monthly ironfile).
        nx, nface, dtype: LLC270 geometry / precision (defaults are correct for v05).

    Raises:
        FileNotFoundError: if ``path`` does not exist.
        ValueError: if the on-disk element count != ``n_records * nface * nx * nx``.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"compact binary not found: {path}")
    a = np.fromfile(path, dtype=dtype)
    expected = n_records * nface * nx * nx
    if a.size != expected:
        raise ValueError(
            f"{path.name}: got {a.size} elements, expected {expected} "
            f"(= {n_records} records x {nface} faces x {nx} x {nx}). "
            f"Wrong nx/dtype/n_records, or a truncated download?"
        )
    if n_records == 1:
        return a.reshape(nface, nx, nx)
    return a.reshape(n_records, nface, nx, nx)


def load_grid_lonlat(grid_dir: str | Path) -> tuple[np.ndarray, np.ndarray]:
    """Read ``XC.data`` / ``YC.data`` cell-center lon/lat (``-180..180`` / ``-90..90``).

    Returns ``(xc, yc)``, each ``(nface, nx, nx)`` -- the alignment key for AOI
    masking and binning (identical LLC270 geometry to every tracer / the ironfile).
    """
    grid_dir = Path(grid_dir)
    xc = read_llc270_compact(grid_dir / "XC.data")
    yc = read_llc270_compact(grid_dir / "YC.data")
    return xc, yc


def load_surface_ocean_mask(
    grid_dir: str | Path, *, nx: int = LLC270_NX, nface: int = LLC270_NFACE
) -> np.ndarray:
    """Boolean ``(nface, nx, nx)`` surface land/sea mask from ``hFacC`` (``> 0`` = ocean).

    ``hFacC`` is the 3-D fractional cell height ``(k, face, nx, nx)`` in compact
    order with ``k`` **outermost**, so the surface level is the first ``nface*nx*nx``
    values -- read only those (a partial read of the 181 MB file). At the LLC270
    surface ``hFacC`` is exactly 0 (land) or 1 (ocean); this is the correct mask for
    a forcing field (see module docstring on why ``field != 0`` is wrong here).
    ``nx``/``nface`` are exposed for testing a synthetic ``hFacC``.
    """
    path = Path(grid_dir) / "hFacC.data"
    if not path.is_file():
        raise FileNotFoundError(f"hFacC not found: {path}")
    n = nface * nx * nx
    surf = np.fromfile(path, dtype=LLC_COMPACT_DTYPE, count=n)
    if surf.size != n:
        raise ValueError(
            f"hFacC surface read short: {surf.size} elements from {path} (expected {n})"
        )
    return (surf.reshape(nface, nx, nx) > 0.0)


def load_surface_dz(grid_dir: str | Path) -> float:
    """Surface-layer thickness ``DRF[0]`` in metres (``10.0`` for LLC270 v05).

    This is Darwin's ``dr_F`` -- the depth the areal deposition is injected into in
    the native model. The box/transport model injects into *its own* surface layer
    of thickness ``dz``, so this is provided for reference / faithful native
    reproduction, not required by :func:`flux_to_phi_dust`.
    """
    drf = read_drf(grid_dir)
    return float(drf[0])


def read_drf(grid_dir: str | Path) -> np.ndarray:
    """Read the 50 vertical layer thicknesses ``DRF`` (metres)."""
    path = Path(grid_dir) / "DRF.data"
    if not path.is_file():
        raise FileNotFoundError(f"DRF not found: {path}")
    return np.fromfile(path, dtype=LLC_COMPACT_DTYPE)


def read_soluble_iron_flux(
    iron_path: str | Path,
    *,
    month: int | None = None,
    inscal: float = IRON_INSCAL,
    n_records: int = IRON_N_RECORDS,
    nx: int = LLC270_NX,
    nface: int = LLC270_NFACE,
) -> np.ndarray:
    """Native-cell areal soluble-Fe deposition flux ``[mmol Fe/m^2/s]``, ``(nface,nx,nx)``.

    Reads the 12-record compact ironfile, applies ``darwin_inscal_iron`` (raw
    ``mol Fe/m^2/s`` -> ``mmol Fe/m^2/s``), and reduces the time axis:

    - ``month=None`` (default): the **annual mean** over the 12 monthly records --
      the time-mean forcing that matches the time-mean (climatology) DFe target the
      Phase-1 E2 fit uses. (Unweighted 12-month mean; day-length weighting differs
      by <~2 % and is a negligible refinement.)
    - ``month`` in ``1..12``: that single month's field, for the seasonal-excitation
      follow-up (pair with :func:`month_of_day` to drive time-varying ``dust=``).

    The areal flux is **grid-independent**; convert to a volumetric box source with
    :func:`flux_to_phi_dust`.
    """
    if month is not None and not (1 <= month <= n_records):
        raise ValueError(f"month must be in 1..{n_records} or None, got {month!r}")
    stack = read_llc270_compact(iron_path, n_records=n_records, nx=nx, nface=nface)
    field = stack.mean(axis=0) if month is None else stack[month - 1]
    return (field.astype(np.float64) * float(inscal))


def iron_flux_aoi_grid(
    iron_path: str | Path,
    grid_dir: str | Path,
    aoi: AOI,
    *,
    month: int | None = None,
) -> np.ndarray:
    """Areal soluble-Fe flux binned to the AOI's 1-deg grid ``[mmol Fe/m^2/s]``.

    Loads the native flux, masks to the AOI bbox **and** the surface ocean mask
    (``hFacC > 0``) **and** finite values, then bin-averages onto the AOI's 1-deg
    grid using the *same* edges as the DFe/PIC targets
    (:func:`darwindiff.llc270_loader.bin_to_1deg_grid`). Returns ``(n_lat, n_lon)``
    with ``NaN`` at land / no-coverage bins -- aligned cell-for-cell with the
    recovery target grid, ready for :func:`phi_dust_surface_field`.
    """
    flux = read_soluble_iron_flux(iron_path, month=month)
    xc, yc = load_grid_lonlat(grid_dir)
    ocean = load_surface_ocean_mask(grid_dir)
    good = (
        aoi_mask_from_xc_yc(xc, yc, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
        & ocean
        & np.isfinite(flux)
    )
    return bin_to_1deg_grid(
        xc[good], yc[good], flux[good],
        aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max,
    )


def flux_to_phi_dust(areal_flux: np.ndarray | float, dz: float) -> np.ndarray | float:
    """Areal flux ``[mmol Fe/m^2/s]`` -> volumetric source ``[mmol Fe/m^3/d]``.

    ``PHI_DUST_cell = areal_flux * 86400 / dz`` -- the per-cell, spatially-varying
    drop-in replacement for the scalar :data:`darwindiff.carroll6.PHI_DUST`, for a
    surface layer of thickness ``dz`` metres. ``alpfe`` is applied separately (in the
    box tendency), exactly as Darwin applies its solubility scalar to the deposition.
    """
    if dz <= 0:
        raise ValueError(f"dz must be positive metres, got {dz!r}")
    return areal_flux * SECONDS_PER_DAY / dz


def phi_dust_surface_field(
    areal_flux_grid: np.ndarray,
    dz: float,
    n_z: int,
    *,
    fill: float = 0.0,
    dtype=None,
    device=None,
):
    """Build the ``[Y, X, Z]`` **surface-only** volumetric dust field for transport.

    Composes the spatial areal flux with deep-review fix **A4** (dust is a *surface*
    flux, not a per-layer injection): the volumetric rate
    ``flux_to_phi_dust(areal_flux_grid, dz)`` is placed at ``Z=0`` and zero below,
    so a column's top layer behaves like the 0-D box and column-integrated dust is
    independent of ``n_z``. ``NaN`` bins (land / no coverage) are replaced by ``fill``
    (default 0 -- no deposition there). The result broadcasts against ``DFe`` of shape
    ``[..., Y, X, Z]`` and drops into ``transport.grid_tendency(dust=...)``.

    **Coverage caveat (deep review 2026-07-08):** the ``fill=0`` at no-coverage bins
    is a *fabricated* zero source. ``transport.interior_mask`` drops only the outer
    boundary ring (the A6 wall artifact), **not** interior land / no-coverage bins --
    so on any AOI with interior no-coverage cells (coastal / island windows; eqpac has
    none) the E2 loss must AND-in a **separate** finite-coverage mask, use
    :func:`coverage_mask` (computed **before** this fill) so those fabricated-zero
    cells are excluded from the residual. ``dtype`` defaults to ``float64`` to match
    the loader's fp64 pipeline; pass the transport state's dtype/device explicitly
    when feeding an fp32 / GPU rollout.

    Returns a torch tensor of shape ``[Y, X, n_z]``.
    """
    import torch

    vol = flux_to_phi_dust(np.asarray(areal_flux_grid, dtype=np.float64), dz)
    vol = np.nan_to_num(vol, nan=fill, posinf=fill, neginf=fill)
    ny, nx = vol.shape
    out = torch.zeros(ny, nx, n_z, dtype=dtype or torch.float64, device=device)
    out[..., 0] = torch.as_tensor(vol, dtype=out.dtype, device=device)
    return out


def coverage_mask(areal_flux_grid: np.ndarray) -> np.ndarray:
    """Boolean ``[Y, X]`` mask of AOI bins with real deposition coverage (finite).

    :func:`iron_flux_aoi_grid` returns ``NaN`` at land / no-native-cell bins, and
    :func:`phi_dust_surface_field` then fills those with a *fabricated* zero source.
    Compute this mask **before** building the dust field and AND it into the E2 loss
    mask (together with ``transport.interior_mask``) so closures are not fit against
    cells whose iron forcing was silently zeroed. ``True`` = keep (finite coverage).
    """
    return np.isfinite(np.asarray(areal_flux_grid))


def phi_dust_sanity(
    areal_flux_grid: np.ndarray,
    *,
    dz: float = 50.0,
    reference: float = PHI_DUST,
    areal_range: tuple[float, float] = (1.0e-12, 1.0e-7),
) -> dict:
    """Units / endianness guard on a loaded soluble-Fe areal flux (physical-range check).

    ``within_tol`` is True iff the AOI-mean **areal** flux sits in ``areal_range``
    (default ``[1e-12, 1e-7] mmol Fe/m^2/s``), which spans dust-poor (Southern Ocean) to
    dust-band (Saharan-outflow) ocean for the Mahowald-2009 soluble product. A wrong
    endianness / dtype / missing-``inscal`` shows up as ``NaN`` or a many-orders miss and
    fails the range.

    **Do NOT gate on the ratio to ``PHI_DUST``.** The box's ``PHI_DUST = 5e-5`` is a
    *tuned effective* source, and the REAL local deposition runs ~100-250x **below** it in
    dust-poor regions (verified: eqpac vol@50m ~2.4e-7 vs PHI_DUST 5e-5) -- because those
    regions get their iron from lateral/vertical **transport** (e.g. the Equatorial
    Undercurrent), which the 0-D box faked with an inflated scalar. That gap is the point
    of Track 2, not a load error. The ``ratio`` is returned for reference only.
    """
    areal = np.asarray(areal_flux_grid, dtype=np.float64)
    mean_areal = float(np.nanmean(areal))
    mean_vol = float(np.nanmean(flux_to_phi_dust(areal, dz)))
    lo, hi = areal_range
    within = bool(np.isfinite(mean_areal) and lo <= mean_areal <= hi)
    return {
        "mean_areal_mmol_m2_s": mean_areal,
        "mean_volumetric_mmol_m3_d": mean_vol,
        "reference_phi_dust": reference,
        "ratio": (mean_vol / reference if reference else float("inf")),
        "within_tol": within,
        "areal_range": areal_range,
        "dz": dz,
    }


def month_of_day(t_days: float, *, days_per_year: float = 365.0) -> int:
    """Map integrator time ``t`` (days) to a monthly-climatology index ``1..12``.

    For driving seasonal ``dust=`` forcing through ``integrators.integrate`` (which
    passes ``t`` in days to ``f(t, x)``): select the month, no temporal interpolation
    -- matching v05's ``iron_interpMethod = 0`` (step function). Wraps at the year
    boundary so multi-year rollouts repeat the 12-month climatology.
    """
    frac = (t_days % days_per_year) / days_per_year
    return min(12, int(frac * 12.0) + 1)
