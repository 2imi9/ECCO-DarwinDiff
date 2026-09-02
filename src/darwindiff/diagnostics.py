"""NaN-safe diagnostics utilities for parameter-learner evaluation.

The DarwinDiff training notebooks evaluate their fits with Pearson r between a
predicted spatial field (phyto biomass from the box-model integration) and a
target field (e.g. z-scored -NO3 from GLODAP). Two failure modes show up in
practice:

1. **Integration blowup at a single cell.** Under unlucky parameter exploration
   (or numerical instability at a coastline cell), one element of ``phyto`` can
   be NaN. ``phyto.mean()`` and ``phyto.std()`` then propagate NaN to every
   element after z-scoring, and the whole reported correlation silently turns
   NaN. This is a bug we want to surface, not paper over.

2. **Constant prediction (zero spatial variance).** The Green's-functions
   parametric class — a single Carroll-6 vector applied uniformly across the
   AOI — produces an identical phyto value at every cell when the initial
   state is also uniform. Pearson r between a constant array and any target is
   mathematically undefined (the denominator ``std(pred) * std(target)`` is
   zero). This is the *structural ceiling* the head-to-head in notebook 09 is
   designed to make visible, not a bug.

Both paths route through ``np.corrcoef``, which silently emits a
``RuntimeWarning: invalid value encountered in divide`` and returns NaN in
either case. ``safe_pearson_r`` distinguishes the two: it filters non-finite
inputs (so NaN never reaches corrcoef) and detects zero-variance inputs
explicitly so callers can render the structural-ceiling case as "undefined
(constant prediction)" rather than as a warning-laden NaN.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# --- Carroll-6 recovery banding ----------------------------------------------
#
# The DarwinDiff parameter-recovery experiments classify each recovered
# Carroll-6 parameter by its relative offset from Carroll's published value,
# ``rel = abs(recovered - carroll) / abs(carroll)``. The four-band scheme
# (Excellent / Cal-grade / Loose / Drifted) is used consistently across
# notebooks, runner scripts, and the result aggregator. Keep the thresholds
# canonical here so everywhere reports the same verdict for the same number.

BAND_EXCELLENT_MAX: float = 0.05
"""Relative-offset ceiling for the ``Excellent`` band. <= 5 % off Carroll."""

BAND_CAL_GRADE_MAX: float = 0.40
"""Relative-offset ceiling for the ``Cal-grade`` band. <= 40 % off Carroll."""

BAND_LOOSE_MAX: float = 0.80
"""Relative-offset ceiling for the ``Loose`` band. <= 80 % off Carroll;
anything beyond is ``Drifted``."""


def band_of(rel_offset: float) -> str:
    """Classify a Carroll-6 parameter recovery by its relative offset.

    Args:
        rel_offset: ``abs(recovered - carroll) / abs(carroll)``. Must be
            non-negative; NaN is treated as ``Drifted`` (worst case) so the
            caller doesn't need a special path for missing values.

    Returns:
        One of ``"Excellent"`` (<= 5 %), ``"Cal-grade"`` (<= 40 %),
        ``"Loose"`` (<= 80 %), ``"Drifted"`` (> 80 % or NaN).
    """
    if not np.isfinite(rel_offset):
        return "Drifted"
    if rel_offset <= BAND_EXCELLENT_MAX:
        return "Excellent"
    if rel_offset <= BAND_CAL_GRADE_MAX:
        return "Cal-grade"
    if rel_offset <= BAND_LOOSE_MAX:
        return "Loose"
    return "Drifted"


@dataclass(frozen=True)
class PearsonResult:
    """Result of a NaN-safe Pearson correlation.

    Attributes:
        r: correlation coefficient over finite pairs, or NaN if undefined.
            ``nan`` covers both edge cases (``is_constant=True`` and
            ``n_finite < 2``); use the other fields to disambiguate.
        n_finite: number of (pred, target) pairs where both sides are finite.
            Equals the number of pairs that participated in the correlation.
        is_constant: True iff at least one of pred / target had zero variance
            over the finite pairs. In that case Pearson r is mathematically
            undefined and this flag is the right thing to report to the user
            (rather than the NaN itself, which can be confused with a numerical
            failure).
    """

    r: float
    n_finite: int
    is_constant: bool


def safe_pearson_r(pred: np.ndarray, target: np.ndarray) -> PearsonResult:
    """Pearson r that handles NaN and zero-variance inputs without warnings.

    Pre-filters non-finite pairs, then checks for zero variance on either side
    before calling :func:`numpy.corrcoef`. The zero-variance case (constant
    prediction or constant target) is reported via ``is_constant=True`` rather
    than letting numpy emit ``RuntimeWarning: invalid value encountered in
    divide``. Callers should branch on ``is_constant`` to render the result
    appropriately — typically as "undefined (zero spatial variance)" when the
    structural-ceiling argument is the point.

    .. warning::

        **Pass RAW fields, not z-scored ones.** Pearson r is scale-and-shift
        invariant for non-degenerate inputs, so the r value is identical
        whether you pass raw or normalised arrays — but the
        ``is_constant`` detection only fires on raw scale. A common anti-
        pattern is to z-score with ``x.std().clamp(min=eps)`` first
        (typically ``eps=1e-6``); the clamp magnifies float-level noise from
        ``~eps_double`` to ``~eps_double/eps`` and moves ``std/|mean|`` from
        ``~1e-16`` to ``~O(1)``, which is indistinguishable from a real
        signal. The relative-tolerance constant check then misses the case
        it exists to catch and the function returns a finite-but-meaningless
        r against random noise. Compare raw to raw.

    Args:
        pred: 1-D array of predicted values.
        target: 1-D array of target values, same length as ``pred``.

    Returns:
        :class:`PearsonResult` with ``r``, ``n_finite``, and ``is_constant``.
        If fewer than 2 finite pairs are present, ``r`` is NaN and
        ``is_constant`` is False (insufficient data, not a constant predictor).

    Raises:
        ValueError: if ``pred`` and ``target`` have different shapes after
            ravelling.
    """
    pred = np.asarray(pred).ravel()
    target = np.asarray(target).ravel()
    if pred.shape != target.shape:
        raise ValueError(
            f"shape mismatch after ravel: pred {pred.shape} vs target {target.shape}"
        )

    finite = np.isfinite(pred) & np.isfinite(target)
    n_finite = int(finite.sum())
    if n_finite < 2:
        return PearsonResult(float("nan"), n_finite, is_constant=False)

    p = pred[finite]
    t = target[finite]
    # Guard against the structural-ceiling case (constant prediction) before
    # corrcoef so we don't fire numpy's divide warning. Use a relative
    # tolerance rather than ``std == 0`` because ``np.std`` of a bitwise-
    # identical array isn't exactly zero — it reflects rounding error in the
    # mean calculation (e.g. ``np.full(582, 1.234).std()`` is ``2.22e-16``).
    # Anything below ~1e-10 of the array's magnitude is float noise, not
    # signal, so it counts as "effectively constant" for correlation purposes.
    if _is_effectively_constant(p) or _is_effectively_constant(t):
        return PearsonResult(float("nan"), n_finite, is_constant=True)

    r = float(np.corrcoef(p, t)[0, 1])
    return PearsonResult(r, n_finite, is_constant=False)


def _is_effectively_constant(arr: np.ndarray) -> bool:
    """True if ``arr`` has no meaningful spread relative to its magnitude.

    Two cases:
        - bitwise-constant: ``np.ptp`` is exactly zero (all elements identical).
        - float-noise-constant: ``std / mean(|arr|) < 1e-10``, i.e. the
          spread is below the precision of the values themselves. This catches
          the case where the box-model integration produces "the same" value
          at every cell up to float roundoff.

    The 1e-10 threshold is generous (well above ``eps_double ≈ 2.2e-16`` even
    after summing ~10⁵ terms) and well below any meaningful spatial signal in
    a z-scored field where ``std/mean ~ O(1)``.
    """
    if float(np.ptp(arr)) == 0.0:
        return True
    spread = float(arr.std())
    if spread == 0.0:
        return True
    scale = float(np.abs(arr).mean())
    if scale == 0.0:
        # Genuine signal centred on zero; ptp guard above already handled the
        # all-zero case, so non-zero spread here is real.
        return False
    return spread / scale < 1e-10


def format_pearson(result: PearsonResult, n_total: int | None = None) -> str:
    """Render a :class:`PearsonResult` for human display.

    Picks the right phrasing for the structural-ceiling case so it doesn't read
    as a numerical failure. Optionally annotates how many cells were dropped
    as non-finite when ``n_total`` is supplied.

    Args:
        result: the result to format.
        n_total: total number of cells the caller intended to correlate over.
            If provided and different from ``result.n_finite``, a "(N/M finite)"
            suffix is appended.

    Returns:
        A string suitable for ``print`` / log output.
    """
    if result.is_constant:
        body = "undefined (constant prediction; zero spatial variance)"
    elif np.isnan(result.r):
        body = f"undefined (only {result.n_finite} finite pair(s))"
    else:
        body = f"{result.r:.3f}  (r^2 = {result.r ** 2:.3f})"

    if n_total is not None and result.n_finite != n_total:
        body += f"  [{result.n_finite}/{n_total} finite]"
    return body


# ---------------------------------------------------------------------------
# Per-AOI collapse statistics.
#
# A recovered parameter is a per-cell FIELD; a recovery count needs a scalar. The
# choice of collapse is therefore part of the estimator, not a formatting detail,
# and for a parameter spanning decades it is load-bearing.
#
# THE IDENTITY THAT MATTERS. For a strictly positive field, Jensen's inequality
# gives arithmetic >= geometric, with equality only for a constant field. For a
# lognormal field of log-standard-deviation sigma the ratio is exactly
#
#     E[X] / exp(E[log X]) = exp(sigma^2 / 2)
#
# The DarwinDiff recovery band is RELATIVE (|v - C| / |C| <= band), so that ratio
# translates directly into pass or fail: an arithmetic collapse alone pushes a
# field whose GEOMETRIC mean sits exactly on the reference outside the band once
#
#     exp(sigma^2 / 2) - 1 > band   <=>   sigma > sqrt(2 * ln(1 + band))
#
# For the 0.40 Cal band that threshold is sigma = 0.8203. Below sigma ~ 0.3 the
# distortion is under 5 % and cannot change a verdict.
#
# `scav_rat` spans 100x in its registry bounds, which is why this was flagged
# (2026-07-28 evidence log, section B5) and why the runner now records all three
# collapses plus the measured per-cell sigma on every seed. Because the collapse
# is pure reporting and never enters the loss, the three statistics come from the
# SAME fit, making the comparison exactly paired rather than an A/B across arms.
# ---------------------------------------------------------------------------

CAL_GRADE_BAND = 0.40


def sigma_threshold_for_band(band: float = CAL_GRADE_BAND) -> float:
    """Per-cell log-sd at which an arithmetic collapse alone clears a relative band.

    Solves ``exp(sigma**2 / 2) - 1 = band``. Above this, a field whose geometric
    mean sits exactly on the reference is scored as NOT recovered purely because
    of the summary statistic.

    >>> round(sigma_threshold_for_band(0.40), 4)
    0.8203

    CAVEAT (mathematical audit, 2026-07-29). This is the threshold for an EXACT
    lognormal field. The real field comes through a truncated sigmoid map, so a
    lognormal is not exactly realisable and the requirement is about **9 % larger**
    in practice: sd(log p) ~= 0.8924 nat (0.3876 dex) for the linear map every
    published run uses. Treat 0.8203 as a lower bound on the threshold, i.e. as the
    conservative side for deciding whether the collapse choice can matter. For
    scale, the hard maximum achievable on ``scav_rat``'s bounds is 2.30 nat.
    """
    if band <= -1.0:
        raise ValueError(f"band must exceed -1, got {band}")
    return float(np.sqrt(2.0 * np.log1p(band)))


def arith_over_geom(sigma: float) -> float:
    """Expected arithmetic/geometric ratio for a lognormal field of log-sd ``sigma``."""
    return float(np.exp(0.5 * sigma * sigma))


def _ocean_values(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Select ocean cells as ``[n_params, n_ocean]``.

    Selection, never multiplication. Multiplying land cells by zero would inject a
    spike of zeros at the low end, which silently drags the median down and makes
    the geometric mean undefined. That is exactly the class of quiet metric bug the
    straddle guard exists to catch, so it is prevented structurally here.
    """
    field = np.asarray(field)
    if field.ndim != 3:
        raise ValueError(f"field must be [n_params, H, W], got shape {field.shape}")
    sel = np.asarray(mask).astype(bool).reshape(-1)
    if sel.shape[0] != field.shape[1] * field.shape[2]:
        raise ValueError(
            f"mask of {sel.shape[0]} cells does not match field grid "
            f"{field.shape[1]}x{field.shape[2]}")
    if not sel.any():
        raise ValueError("mask selects no ocean cells")
    return field.reshape(field.shape[0], -1)[:, sel]


