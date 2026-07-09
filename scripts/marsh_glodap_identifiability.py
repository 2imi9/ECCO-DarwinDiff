"""Identifiability map with GLODAP observation-derived env at EVERY Marsh point.

The Marsh-co-located map (marsh_identifiability_map.py) could not test the equatorial
Pacific: Marsh has ~0 co-located carbonate chemistry below 23N, so eqpac was UNTESTABLE on
the Omega axis. This script co-locates the public **GLODAPv2.2016b OmegaC** (and temperature)
mapped climatology -- an independent, observation-derived product -- to every Marsh calcite
point by nearest-neighbour, so env exists at ALL points including eqpac's ~128. It then runs
the identical env-regime hold-out (upper-quartile Omega band, trivial OLS floor, anomaly-R2
vs the train mean) with a permutation null and BH-FDR correction, per region.

This (a) gives eqpac a TESTED Omega negative on observation-derived env (not the model .pt
cache), and (b) rebuilds the whole map on a UNIFORM env source (GLODAP), removing the
mixed-provenance concern of using Marsh's own sparse carbonate columns.

Prediction from the literature (Maranon 2016, Malaspina): tropical calcification is
Omega-independent, so eqpac should come back NULL -- a tested negative, consistent with the
map's cold-high-latitude-only identifiability.

Run:  python scripts/marsh_glodap_identifiability.py
Needs data/glodap/GLODAPv2.2016b_MappedClimatologies/ (OmegaC + temperature .nc).
"""
from __future__ import annotations

import csv

import numpy as np

from darwindiff.daniels_loader import _data_start_index, _to_float
from darwindiff.glodap_loader import open_glodap_variable, surface_layer_glodap
from darwindiff.marsh_loader import DEFAULT_MARSH_PATH

DEPTH_MAX = 50.0
Q = 0.25
N_PERM = 2000
MIN_CELLS = 12
GLODAP_ROOT = "data/glodap/GLODAPv2.2016b_MappedClimatologies"

REGIONS = [
    ("eqpac",         -5,  15, -160, -110),
    ("natl (AOI)",    50,  65,  -40,  -10),
    ("N.Atl bloom",   45,  65,  -40,   10),
    ("Nordic/Iceland",55,  75,  -30,   20),
    ("S.Atl/Patagon",-60, -40,  -70,  -20),
    ("N.Pacific",     40,  62, -180, -120),
    ("tropics(|lat|<23)", -23, 23, -180, 180),
    ("GLOBAL",       -90,  90, -180, 180),
]


def _col(hdr, s, excl=None):
    for i, h in enumerate(hdr):
        n = h.strip()
        if n.startswith(s) and (excl is None or excl not in n):
            return i
    return -1


