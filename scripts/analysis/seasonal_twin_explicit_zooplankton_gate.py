#!/usr/bin/env python3
"""Run the preregistered source-mirrored explicit-zooplankton target gate."""

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
    GRAZE_HALF_SATURATION_C,
    GRAZE_MAX_PER_DAY,
    N_TRACERS_EXPLICIT_ZOO,
    PLANKTON_NAMES,
    PLANKTON_STATE_INDICES,
    SOURCE_PHYGRAZ_MIN_C,
    STATE_NAMES,
    ZOO_MORTALITY_PER_DAY,
    explicit_zooplankton_step,
    initialize_zooplankton,
    integrate_explicit_zooplankton_restored_cycle,
)
from darwindiff.seasonal_twin import (
    DFE2_MIN_REL_SD,
    astronomical_monthly_light,
    evaluate_light_integrity,
)

PREREGISTRATION = (
    "docs/findings/2026-08-09_prereg_seasonal_twin_explicit_zooplankton_gate.md"
)
DEFAULT_REPORT = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json"
)
DEFAULT_BUNDLE = Path(
    "docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz"
)
N_CYCLES = 12
RECORDED_CYCLES = (11, 12)
STEPS_PER_MONTH = 122
RESTORING_TAU_DAYS = 365.25
CLOSURE_COMPARISON_ATOL = 1.0e-6
IC_FRACTIONS = (0.01, 0.10, 0.50)
DIATOMGRAZ_FACTORS = (0.90, 1.10)
CENTRAL_SCENARIO = "ic_0p10"
SCENARIOS = {
    "ic_0p01": {"zoo_initial_fraction": 0.01, "diatomgraz_factor": 1.0},
    CENTRAL_SCENARIO: {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 1.0},
    "ic_0p50": {"zoo_initial_fraction": 0.50, "diatomgraz_factor": 1.0},
    "dg_0p90": {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 0.90},
    "dg_1p10": {"zoo_initial_fraction": 0.10, "diatomgraz_factor": 1.10},
}
STABILITY_FIELDS = (
    ("DFe1", layer2.I_DFE_1),
    ("DFe2", layer2.I_DFE_2),
    ("Chl1_diatom", layer2.I_DIATOM),
    ("Chl2_lge", layer2.I_LGE),
    ("Chl3_syn", layer2.I_SYN),
    ("Chl4_proll", layer2.I_PROLL),
    ("Chl5_prohl", layer2.I_PROHL),
    ("POC1", layer2.I_POC_1),
    ("PIC1", layer2.I_PIC_1),
    ("DIC1", layer2.I_DIC_1),
    ("ALK1", layer2.I_ALK_1),
    ("Z_small", 15),
    ("Z_large", 16),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, payload: dict) -> None:
    def clean(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(clean(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_gzip_torch_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as stream:
        torch.save(payload, stream)
    temporary.replace(path)


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


def _cycle_stability(
    previous: torch.Tensor,
    current: torch.Tensor,
    mask: torch.Tensor,
) -> dict:
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


def _closure_gate(budget: dict, mask: torch.Tensor) -> dict:
    chemical = set(CHEMICAL_RESTORING_INDICES)
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
            share <= 0.50 + CLOSURE_COMPARISON_ATOL
            and turnover <= 1.0 + CLOSURE_COMPARISON_ATOL
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
        "comparison_atol": CLOSURE_COMPARISON_ATOL,
        "per_state": per_state,
    }


def _numerical_gate(budget: dict, mask: torch.Tensor) -> dict:
    correction = float(
        budget["plankton_clamp_correction"][:, mask].double().sum()
    )
    gross = float(budget["plankton_gross_biology"][:, mask].double().sum())
    events = int(budget["plankton_raw_negative_events"][:, mask].sum())
    denominator = int(budget["step_count"]) * int(mask.sum()) * len(PLANKTON_NAMES)
    burden = correction / max(gross, 1e-30)
    event_fraction = events / max(denominator, 1)
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
        "pass": finite and burden < 0.01 and event_fraction < 0.001,
        "finite": finite,
        "clamp_correction": correction,
        "gross_biology": gross,
        "clamp_burden": burden,
        "clamp_burden_threshold": 0.01,
        "raw_negative_events": events,
        "state_update_count": denominator,
        "raw_negative_event_fraction": event_fraction,
        "raw_negative_event_fraction_threshold": 0.001,
    }


def _dfe_gate(
    previous: torch.Tensor,
    current: torch.Tensor,
    mask: torch.Tensor,
    aoi: str,
) -> dict:
    old = _relative_spatial_sd(previous[layer2.I_DFE_2], mask)
    new = _relative_spatial_sd(current[layer2.I_DFE_2], mask)
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


def _viability_gate(
    initial: torch.Tensor,
    current: torch.Tensor,
    month_ends: torch.Tensor,
    mask: torch.Tensor,
) -> dict:
    per_plankton = {}
    inventories = []
    failures = []
    for name, index in zip(PLANKTON_NAMES, PLANKTON_STATE_INDICES, strict=True):
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

    monthly_diatom_means = month_ends[:, layer2.I_DIATOM][:, mask].double().mean(dim=1)
    minimum_monthly_mean = float(monthly_diatom_means.min())
    positive_monthly = minimum_monthly_mean > 0.0
    if not positive_monthly:
        failures.append("diatom:monthly_positive")
    monthly_cv = float(
        monthly_diatom_means.std(unbiased=False)
        / monthly_diatom_means.mean().abs().clamp(min=1e-30)
    )
    seasonality_pass = monthly_cv >= 0.05
    if not seasonality_pass:
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
        "minimum_monthly_diatom_aoi_mean": minimum_monthly_mean,
        "monthly_diatom_positive": positive_monthly,
        "monthly_diatom_cv": monthly_cv,
        "monthly_diatom_cv_threshold": 0.05,
        "seasonality_pass": seasonality_pass,
    }


