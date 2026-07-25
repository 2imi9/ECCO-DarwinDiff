"""Reusable EKI + Fisher-eigenbasis core for the #187 identifiability bundle.

Imported by the analytic single-box demo (`eki_prototype.py`) and the real-box
promotion (`scripts/analysis/eki_fullbox_trio.py`, the #187 estimator-independence
check on the geo1 box). NOTE: `eki` here is the Iglesias-Law-Stuart 2013 inversion
*optimizer* (perturbed-observation, no inflation/localization); its ensemble
collapses, so its final spread is a point estimate, NOT a calibrated Bayesian
posterior — a credible interval needs the EKS/sample stage (CES), which is future
work. Use it for the posterior MEAN (comparable to backprop) and the qualitative
sloppy-vs-stiff contrast, not for a quantitative CI.

  Lever 2 -- `eki`: Ensemble Kalman Inversion (Iglesias-Law-Stuart 2013),
             perturbed-observation form. Derivative-free, returns a POSTERIOR
             ensemble, never inverts a Hessian -> immune to the theta* saddle (#120).
  Lever 1 -- `fisher_eigenbasis` + `reparam_with_prior`: diagonalize the Fisher,
             estimate the STIFF combination the data pins, and put an informative
             prior only on the SLOPPY direction (prior-controlled nuisance, not
             pretended-known).

Pure numpy, CPU, deterministic given an rng. No torch import so it stays cheap to
unit-test; the box promotion passes a torch->numpy `forward` closure.
"""
from __future__ import annotations

import numpy as np


def eki(y, gamma, forward, u0, n_iter=30, rng=None):
    """Ensemble Kalman Inversion, perturbed-observation form.

    y: obs vector (d,); gamma: obs cov (d,d); forward: u[K,J] -> G[d,J];
    u0: initial ensemble [K,J]. Returns the posterior ensemble [K,J].

    forward may wrap anything (an analytic map, or a torch box integration bridged
    to numpy) as long as it maps a [K,J] parameter ensemble to a [d,J] observable
    ensemble. No gradients are taken, so a saddle in the loss cannot bite.
    """
    if rng is None:
        rng = np.random.default_rng(0)
    u = np.asarray(u0, dtype=float).copy()
    y = np.asarray(y, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    d, J = y.shape[0], u.shape[1]
    for _ in range(n_iter):
        G = forward(u)                                   # [d, J]
        u_bar = u.mean(1, keepdims=True)
        G_bar = G.mean(1, keepdims=True)
        du, dG = u - u_bar, G - G_bar
        C_uG = (du @ dG.T) / (J - 1)                     # [K, d]
        C_GG = (dG @ dG.T) / (J - 1) + gamma             # [d, d]
        K_gain = C_uG @ np.linalg.inv(C_GG)              # [K, d]
        noise = rng.multivariate_normal(np.zeros(d), gamma, size=J).T   # [d, J]
        u = u + K_gain @ (y[:, None] + noise - G)
    return u


def fisher_eigenbasis(F):
    """Eigendecomposition of a (symmetric) Fisher/Hessian F [K,K].

    Returns (eigenvalues low->high, eigenvectors as columns). The smallest
    eigenvalue's eigenvector is the SLOPPY direction (flat), the largest is the
    STIFF direction (pinned). log10(lambda_max/lambda_min) over positive eigenvalues
    is the sloppiness span in decades.
    """
    F = 0.5 * (np.asarray(F, dtype=float) + np.asarray(F, dtype=float).T)
    evals, evecs = np.linalg.eigh(F)
    return evals, evecs


def sloppiness_decades(evals):
    """log10(lambda_max / lambda_min) over strictly-positive eigenvalues, or nan."""
    pos = [float(e) for e in np.asarray(evals) if e > 0]
    if len(pos) < 2:
        return float("nan")
    return float(np.log10(max(pos) / min(pos)))


def reparam_with_prior(F, stiff_obs, stiff_sigma, prior_mean, prior_sigma):
    """Lever 1 on a linear-Gaussian problem: estimate the stiff eigen-coordinate from
    data and the sloppy one from a prior, then map back to parameter space.

    F: Fisher [K,K] (defines the eigenbasis). stiff_obs/stiff_sigma: measurement of
    the stiff coordinate (projection of the data). prior_mean/prior_sigma: informative
    prior on the sloppy coordinate. Returns (mean [K], cov [K,K]) in parameter space.

    This is the concrete "identifiable direction estimated, sloppy direction
    prior-controlled" statement, in closed form for validation; the box version runs
    it through EKI with the prior as a pseudo-observation.
    """
    evals, V = fisher_eigenbasis(F)
    K = F.shape[0]
    # eigen-coordinate 0 is sloppiest, K-1 stiffest
    mean_eig = np.zeros(K)
    var_eig = np.zeros(K)
    mean_eig[-1] = stiff_obs
    var_eig[-1] = stiff_sigma ** 2
    mean_eig[0] = prior_mean
    var_eig[0] = prior_sigma ** 2
    for j in range(1, K - 1):
        var_eig[j] = prior_sigma ** 2  # remaining sloppy dirs also prior-bounded
    mean_p = V @ mean_eig
    cov_p = V @ np.diag(var_eig) @ V.T
    return mean_p, cov_p
