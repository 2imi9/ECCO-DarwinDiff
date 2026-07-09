"""Is the Omega signal causal carbonate chemistry, or Omega-as-bloom-proxy?

Marañón et al. (2016, L&O) found tropical calcification INDEPENDENT of carbonate chemistry
across Omega 1.5-6.5 -- so our North-Atlantic-bloom Omega correlation (identifiability map)
may be Omega standing in for the bloom regime (biomass / nutrient / light state), not a
causal Omega effect. This script tests that directly with **partial correlations that
control for biomass**: on the Marsh cells with co-located rain ratio + Omega + SST + Chl-a,
does Omega retain a correlation with log(CP/PP) AFTER regressing out SST and chlorophyll?

  r(y, Omega)                     -- marginal
  r(y, Omega | SST)               -- controls temperature
  r(y, Omega | Chl)               -- controls biomass (bloom proxy)
  r(y, Omega | SST, Chl)          -- controls both

If Omega survives controlling for biomass -> it carries signal beyond the bloom regime
(supports a carbonate-chemistry reading). If it collapses -> it was a bloom proxy, matching
Marañón. Small n (bloom regions ~14-26 cells, fewer with Chl) -> report n and treat as
suggestive. Transport-free, cache-free (Marsh's own co-located env). No GPU.

Run:  python scripts/marsh_omega_vs_bloom.py
"""
from __future__ import annotations

import csv
from math import sqrt

import numpy as np

from darwindiff.carbonate import calcite_saturation
from darwindiff.daniels_loader import _data_start_index, _to_float
from darwindiff.marsh_loader import DEFAULT_MARSH_PATH

DEPTH_MAX = 50.0
UMOL = 1.025
MIN_CELLS = 10

REGIONS = [
    ("N.Atl bloom",   45, 65,  -40,   10),
    ("Nordic/Iceland",55, 75,  -30,   20),
    ("S.Atl/Patagon",-60, -40, -70,  -20),
    ("GLOBAL",       -90,  90, -180, 180),
]


def _col(hdr, s, excl=None):
    for i, h in enumerate(hdr):
        n = h.strip()
        if n.startswith(s) and (excl is None or excl not in n):
            return i
    return -1


def load_full():
    with open(DEFAULT_MARSH_PATH, encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()
    r = csv.reader(lines[_data_start_index(lines):], delimiter="\t")
    hdr = next(r)
    idx = {"lat": _col(hdr, "Latitude"), "lon": _col(hdr, "Longitude"),
           "depth": _col(hdr, "Depth water"), "cp": _col(hdr, "CaCO3 prod C", "std"),
           "pp": _col(hdr, "PP C", "std"), "T": _col(hdr, "Temp"), "S": _col(hdr, "Sal"),
           "DIC": _col(hdr, "DIC"), "AT": _col(hdr, "AT"), "Chl": _col(hdr, "Chl a")}
    n = len(hdr)
    cols = {k: [] for k in idx}
    for row in r:
        if not row or len(row) < n:
            continue
        for k, i in idx.items():
            cols[k].append(_to_float(row[i]) if i >= 0 else np.nan)
    return {k: np.asarray(v, float) for k, v in cols.items()}


def _omega(dic, at, T, S):
    import torch
    return np.asarray(calcite_saturation(
        torch.as_tensor(dic * UMOL), torch.as_tensor(at * UMOL),
        torch.as_tensor(T), torch.as_tensor(S))["omega_c"].to(torch.float64))


def _bin(lat, lon, *fields):
    """Cell means of each field per 1-deg cell (geomean handled by caller passing log)."""
    key = np.floor(lat).astype(np.int64) * 1000 + np.floor(lon).astype(np.int64)
    order = {}
    for i, k in enumerate(key):
        order.setdefault(k, []).append(i)
    out = [np.array([np.mean(f[ix]) for ix in order.values()]) for f in fields]
    return out


def _resid(y, Z):
    """Residuals of y after OLS on columns of Z (with intercept)."""
    A = np.column_stack([np.ones(len(y))] + [z for z in Z])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def _partial(y, x, controls):
    """Partial correlation r(y,x|controls) via residuals + t-test p (df=n-|controls|-2)."""
    ry = _resid(y, controls) if controls else y - y.mean()
    rx = _resid(x, controls) if controls else x - x.mean()
    r = float(np.corrcoef(ry, rx)[0, 1])
    n = len(y)
    df = n - len(controls) - 2
    if df <= 0 or abs(r) >= 1:
        return r, float("nan")
    t = r * sqrt(df / max(1 - r * r, 1e-12))
    try:
        from scipy import stats
        p = 2 * stats.t.sf(abs(t), df)
    except Exception:
        from math import erfc
        p = erfc(abs(t) / sqrt(2))
    return r, float(p)


def main() -> int:
    if not DEFAULT_MARSH_PATH.is_file():
        print(f"Marsh not staged: {DEFAULT_MARSH_PATH}"); return 1
    d = load_full()
    print("Omega-vs-bloom-proxy: does Omega survive controlling for biomass (Chl-a)?\n")
    print(f"  {'region':16s} {'n':>3s}  {'r(y,OM)':>8s}  {'OM|SST':>7s}(p)  "
          f"{'OM|Chl':>7s}(p)  {'OM|SST,Chl':>10s}(p)")
    for name, la0, la1, lo0, lo1 in REGIONS:
        m = (np.isfinite(d["lat"]) & np.isfinite(d["lon"]) & (d["depth"] <= DEPTH_MAX)
             & (d["cp"] > 0) & (d["pp"] > 0) & np.isfinite(d["DIC"]) & np.isfinite(d["AT"])
             & np.isfinite(d["T"]) & np.isfinite(d["S"]) & np.isfinite(d["Chl"]) & (d["Chl"] > 0)
             & (d["lat"] >= la0) & (d["lat"] <= la1) & (d["lon"] >= lo0) & (d["lon"] <= lo1))
        if int(m.sum()) < 4:
            print(f"  {name:16s} {int(m.sum()):3d}  (too few co-located Chl+carbonate)"); continue
        om = _omega(d["DIC"][m], d["AT"][m], d["T"][m], d["S"][m])
        g = np.isfinite(om)
        logr = np.log(d["cp"][m][g] / d["pp"][m][g])
        yc, oc, sc, cc = _bin(d["lat"][m][g], d["lon"][m][g], logr, om[g], d["T"][m][g],
                              np.log(d["Chl"][m][g]))
        if len(yc) < MIN_CELLS:
            print(f"  {name:16s} {len(yc):3d}  (< {MIN_CELLS} cells, skip)"); continue
        r0 = float(np.corrcoef(yc, oc)[0, 1])
        r_s, p_s = _partial(yc, oc, [sc])
        r_c, p_c = _partial(yc, oc, [cc])
        r_sc, p_sc = _partial(yc, oc, [sc, cc])
        print(f"  {name:16s} {len(yc):3d}  {r0:+8.2f}  {r_s:+7.2f}({p_s:.2f})  "
              f"{r_c:+7.2f}({p_c:.2f})  {r_sc:+10.2f}({p_sc:.2f})")

    print("\nOmega SURVIVES controlling for biomass -> signal beyond the bloom regime")
    print("(supports a carbonate-chemistry reading). Omega COLLAPSES -> it was a bloom proxy")
    print("(matches Maranon 2016). Small n -> suggestive, not decisive; log-Chl used as the")
    print("biomass control (co-located; coccolithophore abundance columns are sparser).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
