"""Seasonal Carroll-6 recovery helpers: constant IC, masked z-score, Chl losses.

Hoisted out of ``scripts/run_seasonal_recovery.py`` so the loss / z-score / IC logic
is importable, unit-tested, and shared rather than duplicated across the runner and
the integrator tests. All pure functions — no I/O, no GPU required.

The Chl loss is pattern-only: each box phytoplankton tracer is z-scored over the AOI
ocean mask and compared to Darwin's z-scored Chl (so biomass-vs-chlorophyll units
cancel), per the PFT→state-index mapping in :data:`PFT_TO_STATE_IDX`.
"""

from __future__ import annotations

import torch

from darwindiff.carroll6_5pft_2layer import (
    I_DIATOM,
    I_LGE,
    I_PROHL,
    I_PROLL,
    I_SYN,
    N_TRACERS_2LAYER,
)

# Box phyto-tracer index for each Darwin Chl PFT (Chl1..Chl5).
PFT_TO_STATE_IDX: tuple[int, ...] = (I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL)

# Plausible-magnitude constant initial state (15-tracer layout); the box relaxes
# from it and the seasonal spin-up cycle damps the transient. Land cells use the
# same finite values (they are masked out of every loss term).
CONSTANT_STATE0: tuple[float, ...] = (
    0.5, 0.1, 0.1, 0.1, 0.1, 0.1, 1.0, 0.1, 2000.0, 2300.0,
    0.6, 0.5, 0.05, 2100.0, 2350.0,
)


def constant_state0(
    spatial: tuple[int, ...] = (), device: torch.device | str | None = None
) -> torch.Tensor:
    """Build the constant 15-tracer initial state, broadcast over ``spatial``.

    ``constant_state0()`` returns shape ``[15]``; ``constant_state0((H, W))`` returns
    ``[15, H, W]`` (contiguous).
    """
    vals = torch.tensor(CONSTANT_STATE0, device=device)
    if not spatial:
        return vals
    base = vals.reshape(N_TRACERS_2LAYER, *([1] * len(spatial)))
    return base.expand(N_TRACERS_2LAYER, *spatial).contiguous()


def zscore_masked(field: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Z-score ``field`` using only masked (ocean) cells; land cells left as-is.

    Uses the population std (``unbiased=False``) clamped to ``1e-6`` so a constant
    ocean region returns a finite zero field rather than NaN. Land values do not
    enter the mean/std and are dropped by the caller's ``[mask]`` selection.
    """
    vals = field[mask]
    mean = vals.mean()
    std = vals.std(unbiased=False).clamp(min=1e-6)
    return (field - mean) / std


def seasonal_chl_loss(
    snaps: torch.Tensor, chl_z: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """Mean over 12 months of summed z-scored Chl1-5 MSE.

    ``snaps``: ``[12, 15, ...]`` month-end states; ``chl_z``: ``[12, 5, ...]``
    z-scored Darwin Chl targets; ``mask``: ocean cells.
    """
    total = snaps.new_zeros(())
    for m in range(12):
        for p, idx in enumerate(PFT_TO_STATE_IDX):
            pred_z = zscore_masked(snaps[m, idx], mask)
            total = total + ((pred_z - chl_z[m, p])[mask] ** 2).mean()
    return total / 12.0


def timemean_chl_loss(
    state: torch.Tensor, chl_z: torch.Tensor, mask: torch.Tensor
) -> torch.Tensor:
    """Single-block baseline: fit the annual-mean Chl pattern.

    ``state``: ``[15, ...]`` final state; ``chl_z``: ``[12, 5, ...]`` monthly z-scored
    targets, averaged over the month axis here.
    """
    target = chl_z.mean(dim=0)
    total = state.new_zeros(())
    for p, idx in enumerate(PFT_TO_STATE_IDX):
        pred_z = zscore_masked(state[idx], mask)
        total = total + ((pred_z - target[p])[mask] ** 2).mean()
    return total
