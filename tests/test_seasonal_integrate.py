"""Tests for the transient seasonal integrator (carroll6_5pft_2layer_integrate_seasonal).

The load-bearing correctness check is `test_constant_forcing_reduces_to_plain_integrate`:
with identical forcing every month and no spin-up, the seasonal loop must produce
exactly what the existing single-block integrator produces over the same number of
steps — i.e. the only new behaviour is *month-varying forcing + monthly snapshots*,
not a change to the per-step physics.
"""

from __future__ import annotations

import pytest
import torch

from darwindiff.carroll6_5pft_2layer import (
    DAYS_PER_MONTH,
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_integrate_seasonal,
    carroll6_5pft_2layer_integrate_seasonal_summary,
)
from darwindiff.seasonal import constant_state0
from darwindiff.seasonal_twin import astronomical_monthly_light

DT = 0.25

# alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC
_PARAMS = (0.02, 1.0e-6, 1.0, 1.0, 1.0, 0.5)


def _params(spatial: tuple[int, ...] = ()) -> torch.Tensor:
    vals = torch.tensor(_PARAMS)
    if not spatial:
        return vals
    base = vals.reshape(6, *([1] * len(spatial)))
    return base.expand(6, *spatial).contiguous()


def _const_forcing(t: float = 18.0, s: float = 35.0, w: float = 7.0):
    return torch.full((12,), t), torch.full((12,), s), torch.full((12,), w)


def test_constant_forcing_reduces_to_plain_integrate():
    state0, params = constant_state0(), _params()
    spm = 3
    t_m, s_m, w_m = _const_forcing()
    snaps = carroll6_5pft_2layer_integrate_seasonal(
        state0, params, DT, t_m, s_m, w_m, steps_per_month=spm, n_spinup_cycles=0
    )
    plain = carroll6_5pft_2layer_integrate(
        state0, params, DT, 12 * spm, T=t_m[0], S=s_m[0], wind=w_m[0]
    )
    assert snaps.shape == (12, N_TRACERS_2LAYER)
    # Last month-end == plain integrate over the same total steps (same physics).
    assert torch.allclose(snaps[-1], plain)


def test_returns_twelve_monthly_snapshots_spatial():
    n_cells = 8
    snaps = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0((1, n_cells)), _params((1, n_cells)), DT,
        torch.full((12, 1, n_cells), 18.0),
        torch.full((12, 1, n_cells), 35.0),
        torch.full((12, 1, n_cells), 7.0),
        steps_per_month=2,
    )
    assert snaps.shape == (12, N_TRACERS_2LAYER, 1, n_cells)


def test_varying_forcing_gives_month_to_month_variation():
    # A seasonal SST swing changes the carbonate state month to month, so the 12
    # snapshots must not be identical (the whole point of seasonal fitting).
    t_m = torch.linspace(5.0, 25.0, 12)
    snaps = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0(), _params(), DT, t_m, torch.full((12,), 35.0), torch.full((12,), 7.0),
        steps_per_month=3,
    )
    assert snaps.std(dim=0).abs().sum() > 0


def test_gradient_flows_to_params():
    params = _params().clone().requires_grad_(True)
    t_m, s_m, w_m = _const_forcing()
    snaps = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0(), params, DT, t_m, s_m, w_m, steps_per_month=3
    )
    snaps.pow(2).mean().backward()
    assert params.grad is not None
    assert torch.isfinite(params.grad).all()
    assert params.grad.abs().sum() > 0


def test_spinup_changes_the_recorded_year():
    t_m = torch.linspace(5.0, 25.0, 12)
    s_m, w_m = torch.full((12,), 35.0), torch.full((12,), 7.0)
    no_spin = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=0
    )
    one_spin = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=1
    )
    assert no_spin.shape == one_spin.shape == (12, N_TRACERS_2LAYER)
    assert not torch.allclose(no_spin, one_spin)


def test_summary_preserves_existing_month_ends_exactly():
    state0, params = constant_state0(), _params()
    t_m = torch.linspace(5.0, 25.0, 12)
    s_m, w_m = torch.full((12,), 35.0), torch.full((12,), 7.0)
    existing = carroll6_5pft_2layer_integrate_seasonal(
        state0, params, DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=1
    )
    month_ends, _ = carroll6_5pft_2layer_integrate_seasonal_summary(
        state0, params, DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=1
    )
    assert torch.equal(month_ends, existing)


def test_explicit_unity_light_preserves_default_path_bitwise():
    state0, params = constant_state0(), _params()
    t_m, s_m, w_m = _const_forcing()
    default_ends, default_mean = carroll6_5pft_2layer_integrate_seasonal_summary(
        state0, params, DT, t_m, s_m, w_m, steps_per_month=3
    )
    light_ends, light_mean = carroll6_5pft_2layer_integrate_seasonal_summary(
        state0,
        params,
        DT,
        t_m,
        s_m,
        w_m,
        steps_per_month=3,
        light_monthly=torch.ones(12),
    )
    assert torch.equal(light_ends, default_ends)
    assert torch.equal(light_mean, default_mean)


