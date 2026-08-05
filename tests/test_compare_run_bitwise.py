"""The reproducibility comparator must fail loudly when it compares nothing.

The bug this guards against shipped and produced a headline. `grade_window_swap.sbatch` read
``params[k]['joint']`` from artifacts that store ``joint_recovered``. Every lookup returned
``None``, every value was skipped, the running maximum stayed at its ``0.0`` initialiser, and
the control printed "max relative difference: 0.000e+00 -> BITWISE IDENTICAL" having compared
zero values. A reproducibility certificate was issued on an empty set.

This is the same shape as the research map's SUPERSEDES constraint, which passed on an empty
join since the day it was written. Both read exactly like success. So the property under test
is not "the comparator is correct on good input" -- it is "the comparator refuses to report
agreement when it had nothing to agree about."
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "analysis" / "compare_run_bitwise.py"

pytestmark = pytest.mark.skipif(not _SCRIPT.is_file(), reason=f"{_SCRIPT} not present")


def _artifact(d: Path, seed: int, value: float, field: str = "joint_recovered") -> None:
    d.mkdir(parents=True, exist_ok=True)
    payload = {
        "seed": seed,
        "params": {
            "alpfe": {
                field: value,
                "joint_carroll_published": 1.0,
                "per_aoi_recovered": {"eqpac": value},
            }
        },
    }
    (d / f"run_seed{seed}.json").write_text(json.dumps(payload), encoding="utf-8")


def _run(a: Path, b: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), str(a), str(b), *extra],
        capture_output=True, text=True,
    )


def test_identical_runs_report_bitwise_identical(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    for seed in range(3):
        _artifact(a, seed, 0.5)
        _artifact(b, seed, 0.5)
    res = _run(a, b)
    assert res.returncode == 0, res.stdout + res.stderr
    assert "BITWISE IDENTICAL" in res.stdout


def test_differing_runs_are_reported_as_differing(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    for seed in range(3):
        _artifact(a, seed, 0.5)
        _artifact(b, seed, 0.5 * 1.02)  # 2% apart
    res = _run(a, b)
    assert res.returncode == 1, res.stdout + res.stderr
    assert "DIFFERS" in res.stdout


def test_a_missing_field_is_vacuous_not_identical(tmp_path: Path) -> None:
    """The actual 2026-07-31 bug: the compared field does not exist on either side."""
    a, b = tmp_path / "a", tmp_path / "b"
    for seed in range(3):
        _artifact(a, seed, 0.5, field="some_renamed_field")
        _artifact(b, seed, 0.5, field="some_renamed_field")
    res = _run(a, b, "--min-values", "100")
    assert res.returncode == 2, (
        "a comparison that examined too few values must exit 2, not report agreement.\n"
        + res.stdout + res.stderr
    )
    assert "VACUOUS" in res.stdout
    assert "BITWISE IDENTICAL" not in res.stdout


def test_no_shared_seeds_is_vacuous(tmp_path: Path) -> None:
    """Two runs that share no seeds agree about nothing."""
    a, b = tmp_path / "a", tmp_path / "b"
    _artifact(a, 0, 0.5)
    _artifact(b, 99, 0.5)
    res = _run(a, b)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "VACUOUS" in res.stdout


def test_empty_directories_are_vacuous(tmp_path: Path) -> None:
    a, b = tmp_path / "a", tmp_path / "b"
    a.mkdir()
    b.mkdir()
    res = _run(a, b)
    assert res.returncode == 2, res.stdout + res.stderr
    assert "VACUOUS" in res.stdout
