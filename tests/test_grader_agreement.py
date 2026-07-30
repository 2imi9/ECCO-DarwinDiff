"""All independent implementations of the per-AOI majority rule must agree.

Eight files implement this rule independently. On 2026-07-30 TWO of them were
provably wrong (hardcoded >=2, so any single-AOI run graded 0/n regardless of what
it recovered). A cross-check on the cited runs showed no PUBLISHED number moved --
the bug was latent, because every published run is 3-AOI where all implementations
use >=2 identically -- but nothing prevented the next divergence.

This runs the agreement check on synthetic fixtures so it works in CI with no
cluster data. The full check against real run directories is
scripts/analysis/grader_crosscheck.py.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from darwindiff.carroll6 import PARAMS  # noqa: E402

X = importlib.util.spec_from_file_location(
    "_crosscheck", REPO / "scripts/analysis/grader_crosscheck.py")
CC = importlib.util.module_from_spec(X)
sys.modules["_crosscheck"] = CC
X.loader.exec_module(CC)


def _write(d: Path, aois: list[str], recovered: dict[str, bool], n: int = 6) -> None:
    """A run where each parameter is on Carroll (recovered) or 10x off, in every AOI."""
    for s in range(n):
        params = {}
        for p in PARAMS:
            v = p.carroll_value if recovered.get(p.name) else p.carroll_value * 10.0
            params[p.name] = {
                "joint_recovered": v,
                "joint_carroll_published": p.carroll_value,
                "joint_band": "Excellent" if recovered.get(p.name) else "Drifted",
                "per_aoi_recovered": {a: v for a in aois},
            }
        (d / f"seed{s}.json").write_text(
            json.dumps({"seed": s, "n_seeds_in_batch": n, "params": params}), encoding="utf-8")


THREE = ["eqpac", "natlsubpolar", "southernoceanpac"]


@pytest.mark.parametrize("aois,label", [(THREE, "3-AOI"), (["eqpac"], "single-AOI")])
def test_all_graders_agree(tmp_path, aois, label):
    """verify_run, grade_all_params and an independent reimplementation must match.

    The single-AOI case is the one that was broken. It is parametrized here so a
    regression fails loudly instead of quietly returning zeros.
    """
    rec = {"alpfe": True, "R_PICPOC": True}     # two recovered, four not
    _write(tmp_path, aois, rec)

    e_counts, e_trio, n = CC.independent_counts(str(tmp_path))
    a_counts, a_status, a_n = CC.verify_run_counts(str(tmp_path))
    c_counts, c_n = CC.grade_all_params_counts(str(tmp_path))

    assert n == a_n == c_n == 6
    assert a_status == "VERIFIED"
    for p in PARAMS:
        vals = {e_counts[p.name], a_counts.get(p.name), c_counts.get(p.name)}
        assert len(vals) == 1, f"{label} {p.name}: graders disagree -> {vals}"
        expected = 6 if rec.get(p.name) else 0
        assert e_counts[p.name] == expected, (
            f"{label} {p.name}: got {e_counts[p.name]}/6, expected {expected}/6")


def test_single_aoi_is_not_silently_zero(tmp_path):
    """The exact regression: everything recovered, one AOI, must NOT grade 0."""
    _write(tmp_path, ["eqpac"], {p.name: True for p in PARAMS})
    e_counts, _, n = CC.independent_counts(str(tmp_path))
    c_counts, _ = CC.grade_all_params_counts(str(tmp_path))
    for p in PARAMS:
        assert e_counts[p.name] == n, f"independent rule zeroed {p.name} on a single-AOI run"
        assert c_counts.get(p.name) == n, f"grade_all_params zeroed {p.name} on a single-AOI run"


def test_a_one_of_three_majority_never_counts(tmp_path):
    """And the multi-AOI rule must stay strict: 1-of-3 is not a majority."""
    for s in range(6):
        params = {}
        for p in PARAMS:
            params[p.name] = {
                "joint_recovered": p.carroll_value,
                "joint_carroll_published": p.carroll_value,
                "joint_band": "Excellent",
                "per_aoi_recovered": {
                    "eqpac": p.carroll_value,
                    "natlsubpolar": p.carroll_value * 10.0,
                    "southernoceanpac": p.carroll_value * 10.0,
                },
            }
        (tmp_path / f"seed{s}.json").write_text(
            json.dumps({"seed": s, "n_seeds_in_batch": 6, "params": params}), encoding="utf-8")
    e_counts, e_trio, _ = CC.independent_counts(str(tmp_path))
    c_counts, _ = CC.grade_all_params_counts(str(tmp_path))
    for p in PARAMS:
        assert e_counts[p.name] == 0, f"{p.name}: a 1-of-3 majority counted"
        assert c_counts.get(p.name, 0) == 0, f"{p.name}: grade_all_params counted 1-of-3"
    assert e_trio == 0
