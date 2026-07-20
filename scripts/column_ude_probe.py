#!/usr/bin/env python
"""column_ude_probe.py -- does a 1-D water column + SEASONAL light make a
growth-pair parameter identifiable that the 0-D climatology box cannot see?

Motivation (the real mechanism, from carroll6):
  In the 0-D box the growth term is  gs = mu_s * f_fe * LIGHT * Ps  with LIGHT a
  FIXED constant, so mu_s and LIGHT are degenerate, and a 23-yr climatology
  averages away the only handle that could separate them. This is *why* the
  growth pair (Smallgrow/Biggrow) is unobservable in the box.

This probe adds the two things the box lacks, on the REAL differentiable box
(darwindiff.carroll6), not a toy:
  (1) a VERTICAL column: Z depth levels coupled by vertical diffusion (transport);
  (2) a SEASONAL, depth-attenuated light field LIGHT(z, t).

Decisive test = profile likelihood of Smallgrow under SEASONAL vs CONSTANT light,
observing only surface+depth POC/PIC/DFe (not the phyto biomass directly). A FLAT
profile = unidentifiable (the box's problem); a CURVED profile with a minimum at
truth = the seasonal handle made it identifiable. Also runs a full self-twin
calibration for each condition as a cross-check.

Run:  python scripts/column_ude_probe.py            (CPU, ~1-2 min)
"""
from __future__ import annotations
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import torch
import darwindiff.carroll6 as c

torch.manual_seed(0)
DEV = "cpu"
DT = 0.25                       # days
Z = 8                           # depth levels
DZ = 25.0                       # m per level
KZ = 1.0e-1                     # vertical diffusivity (level^2/day, schematic)
KATT = 0.03                     # light attenuation (1/m)
YEAR = 365.0
CARROLL = c.CARROLL_VALUES.to(DEV).float()
PN = c.PARAM_NAMES
DEPTH = torch.arange(Z, device=DEV).float() * DZ + DZ / 2.0   # mid-level depth (m)


def light_field(t_day, amp):
    """Depth-attenuated, seasonally-varying light at time t (days)."""
    I0 = 1.0 * (1.0 + amp * torch.sin(torch.tensor(2.0 * 3.141592653589793 * t_day / YEAR)))
    return I0 * torch.exp(-KATT * DEPTH)          # [Z]


def vdiff(field, Kz, dz):
    """Vertical diffusion d/dz(Kz dC/dz) per tracer, zero-flux boundaries. field [T,Z]."""
    up = torch.zeros_like(field)
    up[:, 1:] = field[:, :-1] - field[:, 1:]      # flux from above
    dn = torch.zeros_like(field)
    dn[:, :-1] = field[:, 1:] - field[:, :-1]     # flux from below
    return Kz / (dz * dz) * (up + dn)


def column_step(state, params, dt, light):
    """One forward-Euler step of the 5-tracer BGC on a Z-level column.
    state [5,Z]; light [Z]; params [6] (Carroll-6 order). Mirrors carroll6 bgc_step
    per level, with LIGHT -> light(z,t), plus vertical diffusion coupling levels."""
    DFe, Ps, Pl, POC, PIC = state[0], state[1], state[2], state[3], state[4]
    alpfe, scav_rat = params[c.P.alpfe], params[c.P.scav_rat]
    mu_s, mu_l = params[c.P.Smallgrow], params[c.P.Biggrow]
    g_diatom, R = params[c.P.diatomgraz], params[c.P.R_PICPOC]
    scav_pd = scav_rat * 86400.0
    f_fe = DFe / (DFe + c.K_FE)
    gs = mu_s * f_fe * light * Ps
    gl = mu_l * f_fe * light * Pl
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
    react = torch.stack([dDFe, dPs, dPl, dPOC, dPIC])       # [5,Z]
    diff = vdiff(state, KZ, 1.0)                            # level-space diffusion
    return state + dt * (react + diff)


def rollout_obs(params, amp, years=3, spin_years=1):
    """Integrate the column and return the OBSERVED subset (POC/PIC/DFe at all
    levels), sampled every ~15 d over the final year. Phyto biomass is NOT
    observed -> growth params act only through the tracers they drive."""
    state = torch.stack([
        torch.full((Z,), 2e-5),   # DFe
        torch.full((Z,), 0.1),    # Ps
        torch.full((Z,), 0.1),    # Pl
        torch.full((Z,), 0.1),    # POC
        torch.full((Z,), 0.01),   # PIC
    ]).to(DEV)
    n = int(years * YEAR / DT)
    obs_start = int((years - 1) * YEAR / DT)
    obs = []
    for k in range(n):
        t = k * DT
        state = column_step(state, params, DT, light_field(t, amp))
        if k >= obs_start and (k % int(15.0 / DT) == 0):
            obs.append(torch.stack([state[0], state[3], state[4]]))  # DFe, POC, PIC  [3,Z]
    return torch.stack(obs)       # [T_obs, 3, Z]


