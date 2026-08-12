#!/usr/bin/env python3
"""Independently verify the explicit-zooplankton seasonal target gate."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

import torch

AOIS = ("eqpac", "natlsubpolar", "southernoceanpac")
N_CELLS = {"eqpac": 1071, "natlsubpolar": 489, "southernoceanpac": 1296}
N_STATES = 17
N_STEPS = 12 * 122
CENTRAL_SCENARIO = "ic_0p10"
SCENARIOS = {
    "ic_0p01": {"zoo_initial_fraction": 0.01, "diatomgraz_factor": 1.0},
    CENTRAL_SCENARIO: {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 1.0},
    "ic_0p50": {"zoo_initial_fraction": 0.50, "diatomgraz_factor": 1.0},
    "dg_0p90": {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 0.90},
    "dg_1p10": {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 1.10},
}
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
    "Z_small",
    "Z_large",
)
PLANKTON_NAMES = ("diatom", "lge", "syn", "proLL", "proHL", "z_small", "z_large")
PLANKTON_INDICES = (1, 2, 3, 4, 5, 15, 16)
CHEMICAL_INDICES = (0, 6, 7, 8, 9, 10, 11, 12, 13, 14)
STABILITY_FIELDS = (
    ("DFe1", 0),
    ("DFe2", 10),
    ("Chl1_diatom", 1),
    ("Chl2_lge", 2),
    ("Chl3_syn", 3),
    ("Chl4_proll", 4),
    ("Chl5_prohl", 5),
    ("POC1", 6),
    ("PIC1", 7),
    ("DIC1", 8),
    ("ALK1", 9),
    ("Z_small", 15),
    ("Z_large", 16),
)
DFE2_MIN_REL_SD = {"eqpac": 0.0423, "natlsubpolar": 0.0662, "southernoceanpac": 0.1195}
ASSIMILATION = torch.tensor(
    ((0.2, 0.5), (0.2, 0.5), (0.5, 0.7), (0.5, 0.7), (0.5, 0.7)),
    dtype=torch.float64,
)
GRAZE_MAX = 0.625
HALF_SATURATION = 10.2
CLOSURE_ATOL = 1.0e-6
SOURCE_PHYGRAZ_MIN_C = 1.2e-8
LEGACY_PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_seasonal_twin_explicit_zooplankton_gate.md"
)
CORRECTION_PREREGISTRATION = (
    "docs/findings/2026-08-10_prereg_source_floor_corrected_explicit_zooplankton_chain.md"
)


class VerificationError(ValueError):
    """Raised when the bundle violates a frozen relation."""


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


def _masked_relative_l2(
    current: torch.Tensor,
    previous: torch.Tensor,
    mask: torch.Tensor,
) -> float:
    before = previous[mask].double()
    after = current[mask].double()
    denominator = torch.linalg.vector_norm(before)
    if float(denominator) == 0.0 and torch.equal(before, after):
        return 0.0
    return float(
        torch.linalg.vector_norm(after - before) / denominator.clamp(min=1e-30)
    )


def _relative_spatial_sd(field: torch.Tensor, mask: torch.Tensor) -> float:
    values = field[mask].double()
    return float(values.std() / values.mean().abs().clamp(min=1e-30))


def recompute_light_gate(light: torch.Tensor, mask: torch.Tensor) -> dict:
    values = light[:, mask]
    finite = bool(torch.isfinite(values).all())
    nonnegative = finite and bool((values >= 0.0).all())
    max_error = float((values.mean(dim=0) - 1.0).abs().max())
    mean_one = finite and math.isfinite(max_error) and max_error <= 1e-6
    failures = []
    if not finite:
        failures.append("non_finite")
    if not nonnegative:
        failures.append("negative")
    if not mean_one:
        failures.append("per_cell_mean")
    return {
        "pass": not failures,
        "failure_reasons": failures,
        "finite": finite,
        "nonnegative": nonnegative,
        "per_cell_mean_one": mean_one,
        "per_cell_mean_tolerance": 1e-6,
        "max_abs_per_cell_mean_error": max_error,
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


def recompute_stability(previous: torch.Tensor, current: torch.Tensor, mask: torch.Tensor) -> dict:
    changes = {
        name: _masked_relative_l2(current[index], previous[index], mask)
        for name, index in STABILITY_FIELDS
    }
    maximum = max(changes.values())
    return {
        "pass": maximum <= 0.01,
        "threshold": 0.01,
        "maximum_relative_l2": maximum,
        "per_field_relative_l2": changes,
    }


def recompute_closure(budget: dict, mask: torch.Tensor) -> dict:
    chemical = set(CHEMICAL_INDICES)
    per_state = {}
    failures = []
    for index, name in enumerate(STATE_NAMES):
        closure = float(budget["closure_abs"][index][mask].double().sum())
        model = float(budget["model_abs"][index][mask].double().sum())
        inventory = float(budget["inventory_abs"][index][mask].double().sum())
        share = closure / max(closure + model, 1e-30)
        turnover = closure / max(inventory, 1e-30)
        restored = index in chemical
        passes = (
            share <= 0.50 + CLOSURE_ATOL and turnover <= 1.0 + CLOSURE_ATOL
            if restored
            else closure == 0.0
        )
        if not passes:
            failures.append(name)
        per_state[name] = {
            "restored": restored,
            "closure_abs": closure,
            "model_abs": model,
            "inventory_abs": inventory,
            "closure_share": share,
            "closure_turnover": turnover,
            "pass": passes,
        }
    return {
        "pass": not failures,
        "failure_states": failures,
        "share_threshold": 0.50,
        "turnover_threshold": 1.0,
        "comparison_atol": CLOSURE_ATOL,
        "per_state": per_state,
    }


def recompute_numerical(budget: dict, mask: torch.Tensor) -> dict:
    correction = float(budget["plankton_clamp_correction"][:, mask].double().sum())
    gross = float(budget["plankton_gross_biology"][:, mask].double().sum())
    events = int(budget["plankton_raw_negative_events"][:, mask].sum())
    denominator = int(budget["step_count"]) * int(mask.sum()) * len(PLANKTON_NAMES)
    burden = correction / max(gross, 1e-30)
    fraction = events / max(denominator, 1)
    finite = all(
        bool(torch.isfinite(budget[key]).all())
        for key in (
            "closure_abs",
            "model_abs",
            "inventory_abs",
            "plankton_clamp_correction",
            "plankton_gross_biology",
        )
    )
    return {
        "pass": finite and burden < 0.01 and fraction < 0.001,
        "finite": finite,
        "clamp_correction": correction,
        "gross_biology": gross,
        "clamp_burden": burden,
        "clamp_burden_threshold": 0.01,
        "raw_negative_events": events,
        "state_update_count": denominator,
        "raw_negative_event_fraction": fraction,
        "raw_negative_event_fraction_threshold": 0.001,
    }


def recompute_dfe(
    previous: torch.Tensor,
    current: torch.Tensor,
    mask: torch.Tensor,
    aoi: str,
) -> dict:
    old = _relative_spatial_sd(previous[10], mask)
    new = _relative_spatial_sd(current[10], mask)
    change = abs(new - old) / max(abs(old), 1e-30)
    minimum = DFE2_MIN_REL_SD[aoi]
    return {
        "pass": new >= minimum and change <= 0.05,
        "previous_relative_spatial_sd": old,
        "relative_spatial_sd": new,
        "relative_spatial_sd_minimum": minimum,
        "relative_spatial_sd_change": change,
        "relative_spatial_sd_change_threshold": 0.05,
    }


def recompute_viability(
    initial: torch.Tensor,
    current: torch.Tensor,
    month_ends: torch.Tensor,
    mask: torch.Tensor,
) -> dict:
    per_plankton = {}
    inventories = []
    failures = []
    for name, index in zip(PLANKTON_NAMES, PLANKTON_INDICES, strict=True):
        initial_inventory = float(initial[index][mask].double().sum())
        inventory = float(current[index][mask].double().sum())
        retention = inventory / max(initial_inventory, 1e-30)
        passes = retention >= 0.01
        if not passes:
            failures.append(f"{name}:retention")
        per_plankton[name] = {
            "initial_inventory": initial_inventory,
            "cycle12_inventory": inventory,
            "retention": retention,
            "retention_threshold": 0.01,
            "pass": passes,
        }
        inventories.append(inventory)
    total = sum(inventories)
    dominance = {
        name: inventory / max(total, 1e-30)
        for name, inventory in zip(PLANKTON_NAMES, inventories, strict=True)
    }
    dominant_name = max(dominance, key=dominance.get)
    dominance_pass = dominance[dominant_name] <= 0.95
    if not dominance_pass:
        failures.append(f"{dominant_name}:dominance")
    monthly = month_ends[:, 1][:, mask].double().mean(dim=1)
    minimum_monthly = float(monthly.min())
    positive = minimum_monthly > 0.0
    if not positive:
        failures.append("diatom:monthly_positive")
    cv = float(monthly.std(unbiased=False) / monthly.mean().abs().clamp(min=1e-30))
    seasonal = cv >= 0.05
    if not seasonal:
        failures.append("diatom:seasonality")
    return {
        "pass": not failures,
        "failure_reasons": failures,
        "per_plankton": per_plankton,
        "dominance": dominance,
        "maximum_dominance": dominance[dominant_name],
        "dominant_plankton": dominant_name,
        "dominance_threshold": 0.95,
        "dominance_pass": dominance_pass,
        "minimum_monthly_diatom_aoi_mean": minimum_monthly,
        "monthly_diatom_positive": positive,
        "monthly_diatom_cv": cv,
        "monthly_diatom_cv_threshold": 0.05,
        "seasonality_pass": seasonal,
    }


def recompute_initial_condition_gate(scenarios: dict, mask: torch.Tensor) -> dict:
    central = scenarios[CENTRAL_SCENARIO]["cycle12_all_step_mean"]
    per_flank = {}
    failures = []
    for flank in ("ic_0p01", "ic_0p50"):
        current = scenarios[flank]["cycle12_all_step_mean"]
        changes = {
            name: _masked_relative_l2(current[index], central[index], mask)
            for name, index in zip(PLANKTON_NAMES, PLANKTON_INDICES, strict=True)
        }
        maximum = max(changes.values())
        passes = maximum <= 0.05
        if not passes:
            failures.append(flank)
        per_flank[flank] = {
            "pass": passes,
            "maximum_relative_l2": maximum,
            "per_plankton_relative_l2": changes,
        }
    return {
        "pass": not failures,
        "failure_flanks": failures,
        "threshold": 0.05,
        "per_flank": per_flank,
    }


def recompute_sensitivity(aois: dict) -> dict:
    per_aoi = {}
    signs = []
    qualifying = []
    threshold = math.log(1.05)
    for aoi in AOIS:
        item = aois[aoi]
        mask = item["mask"]
        low = item["scenarios"]["dg_0p90"]["cycle12_all_step_mean"][1][mask].double().sum()
        high = item["scenarios"]["dg_1p10"]["cycle12_all_step_mean"][1][mask].double().sum()
        finite_positive = bool(
            torch.isfinite(low) and torch.isfinite(high) and low > 0.0 and high > 0.0
        )
        response = float(torch.log(high / low)) if finite_positive else float("nan")
        sign = 1 if response > 0 else -1 if response < 0 else 0
        magnitude_pass = finite_positive and abs(response) >= threshold
        if magnitude_pass:
            qualifying.append(aoi)
        if finite_positive:
            signs.append(sign)
        per_aoi[aoi] = {
            "finite_positive": finite_positive,
            "low_inventory": float(low),
            "high_inventory": float(high),
            "log_high_over_low": response,
            "absolute_log_response": abs(response),
            "threshold": threshold,
            "magnitude_pass": magnitude_pass,
            "sign": sign,
        }
    agreement = len(signs) == len(AOIS) and len(set(signs)) == 1 and signs[0] != 0
    return {
        "pass": len(qualifying) >= 2 and agreement,
        "qualifying_aois": qualifying,
        "minimum_qualifying_aois": 2,
        "sign_agreement": agreement,
        "per_aoi": per_aoi,
    }


def verify_source_partition(
    initial: torch.Tensor,
    truth: torch.Tensor,
    scenario: dict,
) -> float:
    phyto = initial[1:6].double()
    zoo = initial[15:17].double()
    g = truth[4].double() * scenario["diatomgraz_factor"]
    palatability = torch.stack(
        (
            torch.stack((0.2 * g, g)),
            torch.stack((0.18 * torch.ones_like(g), 0.9 * torch.ones_like(g))),
            torch.stack((torch.ones_like(g), 0.2 * torch.ones_like(g))),
            torch.stack((torch.ones_like(g), 0.2 * torch.ones_like(g))),
            torch.stack((torch.ones_like(g), 0.2 * torch.ones_like(g))),
        )
    )
    weighted = palatability * phyto.unsqueeze(1)
    pool = weighted.sum(dim=0)
    ingestion = GRAZE_MAX * zoo * pool / (pool + HALF_SATURATION)
    grazing = ingestion.unsqueeze(0) * weighted / pool.clamp(min=1e-20).unsqueeze(0)
    assimilation = ASSIMILATION.reshape(5, 2, *([1] * (initial.ndim - 1)))
    gain = (grazing * assimilation).sum(dim=0)
    unassimilated = (grazing * (1.0 - assimilation)).sum(dim=(0, 1))
    residual_ingestion = (grazing.sum(dim=0) - ingestion).abs().max()
    residual_partition = (
        grazing.sum(dim=(0, 1)) - gain.sum(dim=0) - unassimilated
    ).abs().max()
    return max(float(residual_ingestion), float(residual_partition))


def _compare(expected: object, actual: object, path: str) -> None:
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected mapping")
        _require(set(expected) == set(actual), f"{path}: keys differ")
        for key in expected:
            _compare(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, float):
        _require(isinstance(actual, int | float), f"{path}: expected number")
        tolerance = 2e-10 * max(abs(expected), 1.0)
        if ".light." in path:
            tolerance = max(tolerance, 5e-7)
        _require(abs(expected - float(actual)) <= tolerance, f"{path}: value differs")
    else:
        _require(expected == actual, f"{path}: value differs")


def verify(report: dict, bundle: dict) -> dict:
    _require(report["schema_version"] == 1, "report schema differs")
    _require(bundle["schema_version"] == 1, "bundle schema differs")
    _require(report["config"] == bundle["config"], "report/bundle config differs")
    config = bundle["config"]
    _require(
        report["preregistration"] == bundle["preregistration"],
        "report/bundle prereg differs",
    )
    source_prey_floor_c = float(config.get("source_prey_floor_c", 0.0))
    expected_preregistration = (
        CORRECTION_PREREGISTRATION
        if source_prey_floor_c == SOURCE_PHYGRAZ_MIN_C
        else LEGACY_PREREGISTRATION
    )
    _require(
        source_prey_floor_c in (0.0, SOURCE_PHYGRAZ_MIN_C),
        "unregistered source prey floor",
    )
    _require(
        bundle["preregistration"] == expected_preregistration,
        "preregistration does not match source prey floor",
    )
    _require(config["dt_days"] == 0.25, "dt differs")
    _require(config["steps_per_month"] == 122, "steps/month differs")
    _require(config["cycles"] == 12, "cycle count differs")
    _require(config["recorded_cycles"] == [11, 12], "recorded cycles differ")
    _require(config["aois"] == list(AOIS), "AOIs differ")
    _require(config["scenarios"] == SCENARIOS, "scenarios differ")
    _require(config["restoring_indices"] == list(CHEMICAL_INDICES), "restoring differs")
    _require(config["phytoplankton_restoring"] is False, "phyto restoring enabled")
    _require(config["zooplankton_restoring"] is False, "zoo restoring enabled")
    _require(config["source_constants"]["graze_max_per_day"] == GRAZE_MAX, "Gmax")
    _require(config["source_constants"]["half_saturation_c"] == HALF_SATURATION, "K")
    if source_prey_floor_c > 0.0:
        _require(
            config["source_constants"].get("phygrazmin_c")
            == SOURCE_PHYGRAZ_MIN_C,
            "source phygrazmin differs",
        )
    _require(report["decision"]["b200_authorized"] is False, "B200 authorized")
    _require(set(bundle["aois"]) == set(AOIS), "bundle AOIs differ")
    _require(set(report["aois"]) == set(AOIS), "report AOIs differ")

    truth = torch.tensor(config["truth"], dtype=torch.float64).reshape(6, 1, 1)
    max_partition_residual = 0.0
    raw_tensor_cells = 0
    per_aoi_passes = {}
    for aoi in AOIS:
        item = bundle["aois"][aoi]
        mask = item["mask"]
        _require(mask.dtype == torch.bool and mask.ndim == 2, f"{aoi}: mask")
        _require(int(mask.sum()) == N_CELLS[aoi], f"{aoi}: ocean cells")
        light = item["monthly_light"]
        _require(light.shape == (12, *mask.shape), f"{aoi}: light shape")
        light_gate = recompute_light_gate(light, mask)
        _require(set(item["scenarios"]) == set(SCENARIOS), f"{aoi}: scenarios")

        for name, scenario in item["scenarios"].items():
            _require(scenario["spec"] == SCENARIOS[name], f"{aoi}.{name}: spec")
            initial = scenario["initial_state"]
            _require(initial.shape == (N_STATES, *mask.shape), f"{aoi}.{name}: initial")
            total_phyto = initial[1:6].sum(dim=0)
            expected_zoo = SCENARIOS[name]["zoo_initial_fraction"] * total_phyto
            zoo_init_error = max(
                float((initial[15] - expected_zoo).abs().max()),
                float((initial[16] - expected_zoo).abs().max()),
            )
            _require(zoo_init_error <= 1e-7, f"{aoi}.{name}: zoo initialization")
            for key in (
                "cycle11_all_step_mean",
                "cycle12_all_step_mean",
                "cycle12_endpoint",
            ):
                tensor = scenario[key]
                _require(tensor.shape == (N_STATES, *mask.shape), f"{aoi}.{name}.{key}")
                _require(torch.isfinite(tensor).all(), f"{aoi}.{name}.{key}: non-finite")
                raw_tensor_cells += tensor.numel()
            month_ends = scenario["cycle12_month_ends"]
            _require(
                month_ends.shape == (12, N_STATES, *mask.shape),
                f"{aoi}.{name}: month ends",
            )
            _require(torch.isfinite(month_ends).all(), f"{aoi}.{name}: month non-finite")
            _require(
                torch.equal(month_ends[-1], scenario["cycle12_endpoint"]),
                f"{aoi}.{name}: endpoint mismatch",
            )
            raw_tensor_cells += month_ends.numel()
            budget = scenario["cycle12_budget"]
            _require(int(budget["step_count"]) == N_STEPS, f"{aoi}.{name}: step count")
            for key in ("closure_abs", "model_abs", "inventory_abs"):
                _require(budget[key].shape == initial.shape, f"{aoi}.{name}.{key}")
                raw_tensor_cells += budget[key].numel()
            for key in (
                "plankton_clamp_correction",
                "plankton_gross_biology",
                "plankton_raw_negative_events",
            ):
                _require(budget[key].shape == (7, *mask.shape), f"{aoi}.{name}.{key}")
                raw_tensor_cells += budget[key].numel()
            _require(
                torch.count_nonzero(budget["closure_abs"][list(PLANKTON_INDICES)]) == 0,
                f"{aoi}.{name}: plankton restoring",
            )
            residual = verify_source_partition(initial, truth, SCENARIOS[name])
            max_partition_residual = max(max_partition_residual, residual)
            _require(residual <= 2e-15, f"{aoi}.{name}: carbon partition")

        central = item["scenarios"][CENTRAL_SCENARIO]
        gates = {
            "light": light_gate,
            "numerical": recompute_numerical(central["cycle12_budget"], mask),
            "stability": recompute_stability(
                central["cycle11_all_step_mean"], central["cycle12_all_step_mean"], mask
            ),
            "closure": recompute_closure(central["cycle12_budget"], mask),
            "dfe": recompute_dfe(
                central["cycle11_all_step_mean"],
                central["cycle12_all_step_mean"],
                mask,
                aoi,
            ),
            "viability": recompute_viability(
                central["initial_state"],
                central["cycle12_all_step_mean"],
                central["cycle12_month_ends"],
                mask,
            ),
            "initial_condition_robustness": recompute_initial_condition_gate(
                item["scenarios"], mask
            ),
        }
        _compare(gates, report["aois"][aoi]["gates"], f"report.{aoi}.gates")
        passes = all(gate["pass"] for gate in gates.values())
        _require(
            passes == report["aois"][aoi]["pass_before_sensitivity"],
            f"{aoi}: pass differs",
        )
        per_aoi_passes[aoi] = passes

    sensitivity = recompute_sensitivity(bundle["aois"])
    _compare(sensitivity, report["sensitivity_gate"], "report.sensitivity")
    gate_pass = all(per_aoi_passes.values()) and sensitivity["pass"]
    failures = [aoi for aoi, passes in per_aoi_passes.items() if not passes]
    if not sensitivity["pass"]:
        failures.append("diatomgraz_sensitivity")
    decision = {
        "branch": "stage0-pass-cost-gate-authorized" if gate_pass else "stage0-failed-stop",
        "gate_pass": gate_pass,
        "failure_reasons": failures,
        "per_aoi_pass_before_sensitivity": per_aoi_passes,
        "b200_authorized": gate_pass,
        "next_action": "one-seed-one-epoch-b200-cost-gate" if gate_pass else "no-optimizer-no-b200",
    }
    _require(decision == report["decision"], "report decision differs")
    _require(decision == bundle["decision"], "bundle decision differs")
    return {
        "verified": True,
        "schema_version": 1,
        "raw_tensor_cells": raw_tensor_cells,
        "maximum_source_partition_residual": max_partition_residual,
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
        print(f"EXPLICIT ZOO VERIFICATION FAILED: {exc}")
        return 2
    result["report"] = args.report.as_posix()
    result["report_sha256"] = _sha256(args.report)
    result["bundle"] = args.bundle.as_posix()
    result["bundle_sha256"] = _sha256(args.bundle)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        "VERIFIED explicit zooplankton gate: "
        f"decision={result['decision']['branch']} "
        f"raw_tensor_cells={result['raw_tensor_cells']} "
        f"partition_residual={result['maximum_source_partition_residual']:.3e}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
