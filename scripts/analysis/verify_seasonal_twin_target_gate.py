#!/usr/bin/env python
"""Verify a seasonal-twin target-gate JSON against its saved cycle tensors."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import torch

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
    summarize_target_state,
)

EXPECTED_AOIS = tuple(DFE2_MIN_REL_SD)
EXPECTED_PREREG_BY_HYPOTHESIS = {
    "hy_szn_loss": "docs/findings/2026-08-09_prereg_seasonal_loss_self_twin.md",
    "hy_szn_chem": "docs/findings/2026-08-09_prereg_seasonal_twin_chemical_restoring_closure.md",
    "hy_szn_light": "docs/findings/2026-08-09_prereg_seasonal_twin_astronomical_light.md",
}


class VerificationError(RuntimeError):
    """Raised when a target-gate artifact violates its recorded contract."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def _compare_json(actual, expected, path: str) -> None:
    """Compare strict-JSON data to recomputed data, accepting null for non-finite floats."""
    if isinstance(expected, float):
        if not math.isfinite(expected):
            _require(actual is None, f"{path}: expected null for non-finite value, got {actual!r}")
            return
        _require(isinstance(actual, int | float), f"{path}: expected a number, got {actual!r}")
        _require(
            math.isclose(float(actual), expected, rel_tol=1e-4, abs_tol=1e-7),
            f"{path}: {actual!r} != recomputed {expected!r}",
        )
        return
    if isinstance(expected, dict):
        _require(isinstance(actual, dict), f"{path}: expected object")
        _require(set(actual) == set(expected), f"{path}: keys differ")
        for key, value in expected.items():
            _compare_json(actual[key], value, f"{path}.{key}")
        return
    if isinstance(expected, list | tuple):
        _require(isinstance(actual, list), f"{path}: expected list")
        _require(len(actual) == len(expected), f"{path}: list length differs")
        for index, value in enumerate(expected):
            _compare_json(actual[index], value, f"{path}[{index}]")
        return
    _require(actual == expected, f"{path}: {actual!r} != {expected!r}")


def _same_tensor(actual: torch.Tensor, expected: torch.Tensor, path: str) -> None:
    _require(actual.shape == expected.shape, f"{path}: tensor shape differs")
    _require(
        torch.allclose(actual, expected, rtol=0.0, atol=0.0, equal_nan=True),
        f"{path}: tensor differs from selected cycle",
    )


