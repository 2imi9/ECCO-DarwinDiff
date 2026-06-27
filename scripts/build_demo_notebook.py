"""Build notebooks/demo_colab.ipynb from cells defined here.

Run with: python scripts/build_demo_notebook.py
"""
from __future__ import annotations

import json
from pathlib import Path


def md(source: str) -> dict:
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": source.lstrip("\n").rstrip() + "\n",
    }


def code(source: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source.lstrip("\n").rstrip() + "\n",
    }


CELLS = [
    md(r"""
# ECCO-DarwinDiff — Synthetic Recovery Demo

This is a self-contained, runs-on-free-Colab-T4 demonstration of DarwinDiff: a
PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model where
gradients flow through every step of the simulation, so a per-cell neural
network can learn Carroll-6 parameter values directly from observation fields.

In ~5 minutes on a free Colab T4, this notebook:

1. Constructs a synthetic AOI (8×16 grid) with a smooth SST gradient.
2. Picks ground-truth Carroll-6 parameter values that vary smoothly with SST.
3. Forward-integrates the differentiable Darwin box model to produce a target
   phytoplankton biomass field.
4. Trains a tiny per-cell DINN to recover the truth by gradient descent
   *through* the box model.
5. Visualises recovery quality vs Carroll's published optima.

For the full v3.1 results (3-AOI joint training, 857 seeds, structural 5/6
ceiling characterisation), see
[STATUS.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/STATUS.md) and
[docs/findings/v3.1_closeout.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/docs/findings/v3.1_closeout.md).
"""),
    md(r"""
## 1. Setup

Clone the repo and add `src/` to `sys.path`. We deliberately avoid `pip install`
of the full project because its data-loading deps (xarray, xmitgcm, dask,
netcdf4) take ~2 minutes to install on Colab and aren't needed for this
synthetic demo — only `torch`, `numpy`, and `matplotlib`, all pre-installed.
"""),
    code(r"""
import subprocess, sys, os
try:
    import darwindiff  # already on PYTHONPATH (local Jupyter / editable install)
    print("darwindiff already importable; skipping clone.")
except ImportError:
    if not os.path.exists("ECCO-DarwinDiff"):
        subprocess.run(
            ["git", "clone", "-q", "https://github.com/2imi9/ECCO-DarwinDiff.git"],
            check=True,
        )
    src_path = os.path.abspath("ECCO-DarwinDiff/src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)
    import darwindiff  # verify
    print("DarwinDiff src added to sys.path:", src_path)
"""),
    md(r"""
## 2. Imports + Carroll-6 published optima

`darwindiff.carroll6` exposes the 6-parameter Carroll calibration target —
the values Carroll et al. 2020 (JAMES) recovered via Green's-functions. These
are the numbers DarwinDiff aims to recover via gradient descent.
"""),
    code(r"""
import numpy as np
import torch
import matplotlib.pyplot as plt

from darwindiff.carroll6 import (
    CARROLL_VALUES, PARAM_BOUNDS, PARAM_NAMES,
    bounded_params, carroll6_step,
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {DEVICE}")
print(f"\nCarroll-6 published optima (Carroll 2020 JAMES Table 1):")
for name, val in zip(PARAM_NAMES, CARROLL_VALUES.tolist()):
    print(f"  {name:12s} = {val:.5g}")
print(f"\nPhysical bounds (from src/darwindiff/carroll6.py PARAM_BOUNDS):")
for name, (lo, hi) in zip(PARAM_NAMES, PARAM_BOUNDS.tolist()):
    print(f"  {name:12s} ∈ [{lo:.4g}, {hi:.4g}]")
"""),
    md(r"""
## 3. Synthetic AOI + ground-truth parameter field

We build an 8×16 grid with a smooth SST gradient as the single environmental
input channel. Then we pick a ground-truth parameter field that varies smoothly
with SST: `alpfe` higher in warm cells (warm-water iron-dust proxy),
`Smallgrow` higher in cold cells. The other 4 parameters are fixed at
Carroll's published optima.

In the real v3.1 work, environmental inputs are SST + MLD + wind + latitude +
AOI-identity, and the box model couples to GLODAP/GEOTRACES/Darwin v05 fields.
This demo keeps everything in-memory and reproducible.
"""),
    code(r"""
H, W = 8, 16
N_STEPS = 200
DT = 0.25

# SST gradient as the env channel, z-scored
sst = torch.linspace(-2.0, 2.0, H).unsqueeze(1) * torch.ones(1, W)
sst = sst.unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
sst_z = (sst - sst.mean()) / (sst.std() + 1e-8)
sst_z = sst_z.to(DEVICE)
print(f"SST grid shape: {sst_z.shape}  range: [{sst_z.min():.2f}, {sst_z.max():.2f}]")
"""),
    code(r"""
# Truth params: alpfe varies 0.30 -> 0.95 with SST; Smallgrow varies 1.20 -> 0.30 with SST.
# Others fixed at Carroll's optima.
def make_truth(sst_norm_2d):
    bounds = PARAM_BOUNDS.to(DEVICE)
    carroll = CARROLL_VALUES.to(DEVICE)
    truth = torch.zeros(6, H, W, device=DEVICE)
    truth[0] = 0.30 + sst_norm_2d * (0.95 - 0.30)      # alpfe
    truth[1] = carroll[1]                              # scav_rat (constant)
    truth[2] = 1.20 - sst_norm_2d * (1.20 - 0.30)      # Smallgrow
    truth[3] = carroll[3]                              # Biggrow (constant)
    truth[4] = carroll[4]                              # diatomgraz (constant)
    truth[5] = carroll[5]                              # R_PICPOC (constant)
    return truth

sst_norm = (sst_z.squeeze() - sst_z.min()) / (sst_z.max() - sst_z.min() + 1e-8)
truth = make_truth(sst_norm)
print(f"Truth alpfe varies: [{truth[0].min():.3f}, {truth[0].max():.3f}]")
print(f"Truth Smallgrow varies: [{truth[2].min():.3f}, {truth[2].max():.3f}]")
print("Other params fixed at Carroll's optima.")
"""),
    md(r"""
## 4. Forward-integrate the box model

`carroll6_step` is the differentiable PyTorch port of Darwin's 5-tracer
reaction network. It operates per-cell, but PyTorch broadcasting lets us
integrate all 128 cells of the 8×16 grid in parallel.

We integrate 200 forward-Euler steps (50 simulated days) to reach a near
steady-state biomass field. This is the target the DINN will learn to match.
"""),
    code(r"""
def forward_box(params_field):
    # Integrate the box model per cell, vectorized via broadcasting.
    # params_field: shape [6, H, W] in physical units. Returns biomass [H, W].
    state = torch.stack([
        torch.full((H, W), 0.5e-3, device=params_field.device),  # DFe
        torch.full((H, W), 0.05,   device=params_field.device),  # Ps
        torch.full((H, W), 0.05,   device=params_field.device),  # Pl
        torch.full((H, W), 0.1,    device=params_field.device),  # POC
        torch.full((H, W), 0.001,  device=params_field.device),  # PIC
    ])
    for _ in range(N_STEPS):
        state = carroll6_step(state, params_field, DT)
    return state[1] + state[2]

target = forward_box(truth)
print(f"Steady-state phyto biomass: [{target.min():.4f}, {target.max():.4f}] mmol C/m^3")
"""),
    md(r"""
### Quick visualisation: SST gradient, truth params, target field
"""),
    code(r"""
fig, axes = plt.subplots(1, 4, figsize=(15, 3))
imgs = [
    (sst_z.squeeze().cpu(), "Input: SST (z-scored)"),
    (truth[0].cpu(), "Truth alpfe (varies)"),
    (truth[2].cpu(), "Truth Smallgrow (varies)"),
    (target.detach().cpu(), "Target: Ps + Pl biomass"),
]
for ax, (img, title) in zip(axes, imgs):
    im = ax.imshow(img, aspect="auto", origin="lower", cmap="viridis")
    ax.set_title(title, fontsize=10)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout()
plt.show()
"""),
    md(r"""
## 5. Define a minimal per-cell DINN

The architectural commitment is **1×1 convolutions** — every cell predicts its
own parameter vector from its own environmental input, with no spatial sharing.
This is what makes the structural-ceiling argument clean: the DINN parametric
class strictly contains Carroll's global-scalar class.

Production DINN/DINNDeep have ~454 / ~9.4K weights. The tiny version here has
~200 weights, sufficient for this 8×16 demo.
"""),
    code(r"""
class TinyDINN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(1, 8, kernel_size=1),
            torch.nn.Tanh(),
            torch.nn.Conv2d(8, 8, kernel_size=1),
            torch.nn.Tanh(),
            torch.nn.Conv2d(8, 6, kernel_size=1),
        )

    def forward(self, env):
        return self.net(env)  # [B, 6, H, W] unbounded

torch.manual_seed(0)
net = TinyDINN().to(DEVICE)
n_params = sum(p.numel() for p in net.parameters())
print(f"TinyDINN: {n_params} parameters (production DINN: ~454; DINNDeep: ~9.4K)")
"""),
    md(r"""
## 6. Train by gradient descent through the box model

Adam at lr=5e-3 for 800 epochs. Each epoch:

1. Network predicts 6 raw parameter values per cell from SST.
2. `bounded_params` sigmoid-bounds them into physical ranges (PARAM_BOUNDS).
3. `forward_box` integrates the box model with those per-cell params.
4. Z-scored MSE loss against the target field.
5. Backward pass — autograd traces gradients through all 200 box-model steps
   back to the network weights.
6. Adam step.

This is the entire DarwinDiff training loop, in 30 lines.
"""),
    code(r"""
N_EPOCHS = 800
LR = 5e-3
optim = torch.optim.Adam(net.parameters(), lr=LR)
bounds = PARAM_BOUNDS.to(DEVICE)
target_zscored = (target - target.mean()) / (target.std() + 1e-8)

loss_history = []
for epoch in range(N_EPOCHS):
    raw = net(sst_z)                                          # [1, 6, H, W]
    params = bounded_params(raw, bounds, param_axis=1).squeeze(0)  # [6, H, W]
    pred = forward_box(params)
    pred_zscored = (pred - pred.mean()) / (pred.std() + 1e-8)
    loss = ((pred_zscored - target_zscored) ** 2).mean()
    loss.backward()
    optim.step()
    optim.zero_grad()
    loss_history.append(loss.item())
    if epoch % 200 == 0:
        print(f"  epoch {epoch:4d}  loss={loss.item():.4f}")
print(f"Final loss: {loss_history[-1]:.5f}  (target: < 0.01)")
"""),
    md(r"""
## 7. Evaluate recovery

Loss curve + per-parameter recovery (true vs predicted scatter). Per-cell DINN
should recover the spatial structure of the parameters that vary with SST
(alpfe, Smallgrow). Parameters that are constant in the truth may drift to
alternative values that explain the same target field — this is the
underdetermination phenomenon that the full v3.1 work characterises across
857 seeds (historical '5/6 ceiling' framing, since superseded by the 4-observable identifiability study; see STATUS.md).
"""),
    code(r"""
# Loss curve
fig, ax = plt.subplots(1, 1, figsize=(8, 3))
ax.semilogy(loss_history)
ax.set_xlabel("Epoch")
ax.set_ylabel("Loss (log scale)")
ax.set_title(f"Training loss — DINN gradient descent through 200 box steps × {N_EPOCHS} epochs")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()
"""),
    code(r"""
# Recovered params + per-param scatter
net.eval()
with torch.no_grad():
    raw = net(sst_z)
    recovered = bounded_params(raw, bounds, param_axis=1).squeeze(0).cpu().numpy()
truth_np = truth.cpu().numpy()

fig, axes = plt.subplots(2, 3, figsize=(13, 7))
for i, (ax, name) in enumerate(zip(axes.flat, PARAM_NAMES)):
    rec = recovered[i].flatten()
    tru = truth_np[i].flatten()
    carroll_val = CARROLL_VALUES[i].item()
    if np.std(tru) > 1e-9:
        # Varying truth: scatter true-vs-recovered per cell
        ax.scatter(tru, rec, s=20, alpha=0.7)
        mn, mx = min(tru.min(), rec.min()), max(tru.max(), rec.max())
        ax.plot([mn, mx], [mn, mx], "k--", alpha=0.4, label="perfect recovery")
        r = float(np.corrcoef(rec, tru)[0, 1])
        ax.set_title(f"{name} — VARIES (Pearson r={r:.2f})")
    else:
        # Constant truth: histogram of recovered values + truth + Carroll
        ax.hist(rec, bins=15, alpha=0.7, color="steelblue", label="recovered")
        ax.axvline(tru.mean(), color="black", linestyle="--",
                   label=f"truth={tru.mean():.3g}")
        ax.axvline(carroll_val, color="red", linestyle=":",
                   label=f"Carroll={carroll_val:.3g}")
        ax.set_title(f"{name} — CONST in truth")
        ax.legend(fontsize=8)
    ax.set_xlabel("true value")
    ax.set_ylabel("recovered")
plt.tight_layout()
plt.show()
"""),
    md(r"""
## 8. Interpretation

What this demo showed:

- The DINN architecture trains end-to-end via autograd through the box model.
- Loss converges by several orders of magnitude — the spatial pattern of the
  target field is matched.
- **Parameters that vary with the input** (alpfe, Smallgrow in this demo)
  recover their spatial structure (Pearson r close to 1 for Smallgrow). This
  is the per-cell parameter recovery advantage that Carroll's global-scalar
  calibration cannot express.
- **Parameters that are constant in the truth** may drift to alternative
  values that fit the same target field. This is the **underdetermination
  phenomenon** that the full v3.1 work characterises.

In the production v3.1 work (3-AOI joint training across Equatorial Pacific +
North Atlantic Subpolar + Southern Ocean Pacific, with 7+ observation
channels including GEOTRACES biogenic silica), the structural 5/6 Cal-grade
ceiling holds across **857 seeds in 86 configurations**: only 2 single-seed
events broke 5/6, both unreproduced at n=20, and a composition test of their
lever combinations fails. The ceiling is supported by four independent pieces
of evidence — see
[STATUS.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/STATUS.md) for
the full account and the
[paper-prep closeout](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/docs/findings/v3.1_closeout.md).

Next steps for unlocking the 6/6 ceiling are cluster-gated: time-resolved
fitting + box-model extension toward full Darwin 3. See
[docs/cluster_roadmap.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/docs/cluster_roadmap.md).
"""),
]


NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.11",
        },
        "accelerator": "GPU",
        "colab": {"provenance": []},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main():
    out = Path(__file__).resolve().parent.parent / "notebooks" / "demo_colab.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(NOTEBOOK, indent=1), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"  cells: {len(CELLS)} ({sum(1 for c in CELLS if c['cell_type'] == 'code')} code, "
          f"{sum(1 for c in CELLS if c['cell_type'] == 'markdown')} markdown)")


if __name__ == "__main__":
    main()
