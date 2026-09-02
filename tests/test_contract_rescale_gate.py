"""The design-time rescale admissibility gate.

Prescribed by ``docs/findings/2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`` section 6,
where five of six proposed iron closures were screened as re-encoding the degeneracy rather than
breaking it. The screen identified this check as the one that would have rejected the ligand
proposal before any compute was spent, because it is arithmetic on the registry and needs no
fitted model.
"""

from __future__ import annotations

import pytest

from darwindiff.carroll6 import PARAMS
from darwindiff.contract import (
    CAL_GRADE_BAND,
    RESCALE_MARGIN,
    bound_proximity_risk,
    rescale_is_admissible,
)


def _span(name: str) -> float:
    lo, hi = next(p.bounds for p in PARAMS if p.name == name)
    return hi / lo


def _window(name: str) -> tuple[float, float]:
    """The factors that keep the rescaled range touching the Cal-grade band."""
    p = next(q for q in PARAMS if q.name == name)
    lo, hi = p.bounds
    ref = p.carroll_value
    return ref * (1.0 - CAL_GRADE_BAND) / hi, ref * (1.0 + CAL_GRADE_BAND) / lo


def test_margin_is_exactly_the_reachability_window_with_no_slack() -> None:
    """Slack here would be taste. The window is already the widest the grading rule admits."""
    assert RESCALE_MARGIN == 1.0


def test_scav_rat_span_is_the_documented_100x() -> None:
    assert _span("scav_rat") == pytest.approx(100.0)


def test_the_screen_tests_the_band_not_the_bounds() -> None:
    """The whole point of the fix, stated as arithmetic.

    A 100x rescale keeps ``scav_rat`` inside its own 100x bounds span, so the old bounds-based
    screen admitted it. It cannot reach the Cal-grade band: 100 * 3e-8 = 3e-6, which is already
    3.6x above the band's upper edge of 8.435e-7. Reachable-in-bounds is not gradeable.
    """
    f_min, f_max = _window("scav_rat")
    assert f_min == pytest.approx(0.1205, rel=1e-3)
    assert f_max == pytest.approx(28.12, rel=1e-3)
    assert f_max < _span("scav_rat"), "the window must be tighter than the span, or nothing changed"

    ok, why = rescale_is_admissible("scav_rat", 100.0)
    assert not ok, "100x stays inside the bounds but cannot reach the band"
    assert "VOID" in why


def test_the_ligand_upper_end_voids_the_grade() -> None:
    """2001x. This is the case the screen was built to catch."""
    ok, why = rescale_is_admissible("scav_rat", 2001.0)
    assert not ok
    assert "VOID" in why and "2001" in why


def test_the_ligand_lower_end_ALSO_voids() -> None:
    """The finding's prose was right; the screen was wrong.

    ``2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`` says the ligand proposal "fails it
    outright" at "61x to 2001x". An earlier version of this screen compared the factor to the
    bounds span and passed 61x, and this test asserted that pass as a correction to the finding.
    That was the screen's error. 61x puts ``scav_rat`` in [1.83e-6, 1.83e-4] while the band is
    [3.615e-7, 8.435e-7] -- no attainable value is gradeable, so every seed fails regardless of
    the data. "Fails outright" is exactly right, and it fails at BOTH ends of the proposed range.
    """
    for factor in (61.0, 2001.0):
        ok, why = rescale_is_admissible("scav_rat", factor)
        assert not ok, f"{factor}x cannot reach the Cal-grade band"
        assert "VOID" in why


def test_reciprocals_are_NOT_equivalent_because_carroll_is_off_centre() -> None:
    """The window is asymmetric in log space, and pretending otherwise loses cases.

    ``scav_rat``'s geometric bounds centre is 3e-7 but Carroll sits at 6.025e-7, 2.008x above it.
    So shrinking and growing by the same factor do NOT move the estimand equally far relative to
    the band. 1/50 voids while 20x passes, even though 50 > 20.
    """
    f_min, f_max = _window("scav_rat")
    assert f_min * f_max != pytest.approx(1.0), "if this were 1.0 the window would be symmetric"

    assert rescale_is_admissible("scav_rat", 20.0)[0] is True
    assert rescale_is_admissible("scav_rat", 1 / 50.0)[0] is False


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_identity_rescale_is_admissible_for_every_registry_parameter(name: str) -> None:
    """A closure that changes nothing can never void the grade."""
    ok, _ = rescale_is_admissible(name, 1.0)
    assert ok


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_one_percent_past_either_window_edge_voids_for_every_parameter(name: str) -> None:
    f_min, f_max = _window(name)
    assert not rescale_is_admissible(name, f_max * 1.01)[0]
    assert not rescale_is_admissible(name, f_min * 0.99)[0]


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_just_inside_either_window_edge_is_admissible_for_every_parameter(name: str) -> None:
    f_min, f_max = _window(name)
    assert rescale_is_admissible(name, f_max * 0.99)[0]
    assert rescale_is_admissible(name, f_min * 1.01)[0]


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_the_window_is_always_tighter_DOWNWARD_than_the_bounds_span(name: str) -> None:
    """Shrinking is where the span test was unambiguously too permissive.

    The span test admits any factor down to ``lo/hi``; the band test stops at ``band_lo/hi``,
    which is strictly larger for every registry parameter because every band sits above the
    lower bound.
    """
    assert _window(name)[0] > 1.0 / _span(name)


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_upward_looseness_happens_EXACTLY_when_the_band_overhangs_the_upper_bound(
    name: str,
) -> None:
    """The band test is not uniformly stricter, and the exception is not arbitrary.

    ``f_max = band_hi/lo`` exceeds the span ``hi/lo`` precisely when ``band_hi > hi`` -- the band
    pokes out past the top of the bounds. That is the same geometry
    :func:`bound_proximity_risk` flags, so the two screens agree on which parameters have a
    bound sitting inside the pass band: ``alpfe`` and ``diatomgraz``. For those, a rescale a
    little past the span really is still gradeable, and the span test was wrong to reject it.
    """
    looser_upward = _window(name)[1] > _span(name)
    assert looser_upward is bound_proximity_risk(name)[0]


