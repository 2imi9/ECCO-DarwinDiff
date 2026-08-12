#!/usr/bin/env python
"""Independently verify the frozen-prey large-Z support-threshold audit."""

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
    "docs/findings/2026-08-10_prereg_large_zooplankton_support_threshold_audit.md"
)
DT = 0.25
STEPS_PER_MONTH = 122
TOTAL_STEPS = 12 * STEPS_PER_MONTH
RESTORING_TAU_DAYS = 365.25
RESTORING_INDICES = (0, 6, 7, 8, 9, 10, 11, 12, 13, 14)
SOURCE_PHYGRAZ_MIN_C = 1.2e-8
GRAZE_MAX_PER_DAY = 0.625
GRAZE_HALF_SATURATION_C = 10.2
MORTALITY_PER_DAY = 1.0 / 30.0
MORTALITY_INTEGRAL = TOTAL_STEPS * DT * MORTALITY_PER_DAY
MULTIPLIER_LOW = 1.0
MULTIPLIER_HIGH = 64.0
BISECTION_ITERATIONS = 48
NEAR_REFUGE_THRESHOLD = 1.25
REPORT_THRESHOLDS = (1.10, 1.25, 1.50, 2.0, 4.0)
GAIN_REPRODUCTION_ATOL = 5.0e-5
ENDPOINT_REL_L2_ATOL = 2.0e-5


class VerificationError(ValueError):
    """Raised when a frozen support-threshold relation does not hold."""


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


def _annual_gain(
    large_pool: torch.Tensor,
    small_pool: torch.Tensor,
    large_numerator: torch.Tensor,
    small_numerator: torch.Tensor,
    multiplier: torch.Tensor | float,
    mode: str,
    source_prey_floor_c: float,
    sum_dim: int = 0,
) -> torch.Tensor:
    alpha = torch.as_tensor(multiplier, dtype=torch.float64, device=large_pool.device)
    if mode == "all_prey":
        pool = alpha * (large_pool.double() + small_pool.double())
        numerator = alpha * (large_numerator.double() + small_numerator.double())
    elif mode == "large_prey_only":
        pool = alpha * large_pool.double() + small_pool.double()
        numerator = alpha * large_numerator.double() + small_numerator.double()
    else:
        raise VerificationError(f"unknown counterfactual mode: {mode}")
    source_pool = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, source_prey_floor_c),
    )
    responsive_pool = (source_pool - source_prey_floor_c).clamp(min=0.0)
    gain = (
        GRAZE_MAX_PER_DAY
        * responsive_pool
        / (responsive_pool + GRAZE_HALF_SATURATION_C)
        * numerator
        / source_pool
    )
    return DT * gain.sum(dim=sum_dim)


