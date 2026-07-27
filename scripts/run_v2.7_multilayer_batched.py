# -*- coding: utf-8 -*-
"""v2.7 multilayer training, **batched over N seeds in a single GPU pass**.

Companion to ``run_v2.7_multilayer_quick.py`` (single-seed). At the
21x51 Eq Pac AOI the RTX 5090 is severely underutilized when training
one seed at a time -- the box-model integrator dominates wall-clock
and the launch-overhead floor is high. Stacking N seeds along a new
batch dim makes the same compute fully amortize across seeds.

Approach:
- N independent DINN networks (seeded separately via torch.manual_seed
  before each Module construction) maintain N independent parameter
  vectors per epoch.
- The box-model state is replicated to shape ``[15, N_seeds, H, W]``;
  Carroll-6 params to shape ``[6, N_seeds, H, W]``. Because every step
  in ``carroll6_5pft_2layer_step`` is elementwise, the integrator is
  layout-agnostic and runs as-is with no code changes -- broadcasting
  over the new seed dim "for free".
- Per-seed losses (z-score / GEOTRACES surface + subsurface / PINN drift)
  are vectorised over the seed dim so we never loop in Python.
- A single ``loss.backward()`` on ``sum(per_seed_losses)`` routes each
  seed's gradient back to its own network (the parameter graphs are
  disjoint because each DINN owns distinct nn.Parameters).
- One JSON per seed is written at the end.

Run:
    NB23_SEEDS=0,1,2,3,4 python scripts/run_v2.7_multilayer_batched.py

Expected wall-clock: ~120-200 s on RTX 5090 Laptop for 5 seeds (vs
~440-475 s sequential at the same data-cache state). Hands the saved
time straight back to research iteration.

Configuration via env vars (same defaults as single-seed runner unless
noted):
    NB23_SEEDS            comma-separated seed list (default "0")
    NB23_BATCH_SEEDS      alias for NB23_SEEDS (legacy compat)
    GEOTRACES_W           surface GEOTRACES weight (default 0.3)
    GEOTRACES_SUB_W       subsurface GEOTRACES weight (default 0.3)
    NB23_PINN_WEIGHT      PINN drift weight (default 3.0)
    NB23_FET_WEIGHT       z-scored FeT weight (default 1.0)
    NB23_N_EPOCHS         training epochs (default 1500)
    DARWIN_DATA_ROOT      Darwin v05 data root (default D:\\ecco_darwin_v5)
    GEOTRACES_DATA_ROOT   IDP2025 NetCDF root (default D:\\geotraces)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

# Force stdout to UTF-8 on Windows.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate
from darwindiff.carroll6 import (
    CARROLL_VALUES,
    K_FE,
    PARAM_BOUNDS,
    PHI_DUST,
    Q_FE,
    bounded_params,
)
from darwindiff.carroll6_5pft import (
    MU_DEFAULT_DIATOM,
    MU_DEFAULT_PROLL,
    MU_DEFAULT_SYN,
)
from darwindiff.carroll6_5pft_2layer import (
    I_ALK_1,
    I_ALK_2,
    I_DFE_1,
    I_DFE_2,
    I_DIATOM,
    I_DIC_1,
    I_DIC_2,
    I_LGE,
    I_PIC_1,
    I_PIC_2,
    I_POC_1,
    I_POC_2,
    I_PROHL,
    I_PROLL,
    I_SYN,
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
    carroll6_5pft_2layer_step,
)
from darwindiff.ecco_darwin_loader import (
    AOI_BY_KEY,
    open_bin_average,
    subset_aoi,
    time_mean,
)
from darwindiff.geotraces_loader import (
    open_geotraces_bottle,
    subset_aoi_geotraces,
)
from darwindiff.diagnostics import band_of
from darwindiff.llc270_loader import bin_native_tracer_to_1deg
from darwindiff.networks import DINN
from darwindiff.safe_load import safe_torch_load


# ============================== Config ====================================

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\ecco_darwin_v5"))
BIN_AVG_PATH = str(DATA_ROOT / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc")
MONTHLY_ROOT = DATA_ROOT / "output" / "monthly"
GRID_DIR = DATA_ROOT / "grid"
GEOTRACES_ROOT = Path(os.environ.get("GEOTRACES_DATA_ROOT", r"D:\geotraces"))
GEOTRACES_NC = GEOTRACES_ROOT / "GEOTRACES_IDP2025_Seawater.nc"

_seeds_env = os.environ.get("NB23_SEEDS", os.environ.get("NB23_BATCH_SEEDS", "0"))
SEEDS: list[int] = [int(s.strip()) for s in _seeds_env.split(",") if s.strip()]
N_SEEDS = len(SEEDS)

FET_W = float(os.environ.get("NB23_FET_WEIGHT", "1.0"))
PINN_W = float(os.environ.get("NB23_PINN_WEIGHT", "3.0"))
PINN_TYPE = os.environ.get("NB23_PINN_TYPE", "drift").lower()
GEOTRACES_W = float(os.environ.get("GEOTRACES_W", "0.3"))
GEOTRACES_SUB_W = float(os.environ.get("GEOTRACES_SUB_W", "0.3"))
SUB_DEPTH_MIN = float(os.environ.get("GEOTRACES_SUB_DEPTH_MIN", "50.0"))
SUB_DEPTH_MAX = float(os.environ.get("GEOTRACES_SUB_DEPTH_MAX", "1000.0"))
N_EPOCHS = int(os.environ.get("NB23_N_EPOCHS", "1500"))
# DARWIN_IC=1 swaps literature-default initial conditions for Darwin v5
# pickup-derived per-cell ICs (5 inorganics x 2 layers, see
# scripts/build_darwin_ic_cache.py). Phyto biomass stays at literature
# defaults since the 7-PFT -> 5-PFT mapping is non-trivial and biomass
# equilibrates fast. Default off so existing v2.7 JSONs stay reproducible.
USE_DARWIN_IC = os.environ.get("DARWIN_IC", "0") == "1"
DARWIN_IC_CACHE_PATH = Path(__file__).resolve().parent / os.environ.get("DARWIN_IC_CACHE", "darwin_ic_cache.npz")
DARWIN_IC_TAG = os.environ.get("DARWIN_IC_TAG", "darwinic")
# v2.8: depth-resolved POC observation as an L2 z-score loss term. Target
# is Darwin's depth-mean POC over the L2 window (from the same IC cache).
# When > 0, the integrator's L2 POC trajectory gets a direct constraint,
# closing the dynamical degeneracy that scav_rat sits in.
POC_SUB_W = float(os.environ.get("POC_SUB_W", "0.0"))
# GEOTRACES_POC_SUB_W: weight on a separate absolute-units MSE loss against
# REAL GEOTRACES IDP2025 POC observations (POC_LPT_CONC + POC_SPT_CONC at
# subsurface depths, summed and unit-converted to mmol/m^3). Distinct from
# POC_SUB_W (which uses Darwin self-target z-score over all AOI cells).
# The two can coexist. Default 0 = off; existing v2.8 JSONs unchanged.
GEOTRACES_POC_SUB_W = float(os.environ.get("GEOTRACES_POC_SUB_W", "0.0"))
# Block cross-validation: if < 1.0, train on the westernmost TRAIN_LON_FRAC of
# columns and hold out the easternmost (1 - TRAIN_LON_FRAC). After training,
# the recovery report shows both the train-cell-mean recovery and the
# test-cell-mean recovery for spatial-generalization validation. Default 1.0
# = no split (existing behavior preserved bit-for-bit).
TRAIN_LON_FRAC = float(os.environ.get("TRAIN_LON_FRAC", "1.0"))

DT = 0.25
N_STEPS = 200
# K_FE is the iron half-saturation used inside the PINN drift loss.
# Imported from darwindiff.carroll6 so the PINN block uses the same
# constant as the integrator.

# DARWIN_AOI env var selects which AOI to train on (v3.0 multi-AOI scoping
# precursor). Defaults to 'eqpac' so all existing v2.6/v2.7/v2.8 JSONs and
# cache files stay reproducible bit-for-bit. AOI_BY_KEY is the canonical
# lookup table in darwindiff.ecco_darwin_loader.
AOI_KEY = os.environ.get("DARWIN_AOI", "eqpac")
if AOI_KEY not in AOI_BY_KEY:
    raise ValueError(f"DARWIN_AOI={AOI_KEY!r} not in {sorted(AOI_BY_KEY)}")
AOI = AOI_BY_KEY[AOI_KEY]
print(f"AOI: {AOI.name} ({AOI.lat_min}-{AOI.lat_max} N, {AOI.lon_min}-{AOI.lon_max} E)")
print(f"Seeds: {SEEDS} (N={N_SEEDS})")
print(f"Config: fet_w={FET_W}, pinn_w={PINN_W} ({PINN_TYPE}),")
print(f"        geotraces_surface_w={GEOTRACES_W}, geotraces_subsurface_w={GEOTRACES_SUB_W}")
print(f"        epochs={N_EPOCHS}, subsurface depth band: [{SUB_DEPTH_MIN}, {SUB_DEPTH_MAX}] m")
print()


# ============================== Darwin targets (cached) ===================

CACHE_DIR = DATA_ROOT / "cache"
CACHE_PATH = CACHE_DIR / f"eqpac_targets_{AOI.name.replace(' ', '_').lower()}.pt"


def _build_eqpac_targets() -> dict:
    print("  building target cache from Darwin bin_average + LLC270 native...")
    ds_bin = open_bin_average(BIN_AVG_PATH)
    ds_aoi = subset_aoi(ds_bin, AOI)
    ds_avg_local = time_mean(ds_aoi)

    out = {
        "aoi_name": AOI.name,
        "aoi_bounds": (AOI.lat_min, AOI.lat_max, AOI.lon_min, AOI.lon_max),
        "darwin_lats": ds_avg_local.lat.values.astype(np.float64),
        "darwin_lons": ds_avg_local.lon.values.astype(np.float64),
        "sst": ds_avg_local["SST"].values.astype(np.float32),
        "mld": ds_avg_local["mldDepth"].values.astype(np.float32),
        "wind": ds_avg_local["windSpeed"].values.astype(np.float32),
        "sss": (
            ds_avg_local["SSS"].values.astype(np.float32)
            if "SSS" in ds_avg_local
            else np.full_like(ds_avg_local["SST"].values.astype(np.float32), 35.0)
        ),
        "pco2_atm_field": ds_avg_local["apCO2"].values.astype(np.float32),
        "co2_flux_obs": ds_avg_local["CO2_flux"].values.astype(np.float32),
        "chl_per_pft": {
            f"Chl{i}": ds_avg_local[f"Chl{i}"].values.astype(np.float32)
            for i in range(1, 6)
        },
    }
    for var in ["FeT", "POC", "PIC", "DIC", "ALK"]:
        out[f"{var.lower()}_binned"] = bin_native_tracer_to_1deg(
            monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable=var,
            lat_min=AOI.lat_min, lat_max=AOI.lat_max,
            lon_min=AOI.lon_min, lon_max=AOI.lon_max,
            iters="all",
        )
    return out


def _load_or_build_target_cache() -> dict:
    expected_bounds = (AOI.lat_min, AOI.lat_max, AOI.lon_min, AOI.lon_max)
    if CACHE_PATH.is_file():
        try:
            cached = safe_torch_load(CACHE_PATH, map_location="cpu")
            if (cached.get("aoi_name") == AOI.name
                    and cached.get("aoi_bounds") == expected_bounds):
                print(f"Loaded target cache from {CACHE_PATH}.")
                return cached
        except Exception as e:
            print(f"  cache load failed ({e}); rebuilding...")

    data = _build_eqpac_targets()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(data, CACHE_PATH)
        print(f"  saved target cache to {CACHE_PATH}")
    except Exception as e:
        print(f"  [warn] could not save cache: {e}")
    return data


print(f"Loading targets (cache: {CACHE_PATH})...")
_targets = _load_or_build_target_cache()
sst = _targets["sst"]
mld = _targets["mld"]
wind = _targets["wind"]
sss = _targets["sss"]
pco2_atm_field = _targets["pco2_atm_field"]
co2_flux_obs = _targets["co2_flux_obs"]
chl_per_pft = _targets["chl_per_pft"]
fet_binned = _targets["fet_binned"]
poc_binned = _targets["poc_binned"]
pic_binned = _targets["pic_binned"]
dic_binned = _targets["dic_binned"]
alk_binned = _targets["alk_binned"]
darwin_lats = _targets["darwin_lats"]
darwin_lons = _targets["darwin_lons"]
print(f"  bin_average shape: {sst.shape}")


# ============================== GEOTRACES iron — surface + subsurface =======

print(f"Loading GEOTRACES IDP2025 from {GEOTRACES_NC}...")
geotraces_ds = open_geotraces_bottle(GEOTRACES_NC)
geotraces_sub = subset_aoi_geotraces(geotraces_ds, AOI)
print(f"  Eq Pac stations: {geotraces_sub.sizes['N_STATIONS']}")

n_dlat = len(darwin_lats)
n_dlon = len(darwin_lons)
darwin_lat_res = float(darwin_lats[1] - darwin_lats[0]) if n_dlat > 1 else 1.0
darwin_lon_res = float(darwin_lons[1] - darwin_lons[0]) if n_dlon > 1 else 1.0
darwin_lat_edge_lo = darwin_lats[0] - darwin_lat_res / 2.0
darwin_lon_edge_lo = darwin_lons[0] - darwin_lon_res / 2.0

QC_GOOD = (49, 50)
DEPTH_MAX_SURFACE = 50.0

n_st = geotraces_sub.sizes["N_STATIONS"]
n_sa = geotraces_sub.sizes["N_SAMPLES"]
fe_vals = geotraces_sub.Fe_D_CONC.values
g_lats_all = np.broadcast_to(geotraces_sub.latitude.values[:, None], (n_st, n_sa)).flatten()
g_lons_all = np.broadcast_to(geotraces_sub.longitude.values[:, None], (n_st, n_sa)).flatten()
g_depths_all = geotraces_sub.DEPTH.values.flatten()
g_fe_all = fe_vals.flatten()
g_qc_all = geotraces_sub.Fe_D_CONC_qc.values.flatten()
finite_basic = (
    np.isfinite(g_fe_all) & np.isfinite(g_lats_all) & np.isfinite(g_lons_all)
    & np.isfinite(g_depths_all) & np.isin(g_qc_all, np.array(QC_GOOD, dtype=g_qc_all.dtype))
)


def bin_to_darwin_grid(keep_mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    lats = g_lats_all[keep_mask]
    lons = g_lons_all[keep_mask]
    fe = g_fe_all[keep_mask] * 1025.0 * 1.0e-6
    lat_idx = np.floor((lats - darwin_lat_edge_lo) / darwin_lat_res).astype(np.int64)
    lon_idx = np.floor((lons - darwin_lon_edge_lo) / darwin_lon_res).astype(np.int64)
    lat_idx = np.minimum(lat_idx, n_dlat - 1)
    lon_idx = np.minimum(lon_idx, n_dlon - 1)
    in_bounds = (lat_idx >= 0) & (lon_idx >= 0)
    lat_idx, lon_idx, fe = lat_idx[in_bounds], lon_idx[in_bounds], fe[in_bounds]
    sum_grid = np.zeros((n_dlat, n_dlon), dtype=np.float64)
    cnt_grid = np.zeros((n_dlat, n_dlon), dtype=np.int64)
    np.add.at(sum_grid, (lat_idx, lon_idx), fe)
    np.add.at(cnt_grid, (lat_idx, lon_idx), 1)
    target = np.full((n_dlat, n_dlon), np.nan, dtype=np.float32)
    nonzero = cnt_grid > 0
    target[nonzero] = (sum_grid[nonzero] / cnt_grid[nonzero]).astype(np.float32)
    return target, nonzero


keep_surface = finite_basic & (g_depths_all <= DEPTH_MAX_SURFACE)
geotraces_target_np, geotraces_mask_np = bin_to_darwin_grid(keep_surface)
n_geo_surface = int(geotraces_mask_np.sum())

keep_subsurface = (
    finite_basic & (g_depths_all > SUB_DEPTH_MIN) & (g_depths_all <= SUB_DEPTH_MAX)
)
geotraces_sub_target_np, geotraces_sub_mask_np = bin_to_darwin_grid(keep_subsurface)
n_geo_subsurface = int(geotraces_sub_mask_np.sum())

print(f"  Surface bins: {n_geo_surface};  Subsurface bins: {n_geo_subsurface}")


# GEOTRACES POC subsurface target (LPT + SPT) for v2.8's
# GEOTRACES_POC_SUB_W loss term. Units: POC_*_CONC are umol C/kg;
# multiply by RHO_SW (1025) and 1e-3 to get mmol C/m^3 (matches the
# integrator's POC_2 units).
geotraces_poc_target_np = None
geotraces_poc_mask_np = None
n_geo_poc_subsurface = 0
if GEOTRACES_POC_SUB_W > 0:
    print(f"  building GEOTRACES POC subsurface target (POC_LPT + POC_SPT)...")
    poc_lpt = geotraces_sub.POC_LPT_CONC.values
    poc_spt = geotraces_sub.POC_SPT_CONC.values
    poc_lpt_qc = geotraces_sub.POC_LPT_CONC_qc.values
    poc_spt_qc = geotraces_sub.POC_SPT_CONC_qc.values
    poc_lpt_f = poc_lpt.flatten(); poc_spt_f = poc_spt.flatten()
    poc_lpt_qc_f = poc_lpt_qc.flatten(); poc_spt_qc_f = poc_spt_qc.flatten()
    # Either tracer present + good QC + finite + positive (drop negative artifacts).
    qc_good_arr = np.array(QC_GOOD)
    lpt_ok = (np.isfinite(poc_lpt_f) & np.isin(poc_lpt_qc_f, qc_good_arr.astype(poc_lpt_qc_f.dtype)) & (poc_lpt_f > 0))
    spt_ok = (np.isfinite(poc_spt_f) & np.isin(poc_spt_qc_f, qc_good_arr.astype(poc_spt_qc_f.dtype)) & (poc_spt_f > 0))
    poc_total = np.where(lpt_ok, poc_lpt_f, 0.0) + np.where(spt_ok, poc_spt_f, 0.0)
    poc_any = lpt_ok | spt_ok
    # Subsurface depth filter (re-use SUB_DEPTH_MIN/MAX), basic finiteness.
    poc_keep = (
        poc_any & np.isfinite(g_lats_all) & np.isfinite(g_lons_all)
        & np.isfinite(g_depths_all)
        & (g_depths_all > SUB_DEPTH_MIN) & (g_depths_all <= SUB_DEPTH_MAX)
    )
    # Bin to AOI grid with unit conversion umol/kg -> mmol/m^3.
    def bin_poc_to_grid(keep_mask):
        lats = g_lats_all[keep_mask]; lons = g_lons_all[keep_mask]
        poc = poc_total[keep_mask] * 1025.0 * 1.0e-3
        lat_idx = np.floor((lats - darwin_lat_edge_lo) / darwin_lat_res).astype(np.int64)
        lon_idx = np.floor((lons - darwin_lon_edge_lo) / darwin_lon_res).astype(np.int64)
        lat_idx = np.minimum(lat_idx, n_dlat - 1)
        lon_idx = np.minimum(lon_idx, n_dlon - 1)
        in_b = (lat_idx >= 0) & (lon_idx >= 0)
        lat_idx, lon_idx, poc = lat_idx[in_b], lon_idx[in_b], poc[in_b]
        sum_grid = np.zeros((n_dlat, n_dlon), dtype=np.float64)
        cnt_grid = np.zeros((n_dlat, n_dlon), dtype=np.int64)
        np.add.at(sum_grid, (lat_idx, lon_idx), poc)
        np.add.at(cnt_grid, (lat_idx, lon_idx), 1)
        target = np.full((n_dlat, n_dlon), np.nan, dtype=np.float32)
        nz = cnt_grid > 0
        target[nz] = (sum_grid[nz] / cnt_grid[nz]).astype(np.float32)
        return target, nz

    geotraces_poc_target_np, geotraces_poc_mask_np = bin_poc_to_grid(poc_keep)
    n_geo_poc_subsurface = int(geotraces_poc_mask_np.sum())
    poc_finite_vals = geotraces_poc_target_np[geotraces_poc_mask_np]
    print(f"  GEOTRACES POC subsurface bins: {n_geo_poc_subsurface} "
          f"(range [{poc_finite_vals.min():.3g}, {poc_finite_vals.max():.3g}] mmol/m^3)")


# ============================== Ocean mask ================================

full_ocean_mask = (
    np.isfinite(sst) & np.isfinite(mld) & np.isfinite(wind) & np.isfinite(sss)
    & np.isfinite(pco2_atm_field) & np.isfinite(co2_flux_obs)
    & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
    & np.isfinite(dic_binned) & np.isfinite(alk_binned)
)
for chl_arr in chl_per_pft.values():
    full_ocean_mask = full_ocean_mask & np.isfinite(chl_arr)

# Block-CV split (default: TRAIN_LON_FRAC=1.0 = no split, train_mask == full).
if TRAIN_LON_FRAC < 1.0:
    H_total, W_total = full_ocean_mask.shape
    train_cols_end = int(round(W_total * TRAIN_LON_FRAC))
    lon_filter = np.zeros_like(full_ocean_mask)
    lon_filter[:, :train_cols_end] = True
    test_lon_filter = ~lon_filter
    train_mask = full_ocean_mask & lon_filter
    test_mask = full_ocean_mask & test_lon_filter
    print(f"BLOCK-CV: TRAIN_LON_FRAC={TRAIN_LON_FRAC}  train cells={int(train_mask.sum())} (west cols 0..{train_cols_end-1})  test cells={int(test_mask.sum())} (east cols {train_cols_end}..{W_total-1})")
else:
    train_mask = full_ocean_mask
    test_mask = np.zeros_like(full_ocean_mask)

# ocean_mask = the mask used for loss computation (=train_mask under block-CV).
ocean_mask = train_mask
n_ocean = int(ocean_mask.sum())
geotraces_loss_mask_np = geotraces_mask_np & ocean_mask
geotraces_sub_loss_mask_np = geotraces_sub_mask_np & ocean_mask
n_geo_surface_in_ocean = int(geotraces_loss_mask_np.sum())
n_geo_sub_in_ocean = int(geotraces_sub_loss_mask_np.sum())
print(f"Darwin ocean cells: {n_ocean};  GEOTRACES in-ocean surface={n_geo_surface_in_ocean}, "
      f"subsurface={n_geo_sub_in_ocean}")


# ============================== Tensors ===================================

def normalize_covariate(arr, mask):
    o = arr[mask]
    return np.where(mask, (arr - o.mean()) / max(o.std(), 1e-6), 0.0).astype(np.float32)


sst_norm = normalize_covariate(sst, ocean_mask)
env_1ch = torch.tensor(sst_norm, dtype=torch.float32).unsqueeze(0).to(device)  # [1, H, W]
mask_dev = torch.tensor(ocean_mask, dtype=torch.bool).to(device)               # [H, W]
H, W = env_1ch.shape[1], env_1ch.shape[2]
mask_f = mask_dev.to(torch.float32)
n_ocean_f = mask_f.sum()

# Literature-default IC values (mmol/m^3 for tracers, mg/m^3 for Chl).
# Order matches the state vector layout in carroll6_5pft_2layer.py:
#   L1: DFe_1, P_diatom, P_lge, P_syn, P_proLL, P_proHL, POC_1, PIC_1, DIC_1, ALK_1
#   L2: DFe_2, POC_2, PIC_2, DIC_2, ALK_2
LIT_IC = [
    5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
    0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
    5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
]
state0_hw = torch.tensor(LIT_IC, dtype=torch.float32).reshape(N_TRACERS_2LAYER, 1, 1).expand(N_TRACERS_2LAYER, H, W).clone()

if USE_DARWIN_IC:
    if not DARWIN_IC_CACHE_PATH.is_file():
        raise FileNotFoundError(
            f"DARWIN_IC=1 but cache not found at {DARWIN_IC_CACHE_PATH}. "
            f"Run `python scripts/build_darwin_ic_cache.py` first."
        )
    print(f"Loading Darwin v5 ICs from {DARWIN_IC_CACHE_PATH}")
    _ic = np.load(DARWIN_IC_CACHE_PATH)
    # Inorganic L1 / L2 overrides; phyto biomass stays literature.
    # Map: (state_index, cache_key)
    _ic_overrides = [
        (I_DFE_1, "FeT_L1"),
        (I_POC_1, "POC_L1"),
        (I_PIC_1, "PIC_L1"),
        (I_DIC_1, "DIC_L1"),
        (I_ALK_1, "ALK_L1"),
        (I_DFE_2, "FeT_L2"),
        (I_POC_2, "POC_L2"),
        (I_PIC_2, "PIC_L2"),
        (I_DIC_2, "DIC_L2"),
        (I_ALK_2, "ALK_L2"),
    ]
    for state_idx, key in _ic_overrides:
        field = _ic[key]  # shape (n_lat, n_lon) = (H, W)
        if field.shape != (H, W):
            raise ValueError(
                f"Darwin IC field {key!r} has shape {field.shape}, expected ({H}, {W}). "
                f"AOI mismatch — rebuild the cache."
            )
        # Replace NaN with literature default for that tracer (defensive).
        field_safe = np.where(np.isfinite(field), field, LIT_IC[state_idx]).astype(np.float32)
        # Clip tiny negatives from MITgcm advection overshoots.
        if state_idx in (I_DFE_1, I_DFE_2, I_POC_1, I_POC_2, I_PIC_1, I_PIC_2):
            field_safe = np.clip(field_safe, a_min=1e-10, a_max=None)
        state0_hw[state_idx] = torch.tensor(field_safe, dtype=torch.float32)
    print(f"  applied {len(_ic_overrides)} per-cell IC overrides (phyto biomass kept literature)")
else:
    print("Using literature-default ICs (DARWIN_IC=0)")

# Expand to [15, N_seeds, H, W]
state0_single = state0_hw.unsqueeze(1).expand(N_TRACERS_2LAYER, N_SEEDS, H, W).contiguous().to(device)

T_dev = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32)).to(device)
S_dev = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32)).to(device)
wind_dev = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32)).to(device)
pco2_atm_dev = torch.tensor(
    np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)
).to(device)
bounds_dev = PARAM_BOUNDS.to(device)

geotraces_target_t = torch.tensor(
    np.where(geotraces_loss_mask_np, geotraces_target_np, 0.0).astype(np.float32)
).to(device)
geotraces_mask_t = torch.tensor(geotraces_loss_mask_np, dtype=torch.bool).to(device)
geo_mask_f = geotraces_mask_t.to(torch.float32)
n_geo_surf_f = geo_mask_f.sum().clamp(min=1.0)

geotraces_sub_target_t = torch.tensor(
    np.where(geotraces_sub_loss_mask_np, geotraces_sub_target_np, 0.0).astype(np.float32)
).to(device)
geotraces_sub_mask_t = torch.tensor(geotraces_sub_loss_mask_np, dtype=torch.bool).to(device)
geo_sub_mask_f = geotraces_sub_mask_t.to(torch.float32)
n_geo_sub_f = geo_sub_mask_f.sum().clamp(min=1.0)

# GEOTRACES POC subsurface tensors (v2.8 real-obs swap).
geotraces_poc_target_t = None
geotraces_poc_mask_t = None
geo_poc_mask_f = None
n_geo_poc_f = None
n_geo_poc_in_ocean = 0
if GEOTRACES_POC_SUB_W > 0 and geotraces_poc_target_np is not None:
    geotraces_poc_loss_mask_np = geotraces_poc_mask_np & ocean_mask
    n_geo_poc_in_ocean = int(geotraces_poc_loss_mask_np.sum())
    print(f"GEOTRACES POC in-ocean subsurface bins: {n_geo_poc_in_ocean}")
    geotraces_poc_target_t = torch.tensor(
        np.where(geotraces_poc_loss_mask_np, geotraces_poc_target_np, 0.0).astype(np.float32)
    ).to(device)
    geotraces_poc_mask_t = torch.tensor(geotraces_poc_loss_mask_np, dtype=torch.bool).to(device)
    geo_poc_mask_f = geotraces_poc_mask_t.to(torch.float32)
    n_geo_poc_f = geo_poc_mask_f.sum().clamp(min=1.0)


def to_z_target(np_field):
    clean = np.where(ocean_mask, np_field, 1.0).astype(np.float32)
    t = torch.tensor(clean, dtype=torch.float32).to(device)
    o = t[mask_dev]
    mean = o.mean()
    std = o.std().clamp(min=1e-6)
    return (t - mean) / std


fet_z = to_z_target(fet_binned)
poc_z = to_z_target(poc_binned)
pic_z = to_z_target(pic_binned)
dic_z = to_z_target(dic_binned)
alk_z = to_z_target(alk_binned)
co2_flux_z = to_z_target(co2_flux_obs)
chl_z = {f"Chl{i}": to_z_target(chl_per_pft[f"Chl{i}"]) for i in range(1, 6)}

# v2.8: build POC_L2 z-score target from the Darwin IC cache (re-uses the
# same depth-averaged POC field the IC pipeline produces).
poc_l2_z = None
if POC_SUB_W > 0:
    if not DARWIN_IC_CACHE_PATH.is_file():
        raise FileNotFoundError(
            f"POC_SUB_W={POC_SUB_W} but cache not found at {DARWIN_IC_CACHE_PATH}. "
            f"Run `python scripts/build_darwin_ic_cache.py` first."
        )
    print(f"Loading POC_L2 target from {DARWIN_IC_CACHE_PATH.name} (POC_SUB_W={POC_SUB_W})")
    _ic_for_target = np.load(DARWIN_IC_CACHE_PATH)
    _poc_l2_target = _ic_for_target["POC_L2"]
    if _poc_l2_target.shape != (H, W):
        raise ValueError(
            f"POC_L2 target shape {_poc_l2_target.shape} != ({H}, {W}); AOI mismatch"
        )
    poc_l2_z = to_z_target(_poc_l2_target.astype(np.float32))


# ============================== Networks (one per seed) ===================

print(f"\nBuilding {N_SEEDS} DINN networks (one per seed)...")
nets: list[DINN] = []
for s in SEEDS:
    torch.manual_seed(s)
    n = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
    nets.append(n)
# Single optimizer over all networks' params -- each network's params are
# distinct nn.Parameter tensors, so Adam's per-parameter moments evolve
# independently per seed.
all_params = []
for n in nets:
    all_params.extend(n.parameters())
optimizer = torch.optim.Adam(all_params, lr=5e-3)

# torch.compile strategy: compile the per-STEP function (fixed shape,
# no Python loop) and call it from a Python loop. Compiling the full
# integrator with its 200-step Python loop hangs at the batched shape on
# Windows (observed: both ``reduce-overhead`` and ``default`` modes lock
# up for >10 min with 0 % GPU utilisation while RAM climbs into the
# multi-GB range). Compiling just the step bypasses that whole class of
# loop-unrolling pathologies and gives the per-step kernel-fusion win
# without the up-front compile stall.
_COMPILE_STEP = os.environ.get("TORCH_COMPILE_BATCHED", "1") == "1"
if _COMPILE_STEP:
    try:
        _compiled_step = torch.compile(carroll6_5pft_2layer_step, mode="default")
        print("torch.compile applied to per-step function (mode='default').")
    except Exception as e:
        print(f"torch.compile failed ({e}); falling back to eager per-step.")
        _compiled_step = carroll6_5pft_2layer_step
else:
    _compiled_step = carroll6_5pft_2layer_step
    print("torch.compile DISABLED (eager per-step).")


def _integrate(state0, params, dt, n_steps, T, S, wind, pco2_atm,
               h1=None, h2=None, kz_m2_per_day=None, r_remin=None):
    """Lightweight wrapper that calls the (optionally compiled) step in a
    Python loop. Mirrors the integrate-without-snapshots branch of
    ``carroll6_5pft_2layer_integrate`` so the rest of this script can
    swap freely between the wrapper and the original.
    """
    # Use module defaults if any of the optional knobs are not provided.
    from darwindiff.carroll6_5pft_2layer import H1, H2, KZ_M2_PER_DAY, R_REMIN
    if h1 is None: h1 = H1
    if h2 is None: h2 = H2
    if kz_m2_per_day is None: kz_m2_per_day = KZ_M2_PER_DAY
    if r_remin is None: r_remin = R_REMIN

    state = state0
    for _ in range(n_steps):
        state = _compiled_step(state, params, dt, T, S, wind, pco2_atm,
                               h1, h2, kz_m2_per_day, r_remin)
    return state


# ============================== Batched loss helpers ======================
#
# Per-seed z-score mean/std computed in vectorised form over the seed dim.
# Matches the single-seed term() semantics: mean over ocean-masked cells,
# std with Bessel correction (PyTorch torch.std default).

n_ocean_int = int(n_ocean_f.item())  # captured once at startup, used as scalar
bessel_div = max(n_ocean_int - 1, 1)


def term_batched(pred_b: torch.Tensor, target_z: torch.Tensor) -> torch.Tensor:
    """Z-score loss per seed.

    Args:
        pred_b: shape ``[N_seeds, H, W]``.
        target_z: shape ``[H, W]``.

    Returns:
        Per-seed loss, shape ``[N_seeds]``.
    """
    pred_m = pred_b * mask_f[None]
    sums = pred_m.flatten(1).sum(dim=1)  # [N_seeds]
    means = sums / n_ocean_f
    diff = (pred_b - means[:, None, None]) * mask_f[None]
    var = (diff ** 2).flatten(1).sum(dim=1) / bessel_div
    stds = var.sqrt().clamp(min=1e-6)
    pred_z = (pred_b - means[:, None, None]) / stds[:, None, None]
    residual = (pred_z - target_z[None]) * mask_f[None]
    return (residual ** 2).flatten(1).sum(dim=1) / n_ocean_f


# ============================== Training ==================================

print(f"\n=== Batched training: N_SEEDS={N_SEEDS}, 2-layer 15-tracer, "
      f"PINN drift w={PINN_W}, GEO surf w={GEOTRACES_W}, GEO sub w={GEOTRACES_SUB_W} ===")

t0 = time.time()
# Per-seed loss histories on GPU. Shape [N_EPOCHS, N_SEEDS].
loss_history = torch.full((N_EPOCHS, N_SEEDS), float("nan"), dtype=torch.float32, device=device)
geo_surface_history = torch.full((N_EPOCHS, N_SEEDS), float("nan"), dtype=torch.float32, device=device)
geo_sub_history = torch.full((N_EPOCHS, N_SEEDS), float("nan"), dtype=torch.float32, device=device)

for epoch in range(N_EPOCHS):
    optimizer.zero_grad()

    # N forward passes through N networks. The network is tiny (16-dim
    # hidden, 6 outputs over 21x51 input) so sequential is fine here;
    # the integrator is what dominates wall-clock and that runs batched.
    per_seed_params = [bounded_params(net(env_1ch), bounds_dev) for net in nets]
    # Each is [6, H, W]. Stack along a new dim 1 -> [6, N_seeds, H, W].
    params_b = torch.stack(per_seed_params, dim=1)

    state = _integrate(
        state0_single, params_b, DT, N_STEPS,
        T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev,
    )
    # state: [15, N_seeds, H, W]
    dfe1 = state[I_DFE_1]      # [N_seeds, H, W]
    dfe2 = state[I_DFE_2]
    p_diatom = state[I_DIATOM]
    p_lge = state[I_LGE]
    p_syn = state[I_SYN]
    p_proLL = state[I_PROLL]
    p_proHL = state[I_PROHL]
    poc = state[I_POC_1]
    pic = state[I_PIC_1]
    dic = state[I_DIC_1]
    alk = state[I_ALK_1]

    carb_final = solve_carbonate(dic, alk, T_dev[None], S_dev[None])
    co2_flux_pred = co2_flux(carb_final["pCO2"], pco2_atm_dev[None], wind_dev[None],
                             T_dev[None], S_dev[None])  # [N_seeds, H, W]

    # 11-target z-score loss (per seed)
    z_term = (
        FET_W * term_batched(dfe1, fet_z)
        + term_batched(p_diatom, chl_z["Chl1"])
        + term_batched(p_lge,    chl_z["Chl2"])
        + term_batched(p_syn,    chl_z["Chl3"])
        + term_batched(p_proLL,  chl_z["Chl4"])
        + term_batched(p_proHL,  chl_z["Chl5"])
        + term_batched(poc,      poc_z)
        + term_batched(pic,      pic_z)
        + term_batched(dic,      dic_z)
        + term_batched(alk,      alk_z)
        + term_batched(co2_flux_pred, co2_flux_z)
    ) / (FET_W + 10.0)  # [N_seeds]

    # PINN drift loss (per seed)
    if PINN_W > 0:
        alpfe_b   = params_b[0]   # [N_seeds, H, W]
        scav_rat_b = params_b[1]
        mu_proHL_b = params_b[2]
        mu_lge_b   = params_b[3]
        f_fe = state[I_DFE_1] / (state[I_DFE_1] + K_FE)
        growth_total = (
            MU_DEFAULT_DIATOM * f_fe * state[I_DIATOM]
            + mu_lge_b * f_fe * state[I_LGE]
            + MU_DEFAULT_SYN * f_fe * state[I_SYN]
            + MU_DEFAULT_PROLL * f_fe * state[I_PROLL]
            + mu_proHL_b * f_fe * state[I_PROHL]
        )
        iron_source = alpfe_b * PHI_DUST
        iron_sink = scav_rat_b * 86400.0 * state[I_DFE_1] * state[I_POC_1] + Q_FE * growth_total
        if PINN_TYPE == "drift":
            dDFe_dt = iron_source - iron_sink
            rel_rate = dDFe_dt / state[I_DFE_1].clamp(min=1e-10)
            l_pinn = ((rel_rate ** 2) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        else:
            iron_norm = (iron_source * mask_f[None]).abs().flatten(1).sum(dim=1).clamp(min=1e-12)
            iron_norm = iron_norm / n_ocean_f
            imbalance = (iron_source - iron_sink) / iron_norm[:, None, None]
            l_pinn = ((imbalance ** 2) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        z_term = z_term + PINN_W * l_pinn

    # Surface GEOTRACES loss (per seed)
    l_geo_surf = None
    if GEOTRACES_W > 0 and n_geo_surface_in_ocean > 0:
        residual = (dfe1 - geotraces_target_t[None]) * geo_mask_f[None]
        geo_scale = (geotraces_target_t[geotraces_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geo_surf = (residual ** 2).flatten(1).sum(dim=1) / n_geo_surf_f / geo_scale
        z_term = z_term + GEOTRACES_W * l_geo_surf

    # Subsurface GEOTRACES loss (per seed)
    l_geo_sub = None
    if GEOTRACES_SUB_W > 0 and n_geo_sub_in_ocean > 0:
        residual = (dfe2 - geotraces_sub_target_t[None]) * geo_sub_mask_f[None]
        sub_scale = (geotraces_sub_target_t[geotraces_sub_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geo_sub = (residual ** 2).flatten(1).sum(dim=1) / n_geo_sub_f / sub_scale
        z_term = z_term + GEOTRACES_SUB_W * l_geo_sub

    # v2.8: subsurface POC z-score loss (per seed). Constrains the
    # integrator's L2 POC trajectory directly, closing the dynamical
    # degeneracy scav_rat sits in.
    l_poc_sub = None
    if POC_SUB_W > 0 and poc_l2_z is not None:
        l_poc_sub = term_batched(state[I_POC_2], poc_l2_z)
        z_term = z_term + POC_SUB_W * l_poc_sub

    # v2.8 + GEOTRACES POC swap: absolute-units MSE on real POC obs at
    # the populated subsurface bins. Analogous to the iron GEOTRACES_SUB
    # loss above; uses POC_LPT + POC_SPT (sum), unit-converted to mmol/m^3.
    l_geo_poc = None
    if GEOTRACES_POC_SUB_W > 0 and n_geo_poc_in_ocean > 0:
        residual = (state[I_POC_2] - geotraces_poc_target_t[None]) * geo_poc_mask_f[None]
        poc_scale = (geotraces_poc_target_t[geotraces_poc_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geo_poc = (residual ** 2).flatten(1).sum(dim=1) / n_geo_poc_f / poc_scale
        z_term = z_term + GEOTRACES_POC_SUB_W * l_geo_poc

    # Sum across seeds so each seed's gradient routes to its own net's params.
    total_loss = z_term.sum()
    total_loss.backward()
    optimizer.step()

    with torch.no_grad():
        loss_history[epoch] = z_term.detach()
        if l_geo_surf is not None:
            geo_surface_history[epoch] = l_geo_surf.detach()
        if l_geo_sub is not None:
            geo_sub_history[epoch] = l_geo_sub.detach()

    if (epoch + 1) % 250 == 0 or epoch + 1 == N_EPOCHS:
        mean_l = float(z_term.detach().mean().item())
        max_l = float(z_term.detach().max().item())
        min_l = float(z_term.detach().min().item())
        print(f"  epoch {epoch+1:4d}  per-seed loss: min={min_l:.3e}  "
              f"mean={mean_l:.3e}  max={max_l:.3e}")

if device == "cuda":
    torch.cuda.synchronize()
elapsed = time.time() - t0
print(f"Done in {elapsed:.0f}s ({elapsed/N_SEEDS:.1f}s amortized per seed)")


# ============================== Recovery analysis =========================

param_names = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
carroll_published = CARROLL_VALUES.numpy()

# Per-seed recovered parameter means (ocean-cell mean).
print("\n=== Recovered Carroll-6 per seed ===")
print(f"{'Seed':<6s} {'Param':<12s} {'Recovered':>12s} {'Carroll':>12s} "
      f"{'|d|/Carroll':>12s} {'Band':<12s}")

all_results = []
with torch.no_grad():
    per_seed_params_dev = [bounded_params(net(env_1ch), bounds_dev) for net in nets]
    params_b_final = torch.stack(per_seed_params_dev, dim=1)  # [6, N_seeds, H, W]

    state_final = _integrate(
        state0_single, params_b_final, DT, N_STEPS,
        T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev,
    )

    # Build test_mask tensor for block-CV evaluation (if enabled).
    test_mask_dev = (
        torch.tensor(test_mask, dtype=torch.bool).to(device)
        if TRAIN_LON_FRAC < 1.0 else None
    )

    for seed_idx, seed in enumerate(SEEDS):
        param_means = []           # over train cells (= ocean_mask)
        test_param_means = []      # over test cells (block-CV); empty if no split
        for i in range(6):
            p_train = params_b_final[i, seed_idx][mask_dev]
            param_means.append(float(p_train.mean().cpu().numpy()))
            if test_mask_dev is not None and int(test_mask_dev.sum()) > 0:
                p_test = params_b_final[i, seed_idx][test_mask_dev]
                test_param_means.append(float(p_test.mean().cpu().numpy()))
        dfe1_final_mean = float(state_final[I_DFE_1, seed_idx][mask_dev].mean().item())
        dfe2_final_mean = float(state_final[I_DFE_2, seed_idx][mask_dev].mean().item())

        # Per-seed geo-loss initial/final (NaN-safe — replaced with None when
        # the loss term is disabled). Matches the single-seed runner's JSON
        # schema so the downstream aggregator sees the same fields whichever
        # runner produced the file.
        gs_init = float(geo_surface_history[0, seed_idx].item())
        gs_final = float(geo_surface_history[-1, seed_idx].item())
        gsub_init = float(geo_sub_history[0, seed_idx].item())
        gsub_final = float(geo_sub_history[-1, seed_idx].item())

        result = {
            "seed": seed,
            "geotraces_w": GEOTRACES_W,
            "geotraces_sub_w": GEOTRACES_SUB_W,
            "sub_depth_min_m": SUB_DEPTH_MIN,
            "sub_depth_max_m": SUB_DEPTH_MAX,
            "pinn_w": PINN_W,
            "pinn_type": PINN_TYPE,
            "use_darwin_ic": USE_DARWIN_IC,
            "poc_sub_w": POC_SUB_W,
            "geotraces_poc_sub_w": GEOTRACES_POC_SUB_W,
            "n_geo_poc_subsurface_cells": n_geo_poc_in_ocean,
            "aoi_key": AOI_KEY,
            "aoi_name": AOI.name,
            "fet_w": FET_W,
            "n_geo_surface_cells": n_geo_surface_in_ocean,
            "n_geo_sub_cells": n_geo_sub_in_ocean,
            "elapsed_s_total_batch": elapsed,
            "n_seeds_in_batch": N_SEEDS,
            "loss_initial": float(loss_history[0, seed_idx].item()),
            "loss_final": float(loss_history[-1, seed_idx].item()),
            "geo_surface_loss_initial": None if not np.isfinite(gs_init) else gs_init,
            "geo_surface_loss_final": None if not np.isfinite(gs_final) else gs_final,
            "geo_sub_loss_initial": None if not np.isfinite(gsub_init) else gsub_init,
            "geo_sub_loss_final": None if not np.isfinite(gsub_final) else gsub_final,
            "dfe1_pred_mean_mmol_m3": dfe1_final_mean,
            "dfe2_pred_mean_mmol_m3": dfe2_final_mean,
            "params": {},
        }
        n_cal_grade = 0
        n_excellent = 0
        for name, rec, pub in zip(param_names, param_means, carroll_published):
            rel = abs(rec - float(pub)) / abs(float(pub))
            band = band_of(rel)
            if band == "Excellent":
                n_cal_grade += 1
                n_excellent += 1
            elif band == "Cal-grade":
                n_cal_grade += 1
            print(f"{seed:<6d} {name:<12s} {rec:>12.4e} {float(pub):>12.4e} "
                  f"{rel:>12.4f} {band:<12s}")
            entry = {
                "recovered": float(rec),
                "carroll_published": float(pub),
                "abs_rel_offset": float(rel),
                "band": band,
            }
            # Block-CV: per-parameter test-cell mean + offset/band, for spatial-
            # generalization verdicts.
            if test_param_means:
                t_rec = test_param_means[param_names.index(name)]
                t_rel = abs(t_rec - float(pub)) / abs(float(pub))
                t_band = band_of(t_rel)
                entry["test_recovered"] = float(t_rec)
                entry["test_abs_rel_offset"] = float(t_rel)
                entry["test_band"] = t_band
            result["params"][name] = entry
        result["n_cal_grade"] = n_cal_grade
        result["n_excellent"] = n_excellent
        if TRAIN_LON_FRAC < 1.0:
            result["train_lon_frac"] = TRAIN_LON_FRAC
        print(f"       -> {n_cal_grade}/6 cal-grade ({n_excellent} Excellent)")
        if test_param_means:
            n_cg_test = sum(1 for name, t_rec in zip(param_names, test_param_means)
                            if band_of(abs(t_rec - float(carroll_published[param_names.index(name)])) /
                                       abs(float(carroll_published[param_names.index(name)]))) in ("Cal-grade", "Excellent"))
            print(f"       -> TEST cells: {n_cg_test}/6 cal-grade")
        all_results.append(result)

# Write one JSON per seed (matching the single-seed runner's naming).
# Default behavior: write JSONs.
# Set NB23_SKIP_JSON_WRITE=1 (smoke tests) to skip the write step --
# protects committed result JSONs from being clobbered by short runs.
SKIP_JSON_WRITE = os.environ.get("NB23_SKIP_JSON_WRITE", "0") == "1"
out_dir = Path(__file__).resolve().parent
if SKIP_JSON_WRITE:
    print(f"\nNB23_SKIP_JSON_WRITE=1: skipping JSON write for {len(all_results)} results.")
else:
    ic_tag = f"_{DARWIN_IC_TAG}" if USE_DARWIN_IC else ""
    poc_tag = f"_pocsubW{POC_SUB_W}" if POC_SUB_W > 0 else ""
    aoi_tag = f"_{AOI_KEY}" if AOI_KEY != "eqpac" else ""
    cv_tag = f"_blockcvW{TRAIN_LON_FRAC}" if TRAIN_LON_FRAC < 1.0 else ""
    geo_poc_tag = f"_geopocW{GEOTRACES_POC_SUB_W}" if GEOTRACES_POC_SUB_W > 0 else ""
    for r in all_results:
        out = out_dir / (
            f"run_v2.7_multilayer_result_seed{r['seed']}"
            f"_surf{GEOTRACES_W}"
            f"_sub{GEOTRACES_SUB_W}"
            f"_pinn{PINN_W}"
            f"{ic_tag}"
            f"{poc_tag}"
            f"{aoi_tag}"
            f"{cv_tag}"
            f"{geo_poc_tag}.json"
        )
        existed = out.is_file()
        with out.open("w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, allow_nan=False)
        suffix = " (overwrote existing)" if existed else ""
        print(f"  wrote {out.name}{suffix}")

print(f"\nBatch summary: {N_SEEDS} seeds in {elapsed:.0f}s "
      f"({elapsed/N_SEEDS:.1f}s amortized per seed).")
