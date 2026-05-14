# -*- coding: utf-8 -*-
"""Quick GEOTRACES + Darwin hybrid experiment to break the alpfe-scav_rat degeneracy.

Standalone training script (NOT a notebook builder) to verify the
hypothesis fast: does adding GEOTRACES IDP2025 dissolved iron as an
absolute-units (mmol/m^3) loss term to the v2.4 PINN drift w=3.0
winning configuration unstick alpfe?

Mirrors nb29 (v2.4 PINN drift w=3.0) exactly except for the new
GEOTRACES iron loss term added at the bottom of the per-epoch loss.

Run:
    python scripts/run_geotraces_hybrid_quick.py

Expected wall-clock: ~5 min on RTX 5090 Laptop (5-PFT 1500-epoch
training, same as nb29).

Configuration via env vars (defaults match nb29 winner + GEOTRACES_W=1.0):
    GEOTRACES_W       weight on the new GEOTRACES iron MSE term (default 1.0)
    GEOTRACES_DATA_ROOT  where the IDP2025 NetCDF lives (default D:\\geotraces)
    NB23_SEED         training seed (default 0)
    NB23_PINN_WEIGHT  PINN drift weight (default 3.0, the nb29 winner)
    NB23_FET_WEIGHT   z-scored FeT weight (default 1.0)
    DARWIN_DATA_ROOT  Darwin v05 data root (default D:\\ecco_darwin_v5)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

# Force stdout to UTF-8 on Windows so Δ / Greek letters don't break the
# end-of-run summary table.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

import numpy as np
import torch
import xarray as xr

# Ensure src/ on sys.path so the script works without `pip install -e .`.
_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate
from darwindiff.carroll6 import (
    CARROLL_VALUES,
    PARAM_BOUNDS,
    PHI_DUST,
    Q_FE,
    bounded_params,
)
from darwindiff.carroll6_5pft import (
    I_ALK,
    I_DFE,
    I_DIATOM,
    I_DIC,
    I_LGE,
    I_PIC,
    I_POC,
    I_PROHL,
    I_PROLL,
    I_SYN,
    MU_DEFAULT_DIATOM,
    MU_DEFAULT_PROLL,
    MU_DEFAULT_SYN,
    N_TRACERS,
    carroll6_5pft_integrate,
)
from darwindiff.diagnostics import band_of
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    open_bin_average,
    subset_aoi,
    time_mean,
)
from darwindiff.geotraces_loader import (
    bin_to_grid as geotraces_bin_to_grid,
    open_geotraces_bottle,
    subset_aoi_geotraces,
    to_mmol_per_m3,
)
from darwindiff.llc270_loader import bin_native_tracer_to_1deg
from darwindiff.networks import DINN


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

SEED = int(os.environ.get("NB23_SEED", "0"))
FET_W = float(os.environ.get("NB23_FET_WEIGHT", "1.0"))
RAW_FET_W = float(os.environ.get("NB23_RAW_FET_WEIGHT", "0.0"))
PINN_W = float(os.environ.get("NB23_PINN_WEIGHT", "3.0"))
PINN_TYPE = os.environ.get("NB23_PINN_TYPE", "drift").lower()
GEOTRACES_W = float(os.environ.get("GEOTRACES_W", "1.0"))

DT = 0.25
N_STEPS = 200
N_EPOCHS = int(os.environ.get("NB23_N_EPOCHS", "1500"))
H_MLD = 50.0
K_FE = 5.0e-5

AOI = EQUATORIAL_PACIFIC_AOI
print(f"AOI: {AOI.name} ({AOI.lat_min}-{AOI.lat_max} N, {AOI.lon_min}-{AOI.lon_max} E)")
print(f"Config: seed={SEED}, fet_w={FET_W}, raw_fet_w={RAW_FET_W}, "
      f"pinn_w={PINN_W} ({PINN_TYPE}), geotraces_w={GEOTRACES_W}")
print()


# ============================== Darwin targets (with on-disk cache) =======
#
# LLC270 native loading + xmitgcm decoding takes ~60 s. Cache the
# AOI-binned 1-deg targets + bin_average covariates as a single .pt
# tensor file. Cache key includes the AOI bounds so different AOIs
# don't collide. Shared with run_v2.7_multilayer_quick.py.

CACHE_DIR = DATA_ROOT / "cache"
CACHE_PATH = CACHE_DIR / f"eqpac_targets_{AOI.name.replace(' ', '_').lower()}.pt"


def _build_eqpac_targets() -> dict:
    """Slow path: load bin_average + 5 LLC270 native variables."""
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
    """Fast path: torch.load the .pt cache if AOI matches; else rebuild."""
    expected_bounds = (AOI.lat_min, AOI.lat_max, AOI.lon_min, AOI.lon_max)
    if CACHE_PATH.is_file():
        try:
            cached = torch.load(CACHE_PATH, map_location="cpu", weights_only=False)
            if (cached.get("aoi_name") == AOI.name
                    and cached.get("aoi_bounds") == expected_bounds):
                print(f"Loaded target cache from {CACHE_PATH} "
                      f"(skipping ~60 s of LLC270 binning).")
                return cached
            print(f"  cache AOI mismatch ({cached.get('aoi_name')!r} vs "
                  f"{AOI.name!r}); rebuilding...")
        except Exception as e:
            print(f"  cache load failed ({e}); rebuilding...")

    data = _build_eqpac_targets()
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(data, CACHE_PATH)
        print(f"  saved target cache to {CACHE_PATH}")
    except Exception as e:
        print(f"  [warn] could not save cache to {CACHE_PATH}: {e}")
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
darwin_lats_cached = _targets["darwin_lats"]
darwin_lons_cached = _targets["darwin_lons"]
print(f"  bin_average shape: {sst.shape}")


# ============================== GEOTRACES iron ============================

print(f"Loading GEOTRACES IDP2025 from {GEOTRACES_NC}...")
geotraces_ds = open_geotraces_bottle(GEOTRACES_NC)
geotraces_sub = subset_aoi_geotraces(geotraces_ds, AOI)
print(f"  Eq Pac stations: {geotraces_sub.sizes['N_STATIONS']}")

# Bin GEOTRACES samples directly onto Darwin's exact grid (cell centers
# at integer degrees, NOT the half-integer convention bin_to_grid uses).
# Reuses subset_aoi_geotraces output and the QC + depth filters but
# inlines a custom binning so the output shape matches fet_binned exactly.
darwin_lats = darwin_lats_cached   # e.g. -5, -4, ..., 15 (21 cells)
darwin_lons = darwin_lons_cached   # e.g. -160, ..., -110 (51 cells)
n_dlat = len(darwin_lats)
n_dlon = len(darwin_lons)
darwin_lat_res = float(darwin_lats[1] - darwin_lats[0]) if n_dlat > 1 else 1.0
darwin_lon_res = float(darwin_lons[1] - darwin_lons[0]) if n_dlon > 1 else 1.0
# Bin edges at half-integer offsets from the cell centers.
darwin_lat_edge_lo = darwin_lats[0]  - darwin_lat_res / 2.0
darwin_lon_edge_lo = darwin_lons[0]  - darwin_lon_res / 2.0

# Flatten the discrete GEOTRACES samples (replicates the bin_to_grid
# logic but with the Darwin grid as target).
QC_GOOD = (49, 50)  # SeaDataNet ASCII codes for good / probably_good
DEPTH_MAX = 50.0
n_st = geotraces_sub.sizes["N_STATIONS"]
n_sa = geotraces_sub.sizes["N_SAMPLES"]
fe_vals = geotraces_sub.Fe_D_CONC.values
g_lats = np.broadcast_to(geotraces_sub.latitude.values[:, None], (n_st, n_sa)).flatten()
g_lons = np.broadcast_to(geotraces_sub.longitude.values[:, None], (n_st, n_sa)).flatten()
g_depths = geotraces_sub.DEPTH.values.flatten()
g_fe = fe_vals.flatten()
g_qc = geotraces_sub.Fe_D_CONC_qc.values.flatten()
keep = (
    np.isfinite(g_fe) & np.isfinite(g_lats) & np.isfinite(g_lons) & np.isfinite(g_depths)
    & (g_depths <= DEPTH_MAX) & np.isin(g_qc, np.array(QC_GOOD, dtype=g_qc.dtype))
)
g_lats, g_lons, g_fe = g_lats[keep], g_lons[keep], g_fe[keep]
# Convert nmol/kg -> mmol/m^3 (same factor as to_mmol_per_m3).
g_fe_mmol = g_fe * 1025.0 * 1.0e-6
print(f"  Surface QC-good samples: {len(g_fe)}")

# Bin to the Darwin grid.
g_lat_idx = np.floor((g_lats - darwin_lat_edge_lo) / darwin_lat_res).astype(np.int64)
g_lon_idx = np.floor((g_lons - darwin_lon_edge_lo) / darwin_lon_res).astype(np.int64)
g_lat_idx = np.minimum(g_lat_idx, n_dlat - 1)
g_lon_idx = np.minimum(g_lon_idx, n_dlon - 1)
in_bounds = (g_lat_idx >= 0) & (g_lon_idx >= 0)
g_lat_idx, g_lon_idx, g_fe_mmol = (
    g_lat_idx[in_bounds], g_lon_idx[in_bounds], g_fe_mmol[in_bounds],
)
sum_grid = np.zeros((n_dlat, n_dlon), dtype=np.float64)
cnt_grid = np.zeros((n_dlat, n_dlon), dtype=np.int64)
np.add.at(sum_grid, (g_lat_idx, g_lon_idx), g_fe_mmol)
np.add.at(cnt_grid, (g_lat_idx, g_lon_idx), 1)
geotraces_target_np = np.full((n_dlat, n_dlon), np.nan, dtype=np.float32)
nonzero = cnt_grid > 0
geotraces_target_np[nonzero] = (sum_grid[nonzero] / cnt_grid[nonzero]).astype(np.float32)
geotraces_mask_np = nonzero
n_geotraces_cells = int(geotraces_mask_np.sum())
print(f"  Populated bins on Darwin grid (depth <= 50 m, QC=49/50): "
      f"{n_geotraces_cells} of {geotraces_mask_np.size}")
if n_geotraces_cells > 0:
    vals = geotraces_target_np[geotraces_mask_np]
    print(f"  Bin-mean Fe_D range (mmol/m^3): [{vals.min():.3e}, {vals.max():.3e}]")


# ============================== Grid alignment ============================

assert geotraces_target_np.shape == fet_binned.shape, (
    f"GEOTRACES shape {geotraces_target_np.shape} != Darwin shape "
    f"{fet_binned.shape}; AOI grid mismatch (should be impossible after "
    f"inline rebinning above)"
)


# ============================== Ocean mask ================================

ocean_mask = (
    np.isfinite(sst) & np.isfinite(mld) & np.isfinite(wind) & np.isfinite(sss)
    & np.isfinite(pco2_atm_field) & np.isfinite(co2_flux_obs)
    & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
    & np.isfinite(dic_binned) & np.isfinite(alk_binned)
)
for chl_name, chl_arr in chl_per_pft.items():
    ocean_mask = ocean_mask & np.isfinite(chl_arr)
n_ocean = int(ocean_mask.sum())
# GEOTRACES mask is its own — sparser than ocean_mask but a subset.
geotraces_loss_mask_np = geotraces_mask_np & ocean_mask
n_geo_in_ocean = int(geotraces_loss_mask_np.sum())
print(f"Darwin ocean cells: {n_ocean} of {ocean_mask.size}")
print(f"GEOTRACES cells inside ocean mask: {n_geo_in_ocean}")


# ============================== Tensors ===================================

def normalize_covariate(arr, mask):
    o = arr[mask]
    return np.where(mask, (arr - o.mean()) / max(o.std(), 1e-6), 0.0).astype(np.float32)


sst_norm = normalize_covariate(sst, ocean_mask)
env_1ch = torch.tensor(sst_norm, dtype=torch.float32).unsqueeze(0).to(device)
mask_dev = torch.tensor(ocean_mask, dtype=torch.bool).to(device)
H, W = env_1ch.shape[1], env_1ch.shape[2]

state0 = torch.tensor([
    5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
    0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
]).reshape(N_TRACERS, 1, 1).expand(N_TRACERS, H, W).contiguous().to(device)

T_dev = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32)).to(device)
S_dev = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32)).to(device)
wind_dev = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32)).to(device)
pco2_atm_dev = torch.tensor(
    np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)
).to(device)
bounds_dev = PARAM_BOUNDS.to(device)

# GEOTRACES tensors (target in mmol/m^3, mask of populated cells inside ocean).
geotraces_target_t = torch.tensor(
    np.where(geotraces_loss_mask_np, geotraces_target_np, 0.0).astype(np.float32)
).to(device)
geotraces_mask_t = torch.tensor(geotraces_loss_mask_np, dtype=torch.bool).to(device)


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


# ============================== Training ==================================

print(f"\n=== Training: 5-PFT + 11-target z-score + PINN drift w={PINN_W} + "
      f"GEOTRACES iron w={GEOTRACES_W} ({n_geo_in_ocean} cells) ===")
torch.manual_seed(SEED)
net = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=5e-3)

try:
    _integrate = torch.compile(carroll6_5pft_integrate, mode="reduce-overhead")
except Exception:
    _integrate = carroll6_5pft_integrate

t0 = time.time()
# Pre-allocate GPU loss histories so we never sync host<->device in the hot
# loop. ~2 .item() calls per epoch × 1500 epochs = ~3000 GPU syncs would
# otherwise dominate small-grid runs; storing to a pre-allocated GPU tensor
# and bulk-syncing at the end is dramatically cheaper.
NAN_F32 = float("nan")
loss_history = torch.full((N_EPOCHS,), NAN_F32, dtype=torch.float32, device=device)
geo_history = torch.full((N_EPOCHS,), NAN_F32, dtype=torch.float32, device=device)
for epoch in range(N_EPOCHS):
    optimizer.zero_grad()
    params = bounded_params(net(env_1ch), bounds_dev)
    state = _integrate(
        state0, params, DT, N_STEPS,
        T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev, h_mld=H_MLD,
    )
    dfe_pred = state[I_DFE]
    p_diatom_pred = state[I_DIATOM]
    p_lge_pred = state[I_LGE]
    p_syn_pred = state[I_SYN]
    p_proLL_pred = state[I_PROLL]
    p_proHL_pred = state[I_PROHL]
    poc_pred = state[I_POC]
    pic_pred = state[I_PIC]
    dic_pred = state[I_DIC]
    alk_pred = state[I_ALK]
    carb_final = solve_carbonate(dic_pred, alk_pred, T_dev, S_dev)
    co2_flux_pred = co2_flux(carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev)

    def term(pred, target_z):
        ocean = pred[mask_dev]
        pred_z = (pred - ocean.mean()) / ocean.std().clamp(min=1e-6)
        residual = (pred_z - target_z) * mask_dev.to(pred.dtype)
        return (residual ** 2).sum() / mask_dev.sum().to(residual.dtype)

    l_fet = term(dfe_pred, fet_z)
    l_chl1 = term(p_diatom_pred, chl_z["Chl1"])
    l_chl2 = term(p_lge_pred, chl_z["Chl2"])
    l_chl3 = term(p_syn_pred, chl_z["Chl3"])
    l_chl4 = term(p_proLL_pred, chl_z["Chl4"])
    l_chl5 = term(p_proHL_pred, chl_z["Chl5"])
    l_poc = term(poc_pred, poc_z)
    l_pic = term(pic_pred, pic_z)
    l_dic = term(dic_pred, dic_z)
    l_alk = term(alk_pred, alk_z)
    l_co2 = term(co2_flux_pred, co2_flux_z)
    loss = (FET_W*l_fet + l_chl1 + l_chl2 + l_chl3 + l_chl4 + l_chl5
            + l_poc + l_pic + l_dic + l_alk + l_co2) / (FET_W + 10.0)

    # v2.3-style raw-FeT magnitude term against Darwin's FeT field (NOT
    # GEOTRACES). Used in combo experiments to test whether two different
    # iron-magnitude pins (Darwin-internal + GEOTRACES-external) jointly
    # constrain alpfe + scav_rat better than either alone.
    if RAW_FET_W > 0:
        fet_raw_target = torch.tensor(fet_binned, dtype=torch.float32).to(device)
        residual_raw = (dfe_pred - fet_raw_target) * mask_dev.to(dfe_pred.dtype)
        fet_obs_scale = (fet_raw_target[mask_dev] ** 2).mean().clamp(min=1e-30)
        l_fet_raw = (residual_raw ** 2).sum() / mask_dev.sum().to(residual_raw.dtype) / fet_obs_scale
        loss = loss + RAW_FET_W * l_fet_raw

    # PINN drift loss (matches nb29 winner config).
    if PINN_W > 0:
        alpfe_p = params[0]
        scav_rat_p = params[1]
        mu_proHL_p = params[2]
        mu_lge_p = params[3]
        K_FE_local = 5.0e-5
        f_fe_final = state[I_DFE] / (state[I_DFE] + K_FE_local)
        growth_total_final = (
            MU_DEFAULT_DIATOM * f_fe_final * state[I_DIATOM]
            + mu_lge_p * f_fe_final * state[I_LGE]
            + MU_DEFAULT_SYN * f_fe_final * state[I_SYN]
            + MU_DEFAULT_PROLL * f_fe_final * state[I_PROLL]
            + mu_proHL_p * f_fe_final * state[I_PROHL]
        )
        iron_source = alpfe_p * PHI_DUST
        iron_sink = scav_rat_p * 86400.0 * state[I_DFE] * state[I_POC] + Q_FE * growth_total_final
        if PINN_TYPE == "drift":
            dDFe_dt = iron_source - iron_sink
            rel_rate = dDFe_dt / state[I_DFE].clamp(min=1e-10)
            l_pinn_iron = ((rel_rate ** 2) * mask_dev.to(rel_rate.dtype)).sum() / mask_dev.sum().to(rel_rate.dtype)
        else:
            iron_norm = iron_source[mask_dev].abs().mean().clamp(min=1e-12)
            imbalance = (iron_source - iron_sink) / iron_norm
            l_pinn_iron = ((imbalance ** 2) * mask_dev.to(imbalance.dtype)).sum() / mask_dev.sum().to(imbalance.dtype)
        loss = loss + PINN_W * l_pinn_iron

    # NEW: GEOTRACES iron loss term. Absolute-units MSE on the sparse
    # populated cells, normalized by mean target magnitude (so the weight
    # is order-of-magnitude meaningful).
    l_geotraces = None
    if GEOTRACES_W > 0 and n_geo_in_ocean > 0:
        residual_geo = (dfe_pred - geotraces_target_t) * geotraces_mask_t.to(dfe_pred.dtype)
        geo_scale = (geotraces_target_t[geotraces_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geotraces = (residual_geo ** 2).sum() / geotraces_mask_t.sum().to(residual_geo.dtype) / geo_scale
        loss = loss + GEOTRACES_W * l_geotraces

    loss.backward()
    optimizer.step()

    # Stash the per-epoch losses on GPU (no host sync in the hot loop).
    with torch.no_grad():
        loss_history[epoch] = loss.detach()
        if l_geotraces is not None:
            geo_history[epoch] = l_geotraces.detach()

    if (epoch + 1) % 250 == 0 or epoch + 1 == N_EPOCHS:
        # Single sync per log line.
        l_now = float(loss_history[epoch].item())
        g_now = float(geo_history[epoch].item())
        print(f"  epoch {epoch+1:4d}  loss = {l_now:.4e}  geo = {g_now:.4e}")

if device == "cuda":
    torch.cuda.synchronize()
elapsed = time.time() - t0

# Bulk-sync histories to CPU once.
losses_total = loss_history.cpu().numpy().tolist()
losses_geo = geo_history.cpu().numpy().tolist()
print(f"Done in {elapsed:.0f}s, loss {losses_total[0]:.3e} -> {losses_total[-1]:.3e}")


# ============================== Recovery analysis =========================

with torch.no_grad():
    params_dev = bounded_params(net(env_1ch), bounds_dev)
    # Mean per parameter over ocean cells.
    param_means = []
    for i in range(6):
        p = params_dev[i][mask_dev]
        param_means.append(float(p.mean().cpu().numpy()))

param_names = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
carroll_published = CARROLL_VALUES.numpy()

results = {
    "seed": SEED,
    "geotraces_w": GEOTRACES_W,
    "raw_fet_w": RAW_FET_W,
    "pinn_w": PINN_W,
    "pinn_type": PINN_TYPE,
    "fet_w": FET_W,
    "n_geotraces_cells": n_geo_in_ocean,
    "elapsed_s": elapsed,
    "loss_initial": losses_total[0],
    "loss_final": losses_total[-1],
    # NaN-safe JSON: replace nan with None so json.dump(allow_nan=False)
    # produces spec-compliant output even when GEOTRACES_W=0.
    "geo_loss_initial": (
        None if not np.isfinite(losses_geo[0]) else losses_geo[0]
    ),
    "geo_loss_final": (
        None if not np.isfinite(losses_geo[-1]) else losses_geo[-1]
    ),
    "params": {},
}

print("\n=== Recovered Carroll-6 vs Carroll's published optima ===")
print(f"{'Param':<12s} {'Recovered':>12s} {'Carroll':>12s} {'|d|/Carroll':>12s} {'Band':<12s}")
n_cal_grade = 0
n_excellent = 0
for name, recovered, published in zip(param_names, param_means, carroll_published):
    rel = abs(recovered - float(published)) / abs(float(published))
    band = band_of(rel)
    if band == "Excellent":
        n_cal_grade += 1
        n_excellent += 1
    elif band == "Cal-grade":
        n_cal_grade += 1
    print(f"{name:<12s} {recovered:>12.4e} {float(published):>12.4e} {rel:>12.4f} {band:<12s}")
    results["params"][name] = {
        "recovered": float(recovered),
        "carroll_published": float(published),
        "abs_rel_offset": float(rel),
        "band": band,
    }

results["n_cal_grade"] = n_cal_grade
results["n_excellent"] = n_excellent

print(f"\nVerdict: {n_cal_grade} / 6 calibration-grade ({n_excellent} excellent)")
print(f"vs nb29 seed=0 baseline (PINN drift w=3.0, NO GEOTRACES): 4 / 6 cal-grade")
print(f"vs nb29 seed-averaged baseline (5 seeds): 2 / 6 cal-grade")
print(f"\nGEOTRACES iron loss term: weight={GEOTRACES_W}, populated cells={n_geo_in_ocean}")
print(f"  initial geo loss: {losses_geo[0]:.4e}")
print(f"  final geo loss:   {losses_geo[-1]:.4e}")

# Persist to disk so the result isn't lost if the print step errors.
# Filename includes all knobs that vary across sweep runs so combos
# don't overwrite each other.
results_path = Path(__file__).resolve().parent / (
    f"run_geotraces_hybrid_result_seed{SEED}"
    f"_w{GEOTRACES_W}"
    f"_rawfet{RAW_FET_W}"
    f"_pinn{PINN_W}.json"
)
with results_path.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, allow_nan=False)
print(f"\nResults JSON written to: {results_path}")
