from __future__ import annotations

import pytest
import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES, G0_GRAZE
from darwindiff.explicit_zooplankton import (
    CHEMICAL_RESTORING_INDICES,
    I_Z_LARGE,
    I_Z_SMALL,
    PLANKTON_STATE_INDICES,
    SOURCE_PHYGRAZ_MIN_C,
    darwin1_explicit_grazing_rates,
    explicit_zooplankton_step,
    initialize_zooplankton,
    integrate_explicit_zooplankton_restored_cycle,
)


def _base_state(*shape: int) -> torch.Tensor:
    values = torch.tensor(
        (
            5.0e-4,
            0.4,
            0.3,
            0.02,
            0.001,
            0.65,
            0.5,
            0.025,
            2050.0 * 1.025,
            2350.0 * 1.025,
            5.0e-4,
            0.05,
            0.003,
            2150.0 * 1.025,
            2400.0 * 1.025,
        ),
        dtype=torch.float64,
    )
    return values.reshape(15, *([1] * len(shape))).expand(15, *shape).clone()


def _params(*shape: int) -> torch.Tensor:
    return CARROLL_VALUES.to(torch.float64).reshape(6, *([1] * len(shape))).expand(
        6, *shape
    )


def test_grazing_fluxes_partition_prey_carbon_exactly() -> None:
    state = initialize_zooplankton(_base_state(2, 3), 0.1)
    rates = darwin1_explicit_grazing_rates(state, _params(2, 3))

    torch.testing.assert_close(
        rates["grazing_by_prey_predator"].sum(dim=0),
        rates["predator_ingestion"],
        rtol=1e-14,
        atol=1e-14,
    )
    torch.testing.assert_close(
        rates["prey_loss"].sum(dim=0),
        rates["zoo_gain"].sum(dim=0) + rates["unassimilated_to_poc"],
        rtol=1e-14,
        atol=1e-14,
    )
    torch.testing.assert_close(
        rates["zoo_gain"],
        state[[I_Z_SMALL, I_Z_LARGE]] * rates["zoo_specific_gain"],
        rtol=1e-14,
        atol=1e-14,
    )
    torch.testing.assert_close(
        rates["zoo_specific_gain_by_prey"].sum(dim=0),
        rates["zoo_specific_gain"],
        rtol=1e-14,
        atol=1e-14,
    )
    torch.testing.assert_close(
        rates["prey_allocation"].sum(dim=0),
        torch.ones_like(rates["predator_specific_ingestion"]),
        rtol=1e-14,
        atol=1e-14,
    )


def test_zero_source_floor_is_bitwise_legacy() -> None:
    state = initialize_zooplankton(_base_state(2, 3), 0.1)
    params = _params(2, 3)
    legacy = darwin1_explicit_grazing_rates(state, params)
    explicit_zero = darwin1_explicit_grazing_rates(
        state,
        params,
        source_prey_floor_c=0.0,
    )

    assert legacy.keys() == explicit_zero.keys()
    for key in legacy:
        assert torch.equal(legacy[key], explicit_zero[key]), key


def test_source_floor_reproduces_darwin_tmpz_response() -> None:
    state = initialize_zooplankton(_base_state(), 0.1)
    state[list(layer2.PHYTOPLANKTON_STATE_INDICES)] = 0.0
    state[layer2.I_DIATOM] = 4.0 * SOURCE_PHYGRAZ_MIN_C
    params = _params()

    rates = darwin1_explicit_grazing_rates(
        state,
        params,
        source_prey_floor_c=SOURCE_PHYGRAZ_MIN_C,
    )
    prey_pool = rates["prey_pool"]
    responsive_pool = (prey_pool - SOURCE_PHYGRAZ_MIN_C).clamp(min=0.0)
    expected = 0.625 * responsive_pool / (responsive_pool + 10.2)

    torch.testing.assert_close(
        rates["predator_specific_ingestion"],
        expected,
        rtol=0.0,
        atol=0.0,
    )
    assert rates["predator_specific_ingestion"][0] == 0.0
    assert rates["predator_specific_ingestion"][1] > 0.0


def test_diatomgraz_changes_only_diatom_palatability_entries() -> None:
    state = initialize_zooplankton(_base_state(), 0.1)
    low = _params().clone()
    high = _params().clone()
    low[layer2.I_DIATOMGRAZ] *= 0.9
    high[layer2.I_DIATOMGRAZ] *= 1.1

    low_palat = darwin1_explicit_grazing_rates(state, low)["palatability"]
    high_palat = darwin1_explicit_grazing_rates(state, high)["palatability"]
    torch.testing.assert_close(high_palat[1:], low_palat[1:], rtol=0.0, atol=0.0)
    torch.testing.assert_close(
        high_palat[0] / low_palat[0],
        torch.full_like(high_palat[0], 1.1 / 0.9),
        rtol=1e-14,
        atol=1e-14,
    )


