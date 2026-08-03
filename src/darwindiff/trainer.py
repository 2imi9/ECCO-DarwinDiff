"""Windowed-BPTT trainer for Track-2 UDE closures on prescribed spatial transport.

This is the last piece of E2 infrastructure: fit a learned closure
(:class:`darwindiff.closures.EnvCalciteClosure` / :class:`~darwindiff.closures.ScavClosure`)
by rolling the spatial field out through :func:`darwindiff.transport.imex_rollout`
(prescribed velocities + forcing, mass-conserving, no vertical-CFL wall) and
backpropagating an observation loss to the closure's parameters.

**Windowed BPTT.** The rollout to (quasi-)steady state is long, so the backward pass
is memory-bounded two ways: (1) ``checkpoint_segment`` bounds a *single* backward's
activation memory (the default — full BPTT, exact gradient); (2) ``detach_window``
switches to **truncated** BPTT — roll ``detach_window`` steps with grad, apply the
loss, step the optimizer, detach the state, continue — for trajectories too long even
for checkpointing, or for time-resolved fits. Both ride the checkpoint-equivalence gate
already verified in ``transport.imex_rollout``.

**E2 controls, built in.** :func:`rollout_field` with a frozen closure gives the
**null-closure baseline** (the deep-review primary control: the learned closure must
beat it), and :func:`masked_r2` scores **held-out** cells (train/test split via masks) —
so the trainer measures the E2 quantity (does the learned closure add held-out skill
over a constant closure through the *identical* transport), not raw fit.

**Status:** the machinery is validated on a **synthetic self-twin** (recover a known
closure; held-out R^2 > 0). A real-data E2 *number* additionally needs DB-2 (v05
velocity) + DB-3 (held-out GEOTRACES/calcite obs) staged; those are the inputs here,
not part of the trainer.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import torch
from torch import nn

from darwindiff.transport import grid_tendency, imex_rollout

# An observable maps a field [..., Y, X, Z, tracer] -> a scored quantity [..., Y, X, Z]
# (e.g. DFe = f[..., 0]; PIC:POC = f[..., 4] / f[..., 3]).
Observable = Callable[[torch.Tensor], torch.Tensor]


def dfe_observable(field: torch.Tensor) -> torch.Tensor:
    """Dissolved-iron observable (tracer 0)."""
    return field[..., 0]


def picpoc_observable(field: torch.Tensor, eps: float = 1e-9) -> torch.Tensor:
    """PIC:POC rain-ratio observable (tracer 4 / tracer 3, floored)."""
    return field[..., 4] / field[..., 3].clamp_min(eps)


def masked_mse(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Mean squared error over the ``True`` cells of ``mask`` (the loss / score kernel)."""
    d = (pred - target)[mask]
    return (d * d).mean()


