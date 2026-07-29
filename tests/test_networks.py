"""Tests for darwindiff.networks: DINN and DINNRegional.

Smoke + shape + sanity tests. The networks are intentionally tiny; full recovery
validation lives in tests for the box model (test_carroll6_recovery.py) — these
just confirm the architectures plug together correctly.
"""

from __future__ import annotations

import pytest
import torch

from darwindiff.carroll6 import N_PARAMS, PARAM_BOUNDS, bounded_params
from darwindiff.networks import (
    DINN,
    DINNDeep,
    DINNRegional,
    GlobalScalarNet,
    PerCellFreeField,
)


def test_dinn_regional_unbatched_shape() -> None:
    """Unbatched env [3] -> output [6]."""
    mlp = DINNRegional()
    env = torch.zeros(3)
    out = mlp(env)
    assert out.shape == (6,)
    assert torch.isfinite(out).all()


def test_dinn_regional_batched_shape() -> None:
    """Batched env [B, 3] -> output [B, 6]."""
    mlp = DINNRegional()
    env = torch.zeros(4, 3)
    out = mlp(env)
    assert out.shape == (4, 6)
    assert torch.isfinite(out).all()


def test_dinn_regional_default_param_count() -> None:
    """Default architecture: 3 -> 16 -> 6 plus biases (16 + 6) = 166 weights."""
    mlp = DINNRegional()
    n_params = sum(p.numel() for p in mlp.parameters())
    # Linear(3, 16): 48 weights + 16 biases = 64
    # Linear(16, 6): 96 weights + 6 biases = 102
    # Total: 166
    assert n_params == 166, f"unexpected parameter count {n_params}"


def test_dinn_unbatched_shape() -> None:
    """Unbatched env [3, H, W] -> output [6, H, W]."""
    cnn = DINN()
    H, W = 32, 32
    env = torch.zeros(3, H, W)
    out = cnn(env)
    assert out.shape == (6, H, W)
    assert torch.isfinite(out).all()


def test_dinn_batched_shape() -> None:
    """Batched env [B, 3, H, W] -> output [B, 6, H, W]."""
    cnn = DINN()
    B, H, W = 2, 16, 16
    env = torch.zeros(B, 3, H, W)
    out = cnn(env)
    assert out.shape == (B, 6, H, W)
    assert torch.isfinite(out).all()


def test_dinn_is_per_cell() -> None:
    """1x1 convs mean each cell's output depends ONLY on its own inputs.

    Concretely: changing one cell's input must not affect any other cell's output.
    This test catches anyone accidentally bumping the kernel size beyond 1x1.
    """
    cnn = DINN()
    H, W = 8, 8
    env_a = torch.randn(3, H, W)
    out_a = cnn(env_a)

    # Modify one specific cell.
    env_b = env_a.clone()
    env_b[:, 3, 4] += 5.0
    out_b = cnn(env_b)

    diff = (out_a - out_b).abs()
    assert diff[:, 3, 4].max().item() > 0, "Modified cell should change in output."
    mask = torch.ones(H, W, dtype=torch.bool)
    mask[3, 4] = False
    other_cells_diff = diff[:, mask].max().item()
    assert other_cells_diff < 1e-6, (
        f"1x1 convs should leave other cells unchanged; max other-cell diff "
        f"was {other_cells_diff}."
    )


def test_dinn_with_bounded_params_2d() -> None:
    """End-to-end: DINN -> bounded_params(2-D) produces valid Carroll-6 maps."""
    cnn = DINN()
    H, W = 16, 16
    env = torch.randn(3, H, W)
    theta = cnn(env)                            # [6, H, W]
    params = bounded_params(theta, PARAM_BOUNDS)  # [6, H, W]

    assert params.shape == (6, H, W)
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert (params[i] >= lo).all(), f"Param {i} below lower bound {lo}."
        assert (params[i] <= hi).all(), f"Param {i} above upper bound {hi}."


def test_dinn_regional_with_bounded_params() -> None:
    """End-to-end: DINNRegional -> bounded_params(scalar) produces valid Carroll-6 vectors."""
    mlp = DINNRegional()
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


def test_dinn_autograd_flows() -> None:
    """Backward through DINN + bounded_params produces gradients on every weight."""
    cnn = DINN()
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
    theta = torch.zeros(4, 6)
    with pytest.raises(ValueError):
        bounded_params(theta, PARAM_BOUNDS)


def test_bounded_params_dinn_regional_batched_end_to_end() -> None:
    """``DINNRegional`` produces ``[B, 6]``; ``bounded_params(..., param_axis=-1)`` bounds it correctly."""
    mlp = DINNRegional()
    B = 3
    env = torch.randn(B, 3)
    theta = mlp(env)               # [B, 6]
    params = bounded_params(theta, PARAM_BOUNDS, param_axis=-1)

    assert params.shape == (B, 6)
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert (params[:, i] >= lo).all(), f"Param {i} below lower bound {lo}."
        assert (params[:, i] <= hi).all(), f"Param {i} above upper bound {hi}."


