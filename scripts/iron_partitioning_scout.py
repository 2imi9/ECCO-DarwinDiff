"""E2-hunt lever 1 (iron): does the particulate:dissolved Fe PARTITIONING break the
scavenging-rate information wall that dissolved concentration alone hits?

`iron_scav_rat_profile.py` showed the wall: steady-state DFe ~ alpfe*dust /
(scav_rat*POC), so the (alpfe, scav_rat) misfit surface is a degenerate ridge and
the scav_rat profile is FLAT -- concentration constrains the source/sink
*combination*, not the rate.

The scavenging SINK flux is ``scav_rat * DFe * POC`` -> it becomes particulate
iron. So the particulate standing stock (sinking at ``W_SINK``) is
``pFe ~= scav_rat * DFe * POC / W_SINK``, and the **partitioning ratio**
``pFe/DFe ~= scav_rat * POC / W_SINK`` has **no direct alpfe dependence** -- it is
the axis the dissolved-only wall is flat along. GEOTRACES measures exactly this:
``Fe_TP_CONC`` (total particulate Fe) alongside ``Fe_D_CONC`` (dissolved).

This scout is the **cost-first go/no-go** for that lever: on the same real eqpac
footprint + prescribed transport as the wall demo, sweep (alpfe, scav_rat) and
compare the profiled scav_rat likelihood for two self-twin targets -- dissolved
DFe (reproduces the wall) vs the partitioning ratio pFe/DFe. If the partitioning
profile is sharply curved where DFe-only is flat, the observable is rate-informative
-> a real E2 with GEOTRACES Fe_TP is warranted. This is a **self-twin capacity
result** (does the observable identify the rate *in principle*), NOT a real-data
recovery, and it carries a real caveat: measured Fe_TP also includes biogenic /
lithogenic particulate iron, not only scavenged Fe -- which a real E2 must handle.

Runs CPU (``CUDA_VISIBLE_DEVICES=``); a few hundred launch-bound rollouts.
"""
from __future__ import annotations

import argparse

import numpy as np
import torch

from darwindiff.carroll6 import P, W_SINK
from darwindiff.trainer import TransportConfig, rollout_field

# reuse the wall demo's real-footprint input builder verbatim
from iron_scav_rat_profile import DX, DY, DZ, EPS, N_Z, build_inputs


def _profile(misfit: np.ndarray, scav_g: np.ndarray, alpfe_g: np.ndarray, band: float = 0.02):
    """Profile out alpfe (min misfit over alpfe at each scav_rat). Return the
    profiled curve, the near-best scav_rat band, and the best-alpfe ridge."""
    prof = np.nanmin(misfit, axis=1)
    within = scav_g[prof <= prof.min() + band]
    ridge = np.array([alpfe_g[int(np.nanargmin(misfit[i]))] for i in range(len(scav_g))])
    return prof, within, ridge


