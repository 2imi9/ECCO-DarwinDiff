#!/usr/bin/env python
"""Derive per-(AOI, block) ADEQUACY weights from residual geometry at the prior midpoint.

WHAT THIS DECIDES
-----------------
`emit_routing_rule.py` weighted AOIs by Fisher information and made recovery WORSE
(`scav_rat` 26/50 -> 11/50, job 256953). The post-mortem named the reason:

    information is not helpfulness

A Fisher diagonal measures how much the observable MOVES when the parameter moves. It is
silent on whether the residual it is driven against is one the forward model could ever
reach. Where the model is misspecified, high information means the optimiser is confidently
pushed toward a target it cannot attain -- it up-weights confident error.

This script supplies the missing factor. Per observable block `b` in AOI `a`:

    rho(a, b) = ||model(theta_0) - d|| / ||d||          (relative residual)
    adequacy  = max(0, 1 - rho^2)                       (the variance-explained analogue)

rho -> 0 : the box can already reproduce this block; residual is nearly all signal-free.
rho -> 1 : the residual is as large as the data. NO parameter value makes the box match.

WHY THIS IS NOT THE SAME MEASUREMENT AS residual_angle.py
---------------------------------------------------------
That script evaluates at the RECOVERED optimum, so it needs a completed fit and cannot
route one. This evaluates at the prior midpoint `theta_0` -- available before any fit, and
the point an untrained network actually starts from (`bounded_params` maps a zero-output
net to the middle of `bounds`). Nothing here reads `CARROLL_VALUES`; the script asserts that
at the end, exactly as `emit_routing_rule.py` does.

It also does NOT clip. `residual_angle.py` caps sin(phi) at 1 - 1e-12, which collapses
"residual 1.05x the signal" and "residual 700000x the signal" onto the same number and
made POC, PIC and eqpac FeT indistinguishable in the 2026-07-28 table. The raw ratio is
reported here so the saturated blocks can be told apart.

WHY THE WEIGHT IS RELATIVE WITHIN A BLOCK, NOT ABSOLUTE
--------------------------------------------------------
This is the load-bearing design choice, and it comes from the 2026-07-28 caveat: POC and
PIC are saturated in EVERY AOI. An absolute adequacy cut would therefore zero the
Darwin-pattern POC/PIC terms in all three basins -- and those terms are what `R_PICPOC`
recovers 50/50 from, so the rule would destroy the project's cleanest result on its way to
fixing `scav_rat`.

A residual common to all three basins is the known 0-D-vs-3-D surrogate gap: a systematic
offset between the box's steady state and Darwin's, not a statement about any one basin.
Only the part that VARIES across basins is evidence of basin-specific misspecification. So:

    w(a, b) = adequacy(a, b) / max_a' adequacy(a', b)

A block that is equally (in)adequate everywhere gets w = 1 everywhere and is left alone.
A block that is adequate in two basins and saturated in a third down-weights only the third.

USAGE
    DARWIN_DATA_ROOT=D:/ecco_darwin_v5 python scripts/analysis/emit_adequacy_rule.py \
        --out docs/findings/2026-08-03_adequacy_rule.json

Commit the emitted JSON BEFORE submitting any training job and quote its commit hash with
the results.
"""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

import numpy as np
import torch

from darwindiff.carroll6 import PARAM_BOUNDS, PARAM_NAMES, bounded_params
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1,
    I_DFE_1,
    I_DIC_1,
    I_PIC_1,
    I_POC_1,
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
)
from darwindiff.safe_load import safe_torch_load

DT, N_STEPS = 0.25, 200

CACHE_FILES = {
    "eqpac": "eqpac_targets_equatorial_pacific.pt",
    "natlsubpolar": "eqpac_targets_north_atlantic_subpolar.pt",
    "southernoceanpac": "eqpac_targets_southern_ocean_pacific.pt",
}
BLOCKS = {
    "FeT": ("fet_binned", I_DFE_1),
    "POC": ("poc_binned", I_POC_1),
    "PIC": ("pic_binned", I_PIC_1),
    "DIC": ("dic_binned", I_DIC_1),
    "ALK": ("alk_binned", I_ALK_1),
}


def prior_midpoint() -> torch.Tensor:
    """theta_0: where an untrained network actually starts.

    `bounded_params` maps a zero-output net through a sigmoid to the middle of `bounds`.
    log_mask is left at None to match the runner's default, so this is the midpoint the
    real pipeline begins from rather than a differently-scaled one.
    """
    return bounded_params(torch.zeros(len(PARAM_NAMES)), PARAM_BOUNDS)


