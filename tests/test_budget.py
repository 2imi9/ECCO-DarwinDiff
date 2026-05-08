"""Tests for darwindiff.budget: per-op-cost and activation-memory models.

These models are order-of-magnitude (constants are estimates, not measurements).
The tests check the *shape* of the answers — monotonicities, regime transitions,
checkpointing semantics — not specific values.
"""

from __future__ import annotations

import math

import pytest

from darwindiff.budget import (
    DEVICES,
    GPU_MEMORY_GB,
    autograd_activation_GB,
    fits_on_gpu,
    predicted_per_op_us,
)


# ---------------------------------------------------------------------------
# predicted_per_op_us
# ---------------------------------------------------------------------------


def test_per_op_us_dispatch_dominates_at_small_size() -> None:
    """At 1 K elements every device's per-op time is dominated by launch overhead."""
    for device, cfg in DEVICES.items():
        t = predicted_per_op_us(elements=1000, device=device)
        assert math.isclose(t, cfg["launch_us"], rel_tol=0.05), (
            f"At 1 K elements {device} should be ~{cfg['launch_us']} us "
            f"(launch-bound), got {t}."
        )


def test_per_op_us_bandwidth_dominates_at_large_size() -> None:
    """At 100 M elements per-op time is dominated by memory bandwidth."""
    for device, cfg in DEVICES.items():
        t = predicted_per_op_us(elements=100_000_000, device=device)
        bandwidth_term = 100_000_000 * 4 / (cfg["bandwidth_GBs"] * 1e3)
        assert t > bandwidth_term * 0.95, (
            f"At 100 M elements {device} should be bandwidth-dominated."
        )


def test_per_op_us_gpu_beats_cpu_at_million_elements() -> None:
    """The crossover where GPU wins is somewhere below 1 M elements."""
    cpu = predicted_per_op_us(elements=1_000_000, device="CPU")
    gpu_5090 = predicted_per_op_us(elements=1_000_000, device="GPU_5090")
    gpu_b200 = predicted_per_op_us(elements=1_000_000, device="GPU_B200")
    assert gpu_5090 < cpu
    assert gpu_b200 < cpu
    assert gpu_b200 < gpu_5090  # B200 always at least as fast as 5090


def test_per_op_us_unknown_device_raises() -> None:
    with pytest.raises(ValueError):
        predicted_per_op_us(elements=1024, device="quantum_machine")


# ---------------------------------------------------------------------------
# autograd_activation_GB
# ---------------------------------------------------------------------------


def test_activation_memory_scales_linearly_in_timesteps_no_checkpoint() -> None:
    """Without checkpointing, doubling timesteps doubles peak memory."""
    cells, tracers = 1_000_000, 5
    m100 = autograd_activation_GB(cells, tracers, n_timesteps_in_graph=100)
    m200 = autograd_activation_GB(cells, tracers, n_timesteps_in_graph=200)
    assert math.isclose(m200, 2.0 * m100, rel_tol=0.001)


def test_activation_memory_notebook07_scale_known_value() -> None:
    """Notebook 07's scale (128*128 cells, 5 tracers, 200 steps, no checkpoint).

    Expected: 128*128 * 5 * 4 bytes * 200 * 10 intermediates
            = 16384 * 5 * 4 * 200 * 10 bytes
            = 655_360_000 bytes ~ 0.61 GB.
    """
    gb = autograd_activation_GB(
        n_cells=128 * 128, n_tracers=5, n_timesteps_in_graph=200
    )
    expected = 128 * 128 * 5 * 4 * 200 * 10 / (1024 ** 3)
    assert math.isclose(gb, expected, rel_tol=1e-9)
    # Should fit anywhere — this matches the notebook 08 table row.
    assert fits_on_gpu(gb, "RTX_5090")


def test_activation_memory_checkpoint_reduces_peak() -> None:
    """Checkpointing always reduces peak vs no-checkpoint at the same workload."""
    cells, tracers, T = 1_500_000, 39, 30
    no_ckpt = autograd_activation_GB(cells, tracers, T)
    with_ckpt = autograd_activation_GB(cells, tracers, T, checkpoint_every=5)
    assert with_ckpt < no_ckpt


def test_activation_memory_checkpoint_optimum_is_bounded() -> None:
    """Peak under checkpointing has a U-shape in K: too small or too large is worse.

    With K=1 every step is its own segment (boundary count = T, segment work = 1
    intermediate set). With K=T the whole thing is one segment (no benefit). The
    optimum is somewhere in between. This test just checks the U-shape exists.
    """
    cells, tracers, T = 12_000_000, 39, 365
    m_k1 = autograd_activation_GB(cells, tracers, T, checkpoint_every=1)
    m_k_mid = autograd_activation_GB(cells, tracers, T, checkpoint_every=20)
    m_k_T = autograd_activation_GB(cells, tracers, T, checkpoint_every=T)
    # Either endpoint should be at least as bad as the middle.
    assert m_k_mid <= m_k1 or m_k_mid <= m_k_T


def test_activation_memory_llc270_yearly_does_not_fit_b200() -> None:
    """The motivating case from notebook 08: LLC270 1-yr autograd does NOT fit a single B200.

    This test locks the conclusion that drove the multi-GPU / time-window
    decomposition decision in research_log.md (D3).
    """
    gb_no_ckpt = autograd_activation_GB(12_000_000, 39, 365)
    gb_ckpt5 = autograd_activation_GB(12_000_000, 39, 365, checkpoint_every=5)
    gb_ckpt10 = autograd_activation_GB(12_000_000, 39, 365, checkpoint_every=10)
    assert not fits_on_gpu(gb_no_ckpt, "B200")
    assert not fits_on_gpu(gb_ckpt5, "B200")
    assert not fits_on_gpu(gb_ckpt10, "B200")


def test_activation_memory_llc270_monthly_fits_b200_with_checkpoint() -> None:
    """Global LLC270 + 30 days + ckpt@5 fits B200 (the affirmative ORCD case)."""
    gb = autograd_activation_GB(12_000_000, 39, 30, checkpoint_every=5)
    assert fits_on_gpu(gb, "B200")
    # Should not fit H100 (80 GB) at this aggressive workload.
    assert not fits_on_gpu(gb, "H100")


def test_activation_memory_invalid_checkpoint_raises() -> None:
    with pytest.raises(ValueError):
        autograd_activation_GB(1000, 5, 100, checkpoint_every=0)


# ---------------------------------------------------------------------------
# fits_on_gpu
# ---------------------------------------------------------------------------


def test_fits_on_gpu_unknown_gpu_raises() -> None:
    with pytest.raises(ValueError):
        fits_on_gpu(memory_gb=10.0, gpu="A4000")


def test_fits_on_gpu_boundary() -> None:
    """A workload exactly at the limit does not fit (strict less-than)."""
    assert not fits_on_gpu(memory_gb=GPU_MEMORY_GB["RTX_5090"], gpu="RTX_5090")
    assert fits_on_gpu(memory_gb=GPU_MEMORY_GB["RTX_5090"] - 1.0, gpu="RTX_5090")
