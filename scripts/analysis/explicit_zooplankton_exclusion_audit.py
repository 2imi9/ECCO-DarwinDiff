#!/usr/bin/env python3
"""Run the preregistered cycle-13 explicit-zooplankton exclusion audit."""

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
    CHEMICAL_RESTORING_INDICES,
    I_Z_LARGE,
    I_Z_SMALL,
    SOURCE_PHYGRAZ_MIN_C,
    darwin1_explicit_grazing_rates,
    explicit_zooplankton_step,
)
from darwindiff.seasonal_twin import astronomical_monthly_light

PREREGISTRATION = "docs/findings/2026-08-09_prereg_explicit_zooplankton_exclusion_audit.md"
SOURCE_REPORT = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
SOURCE_BUNDLE = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json"
)
DEFAULT_BUNDLE = Path(
    "docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz"
)
STEPS_PER_MONTH = 122
RESTORING_TAU_DAYS = 365.25
CENTRAL_SCENARIO = "ic_0p10"
PREDATOR_NAMES = ("z_small", "z_large")
LOG_RATIO_ATOL = 5.0e-4


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_gzip_bundle(path: Path) -> dict:
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


def _classification(values: torch.Tensor) -> str:
    maximum = float(values.max())
    minimum = float(values.min())
    if maximum < -0.10:
        return "uniformly-excluded"
    if minimum > 0.10:
        return "uniformly-viable"
    return "mixed-or-near-neutral"


