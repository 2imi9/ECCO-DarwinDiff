"""Coupled two-tracer prototype: nutrient + phytoplankton in a 1D column.

The next step beyond the single-tracer prototype. Real ECCO-Darwin biogeochemistry is a
coupled system of many interacting tracers; this two-tracer toy is the smallest test that
the differentiable scaffold handles inter-tracer coupling and nonlinear reaction terms.

Equations (NPZ-style, light-limited growth):

    dN/dt = kappa * d²N/dz² - mu(z) * P * f_light(z) * N
    dP/dt = kappa * d²P/dz² + mu(z) * P * f_light(z) * N - mortality * P²

- N(z, t)      : nutrient concentration
- P(z, t)      : phytoplankton biomass
- mu(z)        : depth-dependent uptake rate (the parameter we learn)
- f_light(z)   : fixed light profile, exponential decay with depth
- mortality    : fixed quadratic loss coefficient

Why quadratic mortality: density-dependent loss is standard in NPZ plankton models and
bounds growth — without it, sustained nutrient supply can drive unbounded blow-up.

Why coupled is meaningfully harder than the single-tracer case: an error in mu(z) propagates
through the full N–P coupling, so the MLP has to find a single mu profile that
simultaneously reproduces both observed tracer fields. Real Darwin parameters work the
same way — one parameter influences many tracers via the BGC reaction network.
"""

from __future__ import annotations

import torch
from torch.optim import Adam

from .parameter_mlp import ParameterMLP


def light_profile(z: torch.Tensor, attenuation_length: float = 50.0) -> torch.Tensor:
    """Exponential light attenuation with depth; normalised to 1 at the surface."""
    return torch.exp(-z / attenuation_length)


