"""Carroll-2020 6-parameter box-model tests.

Validates the differentiable scaffold for the exact six parameters Carroll et al. 2020
(JAMES) tuned via Green's functions: smoke test for stable forward integration, autograd
flow to all six knobs, and bounded-parameter mapping behaviour. End-to-end recovery
against synthetic observations was removed when the project transitioned to real-data
fits — recovery quality on real ECCO-Darwin v5 output is now exercised by the notebooks
that load real data, not by unit tests.
"""

from __future__ import annotations

import torch

from darwindiff.carroll6 import (
    CARROLL_VALUES,
    PARAM_BOUNDS,
    PARAM_NAMES,
    bounded_params,
    carroll6_integrate,
    carroll6_step,
)


def _fixture() -> tuple[torch.Tensor, float, int, list[int]]:
    """Same physical setup as notebook 05: 50-day spin-up at dt=0.25 d, 5 snapshots."""
    state0 = torch.tensor([5.0e-4, 1.0, 1.0, 0.5, 0.025])  # DFe, Ps, Pl, POC, PIC
    dt = 0.25
    n_steps = 200
    snapshot_indices = [40, 80, 120, 160, 200]
    return state0, dt, n_steps, snapshot_indices


def test_carroll6_step_runs_and_is_finite() -> None:
    """Smoke test: a single step on the Carroll truth produces finite tracers."""
    state0, dt, _n, _s = _fixture()
    state_next = carroll6_step(state0, CARROLL_VALUES, dt)
    assert state_next.shape == state0.shape
    assert torch.isfinite(state_next).all()
    assert (state_next > 0).all(), "All tracers should remain positive after one step."


def test_carroll6_integration_stable_at_truth() -> None:
    """200 forward-Euler steps at Carroll's published optimum reach a finite state."""
    state0, dt, n_steps, snapshot_indices = _fixture()
    with torch.no_grad():
        traj = carroll6_integrate(
            state0=state0, params=CARROLL_VALUES, dt=dt,
            n_steps=n_steps, snapshot_indices=snapshot_indices,
        )
    assert traj.shape == (len(snapshot_indices), 5)
    assert torch.isfinite(traj).all()
    assert (traj > 0).all(), "All tracers should remain positive through the trajectory."


def test_carroll6_autograd_flows_to_all_six() -> None:
    """Gradient flows from the final state back to all six learnable parameters."""
    state0, dt, n_steps, snapshot_indices = _fixture()
    theta = torch.zeros(6, requires_grad=True)
    params = bounded_params(theta, PARAM_BOUNDS)
    traj = carroll6_integrate(
        state0=state0, params=params, dt=dt,
        n_steps=n_steps, snapshot_indices=snapshot_indices,
    )
    traj.sum().backward()
    assert theta.grad is not None
    assert torch.isfinite(theta.grad).all()
    # Every parameter must receive a non-trivial gradient — none should be exactly zero,
    # which would indicate the parameter is structurally absent from the loss path.
    for i, name in enumerate(PARAM_NAMES):
        assert theta.grad[i].abs().item() > 0, (
            f"Parameter {name} (index {i}) received zero gradient — autograd path broken."
        )


def test_bounded_params_respects_ranges() -> None:
    """sigmoid-bounded parameter mapping stays within the declared physical ranges."""
    # theta sweeping a wide range tests the saturation behavior at both ends.
    for theta_val in [-10.0, -5.0, 0.0, 5.0, 10.0]:
        theta = torch.full((6,), theta_val)
        params = bounded_params(theta, PARAM_BOUNDS)
        for i in range(6):
            lo = PARAM_BOUNDS[i, 0].item()
            hi = PARAM_BOUNDS[i, 1].item()
            assert lo <= params[i].item() <= hi, (
                f"Parameter {PARAM_NAMES[i]} = {params[i].item()} out of bounds [{lo}, {hi}]."
            )
