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

    dDFe = alpfe * phi_dust - scav_rat_per_day * DFe * POC - fe_uptake
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
    """
    grad = (field[..., 1:, :] - field[..., :-1, :]) / dz          # [..., Z-1, T]
    flux = -kz * grad                                             # interior interfaces
    zero = torch.zeros_like(field[..., :1, :])
    flux_full = torch.cat([zero, flux, zero], dim=-2)             # [..., Z+1, T]
    return -(flux_full[..., 1:, :] - flux_full[..., :-1, :]) / dz


def vertical_advection(field: torch.Tensor, w: float, dz: float) -> torch.Tensor:
    """Tendency from constant vertical advection (upwind) with no-flux boundaries.

    ``w`` is a signed vertical velocity (same length unit as ``dz``, per day).
    Upwind differencing keeps it stable and non-oscillatory; no-flux top/bottom
    boundaries conserve the column total.
    """
    upwind = field[..., :-1, :] if w >= 0.0 else field[..., 1:, :]  # interior interfaces
    flux = w * upwind
    zero = torch.zeros_like(field[..., :1, :])
    flux_full = torch.cat([zero, flux, zero], dim=-2)
    return -(flux_full[..., 1:, :] - flux_full[..., :-1, :]) / dz


def horizontal_advection(
    field: torch.Tensor,
    u: torch.Tensor,
    v: torch.Tensor,
    dx: float,
    dy: float,
) -> torch.Tensor:
    """Tendency from horizontal advection, flux-form centered-2nd, no-flux edges.

    This is the operator the 0-D box structurally lacks: it lets a prescribed
    velocity field redistribute the spatially-varying tracer fields (``DFe``,
    ``POC``, the calcite ratio) whose local products forced ``scav_rat`` /
    ``R_PICPOC`` per-cell in Track 1 — i.e. it is the mechanism behind the E2
    thesis (does transport homogenise the per-cell parameters?).

    ``field``: ``[..., Y, X, tracer]`` (Y second-, X third-to-last spatial axes,
    tracer last). ``u`` (x-velocity) and ``v`` (y-velocity) are per-cell fields
    broadcastable to ``[..., Y, X]`` (same for every tracer) or to the full
    ``field`` shape. ``dx``, ``dy`` are the grid spacings.

    Conservation: the interface flux ``F = v_face * C_face`` is shared between
    adjacent cells and both domain edges carry zero flux, so the flux-difference
    tendency telescopes and the domain-integrated tracer is conserved to machine
    precision — exactly like :func:`vertical_diffusion`/:func:`vertical_advection`.
    Centered-2nd (not upwind) keeps the operator smooth for autograd; a smooth
    tanh-blended limiter is a follow-up only if false extrema appear.
    """
    # add a trailing tracer axis to the velocities if they are given per-cell
    if u.dim() == field.dim() - 1:
        u = u.unsqueeze(-1)
    if v.dim() == field.dim() - 1:
        v = v.unsqueeze(-1)

    # --- advection along X (axis=-2): u ---
    u_face = 0.5 * (u[..., :, :-1, :] + u[..., :, 1:, :])          # [..., Y, X-1, T]
    c_face = 0.5 * (field[..., :, :-1, :] + field[..., :, 1:, :])
    fx = u_face * c_face                                           # interior face flux
    zx = torch.zeros_like(field[..., :, :1, :])
    fx_full = torch.cat([zx, fx, zx], dim=-2)                      # [..., Y, X+1, T]
    d_x = -(fx_full[..., :, 1:, :] - fx_full[..., :, :-1, :]) / dx

    # --- advection along Y (axis=-3): v ---
    v_face = 0.5 * (v[..., :-1, :, :] + v[..., 1:, :, :])          # [..., Y-1, X, T]
    c_face_y = 0.5 * (field[..., :-1, :, :] + field[..., 1:, :, :])
    fy = v_face * c_face_y
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
    w: float = 0.0,
    bgc: bool = True,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
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
            dust=dust, light=light,
        )
    d = d + vertical_diffusion(state, kz, dz)
    if w != 0.0:
        d = d + vertical_advection(state, w, dz)
    return d
