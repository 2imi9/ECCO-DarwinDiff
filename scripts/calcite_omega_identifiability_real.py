"""Does the REAL Daniels rain ratio carry an identifiable Omega dependence?

The calcite E2 came back a NULL (learned closure did no better than a constant
through transport), and the open question is whether that is a *non-identifiability*
of an Omega-driven rain-ratio law from the sparse real data, or a genuine
wrong-closure result. This script answers the identifiability half **directly on
the real data**, with the bootstrap power-law oracle built this session
(`scripts/symbolic_distill_probe.distill_powerlaw`) — no closure training, no GPU.

Method: pair the real **Daniels et al. 2018 CP:PP rain ratio** (Darwin-independent
observation, `daniels_loader.build_aoi_climatology`) with the real **Omega_calcite**
derived from the v05 DIC/ALK/T/S cache (`held_out_obs.aoi_env_field` ->
`carbonate.calcite_saturation`) at the covered 1-deg cells, then test whether
`ratio = R0 * Omega**n` has an exponent `n` distinguishable from 0, stable, and
supported. Also report the plain `corr(log ratio, log Omega)` for comparison to
the earlier point-level correlation NULL (~0.01).

**Honesty:** this is an **identifiability-LIMITS** result (the sanctioned honest
framing), NOT a physical claim that calcification is Omega-independent. A
NON-IDENTIFIABLE verdict means *the sparse Daniels data cannot constrain an
Omega-power-law rain ratio*, which is consistent with (but does not establish)
Maranon-2016 Omega-independent tropical calcification. Small n and narrow visited
Omega are the limiting factors, and the oracle reports them explicitly.

Run (needs D: v05 caches + Daniels .tab): ``python scripts/calcite_omega_identifiability_real.py``.
Writes ``docs/findings/calcite_omega_identifiability_real.json``.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import torch

from darwindiff import daniels_loader, marsh_loader
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
    SOUTHERN_OCEAN_PACIFIC_AOI,
)
from darwindiff.held_out_obs import aoi_env_field

# Ratio source: Daniels 2018 (default) or the denser high-lat Marsh 2025 compilation.
# Both expose the same build_aoi_climatology(aoi) -> (values, mask, counts).
_SOURCES = {"daniels": daniels_loader.build_aoi_climatology,
            "marsh": marsh_loader.build_aoi_climatology}

# Load the oracle module by path (scripts/, not an installed package).
_GATE = Path(__file__).resolve().parent / "symbolic_distill_probe.py"
_spec = importlib.util.spec_from_file_location("symbolic_distill_probe", _GATE)
sd = importlib.util.module_from_spec(_spec)
sys.modules["symbolic_distill_probe"] = sd
_spec.loader.exec_module(sd)

AOIS = {
    "eqpac": EQUATORIAL_PACIFIC_AOI,
    "natl": NORTH_ATLANTIC_SUBPOLAR_AOI,
    "so": SOUTHERN_OCEAN_PACIFIC_AOI,
}


def _pairs(aoi, build_climatology) -> tuple[np.ndarray, np.ndarray]:
    """Return the covered (Omega, ratio) pairs for an AOI on the shared 1-deg grid."""
    values, dmask, _counts = build_climatology(aoi)          # [Y,X] rain ratio, finite mask
    values = np.asarray(values, dtype=np.float64)
    dmask = np.asarray(dmask, dtype=bool)
    env = aoi_env_field(aoi)
    omega = np.asarray(env["omega_c"].detach().to(torch.float64))
    finite = np.asarray(env["finite"].detach()).astype(bool)
    if omega.shape != values.shape:
        raise ValueError(f"grid mismatch for {aoi.name}: Daniels {values.shape} "
                         f"vs env {omega.shape}")
    cov = dmask & finite & np.isfinite(values) & np.isfinite(omega) & (values > 0) & (omega > 0)
    return omega[cov], values[cov]


def _analyze(omega: np.ndarray, ratio: np.ndarray, seed: int = 0) -> dict:
    v = sd.distill_powerlaw(omega, ratio, seed=seed)
    # plain correlation in log-log for comparison to the earlier corr~0.01 NULL
    if omega.size >= 3 and np.log(omega).std() > 0 and np.log(ratio).std() > 0:
        corr = float(np.corrcoef(np.log(omega), np.log(ratio))[0, 1])
    else:
        corr = float("nan")
    d = v.as_dict()
    d.update({
        "n_cells": int(omega.size),
        "omega_min": float(omega.min()) if omega.size else float("nan"),
        "omega_max": float(omega.max()) if omega.size else float("nan"),
        "ratio_geomean": float(np.exp(np.log(ratio).mean())) if ratio.size else float("nan"),
        "corr_logratio_logomega": corr,
    })
    return d


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", choices=sorted(_SOURCES), default="daniels",
                    help="rain-ratio source: daniels (tropical) or marsh (denser high-lat)")
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()
    build_climatology = _SOURCES[args.source]

    out: dict = {"source": args.source, "aois": {},
                 "note": "identifiability-limits; not a physical Omega-independence claim"}
    pooled_om, pooled_ra = [], []
    for key, aoi in AOIS.items():
        try:
            om, ra = _pairs(aoi, build_climatology)
        except Exception as e:  # noqa: BLE001 -- surface which AOI/data is missing
            out["aois"][key] = {"error": f"{type(e).__name__}: {e}"}
            print(f"[{key}] SKIP: {type(e).__name__}: {e}")
            continue
        d = _analyze(om, ra)
        out["aois"][key] = d
        pooled_om.append(om)
        pooled_ra.append(ra)
        tag = "IDENT" if d["identifiable"] else "NULL "
        print(f"[{key:<6}] [{tag}] n={d['n_cells']:>3} Omega[{d['omega_min']:.2f},{d['omega_max']:.2f}] "
              f"span={d['driver_log_span']:.2f}dex n_hat={d['n_hat']:+.2f} "
              f"CI[{d['n_ci_lo']:+.2f},{d['n_ci_hi']:+.2f}] corr={d['corr_logratio_logomega']:+.3f}")
        print(f"          {d['reason']}")

    if pooled_om:
        om = np.concatenate(pooled_om)
        ra = np.concatenate(pooled_ra)
        d = _analyze(om, ra)
        out["pooled"] = d
        tag = "IDENT" if d["identifiable"] else "NULL "
        print(f"[pooled] [{tag}] n={d['n_cells']:>3} Omega[{d['omega_min']:.2f},{d['omega_max']:.2f}] "
              f"span={d['driver_log_span']:.2f}dex n_hat={d['n_hat']:+.2f} "
              f"CI[{d['n_ci_lo']:+.2f},{d['n_ci_hi']:+.2f}] corr={d['corr_logratio_logomega']:+.3f}")
        print(f"          {d['reason']}")

    any_ident = any(v.get("identifiable") for v in out["aois"].values()) or \
        out.get("pooled", {}).get("identifiable", False)
    out["verdict"] = ("identifiable Omega dependence found"
                      if any_ident else
                      "NULL: real Daniels data does not constrain an Omega-power-law rain "
                      "ratio (identifiability-limits; small n / narrow Omega support)")
    print(f"\n== {out['verdict']} ==")

    default_name = ("docs/findings/calcite_omega_identifiability_real.json" if args.source == "daniels"
                    else f"docs/findings/calcite_omega_identifiability_real_{args.source}.json")
    dest = Path(args.out or default_name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
