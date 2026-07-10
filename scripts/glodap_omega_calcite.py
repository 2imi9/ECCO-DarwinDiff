"""Independent-Omega calcite identifiability check with GLODAPv3 in-situ carbonate data.

The map's calcite oracle (calcite_omega_identifiability_real.py) computed Omega from the v05
DIC/ALK model CACHE, so its "null" leaned partly on model-derived Omega. This script removes that
dependence: it recomputes Omega from **independent, in-situ GLODAPv3 bottle** DIC/TAlk/T/S
(NCEI accession 0315582, 2026; 1181 cruises) co-located to the calcite observing cells, and re-runs
the bootstrap power-law oracle. If the exponent's CI still straddles zero on real in-situ Omega,
the calcite null no longer depends on the model cache.

Pipeline: read the GLODAPv3 regional CSV -> surface (<=50 m), good-flag, in-AOI-box, finite ->
convert tco2/talk (umol/kg) to mmol/m^3 (x1.025) -> Omega via carbonate.calcite_saturation ->
bin to the shared 1-deg AOI grid (mean per cell) -> pair with the Daniels/Marsh rain ratio at the
same cells -> distill_powerlaw. Honest: independent Omega, but still small-n (bottle coverage on
the calcite cells is finite); a scale offset between in-situ and cache Omega does not change the
oracle (it tests the log-log SLOPE, invariant to an overall Omega scale).

Data provenance: GLODAPv3 DIC/TAlk are INTERNALLY-CONSISTENCY-ADJUSTED values, not raw bottle
measurements -- the per-cruise adjustments are computed by the furthest-first (FF) crossover
inversion of Humphreys et al. 2026 (EGUsphere 2026-3063; magnitudes <~12 umol/kg, 2 umol/kg
minimum cut-off, expert-committee reviewed). These are SYSTEMATIC per-cruise offset corrections
that IMPROVE internal consistency; they do not manufacture spatial Omega variance across the
calcite cells, so the narrow-Omega-support null here is robust to (and benefits from) them.
Conceptual resonance worth citing: the FF inversion is itself validated on SIMULATED (self-twin)
data and the authors note "no algorithm can completely replace expert judgement" -- the same
honest bounding of an inverse method by what the data + judgement allow.

CPU. Needs D:\glodap\GLODAPv3_{Pacific,Atlantic}_Ocean.csv + D: v05 caches + Daniels/Marsh .tab.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from darwindiff import daniels_loader, marsh_loader
from darwindiff.carbonate import calcite_saturation
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
)
from darwindiff.held_out_obs import aoi_env_field

_GATE = Path(__file__).resolve().parent / "symbolic_distill_probe.py"
_spec = importlib.util.spec_from_file_location("symbolic_distill_probe", _GATE)
sd = importlib.util.module_from_spec(_spec)
sys.modules["symbolic_distill_probe"] = sd
_spec.loader.exec_module(sd)

RHO = 1.025  # umol/kg -> mmol/m^3 at rho_sw=1025 (matches carbonate.py convention)
GLODAP_DIR = Path(r"D:\glodap")
_SRC = {"daniels": daniels_loader.build_aoi_climatology, "marsh": marsh_loader.build_aoi_climatology}
_AOIS = {"eqpac": (EQUATORIAL_PACIFIC_AOI, "GLODAPv3_Pacific_Ocean.csv"),
         "natl": (NORTH_ATLANTIC_SUBPOLAR_AOI, "GLODAPv3_Atlantic_Ocean.csv")}
_COLS = ["latitude", "longitude", "depth", "temperature", "salinity",
         "tco2", "talk", "tco2f", "talkf"]


def _glodap_omega_grid(aoi, csv_name, lats, lons, depth_max=50.0):
    """Bin in-situ GLODAPv3 surface Omega_calcite onto the AOI's 1-deg grid centers."""
    df = pd.read_csv(GLODAP_DIR / csv_name, usecols=lambda c: c in _COLS,
                     na_values=[-9999, -1e10], low_memory=False)
    lat0, lat1, lon0, lon1 = aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max
    lon = df.longitude.to_numpy()
    if np.nanmax(lon) > 180:  # GLODAP 0..360 -> -180..180 to match the AOI convention
        df = df.assign(longitude=((lon + 180) % 360) - 180)
    m = (df.depth <= depth_max) & df.tco2.notna() & df.talk.notna() \
        & df.temperature.notna() & df.salinity.notna() \
        & (df.tco2 > 0) & (df.talk > 0) \
        & df.latitude.between(lat0, lat1) & df.longitude.between(lon0, lon1)
    # GLODAP flag 2 == good (accept 0/2 if a flag col exists; else keep all finite)
    for f in ("tco2f", "talkf"):
        if f in df:
            m &= df[f].isin([0, 2]) | df[f].isna()
    d = df[m]
    if len(d) == 0:
        return np.full((len(lats), len(lons)), np.nan), 0
    omega = calcite_saturation(
        torch.as_tensor(d.tco2.to_numpy() * RHO), torch.as_tensor(d.talk.to_numpy() * RHO),
        torch.as_tensor(d.temperature.to_numpy()), torch.as_tensor(d.salinity.to_numpy()),
    )["omega_c"].detach().numpy()
    # nearest grid center bin
    lat_i = np.abs(d.latitude.to_numpy()[:, None] - lats[None, :]).argmin(1)
    lon_i = np.abs(d.longitude.to_numpy()[:, None] - lons[None, :]).argmin(1)
    grid = np.full((len(lats), len(lons)), np.nan)
    cnt = np.zeros_like(grid)
    accum = np.zeros_like(grid)
    for yi, xi, om in zip(lat_i, lon_i, omega):
        if np.isfinite(om):
            accum[yi, xi] += om
            cnt[yi, xi] += 1
    good = cnt > 0
    grid[good] = accum[good] / cnt[good]
    return grid, int(len(d))


