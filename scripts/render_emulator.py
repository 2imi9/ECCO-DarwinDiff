"""Render Earth-2-style visuals of the DarwinDiff emulator's held-out predictions.

Reads the .npz dumped by scripts/emulator_poc.py --dump-fields and produces:
  1. <out>_forecast.png : per-tracer [truth | emulator | error] maps for one held-out month.
  2. <out>_skillmap.png : per-cell skill (1 - MSE_model/MSE_persistence) over all held-out months,
                          i.e. WHERE the emulator beats persistence.
Usage: python render_emulator.py fields.npz out_prefix
"""
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

npz, out = sys.argv[1], sys.argv[2]
d = np.load(npz, allow_pickle=True)
pred, true, persist = d["pred"].astype(float), d["true"].astype(float), d["persistence"].astype(float)  # [N,C,H,W]
vm = d["valid_mask"].astype(bool)
lats, lons = d["lats"], d["lons"]
chans = [str(c) for c in d["chan_names"]]
N, C, H, W = pred.shape
extent = [lons.min(), lons.max(), lats.min(), lats.max()]
land = ~vm

# collapse depth-level channels to their base tracer for a cleaner figure (surface level k0 if present)
def base_idx():
    keep, labels = [], []
    for i, c in enumerate(chans):
        if c.endswith("_k0") or "_k" not in c:
            keep.append(i); labels.append(c.replace("_k0", ""))
    return keep, labels
keep, labels = base_idx()

def mask(f):
    g = f.copy(); g[land] = np.nan; return g

# choose the held-out month with the most "action" (largest true month-to-month change) for a vivid panel
change = np.array([np.nanmean(np.abs((true[m] - persist[m])[:, vm])) for m in range(N)])
m = int(np.argmax(change))

# ---- Figure 1: forecast panels (truth | emulator | error) ----
nrow = len(keep)
fig, axes = plt.subplots(nrow, 3, figsize=(11, 2.5 * nrow), constrained_layout=True)
if nrow == 1:
    axes = axes[None, :]
fig.suptitle(f"DarwinDiff emulator — eqpac held-out month (iter {int(d['val_iters'][m])})\n"
             f"residual+rollout-k{int(d['rollout_train_k'])} · truth vs 1-step prediction",
             fontsize=13, fontweight="bold")
for r, (ci, name) in enumerate(zip(keep, labels)):
    t, p = mask(true[m, ci]), mask(pred[m, ci])
    vmin, vmax = np.nanpercentile(t, 2), np.nanpercentile(t, 98)
    err = p - t
    emax = np.nanpercentile(np.abs(err), 98) or 1e-9
    for c, (data_, title, cmap, norm) in enumerate([
        (t, "truth (v05)", "viridis", None),
        (p, "emulator", "viridis", None),
        (err, "error (emu−truth)", "RdBu_r", TwoSlopeNorm(0, -emax, emax)),
    ]):
        ax = axes[r, c]
        kw = dict(extent=extent, origin="lower", aspect="auto", cmap=cmap)
        im = ax.imshow(data_, vmin=vmin, vmax=vmax, **kw) if norm is None else ax.imshow(data_, norm=norm, **kw)
        ax.set_facecolor("#dddddd")
        fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
        if r == 0:
            ax.set_title(title, fontsize=11)
        if c == 0:
            ax.set_ylabel(f"{name}\nlat", fontsize=10)
        if r == nrow - 1:
            ax.set_xlabel("lon")
        ax.tick_params(labelsize=7)
fig.savefig(f"{out}_forecast.png", dpi=130)
print(f"wrote {out}_forecast.png  (month idx {m}, {nrow} tracers)")

# ---- Figure 2: per-cell skill map over all held-out months ----
fig2, axes2 = plt.subplots(1, len(keep), figsize=(3.1 * len(keep), 3.4), constrained_layout=True)
if len(keep) == 1:
    axes2 = [axes2]
fig2.suptitle("Where the emulator beats persistence — per-cell skill = 1 − MSE(emu)/MSE(persist)\n"
              "green = beats persistence, red = worse (held-out months)", fontsize=12, fontweight="bold")
for ax, ci, name in zip(axes2, keep, labels):
    se_m = np.nansum((pred[:, ci] - true[:, ci]) ** 2, axis=0)
    se_p = np.nansum((persist[:, ci] - true[:, ci]) ** 2, axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        skill = 1.0 - se_m / se_p
    skill = mask(skill)
    im = ax.imshow(skill, extent=extent, origin="lower", aspect="auto",
                   cmap="RdYlGn", norm=TwoSlopeNorm(0, -1.0, 1.0))
    ax.set_facecolor("#dddddd")
    frac = np.mean(skill[np.isfinite(skill)] > 0)
    ax.set_title(f"{name}  ({100*frac:.0f}% cells > 0)", fontsize=10)
    ax.set_xlabel("lon"); ax.tick_params(labelsize=7)
    fig2.colorbar(im, ax=ax, fraction=0.045, pad=0.02)
axes2[0].set_ylabel("lat")
fig2.savefig(f"{out}_skillmap.png", dpi=130)
print(f"wrote {out}_skillmap.png")
