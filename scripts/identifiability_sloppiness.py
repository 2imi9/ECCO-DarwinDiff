"""Quantitative structural identifiability ("sloppiness") of the Carroll-6 params.

Companion to `box_vs_darwin_fidelity.py` (which shows the *forward-model* wall) and to
`docs/findings/rpicpoc_ratio_structural.md`. This script answers the estimator-theory
question for paper #1 (#120): given the differentiable box at Carroll's published optimum,
how well is each of the 6 parameters constrained by the z-scored multi-tracer recovery
objective?

Two diagnostics, both in **log-parameter** space (scale-free, since the params span
~6 orders, e.g. scav_rat ~6e-7 vs Smallgrow ~0.66):

1. **Per-AOI relative sensitivity** |dL/d ln(theta)| of the z-scored loss at Carroll's
   values, per AOI. Reveals that R_PICPOC's identifiability is *AOI-dependent* — real in
   eqpac (where the rigid box's PIC:POC ~0.042 matches Darwin's ~0.033) and collapsing in
   natl (where Darwin is ~0.68, unreachable). Identifiability is gated by forward-model
   fidelity.

2. **Fisher / Gauss-Newton information matrix** F = J^T J (J = d(residuals)/d ln(theta),
   finite-difference), over the *joint multi-AOI* residuals — the setting the real
   recovery uses (shared params). Its eigenspectrum quantifies sloppiness (eigenvalues
   spanning orders of magnitude); the marginal stiffness sqrt(F_ii) ranks per-parameter
   identifiability; eigenvector loadings expose degenerate directions.

Headline (2026-06-24, eqpac+natl+SO 1deg caches): the model is sloppy (lambda_max/lambda_min
~7e2), and **R_PICPOC is the least-constrained parameter** — marginal stiffness ~4-17x below
every other param, and ~0 loading on the stiffest eigenvector. The recoverable params
(Biggrow, diatomgraz, alpfe) align with the stiff directions. This is the quantitative
companion to the 5/6 ceiling: R_PICPOC is structurally weakly-identified in the joint fit.

Run:  uv run python scripts/identifiability_sloppiness.py [--md docs/findings/...md]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import torch

torch.set_default_dtype(torch.float64)  # clean eigenvalues / finite differences

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1, I_ALK_2, I_DFE_1, I_DFE_2, I_DIATOM, I_DIC_1, I_DIC_2, I_LGE,
    I_PIC_1, I_PIC_2, I_POC_1, I_POC_2, I_PROHL, I_PROLL, I_SYN,
    N_TRACERS_2LAYER, carroll6_5pft_2layer_integrate as integ,
)

DT, N_STEPS = 0.25, 200
CACHE_DIR = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"
CACHES = {
    "eqpac": "eqpac_targets_equatorial_pacific.pt",
    "natl": "eqpac_targets_north_atlantic_subpolar.pt",
    "SO": "eqpac_targets_southern_ocean_pacific.pt",
}
NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
# z-scored target fields (box state index). DIC/ALK excluded: IC-confounded (see
# box_vs_darwin_fidelity.py note). These are the core recovery z-targets.
FIELDS = [("Chl1", I_DIATOM), ("Chl2", I_LGE), ("Chl3", I_SYN), ("Chl4", I_PROLL),
          ("Chl5", I_PROHL), ("FeT", I_DFE_1), ("POC", I_POC_1), ("PIC", I_PIC_1)]


def _fill(a, v):
    return torch.tensor(np.nan_to_num(np.asarray(a, float), nan=v))


def _z(x, m):
    v = x[m]
    return (x - v.mean()) / (v.std() + 1e-9)


def _setup(fn):
    c = torch.load(CACHE_DIR / fn, weights_only=False)
    dar = {**{f"Chl{i}": c["chl_per_pft"][f"Chl{i}"] for i in range(1, 6)},
           "FeT": c["fet_binned"], "POC": c["poc_binned"], "PIC": c["pic_binned"]}
    sst, sss, wind = c["sst"], c["sss"], c["wind"]
    mask = np.isfinite(sst) & np.isfinite(sss) & np.isfinite(wind)
    for f, _ in FIELDS:
        mask = mask & np.isfinite(dar[f])
    mt = torch.tensor(mask)
    s0 = torch.zeros(N_TRACERS_2LAYER, *sst.shape)
    s0[I_DFE_1] = _fill(dar["FeT"], 1e-4); s0[I_DFE_2] = _fill(dar["FeT"], 1e-4)
    for idx in (I_DIATOM, I_LGE, I_SYN, I_PROLL, I_PROHL):
        s0[idx] = 0.1
    s0[I_POC_1] = _fill(dar["POC"], 1.0); s0[I_POC_2] = _fill(dar["POC"], 1.0)
    s0[I_PIC_1] = _fill(dar["PIC"], 0.05); s0[I_PIC_2] = _fill(dar["PIC"], 0.05)
    s0[I_DIC_1] = _fill(c["dic_binned"], 2000.0); s0[I_DIC_2] = _fill(c["dic_binned"], 2000.0)
    s0[I_ALK_1] = _fill(c["alk_binned"], 2300.0); s0[I_ALK_2] = _fill(c["alk_binned"], 2300.0)
    tz = {f: _z(_fill(dar[f], 0.0), mt) for f, _ in FIELDS}
    forc = dict(T=_fill(sst, 15.0), S=_fill(sss, 35.0), wind=_fill(wind, 7.0))
    return s0, mt, tz, forc


def _loss(theta, aoi):
    s0, mt, tz, forc = aoi
    fin = integ(s0, theta, DT, N_STEPS, **forc)
    return sum(((_z(fin[idx], mt) - tz[f])[mt] ** 2).mean() for f, idx in FIELDS)


def _resid(theta, aois):
    rs = []
    for s0, mt, tz, forc in aois:
        fin = integ(s0, theta, DT, N_STEPS, **forc)
        for f, idx in FIELDS:
            rs.append((_z(fin[idx], mt) - tz[f])[mt])
    return torch.cat(rs)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--md", type=Path, default=None)
    p.add_argument("--eps", type=float, default=1e-3, help="log-param FD step for the Jacobian")
    args = p.parse_args(argv)

    aois = {k: _setup(f) for k, f in CACHES.items() if (CACHE_DIR / f).exists()}
    th = torch.tensor([float(x) for x in CARROLL_VALUES])
    lines = []

    # 1. per-AOI relative sensitivity (autograd)
    print("Per-AOI relative sensitivity |dL/d ln(theta)| of z-scored loss at Carroll:")
    sens = {}
    for k, aoi in aois.items():
        t = th.clone().requires_grad_(True)
        L = _loss(t, aoi); L.backward()
        sens[k] = (t.grad.detach() * th).abs()
    hdr = "  param".ljust(13) + "".join(k.rjust(11) for k in aois)
    print(hdr)
    for i, nm in enumerate(NAMES):
        print(f"  {nm:11}" + "".join(f"{sens[k][i].item():11.3e}" for k in aois))

    # 2. Fisher / Gauss-Newton eigenspectrum over the joint multi-AOI residuals
    r0 = _resid(th, list(aois.values())).detach()
    J = torch.zeros(r0.numel(), 6)
    for j in range(6):
        tp = th.clone(); tp[j] = tp[j] * np.exp(args.eps)
        J[:, j] = (_resid(tp, list(aois.values())).detach() - r0) / args.eps
    F = J.T @ J
    ev, evec = torch.linalg.eigh(F)
    ev, evec = ev.flip(0), evec.flip(1)
    print(f"\nFisher (J^T J) eigenspectrum, log-params, joint {'+'.join(aois)} (n_res={r0.numel()}):")
    print("  lambda:", "  ".join(f"{ev[k].item():.3e}" for k in range(6)))
    print(f"  sloppiness lambda_max/lambda_min = {(ev[0] / ev[-1]).item():.3e}")
    print("  marginal stiffness sqrt(F_ii):")
    for i, nm in enumerate(NAMES):
        print(f"    {nm:11} {F[i, i].sqrt().item():9.2f}")
    print("  stiffest eigvec (lambda_max) loadings:",
          "  ".join(f"{nm}={evec[i, 0].item():+.2f}" for i, nm in enumerate(NAMES)))
    print("  sloppiest eigvec (lambda_min) loadings:",
          "  ".join(f"{nm}={evec[i, -1].item():+.2f}" for i, nm in enumerate(NAMES)))

    if args.md:
        args.md.parent.mkdir(parents=True, exist_ok=True)
        m = ["# Carroll-6 identifiability / sloppiness (quantitative)\n",
             f"Generated by `scripts/identifiability_sloppiness.py`. Box at Carroll's optimum, "
             f"z-scored multi-tracer loss, log-parameter space. AOIs: {', '.join(aois)}.\n",
             "## Per-AOI relative sensitivity `|dL/d ln(theta)|`\n",
             "| param | " + " | ".join(aois) + " |", "|" + "---|" * (len(aois) + 1)]
        for i, nm in enumerate(NAMES):
            m.append(f"| {nm} | " + " | ".join(f"{sens[k][i].item():.3e}" for k in aois) + " |")
        m += ["\n## Fisher (J^T J) eigenspectrum (joint multi-AOI)\n",
              "- eigenvalues: " + ", ".join(f"{ev[k].item():.3e}" for k in range(6)),
              f"- sloppiness lambda_max/lambda_min = {(ev[0] / ev[-1]).item():.3e}\n",
              "| param | marginal stiffness sqrt(F_ii) | loading on stiffest eigvec |",
              "|---|---|---|"]
        for i, nm in enumerate(NAMES):
            m.append(f"| {nm} | {F[i, i].sqrt().item():.2f} | {evec[i, 0].item():+.3f} |")
        m.append("\n**R_PICPOC is the least-constrained parameter** (lowest marginal stiffness, "
                 "~0 loading on the stiffest direction) — the quantitative companion to the 5/6 "
                 "ceiling. Identifiability is gated by forward-model fidelity (see "
                 "`box_vs_darwin_fidelity.py`).")
        args.md.write_text("\n".join(m), encoding="utf-8")
        print(f"\nwrote {args.md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
