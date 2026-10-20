#!/usr/bin/env python
"""Gate 0b of the Sentinel-3 side-helper plan: can a satellite observable see each parameter?

For every Carroll-6 parameter and every candidate surface observable, this computes the
log-sensitivity ``s = d log y / d log theta`` of the time-mean observable through the
differentiable box (autograd, float64), then the signal a band-sized parameter change produces,

    signal_dex = |s| * log10(1.4)

and compares it with a retrieval noise floor in dex. A parameter whose signal sits below the floor
in every regime is not visible to that observable, whatever model sits on top of the radiance.

Observables, all time-means over the window:

* ``chl``    -- Ps + Pl. The box carries carbon; a fixed Chl:C factor cancels in a log-sensitivity.
* ``pic``, ``poc``
* ``pp``     -- primary production, (mu_s Ps + mu_l Pl) * f_Fe * LIGHT
* ``cp``     -- calcite production, R_PICPOC * M_tot
* ``cp_pp``  -- ratio of the two means: the Daniels observation operator
* ``pic_poc`` -- the standing-stock ratio a satellite PIC/POC pair would give
* ``f_fe``   -- iron limitation DFe / (DFe + K_FE), the quantity a fluorescence quantum-yield
  (iron-stress) retrieval proxies
* ``dfe``    -- dissolved iron, NOT satellite-visible; the in-situ reference row

Two combined columns follow the six parameters. ``alpfe+scav`` scales both by the same factor, the
direction the iron degeneracy leaves free (``d log y/d log alpfe + d log y/d log scav_rat``);
``alpfe-scav`` moves them in opposition, for contrast. An observable that cannot see ``alpfe+scav``
cannot separate the pair, whatever its sensitivity to either parameter alone.

The only measured noise floor in the repo is Chl, 0.130 dex (MODIS vs v05,
``docs/findings/2026-07-21_chl_binning_recompute.md``). PIC, PP and CP/PP floors are not yet sourced,
so the table reports raw signal and flags against the Chl floor only as a reference.

LIMITATION. The AOI initial-condition caches (``scripts/darwin_ic_cache_*.npz``) are built from the
v05 archive and are not committed; without them this runs three stylised iron regimes on the
default background constants. It is a first-order screen of the 0-D box, not the flagship geometry.

Usage::

    python scripts/analysis/satellite_observable_screen.py
    python scripts/analysis/satellite_observable_screen.py --n-steps 1460
"""
from __future__ import annotations

import argparse
import math

import torch

from darwindiff import carroll6 as C
from darwindiff.carroll6 import PARAMS, P

CAL_GRADE_BAND = 0.40
CHL_FLOOR_DEX = 0.130

#: Stylised regimes, by initial dissolved iron relative to K_FE (5e-5 mmol/m^3).
REGIMES: dict[str, float] = {
    "iron-limited": 0.4 * C.K_FE,
    "near-K_Fe": 1.0 * C.K_FE,
    "iron-replete": 10.0 * C.K_FE,
}
OBSERVABLES = ("chl", "pic", "poc", "pp", "cp", "cp_pp", "pic_poc", "f_fe", "dfe")


def time_mean_observables(
    log_params: torch.Tensor, dfe0: float, n_steps: int, dt: float = 0.25
) -> torch.Tensor:
    params = torch.exp(log_params)
    s = torch.tensor([dfe0, 0.1, 0.1, 0.1, 0.01], dtype=torch.float64)
    acc = torch.zeros(8, dtype=torch.float64)
    for _ in range(n_steps):
        DFe, Ps, Pl, POC, PIC = s[0], s[1], s[2], s[3], s[4]
        f_fe = DFe / (DFe + C.K_FE)
        pp = (params[P.Smallgrow] * Ps + params[P.Biggrow] * Pl) * f_fe * C.LIGHT
        m_tot = (
            C.M_LIN * (Ps + Pl)
            + C.M_QUAD * (Ps * Ps + Pl * Pl)
            + params[P.diatomgraz] * C.G0_GRAZE * Pl
        )
        cp = params[P.R_PICPOC] * m_tot
        acc = acc + torch.stack([Ps + Pl, PIC, POC, pp, cp, DFe, m_tot, f_fe])
        s = torch.clamp(s + dt * C.carroll6_tendency(s, params), min=1e-12)
    m = acc / n_steps
    chl, pic, poc, pp, cp, dfe, f_fe_mean = m[0], m[1], m[2], m[3], m[4], m[5], m[7]
    return torch.stack([chl, pic, poc, pp, cp, cp / pp, pic / poc, f_fe_mean, dfe])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--n-steps", type=int, default=200, help="run window; flagship is 200")
    args = ap.parse_args()

    base = torch.log(torch.tensor([p.carroll_value for p in PARAMS], dtype=torch.float64))
    band_dex = math.log10(1.0 + CAL_GRADE_BAND)
    names = [p.name for p in PARAMS]

    print(f"window {args.n_steps} steps x 0.25 d; signal = |dlog y/dlog theta| * log10(1.4) "
          f"= |s| * {band_dex:.3f} dex; Chl floor {CHL_FLOOR_DEX} dex")
    for regime, dfe0 in REGIMES.items():
        jac = torch.autograd.functional.jacobian(
            lambda lp: torch.log(time_mean_observables(lp, dfe0, args.n_steps)), base
        )
        print(f"\n[{regime}]  DFe0 = {dfe0:.1e} mmol/m^3   signal in dex (* = above Chl floor)")
        cols = [*names, "alpfe+scav", "alpfe-scav"]
        print(f"{'':>9}" + "".join(f"{n:>12}" for n in cols))
        for i, obs in enumerate(OBSERVABLES):
            s_a, s_s = float(jac[i, P.alpfe]), float(jac[i, P.scav_rat])
            sens = [float(jac[i, j]) for j in range(len(names))] + [s_a + s_s, s_a - s_s]
            row = ""
            for s in sens:
                sig = abs(s) * band_dex
                flag = "*" if sig > CHL_FLOOR_DEX else " "
                row += f"{sig:>11.4f}{flag}"
            print(f"{obs:>9}" + row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
