"""H200 synthetic-twin validation of the windowed-BPTT trainer MACHINERY.

Fits a learned env-driven calcite closure through a genuine prescribed-transport spatial
rollout (divergence-free advection + diffusion) at eqpac scale, and checks the trainer
recovers it against a BLOCKED hold-out and beats the null-closure baseline.

**Honest scope (read this).** This validates the trainer *machinery* — optimization
through the spatial rollout, held-out recovery, the learned-vs-null delta — NOT the E2
scientific thesis. Two reasons it is not an E2 result:
  1. The "truth" is a KNOWN closure in the hypothesis class, so the fit is a self-twin,
     not real ECCO-Darwin.
  2. The closure is **per-cell in env** (g(env)), so held-out recovery comes from
     ENV-interpolation, and a flexible closure can ABSORB transport differences. Hence
     the K_num ablation below is **non-discriminating on a self-twin** (delta ~ flat in
     kh) — it only bites on real, out-of-class data where the closure cannot compensate.
     The K_num result is reported as a diagnostic; it does NOT gate the pass.
So: PASS = the machinery recovers the closure and beats null under a blocked hold-out
through real advective transport. The real E2 gate needs DB-2 (v05 velocity) + DB-3
(real held-out obs) and an out-of-class target.

Run:  sbatch scripts/slurm/run_e2_twin_h200.sbatch  (or srun ... python this)
Falls back to CPU (fp64) if CUDA is unavailable.
"""
from __future__ import annotations

import time

import torch

from darwindiff.carroll6 import CARROLL_VALUES
from darwindiff.closures import EnvCalciteClosure
from darwindiff.trainer import (
    TransportConfig,
    masked_r2,
    picpoc_observable,
    rollout_field,
    train_ude_closure,
)
from darwindiff.transport import w_from_continuity


def _device_dtype():
    if torch.cuda.is_available():
        return torch.device("cuda"), torch.float32
    return torch.device("cpu"), torch.float64


def _truth_closure(env, dtype, device):
    c = EnvCalciteClosure(env, A=1.0)
    with torch.no_grad():
        c.net[0].weight.zero_(); c.net[0].weight[0, 0] = 2.0; c.net[0].bias.zero_()
        c.net[2].weight.zero_(); c.net[2].weight[0, 0] = 1.0; c.net[2].bias.zero_()
        c.net[-1].weight.zero_(); c.net[-1].weight[0, 0] = 1.2; c.net[-1].bias.zero_()
    return c.to(device=device, dtype=dtype)


