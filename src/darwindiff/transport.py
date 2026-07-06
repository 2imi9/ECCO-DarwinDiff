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
) -> torch.Tensor:
    """Vectorized Carroll-6 BGC tendency over an arbitrary field of cells.

    Same rate equations as :func:`darwindiff.carroll6.carroll6_ude_tendency`, but
    the tracer axis is the last dim so any leading shape (columns, depth, grid)
    integrates at once. ``params`` may be ``[6]`` (shared) or broadcastable to the
    field. Optional neural closures replace the iron-limitation and calcification
    terms (the UDE hook).
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

    f_fe = ffe_closure(DFe) if ffe_closure is not None else DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * LIGHT * Ps
    growth_l = mu_l * f_fe * LIGHT * Pl
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

    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
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
) -> torch.Tensor:
    """Full column tendency: BGC (per layer) + vertical mixing + vertical advection.

    ``state``: ``[..., Z, tracer]``. Set ``bgc=False`` to test the pure-transport
    conservation invariant. Plug into ``integrators.integrate`` via a closure over
    ``params`` and the forcing kwargs.
    """
    d = torch.zeros_like(state)
    if bgc:
        d = d + bgc_tendency_field(
            state, params, ffe_closure=ffe_closure, calcite_closure=calcite_closure
        )
    d = d + vertical_diffusion(state, kz, dz)
    if w != 0.0:
        d = d + vertical_advection(state, w, dz)
    return d