def _same_formula_tensor(
    actual: torch.Tensor,
    expected: torch.Tensor,
    path: str,
    *,
    atol: float,
) -> None:
    """Compare a CPU/GPU transcendental reconstruction at a frozen tolerance."""
    _require(actual.shape == expected.shape, f"{path}: tensor shape differs")
    max_abs = float((actual - expected).abs().max())
    _require(
        torch.allclose(actual, expected, rtol=0.0, atol=atol, equal_nan=False),
        f"{path}: formula reconstruction differs (max_abs={max_abs:.9g}, atol={atol:.9g})",
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(report: dict, bundle: dict, *, production: bool = True) -> dict:
    _require(report.get("schema_version") == 2, "report schema_version must be 2")
    _require(bundle.get("schema_version") == 2, "bundle schema_version must be 2")
    hypothesis = report.get("relational_hypothesis")
    _require(hypothesis in EXPECTED_PREREG_BY_HYPOTHESIS, "unexpected hypothesis id")
    expected_prereg = EXPECTED_PREREG_BY_HYPOTHESIS[hypothesis]
    _require(report.get("preregistration") == expected_prereg, "unexpected preregistration")
    _require(bundle.get("preregistration") == expected_prereg, "bundle preregistration differs")
    _require(bundle.get("relational_hypothesis") == hypothesis, "bundle hypothesis id differs")
    _compare_json(report["config"], bundle["config"], "config")

    config = report["config"]
    closure_config = config.get("chemical_restoring_closure")
    closure_enabled = closure_config is not None
    light_config = config.get("astronomical_monthly_light")
    light_enabled = light_config is not None
    _require(
        bool(config.get("monthly_light", False)) is light_enabled,
        "monthly_light flag differs from astronomical-light config",
    )
    if light_enabled:
        _require(closure_enabled, "astronomical light requires the chemical closure")
        _require(hypothesis == "hy_szn_light", "light run must test hy_szn_light")
    elif closure_enabled:
        _require(hypothesis == "hy_szn_chem", "closure run must test hy_szn_chem")
    else:
        _require(hypothesis == "hy_szn_loss", "no-closure run must test hy_szn_loss")
    report_aois = tuple(config["aois"])
    _require(set(report_aois).issubset(EXPECTED_AOIS), "report contains an unregistered AOI")
    if production:
        _require(report_aois == EXPECTED_AOIS, f"production AOIs must be {EXPECTED_AOIS}")
        _require(config["dt_days"] == 0.25, "production dt_days must be 0.25")
        _require(config["steps_per_month"] == 122, "production steps_per_month must be 122")
        _require(config["min_cycles"] == 2, "production min_cycles must be 2")
        _require(config["max_cycles"] == 8, "production max_cycles must be 8")
        _require(config["use_eppley_temperature_growth"] is True, "Eppley gate must be on")
        _require(config["a_e_eppley"] == 0.0633, "unexpected Eppley coefficient")
        _require(config["t_ref_eppley"] == 15.0, "unexpected Eppley reference")
        _require(config["monthly_light"] is light_enabled, "monthly light flag drift")
        _require(config["southern_ocean_daniels_weight"] == 0.0, "SO Daniels must be off")
        _require(config["southern_ocean_posi_weight"] == 0.0, "SO POSi must be off")
        if closure_enabled:
            _require(closure_config["timescale_days"] == 365.25, "closure tau must be 365.25 d")
            _require(
                closure_config["indices"] == list(CHEMICAL_RESTORING_INDICES),
                "unexpected closure indices",
            )
            _require(
                closure_config["phytoplankton_restoring"] is False,
                "phytoplankton restoring must be off",
            )
            _require(closure_config["closure_share_max"] == 0.50, "closure share gate drift")
            _require(
                closure_config["closure_turnover_max"] == 1.0,
                "closure turnover gate drift",
            )
        if light_enabled:
            _require(
                light_config["construction"] == "daily_mean_top_of_atmosphere_insolation",
                "unexpected astronomical-light construction",
            )
            _require(
                light_config["obliquity_degrees"] == ASTRONOMICAL_OBLIQUITY_DEGREES,
                "astronomical obliquity drift",
            )
            _require(light_config["year_days"] == ASTRONOMICAL_YEAR_DAYS, "year length drift")
            _require(
                light_config["declination_phase_day"] == ASTRONOMICAL_DECLINATION_PHASE_DAY,
                "declination phase drift",
            )
            _require(
                light_config["month_midpoint_day_of_year"]
                == list(MONTH_MIDPOINT_DAY_OF_YEAR),
                "month midpoint drift",
            )
            _require(
                light_config["normalization"] == "per_cell_12_month_arithmetic_mean",
                "light normalization drift",
            )
            _require(light_config["fitted_parameters"] is False, "light must not be fitted")
            _require(
                light_config["per_cell_mean_tolerance"] == 1e-6,
                "light mean tolerance drift",
            )
            _require(
                light_config["cross_device_reconstruction_atol"]
                == ASTRONOMICAL_RECONSTRUCTION_ATOL,
                "light reconstruction tolerance drift",
            )

    _require(set(report["aois"]) == set(report_aois), "report AOI records differ from config")
    _require(set(bundle["aois"]) == set(report_aois), "bundle AOI records differ from config")

    verified_cycles = 0
    per_aoi_pass: dict[str, bool] = {}
    for aoi_key in report_aois:
        report_aoi = report["aois"][aoi_key]
        bundle_aoi = bundle["aois"][aoi_key]
        mask = bundle_aoi["mask"]
        _require(
            isinstance(mask, torch.Tensor) and mask.dtype == torch.bool,
            f"{aoi_key}: bad mask",
        )
        _require(int(mask.sum()) == report_aoi["n_ocean_cells"], f"{aoi_key}: cell count differs")

        recomputed_light_gate = None
        if light_enabled:
            latitude = bundle_aoi.get("latitude_degrees")
            saved_light = bundle_aoi.get("monthly_light")
            _require(isinstance(latitude, torch.Tensor), f"{aoi_key}: latitude tensor missing")
            _require(isinstance(saved_light, torch.Tensor), f"{aoi_key}: light tensor missing")
            expected_light = astronomical_monthly_light(latitude)
            _same_formula_tensor(
                saved_light,
                expected_light,
                f"{aoi_key}.monthly_light",
                atol=light_config["cross_device_reconstruction_atol"],
            )
            # The report describes the exact saved GPU field. Formula parity is
            # checked above; summarize the saved values so CPU trig round-off
            # cannot masquerade as report tampering.
            recomputed_light_gate = evaluate_light_integrity(saved_light, mask)
            _compare_json(
                report_aoi.get("light_gate"),
                recomputed_light_gate,
                f"{aoi_key}.light_gate",
            )

        report_cycles = report_aoi["cycles"]
        state_cycles = bundle_aoi["cycles"]
        _require(len(report_cycles) == len(state_cycles), f"{aoi_key}: cycle count differs")
        previous_mean: torch.Tensor | None = None
        first_passing_cycle: int | None = None

        paired_cycles = zip(report_cycles, state_cycles, strict=True)
        for index, (report_cycle, state_cycle) in enumerate(paired_cycles, 1):
            _require(report_cycle["cycle"] == index, f"{aoi_key}: report cycle index differs")
            _require(state_cycle["cycle"] == index, f"{aoi_key}: bundle cycle index differs")
            for statistic in ("endpoint", "all_step_mean", "month_endpoint_mean"):
                state = state_cycle[statistic]
                _require(
                    isinstance(state, torch.Tensor) and state.shape[1:] == mask.shape,
                    f"{aoi_key}.cycle{index}.{statistic}: bad tensor",
                )
                recomputed_summary = summarize_target_state(state, mask)
                _compare_json(
                    report_cycle[statistic],
                    recomputed_summary,
                    f"{aoi_key}.cycle{index}.{statistic}",
                )

            current_mean = state_cycle["all_step_mean"]
            recomputed_gate = None
            if previous_mean is not None:
                recomputed_gate = evaluate_target_cycle(previous_mean, current_mean, mask, aoi_key)
            _compare_json(report_cycle["gate"], recomputed_gate, f"{aoi_key}.cycle{index}.gate")
            recomputed_closure_gate = None
            if closure_enabled:
                budget = state_cycle.get("restoring_budget")
                _require(isinstance(budget, dict), f"{aoi_key}.cycle{index}: budget missing")
                recomputed_closure_gate = evaluate_restoring_budget(budget, mask)
                _compare_json(
                    report_cycle.get("closure_gate"),
                    recomputed_closure_gate,
                    f"{aoi_key}.cycle{index}.closure_gate",
                )
            if (
                index >= config["min_cycles"]
                and recomputed_gate is not None
                and recomputed_gate["pass"]
                and (recomputed_closure_gate is None or recomputed_closure_gate["pass"])
                and (recomputed_light_gate is None or recomputed_light_gate["pass"])
                and first_passing_cycle is None
            ):
                first_passing_cycle = index
            previous_mean = current_mean
            verified_cycles += 1

        aoi_pass = first_passing_cycle is not None
        per_aoi_pass[aoi_key] = aoi_pass
        _require(report_aoi["pass"] is aoi_pass, f"{aoi_key}: report pass flag differs")
        _require(bundle_aoi["pass"] is aoi_pass, f"{aoi_key}: bundle pass flag differs")
        _require(
            report_aoi["selected_cycle"] == first_passing_cycle,
            f"{aoi_key}: selected report cycle differs",
        )
        _require(
            bundle_aoi["selected_cycle"] == first_passing_cycle,
            f"{aoi_key}: selected bundle cycle differs",
        )
        expected_length = first_passing_cycle if aoi_pass else config["max_cycles"]
        _require(len(state_cycles) == expected_length, f"{aoi_key}: unexpected stopping cycle")
        selected_state = state_cycles[-1]
        for statistic in ("endpoint", "all_step_mean", "month_endpoint_mean"):
            _same_tensor(bundle_aoi[statistic], selected_state[statistic], f"{aoi_key}.{statistic}")

    gate_pass = all(per_aoi_pass.values())
    _require(report["gate_pass"] is gate_pass, "report global gate_pass differs")
    _require(bundle["gate_pass"] is gate_pass, "bundle global gate_pass differs")
    _require(report["status"] == ("PASS" if gate_pass else "FAIL"), "report status differs")
    failure_kind = "combined_gate_not_passed" if closure_enabled else "target_gate_not_passed"
    expected_failures = [] if gate_pass else [
        f"{aoi}:{failure_kind}" for aoi, passed in per_aoi_pass.items() if not passed
    ]
    _require(report["failure_reasons"] == expected_failures, "global failure reasons differ")
    return {
        "verified": True,
        "science_status": report["status"],
        "gate_pass": gate_pass,
        "aois": list(report_aois),
        "verified_cycles": verified_cycles,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument(
        "--nonproduction",
        action="store_true",
        help="verify structure but do not require the frozen 3-AOI/native-step production config",
    )
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
        artifact = report["bundle_artifact"]
        _require(args.bundle.stat().st_size == artifact["bytes"], "bundle byte size differs")
        bundle_sha256 = _sha256(args.bundle)
        _require(bundle_sha256 == artifact["sha256"], "bundle SHA-256 differs")
        bundle = torch.load(args.bundle, map_location="cpu", weights_only=True)
        result = verify(report, bundle, production=not args.nonproduction)
    except (OSError, ValueError, KeyError, TypeError, VerificationError) as exc:
        print(f"TARGET GATE VERIFICATION FAILED: {exc}")
        return 1
    if args.receipt is not None:
        receipt = {
            **result,
            "verified_utc": datetime.now(UTC).isoformat(),
            "report": str(args.report),
            "report_sha256": _sha256(args.report),
            "bundle": str(args.bundle),
            "bundle_sha256": bundle_sha256,
            "production_contract": not args.nonproduction,
        }
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_text(
            json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
    print(
        f"VERIFIED target gate: science_status={result['science_status']} "
        f"aois={','.join(result['aois'])} cycles={result['verified_cycles']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