def _initial_condition_gate(scenarios: dict, mask: torch.Tensor) -> dict:
    central = scenarios[CENTRAL_SCENARIO]["cycle12_all_step_mean"]
    per_flank = {}
    failures = []
    for flank in ("ic_0p01", "ic_0p50"):
        current = scenarios[flank]["cycle12_all_step_mean"]
        changes = {
            name: _masked_relative_l2(current[index], central[index], mask)
            for name, index in zip(
                PLANKTON_NAMES, PLANKTON_STATE_INDICES, strict=True
            )
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


def _sensitivity_gate(aois: dict) -> dict:
    per_aoi = {}
    signs = []
    qualifying = []
    threshold = math.log(1.05)
    for aoi, item in aois.items():
        mask = item["mask"]
        low = item["scenarios"]["dg_0p90"]["cycle12_all_step_mean"][
            layer2.I_DIATOM
        ][mask].double().sum()
        high = item["scenarios"]["dg_1p10"]["cycle12_all_step_mean"][
            layer2.I_DIATOM
        ][mask].double().sum()
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
    sign_agreement = len(signs) == len(aois) and len(set(signs)) == 1 and signs[0] != 0
    return {
        "pass": len(qualifying) >= 2 and sign_agreement,
        "qualifying_aois": qualifying,
        "minimum_qualifying_aois": 2,
        "sign_agreement": sign_agreement,
        "per_aoi": per_aoi,
    }


def _cpu_record(record: dict) -> dict:
    out = {}
    for key, value in record.items():
        if isinstance(value, torch.Tensor):
            out[key] = value.detach().cpu()
        elif isinstance(value, dict):
            out[key] = _cpu_record(value)
        else:
            out[key] = value
    return out


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
    parser.add_argument("--source-prey-floor-c", type=float, default=0.0)
    parser.add_argument("--preregistration", default=PREREGISTRATION)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    args = parser.parse_args(argv)

    device = args.device
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by the frozen full-resolution gate")
    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    layer2.USE_COCCOLITH_ONLY_CALCITE = False
    layer2.USE_ENV_RAIN_RATIO = False

    step_fn = explicit_zooplankton_step
    compiled = False
    if args.compile_step:
        try:
            step_fn = torch.compile(
                explicit_zooplankton_step,
                backend="inductor",
                fullgraph=True,
                dynamic=False,
            )
            compiled = True
        except Exception as exc:  # pragma: no cover - device/compiler dependent
            print(f"torch.compile setup failed: {exc}; using eager")

    truth_base = CARROLL_VALUES.to(device=device, dtype=torch.float32)
    config = {
        "dt_days": DT,
        "steps_per_month": STEPS_PER_MONTH,
        "cycles": N_CYCLES,
        "recorded_cycles": list(RECORDED_CYCLES),
        "aois": list(args.aois),
        "light": "parameter-free-astronomical-monthly",
        "chemical_restoring_tau_days": RESTORING_TAU_DAYS,
        "restoring_indices": list(CHEMICAL_RESTORING_INDICES),
        "phytoplankton_restoring": False,
        "zooplankton_restoring": False,
        "source_prey_floor_c": args.source_prey_floor_c,
        "zoo_initial_fractions_per_predator": list(IC_FRACTIONS),
        "diatomgraz_factors": list(DIATOMGRAZ_FACTORS),
        "central_scenario": CENTRAL_SCENARIO,
        "scenarios": SCENARIOS,
        "truth": [float(value) for value in truth_base.cpu()],
        "state_count": N_TRACERS_EXPLICIT_ZOO,
        "source_constants": {
            "graze_max_per_day": GRAZE_MAX_PER_DAY,
            "half_saturation_c": GRAZE_HALF_SATURATION_C,
            "zoo_mortality_per_day": ZOO_MORTALITY_PER_DAY,
            "phygrazmin_c": SOURCE_PHYGRAZ_MIN_C,
            "assimilation": [list(row) for row in ASSIMILATION],
        },
        "source_commit": "75b8e4337c2fa0c0baa9fa9376590503229121af",
    }
    bundle = {
        "schema_version": 1,
        "preregistration": args.preregistration,
        "config": config,
        "aois": {},
    }
    report = {
        "schema_version": 1,
        "status": "MEASURED_NOT_INDEPENDENTLY_VERIFIED",
        "created_utc": datetime.now(UTC).isoformat(),
        "preregistration": args.preregistration,
        "config": config,
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(device),
            "compiled_step": compiled,
        },
        "aois": {},
        "decision": {"gate_pass": False, "b200_authorized": False},
    }

    started = time.perf_counter()
    dataset = open_bin_average(args.bin_average)
    try:
        for aoi in args.aois:
            aoi_started = time.perf_counter()
            base_state, forcing, mask, metadata = _load_aoi(dataset, aoi, device)
            monthly_light = astronomical_monthly_light(forcing["latitude_degrees"])
            light_gate = evaluate_light_integrity(monthly_light, mask)
            height, width = mask.shape
            truth = truth_base.reshape(6, 1, 1).expand(6, height, width).contiguous()
            scenario_bundle = {}
            scenario_runtime = {}

            print(f"{aoi}: cells={int(mask.sum())} scenarios={len(SCENARIOS)}")
            for scenario, spec in SCENARIOS.items():
                scenario_started = time.perf_counter()
                initial = initialize_zooplankton(
                    base_state.clone(), spec["zoo_initial_fraction"]
                )
                state = initial.clone()
                restoring_reference = initial.clone()
                params = truth.clone()
                params[layer2.I_DIATOMGRAZ] *= spec["diatomgraz_factor"]
                recorded = {}
                for cycle in range(1, N_CYCLES + 1):
                    with torch.no_grad():
                        month_ends, all_step_mean, budget = (
                            integrate_explicit_zooplankton_restored_cycle(
                                state,
                                params,
                                DT,
                                forcing["T_monthly"],
                                forcing["S_monthly"],
                                forcing["wind_monthly"],
                                restoring_reference,
                                restoring_timescale_days=RESTORING_TAU_DAYS,
                                restoring_spatial_mask=mask,
                                steps_per_month=STEPS_PER_MONTH,
                                pco2_atm=forcing["pco2_atm"],
                                step_fn=step_fn,
                                light_monthly=monthly_light,
                                source_prey_floor_c=args.source_prey_floor_c,
                            )
                        )
                    endpoint = month_ends[-1]
                    if cycle in RECORDED_CYCLES:
                        recorded[cycle] = {
                            "all_step_mean": all_step_mean,
                            "month_ends": month_ends,
                            "endpoint": endpoint,
                            "budget": budget,
                        }
                    state = endpoint
                _synchronize(device)
                elapsed = time.perf_counter() - scenario_started
                scenario_runtime[scenario] = elapsed
                scenario_bundle[scenario] = _cpu_record(
                    {
                        "spec": spec,
                        "initial_state": initial,
                        "cycle11_all_step_mean": recorded[11]["all_step_mean"],
                        "cycle12_all_step_mean": recorded[12]["all_step_mean"],
                        "cycle12_month_ends": recorded[12]["month_ends"],
                        "cycle12_endpoint": recorded[12]["endpoint"],
                        "cycle12_budget": recorded[12]["budget"],
                    }
                )
                print(f"  {scenario}: {elapsed:.1f}s")

            mask_cpu = mask.cpu()
            central = scenario_bundle[CENTRAL_SCENARIO]
            gates = {
                "light": light_gate,
                "numerical": _numerical_gate(central["cycle12_budget"], mask_cpu),
                "stability": _cycle_stability(
                    central["cycle11_all_step_mean"],
                    central["cycle12_all_step_mean"],
                    mask_cpu,
                ),
                "closure": _closure_gate(central["cycle12_budget"], mask_cpu),
                "dfe": _dfe_gate(
                    central["cycle11_all_step_mean"],
                    central["cycle12_all_step_mean"],
                    mask_cpu,
                    aoi,
                ),
                "viability": _viability_gate(
                    central["initial_state"],
                    central["cycle12_all_step_mean"],
                    central["cycle12_month_ends"],
                    mask_cpu,
                ),
                "initial_condition_robustness": _initial_condition_gate(
                    scenario_bundle, mask_cpu
                ),
            }
            aoi_pass = all(gate["pass"] for gate in gates.values())
            report["aois"][aoi] = {
                "metadata": metadata,
                "scenario_elapsed_seconds": scenario_runtime,
                "gates": gates,
                "pass_before_sensitivity": aoi_pass,
            }
            bundle["aois"][aoi] = {
                "mask": mask_cpu,
                "monthly_light": monthly_light.cpu(),
                "scenarios": scenario_bundle,
            }
            print(
                f"  gates={'PASS' if aoi_pass else 'FAIL'} "
                f"retention={gates['viability']['per_plankton']['diatom']['retention']:.3g} "
                f"zIC={gates['initial_condition_robustness']['pass']}"
            )
            report["aois"][aoi]["elapsed_seconds"] = time.perf_counter() - aoi_started
    finally:
        dataset.close()

    sensitivity = _sensitivity_gate(bundle["aois"])
    report["sensitivity_gate"] = sensitivity
    aoi_passes = {
        aoi: item["pass_before_sensitivity"] for aoi, item in report["aois"].items()
    }
    gate_pass = all(aoi_passes.values()) and sensitivity["pass"]
    failure_reasons = [aoi for aoi, passes in aoi_passes.items() if not passes]
    if not sensitivity["pass"]:
        failure_reasons.append("diatomgraz_sensitivity")
    report["decision"] = {
        "branch": "stage0-pass-cost-gate-authorized" if gate_pass else "stage0-failed-stop",
        "gate_pass": gate_pass,
        "failure_reasons": failure_reasons,
        "per_aoi_pass_before_sensitivity": aoi_passes,
        "b200_authorized": gate_pass,
        "next_action": (
            "one-seed-one-epoch-b200-cost-gate"
            if gate_pass
            else "no-optimizer-no-b200"
        ),
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
    print(
        f"decision={report['decision']['branch']} "
        f"B200={report['decision']['b200_authorized']} "
        f"report={args.report} bundle={args.bundle}"
    )
    return 0 if gate_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
