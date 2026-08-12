#!/usr/bin/env python3
"""Measure rare-diatom invasion on the frozen seasonal resident trajectory."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import time
from pathlib import Path

import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.ecco_darwin_loader import open_bin_average
from darwindiff.seasonal_twin import (
    CHEMICAL_RESTORING_INDICES,
    STATE_NAMES,
    astronomical_monthly_light,
)

try:
    from scripts.analysis.seasonal_twin_target_gate import (
        DEFAULT_AOIS,
        DT,
        _device,
        _load_aoi,
        _parse_aois,
        _synchronize,
    )
except ModuleNotFoundError:  # Direct execution from scripts/analysis.
    from seasonal_twin_target_gate import (  # type: ignore[no-redef]
        DEFAULT_AOIS,
        DT,
        _device,
        _load_aoi,
        _parse_aois,
        _synchronize,
    )

PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_seasonal_twin_diatom_invasion_test.md"
)
CONSTRUCTIONS = ("chemical-fixed-light", "chemical-astronomical-light")
RECORDED_CYCLES = (7, 8)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _atomic_bundle(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as stream:
        torch.save(payload, stream)
    temporary.replace(path)


def summarize_invasion(record: dict, mask: torch.Tensor) -> dict[str, object]:
    annual_log = record["monthly_discrete_log_multiplier"].sum(dim=0)
    annual_continuous = record["monthly_continuous_exponent"].sum(dim=0)
    values = annual_log[mask].double()
    multiplier = values.exp()
    positive_events = int(record["monthly_positive_rate_events"][:, mask].sum())
    event_denominator = int(record["step_count_per_month"]) * 12 * int(mask.sum())
    maximum = float(values.max())
    minimum = float(values.min())
    if maximum < -0.10:
        classification = "uniformly-non-invadable"
    elif minimum > 0.10:
        classification = "uniformly-invadable"
    else:
        classification = "mixed"
    return {
        "classification": classification,
        "log_multiplier_min": minimum,
        "log_multiplier_median": float(values.median()),
        "log_multiplier_max": maximum,
        "annual_multiplier_min": float(multiplier.min()),
        "annual_multiplier_median": float(multiplier.median()),
        "annual_multiplier_max": float(multiplier.max()),
        "fraction_log_multiplier_negative": float((values < 0).double().mean()),
        "fraction_log_multiplier_positive": float((values > 0).double().mean()),
        "continuous_exponent_min": float(annual_continuous[mask].double().min()),
        "continuous_exponent_median": float(annual_continuous[mask].double().median()),
        "continuous_exponent_max": float(annual_continuous[mask].double().max()),
        "positive_rate_step_fraction": positive_events / max(event_denominator, 1),
        "minimum_euler_factor": float(record["monthly_min_euler_factor"][:, mask].min()),
        "resident_diatom_max_abs": float(record["resident_diatom_max_abs"]),
    }


def resident_stability(cycle7: dict, cycle8: dict, mask: torch.Tensor) -> dict[str, object]:
    previous = cycle7["all_step_mean"]
    current = cycle8["all_step_mean"]
    per_tracer = {}
    for index in range(previous.shape[0]):
        if index == layer2.I_DIATOM:
            continue
        before = previous[index][mask].double()
        after = current[index][mask].double()
        denominator = torch.linalg.vector_norm(before)
        relative = (
            0.0
            if float(denominator) == 0.0 and torch.equal(before, after)
            else float(
                torch.linalg.vector_norm(after - before)
                / denominator.clamp(min=1e-30)
            )
        )
        per_tracer[STATE_NAMES[index]] = relative
    maximum = max(per_tracer.values())
    return {
        "stable": maximum <= 0.01,
        "threshold": 0.01,
        "maximum_per_tracer_relative_l2": maximum,
        "per_tracer_relative_l2": per_tracer,
    }


def classify_decision(report: dict) -> dict[str, object]:
    structural_cells = []
    light_specific = []
    for aoi in DEFAULT_AOIS:
        fixed = report["constructions"]["chemical-fixed-light"]["aois"][aoi]
        light = report["constructions"]["chemical-astronomical-light"]["aois"][aoi]
        fixed_agrees = (
            fixed["cycles"]["7"]["classification"]
            == fixed["cycles"]["8"]["classification"]
        )
        light_agrees = (
            light["cycles"]["7"]["classification"]
            == light["cycles"]["8"]["classification"]
        )
        fixed_non = fixed["cycles"]["8"]["classification"] == "uniformly-non-invadable"
        light_non = light["cycles"]["8"]["classification"] == "uniformly-non-invadable"
        if (
            fixed_non
            and light_non
            and fixed_agrees
            and light_agrees
            and fixed["stability"]["stable"]
            and light["stability"]["stable"]
        ):
            structural_cells.append(aoi)
        if (
            not fixed_non
            and light_non
            and light_agrees
            and fixed["stability"]["stable"]
            and light["stability"]["stable"]
        ):
            light_specific.append(aoi)
    if len(structural_cells) == 3:
        branch = "structural-diatom-free-attractor"
        qualifying = structural_cells
    elif len(light_specific) >= 2:
        branch = "light-driver-specific"
        qualifying = light_specific
    else:
        branch = "spatial-or-mixed-viability"
        qualifying = []
    return {
        "branch": branch,
        "qualifying_aois": qualifying,
        "structural_cells": structural_cells,
        "light_specific_aois": light_specific,
        "b200_authorized": False,
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
    parser.add_argument("--steps-per-month", type=int, default=122)
    parser.add_argument("--cycles", type=int, default=8)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compile", action="store_true", dest="compile_step")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bundle-out", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.steps_per_month != 122 or args.cycles != 8:
        parser.error("production requires 122 steps/month and 8 cycles")
    if tuple(args.aois) != DEFAULT_AOIS:
        parser.error("production requires all three canonical AOIs")
    if not args.bin_average.is_file():
        parser.error(f"bin-average product does not exist: {args.bin_average}")

    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    device = _device(args.device)
    torch.set_grad_enabled(False)
    step_fn = layer2.carroll6_5pft_2layer_step
    if args.compile_step:
        step_fn = torch.compile(step_fn, mode="default", dynamic=True)

    config = {
        "dt_days": DT,
        "steps_per_month": args.steps_per_month,
        "cycles": args.cycles,
        "recorded_cycles": list(RECORDED_CYCLES),
        "aois": list(args.aois),
        "constructions": list(CONSTRUCTIONS),
        "chemical_restoring_tau_days": 365.25,
        "initial_diatom": 0.0,
        "phytoplankton_restoring": False,
        "truth": [float(value) for value in CARROLL_VALUES],
        "compiled_step": args.compile_step,
        "device": str(device),
    }
    bundle = {
        "schema_version": 1,
        "preregistration": PREREGISTRATION,
        "config": config,
        "constructions": {},
    }
    report = {
        "schema_version": 1,
        "status": "measured-not-yet-independently-verified",
        "preregistration": PREREGISTRATION,
        "config": config,
        "constructions": {},
    }

    dataset = open_bin_average(args.bin_average)
    started = time.perf_counter()
    try:
        loaded = {aoi: _load_aoi(dataset, aoi, device) for aoi in args.aois}
        for construction in CONSTRUCTIONS:
            use_light = construction == "chemical-astronomical-light"
            bundle_aois = {}
            report_aois = {}
            for aoi in args.aois:
                aoi_started = time.perf_counter()
                original, forcing, mask, metadata = loaded[aoi]
                state = original.clone()
                state[layer2.I_DIATOM] = 0.0
                reference = original
                selector = torch.zeros_like(state)
                selector[list(CHEMICAL_RESTORING_INDICES)] = mask.to(state.dtype)
                height, width = mask.shape
                truth = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
                truth = truth.expand(6, height, width).contiguous()
                monthly_light = (
                    astronomical_monthly_light(forcing["latitude_degrees"])
                    if use_light
                    else None
                )
                records = {}
                for cycle in range(1, args.cycles + 1):
                    record = cycle in RECORDED_CYCLES
                    if record:
                        monthly_log = []
                        monthly_continuous = []
                        monthly_positive = []
                        monthly_min_factor = []
                        state_sum = torch.zeros_like(state)
                    for month in range(12):
                        if record:
                            log_sum = torch.zeros_like(state[layer2.I_DFE_1])
                            continuous_sum = torch.zeros_like(log_sum)
                            positive_count = torch.zeros_like(log_sum, dtype=torch.int32)
                            minimum_factor = torch.full_like(log_sum, math.inf)
                        for _ in range(args.steps_per_month):
                            light = None if monthly_light is None else monthly_light[month]
                            rates = layer2.phytoplankton_process_rates(
                                state,
                                truth,
                                forcing["T_monthly"][month],
                                layer2.LIGHT if light is None else light,
                            )
                            step_args = (
                                state,
                                truth,
                                DT,
                                forcing["T_monthly"][month],
                                forcing["S_monthly"][month],
                                forcing["wind_monthly"][month],
                                forcing["pco2_atm"],
                                layer2.H1,
                                layer2.H2,
                                layer2.KZ_M2_PER_DAY,
                                layer2.R_REMIN,
                            )
                            model_next = (
                                step_fn(*step_args)
                                if light is None
                                else step_fn(*step_args, light)
                            )
                            requested = DT * (reference - state) / 365.25 * selector
                            next_state = (model_next + requested).clamp(min=0.0)
                            if record:
                                rate = rates["diatom_low_density_rate"]
                                factor = 1.0 + DT * rate
                                log_sum += torch.log(factor)
                                continuous_sum += DT * rate
                                positive_count += (rate > 0).to(torch.int32)
                                minimum_factor = torch.minimum(minimum_factor, factor)
                                state_sum += next_state
                            state = next_state
                        if record:
                            if float(minimum_factor.min()) <= 0.0:
                                raise RuntimeError(
                                    f"{construction}/{aoi}: nonpositive Euler factor"
                                )
                            monthly_log.append(log_sum)
                            monthly_continuous.append(continuous_sum)
                            monthly_positive.append(positive_count)
                            monthly_min_factor.append(minimum_factor)
                    if record:
                        _synchronize(device)
                        records[cycle] = {
                            "monthly_discrete_log_multiplier": torch.stack(monthly_log).cpu(),
                            "monthly_continuous_exponent": torch.stack(monthly_continuous).cpu(),
                            "monthly_positive_rate_events": torch.stack(monthly_positive).cpu(),
                            "monthly_min_euler_factor": torch.stack(monthly_min_factor).cpu(),
                            "all_step_mean": (state_sum / float(12 * args.steps_per_month)).cpu(),
                            "resident_diatom_max_abs": float(state[layer2.I_DIATOM].abs().max()),
                            "step_count_per_month": args.steps_per_month,
                        }
                mask_cpu = mask.cpu()
                stability = resident_stability(records[7], records[8], mask_cpu)
                summaries = {
                    str(cycle): summarize_invasion(record, mask_cpu)
                    for cycle, record in records.items()
                }
                bundle_aois[aoi] = {
                    "metadata": metadata,
                    "mask": mask_cpu,
                    "cycles": records,
                    "monthly_light": monthly_light.cpu() if monthly_light is not None else None,
                }
                report_aois[aoi] = {
                    **metadata,
                    "cycles": summaries,
                    "stability": stability,
                    "elapsed_seconds": time.perf_counter() - aoi_started,
                }
                print(
                    f"{construction} {aoi}: class={summaries['8']['classification']} "
                    f"Lambda=[{summaries['8']['log_multiplier_min']:.3f},"
                    f"{summaries['8']['log_multiplier_max']:.3f}] stable={stability['stable']}"
                )
            bundle["constructions"][construction] = {"aois": bundle_aois}
            report["constructions"][construction] = {"aois": report_aois}
    finally:
        dataset.close()

    report["decision"] = classify_decision(report)
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_bundle(args.bundle_out, bundle)
    report["bundle_artifact"] = {
        "path": args.bundle_out.as_posix(),
        "bytes": args.bundle_out.stat().st_size,
        "sha256": _sha256(args.bundle_out),
    }
    _atomic_json(args.output, report)
    print(f"DIATOM INVASION MEASURED branch={report['decision']['branch']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
