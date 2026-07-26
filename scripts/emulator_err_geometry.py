"""Does the emulator's one-step error concentrate at GEOMETRY features?

THE TEST (2026-07-21). The Track-2 rollout ceiling was ruled "irreducible state-dependent
approximation error" for THIS architecture (commit 558fcbb) after eliminating capacity, data
volume, variance-collapse, chaos, and constant-bias. Geometry was NEVER a tested candidate.
FNO2d runs a plain 2-D FFT (torch.fft.rfft2) on LLC270 AOI crops with land masking -- and a
flat/Euclidean FFT on a non-flat, land-masked domain produces artifacts that compound into a
SYSTEMATIC, STATE-DEPENDENT bias (Spherical-FNO diagnosis, Bonev et al. 2023). If our
"irreducible" err(1) concentrates in the coastal band (near the land mask) and/or grows with
|latitude|, it is a geometry artifact -- fixable with a geometry-aware operator (GINO) -- and
the "ceiling closed" conclusion is premature. If err(1) is spatially flat, the ceiling stands.

Uses the same forward map as rollout_verify.py (x + f(x)*dt, log-space, masked).

Run: uv run python scripts/emulator_err_geometry.py --cube global3d_L10_cube.npz \
       --model 'opt3d_seed*.pt' --log-transform --out err_geometry.json
"""
from __future__ import annotations
import argparse, glob, json, sys
from pathlib import Path
import numpy as np, torch

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path: sys.path.insert(0, str(_HERE))
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path: sys.path.insert(0, str(_SRC))
from darwindiff.safe_load import safe_torch_load  # noqa: E402
from diffusion_emulator import FNO2d, load_cube, time_split, zscore  # noqa: E402


