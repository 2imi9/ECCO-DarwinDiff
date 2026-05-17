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
