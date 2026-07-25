"""OSSE self-twin: does a 1-D iron COLUMN break the alpfe<->scav_rat rank-1 degeneracy
that a 0-D box cannot? — the cheap go/no-go from the 2026-07-22 bottleneck solution map.

The Track-1 bottleneck is that surface dissolved-iron (DFe) CONCENTRATION constrains only the
combination alpfe*dust/scav_rat (a rank-1 null; the same surface value is consistent with high
source/high sink or low source/low sink). The claim to test: the VERTICAL PROFILE separates them
because alpfe (a surface dust SOURCE) sets the profile AMPLITUDE while scav_rat (a volumetric SINK)
sets its SHAPE — the e-folding depth ~ sqrt(kz/scav_rat). If true, the profile Jacobian has a second
non-null direction the surface-scalar Jacobian lacks.

This is a self-twin (synthetic truth), so it isolates the identifiability GEOMETRY from real-data
confounds. It is honest in three ways:
  1. It compares the SAME truth fit two ways: a 0-D box (surface scalar only) vs a 1-D column (full
     profile). The box is a *mis-specified* surrogate; the column is the truth's own operator.
  2. It reports the Fisher/CRLB spectrum (deterministic) AND a noisy-fit recovery scatter (n seeds).
  3. It runs the kz-NUISANCE confound: if vertical diffusivity is unknown, the e-folding depth
     sqrt(kz/scav_rat) confounds kz and scav_rat — the "confound floor" the literature warns of
     (Pham & Ito 2018). A column that only separates when kz is known is a weaker result; report it.
  It also scans scav_rat across regimes (the Damkohler number scav*Z^2/kz) so we see WHERE in
  parameter space the profile actually helps, rather than cherry-picking one favorable point.

Decision rule:
  (a) column Fisher is well-conditioned (2nd eigenvalue >> box's ~0) AND scav_rat recovery tightens
      AND survives the kz-nuisance -> the profile breaks the degeneracy; build the real-data column.
  (b) column stays ill-conditioned or scav_rat dies under the kz-nuisance -> the confound dominates;
      fall back to reporting the stiff combination + a dust prior. Close by evidence.

Pure numpy/scipy, no external data (synthetic self-twin). Run:
  python scripts/analysis/column_osse_identifiability.py --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

# --- physical setup (years + metres; documented, realistic iron-cycle scales) ----------------
# kz interior ~1e-4 m^2/s ~= 3150 m^2/yr; iron scavenging timescale months-years -> scav ~0.1-5 /yr;
# e-folding depth sqrt(kz/scav) is then tens-hundreds of m (realistic). Absolute DFe units are
# arbitrary (self-twin); only the identifiability geometry matters.
KZ_TRUE = 3150.0          # m^2/yr
SCAV_TRUE = 1.0           # 1/yr   (nominal truth)
ALPFE_TRUE = 0.93         # dimensionless dust-solubility scalar (Carroll-ish)
DUST = 1.0                # surface dust-Fe flux (arbitrary units / m^2 / yr)
Z_MAX = 1500.0            # m
N_Z = 61                  # 25 m grid: resolves the ~56 m e-folding depth
H_MLD = 100.0             # mixed-layer depth for the 0-D box surrogate (m)
REMIN0_TRUE = 0.15        # background mid-depth iron regeneration amplitude (source units / m / yr)
Z_REMIN = 400.0           # depth of the remineralization source peak (m)
REMIN_W = 250.0           # width of the remineralization source (m)


def remin_profile(z, remin0=REMIN0_TRUE):
    """Prescribed iron regeneration from remineralized sinking organic Fe (alpfe/scav-independent)."""
    return remin0 * np.exp(-0.5 * ((z - Z_REMIN) / REMIN_W) ** 2)


def solve_column(alpfe, scav, kz, z, remin0=REMIN0_TRUE):
    """Steady-state 1-D DFe profile: 0 = kz*DFe'' - scav*DFe + S(z), zero-flux both ends.

    S(z) = alpfe*DUST at the surface cell (source/dz) + remin(z) at depth. Tridiagonal solve.
    Returns DFe[z] (>=0 for physical inputs).
    """
    nz = len(z)
    dz = z[1] - z[0]
    A = np.zeros((nz, nz))
    b = np.zeros(nz)
    src = remin_profile(z).copy()
    src[0] += alpfe * DUST / dz          # surface dust source (flux -> volumetric in top cell)
    for i in range(nz):
        if i == 0:                        # zero-flux top: DFe[-1]=DFe[0] mirror
            A[i, i] = -kz / dz**2 - scav
            A[i, i + 1] = kz / dz**2
        elif i == nz - 1:                 # zero-flux bottom
            A[i, i] = -kz / dz**2 - scav
            A[i, i - 1] = kz / dz**2
        else:
            A[i, i - 1] = kz / dz**2
            A[i, i] = -2 * kz / dz**2 - scav
            A[i, i + 1] = kz / dz**2
        b[i] = -src[i]
    dfe = np.linalg.solve(A, b)
    return dfe


def box_surface(alpfe, scav):
    """0-D mixed-layer box: source alpfe*DUST balanced by scav over depth H_MLD -> surface DFe scalar.

    d(DFe*H)/dt = alpfe*DUST - scav*DFe*H  ->  DFe = alpfe*DUST/(scav*H_MLD).  Rank-1 by construction:
    one scalar observation, two parameters, so surface DFe fixes only alpfe/scav.
    """
    return alpfe * DUST / (scav * H_MLD)


# --- Fisher / CRLB ---------------------------------------------------------------------------
def fisher_matrix(forward, theta_log, sigma, param_names):
    """Fisher information F = J^T J / sigma^2 with J = d(prediction)/d(log theta) (finite diff).

    forward(theta_phys) -> prediction vector (scalar-as-len-1 for the box). Log-space params so the
    sloppy direction is reported in decades. sigma = obs noise std (same units as prediction).
    Returns (F, J, eigvals, eigvecs).
    """
    theta = np.exp(theta_log)
    base = np.atleast_1d(forward(theta))
    m, p = len(base), len(theta)
    J = np.zeros((m, p))
    eps = 1e-4
    for k in range(p):
        tl = theta_log.copy()
        tl[k] += eps
        pred = np.atleast_1d(forward(np.exp(tl)))
        J[:, k] = (pred - base) / eps
    F = (J.T @ J) / sigma**2
    evals, evecs = np.linalg.eigh(F)
    return F, J, evals, evecs


def crlb_std(F):
    """Cramer-Rao lower-bound std per param = sqrt(diag(F^-1)); inf if singular (unidentified)."""
    try:
        cov = np.linalg.inv(F)
        d = np.diag(cov)
        return np.sqrt(np.where(d > 0, d, np.inf))
    except np.linalg.LinAlgError:
        return np.full(F.shape[0], np.inf)


def spectrum_summary(evals):
    evals = np.sort(evals)[::-1]
    lam_max = float(evals[0])
    lam_min = float(evals[-1])
    cond = lam_max / lam_min if lam_min > 0 else float("inf")
    return {"eigenvalues": [float(e) for e in evals],
            "lambda_max": lam_max, "lambda_min": lam_min,
            "condition_number": cond,
            "decades_sloppy": float(np.log10(cond)) if np.isfinite(cond) else float("inf")}


# --- noisy-fit recovery scatter --------------------------------------------------------------
def recover(forward, obs, theta0_log, sigma, bounds_log, seed_noise, param_names):
    """Fit log-params to noisy obs via least_squares; return recovered physical params."""
    def resid(tl):
        return (np.atleast_1d(forward(np.exp(tl))) - obs) / sigma
    lo = np.array([b[0] for b in bounds_log]); hi = np.array([b[1] for b in bounds_log])
    res = least_squares(resid, theta0_log, bounds=(lo, hi), method="trf", max_nfev=200)
    return np.exp(res.x)


def recovery_scatter(forward, truth_phys, obs_operator, sigma, bounds_log, n_seeds, param_names, rng):
    """n_seeds noisy realizations -> recovered param scatter (CV per param)."""
    truth_pred = obs_operator(truth_phys)
    recs = []
    theta0 = np.log(truth_phys)
    for s in range(n_seeds):
        noisy = truth_pred + rng.normal(0, sigma, size=np.atleast_1d(truth_pred).shape)
        # random init off-truth to probe the ridge (up to +-1 decade)
        init = theta0 + rng.uniform(-1.0, 1.0, size=len(theta0)) * np.log(10)
        init = np.clip(init, [b[0] for b in bounds_log], [b[1] for b in bounds_log])
        recs.append(recover(forward, noisy, init, sigma, bounds_log, s, param_names))
    recs = np.array(recs)
    out = {}
    for k, nm in enumerate(param_names):
        v = recs[:, k]
        out[nm] = {"true": float(truth_phys[k]), "median": float(np.median(v)),
                   "cv": float(np.std(v) / (np.mean(v) + 1e-30)),
                   "log10_spread": float(np.std(np.log10(v)))}
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-seeds", type=int, default=20)
    ap.add_argument("--noise-frac", type=float, default=0.05, help="obs noise as fraction of signal std")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    z = np.linspace(0, Z_MAX, N_Z)
    rng = np.random.default_rng(0)
    result = {"setup": {"kz_true": KZ_TRUE, "scav_true": SCAV_TRUE, "alpfe_true": ALPFE_TRUE,
                        "z_max": Z_MAX, "n_z": N_Z, "H_MLD": H_MLD, "n_seeds": args.n_seeds,
                        "efolding_depth_m": float(np.sqrt(KZ_TRUE / SCAV_TRUE)),
                        "damkohler_scavZ2_kz": float(SCAV_TRUE * Z_MAX**2 / KZ_TRUE)}}

    # truth profile + obs noise scales
    dfe_true = solve_column(ALPFE_TRUE, SCAV_TRUE, KZ_TRUE, z)
    surf_true = box_surface(ALPFE_TRUE, SCAV_TRUE)
    sig_prof = args.noise_frac * float(np.std(dfe_true))
    sig_surf = args.noise_frac * float(abs(surf_true))
    theta_log = np.log(np.array([ALPFE_TRUE, SCAV_TRUE]))
    bounds2 = [(np.log(1e-2), np.log(1e2)), (np.log(1e-2), np.log(1e2))]

    print(f"[osse] e-folding depth = {np.sqrt(KZ_TRUE/SCAV_TRUE):.0f} m, "
          f"Damkohler scav*Z^2/kz = {SCAV_TRUE*Z_MAX**2/KZ_TRUE:.1f}", flush=True)

    # ---- (1) Fisher spectra: 0-D box (surface scalar) vs 1-D column (full profile) ----
    def fwd_box(theta):  # theta=[alpfe,scav]
        return np.array([box_surface(theta[0], theta[1])])
    def fwd_col(theta):
        return solve_column(theta[0], theta[1], KZ_TRUE, z)

    F_box, _, ev_box, evec_box = fisher_matrix(fwd_box, theta_log, sig_surf, ["alpfe", "scav"])
    F_col, _, ev_col, evec_col = fisher_matrix(fwd_col, theta_log, sig_prof, ["alpfe", "scav"])
    result["box_fisher"] = spectrum_summary(ev_box)
    result["column_fisher"] = spectrum_summary(ev_col)
    crlb_box = crlb_std(F_box); crlb_col = crlb_std(F_col)
    result["box_fisher"]["crlb_log_alpfe_scav"] = [float(crlb_box[0]), float(crlb_box[1])]
    result["column_fisher"]["crlb_log_alpfe_scav"] = [float(crlb_col[0]), float(crlb_col[1])]
    print(f"[osse] BOX   Fisher eigs={result['box_fisher']['eigenvalues']}  "
          f"cond={result['box_fisher']['condition_number']:.2e}  "
          f"CRLB(log scav)={crlb_box[1]:.3f}", flush=True)
    print(f"[osse] COLUMN Fisher eigs={result['column_fisher']['eigenvalues']}  "
          f"cond={result['column_fisher']['condition_number']:.2e}  "
          f"CRLB(log scav)={crlb_col[1]:.3f}", flush=True)

    # ---- (2a) kz-NUISANCE confound: column with [alpfe, scav, kz] all free ----
    theta3 = np.log(np.array([ALPFE_TRUE, SCAV_TRUE, KZ_TRUE]))
    def fwd_col3(theta):
        return solve_column(theta[0], theta[1], theta[2], z)
    F3, _, ev3, _ = fisher_matrix(fwd_col3, theta3, sig_prof, ["alpfe", "scav", "kz"])
    crlb3 = crlb_std(F3)
    result["column_fisher_kz_nuisance"] = spectrum_summary(ev3)
    result["column_fisher_kz_nuisance"]["crlb_log_alpfe_scav_kz"] = [float(x) for x in crlb3]
    print(f"[osse] COLUMN+kz-nuisance eigs={[f'{e:.1f}' for e in result['column_fisher_kz_nuisance']['eigenvalues']]}  "
          f"cond={result['column_fisher_kz_nuisance']['condition_number']:.2e}  "
          f"CRLB(log scav)={crlb3[1]:.3f}", flush=True)

    # ---- (2b) FULL confound floor: [alpfe, scav, kz, remin0] all free (Pham & Ito confounds) ----
    theta4 = np.log(np.array([ALPFE_TRUE, SCAV_TRUE, KZ_TRUE, REMIN0_TRUE]))
    def fwd_col4(theta):
        return solve_column(theta[0], theta[1], theta[2], z, remin0=theta[3])
    F4, _, ev4, _ = fisher_matrix(fwd_col4, theta4, sig_prof, ["alpfe", "scav", "kz", "remin0"])
    crlb4 = crlb_std(F4)
    result["column_fisher_kz_remin_nuisance"] = spectrum_summary(ev4)
    result["column_fisher_kz_remin_nuisance"]["crlb_log_alpfe_scav_kz_remin"] = [float(x) for x in crlb4]
    print(f"[osse] COLUMN+kz+remin-nuisance eigs={[f'{e:.1f}' for e in result['column_fisher_kz_remin_nuisance']['eigenvalues']]}  "
          f"cond={result['column_fisher_kz_remin_nuisance']['condition_number']:.2e}  "
          f"CRLB(log scav)={crlb4[1]:.3f}", flush=True)

    # ---- (3) noisy-fit recovery scatter, box vs column ----
    box_rec = recovery_scatter(fwd_box, np.array([ALPFE_TRUE, SCAV_TRUE]),
                               lambda th: np.array([box_surface(th[0], th[1])]),
                               sig_surf, bounds2, args.n_seeds, ["alpfe", "scav"], rng)
    col_rec = recovery_scatter(fwd_col, np.array([ALPFE_TRUE, SCAV_TRUE]),
                               lambda th: solve_column(th[0], th[1], KZ_TRUE, z),
                               sig_prof, bounds2, args.n_seeds, ["alpfe", "scav"], rng)
    result["box_recovery"] = box_rec
    result["column_recovery"] = col_rec
    print(f"[osse] BOX   recovery scav CV={box_rec['scav']['cv']:.2f} "
          f"(log10 spread {box_rec['scav']['log10_spread']:.2f} decades)", flush=True)
    print(f"[osse] COLUMN recovery scav CV={col_rec['scav']['cv']:.2f} "
          f"(log10 spread {col_rec['scav']['log10_spread']:.2f} decades)", flush=True)

    # ---- (4) regime scan: column condition number vs scav_rat (Damkohler sweep) ----
    scan = []
    for scav in np.geomspace(0.05, 20.0, 12):
        dfe = solve_column(ALPFE_TRUE, scav, KZ_TRUE, z)
        sig = args.noise_frac * float(np.std(dfe)) or 1e-12
        tl = np.log(np.array([ALPFE_TRUE, scav]))
        _, _, ev, _ = fisher_matrix(fwd_col, tl, sig, ["alpfe", "scav"])
        ss = spectrum_summary(ev)
        scan.append({"scav": float(scav), "damkohler": float(scav * Z_MAX**2 / KZ_TRUE),
                     "condition_number": ss["condition_number"],
                     "efolding_depth_m": float(np.sqrt(KZ_TRUE / scav))})
    result["regime_scan"] = scan

    # ---- verdict (keyed on the CRLB of log scav_rat, the honest identifiability metric — NOT the raw
    #      condition number, which reflects alpfe being far better determined than scav, not a scav null) ----
    crlb_scav_box = float(crlb_box[1])
    crlb_scav_col = float(crlb_col[1])
    crlb_scav_kz = float(crlb3[1])
    crlb_scav_full = float(crlb4[1])
    box_scav_cv = box_rec["scav"]["cv"]; col_scav_cv = col_rec["scav"]["cv"]
    # "identifiable" = CRLB(log scav) < 0.3 decades (scav to within ~a factor of 2); box is ~inf.
    ID = 0.3
    box_id = crlb_scav_box < ID
    col_id = crlb_scav_col < ID
    full_id = crlb_scav_full < ID
    if (not box_id) and col_id and full_id:
        verdict = ("(a) PROFILE BREAKS IT: the 1-D column makes scav_rat identifiable where the 0-D box "
                   "cannot, AND scav_rat survives the full kz+remin nuisance floor -> build the real-data "
                   "1-D column fit (idealized self-twin; real confounds are richer, see caveats).")
    elif (not box_id) and col_id and not full_id:
        verdict = ("(a-) the column separates scav_rat WHEN confounds are known, but the kz+remin nuisance "
                   "floor re-inflates its uncertainty -> the real build needs independent kz/remin "
                   "constraints; the profile helps but is not self-sufficient.")
    else:
        verdict = ("(b) CONFOUND DOMINATES: the column does not cleanly separate alpfe/scav_rat -> fall "
                   "back to the stiff combination + dust prior; close the profile route by evidence.")
    result["verdict"] = verdict
    result["crlb_log_scav"] = {"box": crlb_scav_box, "column": crlb_scav_col,
                               "column_kz_nuisance": crlb_scav_kz, "column_kz_remin_nuisance": crlb_scav_full}
    print(f"\n=== VERDICT (metric = CRLB on log10 scav_rat; <{ID} = identifiable) ===")
    print(f"  CRLB(log scav):  box={crlb_scav_box:.2e}  column={crlb_scav_col:.3f}  "
          f"+kz={crlb_scav_kz:.3f}  +kz+remin={crlb_scav_full:.3f}")
    print(f"  scav recovery CV: box={box_scav_cv:.2f} -> column={col_scav_cv:.2f}")
    print(f"  {verdict}", flush=True)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
