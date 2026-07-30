#!/usr/bin/env python
"""Baseline-comparison matrix v2 for the depth-resolved Track-2 emulator.

WHY A v2 (the domain-expert critique of v1)
-------------------------------------------
v1 (`emulator_baselines.py`) settled the "structural-ceiling" story: the emulator
loses to persistence on the near-conserved tracers (DIC/ALK/FeT/Chl) but beats it
on PIC/POC. A domain expert pushed back on TWO things v1 could not answer:

  (1) PERSISTENCE IS A WEAK STRAW MAN.  Beating "copy last month" is easy when a
      tracer swings a lot month-to-month.  A referee wants stronger, still-free
      baselines: a per-cell AR(1) (the optimal linear one-lag predictor, which is
      what a well-tuned persistence *should* be), and a per-cell linear trend.
      If the emulator only ties AR(1)/climatology, it has learned nothing beyond
      what a 2-parameter-per-cell autoregression already knows.

  (2) "PIC/POC BEAT PERSISTENCE" MAY BE MECHANICAL HEADROOM.  PIC/POC have large
      monthly tendency variance relative to their total field variability (v1's
      tend/anom ratio ~0.9 vs ~0.4 for DIC/ALK).  A large tendency makes the
      persistence RMSE (= rms of the true tendency) a *large denominator*, so the
      skill-vs-persistence ratio looks favourable even if the emulator's ABSOLUTE
      error is unremarkable.  The honest test is TENDENCY-NORMALIZED error
      (RMSE_model / rms(true tendency)) compared against the SAME quantity for the
      cheap baselines, and skill measured against the BEST cheap baseline, not the
      weakest one.

  (3) NO UNCERTAINTY.  v1 reported point skills over ~43k spatially autocorrelated
      cells.  A single ratio with no CI cannot support "genuine skill".  v2 attaches
      BLOCK-BOOTSTRAP confidence intervals (resample spatial blocks, not cells, so
      the CI respects spatial autocorrelation) to every headline number.

WHAT v2 ADDS ON TOP OF v1
-------------------------
Baselines (predictors of x_{t+1}, all leak-free -- climatologies / alpha / AR(1) phi /
trend coefficients fit on TRAIN months only, evaluated on the held-out val pairs):

    persistence            P    = x_t                                   (v1)
    damped persistence      D    = clim_ann + alpha*(x_t-clim_ann)       (v1; alpha per channel)
    seasonal climatology    S    = clim_month(t+1)                       (v1)
    annual climatology      CA   = clim_ann                             (v1)
    anomaly persistence     AP   = clim_month(t+1) + (x_t-clim_month(t)) (v1)
  * AR(1) per cell          A1   = clim_ann + phi_cell*(x_t-clim_ann)    (NEW: optimal lag-1)
  * AR(1) per cell seasonal A1s  = clim_month(t+1) + phi_s*(x_t-clim_month(t))  (NEW)
  * linear trend per cell   LT   = a_cell + b_cell * t_target            (NEW)
    emulator                E    = pred                                  (model under test)

Skill (task convention, matches v1 / CLAUDE.md):  SKILL = 1 - RMSE_model/RMSE_base.
Cross-check convention (matches emulator_poc.json):  1 - MSE_model/MSE_base.

Tendency-normalized error:  NE = RMSE_model / rms(true tendency)  == RMSE_model/RMSE_P.
    NE = 1  -> exactly as good as persistence;  NE < 1 -> beats it.  Reported for the
    emulator AND every baseline so the reader can see whether the *cheap* baselines
    already beat persistence (i.e. persistence is weak / the win is mechanical).

Decisive per-tracer verdict:
    genuine skill  <=>  skill_vs_best_simple_baseline CI lower bound > 0
    (the emulator must beat the strongest FREE baseline, with the CI clear of zero).

Pooling & normalization:  residuals are z-normalized per channel by the TRAIN std
(work space -- log for Chl, linear otherwise) before pooling across a tracer's 5
depth levels, so levels with different units/variance contribute evenly.  Per-channel
skills (which are z-invariant) are also emitted for a direct cross-check to v1 /
emulator_poc.json.

Breakdowns, each with block-bootstrap CIs:
    - by depth level   (per channel)
    - by biome/region  (equatorial |lat|<=5  vs  northern lat>5)
    - by init month    (val pairs grouped by month-of-year of the source snapshot)

INPUTS  (reuses already-dumped fields -- NO retraining)
    --fields   depth_chl_fields.npz    pred/true/persistence [Nval,C,H,W] + mask/lats/val_iters
    --cube     darwin_v05_L5_chl.npz   full state [M,C,H,W] + iters/times_days/chan_names
    --emu-json depth_chl_emulator.json config (val_frac, adjacency_tol, log_tracers, residual)

Cluster run (AICR):
    ~/dd_venv/bin/python scripts/analysis/emulator_baselines_v2.py \
        --fields  /scratch/qi_zim_neu/depth/depth_chl_fields.npz \
        --cube    /scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz \
        --emu-json /scratch/qi_zim_neu/depth/depth_chl_emulator.json \
        --out     /scratch/qi_zim_neu/depth/emulator_baseline_matrix_v2.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

LOG_EPS = 1e-12  # matches emulator_poc.LOG_EPS / e2s prognostic clamp


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def _to_work(x, is_log):
    """Physical -> working space (log for Chl channels, identity otherwise)."""
    if is_log:
        return np.log(np.clip(x, a_min=LOG_EPS, a_max=None))
    return x


def _season_bin(times_days):
    """Month-of-year bin 0..11 from days-since-ref.  Absolute phase is uncalibrated
    (see v1) but grouping is internally consistent: identical true calendar month ->
    identical bin."""
    m = (np.asarray(times_days, dtype=float) % 365.25) / (365.25 / 12.0)
    return np.floor(m).astype(int) % 12


def build_splits(times_days, val_frac, adjacency_tol):
    """Replicate emulator_poc.build_splits so we recover the exact train months and
    train adjacent pairs used for every leak-free fit."""
    times = np.asarray(times_days, dtype=float)
    M = len(times)
    gaps = np.diff(times)
    med_gap = float(np.median(gaps)) if len(gaps) else 0.0
    adjacent = gaps <= adjacency_tol * med_gap
    split_idx = int(round(M * (1.0 - val_frac)))
    split_idx = max(2, min(split_idx, M - 1))
    train_months = np.arange(0, split_idx)
    train_pairs = np.array([m for m in range(M - 1) if adjacent[m] and (m + 1) < split_idx])
    val_pairs = np.array([m for m in range(M - 1) if adjacent[m] and m >= split_idx])
    return {
        "adjacent": adjacent, "split_idx": split_idx,
        "train_months": train_months, "train_pairs": train_pairs,
        "val_pairs": val_pairs, "median_step_days": med_gap,
    }


# ---------------------------------------------------------------------------
# leak-free fits (train months only), all on the valid-cell axis [C, ncells]
# ---------------------------------------------------------------------------
def fit_climatologies(state_ws_v, train_months, season_bins):
    tm = np.asarray(train_months)
    clim_ann = np.nanmean(state_ws_v[tm], axis=0)             # [C,ncells]
    clim_seas = {}
    for b in range(12):
        members = tm[season_bins[tm] == b]
        clim_seas[b] = np.nanmean(state_ws_v[members], axis=0) if members.size else clim_ann
    return clim_ann, clim_seas


def fit_alpha_perchannel(state_ws_v, train_pairs, clim_ann):
    """v1's per-channel damping scalar alpha_c (one number per channel)."""
    C = state_ws_v.shape[1]
    alpha = np.ones(C, dtype=float)
    if train_pairs.size == 0:
        return alpha
    for c in range(C):
        num = den = 0.0
        cl = clim_ann[c]
        for m in train_pairs:
            ds = state_ws_v[m, c] - cl
            dt = state_ws_v[m + 1, c] - cl
            g = np.isfinite(ds) & np.isfinite(dt)
            num += float((ds[g] * dt[g]).sum())
            den += float((ds[g] * ds[g]).sum())
        alpha[c] = num / den if den > 1e-30 else 1.0
    return alpha


