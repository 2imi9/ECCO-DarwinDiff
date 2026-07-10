"""Tests for the learned Track-2 closures (Phase 1)."""
from __future__ import annotations

import math

import torch
from torch import nn

from darwindiff.carroll6 import CARROLL_VALUES, K_FE, P
from darwindiff.closures import EnvCalciteClosure, ScavClosure
from darwindiff.integrators import integrate
from darwindiff.transport import column_tendency


def _state(C=4, Z=6, seed=0):
    g = torch.Generator().manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    return base * (1.0 + 0.1 * torch.rand(C, Z, 5, generator=g))


def _env(C=4, Z=6, n=3, seed=1):
    g = torch.Generator().manual_seed(seed)
    return torch.randn(C, Z, n, generator=g)  # standardised SST/Omega/PAR proxy


def test_env_calcite_baseline_byte_identical():
    """At init (zero-readout, g==1) with R0 = Carroll R_PICPOC, the closure
    byte-reproduces the constant-ratio baseline R_PICPOC * mort_total."""
    clo = EnvCalciteClosure(_env())  # R0 defaults to Carroll R_PICPOC
    mort = 0.1 + 0.2 * torch.rand(4, 6)
    r_picpoc = float(CARROLL_VALUES[P.R_PICPOC])
    torch.testing.assert_close(clo(_state(), mort), r_picpoc * mort, rtol=0.0, atol=0.0)


def test_env_calcite_envelope_bounded():
    """g_theta stays inside the log-symmetric band [10**-A, 10**A] for any weights."""
    clo = EnvCalciteClosure(_env(), A=1.0)
    torch.manual_seed(3)
    for p in clo.net.parameters():
        nn.init.normal_(p, std=2.0)  # non-trivial net, stress the bound
    g = clo.g(_state())
    assert g.min().item() >= 10.0 ** -1.0 - 1e-6
    assert g.max().item() <= 10.0 ** 1.0 + 1e-6


def test_env_calcite_trains_through_transport():
    """The closure gets finite, nonzero gradients through a checkpointed transport
    rollout -- Phase-1 trainability of the calcite hook."""
    params = CARROLL_VALUES.clone()
    state0 = _state(C=6, Z=6)
    clo = EnvCalciteClosure(_env(C=6, Z=6))

    def tend(s):
        return column_tendency(s, params, kz=0.1, dz=25.0, calcite_closure=clo)

    fN = integrate(tend, state0, dt=0.25, n_steps=80, method="rk4", checkpoint_segment=20)
    fN.pow(2).mean().backward()
    grads = [p.grad for p in clo.net.parameters()]
    assert all(g is not None and torch.isfinite(g).all() for g in grads)
    assert any(g.abs().sum().item() > 0.0 for g in grads)


# --- PR-3: scavenging iron sink closure -------------------------------------------


def test_scav_baseline_byte_identical():
    """At init (p==1, corr==1, r0=scav_rat_per_day*POC0) the closure reproduces the
    box sink scav_rat_per_day * DFe * POC (strict superset of the box law)."""
    clo = ScavClosure()
    assert abs(clo.p.item() - 1.0) < 1e-6
    dfe = 1.0e-4 * (0.5 + torch.rand(4, 6))
    poc = 0.1 + 0.5 * torch.rand(4, 6)
    scav_rat_per_day = float(CARROLL_VALUES[P.scav_rat]) * 86400.0
    torch.testing.assert_close(clo(dfe, poc), scav_rat_per_day * dfe * poc, rtol=1e-6, atol=0.0)


def test_scav_sink_nonneg_and_bounded_correction():
    """For any weights the sink is >=0 and its correction factor stays in
    [1-eps, 1+eps] (bounded deformation of the Parekh backbone)."""
    clo = ScavClosure(eps=0.2)
    torch.manual_seed(5)
    for p in clo.net.parameters():
        nn.init.normal_(p, std=3.0)
    dfe = 1.0e-4 * (0.5 + torch.rand(8, 8))
    poc = 0.1 + 0.5 * torch.rand(8, 8)
    sink = clo(dfe, poc)
    assert (sink >= 0.0).all()
    backbone = torch.exp(clo.log_r0) * (poc / clo.POC0).pow(clo.p) * dfe
    corr = sink / backbone
    assert corr.min().item() >= 1.0 - clo.eps - 1e-6
    assert corr.max().item() <= 1.0 + clo.eps + 1e-6


