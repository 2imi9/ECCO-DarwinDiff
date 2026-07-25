"""Full-box EKI: estimator-independence check for the trio {alpfe, scav_rat, R_PICPOC} (#187).

The genuine, Fable-vetted promotion of the analytic EKI prototype to the REAL geo1 box. This is a
METHOD-INDEPENDENCE check (closes the "single-method / DINN+autograd artifact" reviewer attack), NOT a
discovery: it grades against Carroll and the anchors, so it adds no new information -- it confirms that a
derivative-free ensemble estimator, run through the exact real box + real anchors, reaches the same
identifiability verdict as backprop.

Design (from the 2026-07-22 Fable adjudication of #187/#163):
  - reuse identifiability_sloppiness._import_runner() to expose the exact geo1 bundles + aoi_loss (real
    GEOTRACES surf/sub DFe + Daniels CP:PP targets/masks/IC/forcing), NB23_N_EPOCHS=0 (no training);
  - forward G(u[3,J]) -> obs[d,J] over the real observables {per-AOI mean log surface DFe, mean log
    subsurface DFe, mean log PIC:POC at Daniels cells}, holding growth {Smallgrow,Biggrow,diatomgraz}
    at Carroll and varying only the trio in log space;
  - run the unit-tested eki_core.eki (ILS-2013 inversion) with a wide log-uniform prior ensemble;
  - report posterior mean + spread per trio param vs Carroll vs the band, and the alpfe<->scav_rat
    sub-covariance principal axis (should ride the FeMIP sloppy ridge).

HONESTY (per the Fable check): eki_core.eki is an EKI *optimizer* (no inflation/localization); its
ensemble spread is NOT a calibrated Bayesian posterior and UNDER-covers along the sloppy direction. So
this reports the posterior MEAN (a point estimate, comparable to backprop recovery) and the *qualitative*
wide-vs-tight contrast, NOT a quantitative credible interval. A calibrated CI needs the EKS/sample stage
(CES), which is future work.

CPU-local (hours). Run: PYTHONPATH=src python scripts/analysis/eki_fullbox_trio.py --out <json>
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
TRIO = [0, 1, 5]  # alpfe, scav_rat, R_PICPOC


def _set_geo1_env():
    """The flagship geo1 recipe (ci_ensemble_array_2k.sbatch), CPU, no training."""
    env = {
        "AOIS": "eqpac,natlsubpolar,southernoceanpac",
        "GEOTRACES_W": "1.0", "GEOTRACES_SUB_W": "1.0", "POC_SUB_W": "3.0",
        "AOI_W_NATLSUBPOLAR": "2.0", "AOI_W_SOUTHERNOCEANPAC": "2.0", "CHL1_W_EXTRA": "3.0",
        "DANIELS_RPICPOC_W": "1.0", "DANIELS_DEPTH_MAX": "50.0", "POSI_W": "1.0",
        "NB23_PINN_WEIGHT": "3.0", "USE_EPPLEY_T": "1", "A_E_EPPLEY": "0.0633", "T_REF_EPPLEY": "15.0",
        "DINN_HIDDEN_DIM": "16", "FET_W": "1.0", "RATIO_W": "0.0",
        "NB23_N_EPOCHS": "0", "NB23_SEEDS": "0", "TORCH_COMPILE_BATCHED": "0",
        # NB: do NOT set CUDA_VISIBLE_DEVICES="" here -- on this Windows/CUDA box it leaves
        # torch.cuda.is_available()=True with no valid device, crashing the runner's device probe.
        # We match the runner's own device/dtype below instead.
    }
    for k, v in env.items():
        os.environ.setdefault(k, v)


def _masked_logmean(field_jhw: torch.Tensor, mask_hw: torch.Tensor) -> torch.Tensor:
    """mean over masked cells of log(field), per ensemble member -> [J]."""
    m = mask_hw.reshape(-1) > 0
    flat = field_jhw.reshape(field_jhw.shape[0], -1)[:, m]  # [J, nmask]
    return torch.log(flat.clamp(min=1e-12)).mean(dim=1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ensemble", type=int, default=256, help="EKI ensemble size J")
    ap.add_argument("--n-iter", type=int, default=30)
    ap.add_argument("--obs-sigma", type=float, default=0.30, help="log-space obs noise sd per observable")
    ap.add_argument("--prior-sd", type=float, default=2.0, help="log-space prior sd around Carroll per trio param")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    _set_geo1_env()
    from identifiability_sloppiness import _import_runner  # noqa: E402
    from eki_core import eki  # noqa: E402  (the unit-tested #187 core)

    R = _import_runner()
    bundles = R.bundles
    aoi_loss = R.aoi_loss
    carroll = R.CARROLL_VALUES.detach().cpu().numpy().astype(np.float64)  # [6]
    bounds = R.PARAM_BOUNDS.detach().cpu().numpy().astype(np.float64)      # [6,2]
    lo, hi = bounds[:, 0], bounds[:, 1]
    # Match the runner's own device/dtype (it picked them at import; bundles live there).
    device = bundles[0]["mask_f"].device
    dtype = bundles[0]["geo_surf_target_t"].dtype if bundles[0].get("n_geo_surf", 0) > 0 else torch.float32
    print(f"[eki-fullbox] device={device} dtype={dtype}", flush=True)

    # Which observables exist, and their target values y (constant, from the real anchors).
    obs_specs = []  # (bundle_index, kind)
    y = []
    for bi, b in enumerate(bundles):
        if b.get("n_geo_surf", 0) > 0:
            obs_specs.append((bi, "surf"))
            y.append(float(torch.log(b["geo_surf_target_t"][b["geo_surf_mask_t"] > 0].clamp(min=1e-12)).mean()))
        if b.get("n_geo_sub", 0) > 0:
            obs_specs.append((bi, "sub"))
            y.append(float(torch.log(b["geo_sub_target_t"][b["geo_sub_mask_t"] > 0].clamp(min=1e-12)).mean()))
        if b.get("n_daniels", 0) > 0:
            obs_specs.append((bi, "daniels"))
            y.append(float(torch.log(b["daniels_target_t"][b["daniels_mask_t"] > 0].clamp(min=1e-12)).mean()))
    y = np.array(y, dtype=np.float64)
    d = len(y)
    gamma = np.diag(np.full(d, args.obs_sigma ** 2))
    print(f"[eki-fullbox] observables d={d}: "
          + ", ".join(f"{bundles[bi]['key']}:{kind}" for bi, kind in obs_specs), flush=True)

    carroll_t = torch.tensor(carroll, dtype=dtype, device=device)

    def forward(u_np: np.ndarray) -> np.ndarray:
        """u_np [3,J] = log(trio) -> obs [d,J]. Growth held at Carroll; box integrated per ensemble."""
        J = u_np.shape[1]
        trio = np.exp(u_np)                                   # [3,J]
        theta = np.tile(carroll[:, None], (1, J))             # [6,J]
        theta[TRIO] = np.clip(trio, lo[TRIO, None], hi[TRIO, None])
        th = torch.tensor(theta, dtype=dtype, device=device)  # [6,J]
        rows = [None] * d
        # group observables by bundle so each bundle integrates once
        by_bundle = {}
        for oi, (bi, kind) in enumerate(obs_specs):
            by_bundle.setdefault(bi, []).append((oi, kind))
        for bi, items in by_bundle.items():
            b = bundles[bi]
            H, W = b["mask_f"].shape
            pb = th.reshape(6, J, 1, 1).expand(6, J, H, W)
            with torch.no_grad():
                _, state = aoi_loss(b, pb)                    # state [15,J,H,W]
            for oi, kind in items:
                if kind == "surf":
                    rows[oi] = _masked_logmean(state[R.I_DFE_1], b["geo_surf_mask_t"])
                elif kind == "sub":
                    rows[oi] = _masked_logmean(state[R.I_DFE_2], b["geo_sub_mask_t"])
                else:  # daniels PIC:POC
                    ratio = state[R.I_PIC_1] / state[R.I_POC_1].clamp(min=1e-9)
                    rows[oi] = _masked_logmean(ratio, b["daniels_mask_t"])
        return torch.stack(rows).cpu().numpy()                # [d,J]

    # Bundles were built with N_SEEDS=1; expand each state0 to the ensemble size J so the box's
    # per-step torch.stack does not mix leading dims J and 1 (mirrors identifiability_sloppiness
    # set_seeds()). Broadcast view = cheap; J is constant across the EKI run.
    J = args.ensemble
    for b in bundles:
        s0 = b["state0_per_seed"]
        b["state0_per_seed"] = s0[:, :1].expand(s0.shape[0], J, s0.shape[2], s0.shape[3])

    # wide log-uniform prior ensemble over the trio (centered on Carroll, sd=prior-sd in log space)
    rng = np.random.default_rng(args.seed)
    u0 = np.log(carroll[TRIO])[:, None] + rng.normal(0.0, args.prior_sd, size=(3, args.ensemble))
    print(f"[eki-fullbox] running EKI: J={args.ensemble}, n_iter={args.n_iter}, "
          f"prior_sd={args.prior_sd}, obs_sigma={args.obs_sigma}", flush=True)
    post = eki(y, gamma, forward, u0, n_iter=args.n_iter, rng=rng)   # [3,J]

    theta_post = np.exp(post)                                        # physical [3,J]
    theta_post = np.clip(theta_post, lo[TRIO, None], hi[TRIO, None])
    mean = theta_post.mean(axis=1)
    cv = theta_post.std(axis=1) / np.abs(mean)
    result = {"n_ensemble": args.ensemble, "n_iter": args.n_iter, "obs_sigma": args.obs_sigma,
              "observables": [f"{bundles[bi]['key']}:{k}" for bi, k in obs_specs],
              "trio": {}}
    print("\n=== full-box EKI posterior (trio; growth held at Carroll) ===")
    print(f"{'param':<10}{'post_mean':>13}{'Carroll':>13}{'rel_off':>9}{'CV%':>8}")
    for j, pi in enumerate(TRIO):
        rel = abs(mean[j] - carroll[pi]) / abs(carroll[pi])
        band = "Excellent" if rel <= 0.05 else "Cal-grade" if rel <= 0.40 else "Loose" if rel <= 0.80 else "Drifted"
        result["trio"][PARAM_NAMES[pi]] = {"post_mean": float(mean[j]), "carroll": float(carroll[pi]),
                                           "rel_offset": float(rel), "cv": float(cv[j]), "band": band}
        print(f"{PARAM_NAMES[pi]:<10}{mean[j]:>13.5g}{carroll[pi]:>13.5g}{rel:>9.2f}{cv[j]*100:>7.1f}  {band}")

    # alpfe<->scav_rat sub-covariance principal axis (should ride the FeMIP sloppy ridge)
    sub = post[[0, 1], :]                                            # ln alpfe, ln scav_rat
    C = np.cov(sub)
    w, V = np.linalg.eigh(C)
    sloppy = V[:, int(np.argmax(w))]
    result["alpfe_scav_sloppy_axis"] = {"alpfe": float(sloppy[0]), "scav_rat": float(sloppy[1]),
                                        "align_with_(1,1)": float(abs(sloppy @ (np.array([1, 1]) / np.sqrt(2))))}
    print(f"\nalpfe<->scav_rat posterior sloppy axis: ({sloppy[0]:+.2f},{sloppy[1]:+.2f})  "
          f"|align (1,1)/sqrt2| = {result['alpfe_scav_sloppy_axis']['align_with_(1,1)']:.3f}")
    print("(a ridge along (1,-1) = source/scavenging trade at fixed concentration = the FeMIP degeneracy)")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
