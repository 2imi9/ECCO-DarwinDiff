from __future__ import annotations

import copy
import math

import pytest
import torch
from scripts.analysis.verify_seasonal_twin_target_gate import VerificationError, verify

from darwindiff.carroll6_5pft_2layer import I_DFE_2, I_DIATOM, N_TRACERS_2LAYER
from darwindiff.seasonal_twin import (
    ASTRONOMICAL_DECLINATION_PHASE_DAY,
    ASTRONOMICAL_OBLIQUITY_DEGREES,
    ASTRONOMICAL_RECONSTRUCTION_ATOL,
    ASTRONOMICAL_YEAR_DAYS,
    CHEMICAL_RESTORING_INDICES,
    MONTH_MIDPOINT_DAY_OF_YEAR,
    astronomical_monthly_light,
    evaluate_light_integrity,
    evaluate_restoring_budget,
    evaluate_target_cycle,
    integrate_seasonal_restored_summary,
    masked_relative_l2,
    relative_spatial_sd,
    summarize_target_state,
)


def _passing_state() -> tuple[torch.Tensor, torch.Tensor]:
    state = torch.ones(N_TRACERS_2LAYER, 1, 4)
    state[I_DFE_2, 0] = torch.tensor([1.0, 1.2, 1.4, 1.6])
    state[I_DIATOM, 0] = torch.tensor([1.0, 1.2, 1.4, 1.6])
    return state, torch.ones(1, 4, dtype=torch.bool)


def test_masked_relative_l2_uses_previous_cycle_denominator():
    previous = torch.tensor([1.0, 2.0, 100.0])
    current = torch.tensor([2.0, 2.0, -100.0])
    mask = torch.tensor([True, True, False])
    assert masked_relative_l2(current, previous, mask) == pytest.approx(1 / math.sqrt(5))


def test_relative_spatial_sd_is_sample_sd_over_absolute_mean():
    field = torch.tensor([1.0, 2.0, 3.0, 999.0])
    mask = torch.tensor([True, True, True, False])
    assert relative_spatial_sd(field, mask) == pytest.approx(0.5)


def test_target_cycle_passes_when_all_frozen_gates_pass():
    current, mask = _passing_state()
    result = evaluate_target_cycle(current.clone(), current, mask, "eqpac")
    assert result["pass"] is True
    assert result["failure_reasons"] == []
    assert all(result["checks"].values())


def test_target_cycle_reports_each_independent_failure():
    previous, mask = _passing_state()
    current = previous.clone()
    current[0] *= 1.1
    current[I_DFE_2] = 1.0
    current[I_DIATOM] = torch.tensor([[0.1, 0.1, 0.1, 10.0]])
    result = evaluate_target_cycle(previous, current, mask, "southernoceanpac")
    assert result["pass"] is False
    assert "cycle_field_stability" in result["failure_reasons"]
    assert "dfe2_contrast_stability" in result["failure_reasons"]
    assert "dfe2_contrast_retention" in result["failure_reasons"]
    assert "chl1_sanity" in result["failure_reasons"]


def test_target_cycle_rejects_unregistered_aoi():
    state, mask = _passing_state()
    with pytest.raises(KeyError, match="no preregistered"):
        evaluate_target_cycle(state, state, mask, "kerguelen")


def test_astronomical_light_is_mean_one_and_hemispherically_phased():
    latitude = torch.tensor([[-60.0, 0.0, 60.0]])
    light = astronomical_monthly_light(latitude)
    mask = torch.ones_like(latitude, dtype=torch.bool)
    integrity = evaluate_light_integrity(light, mask)
    assert light.shape == (12, 1, 3)
    assert integrity["pass"] is True
    assert torch.allclose(light.mean(dim=0), torch.ones_like(latitude), atol=1e-7)
    south_peak = int(light[:, 0, 0].argmax())
    north_peak = int(light[:, 0, 2].argmax())
    assert (north_peak - south_peak) % 12 == 6
    assert 0.0 < float(light[:, 0, 1].std()) < 0.05


def test_astronomical_light_rejects_invalid_latitude():
    with pytest.raises(ValueError, match=r"\[-90, 90\]"):
        astronomical_monthly_light(torch.tensor([91.0]))


