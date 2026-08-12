"""Numerical-equivalence check: did the 2026-08 box-model refactor move the flagship forward path?

Between AICR checkout dd83710 and main, carroll6_5pft_2layer.py changed by 259 lines, and the
diff mutates the core growth computation (growth_diatom / growth_lge / ... were rewritten,
apparently extracted into a new phytoplankton_process_rates helper).

The flagship's published numbers were produced BEFORE that refactor. The paper is written from
HEAD. So the question that must be answered before any number is attributed to HEAD:

    does HEAD's carroll6_5pft_2layer_step produce bitwise-identical trajectories to dd83710's,
    at Carroll values, under identical inputs?

Run with a --repo argument pointing at a checkout; it writes a JSON of trajectory hashes and
final states so two checkouts can be compared exactly.

Deterministic by construction: fixed seed, float64, CPU, no data files touched.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import torch


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="checkout root to import darwindiff from")
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=200, help="flagship N_STEPS")
    ap.add_argument("--dt", type=float, default=0.25, help="flagship dt (200*0.25 = 50 d)")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo / "src"))

    from darwindiff import carroll6
    from darwindiff import carroll6_5pft_2layer as box

    torch.manual_seed(0)
    torch.use_deterministic_algorithms(True)

    # Carroll truth, float64, on CPU. PARAMS order is load-bearing; read by name defensively.
    names = [p.name for p in carroll6.PARAMS]
    params = torch.tensor(
        [p.carroll_value for p in carroll6.PARAMS], dtype=torch.float64
    )

    # A spatial field of cells so any broadcasting/reduction change shows up, not just a scalar.
    n_cells = 37
    g = torch.Generator().manual_seed(12345)

    # Initial state: perturb a plausible baseline per cell, deterministically.
    n_tracers = 15
    base = torch.tensor(
        [
            1.0e-4, 1.0e-4,          # DFe_1, DFe_2  (approx)
            0.10, 0.10, 0.05, 0.05, 0.05,   # 5 PFTs layer 1
            0.5, 0.5,                # POC_1, POC_2
            2.0, 2.0,                # DIC_1, DIC_2
            2.3, 2.3,                # ALK_1, ALK_2
            0.01, 0.01,              # PIC_1, PIC_2
        ],
        dtype=torch.float64,
    )[:n_tracers]
    if base.numel() < n_tracers:  # pad defensively if layout differs
        base = torch.cat([base, torch.full((n_tracers - base.numel(),), 0.1, dtype=torch.float64)])

    jitter = 1.0 + 0.05 * torch.randn(n_tracers, n_cells, generator=g, dtype=torch.float64)
    state = (base[:, None] * jitter).contiguous()

    T = 10.0 + 8.0 * torch.rand(n_cells, generator=g, dtype=torch.float64)
    S = 34.0 + 1.5 * torch.rand(n_cells, generator=g, dtype=torch.float64)
    wind = 4.0 + 6.0 * torch.rand(n_cells, generator=g, dtype=torch.float64)

    hashes = []
    checkpoints = {}
    for i in range(args.steps):
        state = box.carroll6_5pft_2layer_step(
            state, params, args.dt, T=T, S=S, wind=wind
        )
        b = state.detach().contiguous().numpy().tobytes()
        hashes.append(hashlib.sha256(b).hexdigest()[:16])
        if i in (0, 9, 49, 99, args.steps - 1):
            checkpoints[str(i)] = state.detach().flatten()[:12].tolist()

    result = {
        "repo": str(repo),
        "param_names": names,
        "param_values": [float(x) for x in params],
        "steps": args.steps,
        "dt": args.dt,
        "n_cells": n_cells,
        "traj_hash": hashlib.sha256("".join(hashes).encode()).hexdigest(),
        "per_step_hashes_first10": hashes[:10],
        "final_state_sum": float(state.sum()),
        "final_state_absmax": float(state.abs().max()),
        "checkpoints": checkpoints,
        "has_phyto_process_rates": hasattr(box, "phytoplankton_process_rates"),
    }
    Path(args.out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    print(f"traj_hash={result['traj_hash']}")
    print(f"final_sum={result['final_state_sum']!r}")
    print(f"has_phyto_process_rates={result['has_phyto_process_rates']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
