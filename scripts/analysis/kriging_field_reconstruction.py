"""Classical spatial-prior diagnostic for iron-field reconstruction (#163) — the
go/no-go the Fun-DDPS / Neural-BGC assessment prescribed BEFORE any diffusion build.

The question (regime-bounded, empirical): can a spatial prior beat the v05 box model at
predicting held-out GEOTRACES dissolved-iron cells? If a *classical* kriging LOO-CV cannot
beat the model, a fancier non-Gaussian patch-diffusion prior cannot manufacture correlation
that is not there — close the route by evidence. If it can, the discovery is already in hand
with no diffusion needed.

Two decisive quantities, on data already local (D:\\ecco_darwin_v5 caches + D:\\geotraces):
  1. **Correlation length L vs inter-cell spacing D.** L = the spatial autocorrelation length
     of the DENSE v05 DFe (FeT) field (empirical semivariogram, within-AOI pairs so basins
     don't cross-contaminate). D = the nearest-neighbour great-circle spacing of the sparse
     GEOTRACES surface-DFe cells. A spatial prior can only carry information across cells when
     L is comparable to (or larger than) D. If L << D, the route is dead.
  2. **Ordinary-kriging LOO-CV held-out R^2 vs the box baseline.** Baseline = the v05 model's
     own DFe at the cell (log space, anomaly-R^2 against the train mean, matching #163). Two
     kriging variants: (i) krige the OBS field directly (does spatial interpolation beat the
     model?); (ii) krige the obs-minus-model RESIDUAL and add it back (is the model's spatial
     bias learnable from the sparse residuals?).

Decision rule (from the assessment):
  (a) kriging LOO-CV flips R^2 positive AND beats the box -> discovery in hand, no diffusion.
  (b) kriging cannot beat the box AND L << D -> spatial-prior route dead; close by evidence.
  (c) kriging near-zero AND L ~ D -> a bounded within-realization patch-diffusion prototype
      (SinDDM / self-supervised patch, arXiv 2406.13252) earns a look + Anandkumar-lab pitch.

Reuses the vetted loaders (darwindiff.geotraces_loader.dfe_aoi_1deg_grid for the obs,
held_out_obs.CACHE_FILENAMES for the model fet_binned field) so cells/grid/units match every
other recovery number. Ordinary kriging is hand-rolled (scipy only; sklearn absent in-env).

Run:  PYTHONPATH=src python scripts/analysis/kriging_field_reconstruction.py --out <json>
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np

os.environ.setdefault("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")

EARTH_R_KM = 6371.0
AOI_KEYS = ["eqpac", "natlsubpolar", "southernoceanpac"]


def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance (km) between broadcastable lat/lon arrays (degrees)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dl = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_R_KM * np.arcsin(np.sqrt(np.clip(a, 0, 1)))


def pairwise_km(lats, lons):
    """[N,N] great-circle distance matrix."""
    return haversine_km(lats[:, None], lons[:, None], lats[None, :], lons[None, :])


def empirical_semivariogram(dists, vals, n_bins=15, max_km=None):
    """Empirical semivariogram gamma(h) = 0.5*mean((z_i - z_j)^2) over distance bins.

    dists: [M,M] distance matrix (km). vals: [M] values. Uses the upper triangle.
    Returns (bin_centers, gamma, counts).
    """
    iu = np.triu_indices(len(vals), k=1)
    h = dists[iu]
    g = 0.5 * (vals[iu[0]] - vals[iu[1]]) ** 2
    if max_km is None:
        max_km = np.percentile(h, 90) if len(h) else 1.0
    edges = np.linspace(0, max_km, n_bins + 1)
    centers, gam, cnt = [], [], []
    for b in range(n_bins):
        m = (h >= edges[b]) & (h < edges[b + 1])
        if m.sum() >= 3:
            centers.append(0.5 * (edges[b] + edges[b + 1]))
            gam.append(float(g[m].mean()))
            cnt.append(int(m.sum()))
    return np.array(centers), np.array(gam), np.array(cnt)


def fit_exponential_variogram(centers, gam):
    """Fit gamma(h) = nugget + (sill-nugget)*(1 - exp(-h/L)) by grid search over L.

    Returns dict(nugget, sill, range_L_km, r2). Robust to few points (no curve_fit).
    L is the correlation length (e-folding). Returns L=nan if unfittable.
    """
    if len(centers) < 3:
        return {"nugget": float("nan"), "sill": float("nan"),
                "range_L_km": float("nan"), "r2": float("nan")}
    sill0 = float(gam.max())
    best = None
    for L in np.geomspace(20.0, 8000.0, 120):
        basis = 1.0 - np.exp(-centers / L)
        # linear LS for [nugget, (sill-nugget)] given this L, with A=[1, basis]
        A = np.column_stack([np.ones_like(centers), basis])
        coef, *_ = np.linalg.lstsq(A, gam, rcond=None)
        nugget, amp = coef
        if amp < 0:  # non-physical (variogram must rise)
            continue
        pred = A @ coef
        ss_res = float(((gam - pred) ** 2).sum())
        ss_tot = float(((gam - gam.mean()) ** 2).sum()) or 1e-30
        r2 = 1 - ss_res / ss_tot
        if best is None or r2 > best["r2"]:
            best = {"nugget": float(nugget), "sill": float(nugget + amp),
                    "range_L_km": float(L), "r2": float(r2)}
    if best is None:
        return {"nugget": float("nan"), "sill": sill0,
                "range_L_km": float("nan"), "r2": float("nan")}
    return best


def variogram_model(h, nugget, sill, L):
    """Exponential variogram value(s) at distance h."""
    g = nugget + (sill - nugget) * (1.0 - np.exp(-h / L))
    return np.where(h <= 0, 0.0, g)


def ordinary_kriging_loo(lats, lons, vals, vgm):
    """Leave-one-out ordinary kriging predictions for `vals` at (lats,lons).

    vgm = (nugget, sill, L). Returns pred[N] (kriged value at each held-out cell).
    Ordinary kriging: solve [[G, 1],[1^T, 0]] [w; mu] = [g0; 1], pred = w^T z.
    Falls back to the train mean if the system is singular.
    """
    n = len(vals)
    D = pairwise_km(lats, lons)
    pred = np.full(n, np.nan)
    nugget, sill, L = vgm
    for k in range(n):
        idx = np.array([i for i in range(n) if i != k])
        if len(idx) < 2:
            pred[k] = float(vals[idx].mean()) if len(idx) else np.nan
            continue
        Dt = D[np.ix_(idx, idx)]
        G = variogram_model(Dt, nugget, sill, L)
        np.fill_diagonal(G, 0.0)
        m = len(idx)
        A = np.ones((m + 1, m + 1))
        A[:m, :m] = G
        A[m, m] = 0.0
        g0 = variogram_model(D[k, idx], nugget, sill, L)
        b = np.append(g0, 1.0)
        try:
            sol = np.linalg.solve(A + np.eye(m + 1) * 1e-8, b)
            w = sol[:m]
            pred[k] = float(w @ vals[idx])
        except np.linalg.LinAlgError:
            pred[k] = float(vals[idx].mean())
    return pred


def anomaly_r2(pred, target, train_mean):
    """1 - SS_res/SS_tot where SS_tot uses the constant train mean (matches #163 metric)."""
    ss_res = float(((pred - target) ** 2).sum())
    ss_tot = float(((target - train_mean) ** 2).sum()) or 1e-30
    return 1.0 - ss_res / ss_tot


def level_r2(pred, target):
    ss_res = float(((pred - target) ** 2).sum())
    ss_tot = float(((target - target.mean()) ** 2).sum()) or 1e-30
    return 1.0 - ss_res / ss_tot


def collect_cells(geotraces_path, depth_max=50.0):
    """Per-AOI + pooled (lat, lon, log-obs, log-model) at cells with finite obs AND model."""
    from darwindiff.ecco_darwin_loader import AOI_BY_KEY
    from darwindiff.geotraces_loader import dfe_aoi_1deg_grid
    from darwindiff.held_out_obs import CACHE_FILENAMES, _DEFAULT_CACHE_DIR
    import torch

    per_aoi = {}
    dense_model = []  # (lat, lon, log model) over ALL finite model cells (for L_model)
    for key in AOI_KEYS:
        aoi = AOI_BY_KEY[key]
        cache_p = Path(_DEFAULT_CACHE_DIR) / CACHE_FILENAMES[aoi.name]
        c = torch.load(cache_p, weights_only=False)
        model = np.asarray(c["fet_binned"], dtype=np.float64)      # [Y,X] mmol/m^3
        lats1d = np.asarray(c["darwin_lats"], dtype=np.float64)
        lons1d = np.asarray(c["darwin_lons"], dtype=np.float64)
        obs = np.asarray(dfe_aoi_1deg_grid(geotraces_path, aoi, depth_max=depth_max),
                         dtype=np.float64)                          # [Y,X] mmol/m^3
        if obs.shape != model.shape:
            raise ValueError(f"{key}: obs {obs.shape} != model {model.shape}")
        LAT, LON = np.meshgrid(lats1d, lons1d, indexing="ij")
        # dense model field cells (for correlation length of the model field)
        dm = np.isfinite(model) & (model > 0)
        for la, lo, mv in zip(LAT[dm], LON[dm], model[dm]):
            dense_model.append((la, lo, np.log(mv)))
        # obs cells with model present
        both = np.isfinite(obs) & (obs > 0) & np.isfinite(model) & (model > 0)
        cells = []
        for la, lo, ov, mv in zip(LAT[both], LON[both], obs[both], model[both]):
            cells.append((float(la), float(lo), float(np.log(ov)), float(np.log(mv))))
        per_aoi[key] = {"aoi_name": aoi.name, "n_cells": len(cells), "cells": cells,
                        "grid": model.shape}
    return per_aoi, dense_model


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--geotraces", default=r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")
    ap.add_argument("--depth-max", type=float, default=50.0)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    per_aoi, dense_model = collect_cells(args.geotraces, depth_max=args.depth_max)

    # ---- pooled obs cells ----
    pooled = [c for k in AOI_KEYS for c in per_aoi[k]["cells"]]
    lat = np.array([c[0] for c in pooled])
    lon = np.array([c[1] for c in pooled])
    y_obs = np.array([c[2] for c in pooled])   # log obs DFe
    y_mod = np.array([c[3] for c in pooled])   # log model DFe
    N = len(pooled)
    print(f"[kriging] pooled obs cells with model coverage: N={N}", flush=True)
    for k in AOI_KEYS:
        print(f"    {k:18s} n_cells={per_aoi[k]['n_cells']:3d}  grid={per_aoi[k]['grid']}", flush=True)

    result = {"n_cells_pooled": N,
              "per_aoi_counts": {k: per_aoi[k]["n_cells"] for k in AOI_KEYS}}
    if N < 4:
        print("[kriging] too few pooled cells for LOO kriging; reporting counts only.", flush=True)
        if args.out:
            Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        return 0

    # ---- (1a) inter-cell spacing D (nearest-neighbour great-circle km) ----
    D = pairwise_km(lat, lon)
    Dnn = np.array([np.min(D[i, np.arange(N) != i]) for i in range(N)])
    result["intercell_spacing_km"] = {
        "nn_median": float(np.median(Dnn)), "nn_min": float(Dnn.min()),
        "nn_max": float(Dnn.max()), "nn_mean": float(Dnn.mean())}
    print(f"[kriging] nearest-neighbour spacing D (km): median={np.median(Dnn):.0f} "
          f"min={Dnn.min():.0f} max={Dnn.max():.0f}", flush=True)

    # ---- (1b) correlation length L of the DENSE v05 model field (within-AOI pairs) ----
    # Build the model-field semivariogram per AOI (so we never pair across basins), pool bins.
    all_centers, all_gam = [], []
    for k in AOI_KEYS:
        cells = per_aoi[k]["cells"]
        # use the dense model cells belonging to this AOI's grid extent
        dm = [t for t in dense_model
              if per_aoi[k]["grid"] and _in_aoi(t[0], t[1], per_aoi[k]["aoi_name"])]
        if len(dm) < 20:
            continue
        la = np.array([t[0] for t in dm]); lo = np.array([t[1] for t in dm])
        vv = np.array([t[2] for t in dm])
        # subsample for tractability
        if len(vv) > 500:
            rng = np.random.default_rng(0)
            sel = rng.choice(len(vv), 500, replace=False)
            la, lo, vv = la[sel], lo[sel], vv[sel]
        Dk = pairwise_km(la, lo)
        c_, g_, _ = empirical_semivariogram(Dk, vv, n_bins=15)
        all_centers.append(c_); all_gam.append(g_)
    if all_centers:
        cc = np.concatenate(all_centers); gg = np.concatenate(all_gam)
        order = np.argsort(cc)
        vfit_model = fit_exponential_variogram(cc[order], gg[order])
    else:
        vfit_model = {"range_L_km": float("nan"), "r2": float("nan"),
                      "nugget": float("nan"), "sill": float("nan")}
    result["model_field_variogram"] = vfit_model
    L_model = vfit_model["range_L_km"]
    print(f"[kriging] v05 model-field correlation length L_model = {L_model:.0f} km "
          f"(fit r2={vfit_model['r2']:.2f})", flush=True)

    # ---- box baseline: model predicts obs at the cells ----
    train_mean = float(y_obs.mean())
    box_anom = anomaly_r2(y_mod, y_obs, train_mean)
    box_level = level_r2(y_mod, y_obs)
    result["box_baseline"] = {"anomaly_r2": box_anom, "level_r2": box_level,
                              "resid_mean_log": float((y_obs - y_mod).mean()),
                              "resid_std_log": float((y_obs - y_mod).std())}
    print(f"[kriging] BOX baseline (model->obs): anomaly_r2={box_anom:.3f} "
          f"level_r2={box_level:.3f}", flush=True)

    # ---- residual variogram (is obs-model spatially structured?) ----
    resid = y_obs - y_mod
    c_r, g_r, _ = empirical_semivariogram(D, resid, n_bins=12)
    vfit_resid = fit_exponential_variogram(c_r, g_r)
    result["residual_variogram"] = vfit_resid
    # nugget/sill ratio: ~1 => pure nugget (unstructured, unlearnable); <<1 => structured
    nug, sill = vfit_resid["nugget"], vfit_resid["sill"]
    nug_ratio = float(nug / sill) if (sill and np.isfinite(sill) and sill > 0) else float("nan")
    result["residual_nugget_ratio"] = nug_ratio
    print(f"[kriging] residual variogram: L={vfit_resid['range_L_km']:.0f} km, "
          f"nugget/sill={nug_ratio:.2f} (1.0 = unstructured/unlearnable)", flush=True)

    # ---- (2) ordinary-kriging LOO-CV ----
    # variant (i): krige the OBS field. Use the obs-field variogram; fall back to L_model.
    c_o, g_o, _ = empirical_semivariogram(D, y_obs, n_bins=12)
    vfit_obs = fit_exponential_variogram(c_o, g_o)
    L_obs = vfit_obs["range_L_km"] if np.isfinite(vfit_obs["range_L_km"]) else L_model
    vgm_obs = (vfit_obs.get("nugget", 0.0) or 0.0,
               vfit_obs.get("sill", float(np.var(y_obs))) or float(np.var(y_obs)),
               L_obs if np.isfinite(L_obs) else 1000.0)
    pred_obs = ordinary_kriging_loo(lat, lon, y_obs, vgm_obs)
    krige_obs_anom = anomaly_r2(pred_obs, y_obs, train_mean)
    krige_obs_level = level_r2(pred_obs, y_obs)
    result["kriging_obs_field"] = {"variogram": vfit_obs, "L_used_km": vgm_obs[2],
                                   "anomaly_r2": krige_obs_anom, "level_r2": krige_obs_level}
    print(f"[kriging] KRIGE obs-field LOO: anomaly_r2={krige_obs_anom:.3f} "
          f"level_r2={krige_obs_level:.3f}  (L={vgm_obs[2]:.0f} km)", flush=True)

    # variant (ii): krige the RESIDUAL, add back to model.
    vgm_res = (nug if np.isfinite(nug) else 0.0,
               sill if (np.isfinite(sill) and sill > 0) else float(np.var(resid)),
               vfit_resid["range_L_km"] if np.isfinite(vfit_resid["range_L_km"]) else 1000.0)
    pred_res = ordinary_kriging_loo(lat, lon, resid, vgm_res)
    pred_obs2 = y_mod + pred_res
    krige_res_anom = anomaly_r2(pred_obs2, y_obs, train_mean)
    krige_res_level = level_r2(pred_obs2, y_obs)
    result["kriging_residual"] = {"variogram": vfit_resid, "anomaly_r2": krige_res_anom,
                                  "level_r2": krige_res_level}
    print(f"[kriging] KRIGE residual+model LOO: anomaly_r2={krige_res_anom:.3f} "
          f"level_r2={krige_res_level:.3f}", flush=True)

    # ---- decision rule ----
    best_krige = max(krige_obs_anom, krige_res_anom)
    L_vs_D = (L_model / np.median(Dnn)) if (np.isfinite(L_model) and np.median(Dnn) > 0) else float("nan")
    if best_krige > 0 and best_krige > box_anom + 0.05:
        regime = "(a) DISCOVERY: kriging beats the box at held-out cells — spatial prior carries real info"
    elif (not np.isfinite(L_vs_D)) or (L_vs_D < 0.5):
        regime = "(b) DEAD: L << D and kriging cannot beat the box — close the spatial-prior route by evidence"
    elif abs(best_krige) < 0.1 and 0.5 <= L_vs_D:
        regime = "(c) MARGINAL: near-zero with L ~ D — a bounded patch-diffusion prototype could earn a look"
    else:
        regime = "(b/mixed): kriging does not beat the box; route is not supported by evidence"
    result["L_over_D"] = float(L_vs_D)
    result["verdict"] = regime
    print(f"\n=== VERDICT ===\n  L_model/D_median = {L_vs_D:.2f}")
    print(f"  box anomaly_r2={box_anom:.3f}  best kriging anomaly_r2={best_krige:.3f}")
    print(f"  {regime}", flush=True)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
        print(f"  wrote {args.out}")
    return 0


_AOI_BOUNDS_CACHE = {}


def _in_aoi(lat, lon, aoi_name):
    """Membership test using the AOI registry bounds (cached)."""
    if aoi_name not in _AOI_BOUNDS_CACHE:
        from darwindiff.ecco_darwin_loader import AOI_BY_KEY
        a = next(x for x in AOI_BY_KEY.values() if x.name == aoi_name)
        _AOI_BOUNDS_CACHE[aoi_name] = (a.lat_min, a.lat_max, a.lon_min, a.lon_max)
    la0, la1, lo0, lo1 = _AOI_BOUNDS_CACHE[aoi_name]
    return (la0 <= lat <= la1) and (lo0 <= lon <= lo1)


if __name__ == "__main__":
    raise SystemExit(main())
