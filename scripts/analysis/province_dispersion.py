"""Does within-AOI parameter dispersion follow Longhurst province boundaries?

Consumes the per-cell fields written by ``SAVE_PER_CELL_SEEDS`` and asks, directly,
how much of a parameter's per-cell log-variance inside an AOI is explained by which
biogeochemical province the cell sits in.

THE QUESTION THIS SETTLES
-------------------------
``natlsubpolar`` carries ``per_aoi_log_sd`` = 0.936, above the sigma = 0.820 at which
the arithmetic collapse ALONE clears the +/-40% band, and that one leg is the whole of
the flagship trio's 25/50 -> 12/50 halving. The 2026-08-17 overlay showed the box is a
3.10-effective-province mixture spanning three of Longhurst's four biomes, which makes
"the spread is regime heterogeneity being averaged over" the obvious hypothesis.

Until the per-cell field was persisted (commit 01f053e) that hypothesis was untestable:
the runner wrote only collapses and has no ``state_dict()`` save, so sigma was a
magnitude with no spatial structure attached.

WHAT IS REPORTED
----------------
``eta_sq`` -- the fraction of per-cell log-variance explained by province membership,
i.e. a one-way ANOVA on log(parameter) with province as the factor. It is the direct
answer: eta_sq near 1 means the dispersion IS the province structure; near 0 means the
spread lives *within* provinces and redrawing AOI boundaries along them will not
collapse it.

``eta_sq`` is reported against TWO references, and the second is the one that matters.

1. A **shuffled-label null**, because ``eta_sq`` is biased upward by construction: with
   k groups it is positive even for a spatially random field.
2. A **latitude-band control** -- the same group sizes, boundaries drawn by latitude
   alone. Longhurst provinces are largely latitudinal bands, so beating the shuffle
   only shows the field has a north-south gradient, which a per-cell net reading an SST
   channel produces trivially. Only ``eta_sq`` clearly ABOVE the latitude-band control
   is evidence that province boundaries carry information latitude alone does not, and
   therefore that redrawing AOIs along them would collapse the dispersion.

On a deliberately under-trained 3-epoch smoke field the two came out at 0.733 and 0.750
respectively -- i.e. provinces explained slightly LESS than arbitrary latitude bands.
That is the confound behaving exactly as expected, and it is why the control exists.

Usage::

    python scripts/analysis/province_dispersion.py RUN_DIR [--param scav_rat] [--json OUT]
    python scripts/analysis/province_dispersion.py RUN_DIR --aoi natlsubpolar --n-perm 500
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from province_overlay import _gdf, fetch


def province_labels(lats: np.ndarray, lons: np.ndarray, features: list[dict]) -> np.ndarray:
    """First-covering province per cell. ``covers`` so a cell on an edge lands somewhere."""
    from shapely.geometry import Point
    from shapely.prepared import prep

    prepared = [(f["provcode"], prep(f.geometry)) for _, f in _gdf(features).iterrows()]
    out = np.empty(lats.size, dtype=object)
    for i, (la, lo) in enumerate(zip(lats, lons, strict=False)):
        pt = Point(float(lo), float(la))
        out[i] = next((c for c, p in prepared if p.covers(pt)), "<none>")
    return out


def eta_squared(y: np.ndarray, groups: np.ndarray) -> float:
    """Fraction of variance in ``y`` explained by group membership (one-way ANOVA)."""
    grand = y.mean()
    ss_total = float(((y - grand) ** 2).sum())
    if ss_total <= 0:
        return 0.0
    ss_between = 0.0
    for g in np.unique(groups):
        sel = groups == g
        ss_between += sel.sum() * (y[sel].mean() - grand) ** 2
    return float(ss_between / ss_total)


def analyse(path: str, param: str, n_perm: int, rng: np.random.Generator) -> dict | None:
    d = np.load(path, allow_pickle=False)
    names = [str(x) for x in d["param_names"]]
    if param not in names:
        return None
    i = names.index(param)

    n_lon = int(d["W"])          # grid width, as saved by the runner
    idx = d["ocean_index"]
    lats = d["lats"][idx // n_lon]
    lons = d["lons"][idx % n_lon]
    y = np.log(d["values"][i].astype(np.float64))

    aoi = str(d["aoi"])
    b = d["aoi_bounds"]
    feats = fetch((float(b[2]), float(b[0]), float(b[3]), float(b[1])), aoi)
    labels = province_labels(lats, lons, feats)

    obs = eta_squared(y, labels)
    null = np.array([eta_squared(y, rng.permutation(labels)) for _ in range(n_perm)])
    # One-sided permutation P, with the +1 correction so P is never exactly 0.
    p = float((int((null >= obs).sum()) + 1) / (n_perm + 1))

    # THE CONTROL THAT MAKES eta_sq INTERPRETABLE.
    #
    # Longhurst provinces are largely latitudinal bands, so eta_sq against a
    # shuffled null will look large for ANY smooth north-south gradient -- and a
    # per-cell net reading an SST channel produces exactly that. Beating the shuffle
    # therefore shows the field is spatially structured, which was never in doubt;
    # it does NOT show the structure is province structure.
    #
    # The honest comparison is against ARBITRARY latitude bands carrying the same
    # group sizes. If province boundaries explain no more than boundaries drawn at
    # matched sizes in the same direction, the signal is a gradient, not a regime
    # boundary, and redrawing AOIs along provinces buys nothing.
    order = np.argsort(lats, kind="stable")
    sizes = [int((labels == g).sum()) for g in np.unique(labels)]
    band = np.empty(y.size, dtype=object)
    at = 0
    for k, n in enumerate(sorted(sizes, reverse=True)):
        band[order[at:at + n]] = f"band{k}"
        at += n
    if at < y.size:                      # rounding slack -> last band
        band[order[at:]] = f"band{len(sizes) - 1}"
    lat_band = eta_squared(y, band)

    per_prov = {}
    for g in np.unique(labels):
        sel = labels == g
        per_prov[str(g)] = {
            "n_cells": int(sel.sum()),
            "median": float(np.exp(np.median(y[sel]))),
            "log_sd": float(y[sel].std(ddof=1)) if sel.sum() > 1 else 0.0,
        }

    return {
        "aoi": aoi,
        "seed": int(d["seed"]),
        "param": param,
        "n_cells": int(y.size),
        "log_sd_total": float(y.std(ddof=1)),
        "eta_sq": obs,
        "eta_sq_null_mean": float(null.mean()),
        "eta_sq_null_p95": float(np.percentile(null, 95)),
        "eta_sq_lat_band_control": lat_band,
        "p_permutation": p,
        "by_province": per_prov,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("run_dir", help="run directory containing per_cell/*.npz")
    ap.add_argument("--param", default="scav_rat")
    ap.add_argument("--aoi", help="restrict to one AOI key")
    ap.add_argument("--n-perm", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0, help="RNG seed for the permutation null")
    ap.add_argument("--json", help="write full per-seed results here")
    args = ap.parse_args()

    files = sorted(glob.glob(os.path.join(args.run_dir, "per_cell", "*.npz")))
    if args.aoi:
        files = [f for f in files if f"percell_{args.aoi}_" in os.path.basename(f)]
    if not files:
        print(f"no per-cell fields under {args.run_dir}/per_cell "
              f"-- was the run submitted with SAVE_PER_CELL_SEEDS>0?")
        return 2

    rng = np.random.default_rng(args.seed)
    rows = [r for f in files if (r := analyse(f, args.param, args.n_perm, rng))]
    if not rows:
        print(f"no field carried parameter {args.param!r}")
        return 2

    by_aoi = defaultdict(list)
    for r in rows:
        by_aoi[r["aoi"]].append(r)

    print(f"\n=== province share of per-cell log-variance in {args.param} ===")
    print(f"    {len(rows)} fields from {args.run_dir}, {args.n_perm} permutations each\n")
    print(f"{'AOI':20s} {'seeds':>5s} {'log_sd':>8s} {'eta^2':>8s} {'shuf':>7s} "
          f"{'latband':>8s} {'vs band':>8s} {'P':>8s}")
    summary = {}
    for aoi, rs in sorted(by_aoi.items()):
        eta = np.array([r["eta_sq"] for r in rs])
        nul = np.array([r["eta_sq_null_mean"] for r in rs])
        sd = np.array([r["log_sd_total"] for r in rs])
        # Fisher's method would assume independence across seeds; these share a fit
        # lineage, so report the median P instead and say so.
        lb = np.array([r["eta_sq_lat_band_control"] for r in rs])
        pmed = float(np.median([r["p_permutation"] for r in rs]))
        print(f"{aoi:20s} {len(rs):5d} {np.median(sd):8.3f} {np.median(eta):8.3f} "
              f"{np.median(nul):7.3f} {np.median(lb):8.3f} {np.median(eta - lb):8.3f} "
              f"{pmed:8.4f}")
        summary[aoi] = {
            "n_seeds": len(rs), "median_log_sd": float(np.median(sd)),
            "median_eta_sq": float(np.median(eta)),
            "median_shuffle_null_eta_sq": float(np.median(nul)),
            "median_lat_band_control_eta_sq": float(np.median(lb)),
            "median_excess_vs_lat_band": float(np.median(eta - lb)),
            "median_p_vs_shuffle": pmed,
        }

    print("\n  eta^2 = fraction of per-cell log-variance explained by province membership.")
    print("  'null' is the permutation mean (positive by construction with k groups);")
    print("  'excess' is the honest effect size. P is the MEDIAN across seeds -- seeds")
    print("  share a fit lineage, so they are not independent and must not be combined.")

    for aoi, rs in sorted(by_aoi.items()):
        print(f"\n--- {aoi}: per-province medians (seed {rs[0]['seed']}) ---")
        for code, c in sorted(rs[0]["by_province"].items(), key=lambda kv: -kv[1]["n_cells"]):
            print(f"    {code:10s} n={c['n_cells']:5d}  median={c['median']:.4g}  "
                  f"within-province log_sd={c['log_sd']:.3f}")

    if args.json:
        Path(args.json).write_text(
            json.dumps({"summary": summary, "per_seed": rows}, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
