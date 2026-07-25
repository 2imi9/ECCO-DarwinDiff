"""Regression tests for the emulator log-space defects (F1-F4).

Each test pins one measured defect so it cannot silently return. The reference numbers in
the docstrings come from `darwin_v05_L5_chl.npz` on AICR, re-derived 2026-07-25.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest

_SPEC = importlib.util.spec_from_file_location(
    "emulator_poc", Path(__file__).resolve().parents[1] / "scripts" / "emulator_poc.py"
)
emu = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(emu)


def _lognormal_cube(n_months=12, h=6, w=8, frac_nonpos=0.13, seed=0):
    """A Chl-like field: lognormal over ~6 decades with a realistic non-positive tail."""
    rng = np.random.default_rng(seed)
    x = np.exp(rng.normal(-7.0, 2.0, size=(n_months, 1, h, w)))
    flat = x.reshape(-1)
    idx = rng.choice(flat.size, size=int(frac_nonpos * flat.size), replace=False)
    flat[idx] = -np.abs(rng.normal(0, 1e-3, size=idx.size))  # v05-style negative cells
    return x


# --------------------------------------------------------------------------- F1
def test_f1_log_tracers_default_covers_all_lognormal_tracers():
    """PIC/POC/FeT have the same failure mode as Chl and must be logged by default.

    Measured: logged Chl1 keeps 0.971 of its log-range with 0.00% non-physical output,
    while unlogged PIC/POC/FeT keep 0.39/0.34/0.67 and emit 13.9/10.2/3.5%.
    """
    args = emu.parse_args(["--log-transform"])
    stems = {s.strip() for s in args.log_tracers.split(",")}
    for required in ("Chl1", "PIC", "POC", "FeT"):
        assert required in stems, f"{required} must be log-transformed by default"


def test_f1_stem_matching_is_depth_level_aware():
    names = ["PIC_k0", "PIC_k3", "DIC_k0", "Chl1_k2", "ALK"]
    mask = emu.build_log_mask(names, True, "Chl1,PIC,POC,FeT")
    assert list(mask) == [True, True, False, True, False]


# --------------------------------------------------------------------------- F2
def test_f2_percentile_floor_beats_fixed_epsilon_on_std_inflation():
    """A 1e-12 floor puts non-positive cells ~21 log-units below the signal.

    On real Chl1 that inflated the log-space std 1.72x (4.81 -> 8.26) and compressed the
    usable signal from +/-1.0 to +/-0.58 z-units.
    """
    state = _lognormal_cube()
    train = np.arange(8)
    vmask = np.ones(state.shape[-2:], dtype=bool)
    log_mask = np.array([True])

    eps_floors = emu.log_floors(state, train, vmask, log_mask, floor_pct=0.0)
    pct_floors = emu.log_floors(state, train, vmask, log_mask, floor_pct=1.0)
    assert eps_floors[0] == pytest.approx(emu.LOG_EPS)
    assert pct_floors[0] > eps_floors[0] * 1e3, "percentile floor must lift off the epsilon"

    _, _, stds_eps = emu.standardize(state, train, vmask, log_mask, eps_floors)
    _, _, stds_pct = emu.standardize(state, train, vmask, log_mask, pct_floors)
    assert stds_pct[0] < stds_eps[0], "percentile floor must reduce std inflation"


def test_f2_floor_uses_train_months_only():
    """Leak-free: a wild value in a validation month must not move the floor."""
    state = _lognormal_cube(n_months=10)
    vmask = np.ones(state.shape[-2:], dtype=bool)
    log_mask = np.array([True])
    train = np.arange(6)

    base = emu.log_floors(state, train, vmask, log_mask, 1.0)[0]
    state[8] = state[8] * 1e6  # contaminate a val month only
    after = emu.log_floors(state, train, vmask, log_mask, 1.0)[0]
    assert base == pytest.approx(after)


def test_f2_floor_pct_zero_restores_legacy_behaviour():
    state = _lognormal_cube()
    vmask = np.ones(state.shape[-2:], dtype=bool)
    log_mask = np.array([True])
    floors = emu.log_floors(state, np.arange(8), vmask, log_mask, 0.0)
    assert floors[0] == pytest.approx(emu.LOG_EPS)


# --------------------------------------------------------------------------- F3
def test_f3_climatology_is_mean_of_logs_not_log_of_mean():
    """log(mean x) != mean(log x); for Chl1_k0 the gap was +3.21 nat-log units (+0.39 sigma).

    Averaging in physical space and logging afterwards displaces the climatology baseline
    upward, which inflates skill_vs_climatology for every logged channel.
    """
    state = _lognormal_cube(frac_nonpos=0.0)
    train = np.arange(8)
    floor = emu.LOG_EPS

    log_of_mean = np.log(np.clip(np.nanmean(state[train], axis=0), floor, None))
    mean_of_log = np.nanmean(np.log(np.clip(state[train], floor, None)), axis=0)

    # Jensen: the arithmetic mean of a positive field always sits above the geometric mean.
    assert np.all(log_of_mean >= mean_of_log - 1e-12)
    assert np.mean(log_of_mean - mean_of_log) > 0.05, "the two orderings must be distinguishable"


# --------------------------------------------------------------------------- F4
def _cube_with_gaps(gaps_days):
    times = np.concatenate([[0.0], np.cumsum(np.asarray(gaps_days, dtype=float))])
    n = len(times)
    return {
        "times_days": times,
        "state": np.ones((n, 1, 2, 2)),
        "valid_mask": np.ones((2, 2), dtype=bool),
        "chan_names": ["Chl1"],
    }


def test_f4_guard_fires_on_realistic_every_other_month_calendar():
    """The old 0.02 tolerance never fired on real calendar data.

    Real every-other-month gaps run 59-62 d, so ptp/median ~= 0.05 and the uniformly-sparse
    axis sailed through, mislabelling two-month jumps as next-month skill (#191).
    """
    data = _cube_with_gaps([59, 62, 60, 61, 59, 62, 60])
    with pytest.raises(RuntimeError, match="uniformly-sparse"):
        emu.build_splits(data, val_frac=0.3, adjacency_tol=1.6)


def test_f4_guard_silent_on_genuine_monthly_cadence():
    data = _cube_with_gaps([31, 28, 31, 30, 31, 30, 31, 31])
    splits = emu.build_splits(data, val_frac=0.3, adjacency_tol=1.6)
    assert splits["median_step_days"] < 45.0


def test_f4_expected_step_days_overrides_the_guard():
    """Pinning the true cadence is the sanctioned escape hatch, not a silent pass."""
    data = _cube_with_gaps([59, 62, 60, 61, 59, 62, 60])
    splits = emu.build_splits(
        data, val_frac=0.3, adjacency_tol=1.6, expected_step_days=60.9
    )
    assert splits["adjacency_ref_days"] == pytest.approx(60.9)
