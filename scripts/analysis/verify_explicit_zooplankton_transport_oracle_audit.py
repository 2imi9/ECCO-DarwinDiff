#!/usr/bin/env python
"""Independently verify the large-Z frozen-path transport-oracle audit."""

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
    "docs/findings/2026-08-10_prereg_large_zooplankton_transport_oracle.md"
)
DT = 0.25
STEPS_PER_MONTH = 122
MONTHS = 12
TOTAL_STEPS = MONTHS * STEPS_PER_MONTH
SOURCE_PREY_FLOOR_C = 1.2e-8
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
MORTALITY_PER_DAY = 1.0 / 30.0
MORTALITY_INTEGRAL = TOTAL_STEPS * DT * MORTALITY_PER_DAY
GAIN_REPRODUCTION_ATOL = 5.0e-5


class VerificationError(ValueError):
    """Raised when a frozen oracle relation does not hold."""


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


def _step_gain(item: dict) -> torch.Tensor:
    pool = item["weighted_large_prey"].double() + item["weighted_small_prey"].double()
    numerator = (
        item["assimilated_large_numerator"].double()
        + item["assimilated_small_numerator"].double()
    )
    source_pool = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, item["source_prey_floor_c"]),
    )
    responsive_pool = (source_pool - item["source_prey_floor_c"]).clamp(min=0.0)
    rate = (
        GRAZE_MAX_PER_DAY
        * responsive_pool
        / (responsive_pool + GRAZE_HALF_SATURATION_C)
        * numerator
        / source_pool
    )
    return DT * rate


def _jump_summary(selected: torch.Tensor, coordinates: torch.Tensor) -> dict:
    selected_coordinates = coordinates[selected]
    jumps = (
        selected_coordinates[1:] - selected_coordinates[:-1]
    ).abs().sum(dim=1).double()
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


def _oracle_summary(values: torch.Tensor, selected: torch.Tensor, coords: torch.Tensor) -> dict:
    integral = float(values.sum())
    return {
        "gain_integral": integral,
        "gain_to_mortality": integral / MORTALITY_INTEGRAL,
        "margin_vs_mortality": integral - MORTALITY_INTEGRAL,
        **_jump_summary(selected, coords),
    }


def _summarize(item: dict, energy_item: dict) -> dict:
    mask = item["mask"]
    coordinates = mask.nonzero()
    step_gain = _step_gain(item)
    wet = step_gain[:, mask]
    fixed = wet.sum(dim=0)
    fixed_value, fixed_index = fixed.max(dim=0)
    monthly = wet.reshape(MONTHS, STEPS_PER_MONTH, -1).sum(dim=1)
    monthly_values, monthly_selected = monthly.max(dim=1)
    step_values, step_selected = wet.max(dim=1)

    expected_monthly = energy_item["monthly_total_specific_gain"][:, 1].double()
    actual_monthly = step_gain.reshape(MONTHS, STEPS_PER_MONTH, *mask.shape).sum(dim=1)
    expected_annual = expected_monthly.sum(dim=0)
    actual_annual = step_gain.sum(dim=0)
    monthly_error = float((actual_monthly - expected_monthly).abs()[:, mask].max())
    annual_error = float((actual_annual - expected_annual).abs()[mask].max())
    finite = bool(torch.isfinite(wet).all())
    fixed_coordinate = coordinates[fixed_index]
    return {
        "integrity": {
            "pass": finite
            and monthly_error <= GAIN_REPRODUCTION_ATOL
            and annual_error <= GAIN_REPRODUCTION_ATOL,
            "finite_wet_step_gain": finite,
            "monthly_gain_max_abs_error": monthly_error,
            "annual_gain_max_abs_error": annual_error,
            "gain_reproduction_atol": GAIN_REPRODUCTION_ATOL,
        },
        "fixed_cell": {
            "gain_integral": float(fixed_value),
            "gain_to_mortality": float(fixed_value) / MORTALITY_INTEGRAL,
            "margin_vs_mortality": float(fixed_value) - MORTALITY_INTEGRAL,
            "row_col": [int(fixed_coordinate[0]), int(fixed_coordinate[1])],
        },
        "monthly_teleport": _oracle_summary(
            monthly_values, monthly_selected, coordinates
        ),
        "stepwise_teleport": _oracle_summary(step_values, step_selected, coordinates),
        "fraction_steps_with_any_instantaneous_refuge": float(
            (wet.max(dim=1).values / DT >= MORTALITY_PER_DAY).double().mean()
        ),
    }


