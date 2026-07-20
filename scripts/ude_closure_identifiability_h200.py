#!/usr/bin/env python3
"""2x2 closure-identifiability ablation for the Track-2 UDE (structure x excitation).

Tests the recipe in docs/research_notes/2026-07-06_ude_closure_identifiability_recipe.md
against the equifinality measured on night 1 (trajectory MSE dropped ~10,000x yet the
learned closure had ~293% error). Four arms x K seeds; the between-seed ensemble std at
each DFe IS the per-input identifiability band (function-space analog of the Track-1
Fisher/profile diagnostics).

  A  free MLP,       single-IC, final-state loss   (the failing baseline)
  B  Monod-anchored, single-IC, final-state loss   (structure only)
  C  free MLP,       multi-IC,  snapshot loss       (excitation only)
  D  Monod-anchored, multi-IC,  snapshot loss       (structure + excitation)

Reported per arm: on-visited-support closure error (headline), off-support error
(labeled -- unfixable by loss), ensemble std, trajectory loss (only to show the
decoupling). JSON-logged, resumable via .done markers; drop STOP to halt.

Usage: python scripts/ude_closure_identifiability_h200.py --out-dir runs/ude_ident [--quick]
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.carroll6 import K_FE, LIGHT, PHI_DUST
from darwindiff.integrators import integrate
from darwindiff.transport import column_tendency


def _true_ffe(dfe: torch.Tensor) -> torch.Tensor:
    return (dfe / (dfe + 8.0e-5)) ** 0.7


# Fisher-optimal excitation (drawdown_pulse, winner of ude_forcing_design):
# strong seasonal light + low/pulsed dust draws DFe down through the half-sat k.
_PULSE_T = [120.0, 300.0, 500.0, 640.0]


def _dust_m(t: float) -> float:
    v = 0.2 * math.exp(1.2 * math.sin(2 * math.pi * t / 365.0))
    for tp in _PULSE_T:
        v *= 1.0 - 0.9 * math.exp(-((t - tp) / 15.0) ** 2)
    return v


def _light_m(t: float) -> float:
    return math.exp(2.5 * math.sin(2 * math.pi * t / 365.0))


class FreeMLP(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 16), nn.Tanh(),
                                 nn.Linear(16, 1), nn.Sigmoid())

    def forward(self, dfe):
        return self.net(dfe.unsqueeze(-1)).squeeze(-1)


class MonodAnchored(nn.Module):
    """g(DFe) = [DFe/(DFe+k)] * (1 + eps*tanh(NN(feat))), k learnable ~ K_FE."""

    def __init__(self, eps: float = 0.25):
        super().__init__()
        self.log_k = nn.Parameter(torch.tensor(math.log(K_FE)))
        self.net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1), nn.Tanh())
        self.eps = eps

    def forward(self, dfe):
        k = torch.exp(self.log_k)
        monod = dfe / (dfe + k)
        feat = torch.log10(dfe.clamp_min(1e-9)) + 4.0  # ~O(1) over our DFe range
        corr = 1.0 + self.eps * self.net(feat.unsqueeze(-1)).squeeze(-1)
        return (monod * corr).clamp(0.0, 1.0)


def _make_ic(n_cols, n_z, device, multi, seed):
    g = torch.Generator(device="cpu").manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    f = base * (1.0 + 0.1 * torch.rand(n_cols, n_z, 5, generator=g))
    if multi:  # spread initial DFe 0.1x-10x across columns -> wider visited support
        f[..., 0] = f[..., 0] * torch.logspace(-1, 1, n_cols).reshape(n_cols, 1)
    return f.to(device)


def _visited_range(traj):
    dfe = traj[..., 0].flatten()
    lo = torch.quantile(dfe, 0.02).clamp_min(1e-8).item()
    hi = torch.quantile(dfe, 0.98).clamp_min(1e-7).item()
    return lo, hi


def _train_seed(closure_cls, excite, seed, n_cols, n_z, ns, epochs, device):
    """excite in {'single', 'multi_ic', 'regime'}. 'regime' = spatially
    heterogeneous forcing (per-column iron-dust input via alpfe) so columns reach
    *different equilibria* -> the shared closure sees a range of DFe at steady
    state (robust support), the multi-AOI lesson applied to the closure."""
    torch.manual_seed(seed)
    forced = (excite == "forced")
    if forced:                       # seasonal drawdown needs a long span; the snapshot
        n_cols = min(n_cols, 250)    # loss keeps the full graph, so bound the grid,
        ns = ns * 4                  # span the cycle, and cap epochs (each is 4x longer)
        epochs = min(epochs, 120)
    base = carroll6.CARROLL_VALUES.to(device)
    if excite == "regime":
        params = base.reshape(1, 1, 6).repeat(n_cols, 1, 1).clone()  # [n_cols,1,6]
        params[:, 0, carroll6.P.alpfe] = torch.logspace(
            math.log10(0.2), math.log10(1.0), n_cols, device=device)
    else:
        params = base
    f0 = _make_ic(n_cols, n_z, device, excite == "multi_ic", seed)
    snaps = list(range(ns // 10, ns + 1, ns // 10)) if excite != "single" else None

    def tend_with(ffe):
        if forced:  # Fisher-optimal drawdown_pulse forcing (time-aware tendency)
            def tf(tt, s):
                return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe,
                                       dust=PHI_DUST * _dust_m(tt), light=LIGHT * _light_m(tt))
            return tf
        def t(s):
            return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe)
        return t

    with torch.no_grad():
        target = integrate(tend_with(_true_ffe), f0, dt=0.25, n_steps=ns, method="rk4",
                           snapshot_indices=snaps)
    net = closure_cls().to(device)
    opt = torch.optim.Adam(net.parameters(), lr=5e-3)
    last = float("nan")
    for _ in range(epochs):
        opt.zero_grad()
        pred = integrate(tend_with(net), f0, dt=0.25, n_steps=ns, method="rk4",
                         snapshot_indices=snaps,
                         checkpoint_segment=(None if snaps else 50))
        loss = (pred - target).pow(2).mean()
        loss.backward()
        opt.step()
        last = loss.item()

    with torch.no_grad():  # support = DFe realized by the true dynamics along the way
        dense = integrate(tend_with(_true_ffe), f0, dt=0.25, n_steps=ns, method="rk4",
                          snapshot_indices=list(range(1, ns + 1, max(1, ns // 20))))
    lo, hi = _visited_range(dense)
    return net, last, lo, hi


def run_arm(out, tag, closure_cls, excite, seeds, n_cols, n_z, ns, epochs, device):
    if (out / f".done_{tag}").exists() or (out / "STOP").exists():
        return
    nets, losses, los, his = [], [], [], []
    for s in seeds:
        net, loss, lo, hi = _train_seed(closure_cls, excite, s, n_cols, n_z, ns, epochs, device)
        nets.append(net)
        losses.append(loss)
        los.append(lo)
        his.append(hi)
        print(f"[{tag}] seed {s}: traj_loss={loss:.2e} visited=[{lo:.2e},{hi:.2e}]", flush=True)

    lo, hi = min(los), max(his)
    grid = torch.logspace(math.log10(lo), math.log10(hi), 120, device=device)
    off = torch.logspace(-6, -3, 120, device=device)
    with torch.no_grad():
        preds = torch.stack([n(grid) for n in nets])       # [K, 120]
        off_preds = torch.stack([n(off) for n in nets])
    true = _true_ffe(grid)
    true_off = _true_ffe(off)
    ens_mean = preds.mean(0)
    per_seed_err = [((p - true).abs() / true.clamp_min(1e-8)).mean().item() for p in preds]
    rec = {
        "arm": tag, "closure": closure_cls.__name__, "excite": excite,
        "n_seeds": len(seeds), "n_cols": n_cols, "n_z": n_z, "n_steps": ns, "epochs": epochs,
        "status": "ok", "visited_dfe": [lo, hi],
        "on_support_ensemble_err": ((ens_mean - true).abs() / true.clamp_min(1e-8)).mean().item(),
        "on_support_per_seed_err_mean": sum(per_seed_err) / len(per_seed_err),
        "on_support_per_seed_err": [round(e, 4) for e in per_seed_err],
        "ensemble_std_mean": preds.std(0).mean().item(),
        "off_support_ensemble_err": ((off_preds.mean(0) - true_off).abs()
                                     / true_off.clamp_min(1e-8)).mean().item(),
        "traj_loss_mean": sum(losses) / len(losses),
    }
    (out / f"{tag}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    (out / f".done_{tag}").touch()
    print(f"[{tag}] DONE on-support(ens)={rec['on_support_ensemble_err']:.3f} "
          f"per-seed={rec['on_support_per_seed_err_mean']:.3f} "
          f"ens-std={rec['ensemble_std_mean']:.3f} "
          f"off-support={rec['off_support_ensemble_err']:.3f} "
          f"traj={rec['traj_loss_mean']:.2e}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    (out / "device_info.json").write_text(json.dumps({
        "device": device.type,
        "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
        "torch": torch.__version__}, indent=1), encoding="utf-8")

    K = 2 if args.quick else 4
    seeds = list(range(K))
    n_cols, n_z, ns, epochs = (300, 6, 100, 100) if args.quick else (1000, 8, 300, 300)

    arms = [
        ("A_free_singleIC", FreeMLP, "single"),
        ("B_monod_singleIC", MonodAnchored, "single"),
        ("C_free_multiIC", FreeMLP, "multi_ic"),
        ("D_monod_multiIC", MonodAnchored, "multi_ic"),
        ("E_free_regime", FreeMLP, "regime"),
        ("F_monod_regime", MonodAnchored, "regime"),
        ("G_free_forced", FreeMLP, "forced"),
        ("H_monod_forced", MonodAnchored, "forced"),
    ]
    for tag, cls, excite in arms:
        run_arm(out, tag, cls, excite, seeds, n_cols, n_z, ns, epochs, device)
    print("ABLATION COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
