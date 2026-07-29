"""Tests for the per-AOI collapse statistics in darwindiff.diagnostics.

The collapse turns a recovered per-cell FIELD into the scalar that gets graded, so
it is part of the estimator rather than a formatting choice. For a parameter
spanning decades it is load-bearing, and it was flagged untested on 2026-07-28
(evidence log section B5) with an unexplained discrepancy attached: EKI reports
`scav_rat` biased LOW while an arithmetic-mean collapse biases HIGH.

These pin the mathematics the runner now relies on, and in particular the
threshold sigma = sqrt(2 ln(1+band)) at which the collapse choice alone decides a
verdict.
"""
from __future__ import annotations

import numpy as np
import pytest

from darwindiff.diagnostics import (
    CAL_GRADE_BAND,
    arith_over_geom,
    collapse_arithmetic,
    collapse_geometric,
    collapse_median,
    collapse_report,
    per_cell_log_sd,
    sigma_threshold_for_band,
)

# scav_rat's Carroll value, the parameter this analysis exists for.
SCAV_RAT_CARROLL = 10.41124 * 0.005 / 86400.0


def _lognormal_field(sigma: float, centre: float, h: int = 8, w: int = 9, seed: int = 0):
    """A field whose GEOMETRIC mean is exactly ``centre`` in expectation."""
    rng = np.random.default_rng(seed)
    vals = np.exp(np.log(centre) + rng.normal(0.0, sigma, size=(1, h, w)))
    mask = np.ones((h, w), dtype=bool)
    return vals, mask


def test_jensen_arithmetic_dominates_geometric() -> None:
    """Jensen: arithmetic >= geometric for any positive field, equality iff constant."""
    field, mask = _lognormal_field(0.5, SCAV_RAT_CARROLL, seed=1)
    assert collapse_arithmetic(field, mask)[0] > collapse_geometric(field, mask)[0]

    flat = np.full((1, 5, 5), SCAV_RAT_CARROLL)
    m = np.ones((5, 5), dtype=bool)
    assert collapse_arithmetic(flat, m)[0] == pytest.approx(collapse_geometric(flat, m)[0])
    assert per_cell_log_sd(flat, m)[0] == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("sigma", [0.1, 0.3, 0.5, 0.8, 1.2])
def test_arith_over_geom_matches_exp_sigma_squared_over_two(sigma: float) -> None:
    """The exact lognormal identity E[X]/exp(E[log X]) = exp(sigma^2/2).

    This is the identity the whole concern rests on, so it is checked against a
    large sample rather than asserted.
    """
    rng = np.random.default_rng(7)
    vals = np.exp(np.log(SCAV_RAT_CARROLL) + rng.normal(0.0, sigma, size=(1, 400, 500)))
    mask = np.ones((400, 500), dtype=bool)
    ratio = collapse_arithmetic(vals, mask)[0] / collapse_geometric(vals, mask)[0]
    assert ratio == pytest.approx(arith_over_geom(sigma), rel=0.02)


def test_sigma_threshold_is_where_arithmetic_alone_clears_the_band() -> None:
    """sigma = sqrt(2 ln(1+band)); at 0.40 that is 0.8203.

    Above it, a field whose geometric mean sits EXACTLY on the reference is scored
    as not recovered purely because of the summary statistic.
    """
    s = sigma_threshold_for_band(CAL_GRADE_BAND)
    assert s == pytest.approx(0.8203, abs=1e-4)
    assert arith_over_geom(s) - 1.0 == pytest.approx(CAL_GRADE_BAND, rel=1e-9)

    # Just above the threshold the arithmetic collapse fails a perfectly centred field.
    rng = np.random.default_rng(3)
    for sigma, should_fail in ((s * 1.25, True), (s * 0.4, False)):
        vals = np.exp(np.log(SCAV_RAT_CARROLL) + rng.normal(0.0, sigma, size=(1, 300, 400)))
        mask = np.ones((300, 400), dtype=bool)
        a = collapse_arithmetic(vals, mask)[0]
        g = collapse_geometric(vals, mask)[0]
        # the geometric collapse stays inside the band by construction
        assert abs(g - SCAV_RAT_CARROLL) / SCAV_RAT_CARROLL < CAL_GRADE_BAND
        # bool() is required: numpy comparisons yield np.bool_, and np.bool_(True)
        # is not the Python singleton True, so an `is` check would always fail.
        outside = bool(abs(a - SCAV_RAT_CARROLL) / SCAV_RAT_CARROLL > CAL_GRADE_BAND)
        assert outside is should_fail


def test_below_three_tenths_the_collapse_choice_cannot_change_a_verdict() -> None:
    """The stated 'under 5%, cannot matter' claim, verified rather than asserted."""
    assert arith_over_geom(0.3) - 1.0 < 0.05


def test_mask_is_applied_by_selection_not_multiplication() -> None:
    """Land cells must be EXCLUDED, not zeroed.

    Zeroing would inject a spike at the low end: it drags the median down and makes
    the geometric mean collapse to zero. This is the quiet-metric-bug class the
    straddle guard exists to catch, so it is prevented structurally.
    """
    h, w = 4, 4
    field = np.full((1, h, w), SCAV_RAT_CARROLL)
    mask = np.zeros((h, w), dtype=bool)
    mask[:2, :] = True          # half ocean
    field[0, 2:, :] = 0.0       # land cells carry nonsense

    assert collapse_arithmetic(field, mask)[0] == pytest.approx(SCAV_RAT_CARROLL)
    assert collapse_geometric(field, mask)[0] == pytest.approx(SCAV_RAT_CARROLL)
    assert collapse_median(field, mask)[0] == pytest.approx(SCAV_RAT_CARROLL)
    # and the zeros would have been fatal had they been included
    all_ocean = np.ones((h, w), dtype=bool)
    with pytest.raises(ValueError, match="strictly positive"):
        collapse_geometric(field, all_ocean)


