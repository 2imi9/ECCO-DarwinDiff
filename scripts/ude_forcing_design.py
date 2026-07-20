#!/usr/bin/env python3
"""Offline Fisher-gated excitation-forcing design for the Track-2 UDE closure.

Night 1 showed closure identifiability is a *support* problem: a near-equilibrium
twin only constrains the iron-limitation closure at one DFe. This probe ranks
candidate time-varying forcings (seasonal dust +/- pulses) by how well the DFe
range they excite would identify the closure -- WITHOUT training. For each
forcing it runs the forced trajectory, collects the visited DFe, and computes the
empirical Fisher information of a parametric Monod design-closure
g(DFe; k, n) = (DFe/(DFe+k))^n over that visited distribution:

    J_i = [dg/dlog_k, dg/dn] at DFe_i     (analytic)
    G   = mean_i J_i J_i^T                (2x2)
    score = lambda_min(G)                 (higher -> both shape params constrained)

We pick the forcing with the largest lambda_min (best-conditioned identifiability)
and widest DFe coverage; only that winner is then trained at scale on an H200.
Cheap enough for a T4/A100 -- no backprop, no optimization.

Usage: python scripts/ude_forcing_design.py --out-dir runs/forcing_design
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import torch

from darwindiff import carroll6
from darwindiff.carroll6 import K_FE, PHI_DUST
from darwindiff.integrators import integrate
from darwindiff.transport import column_tendency

# Candidate forcings: dust(t) = PHI_DUST * exp(a1 sin(2pi t/365) + a2 sin(4pi t/365 + ph))
#                               + pulse train. exp keeps dust positive at any amplitude.
# dust(t) = PHI_DUST * dmean * exp(a1 sin) ; light(t) = LIGHT * exp(bL sin(.. + phL)).
# To identify the iron closure we must DRAW DFe DOWN toward k=K_FE (biological
# uptake via light), not add dust (which pushes DFe up into the saturated regime).
# So the interesting configs pair high light amplitude with a reduced/low dust mean.
FORCINGS = [
    {"name": "const", "dmean": 1.0, "a1": 0.0, "bL": 0.0, "phL": 0.0, "pulse": 0.0},
    {"name": "light_annual", "dmean": 1.0, "a1": 0.0, "bL": 1.2, "phL": 0.0, "pulse": 0.0},
    {"name": "light_strong", "dmean": 1.0, "a1": 0.0, "bL": 2.2, "phL": 0.0, "pulse": 0.0},
    {"name": "drawdown", "dmean": 0.3, "a1": 0.8, "bL": 2.2, "phL": 0.0, "pulse": 0.0},
    {"name": "drawdown_pulse", "dmean": 0.2, "a1": 1.2, "bL": 2.5, "phL": 0.0, "pulse": 3.0},
    {"name": "antiphase", "dmean": 0.5, "a1": 1.2, "bL": 2.2, "phL": math.pi, "pulse": 0.0},
]
_PULSE_TIMES = [120.0, 300.0, 500.0, 640.0]  # low-dust "iron-limitation" episodes
_PULSE_W = 15.0


def _dust_mult(t: float, cfg: dict) -> float:
    val = cfg["dmean"] * math.exp(cfg["a1"] * math.sin(2 * math.pi * t / 365.0))
    if cfg["pulse"] > 0.0:  # episodic dust SHUTOFF (drives drawdown)
        for tp in _PULSE_TIMES:
            val *= 1.0 - 0.9 * math.exp(-((t - tp) / _PULSE_W) ** 2)
    return val


def _light_mult(t: float, cfg: dict) -> float:
    return math.exp(cfg["bL"] * math.sin(2 * math.pi * t / 365.0 + cfg["phL"]))


def _run_forced(cfg, n_cols, n_z, ns, device):
    params = carroll6.CARROLL_VALUES.to(device)
    g = torch.Generator(device="cpu").manual_seed(0)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    f0 = (base * (1.0 + 0.1 * torch.rand(n_cols, n_z, 5, generator=g))).to(device)

    def tend(t, s):
        return column_tendency(s, params, kz=0.1, dz=25.0,
                               dust=PHI_DUST * _dust_mult(t, cfg),
                               light=carroll6.LIGHT * _light_mult(t, cfg))

    snaps = list(range(ns // 40, ns + 1, ns // 40))  # ~40 snapshots over the run
    with torch.no_grad():
        traj = integrate(tend, f0, dt=0.25, n_steps=ns, method="rk4", snapshot_indices=snaps)
    return traj[..., 0].reshape(-1)  # all visited DFe


def _design_fisher(dfe: torch.Tensor):
    """Fisher of the Monod design-closure params over the visited DFe (analytic)."""
    dfe = dfe.clamp_min(1e-9)
    k = torch.tensor(K_FE, device=dfe.device)
    n = 1.0
    m = dfe / (dfe + k)
    g = m ** n
    dg_dlogk = -n * g * k / (dfe + k)          # dg/d(log k)
    dg_dn = g * torch.log(m.clamp_min(1e-12))  # dg/dn
    J = torch.stack([dg_dlogk, dg_dn], dim=-1)  # [M, 2]
    G = (J.unsqueeze(-1) * J.unsqueeze(-2)).mean(0)  # [2,2]
    evals = torch.linalg.eigvalsh(G)
    lam_min = evals[0].item()
    lam_max = evals[-1].item()
    cond = (lam_max / lam_min) if lam_min > 0 else float("inf")
    return lam_min, cond


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    n_cols, n_z, ns = (300, 6, 400) if args.quick else (1000, 8, 730 * 2)  # ~4 yr

    results = []
    for cfg in FORCINGS:
        dfe = _run_forced(cfg, n_cols, n_z, ns, device)
        lo = torch.quantile(dfe, 0.02).clamp_min(1e-9).item()
        hi = torch.quantile(dfe, 0.98).clamp_min(1e-8).item()
        dfe_min = dfe.min().item()
        min_over_k = dfe_min / K_FE  # <~1 means we reached the identifiable half-sat region
        coverage_decades = math.log10(hi / lo) if hi > lo else 0.0
        lam_min, cond = _design_fisher(dfe)
        rec = {"name": cfg["name"], "cfg": cfg, "lambda_min": lam_min, "cond": cond,
               "coverage_decades": round(coverage_decades, 3),
               "visited_dfe": [lo, hi], "dfe_min": dfe_min,
               "min_over_k": round(min_over_k, 3), "n_visited": dfe.numel()}
        results.append(rec)
        print(f"[{cfg['name']:>15}] lambda_min={lam_min:.3e} cov={coverage_decades:.2f}dec "
              f"minDFe/k={min_over_k:.2f} DFe=[{lo:.2e},{hi:.2e}]", flush=True)

    results.sort(key=lambda r: r["lambda_min"], reverse=True)
    winner = results[0]["name"]
    (out / "forcing_design.json").write_text(
        json.dumps({"ranked": results, "winner": winner}, indent=1), encoding="utf-8")
    print(f"\nWINNER (max lambda_min): {winner}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
