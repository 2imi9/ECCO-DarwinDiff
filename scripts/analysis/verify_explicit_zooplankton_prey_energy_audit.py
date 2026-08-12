#!/usr/bin/env python3
"""Independently verify the explicit-zooplankton prey-energy audit."""

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
PREY = ("diatom", "lge", "syn", "proLL", "proHL")
RESTORING_INDICES = (0, 6, 7, 8, 9, 10, 11, 12, 13, 14)
ASSIMILATION = (
    (0.2, 0.5),
    (0.2, 0.5),
    (0.5, 0.7),
    (0.5, 0.7),
    (0.5, 0.7),
)
DT = 0.25
STEPS_PER_MONTH = 122
MORTALITY_PER_DAY = 1.0 / 30.0
MORTALITY_INTEGRAL = 12 * STEPS_PER_MONTH * DT * MORTALITY_PER_DAY
PARTITION_ATOL = 5.0e-5
LOG_RATIO_ATOL = 5.0e-4
PRIOR_LOG_ATOL = 5.0e-4
PRIOR_ENDPOINT_REL_L2_ATOL = 2.0e-5
CONTINUOUS_EXCLUSION_THRESHOLD = -0.10
PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_explicit_zooplankton_prey_energy_audit.md"
)
CORRECTION_PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_source_floor_corrected_explicit_zooplankton_chain.md"
)
SOURCE_PHYGRAZ_MIN_C = 1.2e-8


class VerificationError(ValueError):
    """Raised when a frozen prey-energy relation does not hold."""


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
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        tolerance = 2.0e-10 * max(abs(expected), 1.0)
        _require(
            math.isclose(expected, float(actual), abs_tol=tolerance),
            f"{path}: value differs",
        )
    else:
        _require(expected == actual, f"{path}: value differs")


def _relative_l2(actual: torch.Tensor, expected: torch.Tensor, mask: torch.Tensor) -> float:
    numerator = torch.linalg.vector_norm((actual - expected)[:, mask].double())
    denominator = torch.linalg.vector_norm(expected[:, mask].double()).clamp(min=1.0e-300)
    return float(numerator / denominator)


def _classification(large_margin: torch.Tensor, large_exact_log: torch.Tensor) -> str:
    if float(large_exact_log.max()) >= CONTINUOUS_EXCLUSION_THRESHOLD:
        return "inconsistent-with-prior-exclusion"
    if float(large_margin.max()) < CONTINUOUS_EXCLUSION_THRESHOLD:
        return "continuous-energetic-deficit"
    return "discrete-or-variance-penalty"


def _summarize(item: dict, prior: dict, mask: torch.Tensor) -> dict:
    monthly_by_prey = item["monthly_specific_gain_by_prey"]
    monthly_total = item["monthly_total_specific_gain"]
    monthly_log = item["monthly_log_multiplier"]
    monthly_min_factor = item["monthly_min_euler_factor"]
    start_zoo = item["start_zoo"]
    end_zoo = item["end_zoo"]

    annual_by_prey = monthly_by_prey.sum(dim=0).double()
    annual_total = monthly_total.sum(dim=0).double()
    annual_from_parts = annual_by_prey.sum(dim=0)
    continuous_margin = annual_total - MORTALITY_INTEGRAL
    exact_log = monthly_log.sum(dim=0).double()
    endpoint_log = torch.log(end_zoo.double() / start_zoo.double())
    partition_error = (annual_from_parts - annual_total).abs()
    identity_error = (exact_log - endpoint_log).abs()
    prior_log_error = (
        monthly_log.double() - prior["monthly_log_multiplier"].double()
    ).abs()
    prior_endpoint_rel_l2 = _relative_l2(end_zoo, prior["end_zoo"], mask)

    predators = {}
    for predator_index, predator_name in enumerate(PREDATORS):
        total = annual_total[predator_index][mask]
        margin = continuous_margin[predator_index][mask]
        log_values = exact_log[predator_index][mask]
        denominator = annual_total[predator_index].clamp(min=1.0e-300)
        shares = annual_by_prey[:, predator_index] / denominator.unsqueeze(0)
        prey_shares = {
            prey_name: float(shares[prey_index][mask].median())
            for prey_index, prey_name in enumerate(PREY)
        }
        large_share = shares[[0, 1]].sum(dim=0)[mask]
        small_share = shares[[2, 3, 4]].sum(dim=0)[mask]
        predators[predator_name] = {
            "annual_specific_gain_integral_min": float(total.min()),
            "annual_specific_gain_integral_median": float(total.median()),
            "annual_specific_gain_integral_max": float(total.max()),
            "continuous_margin_min": float(margin.min()),
            "continuous_margin_median": float(margin.median()),
            "continuous_margin_max": float(margin.max()),
            "exact_log_multiplier_min": float(log_values.min()),
            "exact_log_multiplier_median": float(log_values.median()),
            "exact_log_multiplier_max": float(log_values.max()),
            "median_gain_share_by_prey": prey_shares,
            "large_prey_gain_share_median": float(large_share.median()),
            "small_prey_gain_share_median": float(small_share.median()),
        }

    finite = all(
        bool(torch.isfinite(tensor).all())
        for tensor in (
            monthly_by_prey,
            monthly_total,
            monthly_log,
            monthly_min_factor,
            start_zoo,
            end_zoo,
        )
    )
    nonnegative = float(monthly_by_prey[:, :, :, mask].min()) >= 0.0
    positive_factors = float(monthly_min_factor[:, :, mask].min()) > 0.0
    positive_endpoints = float(end_zoo[:, mask].min()) > 0.0
    maximum_partition_error = float(partition_error[:, mask].max())
    maximum_identity_error = float(identity_error[:, mask].max())
    maximum_prior_log_error = float(prior_log_error[:, :, mask].max())
    classification = _classification(
        continuous_margin[1][mask],
        exact_log[1][mask],
    )
    integrity = (
        finite
        and nonnegative
        and positive_factors
        and positive_endpoints
        and maximum_partition_error <= PARTITION_ATOL
        and math.isclose(MORTALITY_INTEGRAL, 12.2, abs_tol=1.0e-7)
        and maximum_identity_error <= LOG_RATIO_ATOL
        and maximum_prior_log_error <= PRIOR_LOG_ATOL
        and prior_endpoint_rel_l2 <= PRIOR_ENDPOINT_REL_L2_ATOL
    )
    return {
        "pass": integrity,
        "finite": finite,
        "nonnegative_gain_contributions": nonnegative,
        "strictly_positive_euler_factors": positive_factors,
        "strictly_positive_endpoint_biomass": positive_endpoints,
        "mortality_integral": MORTALITY_INTEGRAL,
        "maximum_partition_error": maximum_partition_error,
        "partition_atol": PARTITION_ATOL,
        "maximum_log_ratio_discrepancy": maximum_identity_error,
        "log_ratio_atol": LOG_RATIO_ATOL,
        "maximum_prior_monthly_log_difference": maximum_prior_log_error,
        "prior_monthly_log_atol": PRIOR_LOG_ATOL,
        "prior_endpoint_relative_l2": prior_endpoint_rel_l2,
        "prior_endpoint_relative_l2_atol": PRIOR_ENDPOINT_REL_L2_ATOL,
        "large_predator_classification": classification,
        "predators": predators,
    }


