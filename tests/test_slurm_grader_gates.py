"""Cluster graders must gate every fitted/null input and every secondary summary."""

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_TWIN = _ROOT / "scripts" / "slurm" / "grade_loss_twin.sbatch"
_BASIN = _ROOT / "scripts" / "slurm" / "grade_basin_x_loss.sbatch"

pytestmark = pytest.mark.skipif(
    not (_TWIN.is_file() and _BASIN.is_file()), reason="Slurm graders not present"
)


def test_both_twin_loops_gate_complete_verified_null() -> None:
    src = _TWIN.read_text(encoding="utf-8")
    matched = src.split("MATCHED CELLS", 1)[1].split("DECISIVE CELLS", 1)[0]
    decisive = src.split("DECISIVE CELLS", 1)[1].split("median recovered value", 1)[0]
    for section in (matched, decisive):
        assert "n_null=$(ls $S/$NUL/*.json" in section
        assert 'if [ "$n_null" -ne "$NEED" ]' in section
        assert "python scripts/verify_run.py $S/$NUL" in section
        assert "VERIFY FAILED NULL -- NOT GRADED" in section


@pytest.mark.parametrize("path", [_TWIN, _BASIN])
def test_pooler_failure_is_propagated_to_grader_exit(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    assert "POOLER_RC=$?" in src
    assert "POOLER AUDIT FAILED (exit=$POOLER_RC) -- NOT GRADED" in src
    assert "GRADE_FAILED=2" in src
    assert 'exit "$GRADE_FAILED"' in src


# Both graders now share one standard: label the arm n/NEED, refuse a partial arm or a partial
# null with an explicit NOT GRADED, and gate on verify_run's exit code for the arm and the null.
_PRIMARY_GATE_MARKERS = (
    "INCOMPLETE ($n of $NEED seeds)",
    "INCOMPLETE NULL ($n_null of $NEED seeds)",
    "VERIFY FAILED -- NOT GRADED",
    "VERIFY FAILED NULL -- NOT GRADED",
)


@pytest.mark.parametrize("path", [_TWIN, _BASIN])
def test_every_primary_gate_propagates_failure(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    for marker in _PRIMARY_GATE_MARKERS:
        positions = [match.start() for match in re.finditer(re.escape(marker), src)]
        assert positions, f"missing expected gate marker {marker!r}"
        for position in positions:
            block = src[max(0, position - 240) : position + 360]
            assert "GRADE_FAILED=2" in block, f"{marker!r} suppresses output but exits green"


@pytest.mark.parametrize("path", [_TWIN, _BASIN])
def test_median_summary_suppresses_incomplete_and_gated_runs(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    summary = src.split("median recovered value", 1)[1]
    assert "INCOMPLETE -- medians suppressed" in summary
    assert "subprocess.run(" in summary
    assert '"scripts/verify_run.py"' in summary
    assert "GATED (verify_run=" in summary
    assert "-- medians suppressed" in summary
    assert "geometric collapse unavailable" in summary


@pytest.mark.parametrize("path", [_TWIN, _BASIN])
def test_median_program_failure_is_propagated_to_grader_exit(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    summary = src.split("median recovered value", 1)[1]
    assert "SUMMARY_RC=$?" in summary
    assert 'if [ "$SUMMARY_RC" -ne 0 ]' in summary
    assert "MEDIAN SUMMARY FAILED (exit=$SUMMARY_RC)" in summary
    assert "GRADE_FAILED=2" in summary
    assert "summary_failed = True" in summary
    assert "raise SystemExit(2 if summary_failed else 0)" in summary


@pytest.mark.parametrize("path", [_TWIN, _BASIN])
def test_embedded_median_program_is_valid_python(path: Path) -> None:
    src = path.read_text(encoding="utf-8")
    program = src.split("python - <<'PYEOF'", 1)[1].split("\nPYEOF", 1)[0]
    compile(program, str(path), "exec")
