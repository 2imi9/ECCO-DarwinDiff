"""Differentiable vertical transport for the Track-2 (UDE) column/field model.

Phase 1 adds what the 0-D box structurally lacks: vertical structure and mixing.
This module provides autograd-clean, mass-conserving vertical operators
(diffusion + upwind advection) and a vectorized BGC tendency, all acting on a
batched field of water columns ``[..., Z, tracer]`` so many grid cells integrate
together (the shape that loads a GPU). Everything plugs into
:mod:`darwindiff.integrators` via a tendency ``f(state) -> dstate``.

Conventions match the box: time in days, ``dt`` in days; the tracer axis is last
(``[DFe, Ps, Pl, POC, PIC]``); the depth axis is second-to-last. Vertical
operators use no-flux top/bottom boundaries, so a closed column conserves the
column-integrated tracer exactly (the invariant the #7 budget check relies on).
"""
from __future__ import annotations

from collections.abc import Callable

import torch

from darwindiff.carroll6 import (
    G0_GRAZE,
    K_FE,
    LIGHT,
    M_LIN,
    M_QUAD,
    P,
    PHI_DUST,
    Q_FE,
    W_SINK,
)

Tendency = Callable[[torch.Tensor], torch.Tensor]


def bgc_tendency_field(
    state: torch.Tensor,
    params: torch.Tensor,
    *,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    scav_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    dust: torch.Tensor | float | None = None,
    light: torch.Tensor | float | None = None,
) -> torch.Tensor:
    """Vectorized Carroll-6 BGC tendency over an arbitrary field of cells.

    Same rate equations as :func:`darwindiff.carroll6.carroll6_ude_tendency`, but
    the tracer axis is the last dim so any leading shape (columns, depth, grid)
    integrates at once. ``params`` may be ``[6]`` (shared) or broadcastable to the
    field. Optional neural closures replace the iron-limitation and calcification
    terms (the UDE hook). ``dust`` (iron-dust source, default ``PHI_DUST``) and
    ``light`` (default ``LIGHT``) may be time-varying scalars/fields for temporal
    forcing (broadcastable to the field).

    **Precondition on a COLUMN/grid state:** atmospheric dust is a *surface* flux, so
    a scalar ``dust`` (applied at every Z layer) over-injects iron ~Z-fold and
    destroys the vertical DFe gradient. For ``[..., Z, tracer]`` states pass a
    surface-only ``dust`` field (``PHI_DUST/dz`` at Z=0, zero below); the scalar
    default is correct only for the 0-D box. (deep review 2026-07-07)
    """
    DFe = state[..., 0]
    Ps = state[..., 1]
    Pl = state[..., 2]
    POC = state[..., 3]
    PIC = state[..., 4]

    alpfe = params[..., P.alpfe]
    scav_rat = params[..., P.scav_rat]
    mu_s = params[..., P.Smallgrow]
    mu_l = params[..., P.Biggrow]
    g_diatom = params[..., P.diatomgraz]
    R_PICPOC = params[..., P.R_PICPOC]
    scav_rat_per_day = scav_rat * 86400.0
    phi_dust = PHI_DUST if dust is None else dust
    lgt = LIGHT if light is None else light

    f_fe = ffe_closure(DFe) if ffe_closure is not None else DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * lgt * Ps
    growth_l = mu_l * f_fe * lgt * Pl
    fe_uptake = Q_FE * (growth_s + growth_l)
    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l
    pic_prod = (
        calcite_closure(state, mort_total)
        if calcite_closure is not None
        else R_PICPOC * mort_total
    )

    scav_sink = (
        scav_closure(DFe, POC)
        if scav_closure is not None
        else scav_rat_per_day * DFe * POC
    )
    dDFe = alpfe * phi_dust - scav_sink - fe_uptake
    dPs = growth_s - mort_s
    dPl = growth_l - mort_l - graze_l
    dPOC = mort_total - W_SINK * POC
    dPIC = pic_prod - W_SINK * PIC
    return torch.stack([dDFe, dPs, dPl, dPOC, dPIC], dim=-1)


