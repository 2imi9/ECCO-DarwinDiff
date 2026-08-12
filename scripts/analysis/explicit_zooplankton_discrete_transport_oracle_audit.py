#!/usr/bin/env python
"""Bound frozen-path large-Z survival with exact discrete Euler factors."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import torch

from darwindiff.explicit_zooplankton import (
    GRAZE_HALF_SATURATION_C,
    GRAZE_MAX_PER_DAY,
    SOURCE_PHYGRAZ_MIN_C,
    ZOO_MORTALITY_PER_DAY,
)

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_discrete_large_z_transport_oracle.md"
)
DEFAULT_SUPPORT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
DEFAULT_SUPPORT_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)
DEFAULT_EXCLUSION_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_exclusion_source_floor_corrected.json"
)
DEFAULT_EXCLUSION_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_exclusion_source_floor_corrected.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_discrete_transport_oracle_audit.json"
)

DT = 0.25
STEPS_PER_MONTH = 122
MONTHS = 12
TOTAL_STEPS = MONTHS * STEPS_PER_MONTH
LOG_REPRODUCTION_ATOL = 5.0e-4


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_bundle(path: Path) -> dict:
    with gzip.open(path, "rb") as stream:
        return torch.load(stream, map_location="cpu", weights_only=True)


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _step_metrics(item: dict) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
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
    gain_rate = (
        GRAZE_MAX_PER_DAY
        * responsive_pool
        / (responsive_pool + GRAZE_HALF_SATURATION_C)
        * numerator
        / source_pool
    )
    continuous_margin = DT * (gain_rate - ZOO_MORTALITY_PER_DAY)
    factor = 1.0 + continuous_margin
    return continuous_margin, factor, torch.log(factor)


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


def _envelope_summary(
    log_values: torch.Tensor,
    continuous_values: torch.Tensor,
    selected: torch.Tensor,
    coordinates: torch.Tensor,
) -> dict:
    log_multiplier = float(log_values.sum())
    continuous_margin = float(continuous_values.sum())
    return {
        "annual_log_multiplier": log_multiplier,
        "annual_retention": float(torch.exp(torch.tensor(log_multiplier, dtype=torch.float64))),
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
            "annual_retention": float(
                torch.exp(torch.tensor(fixed_log, dtype=torch.float64))
            ),
            "continuous_net_margin": fixed_margin,
            "jensen_gap": fixed_margin - fixed_log,
            "row_col": [int(fixed_coordinate[0]), int(fixed_coordinate[1])],
        },
        "monthly_teleport": _envelope_summary(
            monthly_values,
            monthly_continuous_values,
            monthly_selected,
            coordinates,
        ),
        "stepwise_teleport": _envelope_summary(
            step_values,
            step_continuous_values,
            step_selected,
            coordinates,
        ),
    }


def _validate_sources(
    support_report: dict,
    support_bundle: dict,
    exclusion_report: dict,
    exclusion_bundle: dict,
    hashes: dict[str, str],
) -> None:
    if support_report["bundle_artifact"]["sha256"] != hashes["support_bundle_sha256"]:
        raise RuntimeError("support report does not bind its bundle")
    if support_report["config"] != support_bundle["config"]:
        raise RuntimeError("support configs differ")
    if exclusion_report["bundle_artifact"]["sha256"] != hashes[
        "exclusion_bundle_sha256"
    ]:
        raise RuntimeError("exclusion report does not bind its bundle")
    if exclusion_report["config"] != exclusion_bundle["config"]:
        raise RuntimeError("exclusion configs differ")
    if support_report["config"]["source_target_report_sha256"] != exclusion_report[
        "config"
    ]["source_report_sha256"]:
        raise RuntimeError("support and exclusion target reports differ")
    if support_report["config"]["source_target_bundle_sha256"] != exclusion_report[
        "config"
    ]["source_bundle_sha256"]:
        raise RuntimeError("support and exclusion target bundles differ")
    if support_report["config"]["source_prey_floor_c"] != SOURCE_PHYGRAZ_MIN_C:
        raise RuntimeError("support artifact uses the wrong prey floor")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-report", type=Path, default=DEFAULT_SUPPORT_REPORT)
    parser.add_argument("--support-bundle", type=Path, default=DEFAULT_SUPPORT_BUNDLE)
    parser.add_argument("--exclusion-report", type=Path, default=DEFAULT_EXCLUSION_REPORT)
    parser.add_argument("--exclusion-bundle", type=Path, default=DEFAULT_EXCLUSION_BUNDLE)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = _load_bundle(args.support_bundle)
    exclusion_report = json.loads(args.exclusion_report.read_text(encoding="utf-8"))
    exclusion_bundle = _load_bundle(args.exclusion_bundle)
    hashes = {
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
        "exclusion_report_sha256": _sha256(args.exclusion_report),
        "exclusion_bundle_sha256": _sha256(args.exclusion_bundle),
    }
    _validate_sources(
        support_report, support_bundle, exclusion_report, exclusion_bundle, hashes
    )

    config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "months": MONTHS,
        "mortality_per_day": ZOO_MORTALITY_PER_DAY,
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "log_reproduction_atol": LOG_REPRODUCTION_ATOL,
        "oracles": ["fixed_cell", "monthly_teleport", "stepwise_teleport"],
        **hashes,
    }
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "aois": {},
    }
    for aoi in AOIS:
        report["aois"][aoi] = _summarize(
            support_bundle["aois"][aoi], exclusion_bundle["aois"][aoi]
        )

    integrity = all(item["integrity"]["pass"] for item in report["aois"].values())
    nonpositive = {
        aoi: item["stepwise_teleport"]["annual_log_multiplier"] <= 0.0
        for aoi, item in report["aois"].items()
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
    report["decision"] = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "stepwise_log_nonpositive_by_aoi": nonpositive,
        "actual_transport_tested": False,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_json(args.report, report)
    print(
        "discrete transport-oracle audit: "
        f"branch={branch} elapsed={report['elapsed_seconds']:.2f}s"
    )
    return 0 if integrity else 2


if __name__ == "__main__":
    raise SystemExit(main())