def masked_r2(pred: torch.Tensor, target: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Coefficient of determination over the ``True`` cells of ``mask``.

    ``1 - SS_res/SS_tot`` against the masked target's own mean. This is the **held-out**
    E2 metric when ``mask`` selects test cells excluded from training. Returns a 0-d
    tensor; ``-inf``-safe (SS_tot floored).
    """
    p, t = pred[mask], target[mask]
    ss_res = ((p - t) ** 2).sum()
    ss_tot = ((t - t.mean()) ** 2).sum().clamp_min(torch.finfo(t.dtype).tiny)
    return 1.0 - ss_res / ss_tot


@dataclass
class TransportConfig:
    """Prescribed-transport + numerics knobs passed to every rollout step.

    ``u``/``v`` horizontal velocities ``[Y, X]`` (or broadcastable); ``w`` per-interface
    vertical velocity (from ``transport.w_from_continuity``) or a scalar; ``dust``/
    ``light`` forcing (e.g. ``iron_forcing_loader.phi_dust_surface_field``); ``kz``/``kh``
    vertical/horizontal diffusivities; ``dz``/``dx``/``dy`` spacings; ``dt`` step (days).
    """

    dx: float
    dy: float
    dz: float = 10.0
    dt: float = 0.25
    kz: float = 0.1
    kh: float = 0.0
    u: torch.Tensor | float = 0.0
    v: torch.Tensor | float = 0.0
    w: torch.Tensor | float = 0.0
    dust: torch.Tensor | float | None = None
    light: torch.Tensor | float | None = None
    method: str = "rk4"


def _tendency(params, params_tc: TransportConfig, closures: dict):
    """Build the vdiff-free explicit tendency (imex adds vertical diffusion implicitly).

    ``horizontal_advection`` needs tensor ``u``/``v``; a scalar in the config (the
    "no prescribed horizontal flow" default) is materialized as a zero ``[Y, X]``
    field matching the state (``vertical_advection`` already handles a scalar ``w``).
    """
    tc = params_tc

    def tend(t: float, x: torch.Tensor) -> torch.Tensor:
        u, v = tc.u, tc.v
        if not torch.is_tensor(u):
            u = x.new_full((x.shape[-4], x.shape[-3]), float(u))
        if not torch.is_tensor(v):
            v = x.new_full((x.shape[-4], x.shape[-3]), float(v))
        return grid_tendency(
            x, params, u=u, v=v, dx=tc.dx, dy=tc.dy, kz=tc.kz, dz=tc.dz,
            w=tc.w, kh=tc.kh, bgc=True, include_vdiff=False,
            dust=tc.dust, light=tc.light, **closures,
        )

    return tend


def rollout_field(
    ic: torch.Tensor,
    params: torch.Tensor,
    tc: TransportConfig,
    n_steps: int,
    *,
    calcite_closure=None,
    scav_closure=None,
    ffe_closure=None,
    checkpoint_segment: int | None = None,
) -> torch.Tensor:
    """Roll the spatial field ``ic`` forward ``n_steps`` and return the final field.

    Composes ``grid_tendency`` (explicit, vdiff excluded) with implicit vertical
    diffusion via :func:`darwindiff.transport.imex_rollout`. Pass a *frozen* closure
    (e.g. constructed and never optimized, so it stays at its ``g==1`` anchor) to get
    the **null-closure baseline** field for the E2 control.
    """
    closures = {}
    if calcite_closure is not None:
        closures["calcite_closure"] = calcite_closure
    if scav_closure is not None:
        closures["scav_closure"] = scav_closure
    if ffe_closure is not None:
        closures["ffe_closure"] = ffe_closure
    tend = _tendency(params, tc, closures)
    return imex_rollout(
        tend, ic, dt=tc.dt, n_steps=n_steps, kz=tc.kz, dz=tc.dz,
        method=tc.method, checkpoint_segment=checkpoint_segment,
    )


@dataclass
class TrainResult:
    closure: nn.Module
    final_field: torch.Tensor
    history: list[dict] = field(default_factory=list)


def train_ude_closure(
    closure: nn.Module,
    ic: torch.Tensor,
    params: torch.Tensor,
    tc: TransportConfig,
    n_steps: int,
    *,
    observable: Observable,
    target: torch.Tensor,
    train_mask: torch.Tensor,
    val_mask: torch.Tensor | None = None,
    hook: str = "calcite_closure",
    epochs: int = 50,
    lr: float = 5e-2,
    weight_decay: float = 0.0,
    checkpoint_segment: int | None = None,
    detach_window: int | None = None,
    grad_clip: float | None = 1.0,
    log_every: int = 10,
    logger: Callable[[dict], None] | None = None,
) -> TrainResult:
    """Fit ``closure`` so the rolled-out field matches ``target`` on ``train_mask`` cells.

    ``observable`` maps the final field to the scored quantity (``dfe_observable`` /
    ``picpoc_observable``); ``target`` is the observed field of that quantity aligned to
    the grid; ``train_mask``/``val_mask`` are boolean ``[Y, X, Z]`` train/held-out splits.
    ``hook`` selects which ``grid_tendency`` closure slot the module fills
    (``"calcite_closure"``, ``"scav_closure"``, ``"ffe_closure"``).

    Windowing: with ``detach_window=None`` (default) each epoch is one **checkpointed
    full-BPTT** rollout with a terminal loss (exact gradient, memory bounded by
    ``checkpoint_segment``) — the right mode for a climatology steady-state fit. With
    ``detach_window=k`` it runs **truncated** BPTT for trajectories too long to hold even
    with checkpointing: roll the trajectory in detached ``k``-step windows and apply the
    loss + optimizer step **only on the final window** (the one ending at ``n_steps``),
    so the steady-state ``target`` is scored against a converged state, not an
    unconverged intermediate one. The gradient horizon is truncated to the last window,
    so recovery is weaker than full BPTT (a memory-vs-fidelity trade). A genuinely
    *time-resolved* fit would need a target trajectory (one target per window), not the
    single ``target`` tensor this API takes.

    Robustness: ``weight_decay`` is applied **only to the flexible MLP** parameters, not
    to a closure's physically-anchored scalars (``ScavClosure.raw_p`` anchors at a *nonzero*
    value, so decaying it toward 0 would fabricate a p-exponent signal; the scav rate
    ``log_r0`` is no longer trainable at all). A **structural-coupling guard** rejects a
    hook/observable pairing the closure
    cannot influence (e.g. ``calcite_closure`` vs ``dfe_observable`` — calcite never feeds
    DFe — which would otherwise train silently with zero gradient). A **finite guard**
    aborts (preserving the last-good parameters) and records ``aborted`` in history if the
    loss or a gradient goes non-finite, instead of the clip/step silently poisoning every
    parameter with NaN.

    Returns the trained closure, the final rolled-out field, and a per-log-epoch history
    of ``{epoch, train_loss, val_r2}``.
    """
    # weight_decay only on the flexible correction MLP; never on nonzero-anchored scalars.
    # `log_r0` stopped being a Parameter in 2026-08-02 (issue #217: it was a free level,
    # exactly redundant with `scav_rat`) so it no longer reaches named_parameters at all.
    anchored = {"raw_p"}
    decay_p, nodecay_p = [], []
    for name, p in closure.named_parameters():
        (nodecay_p if name in anchored else decay_p).append(p)
    opt = torch.optim.Adam(
        [{"params": decay_p, "weight_decay": weight_decay},
         {"params": nodecay_p, "weight_decay": 0.0}],
        lr=lr,
    )
    hook_kw = {hook: closure}
    result = TrainResult(closure=closure, final_field=ic, history=[])

    # Structural-coupling guard: the closure MUST be able to influence the observable,
    # else every gradient is exactly zero and training is a silent no-op.
    probe = rollout_field(ic, params, tc, min(4, n_steps), **hook_kw)
    g = torch.autograd.grad(
        observable(probe).sum(), list(closure.parameters()), allow_unused=True
    )
    if all(gi is None or float(gi.abs().sum()) == 0.0 for gi in g):
        raise ValueError(
            f"hook '{hook}' is structurally decoupled from the observable — no closure "
            f"parameter can influence it (e.g. calcite_closure only affects PIC/DIC/ALK "
            f"but dfe_observable reads DFe). Check the hook/observable pairing."
        )

    def _grads_finite() -> bool:
        return all(p.grad is None or torch.isfinite(p.grad).all() for p in closure.parameters())

    def record(epoch: int, train_loss: float, final: torch.Tensor, aborted: bool = False) -> None:
        entry = {"epoch": epoch, "train_loss": train_loss}
        if aborted:
            entry["aborted"] = True
        if val_mask is not None:
            with torch.no_grad():
                entry["val_r2"] = float(masked_r2(observable(final), target, val_mask))
        result.history.append(entry)
        if logger is not None:
            logger(entry)

    def step_from(loss: torch.Tensor) -> bool:
        """backward + finite-guard + clip + step. Returns False (abort) on non-finite."""
        if not torch.isfinite(loss):
            return False
        loss.backward()
        if not _grads_finite():
            opt.zero_grad(set_to_none=True)
            return False
        if grad_clip is not None:
            nn.utils.clip_grad_norm_(closure.parameters(), grad_clip)
        opt.step()
        return True

    aborted_epoch = None
    for epoch in range(epochs):
        if detach_window is None:  # checkpointed full BPTT, terminal loss
            opt.zero_grad()
            final = rollout_field(
                ic, params, tc, n_steps, checkpoint_segment=checkpoint_segment, **hook_kw
            )
            loss = masked_mse(observable(final), target, train_mask)
            if not step_from(loss):
                aborted_epoch = epoch
                break
            last_loss = float(loss.detach())
        else:  # truncated BPTT: detached spin-up windows, loss/step on the FINAL window
            state = ic.detach()
            n_win = (n_steps + detach_window - 1) // detach_window
            last_loss = float("nan")
            for w in range(n_win):
                k = min(detach_window, n_steps - w * detach_window)
                if w == n_win - 1:  # final window: converged state -> score + step
                    opt.zero_grad()
                    state = rollout_field(
                        state, params, tc, k, checkpoint_segment=checkpoint_segment, **hook_kw
                    )
                    loss = masked_mse(observable(state), target, train_mask)
                    if not step_from(loss):
                        aborted_epoch = epoch
                        break
                    last_loss = float(loss.detach())
                else:  # earlier windows: detached forward spin-up, no loss
                    with torch.no_grad():
                        state = rollout_field(state, params, tc, k, **hook_kw)
                state = state.detach()
            if aborted_epoch is not None:
                break
            final = state

        result.final_field = final.detach()
        if epoch % log_every == 0 or epoch == epochs - 1:
            record(epoch, last_loss, result.final_field)

    if aborted_epoch is not None:  # loud, sweep-visible failure; last-good params kept
        record(aborted_epoch, float("nan"), result.final_field, aborted=True)

    return result
