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
from darwindiff.contract import RESCALE_MARGIN, rescale_is_admissible


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
