#!/usr/bin/env python
"""Quantify the frozen-prey support needed to offset large-Z mortality."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import torch
from seasonal_twin_target_gate import (
    DEFAULT_AOIS,
    DT,
    _device,
    _load_aoi,
    _parse_aois,
)

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.ecco_darwin_loader import open_bin_average
from darwindiff.explicit_zooplankton import (
    CHEMICAL_RESTORING_INDICES,
    GRAZE_HALF_SATURATION_C,
    GRAZE_MAX_PER_DAY,
    I_Z_LARGE,
    I_Z_SMALL,
    SOURCE_PHYGRAZ_MIN_C,
    ZOO_MORTALITY_PER_DAY,
    explicit_zooplankton_step,
)
from darwindiff.seasonal_twin import astronomical_monthly_light

PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_large_zooplankton_support_threshold_audit.md"
)
SOURCE_TARGET_REPORT = Path(
    "docs/findings/2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected.json"
)
SOURCE_TARGET_BUNDLE = Path(
    "docs/findings/2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected.pt.gz"
)
SOURCE_ENERGY_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.json"
)
SOURCE_ENERGY_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.json"
)
DEFAULT_BUNDLE = Path(
    "docs/findings/2026-08-10_explicit_zooplankton_support_threshold_audit.pt.gz"
)

STEPS_PER_MONTH = 122
RESTORING_TAU_DAYS = 365.25
CENTRAL_SCENARIO = "ic_0p10"
TOTAL_STEPS = 12 * STEPS_PER_MONTH
MORTALITY_INTEGRAL = TOTAL_STEPS * DT * ZOO_MORTALITY_PER_DAY
MULTIPLIER_LOW = 1.0
MULTIPLIER_HIGH = 64.0
BISECTION_ITERATIONS = 48
NEAR_REFUGE_THRESHOLD = 1.25
REPORT_THRESHOLDS = (1.10, 1.25, 1.50, 2.0, 4.0)
GAIN_REPRODUCTION_ATOL = 5.0e-5
ENDPOINT_REL_L2_ATOL = 2.0e-5


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


def _atomic_gzip_torch_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as stream:
        torch.save(payload, stream)
    temporary.replace(path)


def _relative_l2(actual: torch.Tensor, expected: torch.Tensor, mask: torch.Tensor) -> float:
    numerator = torch.linalg.vector_norm((actual - expected)[:, mask].double())
    denominator = torch.linalg.vector_norm(expected[:, mask].double()).clamp(min=1.0e-300)
    return float(numerator / denominator)


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
    """Evaluate annual gain on a fixed trajectory in float64."""
    alpha = torch.as_tensor(multiplier, dtype=torch.float64, device=large_pool.device)
    if mode == "all_prey":
        pool = alpha * (large_pool.double() + small_pool.double())
        numerator = alpha * (large_numerator.double() + small_numerator.double())
    elif mode == "large_prey_only":
        pool = alpha * large_pool.double() + small_pool.double()
        numerator = alpha * large_numerator.double() + small_numerator.double()
    else:
        raise ValueError(f"unknown counterfactual mode: {mode}")
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
    low = torch.full((count,), MULTIPLIER_LOW, dtype=torch.float64, device=mask.device)
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
    root_grid = torch.full(mask.shape, float("nan"), dtype=torch.float64, device=mask.device)
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
    canonical_gain = _annual_gain(
        item["weighted_large_prey"],
        item["weighted_small_prey"],
        item["assimilated_large_numerator"],
        item["assimilated_small_numerator"],
        1.0,
        "all_prey",
        item["source_prey_floor_c"],
    ).cpu()
    canonical_monthly = (
        _annual_gain(
            item["weighted_large_prey"].reshape(12, STEPS_PER_MONTH, *mask.shape),
            item["weighted_small_prey"].reshape(12, STEPS_PER_MONTH, *mask.shape),
            item["assimilated_large_numerator"].reshape(
                12, STEPS_PER_MONTH, *mask.shape
            ),
            item["assimilated_small_numerator"].reshape(
                12, STEPS_PER_MONTH, *mask.shape
            ),
            1.0,
            "all_prey",
            item["source_prey_floor_c"],
            sum_dim=1,
        )
        .cpu()
    )
    expected_gain = energy_item["monthly_total_specific_gain"][:, 1].sum(dim=0).double()
    expected_monthly = energy_item["monthly_total_specific_gain"][:, 1].double()
    gain_error = (canonical_gain - expected_gain).abs()
    monthly_gain_error = (canonical_monthly - expected_monthly).abs()
    subsidy = ((MORTALITY_INTEGRAL - canonical_gain) / (TOTAL_STEPS * DT)).clamp(min=0.0)
    subsidy_fraction = subsidy / ZOO_MORTALITY_PER_DAY
    all_summary = _root_summary(item["all_prey_multiplier"], mask)
    large_summary = _root_summary(item["large_prey_only_multiplier"], mask)
    minimum_ratio = None
    if all_summary["minimum"] is not None and large_summary["minimum"] is not None:
        minimum_ratio = large_summary["minimum"] / all_summary["minimum"]
    maximum_gain_error = float(gain_error[mask].max())
    maximum_monthly_gain_error = float(monthly_gain_error[:, mask].max())
    finite = all(
        bool(torch.isfinite(item[name]).all())
        for name in (
            "weighted_large_prey",
            "weighted_small_prey",
            "assimilated_large_numerator",
            "assimilated_small_numerator",
        )
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


def _validate_sources(
    target_report: dict,
    target_bundle: dict,
    energy_report: dict,
    energy_bundle: dict,
    hashes: dict[str, str],
) -> float:
    if target_report["bundle_artifact"]["sha256"] != hashes["source_target_bundle_sha256"]:
        raise RuntimeError("source target report does not bind its tensor bundle")
    if target_report["config"] != target_bundle["config"]:
        raise RuntimeError("source target report/bundle configs differ")
    if energy_report["bundle_artifact"]["sha256"] != hashes["source_energy_bundle_sha256"]:
        raise RuntimeError("source energy report does not bind its tensor bundle")
    if energy_report["config"] != energy_bundle["config"]:
        raise RuntimeError("source energy report/bundle configs differ")
    if energy_bundle["decision"]["branch"] != "prey-field-energy-deficit":
        raise RuntimeError("source energy artifact has the wrong decision")
    config = energy_bundle["config"]
    if config["source_target_report_sha256"] != hashes["source_target_report_sha256"]:
        raise RuntimeError("source energy artifact does not bind the target report")
    if config["source_target_bundle_sha256"] != hashes["source_target_bundle_sha256"]:
        raise RuntimeError("source energy artifact does not bind the target bundle")
    floor = float(config["source_prey_floor_c"])
    if floor != SOURCE_PHYGRAZ_MIN_C:
        raise RuntimeError("source energy artifact lacks the corrected prey floor")
    return floor


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
    parser.add_argument(
        "--bin-average",
        type=Path,
        default=default_root / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc",
    )
    parser.add_argument("--aois", type=_parse_aois, default=DEFAULT_AOIS)
    parser.add_argument("--device", type=_device, default=torch.device("cuda"))
    parser.add_argument("--compile", action="store_true", dest="compile_step")
    parser.add_argument("--source-target-report", type=Path, default=SOURCE_TARGET_REPORT)
    parser.add_argument("--source-target-bundle", type=Path, default=SOURCE_TARGET_BUNDLE)
    parser.add_argument("--source-energy-report", type=Path, default=SOURCE_ENERGY_REPORT)
    parser.add_argument("--source-energy-bundle", type=Path, default=SOURCE_ENERGY_BUNDLE)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args(argv)

    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = _load_bundle(args.source_target_bundle)
    energy_report = json.loads(args.source_energy_report.read_text(encoding="utf-8"))
    energy_bundle = _load_bundle(args.source_energy_bundle)
    hashes = {
        "source_target_report_sha256": _sha256(args.source_target_report),
        "source_target_bundle_sha256": _sha256(args.source_target_bundle),
        "source_energy_report_sha256": _sha256(args.source_energy_report),
        "source_energy_bundle_sha256": _sha256(args.source_energy_bundle),
    }
    source_prey_floor_c = _validate_sources(
        target_report, target_bundle, energy_report, energy_bundle, hashes
    )

    device = args.device
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by the full-resolution audit")
    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    layer2.USE_COCCOLITH_ONLY_CALCITE = False
    layer2.USE_ENV_RAIN_RATIO = False
    step_fn = explicit_zooplankton_step
    if args.compile_step:
        step_fn = torch.compile(step_fn, backend="inductor", fullgraph=True, dynamic=False)

    config = {
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "audit_cycle": 13,
        "aois": list(args.aois),
        "scenario": CENTRAL_SCENARIO,
        "chemical_restoring_tau_days": RESTORING_TAU_DAYS,
        "restoring_indices": list(CHEMICAL_RESTORING_INDICES),
        "zooplankton_restoring": False,
        "source_prey_floor_c": source_prey_floor_c,
        "mortality_per_day": ZOO_MORTALITY_PER_DAY,
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
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "runtime": {
            "device": str(device),
            "compiled_step": bool(args.compile_step),
        },
        "aois": {},
    }
    if device.type == "cuda":
        report["runtime"]["device_name"] = torch.cuda.get_device_name(device)
    bundle = {
        "schema_version": 1,
        "preregistration": args.preregistration,
        "config": config,
        "aois": {},
    }

    started = time.perf_counter()
    dataset = open_bin_average(args.bin_average)
    try:
        for aoi in args.aois:
            aoi_started = time.perf_counter()
            _, forcing, mask, _ = _load_aoi(dataset, aoi, device)
            target_item = target_bundle["aois"][aoi]
            energy_item = energy_bundle["aois"][aoi]
            if not torch.equal(mask.cpu(), target_item["mask"]):
                raise RuntimeError(f"{aoi}: target and live masks differ")
            if not torch.equal(mask.cpu(), energy_item["mask"]):
                raise RuntimeError(f"{aoi}: energy and live masks differ")
            scenario = target_item["scenarios"][CENTRAL_SCENARIO]
            state = scenario["cycle12_endpoint"].to(device)
            restoring_reference = scenario["initial_state"].to(device)
            light = astronomical_monthly_light(forcing["latitude_degrees"])
            height, width = mask.shape
            params = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
            params = params.expand(6, height, width).contiguous()
            selector = torch.zeros_like(state)
            selector[list(CHEMICAL_RESTORING_INDICES)] = mask.to(state.dtype)
            weighted_large: list[torch.Tensor] = []
            weighted_small: list[torch.Tensor] = []
            numerator_large: list[torch.Tensor] = []
            numerator_small: list[torch.Tensor] = []

            with torch.no_grad():
                for month in range(12):
                    for _ in range(STEPS_PER_MONTH):
                        phyto = state[list(layer2.PHYTOPLANKTON_STATE_INDICES)]
                        large_pool = params[layer2.I_DIATOMGRAZ] * phyto[0] + 0.90 * phyto[1]
                        small_pool = 0.20 * phyto[2:].sum(dim=0)
                        weighted_large.append(large_pool)
                        weighted_small.append(small_pool)
                        numerator_large.append(0.50 * large_pool)
                        numerator_small.append(0.70 * small_pool)
                        model_next = step_fn(
                            state,
                            params,
                            DT,
                            forcing["T_monthly"][month],
                            forcing["S_monthly"][month],
                            forcing["wind_monthly"][month],
                            forcing["pco2_atm"],
                            layer2.H1,
                            layer2.H2,
                            layer2.KZ_M2_PER_DAY,
                            layer2.R_REMIN,
                            light[month],
                            source_prey_floor_c,
                        )
                        requested = (
                            DT
                            * (restoring_reference - state)
                            / RESTORING_TAU_DAYS
                            * selector
                        )
                        state = (model_next + requested).clamp(min=0.0)

            support = {
                "weighted_large_prey": torch.stack(weighted_large),
                "weighted_small_prey": torch.stack(weighted_small),
                "assimilated_large_numerator": torch.stack(numerator_large),
                "assimilated_small_numerator": torch.stack(numerator_small),
            }
            all_root, all_high_gain = _solve_multiplier(
                support["weighted_large_prey"],
                support["weighted_small_prey"],
                support["assimilated_large_numerator"],
                support["assimilated_small_numerator"],
                mask=mask,
                mode="all_prey",
                source_prey_floor_c=source_prey_floor_c,
            )
            large_root, large_high_gain = _solve_multiplier(
                support["weighted_large_prey"],
                support["weighted_small_prey"],
                support["assimilated_large_numerator"],
                support["assimilated_small_numerator"],
                mask=mask,
                mode="large_prey_only",
                source_prey_floor_c=source_prey_floor_c,
            )
            endpoint_rel_l2 = _relative_l2(
                state[[I_Z_SMALL, I_Z_LARGE]], energy_item["end_zoo"].to(device), mask
            )
            item = {
                "mask": mask.cpu(),
                **{name: tensor.cpu() for name, tensor in support.items()},
                "all_prey_multiplier": all_root.cpu(),
                "large_prey_only_multiplier": large_root.cpu(),
                "all_prey_gain_at_bracket_high": all_high_gain.cpu(),
                "large_prey_only_gain_at_bracket_high": large_high_gain.cpu(),
                "source_prey_floor_c": source_prey_floor_c,
                "endpoint_relative_l2_vs_energy": endpoint_rel_l2,
            }
            summary = _summarize(item, energy_item)
            report["aois"][aoi] = {
                "summary": summary,
                "elapsed_seconds": time.perf_counter() - aoi_started,
            }
            bundle["aois"][aoi] = item
            minimum = summary["all_prey_multiplier"]["minimum"]
            minimum_text = "unbracketed" if minimum is None else f"{minimum:.6g}"
            print(
                f"{aoi}: all-prey min={minimum_text} "
                f"bracketed={summary['all_prey_multiplier']['bracketed_count']}/"
                f"{summary['all_prey_multiplier']['ocean_cell_count']} "
                f"near={summary['near_local_refuge']}"
            )
            del support, weighted_large, weighted_small, numerator_large, numerator_small
    finally:
        dataset.close()

    integrity = all(item["summary"]["pass"] for item in report["aois"].values())
    near_by_aoi = {
        aoi: item["summary"]["near_local_refuge"] for aoi, item in report["aois"].items()
    }
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
    report["decision"] = decision
    bundle["decision"] = decision
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_gzip_torch_save(args.bundle, bundle)
    report["bundle_artifact"] = {
        "path": args.bundle.as_posix(),
        "bytes": args.bundle.stat().st_size,
        "sha256": _sha256(args.bundle),
    }
    _atomic_json(args.report, report)
    print(f"decision={branch} report={args.report} bundle={args.bundle}")
    return 0 if integrity else 2


if __name__ == "__main__":
    raise SystemExit(main())
