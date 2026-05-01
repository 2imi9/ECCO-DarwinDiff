"""Synthetic observations from a known-truth parameter profile.

Why generate fake data when we have real ECCO-Darwin output: this is the BINN-style validation
pattern. The MLP is asked to recover a profile we already know. If it succeeds, the
differentiable scaffold (autograd + optimiser + parameter MLP) demonstrably works. Only after
that do we trust it on real data, where we can no longer score against ground truth.
"""

from __future__ import annotations

import torch

from .physics import integrate


def true_lambda_profile(z: torch.Tensor) -> torch.Tensor:
    """Ground-truth depth-dependent loss rate.

    Pattern: high near the surface, exponential decay with depth. Plausibly oceanographic
    (surface remineralisation is faster than deep) and smooth enough that a small MLP can
    fit it without overparameterisation.
    """
    return 0.1 + 0.5 * torch.exp(-z / 100.0)


def generate_synthetic_observations(
    z: torch.Tensor,
    u0: torch.Tensor,
    S_z: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    noise_std: float = 0.005,
    seed: int = 0,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Run the toy forward with the TRUE lambda(z), add Gaussian noise, return as observations.

    The added Gaussian noise stands in for the irreducible measurement noise in real
    biogeochemistry data (GLODAP cruise samples, BGC-Argo sensor drift). It also keeps the
    recovery problem honest — without noise, the network could trivially memorise.

    Returns:
        u_obs: shape [Nz], noisy final concentration.
        lambda_true: shape [Nz], the ground-truth profile (for evaluation only — never seen
            by the MLP during training).
    """
    torch.manual_seed(seed)
    lambda_true = true_lambda_profile(z)
    u_final = integrate(u0, lambda_true, S_z, kappa, dz, dt, n_steps)
    noise = noise_std * torch.randn_like(u_final)
    return u_final + noise, lambda_true
