"""Part 2 of the refactor-equivalence check: float32 forward AND gradients.

Part 1 showed the float64 forward trajectory is bitwise identical across the refactor. That is
necessary but not sufficient for the flagship, because:

  * training runs in float32, where a re-association of the same algebra CAN change the result;
  * recovery is driven by d(loss)/d(params) THROUGH the box, so the autograd graph is what
    actually has to match, not just the forward value.

Emits float32 trajectory hashes and the parameter gradient of a scalar objective.
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
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--dt", type=float, default=0.25)
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    sys.path.insert(0, str(repo / "src"))

    from darwindiff import carroll6
    from darwindiff import carroll6_5pft_2layer as box

    torch.manual_seed(0)
    out: dict = {"repo": str(repo), "steps": args.steps, "dt": args.dt}

    for dtype_name, dtype in (("float32", torch.float32), ("float64", torch.float64)):
        g = torch.Generator().manual_seed(12345)
        n_cells, n_tracers = 37, 15

        params = torch.tensor(
            [p.carroll_value for p in carroll6.PARAMS], dtype=dtype, requires_grad=True
        )

        base = torch.tensor(
            [1.0e-4, 1.0e-4, 0.10, 0.10, 0.05, 0.05, 0.05,
             0.5, 0.5, 2.0, 2.0, 2.3, 2.3, 0.01, 0.01],
            dtype=dtype,
        )[:n_tracers]
        jitter = 1.0 + 0.05 * torch.randn(n_tracers, n_cells, generator=g, dtype=dtype)
        state = (base[:, None] * jitter).contiguous()

        T = (10.0 + 8.0 * torch.rand(n_cells, generator=g, dtype=dtype))
        S = (34.0 + 1.5 * torch.rand(n_cells, generator=g, dtype=dtype))
        wind = (4.0 + 6.0 * torch.rand(n_cells, generator=g, dtype=dtype))

        hashes = []
        for _ in range(args.steps):
            state = box.carroll6_5pft_2layer_step(state, params, args.dt, T=T, S=S, wind=wind)
            hashes.append(
                hashlib.sha256(
                    state.detach().contiguous().numpy().tobytes()
                ).hexdigest()[:16]
            )

        # A scalar objective that touches every tracer, then differentiate wrt the 6 params.
        loss = (state ** 2).mean() + state.abs().sum()
        (grad,) = torch.autograd.grad(loss, params)

        out[dtype_name] = {
            "traj_hash": hashlib.sha256("".join(hashes).encode()).hexdigest(),
            "final_sum": float(state.sum()),
            "loss": float(loss),
            "param_grad": [float(x) for x in grad],
            "grad_hash": hashlib.sha256(
                grad.detach().contiguous().numpy().tobytes()
            ).hexdigest(),
        }

    out["has_phyto_process_rates"] = hasattr(box, "phytoplankton_process_rates")
    Path(args.out).write_text(json.dumps(out, indent=1), encoding="utf-8")
    for k in ("float32", "float64"):
        print(f"{k}: traj={out[k]['traj_hash'][:16]} grad={out[k]['grad_hash'][:16]}")
    print("has_phyto_process_rates=", out["has_phyto_process_rates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