def test_scav_trains_through_transport():
    """The scavenging closure (rate r0, exponent p, and net) gets finite, nonzero
    gradients through a checkpointed transport rollout."""
    params = CARROLL_VALUES.clone()
    state0 = _state(C=6, Z=6)
    clo = ScavClosure()

    def tend(s):
        return column_tendency(s, params, kz=0.1, dz=25.0, scav_closure=clo)

    fN = integrate(tend, state0, dt=0.25, n_steps=80, method="rk4", checkpoint_segment=20)
    fN.pow(2).mean().backward()
    named = dict(clo.named_parameters())
    for g in (named["log_r0"].grad, named["raw_p"].grad):
        assert g is not None and torch.isfinite(g).all()
    assert any(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum().item() > 0.0
        for p in clo.parameters()
    )


# --- NaN/singularity regressions (from the PR-1/2/3 review) ------------------------


def test_env_calcite_finite_grad_at_negative_dfe():
    """A cell at DFe = -K_FE (reachable via advection overshoot) must not emit NaN
    gradients: the DFe>=0 clamp removes the f_lim pole. Forward looked finite even
    before the fix (tanh saturates) -- the failure was silent in backward."""
    clo = EnvCalciteClosure(_env(C=2, Z=3))
    torch.manual_seed(7)
    for p in clo.net.parameters():
        nn.init.normal_(p, std=1.0)  # live (nonzero) readout
    state = _state(C=2, Z=3).clone()
    state[..., 0] = -float(K_FE)  # sit exactly on the old pole
    state.requires_grad_(True)
    mort = 0.1 + 0.1 * torch.rand(2, 3)
    out = clo(state, mort)
    assert torch.isfinite(out).all()
    out.pow(2).sum().backward()
    assert torch.isfinite(state.grad).all()
    assert all(torch.isfinite(p.grad).all() for p in clo.net.parameters())


def test_scav_finite_grad_sublinear_p_at_zero_poc():
    """In the Parekh sublinear regime (p<1) the pow backbone must stay autograd-clean
    at POC=0 -- d/dp[pocn**p] and d/dPOC are singular there without the clamp."""
    clo = ScavClosure()
    with torch.no_grad():
        clo.raw_p.copy_(torch.tensor(math.log(math.exp(0.58) - 1.0)))  # softplus -> 0.58
    assert abs(clo.p.item() - 0.58) < 1e-4
    dfe = (1.0e-4 * (0.5 + torch.rand(4, 4))).requires_grad_(True)
    poc = torch.zeros(4, 4, requires_grad=True)  # POC == 0 everywhere
    sink = clo(dfe, poc)
    assert torch.isfinite(sink).all()
    sink.sum().backward()
    assert torch.isfinite(poc.grad).all() and torch.isfinite(dfe.grad).all()
    assert all(torch.isfinite(p.grad).all() for p in clo.parameters())


# --- formula-pinning gates (catch sign flips / wrong-channel wiring) ---------------


def test_env_calcite_g_formula_pinned():
    """Pin g_theta = 10**(A*tanh(a)): zero the readout weights and set bias b, so
    a==b everywhere and g == 10**(A*tanh(b)). A sign flip or wrong nonlinearity fails."""
    clo = EnvCalciteClosure(_env(), A=1.0)
    with torch.no_grad():
        clo.net[-1].weight.zero_()
        clo.net[-1].bias.fill_(0.7)
    g = clo.g(_state())
    expected = 10.0 ** (1.0 * math.tanh(0.7))
    torch.testing.assert_close(g, torch.full_like(g, expected))


def test_scav_corr_formula_pinned():
    """Pin corr = 1 + eps*tanh(a): zero readout weights, bias b -> corr == 1+eps*tanh(b).
    Catches the corr sign flip that survived the original gates."""
    clo = ScavClosure(eps=0.2)
    with torch.no_grad():
        clo.net[-1].weight.zero_()
        clo.net[-1].bias.fill_(0.5)
    dfe = 1.0e-4 * torch.ones(3, 3)
    poc = 0.5 * torch.ones(3, 3)
    sink = clo(dfe, poc)
    backbone = torch.exp(clo.log_r0) * (poc / clo.POC0).pow(clo.p) * dfe
    corr = sink / backbone
    expected = 1.0 + 0.2 * math.tanh(0.5)
    torch.testing.assert_close(corr, torch.full_like(corr, expected))