def verify(
    report: dict,
    bundle: dict,
    *,
    target_report: dict,
    target_bundle: dict,
    exclusion_report: dict,
    exclusion_bundle: dict,
    hashes: dict[str, str],
) -> dict:
    """Rebuild every summary and decision without importing the runner."""
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
    _require(config["dt_days"] == DT, "dt differs")
    _require(config["steps_per_month"] == STEPS_PER_MONTH, "steps/month differs")
    _require(config["audit_cycle"] == 13, "audit cycle differs")
    _require(config["aois"] == list(AOIS), "AOIs differ")
    _require(config["scenario"] == "ic_0p10", "scenario differs")
    _require(config["chemical_restoring_tau_days"] == 365.25, "restoring tau differs")
    _require(config["restoring_indices"] == list(RESTORING_INDICES), "restoring differs")
    _require(config["zooplankton_restoring"] is False, "zooplankton restoring enabled")
    _require(config["predator_names"] == list(PREDATORS), "predator names differ")
    _require(config["prey_names"] == list(PREY), "prey names differ")
    _require(config["assimilation"] == [list(row) for row in ASSIMILATION], "assimilation differs")
    _require(config["mortality_per_day"] == MORTALITY_PER_DAY, "mortality differs")
    _require(config["partition_atol"] == PARTITION_ATOL, "partition gate differs")
    _require(config["log_ratio_atol"] == LOG_RATIO_ATOL, "identity gate differs")
    _require(config["prior_monthly_log_atol"] == PRIOR_LOG_ATOL, "prior log gate differs")
    _require(
        config["prior_endpoint_relative_l2_atol"] == PRIOR_ENDPOINT_REL_L2_ATOL,
        "prior endpoint gate differs",
    )
    _require(
        config["continuous_exclusion_threshold"] == CONTINUOUS_EXCLUSION_THRESHOLD,
        "classification threshold differs",
    )
    for key, value in hashes.items():
        _require(config[key] == value, f"{key} differs")

    _require(
        target_report["bundle_artifact"]["sha256"] == hashes["source_target_bundle_sha256"],
        "target report does not bind target bundle",
    )
    _require(
        exclusion_report["bundle_artifact"]["sha256"]
        == hashes["source_exclusion_bundle_sha256"],
        "exclusion report does not bind exclusion bundle",
    )
    _require(
        exclusion_bundle["config"]["source_report_sha256"]
        == hashes["source_target_report_sha256"],
        "exclusion artifact does not bind target report",
    )
    _require(
        exclusion_bundle["config"]["source_bundle_sha256"]
        == hashes["source_target_bundle_sha256"],
        "exclusion artifact does not bind target bundle",
    )
    _require(
        exclusion_bundle["decision"]["branch"]
        == "endogenous-large-predator-exclusion",
        "source exclusion decision differs",
    )
    _require(
        float(target_bundle["config"].get("source_prey_floor_c", 0.0))
        == source_prey_floor_c,
        "source target prey floor differs",
    )
    _require(
        float(exclusion_bundle["config"].get("source_prey_floor_c", 0.0))
        == source_prey_floor_c,
        "source exclusion prey floor differs",
    )
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    _require(report["decision"]["target_rehabilitated"] is False, "target rehabilitated")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")
    _require(set(bundle["aois"]) == set(AOIS), "bundle AOIs differ")

    summaries = {}
    raw_tensor_cells = 0
    expected_keys = {
        "mask",
        "start_zoo",
        "end_zoo",
        "monthly_specific_gain_by_prey",
        "monthly_total_specific_gain",
        "monthly_log_multiplier",
        "monthly_min_euler_factor",
    }
    for aoi in AOIS:
        item = bundle["aois"][aoi]
        _require(set(item) == expected_keys, f"{aoi}: tensor keys differ")
        shape = AOI_SHAPES[aoi]
        mask = item["mask"]
        _require(mask.dtype == torch.bool and tuple(mask.shape) == shape, f"{aoi}: mask")
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: ocean-cell count")
        _require(item["start_zoo"].shape == (2, *shape), f"{aoi}: start shape")
        _require(item["end_zoo"].shape == (2, *shape), f"{aoi}: end shape")
        _require(
            item["monthly_specific_gain_by_prey"].shape == (12, 5, 2, *shape),
            f"{aoi}: prey-gain shape",
        )
        for name in (
            "monthly_total_specific_gain",
            "monthly_log_multiplier",
            "monthly_min_euler_factor",
        ):
            _require(item[name].shape == (12, 2, *shape), f"{aoi}.{name}: shape")

        target_item = target_bundle["aois"][aoi]
        prior_item = exclusion_bundle["aois"][aoi]
        _require(torch.equal(mask, target_item["mask"]), f"{aoi}: target mask differs")
        _require(torch.equal(mask, prior_item["mask"]), f"{aoi}: exclusion mask differs")
        target_start = target_item["scenarios"]["ic_0p10"]["cycle12_endpoint"][[15, 16]]
        _require(torch.equal(item["start_zoo"], target_start), f"{aoi}: target start differs")
        _require(
            torch.equal(item["start_zoo"], prior_item["start_zoo"]),
            f"{aoi}: prior start differs",
        )

        summary = _summarize(item, prior_item, mask)
        _compare(summary, report["aois"][aoi]["summary"], f"report.{aoi}.summary")
        summaries[aoi] = summary
        raw_tensor_cells += sum(tensor.numel() for tensor in item.values())

    integrity = all(summary["pass"] for summary in summaries.values())
    classes = {
        aoi: summaries[aoi]["large_predator_classification"] for aoi in AOIS
    }
    if integrity and all(value == "continuous-energetic-deficit" for value in classes.values()):
        branch = "prey-field-energy-deficit"
    elif integrity and all(
        value in {"continuous-energetic-deficit", "discrete-or-variance-penalty"}
        for value in classes.values()
    ):
        branch = "mixed-energy-and-variance-exclusion"
    else:
        branch = "unresolved-or-reproduction-failed"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "large_predator_classification_by_aoi": classes,
        "b200_authorized": False,
        "target_rehabilitated": False,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(decision == bundle["decision"], "bundle decision differs")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source-target-report", type=Path, required=True)
    parser.add_argument("--source-target-bundle", type=Path, required=True)
    parser.add_argument("--source-exclusion-report", type=Path, required=True)
    parser.add_argument("--source-exclusion-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = load_bundle(args.source_target_bundle)
    exclusion_report = json.loads(
        args.source_exclusion_report.read_text(encoding="utf-8")
    )
    exclusion_bundle = load_bundle(args.source_exclusion_bundle)
    hashes = {
        "source_target_report_sha256": _sha256(args.source_target_report),
        "source_target_bundle_sha256": _sha256(args.source_target_bundle),
        "source_exclusion_report_sha256": _sha256(args.source_exclusion_report),
        "source_exclusion_bundle_sha256": _sha256(args.source_exclusion_bundle),
    }
    try:
        _require(
            report["bundle_artifact"]["sha256"] == _sha256(args.bundle),
            "bundle SHA-256 differs",
        )
        result = verify(
            report,
            bundle,
            target_report=target_report,
            target_bundle=target_bundle,
            exclusion_report=exclusion_report,
            exclusion_bundle=exclusion_bundle,
            hashes=hashes,
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"PREY-ENERGY AUDIT VERIFICATION FAILED: {exc}")
        return 2

    result.update(
        {
            "report": args.report.as_posix(),
            "report_sha256": _sha256(args.report),
            "bundle": args.bundle.as_posix(),
            "bundle_sha256": _sha256(args.bundle),
            **hashes,
        }
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED explicit-zoo prey-energy audit: "
        f"decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
