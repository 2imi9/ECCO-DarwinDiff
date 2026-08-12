#!/usr/bin/env python3
"""Compute the preregistered process budgets for failed seasonal twin targets."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from pathlib import Path

import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.carroll6_5pft_2layer import PHYTOPLANKTON_NAMES
from darwindiff.ecco_darwin_loader import open_bin_average
from darwindiff.seasonal_twin import (
    astronomical_monthly_light,
    integrate_seasonal_restored_process_budgets,
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
    "docs/findings/2026-08-09_prereg_seasonal_twin_phytoplankton_process_budget.md"
)
CONSTRUCTIONS = ("chemical-fixed-light", "chemical-astronomical-light")
BUDGET_CYCLES = (1, 2, 7, 8)


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


def _atomic_gzip_torch_save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(temporary, "wb", compresslevel=6) as stream:
        torch.save(payload, stream)
    temporary.replace(path)


def _masked_sum(tensor: torch.Tensor, mask: torch.Tensor) -> float:
    return float(tensor[:, mask].to(torch.float64).sum())


def _component_summary(
    growth: float,
    linear: float,
    quadratic: float,
    grazing: float,
    clamp: float,
    raw_negative_events: int,
    post_step_zero_events: int,
    initial: float,
    final: float,
    denominator_events: int,
) -> dict[str, float | int | bool | str | None]:
    loss = linear + quadratic + grazing
    scale = max(growth + loss, 1e-30)
    balance = (growth - loss) / scale
    if balance <= -0.10:
        classification = "loss-dominated"
    elif balance >= 0.10:
        classification = "growth-dominated"
    else:
        classification = "balanced"
    shares = {
        "linear": linear / max(loss, 1e-30),
        "quadratic": quadratic / max(loss, 1e-30),
        "grazing": grazing / max(loss, 1e-30),
    }
    dominant_name, dominant_share = max(shares.items(), key=lambda item: item[1])
    clamp_burden = clamp / scale
    event_fraction = raw_negative_events / max(denominator_events, 1)
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
        "dominant_loss_component": dominant_name if dominant_share > 0.50 else None,
        "clamp_correction": clamp,
        "clamp_burden": clamp_burden,
        "raw_negative_events": raw_negative_events,
        "post_step_zero_events": post_step_zero_events,
        "clamp_event_fraction": event_fraction,
        "severe_clamp": clamp_burden >= 0.01 or event_fraction >= 0.01,
        "initial_inventory": initial,
        "final_inventory": final,
        "inventory_retention": retention,
        "collapsed": retention <= 1e-6,
    }


def summarize_budget(
    budget: dict[str, torch.Tensor | int], mask: torch.Tensor
) -> dict[str, object]:
    """Aggregate one raw budget according to the preregistered rules."""
    step_count = int(budget["step_count"])
    n_cells = int(mask.sum())
    pft_summaries: dict[str, dict] = {}
    for index, name in enumerate(PHYTOPLANKTON_NAMES):
        selector = mask.unsqueeze(0)
        pft_summaries[name] = _component_summary(
            float(budget["growth"][index][mask].to(torch.float64).sum()),
            float(budget["linear_mortality"][index][mask].to(torch.float64).sum()),
            float(budget["quadratic_mortality"][index][mask].to(torch.float64).sum()),
            float(budget["grazing"][index][mask].to(torch.float64).sum()),
            float(budget["clamp_correction"][index][mask].to(torch.float64).sum()),
            int(budget["raw_negative_events"][index][mask].sum()),
            int(budget["post_step_zero_events"][index][mask].sum()),
            float(budget["initial_phyto"][index][mask].to(torch.float64).sum()),
            float(budget["final_phyto"][index][mask].to(torch.float64).sum()),
            step_count * int(selector.sum()),
        )

    total = _component_summary(
        _masked_sum(budget["growth"], mask),
        _masked_sum(budget["linear_mortality"], mask),
        _masked_sum(budget["quadratic_mortality"], mask),
        _masked_sum(budget["grazing"], mask),
        _masked_sum(budget["clamp_correction"], mask),
        int(budget["raw_negative_events"][:, mask].sum()),
        int(budget["post_step_zero_events"][:, mask].sum()),
        _masked_sum(budget["initial_phyto"], mask),
        _masked_sum(budget["final_phyto"], mask),
        step_count * n_cells * len(PHYTOPLANKTON_NAMES),
    )
    total["closure_abs"] = _masked_sum(budget["closure_abs"], mask)
    total["f_fe_mean"] = float(budget["f_fe_mean"][mask].to(torch.float64).mean())
    total["light_mean"] = float(budget["light_mean"][mask].to(torch.float64).mean())
    total["gamma_t_mean"] = float(
        budget["gamma_t_mean"][mask].to(torch.float64).mean()
    )
    return {
        "step_count": step_count,
        "n_ocean_cells": n_cells,
        "all_pft": total,
        "per_pft": pft_summaries,
    }


def classify_decision(report: dict) -> dict[str, object]:
    """Apply the frozen cross-AOI precedence rule to cycle 8."""
    numerical: list[str] = []
    light_driver: list[str] = []
    intrinsic: list[str] = []
    fixed = report["constructions"]["chemical-fixed-light"]["aois"]
    astronomical = report["constructions"]["chemical-astronomical-light"]["aois"]
    for aoi in DEFAULT_AOIS:
        fixed_total = fixed[aoi]["cycles"]["8"]["all_pft"]
        light_total = astronomical[aoi]["cycles"]["8"]["all_pft"]
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
        branch = "numerical-floor-failure"
        qualifying = numerical
    elif len(light_driver) >= 2:
        branch = "light-driver-failure"
        qualifying = light_driver
    elif len(intrinsic) >= 2:
        branch = "intrinsic-sink-imbalance"
        qualifying = intrinsic
    else:
        branch = "mixed-or-other"
        qualifying = []
    return {
        "branch": branch,
        "qualifying_aois": qualifying,
        "numerical_floor_aois": numerical,
        "light_driver_aois": light_driver,
        "intrinsic_sink_aois": intrinsic,
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
        parser.error(
            "the preregistered production diagnostic requires 122 steps/month and 8 cycles"
        )
    if tuple(args.aois) != DEFAULT_AOIS:
        parser.error("the preregistered production diagnostic requires all three canonical AOIs")
    if not args.bin_average.is_file():
        parser.error(f"bin-average product does not exist: {args.bin_average}")

    layer2.USE_EPPLEY_T = True
    layer2.A_E_EPPLEY = 0.0633
    layer2.T_REF_EPPLEY = 15.0
    device = _device(args.device)
    step_fn = layer2.carroll6_5pft_2layer_step
    compiled = False
    if args.compile_step:
        step_fn = torch.compile(step_fn, mode="default", dynamic=True)
        compiled = True

    config = {
        "dt_days": DT,
        "steps_per_month": args.steps_per_month,
        "cycles": args.cycles,
        "budget_cycles": list(BUDGET_CYCLES),
        "aois": list(args.aois),
        "constructions": list(CONSTRUCTIONS),
        "chemical_restoring_tau_days": 365.25,
        "phytoplankton_restoring": False,
        "truth": [float(value) for value in CARROLL_VALUES],
        "eppley": {"enabled": True, "coefficient": 0.0633, "reference_c": 15.0},
        "compiled_step": compiled,
        "device": str(device),
    }
    bundle: dict[str, object] = {
        "schema_version": 1,
        "preregistration": PREREGISTRATION,
        "config": config,
        "constructions": {},
    }
    report: dict[str, object] = {
        "schema_version": 1,
        "status": "measured-not-yet-independently-verified",
        "preregistration": PREREGISTRATION,
        "config": config,
        "constructions": {},
    }

    dataset = open_bin_average(args.bin_average)
    started = time.perf_counter()
    try:
        loaded = {
            aoi: _load_aoi(dataset, aoi, device)
            for aoi in args.aois
        }
        for construction in CONSTRUCTIONS:
            use_light = construction == "chemical-astronomical-light"
            bundle_construction = {"aois": {}}
            report_construction = {"aois": {}}
            for aoi in args.aois:
                aoi_started = time.perf_counter()
                state0, forcing, mask, metadata = loaded[aoi]
                height, width = mask.shape
                truth = CARROLL_VALUES.to(device=device, dtype=torch.float32).reshape(6, 1, 1)
                truth = truth.expand(6, height, width).contiguous()
                monthly_light = (
                    astronomical_monthly_light(forcing["latitude_degrees"])
                    if use_light
                    else None
                )
                _synchronize(device)
                final_state, budgets = integrate_seasonal_restored_process_budgets(
                    state0.clone(),
                    truth,
                    DT,
                    forcing["T_monthly"],
                    forcing["S_monthly"],
                    forcing["wind_monthly"],
                    state0,
                    restoring_timescale_days=365.25,
                    restoring_spatial_mask=mask,
                    steps_per_month=args.steps_per_month,
                    n_cycles=args.cycles,
                    budget_cycles=BUDGET_CYCLES,
                    pco2_atm=forcing["pco2_atm"],
                    step_fn=step_fn,
                    light_monthly=monthly_light,
                )
                _synchronize(device)

                mask_cpu = mask.cpu()
                cpu_budgets: dict[int, dict[str, torch.Tensor | int]] = {}
                cycle_summaries: dict[str, dict] = {}
                for cycle, budget in budgets.items():
                    compact = {
                        key: value.cpu() if isinstance(value, torch.Tensor) else value
                        for key, value in budget.items()
                        if key != "month_ends"
                    }
                    cpu_budgets[cycle] = compact
                    cycle_summaries[str(cycle)] = summarize_budget(compact, mask_cpu)
                bundle_construction["aois"][aoi] = {
                    "metadata": metadata,
                    "mask": mask_cpu,
                    "cycles": cpu_budgets,
                    "final_state": final_state.cpu(),
                    "monthly_light": monthly_light.cpu() if monthly_light is not None else None,
                }
                report_construction["aois"][aoi] = {
                    **metadata,
                    "cycles": cycle_summaries,
                    "elapsed_seconds": time.perf_counter() - aoi_started,
                }
                cycle8 = cycle_summaries["8"]["all_pft"]
                print(
                    f"{construction} {aoi}: B={cycle8['signed_balance']:.4f} "
                    f"K={cycle8['clamp_burden']:.3e} Q={cycle8['inventory_retention']:.3e}"
                )
            bundle["constructions"][construction] = bundle_construction
            report["constructions"][construction] = report_construction
    finally:
        dataset.close()

    report["decision"] = classify_decision(report)
    report["elapsed_seconds"] = time.perf_counter() - started
    _atomic_gzip_torch_save(args.bundle_out, bundle)
    report["bundle_artifact"] = {
        "path": args.bundle_out.as_posix(),
        "bytes": args.bundle_out.stat().st_size,
        "sha256": _sha256(args.bundle_out),
    }
    _atomic_json(args.output, report)
    print(
        f"PROCESS BUDGET MEASURED branch={report['decision']['branch']} "
        f"bundle={args.bundle_out} report={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
