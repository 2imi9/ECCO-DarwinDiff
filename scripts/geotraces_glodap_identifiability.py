"""Iron counterexample: is dissolved-iron CONCENTRATION env-predictable, and does that even
help identify the scavenging RATE? (the information-wall side of the identifiability map)

Calcite and iron fail identifiability for DIFFERENT reasons, and that contrast is the
Track-2 story:
  - Calcite: the observable (PIC:POC) ~= the parameter (R_PICPOC), but the OBSERVATIONS are
    too sparse/noisy -> a DATA-limited null (see marsh_glodap_identifiability.py).
  - Iron: the observable (DFe *concentration*) is a low-information projection of the
    parameter (the *scavenging rate*): concentration under-constrains the rate (Tagliabue
    2016). So even dense, env-predictable DFe need not identify scav_rat -> a STRUCTURAL /
    observability wall, independent of sample size.

This script measures the first half empirically: does environment (GLODAP OmegaC / SST,
co-located to every GEOTRACES IDP2025 surface Fe_D point) predict HELD-OUT log DFe, per
region, with the same env-regime hold-out + permutation null + BH-FDR as the calcite map?
Iron is dense (~4500 surface points, ~1300 1-deg cells), so unlike calcite this is NOT
data-limited.

Reading:
  - If DFe IS env-predictable (floor > 0): a scavenging closure fit to held-out DFe would
    appear to "work" -- but that is exactly the trap (an equifinal, meaningless scav_rat can
    reproduce the same concentration field). The apparent skill is the information wall in
    action, not identification of the rate.
  - If DFe is NOT env-predictable: iron fails at the observable level too.
Either way, concentration skill != rate identifiability -- the structural point stands.

Run:  python scripts/geotraces_glodap_identifiability.py
Needs D:\geotraces\GEOTRACES_IDP2025_Seawater.nc + data/glodap/.../OmegaC+temperature.nc.
"""
from __future__ import annotations

import os

import numpy as np

from darwindiff.geotraces_loader import open_geotraces_bottle
from darwindiff.glodap_loader import open_glodap_variable, surface_layer_glodap

DEPTH_MAX = 50.0
Q = 0.25
N_PERM = 2000
MIN_CELLS = 12
GLODAP_ROOT = "data/glodap/GLODAPv2.2016b_MappedClimatologies"
GEOTRACES = os.environ.get("GEOTRACES_NC", r"D:\geotraces\GEOTRACES_IDP2025_Seawater.nc")
QC_GOOD = (49, 50)

REGIONS = [
    ("eqpac",         -5,  15, -160, -110),
    ("natl (AOI)",    50,  65,  -40,  -10),
    ("N.Atl subpolar",45,  65,  -40,   10),
    ("S.Ocean Pac",  -65, -50, -180, -100),
    ("S.Ocean(all)", -70, -45, -180,  180),
    ("N.Pacific",     30,  60, -180, -120),
    ("tropics",      -23,  23, -180,  180),
    ("GLOBAL",       -90,  90, -180,  180),
]


def load_fe_points():
    ds = open_geotraces_bottle(GEOTRACES)
    g = "Fe_D_CONC"
    ns, nsamp = ds[g].shape
    lat = np.broadcast_to(ds.latitude.values[:, None], (ns, nsamp)).ravel()
    lon = np.broadcast_to(ds.longitude.values[:, None], (ns, nsamp)).ravel()
    dep = ds.DEPTH.values.ravel()
    val = ds[g].values.ravel()
    qc = ds[g + "_qc"].values.ravel() if (g + "_qc") in ds else np.full(val.shape, 49)
    keep = ((dep <= DEPTH_MAX) & np.isfinite(val) & (val > 0)
            & np.isfinite(lat) & np.isfinite(lon) & np.isin(qc, QC_GOOD))
    return lat[keep], lon[keep], np.log(val[keep])   # log DFe (log-normal)


def _sample_glodap(var, lats, lons):
    import xarray as xr
    da = surface_layer_glodap(open_glodap_variable(GLODAP_ROOT, var))[
        {"OmegaC": "OmegaC", "T": "temperature"}[var]]
    return da.sel(lat=xr.DataArray(lats, dims="pt"),
                  lon=xr.DataArray(lons, dims="pt"), method="nearest").values


def _bin(lat, lon, y, env):
    key = np.floor(lat).astype(np.int64) * 1000 + np.floor(lon).astype(np.int64)
    ye, ee = {}, {}
    for k, yy, ev in zip(key, y, env):
        ye.setdefault(k, []).append(yy)
        ee.setdefault(k, []).append(ev)
    return (np.array([np.mean(ee[k]) for k in ye]),
            np.array([np.mean(v) for v in ye.values()]))


def _holdout(env, y, q=Q):
    order = np.argsort(env)
    k = max(1, int(np.ceil(q * len(y))))
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
    lat, lon, logfe = load_fe_points()
    om = _sample_glodap("OmegaC", lat, lon)
    sst = _sample_glodap("T", lat, lon)
    print("Iron (GEOTRACES IDP2025 surface Fe_D) env-identifiability floor, GLODAP env")
    print(f"surface points: {len(lat)} | Omega finite: {int(np.isfinite(om).sum())} | "
          f"SST finite: {int(np.isfinite(sst).sum())}\n")

    results = []
    for name, la0, la1, lo0, lo1 in REGIONS:
        inbox = (lat >= la0) & (lat <= la1) & (lon >= lo0) & (lon <= lo1)
        for axis, env in (("Omega", om), ("SST", sst)):
            m = inbox & np.isfinite(env)
            if int(m.sum()) < 3:
                continue
            ec, yc = _bin(lat[m], lon[m], logfe[m], env[m])
            if len(yc) < MIN_CELLS:
                results.append((name, axis, len(yc), np.nan, np.nan)); continue
            ho = _holdout(ec, yc)
            results.append((name, axis, len(yc), ho, _perm_p(ec, yc, ho)))

    tested = [r for r in results if np.isfinite(r[4])]
    keep = _bh_fdr([r[4] for r in tested])
    keepmap = {(r[0], r[1]): k for r, k in zip(tested, keep)}
    print(f"{'region':16s} {'axis':6s} {'cells':>5s}  {'hold-out R2':>11s}  {'perm-p':>7s}  verdict")
    for name, axis, n, ho, p in sorted(results, key=lambda r: (np.inf if not np.isfinite(r[4]) else r[4])):
        if not np.isfinite(p):
            print(f"{name:16s} {axis:6s} {n:5d}  {'--':>11s}  {'--':>7s}  (n<{MIN_CELLS})"); continue
        v = "env-predictable" if (keepmap.get((name, axis)) and ho > 0) else \
            ("uncorrected-only" if (ho > 0 and p < 0.1) else "no")
        print(f"{name:16s} {axis:6s} {n:5d}  {ho:+11.2f}  {p:7.3f}  {v}")

    print("\nNOTE: 'env-predictable' here means DFe CONCENTRATION carries env-regime hold-out")
    print("skill. It does NOT mean the scavenging RATE (scav_rat) is identifiable: concentration")
    print("is a low-information projection of the rate (Tagliabue 2016), so a closure fit to")
    print("held-out DFe can 'work' with an equifinal, meaningless scav_rat. Concentration skill")
    print("!= rate identifiability -- the information wall. Iron is DENSE, so any null here is")
    print("NOT data-limited (unlike calcite); the wall is structural/observability.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
