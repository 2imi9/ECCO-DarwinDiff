#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""EXPERIMENTAL prototype: prognostic dissolved-SiO2 box vs the circular bSi
diagnostic — a diatomgraz identifiability probe.

This is a SELF-CONTAINED experimental module. It does NOT import or modify any
production step function (``carroll6_5pft_2layer.py`` etc.) and it does NOT
change default behaviour anywhere. It only reads the *background constants*
(mortality, grazing, sinking, iron, Si:C ratios) from the production modules so
the prototype box is quantitatively comparable to the real box.

Motivation
----------
A domain expert noted that our claim "diatomgraz is only observable through a
circular biogenic-silica steady-state diagnostic" is a SURROGATE ARTIFACT:
ECCO-Darwin v05 already carries prognostic dissolved SiO2 with Si-limited
diatoms, but our reduced 0-D box (``carroll6_5pft_2layer``) dropped that tracer.
The current ``silica.diagnostic_bsi_steady`` back-solves bSi *algebraically from
the model's own diatom biomass*, so ``diatomgraz`` enters the OBSERVATION
OPERATOR (definitional), not an independent dynamical tracer.

This prototype adds, in a throwaway box:
  * a prognostic dissolved-SiO2 tracer,
  * a Michaelis-Menten Si-limitation factor on diatom growth (Liebig min-law
    with the existing Fe/light limitation),
  * a prognostic bSi tracer with a dissolution return to SiO2,
and asks: does a box with prognostic Si separate ``diatomgraz`` any better than
the circular bSi diagnostic?

The three experiments:
  A. Feasibility + parity self-recovery  (full observable set, diatomgraz free).
  B. The confounding ridge (caveat 4): profile diatomgraz with the diatom GROWTH
     rate marginalised as a nuisance, for Si-only vs Si+biomass observables.
  C. Head-to-head profile: LEGACY (biomass + circular bSi diagnostic) vs
     PROGNOSTIC (biomass + dissolved SiO2 + prognostic bSi), growth marginalised.

