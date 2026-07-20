#!/usr/bin/env python
"""hybrid_h200_train.py -- scaled GPU training of the differentiable-BGC / UDE
hybrid, to tighten the laptop feasibility probe on an H200.

Headline upgrade over the CPU probe: the iron-limitation closure f_fe(DFe) is
learned by a neural net INSIDE the real differentiable biogeochemistry, trained
across a BATCH of initial conditions spanning the iron-limitation knee (so the
net sees the whole curve, not 4 points) -- both on clean and on 5%-noisy
targets. Plus GPU confirmations of deep gradient flow and exact param recovery.

Writes a JSON result. Run on the cluster via scripts/slurm/run_hybrid_h200.sbatch.
"""
from __future__ import annotations
import argparse, json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import torch
import darwindiff.carroll6 as c

DEV = "cuda" if torch.cuda.is_available() else "cpu"
torch.manual_seed(0)
DT = 0.25

_NEED = ["K_FE", "PHI_DUST", "LIGHT", "Q_FE", "M_LIN", "M_QUAD", "G0_GRAZE", "W_SINK"]
for _k in _NEED:
    assert hasattr(c, _k), f"carroll6 missing constant {_k}"
CARROLL = c.CARROLL_VALUES.to(DEV).float()
FFE_TRUE = lambda x: x / (x + c.K_FE)


def bgc_step_b(state, params, dt, ffe_fn):
    """Batched one-step BGC: state [B,5]; ffe_fn maps [B,1]->[B,1]."""
    DFe, Ps, Pl, POC, PIC = state[:, 0], state[:, 1], state[:, 2], state[:, 3], state[:, 4]
    alpfe, scav = params[c.P.alpfe], params[c.P.scav_rat]
    mu_s, mu_l = params[c.P.Smallgrow], params[c.P.Biggrow]
    gd, R = params[c.P.diatomgraz], params[c.P.R_PICPOC]
    scav_pd = scav * 86400.0
    f_fe = ffe_fn(DFe.unsqueeze(1)).squeeze(1)
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


def rollout_b(state0, params, dt, n, ffe_fn, snaps):
    s, out, snapset = state0, [], set(snaps)
    for k in range(1, n + 1):
        s = bgc_step_b(s, params, dt, ffe_fn)
        if k in snapset:
            out.append(s)
    return torch.stack(out)  # [n_snaps, B, 5]


def make_net(w=64):
    return torch.nn.Sequential(
        torch.nn.Linear(1, w), torch.nn.Tanh(),
        torch.nn.Linear(w, w), torch.nn.Tanh(),
        torch.nn.Linear(w, w), torch.nn.Tanh(),
        torch.nn.Linear(w, 1), torch.nn.Sigmoid(),
    ).to(DEV)


def batch_ic(B):
    dfe0 = torch.logspace(-6.0, -3.3, B, device=DEV)             # ~1e-6 .. 5e-4, spans the knee
    rest = torch.tensor([0.1, 0.1, 0.1, 0.01], device=DEV).expand(B, 4)
    return torch.cat([dfe0.unsqueeze(1), rest], dim=1)


def train_ude(noise=0.0, epochs=3500, B=256, n=200, w=64, lr=3e-3):
    snaps = list(range(20, n + 1, 20))
    state0 = batch_ic(B)
    with torch.no_grad():
        clean = rollout_b(state0, CARROLL, DT, n, FFE_TRUE, snaps)
        target = clean.clone()
        if noise > 0:
            target = target * (1.0 + noise * torch.randn_like(target))
        dfe_lo = float(clean[:, :, 0].clamp_min(1e-7).min())
        dfe_hi = float(clean[:, :, 0].max())
    net = make_net(w)
    opt = torch.optim.Adam(net.parameters(), lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    scale = target.abs().mean((0, 1)) + 1e-8
    t0, loss0 = time.time(), None
    for it in range(epochs):
        opt.zero_grad()
        pred = rollout_b(state0, CARROLL, DT, n, net, snaps)
        loss = (((pred - target) / scale) ** 2).mean()
        loss.backward(); opt.step(); sched.step()
        if it == 0:
            loss0 = loss.item()
        if it % 250 == 0 or it == epochs - 1:
            print(f"  [ude noise={noise}] epoch {it:5d}/{epochs}  loss={loss.item():.3e}  "
                  f"{time.time()-t0:5.1f}s", flush=True)
    loss1 = loss.item()
    with torch.no_grad():
        grid = torch.linspace(dfe_lo, dfe_hi, 400, device=DEV).unsqueeze(1)
        mae = (net(grid).squeeze(1) - FFE_TRUE(grid.squeeze(1))).abs().mean().item()
        rmse = ((net(grid).squeeze(1) - FFE_TRUE(grid.squeeze(1))) ** 2).mean().sqrt().item()
    return {"noise": noise, "epochs": epochs, "batch_ics": B, "rollout_steps": n,
            "loss_init": loss0, "loss_final": loss1, "loss_drop_x": loss0 / max(loss1, 1e-12),
            "ffe_curve_MAE": mae, "ffe_curve_RMSE": rmse, "train_sec": round(time.time() - t0, 1),
            "PASS": loss1 < loss0 / 100 and mae < 0.02}


def grad_depth(n=1500):
    p = CARROLL.clone().requires_grad_(True)
    s = batch_ic(1)
    out = rollout_b(s, p, DT, n, FFE_TRUE, [n])
    loss = (out ** 2).sum()
    loss.backward()
    g = p.grad
    return {"n_steps": n, "grad_norm": float(g.norm()), "all_finite": bool(torch.isfinite(g).all()),
            "PASS": bool(torch.isfinite(g).all())}


def recover_param(n=200):
    snaps = list(range(20, n + 1, 20))
    idx = c.P.Smallgrow
    true_val = CARROLL[idx].item()
    s0 = batch_ic(64)
    with torch.no_grad():
        truth = rollout_b(s0, CARROLL, DT, n, FFE_TRUE, snaps)
    guess = torch.nn.Parameter(torch.tensor(true_val * 0.4, device=DEV))
    base = CARROLL.clone()
    opt = torch.optim.Adam([guess], lr=2e-2)
    scale = truth.abs().mean((0, 1)) + 1e-8
    for _ in range(300):
        opt.zero_grad()
        p = torch.cat([base[:idx], guess.reshape(1), base[idx+1:]])
        pred = rollout_b(s0, p, DT, n, FFE_TRUE, snaps)
        (((pred - truth) / scale) ** 2).mean().backward()
        opt.step()
    rel = abs(guess.item() - true_val) / true_val
    return {"true": true_val, "recovered": guess.item(), "rel_err_pct": rel * 100, "PASS": rel < 0.01}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None)
    ap.add_argument("--epochs", type=int, default=3500)
    args = ap.parse_args()
    gpu = torch.cuda.get_device_name(0) if DEV == "cuda" else "cpu"
    print(f"device={DEV} ({gpu}) | torch={torch.__version__}")
    res = {
        "device": DEV, "gpu": gpu, "torch": torch.__version__,
        "ude_clean": train_ude(noise=0.0, epochs=args.epochs),
        "ude_noisy5pct": train_ude(noise=0.05, epochs=args.epochs),
        "grad_depth": grad_depth(),
        "recover_param": recover_param(),
    }
    res["ALL_PASS"] = all(res[k]["PASS"] for k in ("ude_clean", "ude_noisy5pct", "grad_depth", "recover_param"))
    print(json.dumps(res, indent=2))
    if args.out:
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        json.dump(res, open(args.out, "w"), indent=2)
        print("wrote", args.out)
    return 0 if res["ALL_PASS"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
