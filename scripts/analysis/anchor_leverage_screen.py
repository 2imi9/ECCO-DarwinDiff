#!/usr/bin/env python
"""Design-time leverage screen for a proposed observational anchor.

Before wiring a new anchor into the loss and spending a cluster night on it, ask the cheap
question: **can this observable see the parameter at all?**

The screen answers it with two numbers and no fitted model:

1. **Leverage** -- how much the modelled observable moves when the target parameter is swept
   across a stated factor span, at the run's actual integration window.
2. **Required precision** -- how precise the observation must be to resolve a parameter change
   the size of the Cal-grade band.

If the observation's own sigma/value exceeds the required precision, the anchor cannot grade the
parameter, and no amount of coverage or optimisation fixes that. This is the anchor-side sibling
of ``contract.rescale_is_admissible`` and ``contract.bound_proximity_risk``: registry-and-model
arithmetic that fires before compute.

WHY THIS EXISTS. The Black et al. (2020) upper-ocean Fe export compilation was carried in the
repo as the designated SINK anchor for ``scav_rat``, on the premise that a source anchor and a
sink anchor together lift the rank-1 (alpfe <-> scav_rat) degeneracy. Run this screen on it and
the premise fails on mass conservation: in a 0-D box at steady state the total iron leaving the
surface layer EQUALS the iron entering it, so the total export flux is ``alpfe * PHI_DUST`` and
carries exactly zero information about ``scav_rat``. Measured: a 4x change in ``scav_rat`` moves
the total by 0.00% at steady state and 3.2% at the 200-step operating window, against an
observation whose 1-sigma is 412% of its own value.

What the same screen shows IS sensitive is the **partition**: the biogenic share of Fe export
moves 41% for that same 4x. So the discriminating observable is particulate Fe speciation --
scavenged versus biogenic -- not bulk Fe export. That is a redirect the screen produced for the
cost of one 0-D integration.

Usage::

    python scripts/analysis/anchor_leverage_screen.py --param scav_rat --aoi natlsubpolar
    python scripts/analysis/anchor_leverage_screen.py --param scav_rat --obs-sigma-rel 4.12
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import numpy as np
import torch

from darwindiff import carroll6 as C
from darwindiff.carroll6 import PARAMS, P

REPO = Path(__file__).resolve().parents[2]

#: Areal conversion. The box is 0-D; an areal flux needs a layer thickness, and the project's
#: convention for that is H_MLD. Stated here rather than buried, because every flux number the
#: screen prints is linear in it.
H_LAYER_M = C.H_MLD
DAYS_PER_YEAR = 365.25

#: The recovery band. A screen that cannot resolve a change this size cannot grade the parameter.
CAL_GRADE_BAND = 0.40


def _carroll_vector() -> torch.Tensor:
    return torch.tensor([p.carroll_value for p in PARAMS], dtype=torch.float64)


def integrate_fluxes(
    state0: torch.Tensor, params: torch.Tensor, n_steps: int, dt_days: float = 0.25
) -> tuple[float, float]:
    """Time-mean scavenged and biogenic iron export over ``n_steps``.

    Returns ``(scavenged, biogenic)`` in mmol Fe m^-2 yr^-1. The two routes by which dissolved
    iron leaves the box are ``scav_rat * DFe * POC`` and the phytoplankton quota uptake
    ``Q_FE * (growth_s + growth_l)``; a bulk Fe-export observation measures their SUM.
    """
    s = state0.clone()
    scav_int = 0.0
    upt_int = 0.0
    for _ in range(n_steps):
        DFe, Ps, Pl, POC = s[0], s[1], s[2], s[3]
        scav_int += float(params[P.scav_rat] * 86400.0 * DFe * POC) * dt_days
        f_fe = DFe / (DFe + C.K_FE)
        growth = (
            params[P.Smallgrow] * f_fe * C.LIGHT * Ps + params[P.Biggrow] * f_fe * C.LIGHT * Pl
        )
        upt_int += float(C.Q_FE * growth) * dt_days
        s = torch.clamp(s + dt_days * C.carroll6_tendency(s, params), min=1e-12)
    days = n_steps * dt_days
    scale = H_LAYER_M * DAYS_PER_YEAR / days
    return scav_int * scale, upt_int * scale


def ic_state(aoi_key: str) -> torch.Tensor:
    """Median initial condition for an AOI, from the committed Darwin IC cache."""
    path = REPO / "scripts" / f"darwin_ic_cache_{aoi_key}.npz"
    if not path.exists():
        raise FileNotFoundError(
            f"no IC cache for {aoi_key!r} at {path}. Build one with scripts/build_darwin_ic_cache.py"
        )
    d = np.load(path, allow_pickle=True)
    return torch.tensor(
        [
            float(np.nanmedian(d["FeT_L1"])),
            0.1,
            0.1,
            float(np.nanmedian(d["POC_L1"])),
            float(np.nanmedian(d["PIC_L1"])),
        ],
        dtype=torch.float64,
    )


def leverage(
    param: str, aoi_key: str, *, n_steps: int, span: float
) -> dict[str, float]:
    """Fractional response of each candidate observable to a ``span``-fold change in ``param``."""
    idx = {p.name: i for i, p in enumerate(PARAMS)}[param]
    base = _carroll_vector()
    s0 = ic_state(aoi_key)

    def at(mult: float) -> tuple[float, float]:
        p = base.clone()
        p[idx] = base[idx] * mult
        return integrate_fluxes(s0, p, n_steps)

    lo_s, lo_b = at(1.0 / math.sqrt(span))
    md_s, md_b = at(1.0)
    hi_s, hi_b = at(math.sqrt(span))

    def rel(a: float, b: float, ref: float) -> float:
        return abs(b - a) / ref if ref else float("nan")

    return {
        "total": rel(lo_s + lo_b, hi_s + hi_b, md_s + md_b),
        "scav_fraction": rel(
            lo_s / (lo_s + lo_b), hi_s / (hi_s + hi_b), md_s / (md_s + md_b)
        ),
        "biogenic_fraction": rel(
            lo_b / (lo_b + lo_s), hi_b / (hi_b + hi_s), md_b / (md_b + md_s)
        ),
        "scav_flux_mmol_m2_yr": md_s,
        "biogenic_flux_mmol_m2_yr": md_b,
        "total_flux_mmol_m2_yr": md_s + md_b,
    }


def required_precision(lev: float, span: float, band: float = CAL_GRADE_BAND) -> float:
    """Observation sigma/value needed to resolve a band-sized parameter change.

    ``lev`` is the fractional observable response measured over a ``span``-fold parameter change.
    Scaling logarithmically, a band-sized change spans ``(1+band)/(1-band)``.
    """
    band_span = (1.0 + band) / (1.0 - band)
    return lev * math.log(band_span) / math.log(span)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--param", default="scav_rat")
    ap.add_argument("--aoi", default="natlsubpolar")
    ap.add_argument("--n-steps", type=int, default=200, help="run window; flagship is 200")
    ap.add_argument("--span", type=float, default=4.0, help="factor span swept over the parameter")
    ap.add_argument(
        "--obs-sigma-rel",
        type=float,
        default=None,
        help="the observation's own 1-sigma as a fraction of its value, e.g. 4.12",
    )
    a = ap.parse_args()

    lv = leverage(a.param, a.aoi, n_steps=a.n_steps, span=a.span)
    print(f"anchor leverage screen: {a.param} in {a.aoi}, window {a.n_steps} steps, span {a.span}x")
    print(f"  modelled fluxes at Carroll (mmol Fe m^-2 yr^-1):")
    print(f"    scavenged {lv['scav_flux_mmol_m2_yr']:.4g}   biogenic {lv['biogenic_flux_mmol_m2_yr']:.4g}"
          f"   total {lv['total_flux_mmol_m2_yr']:.4g}")
    print(f"  fractional response to a {a.span}x change in {a.param}:")
    for k in ("total", "scav_fraction", "biogenic_fraction"):
        need = required_precision(lv[k], a.span)
        line = f"    {k:<18} {100 * lv[k]:7.2f}%   needs obs precision better than {100 * need:6.2f}%"
        if a.obs_sigma_rel is not None:
            ok = a.obs_sigma_rel <= need
            line += f"   -> {'CAN GRADE' if ok else 'CANNOT GRADE'} at sigma/value {100 * a.obs_sigma_rel:.0f}%"
        print(line)
    if a.obs_sigma_rel is not None and a.obs_sigma_rel > required_precision(lv["total"], a.span):
        short = a.obs_sigma_rel / required_precision(lv["total"], a.span)
        print(f"\n  A bulk-flux anchor is short by a factor of {short:.0f} on the total.")
        print("  The partition carries more signal than the total -- prefer an observable that")
        print("  resolves scavenged vs biogenic particulate Fe over one that measures their sum.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