def vertical_diffusion(field: torch.Tensor, kz: float, dz: float) -> torch.Tensor:
    """Tendency from vertical diffusion (Fickian mixing) with no-flux boundaries.

    ``field``: ``[..., Z, tracer]``. Interior interface fluxes are
    ``-kz * d(field)/dz``; top and bottom fluxes are zero, so the column-summed
    tracer is conserved by construction.

    **CFL (explicit scheme):** stable only for ``kz*dt/dz**2 < 0.5``; above it the
    rollout **silently NaNs** (there is no guard here -- ``dt`` lives in the
    integrator). Realistic mixed-layer ``kz`` can exceed this at ``dt=0.25 d``. The
    planned fix is semi-implicit backward-Euler (batched Thomas), which removes the
    cap (see the E2-readiness note).
    """
    grad = (field[..., 1:, :] - field[..., :-1, :]) / dz          # [..., Z-1, T]
    flux = -kz * grad                                             # interior interfaces
    zero = torch.zeros_like(field[..., :1, :])
    flux_full = torch.cat([zero, flux, zero], dim=-2)             # [..., Z+1, T]
    return -(flux_full[..., 1:, :] - flux_full[..., :-1, :]) / dz


def vertical_advection(
    field: torch.Tensor, w: float | torch.Tensor, dz: float
) -> torch.Tensor:
    """Tendency from vertical advection (upwind).

    ``w`` is either:
    - a **scalar** constant vertical velocity -> upwind with no-flux top+bottom
      boundaries (the original behaviour; conserves the column total); or
    - a **per-interface tensor** broadcastable to ``[..., Z+1]`` giving the velocity
      at each of the ``Z+1`` interfaces (index 0 = surface ... Z = bottom), positive
      = **downward** (index-increasing). This is the form :func:`w_from_continuity`
      returns to make the 3-D flux discretely divergence-free (``w[...,0]=0`` rigid
      lid; the bottom interface carries the diagnosed outflow).

    Upwind differencing keeps it stable and non-oscillatory.
    """
    if not torch.is_tensor(w) or w.dim() == 0:  # scalar: no-flux both ends
        wf = float(w)
        upwind = field[..., :-1, :] if wf >= 0.0 else field[..., 1:, :]
        flux = wf * upwind
        zero = torch.zeros_like(field[..., :1, :])
        flux_full = torch.cat([zero, flux, zero], dim=-2)
        return -(flux_full[..., 1:, :] - flux_full[..., :-1, :]) / dz

    # per-interface w: ghost-pad the field so the surface/bottom interface upwinds
    # the edge cell; positive w (downward) takes the cell ABOVE each interface.
    cpad = torch.cat([field[..., :1, :], field, field[..., -1:, :]], dim=-2)  # [..., Z+2, T]
    above = cpad[..., :-1, :]                                                 # [..., Z+1, T]
    below = cpad[..., 1:, :]
    w_i = w.unsqueeze(-1)                                                     # [..., Z+1, 1]
    flux = w_i * torch.where(w_i >= 0, above, below)                         # [..., Z+1, T]
    return -(flux[..., 1:, :] - flux[..., :-1, :]) / dz


def w_from_continuity(
    u: torch.Tensor,
    v: torch.Tensor,
    dx: float,
    dy: float,
    dz: float,
    n_z: int,
) -> torch.Tensor:
    """Diagnose per-interface vertical velocity ``w(z)`` from horizontal continuity
    so the combined 3-D flux is **discretely divergence-free** (rigid lid: ``w=0`` at
    the surface). This is the A1 fix: flux-form advection is ``dC/dt = -u.grad(C) -
    C.div(u)``, and a divergent ``(u,v)`` makes the ``C.div(u)`` term manufacture
    spurious per-cell structure a uniform tracer develops ~10x fake range) that the
    closures would absorb as fake biology. Recomputing ``w`` from continuity cancels
    it exactly.

    It is made consistent with :func:`horizontal_advection`'s *own* discretization by
    integrating the operator's horizontal divergence of a uniform field, so a uniform
    tracer under ``(u, v, w)`` has **zero tendency at every cell** (machine precision).
    ``u, v`` are broadcastable to ``[..., Y, X]``; returns ``w`` at the ``Z+1``
    interfaces, shape ``[..., Y, X, Z+1]``, for :func:`vertical_advection`.
    """
    ones = u.new_ones(*u.shape, n_z, 1)                       # [..., Y, X, Z, 1]
    # horizontal tendency of a uniform field == -(horizontal flux divergence)
    hd = horizontal_advection(ones.movedim(-2, 0), u, v, dx, dy).movedim(0, -2)
    hd = hd.squeeze(-1)                                        # [..., Y, X, Z]
    # w[k+1] = w[k] + hd_k*dz, w[0]=0  ->  vertical tendency -(w[k+1]-w[k])/dz = -hd_k
    cumw = dz * torch.cumsum(hd, dim=-1)                       # w at interfaces 1..Z
    return torch.cat([torch.zeros_like(cumw[..., :1]), cumw], dim=-1)  # [..., Y, X, Z+1]


