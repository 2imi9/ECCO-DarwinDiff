"""Tests for the reusable EKI + Fisher-eigenbasis core (scripts/analysis/eki_core.py, #187).

Pure numpy, deterministic (seeded rng). Validates the EKI math independent of the box:
a well-posed linear-Gaussian problem recovers the truth; a rank-deficient observable
reproduces the source<->scavenging degeneracy; the eigenbasis + prior reparameterization
bounds the sloppy direction.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

_ANALYSIS = Path(__file__).resolve().parents[1] / "scripts" / "analysis"
if str(_ANALYSIS) not in sys.path:
    sys.path.insert(0, str(_ANALYSIS))
import eki_core as ek  # noqa: E402


def test_eki_recovers_well_posed_linear_truth():
    # Two independent observables of two params => fully identified; EKI must find truth.
    rng = np.random.default_rng(1)
    H = np.array([[1.0, 0.0], [0.0, 1.0]])
    truth = np.array([0.7, -1.3])
    y = H @ truth
    gamma = np.diag([0.02, 0.02]) ** 2
    u0 = rng.normal(0.0, 2.0, size=(2, 400))
    post = ek.eki(y, gamma, lambda u: H @ u, u0, n_iter=30, rng=rng)
    assert np.allclose(post.mean(1), truth, atol=0.05)


def test_eki_reproduces_source_scavenging_degeneracy():
    # One observable ln(S/k) = u0 - u1: pins the RATIO, leaves the sum (residence time) free.
    rng = np.random.default_rng(0)
    log_fe = np.log(0.58)
    G = lambda u: (u[0] - u[1])[None, :]
    u0 = np.vstack([rng.normal(log_fe, 2.0, 400), rng.normal(0.0, 2.0, 400)])
    post = ek.eki(np.array([log_fe]), np.array([[0.24 ** 2]]), G, u0, n_iter=30, rng=rng)
    ratio = post[0] - post[1]      # stiff, observed
    summ = post[0] + post[1]       # along the sloppy ridge
    cv = lambda x: np.std(x) / max(abs(np.mean(x)), 1e-9)
    # the ratio is pinned an order of magnitude tighter than the sloppy sum
    assert np.std(ratio) < 0.15
    assert np.std(summ) > 5 * np.std(ratio)
    # posterior principal axis aligns with the analytic sloppy (1,1)/sqrt2
    _, V = np.linalg.eigh(np.cov(post))
    align = abs(float(V[:, -1] @ (np.array([1, 1]) / np.sqrt(2))))
    assert align > 0.9


def test_fisher_eigenbasis_rank1_sloppiness():
    # A rank-1 Fisher (single stiff combination) => one large eigenvalue, one ~zero.
    v = np.array([1.0, -1.0]) / np.sqrt(2)   # stiff = ratio direction
    F = 100.0 * np.outer(v, v)
    evals, evecs = ek.fisher_eigenbasis(F)
    assert evals[0] < 1e-9 < evals[-1]        # sloppy ~0, stiff large
    # stiff eigenvector aligns with v; sloppy is orthogonal (the (1,1) ridge)
    assert abs(float(evecs[:, -1] @ v)) > 0.99
    assert np.isnan(ek.sloppiness_decades(evals))  # only one positive eigenvalue


def test_reparam_with_prior_bounds_the_sloppy_direction():
    # Rank-1 Fisher: without a prior the sloppy variance is unbounded. reparam_with_prior
    # gives finite covariance along the sloppy direction from the prior.
    v = np.array([1.0, -1.0]) / np.sqrt(2)
    F = 100.0 * np.outer(v, v)
    mean_p, cov_p = ek.reparam_with_prior(F, stiff_obs=0.0, stiff_sigma=0.05,
                                          prior_mean=0.0, prior_sigma=0.4)
    assert np.all(np.isfinite(cov_p))
    sloppy_dir = np.array([1.0, 1.0]) / np.sqrt(2)
    sloppy_var = float(sloppy_dir @ cov_p @ sloppy_dir)
    stiff_var = float(v @ cov_p @ v)
    assert stiff_var < sloppy_var              # data pins the stiff dir tighter than the prior
    assert 0 < sloppy_var < np.inf