def _synthetic_artifacts() -> tuple[dict, dict]:
    state, mask = _passing_state()
    summary = summarize_target_state(state, mask)
    gate = evaluate_target_cycle(state, state, mask, "eqpac")
    config = {"aois": ["eqpac"], "min_cycles": 2, "max_cycles": 2}
    report = {
        "schema_version": 2,
        "preregistration": "docs/findings/2026-08-09_prereg_seasonal_loss_self_twin.md",
        "relational_hypothesis": "hy_szn_loss",
        "config": config,
        "status": "PASS",
        "gate_pass": True,
        "failure_reasons": [],
        "aois": {
            "eqpac": {
                "n_ocean_cells": 4,
                "pass": True,
                "selected_cycle": 2,
                "cycles": [
                    {
                        "cycle": 1,
                        "endpoint": summary,
                        "all_step_mean": summary,
                        "month_endpoint_mean": summary,
                        "gate": None,
                    },
                    {
                        "cycle": 2,
                        "endpoint": summary,
                        "all_step_mean": summary,
                        "month_endpoint_mean": summary,
                        "gate": gate,
                    },
                ],
            }
        },
    }
    cycle_states = [
        {
            "cycle": cycle,
            "endpoint": state.clone(),
            "all_step_mean": state.clone(),
            "month_endpoint_mean": state.clone(),
        }
        for cycle in (1, 2)
    ]
    bundle = {
        "schema_version": 2,
        "preregistration": report["preregistration"],
        "relational_hypothesis": "hy_szn_loss",
        "config": config,
        "gate_pass": True,
        "aois": {
            "eqpac": {
                "pass": True,
                "selected_cycle": 2,
                "mask": mask,
                "cycles": cycle_states,
                "endpoint": state.clone(),
                "all_step_mean": state.clone(),
                "month_endpoint_mean": state.clone(),
            }
        },
    }
    return report, bundle


def test_artifact_verifier_round_trip_and_tamper_detection():
    report, bundle = _synthetic_artifacts()
    result = verify(report, bundle, production=False)
    assert result["verified"] is True
    assert result["gate_pass"] is True

    tampered = copy.deepcopy(report)
    tampered["aois"]["eqpac"]["cycles"][1]["all_step_mean"]["DFe2"]["mean"] += 0.1
    with pytest.raises(VerificationError, match="recomputed"):
        verify(tampered, bundle, production=False)


def _synthetic_light_artifacts() -> tuple[dict, dict]:
    report, bundle = _synthetic_artifacts()
    report["preregistration"] = (
        "docs/findings/2026-08-09_prereg_seasonal_twin_astronomical_light.md"
    )
    report["relational_hypothesis"] = "hy_szn_light"
    report["config"].update(
        {
            "monthly_light": True,
            "chemical_restoring_closure": {},
            "astronomical_monthly_light": {
                "construction": "daily_mean_top_of_atmosphere_insolation",
                "obliquity_degrees": ASTRONOMICAL_OBLIQUITY_DEGREES,
                "year_days": ASTRONOMICAL_YEAR_DAYS,
                "declination_phase_day": ASTRONOMICAL_DECLINATION_PHASE_DAY,
                "month_midpoint_day_of_year": list(MONTH_MIDPOINT_DAY_OF_YEAR),
                "normalization": "per_cell_12_month_arithmetic_mean",
                "fitted_parameters": False,
                "per_cell_mean_tolerance": 1e-6,
                "cross_device_reconstruction_atol": ASTRONOMICAL_RECONSTRUCTION_ATOL,
            },
        }
    )
    bundle["preregistration"] = report["preregistration"]
    bundle["relational_hypothesis"] = report["relational_hypothesis"]
    bundle["config"] = copy.deepcopy(report["config"])

    mask = bundle["aois"]["eqpac"]["mask"]
    latitude = torch.tensor([[-15.0, -5.0, 5.0, 15.0]])
    light = astronomical_monthly_light(latitude)
    light_gate = evaluate_light_integrity(light, mask)
    report["aois"]["eqpac"]["light_gate"] = light_gate
    bundle["aois"]["eqpac"]["latitude_degrees"] = latitude
    bundle["aois"]["eqpac"]["monthly_light"] = light

    budget = {
        name: torch.zeros(N_TRACERS_2LAYER, 1, 4)
        for name in ("closure_abs", "model_abs", "inventory_abs")
    }
    closure_gate = evaluate_restoring_budget(budget, mask)
    for report_cycle, state_cycle in zip(
        report["aois"]["eqpac"]["cycles"],
        bundle["aois"]["eqpac"]["cycles"],
        strict=True,
    ):
        report_cycle["closure_gate"] = closure_gate
        state_cycle["restoring_budget"] = copy.deepcopy(budget)
    return report, bundle


