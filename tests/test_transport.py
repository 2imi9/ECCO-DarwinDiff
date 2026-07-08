"""Tests for the differentiable vertical-transport column model (Track 2, Phase 1)."""
from __future__ import annotations

import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.integrators import integrate, relative_mass_drift
from darwindiff.closures import EnvCalciteClosure
from darwindiff.transport import (
    bgc_tendency_field,
    column_tendency,
    grid_tendency,
    horizontal_advection,
    horizontal_diffusion,
    vertical_advection,
    vertical_diffusion,
    w_from_continuity,
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


def test_horizontal_advection_gradcheck():
    """Exact-Jacobian gradcheck (fp64) w.r.t. the field AND the velocities: centered
    advection is smooth (no upwind sign branch), so gradients flow cleanly to u, v
    too (required if a velocity correction is ever learned)."""
    torch.manual_seed(0)
    f = (0.1 + torch.rand(3, 3, 2, dtype=torch.float64)).requires_grad_(True)
    u = (torch.rand(3, 3, dtype=torch.float64) - 0.5).requires_grad_(True)
    v = (torch.rand(3, 3, dtype=torch.float64) - 0.5).requires_grad_(True)
    assert torch.autograd.gradcheck(
        lambda ff, uu, vv: horizontal_advection(ff, uu, vv, dx=1.0, dy=1.0), (f, u, v)
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


def test_centered_advection_diffusion_stable_long_horizon():
    """A2: centered advection is non-diffusive but dispersively unstable ALONE
    (kh=0 blows up to ~1e7 even on A1's divergence-free field); paired with the
    explicit diffusion kh it stays bounded over a long rollout. This replaces the
    over-diffusive upwind scheme with a controllable, physical diffusion knob."""
    torch.manual_seed(0)
    Y, X, Z = 8, 8, 3
    u, v = 0.5 * (torch.rand(Y, X) - 0.5), 0.5 * (torch.rand(Y, X) - 0.5)
    params = carroll6.CARROLL_VALUES
    w = w_from_continuity(u, v, 1.0, 1.0, 25.0, Z)
    f0 = 0.1 + torch.rand(Y, X, Z, 1)

    def tend(kh):
        return lambda s: grid_tendency(
            s, params, u=u, v=v, w=w, kh=kh, dx=1.0, dy=1.0, kz=0.0, bgc=False
        )

    f_nodiff = integrate(tend(0.0), f0, dt=0.05, n_steps=4000, method="rk4")
    f_diff = integrate(tend(0.1), f0, dt=0.05, n_steps=4000, method="rk4")
    assert f_nodiff.abs().max().item() > 100.0                    # centered ALONE unstable
    assert torch.isfinite(f_diff).all()
    assert f_diff.abs().max().item() < 5.0 * f0.abs().max().item()  # kh stabilizes


def test_horizontal_advection_direction():
    """Advection moves the tracer down-current: with u>0 (v=0) a step [1,1,0,0]
    loses on the left and gains on the right (holds for centered too). A wholesale
    sign flip inverts both signs and fails this gate."""
    f = torch.zeros(1, 4, 1)
    f[0, :2, 0] = 1.0
    u = torch.ones(1, 4)      # flow in +x everywhere
    v = torch.zeros(1, 4)
    d = horizontal_advection(f, u, v, dx=1.0, dy=1.0)[0, :, 0]
    assert d[0].item() < 0.0   # up-current cell loses
    assert d[2].item() > 0.0   # down-current cell gains


def test_horizontal_advection_centered_linear_field_exact():
    """Centered-2nd is exact for a linear field: interior tendency == -u*dC/dx.
    Pins 2nd-order accuracy and direction; catches a sign or dx error."""
    f = torch.arange(5.0).view(1, 5, 1).expand(3, 5, 1).contiguous()  # C(x)=x
    d = horizontal_advection(f, torch.ones(3, 5), torch.zeros(3, 5), dx=1.0, dy=1.0)[..., 0]
    torch.testing.assert_close(d[1, 1:4], torch.full((3,), -1.0))  # interior = -u


def test_horizontal_diffusion_conserves_and_gradcheck():
    """Explicit Laplacian horizontal diffusion conserves the domain total and is
    autograd-clean (the physical + stabilizing companion to centered advection)."""
    f = _hfield(4, 5, 2).requires_grad_(True)
    d = horizontal_diffusion(f, kh=0.1, dx=1.0, dy=1.0)
    assert d.sum(dim=(-3, -2)).abs().max().item() < 1e-5  # domain conserved
    d.pow(2).sum().backward()
    assert torch.isfinite(f.grad).all()
    fd = (0.1 + torch.rand(3, 3, 2, dtype=torch.float64)).requires_grad_(True)
    assert torch.autograd.gradcheck(
        lambda ff: horizontal_diffusion(ff, kh=0.2, dx=1.0, dy=1.0), (fd,)
    )


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


# --- grid_tendency: full 3-D composition (horizontal + vertical + BGC) -------------


def _grid_state(Y=2, X=2, Z=3, seed=0):
    g = torch.Generator().manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    return base * (1.0 + 0.1 * torch.rand(Y, X, Z, 5, generator=g))  # [Y, X, Z, tracer]


def test_grid_tendency_gradcheck_transport():
    """fp64 gradcheck of the full 3-D transport composition (bgc off): horizontal +
    vertical operators are linear in the state, so the Jacobian is exact."""
    torch.manual_seed(0)
    state = _grid_state().double().requires_grad_(True)
    params = carroll6.CARROLL_VALUES.double()
    u = torch.rand(2, 2, dtype=torch.float64) + 0.5  # bounded away from 0 (fixed upwind pattern)
    v = torch.rand(2, 2, dtype=torch.float64) + 0.5
    assert torch.autograd.gradcheck(
        lambda s: grid_tendency(
            s, params, u=u, v=v, dx=1.0, dy=1.0, kz=0.1, dz=25.0, w=1.0, bgc=False
        ),
        (state,),
    )


def test_grid_tendency_transport_only_conserves_domain():
    """With bgc off, the 3-D field conserves the per-tracer domain total over a rollout."""
    f0 = _grid_state(Y=4, X=4, Z=4).double()
    params = carroll6.CARROLL_VALUES.double()
    u = 0.3 * (torch.rand(4, 4, dtype=torch.float64) - 0.5)
    v = 0.3 * (torch.rand(4, 4, dtype=torch.float64) - 0.5)

    def tend(s):
        return grid_tendency(
            s, params, u=u, v=v, dx=1.0, dy=1.0, kz=0.1, dz=25.0, w=1.0, bgc=False
        )

    fN = integrate(tend, f0, dt=0.05, n_steps=40, method="rk4")
    assert torch.isfinite(fN).all()
    tot0 = f0.sum(dim=(-4, -3, -2))  # over Y, X, Z per tracer
    drift = (fN.sum(dim=(-4, -3, -2)) - tot0).abs() / tot0.abs()
    assert drift.max().item() < 1e-10


def test_grid_tendency_trains_a_closure_through_full_rollout():
    """A calcite closure gets finite, nonzero gradients through the full 3-D
    (BGC + vertical + horizontal) checkpointed rollout -- end-to-end trainability."""
    params = carroll6.CARROLL_VALUES.clone()
    state0 = _grid_state(Y=3, X=3, Z=3)
    env = torch.randn(3, 3, 3, 3)  # [Y, X, Z, n_env], cell-aligned with the state
    clo = EnvCalciteClosure(env)
    u = 0.2 * (torch.rand(3, 3) - 0.5)
    v = 0.2 * (torch.rand(3, 3) - 0.5)

    def tend(s):
        return grid_tendency(
            s, params, u=u, v=v, dx=1.0, dy=1.0, kz=0.1, dz=25.0, calcite_closure=clo
        )

    fN = integrate(tend, state0, dt=0.25, n_steps=40, method="rk4", checkpoint_segment=10)
    fN.pow(2).mean().backward()
    grads = [p.grad for p in clo.net.parameters()]
    assert all(g is not None and torch.isfinite(g).all() for g in grads)
    assert any(g.abs().sum().item() > 0.0 for g in grads)


def test_grid_tendency_axis_direction_nonsquare():
    """On a NON-square grid, at an INTERIOR (wall-free) cell, advecting an X-step
    with u only acts (X-gradient) while v only does nothing (field is Y-uniform).
    Catches a Y/X wiring swap in the movedim composition, which conservation and
    field-gradcheck are both blind to (deep-review P1 test-gap). Uses Y=3 so Y=1 is
    interior -- avoiding the no-flux wall effect that every edge cell feels."""
    params = carroll6.CARROLL_VALUES
    f = torch.zeros(3, 4, 2, 1)  # [Y=3, X=4, Z=2, tracer]
    f[:, 0, :, 0] = 1.0          # step along X only; uniform in Y and Z
    kw = dict(dx=1.0, dy=1.0, kz=0.0, w=0.0, bgc=False)
    u_only = grid_tendency(f, params, u=torch.ones(3, 4), v=torch.zeros(3, 4), **kw)[..., 0]
    v_only = grid_tendency(f, params, u=torch.zeros(3, 4), v=torch.ones(3, 4), **kw)[..., 0]
    assert u_only[1, 1:3].abs().sum().item() > 0.0   # interior: u advects the X-step
    assert v_only[1, 1:3].abs().sum().item() == 0.0  # interior: v on a Y-uniform field = 0


def test_grid_checkpoint_matches_dense_with_closure():
    """Checkpoint-vs-dense gradient equivalence through grid_tendency + a live
    closure (with the upwind `where` branch under recompute) -- the invariant the
    checkpointed-decadal plan rests on, previously only tested on a linear tendency."""
    params = carroll6.CARROLL_VALUES.clone()
    env = torch.randn(3, 3, 3, 3, generator=torch.Generator().manual_seed(9))
    u = 0.2 * (torch.rand(3, 3, generator=torch.Generator().manual_seed(1)) - 0.5)
    v = 0.2 * (torch.rand(3, 3, generator=torch.Generator().manual_seed(2)) - 0.5)

    def run(segment):
        torch.manual_seed(0)
        clo = EnvCalciteClosure(env)
        s0 = _grid_state(3, 3, 3).clone().requires_grad_(True)
        fN = integrate(
            lambda s: grid_tendency(
                s, params, u=u, v=v, dx=1.0, dy=1.0, kz=0.1, dz=25.0, calcite_closure=clo
            ),
            s0, dt=0.25, n_steps=20, method="rk4", checkpoint_segment=segment,
        )
        fN.pow(2).sum().backward()
        return s0.grad.clone(), torch.cat([p.grad.flatten() for p in clo.net.parameters()])

    g_dense, p_dense = run(None)
    g_ckpt, p_ckpt = run(5)
    torch.testing.assert_close(g_dense, g_ckpt, rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(p_dense, p_ckpt, rtol=1e-5, atol=1e-6)


# --- A1: continuity-diagnosed w(z) makes the 3-D flux divergence-free ---------------


def test_w_from_continuity_makes_uniform_field_stationary():
    """A1 core: a UNIFORM tracer under (u, v, w_from_continuity) has ~0 tendency at
    every cell (fp64 machine precision), whereas w=0 on the divergent field
    manufactures O(1) spurious per-cell structure (the false-E2 source)."""
    torch.manual_seed(0)
    Y, X, Z = 4, 5, 3
    u = (torch.rand(Y, X) - 0.5).double()
    v = (torch.rand(Y, X) - 0.5).double()
    params = carroll6.CARROLL_VALUES.double()
    f = torch.ones(Y, X, Z, 1, dtype=torch.float64)
    d0 = grid_tendency(f, params, u=u, v=v, w=0.0, dx=1.0, dy=1.0, kz=0.0, bgc=False)
    w = w_from_continuity(u, v, 1.0, 1.0, 25.0, Z)
    dw = grid_tendency(f, params, u=u, v=v, w=w, dx=1.0, dy=1.0, kz=0.0, bgc=False)
    assert d0.abs().max().item() > 0.1     # divergent w=0 manufactures structure
    assert dw.abs().max().item() < 1e-12   # continuity w cancels it to machine zero (fp64)


def test_w_from_continuity_rollout_stays_uniform():
    """A uniform tracer under the continuity-diagnosed velocity stays uniform over a
    rollout (no fake structure develops -- the surrogate-gap artifact is removed)."""
    torch.manual_seed(1)
    Y, X, Z = 4, 4, 3
    u = torch.rand(Y, X) - 0.5
    v = torch.rand(Y, X) - 0.5
    params = carroll6.CARROLL_VALUES
    w = w_from_continuity(u, v, 1.0, 1.0, 25.0, Z)
    f0 = torch.ones(Y, X, Z, 1)

    def tend(s):
        return grid_tendency(s, params, u=u, v=v, w=w, dx=1.0, dy=1.0, kz=0.0, bgc=False)

    fN = integrate(tend, f0, dt=0.05, n_steps=400, method="rk4")
    assert torch.isfinite(fN).all()
    assert (fN - 1.0).abs().max().item() < 1e-5


def test_vertical_advection_per_interface_conserves_when_closed():
    """Per-interface tensor-w vertical advection conserves the column when both
    boundary interfaces are zero (closed column)."""
    f = _field(C=3, Z=6)  # [C, Z, tracer]
    w = torch.zeros(3, 7)
    w[:, 1:-1] = 0.3 * (torch.rand(3, 5) - 0.5)  # interior interfaces nonzero, ends = 0
    d = vertical_advection(f, w, dz=25.0)
    assert d.sum(dim=-2).abs().max().item() < 1e-6
