"""Tests for darwindiff.diagnostics — NaN-safe Pearson correlation."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from darwindiff.diagnostics import PearsonResult, format_pearson, safe_pearson_r


class TestSafePearsonR:
    def test_perfect_positive_correlation(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = 2.0 * x + 1.0
        result = safe_pearson_r(x, y)
        assert result.r == pytest.approx(1.0)
        assert result.n_finite == 5
        assert result.is_constant is False

    def test_perfect_negative_correlation(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = -3.0 * x + 7.0
        result = safe_pearson_r(x, y)
        assert result.r == pytest.approx(-1.0)
        assert result.is_constant is False

    def test_nan_in_pred_is_filtered(self) -> None:
        # Inject one NaN; the remaining four pairs are perfectly correlated.
        x = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        result = safe_pearson_r(x, y)
        assert result.n_finite == 4
        assert result.r == pytest.approx(1.0)
        assert result.is_constant is False

    def test_nan_in_target_is_filtered(self) -> None:
        x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        y = np.array([2.0, 4.0, np.nan, 8.0, 10.0])
        result = safe_pearson_r(x, y)
        assert result.n_finite == 4
        assert result.r == pytest.approx(1.0)

    def test_inf_is_filtered(self) -> None:
        x = np.array([1.0, np.inf, 3.0, 4.0, 5.0])
        y = np.array([2.0, 4.0, 6.0, 8.0, 10.0])
        result = safe_pearson_r(x, y)
        assert result.n_finite == 4
        assert np.isfinite(result.r)

    def test_constant_pred_flags_is_constant(self) -> None:
        # Structural ceiling: global-scalar fit → constant prediction.
        pred = np.full(100, 0.5)
        target = np.linspace(0, 10, 100)
        result = safe_pearson_r(pred, target)
        assert result.is_constant is True
        assert np.isnan(result.r)
        assert result.n_finite == 100

    def test_constant_target_flags_is_constant(self) -> None:
        # Symmetric to constant-pred — either side with zero variance triggers.
        pred = np.linspace(0, 10, 100)
        target = np.full(100, 3.7)
        result = safe_pearson_r(pred, target)
        assert result.is_constant is True
        assert np.isnan(result.r)

    def test_constant_does_not_emit_runtime_warning(self) -> None:
        # The whole point of this helper is to avoid numpy's "invalid value
        # encountered in divide" on the structural-ceiling case.
        pred = np.zeros(50)
        target = np.linspace(0, 1, 50)
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            result = safe_pearson_r(pred, target)
        assert result.is_constant is True

    def test_np_full_constant_pred_is_detected(self) -> None:
        # Regression: ``np.full(N, 1.234).std()`` returns ~2.22e-16, not 0.0,
        # because the mean calculation has rounding error. A naive ``std == 0``
        # check missed this case and let corrcoef fire its divide warning. The
        # relative-tolerance check should catch it.
        pred = np.full(582, 1.234)  # bitwise-constant, but std() != 0
        target = np.random.default_rng(0).standard_normal(582)
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            result = safe_pearson_r(pred, target)
        assert result.is_constant is True
        assert np.isnan(result.r)

    def test_float_noise_around_constant_is_treated_as_constant(self) -> None:
        # The actual notebook 09 case: GPU box-model integration with truly
        # uniform parameters produces values that differ at the float-noise
        # level (e.g. 1e-15 spread relative to magnitude ~ 1.0). That spatial
        # "pattern" is meaningless and shouldn't be treated as a real signal.
        rng = np.random.default_rng(0)
        pred = 1.0 + 1e-15 * rng.standard_normal(582)  # 1e-15 spread on ~1
        target = rng.standard_normal(582)
        result = safe_pearson_r(pred, target)
        assert result.is_constant is True
        assert np.isnan(result.r)

    def test_small_but_real_signal_is_not_treated_as_constant(self) -> None:
        # Sanity check the threshold doesn't swallow genuine signals. A spread
        # of 1e-3 on a magnitude-1 field is small but real: ratio 1e-3 is far
        # above the 1e-10 noise threshold.
        rng = np.random.default_rng(0)
        pred = 1.0 + 1e-3 * rng.standard_normal(582)
        target = pred + 1e-3 * rng.standard_normal(582)  # weakly correlated
        result = safe_pearson_r(pred, target)
        assert result.is_constant is False
        assert np.isfinite(result.r)

    def test_all_nan_inputs(self) -> None:
        # No finite pairs at all — undefined for a different reason than
        # constant inputs (and is_constant should NOT be set).
        pred = np.full(10, np.nan)
        target = np.full(10, np.nan)
        result = safe_pearson_r(pred, target)
        assert result.n_finite == 0
        assert np.isnan(result.r)
        assert result.is_constant is False

    def test_single_finite_pair_undefined(self) -> None:
        # n_finite < 2: correlation is undefined but not for the constant
        # reason — there's just not enough data.
        pred = np.array([1.0, np.nan, np.nan])
        target = np.array([2.0, np.nan, np.nan])
        result = safe_pearson_r(pred, target)
        assert result.n_finite == 1
        assert np.isnan(result.r)
        assert result.is_constant is False

    def test_shape_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="shape mismatch"):
            safe_pearson_r(np.zeros(10), np.zeros(11))

    def test_2d_inputs_are_ravelled(self) -> None:
        # Convenience: real callers often pass 2-D fields after masking; ravel
        # should make that work the same as flat inputs.
        x = np.array([[1.0, 2.0], [3.0, 4.0]])
        y = np.array([[2.0, 4.0], [6.0, 8.0]])
        result = safe_pearson_r(x, y)
        assert result.r == pytest.approx(1.0)
        assert result.n_finite == 4

    def test_realistic_notebook09_dinn_pattern(self) -> None:
        # Sanity check against the notebook 09 DINN headline (r ~ 0.69).
        # Build a synthetic field with that level of correlation.
        rng = np.random.default_rng(0)
        n = 582  # number of ocean cells in the notebook 09 AOI
        target = rng.standard_normal(n)
        noise = rng.standard_normal(n)
        # weighted mix to land in the 0.5-0.85 band
        pred = 0.7 * target + 0.7 * noise
        result = safe_pearson_r(pred, target)
        assert 0.5 < result.r < 0.85
        assert result.is_constant is False
        assert result.n_finite == n


class TestFormatPearson:
    def test_normal_result(self) -> None:
        result = PearsonResult(r=0.691, n_finite=582, is_constant=False)
        s = format_pearson(result)
        assert "0.691" in s
        assert "0.477" in s  # r^2
        assert "undefined" not in s

    def test_constant_result(self) -> None:
        result = PearsonResult(r=float("nan"), n_finite=582, is_constant=True)
        s = format_pearson(result)
        assert "undefined" in s
        assert "constant" in s
        assert "zero spatial variance" in s

    def test_insufficient_data_result(self) -> None:
        result = PearsonResult(r=float("nan"), n_finite=1, is_constant=False)
        s = format_pearson(result)
        assert "undefined" in s
        assert "1 finite pair" in s

    def test_n_total_annotation(self) -> None:
        # When some cells were dropped as non-finite, format should say so.
        result = PearsonResult(r=0.5, n_finite=580, is_constant=False)
        s = format_pearson(result, n_total=582)
        assert "580/582 finite" in s

    def test_n_total_no_annotation_when_all_finite(self) -> None:
        result = PearsonResult(r=0.5, n_finite=582, is_constant=False)
        s = format_pearson(result, n_total=582)
        assert "finite" not in s