Run:  python scripts/analysis/box_silica_prototype.py
(CPU, ~1 min. Nothing is written except an optional --json dump to a path you
pass; no cluster needed — this is a 0-D box.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

# --- background constants pulled from the PRODUCTION modules (read-only) -------
from darwindiff.carroll6 import (  # noqa: E402
    G0_GRAZE, K_FE, LIGHT, M_LIN, M_QUAD, PHI_DUST, Q_FE, W_SINK,
    CARROLL_VALUES, P as PIDX,
)
from darwindiff.carroll6_5pft import MU_DEFAULT_DIATOM, MU_DEFAULT_SYN  # noqa: E402
from darwindiff.silica import R_SI_C, R_SI_DISSOL  # noqa: E402

torch.set_default_dtype(torch.float64)  # 0-D box: use f64 for clean gradients

# --- NEW prototype-only Si constants (would become module constants in prod) ---
K_SI: float = 2.0        # mmol Si/m^3, diatom Si half-saturation (Darwin/Dutkiewicz ~1-4)
SIO2_DEEP: float = 6.0   # mmol Si/m^3, subsurface/source silicate the ML relaxes toward
KAPPA_SI: float = 0.02   # 1/d, vertical-supply (entrainment/mixing) relaxation rate
# Iron gets the same relaxation supply so the small-phyto competitor is well posed.
DFE_DEEP: float = 6.0e-4
KAPPA_FE: float = 0.02

# Carroll reference parameter values we hold fixed / recover.
CARROLL = {k: float(CARROLL_VALUES[getattr(PIDX, k)]) for k in
           ("alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC")}
DIATOMGRAZ_TRUE = CARROLL["diatomgraz"]          # 0.83003
# Diatom growth rate at the synthetic truth. NOTE: MU_DEFAULT_DIATOM (0.431, the
# Carroll lumped Biggrow) sits right at the diatom-extinction boundary when
# diatomgraz=0.83 in a single global-mean 0-D box (net growth ~0), which makes
# P_diatom hypersensitive and the marginalised profiles numerically ragged. That
# is a box-regime artifact, not physics: real diatoms are identifiable where they
# actually bloom (Si-rich upwelling), not at the extinction edge. We therefore set
# the synthetic truth in a diatom-FAVORABLE regime so the identifiability question
# is posed where diatoms carry signal. The qualitative conclusions are unchanged
# by the exact value (checked at 0.65 and 0.90).
MU_DIATOM_TRUE = 0.80                             # diatom growth (nuisance in exp B/C)
MU_SMALL_TRUE = MU_DEFAULT_SYN                    # 0.66098
ALPFE_TRUE = CARROLL["alpfe"]
SCAV_TRUE = CARROLL["scav_rat"] * 86400.0        # per-day


# =============================================================================
# The prototype box.  State = [DFe, P_diatom, P_small, POC, SiO2, bSi]
# `prognostic_si=True`  -> Si-limited diatoms + prognostic SiO2/bSi tracers.
# `prognostic_si=False` -> LEGACY: no Si limitation; bSi is the algebraic
#                          diagnostic (silica.diagnostic_bsi_steady form).
# =============================================================================
I_DFE, I_PD, I_PS, I_POC, I_SIO2, I_BSI = range(6)


def _tendency(state, p, prognostic_si):
    DFe, PD, PS, POC, SiO2, bSi = (state[i] for i in range(6))
    alpfe, scav_pd, mu_d, mu_s, g_diatom = p["alpfe"], p["scav"], p["mu_d"], p["mu_s"], p["diatomgraz"]

    f_fe = DFe / (DFe + K_FE)
    if prognostic_si:
        f_si = SiO2 / (SiO2 + K_SI)
        lim_d = torch.minimum(f_fe, f_si)          # Liebig min-law (Fe vs Si)
    else:
        lim_d = f_fe
    growth_d = mu_d * lim_d * LIGHT * PD
    growth_s = mu_s * f_fe * LIGHT * PS
    fe_uptake = Q_FE * (growth_d + growth_s)

    mort_d = M_LIN * PD + M_QUAD * PD * PD
    mort_s = M_LIN * PS + M_QUAD * PS * PS
    graze_d = g_diatom * G0_GRAZE * PD
    loss_d = mort_d + graze_d

    dDFe = alpfe * PHI_DUST - scav_pd * DFe * POC - fe_uptake + KAPPA_FE * (DFE_DEEP - DFe)
    dPD = growth_d - loss_d
    dPS = growth_s - mort_s
    dPOC = (loss_d + mort_s) - W_SINK * POC

    if prognostic_si:
        si_uptake = R_SI_C * growth_d                 # frustule build during growth
        bsi_prod = R_SI_C * loss_d                    # frustules freed on death/grazing
        dSiO2 = KAPPA_SI * (SIO2_DEEP - SiO2) - si_uptake + R_SI_DISSOL * bSi
        dbSi = bsi_prod - R_SI_DISSOL * bSi - W_SINK * bSi
    else:
        dSiO2 = torch.zeros_like(SiO2)
        dbSi = torch.zeros_like(bSi)
    return torch.stack([dDFe, dPD, dPS, dPOC, dSiO2, dbSi])


def integrate(p, prognostic_si, n_steps=4000, dt=0.25, state0=None):
    if state0 is None:
        state0 = torch.tensor([DFE_DEEP, 0.3, 0.3, 1.0, SIO2_DEEP, 0.02])
    state = state0
    for _ in range(n_steps):
        state = (state + dt * _tendency(state, p, prognostic_si)).clamp(min=0.0)
    return state


def _params(diatomgraz, mu_d, prognostic_si, mu_s=MU_SMALL_TRUE):
    return {"alpfe": torch.tensor(ALPFE_TRUE), "scav": torch.tensor(SCAV_TRUE),
            "mu_d": mu_d, "mu_s": torch.tensor(mu_s),
            "diatomgraz": diatomgraz}


def diagnostic_bsi(state, p):
    """The CURRENT circular diagnostic: bSi back-solved from diatom biomass."""
    PD, g = state[I_PD], p["diatomgraz"]
    mort_d = M_LIN * PD + M_QUAD * PD * PD
    graze_d = g * G0_GRAZE * PD
    return R_SI_C * (mort_d + graze_d) / W_SINK


# --- observables -------------------------------------------------------------
def observe(state, p, prognostic_si, channels):
    """Return a dict of the requested observable channels for a converged state."""
    out = {}
    if "biomass" in channels:
        out["PD"] = state[I_PD]
        out["PS"] = state[I_PS]
        out["POC"] = state[I_POC]
    if "bsi_diag" in channels:
        out["bsi_diag"] = diagnostic_bsi(state, p)
    if "sio2" in channels:
        out["sio2"] = state[I_SIO2]
    if "bsi_prog" in channels:
        out["bsi_prog"] = state[I_BSI]
    return out


def rel_mse(pred, tgt):
    z = torch.zeros((), dtype=torch.float64)
    for k, t in tgt.items():
        z = z + ((pred[k] - t) ** 2) / (t ** 2 + 1e-30)
    return z


# The parameter space here is 1-2 dimensional (diatomgraz, and the growth
# nuisance mu_d), so forward-only GRID search is both far cheaper than
# backprop-through-2000-Euler-steps and immune to local-optimiser artifacts.
N_STEPS = 2200                       # forward-Euler steps to steady state
# diatom growth nuisance grid — includes the true value so that, at the true
# diatomgraz, the marginalised min-loss can reach ~0 (a clean bracketed profile).
MU_GRID = sorted(set(torch.linspace(0.20, 1.40, 25).tolist() + [MU_DIATOM_TRUE]))


def _loss_at(diatomgraz, mu_d, prog, chans, tgt, n_steps=N_STEPS):
    p = _params(torch.tensor(float(diatomgraz)), torch.tensor(float(mu_d)), prog)
    s = integrate(p, prog, n_steps=n_steps)
    return float(rel_mse(observe(s, p, prog, chans), tgt).detach()), p, s


def _make_target(prog, chans):
    p_true = _params(torch.tensor(DIATOMGRAZ_TRUE), torch.tensor(MU_DIATOM_TRUE), prog)
    s_true = integrate(p_true, prog, n_steps=N_STEPS)
    tgt = {k: v.detach() for k, v in observe(s_true, p_true, prog, chans).items()}
    return tgt, s_true


def _span(losses):
    lt = torch.tensor(losses)
    lo = float(lt.min())
    return (float(lt.max()) - lo) / (float(lt.mean()) + 1e-30), lo


# =============================================================================
# Experiment A — feasibility + self-recovery of diatomgraz (growth FIXED, the
# real box's setup where mu_diatom is a fixed default). 1-D profile L(diatomgraz)
# via a fine forward grid; argmin should land on truth and the profile curvature
# (rel_span) measures how sharply the observable constrains diatomgraz.
# =============================================================================
def exp_A():
    print("\n" + "=" * 78)
    print("EXP A — feasibility + self-recovery of diatomgraz  (growth FIXED, as in prod box)")
    print("=" * 78)
    grid = torch.linspace(0.05, 1.0, 40).tolist()
    results = {}
    for arm, prog, chans in (
        ("LEGACY  (biomass + circular bSi diagnostic)", False, ["biomass", "bsi_diag"]),
        ("PROGNOSTIC (biomass + SiO2 + prognostic bSi)", True, ["biomass", "sio2", "bsi_prog"]),
    ):
        tgt, s_true = _make_target(prog, chans)
        if prog:
            fsi = float(s_true[I_SIO2] / (s_true[I_SIO2] + K_SI))
            ffe = float(s_true[I_DFE] / (s_true[I_DFE] + K_FE))
            print(f"   [steady state @ truth] SiO2={float(s_true[I_SIO2]):.3f} f_si={fsi:.3f} "
                  f"f_fe={ffe:.3f} P_diatom={float(s_true[I_PD]):.3f} "
                  f"limiting={'Si' if fsi < ffe else 'Fe'}")
        losses = [_loss_at(g, MU_DIATOM_TRUE, prog, chans, tgt)[0] for g in grid]
        argmin = grid[int(torch.tensor(losses).argmin())]
        span, lo = _span(losses)
        print(f"   {arm}")
        print(f"      argmin(diatomgraz)={argmin:.3f}  (true {DIATOMGRAZ_TRUE:.3f})  "
              f"rel_span={span:.2f}  ->  {'RECOVERED' if abs(argmin-DIATOMGRAZ_TRUE)<0.06 else 'MISSED'}")
        results[arm] = {"argmin": argmin, "rel_span": span, "min_loss": lo}
    return results


# =============================================================================
# Experiment B — caveat 4: does the Si observable ALONE pin diatomgraz, or is it
# confounded with the diatom GROWTH rate?  Profile diatomgraz with mu_d
# marginalised (min over MU_GRID).  Also report the best-fit mu_d at each grid
# point: a rising best-mu_d(diatomgraz) IS the growth-grazing compensation ridge.
# =============================================================================
def _profile_marg(prog, chans, grid):
    tgt, _ = _make_target(prog, chans)
    prof, best_mu = [], []
    for g in grid:
        ls = [(_loss_at(g, mu, prog, chans, tgt)[0], mu) for mu in MU_GRID]
        lmin, mu_star = min(ls, key=lambda x: x[0])
        prof.append(lmin)
        best_mu.append(mu_star)
    return prof, best_mu


def _report_marg(label, prog, chans, grid, out):
    prof, best_mu = _profile_marg(prog, chans, grid)
    span, lo = _span(prof)
    argmin = grid[int(torch.tensor(prof).argmin())]
    # The HONEST identifiability test for a marginalised profile is whether its
    # minimum stays at the true diatomgraz. If growth (mu_d) can be traded off to
    # fit a WRONG diatomgraz better than the truth, diatomgraz is confounded.
    at_truth = abs(argmin - DIATOMGRAZ_TRUE) < 0.10
    verdict = "IDENTIFIED (min at truth)" if at_truth else "CONFOUNDED (min off truth)"
    print(f"   {label}")
    print(f"      diatomgraz grid : {[round(g,2) for g in grid]}")
    print(f"      min-loss(marg mu): {[round(x,4) for x in prof]}")
    print(f"      best-fit mu_d    : {[round(m,2) for m in best_mu]}  (true {MU_DIATOM_TRUE:.2f})")
    print(f"      argmin={argmin:.2f} (true {DIATOMGRAZ_TRUE:.2f})  rel_span={span:.3f}  ->  {verdict}")
    out[label] = {"grid": list(map(float, grid)), "losses": prof, "best_mu": best_mu,
                  "rel_span": span, "min_loss": lo, "argmin": argmin, "at_truth": at_truth}


def exp_B(grid):
    print("\n" + "=" * 78)
    print("EXP B — caveat 4: does the Si observable ALONE identify diatomgraz,")
    print("        or is it confounded with diatom growth?  (growth marginalised)")
    print("=" * 78)
    out = {}
    _report_marg("Si observables ONLY (SiO2 + prognostic bSi, NO biomass)",
                 True, ["sio2", "bsi_prog"], grid, out)
    _report_marg("Si + biomass (SiO2 + bSi + P_diatom/POC)",
                 True, ["sio2", "bsi_prog", "biomass"], grid, out)
    return out


def exp_C(grid):
    print("\n" + "=" * 78)
    print("EXP C — head-to-head: LEGACY circular-bSi vs PROGNOSTIC Si, growth marginalised")
    print("        (both keep the biomass observable; this is the real config's comparison)")
    print("=" * 78)
    out = {}
    _report_marg("LEGACY  (biomass + circular bSi diagnostic)",
                 False, ["biomass", "bsi_diag"], grid, out)
    _report_marg("PROGNOSTIC (biomass + SiO2 + prognostic bSi)",
                 True, ["biomass", "sio2", "bsi_prog"], grid, out)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="optional path to dump results JSON")
    args = ap.parse_args()

    print("Prototype prognostic-Si box — diatomgraz identifiability probe")
    print(f"  true diatomgraz={DIATOMGRAZ_TRUE:.4f}  mu_diatom={MU_DIATOM_TRUE:.4f}  "
          f"K_SI={K_SI} SIO2_DEEP={SIO2_DEEP} KAPPA_SI={KAPPA_SI}")

    grid = [0.10, 0.25, 0.40, 0.55, 0.70, 0.83, 0.95]
    res = {"exp_A": exp_A(),
           "exp_B": exp_B(grid),
           "exp_C": exp_C(grid),
           "constants": {"K_SI": K_SI, "SIO2_DEEP": SIO2_DEEP, "KAPPA_SI": KAPPA_SI,
                         "R_SI_C": R_SI_C, "R_SI_DISSOL": R_SI_DISSOL,
                         "diatomgraz_true": DIATOMGRAZ_TRUE, "mu_diatom_true": MU_DIATOM_TRUE}}
    if args.json:
        with open(args.json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
