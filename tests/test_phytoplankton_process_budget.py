from __future__ import annotations

import torch

from darwindiff import carroll6_5pft_2layer as layer2
from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.seasonal_twin import (
    integrate_seasonal_restored_process_budgets as layer2_process_integrator,
)
from darwindiff.seasonal_twin import (
    integrate_seasonal_restored_summary as restored_summary_integrator,
)


def test_process_rates_reproduce_production_step_phyto_exactly(monkeypatch) -> None:
    monkeypatch.setattr(layer2, "USE_EPPLEY_T", True)
    generator = torch.Generator().manual_seed(90210)
    state = 0.05 + torch.rand((15, 3, 4), generator=generator)
    state[layer2.I_DIC_1] += 2000.0
    state[layer2.I_ALK_1] += 2300.0
    state[layer2.I_DIC_2] += 2100.0
    state[layer2.I_ALK_2] += 2350.0
    params = torch.as_tensor(CARROLL_VALUES, dtype=state.dtype).clone()
    temperature = 2.0 + 24.0 * torch.rand((3, 4), generator=generator)
    light = 0.1 + 1.8 * torch.rand((3, 4), generator=generator)
    dt = 0.25

    rates = layer2.phytoplankton_process_rates(state, params, temperature, light)
    next_state = layer2.carroll6_5pft_2layer_step(
        state,
        params,
        dt,
        temperature,
        light=light,
    )
    indices = list(layer2.PHYTOPLANKTON_STATE_INDICES)
    diagnosed_next = (state[indices] + dt * rates["net"]).clamp(min=0.0)

    assert torch.equal(diagnosed_next, next_state[indices])
    assert torch.equal(
        rates["loss"],
        rates["linear_mortality"]
        + rates["quadratic_mortality"]
        + rates["grazing"],
    )
    expected_invasion_rate = (
        layer2.MU_DEFAULT_DIATOM
        * rates["f_fe"]
        * rates["light"]
        * rates["gamma_t"]
        - layer2.M_LIN
        - params[layer2.I_DIATOMGRAZ] * layer2.G0_GRAZE
    )
    assert torch.equal(rates["diatom_low_density_rate"], expected_invasion_rate)
    drivers = torch.stack([rates["f_fe"], rates["gamma_t"], rates["light"]])
    assert torch.isfinite(drivers).all()


def test_integrated_process_budgets_match_production_integrator(monkeypatch) -> None:
    monkeypatch.setattr(layer2, "USE_EPPLEY_T", True)
    generator = torch.Generator().manual_seed(1031)
    state0 = 0.1 + torch.rand((15, 2, 3), generator=generator)
    state0[layer2.I_DIC_1] += 2000.0
    state0[layer2.I_ALK_1] += 2300.0
    state0[layer2.I_DIC_2] += 2100.0
    state0[layer2.I_ALK_2] += 2350.0
    params = torch.as_tensor(CARROLL_VALUES, dtype=state0.dtype).clone()
    temperature = 8.0 + torch.rand((12, 2, 3), generator=generator)
    salinity = 34.0 + torch.rand((12, 2, 3), generator=generator)
    wind = 5.0 + torch.rand((12, 2, 3), generator=generator)
    light = 0.5 + torch.rand((12, 2, 3), generator=generator)
    mask = torch.ones((2, 3), dtype=torch.bool)

    final_state, budgets = layer2_process_integrator(
        state0,
        params,
        0.25,
        temperature,
        salinity,
        wind,
        state0,
        restoring_spatial_mask=mask,
        steps_per_month=2,
        n_cycles=2,
        budget_cycles=(1, 2),
        light_monthly=light,
    )

    reference_state = state0
    for cycle in (1, 2):
        month_ends, all_step_mean, _ = restored_summary_integrator(
            reference_state,
            params,
            0.25,
            temperature,
            salinity,
            wind,
            state0,
            restoring_spatial_mask=mask,
            steps_per_month=2,
            light_monthly=light,
        )
        reference_state = month_ends[-1]
        budget = budgets[cycle]
        assert torch.equal(budget["month_ends"], month_ends)
        assert torch.equal(budget["all_step_mean"], all_step_mean)

        expected_net = (
            budget["growth"]
            - budget["linear_mortality"]
            - budget["quadratic_mortality"]
            - budget["grazing"]
        )
        torch.testing.assert_close(budget["net"], expected_net, rtol=2e-6, atol=1e-7)
        torch.testing.assert_close(
            budget["actual_increment"],
            budget["net"] + budget["clamp_correction"],
            rtol=1e-5,
            atol=5e-6,
        )
        torch.testing.assert_close(
            budget["final_phyto"] - budget["initial_phyto"],
            budget["actual_increment"],
            rtol=1e-5,
            atol=5e-6,
        )
        assert torch.count_nonzero(budget["closure_abs"]) == 0
        assert float(budget["clamp_correction"].min()) >= -1e-7

    assert torch.equal(final_state, reference_state)