def test_gradient_flows_to_params_with_astronomical_light():
    spatial = (1, 3)
    params = _params(spatial).clone().requires_grad_(True)
    forcing = torch.ones(12, *spatial)
    light = astronomical_monthly_light(torch.tensor([[-45.0, 0.0, 45.0]]))
    month_ends = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0(spatial),
        params,
        DT,
        forcing * 18.0,
        forcing * 35.0,
        forcing * 7.0,
        steps_per_month=2,
        light_monthly=light,
    )
    month_ends.pow(2).mean().backward()
    assert params.grad is not None
    assert torch.isfinite(params.grad).all()
    assert params.grad.abs().sum() > 0


def test_summary_with_one_step_per_month_equals_month_end_mean():
    t_m, s_m, w_m = _const_forcing()
    month_ends, all_step_mean = carroll6_5pft_2layer_integrate_seasonal_summary(
        constant_state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=1
    )
    assert torch.allclose(all_step_mean, month_ends.mean(dim=0), rtol=5e-7, atol=1e-7)


def test_summary_mean_contains_every_post_step_state():
    state0, params = constant_state0(), _params()
    spm = 3
    t_m, s_m, w_m = _const_forcing()
    _, all_step_mean = carroll6_5pft_2layer_integrate_seasonal_summary(
        state0, params, DT, t_m, s_m, w_m, steps_per_month=spm
    )
    every_step = carroll6_5pft_2layer_integrate(
        state0,
        params,
        DT,
        12 * spm,
        snapshot_indices=list(range(1, 12 * spm + 1)),
        T=t_m[0],
        S=s_m[0],
        wind=w_m[0],
    )
    assert torch.allclose(all_step_mean, every_step.mean(dim=0), rtol=5e-7, atol=1e-7)


def test_summary_mean_excludes_initial_state_and_spinup_cycles():
    state0, params = constant_state0(), _params()
    spm = 2
    steps_per_cycle = 12 * spm
    t_m, s_m, w_m = _const_forcing()
    _, all_step_mean = carroll6_5pft_2layer_integrate_seasonal_summary(
        state0, params, DT, t_m, s_m, w_m,
        steps_per_month=spm, n_spinup_cycles=1,
    )
    every_step = carroll6_5pft_2layer_integrate(
        state0,
        params,
        DT,
        2 * steps_per_cycle,
        snapshot_indices=list(range(1, 2 * steps_per_cycle + 1)),
        T=t_m[0],
        S=s_m[0],
        wind=w_m[0],
    )
    expected = every_step[steps_per_cycle:].mean(dim=0)
    assert torch.allclose(all_step_mean, expected, rtol=5e-7, atol=1e-7)
    assert not torch.equal(all_step_mean, every_step.mean(dim=0))


def test_param_bound_extremes_stay_nonnegative_under_spinup():
    # Regression (pre-scale-up audit 2026-06-18): at the upper PARAM_BOUNDS the
    # surface carbonate budget (dDIC_1 / dALK_1 have no analytic floor) used to run
    # away monotonically negative under multi-cycle seasonal spin-up -- e.g. DIC_1
    # reached -2.3e4 by 8 cycles -- while staying torch.isfinite, so an
    # isfinite-only assert missed it and it could NaN the loss at native
    # resolution. The non-negativity floor in carroll6_5pft_2layer_step must keep
    # every tracer >= 0 regardless of params or spin-up depth.
    from darwindiff.carroll6 import PARAM_BOUNDS

    pmax = PARAM_BOUNDS[:, 1].clone()
    t_m = torch.linspace(5.0, 28.0, 12)
    s_m, w_m = torch.full((12,), 35.0), torch.full((12,), 7.0)
    for spin in (0, 3):
        snaps = carroll6_5pft_2layer_integrate_seasonal(
            constant_state0(), pmax, DT, t_m, s_m, w_m, steps_per_month=122, n_spinup_cycles=spin
        )
        assert torch.isfinite(snaps).all()
        assert float(snaps.min()) >= 0.0, f"negative tracer at spin={spin}: {float(snaps.min())}"


def test_deterministic():
    args = (constant_state0(), _params(), DT, *_const_forcing())
    a = carroll6_5pft_2layer_integrate_seasonal(*args, steps_per_month=3)
    b = carroll6_5pft_2layer_integrate_seasonal(*args, steps_per_month=3)
    assert torch.equal(a, b)


def test_default_steps_per_month_is_about_122():
    assert round(DAYS_PER_MONTH / 0.25) == 122


@pytest.mark.parametrize("bad_len", [0, 11, 13])
def test_forcing_must_have_length_12_month_axis(bad_len):
    good = torch.full((12,), 35.0)
    with pytest.raises(ValueError, match="length-12"):
        carroll6_5pft_2layer_integrate_seasonal(
            constant_state0(), _params(), DT, torch.full((bad_len,), 18.0), good, good
        )


def test_steps_per_month_must_be_positive():
    t_m, s_m, w_m = _const_forcing()
    with pytest.raises(ValueError, match="steps_per_month"):
        carroll6_5pft_2layer_integrate_seasonal(
            constant_state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=0
        )


def test_light_must_have_length_12_month_axis():
    t_m, s_m, w_m = _const_forcing()
    with pytest.raises(ValueError, match=r"light_monthly.*length-12"):
        carroll6_5pft_2layer_integrate_seasonal(
            constant_state0(),
            _params(),
            DT,
            t_m,
            s_m,
            w_m,
            light_monthly=torch.ones(11),
        )