# ---------------------------------------------------------------------------
# DINNDeep — upgraded per-cell network (multi-channel, deeper, residual)
# ---------------------------------------------------------------------------


def test_dinn_deep_unbatched_shape() -> None:
    """Unbatched env [4, H, W] -> output [6, H, W]."""
    net = DINNDeep(n_input_channels=4, hidden_dim=32, n_outputs=6, n_blocks=4)
    env = torch.randn(4, 21, 31)
    out = net(env)
    assert out.shape == (6, 21, 31)
    assert torch.isfinite(out).all()


def test_dinn_deep_batched_shape() -> None:
    """Batched env [B, C, H, W] -> output [B, 6, H, W]."""
    net = DINNDeep(n_input_channels=4, hidden_dim=32, n_outputs=6, n_blocks=4)
    env = torch.randn(2, 4, 21, 31)
    out = net(env)
    assert out.shape == (2, 6, 21, 31)


def test_dinn_deep_is_per_cell() -> None:
    """1x1 conv backbone means each cell is processed independently — no
    spatial coupling. Verify by perturbing one cell's input and checking
    only that cell's output changes (within the same batch / channel).
    """
    torch.manual_seed(0)
    net = DINNDeep(n_input_channels=4, hidden_dim=16, n_outputs=6, n_blocks=2)
    env_a = torch.randn(4, 8, 8)
    env_b = env_a.clone()
    env_b[:, 3, 5] += 5.0  # perturb only cell (3, 5)
    out_a = net(env_a)
    out_b = net(env_b)
    diff = (out_a - out_b).abs()
    # Only cell (3, 5) should differ; everything else should be identical.
    assert diff[:, 3, 5].sum() > 1e-6, "Perturbed cell should produce different output"
    mask = torch.ones_like(diff, dtype=torch.bool)
    mask[:, 3, 5] = False
    assert diff[mask].max() < 1e-6, "Other cells should be unaffected (no spatial coupling)"


def test_dinn_deep_default_param_count_is_in_expected_range() -> None:
    """Default DINNDeep should be ~10K params — substantially bigger than DINN's
    ~454 but still small enough to train quickly on a single GPU."""
    net = DINNDeep()  # default config
    n = sum(p.numel() for p in net.parameters())
    assert 5_000 < n < 20_000, f"Unexpected param count: {n}"


def test_dinn_deep_works_with_single_channel_input() -> None:
    """Backward-compat test: should run with n_input_channels=1 to match DINN's
    SST-only setup, even though the default is 4."""
    net = DINNDeep(n_input_channels=1, hidden_dim=16, n_outputs=6, n_blocks=2)
    env = torch.randn(1, 21, 31)
    out = net(env)
    assert out.shape == (6, 21, 31)


def test_dinn_deep_autograd_flows() -> None:
    """Gradients reach all parameters through the full forward pass."""
    net = DINNDeep(n_input_channels=4, hidden_dim=16, n_outputs=6, n_blocks=2)
    env = torch.randn(4, 8, 8, requires_grad=True)
    out = net(env)
    loss = out.pow(2).sum()
    loss.backward()
    n_with_grads = sum(1 for p in net.parameters() if p.grad is not None and p.grad.abs().sum() > 0)
    n_total = sum(1 for p in net.parameters())
    assert n_with_grads == n_total, f"Some params had no gradient: {n_with_grads}/{n_total}"


def test_dinn_deep_with_bounded_params() -> None:
    """End-to-end check: DINNDeep output -> bounded_params produces values in Carroll's ranges."""
    net = DINNDeep(n_input_channels=4, hidden_dim=16, n_outputs=6, n_blocks=2)
    env = torch.randn(4, 21, 31)
    theta = net(env)
    params = bounded_params(theta, PARAM_BOUNDS)
    assert params.shape == (6, 21, 31)
    for i in range(6):
        lo = PARAM_BOUNDS[i, 0].item()
        hi = PARAM_BOUNDS[i, 1].item()
        assert (params[i] >= lo).all() and (params[i] <= hi).all()


def test_dinn_deep_invalid_config_raises() -> None:
    """Sanity: invalid n_blocks / hidden_dim raise."""
    with pytest.raises(ValueError):
        DINNDeep(n_blocks=0)
    with pytest.raises(ValueError):
        DINNDeep(hidden_dim=0)


