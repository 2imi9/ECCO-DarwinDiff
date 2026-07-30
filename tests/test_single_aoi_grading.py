"""The per-AOI majority rule must degrade to >=1-of-1 for a SINGLE-AOI run.

Why this exists. `verify_run.py` has always handled it (:263-270), but
`scripts/analysis/grade_all_params.py` and `scripts/analysis/contract_report.py`
both hardcoded `>= 2`, so every single-AOI run graded as 0/n no matter what it
recovered.

That is not a corner case. A global-scalar fit produces the SAME value in every
AOI, so a 3-AOI global-scalar run has three identical legs and the 2-of-3 rule
degenerates to 1-of-1 anyway; the well-posed design is three separate single-AOI
runs. `main` pre-registered exactly that as the correct estimator for an
observations-only fit, where 96.1% of cells receive no gradient and the per-cell
DINN is ~7x under-determined. With the hardcoded 2, that experiment would have
returned 0/50 for everything and been read as a null result.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
from darwindiff.carroll6 import PARAMS  # noqa: E402


def _load(rel: str):
    spec = importlib.util.spec_from_file_location(f"_m_{Path(rel).stem}", REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _write_run(d: Path, aois: list[str], on_carroll: bool = True, n: int = 4) -> None:
    """A run whose parameters sit exactly on (or far off) Carroll in every named AOI."""
    for s in range(n):
        params = {}
        for p in PARAMS:
            v = p.carroll_value if on_carroll else p.carroll_value * 10.0
            params[p.name] = {
                "joint_recovered": v,
                "joint_carroll_published": p.carroll_value,
                "joint_band": "Excellent" if on_carroll else "Drifted",
                "per_aoi_recovered": {a: v for a in aois},
            }
        (d / f"seed{s}.json").write_text(
            json.dumps({"seed": s, "n_seeds_in_batch": n, "params": params}),
            encoding="utf-8",
        )


def test_verify_run_grades_a_single_aoi_run_on_its_one_leg(tmp_path):
    V = _load("scripts/verify_run.py")
    _write_run(tmp_path, ["eqpac"])
    res = V.verify_config_dir(tmp_path, expect_seeds=None)
    assert res["status"] == "VERIFIED"
    for p in V.PARAMS:
        assert res["per_param_per_aoi"][p] == 4, f"{p} should be 4/4 on its single leg"


def test_grade_all_params_grades_a_single_aoi_run(tmp_path):
    """The regression: this returned 0/n for every parameter before 2026-07-30."""
    G = _load("scripts/analysis/grade_all_params.py")
    _write_run(tmp_path, ["eqpac"])
    counts, n, aois = G.per_aoi_2of3(str(tmp_path))
    assert n == 4
    for p in PARAMS:
        assert counts[p.name] == 4, f"{p.name} graded {counts[p.name]}/4 on a single-AOI run"


def test_grade_all_params_still_requires_two_of_three_when_three_aois_present(tmp_path):
    """Guard the guard: the single-AOI branch must not weaken the 3-AOI rule."""
    G = _load("scripts/analysis/grade_all_params.py")
    # One AOI on Carroll, two far off -> a 1-of-3 majority must NOT count.
    for s in range(4):
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
            json.dumps({"seed": s, "n_seeds_in_batch": 4, "params": params}), encoding="utf-8"
        )
    counts, n, _ = G.per_aoi_2of3(str(tmp_path))
    assert n == 4
    for p in PARAMS:
        assert counts[p.name] == 0, (
            f"{p.name}: a 1-of-3 majority counted, so the single-AOI branch weakened "
            "the multi-AOI rule"
        )


def test_grade_all_params_is_importable_on_this_python(tmp_path):
    """It was a SyntaxError before Python 3.12.

    A backslash inside an f-string expression parses only on 3.12+, so the gate ran
    on the cluster and crashed on a 3.11 workstation. Running it as a subprocess is
    the only way to catch that, since a SyntaxError at import would fail collection
    rather than this test.
    """
    _write_run(tmp_path, ["eqpac", "natlsubpolar", "southernoceanpac"])
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/analysis/grade_all_params.py"), str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"grader failed to run: {r.stderr[-600:]}"
    assert "per-AOI" in r.stdout


def test_contract_report_is_importable_and_grades_single_aoi(tmp_path):
    _write_run(tmp_path, ["eqpac"])
    r = subprocess.run(
        [sys.executable, str(REPO / "scripts/analysis/contract_report.py"),
         "--run", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode in (0, 1, 7), f"unexpected exit {r.returncode}: {r.stderr[-600:]}"
    assert "IDENTIFIABILITY CONTRACT" in r.stdout
