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

Tendencies are **time-aware**: ``f(t, x) -> dstate`` where ``t`` is the (Python
float) simulated time in days, so time-varying forcing (seasonal light/dust,
transient pulses) can drive the model and RK4 evaluates the forcing at the exact
fractional stage times ``t, t+dt/2, t+dt/2, t+dt`` -- required to keep the
O(dt^4) accuracy. Legacy autonomous 1-arg tendencies ``f(x)`` are still accepted
and transparently wrapped, so every Track-1 caller keeps working unchanged.

State may be any shape; all operations are elementwise, so ``[5]``,
``[C, Z, Y, X]``, etc. all work.
"""
from __future__ import annotations

import inspect
from typing import Callable

import torch
from torch.utils.checkpoint import checkpoint

Tendency = Callable[[float, torch.Tensor], torch.Tensor]


def _as_time_aware(f: Callable) -> Tendency:
    """Accept a legacy autonomous tendency ``f(x)`` and wrap it as ``f(t, x)``.

    Detection counts required positional parameters; a 1-arg callable is wrapped
    so its result is time-independent. A 2-arg callable is used as-is.
    """
    try:
        required = [
            p for p in inspect.signature(f).parameters.values()
            if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            and p.default is p.empty
        ]
        n = len(required)
    except (TypeError, ValueError):
        n = 2  # builtins / C-callables: assume already time-aware
    if n <= 1:
        g = f
        return lambda t, x: g(x)
    return f


def euler_step(f: Tendency, x: torch.Tensor, t: float, dt: float) -> torch.Tensor:
    """One explicit forward-Euler step: ``x + dt * f(t, x)``."""
    return x + dt * f(t, x)


def rk4_step(f: Tendency, x: torch.Tensor, t: float, dt: float) -> torch.Tensor:
    """One classical fourth-order Runge-Kutta step, forcing evaluated at the
    stage times ``t, t+dt/2, t+dt/2, t+dt``."""
    k1 = f(t, x)
    k2 = f(t + 0.5 * dt, x + 0.5 * dt * k1)
    k3 = f(t + 0.5 * dt, x + 0.5 * dt * k2)
    k4 = f(t + dt, x + dt * k3)
    return x + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)


_STEP: dict[str, Callable[[Tendency, torch.Tensor, float, float], torch.Tensor]] = {
    "euler": euler_step,
    "rk4": rk4_step,
}


def _make_segment(step, f: Tendency, dt: float, k: int, t0: float):
    """Closure advancing ``k`` steps from time ``t0`` (for checkpointing).

    ``t0`` is passed in (not accumulated across segments) so the recomputed times
    under ``torch.utils.checkpoint`` are bit-identical to the forward pass.
    """
    def segment(x: torch.Tensor) -> torch.Tensor:
        t = t0
        for _ in range(k):
            x = step(f, x, t, dt)
            t += dt
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
    t0: float = 0.0,
) -> torch.Tensor:
    """Integrate ``dx/dt = f(t, x)`` for ``n_steps`` of size ``dt``.

    ``f`` may be time-aware (``f(t, x)``) or a legacy autonomous ``f(x)`` (wrapped
    automatically). ``t0`` is the start time in days. Other args as before:
    ``method`` in {"rk4", "euler"}; ``snapshot_indices`` (1-indexed) to stack
    snapshots; ``checkpoint_segment`` to bound backward memory (honored only when
    ``snapshot_indices`` is None).
    """
    if method not in _STEP:
        raise ValueError(f"unknown method {method!r}; expected one of {sorted(_STEP)}")
    step = _STEP[method]
    f = _as_time_aware(f)

    if snapshot_indices is None:
        x = x0
        if checkpoint_segment and checkpoint_segment > 0:
            i, t = 0, t0
            while i < n_steps:
                k = min(checkpoint_segment, n_steps - i)
                seg = _make_segment(step, f, dt, k, t)
                x = checkpoint(seg, x, use_reentrant=False)
                i += k
                t += k * dt
            return x
        t = t0
        for _ in range(n_steps):
            x = step(f, x, t, dt)
            t += dt
        return x

    wanted = set(snapshot_indices)
    snaps: list[torch.Tensor] = []
    x, t = x0, t0
    for s in range(1, n_steps + 1):
        x = step(f, x, t, dt)
        t += dt
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
    """
    if weights is None:
        m0, mN = x0.sum(), xN.sum()
    else:
        m0, mN = (weights * x0).sum(), (weights * xN).sum()
    return (mN - m0).abs() / m0.abs().clamp_min(torch.finfo(x0.dtype).tiny)
