"""Regression test for the dt-scaled forward map in scripts/diffusion_emulator.py (#190).

Under ``--dt-scaled-residual`` the network emits a per-month tendency, so the forward
map is ``x + f(x) * dt_months`` (per-pair gap), matching train_regression. Before the
fix the diffusion path (residual target, EDM eval, quality ladder, final evaluate) used
the unscaled ``x + f(x)``, scoring a per-month tendency as a full-step correction. This
test pins the shared ``_forward_mu`` helper that all those sites now call.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

torch = pytest.importorskip("torch")

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import diffusion_emulator as de  # noqa: E402


def _const_fno(val):
    return lambda x: torch.full_like(x, val)


def test_forward_mu_applies_per_pair_dt_scaling():
    xt = torch.ones(2, 1, 3, 3)
    fno = _const_fno(0.5)  # constant per-month tendency of 0.5
    dt_months = torch.tensor([1.0, 3.0])  # pair 0 spans 1 month, pair 1 spans 3
    bt = torch.tensor([0, 1])
    mu = de._forward_mu(fno, xt, bt, dt_months, "cpu")
    # x + f(x) * dt: pair 0 -> 1 + 0.5*1 = 1.5 ; pair 1 -> 1 + 0.5*3 = 2.5
    assert torch.allclose(mu[0], torch.full((1, 3, 3), 1.5))
    assert torch.allclose(mu[1], torch.full((1, 3, 3), 2.5))


def test_forward_mu_none_is_unscaled_full_step():
    xt = torch.ones(2, 1, 3, 3)
    fno = _const_fno(0.5)
    bt = torch.tensor([0, 1])
    mu = de._forward_mu(fno, xt, bt, None, "cpu")
    # dt_months is None => x + f(x), bit-identical to the pre-flag behavior.
    assert torch.allclose(mu, torch.full_like(xt, 1.5))


def test_diffusion_residual_target_uses_scaled_map():
    # The diffusion model learns r = yt - mu; assert mu (hence r) is the dt-scaled map,
    # not the unscaled one, for a non-uniform-gap batch.
    xt = torch.ones(2, 1, 2, 2)
    yt = torch.zeros(2, 1, 2, 2)
    fno = _const_fno(0.5)
    dt_months = torch.tensor([1.0, 4.0])
    bt = torch.tensor([0, 1])
    mu = de._forward_mu(fno, xt, bt, dt_months, "cpu")
    r = yt - mu
    assert torch.allclose(r[0], torch.full((1, 2, 2), -1.5))  # 0 - (1 + 0.5*1)
    assert torch.allclose(r[1], torch.full((1, 2, 2), -3.0))  # 0 - (1 + 0.5*4)
    # and it must NOT equal the unscaled residual for the 4-month pair
    r_unscaled = yt - (xt + fno(xt))
    assert not torch.allclose(r[1], r_unscaled[1])