def test_zero_grazers_remove_legacy_linear_grazing(monkeypatch) -> None:
    monkeypatch.setattr(layer2, "USE_COCCOLITH_ONLY_CALCITE", False)
    monkeypatch.setattr(layer2, "USE_ENV_RAIN_RATIO", False)
    base = _base_state()
    state = torch.cat((base, torch.zeros(2, dtype=base.dtype)))
    params = _params()
    dt = 0.01

    legacy = layer2.carroll6_5pft_2layer_step(base, params, dt)
    explicit = explicit_zooplankton_step(state, params, dt)
    old_grazing = params[layer2.I_DIATOMGRAZ] * G0_GRAZE * base[layer2.I_DIATOM]
    calcite = params[layer2.I_R_PICPOC] * old_grazing

    torch.testing.assert_close(
        explicit[layer2.I_DIATOM],
        legacy[layer2.I_DIATOM] + dt * old_grazing,
    )
    torch.testing.assert_close(
        explicit[layer2.I_POC_1], legacy[layer2.I_POC_1] - dt * old_grazing
    )
    torch.testing.assert_close(
        explicit[layer2.I_PIC_1], legacy[layer2.I_PIC_1] - dt * calcite
    )
    torch.testing.assert_close(
        explicit[layer2.I_DIC_1], legacy[layer2.I_DIC_1] + dt * calcite
    )
    torch.testing.assert_close(
        explicit[layer2.I_ALK_1], legacy[layer2.I_ALK_1] + 2.0 * dt * calcite
    )
    assert torch.count_nonzero(explicit[[I_Z_SMALL, I_Z_LARGE]]) == 0


def test_step_preserves_organic_carbon_relative_to_legacy_internal_transfer(
    monkeypatch,
) -> None:
    monkeypatch.setattr(layer2, "USE_COCCOLITH_ONLY_CALCITE", False)
    monkeypatch.setattr(layer2, "USE_ENV_RAIN_RATIO", False)
    base = _base_state(2)
    state = initialize_zooplankton(base, 0.1)
    params = _params(2)
    dt = 0.01

    legacy = layer2.carroll6_5pft_2layer_step(base, params, dt)
    explicit = explicit_zooplankton_step(state, params, dt)
    legacy_delta = (
        legacy[list(layer2.PHYTOPLANKTON_STATE_INDICES)].sum(dim=0)
        + legacy[layer2.I_POC_1]
        - base[list(layer2.PHYTOPLANKTON_STATE_INDICES)].sum(dim=0)
        - base[layer2.I_POC_1]
    )
    explicit_delta = (
        explicit[list(PLANKTON_STATE_INDICES)].sum(dim=0)
        + explicit[layer2.I_POC_1]
        - state[list(PLANKTON_STATE_INDICES)].sum(dim=0)
        - state[layer2.I_POC_1]
    )
    torch.testing.assert_close(explicit_delta, legacy_delta, rtol=1e-11, atol=1e-12)


def test_restoring_cycle_never_nudges_plankton(monkeypatch) -> None:
    monkeypatch.setattr(layer2, "USE_COCCOLITH_ONLY_CALCITE", False)
    monkeypatch.setattr(layer2, "USE_ENV_RAIN_RATIO", False)
    state = initialize_zooplankton(_base_state(2), 0.1)
    params = _params(2)
    forcing = torch.full((12, 2), 15.0, dtype=state.dtype)
    salinity = torch.full((12, 2), 35.0, dtype=state.dtype)
    wind = torch.full((12, 2), 7.0, dtype=state.dtype)

    _, _, budget = integrate_explicit_zooplankton_restored_cycle(
        state,
        params,
        0.01,
        forcing,
        salinity,
        wind,
        state.clone(),
        restoring_indices=CHEMICAL_RESTORING_INDICES,
        restoring_spatial_mask=torch.ones(2, dtype=torch.bool),
        steps_per_month=1,
    )

    assert torch.count_nonzero(budget["closure_abs"][list(PLANKTON_STATE_INDICES)]) == 0
    assert int(budget["step_count"]) == 12


def test_restoring_cycle_propagates_literal_source_floor() -> None:
    state = initialize_zooplankton(_base_state(2), 0.1)
    params = _params(2)
    forcing = torch.full((12, 2), 15.0, dtype=state.dtype)
    salinity = torch.full((12, 2), 35.0, dtype=state.dtype)
    wind = torch.full((12, 2), 7.0, dtype=state.dtype)
    observed_floors = []

    def recording_step(*args):
        observed_floors.append(args[-1])
        return args[0]

    integrate_explicit_zooplankton_restored_cycle(
        state,
        params,
        0.01,
        forcing,
        salinity,
        wind,
        state.clone(),
        steps_per_month=1,
        step_fn=recording_step,
        source_prey_floor_c=SOURCE_PHYGRAZ_MIN_C,
    )

    assert observed_floors == [SOURCE_PHYGRAZ_MIN_C] * 12


@pytest.mark.parametrize("source_prey_floor_c", [-1.0, float("nan"), float("inf")])
def test_restoring_cycle_rejects_invalid_source_floor(source_prey_floor_c: float) -> None:
    state = initialize_zooplankton(_base_state(), 0.1)
    forcing = torch.full((12,), 15.0, dtype=state.dtype)

    with pytest.raises(ValueError, match="source_prey_floor_c"):
        integrate_explicit_zooplankton_restored_cycle(
            state,
            _params(),
            0.01,
            forcing,
            torch.full_like(forcing, 35.0),
            torch.full_like(forcing, 7.0),
            state.clone(),
            steps_per_month=1,
            source_prey_floor_c=source_prey_floor_c,
        )
