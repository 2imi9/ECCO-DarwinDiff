"""E2-hunt lever 3 (growth): can a primary-PRODUCTION observable identify the growth
closure (Smallgrow/Biggrow) that phytoplankton STANDING STOCK cannot?

Standing-stock biomass P is set by a growth-vs-loss balance (growth = mort at steady
state), so it sees the growth rate mu only in combination with the loss terms -- the
"growth wall" (Track-1: growth unobservable from biomass). The flux/stock ratio
NPP/biomass = mu*f_fe*LIGHT is the specific growth rate, loss-terms cancelled -- the
structural twin of the iron pFe/DFe trick.

This scout measures the JOINT (mu_s, mu_l) identifiability for three observables, and is
DELIBERATELY honest about the two traps the iron lever taught us:

  1. biomass        log(Ps+Pl)                          -- the wall (broad).
  2. total_npp      log( (g_s+g_l) / (Ps+Pl) )          -- the ONLY real observable
                    (14C/satellite NPP is total). REAL, NON-tautological question: does it
                    pin the (mu_s, mu_l) PAIR, or only their biomass-weighted MEAN
                    (a ridge mu_s*Ps + mu_l*Pl = const)?
  3. per_pft_npp    log(g_s/Ps), log(g_l/Pl)            -- TAUTOLOGICAL: g_s/Ps =
                    mu_s*f_fe*LIGHT is linear in the candidate mu_s by construction (same
                    artifact as iron pFe/DFe). A sharp well here proves algebra, NOT
                    real recoverability, AND no instrument measures per-PFT production.

Metric: over the near-min region (misfit <= min+band) report the mu_s spread, mu_l spread,
and the ridge indicator corr(mu_s, mu_l) (~ -1 => an anti-correlated ridge = only a weighted
sum is constrained). Honest verdict: total_npp is a PAIR RIDGE (aggregate-observable, not the
pair); per_pft is a tautological point; biomass is the broad wall.

Self-twin, CPU (CUDA_VISIBLE_DEVICES=-1), real eqpac footprint + transport. Needs the
wall-demo bundle (--bundle). A methods result, not a real-data recovery.
"""
from __future__ import annotations

import argparse

import numpy as np
import torch

from darwindiff.carroll6 import K_FE, LIGHT, P
from darwindiff.safe_load import safe_torch_load
from darwindiff.trainer import TransportConfig, rollout_field
from iron_scav_rat_profile import DX, DY, DZ, EPS, build_inputs


def _region_stats(mis, s_g, b_g, band=0.02):
    """Near-min region: (mu_s span, mu_l span, ridge corr, n_cells)."""
    thr = np.nanmin(mis) + band
    ii, jj = np.where(mis <= thr)
    if ii.size < 2:
        return 1.0, 1.0, float("nan"), int(ii.size)
    ms, ml = s_g[ii], b_g[jj]
    s_span = ms.max() / ms.min() if ms.min() > 0 else float("inf")
    l_span = ml.max() / ml.min() if ml.min() > 0 else float("inf")
    ridge = float(np.corrcoef(ms, ml)[0, 1]) if ms.std() > 0 and ml.std() > 0 else float("nan")
    return s_span, l_span, ridge, int(ii.size)


