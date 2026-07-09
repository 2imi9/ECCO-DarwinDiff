"""Validate the symbolic-distillation gate against the *real* closure-training
pipeline (not just analytic closures) -- CPU, synthetic self-twin.

The gate (``scripts/symbolic_distill_probe.py``) was unit-tested on closures with
known analytic laws. This probe closes the loop: it trains a ``MonodAnchored``
closure **through the differentiable box dynamics** (``transport.column_tendency``
+ ``integrators.integrate``, exactly as the H200 arms do) under two excitation
regimes, then runs the gate on each trained NN:

  * narrow   -- single-IC, no forcing: the closure sees a *thin* DFe support that
                never spans the half-saturation knee (the Night-1 equifinality
                regime). Expected verdict: DISTILL-FAIL (aliased / non-identifiable).
  * excited  -- multi-IC DFe spread + seasonal light/dust drawdown forcing: the
                closure is driven through the knee within the trajectory (the
                Night-1 cure). Expected verdict: DISTILL-PASS.

This turns the qualitative Night-1 finding ("closure equifinality is a support
problem; excitation cures it") into a quantitative, gate-checked demonstration on
the actual pipeline. It is a **synthetic self-twin methods demonstration on the
0-D/1-column box, NOT a real-Darwin or real-biology claim** (Track-2-feasibility
guardrail).

Run: ``python scripts/symbolic_distill_dynamics_probe.py`` (CPU, ~5-10 min).
Writes ``docs/findings/symbolic_distill_dynamics_probe.json``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.carroll6 import K_FE, LIGHT, PHI_DUST
from darwindiff.integrators import integrate
from darwindiff.transport import column_tendency

# Load the gate module by path (it lives under scripts/, not an installed package).
_GATE_PATH = Path(__file__).resolve().parent / "symbolic_distill_probe.py"
_spec = importlib.util.spec_from_file_location("symbolic_distill_probe", _GATE_PATH)
sd = importlib.util.module_from_spec(_spec)
sys.modules["symbolic_distill_probe"] = sd
_spec.loader.exec_module(sd)


# --------------------------------------------------------------------------- #
# The closure under test and the true (synthetic) law it is fit against
# --------------------------------------------------------------------------- #

def _true_ffe(dfe: torch.Tensor) -> torch.Tensor:
    """Synthetic ground-truth iron limitation (the harder Monod^0.7 twin used in
    the H200 arms; a pure-Monod fit recovers an effective half-saturation)."""
    return (dfe / (dfe + 8.0e-5)) ** 0.7


class MonodAnchored(nn.Module):
    """g(DFe) = [DFe/(DFe+k)] * (1 + eps*tanh(NN(feat))), k learnable ~ K_FE.
    Mirrors the closure in scripts/ude_closure_identifiability_h200.py."""

    def __init__(self, eps: float = 0.25):
        super().__init__()
        self.log_k = nn.Parameter(torch.tensor(math.log(K_FE)))
        self.net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 1), nn.Tanh())
        self.eps = eps

    def forward(self, dfe):
        k = torch.exp(self.log_k)
        monod = dfe / (dfe + k)
        feat = torch.log10(dfe.clamp_min(1e-9)) + 4.0
        corr = 1.0 + self.eps * self.net(feat.unsqueeze(-1)).squeeze(-1)
        return (monod * corr).clamp(0.0, 1.0)


# --------------------------------------------------------------------------- #
# Seasonal drawdown forcing (excited regime) -- pushes DFe through the knee
# --------------------------------------------------------------------------- #

_PULSE_T = [120.0, 300.0, 500.0, 640.0]


def _dust_m(t: float) -> float:
    v = 0.2 * math.exp(1.2 * math.sin(2 * math.pi * t / 365.0))
    for tp in _PULSE_T:
        v *= 1.0 - 0.9 * math.exp(-((t - tp) / 15.0) ** 2)
    return v


def _light_m(t: float) -> float:
    return math.exp(2.5 * math.sin(2 * math.pi * t / 365.0))


# --------------------------------------------------------------------------- #
# Initial conditions + tendency builders per regime
# --------------------------------------------------------------------------- #

def _make_ic(n_cols: int, n_z: int, seed: int, spread: bool) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    f = base * (1.0 + 0.1 * torch.rand(n_cols, n_z, 5, generator=g))
    if spread:  # 0.1x-10x DFe across columns -> wide steady-state support
        f[..., 0] = f[..., 0] * torch.logspace(-1, 1, n_cols).reshape(n_cols, 1)
    return f


def _tendency(ffe, params, forced: bool):
    if forced:
        def tf(tt, s):
            return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe,
                                   dust=PHI_DUST * _dust_m(tt), light=LIGHT * _light_m(tt))
        return tf

    def t(s):
        return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe)
    return t


# --------------------------------------------------------------------------- #
# Train one closure through the box, return the trained net + visited DFe support
# --------------------------------------------------------------------------- #

def train_and_gather(regime: str, seed: int, n_cols: int, n_z: int, ns: int,
                     epochs: int, lr: float = 5e-3) -> tuple[nn.Module, np.ndarray, float]:
    torch.manual_seed(seed)
    spread = regime == "excited"
    forced = regime == "excited"
    params = carroll6.CARROLL_VALUES
    f0 = _make_ic(n_cols, n_z, seed, spread)
    snaps = list(range(ns // 10, ns + 1, ns // 10))

    target = integrate(_tendency(_true_ffe, params, forced), f0, dt=0.25, n_steps=ns,
                       method="rk4", snapshot_indices=snaps).detach()

    net = MonodAnchored()
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    last = float("nan")
    for _ in range(epochs):
        opt.zero_grad()
        pred = integrate(_tendency(net, params, forced), f0, dt=0.25, n_steps=ns,
                         method="rk4", snapshot_indices=snaps)
        loss = ((pred - target) ** 2).mean()
        loss.backward()
        opt.step()
        last = float(loss.item())

    # Visited DFe support: DFe (tracer 0) across the eval trajectory + all columns.
    with torch.no_grad():
        traj = integrate(_tendency(net, params, forced), f0, dt=0.25, n_steps=ns,
                         method="rk4", snapshot_indices=snaps)
        dfe = traj[..., 0].reshape(-1)
        dfe = dfe[dfe > 0].cpu().numpy()
    return net, dfe, last


# --------------------------------------------------------------------------- #
# Probe
# --------------------------------------------------------------------------- #

def run(seeds=(0, 1), n_cols=48, n_z=1, ns=160, epochs=150) -> dict:
    out: dict = {"config": {"seeds": list(seeds), "n_cols": n_cols, "n_z": n_z,
                            "ns": ns, "epochs": epochs, "dt_days": 0.25},
                 "regimes": {}}
    for regime in ("narrow", "excited"):
        arm = {"seeds": []}
        for s in seeds:
            net, dfe, loss = train_and_gather(regime, s, n_cols, n_z, ns, epochs)
            y = sd.sample_closure(net, dfe)
            v = sd.distill(dfe, y, seed=s)
            span = float(np.log10(dfe.max()) - np.log10(dfe.min())) if dfe.size else 0.0
            rec = {
                "seed": s, "train_loss": loss,
                "n_visited": int(dfe.size),
                "dfe_min": float(dfe.min()), "dfe_max": float(dfe.max()),
                "log10_span": span,
                "learned_k": float(math.exp(net.log_k.item())),
                "passed": bool(v.passed), "reason": v.reason,
                "monod_inclusion": v.monod_inclusion, "k_hat": v.k_hat,
                "monod_linear_alias": v.monod_linear_alias, "r2_holdout": v.r2_holdout,
            }
            arm["seeds"].append(rec)
            tag = "PASS" if v.passed else "FAIL"
            print(f"[{regime:<7} s{s}] [{tag}] loss={loss:.2e} visited={dfe.size} "
                  f"span={span:.2f}dex k_hat={v.k_hat:.2e} alias={v.monod_linear_alias:.3f}")
            print(f"            {v.reason}")
        arm["n_pass"] = sum(r["passed"] for r in arm["seeds"])
        out["regimes"][regime] = arm

    narrow_pass = out["regimes"]["narrow"]["n_pass"]
    excited_pass = out["regimes"]["excited"]["n_pass"]
    n = len(seeds)
    # The demonstration: excitation should lift the gate verdict from FAIL to PASS.
    out["demonstration"] = {
        "narrow_pass": narrow_pass, "excited_pass": excited_pass, "n_seeds": n,
        "excitation_cures_equifinality": bool(narrow_pass < excited_pass),
    }
    print(f"\n== excitation ladder via the gate: narrow {narrow_pass}/{n} PASS "
          f"-> excited {excited_pass}/{n} PASS ==")
    print("   " + ("excitation lifts the gate verdict (support problem confirmed)"
                   if narrow_pass < excited_pass else
                   "no lift observed at this budget -- inspect spans / increase excitation"))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--seeds", type=int, nargs="+", default=[0, 1])
    ap.add_argument("--n-cols", type=int, default=48)
    ap.add_argument("--ns", type=int, default=160)
    ap.add_argument("--epochs", type=int, default=150)
    ap.add_argument("--out", type=str,
                    default="docs/findings/symbolic_distill_dynamics_probe.json")
    args = ap.parse_args()
    torch.set_num_threads(max(1, torch.get_num_threads()))
    result = run(seeds=tuple(args.seeds), n_cols=args.n_cols, ns=args.ns,
                 epochs=args.epochs)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