def _summarize(
    monthly_log: torch.Tensor,
    monthly_events: torch.Tensor,
    monthly_min_factor: torch.Tensor,
    start_zoo: torch.Tensor,
    end_zoo: torch.Tensor,
    mask: torch.Tensor,
) -> dict:
    annual = monthly_log.sum(dim=0).double()
    actual = torch.log(end_zoo.double() / start_zoo.double())
    discrepancy = (annual - actual).abs()
    output = {}
    for index, name in enumerate(PREDATOR_NAMES):
        values = annual[index][mask]
        events = int(monthly_events[:, index][:, mask].sum())
        denominator = 12 * STEPS_PER_MONTH * int(mask.sum())
        output[name] = {
            "classification": _classification(values),
            "annual_log_multiplier_min": float(values.min()),
            "annual_log_multiplier_median": float(values.median()),
            "annual_log_multiplier_max": float(values.max()),
            "annual_multiplier_min": float(values.exp().min()),
            "annual_multiplier_median": float(values.exp().median()),
            "annual_multiplier_max": float(values.exp().max()),
            "positive_rate_step_fraction": events / denominator,
            "minimum_euler_factor": float(monthly_min_factor[:, index][:, mask].min()),
            "start_inventory": float(start_zoo[index][mask].double().sum()),
            "end_inventory": float(end_zoo[index][mask].double().sum()),
            "inventory_retention": float(
                end_zoo[index][mask].double().sum()
                / start_zoo[index][mask].double().sum().clamp(min=1e-300)
            ),
            "maximum_log_ratio_discrepancy": float(discrepancy[index][mask].max()),
        }
    maximum_discrepancy = float(discrepancy[:, mask].max())
    finite = all(
        bool(torch.isfinite(tensor).all())
        for tensor in (
            monthly_log,
            monthly_min_factor,
            start_zoo,
            end_zoo,
        )
    )
    return {
        "pass": finite
        and float(monthly_min_factor[:, :, mask].min()) > 0.0
        and float(end_zoo[:, mask].min()) > 0.0
        and maximum_discrepancy <= LOG_RATIO_ATOL,
        "finite": finite,
        "strictly_positive_euler_factors": float(monthly_min_factor[:, :, mask].min())
        > 0.0,
        "strictly_positive_endpoint_biomass": float(end_zoo[:, mask].min()) > 0.0,
        "maximum_log_ratio_discrepancy": maximum_discrepancy,
        "log_ratio_discrepancy_atol": LOG_RATIO_ATOL,
        "predators": output,
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
    parser.add_argument("--source-report", type=Path, default=SOURCE_REPORT)
    parser.add_argument("--source-bundle", type=Path, default=SOURCE_BUNDLE)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args(argv)

    source_report = json.loads(args.source_report.read_text(encoding="utf-8"))
    source_bundle = _load_gzip_bundle(args.source_bundle)
    if source_report["bundle_artifact"]["sha256"] != _sha256(args.source_bundle):
        raise RuntimeError("source explicit-zoo bundle hash differs")
    if source_report["config"] != source_bundle["config"]:
        raise RuntimeError("source explicit-zoo report/bundle configs differ")
    if source_bundle["decision"]["branch"] != "stage0-failed-stop":
        raise RuntimeError("source bundle is not the registered failed target")
    source_prey_floor_c = float(
        source_bundle["config"].get("source_prey_floor_c", 0.0)
    )
    if (
        not math.isfinite(source_prey_floor_c)
        or source_prey_floor_c not in (0.0, SOURCE_PHYGRAZ_MIN_C)
    ):
        raise RuntimeError("source target has an unregistered prey floor")

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
        "log_ratio_discrepancy_atol": LOG_RATIO_ATOL,
        "source_report_sha256": _sha256(args.source_report),
        "source_bundle_sha256": _sha256(args.source_bundle),
    }
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "runtime": {
            "device": str(device),
            "device_name": torch.cuda.get_device_name(device),
            "compiled_step": compiled,
        },
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
            source_item = source_bundle["aois"][aoi]
            if not torch.equal(mask.cpu(), source_item["mask"]):
                raise RuntimeError(f"{aoi}: source and live masks differ")
            source_scenario = source_item["scenarios"][CENTRAL_SCENARIO]
            state = source_scenario["cycle12_endpoint"].to(device)
            restoring_reference = source_scenario["initial_state"].to(device)
            start_zoo = state[[I_Z_SMALL, I_Z_LARGE]].clone()
            light = astronomical_monthly_light(forcing["latitude_degrees"])
            height, width = mask.shape
            params = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
            params = params.expand(6, height, width).contiguous()
            selector = torch.zeros_like(state)
            selector[list(CHEMICAL_RESTORING_INDICES)] = mask.to(state.dtype)
            monthly_log = []
            monthly_events = []
            monthly_min_factor = []

            with torch.no_grad():
                for month in range(12):
                    log_sum = torch.zeros((2, height, width), device=device)
                    events = torch.zeros(
                        (2, height, width), dtype=torch.int64, device=device
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
                        specific_net = rates["zoo_specific_net"]
                        factor = 1.0 + DT * specific_net
                        log_sum += torch.log(factor)
                        events += (specific_net > 0.0).to(torch.int64)
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
                    monthly_log.append(log_sum)
                    monthly_events.append(events)
                    monthly_min_factor.append(min_factor)
            _synchronize(device)
            tensors = {
                "mask": mask.cpu(),
                "start_zoo": start_zoo.cpu(),
                "end_zoo": state[[I_Z_SMALL, I_Z_LARGE]].cpu(),
                "monthly_log_multiplier": torch.stack(monthly_log).cpu(),
                "monthly_positive_rate_events": torch.stack(monthly_events).cpu(),
                "monthly_min_euler_factor": torch.stack(monthly_min_factor).cpu(),
            }
            summary = _summarize(
                tensors["monthly_log_multiplier"],
                tensors["monthly_positive_rate_events"],
                tensors["monthly_min_euler_factor"],
                tensors["start_zoo"],
                tensors["end_zoo"],
                tensors["mask"],
            )
            report["aois"][aoi] = {
                "summary": summary,
                "elapsed_seconds": time.perf_counter() - aoi_started,
            }
            bundle["aois"][aoi] = tensors
            print(
                f"{aoi}: large={summary['predators']['z_large']['classification']} "
                f"Lambda_max={summary['predators']['z_large']['annual_log_multiplier_max']:.3f} "
                f"identity={summary['maximum_log_ratio_discrepancy']:.2e}"
            )
    finally:
        dataset.close()

    integrity = all(item["summary"]["pass"] for item in report["aois"].values())
    large_classes = {
        aoi: item["summary"]["predators"]["z_large"]["classification"]
        for aoi, item in report["aois"].items()
    }
    if integrity and all(value == "uniformly-excluded" for value in large_classes.values()):
        branch = "endogenous-large-predator-exclusion"
    elif integrity and len(set(large_classes.values())) > 1:
        branch = "spatially-mixed-large-predator-viability"
    else:
        branch = "unresolved-or-numerical"
    report["decision"] = {
        "branch": branch,
        "integrity_pass": integrity,
        "large_predator_classification_by_aoi": large_classes,
        "b200_authorized": False,
        "target_rehabilitated": False,
    }
    bundle["decision"] = report["decision"]
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
