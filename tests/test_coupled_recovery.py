"""End-to-end recovery tests for the coupled two-tracer scaffold.

Same three layers as the single-tracer test (smoke, autograd, recovery), but on the harder
nutrient + phytoplankton system. If recovery still works here, the differentiable scaffold
handles inter-tracer coupling and nonlinear reaction terms — the structural feature that
matters for real Darwin biogeochemistry.
"""

from __future__ import annotations

import torch

from darwindiff.prototype.coupled import (
    generate_coupled_observations,
    integrate_coupled,
    light_profile,
    step_forward_coupled,
    train_coupled_recovery,
)


def _fixture() -> tuple[
    int,
    torch.Tensor,  # z
    torch.Tensor,  # N0
    torch.Tensor,  # P0
    torch.Tensor,  # f_light
]:
    """Shared 1D column setup for the coupled tests.

    Domain is 0–200 m, the lit zone where mu(z) is identifiable from the observations.
    Below the photic depth the uptake term mu*P*f_light*N is essentially zero regardless
    of mu, so mu(z) cannot be recovered there — restricting the domain keeps the inverse
    problem well-posed. Light attenuation length is 100 m so f_light remains > 0.13 even
    at 200 m. Initial nutrient is depth-graded (0.5 surface → 1.0 at 200 m); plankton
    seed is small and uniform.
    """
    Nz = 50
    z = torch.linspace(0.0, 200.0, Nz)
    N0 = 0.5 + 0.5 * (z / 200.0)
    P0 = 0.05 * torch.ones(Nz)
    f_light = light_profile(z, attenuation_length=100.0)
    return Nz, z, N0, P0, f_light


def test_step_forward_coupled_runs_and_is_finite() -> None:
    """Smoke test: a single coupled step produces finite N and P of the right shape."""
    Nz, _z, N0, P0, f_light = _fixture()
    mu_z = torch.full((Nz,), 0.3)
    N_next, P_next = step_forward_coupled(
        N0, P0, mu_z, f_light, kappa=0.05, mortality=0.3, dz=4.0, dt=1.0
    )
    assert N_next.shape == N0.shape
    assert P_next.shape == P0.shape
    assert torch.isfinite(N_next).all()
    assert torch.isfinite(P_next).all()


def test_autograd_flows_through_coupled_integration() -> None:
    """Gradient flows from BOTH final tracer states back to the uptake parameter."""
    Nz, _z, N0, P0, f_light = _fixture()
    mu_z = torch.full((Nz,), 0.3, requires_grad=True)
    N_final, P_final = integrate_coupled(
        N0, P0, mu_z, f_light, kappa=0.05, mortality=0.3, dz=4.0, dt=1.0, n_steps=100
    )
    (N_final.sum() + P_final.sum()).backward()
    assert mu_z.grad is not None
    assert torch.isfinite(mu_z.grad).all()
    assert mu_z.grad.abs().sum() > 0


def test_coupled_recovery_within_tolerance() -> None:
    """End-to-end: trained MLP recovers true mu(z) within 15% relative RMSE.

    Looser tolerance than the single-tracer case (10%) because the coupled inverse
    problem is structurally harder — the MLP has to balance both N and P observations
    through the nonlinear coupling.
    """
    Nz, z, N0, P0, f_light = _fixture()

    N_obs, P_obs, mu_true = generate_coupled_observations(
        z=z, N0=N0, P0=P0, f_light=f_light,
        kappa=0.05, mortality=0.3, dz=4.0, dt=1.0, n_steps=200,
        noise_std=0.005, seed=0,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    mlp, losses = train_coupled_recovery(
        N_obs=N_obs, P_obs=P_obs, z=z, N0=N0, P0=P0, f_light=f_light,
        kappa=0.05, mortality=0.3, dz=4.0, dt=1.0, n_steps=200,
        n_epochs=2500, lr=1e-2, device=device,
    )

    z_norm = ((z - z.mean()) / z.std()).to(device)
    features = z_norm.unsqueeze(-1)
    with torch.no_grad():
        mu_pred = mlp(features).cpu()

    rel_rmse = ((mu_pred - mu_true).pow(2).mean().sqrt() / mu_true.mean()).item()

    assert losses[-1] < losses[0], "Loss should decrease during training."
    assert rel_rmse < 0.15, f"Relative RMSE {rel_rmse:.3f} exceeds 15% tolerance."
