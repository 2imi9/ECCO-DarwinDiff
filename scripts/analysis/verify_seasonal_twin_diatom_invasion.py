#!/usr/bin/env python3
"""Verify the rare-diatom seasonal invasion tensors and frozen decision."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
N_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
CONSTRUCTIONS = ("chemical-fixed-light", "chemical-astronomical-light")
CYCLES = (7, 8)
STATE_NAMES = (
    "DFe1",
    "Chl1_diatom",
    "Chl2_lge",
    "Chl3_syn",
    "Chl4_proll",
    "Chl5_prohl",
    "POC1",
    "PIC1",
    "DIC1",
    "ALK1",
    "DFe2",
    "POC2",
    "PIC2",
    "DIC2",
    "ALK2",
)
REQUIRED_RECORD_KEYS = {
    "monthly_discrete_log_multiplier",
    "monthly_continuous_exponent",
    "monthly_positive_rate_events",
    "monthly_min_euler_factor",
    "all_step_mean",
    "resident_diatom_max_abs",
    "step_count_per_month",
}


class VerificationError(ValueError):
    """Raised when the invasion artifact violates its registered relation."""


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


def recompute_summary(record: dict, mask: torch.Tensor) -> dict[str, object]:
    annual_log = record["monthly_discrete_log_multiplier"].sum(dim=0)
    annual_continuous = record["monthly_continuous_exponent"].sum(dim=0)
    values = annual_log[mask].double()
    multiplier = values.exp()
    positive_events = int(record["monthly_positive_rate_events"][:, mask].sum())
    denominator = int(record["step_count_per_month"]) * 12 * int(mask.sum())
    minimum = float(values.min())
    maximum = float(values.max())
    classification = (
        "uniformly-non-invadable"
        if maximum < -0.10
        else "uniformly-invadable"
        if minimum > 0.10
        else "mixed"
    )
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
        "positive_rate_step_fraction": positive_events / max(denominator, 1),
        "minimum_euler_factor": float(record["monthly_min_euler_factor"][:, mask].min()),
        "resident_diatom_max_abs": float(record["resident_diatom_max_abs"]),
    }


def recompute_stability(cycle7: dict, cycle8: dict, mask: torch.Tensor) -> dict[str, object]:
    previous = cycle7["all_step_mean"]
    current = cycle8["all_step_mean"]
    per_tracer = {}
    for index, name in enumerate(STATE_NAMES):
        if index == 1:
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
        per_tracer[name] = relative
    maximum = max(per_tracer.values())
    return {
        "stable": maximum <= 0.01,
        "threshold": 0.01,
        "maximum_per_tracer_relative_l2": maximum,
        "per_tracer_relative_l2": per_tracer,
    }


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key in expected:
            _compare(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, float):
        _require(isinstance(actual, float | int), f"{path}: expected number")
        tolerance = 2e-12 * max(abs(expected), 1.0)
        _require(abs(expected - float(actual)) <= tolerance, f"{path}: value differs")
    else:
        _require(expected == actual, f"{path}: value differs")


def recompute_decision(summaries: dict[str, dict]) -> dict[str, object]:
    structural = []
    light_specific = []
    for aoi in AOIS:
        fixed = summaries["chemical-fixed-light"][aoi]
        light = summaries["chemical-astronomical-light"][aoi]
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
            structural.append(aoi)
        if (
            not fixed_non
            and light_non
            and light_agrees
            and fixed["stability"]["stable"]
            and light["stability"]["stable"]
        ):
            light_specific.append(aoi)
    if len(structural) == 3:
        branch, qualifying = "structural-diatom-free-attractor", structural
    elif len(light_specific) >= 2:
        branch, qualifying = "light-driver-specific", light_specific
    else:
        branch, qualifying = "spatial-or-mixed-viability", []
    return {
        "branch": branch,
        "qualifying_aois": qualifying,
        "structural_cells": structural,
        "light_specific_aois": light_specific,
        "b200_authorized": False,
    }


def verify(report: dict, bundle: dict) -> dict:
    _require(report["schema_version"] == 1, "report schema differs")
    _require(bundle["schema_version"] == 1, "bundle schema differs")
    _require(report["config"] == bundle["config"], "report/bundle config differs")
    config = bundle["config"]
    _require(config["dt_days"] == 0.25, "dt differs")
    _require(config["steps_per_month"] == 122, "steps/month differs")
    _require(config["cycles"] == 8, "cycles differ")
    _require(config["recorded_cycles"] == list(CYCLES), "recorded cycles differ")
    _require(config["aois"] == list(AOIS), "AOIs differ")
    _require(config["constructions"] == list(CONSTRUCTIONS), "constructions differ")
    _require(config["chemical_restoring_tau_days"] == 365.25, "tau differs")
    _require(config["initial_diatom"] == 0.0, "resident diatom was not zero")
    _require(config["phytoplankton_restoring"] is False, "phyto restoring enabled")
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")

    summaries = {}
    raw_tensor_cells = 0
    maximum_log_vs_continuous_violation = 0.0
    _require(set(bundle["constructions"]) == set(CONSTRUCTIONS), "bundle constructions")
    _require(set(report["constructions"]) == set(CONSTRUCTIONS), "report constructions")
    for construction in CONSTRUCTIONS:
        bundle_aois = bundle["constructions"][construction]["aois"]
        report_aois = report["constructions"][construction]["aois"]
        _require(set(bundle_aois) == set(AOIS), f"{construction}: bundle AOIs")
        _require(set(report_aois) == set(AOIS), f"{construction}: report AOIs")
        summaries[construction] = {}
        for aoi in AOIS:
            item = bundle_aois[aoi]
            mask = item["mask"]
            _require(mask.dtype == torch.bool and mask.ndim == 2, f"{aoi}: mask")
            _require(int(mask.sum()) == N_CELLS[aoi], f"{aoi}: ocean cells")
            monthly_light = item["monthly_light"]
            if construction == "chemical-fixed-light":
                _require(monthly_light is None, f"{aoi}: fixed arm has monthly light")
            else:
                _require(
                    isinstance(monthly_light, torch.Tensor)
                    and monthly_light.shape == (12, *mask.shape),
                    f"{aoi}: light shape",
                )
                _require(torch.isfinite(monthly_light).all(), f"{aoi}: light non-finite")
                _require(float(monthly_light.min()) >= 0.0, f"{aoi}: light negative")
                _require(
                    float((monthly_light.mean(dim=0)[mask] - 1.0).abs().max()) <= 1e-6,
                    f"{aoi}: light mean-one gate",
                )
            _require(set(item["cycles"]) == set(CYCLES), f"{aoi}: cycle set")
            cycle_summaries = {}
            for cycle in CYCLES:
                record = item["cycles"][cycle]
                label = f"{construction}.{aoi}.cycle{cycle}"
                _require(set(record) == REQUIRED_RECORD_KEYS, f"{label}: keys")
                for key in (
                    "monthly_discrete_log_multiplier",
                    "monthly_continuous_exponent",
                    "monthly_positive_rate_events",
                    "monthly_min_euler_factor",
                ):
                    tensor = record[key]
                    _require(tensor.shape == (12, *mask.shape), f"{label}.{key}: shape")
                    _require(torch.isfinite(tensor).all(), f"{label}.{key}: non-finite")
                    raw_tensor_cells += tensor.numel()
                _require(
                    record["all_step_mean"].shape == (15, *mask.shape),
                    f"{label}: state shape",
                )
                _require(torch.isfinite(record["all_step_mean"]).all(), f"{label}: state")
                _require(int(record["step_count_per_month"]) == 122, f"{label}: steps")
                _require(float(record["resident_diatom_max_abs"]) == 0.0, f"{label}: diatom")
                _require(
                    torch.count_nonzero(record["all_step_mean"][1]) == 0,
                    f"{label}: nonzero resident diatom mean",
                )
                events = record["monthly_positive_rate_events"]
                _require(int(events.min()) >= 0 and int(events.max()) <= 122, f"{label}: events")
                factors = record["monthly_min_euler_factor"]
                _require(float(factors.min()) > 0.0, f"{label}: Euler factor")
                inequality = (
                    record["monthly_discrete_log_multiplier"]
                    - record["monthly_continuous_exponent"]
                )
                violation = max(float(inequality[:, mask].max()), 0.0)
                _require(violation <= 2e-5, f"{label}: log1p inequality")
                maximum_log_vs_continuous_violation = max(
                    maximum_log_vs_continuous_violation, violation
                )
                summary = recompute_summary(record, mask)
                cycle_summaries[str(cycle)] = summary
                _compare(summary, report_aois[aoi]["cycles"][str(cycle)], f"report.{label}")
            stability = recompute_stability(item["cycles"][7], item["cycles"][8], mask)
            _compare(
                stability,
                report_aois[aoi]["stability"],
                f"report.{construction}.{aoi}.stability",
            )
            summaries[construction][aoi] = {
                "cycles": cycle_summaries,
                "stability": stability,
            }

    decision = recompute_decision(summaries)
    _require(decision == report["decision"], "decision tree differs")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "maximum_log1p_inequality_violation": maximum_log_vs_continuous_violation,
        "decision": decision,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    try:
        result = verify(report, bundle)
        _require(
            report["bundle_artifact"]["sha256"] == _sha256(args.bundle),
            "bundle SHA-256 differs",
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"DIATOM INVASION VERIFICATION FAILED: {exc}")
        return 2
    result["report"] = args.report.as_posix()
    result["report_sha256"] = _sha256(args.report)
    result["bundle"] = args.bundle.as_posix()
    result["bundle_sha256"] = _sha256(args.bundle)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"VERIFIED diatom invasion: decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
