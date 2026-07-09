"""Tests for the symbolic-distillation go/no-go gate (scripts/symbolic_distill_probe).

The gate is a second, independent identifiability oracle that must agree with the
Fisher / profile-likelihood diagnostics: a genuinely identifiable Monod closure
whose support spans the half-saturation knee must PASS (and recover k); a
profile-flat closure, a narrow-support closure that has not seen the knee, and a
non-Monod (linear) closure must all FAIL. These tests pin exactly that behavior.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

# The probe lives under scripts/ (not an installed package): load it by path.
# Register in sys.modules before exec so its @dataclass can resolve __module__.
_MOD_PATH = Path(__file__).resolve().parents[1] / "scripts" / "symbolic_distill_probe.py"
_spec = importlib.util.spec_from_file_location("symbolic_distill_probe", _MOD_PATH)
sd = importlib.util.module_from_spec(_spec)
sys.modules["symbolic_distill_probe"] = sd
_spec.loader.exec_module(sd)


K_TRUE = 8.0e-5


def _monod(dfe, p=1.0):
    return (dfe / (dfe + K_TRUE)) ** p


# --------------------------------------------------------------------------- #
# Core regression primitives
# --------------------------------------------------------------------------- #

def test_stlsq_recovers_known_sparse_combination():
    """A planted 2-term law must be recovered; irrelevant columns -> ~0."""
    rng = np.random.default_rng(0)
    dfe = np.logspace(-5, -3, 2000)
    theta, names, is_monod = sd.build_library(dfe, sd.monod_bank_ks(), poly_degree=2)
    # plant y = 1.3 * monod(k~8e-5 column) + 0.1 * const
    kcol = int(np.argmin(np.abs(sd.monod_bank_ks() - 8e-5)))
    const_col = names.index("1")
    coef_true = np.zeros(theta.shape[1])
    coef_true[kcol] = 1.3
    coef_true[const_col] = 0.1
    y = theta @ coef_true + 1e-4 * rng.standard_normal(dfe.size)
    coef = sd.stlsq(theta, y, threshold=0.05)
    # the planted Monod column is selected and dominant among Monod atoms
    assert coef[kcol] != 0.0
    assert is_monod[np.argmax(np.abs(np.where(is_monod, coef, 0.0)))]


def test_support_mask_trims_tails():
    dfe = np.concatenate([np.array([1e-9, 1e9]), np.logspace(-5, -3, 1000)])
    m = sd.support_mask(dfe)
    assert not m[0] and not m[1]  # both outliers dropped
    assert m[2:].sum() > 900


def test_inverse_density_weights_mean_one():
    dfe = np.logspace(-5, -3, 5000)
    w = sd.inverse_density_weights(dfe)
    assert np.isclose(w.mean(), 1.0, atol=1e-6)
    assert (w > 0).all()


def test_refine_monod_k_recovers_planted_k():
    dfe = np.logspace(-5, -3, 3000)
    y = _monod(dfe)  # pure Monod, knee bracketed
    k_hat, r2 = sd.refine_monod_k(dfe, y, k0=5e-5)
    assert abs(k_hat - K_TRUE) / K_TRUE < 0.10
    assert r2 > 0.999


def test_alias_high_below_knee_low_across_knee():
    below = np.logspace(-6.5, -5.2, 2000)   # all << K_TRUE
    across = np.logspace(-5, -3, 2000)      # brackets K_TRUE
    assert sd.monod_linear_alias(below, K_TRUE) > 0.98   # indistinguishable from a line
    assert sd.monod_linear_alias(across, K_TRUE) < 0.95  # the knee separates them


# --------------------------------------------------------------------------- #
# The verdict: the four canonical closures
# --------------------------------------------------------------------------- #

def test_pure_monod_wide_support_passes_and_recovers_k():
    rng = np.random.default_rng(1)
    dfe = np.logspace(-5, -3, 4000)
    y = _monod(dfe) + 0.002 * rng.standard_normal(dfe.size)
    v = sd.distill(dfe, y, seed=1)
    assert v.passed, v.reason
    assert v.monod_inclusion >= 0.85
    assert abs(v.k_hat - K_TRUE) / K_TRUE < 0.20


def test_narrow_support_monod_fails_as_non_identifiable():
    """A perfectly Monod closure that never visited the knee must FAIL -- the
    support-is-identifiability point. This is the honest verdict that saves
    H200 budget (excitation, not more compute, is the fix)."""
    rng = np.random.default_rng(2)
    dfe = np.logspace(-6.5, -5.2, 4000)  # all far below K_TRUE
    y = _monod(dfe) + 0.002 * rng.standard_normal(dfe.size)
    v = sd.distill(dfe, y, seed=2)
    assert not v.passed
    assert "alias" in v.reason.lower() and v.monod_linear_alias > 0.95


def test_flat_closure_fails_as_profile_flat():
    """Constant closure (the diatomgraz profile-flat analog) -> FAIL, and the
    gate short-circuits before touching the bank."""
    rng = np.random.default_rng(3)
    dfe = np.logspace(-5, -3, 4000)
    y = 0.5 + 1e-8 * rng.standard_normal(dfe.size)
    v = sd.distill(dfe, y, seed=3)
    assert not v.passed
    assert "flat" in v.reason.lower()
    assert v.monod_inclusion == 0.0


def test_linear_confounder_does_not_false_pass_monod():
    """A rising line that fakes saturation over the support must not be reported
    as a recovered Monod law."""
    rng = np.random.default_rng(4)
    dfe = np.logspace(-5, -3, 4000)
    y = np.clip(0.2 + 300.0 * dfe, 0, 1) + 0.002 * rng.standard_normal(dfe.size)
    v = sd.distill(dfe, y, seed=4)
    assert not v.passed


def test_selftest_panel_is_self_consistent():
    """The bundled analytic panel must return the designed verdicts and recover
    the planted k on the pure-Monod case."""
    out = sd._selftest_panel(seed=0)
    assert out["_meta"]["verdicts_ok"]
    assert out["_meta"]["k_recovery_ok"]


def test_verdict_is_json_serializable():
    import json
    rng = np.random.default_rng(5)
    dfe = np.logspace(-5, -3, 1000)
    y = _monod(dfe) + 0.002 * rng.standard_normal(dfe.size)
    v = sd.distill(dfe, y, seed=5)
    json.dumps(v.as_dict())  # must not raise (no numpy scalars leaking through)


# --------------------------------------------------------------------------- #
# Power-law / calcite oracle (is an Omega-driven rain-ratio law identifiable?)
# --------------------------------------------------------------------------- #

def test_powerlaw_wide_support_identifiable_and_recovers_exponent():
    rng = np.random.default_rng(10)
    om = np.exp(rng.uniform(np.log(0.5), np.log(6.0), 3000))
    ratio = 0.0425 * om ** 0.5 * np.exp(0.03 * rng.standard_normal(om.size))
    v = sd.distill_powerlaw(om, ratio, seed=10)
    assert v.identifiable, v.reason
    assert abs(v.n_hat - 0.5) < 0.10
    assert v.n_ci_lo > 0.0  # CI excludes zero


def test_powerlaw_flat_is_the_null():
    """Omega-independent ratio (Maranon-2016 tropical calcification) -> the NULL."""
    rng = np.random.default_rng(11)
    om = np.exp(rng.uniform(np.log(0.5), np.log(6.0), 3000))
    ratio = 0.0425 * np.exp(0.03 * rng.standard_normal(om.size))
    v = sd.distill_powerlaw(om, ratio, seed=11)
    assert not v.identifiable
    assert abs(v.n_hat) < 0.1


def test_powerlaw_narrow_support_is_underexcited():
    rng = np.random.default_rng(12)
    om = np.exp(rng.uniform(np.log(2.4), np.log(3.0), 3000))  # ~0.1 dex
    ratio = 0.0425 * om ** 0.5 * np.exp(0.03 * rng.standard_normal(om.size))
    v = sd.distill_powerlaw(om, ratio, seed=12)
    assert not v.identifiable
    assert v.driver_log_span < 0.30


def test_calcite_panel_self_consistent():
    out = sd._selftest_calcite_panel(seed=0)
    assert out["_meta"]["verdicts_ok"]
    assert out["_meta"]["n_recovery_ok"]


def test_powerlaw_verdict_json_serializable():
    import json
    rng = np.random.default_rng(13)
    om = np.exp(rng.uniform(np.log(0.5), np.log(6.0), 1000))
    ratio = 0.0425 * om ** 0.5
    json.dumps(sd.distill_powerlaw(om, ratio, seed=13).as_dict())


def test_spatial_holdout_overlapping_groups_transfers():
    """Two spatial regimes that overlap in the DFe driver -> leave-one-group-out
    is a fair interpolation test, and a pure Monod transfers well."""
    rng = np.random.default_rng(6)
    dfe = np.logspace(-5, -3, 3000)
    y = _monod(dfe) + 0.002 * rng.standard_normal(dfe.size)
    groups = rng.integers(0, 2, dfe.size)  # regimes share the DFe support
    v = sd.distill(dfe, y, groups=groups, seed=6)
    assert v.passed
    assert v.r2_holdout > 0.9


def test_spatial_holdout_disjoint_driver_fails_transfer():
    """Groups that are disjoint in the DFe driver (train low-DFe, test the
    saturated high-DFe tail) is a pure extrapolation -> the gate must report a
    transfer FAIL. This is the same surrogate-gap signature as the real held-out
    GEOTRACES test (negative R^2): the honest verdict, not a bug."""
    rng = np.random.default_rng(7)
    dfe = np.logspace(-5, -3, 3000)
    y = _monod(dfe) + 0.002 * rng.standard_normal(dfe.size)
    groups = (np.log10(dfe) > -4).astype(int)  # disjoint: low vs high DFe
    v = sd.distill(dfe, y, groups=groups, seed=7)
    assert not v.passed
    assert "held-out" in v.reason.lower()
