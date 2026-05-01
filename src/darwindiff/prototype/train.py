"""Recovery training loop: MLP learns lambda(z) such that the simulator output matches u_obs.

Why a single MSE loss on the final state: the toy is steady-ish at the end of integration, so
the final-state mismatch carries the gradient signal. For real Darwin we will compare full
trajectories (per-tracer, per-time, per-cell), but the scaffold is identical.
"""

from __future__ import annotations

import torch
from torch.optim import Adam

from .parameter_mlp import ParameterMLP
from .physics import integrate


def train_recovery(
    u_obs: torch.Tensor,
    z: torch.Tensor,
    u0: torch.Tensor,
    S_z: torch.Tensor,
    kappa: float,
    dz: float,
    dt: float,
    n_steps: int,
    n_epochs: int = 2000,
    lr: float = 1e-2,
    device: str = "cuda",
) -> tuple[ParameterMLP, list[float]]:
    """Train an MLP to recover lambda(z) from the synthetic observations u_obs.

    Returns the trained MLP and the per-epoch loss history.

    Why depth is normalised before being fed to the MLP: raw depths span 0–500 m. Without
    normalisation, the first linear layer sees huge inputs and the gradient scale is bad
    on initialisation. Mean-zero / unit-variance features keep training stable.
    """
    u_obs = u_obs.to(device)
    z = z.to(device)
    u0 = u0.to(device)
    S_z = S_z.to(device)

    z_norm = (z - z.mean()) / z.std()
    features = z_norm.unsqueeze(-1)

    mlp = ParameterMLP(n_features=1).to(device)
    optimizer = Adam(mlp.parameters(), lr=lr)
    losses: list[float] = []

    for _ in range(n_epochs):
        optimizer.zero_grad()
        lambda_pred = mlp(features)
        u_pred = integrate(u0, lambda_pred, S_z, kappa, dz, dt, n_steps)
        loss = ((u_pred - u_obs) ** 2).mean()
        loss.backward()
        optimizer.step()
        losses.append(loss.item())

    return mlp, losses
