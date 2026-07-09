"""Transport-free upper bound on E2 feasibility: is the rain ratio env-predictable
*in the real observations at all*?

The E2 gate asks whether a learned closure `g(env)`, rolled through prescribed transport,
predicts held-out PIC:POC. If it fails, we cannot tell whether transport/machinery lost the
signal or whether **the signal was never in the data**. This probe isolates the latter with
ZERO model and ZERO transport: it takes the Marsh 2025 compilation's **co-located
environment** (SST directly; Omega_calcite computed from co-located DIC/AT/T/S) and asks,
with a trivial OLS `log(CP/PP) ~ env`:

  1. How much rain-ratio variance is env-explainable at all (in-sample R^2)?  [the ceiling]
  2. Replicating the E2's **env-regime hold-out** (hold out the upper quartile of the env
     axis, fit OLS on the rest, predict the held-out band), does env prediction **beat the
     train basin mean** on the held-out cells (anomaly-R^2 > 0)?                [the E2 analog]

Interpretation:
  - anomaly-R^2 > 0 here  -> the env->rain-ratio signal IS extrapolable in the data; a
    transport-E2 failure is then a machinery/power problem (region, n, closure capacity).
  - anomaly-R^2 <= 0 here -> even a perfect model on the raw data cannot extrapolate the
    rain ratio to an unseen env band; the transport-E2 is then DOOMED BY THE DATA, and the
    honest result is the identifiability map, not a closure bug.

This is a NECESSARY-condition check (a linear fit is a floor; a real closure could do
better in-sample) run per env axis and per region. No GPU.

Run:  python scripts/probe_marsh_env_rainratio.py
"""
from __future__ import annotations

import csv

import numpy as np

from darwindiff.carbonate import calcite_saturation
from darwindiff.daniels_loader import _data_start_index, _to_float
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    NORTH_ATLANTIC_SUBPOLAR_AOI,
)
from darwindiff.marsh_loader import DEFAULT_MARSH_PATH

DEPTH_MAX = 50.0
UMOL_PER_KG_TO_MMOL_PER_M3 = 1.025  # RHO_SW(1025) * 1e-3, matching geotraces/glodap loaders


def _col(hdr, startswith, exclude=None):
    for i, h in enumerate(hdr):
        n = h.strip()
        if n.startswith(startswith) and (exclude is None or exclude not in n):
            return i
    return -1


def load_marsh_full(path=DEFAULT_MARSH_PATH):
    """Parse Marsh with env columns -> dict of float arrays (NaN where blank)."""
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        lines = f.readlines()
    r = csv.reader(lines[_data_start_index(lines):], delimiter="\t")
    hdr = next(r)
    idx = {
        "lat": _col(hdr, "Latitude"), "lon": _col(hdr, "Longitude"),
        "depth": _col(hdr, "Depth water"),
        "cp": _col(hdr, "CaCO3 prod C", "std"), "pp": _col(hdr, "PP C", "std"),
        "T": _col(hdr, "Temp"), "S": _col(hdr, "Sal"),
        "DIC": _col(hdr, "DIC"), "AT": _col(hdr, "AT"),
    }
    n = len(hdr)
    cols = {k: [] for k in idx}
    for row in r:
        if not row or len(row) < n:
            continue
        for k, i in idx.items():
            cols[k].append(_to_float(row[i]) if i >= 0 else np.nan)
    return {k: np.asarray(v, dtype=np.float64) for k, v in cols.items()}


def _omega(d, m):
    """Omega_calcite at the points in mask m, from co-located DIC/AT/T/S (unit-converted)."""
    import torch
    dic = torch.as_tensor(d["DIC"][m] * UMOL_PER_KG_TO_MMOL_PER_M3)
    alk = torch.as_tensor(d["AT"][m] * UMOL_PER_KG_TO_MMOL_PER_M3)
    T = torch.as_tensor(d["T"][m]); S = torch.as_tensor(d["S"][m])
    return np.asarray(calcite_saturation(dic, alk, T, S)["omega_c"].to(torch.float64))


def _r2(y, yhat):
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")


def _regime_holdout(env, y, q=0.25):
    """E2 analog: hold out the upper-q env band, OLS on the rest, anomaly-R2 vs train mean."""
    n = len(y)
    order = np.argsort(env)
    k = max(1, int(np.ceil(q * n)))
    val = order[-k:]; train = order[:-k]
    if len(train) < 2:
        return float("nan"), 0, 0
    b, a = np.polyfit(env[train], y[train], 1)      # y = b*env + a
    pred = b * env[val] + a
    train_mean = y[train].mean()                     # the "basin mean" null baseline
    ss_res = np.sum((pred - y[val]) ** 2)
    ss_tot = np.sum((y[val] - train_mean) ** 2)      # error of predicting train mean everywhere
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return r2, len(train), len(val)


def _analyze(name, env, logr, axis):
    if len(env) < 8:
        print(f"  [{name}] {axis}: n={len(env)} too few — skip")
        return
    r = np.corrcoef(env, logr)[0, 1]
    b, a = np.polyfit(env, logr, 1)
    insample = _r2(logr, b * env + a)
    ho_r2, n_tr, n_val = _regime_holdout(env, logr)
    verdict = "SIGNAL extrapolates (>0)" if ho_r2 > 0 else "NO extrapolation (<=0)"
    print(f"  [{name}] {axis}: n={len(env)}  corr={r:+.2f}  in-sample R2={insample:+.2f}  "
          f"slope={b:+.3f}/unit")
    print(f"        env-regime hold-out (upper-q): anomaly-R2={ho_r2:+.2f} "
          f"(train {n_tr}/val {n_val})  -> {verdict}")


