#!/usr/bin/env python3
r"""plot_emulator_globe.py -- render the Track-2 FNO emulator's global prediction
as a 2-D globe (orthographic) + flat comparison maps, from an emulator_poc
``--dump-fields`` npz.

The emulator field is ocean-only (land = NaN), so an orthographic projection with
land filled neutral-grey shows the continents for free (the land/ocean boundary IS
the coastline) -- no cartopy/coastline dataset needed.

npz keys (from emulator_poc.py): pred/true/persistence [Nval,C,H,W], valid_mask [H,W],
lats [H], lons [W], chan_names [C], val_iters [Nval].

Usage:
  python scripts/plot_emulator_globe.py --npz global_fields.npz --channel Chl1 \
      --out docs/figures/emulator_globe.png [--lon0 -150 --lat0 20 --month -1 --log]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors


def _orthographic(lats, lons, lon0, lat0):
    """Project a regular lat/lon grid to orthographic (x, y) + visibility mask."""
    LON, LAT = np.meshgrid(lons, lats)  # [H, W]
    lam = np.deg2rad(LON - lon0)
    phi = np.deg2rad(LAT)
    phi0 = np.deg2rad(lat0)
    cosc = np.sin(phi0) * np.sin(phi) + np.cos(phi0) * np.cos(phi) * np.cos(lam)
    x = np.cos(phi) * np.sin(lam)
    y = np.cos(phi0) * np.sin(phi) - np.sin(phi0) * np.cos(phi) * np.cos(lam)
    return x, y, cosc > 0


def _norm(field, log):
    finite = np.isfinite(field)
    if not finite.any():
        return mcolors.Normalize(0, 1)
    if log:
        pos = field[finite & (field > 0)]
        if pos.size:
            vmin, vmax = np.percentile(pos, [2, 98])
            return mcolors.LogNorm(max(vmin, 1e-6), max(vmax, vmin * 10))
    vmin, vmax = np.percentile(field[finite], [2, 98])
    return mcolors.Normalize(vmin, vmax)


def _globe(ax, lats, lons, field, lon0, lat0, norm, cmap, title):
    x, y, vis = _orthographic(lats, lons, lon0, lat0)
    # sphere disc background (ocean grey where no data, so land reads as the field gap)
    th = np.linspace(0, 2 * np.pi, 200)
    ax.fill(np.cos(th), np.sin(th), color="#dfe3e8", zorder=0)          # sphere face (land+empty)
    fld = np.where(vis, field, np.nan)
    ax.pcolormesh(x, y, fld, norm=norm, cmap=cmap, shading="nearest", zorder=1)
    ax.plot(np.cos(th), np.sin(th), color="#7c8592", lw=1.2, zorder=3)  # limb
    ax.set_xlim(-1.05, 1.05); ax.set_ylim(-1.05, 1.05)
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title, fontsize=11, fontweight="bold", color="#1a1a1a")


def _flat(ax, lats, lons, field, norm, cmap, title):
    ax.set_facecolor("#dfe3e8")  # land/empty
    pm = ax.pcolormesh(lons, lats, field, norm=norm, cmap=cmap, shading="nearest")
    ax.set_xlim(lons.min(), lons.max()); ax.set_ylim(lats.min(), lats.max())
    ax.set_title(title, fontsize=10, fontweight="bold", color="#1a1a1a")
    ax.set_xticks([]); ax.set_yticks([])
    return pm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--npz", required=True)
    ap.add_argument("--channel", default="Chl1")
    ap.add_argument("--month", type=int, default=-1, help="validation-month index (default last)")
    ap.add_argument("--lon0", type=float, default=-150.0)
    ap.add_argument("--lat0", type=float, default=20.0)
    ap.add_argument("--log", action="store_true", help="log color scale (for chl)")
    ap.add_argument("--out", default="docs/figures/emulator_globe.png")
    args = ap.parse_args()

    d = np.load(args.npz, allow_pickle=True)
    chans = [str(c) for c in d["chan_names"]]
    if args.channel not in chans:
        raise SystemExit(f"--channel {args.channel} not in {chans}")
    ci = chans.index(args.channel)
    lats = d["lats"].astype(float); lons = d["lons"].astype(float)
    pred = d["pred"][args.month, ci]
    true = d["true"][args.month, ci]
    persist = d["persistence"][args.month, ci]

    # per-cell skill vs persistence over ALL val months (1 - MSE_model/MSE_persist)
    P = d["pred"][:, ci]; T = d["true"][:, ci]; K = d["persistence"][:, ci]
    se_m = np.nanmean((P - T) ** 2, axis=0)
    se_k = np.nanmean((K - T) ** 2, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        skill = 1.0 - se_m / se_k
    skill = np.where(np.isfinite(skill), skill, np.nan)

    norm = _norm(true, args.log)
    cmap = "viridis"

    fig = plt.figure(figsize=(13, 7.2))
    fig.patch.set_facecolor("white")
    gs = fig.add_gridspec(2, 3, height_ratios=[1.35, 1.0], hspace=0.16, wspace=0.12,
                          left=0.03, right=0.97, top=0.9, bottom=0.06)
    lbl = f"{args.channel}" + ("  (log)" if args.log else "")

    # hero globe (spans the top-left 2 cols)
    axg = fig.add_subplot(gs[0, :2])
    _globe(axg, lats, lons, pred, args.lon0, args.lat0, norm, cmap,
           f"Emulator prediction — next-month {lbl}  (2-D globe)")
    # top-right: skill globe
    axs = fig.add_subplot(gs[0, 2])
    sknorm = mcolors.TwoSlopeNorm(vcenter=0.0, vmin=-1.0, vmax=1.0)
    _globe(axs, lats, lons, skill, args.lon0, args.lat0, sknorm, "RdBu_r",
           "Skill vs persistence")

    pm = _flat(fig.add_subplot(gs[1, 0]), lats, lons, pred, norm, cmap, f"predicted {lbl}")
    _flat(fig.add_subplot(gs[1, 1]), lats, lons, true, norm, cmap, f"ECCO-Darwin v05 truth {lbl}")
    axsk = fig.add_subplot(gs[1, 2])
    pmsk = _flat(axsk, lats, lons, skill, sknorm, "RdBu_r", "skill vs persistence")

    cax1 = fig.add_axes([0.045, 0.02, 0.28, 0.018]); fig.colorbar(pm, cax=cax1, orientation="horizontal")
    cax2 = fig.add_axes([0.70, 0.02, 0.25, 0.018]); fig.colorbar(pmsk, cax=cax2, orientation="horizontal")

    fig.suptitle("ECCO-DarwinDiff Track-2 emulator — global next-month prediction (FNO2d)",
                 fontsize=13, fontweight="bold", color="#1a1a1a", y=0.975)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=160, facecolor="white")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
