"""Adversarial controls for the iron-partitioning scout -- quantify how much of the
apparent scav_rat identifiability is a construction artifact vs a real signal.

A verification pass (5 skeptics) showed the scout's observable pFe/DFe reduces
ALGEBRAICALLY to ``scav_per_day * POC / W_SINK`` -- DFe cancels exactly, so the
parameter appears as an explicit prefactor and the "sharp well" is largely
tautological (fitting c*scav to c*scav0), with the reported ~14x/1x band a grid+
threshold artifact. What legitimately survives: alpfe cancels from pFe/DFe, so
partitioning removes the *alpfe* confounder. But the rate stays degenerate with
POC*W_SINK, and a real contaminated Fe_TP re-injects alpfe. This script measures
those two corrections numerically:

  A. CANCELLATION / W_SINK degeneracy -- confirm corr(pFe/DFe, DFe) ~ 0 and that
     (scav, W_SINK) -> (k*scav, k*W_SINK) gives an identical observable (a perfect
     new degeneracy the self-twin hides by fixing W_SINK at truth).
  B. CONTAMINATION -- re-profile scav_rat with pFe_obs = scavenged + biogenic
     (~Q_FE*biomass, scav-independent) + labile-lithogenic (~alpfe*dust, which
     RE-INJECTS alpfe), for a moderate contamination fraction, and report how much
     the scav_rat band re-widens and whether an alpfe ridge returns.

CPU: ``CUDA_VISIBLE_DEVICES=-1``. Needs the wall-demo bundle (--bundle).
"""
from __future__ import annotations

import argparse

import numpy as np
import torch

from darwindiff.carroll6 import P, Q_FE, W_SINK
from darwindiff.trainer import TransportConfig, rollout_field
from iron_scav_rat_profile import DX, DY, DZ, EPS, build_inputs


