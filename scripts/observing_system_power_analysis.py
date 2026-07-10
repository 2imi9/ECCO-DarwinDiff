"""Observing-system power analysis for the calcite rain-ratio closure ``ratio = R0 * Omega^n``.

Track-2 (Paper #2) finds the calcite Omega-modulation is *support-limited*: within-region Omega
support is <= 0.16 dex everywhere, too narrow to fit the power law. The paper's forward contribution
is an observing-system recommendation ("get wider Omega coverage"), but that was a heuristic. This
script makes it a **quantified requirement**: how much Omega span (dex) x how many co-located
ratio+Omega samples x at what measurement precision are needed to make the exponent ``n`` identifiable?

Model. Fit ``log10(ratio) = n * log10(Omega) + c`` by OLS on N samples whose log10(Omega) spans S dex
(log-uniform) with log10-residual scatter sigma. The OLS slope SE is
``sigma / sqrt(sum (x-xbar)^2) = sigma * sqrt(12) / (S * sqrt(N))`` (var of a uniform over S is S^2/12).
"Identifiable" = the slope's 95% CI excludes 0, i.e. |n_hat|/SE > 1.96. The detection **power** is then
``Phi( n * S * sqrt(N) / (sigma * sqrt(12)) - 1.96 )`` (a closed form we also verify by Monte Carlo).

The frontier at power p solves ``n*S*sqrt(N)/(sigma*sqrt(12)) = 1.96 + Phi^{-1}(p)``, i.e.
``S * sqrt(N) = (1.96 + z_p) * sqrt(12) * sigma / n``  -- a hyperbola in (S, N) per (n, sigma).

CPU-only, seconds. Numpy (+ scipy if present; falls back to a math.erf normal CDF/quantile).
Run:  python scripts/observing_system_power_analysis.py --out docs/findings/observing_system_power.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np

try:
    from scipy.stats import norm
    _PHI, _PHIINV = norm.cdf, norm.ppf
except Exception:                                                    # pragma: no cover
    _PHI = lambda z: 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    def _PHIINV(p):                                                  # Acklam approximation
        a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
             1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
        b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
             6.680131188771972e+01, -1.328068155288572e+01]
        c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
             -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
        d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00, 3.754408661907416e+00]
        pl, ph = 0.02425, 1 - 0.02425
        if p < pl:
            q = math.sqrt(-2 * math.log(p))
            return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
        if p <= ph:
            q = p - 0.5; r = q*q
            return (((((a[0]*r+a[1])*r+a[2])*r+a[3])*r+a[4])*r+a[5])*q / (((((b[0]*r+b[1])*r+b[2])*r+b[3])*r+b[4])*r+1)
        q = math.sqrt(-2 * math.log(1-p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)

Z = 1.959963985                                                      # 95% two-sided
SQRT12 = math.sqrt(12.0)
CURRENT_SUPPORT_DEX = 0.16                                          # Track-2: within-region Omega support


def power(n_true, span_dex, n_samp, sigma):
    """Analytic detection power = P(slope CI excludes 0)."""
    ncp = n_true * span_dex * math.sqrt(n_samp) / (sigma * SQRT12)
    return _PHI(ncp - Z) + _PHI(-ncp - Z)


def n_needed(n_true, span_dex, sigma, p=0.8):
    """Samples needed at a given span for power p (inverse of the frontier)."""
    k = (Z + _PHIINV(p)) * SQRT12 * sigma / n_true
    return (k / span_dex) ** 2


def mc_power(n_true, span_dex, n_samp, sigma, reps=400, seed=0, R0=0.04):
    """Monte-Carlo check: draw data, OLS-fit, count 95%-CI-excludes-0."""
    rng = np.random.default_rng(seed)
    n_samp = int(round(n_samp))
    if n_samp < 3:
        return float("nan")
    hits = 0
    for _ in range(reps):
        x = rng.uniform(0.0, span_dex, n_samp)                       # log10(Omega/Omega0), spans S dex
        y = n_true * x + np.log10(R0) + sigma * rng.standard_normal(n_samp)
        b, a = np.polyfit(x, y, 1)
        resid = y - (b * x + a)
        sxx = np.sum((x - x.mean()) ** 2)
        se = math.sqrt(np.sum(resid ** 2) / (n_samp - 2) / sxx) if sxx > 0 else float("inf")
        if se > 0 and abs(b) / se > Z:
            hits += 1
    return hits / reps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=None)
    ap.add_argument("--mc-reps", type=int, default=400)
    args = ap.parse_args()

    n_trues = [0.3, 0.5, 1.0]                                        # Omega-sensitivities to detect
    sigmas = [0.10, 0.20, 0.30]                                      # log10 residual scatter (calibrate to Marsh/Daniels)
    spans = [round(s, 3) for s in np.linspace(0.05, 1.2, 24)]
    n_grid = [10, 20, 30, 50, 75, 100, 150, 250, 400, 600]
    p_target = 0.8

    # -- power surface (analytic) -----------------------------------------------------
    surface = {}
    for nt in n_trues:
        for sg in sigmas:
            grid = [[round(power(nt, S, N, sg), 4) for N in n_grid] for S in spans]
            surface[f"n{nt}_sigma{sg}"] = grid

    # -- the actionable frontier: N needed at anchor spans; span needed at anchor N ----
    anchor_spans = [CURRENT_SUPPORT_DEX, 0.3, 0.5, 0.8, 1.0]
    frontier = {}
    for nt in n_trues:
        for sg in sigmas:
            row = {f"span_{S}dex": (round(n_needed(nt, S, sg, p_target), 1)) for S in anchor_spans}
            # span needed for N in {50, 100} (invert S*sqrt(N)=k)
            k = (Z + _PHIINV(p_target)) * SQRT12 * sg / nt
            row["span_for_N50_dex"] = round(k / math.sqrt(50), 3)
            row["span_for_N100_dex"] = round(k / math.sqrt(100), 3)
            frontier[f"n{nt}_sigma{sg}"] = row

    # -- Monte-Carlo validation on 4 anchor cells -------------------------------------
    checks = []
    for (nt, S, N, sg) in [(0.5, 0.16, 100, 0.2), (0.5, 0.5, 100, 0.2),
                           (0.5, 0.5, 50, 0.2), (0.3, 1.0, 100, 0.3)]:
        checks.append({"n_true": nt, "span_dex": S, "n_samp": N, "sigma": sg,
                       "analytic_power": round(power(nt, S, N, sg), 3),
                       "mc_power": round(mc_power(nt, S, N, sg, reps=args.mc_reps), 3)})

    # -- headline (the realistic calcite case) ----------------------------------------
    nt0, sg0 = 0.5, 0.2
    headline = {
        "case": f"detect n={nt0} at sigma={sg0} (log10 residual), 80% power",
        "at_current_support_0.16dex_samples_needed": round(n_needed(nt0, CURRENT_SUPPORT_DEX, sg0, p_target)),
        "at_0.5dex_samples_needed": round(n_needed(nt0, 0.5, sg0, p_target)),
        "at_1.0dex_samples_needed": round(n_needed(nt0, 1.0, sg0, p_target)),
        "interpretation": (
            f"At the current within-region Omega support (0.16 dex), detecting an Omega-exponent of "
            f"{nt0} needs ~{round(n_needed(nt0, CURRENT_SUPPORT_DEX, sg0, p_target))} co-located "
            f"ratio+Omega samples -- impractical. Widen the co-located Omega range to ~0.5 dex and it "
            f"drops to ~{round(n_needed(nt0, 0.5, sg0, p_target))}; at ~1.0 dex, ~"
            f"{round(n_needed(nt0, 1.0, sg0, p_target))}. So the binding lever is Omega SPAN, not sample "
            f"count -- the observing-system spec is 'span, then samples'."),
    }

    out = {
        "description": ("Quantified observing-system requirement to make the calcite Omega-power-law "
                        "closure ratio=R0*Omega^n identifiable. Frontier: n_true*S*sqrt(N)/(sigma*sqrt12) "
                        "= 1.96 + Phi^{-1}(power). Converts Paper #2's 'wider Omega' heuristic into a spec."),
        "assumptions": {"fit": "OLS log10(ratio)~n*log10(Omega); identifiable = 95% CI excludes 0",
                        "power_target": p_target, "current_within_region_support_dex": CURRENT_SUPPORT_DEX,
                        "sigma_note": "sigma = log10 residual scatter of the rain ratio; calibrate to "
                                      "the Marsh/Daniels within-basin residuals (swept 0.10-0.30 here)"},
        "grids": {"n_true": n_trues, "sigma": sigmas, "span_dex": spans, "n_samp": n_grid},
        "headline": headline,
        "frontier_samples_needed": frontier,
        "mc_validation": checks,
        "power_surface": surface,
    }
    print(json.dumps({"headline": headline, "mc_validation": checks}, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