def collapse_arithmetic(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Arithmetic mean over ocean cells. The PRIMARY verdict statistic, unchanged.

    Kept as the primary so every published run reproduces bitwise. Note it is the
    one most distorted by a wide field, being dominated by the largest cells.
    """
    return _ocean_values(field, mask).mean(axis=1)


def collapse_geometric(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Geometric mean over ocean cells, ``exp(mean(log v))``.

    The natural summary for a strictly positive parameter spanning decades, and
    the one that is equivariant under the log reparameterisation that
    ``Param.scale = "log"`` applies to the bounding map.
    """
    vals = _ocean_values(field, mask)
    if not np.all(vals > 0):
        raise ValueError(
            "geometric collapse needs a strictly positive field; bounded_params "
            "guarantees this for every registry entry, so a non-positive value "
            "means the field did not come through the sigmoid bounding map")
    return np.exp(np.log(vals).mean(axis=1))


def collapse_median(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Median over ocean cells. Robust to a heavy upper tail, unlike the mean."""
    return np.median(_ocean_values(field, mask), axis=1)


def per_cell_log_sd(field: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Per-cell log-standard-deviation over ocean cells, sample (ddof=1).

    THE diagnostic that decides whether the collapse choice can matter at all.
    Compare against :func:`sigma_threshold_for_band`.
    """
    vals = _ocean_values(field, mask)
    if not np.all(vals > 0):
        raise ValueError("log-sd needs a strictly positive field")
    if vals.shape[1] < 2:
        return np.zeros(vals.shape[0])
    return np.log(vals).std(axis=1, ddof=1)


def collapse_report(field: np.ndarray, mask: np.ndarray) -> dict:
    """All three collapses plus the sigma diagnostic, computed from one field.

    Returns a dict of ``[n_params]`` arrays. Because these all come from the same
    field they are exactly paired, which is why no A/B arm is needed to compare
    collapse statistics.
    """
    sigma = per_cell_log_sd(field, mask)
    return {
        "arithmetic": collapse_arithmetic(field, mask),
        "geometric": collapse_geometric(field, mask),
        "median": collapse_median(field, mask),
        "log_sd": sigma,
        "arith_over_geom": np.exp(0.5 * sigma * sigma),
        "sigma_threshold": sigma_threshold_for_band(CAL_GRADE_BAND),
    }