def obs_loss(theta, truth_obs, amp):
    """z-scored MSE of observed tracers vs truth, params = theta * Carroll."""
    params = theta * CARROLL
    pred = rollout_obs(params, amp)
    # per-channel z-score so no single tracer dominates
    mu = truth_obs.mean(dim=(0, 2), keepdim=True)
    sd = truth_obs.std(dim=(0, 2), keepdim=True).clamp(min=1e-12)
    return (((pred - truth_obs) / sd) ** 2).mean()


def profile(pidx, truth_obs, amp, span=0.6, npts=13):
    """Profile likelihood: fix all params at truth, sweep one param's multiplier
    over [1-span, 1+span], return loss curve. Flat = unidentifiable."""
    losses = []
    grid = torch.linspace(1.0 - span, 1.0 + span, npts)
    for m in grid:
        theta = torch.ones(6)
        theta[pidx] = m
        with torch.no_grad():
            losses.append(float(obs_loss(theta, truth_obs, amp)))
    lo = min(losses)
    curv = (max(losses) - lo)             # depth of the well (identifiability proxy)
    return grid.tolist(), losses, curv


def calibrate(truth_obs, amp, init_scale, steps=250):
    """Recover all 6 params by gradient descent through the column rollout."""
    theta = torch.full((6,), init_scale, requires_grad=True)
    opt = torch.optim.Adam([theta], lr=0.05)
    for _ in range(steps):
        opt.zero_grad()
        loss = obs_loss(theta, truth_obs, amp)
        loss.backward()
        opt.step()
        with torch.no_grad():
            theta.clamp_(0.1, 3.0)
    rel = (theta.detach() - 1.0).abs()          # |recovered/carroll - 1|
    return theta.detach().tolist(), rel.tolist()


def band(rel):
    return "Excellent" if rel <= 0.05 else "Cal" if rel <= 0.40 else "Loose" if rel <= 0.80 else "Drift"


def main():
    truth = torch.ones(6)                        # self-twin: theta = 1 (Carroll)
    result = {"config": {"Z": Z, "DZ": DZ, "KZ": KZ, "years": 3}, "conditions": {}}
    print(f"1-D column UDE probe  (Z={Z} levels, seasonal vs constant light)\n")

    for label, amp in [("constant_light(climatology)", 0.0), ("seasonal_light", 0.8)]:
        truth_obs = rollout_obs(truth * CARROLL, amp)
        # --- decisive test: profile likelihood of the growth pair ---
        prof = {}
        for name in ("Smallgrow", "Biggrow"):
            pidx = PN.index(name)
            _, losses, curv = profile(pidx, truth_obs, amp)
            prof[name] = {"well_depth": curv, "flat": curv < 1e-3}
        # --- cross-check: full self-twin calibration from a perturbed init ---
        _, rel = calibrate(truth_obs, amp, init_scale=1.5)
        recov = {PN[i]: {"rel_offset": round(rel[i], 4), "band": band(rel[i])} for i in range(6)}
        result["conditions"][label] = {"profile_growth_pair": prof, "calibration": recov}

        print(f"=== {label} ===")
        for name in ("Smallgrow", "Biggrow"):
            p = prof[name]
            print(f"  profile {name:10s}: well_depth={p['well_depth']:.3e}  "
                  f"{'FLAT (unidentifiable)' if p['flat'] else 'curved (identifiable)'}")
        gp = ", ".join(f"{n}={recov[n]['rel_offset']:.2f}({recov[n]['band']})"
                       for n in ("Smallgrow", "Biggrow"))
        print(f"  self-twin recovery  growth pair: {gp}")
        print(f"  self-twin recovery  iron/ratio : "
              + ", ".join(f"{n}={recov[n]['rel_offset']:.2f}({recov[n]['band']})"
                          for n in ("alpfe", "scav_rat", "R_PICPOC")) + "\n")

    # verdict
    csmall = result["conditions"]["constant_light(climatology)"]["profile_growth_pair"]["Smallgrow"]["well_depth"]
    ssmall = result["conditions"]["seasonal_light"]["profile_growth_pair"]["Smallgrow"]["well_depth"]
    ratio = (ssmall / csmall) if csmall > 0 else float("inf")
    result["verdict"] = {
        "smallgrow_well_constant": csmall, "smallgrow_well_seasonal": ssmall,
        "seasonal_over_constant_ratio": ratio,
        "seasonal_unlocks_growth": bool(ssmall > 5 * max(csmall, 1e-9)),
    }
    print(f"VERDICT: Smallgrow profile well  constant={csmall:.3e}  seasonal={ssmall:.3e}  "
          f"(seasonal/constant = {ratio:.1f}x)")
    print("  -> seasonal light " + ("UNLOCKS" if result["verdict"]["seasonal_unlocks_growth"]
                                     else "does NOT clearly unlock") + " growth-pair identifiability")
    out = os.path.join(os.path.dirname(__file__), "..", "docs", "findings", "column_ude_probe.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(result, open(out, "w"), indent=2)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