# --------------------------------------------------------------------------
# PerCellFreeField -- the pointwise rung of the parameterisation ladder.
# See docs/findings/2026-07-29_preregistration_obsonly_and_ladder.md for the
# pre-registered interpretation of the arm these tests support.
# --------------------------------------------------------------------------


def test_free_field_call_signature_matches_dinn() -> None:
    """env [C, H, W] -> [N_PARAMS, H, W], the same contract DINN honours."""
    net = PerCellFreeField(height=21, width=31, n_input_channels=2)
    env = torch.randn(2, 21, 31)
    out = net(env)
    assert out.shape == (N_PARAMS, 21, 31)
    assert torch.isfinite(out).all()


def test_free_field_batched_shape() -> None:
    """Batched env [B, C, H, W] -> [B, N_PARAMS, H, W]."""
    net = PerCellFreeField(height=8, width=9, n_input_channels=1)
    out = net(torch.randn(4, 1, 8, 9))
    assert out.shape == (4, N_PARAMS, 8, 9)


def test_free_field_ignores_covariates_entirely() -> None:
    """The whole point of the control: output does NOT depend on env content.

    DINN conditions parameters on covariates; the free field does not. If this
    ever fails, the arm has stopped being a pointwise null.
    """
    net = PerCellFreeField(height=6, width=7, n_input_channels=3)
    a = net(torch.randn(3, 6, 7))
    b = net(torch.randn(3, 6, 7) * 100.0)
    assert torch.equal(a, b)


def test_free_field_degrees_of_freedom() -> None:
    """One free value per parameter per cell, and nothing else.

    This count IS the experiment, and it has two honest versions that must not
    be conflated. The field is ALLOCATED over the full grid, but only ocean
    cells enter the loss, so the number of free values the observations can
    possibly constrain is the smaller one:

        allocated : 6 * (21*51 + 16*31 + 16*81) = 6 * 2863 = 17,178
        on ocean  : 6 * (1071  +  484  + 1296)  = 6 * 2851 = 17,106

    natlsubpolar is the only AOI with land: a 16x31 = 496-cell grid carrying
    484 ocean cells. Quote the ocean figure when comparing against DINN's
    weight count, because the 12 land cells are never gradient-connected.
    """
    net = PerCellFreeField(height=21, width=51)
    assert sum(p.numel() for p in net.parameters()) == N_PARAMS * 21 * 51
    allocated = sum(N_PARAMS * h * w for (h, w) in [(21, 51), (16, 31), (16, 81)])
    on_ocean = N_PARAMS * (1071 + 484 + 1296)
    assert allocated == 17178
    assert on_ocean == 17106


def test_free_field_is_grid_bound_and_says_so() -> None:
    """A field built for one AOI must refuse another AOI's grid.

    Silently broadcasting would let one instance be aliased across AOIs, which
    would make this arm a different (and unintended) parameterisation.
    """
    net = PerCellFreeField(height=21, width=51)
    with pytest.raises(ValueError, match="bound to one AOI"):
        net(torch.randn(1, 16, 31))
    with pytest.raises(ValueError):
        PerCellFreeField(height=0, width=5)


def test_free_field_init_matches_global_scalar_geometry() -> None:
    """Untrained distribution must be comparable across ladder rungs.

    Both controls init at 0.01 * randn so the sigmoid lands near mid-bounds.
    If the free field started somewhere else, its measured chance baseline
    would not be comparable to the other rungs' and the ladder would not be a
    controlled comparison.
    """
    torch.manual_seed(0)
    field = PerCellFreeField(height=12, width=13)
    torch.manual_seed(0)
    scalar = GlobalScalarNet(n_outputs=N_PARAMS)
    assert abs(float(field.theta.detach().std()) - 0.01) < 0.002
    assert abs(float(scalar.theta.detach().std()) - 0.01) < 0.02


def test_free_field_with_bounded_params_respects_registry_ranges() -> None:
    """End-to-end: free field -> bounded_params stays inside every bound."""
    net = PerCellFreeField(height=9, width=11)
    params = bounded_params(net(torch.randn(1, 9, 11)), PARAM_BOUNDS)
    assert params.shape == (N_PARAMS, 9, 11)
    for i in range(N_PARAMS):
        assert (params[i] >= PARAM_BOUNDS[i, 0].item()).all()
        assert (params[i] <= PARAM_BOUNDS[i, 1].item()).all()


def test_free_field_carries_no_regularisation() -> None:
    """The pointwise control must be unregularised by construction.

    A smoothness or magnitude penalty would make this a third parameterisation
    rather than a null, and would confound the ADCME comparison it exists to
    run. Guard: the module exposes exactly one parameter tensor and no buffers.
    """
    net = PerCellFreeField(height=5, width=5)
    assert len(list(net.parameters())) == 1
    assert len(list(net.buffers())) == 0
