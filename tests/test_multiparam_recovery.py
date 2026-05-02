"""Multi-parameter recovery test: learn mu(z) AND mortality(z) simultaneously.

This is the test that directly addresses DarwinDiff's central claim — gradient descent
learns many parameters in one training run. The single-parameter recovery tests confirm
the scaffold works; this one confirms the scaffold scales to joint recovery of multiple
spatially-varying parameters.

Tolerance is looser than the single-parameter case (25% rel RMSE per parameter vs 10–15%)
because the joint inverse problem has a bumpier loss landscape and partial identifiability
degeneracies between parameters.
"""

from __future__ import annotations

import torch

from darwindiff.prototype.coupled import (
    generate_coupled_observations_mp,
    integrate_coupled_mp,
    light_profile,
    step_forward_coupled_mp,
    train_coupled_recovery_mp,
)
from darwindiff.prototype.parameter_mlp import ParameterMLP


def _fixture() -> tuple[
    int,
    torch.Tensor,
    torch.Tensor,
    torch.Tensor,
    torch.Tensor,
]:
    """Same lit-zone setup as the single-parameter coupled test (0–200 m, 50 levels)."""
    Nz = 50
    z = torch.linspace(0.0, 200.0, Nz)
    N0 = 0.5 + 0.5 * (z / 200.0)
    P0 = 0.05 * torch.ones(Nz)
    f_light = light_profile(z, attenuation_length=100.0)
    return Nz, z, N0, P0, f_light


def test_multiparam_step_runs_and_is_finite() -> None:
    """Smoke test: a single multi-parameter step produces finite tracers."""
    Nz, _z, N0, P0, f_light = _fixture()
    mu_z = torch.full((Nz,), 0.3)
    mortality_z = torch.full((Nz,), 0.3)
    N_next, P_next = step_forward_coupled_mp(
        N0, P0, mu_z, mortality_z, f_light, kappa=0.05, dz=4.0, dt=1.0
    )
    assert N_next.shape == N0.shape
    assert P_next.shape == P0.shape
    assert torch.isfinite(N_next).all()
    assert torch.isfinite(P_next).all()


def test_autograd_flows_to_both_parameters() -> None:
    """Gradient flows from final tracer states back to BOTH mu and mortality fields."""
    Nz, _z, N0, P0, f_light = _fixture()
    mu_z = torch.full((Nz,), 0.3, requires_grad=True)
    mortality_z = torch.full((Nz,), 0.3, requires_grad=True)
    N_final, P_final = integrate_coupled_mp(
        N0, P0, mu_z, mortality_z, f_light, kappa=0.05, dz=4.0, dt=1.0, n_steps=100
    )
    (N_final.sum() + P_final.sum()).backward()
    assert mu_z.grad is not None
    assert mortality_z.grad is not None
    assert torch.isfinite(mu_z.grad).all()
    assert torch.isfinite(mortality_z.grad).all()
    assert mu_z.grad.abs().sum() > 0
    assert mortality_z.grad.abs().sum() > 0


def test_parameter_mlp_two_outputs() -> None:
    """ParameterMLP with n_outputs=2 returns shape [Nz, 2] and Softplus-positive values."""
    Nz = 50
    mlp = ParameterMLP(n_features=1, n_outputs=2)
    features = torch.randn(Nz, 1)
    out = mlp(features)
    assert out.shape == (Nz, 2)
    assert (out >= 0).all()


def test_multiparam_recovery_within_tolerance() -> None:
    """End-to-end: trained 2-output MLP recovers BOTH true profiles within 25% rel RMSE.

    Looser tolerance than single-parameter (10–15%) because the joint inverse problem
    is genuinely harder. If both parameters land within 25%, the multi-parameter scaffold
    is empirically functional.
    """
    Nz, z, N0, P0, f_light = _fixture()

    N_obs, P_obs, mu_true, mortality_true = generate_coupled_observations_mp(
        z=z, N0=N0, P0=P0, f_light=f_light,
        kappa=0.05, dz=4.0, dt=1.0, n_steps=200,
        noise_std=0.005, seed=0,
    )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    mlp, losses = train_coupled_recovery_mp(
        N_obs=N_obs, P_obs=P_obs, z=z, N0=N0, P0=P0, f_light=f_light,
        kappa=0.05, dz=4.0, dt=1.0, n_steps=200,
        n_epochs=3000, lr=1e-2, device=device,
    )

    z_norm = ((z - z.mean()) / z.std()).to(device)
    features = z_norm.unsqueeze(-1)
    with torch.no_grad():
        params = mlp(features).cpu()
    mu_pred = params[:, 0]
    mortality_pred = params[:, 1]

    rel_rmse_mu = (
        (mu_pred - mu_true).pow(2).mean().sqrt() / mu_true.mean()
    ).item()
    rel_rmse_mort = (
        (mortality_pred - mortality_true).pow(2).mean().sqrt() / mortality_true.mean()
    ).item()

    assert losses[-1] < losses[0], "Loss should decrease during training."
    assert rel_rmse_mu < 0.25, f"mu rel RMSE {rel_rmse_mu:.3f} exceeds 25%."
    assert rel_rmse_mort < 0.25, f"mortality rel RMSE {rel_rmse_mort:.3f} exceeds 25%."
