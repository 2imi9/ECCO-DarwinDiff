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

Equations (5-tracer baseline, ``carroll6_step`` / ``carroll6_integrate``):
    dDFe/dt   = alpfe*Φ_dust - scav_rat*DFe*POC - Q_Fe*(μ_s P_s + μ_l P_l)*f_Fe(DFe)
    dPs/dt    = μ_s f_Fe Ps - m_lin Ps - m_quad Ps²
    dPl/dt    = μ_l f_Fe Pl - m_lin Pl - m_quad Pl² - g_diatom G0 Pl
    dPOC/dt   = M_tot - w_sink POC
    dPIC/dt   = R_PICPOC M_tot - w_sink PIC

with f_Fe(DFe) = DFe / (DFe + K_Fe) and M_tot the sum of all phyto loss fluxes.

Carbonate extension (7-tracer, ``carroll6_carbonate_step`` /
``carroll6_carbonate_integrate``): adds DIC + ALK with couplings

    dDIC/dt   = -μ_s f_Fe Ps - μ_l f_Fe Pl                  # phyto C fixation
                - R_PICPOC * M_tot                            # CaCO3 formation (calcification)
                - F_CO2 / H_mld                               # air-sea export (positive F = outgassing)
    dALK/dt   = -2 * R_PICPOC * M_tot                         # CaCO3 takes 2 ALK eq per mole

F_CO2 is computed each step from (DIC, ALK, T, S) via the Follows-2006 carbonate solver
(``darwindiff.carbonate.solve_carbonate``) and the Wanninkhof-2014 gas-transfer law
(``darwindiff.carbonate.co2_flux``). Total carbon in the box decays only through air-sea
flux + particulate sinking export — verified by ``test_carroll6_carbonate.py``.

Background defaults (M_LIN, M_QUAD, G0_GRAZE, W_SINK, K_FE, PHI_DUST, Q_FE, LIGHT, H_MLD)
are fixed at literature-plausible values and not learned — they correspond to the ~94%
of Darwin parameters Carroll left at expert defaults.

