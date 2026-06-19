"""Unit tests for the shared seasonal-recovery helpers (``darwindiff.seasonal``).

Pure functions hoisted out of ``scripts/run_seasonal_recovery.py``; tested here with
no GPU and no real data so the loss / z-score / IC logic is regression-protected
(previously it lived only in the script and was untested).
"""

from __future__ import annotations

import torch

from darwindiff.carroll6_5pft_2layer import N_TRACERS_2LAYER
from darwindiff.seasonal import (
    CONSTANT_STATE0,
    PFT_TO_STATE_IDX,
    constant_state0,
    seasonal_chl_loss,
    timemean_chl_loss,
    zscore_masked,
)


def test_constant_state0_scalar_and_spatial():
    expected = torch.tensor(CONSTANT_STATE0)  # float32, same construction
    s = constant_state0()
    assert s.shape == (N_TRACERS_2LAYER,)
    assert torch.equal(s, expected)
    grid = constant_state0((3, 4))
    assert grid.shape == (N_TRACERS_2LAYER, 3, 4)
    assert grid.is_contiguous()
    # Every cell holds the same IC vector.
    assert torch.equal(grid[:, 0, 0], expected)
    assert torch.equal(grid[:, 2, 3], expected)


def test_zscore_masked_uses_only_ocean_cells():
    field = torch.tensor([[1.0, 2.0, 3.0], [4.0, 1e9, 6.0]])
    mask = torch.tensor([[True, True, True], [True, False, True]])
    vals = zscore_masked(field, mask)[mask]
    assert abs(float(vals.mean())) < 1e-5
    assert abs(float(vals.std(unbiased=False)) - 1.0) < 1e-5
    # The huge unmasked cell must not perturb the masked stats.
    field2 = field.clone()
    field2[1, 1] = -1e9
    assert torch.allclose(zscore_masked(field2, mask)[mask], vals)


def test_zscore_masked_constant_region_is_finite():
    field = torch.full((2, 3), 5.0)
    mask = torch.ones(2, 3, dtype=torch.bool)
    # std.clamp(min=1e-6) avoids a div-by-zero NaN on a constant ocean field.
    assert torch.isfinite(zscore_masked(field, mask)).all()


def _matched(h: int = 4, w: int = 5):
    """Build (snaps, chl_z, mask) where the z-scored phyto channels exactly equal
    the targets, so a correct seasonal loss is ~0."""
    torch.manual_seed(0)
    snaps = torch.rand(12, N_TRACERS_2LAYER, h, w) + 0.1
    mask = torch.ones(h, w, dtype=torch.bool)
    chl_z = torch.zeros(12, 5, h, w)
    for m in range(12):
        for p, idx in enumerate(PFT_TO_STATE_IDX):
            chl_z[m, p] = zscore_masked(snaps[m, idx], mask)
    return snaps, chl_z, mask


def test_seasonal_loss_zero_at_perfect_match():
    snaps, chl_z, mask = _matched()
    assert float(seasonal_chl_loss(snaps, chl_z, mask)) < 1e-10


def test_seasonal_loss_detects_pft_mismapping():
    # Rolling the PFT axis mis-assigns each Chl target to the wrong box tracer; the
    # loss must rise (locks PFT_TO_STATE_IDX order against silent corruption).
    snaps, chl_z, mask = _matched()
    rolled = torch.roll(chl_z, shifts=1, dims=1)
    assert float(seasonal_chl_loss(snaps, rolled, mask)) > 1e-3


def test_seasonal_loss_is_mean_over_months():
    # All 12 months identical -> seasonal loss == the single-month summed-PFT MSE
    # (pins the /12 averaging).
    torch.manual_seed(1)
    one = torch.rand(N_TRACERS_2LAYER, 3, 3) + 0.1
    snaps = one[None].expand(12, N_TRACERS_2LAYER, 3, 3).contiguous()
    mask = torch.ones(3, 3, dtype=torch.bool)
    tgt = torch.rand(5, 3, 3)
    chl_z = tgt[None].expand(12, 5, 3, 3).contiguous()
    single = sum(
        float(((zscore_masked(one[idx], mask) - tgt[p])[mask] ** 2).mean())
        for p, idx in enumerate(PFT_TO_STATE_IDX)
    )
    assert abs(float(seasonal_chl_loss(snaps, chl_z, mask)) - single) < 1e-5


def test_timemean_loss_uses_annual_mean_target():
    torch.manual_seed(2)
    state = torch.rand(N_TRACERS_2LAYER, 3, 3) + 0.1
    chl_z = torch.rand(12, 5, 3, 3)
    mask = torch.ones(3, 3, dtype=torch.bool)
    target = chl_z.mean(dim=0)
    expected = sum(
        float(((zscore_masked(state[idx], mask) - target[p])[mask] ** 2).mean())
        for p, idx in enumerate(PFT_TO_STATE_IDX)
    )
    assert abs(float(timemean_chl_loss(state, chl_z, mask)) - expected) < 1e-5
