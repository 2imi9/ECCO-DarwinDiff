"""Forward-model control for the iron-partitioning finding — the REAL W_SINK / alpfe
experiment the original Control A skipped.

Background. The retracted "partitioning breaks the wall" scout scored pFe/DFe, which
reduces algebraically to ``scav_rat*POC/W_SINK`` (DFe cancels). The first correction
(``iron_partitioning_controls.py`` Control A) then asserted that ``(scav, W_SINK)`` are
*perfectly* degenerate — that ``(scav, W_SINK) -> (k*scav, k*W_SINK)`` leaves the
observable unchanged. But that "control" was itself an algebraic identity: it computed
``(2*scav)*POC0/(2*W_SINK)/DFe0`` on the FROZEN truth POC field, so the two 2's cancel by
construction and the change is 0 by definition. It never re-ran the forward model.

W_SINK is NOT an inert divisor: in ``transport.py`` the POC budget is
``dPOC = mort_total - W_SINK*POC`` (so steady-state POC ~ mort/W_SINK). Changing W_SINK
therefore changes POC, and the observable ``scav*POC/W_SINK`` responds. This script does the
honest thing — it varies W_SINK (and alpfe) INSIDE ``rollout_field`` and measures the actual
observable change:

  T1  W_SINK x2 (scav fixed):        does POC drop (W_SINK governs POC)?
  T2  equal scaling (scav,W)->(2,2): the "perfectly degenerate" claim — REAL change != 0?
  T3  the proposed (k^2,k) invariant (scav x4, W x2): is even THAT a clean invariant?
  T4  alpfe x3 (scav,W fixed):       does the "pure" observable move (alpfe leaks via POC)?

Verdicts (do not change the paper-level negative — the rate is still not cleanly identifiable):
  * the (scav, W_SINK) pair is NOT perfectly degenerate (equal scaling changes the observable);
  * W_SINK is partially self-identifying through POC;
  * the "pure" scavenged pFe/DFe is NOT insensitive to the iron source — alpfe re-enters via POC,
    modestly.

CPU only. Needs D:\\ecco_darwin_v5\\cache\\eqpac_targets_equatorial_pacific.pt (via build_inputs).
Run:  CUDA_VISIBLE_DEVICES=-1 python scripts/iron_partitioning_forward_control.py \
        --out docs/findings/iron_partitioning_forward_control.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")
os.environ.setdefault("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5")
sys.path.insert(0, str(Path(__file__).resolve().parent))

import torch

import darwindiff.transport as T
from darwindiff.carroll6 import P
from darwindiff.trainer import TransportConfig, rollout_field
from iron_scav_rat_profile import DX, DY, DZ, EPS, build_inputs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n-steps", type=int, default=100, help="rollout steps (match the finding's controls)")
    ap.add_argument("--out", default=None, help="write JSON verdict here")
    args = ap.parse_args()

    dev, dtp = torch.device("cpu"), torch.float64
    inp = build_inputs()
    to = lambda t: t.to(device=dev, dtype=(torch.bool if t.dtype == torch.bool else dtp))
    u, v, w, dust, ic, mask, base = (to(inp[k]) for k in ("u", "v", "w", "dust", "ic", "mask", "base"))
    tc = TransportConfig(dx=DX, dy=DY, dz=DZ, dt=0.25, kz=50.0, kh=50.0, u=u, v=v, w=w, dust=dust)
    m = mask if mask.dtype == torch.bool else (mask > 0)
    W0 = float(T.W_SINK)
    scav0 = float(base[P.scav_rat]) * 86400.0
    N = args.n_steps

    def roll(params, wsink):
        old = T.W_SINK
        T.W_SINK = wsink
        try:
            with torch.no_grad():
                return rollout_field(ic, params, tc, N)
        finally:
            T.W_SINK = old

    def pure_obs(fld, scav_per_day, wsink):          # pFe/DFe (pure) = scav*POC/W_SINK
        return scav_per_day * fld[..., 0, 3].clamp_min(EPS) / wsink

    def med(x):
        return float(x[m].median())

    f0 = roll(base, W0)
    poc0 = f0[..., 0, 3].clamp_min(EPS)
    obs0 = pure_obs(f0, scav0, W0)

    # T1: W_SINK x2 alone
    f_2w = roll(base, 2 * W0)
    t1_poc = med(f_2w[..., 0, 3].clamp_min(EPS) / poc0)

    # T2: equal scaling (scav, W_SINK) -> (2x, 2x) -- the "perfectly degenerate" claim
    p2 = base.clone(); p2[P.scav_rat] = base[P.scav_rat] * 2
    t2_obs = med(pure_obs(roll(p2, 2 * W0), 2 * scav0, 2 * W0) / obs0)

    # T3: proposed (k^2, k) invariant, k=2
    p4 = base.clone(); p4[P.scav_rat] = base[P.scav_rat] * 4
    t3_obs = med(pure_obs(roll(p4, 2 * W0), 4 * scav0, 2 * W0) / obs0)

    # T4: alpfe x3 vs scav x3 sensitivity of the pure observable
    pa = base.clone(); pa[P.alpfe] = base[P.alpfe] * 3
    dex_alpfe = math.log10(med(pure_obs(roll(pa, W0), scav0, W0) / obs0))
    ps = base.clone(); ps[P.scav_rat] = base[P.scav_rat] * 3
    dex_scav = math.log10(med(pure_obs(roll(ps, W0), scav0 * 3, W0) / obs0))

    out = {
        "description": ("REAL forward-model control for the iron-partitioning finding: varies "
                        "W_SINK / alpfe INSIDE rollout_field (the original Control A used a frozen-POC "
                        "algebraic identity). Confirms (scav_rat, W_SINK) are NOT perfectly degenerate "
                        "and the pure pFe/DFe observable is NOT insensitive to the iron source; the "
                        "paper-level negative (rate not cleanly identifiable) is unchanged."),
        "config": {"n_steps": N, "n_cells": int(m.sum()), "W_SINK0": W0,
                   "scav0_per_day": scav0, "alpfe0": float(base[P.alpfe])},
        "T1_wsink_x2_poc_ratio": round(t1_poc, 4),
        "T2_equal_scaling_obs_ratio": round(t2_obs, 4),
        "T2_equal_scaling_pct_change": round(abs(t2_obs - 1) * 100, 1),
        "T3_k2k_invariant_obs_ratio": round(t3_obs, 4),
        "T4_alpfe_x3_dex": round(dex_alpfe, 4),
        "T4_scav_x3_dex": round(dex_scav, 4),
        "T4_alpfe_over_scav_sensitivity": round(dex_alpfe / dex_scav, 3) if dex_scav else None,
        "verdicts": {
            "wsink_perfectly_degenerate": bool(abs(t2_obs - 1) < 0.05),
            "wsink_partially_self_identifying_via_poc": bool(abs(t1_poc - 1) > 0.1),
            "pure_obs_source_insensitive": bool(abs(dex_alpfe) < 0.05),
            "clean_1d_degeneracy_of_pair": bool(abs(t3_obs - 1) < 0.1),
        },
    }
    print(json.dumps(out, indent=2))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(out, indent=2))
        print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
