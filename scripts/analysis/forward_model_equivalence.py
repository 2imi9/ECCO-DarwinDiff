"""Numerical-equivalence gate: does a refactor move the flagship forward model?

Between AICR checkout dd83710 and the post-refactor tree, carroll6_5pft_2layer.py changed by
259 lines, and the diff mutates the core growth computation (growth_diatom / growth_lge / ...
were rewritten, extracted into a new phytoplankton_process_rates helper).

The flagship's published numbers were produced BEFORE that refactor. The paper is written from
HEAD. So the question that must be answered before any number is attributed to HEAD:

    does HEAD's carroll6_5pft_2layer_step produce bitwise-identical trajectories AND parameter
    gradients to dd83710's, at Carroll values, under identical inputs, in BOTH precisions?

Gradients matter because recovery is driven by d(loss)/d(params) through the box; float32
matters because training runs in float32, where re-associating identical algebra can change
the result even when float64 agrees.

Usage (two invocations, one per checkout, so module caching cannot alias the two trees):

    python forward_model_equivalence.py --repo <pre-refactor worktree>  --out pre.json
    python forward_model_equivalence.py --repo <post-refactor checkout> --out post.json \
        --baseline pre.json

With --baseline the run compares every hash against the baseline JSON and exits 1 on any
mismatch — it is a gate, not a report. Without --baseline it only writes the JSON.

Deterministic by construction: fixed seed, CPU, no data files touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import torch

# The model's documented tracer layout (carroll6_5pft_2layer.py module docstring):
#   L1: 0=DFe_1, 1=P_diatom, 2=P_lge, 3=P_syn, 4=P_proLL, 5=P_proHL,
#       6=POC_1, 7=PIC_1, 8=DIC_1, 9=ALK_1
#   L2: 10=DFe_2, 11=POC_2, 12=PIC_2, 13=DIC_2, 14=ALK_2
# Plausible per-tracer magnitudes in that order, so the equivalence is measured in the
# regime the flagship actually integrates, not at a scrambled state.
PLAUSIBLE_BASE = [
    1.0e-4,                        # DFe_1
    0.10, 0.10, 0.05, 0.05, 0.05,  # P_diatom, P_lge, P_syn, P_proLL, P_proHL
    0.5,                           # POC_1
    0.01,                          # PIC_1
    2.0,                           # DIC_1
    2.3,                           # ALK_1
    1.0e-4,                        # DFe_2
    0.5,                           # POC_2
    0.01,                          # PIC_2
    2.1,                           # DIC_2
    2.35,                          # ALK_2
]

COMPARED_KEYS = ("traj_hash", "grad_hash", "final_state_sum", "final_state_absmax")


def run_side(box, params64: torch.Tensor, steps: int, dt: float, dtype: torch.dtype) -> dict:
    n_tracers = len(PLAUSIBLE_BASE)
    declared = getattr(box, "N_TRACERS_2LAYER", n_tracers)
    if declared != n_tracers:
        raise SystemExit(
            f"tracer layout changed: N_TRACERS_2LAYER={declared}, harness knows {n_tracers}; "
            "update PLAUSIBLE_BASE against the module docstring before trusting any verdict"
        )

    n_cells = 37
    g = torch.Generator().manual_seed(12345)

    base = torch.tensor(PLAUSIBLE_BASE, dtype=torch.float64)
    jitter = 1.0 + 0.05 * torch.randn(n_tracers, n_cells, generator=g, dtype=torch.float64)
    state0 = (base[:, None] * jitter).contiguous()

    T = 10.0 + 8.0 * torch.rand(n_cells, generator=g, dtype=torch.float64)
    S = 34.0 + 1.5 * torch.rand(n_cells, generator=g, dtype=torch.float64)
    wind = 4.0 + 6.0 * torch.rand(n_cells, generator=g, dtype=torch.float64)

    # Cast AFTER generation so both precisions start from the same float64 draws.
    state = state0.to(dtype)
    params = params64.to(dtype).clone().requires_grad_(True)
    T, S, wind = T.to(dtype), S.to(dtype), wind.to(dtype)

    hashes = []
    checkpoints = {}
    for i in range(steps):
        state = box.carroll6_5pft_2layer_step(state, params, dt, T=T, S=S, wind=wind)
        b = state.detach().contiguous().numpy().tobytes()
        hashes.append(hashlib.sha256(b).hexdigest()[:16])
        if i in (0, 9, 49, 99, steps - 1):
            checkpoints[str(i)] = state.detach().flatten()[:12].tolist()

    # The gradient the recovery loop actually consumes: d(loss)/d(params) through the
    # whole rollout. A squared functional so every tracer contributes with sign structure.
    loss = (state * state).sum()
    (grad,) = torch.autograd.grad(loss, params)

    return {
        "traj_hash": hashlib.sha256("".join(hashes).encode()).hexdigest(),
        "per_step_hashes_first10": hashes[:10],
        "grad_hash": hashlib.sha256(grad.detach().contiguous().numpy().tobytes()).hexdigest(),
        "grad": [repr(float(x)) for x in grad],
        "final_state_sum": repr(float(state.detach().sum())),
        "final_state_absmax": repr(float(state.detach().abs().max())),
        "checkpoints": checkpoints,
    }


def compare(result: dict, baseline: dict) -> int:
    rc = 0
    if baseline.get("param_values") != result.get("param_values"):
        print("FAIL param_values differ — the two sides were not run at the same truth")
        rc = 1
    for dtype_key in ("float64", "float32"):
        mine = result["results"].get(dtype_key)
        theirs = (baseline.get("results") or {}).get(dtype_key)
        if theirs is None:
            print(f"FAIL {dtype_key}: baseline JSON has no such block (old harness format?)")
            rc = 1
            continue
        for key in COMPARED_KEYS:
            ok = mine[key] == theirs[key]
            print(f"{'PASS' if ok else 'FAIL'} {dtype_key} {key}: "
                  f"{mine[key][:32]} vs {theirs[key][:32]}")
            if not ok:
                rc = 1
    return rc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="checkout root to import darwindiff from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--baseline", help="JSON from the other checkout; compare and exit 1 on any mismatch")
    ap.add_argument("--steps", type=int, default=200, help="flagship N_STEPS")
    ap.add_argument("--dt", type=float, default=0.25, help="flagship dt (200*0.25 = 50 d)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo / "src"))

    from darwindiff import carroll6
    from darwindiff import carroll6_5pft_2layer as box

    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)

    # Carroll truth. PARAMS order is load-bearing; read by name defensively.
    names = [p.name for p in carroll6.PARAMS]
    params64 = torch.tensor([p.carroll_value for p in carroll6.PARAMS], dtype=torch.float64)

    try:
        sha = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        sha = "<unknown>"

    result = {
        "repo": str(repo),
        "sha": sha,
        "param_names": names,
        "param_values": [float(x) for x in params64],
        "steps": args.steps,
        "dt": args.dt,
        "n_cells": 37,
        "has_phyto_process_rates": hasattr(box, "phytoplankton_process_rates"),
        "results": {
            "float64": run_side(box, params64, args.steps, args.dt, torch.float64),
            "float32": run_side(box, params64, args.steps, args.dt, torch.float32),
        },
    }
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")

    for dtype_key in ("float64", "float32"):
        r = result["results"][dtype_key]
        print(f"{dtype_key}: traj={r['traj_hash'][:16]} grad={r['grad_hash'][:16]} "
              f"final_sum={r['final_state_sum']}")
    print(f"sha={sha} has_phyto_process_rates={result['has_phyto_process_rates']}")

    if args.baseline:
        baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
        rc = compare(result, baseline)
        print("VERDICT:", "EQUIVALENT" if rc == 0 else "NOT EQUIVALENT — refactor moved the model")
        return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