def verify(
    report: dict,
    support_report: dict,
    support_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
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
        energy_report["bundle_artifact"]["sha256"] == hashes["energy_bundle_sha256"],
        "energy bundle SHA-256 differs",
    )
    _require(energy_report["config"] == energy_bundle["config"], "energy configs differ")
    _require(
        support_report["config"]["source_energy_report_sha256"]
        == hashes["energy_report_sha256"],
        "support-to-energy report lineage differs",
    )
    _require(
        support_report["config"]["source_energy_bundle_sha256"]
        == hashes["energy_bundle_sha256"],
        "support-to-energy bundle lineage differs",
    )
    expected_config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "months": MONTHS,
        "mortality_per_day": MORTALITY_PER_DAY,
        "mortality_integral": MORTALITY_INTEGRAL,
        "source_prey_floor_c": SOURCE_PREY_FLOOR_C,
        "gain_reproduction_atol": GAIN_REPRODUCTION_ATOL,
        "oracles": ["fixed_cell", "monthly_teleport", "stepwise_teleport"],
        **hashes,
    }
    _require(report["config"] == expected_config, "frozen config differs")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")
    _require(set(support_bundle["aois"]) == set(AOIS), "support AOIs differ")
    _require(set(energy_bundle["aois"]) == set(AOIS), "energy AOIs differ")

    summaries = {}
    raw_tensor_cells = 0
    for aoi in AOIS:
        item = support_bundle["aois"][aoi]
        mask = item["mask"]
        _require(
            mask.dtype == torch.bool and tuple(mask.shape) == AOI_SHAPES[aoi],
            f"{aoi}: mask differs",
        )
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: wet-cell count differs")
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
            raw_tensor_cells += tensor.numel()
        _require(
            torch.allclose(
                item["assimilated_large_numerator"],
                0.5 * item["weighted_large_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: large-prey assimilation relation differs",
        )
        _require(
            torch.allclose(
                item["assimilated_small_numerator"],
                0.7 * item["weighted_small_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: small-prey assimilation relation differs",
        )
        summary = _summarize(item, energy_bundle["aois"][aoi])
        _compare(summary, report["aois"][aoi], f"report.{aoi}")
        summaries[aoi] = summary

    integrity = all(item["integrity"]["pass"] for item in summaries.values())
    clears = {
        aoi: item["stepwise_teleport"]["gain_integral"] >= MORTALITY_INTEGRAL
        for aoi, item in summaries.items()
    }
    if integrity and all(clears.values()):
        branch = "energetically-open-under-unrestricted-oracle"
        primary = "supported"
    elif integrity:
        branch = "frozen-path-relocation-ruled-out-in-one-or-more-aois"
        primary = "falsified"
    else:
        branch = "unresolved-reproduction-failed"
        primary = "unresolved"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "stepwise_oracle_clears_mortality_by_aoi": clears,
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
        "raw_support_tensor_cells": raw_tensor_cells,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--support-report", type=Path, required=True)
    parser.add_argument("--support-bundle", type=Path, required=True)
    parser.add_argument("--energy-report", type=Path, required=True)
    parser.add_argument("--energy-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = load_bundle(args.support_bundle)
    energy_report = json.loads(args.energy_report.read_text(encoding="utf-8"))
    energy_bundle = load_bundle(args.energy_bundle)
    hashes = {
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
        "energy_report_sha256": _sha256(args.energy_report),
        "energy_bundle_sha256": _sha256(args.energy_bundle),
    }
    try:
        result = verify(
            report,
            support_report,
            support_bundle,
            energy_report,
            energy_bundle,
            hashes,
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"TRANSPORT-ORACLE AUDIT VERIFICATION FAILED: {exc}")
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
        "VERIFIED explicit-zoo transport oracle: "
        f"decision={result['decision']['branch']} "
        f"raw_support_tensor_cells={result['raw_support_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