def run(inp: dict, n_steps: int = 100, n_alpfe: int = 13, n_scav: int = 15) -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    dtype = torch.float32 if device.type == "cuda" else torch.float64
    to = lambda t: t.to(device=device, dtype=(torch.bool if t.dtype == torch.bool else dtype))
    u, v, w, dust, ic, mask, base = (to(inp[k]) for k in ("u", "v", "w", "dust", "ic", "mask", "base"))
    tc = TransportConfig(dx=DX, dy=DY, dz=DZ, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w, dust=dust)
    print(f"[partitioning] device={device} dtype={dtype} covered cells={int(mask.sum())}")
    w_sink = float(W_SINK)

    def observables(field, scav_per_day):
        """Surface DFe and the partitioning ratio pFe/DFe from a rolled field.
        pFe (scavenged particulate standing stock) ~= scav*DFe*POC / W_SINK."""
        dfe = field[..., 0, 0].clamp_min(EPS)
        poc = field[..., 0, 3].clamp_min(EPS)
        pfe = scav_per_day * dfe * poc / w_sink
        return dfe, (pfe / dfe).clamp_min(EPS)

    # self-twin target at Carroll
    with torch.no_grad():
        twin = rollout_field(ic, base, tc, n_steps)
    scav0 = float(base[P.scav_rat]) * 86400.0
    dfe0, ratio0 = observables(twin, scav0)
    tgt_dfe = torch.log(dfe0).detach()
    tgt_ratio = torch.log(ratio0).detach()
    print(f"[partitioning] twin at Carroll alpfe={float(base[P.alpfe]):.3f} "
          f"scav_rat={float(base[P.scav_rat]):.2e}; median pFe/DFe={float(ratio0[mask].median()):.3g}")

    alpfe_g = np.geomspace(0.03, 12.0, n_alpfe)
    scav_g = np.geomspace(1e-7, 1e-5, n_scav)
    mis_dfe = np.full((len(scav_g), len(alpfe_g)), np.nan)
    mis_ratio = np.full((len(scav_g), len(alpfe_g)), np.nan)

    @torch.no_grad()
    def fit(alpfe, scav):
        p = base.clone()
        p[P.alpfe] = float(alpfe)
        p[P.scav_rat] = float(scav)
        field = rollout_field(ic, p, tc, n_steps)
        dfe, ratio = observables(field, float(scav) * 86400.0)
        d_dfe = (torch.log(dfe) - tgt_dfe)[mask]
        d_ratio = (torch.log(ratio) - tgt_ratio)[mask]
        return float((d_dfe * d_dfe).mean()), float((d_ratio * d_ratio).mean())

    for i, s in enumerate(scav_g):
        for j, al in enumerate(alpfe_g):
            mis_dfe[i, j], mis_ratio[i, j] = fit(al, s)
        print(f"[partitioning] scav row {i + 1}/{len(scav_g)} done", flush=True)

    prof_d, within_d, ridge_d = _profile(mis_dfe, scav_g, alpfe_g)
    prof_r, within_r, ridge_r = _profile(mis_ratio, scav_g, alpfe_g)

    def band_x(within):
        return (within.max() / within.min()) if len(within) >= 2 else 1.0

    print("\n[partitioning] scav_rat PROFILE (min misfit over alpfe):")
    print(f"  {'scav_rat':>10s}  {'DFe-only':>10s}  {'partition':>10s}")
    for i, s in enumerate(scav_g):
        f_d = " <-flat" if s in within_d else ""
        f_r = " <-flat" if s in within_r else ""
        print(f"  {s:10.2e}  {prof_d[i]:10.4f}{f_d:7s}  {prof_r[i]:10.4f}{f_r}")

    bx_d, bx_r = band_x(within_d), band_x(within_r)
    print(f"\n[partitioning] DFe-only  unidentifiable band: {bx_d:.0f}x  "
          f"({within_d.min():.1e}..{within_d.max():.1e})" if len(within_d) >= 2 else
          f"\n[partitioning] DFe-only  band: single point")
    print(f"[partitioning] partition unidentifiable band: {bx_r:.0f}x  "
          f"({within_r.min():.1e}..{within_r.max():.1e})" if len(within_r) >= 2 else
          f"[partitioning] partition band: single point (SHARP)")
    verdict = "PASS" if bx_r < bx_d / 3.0 else "NO-BREAK"
    print(f"\n[partitioning] VERDICT: {verdict} -- partitioning tightens the scav_rat band "
          f"{bx_d:.0f}x -> {bx_r:.0f}x ({bx_d / max(bx_r,1e-9):.1f}x tighter). "
          + ("The partitioning observable is rate-informative where DFe-only is flat; a real "
             "E2 with GEOTRACES Fe_TP is warranted (caveat: measured Fe_TP includes non-scavenged "
             "particulate Fe)." if verdict == "PASS" else
             "Partitioning does not meaningfully tighten the rate; the wall survives this lever."))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle", type=str, default=None, help="load inputs from a wall-demo bundle")
    ap.add_argument("--n-steps", type=int, default=100)
    ap.add_argument("--n-alpfe", type=int, default=13)
    ap.add_argument("--n-scav", type=int, default=15)
    args = ap.parse_args()
    inp = torch.load(args.bundle, weights_only=False) if args.bundle else build_inputs()
    return run(inp, args.n_steps, args.n_alpfe, args.n_scav)


if __name__ == "__main__":
    raise SystemExit(main())
