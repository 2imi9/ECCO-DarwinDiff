#!/usr/bin/env python
"""Independently verify the discrete frozen-path large-Z relocation bound."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
AOI_SHAPES = {
    "eqpac": (21, 51),
    "natlsubpolar": (16, 31),
    "southernoceanpac": (16, 81),
}
OCEAN_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_discrete_large_z_transport_oracle.md"
)
DT = 0.25
STEPS_PER_MONTH = 122
MONTHS = 12
TOTAL_STEPS = MONTHS * STEPS_PER_MONTH
SOURCE_PREY_FLOOR_C = 1.2e-8
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
MORTALITY_PER_DAY = 1.0 / 30.0
LOG_REPRODUCTION_ATOL = 5.0e-4


class VerificationError(ValueError):
    """Raised when a discrete oracle relation does not hold."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_bundle(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return torch.load(stream, map_location="cpu", weights_only=True)


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key, value in expected.items():
            _compare(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, list):
        _require(isinstance(actual, list), f"{path}: expected list")
        _require(len(expected) == len(actual), f"{path}: length differs")
        for index, value in enumerate(expected):
            _compare(value, actual[index], f"{path}[{index}]")
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        tolerance = 2.0e-9 * max(abs(expected), 1.0)
        _require(
            math.isclose(expected, float(actual), abs_tol=tolerance),
            f"{path}: value differs",
        )
    else:
        _require(expected == actual, f"{path}: value differs")


def _step_metrics(item: dict) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    large = item["weighted_large_prey"].double()
    small = item["weighted_small_prey"].double()
    numerator = (
        item["assimilated_large_numerator"].double()
        + item["assimilated_small_numerator"].double()
    )
    pool = large + small
    source = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, item["source_prey_floor_c"]),
    )
    responsive = (source - item["source_prey_floor_c"]).clamp(min=0.0)
    gain = (
        GRAZE_MAX_PER_DAY
        * responsive
        / (responsive + GRAZE_HALF_SATURATION_C)
        * numerator
        / source
    )
    continuous = DT * (gain - MORTALITY_PER_DAY)
    factor = 1.0 + continuous
    return continuous, factor, torch.log(factor)


def _jump_summary(selected: torch.Tensor, coordinates: torch.Tensor) -> dict:
    points = coordinates[selected]
    jumps = (points[1:] - points[:-1]).abs().sum(dim=1).double()
    return {
        "selected_cell_count": int(torch.unique(selected).numel()),
        "switch_count": int((selected[1:] != selected[:-1]).sum()),
        "jump_manhattan_grid_cells": {
            "median": float(jumps.median()),
            "p95": float(torch.quantile(jumps, 0.95)),
            "maximum": float(jumps.max()),
            "zero_fraction": float((jumps == 0).double().mean()),
        },
    }


def _envelope(
    logs: torch.Tensor,
    continuous: torch.Tensor,
    selected: torch.Tensor,
    coordinates: torch.Tensor,
) -> dict:
    log_multiplier = float(logs.sum())
    continuous_margin = float(continuous.sum())
    return {
        "annual_log_multiplier": log_multiplier,
        "annual_retention": math.exp(log_multiplier),
        "continuous_net_margin": continuous_margin,
        "jensen_gap": continuous_margin - log_multiplier,
        **_jump_summary(selected, coordinates),
    }


def _summarize(item: dict, exclusion_item: dict) -> dict:
    mask = item["mask"]
    coordinates = mask.nonzero()
    continuous, factors, logs = _step_metrics(item)
    wet_continuous = continuous[:, mask]
    wet_logs = logs[:, mask]

    fixed_logs = wet_logs.sum(dim=0)
    fixed_value, fixed_selected = fixed_logs.max(dim=0)
    fixed_continuous = wet_continuous[:, fixed_selected].sum()
    fixed_coordinate = coordinates[fixed_selected]

    monthly_logs = wet_logs.reshape(MONTHS, STEPS_PER_MONTH, -1).sum(dim=1)
    monthly_continuous = wet_continuous.reshape(
        MONTHS, STEPS_PER_MONTH, -1
    ).sum(dim=1)
    monthly_values, monthly_selected = monthly_logs.max(dim=1)
    monthly_continuous_values = monthly_continuous.gather(
        1, monthly_selected[:, None]
    ).squeeze(1)

    step_values, step_selected = wet_logs.max(dim=1)
    step_continuous_values = wet_continuous.gather(
        1, step_selected[:, None]
    ).squeeze(1)

    actual_monthly = logs.reshape(MONTHS, STEPS_PER_MONTH, *mask.shape).sum(dim=1)
    expected_monthly = exclusion_item["monthly_log_multiplier"][:, 1].double()
    monthly_error = float((actual_monthly - expected_monthly).abs()[:, mask].max())
    annual_error = float(
        (actual_monthly.sum(dim=0) - expected_monthly.sum(dim=0)).abs()[mask].max()
    )
    positive = bool((factors[:, mask] > 0.0).all())
    finite = bool(torch.isfinite(wet_logs).all())
    fixed_log = float(fixed_value)
    fixed_margin = float(fixed_continuous)
    return {
        "integrity": {
            "pass": positive
            and finite
            and monthly_error <= LOG_REPRODUCTION_ATOL
            and annual_error <= LOG_REPRODUCTION_ATOL,
            "strictly_positive_euler_factors": positive,
            "finite_wet_log_increments": finite,
            "minimum_euler_factor": float(factors[:, mask].min()),
            "monthly_log_max_abs_error": monthly_error,
            "annual_log_max_abs_error": annual_error,
            "log_reproduction_atol": LOG_REPRODUCTION_ATOL,
        },
        "fixed_cell": {
            "annual_log_multiplier": fixed_log,
            "annual_retention": math.exp(fixed_log),
            "continuous_net_margin": fixed_margin,
            "jensen_gap": fixed_margin - fixed_log,
            "row_col": [int(fixed_coordinate[0]), int(fixed_coordinate[1])],
        },
        "monthly_teleport": _envelope(
            monthly_values, monthly_continuous_values, monthly_selected, coordinates
        ),
        "stepwise_teleport": _envelope(
            step_values, step_continuous_values, step_selected, coordinates
        ),
    }


