#!/usr/bin/env python
"""Baseline-comparison matrix for the depth-resolved Track-2 emulator.

WHY THIS EXISTS (the reviewer critique)
---------------------------------------
The prior write-up defended the emulator's failure-to-beat-persistence with a
"structural ceiling" story: *DIC/ALK/FeT/Chl are near-conserved / slow, so
persistence is unbeatable*. That story is scientifically wrong for the fast
tracers -- Chl (blooms, grazing, photo-acclimation) and FeT (uptake,
remineralization, scavenging, episodic dust) move fast on a monthly step. A
*correct* one-month operator must beat persistence **whenever the state actually
moves**. If it does not, the honest explanations are:

  (i)   the monthly tendency sits **below the emulator / discretization floor**
        (there is genuinely little to predict above persistence),
  (ii)  the **level-space RMSE rewards autocorrelation** -- persistence is a very
        strong denominator, so a scale-free level skill looks like a ceiling even
        when the model captures real deseasonalized structure, or
  (iii) **inputs are missing** (e.g. atmospheric-dust iron, PAR) so the operator
        cannot see the forcing that drives the tendency.

The `emulator_poc.py` headline reports exactly one number -- level skill vs
persistence -- which cannot separate these. This script builds the matrix that
can: for every tracer x depth level it scores the emulator against FOUR baselines
and re-frames the prediction target THREE ways. The decisive test:

    if the emulator beats persistence on the ANOMALY (deseasonalized) or TENDENCY
    target even where it loses on the LEVEL, the "structural ceiling" claim is
    refuted -- the loss was the metric, not the physics.

WHAT IT COMPUTES  (all leak-free: climatologies & the damping alpha are fit on
TRAIN months only; the emulator's `pred` is its held-out validation output)
--------------------------------------------------------------------------------
Predictors of x_{t+1} (per channel, in the emulator's own working space -- log
space for Chl, linear otherwise -- so numbers are comparable to the PoC):

    1. persistence           P   = x_t
    2. damped persistence     D   = clim_ann + alpha*(x_t - clim_ann)   (alpha fit per channel)
    3. seasonal climatology   S   = clim_month(t+1)   (proper monthly climatology)
    4. emulator               E   = pred              (context / the model under test)
    (+) anomaly persistence   AP  = clim_month(t+1) + (x_t - clim_month(t))  (deseasonalized persistence)

Skill (task convention):   SKILL = 1 - RMSE_model / RMSE_baseline   (>0 beats the baseline)
Also reported: the MSE-ratio skill (1 - MSE_model/MSE_persist) that `emulator_poc.py`
uses as its headline, for a direct cross-check against `depth_chl_emulator.json`.

Three prediction targets:
    (a) LEVEL     x_{t+1}                 -> skill vs {persistence, damped, seasonal clim}
    (b) TENDENCY  x_{t+1} - x_t           -> R^2 & correlation of predicted vs true change
                                            (note: emulator skill-vs-persistence on the
                                             tendency is *algebraically identical* to the
                                             level, because x_t cancels -- so the tendency
                                             framing refutes the ceiling only via variance
                                             explained, which this reports)
    (c) ANOMALY   x_{t+1} - clim_month    -> skill vs {seasonal clim, anomaly persistence}

Breakdowns: per depth level, per tracer (level-mean), by season (month-of-year of
the target), and by region (equatorial |lat|<=5 vs northern 5<lat<=15) when the
cube's lat axis supports it.

INPUTS  (reuses already-dumped fields -- no training)
-----------------------------------------------------
    --fields    depth_chl_fields.npz   : pred/true/persistence [Nval,C,H,W] + valid_mask,
                                         lats, lons, chan_names, val_iters   (physical units)
    --cube      darwin_v05_L5_chl.npz  : full state [M,C,H,W] + iters/times_days/chan_names
    --emu-json  depth_chl_emulator.json: config (val_frac, adjacency_tol, log_tracers, residual)

Cluster run (AICR):
    ~/dd_venv/bin/python scripts/analysis/emulator_baselines.py \
        --fields  /scratch/qi_zim_neu/depth/depth_chl_fields.npz \
        --cube    /scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz \
        --emu-json /scratch/qi_zim_neu/depth/depth_chl_emulator.json \
        --out     /scratch/qi_zim_neu/depth/emulator_baseline_matrix.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

LOG_EPS = 1e-12  # matches emulator_poc.LOG_EPS / e2s prognostic clamp


# ---------------------------------------------------------------------------
def _to_work(x, is_log):
    """Physical -> working space (log for Chl channels, identity otherwise)."""
    if is_log:
        return np.log(np.clip(x, a_min=LOG_EPS, a_max=None))
    return x


def _rmse(pred, true):
    """Root-mean-square error over all supplied elements (already masked/flat)."""
    d = pred - true
    return float(np.sqrt(np.mean(d * d)))


def _mse(pred, true):
    d = pred - true
    return float(np.mean(d * d))


def _skill(rmse_model, rmse_base):
    """Task convention: 1 - RMSE_model / RMSE_baseline (>0 beats the baseline)."""
    return 1.0 - rmse_model / (rmse_base + 1e-30)


def _corr(a, b):
    a = a.ravel()
    b = b.ravel()
    a = a - a.mean()
    b = b - b.mean()
    na = np.sqrt((a * a).sum())
    nb = np.sqrt((b * b).sum())
    if na < 1e-30 or nb < 1e-30:
        return float("nan")
    return float((a * b).sum() / (na * nb))


def _season_bin(times_days):
    """Month-of-year bin 0..11 from days-since-ref (absolute phase uncalibrated,
    but grouping is internally consistent: same true calendar month -> same bin)."""
    m = (np.asarray(times_days, dtype=float) % 365.25) / (365.25 / 12.0)
    return np.floor(m).astype(int) % 12


# ---------------------------------------------------------------------------
def build_splits(times_days, val_frac, adjacency_tol):
    """Replicate emulator_poc.build_splits (val_frac / adjacency) to recover the
    exact train months and the train adjacent pairs used for the fits."""
    times = np.asarray(times_days, dtype=float)
    M = len(times)
    gaps = np.diff(times)
    med_gap = float(np.median(gaps)) if len(gaps) else 0.0
    adjacent = gaps <= adjacency_tol * med_gap  # adjacent[m] links m -> m+1
    split_idx = int(round(M * (1.0 - val_frac)))
    split_idx = max(2, min(split_idx, M - 1))
    train_months = np.arange(0, split_idx)
    train_pairs = np.array([m for m in range(M - 1) if adjacent[m] and (m + 1) < split_idx])
    val_pairs = np.array([m for m in range(M - 1) if adjacent[m] and m >= split_idx])
    return {
        "adjacent": adjacent,
        "split_idx": split_idx,
        "train_months": train_months,
        "train_pairs": train_pairs,
        "val_pairs": val_pairs,
        "median_step_days": med_gap,
    }


def climatologies(state_ws, train_months, season_bins):
    """Train-only climatologies in working space.

    Returns (clim_ann [C,H,W], clim_seas dict{bin: [C,H,W]}). NaN land stays NaN;
    a season bin with no train month falls back to the annual mean.
    """
    tm = np.asarray(train_months)
    clim_ann = np.nanmean(state_ws[tm], axis=0)  # [C,H,W]
    clim_seas = {}
    for b in range(12):
        members = tm[season_bins[tm] == b]
        if members.size:
            clim_seas[b] = np.nanmean(state_ws[members], axis=0)
        else:
            clim_seas[b] = clim_ann
    return clim_ann, clim_seas


def fit_alpha(state_ws, train_pairs, clim_ann, valid_mask):
    """Per-channel damping alpha (1-D least squares, train pairs only, on valid
    cells): alpha_c = <(x_s-clim)(x_t-clim)> / <(x_s-clim)^2>. alpha~1 => persistence-
    like (strong autocorrelation); alpha~0 => climatology-like."""
    C = state_ws.shape[1]
    alpha = np.ones(C, dtype=float)
    if train_pairs.size == 0:
        return alpha
    for c in range(C):
        num = 0.0
        den = 0.0
        for m in train_pairs:
            xs = state_ws[m, c][valid_mask]
            xt = state_ws[m + 1, c][valid_mask]
            cl = clim_ann[c][valid_mask]
            good = np.isfinite(xs) & np.isfinite(xt) & np.isfinite(cl)
            ds = xs[good] - cl[good]
            dt = xt[good] - cl[good]
            num += float((ds * dt).sum())
            den += float((ds * ds).sum())
        alpha[c] = num / den if den > 1e-30 else 1.0
    return alpha


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fields", default="/scratch/qi_zim_neu/depth/depth_chl_fields.npz")
    ap.add_argument("--cube", default="/scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz")
    ap.add_argument("--emu-json", default="/scratch/qi_zim_neu/depth/depth_chl_emulator.json")
    ap.add_argument("--out", default="/scratch/qi_zim_neu/depth/emulator_baseline_matrix.json")
    ap.add_argument("--log-tracers", default=None,
                    help="Override comma-separated log-space tracer stems (default: from emu-json).")
    args = ap.parse_args(argv)

    fields = np.load(args.fields, allow_pickle=True)
    cube = np.load(args.cube, allow_pickle=True)
    cfg = json.load(open(args.emu_json))["config"] if Path(args.emu_json).is_file() else {}
    val_frac = float(cfg.get("val_frac", 0.3))
    adjacency_tol = float(cfg.get("adjacency_tol", 1.6))
    residual = bool(cfg.get("residual", False))
    log_tracers = (args.log_tracers.split(",") if args.log_tracers
                   else cfg.get("log_tracers", ["Chl1", "Chl2", "Chl3", "Chl4", "Chl5"]))
    log_tracers = {s.strip() for s in log_tracers if str(s).strip()}

    chan = [str(x) for x in cube["chan_names"]]
    C = len(chan)
    is_log = np.array([c.split("_k")[0] in log_tracers for c in chan], dtype=bool)
    state = np.asarray(cube["state"], dtype=np.float64)          # [M,C,H,W] physical
    times_days = np.asarray(cube["times_days"], dtype=float)
    cube_iters = [int(x) for x in cube["iters"]]
    M = state.shape[0]

    pred_phys = np.asarray(fields["pred"], dtype=np.float64)     # [Nval,C,H,W] physical
    true_phys = np.asarray(fields["true"], dtype=np.float64)
    pers_phys = np.asarray(fields["persistence"], dtype=np.float64)
    valid_mask = np.asarray(fields["valid_mask"], dtype=bool)    # [H,W]
    lats = np.asarray(fields["lats"], dtype=float)               # [H]
    val_iters = [int(x) for x in fields["val_iters"]]

    # Locate the val pairs in the cube: target index = index_of(val_iter); source = target-1.
    tgt_idx = np.array([cube_iters.index(v) for v in val_iters])
    src_idx = tgt_idx - 1
    assert np.all(src_idx >= 0)
    # Sanity: the dumped persistence / true must equal the cube source / target snapshots.
    assert np.nanmax(np.abs(state[src_idx] - pers_phys)) < 1e-3, "persistence != cube.state[source]"
    assert np.nanmax(np.abs(state[tgt_idx] - true_phys)) < 1e-3, "true != cube.state[target]"

    season_bins = _season_bin(times_days)
    splits = build_splits(times_days, val_frac, adjacency_tol)

    # Working space for everything (log for Chl).
    state_ws = state.copy()
    for c in np.where(is_log)[0]:
        state_ws[:, c] = _to_work(state[:, c], True)
    pred_ws = pred_phys.copy()
    for c in np.where(is_log)[0]:
        pred_ws[:, c] = _to_work(pred_phys[:, c], True)

    clim_ann, clim_seas = climatologies(state_ws, splits["train_months"], season_bins)
    alpha = fit_alpha(state_ws, splits["train_pairs"], clim_ann, valid_mask)

    val_tgt_bins = season_bins[tgt_idx]
    val_src_bins = season_bins[src_idx]

    # Build the five predictors of x_{t+1} for the Nval pairs, per channel, in work space.
    Nval = pred_ws.shape[0]
    H, W = valid_mask.shape

    def pred_stacks(cidx):
        """Return dict of predictor stacks + truth for channel cidx, shape [Nval,H,W]."""
        E = pred_ws[:, cidx]                          # emulator
        T = state_ws[tgt_idx, cidx]                   # truth
        P = state_ws[src_idx, cidx]                   # persistence
        cl_ann = clim_ann[cidx]
        D = cl_ann[None] + alpha[cidx] * (P - cl_ann[None])           # damped
        S = np.stack([clim_seas[val_tgt_bins[i]][cidx] for i in range(Nval)])  # seasonal clim
        AP = (np.stack([clim_seas[val_tgt_bins[i]][cidx] for i in range(Nval)])
              + (P - np.stack([clim_seas[val_src_bins[i]][cidx] for i in range(Nval)])))  # anomaly persist
        return {"E": E, "T": T, "P": P, "D": D, "S": S, "AP": AP, "clim_ann": cl_ann}

    def masked(arr, cellmask):
        """Flatten [Nval,H,W] over the given [H,W] cell mask, keeping finite cells."""
        v = arr[:, cellmask]
        return v[np.isfinite(v)]

    # Region masks (equatorial cold-tongue vs northern warm-pool) from the lat axis.
    regions = {"all": valid_mask}
    if lats.size == H and (lats.min() < 0 <= lats.max()):
        eq = (np.abs(lats) <= 5.0)[:, None] & valid_mask
        no = (lats > 5.0)[:, None] & valid_mask
        if eq.sum() > 100 and no.sum() > 100:
            regions = {"all": valid_mask, "equatorial|lat|<=5": eq, "northern 5<lat<=15": no}

    channels = {}
    for c, name in enumerate(chan):
        st = pred_stacks(c)
        cm = valid_mask
        E = masked(st["E"], cm)
        T = masked(st["T"], cm)
        P = masked(st["P"], cm)
        D = masked(st["D"], cm)
        S = masked(st["S"], cm)
        AP = masked(st["AP"], cm)
        # tendency (target b): predicted vs true change, x_t cancels.
        true_tend = (st["T"] - st["P"])[:, cm].ravel()
        pred_tend = (st["E"] - st["P"])[:, cm].ravel()
        keep = np.isfinite(true_tend) & np.isfinite(pred_tend)
        true_tend, pred_tend = true_tend[keep], pred_tend[keep]
        ss_res = float(((pred_tend - true_tend) ** 2).sum())
        ss_tot = float(((true_tend - true_tend.mean()) ** 2).sum())
        r2_tend = 1.0 - ss_res / (ss_tot + 1e-30)
        # anomaly amplitude vs annual clim (deseasonalized field variability).
        anom = masked(st["T"] - st["clim_ann"][None], cm)
        rmse_E = _rmse(E, T)
        rec = {
            "log_space": bool(is_log[c]),
            "alpha_damped": float(alpha[c]),
            "rmse_emulator": rmse_E,
            "rmse_persistence": _rmse(P, T),
            "rmse_damped": _rmse(D, T),
            "rmse_seasonal_clim": _rmse(S, T),
            "rmse_anomaly_persist": _rmse(AP, T),
            "rmse_annual_clim": _rmse(masked(np.broadcast_to(st["clim_ann"][None], st["T"].shape), cm), T),
            # LEVEL target skills (task convention 1 - RMSE ratio)
            "skill_vs_persistence": _skill(rmse_E, _rmse(P, T)),
            "skill_vs_damped": _skill(rmse_E, _rmse(D, T)),
            "skill_vs_seasonal_clim": _skill(rmse_E, _rmse(S, T)),
            # ANOMALY target skills
            "skill_vs_anomaly_persist": _skill(rmse_E, _rmse(AP, T)),
            # cross-check vs emulator_poc.json (MSE-ratio convention)
            "skill_vs_persistence_mse": 1.0 - _mse(E, T) / (_mse(P, T) + 1e-30),
            "anomaly_r2_annual_clim_mse": 1.0 - _mse(E, T) / (_mse(
                masked(np.broadcast_to(st["clim_ann"][None], st["T"].shape), cm), T) + 1e-30),
            # TENDENCY target
            "r2_tendency": float(r2_tend),
            "corr_tendency": _corr(pred_tend, true_tend),
            # tendency-below-noise diagnostics
            "rms_monthly_tendency": _rmse(P, T),          # == ||x_{t+1}-x_t||
            "rms_field_anomaly": _rmse(anom, np.zeros_like(anom)),  # ||x - clim_ann||
            "tendency_to_anomaly_ratio": (_rmse(P, T) / (_rmse(anom, np.zeros_like(anom)) + 1e-30)),
            "persist_over_seasclim_rmse": _rmse(P, T) / (_rmse(S, T) + 1e-30),
        }
        # region breakdown (level skill vs persistence & seasonal clim)
        if len(regions) > 1:
            rr = {}
            for rname, rmask in regions.items():
                if rname == "all":
                    continue
                Er = masked(st["E"], rmask); Tr = masked(st["T"], rmask)
                Pr = masked(st["P"], rmask); Sr = masked(st["S"], rmask)
                rr[rname] = {
                    "skill_vs_persistence": _skill(_rmse(Er, Tr), _rmse(Pr, Tr)),
                    "skill_vs_seasonal_clim": _skill(_rmse(Er, Tr), _rmse(Sr, Tr)),
                    "n_cells": int(rmask.sum()),
                }
            rec["by_region"] = rr
        channels[name] = rec

    # ---- aggregate per tracer (mean over the 5 depth levels) ----
    tracers = list(dict.fromkeys(c.split("_k")[0] for c in chan))
    by_tracer = {}
    for t in tracers:
        idx = [i for i, c in enumerate(chan) if c.split("_k")[0] == t]
        def m(key):
            return float(np.mean([channels[chan[i]][key] for i in idx]))
        by_tracer[t] = {
            "skill_vs_persistence": m("skill_vs_persistence"),
            "skill_vs_damped": m("skill_vs_damped"),
            "skill_vs_seasonal_clim": m("skill_vs_seasonal_clim"),
            "skill_vs_anomaly_persist": m("skill_vs_anomaly_persist"),
            "anomaly_r2_annual_clim_mse": m("anomaly_r2_annual_clim_mse"),
            "skill_vs_persistence_mse": m("skill_vs_persistence_mse"),
            "r2_tendency": m("r2_tendency"),
            "corr_tendency": m("corr_tendency"),
            "tendency_to_anomaly_ratio": m("tendency_to_anomaly_ratio"),
            "persist_over_seasclim_rmse": m("persist_over_seasclim_rmse"),
            "alpha_damped": m("alpha_damped"),
            "log_space": bool(is_log[idx[0]]),
        }

    # ---- season breakdown (val targets grouped by month-of-year bin) ----
    season = {}
    for b in sorted(set(int(x) for x in val_tgt_bins)):
        sel = np.where(val_tgt_bins == b)[0]
        # overall emulator vs persistence skill on this season's pairs, pooled over channels in work space
        num_m = num_p = 0.0
        cnt = 0
        for c in range(C):
            st = pred_stacks(c)
            E = st["E"][sel][:, valid_mask]; T = st["T"][sel][:, valid_mask]; P = st["P"][sel][:, valid_mask]
            g = np.isfinite(E) & np.isfinite(T) & np.isfinite(P)
            num_m += float(((E[g] - T[g]) ** 2).sum())
            num_p += float(((P[g] - T[g]) ** 2).sum())
            cnt += int(g.sum())
        season[f"bin{b}"] = {
            "n_val_pairs": int(sel.size),
            "pooled_skill_vs_persistence_mse": 1.0 - num_m / (num_p + 1e-30),
        }

    out = {
        "meta": {
            "fields": str(args.fields), "cube": str(args.cube),
            "aoi": str(fields["aoi"]) if "aoi" in fields.files else cfg.get("aoi"),
            "residual": residual, "val_frac": val_frac, "adjacency_tol": adjacency_tol,
            "log_tracers": sorted(log_tracers),
            "n_channels": C, "n_val_pairs": int(Nval),
            "n_train_months": int(splits["train_months"].size),
            "n_train_pairs": int(splits["train_pairs"].size),
            "n_valid_cells": int(valid_mask.sum()),
            "val_target_iters": val_iters,
            "val_target_season_bins": [int(x) for x in val_tgt_bins],
            "skill_convention": "1 - RMSE_model/RMSE_baseline (task); *_mse keys use 1 - MSE ratio (emulator_poc).",
            "regions": {k: int(v.sum()) for k, v in regions.items()},
        },
        "channels": channels,
        "by_tracer": by_tracer,
        "by_season": season,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))

    # ------------------------------------------------------------------ report
    def f(x):
        return f"{x:+.3f}" if np.isfinite(x) else "  nan"

    print("=" * 100)
    print(f"EMULATOR BASELINE MATRIX  aoi={out['meta']['aoi']} residual={residual} "
          f"Nval_pairs={Nval} train_months={splits['train_months'].size} "
          f"train_pairs={splits['train_pairs'].size} cells={valid_mask.sum()}")
    print(f"skill = 1 - RMSE_model/RMSE_baseline  (>0 beats baseline).  Chl in log space.")
    print("=" * 100)
    print("PER-TRACER (mean over 5 depth levels)")
    hdr = ("tracer", "vs_persist", "vs_damped", "vs_seasClim", "vs_anomPers",
           "anomR2(clim)", "r2_tend", "corr_tend", "tend/anom", "alpha")
    print("  {:<6} {:>10} {:>9} {:>11} {:>11} {:>12} {:>8} {:>9} {:>9} {:>6}".format(*hdr))
    for t, d in by_tracer.items():
        print("  {:<6} {:>10} {:>9} {:>11} {:>11} {:>12} {:>8} {:>9} {:>9} {:>6.2f}".format(
            t, f(d["skill_vs_persistence"]), f(d["skill_vs_damped"]),
            f(d["skill_vs_seasonal_clim"]), f(d["skill_vs_anomaly_persist"]),
            f(d["anomaly_r2_annual_clim_mse"]), f(d["r2_tendency"]),
            f(d["corr_tendency"]), f(d["tendency_to_anomaly_ratio"]), d["alpha_damped"]))
    print("-" * 100)
    print("BY DEPTH LEVEL  (skill vs persistence [LEVEL] / anomaly-R2 vs seasonal clim)")
    for t in tracers:
        row = []
        for k in range(5):
            nm = f"{t}_k{k}"
            if nm in channels:
                sp = channels[nm]["skill_vs_persistence"]
                sc = channels[nm]["skill_vs_seasonal_clim"]
                row.append(f"k{k}:{sp:+.2f}/{sc:+.2f}")
        print(f"  {t:<6} " + "  ".join(row))
    print("-" * 100)
    print("CROSS-CHECK vs depth_chl_emulator.json (MSE-ratio convention, should match the PoC json)")
    for t, d in by_tracer.items():
        print(f"  {t:<6} skill_vs_persist_mse={d['skill_vs_persistence_mse']:+.4f}  "
              f"anomaly_r2_annualclim={d['anomaly_r2_annual_clim_mse']:+.4f}")
    print("-" * 100)
    print("BY SEASON (val-target month-of-year bin; pooled emulator skill vs persistence, MSE-ratio)")
    for b, d in out["by_season"].items():
        print(f"  {b}: n={d['n_val_pairs']} pooled_skill_vs_persistence={d['pooled_skill_vs_persistence_mse']:+.4f}")
    if len(regions) > 1:
        print("-" * 100)
        print("BY REGION (surface k0 skill vs persistence / vs seasonal clim)")
        for t in tracers:
            nm = f"{t}_k0"
            if nm in channels and "by_region" in channels[nm]:
                parts = []
                for rname, rd in channels[nm]["by_region"].items():
                    parts.append(f"{rname}: p={rd['skill_vs_persistence']:+.2f} c={rd['skill_vs_seasonal_clim']:+.2f}")
                print(f"  {t:<6} " + " | ".join(parts))
    print("=" * 100)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
