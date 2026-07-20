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
    ap.add_argument("--mode", default="global", choices=["global", "peraoi"],
                    help="'global' (default) = shared-theta optimum + 6x6 Hessian + profile; "
                         "'peraoi' = a SEPARATE 6x6 Fisher/Hessian per AOI at Carroll, giving "
                         "basin-resolved identifiability (which parameters each basin's data "
                         "constrains). First cut toward the per-cell spatial map (#152); the box "
                         "is per-cell independent so the field Fisher is block-diagonal.")
    ap.add_argument("--loss", default="full", choices=["full", "realiron", "realbsi", "realpic"],
                    help="'full' = exact runner joint loss; 'realiron' = ONLY the REAL "
                         "GEOTRACES dissolved-iron residual (surf+sub, for alpfe/scav_rat); "
                         "'realbsi' = ONLY the REAL GEOTRACES biogenic-silica residual (for "
                         "diatomgraz). Real-world-relevance audit: 'does real data prefer Carroll?' "
                         "(issue #143/#116). Needs the corresponding weight on (GEOTRACES_W / POSI_W).")
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
    args = ap.parse_args()

    import torch
    from darwindiff.carroll6 import CARROLL_VALUES, PARAM_BOUNDS

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss
    R._RATIO_W_NOW = R.RATIO_W  # full ratio weight (converged state)

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
            print(f"\n-- AOI {b['key']} (weight {b['weight']}, {n_active} cells) empirical Fisher at Carroll --")
            print("   eigenvalues low->high: " + ", ".join(f"{e:.2e}" for e in evals_l)
                  + (f"   (sloppiness {span:.2f} dec)" if len(pos) >= 2 else ""))
            print("   per-param Fisher info (diag; HIGH = constrained): "
                  + "  ".join(f"{PARAM_NAMES[i]}={selfinfo[i]:.2e}" for i in range(6)))
            print("   per-param CRLB (var bound; HIGH = unconstrained): "
                  + "  ".join(f"{PARAM_NAMES[i]}={crlb[i]:.1e}" for i in range(6)))
            print("   sloppiest direction: "
                  + " ".join(f"{PARAM_NAMES[i]}{float(sloppy[i]):+.2f}" for i in range(6)))
            per_aoi[b["key"]] = {
                "weight": float(b["weight"]), "n_cells": n_active, "eigenvalues": evals_l,
                "sloppiness_decades": span,
                "fisher_info_diag": {PARAM_NAMES[i]: selfinfo[i] for i in range(6)},
                "crlb": {PARAM_NAMES[i]: crlb[i] for i in range(6)},
                "sloppy_vector": {PARAM_NAMES[i]: float(sloppy[i]) for i in range(6)},
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

    hess_star = hess_report(theta_star, "theta*")
    hess_carroll = hess_report(carroll, "Carroll")

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
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
