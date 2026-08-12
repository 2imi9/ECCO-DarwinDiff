#!/usr/bin/env python
"""Build the complete, gate-aware fact table for loss-twin job 320993.

The result is deliberately tidy rather than a visually wide spreadsheet: one row is one
arm x parameter x pooler x tolerance-band cell. That preserves every experiment dimension
without hiding missing, excluded, or verifier-gated cells.

Numeric output is limited to the three parameters the pre-registered grader reads. The
remaining Carroll-6 parameters stay in the matrix with an explicit exclusion reason, and every
Southern Ocean numeric cell stays blank while ``verify_run`` exits non-zero.

Usage:
    python scripts/analysis/build_loss_twin_dimensional_matrix.py ROOT \
        --json docs/findings/2026-08-09_loss_twin_dimensional_matrix.json \
        --csv docs/findings/2026-08-09_loss_twin_dimensional_matrix.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

AS_OF = "2026-08-09"
SUBMISSION_JOB = 320993
GRADER_JOB = 320994
EXPECTED_N = 50
BANDS = (0.10, 0.20, 0.30, 0.40)
POOLERS = {
    "arithmetic": "per_aoi_recovered",
    "geometric": "per_aoi_recovered_geom",
    "median": "per_aoi_recovered_median",
}


@dataclass(frozen=True)
class ArmSpec:
    tag: str
    aoi: str
    target: str
    loss: str
    role: str


AOIS = {
    "eq": "eqpac",
    "na": "natlsubpolar",
    "so": "southernoceanpac",
}
ARM_SUFFIXES = {
    "ee": ("end", "endpoint", "matched-control"),
    "mm": ("mean", "time-mean", "matched-control"),
    "le": ("long", "endpoint", "decisive"),
    "lm": ("long", "time-mean", "decisive"),
    "null": ("untrained", "none", "untrained-null"),
}
ARMS = tuple(
    ArmSpec(
        tag=f"{prefix}_{suffix}",
        aoi=aoi,
        target=target,
        loss=loss,
        role=role,
    )
    for prefix, aoi in AOIS.items()
    for suffix, (target, loss, role) in ARM_SUFFIXES.items()
)


PARAMETER_ROLES = {
    "alpfe": {
        "role": "boundary-diagnostic-only",
        "numeric": True,
        "note": "Recorded as a harness diagnostic; bound geometry is not accuracy.",
    },
    "scav_rat": {
        "role": "primary-inferential-target",
        "numeric": True,
        "note": "Read under geometric pooling with arithmetic and median beside it.",
    },
    "R_PICPOC": {
        "role": "twin-anchor-machinery-check",
        "numeric": True,
        "note": "Synthetic Daniels-anchor check, not a real-ocean recovery result.",
    },
    "diatomgraz": {
        "role": "excluded-from-loss-decision",
        "numeric": False,
        "note": "Long-target Chl1 pathology makes this parameter non-gradeable here.",
    },
    "Smallgrow": {
        "role": "excluded-by-construction",
        "numeric": False,
        "note": "No time-mean observable independently identifies this parameter.",
    },
    "Biggrow": {
        "role": "excluded-by-construction",
        "numeric": False,
        "note": "Unobservable by the staged target construction.",
    },
}
PARAMETER_ORDER = (
    "alpfe",
    "scav_rat",
    "Smallgrow",
    "Biggrow",
    "diatomgraz",
    "R_PICPOC",
)


def _load_arm(root: Path, spec: ArmSpec) -> list[dict[str, Any]]:
    run_dir = root / spec.tag
    files = sorted(run_dir.glob("*.json"))
    if len(files) != EXPECTED_N:
        raise ValueError(f"{spec.tag}: expected {EXPECTED_N} JSON artifacts, found {len(files)}")
    rows = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    seeds = sorted(row.get("seed") for row in rows)
    if seeds != list(range(EXPECTED_N)):
        raise ValueError(f"{spec.tag}: expected seeds 0..49, found {seeds}")
    for row in rows:
        if row.get("aois") != [spec.aoi]:
            raise ValueError(f"{spec.tag}: artifact AOI does not match {spec.aoi}")
        if set(row.get("params", {})) != set(PARAMETER_ORDER):
            raise ValueError(f"{spec.tag}: Carroll-6 parameter set is incomplete")
    return rows


def _verify(repo_root: Path, run_dir: Path) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "verify_run.py"), str(run_dir)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    output = (proc.stdout + proc.stderr).strip().splitlines()
    detail = next((line.strip() for line in reversed(output) if "==> exit" in line), "")
    return proc.returncode, detail


def _median_ratio(rows: list[dict[str, Any]], param: str, key: str, aoi: str) -> float:
    truth = rows[0]["params"][param]["joint_carroll_published"]
    values = [row["params"][param][key][aoi] for row in rows]
    return statistics.median(values) / truth


def _median_log_sd(rows: list[dict[str, Any]], param: str, aoi: str) -> float | None:
    values = [
        row["params"][param].get("per_aoi_log_sd", {}).get(aoi)
        for row in rows
    ]
    values = [value for value in values if value is not None]
    return statistics.median(values) if values else None


def _count(rows: list[dict[str, Any]], param: str, key: str, aoi: str, band: float) -> int:
    truth = rows[0]["params"][param]["joint_carroll_published"]
    return sum(
        abs(row["params"][param][key][aoi] - truth) / abs(truth) <= band
        for row in rows
    )


def _binom_ge(k: int, n: int, p: float) -> float:
    p = min(max(p, 1e-12), 1 - 1e-12)
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _p_value(count: int, null_count: int) -> float:
    # Match pooler_audit.py: when the observed null is zero, use the rule-of-three floor.
    chance = max(null_count / EXPECTED_N, 3.0 / EXPECTED_N)
    return _binom_ge(count, EXPECTED_N, chance)


def _coverage(rows: list[dict[str, Any]], aoi: str) -> dict[str, Any]:
    first = rows[0]
    daniels = first.get("n_daniels_cells_per_aoi", {}).get(aoi, 0)
    posi = first.get("n_posi_cells_per_aoi", {}).get(aoi, 0)
    return {
        "daniels_declared_weight": first.get("daniels_rpicpoc_w"),
        "daniels_active_cells": daniels,
        "posi_declared_weight": first.get("posi_w"),
        "posi_active_cells": posi,
        "state": "active" if daniels and posi else "declared-on-zero-coverage",
    }


def build(root: Path, repo_root: Path) -> dict[str, Any]:
    loaded = {spec.tag: _load_arm(root, spec) for spec in ARMS}
    verifier = {
        spec.tag: _verify(repo_root, root / spec.tag)
        for spec in ARMS
    }
    records: list[dict[str, Any]] = []
    arms: list[dict[str, Any]] = []

    for spec in ARMS:
        rows = loaded[spec.tag]
        verify_exit, verify_detail = verifier[spec.tag]
        coverage = _coverage(rows, spec.aoi)
        twin_report = rows[0].get("twin_report") or {}
        aoi_report = (twin_report.get("per_aoi") or {}).get(spec.aoi, {})
        arms.append(
            {
                "arm": spec.tag,
                "aoi": spec.aoi,
                "forcing": "constant",
                "target": spec.target,
                "loss": spec.loss,
                "role": spec.role,
                "n": len(rows),
                "seed_min": 0,
                "seed_max": 49,
                "verify_run": verify_exit,
                "verify_detail": verify_detail,
                "coverage": coverage,
                "target_steps": (
                    twin_report.get("twin_long_steps")
                    if spec.target == "long"
                    else rows[0].get("n_steps")
                ),
                "degenerate_targets": aoi_report.get("degenerate_targets", []),
                "replicated": False,
            }
        )

        null_spec = f"{spec.tag[:2]}_null"
        null_rows = loaded[null_spec]
        null_verify_exit = verifier[null_spec][0]
        for param in PARAMETER_ORDER:
            param_meta = PARAMETER_ROLES[param]
            for pooler, key in POOLERS.items():
                arm_median = _median_ratio(rows, param, key, spec.aoi)
                null_median = _median_ratio(null_rows, param, key, spec.aoi)
                log_sd = _median_log_sd(rows, param, spec.aoi)
                for band in BANDS:
                    reporting_status = "reported"
                    suppression_reason = ""
                    count: int | None = None
                    null_count: int | None = None
                    p_value: float | None = None

                    if verify_exit != 0 or null_verify_exit != 0:
                        reporting_status = "gated"
                        suppression_reason = (
                            "verify_run is non-zero; fitted counts and medians are not evidence"
                        )
                    elif not param_meta["numeric"]:
                        reporting_status = "excluded"
                        suppression_reason = param_meta["note"]
                    else:
                        count = _count(rows, param, key, spec.aoi, band)
                        null_count = _count(null_rows, param, key, spec.aoi, band)
                        if spec.role != "untrained-null":
                            p_value = _p_value(count, null_count)

                    records.append(
                        {
                            "as_of": AS_OF,
                            "submission_job": SUBMISSION_JOB,
                            "grader_job": GRADER_JOB,
                            "arm": spec.tag,
                            "aoi": spec.aoi,
                            "forcing": "constant",
                            "target": spec.target,
                            "loss": spec.loss,
                            "arm_role": spec.role,
                            "n": len(rows),
                            "verify_run": verify_exit,
                            "coverage_state": coverage["state"],
                            "parameter": param,
                            "parameter_role": param_meta["role"],
                            "pooler": pooler,
                            "band": band,
                            "count": count,
                            "null_count": null_count,
                            "p_value": p_value,
                            "median_x_truth": (
                                arm_median if reporting_status == "reported" else None
                            ),
                            "null_median_x_truth": (
                                null_median if reporting_status == "reported" else None
                            ),
                            "per_cell_log_sd_median": (
                                log_sd if reporting_status == "reported" else None
                            ),
                            "reporting_status": reporting_status,
                            "suppression_reason": suppression_reason,
                            "replicated": False,
                            "submission_count": 1,
                        }
                    )

    return {
        "schema_version": 1,
        "as_of": AS_OF,
        "scope": "constant-forcing loss-comparison self-twin",
        "jobs": {"submission": SUBMISSION_JOB, "grader": GRADER_JOB},
        "dimensions": {
            "arms": len(ARMS),
            "aois": list(AOIS.values()),
            "forcing": ["constant"],
            "targets": ["end", "mean", "long", "untrained"],
            "losses": ["endpoint", "time-mean", "none"],
            "parameters": list(PARAMETER_ORDER),
            "poolers": list(POOLERS),
            "bands": list(BANDS),
            "replication": ["one submission; no replication"],
        },
        "parameter_roles": PARAMETER_ROLES,
        "reporting_rules": [
            "Southern Ocean numeric cells are suppressed while verify_run is non-zero.",
            "alpfe is a boundary diagnostic only and is never interpreted as accuracy.",
            "scav_rat is read geometrically with arithmetic and median beside it.",
            "R_PICPOC is a regenerated-anchor machinery check in this synthetic twin.",
            "Smallgrow, Biggrow, and diatomgraz remain present as excluded matrix cells.",
            "All measured cells are one submission and unreplicated.",
        ],
        "arms": arms,
        "records": records,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path, help="directory containing the 15 arm directories")
    parser.add_argument("--json", dest="json_path", type=Path, required=True)
    parser.add_argument("--csv", dest="csv_path", type=Path, required=True)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    payload = build(args.root.resolve(), repo_root)
    _write_json(args.json_path, payload)
    _write_csv(args.csv_path, payload["records"])

    status_counts: dict[str, int] = {}
    for record in payload["records"]:
        status = record["reporting_status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    print(
        f"wrote {len(payload['records'])} cells across {len(payload['arms'])} arms; "
        f"status={status_counts}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
