"""Compute and memory budget calculators for differentiable-physics workloads.

Reference models extracted from notebook 08's pre-ORCD scoping. Two purposes:

1. :func:`predicted_per_op_us` — estimate per-tensor-op time on different
   devices, given the tensor size in elements. Below ~64 KB the launch
   overhead dominates; above ~1 MB memory bandwidth dominates. Use to
   project GPU vs CPU wall-time at unmeasured grid sizes.

2. :func:`autograd_activation_GB` — estimate peak activation memory during
   the backward pass through a forward-Euler integration loop, optionally
   with activation checkpointing. Use to size hardware (5090 / H100 / B200)
   for an unmeasured grid + timestep configuration.

Both are order-of-magnitude models. They are useful for sizing decisions and
ORCD-pitch projections, **not** for replacing a measurement of the actual
workload. The constants (``launch_us``, ``bandwidth_GBs``,
``n_intermediates_per_step``) should be refined against measured numbers from
real notebook runs before being treated as authoritative.
"""

from __future__ import annotations

# Per-device dispatch and bandwidth constants. Order-of-magnitude.
DEVICES: dict[str, dict[str, float]] = {
    "CPU": dict(launch_us=30.0, bandwidth_GBs=50.0),     # Python dispatch + DDR5
    "GPU_5090": dict(launch_us=5.0, bandwidth_GBs=1000.0),  # CUDA launch + GDDR7
    "GPU_H100": dict(launch_us=5.0, bandwidth_GBs=3400.0),  # HBM3
    "GPU_B200": dict(launch_us=5.0, bandwidth_GBs=8000.0),  # HBM3e
}

# Per-GPU memory limits in GB. Conservative working budget (some headroom for
# weights, optimiser state, framework overhead).
GPU_MEMORY_GB: dict[str, float] = {
    "RTX_5090": 24.0,
    "H100": 80.0,
    "B200": 192.0,
}


def predicted_per_op_us(
    elements: int,
    device: str,
    bytes_per_value: int = 4,
) -> float:
    """Predicted per-tensor-op time in microseconds.

    Model: ``launch_overhead_us + (bytes / bandwidth_GBs / 1000)``.

    The first term is the constant kernel-launch (or Python-dispatch) cost
    per op; the second is the time to stream the tensor through the device's
    memory hierarchy. Below ~64 KB the launch term dominates and the device
    is dispatch-bound; above ~1 MB the bandwidth term dominates and the
    device is memory-bound.

    Args:
        elements: number of values in the tensor.
        device: one of ``DEVICES`` keys (``"CPU"``, ``"GPU_5090"``,
            ``"GPU_H100"``, ``"GPU_B200"``).
        bytes_per_value: 4 for fp32 (default), 2 for fp16/bf16.

    Returns:
        Predicted per-op time in microseconds.
    """
    if device not in DEVICES:
        raise ValueError(f"Unknown device {device!r}; choices: {list(DEVICES)}")
    cfg = DEVICES[device]
    bytes_per_op = elements * bytes_per_value
    return cfg["launch_us"] + bytes_per_op / (cfg["bandwidth_GBs"] * 1e3)


def autograd_activation_GB(
    n_cells: int,
    n_tracers: int,
    n_timesteps_in_graph: int,
    n_intermediates_per_step: int = 10,
    bytes_per_value: int = 4,
    checkpoint_every: int | None = None,
) -> float:
    """Peak activation memory during the backward pass.

    Without checkpointing, autograd retains every step's intermediates for the
    entire forward pass before backward begins::

        peak ~= n_timesteps * n_intermediates * state_bytes

    With activation checkpointing in segments of ``K`` timesteps, only the
    segment-boundary states are retained; inside one segment, the K-step
    forward is recomputed and that segment's intermediates are held in memory
    just long enough for its backward pass::

        peak ~= K * n_intermediates * state_bytes        # one-segment intermediates
              + ceil(n_timesteps / K) * state_bytes      # boundary states

    Importantly, peak does **not** decrease as ``1/K`` — increasing K linearly
    *increases* per-segment memory while linearly decreasing the boundary count,
    so the optimal K is bounded and very deep autograd graphs cannot be made
    to fit a single GPU just by choosing K.

    Args:
        n_cells: number of grid cells (e.g. 128*128 = 16 K, LLC270 ~= 12 M).
        n_tracers: number of prognostic tracers (5 in the box-model scaffold,
            39 in Darwin 3).
        n_timesteps_in_graph: number of forward-Euler steps in the autograd
            graph for a single backward pass.
        n_intermediates_per_step: number of distinct tensors PyTorch retains
            for backward per timestep. Order-of-magnitude estimate ~10 for a
            typical forward-Euler reaction-diffusion step; should be measured
            against the actual graph (``torch.cuda.max_memory_allocated()``
            after one backward pass) before relying on a specific number.
        bytes_per_value: 4 for fp32 (default), 2 for fp16/bf16.
        checkpoint_every: segment size for activation checkpointing. If
            ``None``, no checkpointing.

    Returns:
        Peak activation memory in GB.
    """
    state_bytes = n_cells * n_tracers * bytes_per_value
    if checkpoint_every is None:
        total_bytes = n_timesteps_in_graph * n_intermediates_per_step * state_bytes
    else:
        if checkpoint_every <= 0:
            raise ValueError("checkpoint_every must be a positive integer.")
        K = checkpoint_every
        T = n_timesteps_in_graph
        n_segments = (T + K - 1) // K  # ceiling division
        segment_bytes = K * n_intermediates_per_step * state_bytes
        boundary_bytes = n_segments * state_bytes
        total_bytes = segment_bytes + boundary_bytes
    return total_bytes / (1024 ** 3)


def fits_on_gpu(memory_gb: float, gpu: str) -> bool:
    """Whether a workload of ``memory_gb`` fits on ``gpu`` (single-GPU test).

    Args:
        memory_gb: estimated peak memory in GB (typically from
            :func:`autograd_activation_GB`).
        gpu: one of ``GPU_MEMORY_GB`` keys.

    Returns:
        ``True`` if the workload fits, ``False`` otherwise.
    """
    if gpu not in GPU_MEMORY_GB:
        raise ValueError(f"Unknown GPU {gpu!r}; choices: {list(GPU_MEMORY_GB)}")
    return memory_gb < GPU_MEMORY_GB[gpu]