def _pairs(aoi, csv_name, source):
    env = aoi_env_field(aoi)
    lats = np.asarray(env["lats"].numpy()); lons = np.asarray(env["lons"].numpy())
    values, dmask, _ = _SRC[source](aoi)
    values = np.asarray(values, dtype=np.float64); dmask = np.asarray(dmask, dtype=bool)
    omega_grid, n_bottles = _glodap_omega_grid(aoi, csv_name, lats, lons)
    cov = dmask & np.isfinite(values) & (values > 0) & np.isfinite(omega_grid) & (omega_grid > 0)
    return omega_grid[cov], values[cov], n_bottles, int(cov.sum())


def _analyze(omega, ratio, seed=0):
    v = sd.distill_powerlaw(omega, ratio, seed=seed)
    corr = (float(np.corrcoef(np.log(omega), np.log(ratio))[0, 1])
            if omega.size >= 3 and np.log(omega).std() > 0 and np.log(ratio).std() > 0 else float("nan"))
    d = v.as_dict()
    d.update({"n_cells": int(omega.size),
              "omega_min": float(omega.min()) if omega.size else float("nan"),
              "omega_max": float(omega.max()) if omega.size else float("nan"),
              "corr_logratio_logomega": corr})
    return d


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=sorted(_SRC), default="marsh")
    args = ap.parse_args()
    out = {"source": args.source, "omega": "GLODAPv3 in-situ bottle (NCEI 0315582)", "aois": {}}
    pom, pra = [], []
    for key, (aoi, csv) in _AOIS.items():
        if not (GLODAP_DIR / csv).is_file():
            out["aois"][key] = {"error": f"missing {csv}"}
            print(f"[{key}] SKIP: missing {csv}"); continue
        om, ra, nb, ncov = _pairs(aoi, csv, args.source)
        d = _analyze(om, ra); d["n_bottles"] = nb
        out["aois"][key] = d
        pom.append(om); pra.append(ra)
        tag = "IDENT" if d["identifiable"] else "NULL "
        print(f"[{key:<6}] [{tag}] cells={d['n_cells']:>3} (bottles={nb}) "
              f"Omega[{d['omega_min']:.2f},{d['omega_max']:.2f}] span={d['driver_log_span']:.2f}dex "
              f"n_hat={d['n_hat']:+.2f} CI[{d['n_ci_lo']:+.2f},{d['n_ci_hi']:+.2f}] corr={d['corr_logratio_logomega']:+.3f}")
        print(f"          {d['reason']}")
    if pom:
        om = np.concatenate(pom); ra = np.concatenate(pra)
        d = _analyze(om, ra); out["pooled"] = d
        tag = "IDENT" if d["identifiable"] else "NULL "
        print(f"[pooled] [{tag}] cells={d['n_cells']:>3} Omega[{d['omega_min']:.2f},{d['omega_max']:.2f}] "
              f"span={d['driver_log_span']:.2f}dex n_hat={d['n_hat']:+.2f} "
              f"CI[{d['n_ci_lo']:+.2f},{d['n_ci_hi']:+.2f}] corr={d['corr_logratio_logomega']:+.3f}")
        print(f"          {d['reason']}")
    any_id = any(v.get("identifiable") for v in out["aois"].values()) or out.get("pooled", {}).get("identifiable", False)
    out["verdict"] = ("independent in-situ Omega gives an IDENTIFIABLE exponent" if any_id else
                      "NULL on independent in-situ GLODAPv3 Omega too -- the calcite null does NOT "
                      "depend on the model cache")
    print(f"\n== {out['verdict']} ==")
    dest = Path(f"docs/findings/calcite_omega_glodap_{args.source}.json")
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
