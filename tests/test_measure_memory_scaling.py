"""Tests for the GPU-memory scaling harness (scripts/measure_memory_scaling.py).

The fit / extrapolation logic is pure and tested directly. The measurement path is
exercised on CPU at a tiny size (no CUDA peak available there, but the
forward/backward graph still runs — a useful smoke test of the box-model API wiring).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "measure_memory_scaling.py"
_spec = importlib.util.spec_from_file_location("measure_memory_scaling", _SCRIPT)
assert _spec is not None and _spec.loader is not None
mms = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = mms  # frozen dataclasses resolve __module__ via sys.modules
_spec.loader.exec_module(mms)


def test_fit_recovers_known_linear_law():
    a_true, b_true = 50_000_000.0, 1_234.0
    records = [
        mms.MemRecord(n_cells=c, n_steps=s,
                      train_peak_bytes=int(a_true + b_true * c * s),
                      forward_peak_bytes=None, oom=False)
        for c in (1_000, 5_000, 20_000)
        for s in (50, 200, 400)
    ]
    fit = mms.fit_cellstep_scaling(records)
    assert fit["r2"] > 0.9999
    assert fit["b_bytes_per_cellstep"] == pytest.approx(b_true, rel=1e-6)
    assert fit["a_bytes"] == pytest.approx(a_true, rel=1e-6)


def test_fit_degenerate_without_enough_points():
    fit = mms.fit_cellstep_scaling([])
    assert fit["n"] == 0.0


def test_extrapolation_monotonic_in_size():
    fit = {"a_bytes": 1.0e8, "b_bytes_per_cellstep": 1000.0, "r2": 1.0, "n": 9.0}
    by_label = {e["label"]: e for e in mms.extrapolate(fit, mms.EXTRAPOLATION_TARGETS)}
    # finer grid costs more than coarse at equal trajectory length
    assert (by_label["LLC270 global · time-mean"]["pred_gb"]
            > by_label["LLC90 global  · time-mean"]["pred_gb"])
    # seasonal (more steps) costs more than time-mean at equal grid
    assert (by_label["LLC270 global · seasonal"]["pred_gb"]
            > by_label["LLC270 global · time-mean"]["pred_gb"])


def test_reference_grid_cell_counts():
    assert mms.LLC90_CELLS == 105_300
    assert mms.LLC270_CELLS == 947_700
    assert mms.LLC270_CELLS == 9 * mms.LLC90_CELLS  # the 9x spatial factor


def test_measure_peak_runs_on_cpu():
    """Tiny CPU run: graph executes end to end, no CUDA peak, no OOM."""
    rec = mms.measure_peak(n_cells=32, n_steps=8, device="cpu")
    assert rec.n_cells == 32
    assert rec.n_steps == 8
    assert rec.oom is False
    assert rec.train_peak_bytes is None  # CUDA-only metric
