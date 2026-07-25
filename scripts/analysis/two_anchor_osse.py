"""Two-anchor OSSE: does {dust-deposition source anchor + 234Th export-flux sink anchor}
break the alpfe<->scav_rat rank-1 degeneracy? — the decisive test from the Fable joint-inversion
methods synthesis (2026-07-22).

Physics the Fable workflow forced: surface/inventory DFe constrains only the combination
alpfe*D_sol/scav_rat (rank-1, structural). To point-identify each parameter you need two rows that
load source and sink DIFFERENTLY from the DFe ratio — two measurement TYPES from OUTSIDE the DFe
manifold: (C) an absolute soluble-Fe DEPOSITION anchor (source-weighted), and (B) a 234Th-derived
particulate export FLUX (sink-weighted). CRITICAL HONESTY: the Th flux is LUMPED (scavenging +
gravitational export), so scav_rat is point-identified only AFTER the export term E is pinned
(via UVP5 particle field / POC). This OSSE tests exactly that "partition tax": it runs each obs set
with the export nuisance E either PINNED (partition achieved) or FREE (partition not done).

Steady-state upper-ocean Fe box (self-twin; arbitrary units, only the identifiability GEOMETRY matters):
    0 = alpfe*D_sol + R - u*FeT - scav_rat*f'*FeT - E
    Fe' = FeT/(1+K'L)  (Darwin FIXED ligand)  =>  scav removal = scav_rat*f'*FeT, f' = f/(1+K'L)
    =>  FeT = (alpfe*D_sol + R - E) / (u + scav_rat*f')          [source/sink ratio => rank-1 in DFe]
Observation operators:
    DFe   = FeT                             (the shared manifold; combination-only)
    Dust  = alpfe*D_sol   (D_sol known)     (SOURCE row, out-of-manifold -> pins alpfe)
    Thflx = scav_rat*f'*FeT + E             (SINK row, LUMPED with export E)

Decisive criterion: (a) DFe-only => |rho(alpfe,scav)|~1, rank-1; (c) +Dust collapses the SOURCE axis;
(b) +Thflx collapses the SINK axis (only if E pinned); (d) +both => |rho|->0 and BOTH recovered
(only with the partition, i.e. E pinned). If (d) with E FREE stays sloppy, the partition tax is real.

Pure numpy/scipy. Run: python scripts/analysis/two_anchor_osse.py --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

# --- truth + fixed environment (self-twin) ------------------------------------
ALPFE_T = 0.93          # dust-solubility scalar (SOURCE)
SCAV_T = 1.0            # scavenging rate (SINK)
E_T = 0.30             # gravitational export (the lumped-removal nuisance)
D_SOL = 1.0            # soluble-Fe deposition (KNOWN, out-of-manifold)
R = 0.20              # remineralization source (prescribed)
U = 0.50              # biological uptake rate (fixed/known)
FPRIME = 0.10         # free-iron fraction f/(1+K'L) under fixed ligand
PARAM_NAMES = ["alpfe", "scav_rat", "E"]


def forward(alpfe, scav, E):
    """Return (DFe, Dust, Thflx) for given params."""
    FeT = (alpfe * D_SOL + R - E) / (U + scav * FPRIME)
    DFe = FeT
    Dust = alpfe * D_SOL
    Thflx = scav * FPRIME * FeT + E
    return np.array([DFe, Dust, Thflx])


# obs-set masks over (DFe, Dust, Thflx)
OBS_SETS = {
    "a_DFe_only":      np.array([1, 0, 0], dtype=bool),
    "b_DFe_Thflx":     np.array([1, 0, 1], dtype=bool),
    "c_DFe_Dust":      np.array([1, 1, 0], dtype=bool),
    "d_DFe_Dust_Thflx": np.array([1, 1, 1], dtype=bool),
}


def predict(theta_log, mask, free_E):
    """Prediction vector for the active obs, given log-params. If free_E, theta has 3 entries."""
    if free_E:
        alpfe, scav, E = np.exp(theta_log)
    else:
        alpfe, scav = np.exp(theta_log)
        E = E_T
    return forward(alpfe, scav, E)[mask]


def fisher(mask, free_E, sigma_frac):
    """FIM over params (alpfe, scav[, E]) for the active obs set. Returns (F, eig, rho_alpfe_scav)."""
    theta0 = np.log(np.array([ALPFE_T, SCAV_T, E_T]) if free_E else np.array([ALPFE_T, SCAV_T]))
    base_full = forward(ALPFE_T, SCAV_T, E_T)
    sigma = sigma_frac * np.abs(base_full[mask])
    base = predict(theta0, mask, free_E)
    p = len(theta0)
    J = np.zeros((mask.sum(), p))
    eps = 1e-5
    for k in range(p):
        tl = theta0.copy(); tl[k] += eps
        J[:, k] = (predict(tl, mask, free_E) - base) / eps
    F = (J.T / sigma**2) @ J
    # marginal correlation of alpfe,scav from F^{-1} (accounts for E nuisance if free)
    try:
        cov = np.linalg.inv(F)
        rho = cov[0, 1] / np.sqrt(cov[0, 0] * cov[1, 1])
        crlb = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        rho = float("nan"); crlb = np.full(p, np.inf)
    ev = np.sort(np.linalg.eigvalsh(F))[::-1]
    cond = ev[0] / ev[-1] if ev[-1] > 0 else float("inf")
    return {"eigenvalues": [float(x) for x in ev], "condition_number": float(cond),
            "rho_alpfe_scav": float(rho),
            "crlb_log_alpfe": float(crlb[0]), "crlb_log_scav": float(crlb[1])}


def recover(mask, free_E, sigma_frac, n_seeds, rng):
    """n-seed noisy-fit recovery of (alpfe, scav). Returns CV per param."""
    base_full = forward(ALPFE_T, SCAV_T, E_T)
    sigma = sigma_frac * np.abs(base_full[mask])
    truth_pred = base_full[mask]
    lo = np.log(np.array([1e-2, 1e-2, 1e-2] if free_E else [1e-2, 1e-2]))
    hi = np.log(np.array([1e2, 1e2, 1e2] if free_E else [1e2, 1e2]))
    recs = []
    for _ in range(n_seeds):
        noisy = truth_pred + rng.normal(0, sigma)
        th0 = np.log((np.array([ALPFE_T, SCAV_T, E_T]) if free_E else np.array([ALPFE_T, SCAV_T]))) \
            + rng.uniform(-1, 1, size=(3 if free_E else 2)) * np.log(10)
        th0 = np.clip(th0, lo, hi)
        def resid(tl):
            return (predict(tl, mask, free_E) - noisy) / sigma
        res = least_squares(resid, th0, bounds=(lo, hi), method="trf", max_nfev=300)
        recs.append(np.exp(res.x))
    recs = np.array(recs)
    return {"alpfe_cv": float(np.std(recs[:, 0]) / (np.mean(recs[:, 0]) + 1e-30)),
            "scav_cv": float(np.std(recs[:, 1]) / (np.mean(recs[:, 1]) + 1e-30)),
            "alpfe_med": float(np.median(recs[:, 0])), "scav_med": float(np.median(recs[:, 1]))}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-seeds", type=int, default=30)
    ap.add_argument("--noise-frac", type=float, default=0.05)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    rng = np.random.default_rng(0)

    result = {"truth": {"alpfe": ALPFE_T, "scav_rat": SCAV_T, "E": E_T}, "sets": {}}
    print(f"[2anchor] truth alpfe={ALPFE_T} scav={SCAV_T} E={E_T}; noise={args.noise_frac}", flush=True)
    print(f"{'obs set':20s} {'E':6s} {'|rho|':>7s} {'CRLB(scav)':>11s} {'cond':>10s} {'scav_CV':>8s}", flush=True)
    for name, mask in OBS_SETS.items():
        for free_E in (False, True):
            key = f"{name}__E_{'free' if free_E else 'pinned'}"
            fis = fisher(mask, free_E, args.noise_frac)
            rec = recover(mask, free_E, args.noise_frac, args.n_seeds, rng)
            result["sets"][key] = {"fisher": fis, "recovery": rec}
            print(f"{name:20s} {'free' if free_E else 'pin':6s} "
                  f"{abs(fis['rho_alpfe_scav']):7.3f} {fis['crlb_log_scav']:11.3f} "
                  f"{fis['condition_number']:10.1e} {rec['scav_cv']:8.3f}", flush=True)

    # verdict: does (d) break it? compare (a) vs (d, E pinned) and (d, E free)
    d_pin = result["sets"]["d_DFe_Dust_Thflx__E_pinned"]
    d_free = result["sets"]["d_DFe_Dust_Thflx__E_free"]
    a = result["sets"]["a_DFe_only__E_pinned"]
    def idd(s):  # identifiable if |rho|<0.5 AND crlb(scav)<0.3
        return abs(s["fisher"]["rho_alpfe_scav"]) < 0.5 and s["fisher"]["crlb_log_scav"] < 0.3
    if idd(d_pin) and idd(d_free):
        verdict = ("(a) BREAK ROBUST: both anchors identify alpfe AND scav_rat even with export E as a free "
                   "nuisance -> the two-anchor design breaks the degeneracy without a perfect partition.")
    elif idd(d_pin) and not idd(d_free):
        verdict = ("(a-) BREAK CONDITIONAL: the two anchors identify both params ONLY when export E is pinned "
                   "(partition achieved via UVP5/POC). With E free, scav_rat stays confounded -> the partition "
                   "tax is real and load-bearing; the dust anchor still cleanly pins alpfe regardless.")
    else:
        verdict = ("(b) NO CLEAN BREAK: even both anchors + pinned E do not identify scav_rat at this noise -> "
                   "the sink constraint is too weak; revisit noise/effective-N.")
    result["verdict"] = verdict
    # does the DUST anchor alone pin alpfe? (source axis)
    c_pin = result["sets"]["c_DFe_Dust__E_pinned"]
    result["dust_pins_alpfe"] = bool(c_pin["fisher"]["crlb_log_alpfe"] < 0.3)
    result["dfe_only_rank1"] = bool(abs(a["fisher"]["rho_alpfe_scav"]) > 0.9)

    print(f"\n=== VERDICT ===\n  DFe-only |rho|={abs(a['fisher']['rho_alpfe_scav']):.3f} (rank-1 if ~1)")
    print(f"  dust anchor pins alpfe: {result['dust_pins_alpfe']}")
    print(f"  d(E pinned): |rho|={abs(d_pin['fisher']['rho_alpfe_scav']):.3f} scav_CRLB={d_pin['fisher']['crlb_log_scav']:.3f}")
    print(f"  d(E free):   |rho|={abs(d_free['fisher']['rho_alpfe_scav']):.3f} scav_CRLB={d_free['fisher']['crlb_log_scav']:.3f}")
    print(f"  {verdict}", flush=True)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