Used by notebooks 05–19 (5-tracer); nb20 onwards uses the 7-tracer extension. Darwin 3
namelist mapping for these names is documented in the project memory at
reference_darwin3.md.
"""

from __future__ import annotations

import torch

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate

# Background (non-learned) parameters — the ~94% of Darwin knobs Carroll left at defaults.
M_LIN: float = 0.05         # 1/d, linear phyto mortality
M_QUAD: float = 0.50        # 1/d / (mmol C/m^3), quadratic phyto mortality
G0_GRAZE: float = 0.30      # 1/d, baseline grazing rate (multiplied by diatomgraz)
W_SINK: float = 0.10        # 1/d, particulate sinking rate
K_FE: float = 5.0e-5        # mmol Fe/m^3, iron half-saturation for phyto growth
PHI_DUST: float = 5.0e-5    # mmol Fe/m^3/d, dissolved-iron source from dust
Q_FE: float = 1.0e-5        # mol Fe / mol C, phyto Fe quota
LIGHT: float = 1.0          # surface light, dimensionless
H_MLD: float = 50.0         # m, surface mixed-layer depth for the carbonate extension's
                            # air-sea flux conversion. ~50 m is a reasonable Eq Pacific
                            # climatology; override per-cell once Darwin's MLD field is
                            # in the loader (see Day 3 of the v2.0 closeout).


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
    [0.005, 1.5],    # R_PICPOC -- bound raised from 0.20 (session 2026-05-18 diagnostic).
                     #   Empirical Darwin v05 PIC/POC ratio: eqpac median 0.031, natl
                     #   median 0.722 (23x AOI variance). Original bound 0.20 capped at
                     #   3.6x below natl's true ratio. Diagnostic: does the learner
                     #   push above 0.20 when allowed? If not, the binding constraint
                     #   is the inter-AOI tension, not the bound.
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


def carroll6_carbonate_step(
    state: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h_mld: float = H_MLD,
) -> torch.Tensor:
    """One forward-Euler step of the 7-tracer Carroll-6 + carbonate box model.

    Extends ``carroll6_step`` with explicit DIC + ALK prognostic variables and an
    air-sea CO₂ flux computed each step via the Follows-2006 carbonate solver.
    See module docstring for the equations and the conservation derivation.

    Args:
        state: shape [7], [DFe, Ps, Pl, POC, PIC, DIC, ALK]. Iron in mmol Fe/m³;
            phyto, POC, PIC in mmol C/m³; DIC in mmol C/m³; ALK in mmol Eq/m³.
        params: shape [6], identical to ``carroll6_step``
            ([alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]).
        dt: time step in days.
        T, S, wind, pco2_atm: forcing fields. Scalars or tensors broadcastable
            with ``state`` (e.g. shape-(H, W) for per-cell fits). Defaults are
            Eq Pacific climatology: 15 °C, 35 PSU, 7 m/s wind, 405 µatm atm pCO₂.
        h_mld: mixed-layer depth in m for the air-sea-flux → tracer-rate
            conversion. Defaults to module-level ``H_MLD``.

    Returns:
        Next state, shape [7].
    """
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    DIC, ALK = state[5], state[6]
    alpfe, scav_rat, mu_s, mu_l, g_diatom, R_PICPOC = (
        params[0], params[1], params[2], params[3], params[4], params[5]
    )
    scav_rat_per_day = scav_rat * 86400.0

    # --- 5-tracer base, identical to carroll6_step -------------------------------
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

    # --- Carbonate extension -----------------------------------------------------
    # Solve for pCO2 from current DIC + ALK + T + S, then compute air-sea flux.
    # F is in mmol C / m^2 / s (positive = ocean → atm); convert to a tracer
    # rate by dividing by mixed-layer depth and multiplying by 86400 to get
    # mmol C / m^3 / d, matching the units of the biological tendencies above.
    carb = solve_carbonate(DIC, ALK, T, S)
    F_co2 = co2_flux(carb["pCO2"], pco2_atm, wind, T, S)  # mmol C / m^2 / s
    F_per_m3_per_day = F_co2 * 86400.0 / h_mld

    dDIC = (
        -growth_s - growth_l                  # phyto C fixation
        - R_PICPOC * mort_total               # CaCO3 formation (each PIC drains 1 DIC)
        - F_per_m3_per_day                    # air-sea export (positive F = DIC loss)
    )
    dALK = -2.0 * R_PICPOC * mort_total       # CaCO3 takes 2 ALK eq per mole

    return torch.stack([
        DFe + dt * dDFe,
        Ps + dt * dPs,
        Pl + dt * dPl,
        POC + dt * dPOC,
        PIC + dt * dPIC,
        DIC + dt * dDIC,
        ALK + dt * dALK,
    ])


def carroll6_carbonate_integrate(
    state0: torch.Tensor,
    params: torch.Tensor,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int] | None = None,
    T: torch.Tensor | float = 15.0,
    S: torch.Tensor | float = 35.0,
    wind: torch.Tensor | float = 7.0,
    pco2_atm: torch.Tensor | float = PCO2_ATM_DEFAULT,
    h_mld: float = H_MLD,
) -> torch.Tensor:
    """Forward-Euler integration of the 7-tracer carroll6 + carbonate box model.

    Mirrors ``carroll6_integrate`` (autograd-clean through every step) with the
    extra forcing arguments routed to ``carroll6_carbonate_step``.

    Args:
        state0: initial 7-tracer state, shape [7].
        params: Carroll-6 parameters, shape [6].
        dt: time step in days.
        n_steps: number of forward-Euler steps.
        snapshot_indices: 1-indexed steps at which to save state. If None,
            returns only the final state; otherwise returns shape
            [len(snapshot_indices), 7].
        T, S, wind, pco2_atm, h_mld: forcing — see ``carroll6_carbonate_step``.

    Returns:
        Final state shape [7] when snapshot_indices is None, else stacked snapshots.
    """
    state = state0
    if snapshot_indices is None:
        for _ in range(n_steps):
            state = carroll6_carbonate_step(
                state, params, dt, T, S, wind, pco2_atm, h_mld,
            )
        return state
    snapshot_set = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    for step in range(1, n_steps + 1):
        state = carroll6_carbonate_step(
            state, params, dt, T, S, wind, pco2_atm, h_mld,
        )
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
