#!/usr/bin/env python3
r"""identifiability_sloppiness.py -- Fisher/Hessian + profile-likelihood diagnostic
for the 6 GLOBAL Carroll-6 parameters, reusing the runner's EXACT per-AOI loss.

Why this exists
---------------
The growth-pair / iron-pair recovery wall is blocked by an unresolved question
(deep-research synthesis 2026-06-25): is the alpfe collapse on adding the
oligotrophic gyre (npsg) *structural non-identifiability* (a single shared alpfe is
mis-specified across the HNLC eq-Pacific and the dust-fed gyre -> only a new
observable / regional iron param helps) or *practical non-identifiability* (a
directional conflict that gradient gating / reweighting can legitimately resolve)?

Raue et al. 2009 (Bioinformatics 25:1923) give the decisive test: PROFILE-LIKELIHOOD.
Fix one parameter on a grid, re-optimise the rest, read the curve.
  * FLAT profile  => structural non-identifiability (invisible to any amount of this
                     data) -> AOI-reweighting is dead; need a new observable/structure.
  * CURVED/one-sided => practical non-identifiability -> routing/pooling is licensed.

This is the documented blind spot: STATUS.md lists a Fisher/Hessian diagnostic as NOT
available, and a prior note falsely cited a `scripts/identifiability_sloppiness.py`
that never existed. This is that file, built for real.

What it does
------------
Imports ``run_v3.0_joint_multi_aoi`` with NB23_N_EPOCHS=0 (the training loop becomes
``range(0)`` -- a no-op) and gated behind the runner's ``if __name__ == "__main__"``
guard, so the REAL per-AOI bundles (targets/masks/IC/forcing) and the EXACT
``aoi_loss`` are available without running training/recovery. It evaluates the JOINT
loss as a function of a single SHARED theta[6] held CONSTANT across all cells -- the
global-parameter object Carroll's Green's-functions optimisation tuned (the DINN's
per-cell freedom is over-parameterised machinery; the reported "recovered" value is
the cell mean of a global parameter).

Gating is intentionally bypassed: it is a backward-pass gradient mask (forward value
unchanged), so it would corrupt the curvature. We analyse the true ungated loss.

Speed: the runner's loss is batched over a "seed" axis. We exploit that to vectorise
the profile -- every grid point re-optimises in ONE integration -- and finite-difference
the gradient for the 6x6 Hessian (no slow double-backward through compiled code).

Outputs (per config -- run once for 3-AOI, once for 4-AOI to compare):
  1. shared-theta optimum theta* (vs Carroll) + scale-relative gradient norm.
  2. 6x6 normalised Hessian (~2*FIM) eigenspectrum at theta* AND at Carroll:
     eigenvalues (log10 spread = sloppiness, Gutenkunst 2007) + smallest-eigenvalue
     eigenvector = the sloppy parameter combination.
  3. 1-D profile-likelihood over a chosen parameter (default alpfe): grid x
     re-optimise-the-rest, loss curve + a flat/curved verdict (Raue 2009).

Usage (on the cluster, env-configured exactly like the runner):
  AOIS=eqpac,natlsubpolar,southernoceanpac RATIO_MAX=2.0 RATIO_W=2 \
    AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 CHL1_W_EXTRA=3.0 \
    POSI_W=1.0 POSI_DARWIN_W=0.5 USE_EPPLEY_T=1 DARWIN_IC=1 \
    uv run python scripts/identifiability_sloppiness.py --param alpfe --out docs/findings/fim_3aoi.json
  # 4-AOI: AOIS=eqpac,natlsubpolar,southernoceanpac,npsg ... (same knobs)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]


def _import_runner():
    """Import the runner with training disabled, exposing bundles + aoi_loss."""
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    # Compile ON: optimisation + gradient are single-backward (the runner trains this
    # way). The Hessian uses finite-difference of the gradient, so no double-backward.
    os.environ.setdefault("TORCH_COMPILE_BATCHED", "1")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_fim_")
    runner_path = ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py"
    spec = importlib.util.spec_from_file_location("_dd_runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--param", default="alpfe", choices=PARAM_NAMES,
                    help="parameter to profile (default alpfe)")
    ap.add_argument("--mode", default="global", choices=["global", "peraoi", "fisher_gn"],
                    help="'global' (default) = shared-theta optimum + 6x6 Hessian + profile; "
                         "'peraoi' = a SEPARATE 6x6 Fisher/Hessian per AOI at Carroll, giving "
                         "basin-resolved identifiability (which parameters each basin's data "
                         "constrains). First cut toward the per-cell spatial map (#152); the box "
                         "is per-cell independent so the field Fisher is block-diagonal. "
                         "'fisher_gn' = the EXACT Gauss-Newton Fisher J^T J at the joint optimum "
                         "for a residual-vector loss (realiron/realbsi/realpic/realgraze) -- the "
                         "clean-magnitude follow-on to peraoi's residual-weighted empirical Fisher "
                         "(no profile re-optimisation grid, so no convergence-guard failure mode). "
                         "PSD by construction; CRLB = diag(F^-1) is a valid variance bound because "
                         "at the optimum residuals ~0 so GN ~ the true Hessian. Verified in-run "
                         "against 2*J^T J ~ FD-Hessian(theta*).")
    ap.add_argument("--loss", default="full",
                    choices=["full", "realiron", "realbsi", "realpic", "realgraze", "realbsi_synth"],
                    help="'full' = exact runner joint loss; 'realiron' = ONLY the REAL "
                         "GEOTRACES dissolved-iron residual (surf+sub, for alpfe/scav_rat); "
                         "'realbsi' = ONLY the REAL GEOTRACES biogenic-silica residual (for "
                         "diatomgraz). Real-world-relevance audit: 'does real data prefer Carroll?' "
                         "(issue #143/#116). Needs the corresponding weight on (GEOTRACES_W / POSI_W). "
                         "'realgraze' = the diatom SPECIFIC grazing RATE (grazing loss / diatom "
                         "biomass, 1/d) vs a SYNTHETIC self-target -- the dilution-experiment anchor "
                         "(microzooplankton grazing mortality, Schmoker 2013). Biomass cancels, so "
                         "unlike bSi it does NOT route through the model's own diatom biomass (see "
                         "the grazing-guard block). 'realbsi_synth' = the bSi arm with the SAME "
                         "synthetic self-target + ocean-mask footprint as realgraze, for an "
                         "apples-to-apples rate-vs-absolute-flux head-to-head on diatomgraz.")
    ap.add_argument("--grid", type=int, default=9, help="profile grid points")
    ap.add_argument("--opt-steps", type=int, default=400,
                    help="Adam steps to find theta* (profile re-opt uses opt-steps//2)")
    ap.add_argument("--lr", type=float, default=5e-2, help="Adam lr in unconstrained space")
    ap.add_argument("--seed", type=int, default=0,
                    help="RNG seed for the multi-start random initialisations (reproducibility)")
    ap.add_argument("--n-starts", type=int, default=1,
                    help="multi-start global search for theta*: start 0 is Carroll, the rest are "
                         "log-uniform random inside PARAM_BOUNDS. All starts are optimised in ONE "
                         "batched integration (optimise() treats columns independently), so the "
                         "cost is ~flat in n_starts. 1 = the pre-2026-07-20 single-start behaviour.")
    ap.add_argument("--max-refine", type=int, default=3,
                    help="max rounds of adopting a better profile point as theta* and re-optimising. "
                         "The profile starts FROM theta* and runs opt_steps//2 MORE steps, so it can "
                         "beat theta* whenever theta* has not converged -- which inflates the span "
                         "against a too-high baseline. 0 restores the pre-2026-07-19 behaviour.")
    ap.add_argument("--out", default=None, help="write JSON verdict here")
    ap.add_argument("--iron-residence", action="store_true",
                    help="After the profile, compute iron residence time tau = DFe/(alpfe*PHI_DUST) "
                         "per AOI at each profile grid point. The alpfe profile (loss=realiron) "
                         "re-optimises scav_rat at each fixed alpfe, so this traces tau along the "
                         "sloppy (degenerate) iron direction the data leaves free -- the local "
                         "signature of the field's 100x residence-time spread (Tagliabue 2016). "
                         "Use with --param alpfe --loss realiron.")
    args = ap.parse_args()

    import torch
    from darwindiff.carroll6 import CARROLL_VALUES, PARAM_BOUNDS, G0_GRAZE

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss
    R._RATIO_W_NOW = R.RATIO_W  # full ratio weight (converged state)
    _GRAZE_GUARD = None         # populated by the realgraze arm's grazing-guard block

    # Bundle ICs loaded with N_seeds=1; expand state0 to the batch S on demand so a
    # batched theta [6,S] integrates against a matching state0 [15,S,H,W] (else the
    # box's per-step torch.stack mixes S and 1 leading dims). Broadcast view = cheap.
    _base_state0 = {b["key"]: b["state0_per_seed"] for b in bundles}

    def set_seeds(S):
        for b in bundles:
            base = _base_state0[b["key"]]
            b["state0_per_seed"] = base[:, :1].expand(base.shape[0], S, base.shape[2], base.shape[3])

    aois = [b["key"] for b in bundles]
    weights = {b["key"]: float(b["weight"]) for b in bundles}
    print(f"\n=== identifiability diagnostic | AOIS={aois} | weights={weights} ===")
    print(f"    profiling: {args.param}  grid={args.grid}  opt_steps={args.opt_steps}")

    carroll = CARROLL_VALUES.to(dev).float()                # [6]
    bounds = PARAM_BOUNDS.to(dev).float()
    lo = bounds[:, 0:1]                                     # [6,1] (broadcast over seed axis)
    hi = bounds[:, 1:2]

    # -------- per-AOI EMPIRICAL FISHER mode (basin-resolved identifiability, #152) --------
    # The 0-D box integrates each cell independently and the loss scale-normalizer is built
    # from the TARGET (constant w.r.t. params), so d(loss)/d(theta) at every cell is recovered
    # in ONE backward of a per-cell theta FIELD (block-diagonal). The empirical Fisher
    # F = sum_cell g_cell g_cell^T is PSD BY CONSTRUCTION -- unlike the full Hessian at Carroll,
    # which is indefinite because Carroll is the GLOBAL optimum, not each basin's own minimum.
    # (Empirical Fisher, not the exact Gauss-Newton J^T Sigma^-1 J -- it is g=r*J weighted, so
    # CRLB magnitudes are approximate, but the eigenstructure / null-space = the identifiable vs
    # sloppy directions is the robust, PSD-guaranteed deliverable.)
    if args.mode == "peraoi":
        import math
        scale_v = carroll.abs().clamp(min=1e-30)
        per_aoi = {}
        for b in bundles:
            set_seeds(1)
            Hh, Ww = b["mask_f"].shape
            tf = carroll.reshape(6, 1, 1, 1).expand(6, 1, Hh, Ww).clone().requires_grad_(True)
            l, _ = aoi_loss(b, tf)
            (gf,) = torch.autograd.grad(l.sum(), tf)                 # [6,1,Hh,Ww] per-cell grad
            mask = (b["mask_f"] > 0).reshape(-1)
            g = gf.reshape(6, -1)[:, mask]                           # [6, Nactive]
            n_active = int(mask.sum())
            F = (g @ g.T) * scale_v[:, None] * scale_v[None, :]      # dimensionless empirical Fisher
            F = 0.5 * (F + F.T)
            evals, evecs = torch.linalg.eigh(F)
            evals_l = [float(x) for x in evals]
            emax = max(evals_l) if evals_l and max(evals_l) > 0 else 1.0
            ridge = 1e-6 * emax + 1e-30
            crlb = [float(x) for x in
                    torch.linalg.inv(F + ridge * torch.eye(6, device=F.device, dtype=F.dtype)).diagonal()]
            selfinfo = [float(F[i, i]) for i in range(6)]            # per-param Fisher info (>=0)
            sloppy = evecs[:, 0]
            pos = [e for e in evals_l if e > 1e-6 * emax]
            span = math.log10(max(pos) / min(pos)) if len(pos) >= 2 else float("nan")
            # --- Q1: rank + null direction of the 4-OBSERVABLE sub-block. Distinguishes "the 4
            # observables are jointly full-rank (all locally identifiable)" from "rank-deficient ->
            # a null COMBINATION" (which would mean 3 identifiable combinations, NOT 3-of-4 params).
            obs_names = ["alpfe", "scav_rat", "diatomgraz", "R_PICPOC"]
            obs = [PARAM_NAMES.index(p) for p in obs_names]
            F4 = F[obs][:, obs]
            e4, v4 = torch.linalg.eigh(0.5 * (F4 + F4.t()))
            e4l = [float(x) for x in e4]
            tol4 = 1e-4 * max(e4l) if max(e4l) > 0 else 1e-30
            rank4 = int(sum(1 for e in e4l if e > tol4))
            obs_block = {"observables": obs_names, "eigenvalues": e4l, "rank": rank4,
                         "null_direction": {obs_names[i]: float(v4[i, 0]) for i in range(4)}, "tol": tol4}
            print(f"\n-- AOI {b['key']} (weight {b['weight']}, {n_active} cells) empirical Fisher at Carroll --")
            print("   eigenvalues low->high: " + ", ".join(f"{e:.2e}" for e in evals_l)
                  + (f"   (sloppiness {span:.2f} dec)" if len(pos) >= 2 else ""))
            print("   per-param Fisher info (diag; HIGH = constrained): "
                  + "  ".join(f"{PARAM_NAMES[i]}={selfinfo[i]:.2e}" for i in range(6)))
            print("   per-param CRLB (var bound; HIGH = unconstrained): "
                  + "  ".join(f"{PARAM_NAMES[i]}={crlb[i]:.1e}" for i in range(6)))
            print("   sloppiest direction: "
                  + " ".join(f"{PARAM_NAMES[i]}{float(sloppy[i]):+.2f}" for i in range(6)))
            print(f"   [Q1 4-obs block] eigs {[f'{e:.1e}' for e in e4l]} -> rank {rank4}/4  "
                  + "null-dir " + " ".join(f"{obs_names[i]}{float(v4[i, 0]):+.2f}" for i in range(4)))
            per_aoi[b["key"]] = {
                "weight": float(b["weight"]), "n_cells": n_active, "eigenvalues": evals_l,
                "sloppiness_decades": span,
                "fisher_info_diag": {PARAM_NAMES[i]: selfinfo[i] for i in range(6)},
                "crlb": {PARAM_NAMES[i]: crlb[i] for i in range(6)},
                "sloppy_vector": {PARAM_NAMES[i]: float(sloppy[i]) for i in range(6)},
                "obs_block": obs_block,
            }
        out = {"mode": "peraoi", "method": "empirical_fisher", "aois": aois, "weights": weights,
               "carroll": {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)},
               "per_aoi": per_aoi}
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
            print(f"\nwrote {args.out}")
        return 0

    def loss_vec(theta: torch.Tensor) -> torch.Tensor:
        """Exact runner joint loss for a BATCH of global thetas. theta [6,S] -> [S]."""
        S = theta.shape[1]
        set_seeds(S)
        z = theta.new_zeros(S)
        for b in bundles:
            H, W = b["mask_f"].shape
            pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
            l, _ = aoi_loss(b, pb)                          # [S]
            z = z + b["weight"] * l
        return z

    def real_iron_loss_vec(theta: torch.Tensor) -> torch.Tensor:
        """ONLY the REAL GEOTRACES dissolved-iron residual (surf+sub), summed over AOIs.
        Reuses the box state aoi_loss already integrates; replicates the runner's GEOTRACES
        iron block (run_v3.0 lines ~1490-1500) so the term is bit-for-bit the real one."""
        S = theta.shape[1]
        set_seeds(S)
        z = theta.new_zeros(S)
        for b in bundles:
            H, W = b["mask_f"].shape
            pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
            _, state = aoi_loss(b, pb)                       # state [15, S, H, W]
            if R.GEOTRACES_W > 0 and b["n_geo_surf"] > 0:
                dfe1 = state[R.I_DFE_1]
                resid = (dfe1 - b["geo_surf_target_t"][None]) * b["geo_surf_mask_f"][None]
                scale = (b["geo_surf_target_t"][b["geo_surf_mask_t"]] ** 2).mean().clamp(min=1e-30)
                z = z + R.GEOTRACES_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_surf_f"] / scale
            if R.GEOTRACES_SUB_W > 0 and b["n_geo_sub"] > 0:
                dfe2 = state[R.I_DFE_2]
                resid = (dfe2 - b["geo_sub_target_t"][None]) * b["geo_sub_mask_f"][None]
                scale = (b["geo_sub_target_t"][b["geo_sub_mask_t"]] ** 2).mean().clamp(min=1e-30)
                z = z + R.GEOTRACES_SUB_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_sub_f"] / scale
        return z

    def real_bsi_loss_vec(theta: torch.Tensor) -> torch.Tensor:
        """ONLY the REAL GEOTRACES biogenic-silica residual, summed over AOIs. Replicates
        the runner's POSI_W bSi block (only diatoms make bSi, so it pins diatomgraz)."""
        S = theta.shape[1]
        set_seeds(S)
        z = theta.new_zeros(S)
        for b in bundles:
            if not (R.POSI_W > 0 and b["n_posi"] > 0):
                continue
            H, W = b["mask_f"].shape
            pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
            _, state = aoi_loss(b, pb)
            bsi_pred, _ = R.diagnostic_bsi_steady(state[R.I_DIATOM], pb[4])  # pb[4]=diatomgraz
            resid = (bsi_pred - b["posi_target_t"][None]) * b["posi_mask_f"][None]
            scale = (b["posi_target_t"][b["posi_mask_t"]] ** 2).mean().clamp(min=1e-30)
            z = z + R.POSI_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_posi_f"] / scale
        return z

    # Select which loss the optimum/Hessian/profile operate on (late-bound by the helpers).
    if args.loss == "realiron":
        loss_vec = real_iron_loss_vec
        print("    LOSS = realiron (GEOTRACES dissolved-iron residual ONLY)")
    elif args.loss == "realbsi":
        loss_vec = real_bsi_loss_vec
        print("    LOSS = realbsi (GEOTRACES biogenic-silica residual ONLY)")
    elif args.loss == "realpic":
        # REAL MODIS-Aqua surface PIC residual (for R_PICPOC) -- the literal calcite quantity,
        # INDEPENDENT of Darwin v05 (breaks circularity). Cache built by modis_pic_loader.py
        # (keys pic_<aoi>/mask_<aoi>, mol/m^3). Only AOIs present in the cache contribute.
        import numpy as np
        cache_path = os.environ.get("MODIS_PIC_CACHE_PATH",
                                    "/projects/schultz/qi.zim/runs/modis_pic_clim_2017_2019.npz")
        mc = np.load(cache_path)
        modis_tgt = {}
        for b in bundles:
            k = b["key"]
            if f"pic_{k}" not in mc.files:
                continue
            pic_mmol = mc[f"pic_{k}"].astype("float32") * 1000.0   # mol/m^3 -> mmol C/m^3
            ocean = (b["mask_f"] > 0).detach().cpu().numpy()
            m = ocean & mc[f"mask_{k}"] & np.isfinite(pic_mmol) & (pic_mmol > 0)
            tgt = torch.tensor(np.where(m, pic_mmol, 0.0), device=dev)
            mf = torch.tensor(m.astype("float32"), device=dev)
            modis_tgt[k] = (tgt, mf, mf.sum().clamp(min=1.0),
                            (tgt[mf > 0] ** 2).mean().clamp(min=1e-30))
        if not modis_tgt:
            raise SystemExit(f"realpic: no AOI in {aois} has MODIS PIC in {cache_path} "
                             f"(cache: {[f for f in mc.files if f.startswith('pic_')]})")

        def real_pic_loss_vec(theta):
            S = theta.shape[1]; set_seeds(S)
            z = theta.new_zeros(S)
            for b in bundles:
                if b["key"] not in modis_tgt:
                    continue
                H, W = b["mask_f"].shape
                pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
                _, state = aoi_loss(b, pb)
                tgt, mf, nf, sc = modis_tgt[b["key"]]
                resid = (state[R.I_PIC_1] - tgt[None]) * mf[None]
                z = z + (resid ** 2).flatten(1).sum(dim=1) / nf / sc
            return z
        loss_vec = real_pic_loss_vec
        print(f"    LOSS = realpic (MODIS-Aqua PIC residual ONLY; AOIs: {list(modis_tgt)})")

    # -------- realgraze / realbsi_synth: the dilution-grazing-RATE anchor --------
    # THE ANCHOR. A microzooplankton dilution experiment (Landry-Hassett; Schmoker
    # et al. 2013 global synthesis) measures the diatom grazing MORTALITY RATE (per
    # day) -- a field quantity independent of Darwin, exactly as GEOTRACES iron
    # anchors alpfe and Daniels/MODIS calcite anchors R_PICPOC.
    #
    # In the box the diatom grazing loss is graze_diatom = diatomgraz * G0_GRAZE *
    # P_diatom (G0_GRAZE = const; NO grazer-biomass tracer; small PFTs have NO
    # grazing term). So the SPECIFIC grazing rate observable
    #     r_graze = graze_diatom / P_diatom = diatomgraz * G0_GRAZE          [1/d]
    # cancels the diatom biomass EXACTLY: d r_graze / d P_diatom = 0, d r_graze /
    # d diatomgraz = G0_GRAZE. This is why it can constrain diatomgraz where bSi
    # cannot -- bSi anchors the ABSOLUTE flux (~ diatomgraz * P_diatom), and at
    # steady state P_diatom DROPS as diatomgraz rises, so the biomass response
    # compensates the palatability signal and the bSi profile goes FLAT (the M11
    # circularity: bSi is back-solved from the model's own diatom biomass).
    # 'realbsi_synth' reruns that ABSOLUTE-flux bSi observable with the SAME
    # synthetic self-target + ocean-mask footprint so the head-to-head isolates the
    # ONE difference: specific rate (biomass-cancelled) vs absolute flux (biomass-routed).
    # See scratchpad graze_guard.py + docs/findings for the guard derivation.
    if args.loss in ("realgraze", "realbsi_synth"):
        G0 = float(G0_GRAZE)

        def _graze_rate(state, pb):
            """Diatom specific grazing rate graze/P_diatom [S,H,W]. Computed the
            HONEST way (form the loss term, divide by the biomass from state) so any
            residual biomass dependence would show up; algebraically it is
            diatomgraz*G0_GRAZE, biomass-independent."""
            p_diatom = state[R.I_DIATOM]
            graze = pb[4] * G0 * p_diatom                         # pb[4] = diatomgraz
            return graze / p_diatom.clamp(min=1e-12)

        def _bsi_abs(state, pb):
            """Absolute surface bSi_1 [S,H,W] (mmol Si/m^3) -- the biomass-routed flux."""
            bsi_pred, _ = R.diagnostic_bsi_steady(state[R.I_DIATOM], pb[4])
            return bsi_pred

        _obs_fn = _graze_rate if args.loss == "realgraze" else _bsi_abs

        # SYNTHETIC self-target: the observable evaluated at Carroll's diatomgraz,
        # over each AOI's ocean mask. Detached -> a fixed anchor the profile fits.
        synth = {}
        carroll_b = carroll.reshape(6, 1, 1, 1)
        with torch.no_grad():
            set_seeds(1)
            for b in bundles:
                H, W = b["mask_f"].shape
                pbC = carroll_b.expand(6, 1, H, W)
                _, stateC = aoi_loss(b, pbC)
                tgt = _obs_fn(stateC, pbC)[0]                     # [H,W]
                mf = (b["mask_f"] > 0).to(tgt.dtype)
                nf = mf.sum().clamp(min=1.0)
                sc = (tgt[mf > 0] ** 2).mean().clamp(min=1e-30)
                synth[b["key"]] = (tgt.detach(), mf, nf, sc)
        _tgt_mean = {k: float(v[0][v[1] > 0].mean()) for k, v in synth.items()}
        print(f"    LOSS = {args.loss} (SYNTHETIC self-target over ocean mask; "
              f"{'diatom specific grazing RATE 1/d' if args.loss=='realgraze' else 'absolute bSi_1 mmol Si/m^3'}; "
              f"per-AOI target mean {_tgt_mean})")

        def real_graze_like_loss_vec(theta):
            S = theta.shape[1]; set_seeds(S)
            z = theta.new_zeros(S)
            for b in bundles:
                H, W = b["mask_f"].shape
                pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
                _, state = aoi_loss(b, pb)
                tgt, mf, nf, sc = synth[b["key"]]
                pred = _obs_fn(state, pb)
                resid = (pred - tgt[None]) * mf[None]
                z = z + b["weight"] * (resid ** 2).flatten(1).sum(dim=1) / nf / sc
            return z
        loss_vec = real_graze_like_loss_vec

        # ---- GRAZING GUARD (the gate): is the observable sensitive to diatomgraz
        #      but ~insensitive to grazer/diatom biomass? Reported for the REAL
        #      converged bundle states, PARTIAL (frozen biomass) + TOTAL (through the
        #      re-converged steady state). Printed for BOTH arms so the contrast is
        #      explicit. See docstring above + scratchpad graze_guard.py. ----
        if args.loss == "realgraze":
            b0 = bundles[0]
            H, W = b0["mask_f"].shape
            with torch.no_grad():
                set_seeds(1)
                _, stC = aoi_loss(b0, carroll_b.expand(6, 1, H, W))
                mf0 = (b0["mask_f"] > 0)
                Pd0 = float(stC[R.I_DIATOM][0][mf0].mean())
            g_leaf = torch.tensor(float(carroll[4]), requires_grad=True)
            Pd_leaf = torch.tensor(Pd0, requires_grad=True)
            rate = (g_leaf * G0 * Pd_leaf) / Pd_leaf
            flux = g_leaf * G0 * Pd_leaf
            dr = torch.autograd.grad(rate, (g_leaf, Pd_leaf), retain_graph=True)
            df = torch.autograd.grad(flux, (g_leaf, Pd_leaf))
            # total (through steady state): finite-diff diatomgraz, re-converge
            def _obs_total(gval):
                th = carroll.clone(); th[4] = gval
                with torch.no_grad():
                    set_seeds(1)
                    _, s = aoi_loss(b0, th.reshape(6, 1, 1, 1).expand(6, 1, H, W))
                    pd = float(s[R.I_DIATOM][0][mf0].mean())
                return pd, gval * G0 * pd, gval * G0
            eps = 0.02 * float(carroll[4])
            pdp, fxp, rtp = _obs_total(float(carroll[4]) + eps)
            pdm, fxm, rtm = _obs_total(float(carroll[4]) - eps)
            # Pass = the RATE's biomass-sensitivity is negligible RELATIVE to its
            # diatomgraz-sensitivity (a relative test, robust to the runner's float32),
            # its diatomgraz-sensitivity matches G0_GRAZE, AND the absolute-flux control
            # DOES route through biomass (so the test has discriminating power).
            rate_dg, rate_db = abs(float(dr[0])), abs(float(dr[1]))
            flux_dg, flux_db = abs(float(df[0])), abs(float(df[1]))
            rate_biomass_frac = rate_db / rate_dg if rate_dg > 0 else float("inf")
            flux_biomass_frac = flux_db / flux_dg if flux_dg > 0 else float("inf")
            guard = {
                "partial_rate_d_diatomgraz": float(dr[0]), "partial_rate_d_biomass": float(dr[1]),
                "partial_absflux_d_diatomgraz": float(df[0]), "partial_absflux_d_biomass": float(df[1]),
                "rate_biomass_vs_diatomgraz_frac": rate_biomass_frac,
                "flux_biomass_vs_diatomgraz_frac": flux_biomass_frac,
                "total_dPdiatom_ddiatomgraz": (pdp - pdm) / (2 * eps),
                "total_dAbsFlux_ddiatomgraz": (fxp - fxm) / (2 * eps),
                "total_dSpecificRate_ddiatomgraz": (rtp - rtm) / (2 * eps),
                "pass": bool(rate_dg > 0 and rate_biomass_frac < 1e-4
                             and abs(rate_dg - G0) < 1e-4 * G0 and flux_biomass_frac > 1.0),
                "note": "Box has no grazer-biomass tracer and no small-PFT grazing term, so the raw "
                        "specific rate already isolates diatomgraz (biomass cancels); the size-fraction "
                        "contrast is unnecessary here. NECESSARY (rate breaks the bSi biomass-tautology) "
                        "but not SUFFICIENT for the full Darwin grazer_biomass*response*palatability form.",
            }
            print("\n-- GRAZING GUARD (real converged state, AOI "
                  f"{b0['key']}, P_diatom={Pd0:.4g}) --")
            print(f"   PARTIAL specific RATE : d/d diatomgraz={guard['partial_rate_d_diatomgraz']:+.4g}  "
                  f"d/d biomass={guard['partial_rate_d_biomass']:+.4g}  "
                  f"(biomass/diatomgraz={guard['rate_biomass_vs_diatomgraz_frac']:.2e} => isolates diatomgraz)")
            print(f"   PARTIAL abs   FLUX    : d/d diatomgraz={guard['partial_absflux_d_diatomgraz']:+.4g}  "
                  f"d/d biomass={guard['partial_absflux_d_biomass']:+.4g}  "
                  f"(biomass/diatomgraz={guard['flux_biomass_vs_diatomgraz_frac']:.2e} => routes through biomass)")
            print(f"   TOTAL (thru steady st): dP_diatom/dg={guard['total_dPdiatom_ddiatomgraz']:+.4g}  "
                  f"dAbsFlux/dg={guard['total_dAbsFlux_ddiatomgraz']:+.4g}  "
                  f"dRate/dg={guard['total_dSpecificRate_ddiatomgraz']:+.4g}")
            print(f"   GUARD PASS: {guard['pass']}")
            _GRAZE_GUARD = guard
        else:
            _GRAZE_GUARD = None

    def to_phys(u):   # u [6,S] -> physical [6,S]
        return lo + (hi - lo) * torch.sigmoid(u)

    def to_uncon(theta):  # theta [6,S] -> unconstrained [6,S]
        frac = ((theta - lo) / (hi - lo)).clamp(1e-6, 1 - 1e-6)
        return torch.log(frac / (1 - frac))

    def optimise(u_init, steps, fixed_idx=None, fixed_vals=None):
        """Adam in unconstrained space. Each seed-column is an INDEPENDENT theta, so
        minimising the summed loss optimises every column at once (one integration)."""
        u = u_init.clone().detach().requires_grad_(True)
        opt = torch.optim.Adam([u], lr=args.lr)
        for _ in range(steps):
            opt.zero_grad()
            theta = to_phys(u)
            if fixed_idx is not None:
                theta = theta.clone()
                theta[fixed_idx] = fixed_vals
            loss_vec(theta).sum().backward()
            opt.step()
        with torch.no_grad():
            theta = to_phys(u)
            if fixed_idx is not None:
                theta = theta.clone(); theta[fixed_idx] = fixed_vals
            return theta.detach(), loss_vec(theta).detach()

    def grad_at(th):   # th [6] -> grad [6] (single backward)
        t = th.detach().reshape(6, 1).clone().requires_grad_(True)
        (g,) = torch.autograd.grad(loss_vec(t).sum(), t)
        return g.detach().reshape(6)

    def fd_hessian(at, rel_eps=2e-2):
        """6x6 Hessian by central finite-difference of the autograd gradient (12 evals)."""
        at = at.detach().reshape(6)
        Hm = torch.zeros(6, 6, device=at.device, dtype=at.dtype)
        for j in range(6):
            eps = rel_eps * max(abs(float(at[j])), 1e-30)
            ap = at.clone(); ap[j] += eps
            am = at.clone(); am[j] -= eps
            Hm[:, j] = (grad_at(ap) - grad_at(am)) / (2 * eps)
        return 0.5 * (Hm + Hm.T)

    # ---- 1. shared-theta optimum: MULTI-START from Carroll + random inits ----
    # Mechanistic-model calibration conventionally uses GLOBAL optimisation, while
    # gradient-trained hybrid models use local methods; that mismatch is a known source
    # of spurious non-identifiability verdicts. Until 2026-07-20 this was a SINGLE start
    # from Carroll, and the profile search (which continues from theta_star) routinely
    # beat it -- see docs/findings/2026-07-19_silicate_fim_artifact_audit.md.
    # optimise() already treats each column as an independent theta, so extra starts cost
    # one batched integration rather than N sequential fits.
    g0 = torch.Generator(device="cpu").manual_seed(args.seed)
    inits = [to_uncon(carroll.reshape(6, 1))]
    if args.n_starts > 1:
        # log-uniform inside the physical bounds: parameters span decades
        llo, lhi = torch.log10(lo), torch.log10(hi)
        u = torch.rand(6, args.n_starts - 1, generator=g0).to(lo.device)
        rand_theta = torch.pow(10.0, llo + (lhi - llo) * u)
        inits.append(to_uncon(rand_theta))
    u_all = torch.cat(inits, dim=1).contiguous()
    theta1, l1 = optimise(u_all, steps=args.opt_steps)
    _b = int(torch.argmin(l1))
    if args.n_starts > 1:
        _ls = [float(v) for v in l1]
        print(f"\n-- multi-start ({args.n_starts}) losses: "
              f"best={min(_ls):.6g} (start {_b}, {'Carroll' if _b == 0 else 'random'}) "
              f"worst={max(_ls):.6g} spread={max(_ls)-min(_ls):.4g} --")
        if _b != 0:
            print(f"   NOTE: a RANDOM start beat the Carroll start by "
                  f"{_ls[0]-min(_ls):.4g} -- the single-start fit was in a worse basin.")
    theta_star = theta1[:, _b]
    loss_star = float(l1[_b])
    grad_norm = float((grad_at(theta_star) * theta_star).norm())
    print(f"\n-- shared-theta optimum (loss={loss_star:.5e}, rel|grad|={grad_norm:.2e}) --")
    print(f"{'param':<11}{'theta*':>13}{'Carroll':>13}{'rel.off':>9}")
    for i, p in enumerate(PARAM_NAMES):
        ts, cv = float(theta_star[i]), float(carroll[i])
        print(f"{p:<11}{ts:>13.5g}{cv:>13.5g}{abs(ts-cv)/abs(cv):>9.2f}")

    # ---- 2. normalised Hessian eigenspectra (sloppy directions) ----
    def hess_report(at, label):
        at = at.detach().reshape(6)
        scale = at.abs().clamp(min=1e-30)
        Hn = fd_hessian(at) * scale[:, None] * scale[None, :]       # dimensionless
        Hn = 0.5 * (Hn + Hn.T)
        evals, evecs = torch.linalg.eigh(Hn)
        evals_l = [float(x) for x in evals]
        sloppy = evecs[:, 0]; stiff = evecs[:, -1]
        print(f"\n-- normalised Hessian eigenspectrum at {label} --")
        print("   eigenvalues (low->high): " + ", ".join(f"{e:.2e}" for e in evals_l))
        pos = [e for e in evals_l if e > 0]
        if len(pos) >= 2:
            import math
            print(f"   sloppiness span: {math.log10(max(pos) / min(pos)):.2f} decades (+ve evals)")
        print(f"   sloppiest direction (eval={evals_l[0]:.2e}):  "
              + "  ".join(f"{PARAM_NAMES[i]}{float(sloppy[i]):+.2f}" for i in range(6)))
        return {"eigenvalues": evals_l,
                "sloppy_vector": {PARAM_NAMES[i]: float(sloppy[i]) for i in range(6)},
                "stiff_vector": {PARAM_NAMES[i]: float(stiff[i]) for i in range(6)}}

    if args.mode != "fisher_gn":  # the GN-Fisher mode does its own curvature; skip the (saddle) Hessians
        hess_star = hess_report(theta_star, "theta*")
        hess_carroll = hess_report(carroll, "Carroll")

    # ---- EXACT GAUSS-NEWTON FISHER (clean-magnitude, PSD, no profile grid) -----------
    # The peraoi empirical Fisher is F = sum g g^T with g = 2 rho J -> residual-WEIGHTED, so
    # its magnitudes/CRLB are biased away from the optimum (the diatomgraz diagonal artifact).
    # The exact Gauss-Newton Fisher F_GN = J^T J (J = d rho / d theta, rho the SCALED residual
    # with ||rho||^2 == loss) drops the residual weighting -> clean curvature of the model output.
    # At theta* it is the valid CRLB source (residuals ~ min). This is a SINGLE evaluation (12 FD
    # residual evals for J), so it has no profile-re-optimisation convergence-guard failure mode --
    # the trap that invalidated 9/13 runs on 2026-07-19.
    if args.mode == "fisher_gn":
        import math as _math
        if args.loss not in {"realiron", "realbsi"}:
            raise SystemExit(
                "fisher_gn currently supports --loss realiron (iron pair alpfe/scav_rat) or "
                "realbsi (diatomgraz) -- the residual-vector losses whose scaling is exact here. "
                "The 'full' joint loss does not expose its residual vector; realpic scaling is "
                "not yet replicated. Choose realiron or realbsi.")

        def resid_vec(theta_6):
            """Scaled residual vector rho for the selected loss at a single theta [6];
            built so ||rho||^2 == loss_vec(theta) (asserted below)."""
            th = theta_6.detach().reshape(6, 1)
            set_seeds(1)
            parts = []
            for b in bundles:
                H, W = b["mask_f"].shape
                pb = th.reshape(6, 1, 1, 1).expand(6, 1, H, W)
                _, state = aoi_loss(b, pb)
                if args.loss == "realiron":
                    if R.GEOTRACES_W > 0 and b["n_geo_surf"] > 0:
                        r = (state[R.I_DFE_1] - b["geo_surf_target_t"][None]) * b["geo_surf_mask_f"][None]
                        sc = (b["geo_surf_target_t"][b["geo_surf_mask_t"]] ** 2).mean().clamp(min=1e-30)
                        coef = (R.GEOTRACES_W / (b["n_geo_surf_f"] * sc)).sqrt()
                        parts.append(coef * r.reshape(-1))
                    if R.GEOTRACES_SUB_W > 0 and b["n_geo_sub"] > 0:
                        r = (state[R.I_DFE_2] - b["geo_sub_target_t"][None]) * b["geo_sub_mask_f"][None]
                        sc = (b["geo_sub_target_t"][b["geo_sub_mask_t"]] ** 2).mean().clamp(min=1e-30)
                        coef = (R.GEOTRACES_SUB_W / (b["n_geo_sub_f"] * sc)).sqrt()
                        parts.append(coef * r.reshape(-1))
                elif args.loss == "realbsi":
                    if R.POSI_W > 0 and b["n_posi"] > 0:
                        bsi_pred, _ = R.diagnostic_bsi_steady(state[R.I_DIATOM], pb[4])
                        r = (bsi_pred - b["posi_target_t"][None]) * b["posi_mask_f"][None]
                        sc = (b["posi_target_t"][b["posi_mask_t"]] ** 2).mean().clamp(min=1e-30)
                        coef = (R.POSI_W / (b["n_posi_f"] * sc)).sqrt()
                        parts.append(coef * r.reshape(-1))
            return torch.cat(parts) if parts else theta_star.new_zeros(1)

        at = theta_star.detach().reshape(6)
        # SELF-CHECK: the reconstructed residual vector must reproduce the runner loss exactly.
        rho0 = resid_vec(at)
        l_resid = float((rho0 ** 2).sum())
        l_direct = float(loss_vec(at.reshape(6, 1)))
        recon_rel = abs(l_resid - l_direct) / max(abs(l_direct), 1e-30)
        print(f"\n-- GN-Fisher residual reconstruction check: ||rho||^2={l_resid:.6g} vs "
              f"loss_vec={l_direct:.6g}  (rel {recon_rel:.2e}) --")
        if recon_rel > 1e-4:
            raise SystemExit(f"resid_vec does NOT reconstruct the loss (rel {recon_rel:.2e}); "
                             "the GN-Fisher scaling is wrong -- refusing to emit a bad artifact.")

        Nres = rho0.numel()
        Jm = torch.zeros(Nres, 6, device=at.device, dtype=at.dtype)
        rel_eps = 2e-2
        for j in range(6):
            eps = rel_eps * max(abs(float(at[j])), 1e-30)
            ap = at.clone(); ap[j] += eps
            am = at.clone(); am[j] -= eps
            Jm[:, j] = (resid_vec(ap) - resid_vec(am)) / (2 * eps)
        F = Jm.t() @ Jm
        F = 0.5 * (F + F.t())
        scale_v = at.abs().clamp(min=1e-30)
        Fn = F * scale_v[:, None] * scale_v[None, :]                 # dimensionless GN-Fisher
        Fn = 0.5 * (Fn + Fn.t())
        evals, evecs = torch.linalg.eigh(Fn)
        evals_l = [float(x) for x in evals]
        emax = max(evals_l) if evals_l and max(evals_l) > 0 else 1.0
        min_eval = min(evals_l)
        psd = bool(min_eval >= -1e-8 * emax)
        ridge = 1e-6 * emax + 1e-30
        crlb = [float(x) for x in
                torch.linalg.inv(Fn + ridge * torch.eye(6, device=Fn.device, dtype=Fn.dtype)).diagonal()]
        fisher_info = [float(Fn[i, i]) for i in range(6)]
        sloppy = evecs[:, 0]; stiff = evecs[:, -1]
        pos = [e for e in evals_l if e > 1e-6 * emax]
        span = _math.log10(max(pos) / min(pos)) if len(pos) >= 2 else float("nan")

        # --- Q2: {alpfe, scav_rat} sub-block + POSTERIOR CORRELATION + dimensionless rel. uncertainty.
        # The marginal CRLBs alone do NOT show a degeneracy (similar marginals occur in well- and
        # poorly-constrained systems). The degeneracy lives in (a) the 2x2 eigen-spread / condition
        # number and (b) the correlation rho: |rho|->1 means alpfe & scav_rat trade off along one
        # combination. All dimensionless (Fn already scaled by |theta|). LOCAL, at this evaluation point.
        C6 = torch.linalg.inv(Fn + ridge * torch.eye(6, device=Fn.device, dtype=Fn.dtype))
        ia, isc = PARAM_NAMES.index("alpfe"), PARAM_NAMES.index("scav_rat")
        F2 = 0.5 * (Fn[[ia, isc]][:, [ia, isc]] + Fn[[ia, isc]][:, [ia, isc]].t())
        e2v, e2vec = torch.linalg.eigh(F2)                        # ascending: [:,0] = sloppy (flat) dir
        e2l = [float(x) for x in e2v]
        cond2 = (max(e2l) / min(e2l)) if min(e2l) > 0 else float("inf")
        # SLOPPY 2x2 eigenvector in dimensionless (~log-parameter) coords. Same sign on both entries
        # => (+alpfe,+scav_rat) co-vary = the RATIO S/k degeneracy (hold [DFe]=S/k fixed by raising
        # source AND loss together, per C=S/k). Opposite signs => a product/anti-varying direction.
        sv = e2vec[:, 0]
        if sv[0] < 0:  # fix gauge so alpfe component is +, for a readable sign
            sv = -sv
        iron_sloppy_dir = {"alpfe": float(sv[0]), "scav_rat": float(sv[1])}
        ratio_like = bool(sv[0] * sv[1] > 0)  # True => co-vary => S/k ratio degeneracy
        # CONDITIONAL 2x2 correlation (marginalize ONLY the pair, others held) — the pure iron-pair
        # degeneracy; and the FULL-6 MARGINAL (others integrated out), which can flip sign via coupling.
        C2 = torch.linalg.inv(F2 + 1e-6 * float(max(e2l)) * torch.eye(2, device=F2.device, dtype=F2.dtype))
        rho_cond2 = float(C2[0, 1] / (C2[0, 0] * C2[1, 1]).clamp(min=1e-60).sqrt())
        rho_full6 = float(C6[ia, isc] / (C6[ia, ia] * C6[isc, isc]).clamp(min=1e-60).sqrt())
        relstd_alpfe = float(C6[ia, ia].clamp(min=0).sqrt())      # dimensionless posterior rel. std
        relstd_scav = float(C6[isc, isc].clamp(min=0).sqrt())
        iron_block = {"pair": ["alpfe", "scav_rat"], "eigenvalues_2x2": e2l,
                      "condition_number_2x2": cond2, "sloppy_dir_2x2": iron_sloppy_dir,
                      "ratio_like_degeneracy": ratio_like,
                      "posterior_corr_conditional_2x2": rho_cond2, "posterior_corr_full6": rho_full6,
                      "rel_std_alpfe": relstd_alpfe, "rel_std_scav_rat": relstd_scav,
                      "note": "sloppy_dir same-sign => S/k RATIO degeneracy (C=S/k). conditional corr = pure "
                              "iron-pair; full6 marginal can sign-flip via coupling to the other params. LOCAL."}

        # VERIFY #2: at the optimum, loss Hessian ~ 2 * J^T J (the residual-curvature term
        # 2*sum rho*grad^2 rho vanishes only if residuals ~0). Report the gap honestly: a small
        # gap confirms the GN-Fisher IS the curvature; a large gap means the data is not perfectly
        # fit (rho != 0) and the CLEAN GN (which drops that term) is exactly why we prefer it.
        Hn = fd_hessian(at) * scale_v[:, None] * scale_v[None, :]
        Hn = 0.5 * (Hn + Hn.t())
        gap_fro = float((Hn - 2.0 * Fn).norm() / (2.0 * Fn).norm().clamp(min=1e-30))

        print(f"\n-- EXACT Gauss-Newton Fisher (loss={args.loss}) at theta* ({Nres} residuals) --")
        print("   eigenvalues (low->high): " + ", ".join(f"{e:.2e}" for e in evals_l)
              + (f"   (sloppiness {span:.2f} dec)" if len(pos) >= 2 else ""))
        print(f"   PSD: {psd} (min eval {min_eval:.2e})   ||H - 2F||/||2F|| = {gap_fro:.2f} "
              f"(small => residuals ~0, GN == curvature; large => data not perfectly fit)")
        print("   per-param Fisher info (diag; HIGH = constrained): "
              + "  ".join(f"{PARAM_NAMES[i]}={fisher_info[i]:.2e}" for i in range(6)))
        print("   per-param CRLB (rel-var bound; HIGH = unconstrained): "
              + "  ".join(f"{PARAM_NAMES[i]}={crlb[i]:.1e}" for i in range(6)))
        print("   sloppiest direction (eval={:.2e}): ".format(evals_l[0])
              + " ".join(f"{PARAM_NAMES[i]}{float(sloppy[i]):+.2f}" for i in range(6)))
        print("   stiffest  direction (eval={:.2e}): ".format(evals_l[-1])
              + " ".join(f"{PARAM_NAMES[i]}{float(stiff[i]):+.2f}" for i in range(6)))
        print(f"   [Q2 iron pair] 2x2 eigs {e2l[0]:.2e}/{e2l[1]:.2e} cond={cond2:.1f}")
        print(f"      sloppy 2x2 dir (dimensionless~log): alpfe {iron_sloppy_dir['alpfe']:+.2f}, "
              f"scav_rat {iron_sloppy_dir['scav_rat']:+.2f}  => "
              f"{'S/k RATIO degeneracy (co-vary; C=S/k)' if ratio_like else 'anti-vary/product direction'}")
        print(f"      corr(alpfe,scav_rat): conditional(pure 2x2)={rho_cond2:+.3f}  full-6 marginal={rho_full6:+.3f}  "
              f"(marginal sign-flips via coupling; lead with the conditional)")
        print(f"      dimensionless rel-std alpfe={relstd_alpfe:.2f} scav_rat={relstd_scav:.2f}")

        out = {
            "mode": "fisher_gn", "method": "exact_gauss_newton_JtJ", "loss_mode": args.loss,
            "aois": aois, "weights": weights,
            "theta_star": {PARAM_NAMES[i]: float(theta_star[i]) for i in range(6)},
            "carroll": {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)},
            "loss_star": float(loss_star), "n_residuals": int(Nres),
            "recon_rel_error": recon_rel, "psd": psd, "min_eigenvalue": min_eval,
            "hessian_gn_gap_fro": gap_fro,
            "eigenvalues": evals_l, "sloppiness_decades": span,
            "fisher_info_diag": {PARAM_NAMES[i]: fisher_info[i] for i in range(6)},
            "crlb": {PARAM_NAMES[i]: crlb[i] for i in range(6)},
            "sloppy_vector": {PARAM_NAMES[i]: float(sloppy[i]) for i in range(6)},
            "stiff_vector": {PARAM_NAMES[i]: float(stiff[i]) for i in range(6)},
            "iron_block": iron_block,
            "note": "F_GN = J^T J, J = d(scaled residual)/d theta by central FD (rel_eps 2e-2), "
                    "dimensionless (scaled by |theta*|). CRLB = diag((F+ridge)^-1). Verified: "
                    "residual reconstruction reproduces loss_vec; H ~ 2F gap reported.",
        }
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
            print(f"\nwrote {args.out}")
        return 0

    # ---- 3. profile-likelihood over the chosen parameter (VECTORISED over the grid) ----
    pidx = PARAM_NAMES.index(args.param)
    grid = torch.logspace(float(torch.log10(lo[pidx, 0])),
                          float(torch.log10(hi[pidx, 0])), args.grid).to(dev).float()  # [G]
    G = grid.numel()
    # NOTE ON THE STEP BUDGET (2026-07-19). The profile starts FROM theta_star and then runs
    # further steps, so each grid point receives opt_steps + prof_steps of optimisation against
    # theta_star's opt_steps. That makes min(profile) < loss_star GUARANTEED whenever theta_star
    # has not converged -- and rel_span, normalised by that too-high baseline, is inflated by the
    # same amount. On 2026-07-19 this silently manufactured a silicate-ablation conclusion.
    # The loop below closes the asymmetry: whenever the profile finds something better, we adopt
    # it as the new theta_star, re-optimise, and recompute. See
    # docs/findings/2026-07-19_silicate_fim_artifact_audit.md.
    prof_steps = max(150, args.opt_steps // 2)
    conv_tol0 = 1e-3 * abs(loss_star)
    prof_theta = prof_losses = None
    for _round in range(args.max_refine + 1):
        u0 = to_uncon(theta_star.reshape(6, 1)).expand(6, G).contiguous()
        prof_theta, prof_losses = optimise(u0, steps=prof_steps,
                                           fixed_idx=pidx, fixed_vals=grid)
        bi = int(torch.argmin(prof_losses))
        gap = float(prof_losses[bi]) - loss_star
        if gap >= -conv_tol0 or _round == args.max_refine:
            if gap < -conv_tol0:
                print(f"\n[refine] EXHAUSTED {args.max_refine} rounds, residual gap {gap:.4g} "
                      f"-- theta_star still under-converged; raise --opt-steps/--max-refine")
            break
        # The profile beat theta_star: adopt its best point and re-optimise from there.
        print(f"\n[refine round {_round}] profile beat theta* by {-gap:.4g} "
              f"(loss_star={loss_star:.6g} -> re-optimising from grid point {bi})")
        theta_seed = prof_theta[:, bi].reshape(6, 1)
        th_new, l_new = optimise(to_uncon(theta_seed), steps=args.opt_steps)
        if float(l_new[0]) < loss_star:
            theta_star, loss_star = th_new[:, 0], float(l_new[0])
            conv_tol0 = 1e-3 * abs(loss_star)
        else:
            break
    # theta_star may have moved; refresh everything derived from it.
    grad_norm = float((grad_at(theta_star) * theta_star).norm())
    hess_star = hess_report(theta_star, "theta*")

    prof = [(float(grid[i]), float(prof_losses[i])) for i in range(G)]
    best = min(l for _, l in prof)
    print(f"\n-- profile-likelihood over {args.param} (fix on grid, re-optimise other 5) --")
    print(f"{args.param:>13}{'min loss':>14}{'  Δ vs best':>14}")
    for val, lmin in prof:
        print(f"{val:>13.4g}{lmin:>14.5e}{lmin - best:>14.3e}")
    rel_span = (max(l for _, l in prof) - best) / max(best, 1e-30)

    # ---- validity guards (see docs/findings/2026-07-19_silicate_fim_artifact_audit.md) ----
    # The profile fixes the profiled parameter on a grid and re-optimises the other
    # five, so its minimum CANNOT legitimately fall below the joint optimum: at
    # p = theta*_p it must return loss_star itself. When it does fall below,
    # theta_star is under-converged and rel_span is measured against a wrong
    # baseline. On 2026-07-19 this silently inverted a silicate-ablation
    # conclusion -- the four parameters that appeared to gain from adding
    # silicate were exactly the four whose profile escaped a bad theta_star, and
    # both parameters whose fits had converged showed no gain at all. Every job
    # exited 0 and emitted a confident verdict string.
    conv_tol = 1e-3 * abs(loss_star)
    conv_gap = best - loss_star
    converged = bool(conv_gap >= -conv_tol)

    # A profile whose minimum sits on a grid endpoint has not bracketed the
    # optimum: rel_span is then only a lower bound and the verdict is not
    # meaningful. Report "at bound" rather than a span.
    amin = min(range(len(prof)), key=lambda i: prof[i][1])
    bracketed = bool(0 < amin < len(prof) - 1)

    if rel_span < 0.05:
        verdict = "FLAT -> STRUCTURAL non-identifiability (reweighting dead; need new observable/structure)"
    elif rel_span < 0.5:
        verdict = "SHALLOW -> weak practical non-identifiability (more same-type data helps only marginally)"
    else:
        verdict = "CURVED -> PRACTICAL non-identifiability (routing/pooling/seeds licensed; param IS constrained)"
    print(f"\n   profile span (max-min)/best = {rel_span:.3f}  =>  {verdict}")

    problems = []
    if not converged:
        problems.append(
            f"theta_star UNDER-CONVERGED: min(profile)={best:.6g} is {-conv_gap:.6g} BELOW "
            f"loss_star={loss_star:.6g} (tol {conv_tol:.3g}). The profile search beat the joint "
            f"fit, so rel_span is measured against a wrong baseline."
        )
    if not bracketed:
        side = "LOWER" if amin == 0 else "UPPER"
        problems.append(
            f"profile minimum is ON THE {side} GRID EDGE (value={prof[amin][0]:.6g}); the optimum "
            f"is not bracketed, so rel_span is a lower bound only."
        )
    if problems:
        verdict = "INVALID -> " + " | ".join(problems)
        print("\n" + "=" * 78)
        print("  PROFILE INVALID -- do not quote this span or verdict:")
        for p in problems:
            print(f"    * {p}")
        print("=" * 78)

    out = {
        "aois": aois, "weights": weights, "profiled_param": args.param,
        "loss_mode": args.loss, "grazing_guard": _GRAZE_GUARD,
        "theta_star": {PARAM_NAMES[i]: float(theta_star[i]) for i in range(6)},
        "carroll": {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)},
        "loss_star": loss_star, "rel_grad_norm": grad_norm,
        "hessian_at_theta_star": hess_star, "hessian_at_carroll": hess_carroll,
        "profile": [{"value": v, "min_loss": l} for v, l in prof],
        "profile_rel_span": rel_span, "verdict": verdict,
        "valid": bool(converged and bracketed),
        "convergence": {
            "converged": converged, "profile_min": best, "conv_gap": conv_gap,
            "tol": conv_tol,
            "note": "conv_gap = min(profile) - loss_star; must be >= -tol. Negative means "
                    "theta_star is under-converged and the span is untrustworthy.",
        },
        "bracketing": {
            "bracketed": bracketed, "argmin_index": amin, "n_grid": len(prof),
            "argmin_value": prof[amin][0],
            "note": "False means the profile minimum is on a grid endpoint; the optimum is not "
                    "bracketed and rel_span is a lower bound only.",
        },
    }

    # ---- 4. iron residence time along the sloppy (degenerate) direction (#163 / research Q1) ----
    # At steady state the box's iron budget balances alpfe*PHI_DUST (source) against scavenging +
    # biological uptake (sink), so tau = [DFe] / (alpfe * PHI_DUST) [days]. The alpfe profile fixes
    # alpfe on the grid and RE-OPTIMISES scav_rat (+ the rest) at each point -- i.e. it walks the
    # sloppy iron eigenvector the real GEOTRACES concentration data leaves free. Tracing tau along
    # that walk shows how far residence time roams while the observable ([DFe]) stays pinned: the
    # LOCAL analogue of the 5-500 yr (100x) inter-model spread in Tagliabue et al. 2016 (GBC,
    # 10.1002/2015GB005289), which agrees on concentration. Reported per AOI, over the full grid and
    # over the data-consistent band {loss <= loss_star*(1+band)}. CAVEAT: the box is a 0-D surface
    # mixed layer with constant PHI_DUST=5e-5 mmol/m^3/d; Tagliabue's spread is whole-ocean, so this
    # is a structural analogy (concentration-pinned, residence-time-free), NOT a like-for-like tau.
    if args.iron_residence:
        import math as _math
        phi = float(R.PHI_DUST)
        idfe = R.I_DFE_1
        alpfe_idx = PARAM_NAMES.index("alpfe")
        per_aoi_tau = {b["key"]: [] for b in bundles}
        with torch.no_grad():
            for gi in range(G):
                theta_gp = prof_theta[:, gi].reshape(6, 1)          # re-optimised params at grid alpfe
                alpfe_gp = float(grid[gi])
                set_seeds(1)
                for b in bundles:
                    H, W = b["mask_f"].shape
                    pb = theta_gp.reshape(6, 1, 1, 1).expand(6, 1, H, W)
                    _, state = aoi_loss(b, pb)
                    dfe = state[idfe][0]                            # [H,W] surface DFe (mmol/m^3)
                    ocean = (b["mask_f"] > 0)
                    dfe_ocean = float((dfe * ocean).sum() / ocean.sum().clamp(min=1))
                    rec = {"alpfe": alpfe_gp, "loss": float(prof_losses[gi]),
                           "dfe_ocean_mean": dfe_ocean,
                           "tau_days": dfe_ocean / max(alpfe_gp * phi, 1e-30),
                           "tau_years": dfe_ocean / max(alpfe_gp * phi, 1e-30) / 365.25}
                    if b["n_geo_surf"] > 0:
                        gm = (b["geo_surf_mask_f"] > 0)
                        rec["dfe_geo_mean"] = float((dfe * gm).sum() / gm.sum().clamp(min=1))
                    per_aoi_tau[b["key"]].append(rec)

        def _band_summary(recs, band):
            keep = [r for r in recs if r["loss"] <= loss_star * (1.0 + band)] or recs
            taus = [r["tau_years"] for r in keep]
            dfes = [r["dfe_ocean_mean"] for r in keep]
            tmin, tmax = min(taus), max(taus)
            dmin, dmax = min(dfes), max(dfes)
            return {"band": band, "n_grid_in_band": len(keep),
                    "alpfe_range": [min(r["alpfe"] for r in keep), max(r["alpfe"] for r in keep)],
                    "tau_years_min": tmin, "tau_years_max": tmax,
                    "tau_fold": (tmax / tmin) if tmin > 0 else float("inf"),
                    "dfe_min": dmin, "dfe_max": dmax,
                    "dfe_fold": (dmax / dmin) if dmin > 0 else float("inf")}

        iron_res = {"phi_dust_mmol_m3_day": phi,
                    "note": "tau = dfe_ocean_mean / (alpfe * PHI_DUST). Profile re-optimises scav_rat "
                            "at each fixed alpfe, so the grid IS the sloppy iron direction. Compare "
                            "tau_fold (residence time roams) against dfe_fold (observable pinned).",
                    "tagliabue_2016_ref": {"doi": "10.1002/2015GB005289",
                                           "reported_spread": "whole-ocean model residence time "
                                                              "~5-500 yr (100x) at agreed concentration",
                                           "caveat": "0-D surface box vs whole-ocean: analogy of "
                                                     "structure, not a like-for-like tau"},
                    "per_aoi": {}}
        print("\n-- iron residence time tau = DFe/(alpfe*PHI_DUST) along the sloppy direction --")
        for k, recs in per_aoi_tau.items():
            s10 = _band_summary(recs, 0.10)
            s_all = _band_summary(recs, 1e9)
            iron_res["per_aoi"][k] = {"grid": recs, "band_10pct": s10, "full_grid": s_all}
            print(f"   {k:20s} band(+10% loss, n={s10['n_grid_in_band']}): "
                  f"tau {s10['tau_years_min']:.2f}-{s10['tau_years_max']:.2f} yr "
                  f"({s10['tau_fold']:.1f}x) while DFe moves {s10['dfe_fold']:.2f}x")
        out["iron_residence"] = iron_res

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
