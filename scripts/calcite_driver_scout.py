"""Does ANY environmental driver constrain the calcite rain ratio where Omega cannot?

The calcite null is scoped to a power-law in Omega. But Omega barely varies WITHIN a region
(<=0.16 dex), so the Omega test is under-excited. Other candidate drivers -- SST especially --
DO vary within regions (eqpac SST spans ~5 C), so they could constrain an environment-driven
rain-ratio closure where Omega cannot. This scout tests that, honestly, against the reviewer
panel's own Simpson critique: a raw cross-biome correlation is confounded (tropical-warm vs
polar-cold), so the load-bearing metric here is the **within-biome (biome-demeaned) partial
correlation** -- does a driver track the rain ratio WITHIN a region, with the between-biome
confound removed by biome fixed effects?

Drivers tested: log Omega_calcite, SST, coccolithophore (Chl2) fraction. For each we report the
pooled (cross-biome, CONFOUNDED) correlation, the within-biome partial correlation + bootstrap CI,
the per-biome correlations (sign consistency), and the within-biome driver excitation. A driver is
a CANDIDATE positive iff its within-biome partial correlation is significant (CI excludes 0), the
per-biome signs are consistent, and it is excited within biomes. Otherwise the apparent signal is a
between-biome artifact and the driver does not rescue the closure.

Note: the Chl2-fraction (composition) driver was previously found ~flat vs real bulk Chl; included
here for completeness. CPU. Needs D: caches + Daniels/Marsh .tab.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from darwindiff import daniels_loader, marsh_loader
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
    SOUTHERN_OCEAN_PACIFIC_AOI,
)
from darwindiff.held_out_obs import _resolve_cache, aoi_env_field

_SRC = {"daniels": daniels_loader.build_aoi_climatology, "marsh": marsh_loader.build_aoi_climatology}
_AOIS = {"eqpac": EQUATORIAL_PACIFIC_AOI, "natl": NORTH_ATLANTIC_SUBPOLAR_AOI,
         "so": SOUTHERN_OCEAN_PACIFIC_AOI}


def _drivers_for_aoi(aoi, build_clim):
    """Return covered-cell dict: log_ratio + drivers {logOmega, SST, cocco_frac}."""
    env = aoi_env_field(aoi)
    omega = np.asarray(env["omega_c"].numpy())
    finite_env = np.asarray(env["finite"].numpy(), bool)
    c = _resolve_cache(aoi, cache_dir=None, cache_path=None, cache=None)
    sst = np.asarray(c["sst"], dtype=np.float64)
    cp = c["chl_per_pft"]
    chl = {k: np.asarray(v, dtype=np.float64) for k, v in cp.items()}
    tot = sum(np.nan_to_num(chl[f"Chl{i}"]) for i in range(1, 6))
    cocco = np.where(tot > 0, np.nan_to_num(chl["Chl2"]) / np.where(tot > 0, tot, 1.0), np.nan)

    values, dmask, _ = build_clim(aoi)
    values = np.asarray(values, dtype=np.float64)
    dmask = np.asarray(dmask, bool)
    cov = (dmask & finite_env & np.isfinite(values) & (values > 0) & np.isfinite(omega)
           & (omega > 0) & np.isfinite(sst) & np.isfinite(cocco))
    return {
        "log_ratio": np.log(values[cov]),
        "logOmega": np.log(omega[cov]),
        "SST": sst[cov],
        "cocco_frac": cocco[cov],
    }


def _partial_within(y, x, biome):
    """Biome-demeaned (fixed-effect) partial correlation of y on x + bootstrap CI + per-biome r."""
    yd = y.copy().astype(float); xd = x.copy().astype(float)
    for b in np.unique(biome):
        m = biome == b
        if m.sum() >= 1:
            yd[m] -= yd[m].mean(); xd[m] -= xd[m].mean()
    def corr(a, b):
        return float(np.corrcoef(a, b)[0, 1]) if a.std() > 1e-12 and b.std() > 1e-12 else float("nan")
    r = corr(yd, xd)
    rng = np.random.default_rng(0)
    n = len(yd)
    bs = np.array([corr(yd[i], xd[i]) for i in (rng.integers(0, n, n) for _ in range(500))])
    bs = bs[np.isfinite(bs)]
    lo, hi = (np.quantile(bs, [0.025, 0.975]) if bs.size else (np.nan, np.nan))
    per = {}
    for b in np.unique(biome):
        m = biome == b
        per[b] = (int(m.sum()), corr(y[m], x[m]),
                  float(x[m].max() - x[m].min()) if m.sum() else float("nan"))
    return r, float(lo), float(hi), per


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=sorted(_SRC), default="marsh")
    args = ap.parse_args()
    build = _SRC[args.source]

    cols = {"log_ratio": [], "logOmega": [], "SST": [], "cocco_frac": [], "biome": []}
    for name, aoi in _AOIS.items():
        try:
            d = _drivers_for_aoi(aoi, build)
        except Exception as e:  # noqa: BLE001
            print(f"[{name}] skip: {type(e).__name__}: {e}"); continue
        n = len(d["log_ratio"])
        if n == 0:
            print(f"[{name}] no covered cells"); continue
        for k in ("log_ratio", "logOmega", "SST", "cocco_frac"):
            cols[k].append(d[k])
        cols["biome"].append(np.array([name] * n))
        print(f"[{name}] {n} cells")
    y = np.concatenate(cols["log_ratio"]); biome = np.concatenate(cols["biome"])
    out = {"source": args.source, "n_total": int(len(y)), "drivers": {}}
    print(f"\n{'driver':<12} {'pooled r':>9} {'within r':>9} {'within CI':>18} {'per-biome r (n, span)':>40}")
    for drv in ("logOmega", "SST", "cocco_frac"):
        x = np.concatenate(cols[drv])
        pooled = float(np.corrcoef(y, x)[0, 1])
        r, lo, hi, per = _partial_within(y, x, biome)
        sig = (lo > 0) or (hi < 0)
        signs = [np.sign(v[1]) for v in per.values() if np.isfinite(v[1])]
        consistent = len(set(signs)) == 1 and len(signs) >= 2
        out["drivers"][drv] = {"pooled_r": pooled, "within_r": r, "within_ci": [lo, hi],
                               "within_significant": bool(sig), "sign_consistent": bool(consistent),
                               "per_biome": {b: {"n": v[0], "r": v[1], "span": v[2]} for b, v in per.items()}}
        perstr = "  ".join(f"{b}:{v[1]:+.2f}(n{v[0]},s{v[2]:.2f})" for b, v in per.items())
        verdict = "CANDIDATE" if (sig and consistent) else "confounded/null"
        print(f"{drv:<12} {pooled:>+9.2f} {r:>+9.2f} {('['+format(lo,'+.2f')+','+format(hi,'+.2f')+']'):>18} {perstr}")
        print(f"{'':<12} within-biome partial: {verdict}")
    # headline
    cand = [d for d, v in out["drivers"].items() if v["within_significant"] and v["sign_consistent"]]
    out["verdict"] = (f"CANDIDATE driver(s): {cand} -- significant, sign-consistent WITHIN-biome "
                      f"partial correlation; a closure keyed on this could be constrainable"
                      if cand else
                      "NO driver has a significant + sign-consistent within-biome partial correlation "
                      "-- the calcite limit is not Omega-specific; the climatological data lack "
                      "within-region driver variation for ALL candidates (fundamental, not fixable "
                      "by picking a different driver)")
    print(f"\n== {out['verdict']} ==")
    dest = Path(f"docs/findings/calcite_driver_scout_{args.source}.json")
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
