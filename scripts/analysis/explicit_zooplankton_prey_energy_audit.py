#!/usr/bin/env python3
"""Run the preregistered prey-energy audit on the excluded predator mode."""

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
    _synchronize,
)

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.ecco_darwin_loader import open_bin_average
from darwindiff.explicit_zooplankton import (
    ASSIMILATION,
    CHEMICAL_RESTORING_INDICES,
    I_Z_LARGE,
    I_Z_SMALL,
    SOURCE_PHYGRAZ_MIN_C,
    ZOO_MORTALITY_PER_DAY,
    darwin1_explicit_grazing_rates,
    explicit_zooplankton_step,
)
from darwindiff.seasonal_twin import astronomical_monthly_light

PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_explicit_zooplankton_prey_energy_audit.md"
)
SOURCE_TARGET_REPORT = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
SOURCE_TARGET_BUNDLE = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
)
SOURCE_EXCLUSION_REPORT = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json"
)
SOURCE_EXCLUSION_BUNDLE = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.json"
)
DEFAULT_BUNDLE = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.pt.gz"
)

STEPS_PER_MONTH = 122
RESTORING_TAU_DAYS = 365.25
CENTRAL_SCENARIO = "ic_0p10"
PREDATOR_NAMES = ("z_small", "z_large")
PREY_NAMES = ("diatom", "lge", "syn", "proLL", "proHL")
LARGE_PREY_INDICES = (0, 1)
SMALL_PREY_INDICES = (2, 3, 4)
PARTITION_ATOL = 5.0e-5
LOG_RATIO_ATOL = 5.0e-4
PRIOR_LOG_ATOL = 5.0e-4
PRIOR_ENDPOINT_REL_L2_ATOL = 2.0e-5
CONTINUOUS_EXCLUSION_THRESHOLD = -0.10


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


def _aoi_classification(
    large_margin: torch.Tensor,
    large_exact_log: torch.Tensor,
) -> str:
    if float(large_exact_log.max()) >= CONTINUOUS_EXCLUSION_THRESHOLD:
        return "inconsistent-with-prior-exclusion"
    if float(large_margin.max()) < CONTINUOUS_EXCLUSION_THRESHOLD:
        return "continuous-energetic-deficit"
    return "discrete-or-variance-penalty"


