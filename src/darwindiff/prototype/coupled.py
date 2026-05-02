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