def _blocked_val_mask(ny, nx, nz, block=3, device=None):
    """Checkerboard of `block`x`block` spatial blocks held out (blocked CV)."""
    by = (torch.arange(ny, device=device) // block) % 2
    bx = (torch.arange(nx, device=device) // block) % 2
    tile = (by[:, None] ^ bx[None, :]).bool()
    return tile[:, :, None].expand(ny, nx, nz).clone()


def _divfree_velocity(ny, nx, nz, dx, dy, dz, device, dtype):
    """A prescribed advecting field made discretely divergence-free via A1's
    w_from_continuity, so the rollout genuinely transports tracers (couples cells) while
    conserving mass -- unlike u=v=0, which leaves the columns nearly independent."""
    yy = torch.linspace(-1, 1, ny, device=device, dtype=dtype).view(ny, 1)
    xx = torch.linspace(-1, 1, nx, device=device, dtype=dtype).view(1, nx)
    u = (0.4 * torch.cos(1.5708 * yy)).expand(ny, nx).contiguous()  # zonal jet, y-shear
    v = (0.15 * torch.sin(3.1416 * xx)).expand(ny, nx).contiguous()  # weak meridional
    w = w_from_continuity(u, v, dx, dy, dz, nz)                      # [Y,X,Z+1], div-free
    return u, v, w


def main() -> int:
    device, dtype = _device_dtype()
    torch.manual_seed(0)
    print(f"[e2-twin] device={device} dtype={dtype} torch={torch.__version__}")
    if device.type == "cuda":
        print(f"[e2-twin] gpu={torch.cuda.get_device_name(0)} cap={torch.cuda.get_device_capability(0)}")

    ny, nx, nz, ntr = 21, 51, 6, 5
    n_steps, epochs = 60, 80
    dx, dy, dz = 1e5, 1e5, 10.0
    yy = torch.linspace(-1, 1, ny, device=device, dtype=dtype).view(ny, 1, 1)
    xx = torch.linspace(-1, 1, nx, device=device, dtype=dtype).view(1, nx, 1)
    env = torch.stack([
        (yy + 0.5 * xx).expand(ny, nx, nz),
        torch.sin(3.0 * xx).expand(ny, nx, nz),
    ], dim=-1).contiguous()
    params = torch.tensor([CARROLL_VALUES[i] for i in range(6)], device=device, dtype=dtype)
    ic = (torch.rand(ny, nx, nz, ntr, device=device, dtype=dtype) * 0.1 + 0.05)
    u, v, w = _divfree_velocity(ny, nx, nz, dx, dy, dz, device, dtype)
    val_mask = _blocked_val_mask(ny, nx, nz, block=3, device=device)
    train_mask = ~val_mask
    print(f"[e2-twin] grid=({ny},{nx},{nz}) advecting (|u|max={float(u.abs().max()):.2f}) "
          f"blocked hold-out {int(val_mask.float().mean()*100)}% of cells")

    KH_TRUTH = 50.0
    tc_truth = TransportConfig(dx=dx, dy=dy, dz=dz, dt=0.25, kz=50.0, kh=KH_TRUTH, u=u, v=v, w=w)
    truth = _truth_closure(env, dtype, device)
    target = picpoc_observable(rollout_field(ic, params, tc_truth, n_steps, calcite_closure=truth)).detach()

    def run_at_kh(kh: float):
        tc = TransportConfig(dx=dx, dy=dy, dz=dz, dt=0.25, kz=50.0, kh=kh, u=u, v=v, w=w)
        null = EnvCalciteClosure(env, A=1.0).to(device=device, dtype=dtype)
        r2_null = float(masked_r2(
            picpoc_observable(rollout_field(ic, params, tc, n_steps, calcite_closure=null)),
            target, val_mask))
        clo = EnvCalciteClosure(env, A=1.0).to(device=device, dtype=dtype)
        res = train_ude_closure(
            clo, ic, params, tc, n_steps, observable=picpoc_observable, target=target,
            train_mask=train_mask, val_mask=val_mask, epochs=epochs, lr=5e-2,
            checkpoint_segment=15, log_every=epochs,
        )
        r2_learned = float(masked_r2(picpoc_observable(res.final_field), target, val_mask))
        return r2_learned, r2_null, r2_learned - r2_null

    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(); torch.cuda.synchronize()
    t0 = time.perf_counter()

    print("\n[e2-twin] MACHINERY validation (blocked hold-out, advective transport):")
    r2_l, r2_n, delta = run_at_kh(KH_TRUTH)
    ok = r2_l > 0.5 and delta > 0.1
    print(f"  held-out R2  learned={r2_l:+.3f}  null={r2_n:+.3f}  DELTA={delta:+.3f}  "
          f"({'PASS (recovers + beats null through real transport)' if ok else 'FAIL'})")

    print("\n[e2-twin] K_num diagnostic (NON-gating -- expected flat on a self-twin):")
    ladder = [(kh, run_at_kh(kh)[2]) for kh in [KH_TRUTH, 4 * KH_TRUTH, 16 * KH_TRUTH]]
    for kh, d in ladder:
        print(f"  kh={kh:7.0f}  delta={d:+.3f}")
    flat = (max(d for _, d in ladder) - min(d for _, d in ladder)) < 0.1
    print(f"  -> delta ~flat across kh? {flat}  "
          f"(EXPECTED on a self-twin: the per-cell env closure absorbs transport; K_num "
          f"only discriminates on real out-of-class data -- see module docstring)")

    if device.type == "cuda":
        torch.cuda.synchronize()
    wall = time.perf_counter() - t0
    mem = (torch.cuda.max_memory_allocated() / 1e9) if device.type == "cuda" else float("nan")
    print(f"\n[e2-twin] {wall:.1f}s  peak_mem={mem:.2f}GB  "
          f"{'MACHINERY VALIDATED (not an E2 result -- see honest-scope docstring)' if ok else 'CHECK RESULTS'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
