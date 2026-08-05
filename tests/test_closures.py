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
    """For any weights the sink is >=0 and its shape factor stays bounded.

    The bound widened when G became mean-centred (issue #217): G = corr / gm with both
    corr and the reference geometric mean gm in [1-eps, 1+eps], so
    G in [(1-eps)/(1+eps), (1+eps)/(1-eps)]. Still a bounded, strictly positive
    deformation of the Parekh backbone, which is what keeps the sink a proper loss term.
    """
    clo = ScavClosure(eps=0.2)
    torch.manual_seed(5)
    for p in clo.net.parameters():
        nn.init.normal_(p, std=3.0)
    dfe = 1.0e-4 * (0.5 + torch.rand(8, 8))
    poc = 0.1 + 0.5 * torch.rand(8, 8)
    sink = clo(dfe, poc)
    assert (sink >= 0.0).all()
    backbone = math.exp(clo.log_r0) * (poc / clo.POC0).pow(clo.p) * dfe
    corr = sink / backbone
    lo = (1.0 - clo.eps) / (1.0 + clo.eps)
    hi = (1.0 + clo.eps) / (1.0 - clo.eps)
    assert corr.min().item() >= lo - 1e-6
    assert corr.max().item() <= hi + 1e-6


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
    # log_r0 is deliberately absent: it is a fixed level, not a Parameter (issue #217).
    assert "log_r0" not in named
    g = named["raw_p"].grad
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


def test_a_constant_readout_is_normalised_away():
    """A constant correction is a multiplicative LEVEL, and the level belongs to scav_rat.

    Zero readout weights with bias b used to give corr == 1 + eps*tanh(b), i.e. a uniform
    rescaling of the sink -- exactly the free level that made `scav_rat` non-identifiable
    by construction (issue #217). Mean-centring in log space maps every constant to 1, so
    the gauge direction is no longer reachable by any weight setting.
    """
    clo = ScavClosure(eps=0.2)
    dfe = 1.0e-4 * torch.ones(3, 3)
    poc = 0.5 * torch.ones(3, 3)
    backbone = math.exp(clo.log_r0) * (poc / clo.POC0).pow(clo.p) * dfe
    for b in (0.5, -1.3, 2.0):
        with torch.no_grad():
            clo.net[-1].weight.zero_()
            clo.net[-1].bias.fill_(b)
        corr = clo(dfe, poc) / backbone
        torch.testing.assert_close(corr, torch.ones_like(corr), rtol=1e-6, atol=1e-7)


def test_scav_corr_formula_pinned():
    """Pin the SHAPE: G is the bounded correction divided by its reference geometric mean.

    Catches the corr sign flip that survived the original gates. Uses a non-constant
    readout, because a constant one is now normalised away by construction.
    """
    clo = ScavClosure(eps=0.2)
    with torch.no_grad():
        clo.net[-1].weight.zero_()
        clo.net[-1].weight[0, 1] = 0.9      # respond to f2 = log10(POC/POC0) only
        clo.net[-1].bias.fill_(0.3)
    dfe = 1.0e-4 * torch.ones(4)
    poc = clo.POC0 * torch.tensor([0.25, 0.5, 2.0, 4.0])

    # by hand: a = 0.9 * tanh_hidden_out + 0.3 is what the net computes; instead of
    # reimplementing the hidden layer, pin G against _corr, which is the pinned formula.
    f1 = torch.log10(dfe) + 4.0
    f2 = torch.log10(poc / clo.POC0)
    feat = torch.stack([f1, f2], dim=-1)
    raw = 1.0 + clo.eps * torch.tanh(clo.net(feat).squeeze(-1))
    gm = torch.exp(torch.log(clo._corr(clo.ref_feat)).mean())
    backbone = math.exp(clo.log_r0) * (poc / clo.POC0).pow(clo.p) * dfe

    torch.testing.assert_close(clo(dfe, poc) / backbone, raw / gm)
    assert not torch.allclose(raw, raw[0].expand_as(raw)), "readout must vary for this test"


def test_scav_G_is_exactly_one_at_init():
    """Acceptance criterion (#217): G == 1 bitwise at init, so the closure reproduces the
    bilinear sink and the untrained null is exact rather than approximate.

    Bitwise, not approximately: the readout is zero-initialised so _corr is exactly 1.0,
    log of that is exactly 0.0, the mean of zeros is exactly 0.0, and exp(0) is exactly 1.
    """
    for env in (None, torch.randn(6, 3)):
        clo = ScavClosure(env=env, eps=0.2)
        feat = torch.randn(6, 2 if env is None else 5)
        G = clo.G(feat)
        assert torch.equal(G, torch.ones_like(G)), "G must be bitwise 1 at initialisation"


def test_scav_has_no_free_multiplicative_level():
    """Acceptance criterion (#217): the gauge is CLOSED.

    Scaling the whole sink by a constant lambda != 1 must not be achievable by any weight
    setting. Two independent checks:

    1. No parameter named `log_r0` exists -- the level is a fixed float, not learnable.
    2. Search over readout biases (the only way a bounded tanh net can emit a constant):
       every one of them leaves the sink unchanged, so the orbit has been removed rather
       than merely re-parameterised.
    """
    clo = ScavClosure(eps=0.2)
    assert "log_r0" not in dict(clo.named_parameters())
    assert isinstance(clo.log_r0, float)

    dfe = 1.0e-4 * (0.5 + torch.rand(5, 5))
    poc = 0.1 + 0.5 * torch.rand(5, 5)
    with torch.no_grad():
        clo.net[-1].weight.zero_()
        clo.net[-1].bias.zero_()
    base = clo(dfe, poc).clone()
    for b in (-2.0, -0.4, 0.4, 2.0):
        with torch.no_grad():
            clo.net[-1].bias.fill_(b)
        torch.testing.assert_close(clo(dfe, poc), base, rtol=1e-6, atol=0.0)


def test_scav_reference_support_is_fixed_not_per_batch():
    """The normaliser must not depend on the data the closure is evaluated on.

    A batch-dependent mean would make the closure's meaning a function of its evaluation
    set, so two identical states in different batches would scavenge differently.
    """
    clo = ScavClosure(eps=0.2)
    torch.manual_seed(11)
    for p in clo.net.parameters():
        nn.init.normal_(p, std=2.0)
    dfe = 1.0e-4 * torch.tensor([[1.0, 2.0, 3.0]])
    poc = clo.POC0 * torch.tensor([[0.5, 1.0, 2.0]])
    alone = clo(dfe[:, :1], poc[:, :1])
    together = clo(dfe, poc)[:, :1]
    torch.testing.assert_close(alone, together, rtol=1e-6, atol=0.0)
