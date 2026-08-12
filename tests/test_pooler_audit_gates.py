from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "analysis" / "pooler_audit.py"


def _artifact(*, include_all_poolers: bool) -> dict:
    parameter = {
        "joint_carroll_published": 1.0,
        "per_aoi_recovered": {"eqpac": 1.0},
        "per_aoi_log_sd": {"eqpac": 0.1},
    }
    if include_all_poolers:
        parameter.update(
            {
                "per_aoi_recovered_geom": {"eqpac": 1.0},
                "per_aoi_recovered_median": {"eqpac": 1.0},
            }
        )
    return {"seed": 0, "params": {"scav_rat": parameter}}


def _write(directory: Path, payload: dict) -> None:
    directory.mkdir()
    (directory / "seed_0.json").write_text(json.dumps(payload), encoding="utf-8")


def _run(fitted: Path, null: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(fitted),
            "--null",
            str(null),
            "--params",
            "scav_rat",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_missing_null_collapse_keys_fail_the_audit(tmp_path: Path) -> None:
    fitted = tmp_path / "fitted"
    null = tmp_path / "null"
    _write(fitted, _artifact(include_all_poolers=True))
    _write(null, _artifact(include_all_poolers=False))

    result = _run(fitted, null)

    assert result.returncode == 2
    assert "NULL" in result.stdout
    assert "per_aoi_recovered_geom" in result.stdout


def test_complete_fitted_and_null_collapses_pass(tmp_path: Path) -> None:
    fitted = tmp_path / "fitted"
    null = tmp_path / "null"
    _write(fitted, _artifact(include_all_poolers=True))
    _write(null, _artifact(include_all_poolers=True))

    result = _run(fitted, null)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "scav_rat" in result.stdout
