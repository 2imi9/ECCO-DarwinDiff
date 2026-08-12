#!/usr/bin/env python
"""Verify the complete gate-aware fact table for loss-twin job 320993."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

try:
    from scripts.analysis.build_loss_twin_dimensional_matrix import (
        ARMS,
        BANDS,
        EXPECTED_N,
        GRADER_JOB,
        PARAMETER_ORDER,
        PARAMETER_ROLES,
        POOLERS,
        SUBMISSION_JOB,
    )
except ModuleNotFoundError:  # direct ``python scripts/analysis/...`` execution
    from build_loss_twin_dimensional_matrix import (  # type: ignore[no-redef]
        ARMS,
        BANDS,
        EXPECTED_N,
        GRADER_JOB,
        PARAMETER_ORDER,
        PARAMETER_ROLES,
        POOLERS,
        SUBMISSION_JOB,
    )

KEY_FIELDS = ("arm", "parameter", "pooler", "band")
SUPPRESSED_FIELDS = (
    "count",
    "null_count",
    "p_value",
    "median_x_truth",
    "null_median_x_truth",
    "per_cell_log_sd_median",
)
MATCHED_ARMS = ("eq_ee", "eq_mm", "na_ee", "na_mm")
LONG_ARMS = ("eq_le", "eq_lm", "na_le", "na_lm")


class VerificationError(RuntimeError):
    """Raised when the dimensional matrix violates its registered contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _cell(index: dict[tuple, dict], arm: str, pooler: str, band: float) -> dict:
    return index[(arm, "scav_rat", pooler, band)]


def _verify_csv(records: list[dict], csv_rows: list[dict[str, str]]) -> None:
    _require(len(csv_rows) == len(records), "CSV and JSON row counts differ")
    _require(bool(records), "matrix contains no records")
    expected_fields = list(records[0])
    _require(list(csv_rows[0]) == expected_fields, "CSV field order differs from JSON")
    for index, (record, csv_row) in enumerate(zip(records, csv_rows, strict=True)):
        for field in expected_fields:
            value = record[field]
            expected = "" if value is None else str(value)
            _require(
                csv_row[field] == expected,
                f"CSV row {index} field {field} differs: {csv_row[field]!r} != {expected!r}",
            )