def test_reason_is_populated_on_a_pass_too() -> None:
    """Callers log why something passed, not only why it failed."""
    ok, why = rescale_is_admissible("alpfe", 2.0)
    assert ok and why.strip()


def test_bounds_and_reference_override_bypass_the_registry() -> None:
    ok, _ = rescale_is_admissible("scav_rat", 5.0, bounds=(1.0, 2.0), reference=1.5)
    assert not ok, "5x lifts [1,2] to [5,10], clear of a band topping out at 2.1"
    ok, _ = rescale_is_admissible("scav_rat", 1.0, bounds=(1.0, 2.0), reference=1.5)
    assert ok, "the identity keeps 1.5 attainable"


def test_rejects_a_zero_reference_override() -> None:
    with pytest.raises(ValueError, match="no relative band"):
        rescale_is_admissible("alpfe", 2.0, bounds=(0.05, 1.0), reference=0.0)


def test_rejects_a_parameter_that_is_not_in_the_registry() -> None:
    with pytest.raises(ValueError, match="not in the Carroll-N registry"):
        rescale_is_admissible("not_a_parameter", 2.0)


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_rejects_a_non_positive_factor(bad: float) -> None:
    with pytest.raises(ValueError, match="must be positive"):
        rescale_is_admissible("alpfe", bad)


def test_rejects_a_non_positive_lower_bound() -> None:
    """A ratio span is undefined there, and silently returning True would be the wrong answer."""
    with pytest.raises(ValueError, match="span is undefined"):
        rescale_is_admissible("alpfe", 2.0, bounds=(0.0, 1.0))


# ------------------------------------------------------------------ bound proximity screen
# Measured 2026-08-05, job 276927: a trained fit drives alpfe to 99.7% of a 1.0 bound and 99.6%
# of a 1.6 bound. So a bound lying inside the pass band manufactures a pass on its own.

def test_alpfe_is_flagged_because_its_upper_bound_is_inside_the_band() -> None:
    at_risk, why = bound_proximity_risk("alpfe")
    assert at_risk
    assert "upper" in why


def test_r_picpoc_is_exonerated_by_arithmetic() -> None:
    """The other half of the "recovered globally" claim, and this result must not touch it."""
    at_risk, why = bound_proximity_risk("R_PICPOC")
    assert not at_risk, why


def test_exactly_alpfe_and_diatomgraz_are_at_risk() -> None:
    flagged = sorted(p.name for p in PARAMS if bound_proximity_risk(p.name)[0])
    assert flagged == ["alpfe", "diatomgraz"]


def test_a_bound_exactly_on_the_band_edge_counts_as_at_risk() -> None:
    """Inclusive on purpose: a fit railing to the edge still scores as recovered."""
    ref = 1.0
    at_risk, _ = bound_proximity_risk("alpfe", bounds=(0.01, 1.0 + CAL_GRADE_BAND), reference=ref)
    assert at_risk


def test_widening_a_bound_can_move_a_parameter_from_at_risk_to_safe() -> None:
    """This is the experiment, expressed as arithmetic: 1.0 is inside the band, 1.6 is not."""
    assert bound_proximity_risk("alpfe", bounds=(0.05, 1.0))[0] is True
    assert bound_proximity_risk("alpfe", bounds=(0.05, 1.6))[0] is False


def test_rejects_a_zero_reference() -> None:
    with pytest.raises(ValueError, match="no relative band"):
        bound_proximity_risk("alpfe", bounds=(0.05, 1.0), reference=0.0)
