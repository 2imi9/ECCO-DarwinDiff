"""Loader for the ECCO-Darwin v05 prescribed velocity field (DB-2).

The Track-2 transport UDE is driven by ECCO-Darwin's *own* velocities (no new GCM
runs). v05 conveniently publishes them **cell-centered and already geographic**:
``uVel_C`` (fldList ``UE_VEL_C`` = eastward velocity at the cell center) and ``vVel_C``
(``VN_VEL_C`` = northward), so there is **no C-grid staggering and no AngleCS/AngleSN
rotation to undo** -- ``uVel_C`` maps straight to the transport's zonal ``u`` and
``vVel_C`` to the meridional ``v`` on the regular AOI grid. (``wVel`` = ``WVEL`` is also
published, but the transport recomputes ``w`` from continuity for discrete
divergence-freeness, so ``wVel`` is only a cross-check.)

Files are LLC270 native mds binaries (``uVel_C.NNNN.data`` + ``.meta``), 50 levels,
big-endian float32, one record per monthly snapshot -- the same format as the tracers in
:mod:`darwindiff.llc270_loader`. This loader reads only the **top ``n_z`` levels** (a
partial read, since ``k`` is outermost in the compact layout), time-means over the
requested iterations (climatology), AOI-bins each level onto the 1-deg grid that the
DFe/PIC targets and the iron forcing share, and converts **m/s -> m/day** so the velocity
is consistent with the transport's day-based ``dt``.

**Unit / balance note (DB-1 finding):** the real local iron deposition is ~200x below
the box's tuned ``PHI_DUST`` because dust-poor regions get their iron from *transport*
(the Equatorial Undercurrent) -- so this velocity field is what makes the real (low) iron
forcing produce realistic DFe. That is the Track-2 thesis; DB-2 supplies its load-bearing
input.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from darwindiff.ecco_darwin_loader import AOI
from darwindiff.iron_forcing_loader import (
    LLC270_NFACE,
    LLC270_NX,
    LLC_COMPACT_DTYPE,
    load_surface_ocean_mask,  # (surface only; per-level mask uses read_hfacc_topz below)
)
from darwindiff.llc270_loader import (
    aoi_mask_from_xc_yc,
    bin_to_1deg_grid,
    list_available_iterations,
)

# Friendly velocity dir -> .meta fldList (verified against the on-disk v05 monthly files).
VEL_FLDLIST: dict[str, str] = {"uVel_C": "UE_VEL_C", "vVel_C": "VN_VEL_C", "wVel": "WVEL"}
M_PER_S_TO_M_PER_DAY: float = 86400.0
MITGCM_MISSING: float = -999.0  # .meta missingValue on land / fill


def read_hfacc_topz(grid_dir: str | Path, n_z: int, *, nx: int = LLC270_NX,
                    nface: int = LLC270_NFACE) -> np.ndarray:
    """Top ``n_z`` levels of ``hFacC`` (fractional cell height; ``>0`` = ocean), a
    partial read of the 3-D compact file (``k`` outermost). Shape ``(n_z, nface, nx, nx)``."""
    path = Path(grid_dir) / "hFacC.data"
    n = n_z * nface * nx * nx
    a = np.fromfile(path, dtype=LLC_COMPACT_DTYPE, count=n)
    if a.size != n:
        raise ValueError(f"hFacC short read: {a.size} < {n} from {path}")
    return a.reshape(n_z, nface, nx, nx)


def read_velocity_native_topz(
    monthly_root: str | Path,
    var: str,
    *,
    n_z: int,
    iters: int | list[int] | str = "all",
    max_iters: int | None = None,
    nx: int = LLC270_NX,
    nface: int = LLC270_NFACE,
) -> np.ndarray:
    """Time-mean of the top ``n_z`` levels of a native velocity field, in **m/s**.

    ``var`` is a key of :data:`VEL_FLDLIST` (``"uVel_C"``/``"vVel_C"``/``"wVel"``). Each
    monthly ``.data`` file is read with a **partial** ``np.fromfile`` of the first
    ``n_z*nface*nx*nx`` floats (the top ``n_z`` levels, since ``k`` is outermost), so the
    189 MB/file is never fully loaded. ``iters="all"`` averages every monthly snapshot;
    pass an int/list for a subset, or ``max_iters`` to cap ``"all"`` (useful for a quick
    validation climatology). Land/fill values (``missingValue``, non-finite) are masked
    per cell before averaging. Returns ``(n_z, nface, nx, nx)``.
    """
    if var not in VEL_FLDLIST:
        raise KeyError(f"unknown velocity var {var!r}; known: {sorted(VEL_FLDLIST)}")
    var_dir = Path(monthly_root) / var
    if iters == "all":
        iters = list_available_iterations(monthly_root, var)
    elif isinstance(iters, int):
        iters = [iters]
    if not iters:
        raise FileNotFoundError(f"no iterations for {var!r} under {monthly_root}")
    if max_iters is not None:
        iters = iters[:max_iters]

    n = n_z * nface * nx * nx
    acc = np.zeros((n_z, nface, nx, nx), dtype=np.float64)
    cnt = np.zeros((n_z, nface, nx, nx), dtype=np.float64)
    for it in iters:
        f = var_dir / f"{var}.{it:010d}.data"
        a = np.fromfile(f, dtype=LLC_COMPACT_DTYPE, count=n)
        if a.size != n:
            raise ValueError(f"{f.name}: short read {a.size} < {n}")
        a = a.reshape(n_z, nface, nx, nx).astype(np.float64)
        good = np.isfinite(a) & (a != MITGCM_MISSING)
        acc += np.where(good, a, 0.0)
        cnt += good
    with np.errstate(invalid="ignore"):
        mean = acc / cnt
    mean[cnt == 0] = np.nan  # cells never observed (land)
    return mean


def velocity_aoi_grid(
    monthly_root: str | Path,
    grid_dir: str | Path,
    aoi: AOI,
    *,
    n_z: int = 6,
    iters: int | list[int] | str = "all",
    max_iters: int | None = None,
    to_m_per_day: bool = True,
    nx: int = LLC270_NX,
    nface: int = LLC270_NFACE,
) -> dict:
    """AOI velocity field on the shared 1-deg grid, per level, ready for the transport.

    Reads ``uVel_C``/``vVel_C`` (top ``n_z`` levels, time-mean), masks each level to the
    AOI bbox + ocean (``hFacC>0``) + finite, bin-averages onto the AOI 1-deg grid (same
    edges as the DFe/PIC targets and the iron forcing), and -- with ``to_m_per_day`` --
    converts **m/s -> m/day** to match the transport's day-based ``dt``. Land / no-coverage
    bins are filled with **0** (no flow through land). Returns a dict with ``u``/``v``
    (``[Y, X, n_z]``), ``dz`` (native ``DRF[:n_z]``, m), ``n_z``, and ``units``.
    ``nx``/``nface`` are exposed for testing on a small synthetic grid.

    Land note: v05 stores land velocity as exactly ``0.0`` (not the ``.meta``
    ``missingValue``), so the **``hFacC>0`` ocean mask here** -- not the finite/-999 mask in
    :func:`read_velocity_native_topz` -- is what actually excludes land from each bin.
    """
    xc = np.fromfile(Path(grid_dir) / "XC.data", dtype=LLC_COMPACT_DTYPE).reshape(nface, nx, nx)
    yc = np.fromfile(Path(grid_dir) / "YC.data", dtype=LLC_COMPACT_DTYPE).reshape(nface, nx, nx)
    ocean = read_hfacc_topz(grid_dir, n_z, nx=nx, nface=nface) > 0.0  # (n_z, nface, nx, nx)
    aoi_bbox = aoi_mask_from_xc_yc(xc, yc, aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
    drf = np.fromfile(Path(grid_dir) / "DRF.data", dtype=LLC_COMPACT_DTYPE)[:n_z].astype(float)
    scale = M_PER_S_TO_M_PER_DAY if to_m_per_day else 1.0

    def _grid(var: str) -> np.ndarray:
        native = read_velocity_native_topz(monthly_root, var, n_z=n_z, iters=iters,
                                           max_iters=max_iters, nx=nx, nface=nface)
        levels = []
        for k in range(n_z):
            fld = native[k]
            good = aoi_bbox & ocean[k] & np.isfinite(fld)
            g = bin_to_1deg_grid(xc[good], yc[good], fld[good] * scale,
                                 aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
            levels.append(np.nan_to_num(g, nan=0.0))              # land/no-coverage -> no flow
        return np.stack(levels, axis=-1)                          # [Y, X, n_z]

    # SIGN CONVENTION (do not negate): uVel_C is EASTWARD velocity (UE_VEL_C) and the
    # transport's +u advects toward +lon (east, +X after bin_to_1deg_grid), so u maps to
    # uVel_C directly. Negating it would invert every zonal flow -- e.g. flip the
    # (westward) South Equatorial Current to eastward. Verified: eqpac climatology
    # surface u = -0.149 m/s (westward SEC). Same for v (VN_VEL_C = northward = +y).
    return {
        "u": _grid("uVel_C"), "v": _grid("vVel_C"), "dz": drf, "n_z": n_z,
        "units": "m/day" if to_m_per_day else "m/s",
    }


def depth_mean(field_yxz: np.ndarray) -> np.ndarray:
    """Depth-average a ``[Y, X, Z]`` field to ``[Y, X]`` (the barotropic component)."""
    return np.asarray(field_yxz).mean(axis=-1)


def divfree_barotropic_velocity(u2d, v2d, dx: float, dy: float, dz: float, n_z: int,
                                *, dtype=None, device=None):
    """Build a discretely **divergence-free** transport velocity from a depth-mean
    (barotropic) ``u``/``v`` via :func:`darwindiff.transport.w_from_continuity` (A1).

    Returns ``(u, v, w)`` torch tensors for ``trainer.TransportConfig`` / ``grid_tendency``:
    ``u``/``v`` are the ``[Y, X]`` barotropic fields (applied at every level) and ``w`` is
    the ``[Y, X, Z+1]`` per-interface vertical velocity that makes the 3-D flux div-free.

    **Scope (Phase-1):** this is the *barotropic* (depth-independent ``u``/``v``) div-free
    field -- the same shape the E2 dry-run used. A *baroclinic* (depth-varying) div-free
    ``w`` needs a per-level continuity integration (a generalization of
    ``w_from_continuity``); it is a named follow-up. The full per-level field from
    :func:`velocity_aoi_grid` is available for that when it lands.
    """
    import torch

    from darwindiff.transport import w_from_continuity

    u = torch.as_tensor(np.asarray(u2d), dtype=dtype or torch.float64, device=device)
    v = torch.as_tensor(np.asarray(v2d), dtype=dtype or torch.float64, device=device)
    w = w_from_continuity(u, v, dx, dy, dz, n_z)
    return u, v, w
