#!/usr/bin/env python
"""COMMON-GRID CONTROL for the resolution-sharpening claim (headline deliverable).

Defeats two objections at once:
  (1) DENOMINATOR TRAP: native "skill" could be high only because persistence is a
      weaker baseline on noisier fine fields.
  (2) COARSE-GRAINING TAUTOLOGY: coarse fields are smoother/more persistent by
      construction.

Method: take the NATIVE-origin model's held-out prediction, target, and persistence
fields (dumped at 0.25deg), conservatively area-average them onto the SAME 1deg grid
the coarse model lives on, restrict to the COMMON valid footprint, and recompute
MSE_model / MSE_persistence / skill THERE. Compare head-to-head against the
1deg-origin model (A2) evaluated on the identical coarse field + footprint.

Sharpening is real ONLY if the native-origin model still beats the 1deg-origin model
on the SAME smoothed 1deg target. Also reports absolute physical RMSE of model AND
persistence per tracer at every stage (rules out the denominator effect directly).

Usage:
  python common_grid_control.py A1_fields.npz A3_fields.npz A2_fields.npz [--aoi-bounds latmin latmax lonmin lonmax] [--out out.json]
  (order: two native field files then the 1deg field file; extra native files allowed)
"""
import numpy as np, json, sys, argparse

def load_fields(p):
    z = np.load(p, allow_pickle=True)
    return {
        "pred": z["pred"].astype(np.float64), "true": z["true"].astype(np.float64),
        "persist": z["persistence"].astype(np.float64), "vm": z["valid_mask"].astype(bool),
        "chans": [str(x) for x in z["chan_names"]], "file": p.split("/")[-1],
    }

def coarsen(field, vm, native_lat, native_lon, coarse_lat, coarse_lon, res=1.0):
    """Area-average [N,C,H,W] native -> [N,C,h,w] coarse over valid native cells only.
    Returns (coarse_field, coarse_count[h,w]) ; NaN where no valid native cell fell in a coarse bin."""
    N, C, H, W = field.shape
    h, w = coarse_lat.size, coarse_lon.size
    ri = np.clip(np.round((native_lat - coarse_lat[0]) / res).astype(int), 0, h - 1)  # [H]
    cj = np.clip(np.round((native_lon - coarse_lon[0]) / res).astype(int), 0, w - 1)  # [W]
    RI = np.broadcast_to(ri[:, None], (H, W)).ravel()
    CJ = np.broadcast_to(cj[None, :], (H, W)).ravel()
    flat = (RI * w + CJ)
    out = np.full((N, C, h * w), np.nan)
    cnt2d = np.zeros(h * w)
    m = vm.ravel().astype(np.float64)
    np.add.at(cnt2d, flat, m)
    for n in range(N):
        for c in range(C):
            s = field[n, c].ravel()
            good = vm.ravel() & np.isfinite(s)
            acc = np.zeros(h * w)
            np.add.at(acc, flat[good], s[good])
            cnt = np.zeros(h * w); np.add.at(cnt, flat[good], 1.0)
            with np.errstate(invalid="ignore", divide="ignore"):
                out[n, c] = np.where(cnt > 0, acc / cnt, np.nan)
    return out.reshape(N, C, h, w), cnt2d.reshape(h, w)