def _region_mask(d, aoi):
    return ((d["lat"] >= aoi.lat_min) & (d["lat"] <= aoi.lat_max)
            & (d["lon"] >= aoi.lon_min) & (d["lon"] <= aoi.lon_max))


def _cell_level(aoi_key, aoi, split_channel):
    """The TRUE E2 feasibility ceiling: at the exact 1-deg cells held_out_calcite_obs uses
    (Marsh-binned geomean rain ratio + cached env), fit a trivial OLS env->log-ratio on the
    TRAIN cells, predict the held-out env-regime cells, and score anomaly-R2 vs the train
    basin mean. Transport-free. If this is <=0, even a perfect data model can't beat null at
    the E2's own cells -> the transport-E2 is data-limited, not a machinery bug."""
    import torch

    from darwindiff.held_out_obs import (
        anomaly_masked_r2,
        held_out_calcite_obs,
    )
    from darwindiff.marsh_loader import load_marsh_points
    try:
        obs = held_out_calcite_obs(aoi, n_z=1, split_channel=split_channel,
                                   points=load_marsh_points(), dtype=torch.float64)
    except Exception as e:  # degenerate split / missing cache
        print(f"  [{aoi_key}] cell-level {split_channel}: skip ({type(e).__name__}: {e})")
        return
    # env channel index in the standardized env tensor
    ch = obs.env_stats["channels"]
    if split_channel not in ch:
        print(f"  [{aoi_key}] cell-level: {split_channel} not an env channel"); return
    ci = ch.index(split_channel)
    tr = obs.train_mask[..., 0]; va = obs.val_mask[..., 0]
    env2d = obs.env[..., 0, ci]                       # standardized env at surface
    y2d = obs.target[..., 0]                          # log rain ratio at surface
    xe, ye = env2d[tr].numpy(), y2d[tr].numpy()
    if len(xe) < 3:
        print(f"  [{aoi_key}] cell-level {split_channel}: n_train={len(xe)} too few"); return
    b, a = np.polyfit(xe, ye, 1)
    pred = torch.as_tensor(b) * env2d + torch.as_tensor(a)
    r2_lin = float(anomaly_masked_r2(pred, y2d, va, obs.basin_mean))
    # null already = basin mean everywhere -> anomaly-R2 == 0 by construction
    verdict = "beats null (>0)" if r2_lin > 0 else "cannot beat null (<=0)"
    print(f"  [{aoi_key}] cell-level {split_channel}: train {int(tr.sum())}/val {int(va.sum())}  "
          f"linear hold-out anomaly-R2={r2_lin:+.2f}  -> {verdict}")


def main() -> int:
    if not DEFAULT_MARSH_PATH.is_file():
        print(f"Marsh file not staged: {DEFAULT_MARSH_PATH}")
        return 1
    d = load_marsh_full()
    surf = (np.isfinite(d["lat"]) & np.isfinite(d["lon"]) & np.isfinite(d["depth"])
            & (d["depth"] <= DEPTH_MAX) & (d["cp"] > 0) & (d["pp"] > 0))
    logr_all = np.full_like(d["cp"], np.nan)
    logr_all[surf] = np.log(d["cp"][surf] / d["pp"][surf])
    print("Marsh 2025 env->rain-ratio feasibility (transport-free, real obs)")
    print(f"surface positive-ratio samples: {int(surf.sum())}\n")

    regions = [("GLOBAL", None), ("eqpac", EQUATORIAL_PACIFIC_AOI),
               ("natl", NORTH_ATLANTIC_SUBPOLAR_AOI)]
    print("=== log(PIC:POC) vs SST (co-located Temp) ===")
    for name, aoi in regions:
        m = surf & np.isfinite(d["T"])
        if aoi is not None:
            m = m & _region_mask(d, aoi)
        _analyze(name, d["T"][m], logr_all[m], "SST")

    print("\n=== log(PIC:POC) vs Omega_calcite (co-located DIC/AT/T/S) ===")
    for name, aoi in regions:
        m = surf & np.isfinite(d["DIC"]) & np.isfinite(d["AT"]) & np.isfinite(d["T"]) & np.isfinite(d["S"])
        if aoi is not None:
            m = m & _region_mask(d, aoi)
        if int(m.sum()) < 8:
            print(f"  [{name}] Omega: n={int(m.sum())} too few — skip")
            continue
        om = _omega(d, m)
        good = np.isfinite(om)
        _analyze(name, om[good], logr_all[m][good], "Omega_c")

    print("\n=== CELL-LEVEL (the true E2 ceiling: 1-deg binned cells the E2 uses, no transport) ===")
    for name, aoi in [("eqpac", EQUATORIAL_PACIFIC_AOI), ("natl", NORTH_ATLANTIC_SUBPOLAR_AOI)]:
        for axis in ("omega_c", "sst"):
            _cell_level(name, aoi, axis)

    print("\nInterpretation: a POSITIVE env-regime hold-out anomaly-R2 means the rain-ratio")
    print("signal is extrapolable in the raw data (a transport-E2 miss is then machinery/power);")
    print("a NON-POSITIVE one means even a perfect data model can't extrapolate -> the E2 is")
    print("data-limited and the honest result is the identifiability map. (Linear = a floor.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
