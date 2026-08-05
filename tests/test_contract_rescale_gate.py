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
    lo, hi = [p.bounds for p in PARAMS if p.name == name][0]
    return hi / lo


def test_margin_is_exactly_the_span_with_no_slack() -> None:
    """Slack here would be taste. The span is already the widest the registry admits."""
    assert RESCALE_MARGIN == 1.0


def test_scav_rat_span_is_the_documented_100x() -> None:
    assert _span("scav_rat") == pytest.approx(100.0)


def test_a_rescale_exactly_at_the_span_is_admissible() -> None:
    """The boundary is inclusive: at the span the parameter can still reach its bounds."""
    ok, why = rescale_is_admissible("scav_rat", 100.0)
    assert ok, why


def test_the_ligand_upper_end_voids_the_grade() -> None:
    """2001x against a 100x span. This is the case the screen was built to catch."""
    ok, why = rescale_is_admissible("scav_rat", 2001.0)
    assert not ok
    assert "VOID" in why and "2001" in why


def test_the_ligand_lower_end_does_NOT_void_on_its_own() -> None:
    """A correction to the finding's prose.

    ``2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`` says the ligand proposal "fails it
    outright" at "61x to 2001x". Point-by-point that is not so: 61x sits inside a 100x span and
    passes. The proposal is inadmissible because it does not PIN a factor and its worst case
    voids, which is a different and weaker statement than every point failing. A caller screening
    a range must therefore test the extreme, not the midpoint.
    """
    ok, _ = rescale_is_admissible("scav_rat", 61.0)
    assert ok, "61x is inside a 100x span; the finding's 'outright' is imprecise"

    worst = max(61.0, 2001.0)
    assert not rescale_is_admissible("scav_rat", worst)[0]


def test_reciprocal_rescales_are_treated_alike() -> None:
    """Shrinking by 200x moves the estimand as far as growing by 200x."""
    up, _ = rescale_is_admissible("scav_rat", 200.0)
    down, _ = rescale_is_admissible("scav_rat", 1.0 / 200.0)
    assert up is down is False
    assert rescale_is_admissible("scav_rat", 1 / 50.0)[0] is True


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_identity_rescale_is_admissible_for_every_registry_parameter(name: str) -> None:
    """A closure that changes nothing can never void the grade."""
    ok, _ = rescale_is_admissible(name, 1.0)
    assert ok


@pytest.mark.parametrize("name", [p.name for p in PARAMS if p.bounds[0] > 0])
def test_a_rescale_one_percent_past_the_span_voids_for_every_parameter(name: str) -> None:
    ok, _ = rescale_is_admissible(name, _span(name) * 1.01)
    assert not ok


def test_reason_is_populated_on_a_pass_too() -> None:
    """Callers log why something passed, not only why it failed."""
    ok, why = rescale_is_admissible("alpfe", 2.0)
    assert ok and why.strip()


def test_bounds_override_bypasses_the_registry() -> None:
    ok, _ = rescale_is_admissible("scav_rat", 5.0, bounds=(1.0, 2.0))
    assert not ok, "a 2x span must reject a 5x rescale regardless of the registry"


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