def _monthly_gain_by_prey_group(
    large_pool: torch.Tensor,
    small_pool: torch.Tensor,
    large_numerator: torch.Tensor,
    small_numerator: torch.Tensor,
    source_prey_floor_c: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    """Reconstruct canonical monthly gain for each saved prey group."""
    shape = (12, STEPS_PER_MONTH, *large_pool.shape[1:])
    large_pool = large_pool.reshape(shape).double()
    small_pool = small_pool.reshape(shape).double()
    large_numerator = large_numerator.reshape(shape).double()
    small_numerator = small_numerator.reshape(shape).double()
    pool = large_pool + small_pool
    source_pool = torch.where(
        pool > 0.0,
        pool,
        torch.full_like(pool, source_prey_floor_c),
    )
    responsive_pool = (source_pool - source_prey_floor_c).clamp(min=0.0)
    common = (
        DT
        * GRAZE_MAX_PER_DAY
        * responsive_pool
        / (responsive_pool + GRAZE_HALF_SATURATION_C)
        / source_pool
    )
    return (
        (common * large_numerator).sum(dim=1),
        (common * small_numerator).sum(dim=1),
    )


def _validate_prey_decomposition(item: dict, energy_item: dict, aoi: str) -> dict:
    reconstructed = _monthly_gain_by_prey_group(
        item["weighted_large_prey"],
        item["weighted_small_prey"],
        item["assimilated_large_numerator"],
        item["assimilated_small_numerator"],
        item["source_prey_floor_c"],
    )
    expected_by_prey = energy_item["monthly_specific_gain_by_prey"][:, :, 1].double()
    expected = (expected_by_prey[:, :2].sum(dim=1), expected_by_prey[:, 2:].sum(dim=1))
    mask = item["mask"]
    errors = {}
    for group, actual, target in zip(
        ("large", "small"), reconstructed, expected, strict=True
    ):
        error = float((actual - target).abs()[:, mask].max())
        _require(
            error <= GAIN_REPRODUCTION_ATOL,
            f"{aoi}: {group}-prey monthly gain decomposition differs",
        )
        errors[group] = error
    return errors


def _solve_multiplier(
    large_pool: torch.Tensor,
    small_pool: torch.Tensor,
    large_numerator: torch.Tensor,
    small_numerator: torch.Tensor,
    mask: torch.Tensor,
    mode: str,
    source_prey_floor_c: float,
) -> tuple[torch.Tensor, torch.Tensor]:
    flat_mask = mask.flatten()
    support = tuple(
        tensor.reshape(TOTAL_STEPS, -1)[:, flat_mask]
        for tensor in (large_pool, small_pool, large_numerator, small_numerator)
    )
    count = int(flat_mask.sum())
    low = torch.full((count,), MULTIPLIER_LOW, dtype=torch.float64)
    high = torch.full_like(low, MULTIPLIER_HIGH)
    high_gain = _annual_gain(*support, high, mode, source_prey_floor_c)
    bracketed = high_gain >= MORTALITY_INTEGRAL
    for _ in range(BISECTION_ITERATIONS):
        midpoint = (low + high) / 2.0
        gain = _annual_gain(*support, midpoint, mode, source_prey_floor_c)
        reaches = gain >= MORTALITY_INTEGRAL
        high = torch.where(reaches, midpoint, high)
        low = torch.where(reaches, low, midpoint)
    roots = torch.where(bracketed, high, torch.full_like(high, float("nan")))
    root_grid = torch.full(mask.shape, float("nan"), dtype=torch.float64)
    high_gain_grid = torch.full_like(root_grid, float("nan"))
    root_grid.flatten()[flat_mask] = roots
    high_gain_grid.flatten()[flat_mask] = high_gain
    return root_grid, high_gain_grid


def _censored_quantile(values: torch.Tensor, total: int, q: float) -> float | None:
    if values.numel() / total + 1.0e-15 < q:
        return None
    rank = max(0, math.ceil(q * total) - 1)
    return float(values.sort().values[rank])


def _root_summary(roots: torch.Tensor, mask: torch.Tensor) -> dict:
    ocean = roots[mask]
    finite = ocean[torch.isfinite(ocean)]
    total = ocean.numel()
    bracketed = finite.numel()
    return {
        "ocean_cell_count": total,
        "bracketed_count": bracketed,
        "unbracketed_count": total - bracketed,
        "bracketed_fraction": bracketed / total,
        "minimum": float(finite.min()) if bracketed else None,
        "median": _censored_quantile(finite, total, 0.50),
        "p95": _censored_quantile(finite, total, 0.95),
        "maximum": float(finite.max()) if bracketed == total else None,
        "censoring_bound": MULTIPLIER_HIGH,
        "fraction_at_or_below": {
            f"{threshold:g}": float((finite <= threshold).sum()) / total
            for threshold in REPORT_THRESHOLDS
        },
    }


def _value_summary(values: torch.Tensor, mask: torch.Tensor) -> dict:
    ocean = values[mask].double()
    return {
        "minimum": float(ocean.min()),
        "median": float(ocean.median()),
        "p95": float(torch.quantile(ocean, 0.95)),
        "maximum": float(ocean.max()),
    }


def _summarize(item: dict, energy_item: dict) -> dict:
    mask = item["mask"]
    support = (
        item["weighted_large_prey"],
        item["weighted_small_prey"],
        item["assimilated_large_numerator"],
        item["assimilated_small_numerator"],
    )
    canonical_gain = _annual_gain(
        *support, 1.0, "all_prey", item["source_prey_floor_c"]
    )
    monthly_support = tuple(
        tensor.reshape(12, STEPS_PER_MONTH, *mask.shape) for tensor in support
    )
    canonical_monthly = _annual_gain(
        *monthly_support,
        1.0,
        "all_prey",
        item["source_prey_floor_c"],
        sum_dim=1,
    )
    expected_monthly = energy_item["monthly_total_specific_gain"][:, 1].double()
    expected_gain = expected_monthly.sum(dim=0)
    gain_error = (canonical_gain - expected_gain).abs()
    monthly_gain_error = (canonical_monthly - expected_monthly).abs()
    subsidy = ((MORTALITY_INTEGRAL - canonical_gain) / (TOTAL_STEPS * DT)).clamp(min=0.0)
    subsidy_fraction = subsidy / MORTALITY_PER_DAY
    all_summary = _root_summary(item["all_prey_multiplier"], mask)
    large_summary = _root_summary(item["large_prey_only_multiplier"], mask)
    minimum_ratio = None
    if all_summary["minimum"] is not None and large_summary["minimum"] is not None:
        minimum_ratio = large_summary["minimum"] / all_summary["minimum"]
    maximum_gain_error = float(gain_error[mask].max())
    maximum_monthly_gain_error = float(monthly_gain_error[:, mask].max())
    finite = all(
        bool(torch.isfinite(tensor).all())
        for tensor in support
    )
    integrity = (
        finite
        and maximum_gain_error <= GAIN_REPRODUCTION_ATOL
        and maximum_monthly_gain_error <= GAIN_REPRODUCTION_ATOL
        and item["endpoint_relative_l2_vs_energy"] <= ENDPOINT_REL_L2_ATOL
        and float(canonical_gain[mask].max()) < MORTALITY_INTEGRAL
    )
    return {
        "pass": integrity,
        "finite_support_tensors": finite,
        "maximum_canonical_gain_difference": maximum_gain_error,
        "maximum_canonical_monthly_gain_difference": maximum_monthly_gain_error,
        "canonical_gain_atol": GAIN_REPRODUCTION_ATOL,
        "endpoint_relative_l2_vs_energy": item["endpoint_relative_l2_vs_energy"],
        "endpoint_relative_l2_atol": ENDPOINT_REL_L2_ATOL,
        "canonical_annual_gain_integral": _value_summary(canonical_gain, mask),
        "all_prey_multiplier": all_summary,
        "large_prey_only_multiplier": large_summary,
        "minimum_large_only_to_all_prey_ratio": minimum_ratio,
        "required_subsidy_per_day": _value_summary(subsidy, mask),
        "required_subsidy_fraction_of_mortality": _value_summary(subsidy_fraction, mask),
        "near_local_refuge": bool(
            all_summary["minimum"] is not None
            and all_summary["minimum"] <= NEAR_REFUGE_THRESHOLD
        ),
    }


def _validate_source_chain(
    target_report: dict,
    target_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
    hashes: dict[str, str],
) -> None:
    _require(
        target_report["bundle_artifact"]["sha256"] == hashes["source_target_bundle_sha256"],
        "source target bundle SHA-256 differs",
    )
    _require(target_report["config"] == target_bundle["config"], "target configs differ")
    _require(
        energy_report["bundle_artifact"]["sha256"] == hashes["source_energy_bundle_sha256"],
        "source energy bundle SHA-256 differs",
    )
    _require(energy_report["config"] == energy_bundle["config"], "energy configs differ")
    _require(
        energy_bundle["decision"]["branch"] == "prey-field-energy-deficit",
        "source energy decision differs",
    )
    _require(
        energy_bundle["config"]["source_target_report_sha256"]
        == hashes["source_target_report_sha256"],
        "source target report SHA-256 differs",
    )
    _require(
        energy_bundle["config"]["source_target_bundle_sha256"]
        == hashes["source_target_bundle_sha256"],
        "source target bundle lineage differs",
    )


def verify(
    report: dict,
    bundle: dict,
    *,
    target_report: dict,
    target_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
    hashes: dict[str, str],
) -> dict:
    _validate_source_chain(
        target_report, target_bundle, energy_report, energy_bundle, hashes
    )
    _require(report["schema_version"] == 1, "report schema version")
    _require(bundle["schema_version"] == 1, "bundle schema version")
    _require(report["status"] == "MEASURED_NOT_INDEPENDENTLY_VERIFIED", "report status")
    _require(report["preregistration"] == PREREGISTRATION, "report preregistration")
    _require(bundle["preregistration"] == PREREGISTRATION, "bundle preregistration")
    _require(report["config"] == bundle["config"], "report/bundle configs differ")
    config = bundle["config"]
    expected_config = {
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "audit_cycle": 13,
        "aois": list(AOIS),
        "scenario": "ic_0p10",
        "chemical_restoring_tau_days": RESTORING_TAU_DAYS,
        "restoring_indices": list(RESTORING_INDICES),
        "zooplankton_restoring": False,
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "mortality_per_day": MORTALITY_PER_DAY,
        "mortality_integral": MORTALITY_INTEGRAL,
        "counterfactuals": ["all_prey", "large_prey_only"],
        "large_prey_indices": [0, 1],
        "small_prey_indices": [2, 3, 4],
        "multiplier_bracket": [MULTIPLIER_LOW, MULTIPLIER_HIGH],
        "bisection_iterations": BISECTION_ITERATIONS,
        "near_refuge_threshold": NEAR_REFUGE_THRESHOLD,
        "report_thresholds": list(REPORT_THRESHOLDS),
        "canonical_gain_atol": GAIN_REPRODUCTION_ATOL,
        "endpoint_relative_l2_atol": ENDPOINT_REL_L2_ATOL,
        **hashes,
    }
    _require(config == expected_config, "frozen config differs")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")
    _require(set(bundle["aois"]) == set(AOIS), "bundle AOIs differ")

    expected_keys = {
        "mask",
        "weighted_large_prey",
        "weighted_small_prey",
        "assimilated_large_numerator",
        "assimilated_small_numerator",
        "all_prey_multiplier",
        "large_prey_only_multiplier",
        "all_prey_gain_at_bracket_high",
        "large_prey_only_gain_at_bracket_high",
        "source_prey_floor_c",
        "endpoint_relative_l2_vs_energy",
    }
    summaries = {}
    decomposition_error_by_aoi = {}
    raw_tensor_cells = 0
    for aoi in AOIS:
        item = bundle["aois"][aoi]
        _require(set(item) == expected_keys, f"{aoi}: tensor keys differ")
        shape = AOI_SHAPES[aoi]
        mask = item["mask"]
        _require(mask.dtype == torch.bool and tuple(mask.shape) == shape, f"{aoi}: mask")
        _require(int(mask.sum()) == OCEAN_CELLS[aoi], f"{aoi}: ocean-cell count")
        _require(torch.equal(mask, target_bundle["aois"][aoi]["mask"]), f"{aoi}: target mask")
        _require(torch.equal(mask, energy_bundle["aois"][aoi]["mask"]), f"{aoi}: energy mask")
        for name in (
            "weighted_large_prey",
            "weighted_small_prey",
            "assimilated_large_numerator",
            "assimilated_small_numerator",
        ):
            _require(
                item[name].dtype == torch.float32
                and tuple(item[name].shape) == (TOTAL_STEPS, *shape),
                f"{aoi}.{name}: shape or dtype",
            )
            _require(float(item[name].min()) >= 0.0, f"{aoi}.{name}: negative")
        for name in (
            "all_prey_multiplier",
            "large_prey_only_multiplier",
            "all_prey_gain_at_bracket_high",
            "large_prey_only_gain_at_bracket_high",
        ):
            _require(
                item[name].dtype == torch.float64 and tuple(item[name].shape) == shape,
                f"{aoi}.{name}: shape or dtype",
            )
        _require(
            torch.allclose(
                item["assimilated_large_numerator"],
                0.5 * item["weighted_large_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: large-prey assimilation relation",
        )
        _require(
            torch.allclose(
                item["assimilated_small_numerator"],
                0.7 * item["weighted_small_prey"],
                rtol=0.0,
                atol=1.0e-7,
            ),
            f"{aoi}: small-prey assimilation relation",
        )
        _require(item["source_prey_floor_c"] == SOURCE_PHYGRAZ_MIN_C, f"{aoi}: prey floor")
        support = (
            item["weighted_large_prey"],
            item["weighted_small_prey"],
            item["assimilated_large_numerator"],
            item["assimilated_small_numerator"],
        )
        decomposition_error_by_aoi[aoi] = _validate_prey_decomposition(
            item, energy_bundle["aois"][aoi], aoi
        )
        for mode, root_name, high_name in (
            ("all_prey", "all_prey_multiplier", "all_prey_gain_at_bracket_high"),
            (
                "large_prey_only",
                "large_prey_only_multiplier",
                "large_prey_only_gain_at_bracket_high",
            ),
        ):
            roots, high_gain = _solve_multiplier(
                *support,
                mask,
                mode,
                SOURCE_PHYGRAZ_MIN_C,
            )
            _require(
                torch.allclose(roots, item[root_name], rtol=0.0, atol=2.0e-10, equal_nan=True),
                f"{aoi}.{root_name}: roots differ",
            )
            _require(
                torch.allclose(
                    high_gain, item[high_name], rtol=0.0, atol=2.0e-10, equal_nan=True
                ),
                f"{aoi}.{high_name}: bracket gain differs",
            )
        summary = _summarize(item, energy_bundle["aois"][aoi])
        _compare(summary, report["aois"][aoi]["summary"], f"report.{aoi}.summary")
        summaries[aoi] = summary
        raw_tensor_cells += sum(
            tensor.numel() for tensor in item.values() if isinstance(tensor, torch.Tensor)
        )

    integrity = all(summary["pass"] for summary in summaries.values())
    near_by_aoi = {aoi: summaries[aoi]["near_local_refuge"] for aoi in AOIS}
    if integrity and all(near_by_aoi.values()):
        branch = "near-local-refuge-all-aois"
        primary = "supported"
    elif integrity:
        branch = "near-local-refuge-not-universal"
        primary = "falsified"
    else:
        branch = "unresolved-reproduction-failed"
        primary = "unresolved"
    decision = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "near_local_refuge_by_aoi": near_by_aoi,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    _require(decision == report["decision"], "report decision differs")
    _require(decision == bundle["decision"], "bundle decision differs")
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    _require(report["decision"]["target_rehabilitated"] is False, "target rehabilitated")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "monthly_prey_group_gain_max_abs_error": decomposition_error_by_aoi,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--source-target-report", type=Path, required=True)
    parser.add_argument("--source-target-bundle", type=Path, required=True)
    parser.add_argument("--source-energy-report", type=Path, required=True)
    parser.add_argument("--source-energy-bundle", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()

    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = load_bundle(args.source_target_bundle)
    energy_report = json.loads(args.source_energy_report.read_text(encoding="utf-8"))
    energy_bundle = load_bundle(args.source_energy_bundle)
    hashes = {
        "source_target_report_sha256": _sha256(args.source_target_report),
        "source_target_bundle_sha256": _sha256(args.source_target_bundle),
        "source_energy_report_sha256": _sha256(args.source_energy_report),
        "source_energy_bundle_sha256": _sha256(args.source_energy_bundle),
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
            energy_report=energy_report,
            energy_bundle=energy_bundle,
            hashes=hashes,
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"SUPPORT-THRESHOLD AUDIT VERIFICATION FAILED: {exc}")
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
        "VERIFIED explicit-zoo support-threshold audit: "
        f"decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
