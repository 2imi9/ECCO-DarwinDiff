"""Toy 1D reaction-diffusion simulator, designed to be differentiable end-to-end.

Equation:
    du/dt = kappa * d²u/dz² - lambda(z) * u + S(z)

- u(z, t)    : tracer concentration at depth z, time t
- kappa      : vertical diffusion coefficient (fixed)
- lambda(z)  : depth-dependent loss rate (the parameter we learn)
- S(z)       : depth-dependent source (fixed)

Why this exists: every real biogeochemical tracer in Darwin obeys some advection-reaction-
diffusion equation. This toy captures the same gradient-flow structure (timestep loop,
spatial coupling, autograd through every step) without committing to a specific Darwin
parameterization. If autograd works here, it works in the real model.
"""

from __future__ import annotations

import torch


def step_forward(
    u: torch.Tensor,
    lambda_z: torch.Tensor,
    S_z: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
) -> torch.Tensor:
    """One forward-Euler step of the 1D reaction-diffusion equation.

    Zero-flux boundary conditions (no tracer leaves through top/bottom): the ghost cells
    are taken equal to the adjacent interior cells, which makes the discrete Laplacian
    vanish at the boundary.

    Args:
        u: shape [Nz], current concentration profile.
        lambda_z: shape [Nz], depth-dependent loss rate.
        S_z: shape [Nz], depth-dependent source.
        kappa: scalar diffusion coefficient.
        dz: spatial grid spacing.
        dt: time step.

    Returns:
        u_next: shape [Nz], concentration after one step.
    """
    # Zero-flux boundaries via index reflection — autograd-safe (no in-place ops).
    u_left = torch.cat([u[:1], u[:-1]])
    u_right = torch.cat([u[1:], u[-1:]])
    d2u_dz2 = (u_right - 2.0 * u + u_left) / dz**2

    return u + dt * (kappa * d2u_dz2 - lambda_z * u + S_z)


def integrate(
    u0: torch.Tensor,
    lambda_z: torch.Tensor,
    S_z: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
) -> torch.Tensor:
    """Integrate forward for n_steps. Autograd flows through every timestep.

    Why a Python loop instead of a vectorised solver: forward Euler is simple, transparent,
    and gives us full control over the autograd graph. Higher-order schemes (RK4, leap-frog)
    are upgrades for later — for the toy, simplicity beats sophistication.
    """
    u = u0
    for _ in range(n_steps):
        u = step_forward(u, lambda_z, S_z, kappa, dz, dt)
    return u
