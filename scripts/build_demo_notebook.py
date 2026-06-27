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
# ECCO-DarwinDiff — Identifiability Demo (differentiable parameter recovery)

A self-contained, runs-in-the-browser demonstration of DarwinDiff: a PyTorch
reimplementation of the ECCO-Darwin ocean-biogeochemistry box model where
gradients flow through every simulation step, so parameters can be learned by
gradient descent *through* the model.

In ~10 minutes on a free Colab T4 (CPU works too), this notebook builds a
synthetic test problem and uses it to show the project's three core lessons —
**honestly, by running them**, not asserting them:

1. **Capacity.** A *per-cell* neural network can fit spatial structure that a
   single *global* parameter vector (the analogue of one Green's-functions
   optimum) provably cannot.
2. **Fitting ≠ identifying.** Driving the loss to ~zero does **not** mean the
   true parameters were recovered — different parameter fields fit the same
   observable (equifinality). We show `alpfe` recovered with a *coin-flip sign*
   across seeds.
3. **Identifiability is parameter-specific.** Under identical fits, some
   parameters are recovered consistently and others are not — which is exactly
   what determines whether a given observation can constrain a given parameter.

This is why the real project is framed as a **surrogate-to-model identifiability
study over the 4 observable Carroll-6 parameters** ({`alpfe`, `scav_rat`,
`diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is
unobservable by construction), and why it leans on real *absolute* anchors
(GEOTRACES iron, Daniels calcite) rather than pattern-matching alone. See
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
    print(f"  {name:12s} in [{lo:.4g}, {hi:.4g}]")
"""),
    md(r"""
## 3. Synthetic AOI + ground-truth parameter field

We build an 8×16 grid with a smooth SST gradient as the single environmental
input channel, then a ground-truth parameter field that varies smoothly with
SST: `alpfe` higher in warm cells (warm-water iron-dust proxy), `Smallgrow`
higher in cold cells. The other 4 parameters are fixed at Carroll's optima.

This is the *favourable* case for a per-cell predictor — the truth genuinely
varies in space, so there is structure to find. (ECCO-Darwin's real parameters
were calibrated as **global constants**, which is why the per-cell-vs-global
question is open and worth a real ablation; we return to this at the end.)
"""),
    code(r"""
H, W = 8, 16
N_STEPS = 150
DT = 0.25

sst = (torch.linspace(-2.0, 2.0, H).unsqueeze(1) * torch.ones(1, W)).unsqueeze(0).unsqueeze(0)
sst_z = ((sst - sst.mean()) / (sst.std() + 1e-8)).to(DEVICE)   # [1,1,H,W]
print(f"SST grid shape: {sst_z.shape}  range: [{sst_z.min():.2f}, {sst_z.max():.2f}]")
"""),
    code(r"""
def make_truth(sst_norm_2d):
    carroll = CARROLL_VALUES.to(DEVICE)
    t = torch.zeros(6, H, W, device=DEVICE)
    t[0] = 0.30 + sst_norm_2d * (0.95 - 0.30)      # alpfe varies with SST
    t[1] = carroll[1]                              # scav_rat (constant)
    t[2] = 1.20 - sst_norm_2d * (1.20 - 0.30)      # Smallgrow varies with SST
    t[3] = carroll[3]; t[4] = carroll[4]; t[5] = carroll[5]
    return t

sst_norm = (sst_z.squeeze() - sst_z.min()) / (sst_z.max() - sst_z.min() + 1e-8)
truth = make_truth(sst_norm)
alpfe_true = truth[0].flatten().cpu().numpy()
smallgrow_true = truth[2].flatten().cpu().numpy()
print(f"Truth alpfe varies:     [{truth[0].min():.3f}, {truth[0].max():.3f}]")
print(f"Truth Smallgrow varies: [{truth[2].min():.3f}, {truth[2].max():.3f}]")
print("Other params fixed at Carroll's optima.")
"""),
    md(r"""
## 4. Forward-integrate the box model

`carroll6_step` is the differentiable PyTorch port of Darwin's 5-tracer reaction
network. It is per-cell, but PyTorch broadcasting integrates all 128 cells in
parallel. 150 forward-Euler steps reach a near steady-state biomass field — the
**single observable** both recovery methods must match.
"""),
    code(r"""
def forward_box(params_field):
    state = torch.stack([
        torch.full((H, W), 0.5e-3, device=params_field.device),  # DFe
        torch.full((H, W), 0.05,   device=params_field.device),  # Ps
        torch.full((H, W), 0.05,   device=params_field.device),  # Pl
        torch.full((H, W), 0.1,    device=params_field.device),  # POC
        torch.full((H, W), 0.001,  device=params_field.device),  # PIC
    ])
    for _ in range(N_STEPS):
        state = carroll6_step(state, params_field, DT)
    return state[1] + state[2]                                   # Ps + Pl biomass

target = forward_box(truth).detach()
target_z = (target - target.mean()) / (target.std() + 1e-8)
print(f"Steady-state phyto biomass: [{target.min():.4f}, {target.max():.4f}] mmol C/m^3")
"""),
    md(r"""
### Quick visualisation: SST gradient, truth params, target field
"""),
    code(r"""
fig, axes = plt.subplots(1, 4, figsize=(15, 3))
for ax, (img, title) in zip(axes, [
    (sst_z.squeeze().cpu(), "Input: SST (z-scored)"),
    (truth[0].cpu(), "Truth alpfe (varies)"),
    (truth[2].cpu(), "Truth Smallgrow (varies)"),
    (target.detach().cpu(), "Target: Ps + Pl biomass"),
]):
    im = ax.imshow(img, aspect="auto", origin="lower", cmap="viridis")
    ax.set_title(title, fontsize=10); plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout(); plt.show()
"""),
    md(r"""
## 5. Two parameter classes: per-cell DINN vs one global scalar

Should **each grid cell** get its own parameter vector (a **per-cell DINN**, 1×1
convolutions — every cell predicts from its own covariates, no spatial sharing),
or is a **single global vector** enough (Carroll's actual calibration produces
one global Carroll-6 set)? The per-cell class strictly *contains* the global one.
We define both and put them through the identical loss.
"""),
    code(r"""
class TinyDINN(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(1, 8, kernel_size=1), torch.nn.Tanh(),
            torch.nn.Conv2d(8, 8, kernel_size=1), torch.nn.Tanh(),
            torch.nn.Conv2d(8, 6, kernel_size=1),
        )
    def forward(self, env):
        return self.net(env)  # [B, 6, H, W] unbounded

bounds = PARAM_BOUNDS.to(DEVICE)
LR, N_EPOCHS = 5e-3, 400

def train_percell(seed, n_epochs=N_EPOCHS):
    torch.manual_seed(seed)
    net = TinyDINN().to(DEVICE)
    opt = torch.optim.Adam(net.parameters(), lr=LR)
    hist = []
    for _ in range(n_epochs):
        params = bounded_params(net(sst_z), bounds, param_axis=1).squeeze(0)  # [6,H,W]
        pred = forward_box(params)
        pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
        loss = ((pred_z - target_z) ** 2).mean()                              # z-scored PATTERN loss
        loss.backward(); opt.step(); opt.zero_grad(); hist.append(loss.item())
    with torch.no_grad():
        params = bounded_params(net(sst_z), bounds, param_axis=1).squeeze(0)
    return params.detach(), hist

def train_global(seed, n_epochs=N_EPOCHS):
    torch.manual_seed(seed)
    raw_g = torch.zeros(6, device=DEVICE, requires_grad=True)                 # ONE vector, no spatial variation
    opt = torch.optim.Adam([raw_g], lr=LR)
    hist = []
    for _ in range(n_epochs):
        params = bounded_params(raw_g, bounds).view(6, 1, 1).expand(6, H, W)
        pred = forward_box(params)
        pred_z = (pred - pred.mean()) / (pred.std() + 1e-8)
        loss = ((pred_z - target_z) ** 2).mean()
        loss.backward(); opt.step(); opt.zero_grad(); hist.append(loss.item())
    with torch.no_grad():
        params = bounded_params(raw_g, bounds).view(6, 1, 1).expand(6, H, W)
    return params.detach(), hist

print("TinyDINN params:", sum(p.numel() for p in TinyDINN().parameters()),
      "| global-scalar: 6 free parameters")
"""),
    md(r"""
## 6. Lesson 1 — capacity: per-cell fits the pattern, a global scalar cannot

Same target, same optimiser, same epochs; only the parameter source differs.
"""),
    code(r"""
pc_params, pc_hist = train_percell(0)
g_params, g_hist = train_global(0)
print(f"per-cell DINN  final loss: {pc_hist[-1]:.5f}")
print(f"global scalar  final loss: {g_hist[-1]:.5f}   (ratio {g_hist[-1]/max(pc_hist[-1],1e-12):.0f}x)")

fig, ax = plt.subplots(1, 1, figsize=(8, 3))
ax.semilogy(pc_hist, label=f"per-cell DINN (final {pc_hist[-1]:.4f})")
ax.semilogy(g_hist, label=f"global scalar (final {g_hist[-1]:.4f})")
ax.set_xlabel("Epoch"); ax.set_ylabel("z-scored pattern loss (log)")
ax.set_title("Lesson 1 — per-cell fits the spatially-varying target; global scalar is pinned at the variance floor")
ax.legend(); ax.grid(alpha=0.3); plt.tight_layout(); plt.show()
print("The global scalar produces an identical value at every cell -> no spatial pattern -> "
      "a z-scored PATTERN loss has no gradient for it. Per-cell has the capacity; global does not.")
"""),
    md(r"""
## 7. Lesson 2 — fitting ≠ identifying (equifinality)

The per-cell DINN drove the loss near zero. Did it recover the *true* `alpfe`
field? Below we re-fit from several random seeds and report the **signed**
Pearson correlation of the recovered `alpfe` against the truth. If the **sign
flips across seeds**, the network found *different* parameter fields that fit the
same observable equally well — the parameter is **not identified**, no matter how
low the loss.
"""),
    code(r"""
SEEDS = [0, 1, 2, 3, 4]
def r_signed(field, true_flat):
    a = field.flatten().cpu().numpy()
    return float("nan") if np.std(a) < 1e-9 else float(np.corrcoef(a, true_flat)[0, 1])

rows = []
for s in SEEDS:
    p, h = train_percell(s, n_epochs=300)
    rows.append((s, h[-1], r_signed(p[0], alpfe_true), r_signed(p[2], smallgrow_true), p))
print(f"{'seed':>4} {'loss':>10} {'alpfe r':>9} {'Smallgrow r':>12}")
for s, l, ra, rs, _ in rows:
    print(f"{s:>4} {l:>10.2e} {ra:>+9.2f} {rs:>+12.2f}")
alpfe_rs = [r[2] for r in rows]
print(f"\nalpfe sign across seeds: {['+' if r > 0 else '-' for r in alpfe_rs]}  "
      f"(|r| mean {np.mean(np.abs(alpfe_rs)):.2f})")
print("Strong |r| but a coin-flip sign = equifinality: the biomass observable does not "
      "pin alpfe's direction.")
"""),
    code(r"""
# Visualise the equifinality: the recovered alpfe field for the first 3 seeds vs truth.
fig, axes = plt.subplots(1, 4, figsize=(15, 3))
ims = [(truth[0].cpu(), "Truth alpfe")]
for s, _, ra, _, p in rows[:3]:
    ims.append((p[0].cpu(), f"seed {s} recovered (r={ra:+.2f})"))
for ax, (img, title) in zip(axes, ims):
    im = ax.imshow(img, aspect="auto", origin="lower", cmap="viridis")
    ax.set_title(title, fontsize=10); plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout(); plt.show()
print("Different seeds recover different alpfe fields (some the mirror image of truth) — "
      "all fitting the same target. That is non-identifiability, shown directly.")
"""),
    md(r"""
## 8. Lesson 3 — identifiability is parameter-specific

Notice in the table that `Smallgrow` tends to track its truth more consistently
than `alpfe`. `Smallgrow` (small-phytoplankton growth rate) has a fairly direct,
monotonic effect on biomass, so the observable constrains it; `alpfe` (iron
solubility) acts indirectly through the iron→growth chain and trades off against
other parameters, so its direction is under-determined. **Which** parameters a
given observation can identify is not all-or-nothing — it is exactly what the
full study characterises.
"""),
    md(r"""
## 9. Interpretation — what this means for the real project

- **The differentiable method works** — autograd traces gradients through 150
  box steps to the parameters, for both the per-cell and global classes.
- **Per-cell has representational capacity a global scalar lacks** (Lesson 1) —
  necessary to express any spatial parameter variation.
- **But fitting the observable does not identify the parameters** (Lesson 2): the
  per-cell DINN reaches ~zero loss while recovering `alpfe` with an arbitrary
  sign across seeds. Capacity ≠ identifiability.
- **Identifiability is parameter-specific** (Lesson 3) and depends on how directly
  the observation constrains each parameter — which is why the real project uses
  **distinct absolute anchors for distinct parameters** (GEOTRACES dissolved iron
  for the iron pair; Daniels/MODIS calcite for `R_PICPOC`), rather than
  pattern-matching one field.

Two facts from the full study this in-memory demo cannot show, but that sharpen
the same point: against real ECCO-Darwin the 0-D box **homogenizes** (tracer
spatial CV → ~1e-15), so the box's *own* spatial pattern carries little
information and identifiability rests on real **absolute** anchors; and the growth
pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real
growth-rate data). The honest target is the **4 observable parameters**.

A note on scope: here the truth varies in space *by construction*, which is what
lets the per-cell class help at all. ECCO-Darwin's Carroll-6 parameters were
calibrated as **global constants**, so whether the per-cell predictor is
*load-bearing for the real problem* is an open question — tested directly by the
project's full **per-cell-vs-global ablation** (real anchors, multi-AOI, n≥10,
`verify_run.py`-gated). See
[STATUS.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/STATUS.md) and
[docs/findings/index.md](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/docs/findings/index.md).
"""),
]


NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py", "mimetype": "text/x-python", "name": "python",
            "nbconvert_exporter": "python", "pygments_lexer": "ipython3", "version": "3.11",
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
