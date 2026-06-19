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
)

DT = 0.25

# Plausible-magnitude initial state (per the module's 15-tracer layout).
_STATE0 = (0.5, 0.1, 0.1, 0.1, 0.1, 0.1, 1.0, 0.1, 2000.0, 2300.0,
           0.6, 0.5, 0.05, 2100.0, 2350.0)
# alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC
_PARAMS = (0.02, 1.0e-6, 1.0, 1.0, 1.0, 0.5)


def _state0(spatial: tuple[int, ...] = ()) -> torch.Tensor:
    vals = torch.tensor(_STATE0)
    if not spatial:
        return vals
    base = vals.reshape(N_TRACERS_2LAYER, *([1] * len(spatial)))
    return base.expand(N_TRACERS_2LAYER, *spatial).contiguous()


def _params(spatial: tuple[int, ...] = ()) -> torch.Tensor:
    vals = torch.tensor(_PARAMS)
    if not spatial:
        return vals
    base = vals.reshape(6, *([1] * len(spatial)))
    return base.expand(6, *spatial).contiguous()


def _const_forcing(t: float = 18.0, s: float = 35.0, w: float = 7.0):
    return torch.full((12,), t), torch.full((12,), s), torch.full((12,), w)


def test_constant_forcing_reduces_to_plain_integrate():
    state0, params = _state0(), _params()
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
        _state0((1, n_cells)), _params((1, n_cells)), DT,
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
        _state0(), _params(), DT, t_m, torch.full((12,), 35.0), torch.full((12,), 7.0),
        steps_per_month=3,
    )
    assert snaps.std(dim=0).abs().sum() > 0


def test_gradient_flows_to_params():
    params = _params().clone().requires_grad_(True)
    t_m, s_m, w_m = _const_forcing()
    snaps = carroll6_5pft_2layer_integrate_seasonal(
        _state0(), params, DT, t_m, s_m, w_m, steps_per_month=3
    )
    snaps.pow(2).mean().backward()
    assert params.grad is not None
    assert torch.isfinite(params.grad).all()
    assert params.grad.abs().sum() > 0


def test_spinup_changes_the_recorded_year():
    t_m = torch.linspace(5.0, 25.0, 12)
    s_m, w_m = torch.full((12,), 35.0), torch.full((12,), 7.0)
    no_spin = carroll6_5pft_2layer_integrate_seasonal(
        _state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=0
    )
    one_spin = carroll6_5pft_2layer_integrate_seasonal(
        _state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=3, n_spinup_cycles=1
    )
    assert no_spin.shape == one_spin.shape == (12, N_TRACERS_2LAYER)
    assert not torch.allclose(no_spin, one_spin)


def test_deterministic():
    args = (_state0(), _params(), DT, *_const_forcing())
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
            _state0(), _params(), DT, torch.full((bad_len,), 18.0), good, good
        )


def test_steps_per_month_must_be_positive():
    t_m, s_m, w_m = _const_forcing()
    with pytest.raises(ValueError, match="steps_per_month"):
        carroll6_5pft_2layer_integrate_seasonal(
            _state0(), _params(), DT, t_m, s_m, w_m, steps_per_month=0
        )