def horizontal_advection(
    field: torch.Tensor,
    u: torch.Tensor,
    v: torch.Tensor,
    dx: float,
    dy: float,
) -> torch.Tensor:
    """Tendency from horizontal advection, flux-form **upwind**, no-flux edges.

    The operator the 0-D box structurally lacks: a prescribed velocity field
    redistributes the spatially-varying tracer fields (``DFe``, ``POC``, the
    calcite ratio) whose local products forced ``scav_rat`` / ``R_PICPOC``
    per-cell in Track 1 -- the mechanism behind the E2 thesis.

    ``field``: ``[..., Y, X, tracer]`` (Y second-, X third-to-last spatial axes,
    tracer last). ``u`` (x-velocity) and ``v`` (y-velocity) are broadcastable to
    the field's non-tracer shape: a per-cell ``[..., Y, X]`` field is unsqueezed to
    a trailing tracer axis automatically, and a bare ``[Y, X]`` broadcasts over a
    batched field. ``dx``, ``dy`` are the grid spacings.

    Reconstruction is **first-order upwind** -- the interface tracer is taken from
    the up-current cell per the sign of the interface velocity, matching
    :func:`vertical_advection`. Upwind is *dissipative* and therefore **stable**
    over decadal rollouts; a naive centered-2nd scheme conserves mass but is
    unconditionally unstable (non-normal exponential growth on divergent velocity
    fields), so it is deliberately not used. Conservation is unchanged: the
    interface flux ``F = v_face * C_up`` is shared between adjacent cells and both
    edges carry zero flux, so the flux-difference tendency telescopes and the
    domain-integrated tracer is conserved to machine precision. A smooth
    higher-order/limited scheme can be layered later if upwind is too diffusive for
    the target front sharpness.

    **Preconditions for a valid E2 result (deep review 2026-07-07 -- see
    docs/research_notes/2026-07-07_deep_review_e2_readiness.md):**
    (1) ``u, v`` (with ``w``) must be **discretely non-divergent**. Flux form is
    ``dC/dt = -u·grad(C) - C·div(u)``; a divergent field makes the ``C·div(u)`` term
    manufacture spurious per-cell structure (a uniform tracer develops ~10x fake
    range) that the closures would absorb as fake biology -- and total conservation
    does **not** reveal it. Recompute ``w(z)`` from continuity before any rollout.
    (2) No-flux edges = a **closed** domain; an open regional (AOI) window needs
    open/outflow BCs or an edge-ring mask, else the walls create a fake boundary
    layer. (3) First-order upwind is heavily diffusive (``K_num ~ 0.5|u|dx``, up to
    ~50x the physical eddy value); quantify/upgrade before trusting an E2 number.
    """
    # give per-cell velocities a trailing tracer axis so they broadcast over
    # tracers (handles [..., Y, X] and a bare [Y, X] against a batched field)
    if u.dim() < field.dim():
        u = u.unsqueeze(-1)
    if v.dim() < field.dim():
        v = v.unsqueeze(-1)

    # --- advection along X (axis=-2): u, upwind ---
    u_face = 0.5 * (u[..., :, :-1, :] + u[..., :, 1:, :])          # interface velocity
    c_up_x = torch.where(u_face >= 0, field[..., :, :-1, :], field[..., :, 1:, :])
    fx = u_face * c_up_x                                           # interior face flux
    zx = torch.zeros_like(field[..., :, :1, :])
    fx_full = torch.cat([zx, fx, zx], dim=-2)                      # [..., Y, X+1, T]
    d_x = -(fx_full[..., :, 1:, :] - fx_full[..., :, :-1, :]) / dx

    # --- advection along Y (axis=-3): v, upwind ---
    v_face = 0.5 * (v[..., :-1, :, :] + v[..., 1:, :, :])          # interface velocity
    c_up_y = torch.where(v_face >= 0, field[..., :-1, :, :], field[..., 1:, :, :])
    fy = v_face * c_up_y
    zy = torch.zeros_like(field[..., :1, :, :])
    fy_full = torch.cat([zy, fy, zy], dim=-3)                      # [..., Y+1, X, T]
    d_y = -(fy_full[..., 1:, :, :] - fy_full[..., :-1, :, :]) / dy

    return d_x + d_y


