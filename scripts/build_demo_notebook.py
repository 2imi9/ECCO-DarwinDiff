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
# ECCO-DarwinDiff — Differentiable Parameter Recovery Demo

A self-contained, runs-on-free-Colab-T4 demonstration of DarwinDiff: a PyTorch
reimplementation of the ECCO-Darwin ocean-biogeochemistry box model where
gradients flow through every simulation step, so parameters can be learned by
gradient descent *through* the model.

In ~5 minutes on a free Colab T4, this notebook:

1. Builds a synthetic AOI (8×16 grid) with a smooth SST gradient.
2. Picks ground-truth Carroll-6 values and forward-integrates the differentiable
   box model to produce a target biomass field.
3. Recovers the parameters **two ways** — a **per-cell DINN** and a **single
   global-scalar vector** (the differentiable analogue of one Green's-functions
   optimum) — and compares them head to head. This is a miniature, in-memory
   version of the per-cell-vs-global ablation the project runs against real
   ECCO-Darwin v05 output.

**What this demo is:** a clean illustration of the differentiable method, and of
*what a per-cell predictor can represent that a global scalar cannot*.
**What it is not:** evidence about which ECCO-Darwin parameters are actually
identifiable — that comes from the full study (multi-AOI fits against real
GEOTRACES iron + calcite anchors, n≥10, `verify_run.py`-gated). The project's
honest framing is a **surrogate-to-model identifiability study over the 4
observable Carroll-6 parameters** ({`alpfe`, `scav_rat`, `diatomgraz`,
`R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is unobservable by
construction). See
[STATUS.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/STATUS.md).
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
## 2. Imports + Carroll-6 calibration target

`darwindiff.carroll6` exposes the 6-parameter Carroll calibration target — the
values ECCO-Darwin was tuned to (Carroll et al.; the canonical registry lives in
`src/darwindiff/carroll6.py`). These are the numbers DarwinDiff aims to recover
by gradient descent.
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
print(f"\nCarroll-6 calibration target (src/darwindiff/carroll6.py):")
for name, val in zip(PARAM_NAMES, CARROLL_VALUES.tolist()):
    print(f"  {name:12s} = {val:.5g}")
print(f"\nPhysical bounds (PARAM_BOUNDS):")
for name, (lo, hi) in zip(PARAM_NAMES, PARAM_BOUNDS.tolist()):
    print(f"  {name:12s} ∈ [{lo:.4g}, {hi:.4g}]")
"""),
    md(r"""
## 3. Synthetic AOI + ground-truth parameter field

We build an 8×16 grid with a smooth SST gradient as the single environmental
input channel. Then we pick a ground-truth parameter field that **varies smoothly
with SST**: `alpfe` higher in warm cells (warm-water iron-dust proxy),
`Smallgrow` higher in cold cells. The other 4 parameters are fixed at Carroll's
optima.

Note this is the *favourable* case for a per-cell predictor — the truth genuinely
varies in space, so there is spatial structure to find. We return to that caveat
in the interpretation: ECCO-Darwin's real parameters were calibrated as **global
constants**, which is why the per-cell-vs-global question is open and worth a real
ablation. In the production work, environmental inputs are SST + MLD + wind +
latitude + AOI-identity, and the box couples to GLODAP/GEOTRACES/Darwin v05 fields.
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

`carroll6_step` is the differentiable PyTorch port of Darwin's 5-tracer reaction
network. It operates per-cell, but PyTorch broadcasting lets us integrate all 128
cells of the 8×16 grid in parallel.

We integrate 200 forward-Euler steps (50 simulated days) to reach a near
steady-state biomass field. This is the target both recovery methods will learn
to match.
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
target_zscored = (target - target.mean()) / (target.std() + 1e-8)
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
## 5. Two parameter classes: per-cell DINN vs one global scalar

The architectural question DarwinDiff poses: should **each grid cell** get its own
parameter vector (a **per-cell DINN**, built from 1×1 convolutions — every cell
predicts from its own covariates, with no spatial sharing), or is a **single
global vector** enough (Carroll's actual calibration produces one global Carroll-6
set)?

The per-cell class strictly *contains* the global one, so on any target it can
never fit worse. The real question is whether that extra capacity is
**load-bearing** — does it recover structure a global scalar cannot? Rather than
assert it, we **test it directly below**: train both on the same target and
compare the loss and the recovered fields.
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
print("Global-scalar baseline: 6 free parameters (one Carroll-6 vector for the whole grid).")
"""),
    md(r"""
## 6. Train both, by gradient descent through the box model

Adam at lr=5e-3 for 800 epochs, identical for both methods. Each epoch: predict
params → `bounded_params` sigmoid into PARAM_BOUNDS → integrate the box →
z-scored MSE against the target → backward (autograd traces gradients through all
200 box steps) → Adam step. The **only** difference between the two runs is the
parameter source: a per-cell field vs a single broadcast vector.
"""),
    code(r"""
N_EPOCHS = 800
LR = 5e-3
bounds = PARAM_BOUNDS.to(DEVICE)

# (a) Per-cell DINN — each cell predicts its own Carroll-6 vector from SST.
torch.manual_seed(0)
net = TinyDINN().to(DEVICE)
optim = torch.optim.Adam(net.parameters(), lr=LR)
loss_history = []
for epoch in range(N_EPOCHS):
    raw = net(sst_z)                                               # [1, 6, H, W]
    params = bounded_params(raw, bounds, param_axis=1).squeeze(0)  # [6, H, W]
    pred = forward_box(params)
    pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
    loss = ((pred_z - target_zscored) ** 2).mean()
    loss.backward(); optim.step(); optim.zero_grad()
    loss_history.append(loss.item())
    if epoch % 200 == 0:
        print(f"  [per-cell] epoch {epoch:4d}  loss={loss.item():.5f}")
print(f"Per-cell DINN final loss: {loss_history[-1]:.5f}")
"""),
    code(r"""
# (b) Global-scalar baseline — ONE Carroll-6 vector for the whole grid (no spatial
# variation). This is the differentiable analogue of a single Green's-functions optimum.
torch.manual_seed(0)
raw_g = torch.zeros(6, device=DEVICE, requires_grad=True)
optim_g = torch.optim.Adam([raw_g], lr=LR)
loss_history_g = []
for epoch in range(N_EPOCHS):
    params_g = bounded_params(raw_g, bounds)                  # [6]
    params_g_field = params_g.view(6, 1, 1).expand(6, H, W)   # broadcast, identical per cell
    pred = forward_box(params_g_field)
    pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
    loss = ((pred_z - target_zscored) ** 2).mean()
    loss.backward(); optim_g.step(); optim_g.zero_grad()
    loss_history_g.append(loss.item())
    if epoch % 200 == 0:
        print(f"  [global ] epoch {epoch:4d}  loss={loss.item():.5f}")
print(f"Global-scalar final loss: {loss_history_g[-1]:.5f}   "
      f"(per-cell DINN: {loss_history[-1]:.5f})")
ratio = loss_history_g[-1] / max(loss_history[-1], 1e-12)
print(f"Loss ratio global/per-cell: {ratio:.1f}x  "
      f"(>1 means per-cell fits the spatially-varying target better)")
"""),
    md(r"""
## 7. Compare — loss curves + recovered fields

The honest A/B: same target, same optimiser, same epochs; only the parameter
source differs.
"""),
    code(r"""
# Loss curves, both methods
fig, ax = plt.subplots(1, 1, figsize=(8, 3))
ax.semilogy(loss_history, label=f"per-cell DINN (final {loss_history[-1]:.4f})")
ax.semilogy(loss_history_g, label=f"global scalar (final {loss_history_g[-1]:.4f})")
ax.set_xlabel("Epoch"); ax.set_ylabel("Loss (log scale)")
ax.set_title(f"Training loss through 200 box steps × {N_EPOCHS} epochs")
ax.legend(); ax.grid(alpha=0.3)
plt.tight_layout(); plt.show()
"""),
    code(r"""
# Recovered alpfe field: truth (varies) vs per-cell (can vary) vs global (flat by construction)
net.eval()
with torch.no_grad():
    raw = net(sst_z)
    rec_pc = bounded_params(raw, bounds, param_axis=1).squeeze(0).cpu().numpy()   # [6,H,W]
    rec_g = bounded_params(raw_g.detach(), bounds).cpu().numpy()                  # [6]
truth_np = truth.cpu().numpy()

idx = 0  # alpfe (the varying one)
g_field = np.full((H, W), rec_g[idx])
vmin = min(truth_np[idx].min(), rec_pc[idx].min(), g_field.min())
vmax = max(truth_np[idx].max(), rec_pc[idx].max(), g_field.max())
fig, axes = plt.subplots(1, 3, figsize=(13, 3))
for ax, (img, title) in zip(axes, [
    (truth_np[idx], "Truth alpfe (varies with SST)"),
    (rec_pc[idx], "Per-cell DINN recovered"),
    (g_field, "Global scalar recovered (flat)"),
]):
    im = ax.imshow(img, aspect="auto", origin="lower", cmap="viridis", vmin=vmin, vmax=vmax)
    ax.set_title(title, fontsize=10); plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout(); plt.show()

r_pc = float(np.corrcoef(rec_pc[idx].flatten(), truth_np[idx].flatten())[0, 1])
print(f"alpfe spatial recovery — per-cell Pearson r = {r_pc:.2f}; "
      f"global scalar is constant ({rec_g[idx]:.3f}) so it has no spatial r by construction.")
"""),
    md(r"""
## 8. Interpretation

- Both classes train end-to-end via autograd through 200 box steps — the
  **differentiable method works**.
- The **per-cell DINN reaches lower loss and recovers the SST-varying structure**
  of `alpfe`/`Smallgrow`; the global scalar is flat by construction (one number
  cannot vary across cells). This is the per-cell *representational advantage* —
  shown, not asserted.
- **Honest caveat (this is the crux).** Here the truth varies spatially *by
  construction*, which hands the per-cell predictor something to find. Against
  real ECCO-Darwin, whose Carroll-6 parameters were calibrated as **global
  constants**, a global scalar is the natural hypothesis — so whether the per-cell
  predictor is *load-bearing for the real problem* is exactly the open question the
  full **per-cell-vs-global ablation** answers (real GEOTRACES iron + calcite
  anchors, multi-AOI, n≥10, `verify_run.py`-gated). This synthetic demo shows the
  mechanism; it does not settle the real case.
- Two facts from the full study this in-memory demo cannot show: against real data
  the 0-D box **homogenizes** (tracer CV → ~1e-15), so identifiability comes from
  real *absolute* anchors rather than the box's own spatial pattern; and the growth
  pair is **unobservable by construction** (no real growth-rate data). The honest
  target is the **4 observable parameters**.

For the full account — the surrogate-to-model identifiability framing, the
real-data iron/calcite recovery, and the known limitations — see
[STATUS.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/STATUS.md) and
[docs/findings/index.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/docs/findings/index.md).
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