def fit_ar1_percell(state_ws_v, train_pairs, mean_field):
    """Per-cell lag-1 autoregression coefficient phi[C,ncells] on anomalies a = x - mean.
    `mean_field` is [C,ncells] (annual clim) OR a callable m->[C,ncells] (seasonal clim
    per source month).  phi = <a_t a_{t+1}> / <a_t^2>, clipped to (-1,1) for stationarity.
    """
    C, N = state_ws_v.shape[1], state_ws_v.shape[2]
    num = np.zeros((C, N)); den = np.zeros((C, N)); cnt = np.zeros((C, N))
    seasonal = callable(mean_field)
    for m in train_pairs:
        mu_s = mean_field(m) if seasonal else mean_field
        mu_t = mean_field(m + 1) if seasonal else mean_field
        a_s = state_ws_v[m] - mu_s
        a_t = state_ws_v[m + 1] - mu_t
        g = np.isfinite(a_s) & np.isfinite(a_t)
        num += np.where(g, a_s * a_t, 0.0)
        den += np.where(g, a_s * a_s, 0.0)
        cnt += g
    phi = np.where(den > 1e-30, num / np.where(den > 1e-30, den, 1.0), 0.0)
    phi = np.clip(phi, -0.999, 0.999)
    phi[cnt < 2] = 0.0  # too few obs -> fall back to the mean (phi=0)
    return phi