def step_forward_coupled(
    N: torch.Tensor,
    P: torch.Tensor,
    mu_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    mortality: float,
    dz: float,
    dt: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """One forward-Euler step of the coupled two-tracer system.

    Zero-flux boundaries on both tracers (same scheme as the single-tracer prototype).
    Reaction terms are evaluated at the current state — the standard explicit-Euler
    coupling.
    """
    # Diffusion for N
    N_left = torch.cat([N[:1], N[:-1]])
    N_right = torch.cat([N[1:], N[-1:]])
    d2N = (N_right - 2.0 * N + N_left) / dz**2

    # Diffusion for P
    P_left = torch.cat([P[:1], P[:-1]])
    P_right = torch.cat([P[1:], P[-1:]])
    d2P = (P_right - 2.0 * P + P_left) / dz**2

    # Reactions: phytoplankton consumes nutrient (light- and rate-modulated),
    # quadratic mortality removes biomass.
    uptake = mu_z * P * f_light * N
    loss = mortality * P * P

    N_next = N + dt * (kappa * d2N - uptake)
    P_next = P + dt * (kappa * d2P + uptake - loss)
    return N_next, P_next


def integrate_coupled(
    N0: torch.Tensor,
    P0: torch.Tensor,
    mu_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    mortality: float,
    dz: float,
    dt: float,
    n_steps: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Integrate the coupled system forward for n_steps. Autograd flows through both tracers."""
    N, P = N0, P0
    for _ in range(n_steps):
        N, P = step_forward_coupled(N, P, mu_z, f_light, kappa, mortality, dz, dt)
    return N, P


def true_mu_profile(z: torch.Tensor) -> torch.Tensor:
    """Ground-truth uptake rate: surface-enhanced, decays with depth.

    Pattern: 0.05 baseline plus a 0.5 surface bonus that decays exponentially. Plausibly
    oceanographic — phytoplankton uptake is typically faster in well-lit surface waters
    and slower at depth.
    """
    return 0.05 + 0.5 * torch.exp(-z / 80.0)


def generate_coupled_observations(
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    mortality: float,
    dz: float,
    dt: float,
    n_steps: int,
    noise_std: float = 0.005,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """Generate noisy observations of both tracers from the TRUE mu(z).

    Returns:
        N_obs: shape [Nz], noisy final nutrient profile.
        P_obs: shape [Nz], noisy final phytoplankton profile.
        mu_true: shape [Nz], ground-truth uptake rate (for evaluation only).
    """
    torch.manual_seed(seed)
    mu_true = true_mu_profile(z)
    N_final, P_final = integrate_coupled(
        N0, P0, mu_true, f_light, kappa, mortality, dz, dt, n_steps
    )
    N_obs = N_final + noise_std * torch.randn_like(N_final)
    P_obs = P_final + noise_std * torch.randn_like(P_final)
    return N_obs, P_obs, mu_true


def train_coupled_recovery(
    N_obs: torch.Tensor,
    P_obs: torch.Tensor,
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    mortality: float,
    dz: float,
    dt: float,
    n_steps: int,
    n_epochs: int = 1000,
    lr: float = 1e-2,
    device: str = "cuda",
) -> tuple[ParameterMLP, list[float]]:
    """Train MLP to recover mu(z) from observations of BOTH tracers.

    Loss is the sum of MSE on N and on P. The MLP must find a single mu(z) profile that
    simultaneously reproduces both observed tracer fields — a strictly harder inverse
    problem than the single-tracer case because errors in mu propagate through the coupling.
    """
    N_obs = N_obs.to(device)
    P_obs = P_obs.to(device)
    z = z.to(device)
    N0 = N0.to(device)
    P0 = P0.to(device)
    f_light = f_light.to(device)

    z_norm = (z - z.mean()) / z.std()
    features = z_norm.unsqueeze(-1)

    mlp = ParameterMLP(n_features=1).to(device)
    optimizer = Adam(mlp.parameters(), lr=lr)
    losses: list[float] = []

    for _ in range(n_epochs):
        optimizer.zero_grad()
        mu_pred = mlp(features)
        N_pred, P_pred = integrate_coupled(
            N0, P0, mu_pred, f_light, kappa, mortality, dz, dt, n_steps
        )
        loss = ((N_pred - N_obs) ** 2).mean() + ((P_pred - P_obs) ** 2).mean()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return mlp, losses


# ---------------------------------------------------------------------------
# Multi-parameter variant: learn mu(z) AND mortality(z) simultaneously.
#
# Why this matters: the central DarwinDiff claim is that gradient descent learns
# many parameters in one training run, where Green's-functions has to do them one
# at a time. Single-parameter recovery (the function above) does not exercise that
# claim. Multi-parameter recovery does — the MLP outputs two values per cell, and
# the optimiser has to disentangle which observation features go to which parameter.
# ---------------------------------------------------------------------------


def step_forward_coupled_mp(
    N: torch.Tensor,
    P: torch.Tensor,
    mu_z: torch.Tensor,
    mortality_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Coupled forward step where mortality is a per-cell array, not a global scalar."""
    N_left = torch.cat([N[:1], N[:-1]])
    N_right = torch.cat([N[1:], N[-1:]])
    d2N = (N_right - 2.0 * N + N_left) / dz**2

    P_left = torch.cat([P[:1], P[:-1]])
    P_right = torch.cat([P[1:], P[-1:]])
    d2P = (P_right - 2.0 * P + P_left) / dz**2

    uptake = mu_z * P * f_light * N
    loss = mortality_z * P * P

    N_next = N + dt * (kappa * d2N - uptake)
    P_next = P + dt * (kappa * d2P + uptake - loss)
    return N_next, P_next


def integrate_coupled_mp(
    N0: torch.Tensor,
    P0: torch.Tensor,
    mu_z: torch.Tensor,
    mortality_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Integrate the multi-parameter coupled system forward for n_steps."""
    N, P = N0, P0
    for _ in range(n_steps):
        N, P = step_forward_coupled_mp(N, P, mu_z, mortality_z, f_light, kappa, dz, dt)
    return N, P


def true_mortality_profile(z: torch.Tensor) -> torch.Tensor:
    """Ground-truth depth-dependent mortality.

    Pattern: low at surface, increases linearly with depth (loosely stands in for
    sinking and grazing pressure that grow downward in real ocean columns). Distinct
    from the surface-enhanced shape of true_mu_profile, which keeps the joint inverse
    problem better posed than two parameters with the same depth structure would.
    """
    return 0.1 + 0.4 * (z / 200.0)


def generate_coupled_observations_mp(
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    noise_std: float = 0.005,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Run the coupled toy with TRUE mu(z) AND TRUE mortality(z), add noise.

    Returns:
        N_obs, P_obs: noisy final tracer profiles.
        mu_true, mortality_true: ground-truth profiles for evaluation only.
    """
    torch.manual_seed(seed)
    mu_true = true_mu_profile(z)
    mortality_true = true_mortality_profile(z)
    N_final, P_final = integrate_coupled_mp(
        N0, P0, mu_true, mortality_true, f_light, kappa, dz, dt, n_steps
    )
    N_obs = N_final + noise_std * torch.randn_like(N_final)
    P_obs = P_final + noise_std * torch.randn_like(P_final)
    return N_obs, P_obs, mu_true, mortality_true


def train_coupled_recovery_mp(
    N_obs: torch.Tensor,
    P_obs: torch.Tensor,
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    n_epochs: int = 3000,
    lr: float = 1e-2,
    device: str = "cuda",
) -> tuple[ParameterMLP, list[float]]:
    """Train a 2-output MLP to recover mu(z) AND mortality(z) from observations of N, P.

    The MLP has a shared trunk and Softplus-positive outputs for both parameters. Loss
    is MSE on N + MSE on P, so the optimiser must find a (mu, mortality) pair that
    jointly reproduces both observed tracer fields.

    More epochs than the single-parameter variant: the joint inverse problem has a
    bumpier loss landscape, and partial degeneracies between parameters slow convergence.
    """
    N_obs = N_obs.to(device)
    P_obs = P_obs.to(device)
    z = z.to(device)
    N0 = N0.to(device)
    P0 = P0.to(device)
    f_light = f_light.to(device)

    z_norm = (z - z.mean()) / z.std()
    features = z_norm.unsqueeze(-1)

    mlp = ParameterMLP(n_features=1, n_outputs=2).to(device)
    optimizer = Adam(mlp.parameters(), lr=lr)
    losses: list[float] = []

    for _ in range(n_epochs):
        optimizer.zero_grad()
        params = mlp(features)
        mu_pred = params[:, 0]
        mortality_pred = params[:, 1]
        N_pred, P_pred = integrate_coupled_mp(
            N0, P0, mu_pred, mortality_pred, f_light, kappa, dz, dt, n_steps
        )
        loss = ((N_pred - N_obs) ** 2).mean() + ((P_pred - P_obs) ** 2).mean()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return mlp, losses


# ---------------------------------------------------------------------------
# 4-parameter closed-loop NPZ — extends the multi-parameter scaffold to four
# spatially-varying knobs that all interact through a coupled cycle.
#
# Equations (closed loop with remineralisation):
#     dN/dt = kappa * d²N/dz² - uptake + r_remin(z) * mortality
#     dP/dt = kappa * d²P/dz² + uptake - mortality
# where:
#     uptake     = mu(z)        * P * f_light(z) * N
#     mortality  = m_lin(z) * P + m_quad(z) * P²
#     recycle    = r_remin(z) * mortality      (returned to N pool)
#
# Four learned parameters: mu(z), m_lin(z), m_quad(z), r_remin(z). Distinct depth
# structures keep the joint inverse problem better posed.
#
# Mass conservation property: when r_remin(z) ≡ 1 everywhere (no export), total
# tracer N + P is conserved up to numerical error from forward-Euler. This is the
# basis of the conservation test in tests/test_4param_recovery.py.
# ---------------------------------------------------------------------------


def step_forward_coupled_4p(
    N: torch.Tensor,
    P: torch.Tensor,
    mu_z: torch.Tensor,
    m_lin_z: torch.Tensor,
    m_quad_z: torch.Tensor,
    r_remin_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """One forward-Euler step of the 4-parameter closed-loop coupled system."""
    N_left = torch.cat([N[:1], N[:-1]])
    N_right = torch.cat([N[1:], N[-1:]])
    d2N = (N_right - 2.0 * N + N_left) / dz**2

    P_left = torch.cat([P[:1], P[:-1]])
    P_right = torch.cat([P[1:], P[-1:]])
    d2P = (P_right - 2.0 * P + P_left) / dz**2

    uptake = mu_z * P * f_light * N
    mortality = m_lin_z * P + m_quad_z * P * P
    recycle = r_remin_z * mortality

    N_next = N + dt * (kappa * d2N - uptake + recycle)
    P_next = P + dt * (kappa * d2P + uptake - mortality)
    return N_next, P_next


def integrate_coupled_4p(
    N0: torch.Tensor,
    P0: torch.Tensor,
    mu_z: torch.Tensor,
    m_lin_z: torch.Tensor,
    m_quad_z: torch.Tensor,
    r_remin_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Integrate the 4-parameter closed-loop system forward for n_steps."""
    N, P = N0, P0
    for _ in range(n_steps):
        N, P = step_forward_coupled_4p(
            N, P, mu_z, m_lin_z, m_quad_z, r_remin_z, f_light, kappa, dz, dt
        )
    return N, P


def true_m_lin_profile(z: torch.Tensor) -> torch.Tensor:
    """Ground-truth depth-dependent LINEAR mortality.

    Surface-enhanced (small) plus low baseline. Distinct from the depth-increasing
    quadratic mortality so the two mortality terms remain separable.
    """
    return 0.02 + 0.03 * torch.exp(-z / 120.0)


def true_r_remin_profile(z: torch.Tensor) -> torch.Tensor:
    """Ground-truth depth-dependent remineralisation fraction.

    Surface-enhanced (organic matter recycles quickly in warm surface waters), decays
    with depth. Peak value 0.2 keeps the closed loop from dominating: 80%+ of mortality
    is exported rather than recycled, which preserves identifiability between mu and
    the mortality terms. With the original peak of 0.7 the joint inverse problem had
    a recycle-dominated degeneracy in which mu could scale freely against mortality
    without changing the steady-state observables.
    """
    return 0.2 * torch.exp(-z / 150.0)


def generate_coupled_observations_4p(
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    noise_std: float = 0.005,
    seed: int = 0,
) -> tuple[
    torch.Tensor, torch.Tensor,
    torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor,
]:
    """Run the 4-parameter closed-loop toy with all known TRUE profiles, add noise.

    Returns:
        N_obs, P_obs: noisy final tracer profiles.
        mu_true, m_lin_true, m_quad_true, r_remin_true: ground-truth profiles.
    """
    torch.manual_seed(seed)
    mu_true = true_mu_profile(z)
    m_lin_true = true_m_lin_profile(z)
    m_quad_true = true_mortality_profile(z)
    r_remin_true = true_r_remin_profile(z)
    N_final, P_final = integrate_coupled_4p(
        N0, P0, mu_true, m_lin_true, m_quad_true, r_remin_true,
        f_light, kappa, dz, dt, n_steps,
    )
    N_obs = N_final + noise_std * torch.randn_like(N_final)
    P_obs = P_final + noise_std * torch.randn_like(P_final)
    return N_obs, P_obs, mu_true, m_lin_true, m_quad_true, r_remin_true


def train_coupled_recovery_4p(
    N_obs: torch.Tensor,
    P_obs: torch.Tensor,
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    n_epochs: int = 5000,
    lr: float = 5e-3,
    device: str = "cuda",
    init_bias: float = -2.0,
) -> tuple[ParameterMLP, list[float]]:
    """Train a 4-output MLP to recover mu, m_lin, m_quad, and r_remin jointly.

    The ``init_bias`` argument biases the MLP's final linear layer so initial Softplus
    outputs are small (Softplus(-2) ≈ 0.13). Without this, random initialisation gives
    Softplus output around 0.7 everywhere, which is ~30× too large for the linear
    mortality term — plankton crashes to zero in the first few integration steps and
    the gradient signal for the other parameters collapses. This is a real issue for
    multi-parameter recovery whenever the parameters span multiple orders of magnitude
    in their physically reasonable ranges.
    """
    N_obs = N_obs.to(device)
    P_obs = P_obs.to(device)
    z = z.to(device)
    N0 = N0.to(device)
    P0 = P0.to(device)
    f_light = f_light.to(device)

    z_norm = (z - z.mean()) / z.std()
    features = z_norm.unsqueeze(-1)

    mlp = ParameterMLP(n_features=1, n_outputs=4).to(device)
    # Negative bias on the final Linear layer keeps initial Softplus output small.
    with torch.no_grad():
        final_linear = mlp.net[-2]  # last layer before Softplus
        final_linear.bias.fill_(init_bias)
    optimizer = Adam(mlp.parameters(), lr=lr)
    losses: list[float] = []

    for _ in range(n_epochs):
        optimizer.zero_grad()
        params = mlp(features)
        N_pred, P_pred = integrate_coupled_4p(
            N0, P0,
            params[:, 0], params[:, 1], params[:, 2], params[:, 3],
            f_light, kappa, dz, dt, n_steps,
        )
        loss = ((N_pred - N_obs) ** 2).mean() + ((P_pred - P_obs) ** 2).mean()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return mlp, losses


# ---------------------------------------------------------------------------
# Trajectory-observation variant of the 4-parameter recovery.
#
# Why this exists: with steady-state-only observations (just the final N and P
# fields), the 4-parameter inverse problem has a flow-rate degeneracy — multiple
# (mu, m_lin, m_quad, r_remin) combinations produce the same equilibrium because
# only NET fluxes are observable. Higher-throughput solutions (faster cycling
# rates) and lower-throughput solutions look identical at steady state.
#
# Observing at MULTIPLE TIME POINTS along the trajectory constrains the rate of
# approach to equilibrium — that breaks the degeneracy because different cycling
# rates produce different transients even when their steady states match. This
# is also physically realistic: BGC-Argo floats, ship cruises, and remote sensing
# all produce time-series, not single-time snapshots.
# ---------------------------------------------------------------------------


def integrate_coupled_4p_traj(
    N0: torch.Tensor,
    P0: torch.Tensor,
    mu_z: torch.Tensor,
    m_lin_z: torch.Tensor,
    m_quad_z: torch.Tensor,
    r_remin_z: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int],
) -> tuple[torch.Tensor, torch.Tensor]:
    """Integrate the 4-parameter system, saving N and P at the requested step indices.

    Returns:
        N_traj: shape [n_snapshots, Nz].
        P_traj: shape [n_snapshots, Nz].
    """
    snapshot_set = set(snapshot_indices)
    snapshots_N: list[torch.Tensor] = []
    snapshots_P: list[torch.Tensor] = []
    N, P = N0, P0
    for step in range(1, n_steps + 1):
        N, P = step_forward_coupled_4p(
            N, P, mu_z, m_lin_z, m_quad_z, r_remin_z, f_light, kappa, dz, dt
        )
        if step in snapshot_set:
            snapshots_N.append(N)
            snapshots_P.append(P)
    return torch.stack(snapshots_N), torch.stack(snapshots_P)


def generate_coupled_observations_4p_traj(
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int],
    noise_std: float = 0.005,
    seed: int = 0,
) -> tuple[
    torch.Tensor, torch.Tensor,
    torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor,
]:
    """Generate noisy time-series observations of N and P at multiple snapshot indices.

    Returns:
        N_obs_traj, P_obs_traj: shape [n_snapshots, Nz], noisy.
        mu_true, m_lin_true, m_quad_true, r_remin_true: ground-truth parameter profiles.
    """
    torch.manual_seed(seed)
    mu_true = true_mu_profile(z)
    m_lin_true = true_m_lin_profile(z)
    m_quad_true = true_mortality_profile(z)
    r_remin_true = true_r_remin_profile(z)
    N_traj, P_traj = integrate_coupled_4p_traj(
        N0, P0, mu_true, m_lin_true, m_quad_true, r_remin_true,
        f_light, kappa, dz, dt, n_steps, snapshot_indices,
    )
    N_obs_traj = N_traj + noise_std * torch.randn_like(N_traj)
    P_obs_traj = P_traj + noise_std * torch.randn_like(P_traj)
    return N_obs_traj, P_obs_traj, mu_true, m_lin_true, m_quad_true, r_remin_true


def train_coupled_recovery_4p_traj(
    N_obs_traj: torch.Tensor,
    P_obs_traj: torch.Tensor,
    z: torch.Tensor,
    N0: torch.Tensor,
    P0: torch.Tensor,
    f_light: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    snapshot_indices: list[int],
    n_epochs: int = 5000,
    lr: float = 5e-3,
    device: str = "cuda",
    init_bias: float = -2.0,
) -> tuple[ParameterMLP, list[float]]:
    """Train 4-output MLP using time-series observations to break flow-rate degeneracies."""
    N_obs_traj = N_obs_traj.to(device)
    P_obs_traj = P_obs_traj.to(device)
    z = z.to(device)
    N0 = N0.to(device)
    P0 = P0.to(device)
    f_light = f_light.to(device)

    z_norm = (z - z.mean()) / z.std()
    features = z_norm.unsqueeze(-1)

    mlp = ParameterMLP(n_features=1, n_outputs=4).to(device)
    with torch.no_grad():
        mlp.net[-2].bias.fill_(init_bias)
    optimizer = Adam(mlp.parameters(), lr=lr)
    losses: list[float] = []

    for _ in range(n_epochs):
        optimizer.zero_grad()
        params = mlp(features)
        N_pred_traj, P_pred_traj = integrate_coupled_4p_traj(
            N0, P0,
            params[:, 0], params[:, 1], params[:, 2], params[:, 3],
            f_light, kappa, dz, dt, n_steps, snapshot_indices,
        )
        loss = (
            ((N_pred_traj - N_obs_traj) ** 2).mean()
            + ((P_pred_traj - P_obs_traj) ** 2).mean()
        )
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return mlp, losses
