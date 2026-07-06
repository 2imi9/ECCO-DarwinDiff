"""Tests for the UDE closure hook (carroll6_ude_tendency) — Track 2 foundation."""
from __future__ import annotations

import torch
from torch import nn

from darwindiff import carroll6

_STATE = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])


def test_ude_default_is_byte_identical_to_mechanistic():
    """With no closures, the UDE tendency must equal the plain tendency exactly."""
    params = carroll6.CARROLL_VALUES.clone()
    mech = carroll6.carroll6_tendency(_STATE, params)
    ude = carroll6.carroll6_ude_tendency(_STATE, params)
    torch.testing.assert_close(ude, mech, rtol=0.0, atol=0.0)


def test_ude_ffe_closure_flows_gradients_to_network():
    """A neural iron-limitation closure must be trainable end-to-end through the box."""
    params = carroll6.CARROLL_VALUES.clone()
    net = nn.Sequential(nn.Linear(1, 8), nn.Tanh(), nn.Linear(8, 1), nn.Sigmoid())

    def ffe(dfe: torch.Tensor) -> torch.Tensor:
        return net(dfe.reshape(1)).reshape(())

    out = carroll6.carroll6_ude_tendency(_STATE, params, ffe_closure=ffe)
    assert torch.isfinite(out).all()
    out.sum().backward()
    grads = [p.grad for p in net.parameters()]
    assert all(g is not None and torch.isfinite(g).all() for g in grads)
    assert any(g.abs().sum().item() > 0.0 for g in grads)


def test_ude_calcite_closure_overrides_only_pic():
    """A learned calcification closure must change dPIC and nothing else."""
    params = carroll6.CARROLL_VALUES.clone()
    base = carroll6.carroll6_ude_tendency(_STATE, params)

    def calcite(state: torch.Tensor, mort_total: torch.Tensor) -> torch.Tensor:
        return 5.0 * mort_total  # deliberately different from R_PICPOC * mort_total

    out = carroll6.carroll6_ude_tendency(_STATE, params, calcite_closure=calcite)
    assert not torch.isclose(out[4], base[4])            # dPIC changed
    torch.testing.assert_close(out[:4], base[:4], rtol=0.0, atol=0.0)  # rest untouched


def test_ude_integrates_with_rk4():
    """The UDE tendency plugs into the generic integrator (RK4) and stays finite."""
    from darwindiff.integrators import integrate

    params = carroll6.CARROLL_VALUES.clone()
    net = nn.Sequential(nn.Linear(1, 4), nn.Tanh(), nn.Linear(4, 1), nn.Sigmoid())

    def tend(s: torch.Tensor) -> torch.Tensor:
        return carroll6.carroll6_ude_tendency(
            s, params, ffe_closure=lambda d: net(d.reshape(1)).reshape(())
        )

    out = integrate(tend, _STATE, dt=0.25, n_steps=200, method="rk4")
    assert out.shape == (5,)
    assert torch.isfinite(out).all()
