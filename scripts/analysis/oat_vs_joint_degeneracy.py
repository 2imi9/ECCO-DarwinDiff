"""One-at-a-time vs joint fit — the Menemenlis (2005) referee-accepted degeneracy demonstration.

Highest-value unimplemented advice from the citation-method pass: SHOW the alpfe<->scav_rat rank-1 FeMIP
degeneracy instead of asserting it. Fit alpfe alone (others at Carroll), scav_rat alone, then both jointly,
against the REAL GEOTRACES iron residual (the observable that carries the pair). Two degeneracy signatures:
  (1) NON-ADDITIVE cost reduction — joint reduction ~ max(OAT), not the sum, if the two params capture the
      same information (linear dependence). Additive => independent; ~max => degenerate.
  (2) The joint optimum lands on a RIDGE (a different alpfe/scav_rat than either OAT), and the recovered
      pair aligns with the analytic sloppy direction.

Reuses identifiability_sloppiness._import_runner + the exact real GEOTRACES iron loss (realiron). CPU/GPU
local. Run: PYTHONPATH=src python scripts/analysis/oat_vs_joint_degeneracy.py --out <json>
"""
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
I_ALPFE, I_SCAV = 0, 1


def _geo1_env():
    env = {
        "AOIS": "eqpac,natlsubpolar,southernoceanpac",
        "GEOTRACES_W": "1.0", "GEOTRACES_SUB_W": "1.0", "POC_SUB_W": "3.0",
        "AOI_W_NATLSUBPOLAR": "2.0", "AOI_W_SOUTHERNOCEANPAC": "2.0", "CHL1_W_EXTRA": "3.0",
        "DANIELS_RPICPOC_W": "1.0", "DANIELS_DEPTH_MAX": "50.0", "POSI_W": "1.0",
        "NB23_PINN_WEIGHT": "3.0", "USE_EPPLEY_T": "1", "A_E_EPPLEY": "0.0633", "T_REF_EPPLEY": "15.0",
        "DINN_HIDDEN_DIM": "16", "FET_W": "1.0", "RATIO_W": "0.0",
        "NB23_N_EPOCHS": "0", "NB23_SEEDS": "0", "TORCH_COMPILE_BATCHED": "0",
    }
    for k, v in env.items():
        os.environ.setdefault(k, v)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--restarts", type=int, default=6, help="random restarts per scenario (best kept)")
    ap.add_argument("--steps", type=int, default=1200)
    ap.add_argument("--lr", type=float, default=5e-2)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    _geo1_env()
    from identifiability_sloppiness import _import_runner  # noqa: E402
    R = _import_runner()
    bundles, aoi_loss = R.bundles, R.aoi_loss
    carroll = R.CARROLL_VALUES.detach().cpu().numpy().astype(np.float64)
    bounds = R.PARAM_BOUNDS.detach().cpu().numpy().astype(np.float64)
    lo, hi = bounds[:, 0], bounds[:, 1]
    device = bundles[0]["mask_f"].device
    dtype = bundles[0]["geo_surf_target_t"].dtype if bundles[0].get("n_geo_surf", 0) > 0 else torch.float32
    S = args.restarts

    for b in bundles:  # expand state0 to the restart batch (mirrors set_seeds)
        s0 = b["state0_per_seed"]
        b["state0_per_seed"] = s0[:, :1].expand(s0.shape[0], S, s0.shape[2], s0.shape[3])

    lo_t = torch.tensor(lo, dtype=dtype, device=device)
    hi_t = torch.tensor(hi, dtype=dtype, device=device)
    carroll_t = torch.tensor(carroll, dtype=dtype, device=device)

    def to_phys(u):                        # u [6,S] uncon -> physical [6,S]
        return lo_t[:, None] + (hi_t - lo_t)[:, None] * torch.sigmoid(u)

    def to_uncon(theta):                   # physical [6] -> uncon [6]
        frac = ((theta - lo_t) / (hi_t - lo_t)).clamp(1e-6, 1 - 1e-6)
        return torch.log(frac / (1 - frac))

    def iron_loss(theta):                  # theta [6,S] -> [S]  (REAL GEOTRACES iron residual, surf+sub)
        Sn = theta.shape[1]
        z = theta.new_zeros(Sn)
        for b in bundles:
            H, W = b["mask_f"].shape
            pb = theta.reshape(6, Sn, 1, 1).expand(6, Sn, H, W)
            _, state = aoi_loss(b, pb)
            if R.GEOTRACES_W > 0 and b["n_geo_surf"] > 0:
                resid = (state[R.I_DFE_1] - b["geo_surf_target_t"][None]) * b["geo_surf_mask_f"][None]
                scale = (b["geo_surf_target_t"][b["geo_surf_mask_t"]] ** 2).mean().clamp(min=1e-30)
                z = z + R.GEOTRACES_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_surf_f"] / scale
            if R.GEOTRACES_SUB_W > 0 and b["n_geo_sub"] > 0:
                resid = (state[R.I_DFE_2] - b["geo_sub_target_t"][None]) * b["geo_sub_mask_f"][None]
                scale = (b["geo_sub_target_t"][b["geo_sub_mask_t"]] ** 2).mean().clamp(min=1e-30)
                z = z + R.GEOTRACES_SUB_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_sub_f"] / scale
        return z

    baseline = float(iron_loss(carroll_t.reshape(6, 1))[0])
    print(f"[oat] baseline iron loss at Carroll = {baseline:.5e}  (device={device})", flush=True)

    g = torch.Generator(device="cpu").manual_seed(0)

    def fit(free):
        """Optimize params in `free` (others fixed at Carroll), S restarts, keep the best."""
        # restart inits: col 0 = Carroll; cols 1..S-1 log-uniform in bounds on the free dims
        u0 = to_uncon(carroll_t).reshape(6, 1).expand(6, S).clone()
        if S > 1:
            llo, lhi = torch.log10(lo_t), torch.log10(hi_t)
            r = torch.rand(6, S - 1, generator=g).to(device)
            rand_phys = torch.pow(10.0, (llo[:, None] + (lhi - llo)[:, None] * r))
            u0[:, 1:] = to_uncon_batch(rand_phys, lo_t, hi_t)
        u = u0.clone().detach().requires_grad_(True)
        opt = torch.optim.Adam([u], lr=args.lr)
        fixed_mask = torch.ones(6, dtype=torch.bool, device=device)
        fixed_mask[free] = False
        for _ in range(args.steps):
            opt.zero_grad()
            theta = to_phys(u)
            theta = torch.where(fixed_mask[:, None], carroll_t[:, None].expand(6, S), theta)
            iron_loss(theta).sum().backward()
            with torch.no_grad():
                u.grad[fixed_mask] = 0.0    # freeze fixed dims
            opt.step()
        with torch.no_grad():
            theta = to_phys(u)
            theta = torch.where(fixed_mask[:, None], carroll_t[:, None].expand(6, S), theta)
            losses = iron_loss(theta)
            bi = int(torch.argmin(losses))
            return theta[:, bi].cpu().numpy(), float(losses[bi])

    def to_uncon_batch(theta, lo_t, hi_t):
        frac = ((theta - lo_t[:, None]) / (hi_t - lo_t)[:, None]).clamp(1e-6, 1 - 1e-6)
        return torch.log(frac / (1 - frac))

    scen = {}
    for name, free in [("oat_alpfe", [I_ALPFE]), ("oat_scav_rat", [I_SCAV]), ("joint", [I_ALPFE, I_SCAV])]:
        th, loss = fit(free)
        red = baseline - loss
        scen[name] = {"loss": loss, "reduction": red,
                      "alpfe": float(th[I_ALPFE]), "scav_rat": float(th[I_SCAV])}
        print(f"[oat] {name:12s} loss={loss:.5e} reduction={red:.5e}  "
              f"alpfe={th[I_ALPFE]:.4f} scav_rat={th[I_SCAV]:.4e}", flush=True)

    sum_oat = scen["oat_alpfe"]["reduction"] + scen["oat_scav_rat"]["reduction"]
    max_oat = max(scen["oat_alpfe"]["reduction"], scen["oat_scav_rat"]["reduction"])
    additivity = scen["joint"]["reduction"] / sum_oat if sum_oat > 0 else float("nan")
    over_max = scen["joint"]["reduction"] / max_oat if max_oat > 0 else float("nan")
    verdict = ("DEGENERATE (joint ~ max(OAT), not additive)" if over_max < 1.3
               else "INDEPENDENT (joint ~ sum(OAT))" if additivity > 0.8 else "PARTIAL")
    result = {"baseline": baseline, "scenarios": scen,
              "sum_oat_reduction": sum_oat, "max_oat_reduction": max_oat,
              "joint_over_sum": additivity, "joint_over_max": over_max,
              "carroll": {"alpfe": float(carroll[I_ALPFE]), "scav_rat": float(carroll[I_SCAV])},
              "verdict": verdict}
    print(f"\n=== Menemenlis OAT-vs-joint degeneracy ===")
    print(f"  reductions: alpfe-alone {scen['oat_alpfe']['reduction']:.4e}, "
          f"scav-alone {scen['oat_scav_rat']['reduction']:.4e}, joint {scen['joint']['reduction']:.4e}")
    print(f"  joint / sum(OAT) = {additivity:.3f}   joint / max(OAT) = {over_max:.3f}")
    print(f"  VERDICT: {verdict}")
    print(f"  joint optimum: alpfe={scen['joint']['alpfe']:.4f} scav_rat={scen['joint']['scav_rat']:.4e} "
          f"(vs Carroll alpfe={carroll[I_ALPFE]:.4f} scav_rat={carroll[I_SCAV]:.4e})")
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
