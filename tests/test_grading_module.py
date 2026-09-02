"""One definition of the per-AOI recovery rule, and every caller must agree with it.

On 2026-07-30 the rule had eight independent implementations across `scripts/`, and
FOUR of them hardcoded `>= 2`, which grades any single-AOI run 0/n regardless of what
it recovered. Two had been fixed the same day; `grade_joint_percell`, `per_aoi_leg_audit`,
`aggregate_daniels_recovery` and `aggregate_rpicpoc_env` had not.

The duplication is the hazard, not any one copy. These tests pin three things:

  1. `darwindiff.grading` implements the rule correctly, including the edges where the
     hardcoded copies were wrong.
  2. Every caller routes through it, checked by importing each script and running it on
     the same fixtures. This is what would have caught the four stragglers.
  3. No new hardcoded threshold reappears, checked against the source text.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "src") not in sys.path:
    sys.path.insert(0, str(REPO / "src"))

from darwindiff.grading import (  # noqa: E402
    CAL_PLUS,
    count_cal_plus_legs,
    is_cal_plus,
    is_recovered_per_aoi,
    relative_offset,
    required_legs,
    straddles,
)

CARROLL = 1.0
INSIDE = 1.2   # rel 0.20, Cal-grade
OUTSIDE = 2.0  # rel 1.00, Drifted


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(f"_g_{Path(rel).stem}", REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. the rule itself
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n, want", [(0, 1), (1, 1), (2, 2), (3, 2)])
def test_required_legs_matches_the_documented_rule(n, want):
    assert required_legs(n) == want


def test_single_aoi_run_is_graded_on_its_one_leg():
    """The regression the hardcoded `>= 2` caused: 1-of-1 must be recovery."""
    assert is_recovered_per_aoi({"eqpac": INSIDE}, CARROLL) is True
    assert is_recovered_per_aoi({"eqpac": OUTSIDE}, CARROLL) is False


def test_three_aoi_run_needs_two_legs():
    a, b, c = "eqpac", "natlsubpolar", "southernoceanpac"
    assert is_recovered_per_aoi({a: INSIDE, b: INSIDE, c: OUTSIDE}, CARROLL) is True
    assert is_recovered_per_aoi({a: INSIDE, b: OUTSIDE, c: OUTSIDE}, CARROLL) is False


def test_no_aois_is_never_recovered():
    assert is_recovered_per_aoi({}, CARROLL) is False
    assert is_recovered_per_aoi(None, CARROLL) is False


@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"), "not-a-number"])
def test_unusable_values_are_never_recovered(bad):
    """A broken record must never score as a success."""
    assert is_cal_plus(bad, CARROLL) is False
    assert relative_offset(bad, CARROLL) == float("inf")


def test_zero_carroll_reference_is_never_recovered():
    """Relative offset is undefined against zero; it must not divide by it."""
    assert relative_offset(0.0, 0.0) == float("inf")
    assert is_cal_plus(0.0, 0.0) is False


def test_band_boundary_is_forty_percent_inclusive():
    assert is_cal_plus(1.40, 1.0) is True     # rel 0.40 exactly
    assert is_cal_plus(1.4001, 1.0) is False


def test_cal_plus_is_excellent_or_cal_grade():
    assert {"Excellent", "Cal-grade"} == CAL_PLUS
    assert count_cal_plus_legs({"a": INSIDE, "b": OUTSIDE, "c": 1.01}, CARROLL) == 2


def test_straddle_is_a_multi_aoi_concept():
    """Cell-weighted claims recovery, per-AOI refuses it."""
    legs = {"a": INSIDE, "b": OUTSIDE, "c": OUTSIDE}
    assert straddles(legs, CARROLL, "Cal-grade") is True
    assert straddles({"a": INSIDE, "b": INSIDE, "c": OUTSIDE}, CARROLL, "Cal-grade") is False
    # with one AOI the two metrics are the same measurement
    assert straddles({"a": OUTSIDE}, CARROLL, "Cal-grade") is False


# ---------------------------------------------------------------------------
# 2. every caller agrees, on the same fixtures
# ---------------------------------------------------------------------------
def _write_seeds(d: Path, legs: dict[str, float], n: int = 3) -> None:
    """Seed JSONs whose every parameter carries the given per-AOI legs."""
    from darwindiff.carroll6 import PARAMS

    for s in range(n):
        params = {}
        for p in PARAMS:
            per_aoi = {a: p.carroll_value * mult for a, mult in legs.items()}
            # The joint value sits exactly on Carroll, so the stored band must be
            # "Excellent" or verify_run rightly reports a stored-vs-recomputed
            # DISCREPANCY. Deriving it from the per-AOI verdict instead would make the
            # fixture self-inconsistent. With minority legs this is a genuine STRADDLE:
            # cell-weighted claims recovery and per-AOI refuses it.
            params[p.name] = {
                "joint_recovered": p.carroll_value,
                "joint_carroll_published": p.carroll_value,
                "joint_aoiweighted_recovered": p.carroll_value,
                "joint_band": "Excellent",
                "joint_cellweighted_band": "Excellent",
                "per_aoi_recovered": per_aoi,
            }
        (d / f"seed{s}.json").write_text(
            json.dumps({"seed": s, "n_seeds_in_batch": n, "params": params}), encoding="utf-8"
        )


THREE_AOI_MAJORITY = {"eqpac": 1.2, "natlsubpolar": 1.2, "southernoceanpac": 3.0}
THREE_AOI_MINORITY = {"eqpac": 1.2, "natlsubpolar": 3.0, "southernoceanpac": 3.0}
SINGLE_AOI_GOOD = {"eqpac": 1.2}
SINGLE_AOI_BAD = {"eqpac": 3.0}


@pytest.mark.parametrize(
    "legs, expect",
    [
        (THREE_AOI_MAJORITY, True),
        (THREE_AOI_MINORITY, False),
        (SINGLE_AOI_GOOD, True),   # the case four implementations got wrong
        (SINGLE_AOI_BAD, False),
    ],
)
def test_verify_run_agrees_with_the_module(tmp_path, legs, expect):
    V = _load("scripts/verify_run.py")
    _write_seeds(tmp_path, legs)
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    for p in V.PARAMS:
        got = res["per_param_per_aoi"][p] == 3  # all 3 seeds identical by construction
        assert got is expect, f"verify_run disagrees for {p} on {legs}"


@pytest.mark.parametrize(
    "legs, expect",
    [
        (THREE_AOI_MAJORITY, True),
        (THREE_AOI_MINORITY, False),
        (SINGLE_AOI_GOOD, True),
        (SINGLE_AOI_BAD, False),
    ],
)
def test_grade_all_params_agrees_with_the_module(tmp_path, legs, expect):
    G = _load("scripts/analysis/grade_all_params.py")
    _write_seeds(tmp_path, legs)
    counts, n, _ = G.per_aoi_2of3(str(tmp_path))
    assert n == 3
    from darwindiff.carroll6 import PARAMS

    for p in PARAMS:
        assert (counts.get(p.name, 0) == 3) is expect, f"grade_all_params disagrees for {p.name}"


@pytest.mark.parametrize("script", [
    "scripts/analysis/grade_joint_percell.py",
    "scripts/analysis/per_aoi_leg_audit.py",
    "scripts/aggregate_daniels_recovery.py",
    "scripts/aggregate_rpicpoc_env.py",
    "scripts/analysis/contract_report.py",
])
def test_every_grading_script_imports_the_shared_threshold(script):
    """These four hardcoded `>= 2` until 2026-07-30. They must not re-derive it."""
    src = (REPO / script).read_text(encoding="utf-8")
    assert "required_legs" in src, f"{script} does not use the shared threshold"


# ---------------------------------------------------------------------------
# 3. no new hardcoded threshold
# ---------------------------------------------------------------------------
# Counting Cal-plus legs and comparing against a bare 2 is the exact bug. Match the
# comparison, not the literal, so unrelated `>= 2` uses (string parsing, argv length)
# do not trip it.
_HARDCODED = re.compile(
    r"(n_cal|n_aoi_cal|n_ok|good|n_legs|legs_ok|sum\(ok\.values\(\)\))\s*>=\s*2\b"
)

_GRADERS = [
    "scripts/verify_run.py",
    "scripts/analysis/grade_all_params.py",
    "scripts/analysis/grade_joint_percell.py",
    "scripts/analysis/per_aoi_leg_audit.py",
    "scripts/analysis/contract_report.py",
    "scripts/aggregate_daniels_recovery.py",
    "scripts/aggregate_rpicpoc_env.py",
]


@pytest.mark.parametrize("script", _GRADERS)
def test_no_grader_hardcodes_the_majority_threshold(script):
    path = REPO / script
    if not path.is_file():
        pytest.skip(f"{script} not present")
    offenders = [
        f"{script}:{i}: {line.strip()}"
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if _HARDCODED.search(line) and not line.lstrip().startswith("#")
    ]
    assert not offenders, (
        "hardcoded per-AOI majority threshold; use darwindiff.grading.required_legs:\n"
        + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# 4. an ungradable run must not exit 0
# ---------------------------------------------------------------------------
def _write_seeds_without_per_aoi(d: Path, n: int = 3) -> None:
    """Seeds carrying only the cell-weighted band, no per_aoi_recovered payload."""
    from darwindiff.carroll6 import PARAMS

    for s in range(n):
        params = {
            p.name: {
                "joint_recovered": p.carroll_value,
                "joint_carroll_published": p.carroll_value,
                "joint_band": "Excellent",
            }
            for p in PARAMS
        }
        (d / f"seed{s}.json").write_text(
            json.dumps({"seed": s, "n_seeds_in_batch": n, "params": params}), encoding="utf-8"
        )


def test_a_run_with_no_per_aoi_payload_is_ungraded_not_verified(tmp_path):
    """Uncomputable is not the same as clean, and must not read as clean.

    Every parameter would look Excellent on the cell-weighted band, so before this
    the run exited 0 VERIFIED while the honest metric could not be computed at all.
    """
    V = _load("scripts/verify_run.py")
    _write_seeds_without_per_aoi(tmp_path)
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "UNGRADED"
    assert V.SEVERITY[res["status"]] != 0, "an ungradable run must not exit 0"
    assert any("NO_PER_AOI_DATA" in f for f in res["flags"])


def test_a_straddle_stays_advisory_and_still_verifies(tmp_path):
    """A straddle is a real measurement, not a corruption; gating on it would be noise."""
    V = _load("scripts/verify_run.py")
    _write_seeds(tmp_path, THREE_AOI_MINORITY)
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "VERIFIED"
    assert V.SEVERITY[res["status"]] == 0
