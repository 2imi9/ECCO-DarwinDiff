#!/usr/bin/env python3
"""Overnight H200 de-risking sweep for the Track-2 differentiable transport UDE.

Three experiments, each JSON-logged and resumable (a `.done_<tag>` marker is
written per config so a re-launch skips finished work; drop a `STOP` file in the
out-dir to halt cleanly):

  EXP-A  memory & wall-clock envelope: full transport+BGC forward+backward across
         (n_cols, n_z, n_steps, checkpoint) -> find the H200 ceiling and the
         checkpointing payoff (informs the Phase-1 scaling + #119).
  EXP-B  mass conservation vs rollout length: transport-only RK4 vs Euler ->
         the decadal budget-drift check at scale (#7).
  EXP-C  neural-closure recovery (self-twin): train a neural iron-limitation
         closure to recover a known nonlinear f_fe inside the batched model ->
         trainability + recovery at scale (de-risks the UDE closure).

Nothing here is a science "recovery number", so it is not gated by verify_run.py;
every measurement is a numeric/infra property recomputed from an actual run.

Usage:
    python scripts/ude_transport_stress_h200.py --out-dir runs/ude_stress [--quick]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import torch
from torch import nn

from darwindiff import carroll6
from darwindiff.integrators import integrate, relative_mass_drift
from darwindiff.transport import column_tendency


def _base_field(n_cols: int, n_z: int, device, seed: int = 0) -> torch.Tensor:
    g = torch.Generator(device="cpu").manual_seed(seed)
    base = torch.tensor([1.0e-4, 0.2, 0.2, 0.5, 0.02])
    f = base * (1.0 + 0.1 * torch.rand(n_cols, n_z, 5, generator=g))
    return f.to(device)


def _sync(device):
    if device.type == "cuda":
        torch.cuda.synchronize()


def _write(out: Path, tag: str, rec: dict) -> None:
    (out / f"{tag}.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    (out / f".done_{tag}").touch()


def _stopped(out: Path) -> bool:
    return (out / "STOP").exists()


# --------------------------------------------------------------------------- A
def exp_a_envelope(out: Path, device, params, quick: bool) -> None:
    cols = [1_000, 10_000] if quick else [1_000, 10_000, 100_000, 500_000]
    zs = [12, 50]
    steps_list = [200, 2000] if quick else [200, 2000, 20_000]
    ckpts = [None, 200]
    for nc in cols:
        for nz in zs:
            for ns in steps_list:
                for ck in ckpts:
                    tag = f"A_c{nc}_z{nz}_s{ns}_ck{ck or 0}"
                    if (out / f".done_{tag}").exists() or _stopped(out):
                        continue
                    rec: dict = {"exp": "A", "n_cols": nc, "n_z": nz, "n_steps": ns,
                                 "checkpoint": ck, "method": "rk4"}
                    try:
                        if device.type == "cuda":
                            torch.cuda.reset_peak_memory_stats()
                            torch.cuda.empty_cache()
                        f0 = _base_field(nc, nz, device).requires_grad_(True)

                        def tend(s):
                            return column_tendency(s, params, kz=0.1, dz=25.0, w=0.5)

                        t0 = time.perf_counter()
                        fN = integrate(tend, f0, dt=0.25, n_steps=ns, method="rk4",
                                       checkpoint_segment=ck)
                        loss = fN.pow(2).mean()
                        _sync(device)
                        t_fwd = time.perf_counter() - t0
                        t1 = time.perf_counter()
                        loss.backward()
                        _sync(device)
                        t_bwd = time.perf_counter() - t1
                        gnorm = f0.grad.norm().item()
                        rec.update(
                            status="ok",
                            t_fwd_s=round(t_fwd, 4), t_bwd_s=round(t_bwd, 4),
                            peak_mem_gb=(round(torch.cuda.max_memory_allocated() / 2**30, 3)
                                         if device.type == "cuda" else None),
                            grad_norm=gnorm, grad_finite=bool(torch.isfinite(f0.grad).all()),
                            final_finite=bool(torch.isfinite(fN).all()),
                        )
                    except RuntimeError as e:
                        rec.update(status="OOM" if "out of memory" in str(e).lower() else "error",
                                   error=str(e)[:200])
                        if device.type == "cuda":
                            torch.cuda.empty_cache()
                    _write(out, tag, rec)
                    print(f"[A] {tag}: {rec.get('status')} "
                          f"mem={rec.get('peak_mem_gb')}GB fwd={rec.get('t_fwd_s')}s "
                          f"bwd={rec.get('t_bwd_s')}s", flush=True)


# --------------------------------------------------------------------------- B
def exp_b_conservation(out: Path, device, params, quick: bool) -> None:
    steps_list = [200, 2000] if quick else [200, 2000, 20_000, 100_000]
    for method in ("rk4", "euler"):
        for ns in steps_list:
            tag = f"B_{method}_s{ns}"
            if (out / f".done_{tag}").exists() or _stopped(out):
                continue
            rec = {"exp": "B", "method": method, "n_steps": ns, "n_cols": 2000, "n_z": 24}
            try:
                f0 = _base_field(2000, 24, device)

                def tend(s):
                    return column_tendency(s, params, kz=0.1, dz=25.0, w=1.0, bgc=False)

                t0 = time.perf_counter()
                with torch.no_grad():
                    fN = integrate(tend, f0, dt=0.25, n_steps=ns, method=method)
                _sync(device)
                drift = relative_mass_drift(f0, fN).item()
                per_cell = ((fN.sum(-2) - f0.sum(-2)).abs() / f0.sum(-2).abs()).max().item()
                rec.update(status="ok", wall_s=round(time.perf_counter() - t0, 3),
                           global_mass_drift=drift, max_per_cell_drift=per_cell,
                           final_finite=bool(torch.isfinite(fN).all()))
            except RuntimeError as e:
                rec.update(status="error", error=str(e)[:200])
            _write(out, tag, rec)
            print(f"[B] {tag}: drift={rec.get('global_mass_drift'):.2e} "
                  if rec.get("status") == "ok" else f"[B] {tag}: {rec.get('status')}", flush=True)


# --------------------------------------------------------------------------- C
def _true_ffe(dfe: torch.Tensor) -> torch.Tensor:
    # a deliberately different, nonlinear iron-limitation law to recover
    k = 8.0e-5
    return (dfe / (dfe + k)) ** 0.7


def exp_c_closure_recovery(out: Path, device, params, quick: bool) -> None:
    tag = "C_closure_recovery"
    if (out / f".done_{tag}").exists() or _stopped(out):
        return
    n_cols, n_z, ns = (500, 8, 150) if quick else (2000, 12, 200)
    epochs = 150 if quick else 400
    f0 = _base_field(n_cols, n_z, device)

    def make_tend(ffe):
        def tend(s):
            return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe)
        return tend

    with torch.no_grad():
        target = integrate(make_tend(_true_ffe), f0, dt=0.25, n_steps=ns, method="rk4")

    net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 16), nn.Tanh(),
                        nn.Linear(16, 1), nn.Sigmoid()).to(device)

    def ffe_net(dfe):
        return net(dfe.unsqueeze(-1)).squeeze(-1)

    opt = torch.optim.Adam(net.parameters(), lr=5e-3)
    losses = []
    for ep in range(epochs):
        if _stopped(out):
            break
        opt.zero_grad()
        pred = integrate(make_tend(ffe_net), f0, dt=0.25, n_steps=ns, method="rk4",
                         checkpoint_segment=50)
        loss = (pred - target).pow(2).mean()
        loss.backward()
        opt.step()
        losses.append(loss.item())
        if ep % 25 == 0:
            print(f"[C] epoch {ep}: loss={loss.item():.3e}", flush=True)

    # recovery: closure match over the FULL DFe range vs the actually-VISITED range
    # (the honest identifiability metric -- outside the visited range the closure is
    # unconstrained, so a large full-range error can be pure extrapolation).
    lo, hi = _visited_dfe(target)
    with torch.no_grad():
        rel_full = _closure_rel_err(ffe_net, 1e-6, 1e-3, device)
        rel_vis = _closure_rel_err(ffe_net, lo, hi, device)
    rec = {"exp": "C", "n_cols": n_cols, "n_z": n_z, "n_steps": ns, "epochs": epochs,
           "status": "ok", "loss_start": losses[0] if losses else None,
           "loss_final": losses[-1] if losses else None,
           "loss_reduction_x": (losses[0] / losses[-1]) if losses and losses[-1] > 0 else None,
           "closure_rel_err_full": rel_full, "closure_rel_err_visited": rel_vis,
           "visited_dfe": [lo, hi]}
    _write(out, tag, rec)
    print(f"[C] done: loss {rec['loss_start']:.2e} -> {rec['loss_final']:.2e}, "
          f"closure rel-err full={rel_full:.3f} visited={rel_vis:.3f}", flush=True)


# --------------------------------------------------------------------------- D
def _visited_dfe(target: torch.Tensor) -> tuple[float, float]:
    dfe = target[..., 0].flatten()
    lo = torch.quantile(dfe, 0.02).clamp_min(1e-8).item()
    hi = torch.quantile(dfe, 0.98).clamp_min(1e-7).item()
    return lo, hi


def _closure_rel_err(net_fn, lo: float, hi: float, device) -> float:
    grid = torch.logspace(math.log10(lo), math.log10(hi), 100, device=device)
    return ((net_fn(grid) - _true_ffe(grid)).abs()
            / _true_ffe(grid).clamp_min(1e-8)).mean().item()


def exp_d_regularized_recovery(out: Path, device, params, quick: bool) -> None:
    """Does the design-brief mitigation (L2 + soft-prior anchor to the mechanistic
    Carroll f_fe) cure the EXP-C equifinality -- i.e. recover the closure, not just
    the trajectory? Sweeps (weight_decay, anchor_lambda)."""
    from darwindiff.carroll6 import K_FE
    n_cols, n_z, ns = (500, 8, 150) if quick else (2000, 12, 200)
    epochs = 150 if quick else 400
    f0 = _base_field(n_cols, n_z, device)

    def make_tend(ffe):
        def tend(s):
            return column_tendency(s, params, kz=0.1, dz=25.0, ffe_closure=ffe)
        return tend

    with torch.no_grad():
        target = integrate(make_tend(_true_ffe), f0, dt=0.25, n_steps=ns, method="rk4")
    lo, hi = _visited_dfe(target)
    anchor_grid = torch.logspace(math.log10(lo), math.log10(hi), 64, device=device)

    def mech(d):  # the Carroll mechanistic iron-limitation the net anchors toward
        return d / (d + K_FE)

    combos = ([(0.0, 0.0), (1e-3, 1e-2)] if quick
              else [(0.0, 0.0), (1e-3, 0.0), (0.0, 1e-2), (1e-3, 1e-2)])
    for wd, anch in combos:
        tag = f"D_wd{wd}_anch{anch}"
        if (out / f".done_{tag}").exists() or _stopped(out):
            continue
        net = nn.Sequential(nn.Linear(1, 16), nn.Tanh(), nn.Linear(16, 16), nn.Tanh(),
                            nn.Linear(16, 1), nn.Sigmoid()).to(device)

        def ffe_net(dfe):
            return net(dfe.unsqueeze(-1)).squeeze(-1)

        opt = torch.optim.Adam(net.parameters(), lr=5e-3, weight_decay=wd)
        data_losses = []
        for ep in range(epochs):
            if _stopped(out):
                break
            opt.zero_grad()
            pred = integrate(make_tend(ffe_net), f0, dt=0.25, n_steps=ns, method="rk4",
                             checkpoint_segment=50)
            data_loss = (pred - target).pow(2).mean()
            loss = data_loss
            if anch > 0.0:
                loss = loss + anch * (ffe_net(anchor_grid) - mech(anchor_grid)).pow(2).mean()
            loss.backward()
            opt.step()
            data_losses.append(data_loss.item())
        with torch.no_grad():
            rel_vis = _closure_rel_err(ffe_net, lo, hi, device)
            rel_full = _closure_rel_err(ffe_net, 1e-6, 1e-3, device)
        rec = {"exp": "D", "weight_decay": wd, "anchor_lambda": anch,
               "n_cols": n_cols, "n_z": n_z, "n_steps": ns, "epochs": epochs, "status": "ok",
               "data_loss_final": data_losses[-1] if data_losses else None,
               "closure_rel_err_visited": rel_vis, "closure_rel_err_full": rel_full,
               "visited_dfe": [lo, hi]}
        _write(out, tag, rec)
        print(f"[D] wd={wd} anch={anch}: data_loss={rec['data_loss_final']:.2e} "
              f"closure_rel_err(visited)={rel_vis:.3f}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--quick", action="store_true", help="tiny grids for a smoke test")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    params = carroll6.CARROLL_VALUES.to(device)

    info = {"device": device.type,
            "gpu": torch.cuda.get_device_name(0) if device.type == "cuda" else None,
            "torch": torch.__version__,
            "total_mem_gb": (round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1)
                             if device.type == "cuda" else None)}
    (out / "device_info.json").write_text(json.dumps(info, indent=1), encoding="utf-8")
    print(f"device={info['device']} gpu={info['gpu']} mem={info['total_mem_gb']}GB "
          f"torch={info['torch']}", flush=True)

    # Training experiments (C/D) run FIRST on a clean CUDA context; the
    # memory-envelope sweep (A) deliberately OOMs, and a caught CUDA OOM poisons
    # the context so a later cuBLAS alloc (a training Linear) fails -- so A runs
    # LAST, after everything that needs a healthy context. See
    # memory/reference_cuda_oom_context_poison.md.
    exp_c_closure_recovery(out, device, params, args.quick)
    exp_d_regularized_recovery(out, device, params, args.quick)
    exp_b_conservation(out, device, params, args.quick)
    exp_a_envelope(out, device, params, args.quick)
    print("SWEEP COMPLETE", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