def column_tendency(
    state: torch.Tensor,
    params: torch.Tensor,
    *,
    kz: float = 0.1,
    dz: float = 25.0,
    w: float | torch.Tensor = 0.0,
    bgc: bool = True,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    scav_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    dust: torch.Tensor | float | None = None,
    light: torch.Tensor | float | None = None,
) -> torch.Tensor:
    """Full column tendency: BGC (per layer) + vertical mixing + vertical advection.

    ``state``: ``[..., Z, tracer]``. Set ``bgc=False`` to test the pure-transport
    conservation invariant. ``dust``/``light`` pass time-varying forcing to the
    BGC (for temporal excitation). Plug into ``integrators.integrate`` via a
    closure over ``params`` and the forcing kwargs.
    """
    d = torch.zeros_like(state)
    if bgc:
        d = d + bgc_tendency_field(
            state, params, ffe_closure=ffe_closure, calcite_closure=calcite_closure,
            scav_closure=scav_closure, dust=dust, light=light,
        )
    d = d + vertical_diffusion(state, kz, dz)
    if torch.is_tensor(w) or w != 0.0:
        d = d + vertical_advection(state, w, dz)
    return d


def grid_tendency(
    state: torch.Tensor,
    params: torch.Tensor,
    *,
    u: torch.Tensor,
    v: torch.Tensor,
    dx: float,
    dy: float,
    kz: float = 0.1,
    dz: float = 25.0,
    w: float | torch.Tensor = 0.0,
    bgc: bool = True,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    scav_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    dust: torch.Tensor | float | None = None,
    light: torch.Tensor | float | None = None,
) -> torch.Tensor:
    """Full 3-D tendency: BGC + vertical mixing/advection + horizontal advection.

    ``state``: ``[..., Y, X, Z, tracer]`` -- horizontal axes (Y, X) then the depth
    axis Z then the tracer axis. This composes :func:`column_tendency` (which
    already applies BGC per cell and the vertical operators on the Z axis, dim -2)
    with :func:`horizontal_advection` on the (Y, X) axes -- reached by moving Z out
    to the front so the operator sees its expected ``[..., Y, X, tracer]`` layout,
    then moving the result back. ``u``, ``v`` are horizontal velocities
    broadcastable to ``[..., Y, X]``. This is the tendency the E2 spatial rollout
    integrates via ``integrators.integrate``.

    Conservation: with ``bgc=False`` every operator is flux-form with no-flux edges,
    so the domain-integrated tracer is conserved; ``bgc=True`` adds the (intended)
    reactive sources/sinks.

    **NOT yet E2-ready** (deep review 2026-07-07): ``w`` defaults to 0 so horizontal
    ``div(u)`` is uncompensated (see :func:`horizontal_advection` precondition (1));
    a per-layer ``w(z)`` from continuity is required. See
    ``docs/research_notes/2026-07-07_deep_review_e2_readiness.md`` for the ordered
    A1-A6 fixes that must land before a held-out-R^2 number is trustworthy.
    """
    d = column_tendency(
        state, params, kz=kz, dz=dz, w=w, bgc=bgc,
        ffe_closure=ffe_closure, calcite_closure=calcite_closure,
        scav_closure=scav_closure, dust=dust, light=light,
    )
    # horizontal advection acts on (Y, X); move the depth axis (-2) to the front so
    # horizontal_advection sees [Z, ..., Y, X, tracer], then move the result back.
    state_h = state.movedim(-2, 0)
    d_h = horizontal_advection(state_h, u, v, dx, dy).movedim(0, -2)
    return d + d_h
