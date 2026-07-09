"""Identifiability map: WHERE is the PIC:POC rain ratio an identifiable env-driven closure
in the real observations? (transport-free, cache-free, permutation-tested)

The E2 investigation converged on a nuanced result: a learned env->rain-ratio closure beats
the null in the North Atlantic (Marsh cells) but not the equatorial Pacific, and a
transport-free linear model already recovers most of the signal (so the constraint is LOCAL
env->ratio, not transport-mediated). This script generalizes that to a MAP over every
well-sampled region, using Marsh 2025's **own co-located environment** (SST directly;
Omega_calcite from co-located DIC/AT/T/S) so it needs no per-AOI .pt cache and works
anywhere Marsh has coverage.

For each region and env axis it: bins the surface samples to 1-deg cells (geomean rain
ratio + mean env per cell), then runs the E2's env-regime hold-out with a **trivial OLS**
(fit env->log-ratio on the lower cells, predict the held-out upper-q env band, anomaly-R^2
vs the train mean) -- the transport-free feasibility CEILING. A **permutation test**
(shuffle the env<->ratio cell pairing) gives a null distribution for the hold-out R^2, so a
positive result on few cells is not over-read.

Reading: hold-out anomaly-R^2 > 0 with a small permutation p means the rain ratio is
env-identifiable there (a transport-E2 has real signal to recover); <= 0 / large p means it
is not (the E2 is data-limited there). Linear is a floor -- a real closure could do better
in-sample, but cannot manufacture extrapolation the data does not contain.

Run:  python scripts/marsh_identifiability_map.py
"""
from __future__ import annotations

import numpy as np

from darwindiff.carbonate import calcite_saturation
from darwindiff.daniels_loader import _data_start_index, _to_float
from darwindiff.marsh_loader import DEFAULT_MARSH_PATH

DEPTH_MAX = 50.0
UMOL_PER_KG_TO_MMOL_PER_M3 = 1.025
Q = 0.25
N_PERM = 2000
MIN_CELLS = 12  # below this a hold-out is not worth reporting

