"""Independent cross-method validation of Carroll-6 recovery on the 0-D box (#163).

The prior record establishes recovery via the per-cell DINN (autograd through the box) and
characterises identifiability analytically (Fisher/CRLB, profile-likelihood). The MISSING
piece is **method-independence**: is the recovered optimum an artifact of the DINN or of
gradient descent, or does it survive a completely different estimator class?

This probe recovers the Carroll-6 from a box-generated multi-cell target with THREE estimators
of different classes and checks (a) do they AGREE, (b) do they match Carroll, (c) a
profile-likelihood band per parameter (turns "consistent with Carroll" into "identified as
X in [CI]"):

  (A) autograd gradient descent on the raw 6-vector  -- differentiable, but NO DINN
  (B) Nelder-Mead simplex on the raw 6-vector        -- NO gradients, NO autograd, NO NN
  (C) profile-likelihood scan per parameter          -- per-param band + identifiability

Scope (honest): the target is generated at Carroll's params + observation noise (a self-twin
with the box's real sloppiness structure). This validates method-independence and quantifies
identifiability; real-data agreement (GEOTRACES iron) still needs the cluster. If A and B
(independent estimator classes) land on the same point, the recovery is not a DINN/autograd
artifact. Where a parameter is sloppy, the estimators scatter and the profile band is wide --
that is the honest signal, not a bug.

All restarts and the whole profile grid are batched into single box forwards (a trailing batch
dim is free), so the whole probe runs in ~1 min on CPU.

Findings (5-tracer proxy self-twin, 2026-07-03):
  * METHOD-INDEPENDENCE HOLDS: gradient descent (A) and gradient-free Nelder-Mead (B) --
    completely different estimator classes -- converge to the SAME optimum on all 6 params.
    So a recovered optimum is NOT an artifact of the DINN or of autograd. (New cross-method
    result; prior work only used the DINN + analytic Fisher/profile.)
  * ...but on THIS proxy the shared optimum is not Carroll and the bands are wide -- the
    5-tracer proxy box structurally under-identifies: DFe depletes to ~1.4e-4 (the iron
    observable carries no magnitude signal, so the absolute-iron anchor is inert), and
    R_PICPOC only touches PIC where it trades off against the growth pair. A faithful limit
    of the proxy, cross-method-confirmed -- consistent with the Fisher/profile sloppiness.
  * A FAITHFUL positive validation (independent methods recovering Carroll) therefore needs
    the 5-PFT 2-layer box + the real GEOTRACES *observed* (non-depleted) absolute iron -> the
    cluster. This tool is the ready harness: point _forward/target at that setup.

Run:  uv run python scripts/independent_validation.py [--n-restarts 8] [--seed 0]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

_SRC = Path(__file__).resolve().parent.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff.carroll6 import (  # noqa: E402
    CARROLL_VALUES,
    PARAM_BOUNDS,
    PARAM_NAMES,
    bounded_params,
    carroll6_integrate,
)

DT = 0.25
N_STEPS = 200          # 50-day transient (dt=0.25) -- the identifiable regime
N_CELLS = 16           # cells with varying initial DFe -> spans the iron-limitation knee
NOISE_REL = 0.02       # 2% relative observation noise on the target
ABS_IRON_W = 3.0       # absolute-iron anchor (local analog of GEOTRACES abs-iron: the
                       # project's key finding is ABSOLUTE iron magnitude identifies alpfe,
                       # not z-scored pattern). Set 0 to reproduce the sloppy pattern-only regime.


def _make_ics() -> torch.Tensor:
    """Tracer-first IC [5, N_CELLS] ([DFe,Ps,Pl,POC,PIC]); DFe log-spaced across the knee."""
    state0 = torch.full((5, N_CELLS), 0.1)
    state0[0] = torch.logspace(-2, 0.3, N_CELLS)  # DFe 0.01 .. ~2.0
    return state0


def _forward(raw: torch.Tensor, ics: torch.Tensor) -> torch.Tensor:
    """Batched forward. raw [6, B] -> final state [5, B, N_CELLS]."""
    params = bounded_params(raw, PARAM_BOUNDS, param_axis=0)     # [6, B]
    b = raw.shape[1]
    state0 = ics.unsqueeze(1).expand(5, b, ics.shape[1])         # [5, B, N]
    return carroll6_integrate(state0, params.unsqueeze(-1), DT, N_STEPS)  # [5, B, N]


def _loss_from_state(pred: torch.Tensor, target, scale) -> torch.Tensor:
    """Scale-normalised pattern MSE + absolute-iron anchor. pred [5,B,N] -> [B]."""
    err = (pred - target.unsqueeze(1)) / scale.view(5, 1, 1)
    rel = (err ** 2).mean(dim=(0, 2))
    abs_iron = ((pred[0] - target[0].unsqueeze(0)) ** 2).mean(dim=1)  # DFe magnitude
    return rel + ABS_IRON_W * abs_iron


def _loss(raw: torch.Tensor, ics, target, scale) -> torch.Tensor:
    return _loss_from_state(_forward(raw, ics), target, scale)


# ---- Estimator A: autograd gradient descent (batched restarts, no DINN) --------------
def recover_gradient(ics, target, scale, n_restarts, seed, n_epochs=700) -> torch.Tensor:
    g = torch.Generator().manual_seed(seed)
    raw = torch.randn(6, n_restarts, generator=g, requires_grad=True)
    opt = torch.optim.Adam([raw], lr=0.1)
    for _ in range(n_epochs):
        opt.zero_grad()
        _loss(raw, ics, target, scale).sum().backward()
        opt.step()
    with torch.no_grad():
        return bounded_params(raw.detach(), PARAM_BOUNDS, param_axis=0)  # [6, n_restarts]


# ---- Estimator B: Nelder-Mead simplex (no gradients, no autograd, no NN) --------------
def recover_simplex(ics, target, scale, n_restarts, seed, max_iter=800) -> torch.Tensor:
    from scipy.optimize import minimize

    def obj(x):
        with torch.no_grad():
            return float(_loss(torch.tensor(x, dtype=torch.float32).view(6, 1), ics, target, scale)[0])

    g = np.random.default_rng(seed)
    outs = []
    for _ in range(n_restarts):
        res = minimize(obj, g.standard_normal(6), method="Nelder-Mead",
                       options={"maxiter": max_iter, "xatol": 1e-4, "fatol": 1e-10})
        with torch.no_grad():
            outs.append(bounded_params(torch.tensor(res.x, dtype=torch.float32), PARAM_BOUNDS, param_axis=0))
    return torch.stack(outs, dim=1)  # [6, n_restarts]


# ---- Estimator C: profile-likelihood (whole grid batched) -> per-param band ----------
def profile_bands(ics, target, scale, best_loss, n_grid=11, n_epochs=250, seed=0):
    """For every (param, grid-value) pin the param, optimise the other 5; batched. -> bands."""
    grids = torch.stack([torch.logspace(np.log10(float(PARAM_BOUNDS[p, 0])),
                                        np.log10(float(PARAM_BOUNDS[p, 1])), n_grid)
                         for p in range(6)])                     # [6, G]
    B = 6 * n_grid
    pin_mask = torch.zeros(6, B, dtype=torch.bool)
    pin_val = torch.zeros(6, B)
    for p in range(6):
        for j in range(n_grid):
            k = p * n_grid + j
            pin_mask[p, k] = True
            pin_val[p, k] = grids[p, j]
    g = torch.Generator().manual_seed(seed)
    raw = torch.randn(6, B, generator=g, requires_grad=True)
    opt = torch.optim.Adam([raw], lr=0.1)
    loss = None
    for _ in range(n_epochs):
        opt.zero_grad()
        params = bounded_params(raw, PARAM_BOUNDS, param_axis=0).clone()
        params = torch.where(pin_mask, pin_val, params)          # pin the profiled param
        state0 = ics.unsqueeze(1).expand(5, B, ics.shape[1])
        pred = carroll6_integrate(state0, params.unsqueeze(-1), DT, N_STEPS)
        loss = _loss_from_state(pred, target, scale)
        loss.sum().backward()
        with torch.no_grad():
            raw.grad[pin_mask] = 0.0
        opt.step()
    losses = loss.detach().view(6, n_grid).numpy()
    thr = best_loss * 2.0 + 1e-12
    bands = []
    for p in range(6):
        inside = grids[p].numpy()[losses[p] <= thr]
        bands.append((float(inside.min()), float(inside.max())) if inside.size else (np.nan, np.nan))
    return bands


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--n-restarts", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    ics = _make_ics()
    true_params = CARROLL_VALUES.clone()

    with torch.no_grad():
        clean = _forward(true_params.view(6, 1), ics)[:, 0, :]           # [5, N]
        gen = torch.Generator().manual_seed(args.seed)
        target = clean * (1.0 + NOISE_REL * torch.randn(clean.shape, generator=gen))
        scale = clean.abs().mean(dim=1).clamp_min(1e-6)  # mean-relative (robust to flat tracers)
        best_loss = float(_loss_from_state(clean.unsqueeze(1), target, scale)[0])

    print("# Independent cross-method validation on the 0-D box  (#163, self-twin scope)", flush=True)
    print(f"# {N_CELLS} cells, {N_STEPS} steps, {NOISE_REL:.0%} obs noise, {args.n_restarts} restarts/estimator")
    print(f"# floor loss (noise only) = {best_loss:.4e}\n", flush=True)

    grad = recover_gradient(ics, target, scale, args.n_restarts, args.seed)      # [6, R]
    print("# (A) gradient done", flush=True)
    simp = recover_simplex(ics, target, scale, args.n_restarts, args.seed)       # [6, R]
    print("# (B) simplex done", flush=True)
    bands = profile_bands(ics, target, scale, best_loss, seed=args.seed)
    print("# (C) profile done\n", flush=True)

    hdr = (f"{'param':<11}{'Carroll':>11}{'grad(A)':>11}{'±':>9}{'simplex(B)':>12}{'±':>9}"
           f"{'A~B?':>6}{'profile band':>24}")
    print(hdr); print("-" * len(hdr))
    for i, name in enumerate(PARAM_NAMES):
        gm, gs = float(grad[i].mean()), float(grad[i].std())
        sm, ss = float(simp[i].mean()), float(simp[i].std())
        agree = "yes" if abs(gm - sm) <= 0.15 * abs(float(true_params[i])) + max(gs, ss) else "NO"
        lo, hi = bands[i]
        print(f"{name:<11}{float(true_params[i]):>11.4g}{gm:>11.4g}{gs:>9.2g}{sm:>12.4g}{ss:>9.2g}"
              f"{agree:>6}   [{lo:.4g}, {hi:.4g}]")

    print("\n# A~B 'yes' = recovery is method-independent (survives dropping the DINN AND autograd).")
    print("# Tight band containing Carroll = identified; wide/rail band or large ± = sloppy")
    print("# (expected: iron pair + growth pair). Real-data agreement -> GEOTRACES + cluster.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
