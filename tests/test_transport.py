"""Tests for the differentiable vertical-transport column model (Track 2, Phase 1)."""
from __future__ import annotations

import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.integrators import integrate, relative_mass_drift
from darwindiff.transport import (
    bgc_tendency_field,
    column_tendency,
    vertical_advection,
    vertical_diffusion,
)


def _field(C=3, Z=8, seed=0):
    g = torch.Generator().manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    return base * (1.0 + 0.1 * torch.rand(C, Z, 5, generator=g))


def test_bgc_field_matches_box_on_single_cell():
    params = carroll6.CARROLL_VALUES.clone()
    state = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    box = carroll6.carroll6_ude_tendency(state, params)
    field = bgc_tendency_field(state, params)
    torch.testing.assert_close(field, box, rtol=0.0, atol=0.0)


def test_vertical_diffusion_conserves_column_and_flows_grad():
    f = _field().requires_grad_(True)
    d = vertical_diffusion(f, kz=0.1, dz=25.0)
    # column-summed tendency is ~0 for every cell and tracer (flux-form, no-flux BC)
    assert d.sum(dim=-2).abs().max().item() < 1e-6
    d.pow(2).sum().backward()
    assert torch.isfinite(f.grad).all()


def test_vertical_advection_conserves_both_signs():
    f = _field()
    for w in (1.0, -1.0):
        d = vertical_advection(f, w=w, dz=25.0)
        assert d.sum(dim=-2).abs().max().item() < 1e-6


def test_transport_only_rollout_conserves_mass():
    """A closed column (transport, no BGC) conserves the column total under RK4."""
    f0 = _field()

    def tend(s):
        return column_tendency(s, carroll6.CARROLL_VALUES, kz=0.1, dz=25.0, w=1.0, bgc=False)

    fN = integrate(tend, f0, dt=0.25, n_steps=400, method="rk4")
    # per-column, per-tracer conservation
    drift = (fN.sum(dim=-2) - f0.sum(dim=-2)).abs() / f0.sum(dim=-2).abs()
    assert drift.max().item() < 1e-4
    assert relative_mass_drift(f0, fN).item() < 1e-4


def test_full_column_rollout_is_finite_batched():
    f0 = _field(C=16, Z=12)

    def tend(s):
        return column_tendency(s, carroll6.CARROLL_VALUES, kz=0.1, dz=25.0, w=0.5)

    fN = integrate(tend, f0, dt=0.25, n_steps=200, method="rk4")
    assert fN.shape == (16, 12, 5)
    assert torch.isfinite(fN).all()


def test_neural_closure_trains_through_batched_transport():
    """A neural iron-limitation closure gets finite, nonzero gradients through the
    full transport+BGC rollout on a batched field — the Phase-1 trainability check."""
    params = carroll6.CARROLL_VALUES.clone()
    net = nn.Sequential(nn.Linear(1, 8), nn.Tanh(), nn.Linear(8, 1), nn.Sigmoid())
    f0 = _field(C=8, Z=6)

    def ffe(dfe):
        return net(dfe.unsqueeze(-1)).squeeze(-1)

    def tend(s):
        return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe)

    fN = integrate(tend, f0, dt=0.25, n_steps=100, method="rk4", checkpoint_segment=25)
    fN.pow(2).mean().backward()
    grads = [p.grad for p in net.parameters()]
    assert all(g is not None and torch.isfinite(g).all() for g in grads)
    assert any(g.abs().sum().item() > 0.0 for g in grads)
