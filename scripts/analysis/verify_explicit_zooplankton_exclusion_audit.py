#!/usr/bin/env python3
"""Independently verify the cycle-13 zooplankton exclusion audit."""

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
PREDATORS = ("z_small", "z_large")
RESTORING_INDICES = (0, 6, 7, 8, 9, 10, 11, 12, 13, 14)
STEPS_PER_MONTH = 122
LOG_RATIO_ATOL = 5.0e-4
PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_explicit_zooplankton_exclusion_audit.md"
)
CORRECTION_PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_source_floor_corrected_explicit_zooplankton_chain.md"
)
SOURCE_PHYGRAZ_MIN_C = 1.2e-8


class VerificationError(ValueError):
    """Raised when a frozen audit relation does not hold."""


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


def _classification(values: torch.Tensor) -> str:
    if float(values.max()) < -0.10:
        return "uniformly-excluded"
    if float(values.min()) > 0.10:
        return "uniformly-viable"
    return "mixed-or-near-neutral"


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key, value in expected.items():
            _compare(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        tolerance = 2.0e-10 * max(abs(expected), 1.0)
        _require(math.isclose(expected, float(actual), abs_tol=tolerance), f"{path}: value differs")
    else:
        _require(expected == actual, f"{path}: value differs")


def _summarize(item: dict, mask: torch.Tensor) -> dict:
    monthly_log = item["monthly_log_multiplier"]
    monthly_events = item["monthly_positive_rate_events"]
    monthly_min_factor = item["monthly_min_euler_factor"]
    start_zoo = item["start_zoo"]
    end_zoo = item["end_zoo"]

    annual = monthly_log.sum(dim=0).double()
    actual = torch.log(end_zoo.double() / start_zoo.double())
    discrepancy = (annual - actual).abs()
    predators = {}
    denominator = 12 * STEPS_PER_MONTH * int(mask.sum())
    for index, name in enumerate(PREDATORS):
        values = annual[index][mask]
        events = int(monthly_events[:, index][:, mask].sum())
        start_inventory = start_zoo[index][mask].double().sum()
        end_inventory = end_zoo[index][mask].double().sum()
        predators[name] = {
            "classification": _classification(values),
            "annual_log_multiplier_min": float(values.min()),
            "annual_log_multiplier_median": float(values.median()),
            "annual_log_multiplier_max": float(values.max()),
            "annual_multiplier_min": float(values.exp().min()),
            "annual_multiplier_median": float(values.exp().median()),
            "annual_multiplier_max": float(values.exp().max()),
            "positive_rate_step_fraction": events / denominator,
            "minimum_euler_factor": float(
                monthly_min_factor[:, index][:, mask].min()
            ),
            "start_inventory": float(start_inventory),
            "end_inventory": float(end_inventory),
            "inventory_retention": float(
                end_inventory / start_inventory.clamp(min=1e-300)
            ),
            "maximum_log_ratio_discrepancy": float(
                discrepancy[index][mask].max()
            ),
        }

    maximum_discrepancy = float(discrepancy[:, mask].max())
    finite = all(
        bool(torch.isfinite(tensor).all())
        for tensor in (monthly_log, monthly_min_factor, start_zoo, end_zoo)
    )
    positive_factors = float(monthly_min_factor[:, :, mask].min()) > 0.0
    positive_endpoints = float(end_zoo[:, mask].min()) > 0.0
    return {
        "pass": finite
        and positive_factors
        and positive_endpoints
        and maximum_discrepancy <= LOG_RATIO_ATOL,
        "finite": finite,
        "strictly_positive_euler_factors": positive_factors,
        "strictly_positive_endpoint_biomass": positive_endpoints,
        "maximum_log_ratio_discrepancy": maximum_discrepancy,
        "log_ratio_discrepancy_atol": LOG_RATIO_ATOL,
        "predators": predators,
    }


def verify(
    report: dict,
    bundle: dict,
    *,
    source_report: dict | None = None,
    source_bundle: dict | None = None,
    source_report_sha256: str | None = None,
    source_bundle_sha256: str | None = None,
) -> dict:
    """Reconstruct the frozen summaries and decision without runner imports."""
    _require(report["schema_version"] == 1, "report schema differs")
    _require(bundle["schema_version"] == 1, "bundle schema differs")
    _require(report["config"] == bundle["config"], "report/bundle config differs")
    config = bundle["config"]
    source_prey_floor_c = float(config.get("source_prey_floor_c", 0.0))
    expected_preregistration = (
        CORRECTION_PREREGISTRATION
        if source_prey_floor_c == SOURCE_PHYGRAZ_MIN_C
        else PREREGISTRATION
    )
    _require(
        source_prey_floor_c in (0.0, SOURCE_PHYGRAZ_MIN_C),
        "unregistered source prey floor",
    )
    _require(
        report["preregistration"] == expected_preregistration,
        "report prereg differs",
    )
    _require(
        bundle["preregistration"] == expected_preregistration,
        "bundle prereg differs",
    )
    _require(config["dt_days"] == 0.25, "dt differs")
    _require(config["steps_per_month"] == STEPS_PER_MONTH, "steps/month differs")
    _require(config["audit_cycle"] == 13, "audit cycle differs")
    _require(config["aois"] == list(AOIS), "AOIs differ")
    _require(config["scenario"] == "ic_0p10", "scenario differs")
    _require(config["chemical_restoring_tau_days"] == 365.25, "restoring tau differs")
    _require(config["restoring_indices"] == list(RESTORING_INDICES), "restoring differs")
    _require(config["zooplankton_restoring"] is False, "zooplankton restoring enabled")
    _require(config["log_ratio_discrepancy_atol"] == LOG_RATIO_ATOL, "identity gate differs")
    _require(set(bundle["aois"]) == set(AOIS), "bundle AOIs differ")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    _require(report["decision"]["target_rehabilitated"] is False, "target rehabilitated")

    if source_report is not None or source_bundle is not None:
        _require(source_report is not None and source_bundle is not None, "partial source input")
        _require(source_report_sha256 is not None, "source report hash absent")
        _require(source_bundle_sha256 is not None, "source bundle hash absent")
        _require(
            config["source_report_sha256"] == source_report_sha256,
            "source report SHA-256 differs",
        )
        _require(
            config["source_bundle_sha256"] == source_bundle_sha256,
            "source bundle SHA-256 differs",
        )
        _require(
            source_report["bundle_artifact"]["sha256"] == source_bundle_sha256,
            "source report does not bind source bundle",
        )
        _require(
            source_bundle["decision"]["branch"] == "stage0-failed-stop",
            "source target was not a registered Stage-0 stop",
        )
        _require(
            source_bundle["decision"]["b200_authorized"] is False,
            "source target authorized B200",
        )
        _require(
            float(source_bundle["config"].get("source_prey_floor_c", 0.0))
            == source_prey_floor_c,
            "source target prey floor differs",
        )

    summaries = {}
    raw_tensor_cells = 0
    masked_predator_step_cells = 0
    for aoi in AOIS:
        item = bundle["aois"][aoi]
        _require(
            set(item)
            == {
                "mask",
                "start_zoo",
                "end_zoo",
                "monthly_log_multiplier",
                "monthly_positive_rate_events",
                "monthly_min_euler_factor",
            },
            f"{aoi}: tensor keys differ",
        )
        mask = item["mask"]
        shape = AOI_SHAPES[aoi]
        _require(mask.dtype == torch.bool and tuple(mask.shape) == shape, f"{aoi}: mask")
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: ocean-cell count")
        for name in ("start_zoo", "end_zoo"):
            _require(item[name].shape == (2, *shape), f"{aoi}.{name}: shape")
        for name in (
            "monthly_log_multiplier",
            "monthly_positive_rate_events",
            "monthly_min_euler_factor",
        ):
            _require(item[name].shape == (12, 2, *shape), f"{aoi}.{name}: shape")
        events = item["monthly_positive_rate_events"]
        _require(events.dtype in (torch.int32, torch.int64), f"{aoi}: event dtype")
        _require(bool((events >= 0).all()), f"{aoi}: negative event count")
        _require(bool((events <= STEPS_PER_MONTH).all()), f"{aoi}: excess event count")

        if source_bundle is not None:
            source_item = source_bundle["aois"][aoi]
            _require(torch.equal(mask, source_item["mask"]), f"{aoi}: source mask differs")
            source_endpoint = source_item["scenarios"]["ic_0p10"]["cycle12_endpoint"]
            _require(
                torch.equal(item["start_zoo"], source_endpoint[[15, 16]]),
                f"{aoi}: audit does not start at source cycle-12 endpoint",
            )

        summary = _summarize(item, mask)
        _compare(summary, report["aois"][aoi]["summary"], f"report.{aoi}.summary")
        summaries[aoi] = summary
        raw_tensor_cells += sum(tensor.numel() for tensor in item.values())
        masked_predator_step_cells += 12 * 2 * int(mask.sum())

    integrity = all(summary["pass"] for summary in summaries.values())
    large_classes = {
        aoi: summaries[aoi]["predators"]["z_large"]["classification"]
        for aoi in AOIS
    }
    if integrity and all(value == "uniformly-excluded" for value in large_classes.values()):
        branch = "endogenous-large-predator-exclusion"
    elif integrity and len(set(large_classes.values())) > 1:
        branch = "spatially-mixed-large-predator-viability"
    else:
        branch = "unresolved-or-numerical"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "large_predator_classification_by_aoi": large_classes,
        "b200_authorized": False,
        "target_rehabilitated": False,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(decision == bundle["decision"], "bundle decision differs")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "masked_predator_month_cells": masked_predator_step_cells,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--source-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    source_report = json.loads(args.source_report.read_text(encoding="utf-8"))
    source_bundle = load_bundle(args.source_bundle)
    try:
        _require(
            report["bundle_artifact"]["sha256"] == _sha256(args.bundle),
            "bundle SHA-256 differs",
        )
        result = verify(
            report,
            bundle,
            source_report=source_report,
            source_bundle=source_bundle,
            source_report_sha256=_sha256(args.source_report),
            source_bundle_sha256=_sha256(args.source_bundle),
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"EXCLUSION AUDIT VERIFICATION FAILED: {exc}")
        return 2

    result.update(
        {
            "report": args.report.as_posix(),
            "report_sha256": _sha256(args.report),
            "bundle": args.bundle.as_posix(),
            "bundle_sha256": _sha256(args.bundle),
            "source_report_sha256": _sha256(args.source_report),
            "source_bundle_sha256": _sha256(args.source_bundle),
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED explicit-zoo exclusion audit: "
        f"decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
