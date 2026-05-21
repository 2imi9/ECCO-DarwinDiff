"""Logic for the Colab demo notebook (notebooks/demo_colab.ipynb).

This file is the testable Python version of the demo. Run it locally to
verify the synthetic-recovery demo works end-to-end. The .ipynb is
generated from this with cell markers, but keeping a .py copy lets us
run pytest-style verification.

Synthetic-recovery demo: pick known Carroll-6 truth values that vary
smoothly across a synthetic AOI grid; forward-integrate the box model to
generate a steady-state biomass field; train a DINN to recover the
per-cell truth from a single environmental channel (synthetic SST).

Validates the structural-ceiling premise of DarwinDiff in ~5 minutes
without needing real Darwin / GLODAP / GEOTRACES data.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

# Add src/ to path so we can import without pip install (matches Colab pattern).
HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from darwindiff.carroll6 import (  # noqa: E402
    CARROLL_VALUES,
    PARAM_BOUNDS,
    PARAM_NAMES,
    bounded_params,
    carroll6_integrate,
)


# ============================================================================
# Configuration
# ============================================================================
H, W = 8, 16                        # synthetic AOI grid (small for fast demo)
N_STEPS = 200                       # box-model spin-up steps
DT = 0.25                           # day per step
N_TRAIN_EPOCHS = 800                # DINN training epochs (smaller than 1500 for demo speed)
LR = 5e-3
SEED = 0
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


def make_synthetic_aoi() -> torch.Tensor:
    """Synthetic SST gradient as the environmental input channel.

    Returns:
        Tensor of shape [1, 1, H, W], z-scored (zero mean, unit variance).
    """
    sst = torch.linspace(-2.0, 2.0, H).unsqueeze(1) * torch.ones(1, W)
    sst = sst.unsqueeze(0).unsqueeze(0)  # [1, 1, H, W]
    sst_z = (sst - sst.mean()) / (sst.std() + 1e-8)
    return sst_z.to(DEVICE)


def make_truth_params(sst_z: torch.Tensor) -> torch.Tensor:
    """Per-cell ground-truth Carroll-6 vector that varies smoothly with SST.

    `alpfe` increases with SST (warm-water iron-dust proxy); `Smallgrow`
    decreases with SST. The other four params are fixed at Carroll's
    published optima.

    Args:
        sst_z: shape [1, 1, H, W], z-scored input.

    Returns:
        Shape [6, H, W] in physical units (bounded by PARAM_BOUNDS).
    """
    sst_norm = (sst_z - sst_z.min()) / (sst_z.max() - sst_z.min() + 1e-8)
    sst_norm = sst_norm.squeeze(0).squeeze(0)  # [H, W]

    bounds = PARAM_BOUNDS.to(DEVICE)
    carroll = CARROLL_VALUES.to(DEVICE)

    # alpfe: 0.30 (cold) -> 0.95 (warm)
    alpfe = bounds[0, 0] + sst_norm * (bounds[0, 1] - bounds[0, 0])
    alpfe = 0.30 + sst_norm * (0.95 - 0.30)

    # Smallgrow: 0.30 (warm) -> 1.20 (cold)
    smallgrow = 1.20 - sst_norm * (1.20 - 0.30)

    params = torch.zeros(6, H, W, device=DEVICE)
    params[0] = alpfe
    params[1] = carroll[1]    # scav_rat at Carroll's published
    params[2] = smallgrow
    params[3] = carroll[3]    # Biggrow at Carroll's
    params[4] = carroll[4]    # diatomgraz at Carroll's
    params[5] = carroll[5]    # R_PICPOC at Carroll's
    return params


def forward_box(params: torch.Tensor) -> torch.Tensor:
    """Forward-integrate the Carroll-6 box model per cell, vectorized.

    Args:
        params: shape [6, H, W] in physical units.

    Returns:
        Steady-state phytoplankton biomass (Ps + Pl), shape [H, W].
    """
    h, w = params.shape[1], params.shape[2]
    # Broadcast initial state to [5, H, W]
    state = torch.stack([
        torch.full((h, w), 0.5e-3, device=params.device),  # DFe
        torch.full((h, w), 0.05, device=params.device),    # Ps
        torch.full((h, w), 0.05, device=params.device),    # Pl
        torch.full((h, w), 0.1, device=params.device),     # POC
        torch.full((h, w), 0.001, device=params.device),   # PIC
    ])

    # carroll6_step is elementwise on state/params, so [5, H, W] + [6, H, W]
    # broadcasts naturally to produce [5, H, W] output.
    from darwindiff.carroll6 import carroll6_step
    for _ in range(N_STEPS):
        state = carroll6_step(state, params, DT)
    return state[1] + state[2]  # Ps + Pl, shape [H, W]


def zscore(x: torch.Tensor) -> torch.Tensor:
    """Standardize over all valid cells."""
    return (x - x.mean()) / (x.std() + 1e-8)


class TinyDINN(torch.nn.Module):
    """Minimal per-cell 1x1-conv DINN matching the project's architectural
    commitment. Takes a single env channel (z-scored SST), outputs 6 raw
    parameter values per cell that are sigmoid-bounded into PARAM_BOUNDS.

    Hidden width 8 for demo speed; production DINN/DINNDeep are 16 / 32+.
    """

    def __init__(self) -> None:
        super().__init__()
        self.net = torch.nn.Sequential(
            torch.nn.Conv2d(1, 8, kernel_size=1),
            torch.nn.Tanh(),
            torch.nn.Conv2d(8, 8, kernel_size=1),
            torch.nn.Tanh(),
            torch.nn.Conv2d(8, 6, kernel_size=1),
        )

    def forward(self, env: torch.Tensor) -> torch.Tensor:
        return self.net(env)  # shape [B, 6, H, W]


def train_dinn(
    sst_z: torch.Tensor,
    target_field: torch.Tensor,
    n_epochs: int = N_TRAIN_EPOCHS,
) -> tuple[TinyDINN, list[float]]:
    """Train a TinyDINN against the synthetic target field via gradient
    descent through the box model.
    """
    torch.manual_seed(SEED)
    net = TinyDINN().to(DEVICE)
    optim = torch.optim.Adam(net.parameters(), lr=LR)
    bounds = PARAM_BOUNDS.to(DEVICE)
    target_z = zscore(target_field)

    loss_history: list[float] = []
    for epoch in range(n_epochs):
        raw = net(sst_z)                                  # [1, 6, H, W]
        params_b = bounded_params(raw, bounds, param_axis=1)  # [1, 6, H, W]
        params = params_b.squeeze(0)                      # [6, H, W]

        phyto = forward_box(params)
        pred_z = zscore(phyto)

        loss = ((pred_z - target_z) ** 2).mean()
        loss.backward()
        optim.step()
        optim.zero_grad()
        loss_history.append(loss.item())
        if epoch % 200 == 0:
            print(f"  epoch {epoch:4d}  loss={loss.item():.4f}")

    return net, loss_history


def evaluate(
    net: TinyDINN,
    sst_z: torch.Tensor,
    truth_params: torch.Tensor,
) -> dict:
    """Compare recovered per-cell params to truth."""
    bounds = PARAM_BOUNDS.to(DEVICE)
    net.eval()
    with torch.no_grad():
        raw = net(sst_z)                                          # [1, 6, H, W]
        recovered = bounded_params(raw, bounds, param_axis=1).squeeze(0)  # [6, H, W]

    results = {}
    for i, name in enumerate(PARAM_NAMES):
        rec = recovered[i].cpu().numpy().flatten()
        tru = truth_params[i].cpu().numpy().flatten()
        if np.std(tru) < 1e-6:
            # Constant truth: report mean-relative error
            mre = float(np.abs(rec.mean() - tru.mean()) / (np.abs(tru.mean()) + 1e-12))
            results[name] = {"varies": False, "mean_rel_err": mre,
                             "tru_mean": float(tru.mean()),
                             "rec_mean": float(rec.mean())}
        else:
            # Varying truth: per-cell mean absolute error + Pearson r
            mae_rel = float(np.mean(np.abs(rec - tru)) / (np.abs(tru.mean()) + 1e-12))
            r = float(np.corrcoef(rec, tru)[0, 1])
            results[name] = {"varies": True, "mae_rel": mae_rel,
                             "pearson_r": r,
                             "tru_range": (float(tru.min()), float(tru.max())),
                             "rec_range": (float(rec.min()), float(rec.max()))}
    return results


def main():
    print(f"DarwinDiff synthetic-recovery demo (device={DEVICE})")
    print()
    print("Carroll-6 published optima (Carroll 2020 JAMES Table 1):")
    for name, val in zip(PARAM_NAMES, CARROLL_VALUES.tolist()):
        print(f"  {name:12s} = {val:.5g}")
    print()

    print(f"Building synthetic AOI ({H}x{W} grid)...")
    sst_z = make_synthetic_aoi()
    truth = make_truth_params(sst_z)
    print(f"  Truth alpfe varies [{truth[0].min():.3f}, {truth[0].max():.3f}]")
    print(f"  Truth Smallgrow varies [{truth[2].min():.3f}, {truth[2].max():.3f}]")
    print()

    print(f"Forward-integrating box model with truth params...")
    target = forward_box(truth)
    print(f"  Steady-state phyto biomass: [{target.min():.4f}, {target.max():.4f}] mmol C/m^3")
    print(f"  Spatial pattern std: {target.std():.4f}")
    print()

    print(f"Training TinyDINN ({N_TRAIN_EPOCHS} epochs, lr={LR})...")
    net, loss_history = train_dinn(sst_z, target, n_epochs=N_TRAIN_EPOCHS)
    print(f"  Final loss: {loss_history[-1]:.4f}")
    print()

    print("Recovery results vs Carroll-6 truth:")
    results = evaluate(net, sst_z, truth)
    for name, r in results.items():
        if r["varies"]:
            print(f"  {name:12s} VARIES truth=[{r['tru_range'][0]:.3f}, {r['tru_range'][1]:.3f}] "
                  f"rec=[{r['rec_range'][0]:.3f}, {r['rec_range'][1]:.3f}] "
                  f"Pearson_r={r['pearson_r']:.3f}, mae_rel={r['mae_rel']:.3f}")
        else:
            print(f"  {name:12s} CONST  truth={r['tru_mean']:.4g} rec={r['rec_mean']:.4g} "
                  f"rel_err={r['mean_rel_err']:.3f}")
    print()
    print("Done. In Colab, plotting cells render figures alongside this output.")

    return net, loss_history, results


if __name__ == "__main__":
    main()