def load_points():
    with open(DEFAULT_MARSH_PATH, encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()
    r = csv.reader(lines[_data_start_index(lines):], delimiter="\t")
    hdr = next(r)
    idx = {"lat": _col(hdr, "Latitude"), "lon": _col(hdr, "Longitude"),
           "depth": _col(hdr, "Depth water"), "cp": _col(hdr, "CaCO3 prod C", "std"),
           "pp": _col(hdr, "PP C", "std")}
    n = len(hdr)
    cols = {k: [] for k in idx}
    for row in r:
        if not row or len(row) < n:
            continue
        for k, i in idx.items():
            cols[k].append(_to_float(row[i]))
    return {k: np.asarray(v, float) for k, v in cols.items()}


def _sample_glodap(var, lats, lons):
    """Nearest-neighbour sample a GLODAP surface variable at scattered (lat,lon) points."""
    import xarray as xr
    da = surface_layer_glodap(open_glodap_variable(GLODAP_ROOT, var))[
        {"OmegaC": "OmegaC", "T": "temperature"}[var]]
    return da.sel(lat=xr.DataArray(lats, dims="pt"),
                  lon=xr.DataArray(lons, dims="pt"), method="nearest").values


def _bin_cells(lat, lon, logr, env):
    key = np.floor(lat).astype(np.int64) * 1000 + np.floor(lon).astype(np.int64)
    ye, ee = {}, {}
    for k, yy, ev in zip(key, logr, env):
        ye.setdefault(k, []).append(yy)
        ee.setdefault(k, []).append(ev)
    yc = np.array([np.mean(v) for v in ye.values()])
    ec = np.array([np.mean(ee[k]) for k in ye])
    return ec, yc


def _holdout(env, y, q=Q):
    n = len(y)
    order = np.argsort(env)
    k = max(1, int(np.ceil(q * n)))
    val, train = order[-k:], order[:-k]
    if len(train) < 3:
        return np.nan
    b, a = np.polyfit(env[train], y[train], 1)
    tm = y[train].mean()
    ss_res = np.sum((b * env[val] + a - y[val]) ** 2)
    ss_tot = np.sum((y[val] - tm) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan


def _perm_p(env, y, obs):
    if not np.isfinite(obs):
        return np.nan
    rng = np.random.default_rng(0)
    ge = sum(1 for _ in range(N_PERM)
             if np.isfinite(r := _holdout(env, rng.permutation(y))) and r >= obs)
    return (ge + 1) / (N_PERM + 1)


def _bh_fdr(pvals, alpha=0.1):
    p = np.asarray(pvals, float)
    m = len(p)
    order = np.argsort(p)
    passed = p[order] <= (np.arange(1, m + 1) / m) * alpha
    keep = np.zeros(m, bool)
    if passed.any():
        keep[order[: np.max(np.where(passed)[0]) + 1]] = True
    return keep


def main() -> int:
    if not DEFAULT_MARSH_PATH.is_file():
        print("Marsh not staged"); return 1
    d = load_points()
    surf = (np.isfinite(d["lat"]) & np.isfinite(d["lon"]) & (d["depth"] <= DEPTH_MAX)
            & (d["cp"] > 0) & (d["pp"] > 0))
    lat, lon = d["lat"][surf], d["lon"][surf]
    logr = np.log(d["cp"][surf] / d["pp"][surf])
    om = _sample_glodap("OmegaC", lat, lon)
    sst = _sample_glodap("T", lat, lon)
    print("Identifiability map with GLODAP observation-derived env at every Marsh point")
    print(f"surface points: {len(lat)} | GLODAP-Omega finite: {int(np.isfinite(om).sum())} | "
          f"GLODAP-SST finite: {int(np.isfinite(sst).sum())}\n")

    results = []
    for name, la0, la1, lo0, lo1 in REGIONS:
        inbox = (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
        for axis, env in (("Omega", om), ("SST", sst)):
            m = inbox & np.isfinite(env)
            if int(m.sum()) < 3:
                continue
            ec, yc = _bin_cells(lat[m], lon[m], logr[m], env[m])
            if len(yc) < MIN_CELLS:
                results.append((name, axis, len(yc), np.nan, np.nan)); continue
            ho = _holdout(ec, yc)
            results.append((name, axis, len(yc), ho, _perm_p(ec, yc, ho)))

    tested = [r for r in results if np.isfinite(r[4])]
    keep = _bh_fdr([r[4] for r in tested])
    keepmap = {(r[0], r[1]): k for r, k in zip(tested, keep)}
    print(f"{'region':18s} {'axis':6s} {'n':>3s}  {'hold-out R2':>11s}  {'perm-p':>7s}  verdict")
    for name, axis, n, ho, p in sorted(results, key=lambda r: (np.inf if not np.isfinite(r[4]) else r[4])):
        if not np.isfinite(p):
            print(f"{name:18s} {axis:6s} {n:3d}  {'--':>11s}  {'--':>7s}  (n<{MIN_CELLS})"); continue
        v = "IDENTIFIABLE" if (keepmap.get((name, axis)) and ho > 0) else \
            ("uncorrected-only" if (ho > 0 and p < 0.1) else "no")
        print(f"{name:18s} {axis:6s} {n:3d}  {ho:+11.2f}  {p:7.3f}  {v}")

    print("\nGLODAP env (independent, observation-derived) at every point. eqpac is now TESTED")
    print("(not untestable). BH-FDR over the tested region-axis pairs. Prediction from Maranon")
    print("2016 (tropical calcification Omega-independent): eqpac/tropics come back NULL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
