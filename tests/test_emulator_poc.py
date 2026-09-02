"""Tests for the science-critical helpers in scripts/emulator_poc.py.

These are the leak-free split/standardization, the AOI binning, and the skill
metric — the pieces where a silent bug invalidates every reported skill number.
CPU-only, tiny synthetic arrays; no data files, no GPU. The module has a
``__main__`` guard so importing it does not run the CLI.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
import emulator_poc as ep  # noqa: E402

from darwindiff.ecco_darwin_loader import AOI  # noqa: E402


# ---------------------------------------------------------------------------
# build_splits — the leak-free temporal split + pairing
# ---------------------------------------------------------------------------
def _data(times):
    return {"times_days": np.asarray(times, dtype=float)}


def test_split_no_pair_straddles_boundary():
    # 10 evenly-spaced months, 30% val -> split_idx = 7.
    s = ep.build_splits(_data(np.arange(10) * 30.0), val_frac=0.3, adjacency_tol=1.6)
    assert s["split_idx"] == 7
    # the boundary-straddling pair (m = split_idx-1 = 6) must be in NEITHER set.
    assert 6 not in s["train_pairs"], "pair 6->7 straddles the split: leakage"
    assert 6 not in s["val_pairs"]
    # every train pair stays fully inside train months; every val pair inside val.
    assert all(m + 1 < s["split_idx"] for m in s["train_pairs"])
    assert all(m >= s["split_idx"] for m in s["val_pairs"])


def test_split_drops_pairs_across_a_gap():
    # a big gap between months 3 and 4 -> that pair is not "adjacent" and is dropped.
    times = [0, 30, 60, 90, 400, 430, 460, 490, 520, 550]  # gap 90->400
    s = ep.build_splits(_data(times), val_frac=0.3, adjacency_tol=1.6)
    assert 3 not in s["train_pairs"] and 3 not in s["val_pairs"], "gap pair must drop"


def test_split_raises_when_no_valid_pairs():
    # all-gap times => no adjacent pairs => explicit error, not silent empty training.
    with pytest.raises(RuntimeError):
        ep.build_splits(_data([0, 1000, 2000, 3000, 4000]), val_frac=0.3, adjacency_tol=1.0)


def test_split_rejects_uniformly_sparse_axis():
    # Every gap == median but ~2 months: the median-based test would accept all pairs
    # as one-step and mislabel multi-month jumps as next-month skill. Must raise (#191).
    times = np.arange(12) * 61.0  # ~2-month uniform stride
    with pytest.raises(RuntimeError, match="uniformly-sparse"):
        ep.build_splits(_data(times), val_frac=0.3, adjacency_tol=1.6)


def test_split_iter_axis_uniformly_sparse_rejected():
    # The [0, 1000, 2000, ...]-style uniform axis (here mapped to >1-month day gaps)
    # is the exact case from #191 and must be flagged, not silently accepted.
    times = np.arange(8) * 90.0  # uniform 3-month stride
    with pytest.raises(RuntimeError, match="uniformly-sparse"):
        ep.build_splits(_data(times), val_frac=0.3, adjacency_tol=1.6)


def test_split_expected_step_days_overrides_guard():
    # Declaring the true cadence bypasses the guard and grades pairs at that cadence.
    times = np.arange(12) * 61.0
    s = ep.build_splits(_data(times), val_frac=0.3, adjacency_tol=1.6, expected_step_days=61.0)
    assert len(s["train_pairs"]) > 0 and len(s["val_pairs"]) > 0
    assert s["adjacency_ref_days"] == 61.0


def test_split_normal_monthly_series_unaffected():
    # A normal ~monthly series (30-day gaps) is NOT flagged and behaves as before.
    s = ep.build_splits(_data(np.arange(10) * 30.0), val_frac=0.3, adjacency_tol=1.6)
    assert len(s["train_pairs"]) > 0 and len(s["val_pairs"]) > 0
    assert s["adjacency_ref_days"] == s["median_step_days"] == 30.0


# ---------------------------------------------------------------------------
# standardize — z-score from TRAIN months only (no leakage)
# ---------------------------------------------------------------------------
def test_standardize_uses_train_months_only():
    # train months (0,1) are all 5.0; val months (2,3) are all 100.0.
    # A leak-free mean must equal 5.0, NOT be pulled toward 100.
    H = W = 4
    state = np.empty((4, 1, H, W))
    state[0:2] = 5.0
    state[2:4] = 100.0
    mask = np.ones((H, W), dtype=bool)
    z, means, _stds = ep.standardize(state, np.array([0, 1]), mask)
    assert means[0] == pytest.approx(5.0), "mean leaked val months in"
    # train months z-score to ~0; val months are far positive (unseen shift).
    assert abs(z[0].mean()) < 1e-9
    assert z[2].mean() > 1.0


def test_standardize_land_nan_becomes_zero():
    state = np.ones((3, 1, 2, 2))
    state[:, :, 0, 0] = np.nan  # a land cell
    mask = np.array([[False, True], [True, True]])  # land excluded from mask
    z, _means, _stds = ep.standardize(state, np.array([0, 1]), mask)
    assert np.isfinite(z).all(), "NaN must be scrubbed to 0"
    assert z[0, 0, 0, 0] == 0.0


def test_standardize_zero_variance_channel_no_divzero():
    state = np.full((3, 1, 2, 2), 7.0)  # constant channel -> std 0
    mask = np.ones((2, 2), dtype=bool)
    z, _means, stds = ep.standardize(state, np.array([0, 1]), mask)
    assert stds[0] == 1.0, "zero std must fall back to 1 (no divide-by-zero)"
    assert np.isfinite(z).all()


# ---------------------------------------------------------------------------
# _aoi_grid_shape / _bin_grid — resolution-correct binning
# ---------------------------------------------------------------------------
def test_aoi_grid_shape_matches_resolution():
    eqpac = AOI("eqpac", -5.0, 15.0, -160.0, -110.0)
    assert ep._aoi_grid_shape(eqpac, 1.0) == (21, 51)
    assert ep._aoi_grid_shape(eqpac, 0.25) == (81, 201)


def test_global_lon_span_drops_redundant_antimeridian_column():
    # a full -180..180 span is periodic: 0.25deg global = 1440 cols, not 1441.
    g = AOI("global", -80.0, 89.75, -180.0, 180.0)
    n_lat, n_lon = ep._aoi_grid_shape(g, 0.25)
    assert (n_lat, n_lon) == (680, 1440), "global span must drop the duplicated seam column"
    # regional AOI keeps inclusive endpoints (unchanged behavior).
    eqpac = AOI("eqpac", -5.0, 15.0, -160.0, -110.0)
    assert ep._aoi_grid_shape(eqpac, 0.25) == (81, 201)
    # _bin_grid agrees on shape and folds a near-+180 cell onto the -180 column.
    binned = ep._bin_grid(
        np.array([179.95]), np.array([0.0]), np.array([9.0]),
        -80.0, 89.75, -180.0, 180.0, res=0.25,
    )
    assert binned.shape == (n_lat, n_lon)
    assert binned[:, 0][np.isfinite(binned[:, 0])].size > 0, "+180 cell should fold to col 0"


def test_bin_grid_shape_and_mean():
    # two points land in the same 1-deg cell -> that cell holds their mean.
    xc = np.array([-159.9, -159.8, -110.1])  # lon
    yc = np.array([-4.9, -4.8, 14.9])  # lat
    vals = np.array([2.0, 4.0, 9.0])
    binned = ep._bin_grid(xc, yc, vals, -5.0, 15.0, -160.0, -110.0, res=1.0)
    assert binned.shape == (21, 51)
    # bottom-left cell (~lat -5, lon -160) = mean(2,4) = 3.0
    assert binned[0, 0] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# _sse_per_channel — the skill metric numerator/denominator building block
# ---------------------------------------------------------------------------
def test_sse_per_channel_masks_and_sums():
    pred = np.zeros((2, 2, 3, 3))
    target = np.zeros((2, 2, 3, 3))
    target[:, 0] = 1.0  # channel 0 off by 1 everywhere
    mask = np.ones((3, 3), dtype=bool)
    mask[0, 0] = False  # exclude one cell
    sse = ep._sse_per_channel(pred, target, mask)
    # channel 0: (3*3-1)=8 valid cells * 2 pairs * 1^2 = 16 ; channel 1: 0
    assert sse[0] == pytest.approx(16.0)
    assert sse[1] == pytest.approx(0.0)


def test_area_weight_downweights_poles():
    # cos(lat) weight: an equatorial cell counts ~1, a near-pole cell ~0.
    lats = np.array([0.0, 89.0])  # equator, near-pole
    w2d = ep._area_weights(lats, width=1)  # [2,1]
    assert w2d[0, 0] == pytest.approx(1.0)  # cos(0) = 1
    assert w2d[1, 0] < 0.02  # cos(89 deg) ~ 0.017
    # identical error in both rows -> weighted SSE is dominated by the equator.
    pred = np.zeros((1, 1, 2, 1))
    target = np.ones((1, 1, 2, 1))
    mask = np.ones((2, 1), dtype=bool)
    assert ep._sse_per_channel(pred, target, mask, None)[0] == pytest.approx(2.0)  # unweighted
    sse_w = ep._sse_per_channel(pred, target, mask, w2d)[0]
    assert sse_w == pytest.approx(w2d[0, 0] + w2d[1, 0])  # cos(0)+cos(89)
    assert sse_w < 1.05, "near-pole cell should be nearly ignored under area weighting"


def test_sse_ignores_masked_cell_values():
    # a huge value in a masked-out cell must NOT enter the SSE.
    pred = np.zeros((1, 1, 2, 2))
    target = np.zeros((1, 1, 2, 2))
    target[0, 0, 0, 0] = 1e6  # masked-out cell
    mask = np.array([[False, True], [True, True]])
    sse = ep._sse_per_channel(pred, target, mask)
    assert sse[0] == pytest.approx(0.0), "masked cell leaked into the metric"


# ---------------------------------------------------------------------------
# save_checkpoint — roundtrip integrity (cross-cluster transfer + HF publish)
# ---------------------------------------------------------------------------
def _tiny_model():
    from darwindiff.emulator import build_emulator

    return build_emulator(variables=["A", "B"], grid_shape=(8, 8), modes=2, width=4, n_layers=1)


def test_save_checkpoint_pt_roundtrip(tmp_path):
    import torch

    m = _tiny_model()
    config = {"modes": 2, "width": 4, "channel_names": ["A", "B"], "residual": True}
    means, stds = np.array([1.0, 2.0]), np.array([3.0, 4.0])
    p = ep.save_checkpoint(tmp_path / "ck.pt", m, config, means, stds)
    assert p.exists()
    blob = torch.load(str(p), map_location="cpu", weights_only=False)
    assert set(blob["state_dict"].keys()) == set(m.state_dict().keys()), "weight keys drifted"
    assert blob["config"] == config, "config metadata not preserved"
    assert np.allclose(blob["means"].numpy(), means) and np.allclose(blob["stds"].numpy(), stds)
    # portability: everything on CPU so it loads on any GPU via map_location.
    assert all(v.device.type == "cpu" for v in blob["state_dict"].values())


def test_rollout_positivity_projection():
    """The rollout positivity fix de-standardizes, clamps physical >=0, re-standardizes.
    It must remove negative concentrations while leaving already-positive tracers untouched."""
    import torch

    means = torch.tensor([2000.0, 0.01]).view(1, 2, 1, 1)  # DIC-like (large), PIC-like (near 0)
    stds = torch.tensor([50.0, 0.02]).view(1, 2, 1, 1)
    x = torch.tensor([[[[-1.0]], [[-2.0]]]])  # DIC z=-1 -> 1950 (ok); PIC z=-2 -> -0.03 (negative)
    x_proj = ((x * stds + means).clamp(min=0.0) - means) / stds
    phys = x_proj * stds + means
    assert (phys >= -1e-6).all(), "projection left a negative physical concentration"
    assert torch.allclose(x_proj[0, 0], x[0, 0]), "already-positive tracer must be unchanged"
    assert phys[0, 1].item() == pytest.approx(0.0, abs=1e-6), "negative tracer must clamp to 0"


def test_rollout_mass_conserve_projection():
    """Mass-conserving positivity: clamp to >=0 then rescale to the pre-clamp domain mean.
    Must remove negatives AND preserve the domain mean (when the mean is positive)."""
    import torch

    means = torch.tensor([0.05]).view(1, 1, 1, 1)
    stds = torch.tensor([0.02]).view(1, 1, 1, 1)
    # physical [-0.03, 0.06, 0.08, 0.02] -> mean 0.0325 > 0, one negative cell
    x = torch.tensor([[[[-4.0, 0.5], [1.5, -1.5]]]])
    mask = torch.ones(2, 2, dtype=torch.bool)
    x_phys = x * stds + means
    pre = x_phys[..., mask].mean().view(1, 1, 1, 1)
    xc = x_phys.clamp(min=0.0)
    post = xc[..., mask].mean().view(1, 1, 1, 1)
    xc = xc * (pre / post.clamp(min=1e-30)).clamp(min=0.0, max=10.0)
    assert (xc >= -1e-6).all(), "positivity violated"
    assert torch.allclose(xc[..., mask].mean(), pre.squeeze(), atol=1e-6), (
        "domain mean not conserved")


def test_save_checkpoint_safetensors_roundtrip(tmp_path):
    import json

    import torch

    pytest.importorskip("safetensors")
    from safetensors import safe_open
    from safetensors.torch import load_file

    from darwindiff.emulator import HAS_PHYSICSNEMO

    m = _tiny_model()
    sd = m.state_dict()
    config = {"modes": 2, "width": 4, "channel_names": ["A", "B"]}
    means, stds = np.array([1.0, 2.0]), np.array([3.0, 4.0])
    p = ep.save_checkpoint(tmp_path / "ck.safetensors", m, config, means, stds)
    tensors = load_file(str(p))
    assert "stats.means" in tensors and "stats.stds" in tensors, "stats not embedded"
    assert any(k.startswith("model.") for k in tensors), "weights not embedded"
    with safe_open(str(p), framework="pt") as f:
        meta = f.metadata()
    assert json.loads(meta["config"]) == config, "config metadata not roundtripped"
    # complex spectral weights (fallback FNO2d) must roundtrip via view_as_complex.
    complex_keys = json.loads(meta.get("complex_keys", "[]"))
    if not HAS_PHYSICSNEMO:
        assert complex_keys, "fallback FNO2d has complex weights; expected complex_keys metadata"
    for k in complex_keys:
        rebuilt = torch.view_as_complex(tensors[f"model.{k}"].contiguous())
        assert torch.allclose(rebuilt, sd[k]), f"complex weight {k} did not roundtrip"
