"""The adequacy lever: dropping an unreachable observable block without rescaling the rest.

Two design decisions in `FET_AOI_W` are load-bearing, and both are silent when wrong -- the
run completes, the numbers look plausible, and the arm answers a different question than the
one asked. That is the failure shape this repo keeps hitting (the vacuous window-swap control,
the unpinned learning rate), so both are pinned here with a negative control that injects the
real bug.

1. THE NORMALISER MUST CARRY THE WEIGHT. The Darwin-pattern block is a weighted sum over
   eleven terms divided by `FET_W + 10`. If FeT is dropped for one AOI but the divisor is
   left at `FET_W + 10`, that AOI's whole pattern block is silently scaled by 10/11 relative
   to the others -- so the arm tests "drop eqpac iron AND down-weight everything else there",
   which is not the hypothesis.

2. THE RULE MUST NORMALISE WITHIN A BLOCK, NOT ABSOLUTELY. POC and PIC are saturated in every
   basin, so an absolute adequacy cut zeroes the Darwin-pattern terms in all three -- and
   those are what `R_PICPOC` recovers 50/50 from. The rule would destroy the project's
   cleanest result on its way to fixing `scav_rat`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RULE = ROOT / "docs" / "findings" / "2026-08-03_adequacy_rule.json"

FET_W = 1.0  # the flagship value
OTHER_TERMS = [0.7, 1.3, 0.9, 1.1, 0.5, 2.0, 0.8, 1.4, 0.6, 1.2]  # the ten non-FeT terms
FET_TERM = 3.0


def pattern_block(fet_aoi_w: float, *, carry_normaliser: bool) -> float:
    """The runner's pattern-block expression.

    `carry_normaliser=False` is the INJECTED BUG: the weight is applied to the term but not
    to the divisor.
    """
    fet_w = FET_W * fet_aoi_w
    numer = fet_w * FET_TERM + sum(OTHER_TERMS)
    denom = (fet_w if carry_normaliser else FET_W) + 10.0
    return numer / denom


def test_default_weight_is_a_bit_identical_no_op():
    """FET_AOI_W=1 must reproduce the historical expression exactly, not approximately."""
    historical = (FET_W * FET_TERM + sum(OTHER_TERMS)) / (FET_W + 10.0)
    assert pattern_block(1.0, carry_normaliser=True) == historical


def test_dropping_fet_leaves_the_survivors_mean_scaled():
    """With FeT dropped, the block must be the plain mean of the ten surviving terms.

    Anything else means the intervention reached beyond the FeT term.
    """
    got = pattern_block(0.0, carry_normaliser=True)
    assert got == pytest.approx(sum(OTHER_TERMS) / 10.0)


def test_negative_control_uncarried_normaliser_rescales_the_whole_block():
    """Inject the real bug and confirm these tests would catch it.

    A test that cannot fail on the bug it claims to guard is worth nothing -- this repo has
    shipped one that passed on an empty comparison.
    """
    buggy = pattern_block(0.0, carry_normaliser=False)
    correct = sum(OTHER_TERMS) / 10.0
    assert buggy != pytest.approx(correct)
    # and it is wrong in the specific, diagnosable way: down-scaled by exactly 10/11
    assert buggy == pytest.approx(correct * 10.0 / 11.0)


@pytest.mark.skipif(not RULE.exists(), reason="adequacy rule artifact not emitted")
def test_rule_leaves_blocks_that_are_saturated_everywhere_alone():
    """POC and PIC are unreachable in all three basins -- the rule must NOT down-weight them.

    They are the Darwin-pattern terms `R_PICPOC` recovers from. A rule that zeroes them
    trades a 50/50 result for a `scav_rat` gain, which is not an improvement.
    """
    rule = json.loads(RULE.read_text(encoding="utf-8"))
    for block in ("POC", "PIC"):
        assert rule["contrast"][block] == 1.0, f"{block} must carry no across-basin contrast"
        for aoi, w in rule["weights"].items():
            assert w[block] == 1.0, f"{block} down-weighted in {aoi} -- R_PICPOC is at risk"


@pytest.mark.skipif(not RULE.exists(), reason="adequacy rule artifact not emitted")
def test_rule_actually_discriminates_on_iron():
    """A rule that weights every basin equally decides nothing. FeT is the one live lever."""
    rule = json.loads(RULE.read_text(encoding="utf-8"))
    fet = {aoi: w["FeT"] for aoi, w in rule["weights"].items()}
    assert fet["eqpac"] == 0.0, "eqpac iron residual exceeds its signal; weight must be zero"
    assert fet["southernoceanpac"] > fet["natlsubpolar"] > fet["eqpac"], (
        f"adequacy must order the basins sopac > natl > eqpac, got {fet}"
    )


@pytest.mark.skipif(not RULE.exists(), reason="adequacy rule artifact not emitted")
def test_rule_never_recorded_the_answer():
    """theta_0 is the prior midpoint, so it must NOT coincide with Carroll's values."""
    from darwindiff.carroll6 import PARAMS

    rule = json.loads(RULE.read_text(encoding="utf-8"))
    for p in PARAMS:
        got = rule["theta_0"][p.name]
        assert got != pytest.approx(p.carroll_value, rel=1e-6), (
            f"{p.name} theta_0 equals its Carroll value -- the rule saw the answer"
        )
