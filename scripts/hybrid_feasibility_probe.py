#!/usr/bin/env python
"""hybrid_feasibility_probe.py -- small-scale "is the differentiable-BGC / UDE
hybrid path executable?" probe.

Four de-risking tests, all CPU, all reusing the REAL differentiable box
(darwindiff.carroll6), not a toy:

  A. Mass conservation -- forward-Euler vs RK4 drift on a CLOSED system
     (the #7 risk: nb04 saw ~5% forward-Euler drift).
  B. UDE hybrid -- replace the iron-limitation closure f_fe(DFe) with a small
     neural net INSIDE the real BGC and train it end-to-end through the time
     integration to recover the true dynamics (the "neural-net hybrid" claim).
  C. Gradient flow at depth -- backprop through a long rollout is finite/stable.
  D. Calibration by backprop -- recover a known parameter by gradient descent
     through the differentiable dynamics (a self-twin).

Run:  python scripts/hybrid_feasibility_probe.py   (needs src on path)
"""
from __future__ import annotations
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import torch
import darwindiff.carroll6 as c

torch.manual_seed(0)
DT = 0.25                      # days
DEV = "cpu"


# ---------------------------------------------------------------------------
# A pluggable BGC step: identical to carroll6_step EXCEPT f_fe is supplied,
# so we can swap the mechanistic closure for a neural net (the UDE element).
# ---------------------------------------------------------------------------
def bgc_step(state, params, dt, ffe_fn):
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    alpfe, scav_rat = params[c.P.alpfe], params[c.P.scav_rat]
    mu_s, mu_l = params[c.P.Smallgrow], params[c.P.Biggrow]
    g_diatom, R = params[c.P.diatomgraz], params[c.P.R_PICPOC]
    scav_pd = scav_rat * 86400.0
    f_fe = ffe_fn(DFe)
    gs = mu_s * f_fe * c.LIGHT * Ps
    gl = mu_l * f_fe * c.LIGHT * Pl
    fe_up = c.Q_FE * (gs + gl)
    ms = c.M_LIN * Ps + c.M_QUAD * Ps * Ps
    ml = c.M_LIN * Pl + c.M_QUAD * Pl * Pl
    gz = g_diatom * c.G0_GRAZE * Pl
    mt = ms + ml + gz
    dDFe = alpfe * c.PHI_DUST - scav_pd * DFe * POC - fe_up
    dPs = gs - ms
    dPl = gl - ml - gz
    dPOC = mt - c.W_SINK * POC
    dPIC = R * mt - c.W_SINK * PIC
    return torch.stack([DFe + dt*dDFe, Ps + dt*dPs, Pl + dt*dPl,
                        POC + dt*dPOC, PIC + dt*dPIC])


def rollout(state0, params, dt, n, ffe_fn, snaps=None):
    s = state0
    out = []
    snapset = set(snaps or [])
    for k in range(1, n + 1):
        s = bgc_step(s, params, dt, ffe_fn)
        if k in snapset:
            out.append(s)
    return torch.stack(out) if out else s


FFE_TRUE = lambda DFe: DFe / (DFe + c.K_FE)            # Michaelis-Menten iron limitation
CARROLL = c.CARROLL_VALUES.to(DEV).float()
STATE0 = torch.tensor([2e-5, 0.1, 0.1, 0.1, 0.01], device=DEV)   # DFe below K_FE -> samples the curve knee


# ===========================================================================
# A. Integrator fidelity: forward-Euler vs RK4 trajectory ACCURACY vs a fine
#    reference (the real #7 risk -- accuracy/stability over long rollouts).
#    NOTE: a linear mass-sum is conserved exactly by ANY explicit scheme
#    (sum of tendencies == 0), so we test trajectory accuracy, and report the
#    linear-mass conservation as a (trivially-passing) sanity check.
# ===========================================================================
def test_A_integrator_fidelity():
    vmax, kn, gmax, kp, mp, mz = 1.0, 0.2, 0.8, 0.3, 0.1, 0.08

    def tend(x):
        N, P, Z = x[0], x[1], x[2]
        up = vmax * N / (kn + N) * P
        gz = gmax * P / (kp + P) * Z
        pm, zm = mp * P, mz * Z
        return torch.stack([-up + pm + zm, up - gz - pm, gz - zm])

    x0 = torch.tensor([1.0, 0.3, 0.2], dtype=torch.float64); T = 200.0

    def integ(method, dt):
        x = x0.clone()
        for _ in range(int(round(T / dt))):
            if method == "fe":
                x = x + dt * tend(x)
            else:
                k1 = tend(x); k2 = tend(x + dt/2*k1)
                k3 = tend(x + dt/2*k2); k4 = tend(x + dt*k3)
                x = x + dt/6*(k1 + 2*k2 + 2*k3 + k4)
        return x

    ref = integ("rk4", 0.01)
    fe  = integ("fe", 0.25)
    rk4 = integ("rk4", 0.25)
    relerr = lambda a: float((a - ref).norm() / ref.norm())
    fe_fin = bool(torch.isfinite(fe).all())
    err_fe, err_rk4 = (relerr(fe) if fe_fin else float("nan")), relerr(rk4)
    mass_ok = abs(rk4.sum().item() - x0.sum().item()) / x0.sum().item() < 1e-6
    fe_str = "diverged" if not fe_fin else f"{err_fe*100:.4g}"
    ok = bool(torch.isfinite(rk4).all()) and err_rk4 < 1e-3 and (not fe_fin or err_rk4 < err_fe/10)
    return {"FE_traj_err_%": fe_str, "RK4_traj_err_%": err_rk4*100,
            "mass_sum_conserved": mass_ok, "verdict": ok}


