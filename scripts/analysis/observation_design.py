#!/usr/bin/env python3
r"""observation_design.py -- DIFFERENTIABLE OBSERVATION DESIGN for the iron degeneracy.

The paper's genuinely-novel contribution is a METHOD, not a finding. "The alpfe/
scav_rat iron degeneracy exists" is not novel (Frants et al. showed compensating
source/scavenging families; FeMIP documented the inter-model spread). What is
defensible is: *use the differentiable 0-D surrogate to compute WHICH new
observation would most shrink the sloppy (degenerate) iron direction* -- optimal
experimental design (OED) via the surrogate's Fisher information.

Because the box is differentiable, the sensitivity of ANY candidate observable to
each Carroll-6 parameter is a cheap Jacobian row j = d(observable)/d(theta). Adding
a hypothetical survey of that observable is a rank-structured Fisher update
F -> F + F_obs, and we can score each candidate BEFORE any cruise is funded by how
much it lifts the smallest eigenvalue / shrinks the posterior variance along the
degenerate iron combination the concentration data leaves free.

Scientifically-motivated hypothesis: a SCAVENGING-FLUX observable (a 234Th/210Po-
derived particulate-Fe removal rate) should separate scav_rat from alpfe far better
than another concentration measurement, because the box's scavenging sink is
    scav_flux = scav_rat * 86400 * DFe * POC        (the 234Th/210Po proxy)
which multiplies scav_rat EXPLICITLY, whereas surface [DFe] sees scav_rat only
through the steady-state balance -- exactly the balance the source term alpfe*PHI
can compensate. The concentration is blind to the (alpfe up, scav_rat up, [DFe]
fixed) trade-off; the flux is not.

METHOD (this script)
--------------------
1. Reuse the runner (NB23_N_EPOCHS=0 no-op) exactly as identifiability_sloppiness.py
   does: import it, take R.bundles / R.aoi_loss / the integrated box state. A single
   batched integration over the "seed" axis carries Carroll + all central-difference
   perturbations, so the full 6-parameter Jacobian of every candidate observable is
   ONE integration per AOI.
2. Build a dimensionless, magnitude-normalised Gauss-Newton Fisher for each candidate
   observable (each treated as a survey of the AOI ocean cells measured with the SAME
   unit fractional noise -- an equal-footing comparison of observable TYPE, matching
   the runner's per-AOI residual scaling scale=mean(target^2)).
3. Base Fisher F0 = surface-DFe concentration ("iron concentration only"). Extract the
   iron 2x2 sub-block {alpfe, scav_rat}, its sloppy eigenvector v (smallest eigenvalue)
   and posterior correlation (should be strongly negative, ~ the reported -0.77).
4. For each candidate, F1 = F0 + F_obs. Score by:
     - var_reduction_sloppy = (v^T F0^-1 v) / (v^T F1^-1 v)   [PRIMARY]
     - iron-block condition-number and smallest-eigenvalue lift
     - D-optimality gain logdet(F1_iron) - logdet(F0_iron)
     - alignment: |cos(top eigenvector of F_obs_iron , v)|  -- the geometric reason.
   Rank candidates by var_reduction_sloppy.

Honesty guards: each observable's magnitude and whether its relative sensitivity is
above the float32 finite-difference floor are reported; an observable whose iron-block
sensitivity is numerically negligible is flagged UNINFORMATIVE (var_reduction ~ 1),
which is the correct answer for bSi/PIC (they constrain other parameters, not iron).

Usage (AICR B200, env configured exactly like the runner / dust sbatch):
  AOIS=eqpac,natlsubpolar,southernoceanpac GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0 \
    AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 USE_EPPLEY_T=1 \
    ~/dd_venv/bin/python scripts/analysis/observation_design.py \
      --out docs/findings/2026-07-23_observation_design.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]


def _import_runner():
    """Import the runner with training disabled (mirrors identifiability_sloppiness._import_runner)."""
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    os.environ.setdefault("TORCH_COMPILE_BATCHED", "0")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_obsdesign_")
    runner_path = ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py"
    spec = importlib.util.spec_from_file_location("_dd_runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rel-eps", type=float, default=2e-2,
                    help="relative finite-difference step for the Jacobian (matches the "
                         "identifiability_sloppiness Hessian FD).")
    ap.add_argument("--tau", type=float, default=1e-2,
                    help="weak isotropic Bayesian prior (dimensionless) for the full-6 "
                         "cross-check only; the primary 2x2 iron metric is prior-free.")
    ap.add_argument("--out", default=None, help="write JSON verdict here")
    args = ap.parse_args()

    import torch

    from darwindiff.carroll6 import CARROLL_VALUES, K_FE, PHI_DUST, Q_FE

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss

    I_DFE_1, I_DFE_2 = R.I_DFE_1, R.I_DFE_2
    I_POC_1, I_POC_2 = R.I_POC_1, R.I_POC_2
    I_PIC_1 = R.I_PIC_1
    I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL = (
        R.I_DIATOM, R.I_LGE, R.I_SYN, R.I_PROLL, R.I_PROHL)
    Pn = R.P  # named parameter indices (P.alpfe == 0, P.scav_rat == 1, ...)

    _base_state0 = {b["key"]: b["state0_per_seed"] for b in bundles}

    def set_seeds(S):
        for b in bundles:
            base = _base_state0[b["key"]]
            b["state0_per_seed"] = base[:, :1].expand(base.shape[0], S, base.shape[2], base.shape[3])

    aois = [b["key"] for b in bundles]
    weights = {b["key"]: float(b["weight"]) for b in bundles}
    carroll = CARROLL_VALUES.to(dev).float()  # [6]

    print(f"\n=== DIFFERENTIABLE OBSERVATION DESIGN | AOIS={aois} | weights={weights} ===")
    print(f"    Carroll theta: " + "  ".join(f"{PARAM_NAMES[i]}={float(carroll[i]):.4g}"
                                             for i in range(6)))

    # --------------------------------------------------------------------------
    # Candidate observables. Each maps (state [15,S,H,W], params_b [6,S,H,W]) -> field [S,H,W].
    # 'base' = the existing constraint (surface FeT concentration). All others are
    # candidate NEW surveys. Two "concentration" controls (dfe_surf_2, poc_surf) and two
    # other-parameter controls (pic_surf, bsi_surf) bracket the two flux hypotheses.
    # --------------------------------------------------------------------------
    def _feupt(state, pb):
        """Biological Fe uptake flux Q_FE * growth_total (the bio arm of the iron sink),
        replicating the runner's PINN-block growth expression (aoi_loss lines ~1701-1710)."""
        f_fe = state[I_DFE_1] / (state[I_DFE_1] + K_FE)
        mu_lge = pb[Pn.Biggrow]
        mu_proHL = pb[Pn.Smallgrow]
        growth_total = (
            R.MU_DEFAULT_DIATOM * f_fe * state[I_DIATOM]
            + mu_lge * f_fe * state[I_LGE]
            + R.MU_DEFAULT_SYN * f_fe * state[I_SYN]
            + R.MU_DEFAULT_PROLL * f_fe * state[I_PROLL]
            + mu_proHL * f_fe * state[I_PROHL]
        )
        return Q_FE * growth_total

    def _scavflux(state, pb, i_dfe, i_poc):
        """Particulate-Fe scavenging removal rate scav_rat_per_day * DFe * POC
        (the 234Th/210Po-derived flux proxy). scav_rat enters EXPLICITLY here."""
        return pb[Pn.scav_rat] * 86400.0 * state[i_dfe] * state[i_poc]

    def _bsi(state, pb):
        bsi_1, _ = R.diagnostic_bsi_steady(state[I_DIATOM], pb[Pn.diatomgraz])
        return bsi_1

    OBS = {
        "dfe_surf":     ("surface dissolved Fe (FeT) concentration [BASE]",
                         lambda st, pb: st[I_DFE_1]),
        "dfe_surf_2":   ("2nd independent surface-FeT survey (control: more of same)",
                         lambda st, pb: st[I_DFE_1]),
        "dfe_sub":      ("subsurface dissolved Fe (FeT) concentration",
                         lambda st, pb: st[I_DFE_2]),
        "poc_surf":     ("surface POC concentration (control: unrelated concentration)",
                         lambda st, pb: st[I_POC_1]),
        "pic_surf":     ("surface PIC / calcite (control: constrains R_PICPOC)",
                         lambda st, pb: st[I_PIC_1]),
        "bsi_surf":     ("surface biogenic silica bSi (control: constrains diatomgraz)",
                         _bsi),
        "feupt_surf":   ("biological Fe uptake flux Q_FE*growth (iron sink, bio arm)",
                         _feupt),
        "scavflux_surf":("surface particulate-Fe scavenging flux (234Th/210Po proxy) [HYP]",
                         lambda st, pb: _scavflux(st, pb, I_DFE_1, I_POC_1)),
        "scavflux_sub": ("subsurface scavenging flux (234Th/210Po proxy, deep) [HYP]",
                         lambda st, pb: _scavflux(st, pb, I_DFE_2, I_POC_2)),
    }
    obs_keys = list(OBS.keys())
    BASE_KEY = "dfe_surf"

    # --------------------------------------------------------------------------
    # ONE batched integration per AOI carries Carroll (col 0) + 12 central-difference
    # perturbation columns (2 per parameter). Assemble per-observable, per-cell
    # Jacobians and the dimensionless, per-AOI-magnitude-normalised Fisher.
    #   F_o = sum_b w_b * (1/N_b) * G_b^T G_b ,  G_b[cell,i] = |theta_i| * dy/dtheta_i / rms_b(y)
    # matching the runner's per-AOI residual scaling (scale = mean(target^2)).
    # --------------------------------------------------------------------------
    S = 1 + 2 * 6  # Carroll + +/- for each of 6 params
    eps = args.rel_eps * carroll.abs().clamp(min=1e-30)  # [6]
    theta_cols = carroll.reshape(6, 1).repeat(1, S).clone()  # [6, S]
    col = 1
    pert_col = {}
    for i in range(6):
        theta_cols[i, col] += eps[i]; pert_col[(i, "+")] = col; col += 1
        theta_cols[i, col] -= eps[i]; pert_col[(i, "-")] = col; col += 1

    scale_v = carroll.abs().clamp(min=1e-30)  # |theta| dimensionless scaling

    # F_o accumulators (dimensionless 6x6), one per observable.
    F = {k: torch.zeros(6, 6, device=dev, dtype=torch.float64) for k in obs_keys}
    obs_mag = {k: {"rms_by_aoi": [], "mean_by_aoi": []} for k in obs_keys}
    fd_floor_flag = {k: False for k in obs_keys}

    set_seeds(S)
    with torch.no_grad():
        for b in bundles:
            H, W = b["mask_f"].shape
            pb = theta_cols.reshape(6, S, 1, 1).expand(6, S, H, W)
            _, state = aoi_loss(b, pb)  # state [15, S, H, W]
            ocean = (b["mask_f"] > 0).reshape(-1)          # [H*W]
            n_b = int(ocean.sum())
            w_b = float(b["weight"])
            for k in obs_keys:
                fn = OBS[k][1]
                y = fn(state, pb).reshape(S, -1)[:, ocean]  # [S, n_b]
                y0 = y[0]                                    # Carroll column
                rms2 = float((y0.double() ** 2).mean().clamp(min=1e-30))
                rms = math.sqrt(rms2)
                obs_mag[k]["rms_by_aoi"].append(rms)
                obs_mag[k]["mean_by_aoi"].append(float(y0.double().mean()))
                # per-cell Jacobian [n_b, 6] via central difference
                Jb = torch.zeros(n_b, 6, device=dev, dtype=torch.float64)
                for i in range(6):
                    yp = y[pert_col[(i, "+")]].double()
                    ym = y[pert_col[(i, "-")]].double()
                    Jb[:, i] = (yp - ym) / (2.0 * float(eps[i]))
                # FD-floor check: is the relative Jacobian signal above float32 noise?
                rel_sig = float((Jb.abs().max(dim=0).values * scale_v.double() / max(rms, 1e-30)).max())
                if rel_sig < 1e-4:
                    fd_floor_flag[k] = True
                # dimensionless, magnitude-normalised residual-gradient
                Gb = (Jb * scale_v.double()[None, :]) / rms          # [n_b, 6]
                F[k] += w_b * (Gb.t() @ Gb) / max(n_b, 1)

    for k in obs_keys:
        F[k] = 0.5 * (F[k] + F[k].t())

    # --------------------------------------------------------------------------
    # Iron 2x2 sub-block analysis (PRIOR-FREE primary metric).
    # --------------------------------------------------------------------------
    ia, isc = PARAM_NAMES.index("alpfe"), PARAM_NAMES.index("scav_rat")

    def iron2(M):
        return M[[ia, isc]][:, [ia, isc]].clone()

    def cond2(M2):
        e = torch.linalg.eigvalsh(0.5 * (M2 + M2.t()))
        emin, emax = float(e[0]), float(e[-1])
        return (emax / emin) if emin > 0 else float("inf"), emin, emax

    F0_iron = iron2(F[BASE_KEY])
    e0, V0 = torch.linalg.eigh(0.5 * (F0_iron + F0_iron.t()))
    v_sloppy = V0[:, 0]        # smallest-eigenvalue eigenvector = degenerate iron combo
    v_stiff = V0[:, 1]
    lam_min0, lam_max0 = float(e0[0]), float(e0[1])
    cond0 = (lam_max0 / lam_min0) if lam_min0 > 0 else float("inf")
    # posterior correlation of (alpfe, scav_rat) under the base iron block
    C0 = torch.linalg.inv(F0_iron + 1e-12 * torch.eye(2, dtype=torch.float64, device=dev))
    rho0 = float(C0[0, 1] / (C0[0, 0] * C0[1, 1]).clamp(min=1e-60).sqrt())
    var0_sloppy = float(v_sloppy @ C0 @ v_sloppy)

    print(f"\n-- BASE Fisher F0 = {OBS[BASE_KEY][0]} --")
    print(f"   iron 2x2 eigenvalues: sloppy={lam_min0:.3e}  stiff={lam_max0:.3e}  "
          f"cond={cond0:.1f}")
    print(f"   sloppy (degenerate) direction: alpfe {float(v_sloppy[0]):+.3f}  "
          f"scav_rat {float(v_sloppy[1]):+.3f}")
    print(f"   stiff  (constrained) direction: alpfe {float(v_stiff[0]):+.3f}  "
          f"scav_rat {float(v_stiff[1]):+.3f}")
    print(f"   posterior corr(alpfe, scav_rat) = {rho0:+.3f}  "
          f"({'DEGENERATE' if abs(rho0) > 0.7 else 'partially separable'})")

    # --------------------------------------------------------------------------
    # Score each candidate: F1 = F0 + F_obs.
    # --------------------------------------------------------------------------
    I6 = torch.eye(6, dtype=torch.float64, device=dev)
    tau = args.tau
    F0_full = F[BASE_KEY] + tau * I6
    C0_full = torch.linalg.inv(F0_full)
    v6 = torch.zeros(6, dtype=torch.float64, device=dev)
    v6[ia] = v_sloppy[0]; v6[isc] = v_sloppy[1]
    var0_full = float(v6 @ C0_full @ v6)

    results = []
    for k in obs_keys:
        if k == BASE_KEY:
            continue
        F1_iron = F0_iron + iron2(F[k])
        C1 = torch.linalg.inv(F1_iron + 1e-12 * torch.eye(2, dtype=torch.float64, device=dev))
        var1_sloppy = float(v_sloppy @ C1 @ v_sloppy)
        var_red = var0_sloppy / max(var1_sloppy, 1e-300)
        c1, emin1, emax1 = cond2(F1_iron)
        lam_lift = emin1 / max(lam_min0, 1e-300)
        logdet_gain = float(torch.logdet(F1_iron) - torch.logdet(F0_iron))

        # alignment of the observable's best-constrained iron direction with v_sloppy
        Fo_iron = iron2(F[k])
        eo, Vo = torch.linalg.eigh(0.5 * (Fo_iron + Fo_iron.t()))
        iron_info = float(eo[-1])  # top eigenvalue of the observable's iron block
        base_iron_scale = float(torch.linalg.eigvalsh(F0_iron)[-1])
        if iron_info > 1e-6 * base_iron_scale:
            u_top = Vo[:, -1]
            alignment = abs(float(u_top @ v_sloppy))
        else:
            alignment = float("nan")  # observable has no iron sensitivity

        # full-6 cross-check (weak prior)
        F1_full = F[k] + F0_full  # = F0 + F_obs + tau I
        C1_full = torch.linalg.inv(F1_full)
        var1_full = float(v6 @ C1_full @ v6)
        var_red_full = var0_full / max(var1_full, 1e-300)

        results.append({
            "obs": k, "desc": OBS[k][0],
            "var_reduction_sloppy": var_red,
            "var_reduction_full6": var_red_full,
            "iron_cond_after": c1, "iron_lambda_min_lift": lam_lift,
            "logdet_gain_iron": logdet_gain,
            "alignment_with_sloppy": alignment,
            "iron_block_top_eig": iron_info,
            "obs_rms_by_aoi": obs_mag[k]["rms_by_aoi"],
            "fd_floor_uninformative": fd_floor_flag[k],
        })

    results.sort(key=lambda r: r["var_reduction_sloppy"], reverse=True)

    print("\n-- CANDIDATE RANKING (by posterior-variance reduction along the sloppy iron direction) --")
    print(f"   base iron condition number = {cond0:.1f}  (higher = more degenerate)")
    hdr = f"{'observable':<15}{'var_red':>10}{'cond_after':>12}{'lam_lift':>10}{'align':>8}  note"
    print(hdr)
    print("   " + "-" * (len(hdr)))
    for r in results:
        note = "UNINFORMATIVE for iron" if r["fd_floor_uninformative"] or r["var_reduction_sloppy"] < 1.05 else ""
        al = f"{r['alignment_with_sloppy']:.2f}" if r["alignment_with_sloppy"] == r["alignment_with_sloppy"] else " -- "
        cond_after = r["iron_cond_after"]
        cond_s = f"{cond_after:.1f}" if math.isfinite(cond_after) else "inf"
        print(f"   {r['obs']:<15}{r['var_reduction_sloppy']:>10.2f}{cond_s:>12}"
              f"{r['iron_lambda_min_lift']:>10.2f}{al:>8}  {note}")

    best = results[0]
    print(f"\n   WINNER: {best['obs']} -- var reduction {best['var_reduction_sloppy']:.1f}x, "
          f"iron condition number {cond0:.0f} -> {best['iron_cond_after']:.1f}")

    out = {
        "method": "differentiable_observation_design_fisher_OED",
        "aois": aois, "weights": weights, "rel_eps": args.rel_eps, "tau_full6": tau,
        "carroll": {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)},
        "base_observable": BASE_KEY, "base_desc": OBS[BASE_KEY][0],
        "base_iron_block": {
            "eig_sloppy": lam_min0, "eig_stiff": lam_max0, "condition_number": cond0,
            "sloppy_direction": {"alpfe": float(v_sloppy[0]), "scav_rat": float(v_sloppy[1])},
            "stiff_direction": {"alpfe": float(v_stiff[0]), "scav_rat": float(v_stiff[1])},
            "posterior_corr_alpfe_scav": rho0,
        },
        "observable_magnitudes": {k: obs_mag[k] for k in obs_keys},
        "ranking": results,
        "winner": best["obs"],
        "note": "F_obs = per-AOI weighted, magnitude-normalised (scale=mean(y^2)) Gauss-Newton "
                "Fisher of each candidate observable, dimensionless (scaled by |theta_Carroll|), "
                "over ocean-mask cells. Primary metric var_reduction_sloppy is the prior-free 2x2 "
                "iron-block posterior-variance ratio along v (base sloppy eigenvector). "
                "var_reduction_full6 is the weak-prior (tau I) full-6 cross-check. "
                "fd_floor_uninformative flags observables whose iron sensitivity is below the "
                "float32 finite-difference floor (correct for bSi/PIC: they constrain other params).",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
