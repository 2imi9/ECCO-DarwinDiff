#!/usr/bin/env python
"""column_ude_sparse_probe.py -- WHERE does growth-pair identifiability break as
observations get sparse? (the honest follow-up to column_ude_probe.py)

The full-observation self-twin recovered the growth pair even at constant light,
so growth blindness is a DATA limit, not a dynamics limit. This probe maps that:
it profiles Smallgrow and alpfe under progressively sparser observations and
watches which parameter's profile well collapses to flat (unidentifiable).

Observation ablation (all under seasonal light):
  full            : DFe+POC+PIC, all levels, 15-d cadence   (rich)
  surface_3tracer : DFe+POC+PIC, surface only, 15-d
  iron_all_levels : DFe only,    all levels, 15-d           (GEOTRACES-like)
  iron_surf_sparse: DFe only,    surface only, 60-d         (real-data-sparse)

Run: python scripts/column_ude_sparse_probe.py   (CPU, profile-only, ~1 min)
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import torch
import darwindiff.carroll6 as c
from column_ude_probe import column_step, light_field, CARROLL, PN, Z, DT, YEAR

torch.manual_seed(0)
AMP = 0.8  # seasonal light


def rollout_masked(params, levels, tracer_idx, stride_days, years=3):
    state = torch.stack([
        torch.full((Z,), 2e-5), torch.full((Z,), 0.1), torch.full((Z,), 0.1),
        torch.full((Z,), 0.1),  torch.full((Z,), 0.01),
    ])
    n = int(years * YEAR / DT)
    obs_start = int((years - 1) * YEAR / DT)
    stride = max(1, int(stride_days / DT))
    lev = torch.tensor(levels)
    tr = torch.tensor(tracer_idx)
    obs = []
    for k in range(n):
        state = column_step(state, params, DT, light_field(k * DT, AMP))
        if k >= obs_start and (k % stride == 0):
            obs.append(state[tr][:, lev])          # [n_tracer, n_level]
    return torch.stack(obs)                          # [T, n_tracer, n_level]


def loss_masked(theta, truth, levels, tracer_idx, stride):
    pred = rollout_masked(theta * CARROLL, levels, tracer_idx, stride)
    sd = truth.std(dim=(0, 2), keepdim=True).clamp(min=1e-12)
    return float((((pred - truth) / sd) ** 2).mean())


def profile_well(pname, truth, levels, tracer_idx, stride, span=0.6, npts=13):
    pidx = PN.index(pname)
    losses = []
    for m in torch.linspace(1 - span, 1 + span, npts):
        theta = torch.ones(6); theta[pidx] = m
        with torch.no_grad():
            losses.append(loss_masked(theta, truth, levels, tracer_idx, stride))
    return max(losses) - min(losses)                 # well depth; ~0 => flat/unidentifiable


CONFIGS = [
    ("full",             list(range(Z)), [0, 3, 4], 15),   # DFe,POC,PIC all levels
    ("surface_3tracer",  [0],            [0, 3, 4], 15),
    ("iron_all_levels",  list(range(Z)), [0],       15),   # DFe only
    ("iron_surf_sparse", [0],            [0],       60),   # DFe only, sparse
]
FLAT = 1e-3


def main():
    truth_params = CARROLL
    print("Sparse-observation ablation (seasonal light) -- profile well depth "
          "(larger=identifiable, ~0=flat)\n")
    print("  %-18s %-14s %-14s %-14s" % ("obs config", "Smallgrow", "Biggrow", "alpfe"))
    result = {}
    for name, lev, tr, stride in CONFIGS:
        truth = rollout_masked(truth_params, lev, tr, stride)
        ws = profile_well("Smallgrow", truth, lev, tr, stride)
        wb = profile_well("Biggrow",   truth, lev, tr, stride)
        wa = profile_well("alpfe",     truth, lev, tr, stride)
        tag = lambda w: "FLAT" if w < FLAT else "%.2e" % w
        print("  %-18s %-14s %-14s %-14s" % (name, tag(ws), tag(wb), tag(wa)))
        result[name] = {"Smallgrow": ws, "Biggrow": wb, "alpfe": wa,
                        "Smallgrow_flat": ws < FLAT, "alpfe_flat": wa < FLAT}
    # verdict: does growth collapse while iron survives under sparse iron-only obs?
    sp = result["iron_surf_sparse"]
    print("\nVERDICT (iron_surf_sparse, the real-data-like case):")
    print("  Smallgrow %s ; alpfe %s" % (
        "COLLAPSED (unidentifiable)" if sp["Smallgrow"] < 100 * FLAT else "still identifiable",
        "COLLAPSED" if sp["alpfe"] < 100 * FLAT else "still identifiable"))
    print("  => growth needs POC/PIC-type obs; iron survives iron-only obs"
          if sp["Smallgrow"] < sp["alpfe"] else "  => unexpected: iron collapsed too")
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "findings", "column_ude_sparse_probe.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out, "w"), indent=2)
    print("\nwrote", out)


if __name__ == "__main__":
    main()
