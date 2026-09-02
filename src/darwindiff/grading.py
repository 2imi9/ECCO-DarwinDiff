"""The per-AOI recovery rule, in one place.

Every recovery count this project publishes is produced by the same rule: a parameter
counts as recovered for a seed when it lands Cal-grade or better against Carroll in
enough of that run's AOIs. As of 2026-07-30 that rule had **eight independent
implementations** across `scripts/`, and four of them hardcoded ``>= 2``, which grades
every single-AOI run 0/n no matter what it recovered.

That defect was latent rather than harmful, because every published number came from a
3-AOI run where the hardcoded and correct forms agree. It stopped being latent when the
global-scalar observations-only design called for single-AOI runs: a global scalar takes
the same value in every AOI, so a 3-AOI global-scalar fit has three identical legs and
2-of-3 degenerates to 1-of-1 anyway. The well-posed design is separate single-AOI runs,
and those are exactly the runs the hardcoded form silently condemns.

The duplication is the hazard, not any individual copy. This module is the single
definition; `scripts/verify_run.py` is the gate that enforces it, and
`tests/test_grading_module.py` asserts every caller agrees with it on a fixture set.

Deliberately dependency-light (standard library only). `verify_run.py` imports the
grading path without torch or numpy available, and that must keep working.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

from .diagnostics import BAND_CAL_GRADE_MAX, band_of

__all__ = [
    "CAL_PLUS",
    "count_cal_plus_legs",
    "is_cal_plus",
    "is_recovered_per_aoi",
    "relative_offset",
    "required_legs",
    "straddles",
]

CAL_PLUS: frozenset[str] = frozenset({"Excellent", "Cal-grade"})
"""Bands that count as recovered. Mirrors ``verify_run.CAL_PLUS``."""


def required_legs(n_aois: int) -> int:
    """How many Cal-plus AOI legs a parameter needs to count as recovered.

    The rule, exactly as ``scripts/verify_run.py`` applies it:

    ==========  ========  ==========================================================
    ``n_aois``  required  why
    ==========  ========  ==========================================================
    0           1         unreachable: no legs means never recovered (see below)
    1           1         a single-AOI run is graded on its only leg
    >= 2        2         the >=2-of-3 metric CLAUDE.md mandates
    ==========  ========  ==========================================================

    For ``n_aois == 0`` the caller must treat the parameter as NOT recovered; a
    threshold of 1 against zero legs can never be met, so returning 1 is safe and
    keeps this function total.

    Note the rule is "at least two legs", not a strict majority. They coincide at
    ``n_aois`` of 1, 2 and 3, and every run in this project uses 1 or 3. At 4 or more
    AOIs the two would part company (2 of 5 is not a majority) and this rule would
    need an explicit decision rather than an accidental one.
    """
    if n_aois <= 1:
        return 1
    return 2


def relative_offset(recovered: float | None, carroll: float | None) -> float:
    """``abs(recovered - carroll) / abs(carroll)``, or ``inf`` when undefined.

    Returns ``inf`` (worst case) rather than raising for a missing value, a
    non-numeric value, or a zero Carroll reference, so callers need no special path
    and a broken record can never be scored as a success.
    """
    if recovered is None or carroll is None:
        return math.inf
    try:
        rec, car = float(recovered), float(carroll)
    except (TypeError, ValueError):
        return math.inf
    if car == 0.0 or not math.isfinite(car) or not math.isfinite(rec):
        return math.inf
    rel = abs(rec - car) / abs(car)
    return rel if math.isfinite(rel) else math.inf


def is_cal_plus(recovered: float | None, carroll: float | None) -> bool:
    """True when ``recovered`` is Cal-grade or better against ``carroll``.

    Uses :func:`darwindiff.diagnostics.band_of` so the band boundaries have one
    definition too. Equivalent to ``relative_offset(...) <= BAND_CAL_GRADE_MAX``.
    """
    return band_of(relative_offset(recovered, carroll)) in CAL_PLUS


def count_cal_plus_legs(per_aoi: Mapping[str, float | None], carroll: float | None) -> int:
    """Number of AOI legs that are Cal-grade or better."""
    return sum(1 for v in (per_aoi or {}).values() if is_cal_plus(v, carroll))


def is_recovered_per_aoi(
    per_aoi: Mapping[str, float | None] | None, carroll: float | None
) -> bool:
    """THE recovery metric: Cal-plus in at least :func:`required_legs` of the run's AOIs.

    Args:
        per_aoi: mapping of AOI name to the recovered value in that AOI. An empty or
            missing mapping means the parameter was not graded per-AOI and is NOT
            recovered.
        carroll: the published Carroll optimum this parameter is graded against.

    This is the *only* number that should be headlined. The cell-weighted band is not
    a recovery statement: a cell-weighted mean can sit inside the band while every
    individual AOI sits outside it on alternating sides. See :func:`straddles`.
    """
    legs = per_aoi or {}
    n_aois = len(legs)
    if n_aois == 0:
        return False
    return count_cal_plus_legs(legs, carroll) >= required_legs(n_aois)


def straddles(
    per_aoi: Mapping[str, float | None] | None,
    carroll: float | None,
    cell_weighted_band: str,
) -> bool:
    """True when the cell-weighted band claims recovery and the per-AOI rule refuses it.

    A straddle is a metric inversion, not a rounding difference. Measured 2026-07-29 on
    the observations-only n=50 run, ``scav_rat`` read 40/50 cell-weighted and 0/50
    per-AOI, because all 50 seeds landed Cal-grade in exactly one AOI so no 2-of-3
    majority ever formed. That is the opposite conclusion.

    Only defined for multi-AOI runs: with one AOI the two metrics are the same
    measurement, so there is nothing to straddle.
    """
    legs = per_aoi or {}
    if len(legs) < 2:
        return False
    return cell_weighted_band in CAL_PLUS and not is_recovered_per_aoi(legs, carroll)


# Re-exported so callers never re-derive the threshold from a literal.
CAL_GRADE_MAX = BAND_CAL_GRADE_MAX
