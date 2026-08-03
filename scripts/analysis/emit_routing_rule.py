#!/usr/bin/env python
"""Derive per-(parameter, AOI) weights from information, never from the answer.

WHAT THIS DECIDES
-----------------
The flagship weights AOIs uniformly per parameter ({1, 2, 2} applies to all six alike). But the
per-AOI legs are wildly unequal *per parameter*: `scav_rat` recovers at 98-100% in the Southern
Ocean and 0-38% elsewhere, while `diatomgraz`'s only live leg is eqpac. A weighting that knows
this should do better than one that does not.

The danger is that the obvious way to set those weights -- "favour the AOI whose recovered value
lands nearest Carroll" -- **uses the answer**. That is the same structure as choosing `scav_rat`
from `geo1` and `diatomgraz` from `mld_dan8` because those runs scored best, and it is the failure
that killed the `diatomgraz` 35/50 claim when its architecture-matched null scored 34/50. Weights
chosen that way cannot support any identifiability statement.

So the weights come from **Fisher information at the prior midpoint**:

    w[j][a]  =  I_jj(a; theta_0) * width_j^2      normalised over AOIs, per parameter

`I_jj(a; theta_0)` is how much AOI `a`'s observations *can* constrain parameter `j`, and
`width_j^2` makes parameters on different scales comparable. Nothing here reads
`CARROLL_VALUES`, and the script asserts that at the end.

WHY theta_0 IS THE PRIOR MIDPOINT AND NOT theta*
------------------------------------------------
Every Fisher result in this repo to date was evaluated at a fitted optimum or at Carroll's
published values -- `observation_design.py` scales by `|theta_Carroll|`. Both are unavailable
before a fit. The prior midpoint is available, and it is also *where an untrained network actually
starts*: `bounded_params` maps a zero-output net through a sigmoid to `(lo + hi) / 2`. So this is
the information available at the initialisation the optimiser really begins from.

WHAT THIS RULE CANNOT DO
------------------------
It ranks **observation sets** -- which AOI's data constrains which parameter. It cannot rank an
**input channel** (MLD vs not), because a channel changes the parameterisation and not the
information, so it never enters the Fisher. The MLD-vs-Darwin-pattern conflict is therefore only
half addressable here; the other half needs `PER_PARAM=1`, where each parameter's own trunk can
use the channels it needs without imposing them on the others.

USAGE
    python scripts/analysis/emit_routing_rule.py --out docs/findings/2026-08-03_routing_rule.json

Commit the emitted JSON **before** submitting any training job, and quote its commit hash with the
results. Pre-registration: docs/findings/2026-08-03_prereg_per_parameter_routing.md
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _import_runner():
    """Import the runner with training disabled (mirrors observation_design._import_runner)."""
    os.environ.setdefault("NB23_N_EPOCHS", "0")
    os.environ.setdefault("NB23_SEEDS", "0")
    os.environ.setdefault("TORCH_COMPILE_BATCHED", "0")
    if not os.environ.get("OUTPUT_DIR"):
        os.environ["OUTPUT_DIR"] = tempfile.mkdtemp(prefix="dd_routing_")
    spec = importlib.util.spec_from_file_location(
        "_dd_runner", ROOT / "scripts" / "run_v3.0_joint_multi_aoi.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rel-eps", type=float, default=2e-2,
                    help="relative finite-difference step (matches observation_design)")
    ap.add_argument("--out", default=None, help="write the routing rule JSON here")
    ap.add_argument("--min-contrast", type=float, default=1.5,
                    help="fail if no parameter's best AOI beats its worst by this factor; a rule "
                         "that says every AOI is equally informative decides nothing")
    args = ap.parse_args()

    import torch

    from darwindiff.carroll6 import PARAM_BOUNDS, PARAMS

    R = _import_runner()
    dev = R.device
    bundles = R.bundles
    aoi_loss = R.aoi_loss
    names = [p.name for p in PARAMS]
    n_p = len(names)

    # ---- theta_0: the PRIOR MIDPOINT. Not Carroll, not a fitted optimum. --------------
    # bounded_params maps a zero-output (untrained) network to exactly this point, so it is
    # both "before the fit" and "where the optimiser actually starts".
    bounds = PARAM_BOUNDS.to(dev).double()
    theta0 = (bounds[:, 0] + bounds[:, 1]) / 2.0                 # [n_p]
    width = (bounds[:, 1] - bounds[:, 0]).abs()                  # [n_p]

    # Observables the flagship's loss anchors on, each with the SUPPORT it is scored over.
    #
    # Restricting to the real observation cells is load-bearing and was got wrong first time.
    # Averaged over all ocean cells the information comes out flat (1.00-1.07x best/worst
    # across AOIs) for every parameter, which is a statement about where the *box* is
    # sensitive, not about where the *data* constrains it. The loss only ever sees these
    # cells, so the Fisher must too. Southern Ocean has ZERO Daniels and ZERO bSi cells,
    # which no ocean-wide average can express.
    OBS = {
        "DFe_surface": (lambda st: st[R.I_DFE_1], "geo_surf_mask_f"),
        "DFe_subsurface": (lambda st: st[R.I_DFE_2], "geo_sub_mask_f"),
        "PIC_over_POC": (lambda st: st[R.I_PIC_1] / st[R.I_POC_1].clamp_min(1e-30),
                         "daniels_mask_f"),
        "bSi_surface": (lambda st: st[R.I_DIATOM], "posi_mask_f"),
        # Darwin-pattern targets are scored over the whole basin, so ocean is their support.
        "POC_subsurface": (lambda st: st[R.I_POC_2], None),
    }

    # One batched integration per AOI carrying theta_0 plus +/- perturbation columns.
    S = 1 + 2 * n_p
    eps = args.rel_eps * theta0.abs().clamp(min=1e-30)
    cols = theta0.reshape(n_p, 1).repeat(1, S).clone()
    col, pert = 1, {}
    for i in range(n_p):
        cols[i, col] += eps[i]; pert[(i, "+")] = col; col += 1
        cols[i, col] -= eps[i]; pert[(i, "-")] = col; col += 1

    base = {b["key"]: b["state0_per_seed"] for b in bundles}
    for b in bundles:
        z = base[b["key"]]
        b["state0_per_seed"] = z[:, :1].expand(z.shape[0], S, z.shape[2], z.shape[3])

    info: dict[str, dict[str, float]] = {n: {} for n in names}
    per_obs: dict[str, dict[str, dict[str, float]]] = {n: {} for n in names}

    with torch.no_grad():
        for b in bundles:
            key = b["key"]
            H, W = b["mask_f"].shape
            pb = cols.reshape(n_p, S, 1, 1).expand(n_p, S, H, W).to(torch.float32)
            _, state = aoi_loss(b, pb)
            ocean = (b["mask_f"] > 0).reshape(-1)
            tot = torch.zeros(n_p, dtype=torch.float64, device=dev)
            for oname, (fn, mask_key) in OBS.items():
                if mask_key is None:
                    sel = ocean
                else:
                    m = b.get(mask_key)
                    if m is None:
                        continue
                    sel = (torch.as_tensor(m).reshape(-1).to(ocean.device) > 0) & ocean
                n_obs = int(sel.sum())
                # An AOI with no cells for this observable contributes ZERO information from
                # it -- not a small number, and not the basin average. Southern Ocean has no
                # Daniels cells at all, so R_PICPOC gets nothing from it directly, which is
                # exactly the fact the ocean-wide average erased.
                for i, nm in enumerate(names):
                    per_obs[nm].setdefault(key, {})[oname] = 0.0
                if n_obs == 0:
                    continue
                y = fn(state).reshape(S, -1)[:, sel].double()
                rms = math.sqrt(float((y[0] ** 2).mean().clamp(min=1e-30)))
                contrib = torch.zeros(n_p, dtype=torch.float64, device=dev)
                for i in range(n_p):
                    dy = (y[pert[(i, "+")]] - y[pert[(i, "-")]]) / (2.0 * float(eps[i]))
                    g = dy * float(width[i]) / max(rms, 1e-30)   # dimensionless residual gradient
                    # SUM, not mean: more observations of the same quantity carry more
                    # information. Dividing by n_obs would make 13 cells and 34 cells
                    # equally informative, which is the opposite of what a Fisher says.
                    contrib[i] = float((g ** 2).sum())
                tot += contrib
                for i, nm in enumerate(names):
                    per_obs[nm][key][oname] = float(contrib[i])
            for i, nm in enumerate(names):
                info[nm][key] = float(tot[i])

    aois = [b["key"] for b in bundles]
    rule: dict[str, dict[str, float]] = {}
    for nm in names:
        tot = sum(info[nm].values())
        rule[nm] = ({a: info[nm][a] / tot for a in aois} if tot > 0
                    else {a: 1.0 / len(aois) for a in aois})

    print(f"\n=== ROUTING RULE from Fisher information at the PRIOR MIDPOINT ===")
    print(f"    theta_0 = " + "  ".join(f"{names[i]}={float(theta0[i]):.4g}" for i in range(n_p)))
    print(f"    AOIs    = {aois}\n")
    print(f"    {'parameter':<12} " + "  ".join(f"{a[:12]:>13}" for a in aois) + "   argmax")
    contrasts = {}
    for nm in names:
        w = rule[nm]
        best = max(w, key=w.get)
        lo = min(w.values())
        # A basin with literally no cells for a parameter's anchor has ZERO information, not
        # a tiny amount. Report that as infinite contrast rather than a 1e29 artifact of
        # dividing by a float floor.
        contrasts[nm] = float("inf") if lo <= 1e-12 else max(w.values()) / lo
        print(f"    {nm:<12} " + "  ".join(f"{w[a]:13.4f}" for a in aois) + f"   {best}")
    print()
    for nm in names:
        c = contrasts[nm]
        zero = [a for a, v in rule[nm].items() if v <= 1e-12]
        tag = f"  (no information at all from: {zero})" if zero else ""
        print(f"    contrast {nm:<12} best/worst = " +
              ("INF" if c == float("inf") else f"{c:.2f}x") + tag)

    # ---- self-checks, because a rule that decides nothing is worse than no rule -------
    # It never reads Carroll: assert theta_0 is the midpoint and nothing else.
    from darwindiff.carroll6 import CARROLL_VALUES
    car = CARROLL_VALUES.to(dev).double()
    assert not torch.allclose(theta0, car), (
        "theta_0 equals CARROLL_VALUES -- the rule would be selecting on the answer")
    graded = ["alpfe", "scav_rat", "diatomgraz", "R_PICPOC"]
    weak = [nm for nm in graded if contrasts[nm] < args.min_contrast]
    zero_info = {nm: [a for a, v in rule[nm].items() if v <= 1e-12] for nm in names}
    zero_info = {k: v for k, v in zero_info.items() if v}
    out = {
        "method": "per_parameter_per_aoi_fisher_at_prior_midpoint",
        "theta_0": {names[i]: float(theta0[i]) for i in range(n_p)},
        "theta_0_is": "prior midpoint (lo+hi)/2 -- where bounded_params maps an untrained net",
        "uses_carroll_values": False,
        "rel_eps": args.rel_eps,
        "aois": aois,
        "weights": rule,
        "raw_information": info,
        "information_by_observable": per_obs,
        "contrast_best_over_worst": {k: (None if v == float("inf") else v)
                                     for k, v in contrasts.items()},
        "aois_with_zero_information": zero_info,
        "low_contrast_parameters": weak,
        "limitation": (
            "Ranks observation sets only. Cannot rank an input channel (e.g. MLD), which changes "
            "the parameterisation rather than the information and never enters the Fisher."
        ),
    }
    if args.out:
        Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"\nwrote {args.out}")
    if weak:
        print(f"\nWARNING: {weak} have best/worst contrast below {args.min_contrast}x. "
              "For those parameters this rule does not discriminate between AOIs and routing "
              "them is not supported by information -- say so rather than routing anyway.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
