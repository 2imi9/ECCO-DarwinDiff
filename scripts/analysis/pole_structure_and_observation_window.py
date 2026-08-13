"""Does the box's POLE STRUCTURE explain why scav_rat only recovers at a 50-day window?

MOTIVATION (2026-08-13). Prompted by arXiv 2503.13158 (Laplace-Net) and the question of whether a
Laplace-domain view helps DarwinDiff.

A Laplace / transfer-function view says a parameter's information sits somewhere in the s-plane:
  * s -> 0   is the DC gain, i.e. the steady state
  * finite s is the transient, governed by the system's poles (the Jacobian eigenvalues)

The repo has already MEASURED something with exactly that shape
(2026-07-31_prereg_flagship_window_sweep.md), by integrating the box to 3200 steps:

    observable        anchors      % converged at 200 steps (50 d)
    DFe_1 surface     alpfe                 100.1%
    PIC/POC           R_PICPOC              100.0%  (flat at 100..1600 steps)
    DFe_2 subsurface  scav_rat               47.5%

and measured that `scav_rat` recovers ONLY at the 50-day window (half and double both fail), while
`alpfe` and `R_PICPOC` are window-indifferent.

The Laplace reading of that is sharp and falsifiable:
  H: alpfe and R_PICPOC are identified from the s->0 limit (steady state), so their sensitivity
     SATURATES early and is flat thereafter. scav_rat is identified from the TRANSIENT, so its
     sensitivity is non-monotone in the observation window T and peaks at a finite time set by the
     slow pole -- which should be of order the 50-day window, not orders away.

This script tests H directly on the shipped 2-layer box:
  1. linearise at Carroll truth -> Jacobian eigenvalues (poles) -> time constants tau = -1/Re(lambda)
  2. sweep the integration window T and compute, for each parameter, the RELATIVE log-sensitivity
     of its own anchor observable, |d ln y / d ln theta|(T)
  3. report where each sensitivity saturates or peaks

Falsifier: if scav_rat's sensitivity is monotone-saturating like alpfe's, the Laplace framing adds
nothing and H is refuted.

Deterministic, CPU, float64. Run:
    python scripts/analysis/pole_structure_and_observation_window.py --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from darwindiff import carroll6  # noqa: E402
from darwindiff import carroll6_5pft_2layer as box  # noqa: E402

DT = 0.25  # days, the flagship value
I = {n: i for i, n in enumerate(carroll6.PARAM_NAMES)}

# anchor observable for each parameter, as the window-sweep prereg assigns them
ANCHOR = {
    "alpfe": ("DFe_1", box.I_DFE_1),
    "scav_rat": ("DFe_2", box.I_DFE_2),
    "R_PICPOC": ("PIC_1", getattr(box, "I_PIC_1", None)),
}


def base_state(n_cells: int, gen: torch.Generator) -> torch.Tensor:
    n_tr = 15
    b = torch.tensor(
        [1.0e-4, 1.0e-4, 0.10, 0.10, 0.05, 0.05, 0.05,
         0.5, 0.5, 2.0, 2.0, 2.3, 2.3, 0.01, 0.01], dtype=torch.float64)[:n_tr]
    jit = 1.0 + 0.05 * torch.randn(n_tr, n_cells, generator=gen, dtype=torch.float64)
    return (b[:, None] * jit).contiguous()


def run(params: torch.Tensor, state0: torch.Tensor, n_steps: int, forcing) -> torch.Tensor:
    T, S, W = forcing
    s = state0
    for _ in range(n_steps):
        s = box.carroll6_5pft_2layer_step(s, params, DT, T=T, S=S, wind=W)
    return s


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--max-days", type=float, default=400.0)
    args = ap.parse_args()

    torch.manual_seed(0)
    g = torch.Generator().manual_seed(4242)
    n_cells = 24
    state0 = base_state(n_cells, g)
    forcing = (10.0 + 8.0 * torch.rand(n_cells, generator=g, dtype=torch.float64),
               34.0 + 1.5 * torch.rand(n_cells, generator=g, dtype=torch.float64),
               4.0 + 6.0 * torch.rand(n_cells, generator=g, dtype=torch.float64))
    p0 = torch.tensor([p.carroll_value for p in carroll6.PARAMS], dtype=torch.float64)

    # ---- 1. poles: Jacobian of the one-step map at Carroll truth, cell 0 -------------
    s_ref = run(p0, state0, 200, forcing)  # start from the flagship end state
    x0 = s_ref[:, :1].clone().requires_grad_(True)
    f0 = box.carroll6_5pft_2layer_step(x0, p0, DT,
                                       T=forcing[0][:1], S=forcing[1][:1], wind=forcing[2][:1])
    n_tr = x0.shape[0]
    Jmap = np.zeros((n_tr, n_tr))
    for i in range(n_tr):
        gr = torch.autograd.grad(f0[i, 0], x0, retain_graph=True, allow_unused=True)[0]
        if gr is not None:
            Jmap[i] = gr[:, 0].detach().numpy()
    ev_map = np.linalg.eigvals(Jmap)          # eigenvalues of the ONE-STEP map
    # continuous-time poles: lambda = ln(mu)/dt
    with np.errstate(divide="ignore", invalid="ignore"):
        lam = np.log(np.abs(ev_map) + 1e-300) / DT
    tau = np.where(lam < 0, -1.0 / lam, np.inf)     # decay time constants, days
    finite = np.sort(tau[np.isfinite(tau) & (tau > 0)])

    print("POLE STRUCTURE of the 2-layer box at Carroll truth (cell 0)\n")
    print(f"  one-step map |eigenvalues| range: {np.abs(ev_map).min():.6f} .. {np.abs(ev_map).max():.6f}")
    print(f"  decay time constants tau = -1/Re(lambda), days:")
    if finite.size:
        show = finite[finite < 1e6]
        print(f"    fastest {show.min():.3f} d   median {np.median(show):.2f} d   "
              f"slowest {show.max():.2f} d   (n={show.size})")
        print(f"    the flagship window is 200 x {DT} = {200*DT:.0f} d")
        near = show[(show > 10) & (show < 500)]
        print(f"    time constants in 10-500 d: {np.round(np.sort(near), 1).tolist()}")

    # ---- 2. sensitivity vs observation window ---------------------------------------
    windows = [int(d / DT) for d in (5, 10, 20, 35, 50, 75, 100, 150, 200, 300, 400)
               if d <= args.max_days]
    h = 1e-5
    rows = []
    print("\nRELATIVE log-sensitivity |d ln y / d ln theta| of each parameter's ANCHOR observable\n")
    hdr = f"{'days':>6} " + "".join(f"{k:>16}" for k in ANCHOR)
    print(hdr)
    for n_steps in windows:
        days = n_steps * DT
        line = {"days": days}
        for pname, (oname, oidx) in ANCHOR.items():
            if oidx is None:
                line[pname] = None
                continue
            pi = I[pname]
            pp = p0.clone(); pp[pi] *= (1 + h)
            pm = p0.clone(); pm[pi] *= (1 - h)
            yp = run(pp, state0, n_steps, forcing)[oidx].mean().item()
            ym = run(pm, state0, n_steps, forcing)[oidx].mean().item()
            y0 = run(p0, state0, n_steps, forcing)[oidx].mean().item()
            sens = abs((yp - ym) / (2 * h * y0)) if y0 != 0 else float("nan")
            line[pname] = sens
        rows.append(line)
        print(f"{days:>6.0f} " + "".join(f"{line[k]:>16.6f}" if line[k] is not None else f"{'--':>16}"
                                         for k in ANCHOR))

    # ---- 3. where does each saturate / peak? ----------------------------------------
    print("\nSHAPE of each sensitivity curve:")
    verdict = {}
    for pname in ANCHOR:
        vals = np.array([r[pname] for r in rows if r[pname] is not None], dtype=float)
        ds = np.array([r["days"] for r in rows if r[pname] is not None], dtype=float)
        if vals.size < 3:
            continue
        imax = int(np.argmax(vals))
        final = vals[-1]
        peak = vals[imax]
        ratio = peak / final if final > 0 else np.inf
        shape = "NON-MONOTONE (peaks then falls)" if (imax < len(vals) - 1 and ratio > 1.05) \
            else "monotone / saturating"
        verdict[pname] = {"peak_days": float(ds[imax]), "peak": float(peak),
                          "final": float(final), "peak_over_final": float(ratio), "shape": shape}
        print(f"  {pname:10s} peak at {ds[imax]:>5.0f} d  (peak/final = {ratio:6.3f})  -> {shape}")

    out = {"dt_days": DT, "time_constants_days": finite[finite < 1e6].tolist(),
           "sensitivity_rows": rows, "verdict": verdict}
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
