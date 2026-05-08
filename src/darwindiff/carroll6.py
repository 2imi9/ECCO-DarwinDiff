"""Carroll-2020 6-parameter box model: 0-D Fe-phyto-POC-PIC reaction network.

Surface mixed-layer scalar BGC with five prognostic tracers and external dust + light
forcing. Exposes the exact six parameters Carroll et al. 2020 (JAMES) tuned via Green's
functions for ECCO-Darwin (Darwin 1 source build at MITgcm-contrib/ecco_darwin/v04/
llc270_JAMES_paper):

    1. alpfe       — iron dust solubility (–)
    2. scav_rat    — iron scavenging rate (s⁻¹)
    3. Smallgrow   — small phytoplankton growth rate (d⁻¹)
    4. Biggrow     — large phytoplankton growth rate (d⁻¹)
    5. diatomgraz  — diatom palatability (–)
    6. R_PICPOC    — PIC/POC ratio (–)

Equations:
    dDFe/dt   = alpfe*Φ_dust - scav_rat*DFe*POC - Q_Fe*(μ_s P_s + μ_l P_l)*f_Fe(DFe)
    dPs/dt    = μ_s f_Fe Ps - m_lin Ps - m_quad Ps²
    dPl/dt    = μ_l f_Fe Pl - m_lin Pl - m_quad Pl² - g_diatom G0 Pl
    dPOC/dt   = M_tot - w_sink POC
    dPIC/dt   = R_PICPOC M_tot - w_sink PIC

with f_Fe(DFe) = DFe / (DFe + K_Fe) and M_tot the sum of all phyto loss fluxes.

Background defaults (M_LIN, M_QUAD, G0_GRAZE, W_SINK, K_FE, PHI_DUST, Q_FE, LIGHT) are
fixed at literature-plausible values and not learned — they correspond to the ~94% of
Darwin parameters Carroll left at expert defaults.

Used by notebooks 05 and 06; kept here so both can import from a single source instead
of duplicating the box model. Darwin 3 namelist mapping for these names is documented in
the project memory at reference_darwin3.md and is the first sub-step of notebook 06+.
"""

from __future__ import annotations

import torch

# Background (non-learned) parameters — the ~94% of Darwin knobs Carroll left at defaults.
M_LIN: float = 0.05         # 1/d, linear phyto mortality
M_QUAD: float = 0.50        # 1/d / (mmol C/m^3), quadratic phyto mortality
G0_GRAZE: float = 0.30      # 1/d, baseline grazing rate (multiplied by diatomgraz)
W_SINK: float = 0.10        # 1/d, particulate sinking rate
K_FE: float = 5.0e-5        # mmol Fe/m^3, iron half-saturation for phyto growth
PHI_DUST: float = 5.0e-5    # mmol Fe/m^3/d, dissolved-iron source from dust
Q_FE: float = 1.0e-5        # mol Fe / mol C, phyto Fe quota
LIGHT: float = 1.0          # surface light, dimensionless


# Carroll 2020 published optimum (JAMES paper Table 1). Values verified directly against
# the v04/llc270_JAMES_paper source build; see docs/ecco_darwin_parameter_inventory.md.
CARROLL_VALUES: torch.Tensor = torch.tensor([
    0.92831,                     # alpfe
    10.41124 * 0.005 / 86400.0,  # scav_rat (per second) = 6.026e-7
    0.66098,                     # Smallgrow (per day)
    0.43148,                     # Biggrow (per day)
    0.83003,                     # diatomgraz
    0.04245,                     # R_PICPOC
])

PARAM_NAMES: list[str] = [
    "alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC",
]

PARAM_BOUNDS: torch.Tensor = torch.tensor([
    [0.05, 1.0],     # alpfe
    [3e-8, 3e-6],    # scav_rat (per second), 100x window around Carroll's 6e-7
    [0.10, 2.0],     # Smallgrow (1/d)
    [0.10, 2.0],     # Biggrow (1/d)
    [0.05, 1.0],     # diatomgraz
    [0.005, 0.20],   # R_PICPOC
])