def run(inp, n_steps=100, n_s=17, n_l=17):
    dev = torch.device("cpu")
    dt = torch.float64
    to = lambda t: t.to(device=dev, dtype=(torch.bool if t.dtype == torch.bool else dt))
    u, v, w, dust, ic, mask, base = (to(inp[k]) for k in ("u", "v", "w", "dust", "ic", "mask", "base"))
    tc = TransportConfig(dx=DX, dy=DY, dz=DZ, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w, dust=dust)
    mu_s0, mu_l0 = float(base[P.Smallgrow]), float(base[P.Biggrow])

    with torch.no_grad():
        twin = rollout_field(ic, base, tc, n_steps)
    dfe0 = twin[..., 0, 0].clamp_min(EPS)
    ps0, pl0 = twin[..., 0, 1].clamp_min(EPS), twin[..., 0, 2].clamp_min(EPS)
    f0 = dfe0 / (dfe0 + K_FE)
    gs0, gl0 = mu_s0 * f0 * LIGHT * ps0, mu_l0 * f0 * LIGHT * pl0
    tgt_bio = torch.log(ps0 + pl0).detach()
    tgt_tot = torch.log(((gs0 + gl0) / (ps0 + pl0)).clamp_min(EPS)).detach()
    tgt_ps = torch.log((gs0 / ps0).clamp_min(EPS)).detach()
    tgt_pl = torch.log((gl0 / pl0).clamp_min(EPS)).detach()

    s_g = np.linspace(0.30, 1.10, n_s)      # Smallgrow around Carroll 0.661
    l_g = np.linspace(0.15, 0.75, n_l)      # Biggrow around Carroll 0.431
    m_bio = np.full((n_s, n_l), np.nan)
    m_tot = np.full((n_s, n_l), np.nan)
    m_perp = np.full((n_s, n_l), np.nan)

    @torch.no_grad()
    def fit(mu_s, mu_l):
        p = base.clone(); p[P.Smallgrow] = float(mu_s); p[P.Biggrow] = float(mu_l)
        fld = rollout_field(ic, p, tc, n_steps)
        dfe = fld[..., 0, 0].clamp_min(EPS)
        ps, pl = fld[..., 0, 1].clamp_min(EPS), fld[..., 0, 2].clamp_min(EPS)
        f_fe = dfe / (dfe + K_FE)
        gs, gl = mu_s * f_fe * LIGHT * ps, mu_l * f_fe * LIGHT * pl
        d_bio = (torch.log(ps + pl) - tgt_bio)[mask]
        d_tot = (torch.log(((gs + gl) / (ps + pl)).clamp_min(EPS)) - tgt_tot)[mask]
        d_ps = (torch.log((gs / ps).clamp_min(EPS)) - tgt_ps)[mask]
        d_pl = (torch.log((gl / pl).clamp_min(EPS)) - tgt_pl)[mask]
        return (float((d_bio * d_bio).mean()), float((d_tot * d_tot).mean()),
                float((0.5 * (d_ps * d_ps + d_pl * d_pl)).mean()))

    for i, ms in enumerate(s_g):
        for j, ml in enumerate(l_g):
            m_bio[i, j], m_tot[i, j], m_perp[i, j] = fit(ms, ml)
        print(f"[growth] Smallgrow row {i + 1}/{n_s} done", flush=True)

    print(f"\n[growth] twin (Smallgrow={mu_s0:.3f}, Biggrow={mu_l0:.3f}); joint (mu_s, mu_l) "
          f"near-min region (misfit <= min+0.02):")
    print(f"  {'observable':<14} {'mu_s span':>10} {'mu_l span':>10} {'ridge corr':>11} {'n_cells':>8}")
    for name, mis in (("biomass", m_bio), ("total_npp", m_tot), ("per_pft_npp", m_perp)):
        ss, ls, rc, nc = _region_stats(mis, s_g, l_g)
        print(f"  {name:<14} {ss:>10.2f} {ls:>10.2f} {rc:>11.2f} {nc:>8d}")

    ss_b, ls_b, _, _ = _region_stats(m_bio, s_g, l_g)
    ss_t, ls_t, _, _ = _region_stats(m_tot, s_g, l_g)
    ss_p, ls_p, _, _ = _region_stats(m_perp, s_g, l_g)
    TOL = 1.5  # a param is "identified" if its near-min span is < TOL x
    ident = lambda span: span < TOL
    print(f"\n[growth] VERDICT (a param is 'identified' if its near-min span < {TOL}x):")
    print(f"  standing-stock biomass: Smallgrow {'ID' if ident(ss_b) else 'FREE'} ({ss_b:.2f}x), "
          f"Biggrow {'ID' if ident(ls_b) else 'FREE'} ({ls_b:.2f}x)  -- the wall")
    print(f"  total NPP (REAL obs)   : Smallgrow {'ID' if ident(ss_t) else 'FREE'} ({ss_t:.2f}x), "
          f"Biggrow {'ID' if ident(ls_t) else 'FREE'} ({ls_t:.2f}x)")
    print(f"  per-PFT NPP (twin only): Smallgrow {'ID' if ident(ss_p) else 'FREE'} ({ss_p:.2f}x), "
          f"Biggrow {'ID' if ident(ls_p) else 'FREE'} ({ls_p:.2f}x)  -- TAUTOLOGICAL + unmeasurable")
    tot_helps = (ss_t < ss_b / 1.3) or (ls_t < ls_b / 1.3)
    print(f"\n  => total NPP {'IMPROVES on' if tot_helps else 'does NOT improve on'} standing-stock "
          f"biomass for the growth pair. In eqpac the large-phyto rate (Biggrow) is "
          f"{'identifiable' if ident(ls_t) else 'UNIDENTIFIABLE (large phyto negligible here)'} "
          f"from the real (total) observable; only the tautological per-PFT NPP pins it. So growth is "
          f"NOT rescued -- not a clean positive E2 (needs a large-phyto-dominated region + per-PFT "
          f"production no instrument provides).")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--n-steps", type=int, default=100)
    ap.add_argument("--n-s", type=int, default=17)
    ap.add_argument("--n-l", type=int, default=17)
    a = ap.parse_args()
    inp = safe_torch_load(a.bundle) if a.bundle else build_inputs()
    return run(inp, a.n_steps, a.n_s, a.n_l)


if __name__ == "__main__":
    raise SystemExit(main())