def test_median_is_robust_to_a_heavy_upper_tail_where_the_mean_is_not() -> None:
    """The mechanism behind the concern: a few large cells move the mean, not the median."""
    field = np.full((1, 10, 10), SCAV_RAT_CARROLL)
    mask = np.ones((10, 10), dtype=bool)
    field[0, 0, :5] = SCAV_RAT_CARROLL * 100.0   # 5 cells of 100, i.e. 5% of cells

    a = collapse_arithmetic(field, mask)[0]
    m = collapse_median(field, mask)[0]
    assert abs(a - SCAV_RAT_CARROLL) / SCAV_RAT_CARROLL > CAL_GRADE_BAND   # mean is dragged out
    assert m == pytest.approx(SCAV_RAT_CARROLL)                            # median is not


def test_collapse_report_is_internally_consistent() -> None:
    field, mask = _lognormal_field(0.6, SCAV_RAT_CARROLL, h=40, w=50, seed=11)
    rep = collapse_report(field, mask)
    assert rep["arithmetic"][0] > rep["geometric"][0]
    assert rep["arith_over_geom"][0] == pytest.approx(
        rep["arithmetic"][0] / rep["geometric"][0], rel=0.1)
    assert rep["log_sd"][0] == pytest.approx(0.6, rel=0.1)
    assert rep["sigma_threshold"] == pytest.approx(0.8203, abs=1e-4)


def test_multi_parameter_fields_collapse_independently() -> None:
    """Shape contract: [n_params, H, W] -> [n_params], no cross-parameter leakage."""
    h, w = 6, 7
    field = np.stack([
        np.full((h, w), 1.0),
        np.full((h, w), 100.0),
        np.full((h, w), 0.001),
    ])
    mask = np.ones((h, w), dtype=bool)
    for fn in (collapse_arithmetic, collapse_geometric, collapse_median):
        out = fn(field, mask)
        assert out.shape == (3,)
        assert out == pytest.approx([1.0, 100.0, 0.001])


def test_bad_input_raises_rather_than_silently_producing_a_number() -> None:
    mask = np.ones((3, 3), dtype=bool)
    with pytest.raises(ValueError, match=r"\[n_params, H, W\]"):
        collapse_arithmetic(np.ones((3, 3)), mask)
    with pytest.raises(ValueError, match="does not match field grid"):
        collapse_arithmetic(np.ones((1, 3, 3)), np.ones((4, 4), dtype=bool))
    with pytest.raises(ValueError, match="no ocean cells"):
        collapse_arithmetic(np.ones((1, 3, 3)), np.zeros((3, 3), dtype=bool))
    with pytest.raises(ValueError):
        sigma_threshold_for_band(-1.5)


def test_numpy_reference_matches_the_runner_inline_torch_expressions() -> None:
    """The runner computes these collapses inline in torch; diagnostics is the numpy reference.

    Two implementations of the same statistic is a real risk, so the equivalence is
    locked here rather than assumed. The duplication is deliberate and temporary:
    array 233419 is already running with the inline torch version, so the runner
    cannot be refactored to call diagnostics mid-array without splitting the batch.
    When it is refactored, this test is what catches a divergence.

    Mirrors run_v3.0_joint_multi_aoi.py exactly:
        per_cell_sum   = (params_b * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        geometric      = exp((log(params_b) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f)
        median / log-sd = over params_b.flatten(1)[:, mask_f.reshape(-1) > 0]
    """
    torch = pytest.importorskip("torch")
    rng = np.random.default_rng(42)
    h, w, npar = 12, 15, 3
    field_np = np.exp(rng.normal(np.log(SCAV_RAT_CARROLL), 0.7, size=(npar, h, w)))
    mask_np = rng.random((h, w)) > 0.25          # ~75% ocean, some land
    mask_np[0, 0] = True                          # guarantee non-empty

    params_b = torch.tensor(field_np, dtype=torch.float64)
    mask_f = torch.tensor(mask_np.astype(np.float64))
    n_ocean_f = mask_f.sum()

    t_arith = ((params_b * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f).numpy()
    t_geom = torch.exp(
        (params_b.clamp(min=1e-300).log() * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
    ).numpy()
    ocean_sel = mask_f.reshape(-1) > 0
    ocean_vals = params_b.flatten(1)[:, ocean_sel]
    t_median = ocean_vals.median(dim=1).values.numpy()
    t_logsd = ocean_vals.clamp(min=1e-300).log().std(dim=1, unbiased=True).numpy()

    assert collapse_arithmetic(field_np, mask_np) == pytest.approx(t_arith, rel=1e-12)
    assert collapse_geometric(field_np, mask_np) == pytest.approx(t_geom, rel=1e-12)
    assert per_cell_log_sd(field_np, mask_np) == pytest.approx(t_logsd, rel=1e-12)
    # torch.median returns a LOWER median on even counts while numpy averages the two
    # middle values. Assert the documented tolerance rather than pretending they match.
    assert collapse_median(field_np, mask_np) == pytest.approx(t_median, rel=0.05)
