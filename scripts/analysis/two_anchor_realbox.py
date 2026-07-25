#!/usr/bin/env python3
r"""two_anchor_realbox.py -- does the {dust SOURCE anchor + scavenging SINK anchor}
design break the alpfe<->scav_rat degeneracy in the REAL differentiable Darwin box?

This promotes the analytic OSSE (scripts/analysis/two_anchor_osse.py) into the REAL
Darwin 0-D box. It reuses identifiability_sloppiness._import_runner() to expose the
EXACT per-AOI bundles + aoi_loss (real GEOTRACES surf/sub DFe + Daniels CP:PP anchors,
IC/forcing), with training disabled (NB23_N_EPOCHS=0), under the ANCHORS-ONLY recipe
(GEOTRACES iron + Daniels ON; Darwin spatial-pattern loss + PINN OFF) -- the recipe whose
verified n=50 cluster batch recovers alpfe 50/50, R_PICPOC 28/50, but scav_rat 0/50 per-AOI
(docs/findings/2026-07-22_anchors_only_n50_verified.md). scav_rat is the binding leg.

WHY THIS IS A SELF-TWIN (read this before quoting any number)
------------------------------------------------------------
The two anchors are SYNTHETIC, computed FROM THE BOX at Carroll truth so they are
self-consistent. A positive result therefore validates the identifiability GEOMETRY of the
real model (can a source row + a sink row make scav_rat identifiable, and is it conditional
on pinning the export/uptake partition?), NOT real-data recovery. It says nothing about
whether a real 234Th dataset would pin scav_rat -- only that the model's response surface
has the geometry the OSSE predicted.

THE BOX IRON BUDGET (run_v3.0 PINN block, lines ~1637-1638; carroll6.py step)
    d[DFe]/dt = alpfe*PHI_DUST            (SOURCE)
              - scav_rat*86400*[DFe]*[POC]  (SINK: scavenging, LUMPED onto POC)
              - Q_FE*growth_total           (SINK: biological uptake/export == the nuisance E)
    [DFe] observation constrains only the SOURCE/SINK combination  => alpfe<->scav_rat rank-1.

THE TWO SYNTHETIC ANCHORS (per-cell masked MSE, scale-normalized like GEOTRACES/Daniels)
  (a) DUST (source, out-of-manifold): target = alpfe_carroll*PHI_DUST; pred = alpfe*PHI_DUST.
      PHI_DUST is the box's homogenized soluble-Fe deposition scalar (the 0-D surrogate of the
      Mahowald D_sol field). Pins alpfe directly.
  (b) SCAV removal (sink), in two modes to reproduce the OSSE "partition tax":
      - PINNED: anchor the scavenging term ALONE  scav_rat*86400*[DFe]*[POC]  (== a 234Th flux
        with the export partition already removed, e.g. via UVP5/POC). Isolates the sink axis.
      - FREE:   anchor the LUMPED particulate removal  scav_rat*86400*[DFe]*[POC] + Q_FE*growth_total
        (== a raw 234Th flux, scavenging + export together). scav_rat then trades against the
        (free) growth params -> not point-identified. This is the partition tax.

CONFIGS (each graded at n>=30 random-init seeds):
  baseline (anchors only) | +dust | +scav(pinned) | +both(pinned) | +both(free)

Deliverables per config:
  * multi-seed recovery: Cal+ n/seeds and median for scav_rat / alpfe / R_PICPOC (global-theta;
    "recovered value is the cell mean of a global parameter" per identifiability_sloppiness).
  * Fisher/curvature geometry at the config optimum: |rho(alpfe,scav_rat)| and the scav_rat CRLB
    (relative) -- the direct real-box analogue of the OSSE's |rho|: 1 -> 0.195.

Grading matches verify_run.py: band_of(rel_offset), Cal+ = {Excellent, Cal-grade} (rel<=0.40).

Usage (cluster, env auto-set below; NB23_N_EPOCHS forced to 0):
  PYTHONPATH=src python scripts/analysis/two_anchor_realbox.py --n-seeds 32 --steps 800 \
      --out docs/findings/two_anchor_realbox.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
I_ALPFE, I_SCAV, I_SMALL, I_BIG, I_DGRAZ, I_RPP = range(6)


def _set_anchors_only_env():
    """The verified anchors-only (PINN/pattern OFF) recipe on the geo1 3-AOI set."""
    env = {
        "AOIS": "eqpac,natlsubpolar,southernoceanpac",
        # real absolute anchors ON:
        "GEOTRACES_W": "1.0", "GEOTRACES_SUB_W": "1.0",
        "DANIELS_RPICPOC_W": "1.0", "DANIELS_DEPTH_MAX": "50.0",
        # AOI up-weights as in the flagship (harmless here; loss is summed with bundle weights):
        "AOI_W_NATLSUBPOLAR": "2.0", "AOI_W_SOUTHERNOCEANPAC": "2.0",
        # spatial-pattern + PINN + every other term OFF -> pure anchors-only loss:
        "DARWIN_PATTERN_W": "0.0", "NB23_PINN_WEIGHT": "0.0", "PINN_W": "0.0",
        "CHL1_W_EXTRA": "0.0", "POC_SUB_W": "0.0", "POSI_W": "0.0", "POSI_DARWIN_W": "0.0",
        "PIC_ABS_W": "0.0", "POC_ABS_W": "0.0", "ALK_ABS_W": "0.0", "RATIO_W": "0.0",
        "PRIMPROD_W": "0.0", "F_CO2_ABS_W": "0.0", "GEOTRACES_POC_SUB_W": "0.0",
        "USE_EPPLEY_T": "1", "A_E_EPPLEY": "0.0633", "T_REF_EPPLEY": "15.0",
        # no training; batched compile off (FD Hessian + Adam are fine eager):
        "NB23_N_EPOCHS": "0", "NB23_SEEDS": "0", "TORCH_COMPILE_BATCHED": "0",
    }
    for k, v in env.items():
        os.environ.setdefault(k, v)


# ---- config table (which anchors are active) --------------------------------
CONFIGS = {
    "baseline":       {"dust": False, "scav_pinned": False, "scav_free": False},
    "dust":           {"dust": True,  "scav_pinned": False, "scav_free": False},
    "scav_pinned":    {"dust": False, "scav_pinned": True,  "scav_free": False},
    "both_pinned":    {"dust": True,  "scav_pinned": True,  "scav_free": False},
    "both_free":      {"dust": True,  "scav_pinned": False, "scav_free": True},
}


def band_of(rel: float) -> str:
    if rel <= 0.05:
        return "Excellent"
    if rel <= 0.40:
        return "Cal-grade"
    if rel <= 0.80:
        return "Loose"
    return "Drifted"


CAL_PLUS = {"Excellent", "Cal-grade"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-seeds", type=int, default=32, help="random-init recovery seeds (>=30)")
    ap.add_argument("--steps", type=int, default=800, help="Adam steps per recovery")
    ap.add_argument("--lr", type=float, default=5e-2)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for the random inits")
    ap.add_argument("--dust-w", type=float, default=1.0, help="dust anchor weight")
    ap.add_argument("--scav-w", type=float, default=1.0, help="scav anchor weight")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    _set_anchors_only_env()
    import torch
    from identifiability_sloppiness import _import_runner

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss
    R._RATIO_W_NOW = getattr(R, "RATIO_W", 0.0)

    PHI_DUST = float(R.PHI_DUST)
    Q_FE = float(R.Q_FE)
    K_FE = float(R.K_FE)
    MU_DIATOM = float(R.MU_DEFAULT_DIATOM)
    MU_SYN = float(R.MU_DEFAULT_SYN)
    MU_PROLL = float(R.MU_DEFAULT_PROLL)
    I_DFE_1, I_POC_1 = R.I_DFE_1, R.I_POC_1
    I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL = R.I_DIATOM, R.I_LGE, R.I_SYN, R.I_PROLL, R.I_PROHL

    carroll = R.CARROLL_VALUES.to(dev).float()          # [6]
    bounds = R.PARAM_BOUNDS.to(dev).float()
    lo = bounds[:, 0:1]                                  # [6,1]
    hi = bounds[:, 1:2]
    aois = [b["key"] for b in bundles]
    weights = {b["key"]: float(b["weight"]) for b in bundles}
    print(f"\n=== two-anchor real-box | AOIS={aois} weights={weights} ===")
    print(f"    PHI_DUST={PHI_DUST:.3g} Q_FE={Q_FE:.3g} K_FE={K_FE:.3g} "
          f"MU(diatom,syn,proll)=({MU_DIATOM:.3g},{MU_SYN:.3g},{MU_PROLL:.3g})")
    print(f"    dust_w={args.dust_w} scav_w={args.scav_w} n_seeds={args.n_seeds} steps={args.steps}")

    # expand state0 to the seed batch on demand (mirrors identifiability_sloppiness)
    _base_state0 = {b["key"]: b["state0_per_seed"] for b in bundles}

    def set_seeds(S):
        for b in bundles:
            base = _base_state0[b["key"]]
            b["state0_per_seed"] = base[:, :1].expand(base.shape[0], S, base.shape[2], base.shape[3])

    def to_phys(u):
        return lo + (hi - lo) * torch.sigmoid(u)

    def to_uncon(theta):
        frac = ((theta - lo) / (hi - lo)).clamp(1e-6, 1 - 1e-6)
        return torch.log(frac / (1 - frac))

    def growth_total(state, theta_bshw):
        f_fe = state[I_DFE_1] / (state[I_DFE_1] + K_FE)
        return (MU_DIATOM * f_fe * state[I_DIATOM]
                + theta_bshw[I_BIG] * f_fe * state[I_LGE]
                + MU_SYN * f_fe * state[I_SYN]
                + MU_PROLL * f_fe * state[I_PROLL]
                + theta_bshw[I_SMALL] * f_fe * state[I_PROHL])

    # -------- 1. synthetic anchor targets from the box at Carroll truth --------
    set_seeds(1)
    targets = {}
    print("\n-- self-twin anchor targets (box at Carroll) --")
    for b in bundles:
        H, W = b["mask_f"].shape
        cf = carroll.reshape(6, 1, 1, 1).expand(6, 1, H, W)
        with torch.no_grad():
            _, state = aoi_loss(b, cf)                  # state [15,1,H,W]
        dfe = state[I_DFE_1][0]                          # [H,W]
        poc = state[I_POC_1][0]
        ocean = (b["mask_f"] > 0).float()
        n_ocean = ocean.sum().clamp(min=1.0)
        scav_rem = carroll[I_SCAV] * 86400.0 * dfe * poc            # [H,W]
        gt = growth_total(state, cf)[0]                             # [H,W]
        uptake = Q_FE * gt
        total_rem = scav_rem + uptake
        dust_val = float(carroll[I_ALPFE]) * PHI_DUST               # scalar
        targets[b["key"]] = {
            "ocean": ocean, "n_ocean": n_ocean,
            "dust_target": dust_val,
            "dust_scale": max(dust_val ** 2, 1e-30),
            "scav_rem_target": scav_rem,
            "scav_scale": ((scav_rem[ocean > 0] ** 2).mean().clamp(min=1e-30)),
            "total_rem_target": total_rem,
            "total_scale": ((total_rem[ocean > 0] ** 2).mean().clamp(min=1e-30)),
        }
        sm = lambda t: float((t * ocean).sum() / n_ocean)
        print(f"   {b['key']:20s} DFe~{sm(dfe):.3e} POC~{sm(poc):.3e} "
              f"scav_rem~{sm(scav_rem):.3e} uptake~{sm(uptake):.3e} "
              f"(scav frac {sm(scav_rem)/max(sm(total_rem),1e-30):.2f})")

    def anchors(b, state, theta_bshw, cfg):
        tj = targets[b["key"]]
        ocean = tj["ocean"]
        n = tj["n_ocean"]
        add = theta_bshw.new_zeros(theta_bshw.shape[1])   # [S]
        if cfg["dust"]:
            pred = theta_bshw[I_ALPFE] * PHI_DUST          # [S,H,W]
            resid = (pred - tj["dust_target"]) * ocean[None]
            add = add + args.dust_w * (resid ** 2).flatten(1).sum(1) / n / tj["dust_scale"]
        if cfg["scav_pinned"]:
            pred = theta_bshw[I_SCAV] * 86400.0 * state[I_DFE_1] * state[I_POC_1]
            resid = (pred - tj["scav_rem_target"][None]) * ocean[None]
            add = add + args.scav_w * (resid ** 2).flatten(1).sum(1) / n / tj["scav_scale"]
        if cfg["scav_free"]:
            scav_rem = theta_bshw[I_SCAV] * 86400.0 * state[I_DFE_1] * state[I_POC_1]
            pred = scav_rem + Q_FE * growth_total(state, theta_bshw)
            resid = (pred - tj["total_rem_target"][None]) * ocean[None]
            add = add + args.scav_w * (resid ** 2).flatten(1).sum(1) / n / tj["total_scale"]
        return add

    def combined_loss(theta, cfg):
        """theta [6,S] -> [S]. anchors-only box loss + active synthetic anchors."""
        S = theta.shape[1]
        set_seeds(S)
        z = theta.new_zeros(S)
        for b in bundles:
            H, W = b["mask_f"].shape
            pb = theta.reshape(6, S, 1, 1).expand(6, S, H, W)
            lbase, state = aoi_loss(b, pb)               # anchors-only base
            z = z + b["weight"] * (lbase + anchors(b, state, pb, cfg))
        return z

    def optimise(u_init, cfg, steps):
        u = u_init.clone().detach().requires_grad_(True)
        opt = torch.optim.Adam([u], lr=args.lr)
        for _ in range(steps):
            opt.zero_grad()
            combined_loss(to_phys(u), cfg).sum().backward()
            opt.step()
        with torch.no_grad():
            th = to_phys(u)
            return th.detach(), combined_loss(th, cfg).detach()

    # ---- Fisher/curvature helpers (FD Hessian of the loss, like identifiability_sloppiness) ----
    def grad_at(th, cfg):
        t = th.detach().reshape(6, 1).clone().requires_grad_(True)
        (g,) = torch.autograd.grad(combined_loss(t, cfg).sum(), t)
        return g.detach().reshape(6)

    def fd_hessian(at, cfg, rel_eps=2e-2):
        at = at.detach().reshape(6)
        Hm = torch.zeros(6, 6, device=at.device, dtype=at.dtype)
        for j in range(6):
            eps = rel_eps * max(abs(float(at[j])), 1e-30)
            ap = at.clone(); ap[j] += eps
            am = at.clone(); am[j] -= eps
            Hm[:, j] = (grad_at(ap, cfg) - grad_at(am, cfg)) / (2 * eps)
        return 0.5 * (Hm + Hm.T)

    def geometry(theta_star, cfg):
        """Normalised curvature at theta*: eigenspectrum + marginal |rho(alpfe,scav)| + scav CRLB."""
        at = theta_star.detach().reshape(6)
        scale = at.abs().clamp(min=1e-30)
        Hn = fd_hessian(at, cfg) * scale[:, None] * scale[None, :]      # dimensionless (relative)
        Hn = 0.5 * (Hn + Hn.T)
        evals = [float(x) for x in torch.linalg.eigvalsh(Hn)]
        # marginal covariance over (alpfe,scav) with the other 4 as nuisances, via ridge-regularised inverse
        emax = max(abs(e) for e in evals) if evals else 1.0
        ridge = 1e-6 * emax + 1e-30
        cov = torch.linalg.inv(Hn + ridge * torch.eye(6, device=Hn.device, dtype=Hn.dtype))
        caa, css, cas = float(cov[I_ALPFE, I_ALPFE]), float(cov[I_SCAV, I_SCAV]), float(cov[I_ALPFE, I_SCAV])
        rho = cas / math.sqrt(abs(caa * css)) if caa > 0 and css > 0 else float("nan")
        crlb_scav = math.sqrt(css) if css > 0 else float("inf")
        crlb_alpfe = math.sqrt(caa) if caa > 0 else float("inf")
        pos = [e for e in evals if e > 1e-6 * emax]
        span = math.log10(max(pos) / min(pos)) if len(pos) >= 2 else float("nan")
        return {"eigenvalues": evals, "sloppiness_decades": span,
                "rho_alpfe_scav": rho, "crlb_rel_scav": crlb_scav, "crlb_rel_alpfe": crlb_alpfe}

    # -------- 2. run every config --------
    g0 = torch.Generator(device="cpu").manual_seed(args.seed)
    llo, lhi = torch.log10(lo), torch.log10(hi)
    S = args.n_seeds
    # shared random inits (same seeds across configs -> paired comparison)
    u_rand = torch.rand(6, S, generator=g0).to(lo.device)
    rand_theta = torch.pow(10.0, llo + (lhi - llo) * u_rand)          # [6,S] physical
    u_init = to_uncon(rand_theta)

    carroll_np = {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)}
    results = {"aois": aois, "weights": weights, "n_seeds": S, "steps": args.steps,
               "carroll": carroll_np, "dust_w": args.dust_w, "scav_w": args.scav_w,
               "note": "SELF-TWIN: synthetic anchors from the box at Carroll. Validates the "
                       "identifiability GEOMETRY of the real model, not real-data recovery.",
               "configs": {}}

    for name, cfg in CONFIGS.items():
        print(f"\n{'='*70}\n[{name}] anchors active: "
              f"{[k for k,v in cfg.items() if v] or ['none (anchors-only baseline)']}")
        theta_f, loss_f = optimise(u_init, cfg, args.steps)            # [6,S], [S]
        # grade every seed
        per_param = {}
        for i, p in enumerate(PARAM_NAMES):
            rec = theta_f[i]                                           # [S]
            rel = (rec - carroll[i]).abs() / abs(float(carroll[i]))
            bands = [band_of(float(r)) for r in rel]
            calplus = sum(1 for bd in bands if bd in CAL_PLUS)
            med = float(rec.median())
            per_param[p] = {"calplus_n": calplus, "n": S,
                            "median": med, "median_rel_to_carroll": med / float(carroll[i]),
                            "cv": float(rec.std() / (rec.mean().abs() + 1e-30))}
        # geometry at the best-loss seed's optimum
        best = int(torch.argmin(loss_f))
        geo = geometry(theta_f[:, best], cfg)
        results["configs"][name] = {"active": [k for k, v in cfg.items() if v],
                                    "loss_best": float(loss_f[best]),
                                    "per_param": per_param, "geometry": geo}
        # print a compact summary
        sc, al, rp = per_param["scav_rat"], per_param["alpfe"], per_param["R_PICPOC"]
        print(f"   scav_rat Cal+ {sc['calplus_n']}/{S}  median {sc['median']:.3e} "
              f"({sc['median_rel_to_carroll']:.2f}x)  CV {sc['cv']:.2f}")
        print(f"   alpfe    Cal+ {al['calplus_n']}/{S}  median {al['median']:.3g} "
              f"({al['median_rel_to_carroll']:.2f}x)  CV {al['cv']:.2f}")
        print(f"   R_PICPOC Cal+ {rp['calplus_n']}/{S}  median {rp['median']:.3g} "
              f"({rp['median_rel_to_carroll']:.2f}x)")
        print(f"   geometry@opt: |rho(alpfe,scav)|={abs(geo['rho_alpfe_scav']):.3f}  "
              f"CRLB_rel(scav)={geo['crlb_rel_scav']:.3f}  "
              f"sloppiness={geo['sloppiness_decades']:.2f} dec")

    # -------- 3. verdict --------
    b_scav = results["configs"]["baseline"]["per_param"]["scav_rat"]["calplus_n"]
    p_scav = results["configs"]["both_pinned"]["per_param"]["scav_rat"]["calplus_n"]
    f_scav = results["configs"]["both_free"]["per_param"]["scav_rat"]["calplus_n"]
    b_rho = abs(results["configs"]["baseline"]["geometry"]["rho_alpfe_scav"])
    p_rho = abs(results["configs"]["both_pinned"]["geometry"]["rho_alpfe_scav"])
    moved = p_scav >= max(int(0.7 * S), b_scav + int(0.3 * S))
    conditional = f_scav < p_scav
    if moved and conditional:
        verdict = (f"BREAK CONDITIONAL: scav_rat Cal+ {b_scav}/{S} (baseline) -> {p_scav}/{S} (+both pinned), "
                   f"but only {f_scav}/{S} with export FREE -> the partition tax is real and load-bearing. "
                   f"|rho(alpfe,scav)| {b_rho:.2f} -> {p_rho:.2f}.")
    elif moved and not conditional:
        verdict = (f"BREAK ROBUST: scav_rat Cal+ {b_scav}/{S} -> {p_scav}/{S} (+both pinned) and {f_scav}/{S} "
                   f"(+both free) -> both anchors identify scav_rat even without pinning export. "
                   f"|rho| {b_rho:.2f} -> {p_rho:.2f}.")
    else:
        verdict = (f"NO CLEAN BREAK in the real box: scav_rat Cal+ {b_scav}/{S} (baseline) -> {p_scav}/{S} "
                   f"(+both pinned), {f_scav}/{S} (+both free). |rho| {b_rho:.2f} -> {p_rho:.2f}.")
    results["verdict"] = verdict
    print(f"\n{'='*70}\nVERDICT: {verdict}")

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(results, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
