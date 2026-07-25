#!/usr/bin/env python3
r"""percell_crlb_map.py -- per-cell SPATIAL identifiability map for the Carroll-6
parameters (manuscript figure, issue #152: "which parameter is constrained where").

Why this exists
---------------
The 0-D box integrates every grid cell INDEPENDENTLY (no horizontal transport in the
surrogate). A per-cell parameter therefore affects the state -- and hence the loss --
only at its own cell, so the field Fisher information is BLOCK-DIAGONAL: a separate
6x6 per cell, no KFAC / cross-cell coupling needed. This script keeps the per-cell
block instead of summing it into one AOI Fisher (as
``identifiability_sloppiness.py --mode peraoi`` does), and maps the per-parameter
Fisher SELF-INFORMATION spatially.

Method (reuses the peraoi runner-import + per-cell-gradient pattern)
-------------------------------------------------------------------
Import ``run_v3.0_joint_multi_aoi`` with NB23_N_EPOCHS=0 (training loop becomes a
no-op) so the REAL per-AOI bundles (targets / masks / IC / forcing) and the EXACT
``aoi_loss`` are available WITHOUT running recovery. For each AOI:

  * build a per-cell theta FIELD ``tf`` of shape [6, 1, H, W], every cell set to
    Carroll's value, ``requires_grad_(True)``;
  * ``l, state = aoi_loss(b, tf)`` -- ONE box integration;
  * ``gf = torch.autograd.grad(scalar_loss, tf)`` -> per-cell gradient field
    [6, 1, H, W] (retain_graph so several loss terms reuse the one integration);
  * per-cell per-parameter Fisher self-information is ``g_cell[i]**2``, scaled by
    ``|carroll_i|**2`` to make it dimensionless -- a [6, H, W] field.

Crucially we do this NOT only for the full joint loss but for the individual REAL
observational residual terms, so the map reflects real observational coverage:

  * REAL GEOTRACES dissolved-iron residual (surf DFe_1 + sub DFe_2)  -> alpfe, scav_rat
  * REAL Daniels CP:PP calcite (PIC/POC) rain-ratio residual         -> R_PICPOC
  * REAL GEOTRACES biogenic-silica (bSi) residual                    -> diatomgraz

Because each real term multiplies its residual by an observation MASK (cells with no
bottle / no Daniels sample are zeroed) and the box is per-cell independent, the
per-cell gradient -- and hence the information -- is EXACTLY ZERO where there is no
observation. So R_PICPOC information is zero in the Southern Ocean (no Daniels
coverage there), matching the rank-2 identifiability finding; the growth pair
{Smallgrow, Biggrow} is ~0 everywhere (unobservable by construction).

Outputs
-------
  * NPZ under --out-dir with, per AOI and per loss term, the [6, H, W]
    self-information field + ocean mask + lat/lon axes + coverage counts.
  * (optional, if matplotlib is importable) one PNG per observable parameter with a
    panel per AOI, plus a growth-pair panel, on real lat/lon axes.

Usage (on the cluster, env-configured exactly like the runner):
  source ~/emulator_poc/covar_env_common.sh
  ~/dd_venv/bin/python scripts/analysis/percell_crlb_map.py \
      --out-dir /scratch/qi_zim_neu/identif --tag percell_crlb
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
OBSERVABLE = ["alpfe", "scav_rat", "diatomgraz", "R_PICPOC"]
GROWTH_PAIR = ["Smallgrow", "Biggrow"]
# Which real observational term primarily carries information about each observable.
TERM_FOR_PARAM = {
    "alpfe": "iron", "scav_rat": "iron", "diatomgraz": "posi", "R_PICPOC": "daniels",
}


def _import_runner():
    """Import the runner with training disabled, exposing bundles + aoi_loss.

    setdefault (not overwrite) so the sourced covar_env_common.sh config -- weights,
    TORCH_COMPILE_BATCHED, AOIS -- is respected exactly as the runner would see it.
    """
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_percell_")
    runner_path = ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py"
    spec = importlib.util.spec_from_file_location("_dd_runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", default="/scratch/qi_zim_neu/identif",
                    help="directory for the NPZ (+ PNGs)")
    ap.add_argument("--tag", default="percell_crlb", help="filename stem")
    ap.add_argument("--no-plot", action="store_true", help="skip PNG rendering")
    args = ap.parse_args()

    import numpy as np
    import torch
    from darwindiff.carroll6 import CARROLL_VALUES

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss

    # Bundle ICs loaded with N_seeds=1; expand state0 to S on demand exactly as the
    # peraoi mode does, so a per-cell theta [6, 1, H, W] integrates against a matching
    # state0 [15, 1, H, W] (broadcast view = cheap).
    _base_state0 = {b["key"]: b["state0_per_seed"] for b in bundles}

    def set_seeds(S):
        for b in bundles:
            base = _base_state0[b["key"]]
            b["state0_per_seed"] = base[:, :1].expand(base.shape[0], S, base.shape[2], base.shape[3])

    aois = [b["key"] for b in bundles]
    weights = {b["key"]: float(b["weight"]) for b in bundles}
    carroll = CARROLL_VALUES.to(dev).float()                     # [6]
    scale2 = (carroll.abs().clamp(min=1e-30)) ** 2               # |carroll_i|^2, for dimensionless info

    print(f"\n=== per-cell spatial identifiability map (#152) ===")
    print(f"    AOIS   = {aois}")
    print(f"    weights= {weights}")
    print(f"    active real terms: GEOTRACES_W={R.GEOTRACES_W} GEOTRACES_SUB_W={R.GEOTRACES_SUB_W} "
          f"DANIELS_RPICPOC_W={R.DANIELS_RPICPOC_W} POSI_W={R.POSI_W}")

    # ---- exact reconstructions of the runner's REAL residual loss terms --------------
    # Each mirrors the corresponding block in aoi_loss() bit-for-bit, so the per-cell
    # gradient is of the real observational term. Returns a scalar (per-seed loss, S=1).
    def term_iron_surf(b, state):
        if not (R.GEOTRACES_W > 0 and b["n_geo_surf"] > 0):
            return None
        resid = (state[R.I_DFE_1] - b["geo_surf_target_t"][None]) * b["geo_surf_mask_f"][None]
        sc = (b["geo_surf_target_t"][b["geo_surf_mask_t"]] ** 2).mean().clamp(min=1e-30)
        return R.GEOTRACES_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_surf_f"] / sc

    def term_iron_sub(b, state):
        if not (R.GEOTRACES_SUB_W > 0 and b["n_geo_sub"] > 0):
            return None
        resid = (state[R.I_DFE_2] - b["geo_sub_target_t"][None]) * b["geo_sub_mask_f"][None]
        sc = (b["geo_sub_target_t"][b["geo_sub_mask_t"]] ** 2).mean().clamp(min=1e-30)
        return R.GEOTRACES_SUB_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_geo_sub_f"] / sc

    def term_daniels(b, state):
        if not (R.DANIELS_RPICPOC_W > 0 and b["n_daniels"] > 0):
            return None
        daniels_pred = state[R.I_PIC_1] / state[R.I_POC_1].clamp(min=1e-9)
        resid = (daniels_pred - b["daniels_target_t"][None]) * b["daniels_mask_f"][None]
        sc = (b["daniels_target_t"][b["daniels_mask_t"]] ** 2).mean().clamp(min=1e-30)
        return (R.DANIELS_RPICPOC_W * R.DANIELS_AOI_W[b["key"]]
                * (resid ** 2).flatten(1).sum(dim=1) / b["n_daniels_f"] / sc)

    def term_posi(b, state, tf):
        if not (R.POSI_W > 0 and b["n_posi"] > 0):
            return None
        bsi_pred, _ = R.diagnostic_bsi_steady(state[R.I_DIATOM], tf[R.P.diatomgraz])
        resid = (bsi_pred - b["posi_target_t"][None]) * b["posi_mask_f"][None]
        sc = (b["posi_target_t"][b["posi_mask_t"]] ** 2).mean().clamp(min=1e-30)
        return R.POSI_W * (resid ** 2).flatten(1).sum(dim=1) / b["n_posi_f"] / sc

    def selfinfo_from_grad(gf):
        """gf [6, 1, H, W] -> per-cell dimensionless self-information [6, H, W]."""
        g = gf.reshape(6, gf.shape[-2], gf.shape[-1])            # [6, H, W]
        return (g ** 2) * scale2[:, None, None]

    npz = {}
    summary = {"aois": aois, "weights": weights,
               "carroll": {PARAM_NAMES[i]: float(carroll[i]) for i in range(6)},
               "active_terms": {"GEOTRACES_W": float(R.GEOTRACES_W),
                                "GEOTRACES_SUB_W": float(R.GEOTRACES_SUB_W),
                                "DANIELS_RPICPOC_W": float(R.DANIELS_RPICPOC_W),
                                "POSI_W": float(R.POSI_W)},
               "per_aoi": {}}
    fields = {}   # key -> {"lat":..,"lon":..,"mask":..,"terms":{term:[6,H,W]}}

    for b in bundles:
        key = b["key"]
        set_seeds(1)
        Hh, Ww = b["mask_f"].shape
        ocean = (b["mask_f"] > 0).detach().cpu().numpy()

        # real lat/lon axes from the runner's own target cache (cached; no recompute).
        try:
            tgt = R._load_or_build_target_cache(R.AOI_BY_KEY[key])
            lat = np.asarray(tgt["darwin_lats"], dtype=float)
            lon = np.asarray(tgt["darwin_lons"], dtype=float)
            if lat.size != Hh or lon.size != Ww:      # guard against axis mismatch
                raise ValueError("axis length mismatch")
        except Exception as e:                        # fall back to AOI-bounds cell centres
            aoi = b["aoi"]
            lat = aoi.lat_min + (np.arange(Hh) + 0.5) * (aoi.lat_max - aoi.lat_min) / Hh
            lon = aoi.lon_min + (np.arange(Ww) + 0.5) * (aoi.lon_max - aoi.lon_min) / Ww
            print(f"  [{key}] lat/lon axes reconstructed from AOI bounds ({e})")

        # ONE integration; reuse the graph for the full loss and every real term.
        tf = carroll.reshape(6, 1, 1, 1).expand(6, 1, Hh, Ww).clone().requires_grad_(True)
        l_full, state = aoi_loss(b, tf)

        term_losses = {"full": l_full}
        ti_s = term_iron_surf(b, state)
        ti_b = term_iron_sub(b, state)
        term_losses["iron_surf"] = ti_s
        term_losses["iron_sub"] = ti_b
        if ti_s is not None or ti_b is not None:
            term_losses["iron"] = sum(t for t in (ti_s, ti_b) if t is not None)
        term_losses["daniels"] = term_daniels(b, state)
        term_losses["posi"] = term_posi(b, state, tf)

        # reconstruction check: real terms should sum to the full loss in this config.
        recon = sum(float(term_losses[k].sum()) for k in ("iron_surf", "iron_sub", "daniels", "posi")
                    if term_losses.get(k) is not None)
        l_full_v = float(l_full.sum())
        recon_rel = abs(recon - l_full_v) / max(abs(l_full_v), 1e-30)

        # per-cell gradients -> self-information fields.
        term_info = {}
        active = [k for k, v in term_losses.items() if v is not None]
        for i, k in enumerate(active):
            retain = i < len(active) - 1
            (gf,) = torch.autograd.grad(term_losses[k].sum(), tf, retain_graph=retain)
            info = selfinfo_from_grad(gf).detach().cpu().numpy()      # [6, H, W]
            info = np.where(ocean[None], info, 0.0).astype(np.float32)  # mask land
            term_info[k] = info

        fields[key] = {"lat": lat, "lon": lon, "mask": ocean, "terms": term_info}

        # npz payload
        npz[f"{key}__lat"] = lat.astype(np.float32)
        npz[f"{key}__lon"] = lon.astype(np.float32)
        npz[f"{key}__mask"] = ocean
        for k, info in term_info.items():
            npz[f"{key}__{k}__selfinfo"] = info

        # per-AOI aggregate: SUMMED self-info per param per term (= peraoi Fisher diag),
        # + fraction of ocean cells with nonzero info.
        n_ocean = int(ocean.sum())
        coverage = {"n_ocean": n_ocean, "n_geo_surf": int(b["n_geo_surf"]),
                    "n_geo_sub": int(b["n_geo_sub"]), "n_daniels": int(b["n_daniels"]),
                    "n_posi": int(b["n_posi"])}
        agg = {}
        for k, info in term_info.items():
            summ = info.reshape(6, -1).sum(axis=1)                 # [6] sum over cells
            ncells = (info.reshape(6, -1) > 0).sum(axis=1)         # informative cells per param
            agg[k] = {PARAM_NAMES[i]: {"info_sum": float(summ[i]), "n_info_cells": int(ncells[i])}
                      for i in range(6)}
        summary["per_aoi"][key] = {
            "H": Hh, "W": Ww, "weight": float(b["weight"]),
            "aoi_bounds": [float(b["aoi"].lat_min), float(b["aoi"].lat_max),
                           float(b["aoi"].lon_min), float(b["aoi"].lon_max)],
            "coverage": coverage,
            "full_loss": l_full_v, "recon_rel_error": recon_rel,
            "agg_info": agg,
        }

        # console report
        print(f"\n-- AOI {key} ({b['aoi'].name}) grid {Hh}x{Ww}, {n_ocean} ocean cells --")
        print(f"   coverage: GEOTRACES surf={coverage['n_geo_surf']} sub={coverage['n_geo_sub']} "
              f"| Daniels={coverage['n_daniels']} | POSi={coverage['n_posi']}")
        print(f"   full_loss={l_full_v:.4e}   real-term reconstruction rel.err={recon_rel:.2e}")
        # headline: each observable's info from its natural real term
        for p in OBSERVABLE:
            term = TERM_FOR_PARAM[p]
            if term in agg:
                a = agg[term][p]
                print(f"     {p:<10} <- {term:<8} : info_sum={a['info_sum']:.3e}  "
                      f"cells={a['n_info_cells']}")
            else:
                print(f"     {p:<10} <- {term:<8} : TERM ABSENT (no coverage) -> info=0")
        gfull = agg.get("full", {})
        gp = sum(gfull.get(p, {}).get("info_sum", 0.0) for p in GROWTH_PAIR)
        ob = sum(gfull.get(p, {}).get("info_sum", 0.0) for p in OBSERVABLE)
        print(f"   [growth pair] full-loss info_sum(Smallgrow+Biggrow)={gp:.3e}  "
              f"vs observables={ob:.3e}  ratio={gp/max(ob,1e-30):.2e}")

    # ---- write NPZ + JSON summary ----
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    npz_path = out_dir / f"{args.tag}.npz"
    np.savez_compressed(npz_path, **npz)
    json_path = out_dir / f"{args.tag}_summary.json"
    json_path.write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\nwrote {npz_path}")
    print(f"wrote {json_path}")

    # ---- optional PNG maps ----
    png_paths = []
    if not args.no_plot:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from matplotlib.colors import LogNorm
        except Exception as e:
            print(f"[plot] matplotlib unavailable ({e}); NPZ written, skipping PNGs")
            plt = None

        if plt is not None:
            def _panel(ax, key, pi, term):
                f = fields[key]
                info = f["terms"].get(term)
                if info is None:
                    ax.set_facecolor("0.9")
                    ax.text(0.5, 0.5, f"{key}\nno {term} coverage", ha="center",
                            va="center", transform=ax.transAxes, fontsize=8)
                    ax.set_xticks([]); ax.set_yticks([])
                    return None
                field = np.array(info[pi], dtype=float)
                field = np.where(f["mask"], field, np.nan)
                vmax = np.nanmax(field) if np.isfinite(field).any() else 0.0
                pos = field[np.isfinite(field) & (field > 0)]
                if pos.size:
                    vmin = max(pos.min(), vmax * 1e-4)
                    norm = LogNorm(vmin=vmin, vmax=max(vmax, vmin * 10))
                else:
                    norm = None
                pm = ax.pcolormesh(f["lon"], f["lat"], field, norm=norm,
                                   cmap="viridis", shading="auto")
                ax.set_title(f"{key} ({int(np.isfinite(field).sum() and (field>0).sum())} cells)",
                             fontsize=8)
                ax.set_xlabel("lon", fontsize=7); ax.set_ylabel("lat", fontsize=7)
                ax.tick_params(labelsize=6)
                return pm

            # one figure per observable parameter (natural real term), panel per AOI
            for p in OBSERVABLE:
                pi = PARAM_NAMES.index(p)
                term = TERM_FOR_PARAM[p]
                fig, axes = plt.subplots(1, len(bundles), figsize=(4.2 * len(bundles), 3.6))
                if len(bundles) == 1:
                    axes = [axes]
                last_pm = None
                for ax, b in zip(axes, bundles):
                    pm = _panel(ax, b["key"], pi, term)
                    last_pm = pm or last_pm
                if last_pm is not None:
                    fig.colorbar(last_pm, ax=axes, fraction=0.046, pad=0.04,
                                 label="self-information (dimensionless)")
                fig.suptitle(f"{p} per-cell Fisher self-information  (from REAL {term} residual)",
                             fontsize=11)
                pth = out_dir / f"{args.tag}_{p}.png"
                fig.savefig(pth, dpi=130, bbox_inches="tight")
                plt.close(fig)
                png_paths.append(str(pth))
                print(f"wrote {pth}")

            # growth-pair (full loss) -- expected ~0 everywhere
            fig, axes = plt.subplots(len(GROWTH_PAIR), len(bundles),
                                     figsize=(4.2 * len(bundles), 3.4 * len(GROWTH_PAIR)),
                                     squeeze=False)
            last_pm = None
            for r, gp_name in enumerate(GROWTH_PAIR):
                pi = PARAM_NAMES.index(gp_name)
                for c, b in enumerate(bundles):
                    pm = _panel(axes[r][c], b["key"], pi, "full")
                    axes[r][c].set_ylabel(f"{gp_name}\nlat", fontsize=7)
                    last_pm = pm or last_pm
            if last_pm is not None:
                fig.colorbar(last_pm, ax=axes.ravel().tolist(), fraction=0.046, pad=0.04,
                             label="self-information (dimensionless)")
            fig.suptitle("growth pair per-cell self-information (full loss) -- unobservable ~ 0",
                         fontsize=11)
            pth = out_dir / f"{args.tag}_growth_pair.png"
            fig.savefig(pth, dpi=130, bbox_inches="tight")
            plt.close(fig)
            png_paths.append(str(pth))
            print(f"wrote {pth}")

    print("\n=== DONE ===")
    print(f"npz: {npz_path}")
    print(f"summary json: {json_path}")
    for p in png_paths:
        print(f"png: {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
