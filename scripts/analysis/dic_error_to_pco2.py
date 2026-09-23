"""What a DIC error means in pCO2: the Revelle amplification an emulator's R^2 does not show.

A biogeochemical emulator that predicts DIC but not alkalinity cannot diagnose surface pCO2 or the
air-sea CO2 flux, and its skill is usually quoted as an R^2 or an RMSE on DIC itself. This script
asks what a DIC error of a given size would mean for pCO2 if alkalinity, temperature and salinity
were known perfectly. It is a SENSITIVITY of the carbonate system, not a measurement of anybody's
emulator: no emulator output is read here.

The DIC perturbations default to 2 and 4 umol/kg because those are the two magnitudes the
SamudraBGC model card reports (validation-period DIC bias "below 2 umol/kg"; time-mean meridional
DIC section RMSE 4.0 umol/kg). Neither of those is a SURFACE error, so the mapping is conditional:
"if the surface error were this large, then". See
docs/findings/2026-09-19_samudrabgc_m2lines_now_does_bgc.md.

Solver: darwindiff.carbonate.solve_carbonate (Follows et al. 2006, Lueker 2000 K1/K2). Its calcite
saturation state is validated against PyCO2SYS on 2000 GLODAPv3 surface points by
scripts/validate_carbonate_pyco2sys.py (r = 0.9999); its pCO2 output has NOT been compared with
PyCO2SYS directly, so the numbers below inherit the solver's pCO2 accuracy unverified. The
Revelle factor is taken by autograd, which is the point of having a differentiable solver. CPU,
no data needed.

Run:
  python scripts/analysis/dic_error_to_pco2.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import torch

_SRC = Path(__file__).resolve().parents[2] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

RHO = 1.025  # umol/kg -> mmol/m^3 (the solver converts back to mol/kg internally)

# Representative surface regimes: DIC, ALK (umol/kg), T (degC), S. The first two bracket the
# oligotrophic-subtropical / productive-subpolar contrast a double-gyre configuration spans.
REGIMES = {
    "subtropical_gyre": (2050.0, 2350.0, 22.0, 36.0),
    "subpolar_gyre": (2120.0, 2310.0, 8.0, 34.8),
    "mid_15C": (2080.0, 2320.0, 15.0, 35.0),
}
DIC_ERRORS = (2.0, 4.0)  # umol/kg


def main(out="docs/findings/dic_error_to_pco2.json"):
    from darwindiff.carbonate import solve_carbonate

    rows = {}
    for name, (dic, alk, temp, sal) in REGIMES.items():
        base = solve_carbonate(dic * RHO, alk * RHO, temp, sal)["pCO2"].item()
        dic_t = torch.tensor(dic * RHO, requires_grad=True)
        p = solve_carbonate(dic_t, alk * RHO, temp, sal)["pCO2"]
        (g,) = torch.autograd.grad(p, dic_t)
        row = {"dic_umolkg": dic, "alk_umolkg": alk, "T_degC": temp, "S": sal,
               "pco2_uatm": round(base, 2), "revelle": round((g * dic_t / p).item(), 2)}
        for d in DIC_ERRORS:
            pert = solve_carbonate((dic + d) * RHO, alk * RHO, temp, sal)["pCO2"].item()
            row[f"dpco2_uatm_for_ddic_{d:g}"] = round(pert - base, 2)
        rows[name] = row
        print(f"{name:18s} pCO2={base:6.1f} uatm  Revelle={row['revelle']:5.2f}  "
              + "  ".join(f"dDIC=+{d:g} -> +{row[f'dpco2_uatm_for_ddic_{d:g}']:.2f} uatm"
                          for d in DIC_ERRORS))
    Path(out).write_text(json.dumps({"dic_errors_umolkg": list(DIC_ERRORS), "regimes": rows},
                                    indent=2))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
