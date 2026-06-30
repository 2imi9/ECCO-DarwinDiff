#!/usr/bin/env python
"""hybrid_spatial_h200.py -- spatial UDE feasibility on an H200.

Two things the 0-D probe could not show, both needed for Track 2:

  1. SCALE / launch-bound fix. The per-step rollout is launch-bound (the H200
     sat idle at ~3 s/epoch). We torch.compile the step to fuse the per-step
     kernels and report the eager-vs-compiled speedup -- the lever that makes
     the GPU actually help.

  2. A SPATIAL, ENVIRONMENT-DEPENDENT closure. Each cell of an H x W field has
     its own iron (DFe) AND a local environment scalar (think temperature /
     light / carbonate saturation -- the thing tonight's Southern-Ocean calcite
     finding says modulates the process). A neural net learns the 2-input
     closure  f(iron, env)  end-to-end through the differentiable rollout,
     batched over the whole field. Truth: f = iron-limitation(DFe) x env-window(env).

Writes a JSON result. Submit via scripts/slurm/run_hybrid_spatial_h200.sbatch.
"""
from __future__ import annotations
import argparse, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import torch
import darwindiff.carroll6 as c

DEV = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)
DT = 0.25
CARROLL = c.CARROLL_VALUES.to(DEV).float()


def norm_dfe(DFe):
    return (torch.log10(DFe.clamp_min(1e-9)) + 4.7) / 2.0


def true_ffe(DFe, env):
    # iron limitation x environmental window (the modulation we want learned)
    return (DFe / (DFe + c.K_FE)) * (0.5 + 0.5 * env)


# Module-level net so the compiled step can close over it cleanly.
NET: torch.nn.Module | None = None


def make_net(w=64):
    return torch.nn.Sequential(
        torch.nn.Linear(2, w), torch.nn.Tanh(),
        torch.nn.Linear(w, w), torch.nn.Tanh(),
        torch.nn.Linear(w, w), torch.nn.Tanh(),
        torch.nn.Linear(w, 1), torch.nn.Sigmoid(),
    ).to(DEV)


def _step(state, env, params, dt, f_fe):
    DFe, Ps, Pl, POC, PIC = state[:, 0], state[:, 1], state[:, 2], state[:, 3], state[:, 4]
    alpfe, scav = params[c.P.alpfe], params[c.P.scav_rat]
    mu_s, mu_l = params[c.P.Smallgrow], params[c.P.Biggrow]
    gd, R = params[c.P.diatomgraz], params[c.P.R_PICPOC]
    scav_pd = scav * 86400.0
    gs = mu_s * f_fe * c.LIGHT * Ps
    gl = mu_l * f_fe * c.LIGHT * Pl
    fe_up = c.Q_FE * (gs + gl)
    ms = c.M_LIN * Ps + c.M_QUAD * Ps * Ps
    ml = c.M_LIN * Pl + c.M_QUAD * Pl * Pl
    gz = gd * c.G0_GRAZE * Pl
    mt = ms + ml + gz
    dDFe = alpfe * c.PHI_DUST - scav_pd * DFe * POC - fe_up
    dPs, dPl = gs - ms, gl - ml - gz
    dPOC, dPIC = mt - c.W_SINK * POC, R * mt - c.W_SINK * PIC
    return torch.stack([DFe + dt*dDFe, Ps + dt*dPs, Pl + dt*dPl,
                        POC + dt*dPOC, PIC + dt*dPIC], dim=1)


def model_step(state, env, params, dt):
    feat = torch.stack([norm_dfe(state[:, 0]), env], dim=1)
    return _step(state, env, params, dt, NET(feat).squeeze(1))


def true_step(state, env, params, dt):
    return _step(state, env, params, dt, true_ffe(state[:, 0], env))


def rollout(step_fn, state0, env, params, n, snaps):
    # All step fns share signature (state, env, params, dt) -> uniform call.
    s, out, ss = state0, [], set(snaps)
    for k in range(1, n + 1):
        s = step_fn(s, env, params, DT)
        if k in ss:
            out.append(s)
    return torch.stack(out)


model_step_c = None  # set in main after compile


def field_ic(H, W):
    n = H * W
    dfe = torch.logspace(-6.0, -3.3, n, device=DEV)               # iron spans the knee
    env = torch.linspace(0.0, 1.0, n, device=DEV)                 # environment 0..1
    env = env[torch.randperm(n, device=DEV)] if False else env   # keep deterministic order
    rest = torch.tensor([0.1, 0.1, 0.1, 0.01], device=DEV).expand(n, 4)
    return torch.cat([dfe.unsqueeze(1), rest], dim=1), env


