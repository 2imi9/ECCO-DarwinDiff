"""H200 smoke test for the semi-implicit (IMEX) vertical-diffusion fix.

Validates on the real GPU (fp32/CUDA) that transport.imex_rollout removes the
explicit vertical-diffusion CFL wall that silently NaNs at realistic mixed-layer kz:

  1. CORRECTNESS: at a large diffusion number r=kz*dt/dz^2 (>> 0.5), a plain EXPLICIT
     rollout blows up / NaNs, while imex_rollout stays finite and bounded.
  2. CHECKPOINT-EQUIVALENCE on GPU: checkpointed rollout == plain rollout (bit-identical),
     the gate windowed-BPTT relies on.
  3. GRADIENT FLOW: d(loss)/d(params) is finite and non-zero through the IMEX rollout.
  4. THROUGHPUT: wall-clock + peak memory on an eqpac-scale and a larger grid.

Run on Explorer:  sbatch scripts/slurm/run_imex_h200_smoke.sbatch
or interactively:  srun -p gpu --gres=gpu:1 -t 0:10:00 python scripts/imex_h200_smoke.py
Falls back to CPU (fp64) if CUDA is unavailable, so it is runnable locally too.
"""
from __future__ import annotations

import time

import torch

from darwindiff.transport import grid_tendency, imex_rollout


def _device_dtype():
    if torch.cuda.is_available():
        return torch.device("cuda"), torch.float32
    return torch.device("cpu"), torch.float64


def _state(ny, nx, nz, ntr, device, dtype):
    torch.manual_seed(0)
    return (torch.rand(ny, nx, nz, ntr, device=device, dtype=dtype) * 0.1 + 0.05)


def _tendency(params, u, v, dz, *, bgc=True):
    # EXPLICIT part only (include_vdiff=False): [BGC +] advection + horizontal diffusion.
    def tend(t, x):
        return grid_tendency(
            x, params, u=u, v=v, dx=1.0e5, dy=1.0e5, kz=0.0, dz=dz, kh=50.0,
            include_vdiff=False, bgc=bgc,
        )
    return tend


def main() -> int:
    device, dtype = _device_dtype()
    print(f"[imex-h200] device={device} dtype={dtype} "
          f"torch={torch.__version__} cuda={torch.version.cuda}")
    if device.type == "cuda":
        print(f"[imex-h200] gpu={torch.cuda.get_device_name(0)} "
              f"cap={torch.cuda.get_device_capability(0)}")

    ny, nx, nz, ntr = 21, 51, 8, 7        # eqpac-scale AOI grid, 7-tracer (DIC/ALK)
    dz, dt = 10.0, 0.25                    # 10 m layers, 0.25 d step
    kz = 864.0                             # ~1e-2 m^2/s mixed-layer turbulent diffusivity (m^2/day)
    r = kz * dt / (dz * dz)                # = 2.16 -> explicit UNSTABLE (needs r<0.5)
    print(f"[imex-h200] grid=({ny},{nx},{nz},{ntr}) dz={dz} dt={dt} kz={kz} -> CFL r={r:.3g} "
          f"(explicit stable only for r<0.5, so this is the realistic-unstable regime)")

    params = torch.tensor([0.928, 1e-8, 1.0, 1.0, 1.0, 0.0425],
                          device=device, dtype=dtype, requires_grad=True)
    u = torch.zeros(ny, nx, device=device, dtype=dtype)
    v = torch.zeros(ny, nx, device=device, dtype=dtype)
    state = _state(ny, nx, nz, ntr, device, dtype)
    n_steps = 40
    ok = True

    # 1. Pure transport (bgc=False) isolates the diffusion instability: imex stays finite
    #    and bounded (diffusion decays toward vertical-uniform), explicit blows up / NaNs.
    tend_pt = _tendency(params, u, v, dz, bgc=False)
    out = imex_rollout(tend_pt, state, dt=dt, n_steps=n_steps, kz=kz, dz=dz)
    imex_finite = bool(torch.isfinite(out).all())
    imex_growth = float((out.abs().max() / state.abs().max()).detach())
    print(f"[1] imex (pure transport) finite={imex_finite} growth={imex_growth:.3g} "
          f"({'PASS' if imex_finite and imex_growth < 2 else 'FAIL'})")
    ok &= imex_finite and imex_growth < 2

    # 1b. EXPLICIT rollout at the same r -> blows up / NaN (the bug the fix removes)
    x = state.detach().clone()
    pdet = params.detach()
    for _ in range(n_steps):
        x = x + dt * grid_tendency(x, pdet, u=u, v=v, dx=1.0e5, dy=1.0e5,
                                   kz=kz, dz=dz, kh=50.0, include_vdiff=True, bgc=False)
    expl_finite = bool(torch.isfinite(x).all())
    expl_growth = float(x.abs().max() / state.abs().max()) if expl_finite else float("inf")
    demonstrated = (not expl_finite) or (expl_growth > 1e6)
    print(f"[1b] EXPLICIT (pure transport) finite={expl_finite} growth={expl_growth:.3g} "
          f"({'PASS (wall demonstrated: explicit dead, imex alive)' if demonstrated else 'FAIL: explicit did not blow up'})")
    ok &= demonstrated

    # 2-4 exercise the full BGC closures (bgc=True) through the same stable IMEX rollout.
    tend = _tendency(params, u, v, dz, bgc=True)

    # 2. checkpoint-equivalence on-device (n_steps=40 not divisible by segment=7)
    plain = imex_rollout(tend, state, dt=dt, n_steps=n_steps, kz=kz, dz=dz)
    ckpt = imex_rollout(tend, state, dt=dt, n_steps=n_steps, kz=kz, dz=dz, checkpoint_segment=7)
    eq = torch.equal(plain, ckpt)
    print(f"[2] checkpoint==plain: {eq} ({'PASS' if eq else 'FAIL'})")
    ok &= eq

    # 3. gradient flow
    loss = imex_rollout(tend, state, dt=dt, n_steps=n_steps, kz=kz, dz=dz).pow(2).mean()
    g = torch.autograd.grad(loss, params)[0]
    gfinite = bool(torch.isfinite(g).all()) and float(g.norm()) > 0
    print(f"[3] grad->params finite&nonzero: {gfinite} norm={float(g.norm()):.3g} "
          f"({'PASS' if gfinite else 'FAIL'})")
    ok &= gfinite

    # 4. throughput on a larger grid
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats()
    by, bx, bz = 128, 128, 20
    bstate = _state(by, bx, bz, ntr, device, dtype)
    bu = torch.zeros(by, bx, device=device, dtype=dtype)
    bv = torch.zeros(by, bx, device=device, dtype=dtype)
    btend = _tendency(params, bu, bv, dz)
    if device.type == "cuda":
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    bout = imex_rollout(btend, bstate, dt=dt, n_steps=n_steps, kz=kz, dz=dz,
                        checkpoint_segment=10)
    bloss = bout.pow(2).mean()
    bloss.backward()
    if device.type == "cuda":
        torch.cuda.synchronize()
    dt_wall = time.perf_counter() - t0
    ncell = by * bx * bz
    mem = (torch.cuda.max_memory_allocated() / 1e9) if device.type == "cuda" else float("nan")
    print(f"[4] big grid ({by}x{bx}x{bz}={ncell} cells) {n_steps} steps fwd+bwd: "
          f"{dt_wall:.2f}s peak_mem={mem:.2f}GB finite={bool(torch.isfinite(bout).all())}")

    print(f"[imex-h200] {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
