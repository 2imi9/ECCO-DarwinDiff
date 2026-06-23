"""Batched (multi-seed) seasonal path == sequential, the correctness contract for #115.

The seasonal runner trains one seed per process today; #115 wants N seeds in one
torch.compile'd graph. That is only sound if (a) the box integrator carries a leading
seed axis without letting seeds interact, and (b) the loss z-scores each seed over the
ocean mask with its OWN stats. These tests pin both on CPU with no real data.
"""
from __future__ import annotations

import torch

from darwindiff.carroll6 import PARAM_BOUNDS, bounded_params
from darwindiff.carroll6_5pft_2layer import (
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate_seasonal,
)
from darwindiff.seasonal import (
    constant_state0,
    seasonal_chl_loss,
    seasonal_chl_loss_batched,
    timemean_chl_loss,
    timemean_chl_loss_batched,
)

S, H, W = 3, 2, 3
DT = 0.25


def _mask() -> torch.Tensor:
    m = torch.ones(H, W, dtype=torch.bool)
    m[0, 0] = False  # at least one land cell, so the mask actually selects
    return m


def test_seasonal_loss_batched_equals_sequential() -> None:
    torch.manual_seed(0)
    mask = _mask()
    snaps = torch.rand(12, N_TRACERS_2LAYER, S, H, W)
    chl_z = torch.randn(12, 5, H, W)
    batched = seasonal_chl_loss_batched(snaps, chl_z, mask)  # [S]
    seq = torch.stack([seasonal_chl_loss(snaps[:, :, s], chl_z, mask) for s in range(S)])
    assert batched.shape == (S,)
    assert torch.allclose(batched, seq, atol=1e-6), (batched, seq)


def test_timemean_loss_batched_equals_sequential() -> None:
    torch.manual_seed(1)
    mask = _mask()
    state = torch.rand(N_TRACERS_2LAYER, S, H, W)
    chl_z = torch.randn(12, 5, H, W)
    batched = timemean_chl_loss_batched(state, chl_z, mask)
    seq = torch.stack([timemean_chl_loss(state[:, s], chl_z, mask) for s in range(S)])
    assert batched.shape == (S,)
    assert torch.allclose(batched, seq, atol=1e-6), (batched, seq)


def test_integrator_seed_batch_is_independent() -> None:
    """Folding S seeds into the spatial dims must give the SAME per-seed result as
    integrating each seed alone -- the prerequisite for one-graph multi-seed training.
    """
    torch.manual_seed(2)
    T = 15.0 + torch.randn(12, H, W)
    Sal = 35.0 + 0.1 * torch.randn(12, H, W)
    wind = 5.0 + torch.rand(12, H, W)
    params = bounded_params(torch.randn(6, S, H, W), PARAM_BOUNDS)  # [6, S, H, W]

    snaps_batched = carroll6_5pft_2layer_integrate_seasonal(
        constant_state0((S, H, W)), params, DT, T, Sal, wind, steps_per_month=2,
    )  # [12, 15, S, H, W]
    assert snaps_batched.shape == (12, N_TRACERS_2LAYER, S, H, W)

    for s in range(S):
        snaps_s = carroll6_5pft_2layer_integrate_seasonal(
            constant_state0((H, W)), params[:, s], DT, T, Sal, wind, steps_per_month=2,
        )
        assert torch.allclose(snaps_batched[:, :, s], snaps_s, atol=1e-5), s


def test_step_fn_injection_is_bit_identical() -> None:
    """Injecting ``step_fn=<the module step>`` must reproduce the default path exactly.

    This is the contract that lets the batched/compiled runner thread a
    ``torch.compile``'d per-step through the integrators (#115/#119): a custom
    ``step_fn`` only swaps the kernel, never the numerics.
    """
    from darwindiff.carroll6_5pft_2layer import (
        carroll6_5pft_2layer_integrate,
        carroll6_5pft_2layer_step,
    )

    torch.manual_seed(3)
    T = 15.0 + torch.randn(12, H, W)
    Sal = 35.0 + 0.1 * torch.randn(12, H, W)
    wind = 5.0 + torch.rand(12, H, W)
    params = bounded_params(torch.randn(6, S, H, W), PARAM_BOUNDS)
    st0 = constant_state0((S, H, W))

    seasonal_default = carroll6_5pft_2layer_integrate_seasonal(
        st0, params, DT, T, Sal, wind, steps_per_month=2,
    )
    seasonal_injected = carroll6_5pft_2layer_integrate_seasonal(
        st0, params, DT, T, Sal, wind, steps_per_month=2, step_fn=carroll6_5pft_2layer_step,
    )
    assert torch.equal(seasonal_default, seasonal_injected)

    tm_default = carroll6_5pft_2layer_integrate(st0, params, DT, 5, T=T[0], S=Sal[0], wind=wind[0])
    tm_injected = carroll6_5pft_2layer_integrate(
        st0, params, DT, 5, T=T[0], S=Sal[0], wind=wind[0], step_fn=carroll6_5pft_2layer_step,
    )
    assert torch.equal(tm_default, tm_injected)
