from __future__ import annotations

import copy
import csv
import json
from pathlib import Path

import pytest
from scripts.analysis.verify_loss_twin_dimensional_matrix import (
    VerificationError,
    verify,
)

ROOT = Path(__file__).resolve().parents[1]
MATRIX_JSON = ROOT / "docs" / "findings" / "2026-08-09_loss_twin_dimensional_matrix.json"
MATRIX_CSV = ROOT / "docs" / "findings" / "2026-08-09_loss_twin_dimensional_matrix.csv"


def _artifacts() -> tuple[dict, list[dict[str, str]]]:
    payload = json.loads(MATRIX_JSON.read_text(encoding="utf-8"))
    with MATRIX_CSV.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    return payload, rows


def test_matrix_verifier_accepts_complete_gated_artifact() -> None:
    payload, rows = _artifacts()
    result = verify(payload, rows)
    assert result["verified"] is True
    assert result["status_counts"] == {"reported": 360, "excluded": 360, "gated": 360}
    assert result["replication"] == "one submission; no replication"


def test_matrix_verifier_rejects_gated_value_leak() -> None:
    payload, rows = _artifacts()
    tampered = copy.deepcopy(payload)
    cell = next(
        record
        for record in tampered["records"]
        if record["arm"] == "so_ee"
        and record["parameter"] == "scav_rat"
        and record["pooler"] == "geometric"
        and record["band"] == 0.2
    )
    cell["count"] = 50
    with pytest.raises(VerificationError, match="values leaked"):
        verify(tampered, rows)


def test_matrix_verifier_rejects_matched_control_drift() -> None:
    payload, rows = _artifacts()
    tampered = copy.deepcopy(payload)
    cell = next(
        record
        for record in tampered["records"]
        if record["arm"] == "eq_ee"
        and record["parameter"] == "scav_rat"
        and record["pooler"] == "geometric"
        and record["band"] == 0.2
    )
    cell["count"] = 49
    with pytest.raises(VerificationError, match="matched count"):
        verify(tampered, rows)


def test_matrix_verifier_rejects_csv_json_disagreement() -> None:
    payload, rows = _artifacts()
    tampered_rows = copy.deepcopy(rows)
    tampered_rows[0]["count"] = "999"
    with pytest.raises(VerificationError, match="CSV row 0 field count differs"):
        verify(payload, tampered_rows)
