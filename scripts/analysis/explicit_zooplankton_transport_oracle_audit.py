#!/usr/bin/env python
"""Bound frozen-path large-Z gain under unrealistically permissive relocation."""

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
    "docs/findings/2026-08-10_prereg_large_zooplankton_transport_oracle.md"
)
DEFAULT_SUPPORT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
DEFAULT_SUPPORT_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)
DEFAULT_ENERGY_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.json"
)
DEFAULT_ENERGY_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_transport_oracle_audit.json"
)

DT = 0.25
STEPS_PER_MONTH = 122
MONTHS = 12
TOTAL_STEPS = MONTHS * STEPS_PER_MONTH
MORTALITY_INTEGRAL = TOTAL_STEPS * DT * ZOO_MORTALITY_PER_DAY
GAIN_REPRODUCTION_ATOL = 5.0e-5


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


def _jump_summary(selected: torch.Tensor, wet_coordinates: torch.Tensor) -> dict:
    coordinates = wet_coordinates[selected]
    jumps = (coordinates[1:] - coordinates[:-1]).abs().sum(dim=1).double()
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


def _oracle_summary(gains: torch.Tensor, selected: torch.Tensor, coords: torch.Tensor) -> dict:
    integral = float(gains.sum())
    return {
        "gain_integral": integral,
        "gain_to_mortality": integral / MORTALITY_INTEGRAL,
        "margin_vs_mortality": integral - MORTALITY_INTEGRAL,
        **_jump_summary(selected, coords),
    }


def _summarize(item: dict, energy_item: dict) -> dict:
    mask = item["mask"]
    wet_coordinates = mask.nonzero()
    step_gain = _step_gain(item)
    wet_step_gain = step_gain[:, mask]
    fixed_gain = wet_step_gain.sum(dim=0)
    fixed_value, fixed_index = fixed_gain.max(dim=0)

    monthly_gain = wet_step_gain.reshape(MONTHS, STEPS_PER_MONTH, -1).sum(dim=1)
    monthly_values, monthly_selected = monthly_gain.max(dim=1)
    step_values, step_selected = wet_step_gain.max(dim=1)

    expected_monthly = energy_item["monthly_total_specific_gain"][:, 1].double()
    reconstructed_monthly = step_gain.reshape(
        MONTHS, STEPS_PER_MONTH, *mask.shape
    ).sum(dim=1)
    expected_annual = expected_monthly.sum(dim=0)
    reconstructed_annual = step_gain.sum(dim=0)
    monthly_error = float((reconstructed_monthly - expected_monthly).abs()[:, mask].max())
    annual_error = float((reconstructed_annual - expected_annual).abs()[mask].max())
    finite = bool(torch.isfinite(wet_step_gain).all())

    fixed_coordinate = wet_coordinates[fixed_index]
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
            monthly_values, monthly_selected, wet_coordinates
        ),
        "stepwise_teleport": _oracle_summary(
            step_values, step_selected, wet_coordinates
        ),
        "fraction_steps_with_any_instantaneous_refuge": float(
            (wet_step_gain.max(dim=1).values / DT >= ZOO_MORTALITY_PER_DAY)
            .double()
            .mean()
        ),
    }


def _validate_sources(
    support_report: dict,
    support_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
    hashes: dict[str, str],
) -> None:
    if support_report["bundle_artifact"]["sha256"] != hashes["support_bundle_sha256"]:
        raise RuntimeError("support report does not bind its tensor bundle")
    if support_report["config"] != support_bundle["config"]:
        raise RuntimeError("support report/bundle configs differ")
    if energy_report["bundle_artifact"]["sha256"] != hashes["energy_bundle_sha256"]:
        raise RuntimeError("energy report does not bind its tensor bundle")
    if energy_report["config"] != energy_bundle["config"]:
        raise RuntimeError("energy report/bundle configs differ")
    if support_report["config"]["source_energy_report_sha256"] != hashes[
        "energy_report_sha256"
    ]:
        raise RuntimeError("support artifact does not bind the energy report")
    if support_report["config"]["source_energy_bundle_sha256"] != hashes[
        "energy_bundle_sha256"
    ]:
        raise RuntimeError("support artifact does not bind the energy bundle")
    if support_report["config"]["source_prey_floor_c"] != SOURCE_PHYGRAZ_MIN_C:
        raise RuntimeError("support artifact uses the wrong source prey floor")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-report", type=Path, default=DEFAULT_SUPPORT_REPORT)
    parser.add_argument("--support-bundle", type=Path, default=DEFAULT_SUPPORT_BUNDLE)
    parser.add_argument("--energy-report", type=Path, default=DEFAULT_ENERGY_REPORT)
    parser.add_argument("--energy-bundle", type=Path, default=DEFAULT_ENERGY_BUNDLE)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)

    started = time.perf_counter()
    support_report = json.loads(args.support_report.read_text(encoding="utf-8"))
    support_bundle = _load_bundle(args.support_bundle)
    energy_report = json.loads(args.energy_report.read_text(encoding="utf-8"))
    energy_bundle = _load_bundle(args.energy_bundle)
    hashes = {
        "support_report_sha256": _sha256(args.support_report),
        "support_bundle_sha256": _sha256(args.support_bundle),
        "energy_report_sha256": _sha256(args.energy_report),
        "energy_bundle_sha256": _sha256(args.energy_bundle),
    }
    _validate_sources(
        support_report, support_bundle, energy_report, energy_bundle, hashes
    )

    config = {
        "aois": list(AOIS),
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "months": MONTHS,
        "mortality_per_day": ZOO_MORTALITY_PER_DAY,
        "mortality_integral": MORTALITY_INTEGRAL,
        "source_prey_floor_c": SOURCE_PHYGRAZ_MIN_C,
        "gain_reproduction_atol": GAIN_REPRODUCTION_ATOL,
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
            support_bundle["aois"][aoi], energy_bundle["aois"][aoi]
        )

    integrity = all(item["integrity"]["pass"] for item in report["aois"].values())
    clears = {
        aoi: item["stepwise_teleport"]["gain_integral"] >= MORTALITY_INTEGRAL
        for aoi, item in report["aois"].items()
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
    report["decision"] = {
        "branch": branch,
        "integrity_pass": integrity,
        "primary_hypothesis": primary,
        "stepwise_oracle_clears_mortality_by_aoi": clears,
        "actual_transport_tested": False,
        "modified_dynamics_integrated": False,
        "target_rehabilitated": False,
        "b200_authorized": False,
    }
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_json(args.report, report)
    print(
        "transport-oracle audit: "
        f"branch={branch} elapsed={report['elapsed_seconds']:.2f}s"
    )
    return 0 if integrity else 2


if __name__ == "__main__":
    raise SystemExit(main())
