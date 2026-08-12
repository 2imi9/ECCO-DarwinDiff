#!/usr/bin/env python
"""Build and gate the preregistered seasonally forced Carroll self-twin target.

This is Stage 0 of issue #239. It runs no optimizer. A recovery runner must only
consume the emitted tensor bundle when ``gate_pass`` is true.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1,
    I_ALK_2,
    I_DFE_1,
    I_DFE_2,
    I_DIC_1,
    I_DIC_2,
    I_PIC_1,
    I_PIC_2,
    I_POC_1,
    I_POC_2,
    N_TRACERS_2LAYER,
    PCO2_ATM_DEFAULT,
    carroll6_5pft_2layer_integrate_seasonal_summary,
    carroll6_5pft_2layer_step,
)
from darwindiff.ecco_darwin_loader import (
    AOI_BY_KEY,
    monthly_climatology,
    open_bin_average,
    subset_aoi,
)
from darwindiff.seasonal_twin import (
    ASTRONOMICAL_DECLINATION_PHASE_DAY,
    ASTRONOMICAL_OBLIQUITY_DEGREES,
    ASTRONOMICAL_RECONSTRUCTION_ATOL,
    ASTRONOMICAL_YEAR_DAYS,
    CHEMICAL_RESTORING_INDICES,
    DFE2_MIN_REL_SD,
    MONTH_MIDPOINT_DAY_OF_YEAR,
    astronomical_monthly_light,
    evaluate_light_integrity,
    evaluate_restoring_budget,
    evaluate_target_cycle,
    integrate_seasonal_restored_summary,
    summarize_target_state,
)

DT = 0.25
DEFAULT_AOIS = tuple(DFE2_MIN_REL_SD)
SCRIPT_DIR = Path(__file__).resolve().parents[1]
IC_CACHE_NAMES = {
    "eqpac": "darwin_ic_cache.npz",
    "natlsubpolar": "darwin_ic_cache_natlsubpolar.npz",
    "southernoceanpac": "darwin_ic_cache_southernoceanpac.npz",
}
LITERATURE_IC = (
    5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
    0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
    5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
)
IC_OVERRIDES = (
    (I_DFE_1, "FeT_L1"),
    (I_POC_1, "POC_L1"),
    (I_PIC_1, "PIC_L1"),
    (I_DIC_1, "DIC_L1"),
    (I_ALK_1, "ALK_L1"),
    (I_DFE_2, "FeT_L2"),
    (I_POC_2, "POC_L2"),
    (I_PIC_2, "PIC_L2"),
    (I_DIC_2, "DIC_L2"),
    (I_ALK_2, "ALK_L2"),
)
POSITIVE_IC_INDICES = {I_DFE_1, I_DFE_2, I_POC_1, I_POC_2, I_PIC_1, I_PIC_2}


def _parse_aois(raw: str) -> tuple[str, ...]:
    keys = tuple(part.strip() for part in raw.split(",") if part.strip())
    if not keys:
        raise argparse.ArgumentTypeError("at least one AOI is required")
    unknown = set(keys) - set(DEFAULT_AOIS)
    if unknown:
        raise argparse.ArgumentTypeError(
            f"no preregistered target gate for {sorted(unknown)}; choose from {list(DEFAULT_AOIS)}"
        )
    if len(set(keys)) != len(keys):
        raise argparse.ArgumentTypeError("AOIs must be unique")
    return keys


def _device(raw: str) -> torch.device:
    if raw == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    device = torch.device(raw)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false")
    return device


def _to_monthly_tensor(values: np.ndarray, fill: float, device: torch.device) -> torch.Tensor:
    clean = np.nan_to_num(values.astype(np.float32), nan=fill, posinf=fill, neginf=fill)
    return torch.tensor(clean, dtype=torch.float32, device=device)


def _load_aoi(
    dataset,
    aoi_key: str,
    device: torch.device,
) -> tuple[torch.Tensor, dict[str, torch.Tensor], torch.Tensor, dict]:
    subset = subset_aoi(dataset, AOI_BY_KEY[aoi_key])
    monthly = monthly_climatology(subset[["SST", "SSS", "windSpeed"]])
    raw_t = monthly["SST"].values.astype(np.float32)
    raw_s = monthly["SSS"].values.astype(np.float32)
    raw_w = monthly["windSpeed"].values.astype(np.float32)
    mask_np = np.all(np.isfinite(raw_t) & np.isfinite(raw_s) & np.isfinite(raw_w), axis=0)
    if int(mask_np.sum()) < 2:
        raise RuntimeError(f"{aoi_key}: fewer than two cells have complete monthly forcing")

    forcing = {
        "T_monthly": _to_monthly_tensor(raw_t, 15.0, device),
        "S_monthly": _to_monthly_tensor(raw_s, 35.0, device),
        "wind_monthly": _to_monthly_tensor(raw_w, 7.0, device),
    }
    latitude = np.broadcast_to(
        np.asarray(subset.lat.values, dtype=np.float32)[:, None], mask_np.shape
    ).copy()
    forcing["latitude_degrees"] = torch.tensor(
        latitude, dtype=torch.float32, device=device
    )
    if "apCO2" in subset:
        pco2 = subset["apCO2"].mean(dim="time", skipna=True).values.astype(np.float32)
        forcing["pco2_atm"] = _to_monthly_tensor(pco2, float(PCO2_ATM_DEFAULT), device)
    else:
        forcing["pco2_atm"] = torch.full(
            mask_np.shape, float(PCO2_ATM_DEFAULT), dtype=torch.float32, device=device
        )

    height, width = mask_np.shape
    state0 = torch.tensor(LITERATURE_IC, dtype=torch.float32).reshape(
        N_TRACERS_2LAYER, 1, 1
    ).expand(N_TRACERS_2LAYER, height, width).clone()
    cache_path = SCRIPT_DIR / IC_CACHE_NAMES[aoi_key]
    if not cache_path.is_file():
        raise FileNotFoundError(f"missing preregistered Darwin IC cache: {cache_path}")
    cache = np.load(cache_path)
    for state_index, cache_key in IC_OVERRIDES:
        field = np.asarray(cache[cache_key])
        if field.shape != (height, width):
            raise ValueError(
                f"{aoi_key} IC {cache_key} shape {field.shape} != {(height, width)}"
            )
        safe = np.where(np.isfinite(field), field, LITERATURE_IC[state_index]).astype(np.float32)
        if state_index in POSITIVE_IC_INDICES:
            safe = np.clip(safe, a_min=1e-10, a_max=None)
        state0[state_index] = torch.from_numpy(safe)

    metadata = {
        "shape": [height, width],
        "n_ocean_cells": int(mask_np.sum()),
        "ic_cache": str(cache_path),
        "lat_bounds": [float(subset.lat.min()), float(subset.lat.max())],
        "lon_bounds": [float(subset.lon.min()), float(subset.lon.max())],
    }
    mask = torch.tensor(mask_np, dtype=torch.bool, device=device)
    return state0.to(device), forcing, mask, metadata


def _synchronize(device: torch.device) -> None:
    if device.type == "cuda":
        torch.cuda.synchronize(device)


def _atomic_json(path: Path, payload: dict) -> None:
    def json_safe(value):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, dict):
            return {key: json_safe(item) for key, item in value.items()}
        if isinstance(value, list):
            return [json_safe(item) for item in value]
        return value

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(json_safe(payload), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _atomic_torch_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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
    parser.add_argument("--min-cycles", type=int, default=2)
    parser.add_argument("--max-cycles", type=int, default=8)
    parser.add_argument("--a-e-eppley", type=float, default=0.0633)
    parser.add_argument("--t-ref-eppley", type=float, default=15.0)
    parser.add_argument(
        "--chemical-restoring-tau-days",
        type=float,
        help="enable fixed chemical-only restoring closure with this timescale",
    )
    parser.add_argument(
        "--astronomical-light",
        action="store_true",
        help="enable the preregistered latitude-only monthly TOA light field",
    )
    parser.add_argument("--device", default="auto")
    parser.add_argument("--compile", action="store_true", dest="compile_step")
    parser.add_argument(
        "--output", type=Path, default=Path("runs/seasonal_twin/target_gate.json")
    )
    parser.add_argument(
        "--bundle-out", type=Path, default=Path("runs/seasonal_twin/target_bundle.pt")
    )
    args = parser.parse_args(argv)

    if args.steps_per_month < 1:
        parser.error("--steps-per-month must be >= 1")
    if args.min_cycles < 2:
        parser.error("--min-cycles must be >= 2 so cycle stability is measurable")
    if args.max_cycles < args.min_cycles:
        parser.error("--max-cycles must be >= --min-cycles")
    if args.chemical_restoring_tau_days is not None and args.chemical_restoring_tau_days <= 0:
        parser.error("--chemical-restoring-tau-days must be > 0")
    if args.astronomical_light and args.chemical_restoring_tau_days is None:
        parser.error("--astronomical-light requires --chemical-restoring-tau-days")
    if not args.bin_average.is_file():
        parser.error(f"bin-average product does not exist: {args.bin_average}")

    # The canonical flagship pins this gate on. Set the module globals before
    # torch.compile traces the step; monthly T otherwise has no biological effect.
    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = args.a_e_eppley
    layer2.T_REF_EPPLEY = args.t_ref_eppley

    device = _device(args.device)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)
    step_fn = carroll6_5pft_2layer_step
    compiled = False
    if args.compile_step:
        try:
            step_fn = torch.compile(
                carroll6_5pft_2layer_step, mode="default", dynamic=True
            )
            compiled = True
        except Exception as exc:
            print(f"torch.compile setup failed: {exc}; using eager step")
            step_fn = carroll6_5pft_2layer_step

    started = time.perf_counter()
    restoring_enabled = args.chemical_restoring_tau_days is not None
    light_enabled = args.astronomical_light
    if light_enabled:
        preregistration = (
            "docs/findings/2026-08-09_prereg_seasonal_twin_astronomical_light.md"
        )
        relational_hypothesis = "hy_szn_light"
    elif restoring_enabled:
        preregistration = (
            "docs/findings/2026-08-09_prereg_seasonal_twin_chemical_restoring_closure.md"
        )
        relational_hypothesis = "hy_szn_chem"
    else:
        preregistration = "docs/findings/2026-08-09_prereg_seasonal_loss_self_twin.md"
        relational_hypothesis = "hy_szn_loss"
    config = {
        "aois": list(args.aois),
        "dt_days": DT,
        "steps_per_month": args.steps_per_month,
        "mean_statistic": "all_post_step_states_in_recorded_cycle",
        "month_endpoint_mean_role": "diagnostic_only",
        "min_cycles": args.min_cycles,
        "max_cycles": args.max_cycles,
        "truth": [float(value) for value in CARROLL_VALUES],
        "monthly_forcing": ["SST", "SSS", "windSpeed"],
        "monthly_light": light_enabled,
        "use_eppley_temperature_growth": True,
        "a_e_eppley": args.a_e_eppley,
        "t_ref_eppley": args.t_ref_eppley,
        "southern_ocean_daniels_weight": 0.0,
        "southern_ocean_posi_weight": 0.0,
    }
    if restoring_enabled:
        config["chemical_restoring_closure"] = {
            "timescale_days": args.chemical_restoring_tau_days,
            "reference": "aoi_darwin_ic_cache",
            "indices": list(CHEMICAL_RESTORING_INDICES),
            "phytoplankton_restoring": False,
            "closure_share_max": 0.50,
            "closure_turnover_max": 1.0,
        }
    if light_enabled:
        config["astronomical_monthly_light"] = {
            "construction": "daily_mean_top_of_atmosphere_insolation",
            "obliquity_degrees": ASTRONOMICAL_OBLIQUITY_DEGREES,
            "year_days": ASTRONOMICAL_YEAR_DAYS,
            "declination_phase_day": ASTRONOMICAL_DECLINATION_PHASE_DAY,
            "month_midpoint_day_of_year": list(MONTH_MIDPOINT_DAY_OF_YEAR),
            "normalization": "per_cell_12_month_arithmetic_mean",
            "fitted_parameters": False,
            "per_cell_mean_tolerance": 1e-6,
            "cross_device_reconstruction_atol": ASTRONOMICAL_RECONSTRUCTION_ATOL,
        }
    report: dict = {
        "schema_version": 2,
        "preregistration": preregistration,
        "relational_hypothesis": relational_hypothesis,
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "RUNNING",
        "gate_pass": False,
        "config": config,
        "runtime": {
            "device": str(device),
            "torch_version": torch.__version__,
            "cuda_version": torch.version.cuda,
            "device_name": torch.cuda.get_device_name(device) if device.type == "cuda" else None,
            "compiled_step": compiled,
        },
        "aois": {},
        "failure_reasons": [],
    }
    bundle: dict = {
        "schema_version": 2,
        "gate_pass": False,
        "preregistration": preregistration,
        "relational_hypothesis": relational_hypothesis,
        "config": config,
        "aois": {},
    }

    print(
        f"seasonal target gate: aois={','.join(args.aois)} spm={args.steps_per_month} "
        f"cycles={args.min_cycles}..{args.max_cycles} device={device} compiled={compiled} "
        f"closure_tau={args.chemical_restoring_tau_days} light={light_enabled}"
    )
    dataset = open_bin_average(args.bin_average)
    try:
        for aoi_key in args.aois:
            aoi_started = time.perf_counter()
            state, forcing, mask, metadata = _load_aoi(dataset, aoi_key, device)
            restoring_reference = state.detach().clone()
            light_monthly = (
                astronomical_monthly_light(forcing["latitude_degrees"])
                if light_enabled
                else None
            )
            light_gate = (
                evaluate_light_integrity(light_monthly, mask)
                if light_monthly is not None
                else None
            )
            mask_cpu = mask.cpu()
            height, width = mask.shape
            truth = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
            truth = truth.expand(6, height, width).contiguous()
            previous_mean_cpu: torch.Tensor | None = None
            selected: dict | None = None
            cycles: list[dict] = []
            cycle_states: list[dict] = []
            last_states: dict[str, torch.Tensor] | None = None

            for cycle_number in range(1, args.max_cycles + 1):
                _synchronize(device)
                cycle_started = time.perf_counter()
                with torch.no_grad():
                    restoring_budget = None
                    if restoring_enabled:
                        month_ends, all_step_mean, restoring_budget = (
                            integrate_seasonal_restored_summary(
                                state,
                                truth,
                                DT,
                                forcing["T_monthly"],
                                forcing["S_monthly"],
                                forcing["wind_monthly"],
                                restoring_reference,
                                restoring_timescale_days=args.chemical_restoring_tau_days,
                                restoring_spatial_mask=mask,
                                steps_per_month=args.steps_per_month,
                                pco2_atm=forcing["pco2_atm"],
                                step_fn=step_fn,
                                light_monthly=light_monthly,
                            )
                        )
                    else:
                        month_ends, all_step_mean = (
                            carroll6_5pft_2layer_integrate_seasonal_summary(
                                state,
                                truth,
                                DT,
                                forcing["T_monthly"],
                                forcing["S_monthly"],
                                forcing["wind_monthly"],
                                steps_per_month=args.steps_per_month,
                                n_spinup_cycles=0,
                                pco2_atm=forcing["pco2_atm"],
                                step_fn=step_fn,
                                light_monthly=light_monthly,
                            )
                        )
                _synchronize(device)
                cycle_elapsed = time.perf_counter() - cycle_started
                endpoint = month_ends[-1].detach()
                month_endpoint_mean = month_ends.mean(dim=0).detach()
                all_step_mean = all_step_mean.detach()
                endpoint_cpu = endpoint.cpu()
                all_step_mean_cpu = all_step_mean.cpu()
                month_endpoint_mean_cpu = month_endpoint_mean.cpu()
                restoring_budget_cpu = (
                    {name: tensor.cpu() for name, tensor in restoring_budget.items()}
                    if restoring_budget is not None
                    else None
                )
                cycle_record = {
                    "cycle": cycle_number,
                    "elapsed_seconds": cycle_elapsed,
                    "endpoint": summarize_target_state(endpoint_cpu, mask_cpu),
                    "all_step_mean": summarize_target_state(all_step_mean_cpu, mask_cpu),
                    "month_endpoint_mean": summarize_target_state(
                        month_endpoint_mean_cpu, mask_cpu
                    ),
                    "gate": None,
                }
                if restoring_budget_cpu is not None:
                    cycle_record["closure_gate"] = evaluate_restoring_budget(
                        restoring_budget_cpu, mask_cpu
                    )
                if previous_mean_cpu is not None:
                    cycle_record["gate"] = evaluate_target_cycle(
                        previous_mean_cpu, all_step_mean_cpu, mask_cpu, aoi_key
                    )
                cycles.append(cycle_record)
                last_states = {
                    "endpoint": endpoint_cpu,
                    "all_step_mean": all_step_mean_cpu,
                    "month_endpoint_mean": month_endpoint_mean_cpu,
                }
                saved_cycle = {"cycle": cycle_number, **last_states}
                if restoring_budget_cpu is not None:
                    saved_cycle["restoring_budget"] = restoring_budget_cpu
                cycle_states.append(saved_cycle)
                state = endpoint
                previous_mean_cpu = all_step_mean_cpu

                gate = cycle_record["gate"]
                closure_gate = cycle_record.get("closure_gate")
                target_gate_pass = gate is not None and gate["pass"]
                closure_gate_pass = closure_gate is None or closure_gate["pass"]
                light_gate_pass = light_gate is None or light_gate["pass"]
                if gate is None:
                    gate_text = "not-yet-comparable"
                elif target_gate_pass and closure_gate_pass and light_gate_pass:
                    gate_text = "PASS"
                else:
                    reasons = list(gate["failure_reasons"])
                    if closure_gate is not None:
                        reasons.extend(closure_gate["failure_reasons"])
                    if light_gate is not None:
                        reasons.extend(
                            f"light:{reason}" for reason in light_gate["failure_reasons"]
                        )
                    gate_text = ",".join(reasons)
                print(
                    f"  {aoi_key} cycle={cycle_number} {cycle_elapsed:.1f}s "
                    "DFe2_rel_sd="
                    f"{cycle_record['all_step_mean']['DFe2']['relative_spatial_sd']:.4f} "
                    "Chl1_rel_sd="
                    f"{cycle_record['all_step_mean']['Chl1_diatom']['relative_spatial_sd']:.4f} "
                    f"gate={gate_text}"
                )
                if (
                    cycle_number >= args.min_cycles
                    and target_gate_pass
                    and closure_gate_pass
                    and light_gate_pass
                ):
                    selected = {
                        "cycle": cycle_number,
                        "gate": gate,
                        "states": last_states,
                    }
                    break

            if last_states is None:
                raise RuntimeError(f"{aoi_key}: no seasonal target state was produced")
            passed = selected is not None
            selected_cycle = selected["cycle"] if selected else None
            report["aois"][aoi_key] = {
                **metadata,
                "pass": passed,
                "selected_cycle": selected_cycle,
                "cycles": cycles,
                "elapsed_seconds": time.perf_counter() - aoi_started,
            }
            if light_gate is not None:
                report["aois"][aoi_key]["light_gate"] = light_gate
            states = selected["states"] if selected else last_states
            bundle["aois"][aoi_key] = {
                "pass": passed,
                "selected_cycle": selected_cycle,
                "mask": mask_cpu,
                "cycles": cycle_states,
                **states,
            }
            if light_monthly is not None:
                bundle["aois"][aoi_key]["latitude_degrees"] = forcing[
                    "latitude_degrees"
                ].cpu()
                bundle["aois"][aoi_key]["monthly_light"] = light_monthly.cpu()
            if not passed:
                failure_kind = (
                    "combined_gate_not_passed"
                    if restoring_enabled
                    else "target_gate_not_passed"
                )
                report["failure_reasons"].append(f"{aoi_key}:{failure_kind}")
    finally:
        dataset.close()

    report["elapsed_seconds"] = time.perf_counter() - started
    if device.type == "cuda":
        report["runtime"]["peak_allocated_bytes"] = torch.cuda.max_memory_allocated(device)
        report["runtime"]["peak_reserved_bytes"] = torch.cuda.max_memory_reserved(device)
    report["gate_pass"] = all(item["pass"] for item in report["aois"].values())
    report["status"] = "PASS" if report["gate_pass"] else "FAIL"
    bundle["gate_pass"] = report["gate_pass"]
    bundle["report_path"] = str(args.output)

    _atomic_torch_save(args.bundle_out, bundle)
    report["bundle_artifact"] = {
        "path": str(args.bundle_out),
        "bytes": args.bundle_out.stat().st_size,
        "sha256": _sha256(args.bundle_out),
    }
    _atomic_json(args.output, report)
    print(
        f"target gate {report['status']}: {args.output} bundle={args.bundle_out} "
        f"elapsed={report['elapsed_seconds']:.1f}s"
    )
    return 0 if report["gate_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