def coastal_distance(mask):
    """For each ocean cell, distance (in cells) to the nearest land/edge. Small = coastal."""
    from scipy import ndimage
    # pad with land so domain edges also count as boundary (the FFT wraps them)
    m = np.pad(mask.astype(bool), 1, constant_values=False)
    d = ndimage.distance_transform_edt(m)[1:-1, 1:-1]
    return d  # 0 on land; >0 on ocean, = distance to nearest land/edge


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--cube", required=True)
    p.add_argument("--model", nargs="*", default=[], help="checkpoint glob(s); if empty, train fresh")
    p.add_argument("--train-epochs", type=int, default=0, help=">0 trains a fresh FNO2d (no checkpoint needed)")
    p.add_argument("--modes", type=int, default=16)
    p.add_argument("--width", type=int, default=32)
    p.add_argument("--rollout-k", type=int, default=8)
    p.add_argument("--log-transform", action="store_true")
    p.add_argument("--log-floor", type=float, default=1e-12)
    p.add_argument("--dt-scaled-residual", action="store_true")
    p.add_argument("--n-starts", type=int, default=40)
    p.add_argument("--out", default=None)
    a = p.parse_args(argv)
    dev = "cuda" if torch.cuda.is_available() else "cpu"

    state, mask, names = load_cube(a.cube)
    if a.log_transform:
        state = np.log(np.clip(state, a.log_floor, None)).astype(np.float32)
    T, C, H, W = state.shape
    z, mean, std = zscore(state, mask); del state
    Z = torch.from_numpy(z)
    _, va_t = time_split(T)
    zr = np.load(a.cube, allow_pickle=True)
    lat = np.abs(zr["YC"]) if "YC" in zr.files else (np.abs(zr["lat"]) if "lat" in zr.files else None)

    mask_t = torch.from_numpy(mask.astype(np.float32))[None, None].to(dev)
    tr_t, _ = time_split(T)
    models = []
    ckpts = sorted({q for m in a.model for q in glob.glob(m)})
    if ckpts:
        for pth in ckpts:
            ck = safe_torch_load(pth, map_location=dev); cfg = ck["config"]
            m = FNO2d(C, C, modes1=cfg["modes"], modes2=cfg["modes"], width=cfg["reg_width"]).to(dev)
            m.load_state_dict(ck["regression"]); m.eval(); models.append(m)
        print(f"[geom] loaded {len(models)} checkpoint(s)", flush=True)
    else:
        from diffusion_emulator import train_regression
        print(f"[geom] no checkpoint -> training fresh FNO2d ({a.train_epochs} ep, k{a.rollout_k})", flush=True)
        fno, _ = train_regression(Z, tr_t, C, mask_t, dev, a.train_epochs, a.modes, a.width,
                                  bs=8, va_t=va_t, rollout_k=a.rollout_k, dt_months=None)
        fno.eval(); models.append(fno)
    print(f"[geom] {len(models)} member(s) | cube {(T,C,H,W)} | lat={'yes' if lat is not None else 'no'}", flush=True)

    starts = [t for t in va_t if t + 1 < T][: a.n_starts]
    err_field = np.zeros((H, W), dtype=np.float64)   # mean over starts of per-cell RMS-over-channel err
    n = 0
    with torch.no_grad():
        for s in starts:
            x = Z[s:s+1].to(dev)
            step = torch.stack([x + mm(x) for mm in models]).mean(0) if len(models) > 1 else x + models[0](x)
            y = Z[s+1:s+2].to(dev)
            e = (((step - y) ** 2).mean(dim=1))[0]        # [H,W] mean over channels (z-score sq err)
            err_field += (e.cpu().numpy() * mask); n += 1
    err_field /= max(n, 1)

    dist = coastal_distance(mask)
    ocean = mask.astype(bool)
    ev = err_field[ocean]; dv = dist[ocean]
    # coastal-distance bins
    bins = [(1, 2), (2, 5), (5, 10), (10, 1e9)]
    band = {}
    for lo, hi in bins:
        sel = (dv >= lo) & (dv < hi)
        band[f"{lo}-{hi if hi < 1e9 else 'inf'}"] = {
            "n_cells": int(sel.sum()), "mean_err": float(ev[sel].mean()) if sel.any() else None}
    coastal = ev[(dv >= 1) & (dv < 3)]; interior = ev[dv >= 10]
    ratio = float(coastal.mean() / interior.mean()) if interior.size and coastal.size else None
    # correlation of err with coastal proximity (1/dist)
    prox = 1.0 / np.clip(dv, 1, None)
    corr = float(np.corrcoef(ev, prox)[0, 1])

    out = {"n_starts": n, "channels": names, "log_transform": a.log_transform,
           "coastal_distance_bands": band,
           "coastal_over_interior_err_ratio": ratio,
           "corr_err_vs_coastal_proximity": corr}
    if lat is not None:
        lv = lat[ocean] if lat.shape == mask.shape else None
        if lv is not None:
            hi = ev[lv > 60]; lo = ev[lv < 30]
            out["highlat_over_lowlat_err_ratio"] = float(hi.mean()/lo.mean()) if hi.size and lo.size else None
            out["corr_err_vs_abslat"] = float(np.corrcoef(ev, lv)[0, 1])

    print("\n=== err(1) vs geometry ===")
    for k, v in band.items(): print(f"  coastal-dist {k:>7} cells: mean_err={v['mean_err']}  (n={v['n_cells']})")
    print(f"  coastal(<3)/interior(>10) err ratio = {ratio}")
    print(f"  corr(err, coastal-proximity)        = {corr:+.3f}")
    if "corr_err_vs_abslat" in out:
        print(f"  highlat(>60)/lowlat(<30) err ratio  = {out.get('highlat_over_lowlat_err_ratio')}")
        print(f"  corr(err, |lat|)                    = {out['corr_err_vs_abslat']:+.3f}")
    verdict = ("GEOMETRY-ARTIFACT-LIKELY (err concentrates coastally -> ceiling reopens; test GINO)"
               if (ratio and ratio > 1.5) or corr > 0.2 else
               "SPATIALLY-FLAT (err not geometry-concentrated -> the irreducible-ceiling reading stands)")
    out["verdict"] = verdict
    print(f"\n  VERDICT: {verdict}")
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(json.dumps(out, indent=1), encoding="utf-8"); print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
