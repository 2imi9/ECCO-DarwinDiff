"""Tests for darwindiff.integrators (time-aware RK4/Euler, checkpointing, drift)."""
from __future__ import annotations

import math

import torch

from darwindiff import carroll6
from darwindiff.integrators import (
    euler_step,
    integrate,
    relative_mass_drift,
)


def _decay(k: torch.Tensor):
    """Time-aware tendency for dx/dt = -k x (exact x0 * exp(-k t))."""
    return lambda t, x: -k * x


def test_euler_step_is_explicit_update():
    k = torch.tensor(0.5)
    x = torch.tensor([2.0, 4.0])
    out = euler_step(_decay(k), x, t=0.0, dt=0.1)
    torch.testing.assert_close(out, x + 0.1 * (-k * x))


def test_rk4_far_more_accurate_than_euler():
    k = torch.tensor(1.0)
    x0 = torch.tensor([1.0])
    dt, n = 0.25, 40  # t_final = 10
    exact = x0 * math.exp(-k.item() * dt * n)
    x_euler = integrate(_decay(k), x0, dt, n, method="euler")
    x_rk4 = integrate(_decay(k), x0, dt, n, method="rk4")
    err_euler = (x_euler - exact).abs().item()
    err_rk4 = (x_rk4 - exact).abs().item()
    assert err_rk4 < err_euler / 100.0
    assert err_rk4 < 1e-4


def test_rk4_matches_analytic_solution():
    k = torch.tensor(0.3)
    x0 = torch.tensor([5.0])
    dt, n = 0.1, 100
    exact = x0 * math.exp(-k.item() * dt * n)
    x = integrate(_decay(k), x0, dt, n, method="rk4")
    torch.testing.assert_close(x, exact, rtol=1e-4, atol=1e-4)


def test_time_aware_forcing_evaluated_at_stage_times():
    """dx/dt = cos(t), x(0)=0 -> x(T)=sin(T). RK4 only nails this if the forcing
    is evaluated at the fractional stage times (not a per-step staircase)."""
    x0 = torch.zeros(1)

    def forced(t, x):
        return torch.full_like(x, math.cos(t))

    T_steps = 200
    dt = 0.05  # T = 10
    x = integrate(forced, x0, dt, T_steps, method="rk4")
    torch.testing.assert_close(x, torch.tensor([math.sin(10.0)]), rtol=1e-5, atol=1e-5)


def test_legacy_one_arg_tendency_still_works():
    """A legacy autonomous f(x) is transparently wrapped and integrates correctly."""
    x0 = torch.tensor([1.0])
    out = integrate(lambda x: -0.5 * x, x0, dt=0.1, n_steps=50, method="rk4")
    exact = x0 * math.exp(-0.5 * 0.1 * 50)
    torch.testing.assert_close(out, exact, rtol=1e-4, atol=1e-4)


def test_autograd_flows_through_rk4():
    k = torch.tensor(0.7, requires_grad=True)
    x0 = torch.tensor([1.0])
    x = integrate(_decay(k), x0, dt=0.2, n_steps=25, method="rk4")
    x.sum().backward()
    assert k.grad is not None and torch.isfinite(k.grad).all()
    assert k.grad.abs().item() > 0.0


def test_checkpointing_matches_dense_gradients():
    k = torch.tensor(0.6, requires_grad=True)
    x0 = torch.tensor([1.0, 2.0], requires_grad=True)

    dense = integrate(_decay(k), x0, dt=0.1, n_steps=50, method="rk4")
    dense.sum().backward()
    g_k_dense, g_x_dense = k.grad.clone(), x0.grad.clone()

    k.grad = None
    x0.grad = None
    ckpt = integrate(_decay(k), x0, dt=0.1, n_steps=50, method="rk4", checkpoint_segment=8)
    ckpt.sum().backward()

    torch.testing.assert_close(ckpt, dense, rtol=1e-6, atol=1e-6)
    torch.testing.assert_close(k.grad, g_k_dense, rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(x0.grad, g_x_dense, rtol=1e-5, atol=1e-6)


def test_snapshots_shape_and_final():
    k = torch.tensor(0.2)
    x0 = torch.tensor([1.0, 3.0])
    snaps = integrate(_decay(k), x0, dt=0.1, n_steps=10, method="rk4",
                      snapshot_indices=[2, 5, 10])
    assert snaps.shape == (3, 2)
    final = integrate(_decay(k), x0, dt=0.1, n_steps=10, method="rk4")
    torch.testing.assert_close(snaps[-1], final)


def test_relative_mass_drift_closed_system_is_tiny():
    def exchange(t, x):  # dA = -A + B, dB = A - B -> sum conserved
        A, B = x[0], x[1]
        return torch.stack([-A + B, A - B])

    x0 = torch.tensor([3.0, 1.0])
    xN = integrate(exchange, x0, dt=0.05, n_steps=200, method="rk4")
    assert relative_mass_drift(x0, xN).item() < 1e-4


def test_relative_mass_drift_with_weights():
    x0 = torch.tensor([2.0, 1.0])
    xN = torch.tensor([1.0, 2.0])
    w = torch.tensor([1.0, 0.0])
    drift = relative_mass_drift(x0, xN, weights=w)
    assert math.isclose(drift.item(), 0.5, rel_tol=1e-6)


def test_carroll6_euler_default_unchanged():
    """method='euler' must reproduce the historical per-step forward-Euler loop."""
    params = carroll6.CARROLL_VALUES.clone()
    state0 = torch.full((5,), 0.1)
    ref = state0.clone()
    for _ in range(200):
        ref = carroll6.carroll6_step(ref, params, dt=0.25)
    out = carroll6.carroll6_integrate(state0, params, dt=0.25, n_steps=200)  # default euler
    torch.testing.assert_close(out, ref, rtol=0.0, atol=0.0)


def test_carroll6_rk4_runs_finite_and_differs_from_euler():
    params = carroll6.CARROLL_VALUES.clone()
    state0 = torch.full((5,), 0.1)
    euler = carroll6.carroll6_integrate(state0, params, dt=0.25, n_steps=200, method="euler")
    rk4 = carroll6.carroll6_integrate(state0, params, dt=0.25, n_steps=200, method="rk4")
    assert torch.isfinite(rk4).all()
    assert (rk4 - euler).abs().max().item() > 0.0
