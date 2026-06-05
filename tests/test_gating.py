"""Tests for darwindiff.gating: per-AOI parameter gradient routing (Stage 1).

CPU-only, tiny tensors. No GPU, no training -- these validate the gradient-mask
mechanism and the policy bookkeeping in isolation from the (heavy) runner.
"""

from __future__ import annotations

import pytest
import torch

from darwindiff.carroll6 import PARAM_NAMES
from darwindiff.gating import (
    apply_gate,
    build_gate_vectors,
    resolve_policy,
    validate_policy,
)


def test_apply_gate_forward_identity() -> None:
    """Gated output values equal the input exactly, for any gate."""
    params = torch.randn(6, 3, 4, 5)
    for gate in (torch.ones(6), torch.zeros(6), torch.tensor([1.0, 0, 1, 0, 1, 0])):
        out = apply_gate(params, gate)
        torch.testing.assert_close(out, params, rtol=0, atol=0)


def test_apply_gate_routes_gradient() -> None:
    """Gradient reaches only the routed parameter channels."""
    theta = torch.randn(6, 4, 4, requires_grad=True)
    gate = torch.tensor([1.0, 0.0, 1.0, 0.0, 0.0, 1.0])
    apply_gate(theta, gate).sum().backward()
    grad_per_param = theta.grad.abs().flatten(1).sum(dim=1)  # [6]
    routed = gate.bool()
    assert (grad_per_param[routed] > 0).all()
    assert torch.count_nonzero(grad_per_param[~routed]) == 0


def test_ungated_gate_is_gradient_noop() -> None:
    """An all-ones gate reproduces the ungated gradient bitwise."""
    theta1 = torch.randn(6, 5, requires_grad=True)
    theta2 = theta1.detach().clone().requires_grad_(True)
    theta1.sum().backward()
    apply_gate(theta2, torch.ones(6)).sum().backward()
    torch.testing.assert_close(theta1.grad, theta2.grad, rtol=0, atol=0)


def test_apply_gate_matches_baseline_loss_value() -> None:
    """A scalar loss on gated params equals the ungated loss (forward identity)."""
    params = torch.randn(6, 8).abs() + 0.1
    gate = torch.tensor([1.0, 0.0, 1.0, 0.0, 1.0, 0.0])
    torch.testing.assert_close((apply_gate(params, gate) ** 2).sum(), (params**2).sum())


def test_apply_gate_shape_mismatch_raises() -> None:
    with pytest.raises(ValueError):
        apply_gate(torch.randn(5, 3), torch.ones(6))


def test_build_gate_vectors_ungated_all_ones() -> None:
    vecs = build_gate_vectors({}, ["eqpac", "natlsubpolar"])
    for v in vecs.values():
        assert v.shape == (6,)
        assert torch.equal(v, torch.ones(6))


def test_build_gate_vectors_signal_2aoi_partition() -> None:
    """The two AOIs together route each parameter exactly once."""
    policy = resolve_policy("signal_2aoi")
    aoi_keys = ["eqpac", "natlsubpolar"]
    vecs = build_gate_vectors(policy, aoi_keys)
    total = sum(vecs[k] for k in aoi_keys)
    torch.testing.assert_close(total, torch.ones(6))


def test_signal_presets_cover_all_params() -> None:
    for name in ("signal_2aoi", "signal_3aoi"):
        policy = resolve_policy(name)
        routed = {p for ps in policy.values() for p in ps}
        assert routed == set(PARAM_NAMES), f"{name} does not cover all 6 params"


def test_resolve_policy_preset_json_and_dict() -> None:
    assert resolve_policy("ungated") == {}
    j = (
        '{"eqpac": ["alpfe"], '
        '"natlsubpolar": ["scav_rat","Smallgrow","Biggrow","diatomgraz","R_PICPOC"]}'
    )
    assert resolve_policy(j)["eqpac"] == ["alpfe"]
    d = {"eqpac": ["alpfe"]}
    out = resolve_policy(d)
    assert out == d and out is not d  # shallow copy, not aliased


def test_resolve_policy_bad_spec_raises() -> None:
    with pytest.raises(ValueError):
        resolve_policy("not_a_preset_or_json")


def test_validate_policy_unknown_aoi_raises() -> None:
    policy = resolve_policy("signal_3aoi")  # references southernoceanpac
    with pytest.raises(ValueError, match="not in this run"):
        validate_policy(policy, ["eqpac", "natlsubpolar"])


def test_validate_policy_orphaned_param_raises() -> None:
    policy = {"eqpac": ["alpfe"], "natlsubpolar": ["scav_rat"]}  # 4 params missing
    with pytest.raises(ValueError, match="un-routed"):
        validate_policy(policy, ["eqpac", "natlsubpolar"])


def test_validate_policy_unknown_param_raises() -> None:
    policy = {"eqpac": ["not_a_param", *PARAM_NAMES]}
    with pytest.raises(ValueError, match="unknown parameter"):
        validate_policy(policy, ["eqpac"])


def test_validate_ungated_passes() -> None:
    validate_policy({}, ["eqpac"])  # must not raise