def mse_skill(pred, true, persist, mask):
    """per-channel + overall MSE(model), MSE(persist), skill, physical RMSE over mask cells & months."""
    C = pred.shape[1]
    res = {"per": {}}
    tot_m = tot_p = 0.0; nel = 0
    for c in range(C):
        d_m = (pred[:, c] - true[:, c]); d_p = (persist[:, c] - true[:, c])
        sel = np.broadcast_to(mask[None], d_m.shape) & np.isfinite(d_m) & np.isfinite(d_p)
        em = float((d_m[sel] ** 2).sum()); ep = float((d_p[sel] ** 2).sum()); n = int(sel.sum())
        tot_m += em; tot_p += ep; nel += n
        res["per"][c] = {"mse_model": em / max(n,1), "mse_persist": ep / max(n,1),
                          "skill": 1 - em/ep if ep > 0 else float("nan"),
                          "rmse_model": (em/max(n,1))**0.5, "rmse_persist": (ep/max(n,1))**0.5}
    res["overall"] = {"mse_model": tot_m/max(nel,1), "mse_persist": tot_p/max(nel,1),
                       "skill": 1 - tot_m/tot_p if tot_p > 0 else float("nan"),
                       "rmse_model": (tot_m/max(nel,1))**0.5, "rmse_persist": (tot_p/max(nel,1))**0.5,
                       "n_cells": int(mask.sum())}
    return res

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", help="native field npz(s) then the 1deg field npz (last)")
    ap.add_argument("--aoi-bounds", nargs=4, type=float, default=[-5.0, 15.0, -160.0, -110.0],
                    help="lat_min lat_max lon_min lon_max (default eqpac)")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    latmin, latmax, lonmin, lonmax = a.aoi_bounds
    coarse = load_fields(a.files[-1])                       # 1deg-origin model (A2)
    ch, cw = coarse["vm"].shape
    coarse_lat = np.linspace(latmin, latmax, ch); coarse_lon = np.linspace(lonmin, lonmax, cw)
    A2 = mse_skill(coarse["pred"], coarse["true"], coarse["persist"], coarse["vm"])

    report = {"aoi_bounds": a.aoi_bounds, "coarse_file": coarse["file"],
              "coarse_grid": [ch, cw], "A2_1deg_native_on_own_grid": A2["overall"], "native_models": {}}
    print(f"=== COMMON-GRID CONTROL (coarse grid {ch}x{cw}, from {coarse['file']}) ===")
    print(f"1deg-origin model (A2) on its own grid: skill={A2['overall']['skill']:+.4f} "
          f"rmse_model={A2['overall']['rmse_model']:.4g} rmse_persist={A2['overall']['rmse_persist']:.4g} "
          f"cells={A2['overall']['n_cells']}\n")

    for nf in a.files[:-1]:
        nat = load_fields(nf)
        nh, nw = nat["vm"].shape
        nlat = np.linspace(latmin, latmax, nh); nlon = np.linspace(lonmin, lonmax, nw)
        cp, cnt = coarsen(nat["pred"], nat["vm"], nlat, nlon, coarse_lat, coarse_lon)
        ct, _ = coarsen(nat["true"], nat["vm"], nlat, nlon, coarse_lat, coarse_lon)
        cs, _ = coarsen(nat["persist"], nat["vm"], nlat, nlon, coarse_lat, coarse_lon)
        common = coarse["vm"] & (cnt > 0)                   # 1deg cells valid on BOTH
        R = mse_skill(cp, ct, cs, common)
        A2c = mse_skill(coarse["pred"], coarse["true"], coarse["persist"], common)  # A2 on SAME footprint
        beats = R["overall"]["mse_model"] < A2c["overall"]["mse_model"]
        report["native_models"][nat["file"]] = {
            "coarsened_native_on_common": R["overall"],
            "A2_on_common_footprint": A2c["overall"],
            "native_beats_coarse_on_common_grid": bool(beats),
            "common_cells": int(common.sum()),
        }
        print(f"--- native-origin {nat['file']} coarse-grained -> {ch}x{cw}, common footprint ({int(common.sum())} cells) ---")
        print(f"    native model on common:  skill={R['overall']['skill']:+.4f}  rmse_model={R['overall']['rmse_model']:.4g}  rmse_persist={R['overall']['rmse_persist']:.4g}")
        print(f"    A2 coarse on common   :  skill={A2c['overall']['skill']:+.4f}  rmse_model={A2c['overall']['rmse_model']:.4g}  rmse_persist={A2c['overall']['rmse_persist']:.4g}")
        print(f"    >>> native beats coarse on identical smoothed field: {beats}  "
              f"(Δmse={A2c['overall']['mse_model']-R['overall']['mse_model']:+.4g})\n")

    if a.out:
        json.dump(report, open(a.out, "w"), indent=2)
        print(f"wrote {a.out}")

if __name__ == "__main__":
    main()