# Named regions spanning Marsh's dense areas (lat_min, lat_max, lon_min, lon_max).
REGIONS = [
    ("eqpac",        -5,  15, -160, -110),
    ("natl (AOI)",    50, 65,  -40,  -10),
    ("N.Atl bloom",   45, 65,  -40,   10),
    ("Nordic/Iceland",55, 75,  -30,   20),
    ("S.Atl/Patagon",-60, -40, -70,  -20),
    ("N.Pacific",     40, 62, -180, -120),
    ("California/NEP", 25, 50, -140, -110),
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
    r = __import__("csv").reader(lines[_data_start_index(lines):], delimiter="\t")
    hdr = next(r)
    idx = {"lat": _col(hdr, "Latitude"), "lon": _col(hdr, "Longitude"),
           "depth": _col(hdr, "Depth water"), "cp": _col(hdr, "CaCO3 prod C", "std"),
           "pp": _col(hdr, "PP C", "std"), "T": _col(hdr, "Temp"), "S": _col(hdr, "Sal"),
           "DIC": _col(hdr, "DIC"), "AT": _col(hdr, "AT")}
    n = len(hdr)
    cols = {k: [] for k in idx}
    for row in r:
        if not row or len(row) < n:
            continue
        for k, i in idx.items():
            cols[k].append(_to_float(row[i]) if i >= 0 else np.nan)
    return {k: np.asarray(v, float) for k, v in cols.items()}


def _omega(dic_umol, at_umol, T, S):
    import torch
    dic = torch.as_tensor(dic_umol * UMOL_PER_KG_TO_MMOL_PER_M3)
    at = torch.as_tensor(at_umol * UMOL_PER_KG_TO_MMOL_PER_M3)
    return np.asarray(calcite_saturation(dic, at, torch.as_tensor(T), torch.as_tensor(S))
                      ["omega_c"].to(torch.float64))


def _bin_cells(lat, lon, logr, env):
    """Geomean rain ratio (mean of log) + mean env per 1-deg cell. Returns (env_cell, y_cell)."""
    cy = np.floor(lat).astype(int)
    cx = np.floor(lon).astype(int)
    key = cy.astype(np.int64) * 1000 + cx
    ye, ee = {}, {}
    for k, yy, ev in zip(key, logr, env):
        ye.setdefault(k, []).append(yy)
        ee.setdefault(k, []).append(ev)
    yc = np.array([np.mean(v) for v in ye.values()])   # mean log-ratio (geomean)
    ec = np.array([np.mean(ee[k]) for k in ye])        # mean env
    return ec, yc


def _holdout_r2(env, y, q=Q):
    n = len(y)
    order = np.argsort(env)
    k = max(1, int(np.ceil(q * n)))
    val, train = order[-k:], order[:-k]
    if len(train) < 3:
        return np.nan
    b, a = np.polyfit(env[train], y[train], 1)
    pred = b * env[val] + a
    tm = y[train].mean()
    ss_res = np.sum((pred - y[val]) ** 2)
    ss_tot = np.sum((y[val] - tm) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def _perm_p(env, y, observed, n_perm=N_PERM):
    if not np.isfinite(observed):
        return np.nan
    rng = np.random.default_rng(0)
    ge = 0
    for _ in range(n_perm):
        yp = rng.permutation(y)
        r = _holdout_r2(env, yp)
        if np.isfinite(r) and r >= observed:
            ge += 1
    return (ge + 1) / (n_perm + 1)


def _region_mask(d, box):
    _, la0, la1, lo0, lo1 = box
    return ((d["lat"] >= la0) & (d["lat"] <= la1) & (d["lon"] >= lo0) & (d["lon"] <= lo1))


def _bh_fdr(pvals, alpha=0.1):
    """Benjamini-Hochberg: return a boolean 'survives FDR' array aligned to pvals."""
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p)
    thresh = (np.arange(1, m + 1) / m) * alpha
    passed = p[order] <= thresh
    keep = np.zeros(m, bool)
    if passed.any():
        kmax = np.max(np.where(passed)[0])
        keep[order[: kmax + 1]] = True
    return keep


def _partial_r(y, x, z):
    """Partial correlation r(y, x | z) and its two-sided t-test p (df = n-3)."""
    from math import sqrt

    def _r(a, b):
        return float(np.corrcoef(a, b)[0, 1])
    ryx, ryz, rxz = _r(y, x), _r(y, z), _r(x, z)
    denom = sqrt(max((1 - ryz ** 2) * (1 - rxz ** 2), 1e-12))
    pr = (ryx - ryz * rxz) / denom
    n = len(y)
    if n <= 3 or abs(pr) >= 1:
        return pr, float("nan")
    t = pr * sqrt((n - 3) / max(1 - pr ** 2, 1e-12))
    # two-sided p via survival of Student-t; use a normal approx if scipy absent
    try:
        from scipy import stats
        p = 2 * stats.t.sf(abs(t), n - 3)
    except Exception:
        from math import erfc
        p = erfc(abs(t) / sqrt(2))
    return pr, float(p)


def _analyze_axis(name, env_pts, logr_pts, lat, lon, axis):
    """Return a result dict (or None if too few cells) for one region-axis test."""
    ec, yc = _bin_cells(lat, lon, logr_pts, env_pts)
    if len(yc) < MIN_CELLS:
        print(f"  {name:16s} {axis:7s}: {len(yc):3d} cells  (< {MIN_CELLS}, skip)")
        return None
    insample = 1.0 - np.sum((yc - np.polyval(np.polyfit(ec, yc, 1), ec)) ** 2) / \
        max(np.sum((yc - yc.mean()) ** 2), 1e-12)
    ho = _holdout_r2(ec, yc)
    p = _perm_p(ec, yc, ho)
    return {"region": name, "axis": axis, "n": len(yc), "insample": insample,
            "ho": ho, "p": p}


def main() -> int:
    if not DEFAULT_MARSH_PATH.is_file():
        print(f"Marsh file not staged: {DEFAULT_MARSH_PATH}")
        return 1
    d = load_full()
    surf = (np.isfinite(d["lat"]) & np.isfinite(d["lon"]) & np.isfinite(d["depth"])
            & (d["depth"] <= DEPTH_MAX) & (d["cp"] > 0) & (d["pp"] > 0))
    logr = np.log(d["cp"] / np.where(d["pp"] > 0, d["pp"], np.nan))
    print("Marsh 2025 rain-ratio identifiability map (transport-free cell-level, "
          f"q={Q}, {N_PERM} perms, BH-FDR corrected)\n")

    results = []
    print("=== SST axis (co-located Temp) ===")
    for box in REGIONS:
        m = surf & np.isfinite(d["T"]) & _region_mask(d, box)
        r = _analyze_axis(box[0], d["T"][m], logr[m], d["lat"][m], d["lon"][m], "SST") \
            if int(m.sum()) >= MIN_CELLS else None
        if r:
            results.append(r)

    print("\n=== Omega_calcite axis (co-located DIC/AT/T/S) ===")
    for box in REGIONS:
        m = (surf & np.isfinite(d["DIC"]) & np.isfinite(d["AT"]) & np.isfinite(d["T"])
             & np.isfinite(d["S"]) & _region_mask(d, box))
        if int(m.sum()) < MIN_CELLS:
            print(f"  {box[0]:16s} Omega  : {int(m.sum()):3d} pts (skip)"); continue
        om = _omega(d["DIC"][m], d["AT"][m], d["T"][m], d["S"][m])
        g = np.isfinite(om)
        r = _analyze_axis(box[0], om[g], logr[m][g], d["lat"][m][g], d["lon"][m][g], "Omega")
        if r:
            results.append(r)

    # --- multiplicity correction over ALL region-axis tests (the referee fix) ---
    survive = _bh_fdr([r["p"] for r in results], alpha=0.1)
    print(f"\n=== VERDICT (BH-FDR over {len(results)} tests, alpha=0.1) ===")
    print(f"  {'region':16s} {'axis':6s} {'n':>3s}  {'hold-out R2':>11s}  {'perm-p':>7s}  verdict")
    for r, keep in sorted(zip(results, survive), key=lambda t: t[0]["p"]):
        v = "IDENTIFIABLE" if (keep and r["ho"] > 0) else \
            ("uncorrected-only" if (r["ho"] > 0 and r["p"] < 0.1) else "no")
        print(f"  {r['region']:16s} {r['axis']:6s} {r['n']:3d}  {r['ho']:+11.2f}  "
              f"{r['p']:7.3f}  {v}")

    # --- partial correlations: does Omega add skill BEYOND SST (and vice versa)? ---
    # (the collinearity disentangler: Omega and SST are correlated within regions, so a
    # marginal Omega hit can be temperature in disguise. Partial-r isolates unique signal.)
    print("\n=== Partial correlations on matched cells (Omega vs SST, controlling each other) ===")
    print(f"  {'region':16s} {'n':>3s}  {'r(OM,SST)':>9s}  {'r(y,OM|SST)':>11s} {'p':>6s}  "
          f"{'r(y,SST|OM)':>11s} {'p':>6s}")
    for box in REGIONS:
        m = (surf & np.isfinite(d["DIC"]) & np.isfinite(d["AT"]) & np.isfinite(d["T"])
             & np.isfinite(d["S"]) & _region_mask(d, box))
        if int(m.sum()) < MIN_CELLS:
            continue
        om = _omega(d["DIC"][m], d["AT"][m], d["T"][m], d["S"][m])
        g = np.isfinite(om)
        oc, yc = _bin_cells(d["lat"][m][g], d["lon"][m][g], logr[m][g], om[g])
        sc, _ = _bin_cells(d["lat"][m][g], d["lon"][m][g], logr[m][g], d["T"][m][g])
        if len(yc) < MIN_CELLS or len(sc) != len(yc):
            continue
        r_os = float(np.corrcoef(oc, sc)[0, 1])
        pr_o, po = _partial_r(yc, oc, sc)   # Omega controlling SST
        pr_s, ps = _partial_r(yc, sc, oc)   # SST controlling Omega
        print(f"  {box[0]:16s} {len(yc):3d}  {r_os:+9.2f}  {pr_o:+11.2f} {po:6.3f}  "
              f"{pr_s:+11.2f} {ps:6.3f}")

    print("\nIDENTIFIABLE = hold-out anomaly-R2 > 0 AND survives BH-FDR (perm-p corrected across")
    print("all tests). Partial-r isolates whether Omega adds extrapolation signal BEYOND SST")
    print("(and vice versa) where the two are collinear. Linear is a FLOOR; small n_val (~4-7")
    print("held-out cells) -> these map WHERE a real closure has signal, not a validated closure.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