def run_aoi(cache_dir: Path, aoi: str, theta: torch.Tensor) -> dict:
    """One forward pass at theta; relative residual per observable block."""
    c = safe_torch_load(cache_dir / CACHE_FILES[aoi])
    sst, sss, wind = c["sst"], c["sss"], c["wind"]
    mask = np.isfinite(sst) & np.isfinite(c["pic_binned"]) & np.isfinite(c["poc_binned"])

    def fill(a, v):
        return torch.tensor(
            np.nan_to_num(np.asarray(a, dtype=np.float64).astype(np.float32), nan=v)
        )

    s0 = torch.zeros(N_TRACERS_2LAYER, *sst.shape)
    s0[I_DFE_1] = fill(c["fet_binned"], 1e-4)
    for i in (1, 2, 3, 4, 5):
        s0[i] = 0.1
    s0[I_POC_1] = fill(c["poc_binned"], 1.0)
    s0[I_PIC_1] = fill(c["pic_binned"], 0.05)
    s0[I_DIC_1] = fill(c["dic_binned"], 2000.0)
    s0[I_ALK_1] = fill(c["alk_binned"], 2300.0)
    s0[10] = fill(c["fet_binned"], 1e-4)
    s0[11] = fill(c["poc_binned"], 1.0)
    s0[12] = fill(c["pic_binned"], 0.05)
    s0[13] = fill(c["dic_binned"], 2000.0)
    s0[14] = fill(c["alk_binned"], 2300.0)

    final = carroll6_5pft_2layer_integrate(
        s0,
        theta.to(torch.float32),
        DT,
        N_STEPS,
        T=fill(sst, 15.0),
        S=fill(sss, 35.0),
        wind=fill(wind, 7.0),
    ).numpy()

    out = {}
    for name, (key, idx) in BLOCKS.items():
        d = np.asarray(c[key], dtype=np.float64)
        m = mask & np.isfinite(d)
        if m.sum() < 10:
            continue
        dv, mv = d[m], final[idx][m].astype(np.float64)
        nd = float(np.linalg.norm(dv))
        nr = float(np.linalg.norm(mv - dv))
        if nd <= 0:
            continue
        rho = nr / nd  # NOT clipped -- see module docstring
        out[name] = {
            "n": int(m.sum()),
            "norm_d": nd,
            "norm_r": nr,
            "rel_resid": rho,
            "adequacy": max(0.0, 1.0 - rho * rho),
            # reported for continuity with the 2026-07-28 table, which clipped
            "sin_phi_clipped": min(rho, 1.0 - 1e-12),
            "phi_deg": math.degrees(math.asin(min(rho, 1.0 - 1e-12))),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", default=None, help="write the adequacy rule JSON here")
    ap.add_argument(
        "--min-contrast",
        type=float,
        default=1.5,
        help="fail if no block's best AOI beats its worst by this factor; a rule that "
        "says every basin is equally adequate decides nothing",
    )
    args = ap.parse_args()

    cache = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")) / "cache"
    theta0 = prior_midpoint()

    print("theta_0 (prior midpoint, the untrained start):")
    for nm, v in zip(PARAM_NAMES, theta0.tolist()):
        print(f"  {nm:12s} {v:.6g}")
    print()

    raw: dict[str, dict] = {}
    print(f"{'AOI':18s} {'block':6s} {'n':>6s} {'rel_resid':>10s} {'adequacy':>9s}")
    for aoi in CACHE_FILES:
        raw[aoi] = run_aoi(cache, aoi, theta0)
        for b, v in raw[aoi].items():
            print(
                f"{aoi:18s} {b:6s} {v['n']:6d} {v['rel_resid']:10.4f} {v['adequacy']:9.4f}"
            )

    # ---- relative-within-block normalisation (see module docstring) -------------
    blocks = sorted({b for a in raw.values() for b in a})
    weights: dict[str, dict[str, float]] = {a: {} for a in raw}
    contrasts = {}
    for b in blocks:
        vals = {a: raw[a][b]["adequacy"] for a in raw if b in raw[a]}
        top = max(vals.values())
        for a, v in vals.items():
            weights[a][b] = (v / top) if top > 0 else 1.0
        lo = min(vals.values())
        if top <= 0:
            # Saturated in every AOI: the block carries no across-basin discrimination
            # at all, which is contrast 1 (leave alone), NOT infinite contrast.
            contrasts[b] = 1.0
        elif lo <= 0:
            contrasts[b] = float("inf")
        else:
            contrasts[b] = top / lo

    print(f"\n{'block':6s} " + " ".join(f"{a:>18s}" for a in raw) + "   contrast")
    for b in blocks:
        row = " ".join(f"{weights[a].get(b, float('nan')):18.4f}" for a in raw)
        c = contrasts[b]
        print(f"{b:6s} {row}   {c:.3g}")

    best = max(contrasts.values())
    if best < args.min_contrast:
        print(
            f"\nFAIL: largest across-AOI contrast is {best:.3g} < {args.min_contrast}. "
            "A rule that says every basin is equally adequate decides nothing."
        )
        return 2

    # ---- the answer-free assertion ---------------------------------------------
    # Nothing above reads the answer. Assert it structurally rather than claim it.
    # A text scan cannot work here: the guard's own message names the symbol, which is
    # exactly the false positive that a substring check produces.
    import ast

    banned = {"CARROLL_VALUES", "carroll_value", "model_value"}
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used.add(node.id)
        elif isinstance(node, ast.Attribute):
            used.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            used.update(a.name for a in node.names)
    leaked = banned & used
    assert not leaked, f"adequacy rule must not read the answer; it references {leaked}"
    print(f"\n[ok] rule derived without reading {sorted(banned)}")

    if args.out:
        payload = {
            "theta_0": dict(zip(PARAM_NAMES, theta0.tolist())),
            "dt": DT,
            "n_steps": N_STEPS,
            "raw": raw,
            "weights": weights,
            "contrast": contrasts,
            "definition": "w(a,b) = max(0,1-rho^2) normalised by the best AOI in that block",
        }
        Path(args.out).write_text(json.dumps(payload, indent=1), encoding="utf-8")
        print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
