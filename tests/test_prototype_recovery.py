"""End-to-end recovery tests for the differentiable scaffold.

If these pass, we have empirical evidence that:
1. Hand-coded numerical integration is autograd-compatible (no broken gradient flow).
2. The MLP-predicts-parameter composition is stable enough for gradient descent.
3. The recovery problem actually converges on synthetic data with known truth.

These are the prerequisites for the real Darwin work — if any of them fails on the toy,
adding Darwin's complexity on top will not fix it.
"""

from __future__ import annotations

import torch

from darwindiff.prototype.physics import integrate, step_forward
from darwindiff.prototype.synthetic_data import generate_synthetic_observations
from darwindiff.prototype.train import train_recovery


def _fixture() -> tuple[int, torch.Tensor, torch.Tensor, torch.Tensor]:
    """Shared 1D column setup: 50 levels, 0–500 m, unit initial concentration, decaying source."""
    Nz = 50
    z = torch.linspace(0.0, 500.0, Nz)
    u0 = torch.ones(Nz)
    S_z = 0.1 * torch.exp(-z / 200.0)
    return Nz, z, u0, S_z


def test_step_forward_runs_and_is_finite() -> None:
    """Smoke test: a single integration step produces finite values of the right shape."""
    Nz, _z, u0, S_z = _fixture()
    lambda_z = torch.full((Nz,), 0.1)
    u_next = step_forward(u0, lambda_z, S_z, kappa=0.01, dz=10.0, dt=1.0)
    assert u_next.shape == u0.shape
    assert torch.isfinite(u_next).all()


def test_autograd_flows_through_integration() -> None:
    """Gradient flows from the final state back to the loss-rate parameter."""
    Nz, _z, u0, S_z = _fixture()
    lambda_z = torch.full((Nz,), 0.1, requires_grad=True)
    u_final = integrate(u0, lambda_z, S_z, kappa=0.01, dz=10.0, dt=1.0, n_steps=100)
    u_final.sum().backward()
    assert lambda_z.grad is not None
    assert torch.isfinite(lambda_z.grad).all()
    assert lambda_z.grad.abs().sum() > 0  # gradients are non-trivial


def test_synthetic_recovery_within_tolerance() -> None:
    """End-to-end: trained MLP recovers true lambda profile within 10% relative RMSE."""
    Nz, z, u0, S_z = _fixture()

    u_obs, lambda_true = generate_synthetic_observations(
        z=z, u0=u0, S_z=S_z, kappa=0.01, dz=10.0, dt=1.0, n_steps=200, noise_std=0.005,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    mlp, losses = train_recovery(
        u_obs=u_obs, z=z, u0=u0, S_z=S_z,
        kappa=0.01, dz=10.0, dt=1.0, n_steps=200,
        n_epochs=2000, lr=1e-2, device=device,
    )

    z_norm = ((z - z.mean()) / z.std()).to(device)
    features = z_norm.unsqueeze(-1)
    with torch.no_grad():
        lambda_pred = mlp(features).cpu()

    rel_rmse = ((lambda_pred - lambda_true).pow(2).mean().sqrt() / lambda_true.mean()).item()

    assert losses[-1] < losses[0], "Loss should decrease during training."
    assert rel_rmse < 0.10, f"Relative RMSE {rel_rmse:.3f} exceeds 10% tolerance."