def _summarize(
    tensors: dict[str, torch.Tensor],
    prior: dict[str, torch.Tensor],
) -> dict:
    mask = tensors["mask"]
    monthly_by_prey = tensors["monthly_specific_gain_by_prey"]
    monthly_total = tensors["monthly_total_specific_gain"]
    monthly_log = tensors["monthly_log_multiplier"]
    monthly_min_factor = tensors["monthly_min_euler_factor"]
    start_zoo = tensors["start_zoo"]
    end_zoo = tensors["end_zoo"]

    annual_by_prey = monthly_by_prey.sum(dim=0).double()
    annual_total = monthly_total.sum(dim=0).double()
    annual_from_parts = annual_by_prey.sum(dim=0)
    mortality_integral = 12 * STEPS_PER_MONTH * DT * ZOO_MORTALITY_PER_DAY
    continuous_margin = annual_total - mortality_integral
    exact_log = monthly_log.sum(dim=0).double()
    endpoint_log = torch.log(end_zoo.double() / start_zoo.double())

    partition_error = (annual_from_parts - annual_total).abs()
    identity_error = (exact_log - endpoint_log).abs()
    prior_log_error = (
        monthly_log.double() - prior["monthly_log_multiplier"].double()
    ).abs()
    prior_endpoint_rel_l2 = _relative_l2(
        end_zoo,
        prior["end_zoo"],
        mask,
    )

    predators = {}
    for predator_index, predator_name in enumerate(PREDATOR_NAMES):
        total = annual_total[predator_index][mask]
        margin = continuous_margin[predator_index][mask]
        log_values = exact_log[predator_index][mask]
        denominator = annual_total[predator_index].clamp(min=1.0e-300)
        shares = annual_by_prey[:, predator_index] / denominator.unsqueeze(0)
        prey_shares = {
            prey_name: float(shares[prey_index][mask].median())
            for prey_index, prey_name in enumerate(PREY_NAMES)
        }
        large_share = shares[list(LARGE_PREY_INDICES)].sum(dim=0)[mask]
        small_share = shares[list(SMALL_PREY_INDICES)].sum(dim=0)[mask]
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
    nonnegative_contributions = float(monthly_by_prey[:, :, :, mask].min()) >= 0.0
    positive_factors = float(monthly_min_factor[:, :, mask].min()) > 0.0
    positive_endpoints = float(end_zoo[:, mask].min()) > 0.0
    maximum_partition_error = float(partition_error[:, mask].max())
    maximum_identity_error = float(identity_error[:, mask].max())
    maximum_prior_log_error = float(prior_log_error[:, :, mask].max())
    large_margin = continuous_margin[1][mask]
    large_exact_log = exact_log[1][mask]
    classification = _aoi_classification(large_margin, large_exact_log)
    integrity = (
        finite
        and nonnegative_contributions
        and positive_factors
        and positive_endpoints
        and maximum_partition_error <= PARTITION_ATOL
        and math.isclose(mortality_integral, 12.2, abs_tol=1.0e-7)
        and maximum_identity_error <= LOG_RATIO_ATOL
        and maximum_prior_log_error <= PRIOR_LOG_ATOL
        and prior_endpoint_rel_l2 <= PRIOR_ENDPOINT_REL_L2_ATOL
    )
    return {
        "pass": integrity,
        "finite": finite,
        "nonnegative_gain_contributions": nonnegative_contributions,
        "strictly_positive_euler_factors": positive_factors,
        "strictly_positive_endpoint_biomass": positive_endpoints,
        "mortality_integral": mortality_integral,
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
    parser.add_argument(
        "--source-exclusion-report",
        type=Path,
        default=SOURCE_EXCLUSION_REPORT,
    )
    parser.add_argument(
        "--source-exclusion-bundle",
        type=Path,
        default=SOURCE_EXCLUSION_BUNDLE,
    )
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args(argv)

    target_report = json.loads(args.source_target_report.read_text(encoding="utf-8"))
    target_bundle = _load_bundle(args.source_target_bundle)
    exclusion_report = json.loads(
        args.source_exclusion_report.read_text(encoding="utf-8")
    )
    exclusion_bundle = _load_bundle(args.source_exclusion_bundle)
    target_report_hash = _sha256(args.source_target_report)
    target_bundle_hash = _sha256(args.source_target_bundle)
    exclusion_report_hash = _sha256(args.source_exclusion_report)
    exclusion_bundle_hash = _sha256(args.source_exclusion_bundle)
    if target_report["bundle_artifact"]["sha256"] != target_bundle_hash:
        raise RuntimeError("source target report does not bind its tensor bundle")
    if target_report["config"] != target_bundle["config"]:
        raise RuntimeError("source target report/bundle configs differ")
    if exclusion_report["bundle_artifact"]["sha256"] != exclusion_bundle_hash:
        raise RuntimeError("source exclusion report does not bind its tensor bundle")
    if exclusion_bundle["decision"]["branch"] != "endogenous-large-predator-exclusion":
        raise RuntimeError("source exclusion artifact has the wrong decision")
    if exclusion_bundle["config"]["source_report_sha256"] != target_report_hash:
        raise RuntimeError("source exclusion artifact does not bind the target report")
    if exclusion_bundle["config"]["source_bundle_sha256"] != target_bundle_hash:
        raise RuntimeError("source exclusion artifact does not bind the target bundle")
    source_prey_floor_c = float(
        target_bundle["config"].get("source_prey_floor_c", 0.0)
    )
    if (
        not math.isfinite(source_prey_floor_c)
        or source_prey_floor_c not in (0.0, SOURCE_PHYGRAZ_MIN_C)
    ):
        raise RuntimeError("source target has an unregistered prey floor")
    if (
        float(exclusion_bundle["config"].get("source_prey_floor_c", 0.0))
        != source_prey_floor_c
    ):
        raise RuntimeError("source exclusion prey floor differs from target")

    device = args.device
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by the full-resolution audit")
    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    layer2.USE_COCCOLITH_ONLY_CALCITE = False
    layer2.USE_ENV_RAIN_RATIO = False
    step_fn = explicit_zooplankton_step
    compiled = False
    if args.compile_step:
        step_fn = torch.compile(
            explicit_zooplankton_step,
            backend="inductor",
            fullgraph=True,
            dynamic=False,
        )
        compiled = True

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
        "predator_names": list(PREDATOR_NAMES),
        "prey_names": list(PREY_NAMES),
        "assimilation": [list(row) for row in ASSIMILATION],
        "mortality_per_day": ZOO_MORTALITY_PER_DAY,
        "partition_atol": PARTITION_ATOL,
        "log_ratio_atol": LOG_RATIO_ATOL,
        "prior_monthly_log_atol": PRIOR_LOG_ATOL,
        "prior_endpoint_relative_l2_atol": PRIOR_ENDPOINT_REL_L2_ATOL,
        "continuous_exclusion_threshold": CONTINUOUS_EXCLUSION_THRESHOLD,
        "source_target_report_sha256": target_report_hash,
        "source_target_bundle_sha256": target_bundle_hash,
        "source_exclusion_report_sha256": exclusion_report_hash,
        "source_exclusion_bundle_sha256": exclusion_bundle_hash,
    }
    runtime = {
        "device": str(device),
        "compiled_step": compiled,
    }
    if device.type == "cuda":
        runtime["device_name"] = torch.cuda.get_device_name(device)
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "runtime": runtime,
        "aois": {},
        "decision": {"b200_authorized": False},
    }
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
            prior_item = exclusion_bundle["aois"][aoi]
            if not torch.equal(mask.cpu(), target_item["mask"]):
                raise RuntimeError(f"{aoi}: target and live masks differ")
            if not torch.equal(mask.cpu(), prior_item["mask"]):
                raise RuntimeError(f"{aoi}: exclusion and live masks differ")
            scenario = target_item["scenarios"][CENTRAL_SCENARIO]
            state = scenario["cycle12_endpoint"].to(device)
            restoring_reference = scenario["initial_state"].to(device)
            start_zoo = state[[I_Z_SMALL, I_Z_LARGE]].clone()
            if not torch.equal(start_zoo.cpu(), prior_item["start_zoo"]):
                raise RuntimeError(f"{aoi}: prior exclusion start state differs")
            light = astronomical_monthly_light(forcing["latitude_degrees"])
            height, width = mask.shape
            params = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
            params = params.expand(6, height, width).contiguous()
            selector = torch.zeros_like(state)
            selector[list(CHEMICAL_RESTORING_INDICES)] = mask.to(state.dtype)
            monthly_by_prey = []
            monthly_total = []
            monthly_log = []
            monthly_min_factor = []

            with torch.no_grad():
                for month in range(12):
                    by_prey_sum = torch.zeros(
                        (5, 2, height, width), dtype=torch.float64, device=device
                    )
                    total_sum = torch.zeros(
                        (2, height, width), dtype=torch.float64, device=device
                    )
                    log_sum = torch.zeros(
                        (2, height, width), dtype=torch.float64, device=device
                    )
                    min_factor = torch.full(
                        (2, height, width), float("inf"), device=device
                    )
                    for _ in range(STEPS_PER_MONTH):
                        rates = darwin1_explicit_grazing_rates(
                            state,
                            params,
                            source_prey_floor_c=source_prey_floor_c,
                        )
                        by_prey_sum += (
                            DT * rates["zoo_specific_gain_by_prey"].double()
                        )
                        total_sum += DT * rates["zoo_specific_gain"].double()
                        factor = 1.0 + DT * rates["zoo_specific_net"]
                        log_sum += torch.log(factor.double())
                        min_factor = torch.minimum(min_factor, factor)
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
                    monthly_by_prey.append(by_prey_sum)
                    monthly_total.append(total_sum)
                    monthly_log.append(log_sum)
                    monthly_min_factor.append(min_factor)
            _synchronize(device)
            tensors = {
                "mask": mask.cpu(),
                "start_zoo": start_zoo.cpu(),
                "end_zoo": state[[I_Z_SMALL, I_Z_LARGE]].cpu(),
                "monthly_specific_gain_by_prey": torch.stack(monthly_by_prey).cpu(),
                "monthly_total_specific_gain": torch.stack(monthly_total).cpu(),
                "monthly_log_multiplier": torch.stack(monthly_log).cpu(),
                "monthly_min_euler_factor": torch.stack(monthly_min_factor).cpu(),
            }
            summary = _summarize(tensors, prior_item)
            report["aois"][aoi] = {
                "summary": summary,
                "elapsed_seconds": time.perf_counter() - aoi_started,
            }
            bundle["aois"][aoi] = tensors
            large = summary["predators"]["z_large"]
            print(
                f"{aoi}: {summary['large_predator_classification']} "
                f"Cmax={large['continuous_margin_max']:.3f} "
                f"Lambda_max={large['exact_log_multiplier_max']:.3f}"
            )
    finally:
        dataset.close()

    integrity = all(item["summary"]["pass"] for item in report["aois"].values())
    classes = {
        aoi: item["summary"]["large_predator_classification"]
        for aoi, item in report["aois"].items()
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
