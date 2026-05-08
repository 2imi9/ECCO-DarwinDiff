"""Tests for darwindiff.networks: CarrollMLP and CarrollCNN.

Smoke + shape + sanity tests. The networks are intentionally tiny; full recovery
validation lives in tests for the box model (test_carroll6_recovery.py) — these
just confirm the architectures plug together correctly.
"""

from __future__ import annotations

import torch

from darwindiff.carroll6 import PARAM_BOUNDS, bounded_params
from darwindiff.networks import CarrollCNN, CarrollMLP


def test_carroll_mlp_unbatched_shape() -> None:
    """Unbatched env [3] -> output [6]."""
    mlp = CarrollMLP()
    env = torch.zeros(3)
    out = mlp(env)
    assert out.shape == (6,)
    assert torch.isfinite(out).all()


def test_carroll_mlp_batched_shape() -> None:
    """Batched env [B, 3] -> output [B, 6]."""
    mlp = CarrollMLP()
    env = torch.zeros(4, 3)
    out = mlp(env)
    assert out.shape == (4, 6)
    assert torch.isfinite(out).all()


def test_carroll_mlp_default_param_count() -> None:
    """Default architecture: 3 -> 16 -> 6 = 144 weights, plus biases (16 + 6 = 22) = 166."""
    mlp = CarrollMLP()
    n_params = sum(p.numel() for p in mlp.parameters())
    # Linear(3, 16): 48 weights + 16 biases = 64
    # Linear(16, 6): 96 weights + 6 biases = 102
    # Total: 166
    assert n_params == 166, f"unexpected parameter count {n_params}"


def test_carroll_cnn_unbatched_shape() -> None:
    """Unbatched env [3, H, W] -> output [6, H, W]."""
    cnn = CarrollCNN()
    H, W = 32, 32
    env = torch.zeros(3, H, W)
    out = cnn(env)
    assert out.shape == (6, H, W)
    assert torch.isfinite(out).all()


def test_carroll_cnn_batched_shape() -> None:
    """Batched env [B, 3, H, W] -> output [B, 6, H, W]."""
    cnn = CarrollCNN()
    B, H, W = 2, 16, 16
    env = torch.zeros(B, 3, H, W)
    out = cnn(env)
    assert out.shape == (B, 6, H, W)
    assert torch.isfinite(out).all()


def test_carroll_cnn_is_per_cell() -> None:
    """1x1 convs mean each cell's output depends ONLY on its own inputs.

    Concretely: changing one cell's input must not affect any other cell's output.
    """
    cnn = CarrollCNN()
    H, W = 8, 8
    env_a = torch.randn(3, H, W)
    out_a = cnn(env_a)

    # Modify one specific cell.
    env_b = env_a.clone()
    env_b[:, 3, 4] += 5.0
    out_b = cnn(env_b)

    # Only cell (3, 4) should differ.
    diff = (out_a - out_b).abs()
    assert diff[:, 3, 4].max().item() > 0, "Modified cell should change in output."
    # Every other cell should be identical.
    mask = torch.ones(H, W, dtype=torch.bool)
    mask[3, 4] = False
    other_cells_diff = diff[:, mask].max().item()
    assert other_cells_diff < 1e-6, (
        f"1x1 convs should leave other cells unchanged; max other-cell diff was {other_cells_diff}."
    )


def test_carroll_cnn_with_bounded_params_2d() -> None:
    """End-to-end: CNN -> bounded_params(2-D) produces valid Carroll-6 maps."""
    cnn = CarrollCNN()
    H, W = 16, 16
    env = torch.randn(3, H, W)
    theta = cnn(env)                            # [6, H, W]
    params = bounded_params(theta, PARAM_BOUNDS)  # [6, H, W]

    assert params.shape == (6, H, W)
    # Every per-cell parameter must lie within its declared bounds.
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert (params[i] >= lo).all(), f"Param {i} below lower bound {lo}."
        assert (params[i] <= hi).all(), f"Param {i} above upper bound {hi}."