def carroll6_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
) -> torch.Tensor:
    """One forward-Euler step of the 5-tracer Carroll-6 box model.

    Args:
        state: shape [5], [DFe, Ps, Pl, POC, PIC] in mmol/m^3 (Fe in mmol Fe/m^3).
        params: shape [6], [alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC].
            scav_rat is per-second following the Carroll source convention; converted
            to per-day at the use site.
        dt: time step in days.

    Returns:
        next state, shape [5].
    """
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    alpfe, scav_rat, mu_s, mu_l, g_diatom, R_PICPOC = (
        params[0], params[1], params[2], params[3], params[4], params[5]
    )
    scav_rat_per_day = scav_rat * 86400.0

    f_fe = DFe / (DFe + K_FE)
    growth_s = mu_s * f_fe * LIGHT * Ps
    growth_l = mu_l * f_fe * LIGHT * Pl
    fe_uptake = Q_FE * (growth_s + growth_l)
    mort_s = M_LIN * Ps + M_QUAD * Ps * Ps
    mort_l = M_LIN * Pl + M_QUAD * Pl * Pl
    graze_l = g_diatom * G0_GRAZE * Pl
    mort_total = mort_s + mort_l + graze_l

    dDFe = alpfe * PHI_DUST - scav_rat_per_day * DFe * POC - fe_uptake
    dPs = growth_s - mort_s
    dPl = growth_l - mort_l - graze_l
    dPOC = mort_total - W_SINK * POC
    dPIC = R_PICPOC * mort_total - W_SINK * PIC

    return torch.stack([
        DFe + dt * dDFe,
        Ps + dt * dPs,
        Pl + dt * dPl,
        POC + dt * dPOC,
        PIC + dt * dPIC,
    ])


def carroll6_integrate(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int] | None = None,
) -> torch.Tensor:
    """Forward-Euler integration with autograd through every step.

    Args:
        state0: initial state, shape [5].
        params: Carroll-6 parameters, shape [6].
        dt: time step in days.
        n_steps: number of forward-Euler steps.
        snapshot_indices: 1-indexed steps at which to save state. If None, returns
            only the final state. If provided, returns shape [len(snapshot_indices), 5].

    Returns:
        Final state shape [5] when snapshot_indices is None, else stacked snapshots.
    """
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = carroll6_step(state, params, dt)
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = carroll6_step(state, params, dt)
        if step in snapshot_set:
            snaps.append(state)
    return torch.stack(snaps)


def bounded_params(
    theta: torch.Tensor,
    bounds: torch.Tensor,
    param_axis: int = 0,
) -> torch.Tensor:
    """Map unconstrained theta to physical Carroll-6 ranges via sigmoid.

    The parameter axis of ``theta`` (the dim with size ``n_params`` matching
    ``bounds.shape[0]``) is identified by ``param_axis``. The default is the
    leading dim, which matches the notebook 05 / 07 usage. For trailing-axis
    conventions (notebook 06 style batched MLP output, or batched CNN output),
    pass ``param_axis`` explicitly.

    Examples:
        - ``theta`` shape ``[6]`` (any ``param_axis``): scalar fit, notebook 05.
        - ``theta`` shape ``[6, H, W]`` with ``param_axis=0``: per-cell fit,
          notebook 07.
        - ``theta`` shape ``[B, 6]`` with ``param_axis=-1``: batched MLP
          output, e.g. multiple regimes evaluated in one call.
        - ``theta`` shape ``[B, 6, H, W]`` with ``param_axis=1``: batched CNN
          output (PyTorch convention with batch + channel + spatial).

    Args:
        theta: unconstrained learnable values.
        bounds: per-parameter ``[lo, hi]`` ranges, shape ``[n_params, 2]``.
        param_axis: index (positive or negative) of the parameter axis in
            ``theta``. Defaults to ``0`` (leading).

    Returns:
        physical-range parameters, same shape as ``theta``.

    Raises:
        ValueError: if ``theta.shape[param_axis] != bounds.shape[0]``.
    """
    n_params = bounds.shape[0]
    if theta.shape[param_axis] != n_params:
        raise ValueError(
            f"theta.shape[{param_axis}] = {theta.shape[param_axis]} does not "
            f"match bounds.shape[0] = {n_params}"
        )
    # Move the parameter axis to position 0 so the reshape + broadcast pattern
    # works uniformly regardless of where the caller put it.
    theta_p = theta.movedim(param_axis, 0)
    extra_dims = theta_p.ndim - 1
    lo = bounds[:, 0].reshape(n_params, *([1] * extra_dims))
    hi = bounds[:, 1].reshape(n_params, *([1] * extra_dims))
    result = lo + (hi - lo) * torch.sigmoid(theta_p)
    return result.movedim(0, param_axis)