def test_artifact_verifier_reconstructs_and_rejects_tampered_light():
    report, bundle = _synthetic_light_artifacts()
    assert verify(report, bundle, production=False)["verified"] is True
    bundle["aois"]["eqpac"]["monthly_light"][0, 0, 0] += 0.01
    with pytest.raises(VerificationError, match="monthly_light"):
        verify(report, bundle, production=False)


def _identity_step(state, *_args):
    return state


def test_restoring_integrator_matches_closed_form_and_never_nudges_phyto():
    state0 = torch.zeros(N_TRACERS_2LAYER, 1, 2)
    reference = torch.ones_like(state0)
    forcing = torch.ones(12, 1, 2)
    month_ends, all_step_mean, budget = integrate_seasonal_restored_summary(
        state0,
        torch.ones(6, 1, 2),
        1.0,
        forcing,
        forcing,
        forcing,
        reference,
        restoring_timescale_days=2.0,
        restoring_spatial_mask=torch.ones(1, 2, dtype=torch.bool),
        steps_per_month=1,
        step_fn=_identity_step,
    )
    expected = torch.tensor([1.0 - 0.5**step for step in range(1, 13)])
    assert torch.allclose(month_ends[:, 0, 0, 0], expected)
    assert all_step_mean[0, 0, 0] == pytest.approx(float(expected.mean()))
    assert budget["closure_abs"][0, 0, 0] == pytest.approx(float(expected[-1]))
    assert torch.count_nonzero(budget["model_abs"]) == 0
    assert torch.count_nonzero(month_ends[:, I_DIATOM]) == 0
    assert torch.count_nonzero(budget["closure_abs"][I_DIATOM]) == 0


def test_restoring_budget_excludes_spinup_cycle():
    state0 = torch.zeros(N_TRACERS_2LAYER, 1, 1)
    reference = torch.ones_like(state0)
    forcing = torch.ones(12, 1, 1)
    _, _, budget = integrate_seasonal_restored_summary(
        state0,
        torch.ones(6, 1, 1),
        1.0,
        forcing,
        forcing,
        forcing,
        reference,
        restoring_timescale_days=2.0,
        steps_per_month=1,
        n_spinup_cycles=1,
        step_fn=_identity_step,
    )
    expected_recorded_closure = (1.0 - 0.5**24) - (1.0 - 0.5**12)
    assert budget["closure_abs"][0, 0, 0] == pytest.approx(expected_recorded_closure)


def test_restoring_budget_gate_enforces_dominance_and_exact_phyto_zero():
    shape = (N_TRACERS_2LAYER, 1, 2)
    closure = torch.zeros(shape)
    model = torch.ones(shape)
    inventory = torch.ones(shape) * 4.0
    closure[list(CHEMICAL_RESTORING_INDICES)] = 1.0
    mask = torch.ones(1, 2, dtype=torch.bool)
    passing = evaluate_restoring_budget(
        {"closure_abs": closure, "model_abs": model, "inventory_abs": inventory}, mask
    )
    assert passing["pass"] is True
    assert passing["phytoplankton_closure_exactly_zero"] is True

    closure[I_DIATOM] = 0.1
    failing = evaluate_restoring_budget(
        {"closure_abs": closure, "model_abs": model, "inventory_abs": inventory}, mask
    )
    assert failing["pass"] is False
    assert "Chl1_diatom:unexpected_closure" in failing["failure_reasons"]