def test_carroll_mlp_with_bounded_params() -> None:
    """End-to-end: MLP -> bounded_params(scalar) produces valid Carroll-6 vectors."""
    mlp = CarrollMLP()
    env = torch.randn(3)
    theta = mlp(env)                            # [6]
    params = bounded_params(theta, PARAM_BOUNDS)  # [6]

    assert params.shape == (6,)
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert lo <= params[i].item() <= hi, (
            f"Param {i} = {params[i].item()} out of bounds [{lo}, {hi}]."
        )


def test_carroll_cnn_autograd_flows() -> None:
    """Backward through CNN + bounded_params produces gradients on every CNN weight."""
    cnn = CarrollCNN()
    env = torch.randn(3, 8, 8, requires_grad=False)
    theta = cnn(env)
    params = bounded_params(theta, PARAM_BOUNDS)
    params.sum().backward()
    for name, p in cnn.named_parameters():
        assert p.grad is not None, f"{name} received no gradient."
        assert torch.isfinite(p.grad).all(), f"{name} has non-finite gradient."


def test_bounded_params_batched_trailing_axis() -> None:
    """``[B, 6]`` with ``param_axis=-1`` works for batched MLP output (notebook 06 style).

    With ``theta = zeros``, every batch element should get the per-parameter
    midpoint value (since ``sigmoid(0) = 0.5``). Test catches the regression
    where ``[B, 6]`` either errors or silently broadcasts wrong.
    """
    B = 4
    theta = torch.zeros(B, 6)
    params = bounded_params(theta, PARAM_BOUNDS, param_axis=-1)
    assert params.shape == (B, 6)

    midpoints = 0.5 * (PARAM_BOUNDS[:, 0] + PARAM_BOUNDS[:, 1])
    for b in range(B):
        torch.testing.assert_close(params[b], midpoints, rtol=1e-6, atol=1e-9)


def test_bounded_params_batched_2d_cnn() -> None:
    """``[B, 6, H, W]`` with ``param_axis=1`` works for batched CNN output.

    Each per-parameter slice should be uniform across batch and spatial dims when
    ``theta`` is zeros (sigmoid midpoint behaviour).
    """
    B, H, W = 2, 8, 8
    theta = torch.zeros(B, 6, H, W)
    params = bounded_params(theta, PARAM_BOUNDS, param_axis=1)
    assert params.shape == (B, 6, H, W)

    for i in range(6):
        midpoint_i = (0.5 * (PARAM_BOUNDS[i, 0] + PARAM_BOUNDS[i, 1])).item()
        slice_i = params[:, i, :, :]
        assert torch.allclose(
            slice_i,
            torch.full_like(slice_i, midpoint_i),
            rtol=1e-6,
            atol=1e-9,
        ), f"Param {i} not uniform at midpoint {midpoint_i}."


def test_bounded_params_axis_mismatch_raises() -> None:
    """Specifying a ``param_axis`` whose size doesn't match ``bounds.shape[0]`` raises."""
    import pytest

    theta = torch.zeros(4, 6)
    # Default param_axis=0 picks dim 0 (size 4), which is not n_params=6.
    with pytest.raises(ValueError):
        bounded_params(theta, PARAM_BOUNDS)


def test_bounded_params_carroll_mlp_batched_end_to_end() -> None:
    """``CarrollMLP`` produces ``[B, 6]``; ``bounded_params(..., param_axis=-1)`` bounds it correctly."""
    mlp = CarrollMLP()
    B = 3
    env = torch.randn(B, 3)
    theta = mlp(env)               # [B, 6]
    params = bounded_params(theta, PARAM_BOUNDS, param_axis=-1)

    assert params.shape == (B, 6)
    # Every per-parameter value across the batch must lie in its declared bounds.
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert (params[:, i] >= lo).all(), f"Param {i} below lower bound {lo}."
        assert (params[:, i] <= hi).all(), f"Param {i} above upper bound {hi}."
