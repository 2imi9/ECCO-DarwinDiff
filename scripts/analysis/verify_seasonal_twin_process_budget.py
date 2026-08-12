#!/usr/bin/env python3
"""Independently verify the preregistered seasonal-twin process budgets."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
N_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
CONSTRUCTIONS = ("chemical-fixed-light", "chemical-astronomical-light")
CYCLES = (1, 2, 7, 8)
PFTS = ("diatom", "lge", "syn", "proLL", "proHL")
TARGET_FIELDS = (
    ("DFe1", 0),
    ("Chl1_diatom", 1),
    ("Chl2_lge", 2),
    ("Chl3_syn", 3),
    ("Chl4_proll", 4),
    ("Chl5_prohl", 5),
    ("POC1", 6),
    ("PIC1", 7),
    ("DIC1", 8),
    ("ALK1", 9),
    ("DFe2", 10),
)
TARGET_REPORTS = {
    "chemical-fixed-light": Path(
        "docs/findings/2026-08-09_seasonal_twin_chemical_restoring_target_gate.json"
    ),
    "chemical-astronomical-light": Path(
        "docs/findings/2026-08-09_seasonal_twin_astronomical_light_target_gate.json"
    ),
}
REQUIRED_BUDGET_KEYS = {
    "growth",
    "linear_mortality",
    "quadratic_mortality",
    "grazing",
    "net",
    "actual_increment",
    "clamp_correction",
    "raw_negative_events",
    "post_step_zero_events",
    "closure_abs",
    "initial_phyto",
    "final_phyto",
    "all_step_mean",
    "f_fe_mean",
    "light_mean",
    "gamma_t_mean",
    "step_count",
}


class VerificationError(ValueError):
    """Raised when an artifact violates its preregistered contract."""


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


def _masked_sum(tensor: torch.Tensor, mask: torch.Tensor) -> float:
    return float(tensor[:, mask].to(torch.float64).sum())


def _component(
    growth: float,
    linear: float,
    quadratic: float,
    grazing: float,
    clamp: float,
    raw_events: int,
    zero_events: int,
    initial: float,
    final: float,
    event_denominator: int,
) -> dict[str, object]:
    loss = linear + quadratic + grazing
    scale = max(growth + loss, 1e-30)
    balance = (growth - loss) / scale
    classification = (
        "loss-dominated"
        if balance <= -0.10
        else "growth-dominated"
        if balance >= 0.10
        else "balanced"
    )
    shares = {
        "linear": linear / max(loss, 1e-30),
        "quadratic": quadratic / max(loss, 1e-30),
        "grazing": grazing / max(loss, 1e-30),
    }
    dominant, share = max(shares.items(), key=lambda item: item[1])
    burden = clamp / scale
    event_fraction = raw_events / max(event_denominator, 1)
    retention = final / max(initial, 1e-30)
    return {
        "growth": growth,
        "linear_mortality": linear,
        "quadratic_mortality": quadratic,
        "grazing": grazing,
        "loss": loss,
        "net": growth - loss,
        "signed_balance": balance,
        "growth_loss_ratio": growth / max(loss, 1e-30),
        "classification": classification,
        "linear_loss_share": shares["linear"],
        "quadratic_loss_share": shares["quadratic"],
        "grazing_loss_share": shares["grazing"],
        "dominant_loss_component": dominant if share > 0.50 else None,
        "clamp_correction": clamp,
        "clamp_burden": burden,
        "raw_negative_events": raw_events,
        "post_step_zero_events": zero_events,
        "clamp_event_fraction": event_fraction,
        "severe_clamp": burden >= 0.01 or event_fraction >= 0.01,
        "initial_inventory": initial,
        "final_inventory": final,
        "inventory_retention": retention,
        "collapsed": retention <= 1e-6,
    }


def recompute_summary(budget: dict, mask: torch.Tensor) -> dict[str, object]:
    steps = int(budget["step_count"])
    n_cells = int(mask.sum())
    per_pft = {}
    for index, name in enumerate(PFTS):
        per_pft[name] = _component(
            float(budget["growth"][index][mask].double().sum()),
            float(budget["linear_mortality"][index][mask].double().sum()),
            float(budget["quadratic_mortality"][index][mask].double().sum()),
            float(budget["grazing"][index][mask].double().sum()),
            float(budget["clamp_correction"][index][mask].double().sum()),
            int(budget["raw_negative_events"][index][mask].sum()),
            int(budget["post_step_zero_events"][index][mask].sum()),
            float(budget["initial_phyto"][index][mask].double().sum()),
            float(budget["final_phyto"][index][mask].double().sum()),
            steps * n_cells,
        )
    total = _component(
        _masked_sum(budget["growth"], mask),
        _masked_sum(budget["linear_mortality"], mask),
        _masked_sum(budget["quadratic_mortality"], mask),
        _masked_sum(budget["grazing"], mask),
        _masked_sum(budget["clamp_correction"], mask),
        int(budget["raw_negative_events"][:, mask].sum()),
        int(budget["post_step_zero_events"][:, mask].sum()),
        _masked_sum(budget["initial_phyto"], mask),
        _masked_sum(budget["final_phyto"], mask),
        steps * n_cells * len(PFTS),
    )
    total.update(
        {
            "closure_abs": _masked_sum(budget["closure_abs"], mask),
            "f_fe_mean": float(budget["f_fe_mean"][mask].double().mean()),
            "light_mean": float(budget["light_mean"][mask].double().mean()),
            "gamma_t_mean": float(budget["gamma_t_mean"][mask].double().mean()),
        }
    )
    return {
        "step_count": steps,
        "n_ocean_cells": n_cells,
        "all_pft": total,
        "per_pft": per_pft,
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


def _normalized_residual(
    residual: torch.Tensor,
    scale: torch.Tensor,
    mask: torch.Tensor,
) -> float:
    selected_residual = residual[:, mask].abs().double()
    selected_scale = scale[:, mask].abs().double().clamp(min=1e-20)
    return float((selected_residual / selected_scale).max())


def _target_stats(state: torch.Tensor, mask: torch.Tensor) -> dict[str, dict[str, float]]:
    result = {}
    for name, index in TARGET_FIELDS:
        values = state[index][mask]
        result[name] = {
            "mean": float(values.mean()),
            "min": float(values.min()),
            "max": float(values.max()),
            "relative_spatial_sd": float(
                values.std() / values.mean().abs().clamp(min=1e-30)
            ),
        }
    return result


def _decision(summaries: dict[str, dict]) -> dict[str, object]:
    numerical = []
    light_driver = []
    intrinsic = []
    fixed = summaries["chemical-fixed-light"]
    light = summaries["chemical-astronomical-light"]
    for aoi in AOIS:
        fixed_total = fixed[aoi]["8"]["all_pft"]
        light_total = light[aoi]["8"]["all_pft"]
        if fixed_total["severe_clamp"] and light_total["severe_clamp"]:
            numerical.append(aoi)
        if (
            fixed_total["classification"] != "loss-dominated"
            and light_total["classification"] == "loss-dominated"
        ):
            light_driver.append(aoi)
        if (
            fixed_total["classification"] == "loss-dominated"
            and light_total["classification"] == "loss-dominated"
            and not fixed_total["severe_clamp"]
            and not light_total["severe_clamp"]
        ):
            intrinsic.append(aoi)
    if len(numerical) >= 2:
        branch, qualifying = "numerical-floor-failure", numerical
    elif len(light_driver) >= 2:
        branch, qualifying = "light-driver-failure", light_driver
    elif len(intrinsic) >= 2:
        branch, qualifying = "intrinsic-sink-imbalance", intrinsic
    else:
        branch, qualifying = "mixed-or-other", []
    return {
        "branch": branch,
        "qualifying_aois": qualifying,
        "numerical_floor_aois": numerical,
        "light_driver_aois": light_driver,
        "intrinsic_sink_aois": intrinsic,
        "b200_authorized": False,
    }


def verify(report: dict, bundle: dict, target_reports: dict[str, dict]) -> dict:
    _require(report["schema_version"] == 1, "report schema differs")
    _require(bundle["schema_version"] == 1, "bundle schema differs")
    _require(report["config"] == bundle["config"], "report/bundle config differs")
    config = bundle["config"]
    _require(config["dt_days"] == 0.25, "dt differs")
    _require(config["steps_per_month"] == 122, "steps/month differs")
    _require(config["cycles"] == 8, "cycle count differs")
    _require(config["budget_cycles"] == list(CYCLES), "budget cycles differ")
    _require(config["aois"] == list(AOIS), "AOI set/order differs")
    _require(config["constructions"] == list(CONSTRUCTIONS), "constructions differ")
    _require(config["chemical_restoring_tau_days"] == 365.25, "tau differs")
    _require(config["phytoplankton_restoring"] is False, "phyto restoring enabled")
    _require(report["decision"]["b200_authorized"] is False, "B200 was authorized")

    max_budget_residual = 0.0
    max_inventory_residual = 0.0
    max_target_difference = 0.0
    raw_tensor_cells = 0
    summaries: dict[str, dict] = {}

    _require(set(bundle["constructions"]) == set(CONSTRUCTIONS), "bundle construction set")
    _require(set(report["constructions"]) == set(CONSTRUCTIONS), "report construction set")
    for construction in CONSTRUCTIONS:
        bundled_aois = bundle["constructions"][construction]["aois"]
        reported_aois = report["constructions"][construction]["aois"]
        _require(set(bundled_aois) == set(AOIS), f"{construction}: bundle AOIs differ")
        _require(set(reported_aois) == set(AOIS), f"{construction}: report AOIs differ")
        summaries[construction] = {}
        target = target_reports[construction]
        for aoi in AOIS:
            item = bundled_aois[aoi]
            mask = item["mask"]
            _require(mask.dtype == torch.bool and mask.ndim == 2, f"{aoi}: bad mask")
            _require(int(mask.sum()) == N_CELLS[aoi], f"{aoi}: ocean-cell count differs")
            _require(torch.isfinite(item["final_state"]).all(), f"{aoi}: final state non-finite")
            _require(set(item["cycles"]) == set(CYCLES), f"{aoi}: budget cycles differ")
            monthly_light = item["monthly_light"]
            if construction == "chemical-fixed-light":
                _require(monthly_light is None, f"{aoi}: fixed-light arm stores monthly light")
                expected_light_mean = torch.ones(mask.shape)
            else:
                _require(
                    isinstance(monthly_light, torch.Tensor)
                    and monthly_light.shape == (12, *mask.shape),
                    f"{aoi}: monthly light shape differs",
                )
                _require(torch.isfinite(monthly_light).all(), f"{aoi}: monthly light non-finite")
                _require(float(monthly_light.min()) >= 0.0, f"{aoi}: monthly light negative")
                expected_light_mean = monthly_light.mean(dim=0)
                _require(
                    float((expected_light_mean[mask] - 1.0).abs().max()) <= 1e-6,
                    f"{aoi}: source monthly light fails mean-one gate",
                )
            summaries[construction][aoi] = {}
            for cycle in CYCLES:
                budget = item["cycles"][cycle]
                label = f"{construction}.{aoi}.cycle{cycle}"
                _require(set(budget) == REQUIRED_BUDGET_KEYS, f"{label}: keys differ")
                phyto_shape = (5, *mask.shape)
                for key in REQUIRED_BUDGET_KEYS - {
                    "all_step_mean",
                    "f_fe_mean",
                    "light_mean",
                    "gamma_t_mean",
                    "step_count",
                }:
                    tensor = budget[key]
                    _require(tensor.shape == phyto_shape, f"{label}.{key}: shape differs")
                    _require(torch.isfinite(tensor).all(), f"{label}.{key}: non-finite")
                for key in ("f_fe_mean", "light_mean", "gamma_t_mean"):
                    tensor = budget[key]
                    _require(tensor.shape == mask.shape, f"{label}.{key}: shape differs")
                    _require(torch.isfinite(tensor).all(), f"{label}.{key}: non-finite")
                _require(
                    budget["all_step_mean"].shape == (15, *mask.shape),
                    f"{label}: all-step mean shape differs",
                )
                _require(
                    torch.isfinite(budget["all_step_mean"]).all(),
                    f"{label}: state non-finite",
                )
                _require(int(budget["step_count"]) == 1464, f"{label}: step count differs")
                for key in (
                    "growth",
                    "linear_mortality",
                    "quadratic_mortality",
                    "grazing",
                    "clamp_correction",
                    "closure_abs",
                    "initial_phyto",
                    "final_phyto",
                ):
                    _require(float(budget[key].min()) >= 0.0, f"{label}.{key}: negative")
                _require(torch.count_nonzero(budget["closure_abs"]) == 0, f"{label}: closure")
                for key in ("raw_negative_events", "post_step_zero_events"):
                    events = budget[key]
                    _require(int(events.min()) >= 0, f"{label}.{key}: negative count")
                    _require(int(events.max()) <= 1464, f"{label}.{key}: count exceeds steps")

                component_net = (
                    budget["growth"]
                    - budget["linear_mortality"]
                    - budget["quadratic_mortality"]
                    - budget["grazing"]
                )
                _require(torch.equal(component_net, budget["net"]), f"{label}: net identity")
                gross_scale = (
                    budget["growth"]
                    + budget["linear_mortality"]
                    + budget["quadratic_mortality"]
                    + budget["grazing"]
                    + budget["initial_phyto"]
                )
                budget_residual = _normalized_residual(
                    budget["actual_increment"]
                    - budget["net"]
                    - budget["clamp_correction"],
                    gross_scale,
                    mask,
                )
                inventory_residual = _normalized_residual(
                    budget["final_phyto"]
                    - budget["initial_phyto"]
                    - budget["actual_increment"],
                    gross_scale,
                    mask,
                )
                _require(budget_residual <= 5e-4, f"{label}: process identity residual")
                _require(inventory_residual <= 5e-4, f"{label}: inventory residual")
                max_budget_residual = max(max_budget_residual, budget_residual)
                max_inventory_residual = max(max_inventory_residual, inventory_residual)

                _require(
                    float(
                        (
                            budget["light_mean"][mask]
                            - expected_light_mean[mask]
                        ).abs().max()
                    )
                    <= 2e-5,
                    f"{label}: repeated-step light mean differs from source tensor",
                )

                summary = recompute_summary(budget, mask)
                summaries[construction][aoi][str(cycle)] = summary
                _compare(
                    summary,
                    reported_aois[aoi]["cycles"][str(cycle)],
                    f"report.{label}",
                )
                target_stats = _target_stats(budget["all_step_mean"], mask)
                expected_stats = target["aois"][aoi]["cycles"][cycle - 1]["all_step_mean"]
                for field, stats in target_stats.items():
                    for metric, value in stats.items():
                        expected = expected_stats[field][metric]
                        difference = abs(value - expected)
                        tolerance = max(5e-6 * abs(expected), 5e-7)
                        _require(
                            difference <= tolerance,
                            f"{label}: target state differs at {field}.{metric}",
                        )
                        max_target_difference = max(max_target_difference, difference)
                raw_tensor_cells += sum(
                    value.numel() for value in budget.values() if isinstance(value, torch.Tensor)
                )

    decision = _decision(summaries)
    _require(decision == report["decision"], "decision tree was not reproduced")
    return {
        "verified": True,
        "schema_version": 1,
        "constructions": len(CONSTRUCTIONS),
        "aois": len(AOIS),
        "cycles_per_cell": len(CYCLES),
        "raw_tensor_cells": raw_tensor_cells,
        "max_process_identity_normalized_residual": max_budget_residual,
        "max_inventory_identity_normalized_residual": max_inventory_residual,
        "max_target_state_absolute_difference": max_target_difference,
        "decision": copy.deepcopy(decision),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    bundle = load_bundle(args.bundle)
    targets = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in TARGET_REPORTS.items()
    }
    try:
        result = verify(report, bundle, targets)
        _require(
            report["bundle_artifact"]["sha256"] == _sha256(args.bundle),
            "bundle SHA-256 differs from report",
        )
    except (KeyError, TypeError, VerificationError) as exc:
        print(f"PROCESS BUDGET VERIFICATION FAILED: {exc}")
        return 2
    result["report"] = args.report.as_posix()
    result["report_sha256"] = _sha256(args.report)
    result["bundle"] = args.bundle.as_posix()
    result["bundle_sha256"] = _sha256(args.bundle)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        f"VERIFIED seasonal process budgets: decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
