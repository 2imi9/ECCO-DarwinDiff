"""Model-agnostic, autograd-clean time integrators for the differentiable BGC.

Track-1 boxes step with naive forward-Euler, which is fine for the 200-step,
climatological fits in the paper but drifts badly over the long rollouts the
Track-2 (UDE / differentiable-Darwin) work needs: the feasibility probe
(`scripts/hybrid_feasibility_probe.py`, Test A) measured ~68% trajectory error
for forward-Euler versus ~0.02% for RK4 on the same closed system. This module
promotes that proven RK4 stepper into the package as a reusable option and adds
the two things decadal rollouts require: optional gradient checkpointing (so the
backward pass does not store every step's activations) and a mass-conservation
diagnostic for the make-or-break budget-closure check (tracker issue #7).

Everything here is model-agnostic: a caller supplies a *tendency function*
``f(state) -> dstate`` (the raw d(state)/dt, no timestep applied), and the
integrator handles the stepping. The tendency function closes over its own
parameters/forcing, so the same integrator serves the 0-D box, a 1-D column, or
a 3-D offline-transport field without change. State may be any shape; all
operations are elementwise, so ``[5]``, ``[C, Z, Y, X]``, etc. all work.
"""
from __future__ import annotations

from typing import Callable

import torch
from torch.utils.checkpoint import checkpoint

Tendency = Callable[[torch.Tensor], torch.Tensor]


def euler_step(f: Tendency, x: torch.Tensor, dt: float) -> torch.Tensor:
    """One explicit forward-Euler step: ``x + dt * f(x)``."""
    return x + dt * f(x)


def rk4_step(f: Tendency, x: torch.Tensor, dt: float) -> torch.Tensor:
    """One classical fourth-order Runge-Kutta step.

    Four tendency evaluations per step; ``O(dt^4)`` local error versus Euler's
    ``O(dt^2)``. Autograd flows cleanly through all four stages.
    """
    k1 = f(x)
    k2 = f(x + 0.5 * dt * k1)
    k3 = f(x + 0.5 * dt * k2)
    k4 = f(x + dt * k3)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


_STEP: dict[str, Callable[[Tendency, torch.Tensor, float], torch.Tensor]] = {
    "euler": euler_step,
    "rk4": rk4_step,
}


def _make_segment(
    step: Callable[[Tendency, torch.Tensor, float], torch.Tensor],
    f: Tendency,
    dt: float,
    k: int,
) -> Callable[[torch.Tensor], torch.Tensor]:
    """Build a closure that advances the state by ``k`` steps (for checkpointing)."""

    def segment(x: torch.Tensor) -> torch.Tensor:
        for _ in range(k):
            x = step(f, x, dt)
        return x

    return segment


def integrate(
    f: Tendency,
    x0: torch.Tensor,
    dt: float,
    n_steps: int,
    method: str = "rk4",
    snapshot_indices: list[int] | None = None,
    checkpoint_segment: int | None = None,
) -> torch.Tensor:
    """Integrate ``dx/dt = f(x)`` for ``n_steps`` of size ``dt``.

    Args:
        f: tendency function ``f(state) -> dstate`` (no timestep applied).
        x0: initial state, any shape.
        dt: time step (days, matching the box convention).
        n_steps: number of steps.
        method: ``"rk4"`` (default, recommended for long rollouts) or ``"euler"``.
        snapshot_indices: 1-indexed steps at which to stack a snapshot. If None,
            only the final state is returned. Ignored together with checkpointing
            (snapshots force full-graph retention within a segment anyway).
        checkpoint_segment: if set, wrap each block of this many steps in
            ``torch.utils.checkpoint`` so the backward pass recomputes rather than
            stores each block's activations. Bounds memory to O(segment) instead
            of O(n_steps) for decadal rollouts. Only honored when
            ``snapshot_indices`` is None.

    Returns:
        Final state (``snapshot_indices is None``) or the stacked snapshots
        (shape ``[len(snapshot_indices), *x0.shape]``).
    """
    if method not in _STEP:
        raise ValueError(f"unknown method {method!r}; expected one of {sorted(_STEP)}")
    step = _STEP[method]

    if snapshot_indices is None:
        x = x0
        if checkpoint_segment and checkpoint_segment > 0:
            i = 0
            while i < n_steps:
                k = min(checkpoint_segment, n_steps - i)
                seg = _make_segment(step, f, dt, k)
                # use_reentrant=False lets the segment close over grad-requiring
                # params (the tendency's weights) and still get their gradients.
                x = checkpoint(seg, x, use_reentrant=False)
                i += k
            return x
        for _ in range(n_steps):
            x = step(f, x, dt)
        return x

    wanted = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    x = x0
    for s in range(1, n_steps + 1):
        x = step(f, x, dt)
        if s in wanted:
            snaps.append(x)
    return torch.stack(snaps)


def relative_mass_drift(
    x0: torch.Tensor,
    xN: torch.Tensor,
    weights: torch.Tensor | None = None,
) -> torch.Tensor:
    """Relative drift of a conserved linear quantity between two states.

    For a *closed* system (no sources/sinks) a good integrator conserves the
    weighted total ``sum(weights * x)``; this returns
    ``|sum(w*xN) - sum(w*x0)| / |sum(w*x0)|``, which should sit near zero. In an
    open system (dust input, sinking export) apply it to the closed budget
    ``total + integrated_export - integrated_input`` instead. This is the reusable
    kernel of the decadal budget-closure check in tracker issue #7.

    Args:
        x0: initial state.
        xN: final state.
        weights: per-tracer weights (e.g. elemental content) broadcast over the
            tracer axis; defaults to all-ones (a plain sum).

    Returns:
        Scalar tensor: the relative drift magnitude.
    """
    if weights is None:
        m0, mN = x0.sum(), xN.sum()
    else:
        m0, mN = (weights * x0).sum(), (weights * xN).sum()
    return (mN - m0).abs() / m0.abs().clamp_min(torch.finfo(x0.dtype).tiny)