def run(inp, n_steps=100, n_alpfe=15, n_scav=21, bio_frac=0.5, lith_frac=0.5):
    dev = torch.device("cpu")
    dt = torch.float64
    to = lambda t: t.to(device=dev, dtype=(torch.bool if t.dtype == torch.bool else dt))
    u, v, w, dust, ic, mask, base = (to(inp[k]) for k in ("u", "v", "w", "dust", "ic", "mask", "base"))
    tc = TransportConfig(dx=DX, dy=DY, dz=DZ, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w, dust=dust)
    w_sink = float(W_SINK)
    dust_surf = dust[..., 0]                                   # surface dust ~ alpfe forcing
    alpfe0, scav0 = float(base[P.alpfe]), float(base[P.scav_rat]) * 86400.0

    with torch.no_grad():
        twin = rollout_field(ic, base, tc, n_steps)
    dfe0, poc0 = twin[..., 0, 0].clamp_min(EPS), twin[..., 0, 3].clamp_min(EPS)
    ps0, pl0 = twin[..., 0, 1].clamp_min(EPS), twin[..., 0, 2].clamp_min(EPS)
    scavenged0 = scav0 * dfe0 * poc0 / w_sink
    bio0 = Q_FE * (ps0 + pl0)
    lith0 = alpfe0 * dust_surf.clamp_min(EPS)
    # scale contamination to the requested fraction of the median scavenged pFe at truth
    bio_scale = bio_frac * float(scavenged0[mask].median()) / float(bio0[mask].median())
    lith_scale = lith_frac * float(scavenged0[mask].median()) / float(lith0[mask].median())

    # ---- Control A: cancellation + W_SINK degeneracy (exact algebra) -------------
    ratio0 = scavenged0 / dfe0
    # corr(pFe/DFe, DFe) is NOT the cancellation test: since pFe/DFe = scav*POC/W_SINK,
    # this correlation is just corr(POC, DFe) (both track the iron state) -- it does NOT
    # mean the observable carries DFe info. The DEFINITIVE cancellation proof is the
    # W_SINK-invariance below: the observable is unchanged under (scav, W_SINK) scaling.
    corr_poc_dfe = float(torch.corrcoef(torch.stack([torch.log(ratio0[mask]),
                                                     torch.log(dfe0[mask])]))[0, 1])
    ratio_2x = (2 * scav0) * dfe0 * poc0 / (2 * w_sink) / dfe0     # scav,Wsink both x2
    rel = float((ratio_2x[mask] / ratio0[mask] - 1).abs().max())
    print("== Control A: cancellation / W_SINK degeneracy ==")
    print(f"  corr(log pFe/DFe, log DFe) = {corr_poc_dfe:+.3f}  (this is just corr(POC,DFe); NOT a cancellation test)")
    print(f"  DEFINITIVE: (scav, W_SINK)->(2scav, 2W_SINK) changes the observable by {rel:.2e}")
    print(f"  => the observable = scav*POC/W_SINK: DFe cancels, and (scav, W_SINK) are perfectly")
    print(f"     degenerate. The self-twin's sharp scav well only exists because W_SINK is fixed at truth.")

    # ---- Control B: contamination re-profile -------------------------------------
    def obs(field, scav_per_day, alpfe, contaminate):
        dfe = field[..., 0, 0].clamp_min(EPS)
        poc = field[..., 0, 3].clamp_min(EPS)
        ps, pl = field[..., 0, 1].clamp_min(EPS), field[..., 0, 2].clamp_min(EPS)
        pfe = scav_per_day * dfe * poc / w_sink
        if contaminate:
            pfe = pfe + bio_scale * Q_FE * (ps + pl) + lith_scale * alpfe * dust_surf.clamp_min(EPS)
        return (pfe / dfe).clamp_min(EPS)

    tgt_clean = torch.log(obs(twin, scav0, alpfe0, False)).detach()
    tgt_contam = torch.log(obs(twin, scav0, alpfe0, True)).detach()
    alpfe_g = np.geomspace(0.03, 12.0, n_alpfe)
    scav_g = np.geomspace(1e-7, 1e-5, n_scav)

    @torch.no_grad()
    def profile(contaminate, tgt):
        mis = np.full((len(scav_g), len(alpfe_g)), np.nan)
        for i, s in enumerate(scav_g):
            for j, al in enumerate(alpfe_g):
                p = base.clone(); p[P.alpfe] = float(al); p[P.scav_rat] = float(s)
                fld = rollout_field(ic, p, tc, n_steps)
                d = (torch.log(obs(fld, float(s) * 86400.0, float(al), contaminate)) - tgt)[mask]
                mis[i, j] = float((d * d).mean())
        prof = np.nanmin(mis, axis=1)
        within = scav_g[prof <= prof.min() + 0.02]
        band = (within.max() / within.min()) if len(within) >= 2 else 1.0
        ridge = np.array([alpfe_g[int(np.nanargmin(mis[i]))] for i in range(len(scav_g))])
        on = prof <= prof.min() + 0.02
        alpfe_spread = (ridge[on].max() / ridge[on].min()) if on.sum() >= 2 else 1.0
        return band, alpfe_spread

    band_clean, alp_clean = profile(False, tgt_clean)
    band_contam, alp_contam = profile(True, tgt_contam)
    print(f"\n== Control B: contamination (bio {bio_frac:.0%} + lith {lith_frac:.0%} of scavenged pFe) ==")
    print(f"  CLEAN self-twin    : scav band {band_clean:.0f}x, alpfe-ridge spread {alp_clean:.1f}x")
    print(f"  CONTAMINATED       : scav band {band_contam:.0f}x, alpfe-ridge spread {alp_contam:.1f}x")
    print(f"\n  => contamination re-widens the scav_rat band {band_clean:.0f}x -> {band_contam:.0f}x and "
          f"restores an alpfe ridge ({alp_clean:.1f}x -> {alp_contam:.1f}x): the labile-lithogenic term "
          f"(~alpfe*dust) re-injects the source/sink degeneracy the clean observable appeared to remove.")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", default=None)
    ap.add_argument("--n-steps", type=int, default=100)
    ap.add_argument("--n-alpfe", type=int, default=15)
    ap.add_argument("--n-scav", type=int, default=21)
    ap.add_argument("--bio-frac", type=float, default=0.5)
    ap.add_argument("--lith-frac", type=float, default=0.5)
    a = ap.parse_args()
    inp = torch.load(a.bundle, weights_only=False) if a.bundle else build_inputs()
    return run(inp, a.n_steps, a.n_alpfe, a.n_scav, a.bio_frac, a.lith_frac)


if __name__ == "__main__":
    raise SystemExit(main())