def verify(
    report: dict,
    support_report: dict,
    support_bundle: dict,
    exclusion_report: dict,
    exclusion_bundle: dict,
    hashes: dict[str, str],
) -> dict:
    _require(report["schema_version"] == 1, "report schema version")
    _require(report["status"] == "MEASURED_NOT_INDEPENDENTLY_VERIFIED", "report status")
    _require(report["preregistration"] == PREREGISTRATION, "report preregistration")
    _require(
        support_report["bundle_artifact"]["sha256"] == hashes["support_bundle_sha256"],
        "support bundle SHA-256 differs",
    )
    _require(support_report["config"] == support_bundle["config"], "support configs differ")
    _require(
        exclusion_report["bundle_artifact"]["sha256"]
        == hashes["exclusion_bundle_sha256"],
        "exclusion bundle SHA-256 differs",
    )
    _require(
        exclusion_report["config"] == exclusion_bundle["config"],
        "exclusion configs differ",
    )
    _require(
        support_report["config"]["source_target_report_sha256"]
        == exclusion_report["config"]["source_report_sha256"],
        "support/exclusion target report lineage differs",
    )
    _require(
        support_report["config"]["source_target_bundle_sha256"]
        == exclusion_report["config"]["source_bundle_sha256"],
        "support/exclusion target bundle lineage differs",
    )
    expected_config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "months": MONTHS,
        "mortality_per_day": MORTALITY_PER_DAY,
        "source_prey_floor_c": SOURCE_PREY_FLOOR_C,
        "log_reproduction_atol": LOG_REPRODUCTION_ATOL,
        "oracles": ["fixed_cell", "monthly_teleport", "stepwise_teleport"],
        **hashes,
    }
    _require(report["config"] == expected_config, "frozen config differs")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")

    summaries = {}
    raw_support_tensor_cells = 0
    for aoi in AOIS:
        item = support_bundle["aois"][aoi]
        mask = item["mask"]
        _require(
            mask.dtype == torch.bool and tuple(mask.shape) == AOI_SHAPES[aoi],
            f"{aoi}: mask differs",
        )
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: wet-cell count differs")
        _require(torch.equal(mask, exclusion_bundle["aois"][aoi]["mask"]), f"{aoi}: mask")
        _require(item["source_prey_floor_c"] == SOURCE_PREY_FLOOR_C, f"{aoi}: prey floor")
        for name in (
            "weighted_large_prey",
            "weighted_small_prey",
            "assimilated_large_numerator",
            "assimilated_small_numerator",
        ):
            tensor = item[name]
            _require(
                tensor.dtype == torch.float32
                and tuple(tensor.shape) == (TOTAL_STEPS, *AOI_SHAPES[aoi]),
                f"{aoi}.{name}: shape or dtype differs",
            )
            raw_support_tensor_cells += tensor.numel()
        _require(
            torch.allclose(
                item["assimilated_large_numerator"],
                0.5 * item["weighted_large_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: large-prey assimilation differs",
        )
        _require(
            torch.allclose(
                item["assimilated_small_numerator"],
                0.7 * item["weighted_small_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: small-prey assimilation differs",
        )
        summary = _summarize(item, exclusion_bundle["aois"][aoi])
        _compare(summary, report["aois"][aoi], f"report.{aoi}")
        summaries[aoi] = summary

    integrity = all(item["integrity"]["pass"] for item in summaries.values())
    nonpositive = {
        aoi: item["stepwise_teleport"]["annual_log_multiplier"] <= 0.0
        for aoi, item in summaries.items()
    }
    if integrity and all(nonpositive.values()):
        branch = "discrete-frozen-path-relocation-ruled-out-all-aois"
        primary = "supported"
    elif integrity:
        branch = "discrete-frozen-path-relocation-remains-open"
        primary = "falsified"
    else:
        branch = "unresolved-reproduction-failed"
        primary = "unresolved"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "stepwise_log_nonpositive_by_aoi": nonpositive,
        "actual_transport_tested": False,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(report["decision"]["actual_transport_tested"] is False, "transport tested")
    _require(report["decision"]["target_rehabilitated"] is False, "target rehabilitated")
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_support_tensor_cells": raw_support_tensor_cells,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--support-report", type=Path, required=True)
    parser.add_argument("--support-bundle", type=Path, required=True)
    parser.add_argument("--exclusion-report", type=Path, required=True)
    parser.add_argument("--exclusion-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = load_bundle(args.support_bundle)
    exclusion_report = json.loads(args.exclusion_report.read_text(encoding="utf-8"))
    exclusion_bundle = load_bundle(args.exclusion_bundle)
    hashes = {
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
        "exclusion_report_sha256": _sha256(args.exclusion_report),
        "exclusion_bundle_sha256": _sha256(args.exclusion_bundle),
    }
    try:
        result = verify(
            report,
            support_report,
            support_bundle,
            exclusion_report,
            exclusion_bundle,
            hashes,
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"DISCRETE TRANSPORT-ORACLE VERIFICATION FAILED: {exc}")
        return 2
    result.update(
        {
            "report": args.report.as_posix(),
            "report_sha256": _sha256(args.report),
            **hashes,
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED discrete explicit-zoo transport oracle: "
        f"decision={result['decision']['branch']} "
        f"raw_support_tensor_cells={result['raw_support_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

