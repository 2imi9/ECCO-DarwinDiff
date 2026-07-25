#!/usr/bin/env python3
r"""surrogate_jacobian_obsop.py -- log-sensitivity Jacobian of the geo1 surrogate box,
pushed through the inverse problem's OWN observation operator, at two FD step sizes.

WHAT IT COMPUTES
----------------
For each observable Carroll-6 parameter p in {alpfe, scav_rat, diatomgraz, R_PICPOC} and
each surrogate observable T:

    S(p, T) = d ln <T>_obs / d ln p

where <T>_obs is the DEPTH-resolved, AOI-FOOTPRINT, observation-masked mean that the
inverse-problem loss forms its residuals against -- exactly the operator in
`run_v3.0_joint_multi_aoi.aoi_loss` / `identifiability_sloppiness` (surface DFe on the
GEOTRACES surface footprint, subsurface DFe on the sub footprint, surface PIC on the ocean
footprint, and the steady-state biogenic-silica diagnostic / diatom biomass on the POSi
footprint). AOIs are aggregated by observation-cell count (the footprint / uncertainty
weighting the loss uses). Since the flagship targets are a 23-yr TIME MEAN, the "phase"
axis of the operator is degenerate (equilibrated mean) -- stated, not silently dropped.

The derivative is a CENTRAL finite difference in LOG-parameter space at GEOMETRIC steps
s = 1.1 and s = 1.2 (i.e. x/1.1..x*1.1 and x/1.2..x*1.2):

    S = [ ln <T>(p0*s) - ln <T>(p0/s) ] / (2 ln s)

The two step sizes are the mandated finite-difference / nonlinearity convergence check:
if S(1.1) and S(1.2) disagree materially the derivative is in the nonlinear regime. These
are the SAME step sizes as the ECCO-Darwin GCM perturbation recipe
(docs/findings/2026-07-23_v05_perturbation_recipe.md Sec.3), so the surrogate rows and the
GCM rows of the Jacobian are directly comparable.

THE LOAD-BEARING OUTPUT is the cross-parameter RANKING by |sensitivity-to-own-observable|.
Only agreement of that ranking with the GCM licenses transferring the surrogate Fisher
eigenstructure (sloppy/stiff directions, EKI reparameterization) to ECCO-Darwin. The
expected surrogate ranking (docs/findings/2026-07-23_surrogate_jacobian_validation.md Sec.3,
scratch single-step) is diatomgraz >> R_PICPOC > alpfe > scav_rat; this script re-derives it
as a committed, verify-gateable artifact at two step sizes.

RUN (where the geo1 box data lives; the box needs v05 IC/forcing caches + GEOTRACES, so this
runs on the cluster, not a bare checkout):

  PYTHONPATH=src \
  DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5 \
  GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces \
  GEOTRACES_W=1 GEOTRACES_SUB_W=1 RATIO_MAX=2.0 \
  AOIS=eqpac,natlsubpolar,southernoceanpac \
  python scripts/analysis/surrogate_jacobian_obsop.py \
    --out docs/findings/2026-07-25_surrogate_jacobian_obsop.json

The JSON is deterministic (no training, no RNG beyond the fixed IC expansion), so
`scripts/verify_run.py`-style re-derivation reproduces it bit-for-bit.
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

# Carroll-6 canonical order (matches run_v3.0 _CONS_PARAM_ORDER and carroll6.CARROLL_VALUES).
PARAM_ORDER = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
PARAM_IDX = {n: i for i, n in enumerate(PARAM_ORDER)}
# The four observable parameters and each one's NATURAL (own) surrogate observable.
OBS_PARAMS = ["alpfe", "scav_rat", "diatomgraz", "R_PICPOC"]
OWN_OBSERVABLE = {
    "alpfe": "dfe_surf",     # dust source raises surface dissolved iron
    "scav_rat": "dfe_surf",  # scavenging sink lowers surface dissolved iron
    "diatomgraz": "diatom",  # grazing lowers diatom biomass (bSi-routed)
    "R_PICPOC": "pic",        # calcite rain ratio raises surface PIC
}
OBSERVABLES = ["dfe_surf", "dfe_sub", "pic", "diatom"]


def _import_runner():
    """Import run_v3.0 with training disabled, exposing bundles + aoi_loss + tracer indices.
    Mirrors identifiability_sloppiness._import_runner so the observation operator is bit-identical."""
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    os.environ.setdefault("TORCH_COMPILE_BATCHED", "1")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_jac_")
    runner_path = ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py"
    spec = importlib.util.spec_from_file_location("_dd_runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--steps", default="1.1,1.2",
                    help="comma-separated geometric FD step sizes (default 1.1,1.2 = the GCM recipe)")
    ap.add_argument("--nonlin-tol", type=float, default=0.25,
                    help="flag a parameter's own-observable derivative NONLINEAR if the relative "
                         "change of |S| between the two steps exceeds this (default 0.25)")
    ap.add_argument("--out", default=None, help="write JSON table + ranking here")
    args = ap.parse_args()

    import torch
    from darwindiff.carroll6 import CARROLL_VALUES

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss

    # Expand each bundle's IC to batch S (single-column forward here). Same op as
    # identifiability_sloppiness.set_seeds, so the box integrates identically.
    _base_state0 = {b["key"]: b["state0_per_seed"] for b in bundles}

    def set_batch(S):
        for b in bundles:
            base = _base_state0[b["key"]]
            b["state0_per_seed"] = base[:, :1].expand(base.shape[0], S, base.shape[2], base.shape[3])

    carroll = CARROLL_VALUES.to(dev).float()  # [6]
    aois = [b["key"] for b in bundles]
    print(f"=== surrogate Jacobian through the obs operator | AOIS={aois} ===")
    print(f"    GEOTRACES_W={R.GEOTRACES_W} GEOTRACES_SUB_W={R.GEOTRACES_SUB_W} "
          f"RATIO_MAX={getattr(R, 'RATIO_MAX', None)}")

    def masked_mean(field, mask_f):
        """field [S,H,W], mask_f [H,W] -> [S] footprint mean over the observation mask."""
        num = (field * mask_f[None]).flatten(1).sum(dim=1)
        den = mask_f.flatten().sum().clamp(min=1.0)
        return num / den

    def observables(theta6):
        """Return {observable: aggregated scalar} through the inverse problem's obs operator.
        Aggregation across AOIs is by observation-cell count (the footprint/uncertainty weight)."""
        S = 1
        set_batch(S)
        # accumulate weighted sums per observable: (sum_w * value) and sum_w
        acc = {o: [0.0, 0.0] for o in OBSERVABLES}  # observable -> [weighted_sum, weight]
        with torch.no_grad():
            for b in bundles:
                H, W = b["mask_f"].shape
                pb = theta6.reshape(6, 1, 1, 1).expand(6, 1, H, W)
                _, state = aoi_loss(b, pb)  # state [15, 1, H, W]
                ocean = b["mask_f"]
                n_ocean = float(ocean.sum().item())

                # surface DFe on the GEOTRACES surface footprint (fall back to ocean)
                if b.get("n_geo_surf", 0) and R.GEOTRACES_W > 0:
                    m = b["geo_surf_mask_f"]; w = float(b["n_geo_surf"])
                else:
                    m = ocean; w = n_ocean
                acc["dfe_surf"][0] += w * float(masked_mean(state[R.I_DFE_1], m)[0]); acc["dfe_surf"][1] += w

                # subsurface DFe on the sub footprint (fall back to ocean)
                if b.get("n_geo_sub", 0) and R.GEOTRACES_SUB_W > 0:
                    m = b["geo_sub_mask_f"]; w = float(b["n_geo_sub"])
                else:
                    m = ocean; w = n_ocean
                acc["dfe_sub"][0] += w * float(masked_mean(state[R.I_DFE_2], m)[0]); acc["dfe_sub"][1] += w

                # surface PIC on the ocean footprint (the calcite observable's operator)
                acc["pic"][0] += n_ocean * float(masked_mean(state[R.I_PIC_1], ocean)[0]); acc["pic"][1] += n_ocean

                # diatom observable: the steady-state bSi diagnostic on the POSi footprint if
                # present (the actual inverse-problem observable), else raw diatom biomass on ocean.
                if b.get("n_posi", 0):
                    bsi_pred, _ = R.diagnostic_bsi_steady(state[R.I_DIATOM], pb[4])
                    m = b["posi_mask_f"]; w = float(b["n_posi"])
                    val = float(masked_mean(bsi_pred, m)[0])
                else:
                    w = n_ocean
                    val = float(masked_mean(state[R.I_DIATOM], ocean)[0])
                acc["diatom"][0] += w * val; acc["diatom"][1] += w
        return {o: (acc[o][0] / acc[o][1] if acc[o][1] > 0 else float("nan")) for o in OBSERVABLES}

    steps = [float(s) for s in args.steps.split(",")]

    # Jacobian[param][step][observable] = central log-sensitivity
    jac = {p: {f"{s:g}": {} for s in steps} for p in OBS_PARAMS}
    for p in OBS_PARAMS:
        j = PARAM_IDX[p]
        for s in steps:
            th_hi = carroll.clone(); th_hi[j] = carroll[j] * s
            th_lo = carroll.clone(); th_lo[j] = carroll[j] / s
            g_hi = observables(th_hi)
            g_lo = observables(th_lo)
            denom = 2.0 * math.log(s)
            for o in OBSERVABLES:
                a, b_ = g_hi[o], g_lo[o]
                if a > 0 and b_ > 0:
                    jac[p][f"{s:g}"][o] = (math.log(a) - math.log(b_)) / denom
                else:  # signed-linear fallback for a decoupled observable that can hit 0
                    base = observables(carroll)[o] if o not in ("pic",) else max(abs(a), abs(b_), 1e-30)
                    jac[p][f"{s:g}"][o] = (a - b_) / (2.0 * (s - 1.0) * (abs(base) + 1e-30))

    # ---- ranking by |sensitivity-to-own-observable| at the smaller (more local) step ----
    s_small = f"{min(steps):g}"
    s_large = f"{max(steps):g}"
    ranking = []
    for p in OBS_PARAMS:
        own = OWN_OBSERVABLE[p]
        s1 = jac[p][s_small][own]
        s2 = jac[p][s_large][own]
        rel = abs(abs(s1) - abs(s2)) / max(abs(s1), 1e-12)
        ranking.append({
            "param": p, "own_observable": own,
            "S_small_step": s1, "S_large_step": s2,
            "abs_S": abs(s1), "nonlinearity_rel": rel,
            "nonlinear_flag": rel > args.nonlin_tol,
        })
    ranking.sort(key=lambda r: r["abs_S"], reverse=True)
    order = " > ".join(r["param"] for r in ranking)
    expected = "diatomgraz > R_PICPOC > alpfe > scav_rat"

    # ---- report ----
    print("\n-- log-sensitivity Jacobian  S = d ln<tracer>_obs / d ln(param)  (step "
          f"{s_small}) --")
    hdr = f"{'param':>11} | " + " | ".join(f"{o:>9}" for o in OBSERVABLES)
    print(hdr); print("-" * len(hdr))
    for p in OBS_PARAMS:
        row = f"{p:>11} | " + " | ".join(f"{jac[p][s_small][o]:>+9.3f}" for o in OBSERVABLES)
        print(row)

    print(f"\n-- ranking by |sensitivity to own observable| (step {s_small}) --")
    for i, r in enumerate(ranking, 1):
        flag = "  [NONLINEAR: recheck step]" if r["nonlinear_flag"] else ""
        print(f"  {i}. {r['param']:>11} -> {r['own_observable']:<9} |S|={r['abs_S']:.3f} "
              f"(S={r['S_small_step']:+.3f}; step {s_large}: {r['S_large_step']:+.3f}){flag}")
    print(f"\n  surrogate ranking : {order}")
    print(f"  expected (Sec.3)  : {expected}")
    print(f"  RANKING MATCHES EXPECTED: {order == expected}")

    out = {
        "what": "surrogate log-sensitivity Jacobian d ln<tracer>_obs / d ln(param) through the "
                "inverse-problem observation operator, central FD at geometric steps",
        "aois": aois, "steps": steps,
        "GEOTRACES_W": float(R.GEOTRACES_W), "GEOTRACES_SUB_W": float(R.GEOTRACES_SUB_W),
        "carroll": {n: float(carroll[PARAM_IDX[n]]) for n in OBS_PARAMS},
        "jacobian": jac,
        "own_observable": OWN_OBSERVABLE,
        "ranking": ranking,
        "ranking_order": order,
        "expected_order": expected,
        "ranking_matches_expected": order == expected,
        "note_phase": "flagship targets are a 23-yr time mean; the operator's phase axis is "
                      "degenerate (equilibrated mean).",
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