def fit_trend_percell(state_ws_v, train_months, times_days):
    """Per-cell OLS linear trend a + b*t on the train months.  Returns a,b [C,ncells]
    and the centering time tbar (so predict = a + b*(t_target - tbar))."""
    tm = np.asarray(train_months)
    t = np.asarray(times_days, dtype=float)[tm]
    tbar = float(t.mean())
    tc = t - tbar                                            # [ntrain]
    x = state_ws_v[tm]                                       # [ntrain,C,ncells]
    fin = np.isfinite(x)
    w = fin.astype(float)
    n = w.sum(0)                                             # [C,ncells]
    sx = np.where(fin, x, 0.0).sum(0)                        # sum x
    st = (w * tc[:, None, None]).sum(0)                      # sum t
    stt = (w * (tc[:, None, None] ** 2)).sum(0)              # sum t^2
    sxt = (np.where(fin, x, 0.0) * tc[:, None, None]).sum(0) # sum x*t
    denom = n * stt - st * st
    b = np.where(denom > 1e-30, (n * sxt - st * sx) / np.where(denom > 1e-30, denom, 1.0), 0.0)
    a = np.where(n > 0, (sx - b * st) / np.where(n > 0, n, 1.0), np.nan)
    return a, b, tbar


# ---------------------------------------------------------------------------
# block-bootstrap machinery
# ---------------------------------------------------------------------------
def block_sums(sq_resid, finite, cell_block, cell_sel, pair_sel, nblocks, preds):
    """Aggregate squared residuals into per-block sums for the selected cells & pairs.

    sq_resid : dict pred -> [Nval, L, ncells]  squared residuals (z-space)
    finite   : [Nval, L, ncells] bool joint-finite mask (identical across preds)
    cell_block : [ncells] int block id per cell
    cell_sel : [ncells] bool ;  pair_sel : [Nval] bool
    returns  block_SS[pred] [nblocks], block_N [nblocks]  over ACTIVE blocks only,
             plus the active-block index array.
    """
    fin = finite[pair_sel]                                   # [np,L,ncells]
    # per-cell count over selected pairs & levels
    ncell = fin.sum(axis=(0, 1)).astype(float)              # [ncells]
    block_N = np.bincount(cell_block[cell_sel], weights=ncell[cell_sel], minlength=nblocks)
    block_SS = {}
    for p in preds:
        r = np.where(fin, sq_resid[p][pair_sel], 0.0)
        scell = r.sum(axis=(0, 1))                          # [ncells]
        block_SS[p] = np.bincount(cell_block[cell_sel], weights=scell[cell_sel], minlength=nblocks)
    active = np.where(block_N > 0)[0]
    return {p: block_SS[p][active] for p in preds}, block_N[active], active


def _skill_from_ss(ss_model, ss_base):
    """1 - RMSE_model/RMSE_base (N cancels since paired)."""
    if ss_base <= 0:
        return float("nan")
    return 1.0 - float(np.sqrt(ss_model / ss_base))


def bootstrap_skill(block_SS, block_N, model_key, base_key, B, rng):
    """Block bootstrap of skill = 1 - RMSE_model/RMSE_base.  Returns point, lo, hi (95%)."""
    nb = block_N.size
    if nb == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan")}
    point = _skill_from_ss(block_SS[model_key].sum(), block_SS[base_key].sum())
    draws = np.empty(B)
    ssm = block_SS[model_key]; ssb = block_SS[base_key]
    for i in range(B):
        idx = rng.integers(0, nb, nb)
        draws[i] = _skill_from_ss(ssm[idx].sum(), ssb[idx].sum())
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"point": point, "lo": float(lo), "hi": float(hi)}