def verify(payload: dict, csv_rows: list[dict[str, str]]) -> dict:
    """Verify dimensions, gates, suppression, and the bounded scav_rat result."""
    _require(payload.get("schema_version") == 1, "schema_version must be 1")
    _require(
        payload.get("jobs") == {"submission": SUBMISSION_JOB, "grader": GRADER_JOB},
        "job ids differ from the registered submission",
    )
    dimensions = payload["dimensions"]
    _require(dimensions["arms"] == len(ARMS), "arm count differs")
    _require(dimensions["parameters"] == list(PARAMETER_ORDER), "parameter order differs")
    _require(dimensions["poolers"] == list(POOLERS), "pooler set differs")
    _require(dimensions["bands"] == list(BANDS), "band set differs")
    _require(
        dimensions["replication"] == ["one submission; no replication"],
        "replication boundary differs",
    )

    expected_arms = {spec.tag: spec for spec in ARMS}
    arms = payload["arms"]
    _require(len(arms) == len(expected_arms), "arm metadata count differs")
    arm_index = {arm["arm"]: arm for arm in arms}
    _require(set(arm_index) == set(expected_arms), "arm metadata set differs")
    for tag, spec in expected_arms.items():
        arm = arm_index[tag]
        _require(arm["aoi"] == spec.aoi, f"{tag}: AOI differs")
        _require(arm["target"] == spec.target, f"{tag}: target differs")
        _require(arm["loss"] == spec.loss, f"{tag}: loss differs")
        _require(arm["role"] == spec.role, f"{tag}: role differs")
        _require(arm["n"] == EXPECTED_N, f"{tag}: n must be {EXPECTED_N}")
        _require((arm["seed_min"], arm["seed_max"]) == (0, 49), f"{tag}: seed range differs")
        _require(arm["replicated"] is False, f"{tag}: must remain unreplicated")
        expected_exit = 2 if spec.aoi == "southernoceanpac" else 0
        _require(arm["verify_run"] == expected_exit, f"{tag}: verifier exit differs")
        expected_coverage = (
            "declared-on-zero-coverage" if expected_exit else "active"
        )
        _require(
            arm["coverage"]["state"] == expected_coverage,
            f"{tag}: coverage state differs",
        )

    records = payload["records"]
    expected_keys = {
        (spec.tag, parameter, pooler, band)
        for spec in ARMS
        for parameter in PARAMETER_ORDER
        for pooler in POOLERS
        for band in BANDS
    }
    _require(len(records) == len(expected_keys), "record count differs from full factorial")
    record_index = {tuple(record[field] for field in KEY_FIELDS): record for record in records}
    _require(len(record_index) == len(records), "duplicate matrix key")
    _require(set(record_index) == expected_keys, "matrix is missing or adding design cells")

    status_counts = {"reported": 0, "excluded": 0, "gated": 0}
    for key, record in record_index.items():
        arm_tag, parameter, pooler, band = key
        spec = expected_arms[arm_tag]
        _require(record["submission_job"] == SUBMISSION_JOB, f"{key}: submission differs")
        _require(record["grader_job"] == GRADER_JOB, f"{key}: grader differs")
        _require(record["aoi"] == spec.aoi, f"{key}: AOI differs")
        _require(record["target"] == spec.target, f"{key}: target differs")
        _require(record["loss"] == spec.loss, f"{key}: loss differs")
        _require(record["arm_role"] == spec.role, f"{key}: role differs")
        _require(record["n"] == EXPECTED_N, f"{key}: n differs")
        _require(record["replicated"] is False, f"{key}: replicated flag differs")
        _require(record["submission_count"] == 1, f"{key}: submission count differs")
        _require(
            record["parameter_role"] == PARAMETER_ROLES[parameter]["role"],
            f"{key}: parameter role differs",
        )
        _require(pooler in POOLERS and band in BANDS, f"{key}: unknown pooler or band")

        if spec.aoi == "southernoceanpac":
            expected_status = "gated"
        elif not PARAMETER_ROLES[parameter]["numeric"]:
            expected_status = "excluded"
        else:
            expected_status = "reported"
        _require(record["reporting_status"] == expected_status, f"{key}: status differs")
        status_counts[expected_status] += 1

        if expected_status != "reported":
            _require(
                all(record[field] is None for field in SUPPRESSED_FIELDS),
                f"{key}: gated or excluded values leaked",
            )
        else:
            _require(record["verify_run"] == 0, f"{key}: reported despite verifier failure")
            _require(isinstance(record["count"], int), f"{key}: count missing")
            _require(isinstance(record["null_count"], int), f"{key}: null count missing")
            _require(0 <= record["count"] <= EXPECTED_N, f"{key}: count out of range")
            _require(0 <= record["null_count"] <= EXPECTED_N, f"{key}: null out of range")
            _require(math.isfinite(record["median_x_truth"]), f"{key}: median missing")
            _require(math.isfinite(record["null_median_x_truth"]), f"{key}: null median missing")
            if spec.role == "untrained-null":
                _require(record["p_value"] is None, f"{key}: null arm has a p-value")
            else:
                _require(
                    isinstance(record["p_value"], int | float)
                    and math.isfinite(record["p_value"]),
                    f"{key}: fitted arm p-value missing",
                )

    _require(
        status_counts == {"reported": 360, "excluded": 360, "gated": 360},
        f"reporting lane counts differ: {status_counts}",
    )

    for arm in MATCHED_ARMS:
        for pooler in POOLERS:
            cell = _cell(record_index, arm, pooler, 0.20)
            _require(cell["count"] == 50, f"{arm}/{pooler}: matched count is not 50")
            _require(cell["null_count"] == 0, f"{arm}/{pooler}: matched null is not 0")
    for arm in LONG_ARMS:
        for pooler in POOLERS:
            for band in BANDS:
                cell = _cell(record_index, arm, pooler, band)
                _require(cell["count"] == 0, f"{arm}/{pooler}/{band}: long count is not 0")
                _require(cell["null_count"] == 0, f"{arm}/{pooler}/{band}: long null is not 0")

    _verify_csv(records, csv_rows)
    return {
        "verified": True,
        "submission_job": SUBMISSION_JOB,
        "grader_job": GRADER_JOB,
        "arms": len(arms),
        "records": len(records),
        "status_counts": status_counts,
        "replication": "one submission; no replication",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix_json", type=Path)
    parser.add_argument("matrix_csv", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args(argv)
    try:
        payload = json.loads(args.matrix_json.read_text(encoding="utf-8"))
        with args.matrix_csv.open(newline="", encoding="utf-8") as handle:
            csv_rows = list(csv.DictReader(handle))
        result = verify(payload, csv_rows)
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        json.JSONDecodeError,
        VerificationError,
    ) as exc:
        print(f"LOSS-TWIN MATRIX VERIFICATION FAILED: {exc}")
        return 1

    if args.receipt is not None:
        receipt = {
            **result,
            "verified_utc": datetime.now(UTC).isoformat(),
            "matrix_json": str(args.matrix_json),
            "matrix_json_sha256": _sha256(args.matrix_json),
            "matrix_csv": str(args.matrix_csv),
            "matrix_csv_sha256": _sha256(args.matrix_csv),
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    print(
        f"VERIFIED loss-twin matrix: arms={result['arms']} records={result['records']} "
        f"status={result['status_counts']} replication={result['replication']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
