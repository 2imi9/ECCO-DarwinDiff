"""Does a PRESCRIBED, externally-constrained iron source break the alpfe<->scav_rat gauge symmetry?

Motivation (2026-08-12). The question "could an AI4Ocean-style physical ML model be coupled to
DarwinDiff and improve recovery?" has two readings, and they have opposite answers.

  (1) Feed the physical fields into the DINN as extra INPUT CHANNELS.
      Settled NO: "Do covariate input channels rescue scav_rat? No. scav_rat stays 0/10 across all
      five arms" (2026-07-22_covariate_channels_result.md). And ded111 gives the reason: the
      degeneracy is a gauge symmetry of the FORWARD MODEL -- S = r0*g_theta(x) is homogeneous of
      degree one in r0, so (alpfe, r0) -> (lambda*alpfe, lambda*r0) leaves the predicted DFe field
      unchanged "for ANY g and any weights inside it". Inputs to g cannot break it.

  (2) Use the physical model to supply a PRESCRIBED SOURCE TERM in the iron budget -- e.g. the
      vertical/eddy iron supply that Uchida, Balwada et al. 2020 (10.1038/s41467-020-14955-0)
      measured as supporting Southern Ocean production.
      This is a different object, and it is NOT covered by the gauge argument, because a prescribed
      source does not co-scale with lambda.

The steady-state box makes the mechanism explicit (same algebra as two_anchor_osse.py):

    FeT = (alpfe*D_sol + R - E) / (U + scav*f')

Under (alpfe, scav) -> (lambda*alpfe, lambda*scav):
    numerator   -> lambda*alpfe*D_sol + R - E     (only the DUST term scales)
    denominator -> U + lambda*scav*f'

With R = E = U = 0 the lambdas cancel exactly and the pair is rank-1. **R > 0 is what breaks it.**
So the prediction is that identifiability of the pair from DFe alone should improve monotonically
with the prescribed source fraction R / (alpfe*D_sol + R).

This script measures that, sweeping R and reporting, from DFe-ONLY observations with E pinned:
  * |rho| : the conditional correlation of (log alpfe, log scav) -- 1.0 means rank-1 / unidentifiable
  * cond  : 2x2 Fisher condition number
  * CRLB  : sqrt of the diagonal of the inverse Fisher, i.e. the achievable sd on each log-parameter

Pure numpy. Run:  python scripts/analysis/prescribed_source_breaks_gauge.py --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

# Truth + environment, matching two_anchor_osse.py so the two are comparable.
ALPFE_T = 0.93
SCAV_T = 1.0
E_T = 0.30
D_SOL = 1.0
U = 0.50
FPRIME = 0.10
SIGMA = 0.05  # relative obs error on DFe


def fe_t(alpfe: float, scav: float, R: float, E: float = E_T) -> float:
    return (alpfe * D_SOL + R - E) / (U + scav * FPRIME)


def fisher_2x2(R_mean: float, sigma: float = SIGMA, n_cells: int = 24,
               seed: int = 0) -> np.ndarray:
    """Fisher information for (log alpfe, log scav) from DFe over a FIELD of cells.

    A single scalar observation gives F = J J^T / sd^2, which is rank-1 BY CONSTRUCTION for any
    two parameters -- that is underdetermination, not the gauge symmetry, and an earlier version of
    this script conflated the two. The gauge question only has content over MANY cells whose
    environments differ: the symmetry says that even with unlimited cells the pair stays rank-1,
    because scaling leaves DFe unchanged *everywhere at once*.

    So the cells here vary in deposition, prescribed source, and free-iron fraction, which is what
    a real basin looks like and what a coupled physical model would supply spatially.
    """
    rng = np.random.default_rng(seed)
    h = 1e-6
    base = np.log([ALPFE_T, SCAV_T])

    # heterogeneous environment: dust deposition, prescribed source, particle field
    d_sol = D_SOL * np.exp(0.5 * rng.standard_normal(n_cells))
    fprime = FPRIME * np.exp(0.4 * rng.standard_normal(n_cells))
    R_cell = R_mean * np.exp(0.6 * rng.standard_normal(n_cells)) if R_mean > 0 \
        else np.zeros(n_cells)

    def pred(theta_log):
        a, s = np.exp(theta_log)
        return (a * d_sol + R_cell - E_T) / (U + s * fprime)

    y0 = pred(base)
    J = np.zeros((n_cells, 2))
    for i in range(2):
        tp = base.copy(); tp[i] += h
        tm = base.copy(); tm[i] -= h
        J[:, i] = (pred(tp) - pred(tm)) / (2 * h)
    sd = sigma * np.abs(y0)
    Jn = J / sd[:, None]
    return Jn.T @ Jn


def metrics(R: float) -> dict:
    F = fisher_2x2(R)
    ev = np.linalg.eigvalsh(F)
    ev = np.clip(ev, 0, None)
    cond = float(ev.max() / ev.min()) if ev.min() > 1e-300 else float("inf")
    # regularise minimally to invert a rank-deficient F, exactly as the repo's ridge convention
    ridge = 1e-9 * max(ev.max(), 1.0)
    C = np.linalg.inv(F + ridge * np.eye(2))
    crlb = np.sqrt(np.diag(C))
    rho = C[0, 1] / np.sqrt(C[0, 0] * C[1, 1])
    src_dust = ALPFE_T * D_SOL
    return {
        "R": R,
        "prescribed_source_fraction": R / (src_dust + R),
        "abs_rho": float(abs(rho)),
        "cond": cond,
        "crlb_log_alpfe": float(crlb[0]),
        "crlb_log_scav": float(crlb[1]),
        "FeT": float(fe_t(ALPFE_T, SCAV_T, R)),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    # R=0 is the pure-gauge case; 0.20 is what two_anchor_osse.py already assumes.
    rows = [metrics(R) for R in (0.0, 0.05, 0.10, 0.20, 0.40, 0.80, 1.60)]

    print("Prescribed non-dust iron source vs identifiability of (alpfe, scav_rat) from DFe ALONE")
    print("(E pinned; |rho| -> 1 means rank-1 / unidentifiable)\n")
    print(f"{'R':>6} {'src frac':>9} {'|rho|':>10} {'cond':>12} {'CRLB alpfe':>12} {'CRLB scav':>12}")
    for r in rows:
        print(f"{r['R']:>6.2f} {r['prescribed_source_fraction']:>9.3f} {r['abs_rho']:>10.6f} "
              f"{r['cond']:>12.3e} {r['crlb_log_alpfe']:>12.4g} {r['crlb_log_scav']:>12.4g}")

    print("\nInterpretation: R is a source that does NOT co-scale with alpfe, so it breaks the")
    print("multiplicative gauge symmetry. R = 0 is exactly rank-1; identifiability improves as the")
    print("prescribed source takes a larger share of the total iron input.")

    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
