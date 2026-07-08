"""Tests for the differentiable vertical-transport column model (Track 2, Phase 1)."""
from __future__ import annotations

import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.integrators import integrate, relative_mass_drift
from darwindiff.transport import (
    bgc_tendency_field,
    column_tendency,
    horizontal_advection,
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


# --- horizontal advection (Phase-1 PR-1: the operator the 0-D box lacks) ---------


def _hfield(Y=4, X=5, T=2, seed=0):
    g = torch.Generator().manual_seed(seed)
    return 0.1 + torch.rand(Y, X, T, generator=g)


def _vel(Y=4, X=5, seed=0):
    g = torch.Generator().manual_seed(seed)
    return torch.rand(Y, X, generator=g) - 0.5  # signed cell-centre velocity


def test_horizontal_advection_conserves_domain_and_flows_grad():
    """Flux-form centered advection conserves the domain-integrated tracer (per
    tracer) and passes clean gradients to the field."""
    f = _hfield().requires_grad_(True)
    u, v = _vel(4, 5, 1), _vel(4, 5, 2)
    d = horizontal_advection(f, u, v, dx=1.0, dy=1.0)
    # sum over the two spatial axes (Y, X) is ~0 for every tracer (no-flux edges)
    assert d.sum(dim=(-3, -2)).abs().max().item() < 1e-5
    d.pow(2).sum().backward()
    assert torch.isfinite(f.grad).all()


def test_horizontal_advection_gradcheck_field():
    """Exact-Jacobian gradcheck (fp64) w.r.t. the field: with the upwind pattern
    fixed by the (constant) velocities, the operator is linear in the field and
    must be autograd-clean. Velocities are not gradchecked -- upwind's branch
    selection is non-smooth at zero-velocity interfaces by construction."""
    torch.manual_seed(0)
    f = (0.1 + torch.rand(3, 3, 2, dtype=torch.float64)).requires_grad_(True)
    u = torch.rand(3, 3, dtype=torch.float64) - 0.5  # fixed constants
    v = torch.rand(3, 3, dtype=torch.float64) - 0.5
    assert torch.autograd.gradcheck(
        lambda ff: horizontal_advection(ff, u, v, dx=1.0, dy=1.0), (f,)
    )


def test_horizontal_advection_rollout_conserves_mass():
    """A closed 2-D field advected under RK4 conserves the per-tracer domain total.
    Run in float64: telescoping conservation is exact in exact arithmetic, so the
    residual is pure round-off (~1e-14 in fp64; ~1e-7 in fp32 -- the earlier 1e-9
    fp32 bound passed only by luck, per the PR review)."""
    f0 = _hfield(Y=6, X=6, T=2).double()
    u, v = (0.5 * _vel(6, 6, 3)).double(), (0.5 * _vel(6, 6, 4)).double()

    def tend(s):
        return horizontal_advection(s, u, v, dx=1.0, dy=1.0)

    fN = integrate(tend, f0, dt=0.05, n_steps=60, method="rk4")
    assert torch.isfinite(fN).all()
    tot0 = f0.sum(dim=(-3, -2))
    drift = (fN.sum(dim=(-3, -2)) - tot0).abs() / tot0.abs()
    assert drift.max().item() < 1e-10


def test_horizontal_advection_upwind_stable_long_horizon():
    """Upwind is dissipative, so a divergent velocity field must NOT blow the tracer
    up over a long rollout (centered-2nd grew to ~1e10 here -- the P1 regression)."""
    f0 = _hfield(Y=6, X=6, T=2)
    u, v = 0.5 * _vel(6, 6, 3), 0.5 * _vel(6, 6, 4)

    def tend(s):
        return horizontal_advection(s, u, v, dx=1.0, dy=1.0)

    fN = integrate(tend, f0, dt=0.05, n_steps=4000, method="rk4")  # t = 200
    assert torch.isfinite(fN).all()
    assert fN.abs().max().item() < 20.0 * f0.abs().max().item()


def test_horizontal_advection_upwind_direction():
    """Upwind takes the up-current cell, and the front moves down-current: with u>0
    (v=0) a step profile [1,1,0,0] loses on the left and gains on the right. A
    wholesale sign flip inverts both signs and fails this gate."""
    f = torch.zeros(1, 4, 1)
    f[0, :2, 0] = 1.0
    u = torch.ones(1, 4)      # flow in +x everywhere
    v = torch.zeros(1, 4)
    d = horizontal_advection(f, u, v, dx=1.0, dy=1.0)[0, :, 0]
    assert d[0].item() < 0.0   # leftmost (up-current) cell loses
    assert d[2].item() > 0.0   # down-current cell gains


def test_horizontal_advection_batched_velocity_broadcast():
    """A shared per-cell [Y, X] velocity must broadcast over a batched field and
    equal the per-batch loop (the old dim-count heuristic crashed on this)."""
    torch.manual_seed(2)
    field = 0.1 + torch.rand(3, 5, 5, 2)  # [B, Y, X, T]
    u = torch.rand(5, 5) - 0.5            # bare [Y, X]
    v = torch.rand(5, 5) - 0.5
    out = horizontal_advection(field, u, v, dx=1.0, dy=1.0)
    ref = torch.stack(
        [horizontal_advection(field[b], u, v, dx=1.0, dy=1.0) for b in range(3)]
    )
    torch.testing.assert_close(out, ref)
