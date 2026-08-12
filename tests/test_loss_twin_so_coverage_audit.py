from __future__ import annotations

import pytest
from scripts.analysis.audit_loss_twin_so_coverage import AuditError, audit, expected_aoi


def _logs() -> dict[int, bytes]:
    logs = {}
    for task in range(75):
        aoi = expected_aoi(task)
        lines = [f"[start] 2026-08-08 task={task} tag=t{task} AOIS={aoi}"]
        if aoi == "eqpac":
            lines.append("Daniels R_PICPOC target: 34 cells (123 samples)")
            lines.append("GEOTRACES bSi in-AOI surface bins (depth <= 50.0m): 7, mean target = 1")
        elif aoi == "natlsubpolar":
            lines.append("Daniels R_PICPOC target: 26 cells (116 samples)")
            lines.append("GEOTRACES bSi in-AOI surface bins (depth <= 50.0m): 4, mean target = 1")
        else:
            lines.append("[warn] no Daniels coverage in AOI; loss term will be skipped")
            lines.append("GEOTRACES bSi in-AOI surface bins (depth <= 50.0m): 0, mean target = 0")
        lines.append(f"=== rc=0 2026-08-08 tag=t{task} ===")
        logs[task] = ("\n".join(lines) + "\n").encode()
    return logs


def _sources() -> dict[str, int]:
    return {"/data/daniels.tab": 473302, "/data/geotraces.nc": 64566461}


def test_audit_distinguishes_expected_zero_from_staging_failure() -> None:
    result = audit(_logs(), _sources(), host="fixture")
    assert result["verified"] is True
    assert result["cause"] == "expected-geographic-zero-not-source-staging-failure"
    assert result["coverage"]["southernoceanpac"]["task_logs"] == 25
    assert result["coverage"]["southernoceanpac"]["source_failure_markers"] == 0
    assert str(result["reporting"]).startswith("excluded:")


def test_audit_rejects_a_missing_expected_zero_warning() -> None:
    logs = _logs()
    logs[40] = logs[40].replace(b"no Daniels coverage in AOI", b"coverage unavailable")
    with pytest.raises(AuditError, match="expected-zero Daniels warning missing"):
        audit(logs, _sources(), host="fixture")


def test_audit_rejects_nonzero_so_coverage() -> None:
    logs = _logs()
    logs[40] = logs[40].replace(
        b"surface bins (depth <= 50.0m): 0",
        b"surface bins (depth <= 50.0m): 1",
    )
    with pytest.raises(AuditError, match="expected zero bSi cells"):
        audit(logs, _sources(), host="fixture")


def test_audit_rejects_source_failure_text() -> None:
    logs = _logs()
    logs[40] += b"Daniels load failed\n"
    with pytest.raises(AuditError, match="source failure text"):
        audit(logs, _sources(), host="fixture")
