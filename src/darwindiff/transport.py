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
    co2_flux: torch.Tensor | float | None = None,
) -> torch.Tensor:
    """Vectorized Carroll-6 BGC tendency over an arbitrary field of cells.

    Same rate equations as :func:`darwindiff.carroll6.carroll6_ude_tendency`, but
    the tracer axis is the last dim so any leading shape (columns, depth, grid)
    integrates at once. ``params`` may be ``[6]`` (shared) or broadcastable to the
    field. The state may be **5-tracer** ``[DFe, Ps, Pl, POC, PIC]`` or **7-tracer**
    ``[..., DIC, ALK]``; with 7 tracers the single ``pic_prod`` feeds
    ``dPIC(+1)/dDIC(-1)/dALK(-2)`` so the calcite closure's carbon effect is captured
    and carbon conserves through calcification (deep review A3). Optional neural
    closures replace the iron-limitation and calcification terms (the UDE hook). ``dust`` (iron-dust source, default ``PHI_DUST``) and
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
    base = [dDFe, dPs, dPl, dPOC, dPIC]

    if state.shape[-1] >= 7:  # 7-tracer [..., DIC, ALK]: A3 calcite/organic stoichiometry
        # The SAME pic_prod drains 1 DIC + 2 ALK per mole CaCO3, and organic C
        # fixation (growth) drains DIC -- so the calcite closure's carbon/alkalinity
        # effect is captured (not silently dropped) and total carbon is conserved
        # through calcification. POC/PIC export (W_SINK) + optional air-sea `co2_flux`
        # (mmol C/m^3/d, positive = DIC loss) are the only carbon exits.
        cf = 0.0 if co2_flux is None else co2_flux
        dDIC = -(growth_s + growth_l) - pic_prod - cf
        dALK = -2.0 * pic_prod
        return torch.stack(base + [dDIC, dALK], dim=-1)
    return torch.stack(base, dim=-1)


def surface_dust_field(
    n_z: int,
    dust: float | None = None,
    *,
    dtype: torch.dtype | None = None,
    device: torch.device | None = None,
) -> torch.Tensor:
    """Per-layer iron-dust source concentrated at the SURFACE layer of a column (A4).

    Atmospheric dust is a *surface* flux, so applying a scalar rate at every layer
    (the default in :func:`bgc_tendency_field`) over-injects iron ~Z-fold and destroys
    the vertical DFe gradient that ``scav_rat`` identifiability depends on. This places
    the 0-D volumetric rate ``dust`` (default ``PHI_DUST``) at ``Z=0`` and zero below,
    so a column's top layer behaves like the 0-D box and the column-integrated input
    (``= dust*dz``) is independent of the number of layers. Returns shape ``[n_z]``,
    to pass through the ``dust=`` kwarg of :func:`bgc_tendency_field` / grid path.
    """
    d = torch.zeros(n_z, dtype=dtype, device=device)
    d[0] = float(PHI_DUST) if dust is None else float(dust)
    return d


def carbon_total(state: torch.Tensor) -> torch.Tensor:
    """Total carbon per cell = the carbon-bearing tracers summed:
    ``Ps + Pl + POC + PIC`` (+ ``DIC`` for a 7-tracer state). Iron (``DFe``) and
    alkalinity (``ALK``) are excluded. Sum this over space for the open-system carbon
    budget: ``d(Total C) = inputs - outputs`` -- with A3's stoichiometry the only
    carbon exits are particulate export (``W_SINK*(POC+PIC)``) and the optional
    air-sea flux, so total carbon conserves through calcification (deep review A5).
    """
    c = state[..., 1] + state[..., 2] + state[..., 3] + state[..., 4]  # Ps+Pl+POC+PIC
    if state.shape[-1] >= 7:
        c = c + state[..., 5]  # + DIC
    return c


def interior_mask(
    ny: int, nx: int, ring: int = 1, *, device: torch.device | None = None
) -> torch.Tensor:
    """Boolean ``[ny, nx]`` mask that is ``False`` on the outer ``ring`` cells and
    ``True`` in the interior.

    The no-flux zero-pad in :func:`horizontal_advection` / the vertical operators is a
    **closed-domain** boundary: it reflects tracer at the edges, creating a fake
    accumulation/depletion boundary layer (verified: uniform outflow gives edge
    tendencies ``[-1, 0, ..., 0, +1]``). The E2 gate fits closures on an **open**
    regional (AOI) window where tracer physically crosses the edges, so the loss must
    **exclude** that boundary ring (deep review A6). Apply this mask to the E2
    residual (an open-BC operator with prescribed-halo inflow is a later upgrade, once
    the AOI-boundary field is staged). ``ring`` cells are dropped on each side.
    """
    m = torch.zeros(ny, nx, dtype=torch.bool, device=device)
    m[ring : ny - ring, ring : nx - ring] = True
    return m


def vertical_cfl_number(kz: float, dz: float, dt: float) -> float:
    """Explicit vertical-diffusion CFL number ``kz*dt/dz**2``. Stable for ``< 0.5``."""
    return kz * dt / (dz * dz)


def assert_vertical_cfl(kz: float, dz: float, dt: float, *, limit: float = 0.5) -> None:
    """Raise if the explicit vertical-diffusion CFL number reaches ``limit`` (0.5).

    The explicit :func:`vertical_diffusion` rollout **silently NaNs** above the limit
    (deep review 2026-07-07: confirmed NaN at ``kz*dt/dz**2 = 1.25``); this makes the
    failure loud instead. For realistic mixed-layer ``kz`` at ``dt=0.25 d`` the limit
    is exceeded -- use the unconditionally-stable :func:`vertical_diffusion_implicit`
    (via :func:`imex_rollout`) rather than shrinking ``dt``.
    """
    cfl = vertical_cfl_number(kz, dz, dt)
    if cfl >= limit:
        raise ValueError(
            f"explicit vertical diffusion is unstable: kz*dt/dz^2 = {cfl:.3g} >= {limit} "
            f"(kz={kz}, dz={dz}, dt={dt}); it will silently NaN. Use "
            f"vertical_diffusion_implicit / imex_rollout (backward-Euler, no CFL limit) "
            f"or reduce dt below {limit * dz * dz / kz:.4g} d."
        )


def vertical_diffusion(
    field: torch.Tensor, kz: float, dz: float, dt: float | None = None
) -> torch.Tensor:
    """Tendency from vertical diffusion (Fickian mixing) with no-flux boundaries.

    ``field``: ``[..., Z, tracer]``. Interior interface fluxes are
    ``-kz * d(field)/dz``; top and bottom fluxes are zero, so the column-summed
    tracer is conserved by construction.

    **CFL (explicit scheme):** stable only for ``kz*dt/dz**2 < 0.5``; above it the
    rollout **silently NaNs**. Pass ``dt`` here to turn that silent failure into a
    loud :func:`assert_vertical_cfl` error. Realistic mixed-layer ``kz`` exceeds the
    cap at ``dt=0.25 d`` -- for E2 rollouts use the unconditionally-stable
    :func:`vertical_diffusion_implicit` (backward-Euler Thomas) via
    :func:`imex_rollout`, which removes the cap entirely.
    """
    if dt is not None:
        assert_vertical_cfl(kz, dz, dt)
    grad = (field[..., 1:, :] - field[..., :-1, :]) / dz          # [..., Z-1, T]
    flux = -kz * grad                                             # interior interfaces
    zero = torch.zeros_like(field[..., :1, :])
    flux_full = torch.cat([zero, flux, zero], dim=-2)             # [..., Z+1, T]
    return -(flux_full[..., 1:, :] - flux_full[..., :-1, :]) / dz


def thomas_solve(
    a: torch.Tensor, b: torch.Tensor, c: torch.Tensor, d: torch.Tensor
) -> torch.Tensor:
    """Batched, autograd-clean tridiagonal solve along the Z axis (``dim=-2``).

    Solves ``a[i]*x[i-1] + b[i]*x[i] + c[i]*x[i+1] = d[i]`` for ``x`` over the depth
    axis of a ``[..., Z, tracer]`` field. ``a`` (sub-diagonal, ``a[0]`` unused), ``b``
    (diagonal), ``c`` (super-diagonal, ``c[-1]`` unused) are 1-D ``[Z]`` coefficient
    vectors (broadcast over every batch/tracer axis); ``d`` is the ``[..., Z, tracer]``
    right-hand side. The Thomas algorithm (forward elimination + back substitution) is
    O(Z) and sequential in Z, implemented with a Python loop over the (small) depth
    axis so gradients flow cleanly (no in-place writes to grad tensors). For a
    diagonally-dominant system (``|b| > |a|+|c|``, true for backward-Euler diffusion)
    it is numerically stable without pivoting.
    """
    n = d.shape[-2]
    if n == 1:
        return d / b[0]
    cp = [c[0] / b[0]]                    # c'[0]
    dp = [d[..., 0, :] / b[0]]            # d'[0], shape [..., tracer]
    for i in range(1, n):
        m = b[i] - a[i] * cp[i - 1]
        cp.append(c[i] / m)
        dp.append((d[..., i, :] - a[i] * dp[i - 1]) / m)
    x = [None] * n
    x[n - 1] = dp[n - 1]
    for i in range(n - 2, -1, -1):
        x[i] = dp[i] - cp[i] * x[i + 1]
    return torch.stack(x, dim=-2)


def vertical_diffusion_implicit(
    state: torch.Tensor, kz: float, dz: float, dt: float
) -> torch.Tensor:
    """One **unconditionally-stable** backward-Euler vertical-diffusion sub-step.

    Solves ``(I - dt*L) x^{n+1} = x^n`` where ``L`` is the *same* no-flux Laplacian
    operator :func:`vertical_diffusion` applies explicitly, via :func:`thomas_solve`.
    Returns ``x^{n+1}`` for ``state = x^n`` (shape ``[..., Z, tracer]``). Unlike the
    explicit scheme this has **no CFL limit** (stable for any ``kz*dt/dz**2``), curing
    the silent-NaN failure at realistic mixed-layer ``kz`` -- the deep-review /
    E2-readiness fix. **Mass-conserving:** ``L`` is column-conservative (each matrix
    column of ``I - dt*L`` sums to 1), so the column-integrated tracer is preserved to
    machine precision, exactly like the explicit operator.

    Row structure (``r = kz*dt/dz**2``, no-flux top/bottom):
    interior ``(-r, 1+2r, -r)``; top/bottom rows ``(1+r, -r)`` / ``(-r, 1+r)``.
    """
    n = state.shape[-2]
    if n == 1:  # single layer: no vertical coupling -> identity
        return state
    r = kz * dt / (dz * dz)
    kw = {"dtype": state.dtype, "device": state.device}
    a = torch.full((n,), -r, **kw)
    b = torch.full((n,), 1.0 + 2.0 * r, **kw)
    c = torch.full((n,), -r, **kw)
    a[0] = 0.0                # unused (no cell above the surface)
    c[n - 1] = 0.0            # unused (no cell below the bottom)
    b[0] = 1.0 + r           # no-flux top: only one neighbour
    b[n - 1] = 1.0 + r       # no-flux bottom: only one neighbour
    return thomas_solve(a, b, c, state)


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

    Reconstruction is **centered-2nd** (``C_face = (C_i + C_{i+1})/2``): 2nd-order
    accurate and, crucially, **non-diffusive** -- it adds no uncontrolled numerical
    diffusion (unlike first-order upwind, whose ``K_num ~ 0.5|u|dx`` is 3-50x the
    physical eddy value at target dt/dx and would bias the E2 gate). It is smooth for
    autograd (no sign branch), so gradients flow to ``u, v`` too. Conservation is by
    construction: ``F = u_face*C_face`` is shared between adjacent cells and both
    edges carry zero flux, so the flux-difference tendency telescopes.

    **Centered advection MUST be paired with** :func:`horizontal_diffusion` -- it is
    dispersively unstable alone. Stability is provided by (a) A1's divergence-free
    ``w`` (which removed the dominant blow-up source) plus (b) an explicit Laplacian
    diffusion ``kh`` (grid-Peclet ``|u|dx/kh`` kept O(1), i.e. ``kh >~ 0.5|u|dx``).
    Because that diffusion is now **explicit and tunable**, the total diffusion is
    controllable and diagnosable -- enabling the E2 ``K_num`` ablation the deep review
    requires (show R^2 does not track ``kh``).

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

    # --- advection along X (axis=-2): u, centered-2nd ---
    u_face = 0.5 * (u[..., :, :-1, :] + u[..., :, 1:, :])          # interface velocity
    c_face_x = 0.5 * (field[..., :, :-1, :] + field[..., :, 1:, :])  # centered interface tracer
    fx = u_face * c_face_x                                         # interior face flux
    zx = torch.zeros_like(field[..., :, :1, :])
    fx_full = torch.cat([zx, fx, zx], dim=-2)                      # [..., Y, X+1, T]
    d_x = -(fx_full[..., :, 1:, :] - fx_full[..., :, :-1, :]) / dx

    # --- advection along Y (axis=-3): v, centered-2nd ---
    v_face = 0.5 * (v[..., :-1, :, :] + v[..., 1:, :, :])          # interface velocity
    c_face_y = 0.5 * (field[..., :-1, :, :] + field[..., 1:, :, :])  # centered interface tracer
    fy = v_face * c_face_y
    zy = torch.zeros_like(field[..., :1, :, :])
    fy_full = torch.cat([zy, fy, zy], dim=-3)                      # [..., Y+1, X, T]
    d_y = -(fy_full[..., 1:, :, :] - fy_full[..., :-1, :, :]) / dy

    return d_x + d_y


def horizontal_diffusion(
    field: torch.Tensor, kh: float, dx: float, dy: float
) -> torch.Tensor:
    """Explicit flux-form Laplacian horizontal diffusion (no-flux edges) on the
    (Y, X) axes -- the physical + stabilizing companion to centered
    :func:`horizontal_advection`.

    ``kh`` is the horizontal eddy diffusivity: set it to the physical value
    (~1e2-1e3 m^2/s in real units) *and* large enough that centered advection is
    stable (grid-Peclet ``|u|dx/kh`` of O(1), i.e. ``kh >~ 0.5|u|dx``). Conservative
    by construction (shared interface flux ``-kh*grad`` + zero-flux edges).
    Explicit-CFL: stable for ``kh*dt*(1/dx^2 + 1/dy^2) < 0.5`` (semi-implicit is a
    later upgrade if that bites). ``field``: ``[..., Y, X, tracer]``.
    """
    if kh == 0.0:
        return torch.zeros_like(field)
    # X-diffusion (axis=-2)
    gx = (field[..., :, 1:, :] - field[..., :, :-1, :]) / dx      # interior interface gradient
    fx = -kh * gx
    zx = torch.zeros_like(field[..., :, :1, :])
    fx_full = torch.cat([zx, fx, zx], dim=-2)
    d_x = -(fx_full[..., :, 1:, :] - fx_full[..., :, :-1, :]) / dx
    # Y-diffusion (axis=-3)
    gy = (field[..., 1:, :, :] - field[..., :-1, :, :]) / dy
    fy = -kh * gy
    zy = torch.zeros_like(field[..., :1, :, :])
    fy_full = torch.cat([zy, fy, zy], dim=-3)
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
    include_vdiff: bool = True,
    dt: float | None = None,
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

    Set ``include_vdiff=False`` to **exclude** the explicit vertical-diffusion term
    from the tendency -- the mode :func:`imex_rollout` uses so vertical diffusion can
    instead be applied implicitly (backward-Euler, no CFL limit) as a separate
    operator-split sub-step. With ``include_vdiff=True`` (default) vertical diffusion
    is explicit and subject to ``kz*dt/dz**2 < 0.5``; pass the integrator's ``dt`` here
    to **guard** it -- :func:`assert_vertical_cfl` then raises loudly instead of the
    rollout silently NaN-ing above the limit (deep review 2026-07-08).
    """
    d = torch.zeros_like(state)
    if bgc:
        d = d + bgc_tendency_field(
            state, params, ffe_closure=ffe_closure, calcite_closure=calcite_closure,
            scav_closure=scav_closure, dust=dust, light=light,
        )
    if include_vdiff:
        d = d + vertical_diffusion(state, kz, dz, dt=dt)
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
    kh: float = 0.0,
    bgc: bool = True,
    include_vdiff: bool = True,
    dt: float | None = None,
    ffe_closure: Callable[[torch.Tensor], torch.Tensor] | None = None,
    calcite_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    scav_closure: Callable[[torch.Tensor, torch.Tensor], torch.Tensor] | None = None,
    dust: torch.Tensor | float | None = None,
    light: torch.Tensor | float | None = None,
) -> torch.Tensor:
    """Full 3-D tendency: BGC + vertical mixing/advection + horizontal advection+diffusion.

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
        state, params, kz=kz, dz=dz, w=w, bgc=bgc, include_vdiff=include_vdiff, dt=dt,
        ffe_closure=ffe_closure, calcite_closure=calcite_closure,
        scav_closure=scav_closure, dust=dust, light=light,
    )
    # horizontal advection + diffusion act on (Y, X); move the depth axis (-2) to the
    # front so they see [Z, ..., Y, X, tracer], then move the result back. Centered
    # advection is paired with the explicit kh diffusion for stability (see A2).
    state_h = state.movedim(-2, 0)
    d_h = horizontal_advection(state_h, u, v, dx, dy)
    if kh != 0.0:
        d_h = d_h + horizontal_diffusion(state_h, kh, dx, dy)
    return d + d_h.movedim(0, -2)


def _rk4_explicit(f, x: torch.Tensor, t: float, dt: float) -> torch.Tensor:
    """Local classical RK4 step (forcing at stage times ``t, t+dt/2, t+dt/2, t+dt``)."""
    k1 = f(t, x)
    k2 = f(t + 0.5 * dt, x + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, x + 0.5 * dt * k2)
    k4 = f(t + dt, x + dt * k3)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


def _euler_explicit(f, x: torch.Tensor, t: float, dt: float) -> torch.Tensor:
    """Local forward-Euler step."""
    return x + dt * f(t, x)


# Local explicit steppers (kept self-contained rather than importing integrators.py,
# whose stepper signatures are mid-refactor in a concurrent branch -- see the shared-
# checkout note). Semantics match integrators.rk4_step/euler_step.
_EXPLICIT_STEP = {"rk4": _rk4_explicit, "euler": _euler_explicit}


def _to_time_aware(f):
    """Accept a legacy autonomous ``f(x)`` and wrap it as ``f(t, x)`` (else use as-is)."""
    import inspect

    try:
        n = len([
            p for p in inspect.signature(f).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD) and p.default is p.empty
        ])
    except (TypeError, ValueError):
        n = 2
    return (lambda t, x: f(x)) if n <= 1 else f


def imex_rollout(
    tendency: Callable,
    state: torch.Tensor,
    dt: float,
    n_steps: int,
    *,
    kz: float,
    dz: float,
    method: str = "rk4",
    t0: float = 0.0,
    checkpoint_segment: int | None = None,
    snapshot_indices: list[int] | None = None,
) -> torch.Tensor:
    """IMEX rollout: **explicit** RK4/Euler on ``tendency`` + **implicit** vertical
    diffusion each step (first-order Lie/Godunov operator splitting).

    ``tendency(t, x) -> dx`` must be the EXPLICIT part **without** the vertical-diffusion
    term. This rollout adds the implicit vertical-diffusion sub-step itself, so if the
    ``tendency`` ALSO contains vertical diffusion it is **double-counted** (silently wrong
    at small ``kz*dt/dz**2``, and NaN above the explicit CFL limit). ``column_tendency`` /
    ``grid_tendency`` default ``include_vdiff=True``, so you MUST pass ``include_vdiff=False``::

        # WRONG -- double-counts vertical diffusion:
        tend = lambda t, x: grid_tendency(x, params, u=u, v=v, dx=dx, dy=dy, kz=kz, dz=dz)
        # RIGHT -- vertical diffusion handled implicitly by imex_rollout:
        tend = lambda t, x: grid_tendency(x, params, u=u, v=v, dx=dx, dy=dy, kz=kz, dz=dz,
                                          include_vdiff=False)
        out = imex_rollout(tend, state, dt, n_steps, kz=kz, dz=dz)

    Each step advances the explicit operators (BGC, advection, horizontal mixing) with the
    chosen explicit ``method`` and then applies one unconditionally-stable backward-Euler
    vertical-diffusion sub-step (:func:`vertical_diffusion_implicit`) -- so the whole
    rollout has **no vertical-CFL limit** and does not silently NaN at realistic
    mixed-layer ``kz`` (the E2-readiness fix). Splitting is first-order in ``dt``; each
    sub-step keeps its own order.

    ``state``: ``[..., Z, tracer]`` (depth axis -2). Supports gradient
    ``checkpoint_segment`` (bound backward memory for windowed BPTT; the implicit solve
    is deterministic so recompute is bit-identical) and ``snapshot_indices`` (1-indexed,
    stack snapshots; honored without checkpointing). Returns the final state, or the
    stacked snapshots if ``snapshot_indices`` is given.
    """
    if method not in _EXPLICIT_STEP:
        raise ValueError(f"unknown method {method!r}; expected one of {sorted(_EXPLICIT_STEP)}")
    estep = _EXPLICIT_STEP[method]
    f = _to_time_aware(tendency)

    def advance(x: torch.Tensor, t: float) -> torch.Tensor:
        x = estep(f, x, t, dt)                          # explicit: BGC + advection + horiz
        return vertical_diffusion_implicit(x, kz, dz, dt)  # implicit: vertical diffusion

    if snapshot_indices is not None:
        wanted = set(snapshot_indices)
        snaps: list[torch.Tensor] = []
        x, t = state, t0
        for s in range(1, n_steps + 1):
            x = advance(x, t)
            t += dt
            if s in wanted:
                snaps.append(x)
        return torch.stack(snaps)

    if checkpoint_segment and checkpoint_segment > 0:
        from torch.utils.checkpoint import checkpoint

        x, i, t = state, 0, t0
        while i < n_steps:
            k = min(checkpoint_segment, n_steps - i)
            t_seg = t

            def seg(x_in: torch.Tensor, _k: int = k, _t: float = t_seg) -> torch.Tensor:
                tt = _t
                for _ in range(_k):
                    x_in = advance(x_in, tt)
                    tt += dt
                return x_in

            x = checkpoint(seg, x, use_reentrant=False)
            i += k
            t += k * dt
        return x

    x, t = state, t0
    for _ in range(n_steps):
        x = advance(x, t)
        t += dt
    return x