def bootstrap_ratio(block_SS, block_N, model_key, base_key, B, rng):
    """Block bootstrap of RMSE_model/RMSE_base (the tendency-normalized error when
    base_key is persistence).  Returns point, lo, hi (95%)."""
    nb = block_N.size
    if nb == 0:
        return {"point": float("nan"), "lo": float("nan"), "hi": float("nan")}

    def ratio(ssm, ssb):
        return float(np.sqrt(ssm / ssb)) if ssb > 0 else float("nan")

    point = ratio(block_SS[model_key].sum(), block_SS[base_key].sum())
    ssm = block_SS[model_key]; ssb = block_SS[base_key]
    draws = np.empty(B)
    for i in range(B):
        idx = rng.integers(0, nb, nb)
        draws[i] = ratio(ssm[idx].sum(), ssb[idx].sum())
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"point": point, "lo": float(lo), "hi": float(hi)}


# ---------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fields", default="/scratch/qi_zim_neu/depth/depth_chl_fields.npz")
    ap.add_argument("--cube", default="/scratch/qi_zim_neu/depth/darwin_v05_L5_chl.npz")
    ap.add_argument("--emu-json", default="/scratch/qi_zim_neu/depth/depth_chl_emulator.json")
    ap.add_argument("--out", default="/scratch/qi_zim_neu/depth/emulator_baseline_matrix_v2.json")
    ap.add_argument("--log-tracers", default=None)
    ap.add_argument(
        "--delta-t-seconds",
        type=float,
        default=None,
        help="Rederive the time axis as iters*delta_t/86400 instead of trusting the cube's "
        "stored `times_days`. Cubes built before PR #186 carry delta_t=900 s where v05 runs "
        "at 1200 s, so their times_days are 0.75x truth. Only the SEASONAL baselines depend "
        "on this (build_splits and the linear trend are invariant to a uniform rescaling of "
        "t), but those are exactly the baselines this script exists to compute. Pass 1200 "
        "for any v05 cube whose implied delta_t is 900.",
    )
    ap.add_argument(
        "--drop-channels",
        default=None,
        help="Comma-separated channel names to exclude from scoring (matched against the "
        "cube's chan_names). Use for channels that are numerically dead and were trained on "
        "anyway -- e.g. surfChl4, whose physical_std is 2.9e-08 and which is negative in "
        "~100%% of ocean cells, so its skill ratio is a division by noise.",
    )
    ap.add_argument("--n-boot", type=int, default=1000)
    ap.add_argument("--block-rows", type=int, default=15, help="block height in grid rows (lat)")
    ap.add_argument("--block-cols", type=int, default=36, help="block width in grid cols (lon)")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    rng = np.random.default_rng(args.seed)

    fields = np.load(args.fields, allow_pickle=True)
    cube = np.load(args.cube, allow_pickle=True)
    cfg = json.load(open(args.emu_json))["config"] if Path(args.emu_json).is_file() else {}
    val_frac = float(cfg.get("val_frac", 0.3))
    adjacency_tol = float(cfg.get("adjacency_tol", 1.6))
    residual = bool(cfg.get("residual", False))
    log_tracers = (args.log_tracers.split(",") if args.log_tracers
                   else cfg.get("log_tracers", ["Chl1"]))
    log_tracers = {s.strip() for s in log_tracers if str(s).strip()}

    chan = [str(x) for x in cube["chan_names"]]
    C = len(chan)
    is_log = np.array([c.split("_k")[0] in log_tracers for c in chan], dtype=bool)
    state = np.asarray(cube["state"], dtype=np.float64)          # [M,C,H,W]
    times_days = np.asarray(cube["times_days"], dtype=float)
    cube_iters = [int(x) for x in cube["iters"]]
    M = state.shape[0]

    pred_phys = np.asarray(fields["pred"], dtype=np.float64)     # [Nval,C,H,W]
    true_phys = np.asarray(fields["true"], dtype=np.float64)
    pers_phys = np.asarray(fields["persistence"], dtype=np.float64)
    valid_mask = np.asarray(fields["valid_mask"], dtype=bool)    # [H,W]
    lats = np.asarray(fields["lats"], dtype=float)               # [H]
    lons = np.asarray(fields["lons"], dtype=float)               # [W]
    val_iters = [int(x) for x in fields["val_iters"]]
    H, W = valid_mask.shape

    # ---- time axis: rederive from iters when the cube's own is calendar-contaminated ----
    if args.delta_t_seconds:
        implied = (
            float(times_days[1] * 86400.0 / cube_iters[1]) if len(cube_iters) > 1 and cube_iters[1] else float("nan")
        )
        times_days = np.asarray(cube_iters, dtype=float) * float(args.delta_t_seconds) / 86400.0
        print(
            f"[time] rederived from iters at delta_t={args.delta_t_seconds:g}s "
            f"(cube implied {implied:g}s); median step "
            f"{float(np.median(np.diff(times_days))):.4f} d"
        )

    # ---- optional channel drop (dead channels distort pooled skill) ----
    if args.drop_channels:
        drop = {s.strip() for s in args.drop_channels.split(",") if s.strip()}
        unknown = drop - set(chan)
        if unknown:
            raise SystemExit(f"--drop-channels: not in the cube's chan_names: {sorted(unknown)}")
        keep = np.array([c not in drop for c in chan], dtype=bool)
        if not keep.any():
            raise SystemExit("--drop-channels: every channel was dropped")
        print(f"[drop] excluding {sorted(drop)}; scoring {int(keep.sum())} of {C} channels")
        chan = [c for c, k in zip(chan, keep) if k]
        C = len(chan)
        is_log = is_log[keep]
        state = state[:, keep]
        pred_phys = pred_phys[:, keep]
        true_phys = true_phys[:, keep]
        pers_phys = pers_phys[:, keep]

    # locate val pairs in the cube; verify the dumped fields == cube snapshots (v1 asserts)
    tgt_idx = np.array([cube_iters.index(v) for v in val_iters])
    src_idx = tgt_idx - 1
    assert np.all(src_idx >= 0)
    assert np.nanmax(np.abs(state[src_idx] - pers_phys)) < 1e-3, "persistence != cube.state[source]"
    assert np.nanmax(np.abs(state[tgt_idx] - true_phys)) < 1e-3, "true != cube.state[target]"

    season_bins = _season_bin(times_days)
    splits = build_splits(times_days, val_frac, adjacency_tol)
    train_months = splits["train_months"]
    train_pairs = splits["train_pairs"]
    Nval = pred_phys.shape[0]

    # ---- collapse to the valid-cell axis (memory + speed) ----
    ii, jj = np.where(valid_mask)                               # [ncells] row/col
    ncells = ii.size
    cell_lat = lats[ii]
    # working space, valid cells only
    state_ws_v = state[:, :, ii, jj].copy()                    # [M,C,ncells]
    pred_ws_v = pred_phys[:, :, ii, jj].copy()                 # [Nval,C,ncells]
    for c in np.where(is_log)[0]:
        state_ws_v[:, c] = _to_work(state_ws_v[:, c], True)
        pred_ws_v[:, c] = _to_work(pred_ws_v[:, c], True)

    # ---- leak-free fits ----
    clim_ann, clim_seas = fit_climatologies(state_ws_v, train_months, season_bins)
    alpha = fit_alpha_perchannel(state_ws_v, train_pairs, clim_ann)
    phi_ann = fit_ar1_percell(state_ws_v, train_pairs, clim_ann)
    phi_seas = fit_ar1_percell(state_ws_v, train_pairs, lambda m: clim_seas[int(season_bins[m])])
    trend_a, trend_b, tbar = fit_trend_percell(state_ws_v, train_months, times_days)

    # ---- per-channel TRAIN std for z-normalization (work space) ----
    zc = np.empty(C)
    tm = np.asarray(train_months)
    for c in range(C):
        v = state_ws_v[tm, c]
        v = v[np.isfinite(v)]
        zc[c] = float(v.std()) if v.size else 1.0
        if zc[c] < 1e-30:
            zc[c] = 1.0

    val_tgt_bins = season_bins[tgt_idx]
    val_src_bins = season_bins[src_idx]
    t_target = np.asarray(times_days)[tgt_idx]                  # [Nval]

    # ---- build the predictor stacks of x_{t+1} : [Nval,C,ncells] (work space) ----
    T = state_ws_v[tgt_idx]                                     # truth
    P = state_ws_v[src_idx]                                     # persistence (x_t)
    E = pred_ws_v                                               # emulator
    Dd = clim_ann[None] + alpha[None, :, None] * (P - clim_ann[None])            # damped
    S = np.stack([clim_seas[int(val_tgt_bins[i])] for i in range(Nval)])         # seasonal clim [Nval,C,ncells]
    Ssrc = np.stack([clim_seas[int(val_src_bins[i])] for i in range(Nval)])
    CA = np.broadcast_to(clim_ann[None], T.shape)                               # annual clim
    AP = S + (P - Ssrc)                                                          # anomaly persistence
    A1 = clim_ann[None] + phi_ann[None] * (P - clim_ann[None])                   # AR(1) annual
    A1s = S + phi_seas[None] * (P - Ssrc)                                        # AR(1) seasonal
    LT = trend_a[None] + trend_b[None] * (t_target[:, None, None] - tbar)        # linear trend

    predictors = {
        "emulator": E, "persistence": P, "damped": Dd, "seasonal_clim": S,
        "annual_clim": CA, "anomaly_persist": AP, "ar1_percell": A1,
        "ar1_seasonal_percell": A1s, "linear_trend_percell": LT,
    }
    SIMPLE = ["persistence", "damped", "seasonal_clim", "annual_clim",
              "anomaly_persist", "ar1_percell", "ar1_seasonal_percell", "linear_trend_percell"]
    BOOT_KEYS = ["emulator", "persistence", "ar1_percell", "seasonal_clim",
                 "damped", "anomaly_persist", "ar1_seasonal_percell",
                 "linear_trend_percell", "annual_clim"]

    # z-normalize residuals per channel; store squared residuals [Nval,C,ncells]
    sq = {}
    finite_all = np.isfinite(T)
    for k, arr in predictors.items():
        r = (arr - T) / zc[None, :, None]
        finite_all &= np.isfinite(r)
        sq[k] = r
    # apply joint finite mask -> square; keep a single finite mask
    finite = finite_all
    for k in sq:
        sq[k] = np.where(finite, sq[k] ** 2, 0.0)

    # ---- spatial blocks ----
    ncol_blocks = int(np.ceil(W / args.block_cols))
    cell_block = (ii // args.block_rows) * ncol_blocks + (jj // args.block_cols)
    nblocks = int(cell_block.max()) + 1

    tracers = list(dict.fromkeys(c.split("_k")[0] for c in chan))
    tracer_lvls = {t: [i for i, c in enumerate(chan) if c.split("_k")[0] == t] for t in tracers}

    # biome cell masks
    biomes = {
        "equatorial_|lat|<=5": np.abs(cell_lat) <= 5.0,
        "northern_lat>5": cell_lat > 5.0,
    }
    biomes = {k: v for k, v in biomes.items() if v.sum() > 100}

    # init-month groups (val pairs grouped by source month-of-year bin)
    init_groups = {}
    for i in range(Nval):
        init_groups.setdefault(int(val_src_bins[i]), []).append(i)

    B = args.n_boot

    def tracer_sq(t, levels=None):
        """squared residuals & finite mask for tracer t (optionally a single level index
        within the tracer), reshaped to [Nval, L, ncells]."""
        lv = tracer_lvls[t] if levels is None else [tracer_lvls[t][levels]]
        sub = {k: sq[k][:, lv, :] for k in BOOT_KEYS}
        fin = finite[:, lv, :]
        return sub, fin

    def do_bootstrap(sub, fin, cell_sel, pair_sel):
        bSS, bN, _ = block_sums(sub, fin, cell_block, cell_sel, pair_sel, nblocks, BOOT_KEYS)
        # choose best SIMPLE baseline on the full (unbootstrapped) selection
        totals = {k: float(bSS[k].sum()) for k in SIMPLE if k in bSS}
        best = min(totals, key=totals.get)
        out = {
            "n_cells": int(cell_sel.sum()), "n_pairs": int(pair_sel.sum()),
            "n_active_blocks": int(bN.size),
            "rmse_z": {k: float(np.sqrt(bSS[k].sum() / max(bN.sum(), 1))) for k in BOOT_KEYS},
            "best_simple_baseline": best,
            "skill_vs_persistence": bootstrap_skill(bSS, bN, "emulator", "persistence", B, rng),
            "skill_vs_ar1_percell": bootstrap_skill(bSS, bN, "emulator", "ar1_percell", B, rng),
            "skill_vs_best_simple": bootstrap_skill(bSS, bN, "emulator", best, B, rng),
            "tendency_normalized_error": bootstrap_ratio(bSS, bN, "emulator", "persistence", B, rng),
        }
        # tendency-normalized error of the cheap baselines (do the free baselines already beat persistence?)
        out["norm_err_baselines"] = {
            k: float(np.sqrt(bSS[k].sum() / max(bSS["persistence"].sum(), 1e-30)))
            for k in SIMPLE
        }
        return out

    all_cells = np.ones(ncells, dtype=bool)
    all_pairs = np.ones(Nval, dtype=bool)

    # ---------- per tracer (pooled over 5 levels, all cells, all pairs) ----------
    by_tracer = {}
    for t in tracers:
        sub, fin = tracer_sq(t)
        rec = do_bootstrap(sub, fin, all_cells, all_pairs)
        # unit-free mechanical-headroom context in WORK space (not z): tend / anomaly amplitude
        lv = tracer_lvls[t]
        tend = (T[:, lv] - P[:, lv]); tend = tend[finite[:, lv]]
        anom = (T[:, lv] - CA[:, lv]); anom = anom[finite[:, lv]]
        rec["rms_tendency_work"] = float(np.sqrt(np.mean(tend ** 2))) if tend.size else float("nan")
        rec["rms_field_anomaly_work"] = float(np.sqrt(np.mean(anom ** 2))) if anom.size else float("nan")
        rec["tend_over_anom"] = (rec["rms_tendency_work"] / rec["rms_field_anomaly_work"]
                                 if rec["rms_field_anomaly_work"] > 0 else float("nan"))
        rec["log_space"] = bool(is_log[lv[0]])
        by_tracer[t] = rec

    # ---------- by depth level (per channel) ----------
    by_level = {}
    for t in tracers:
        by_level[t] = {}
        for klev in range(len(tracer_lvls[t])):
            sub, fin = tracer_sq(t, levels=klev)
            r = do_bootstrap(sub, fin, all_cells, all_pairs)
            by_level[t][f"k{klev}"] = {
                "skill_vs_persistence": r["skill_vs_persistence"],
                "skill_vs_best_simple": r["skill_vs_best_simple"],
                "best_simple_baseline": r["best_simple_baseline"],
                "tendency_normalized_error": r["tendency_normalized_error"],
            }

    # ---------- by biome/region (per tracer) ----------
    by_biome = {}
    for t in tracers:
        by_biome[t] = {}
        sub, fin = tracer_sq(t)
        for bname, bmask in biomes.items():
            r = do_bootstrap(sub, fin, bmask, all_pairs)
            by_biome[t][bname] = {
                "n_cells": r["n_cells"],
                "skill_vs_persistence": r["skill_vs_persistence"],
                "skill_vs_best_simple": r["skill_vs_best_simple"],
                "best_simple_baseline": r["best_simple_baseline"],
                "tendency_normalized_error": r["tendency_normalized_error"],
            }

    # ---------- by init month (pooled across tracers; and per tracer point) ----------
    by_init_month = {}
    # pooled across all channels
    sub_all = {k: sq[k] for k in BOOT_KEYS}
    for bin_id, pair_list in sorted(init_groups.items()):
        pmask = np.zeros(Nval, dtype=bool); pmask[pair_list] = True
        r = do_bootstrap(sub_all, finite, all_cells, pmask)
        by_init_month[f"bin{bin_id}"] = {
            "n_pairs": int(pmask.sum()),
            "val_iters": [val_iters[i] for i in pair_list],
            "pooled_skill_vs_persistence": r["skill_vs_persistence"],
            "pooled_skill_vs_best_simple": r["skill_vs_best_simple"],
            "best_simple_baseline": r["best_simple_baseline"],
            "pooled_tendency_normalized_error": r["tendency_normalized_error"],
        }

    # ---------- overall (pooled all channels/cells/pairs) ----------
    overall = do_bootstrap({k: sq[k] for k in BOOT_KEYS}, finite, all_cells, all_pairs)

    out = {
        "meta": {
            "script": "emulator_baselines_v2.py",
            "fields": str(args.fields), "cube": str(args.cube),
            "aoi": str(fields["aoi"]) if "aoi" in fields.files else cfg.get("aoi"),
            "residual": residual, "val_frac": val_frac, "adjacency_tol": adjacency_tol,
            "log_tracers": sorted(log_tracers),
            # Provenance for the two choices that change what the seasonal baselines mean.
            "delta_t_seconds": args.delta_t_seconds,
            "time_axis": ("rederived from iters" if args.delta_t_seconds else "cube times_days"),
            "dropped_channels": (
                sorted({s.strip() for s in args.drop_channels.split(",") if s.strip()})
                if args.drop_channels else []
            ),
            "scored_channels": list(chan),
            "n_channels": C, "n_val_pairs": int(Nval),
            "n_train_months": int(train_months.size), "n_train_pairs": int(train_pairs.size),
            "n_valid_cells": int(ncells),
            "val_target_iters": val_iters,
            "n_boot": B, "block_rows": args.block_rows, "block_cols": args.block_cols,
            "n_blocks_total": int(nblocks), "seed": args.seed,
            "skill_convention": "1 - RMSE_model/RMSE_base (task); residuals z-normalized per channel by TRAIN std before pooling.",
            "tendency_normalized_error": "RMSE_model / rms(true tendency) == RMSE_model/RMSE_persistence; <1 beats persistence.",
            "biomes": {k: int(v.sum()) for k, v in biomes.items()},
            "predictors": list(predictors.keys()),
            "simple_baselines": SIMPLE,
        },
        "overall": overall,
        "by_tracer": by_tracer,
        "by_level": by_level,
        "by_biome": by_biome,
        "by_init_month": by_init_month,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2))

    # ------------------------------------------------------------------ report
    def ci(d):
        return f"{d['point']:+.3f} [{d['lo']:+.3f},{d['hi']:+.3f}]"

    print("=" * 108)
    print(f"EMULATOR BASELINE MATRIX v2   aoi={out['meta']['aoi']}  residual={residual}  "
          f"Nval={Nval}  train_months={train_months.size}  train_pairs={train_pairs.size}  "
          f"cells={ncells}  blocks={nblocks}  B={B}")
    print("skill = 1 - RMSE_model/RMSE_base (z-normed, pooled).  CI = 95% spatial block-bootstrap.")
    print("=" * 108)
    print("PER TRACER (pooled over 5 depth levels)")
    print("  {:<6} {:>26} {:>26} {:>26} {:>10} {:>9}".format(
        "tracer", "skill_vs_persistence", "skill_vs_AR1(percell)", "skill_vs_BEST_simple",
        "NE(emu)", "tend/anom"))
    for t, d in by_tracer.items():
        print("  {:<6} {:>26} {:>26} {:>26} {:>10} {:>9.3f}  best={}".format(
            t, ci(d["skill_vs_persistence"]), ci(d["skill_vs_ar1_percell"]),
            ci(d["skill_vs_best_simple"]),
            f"{d['tendency_normalized_error']['point']:.3f}", d["tend_over_anom"],
            d["best_simple_baseline"]))
    print("-" * 108)
    print("MECHANICAL-HEADROOM CHECK: tendency-normalized error of the FREE baselines per tracer")
    print("  (values < 1 mean that cheap baseline ALSO beats persistence -> persistence is weak there)")
    hdrs = ["persist", "damped", "seasClim", "annClim", "anomPer", "AR1", "AR1seas", "trend"]
    keys = SIMPLE
    print("  {:<6} ".format("tracer") + " ".join(f"{h:>8}" for h in hdrs))
    for t, d in by_tracer.items():
        vals = d["norm_err_baselines"]
        print("  {:<6} ".format(t) + " ".join(f"{vals[k]:>8.3f}" for k in keys))
    print("-" * 108)
    print("BY BIOME (skill vs persistence / vs best-simple, 95% CI)")
    for t in tracers:
        for bname, bd in by_biome[t].items():
            print(f"  {t:<6} {bname:<20} n={bd['n_cells']:>6}  "
                  f"vsPersist={ci(bd['skill_vs_persistence'])}  "
                  f"vsBest={ci(bd['skill_vs_best_simple'])} (best={bd['best_simple_baseline']})")
    print("-" * 108)
    print("BY INIT MONTH (pooled across tracers; skill vs persistence / vs best-simple)")
    for b, d in by_init_month.items():
        print(f"  {b}: n_pairs={d['n_pairs']}  vsPersist={ci(d['pooled_skill_vs_persistence'])}  "
              f"vsBest={ci(d['pooled_skill_vs_best_simple'])} (best={d['best_simple_baseline']})")
    print("-" * 108)
    print("BY DEPTH LEVEL (skill vs persistence [point] / skill vs best-simple [point])")
    for t in tracers:
        row = []
        for klev in range(len(tracer_lvls[t])):
            dd = by_level[t][f"k{klev}"]
            row.append(f"k{klev}:{dd['skill_vs_persistence']['point']:+.2f}/"
                       f"{dd['skill_vs_best_simple']['point']:+.2f}")
        print(f"  {t:<6} " + "  ".join(row))
    print("=" * 108)
    print("OVERALL pooled:  vsPersist={}  vsBest={} (best={})  NE(emu)={}".format(
        ci(overall["skill_vs_persistence"]), ci(overall["skill_vs_best_simple"]),
        overall["best_simple_baseline"], ci(overall["tendency_normalized_error"])))
    print("=" * 108)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
