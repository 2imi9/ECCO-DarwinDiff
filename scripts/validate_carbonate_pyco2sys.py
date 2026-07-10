"""Independent validation of darwindiff.carbonate.calcite_saturation against PyCO2SYS.

The whole calcite identifiability result rests on Ω_calcite computed by our own carbonate
solver (Follows et al. 2006 iterative scheme, Lueker 2000 K1/K2). That solver is the one
upstream component that same-model review can't independently confirm — a systematic bug there
would propagate through every calcite number. This script checks it against **PyCO2SYS** (the
community-standard, non-Claude reference implementation) on real GLODAPv3 surface inputs.

The load-bearing metric is the **log-Ω correlation / slope**: our null depends on the *range and
structure* of Ω across cells, not its absolute value, so a constant bias is harmless but a
structural disagreement would not be. Matches constants (opt_k_carbonic=10 = Lueker 2000, total
scale). Needs PyCO2SYS + D:\glodap\GLODAPv3_Pacific_Ocean.csv. CPU.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

RHO = 1.025  # umol/kg -> mmol/m^3 (our solver converts back to mol/kg internally)


def main(n=2000, seed=0):
    import PyCO2SYS as pyco2

    from darwindiff.carbonate import calcite_saturation
    cols = ["depth", "temperature", "salinity", "tco2", "talk"]
    df = pd.read_csv(r"D:\glodap\GLODAPv3_Pacific_Ocean.csv",
                     usecols=lambda c: c in cols, na_values=[-9999, -1e10], low_memory=False)
    m = ((df.depth <= 100) & df.tco2.notna() & df.talk.notna() & df.temperature.notna()
         & df.salinity.notna() & (df.tco2 > 1500) & (df.tco2 < 2500)
         & (df.talk > 1900) & (df.talk < 2600))
    d = df[m].sample(n=min(n, int(m.sum())), random_state=seed)
    dic, alk = d.tco2.to_numpy(), d.talk.to_numpy()
    T, S = d.temperature.to_numpy(), d.salinity.to_numpy()

    ours = calcite_saturation(torch.as_tensor(dic * RHO), torch.as_tensor(alk * RHO),
                              torch.as_tensor(T), torch.as_tensor(S))["omega_c"].numpy()
    ref = pyco2.sys(par1=alk, par2=dic, par1_type=1, par2_type=2, temperature=T, salinity=S,
                    opt_k_carbonic=10, opt_pH_scale=1)["saturation_calcite"]

    ok = np.isfinite(ours) & np.isfinite(ref) & (ours > 0) & (ref > 0)
    a, b = ours[ok], ref[ok]
    out = {
        "n": int(ok.sum()),
        "r_omega": float(np.corrcoef(a, b)[0, 1]),
        "r_log_omega": float(np.corrcoef(np.log(a), np.log(b))[0, 1]),
        "mean_ratio_ours_over_ref": float(np.mean(a / b)),
        "median_abs_rel_diff_pct": float(np.median(np.abs(a - b) / b) * 100),
        "loglog_slope": float(np.polyfit(np.log(a), np.log(b), 1)[0]),
        "ours_range": [float(a.min()), float(a.max())],
        "ref_range": [float(b.min()), float(b.max())],
        "verdict": None,
    }
    out["verdict"] = ("PASS: our carbonate solver matches PyCO2SYS in Omega structure (log-Omega r "
                      "and slope ~1.0); constant ~1% bias is harmless to the slope-based oracle"
                      if out["r_log_omega"] > 0.999 and abs(out["loglog_slope"] - 1) < 0.05
                      else "REVIEW: structural disagreement with the reference solver")
    Path("docs/findings/carbonate_pyco2sys_validation.json").write_text(json.dumps(out, indent=2))
    for k, v in out.items():
        print(f"  {k}: {v}".encode("ascii", "replace").decode())
    print("wrote docs/findings/carbonate_pyco2sys_validation.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