def main():
    global NET, model_step_c
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--H", type=int, default=128)
    ap.add_argument("--W", type=int, default=128)
    ap.add_argument("--steps", type=int, default=200)
    ap.add_argument("--epochs", type=int, default=3000)
    args = ap.parse_args()
    gpu = torch.cuda.get_device_name(0) if DEV == "cuda" else "cpu"
    ncells = args.H * args.W
    print(f"device={DEV} ({gpu}) | torch={torch.__version__} | cells={ncells} | steps={args.steps}")

    n, snaps = args.steps, list(range(20, args.steps + 1, 20))
    state0, env = field_ic(args.H, args.W)
    with torch.no_grad():
        truth = rollout(true_step, state0, env, CARROLL, n, snaps)
    scale = truth.abs().mean((0, 1)) + 1e-8

    NET = make_net()
    # --- launch-bound fix: compile the per-step kernel ---
    compiled_ok = True
    try:
        model_step_c = torch.compile(model_step)
    except Exception as e:
        compiled_ok = False
        model_step_c = model_step
        print("torch.compile failed, falling back to eager:", repr(e)[:200])

    def epoch_time(step_fn, k=5):
        # MUST warm up at the SAME shape we time at: torch.compile recompiles on a
        # shape change, so warming at n=5 then timing at n=200 measures compilation,
        # not the compiled run (this bug once made compile look 0.8x = slower).
        opt = torch.optim.Adam(NET.parameters(), lr=1e-9)  # ~no-op updates, just time the pass
        for _ in range(3):  # warmup at the timing shape
            opt.zero_grad()
            pred = rollout(step_fn, state0, env, CARROLL, n, snaps)
            (((pred - truth) / scale) ** 2).mean().backward(); opt.step()
        if DEV == "cuda":
            torch.cuda.synchronize()
        t0 = time.time()
        for _ in range(k):
            opt.zero_grad()
            pred = rollout(step_fn, state0, env, CARROLL, n, snaps)
            (((pred - truth) / scale) ** 2).mean().backward(); opt.step()
        if DEV == "cuda":
            torch.cuda.synchronize()
        return (time.time() - t0) / k

    t_eager = epoch_time(model_step)
    t_comp = epoch_time(model_step_c) if compiled_ok else float("nan")
    print(f"per-epoch: eager={t_eager*1000:.1f} ms | compiled={t_comp*1000:.1f} ms | "
          f"speedup={t_eager/t_comp:.1f}x" if compiled_ok else f"eager={t_eager*1000:.1f} ms")

    # --- train the spatial closure (compiled) ---
    NET = make_net()  # fresh
    if compiled_ok:
        model_step_c = torch.compile(model_step)
    opt = torch.optim.Adam(NET.parameters(), lr=3e-3)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, args.epochs)
    t0, loss0 = time.time(), None
    for it in range(args.epochs):
        opt.zero_grad()
        pred = rollout(model_step_c, state0, env, CARROLL, n, snaps)
        loss = (((pred - truth) / scale) ** 2).mean()
        loss.backward(); opt.step(); sched.step()
        if it == 0:
            loss0 = loss.item()
        if it % 200 == 0 or it == args.epochs - 1:
            print(f"  epoch {it:5d}/{args.epochs} loss={loss.item():.3e} {time.time()-t0:6.1f}s", flush=True)
    loss1 = loss.item()

    # closure recovery over the (iron, env) surface
    with torch.no_grad():
        gd = torch.linspace(float(truth[:, :, 0].clamp_min(1e-7).min()), float(truth[:, :, 0].max()), 60, device=DEV)
        ge = torch.linspace(0, 1, 60, device=DEV)
        DD, EE = torch.meshgrid(gd, ge, indexing="ij")
        feat = torch.stack([norm_dfe(DD.reshape(-1)), EE.reshape(-1)], dim=1)
        pred_s = NET(feat).squeeze(1)
        true_s = true_ffe(DD.reshape(-1), EE.reshape(-1))
        mae = (pred_s - true_s).abs().mean().item()

    res = {"device": DEV, "gpu": gpu, "torch": torch.__version__, "cells": ncells,
           "rollout_steps": n, "epochs": args.epochs, "compiled": compiled_ok,
           "per_epoch_eager_ms": round(t_eager * 1000, 1),
           "per_epoch_compiled_ms": round(t_comp * 1000, 1) if compiled_ok else None,
           "compile_speedup": round(t_eager / t_comp, 1) if compiled_ok else None,
           "loss_init": loss0, "loss_final": loss1, "loss_drop_x": loss0 / max(loss1, 1e-12),
           "closure2d_MAE": mae, "train_sec": round(time.time() - t0, 1),
           "PASS": loss1 < loss0 / 100 and mae < 0.03}
    print(json.dumps(res, indent=2))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(res, open(args.out, "w"), indent=2)
        print("wrote", args.out)
    return 0 if res["PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