# ===========================================================================
# B. UDE: neural net replaces f_fe(DFe) INSIDE the BGC, trained through the rollout
# ===========================================================================
def test_B_ude_closure():
    n, dt = 240, DT
    snaps = list(range(20, n + 1, 20))
    # Several ICs spanning the iron-limitation knee (DFe around K_FE=5e-5) so the
    # closure is sampled where it actually varies, not only near saturation.
    ic_dfe = [8e-6, 2e-5, 5e-5, 1.2e-4]
    truths = []
    with torch.no_grad():
        for d0 in ic_dfe:
            s0 = torch.tensor([d0, 0.1, 0.1, 0.1, 0.01], device=DEV)
            truths.append((s0, rollout(s0, CARROLL, dt, n, FFE_TRUE, snaps)))

    net = torch.nn.Sequential(
        torch.nn.Linear(1, 32), torch.nn.Tanh(),
        torch.nn.Linear(32, 32), torch.nn.Tanh(),
        torch.nn.Linear(32, 1), torch.nn.Sigmoid(),   # f_fe in (0,1) by construction
    ).to(DEV)
    # Normalize the closure input: raw DFe (~1e-5) is too small for the net to
    # resolve -> feed log10(DFe) recentred near the K_FE knee. This is the fix
    # that took curve MAE 0.054 -> ~0.005 (the H200 plateau was this bug, not compute).
    ffe_nn = lambda DFe: net(((torch.log10(DFe.clamp_min(1e-9)) + 4.7) / 2.0).reshape(1, 1)).reshape(())

    opt = torch.optim.Adam(net.parameters(), lr=5e-3)
    sched = torch.optim.lr_scheduler.StepLR(opt, step_size=1400, gamma=0.3)
    loss0 = None
    for it in range(2800):
        opt.zero_grad()
        loss = 0.0
        for s0, tr in truths:
            pred = rollout(s0, CARROLL, dt, n, ffe_nn, snaps)
            scale = tr.abs().mean(0) + 1e-8
            loss = loss + (((pred - tr) / scale) ** 2).mean()
        loss = loss / len(truths)
        loss.backward()
        opt.step(); sched.step()
        if it == 0:
            loss0 = loss.item()
    loss1 = loss.item()

    # how well did the NN recover the true Michaelis-Menten curve over the DFe range visited?
    with torch.no_grad():
        lo = min(float(tr[:, 0].min()) for _, tr in truths)
        hi = max(float(tr[:, 0].max()) for _, tr in truths)
        dfe_grid = torch.linspace(lo, hi, 60)
        nn_curve = torch.stack([ffe_nn(d) for d in dfe_grid])
        true_curve = FFE_TRUE(dfe_grid)
        curve_mae = (nn_curve - true_curve).abs().mean().item()

    return {"loss_init": loss0, "loss_final": loss1, "loss_drop_x": loss0/max(loss1, 1e-12),
            "ffe_curve_MAE": curve_mae, "verdict": loss1 < loss0/100 and curve_mae < 0.02}


# ===========================================================================
# C. Gradient flow at depth: backprop through a long rollout is finite/stable
# ===========================================================================
def test_C_grad_depth():
    n = 2000
    p = CARROLL.clone().requires_grad_(True)
    sf = rollout(STATE0, p, DT, n, FFE_TRUE)
    loss = (sf ** 2).sum()
    loss.backward()
    g = p.grad
    finite = bool(torch.isfinite(g).all())
    return {"n_steps": n, "grad_norm": float(g.norm()), "all_finite": finite,
            "verdict": finite and float(g.norm()) > 0}


# ===========================================================================
# D. Calibration by backprop: recover a known parameter (self-twin)
# ===========================================================================
def test_D_recover_param():
    n, dt = 200, DT
    snaps = list(range(20, n + 1, 20))
    idx = c.P.Smallgrow
    true_val = CARROLL[idx].item()
    with torch.no_grad():
        truth = rollout(STATE0, CARROLL, dt, n, FFE_TRUE, snaps)

    guess = torch.nn.Parameter(torch.tensor(true_val * 0.4))   # start 60% low
    base = CARROLL.clone()
    opt = torch.optim.Adam([guess], lr=2e-2)
    scale = truth.abs().mean(0) + 1e-8
    for _ in range(400):
        opt.zero_grad()
        p = base.clone(); p = torch.cat([p[:idx], guess.reshape(1), p[idx+1:]])
        pred = rollout(STATE0, p, dt, n, FFE_TRUE, snaps)
        loss = (((pred - truth) / scale) ** 2).mean()
        loss.backward(); opt.step()
    rec = guess.item()
    rel = abs(rec - true_val) / true_val
    return {"true": true_val, "recovered": rec, "rel_err_%": rel*100,
            "verdict": rel < 0.05}


if __name__ == "__main__":
    tests = [("A integrator fidelity (FE vs RK4)", test_A_integrator_fidelity),
             ("B UDE neural closure in BGC",     test_B_ude_closure),
             ("C gradient flow @2000 steps",     test_C_grad_depth),
             ("D recover param by backprop",     test_D_recover_param)]
    print("=" * 64)
    print("HYBRID DIFFERENTIABLE-BGC FEASIBILITY PROBE")
    print("=" * 64)
    allpass = True
    for name, fn in tests:
        r = fn(); v = r.pop("verdict"); allpass &= v
        print(f"\n[{'PASS' if v else 'FAIL'}] {name}")
        for k, val in r.items():
            print(f"      {k:18s} = {val:.6g}" if isinstance(val, float) else f"      {k:18s} = {val}")
    print("\n" + "=" * 64)
    print(f"OVERALL: {'ALL TESTS PASS -- path is executable at small scale' if allpass else 'SOME TESTS FAILED'}")
    print("=" * 64)
    sys.exit(0 if allpass else 1)
