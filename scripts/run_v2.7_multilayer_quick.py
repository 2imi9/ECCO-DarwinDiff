# -*- coding: utf-8 -*-
"""v2.7 multi-layer GEOTRACES experiment — break the alpfe-scav_rat surface degeneracy.

Standalone training script (NOT a notebook builder) to verify the v2.7
hypothesis: does adding a SECOND GEOTRACES loss term on subsurface DFe
(50-1000 m bin-mean) unstick scav_rat from its v2.6 floor at 0.92 off
Carroll?

Mirrors ``run_geotraces_hybrid_quick.py`` exactly except:
- swaps ``carroll6_5pft_integrate`` for ``carroll6_5pft_2layer_integrate``
- 15-tracer state vector (10 L1 + 5 L2) instead of 10
- bins GEOTRACES subsurface (50-1000 m) on Darwin grid as a new target
- adds ``GEOTRACES_SUB_W * L_subsurface_DFe`` loss term
- reads out L1 (state[0:10]) for the existing 11-target z-score + PINN
  drift loss — those terms are byte-identical to v2.6

Run:
    python scripts/run_v2.7_multilayer_quick.py

Expected wall-clock: ~5-7 min on RTX 5090 Laptop.

Configuration via env vars (defaults match v2.6 GEOTRACES_W=0.3 winner +
v2.7 subsurface weight 0.3):
    GEOTRACES_W           weight on surface GEOTRACES iron MSE (default 0.3)
    GEOTRACES_SUB_W       weight on subsurface GEOTRACES iron MSE (default 0.3, NEW)
    GEOTRACES_DATA_ROOT   IDP2025 NetCDF location (default D:\\geotraces)
    NB23_SEED             training seed (default 0)
    NB23_PINN_WEIGHT      PINN drift weight on L1 iron (default 3.0)
    NB23_FET_WEIGHT       z-scored FeT weight (default 1.0)
    DARWIN_DATA_ROOT      Darwin v05 data root (default D:\\ecco_darwin_v5)
    GEOTRACES_SUB_DEPTH_MIN  subsurface bin lower edge in m (default 50)
    GEOTRACES_SUB_DEPTH_MAX  subsurface bin upper edge in m (default 1000)
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

# Force stdout to UTF-8 on Windows so non-ASCII characters don't break printing.
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

import numpy as np
import torch
import xarray as xr

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
    I_DFE_1,
    I_DFE_2,
    I_DIATOM,
    I_DIC_1,
    I_LGE,
    I_PIC_1,
    I_POC_1,
    I_PROHL,
    I_PROLL,
    I_SYN,
    N_TRACERS_2LAYER,
    carroll6_5pft_2layer_integrate,
)
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
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

SEED = int(os.environ.get("NB23_SEED", "0"))
FET_W = float(os.environ.get("NB23_FET_WEIGHT", "1.0"))
PINN_W = float(os.environ.get("NB23_PINN_WEIGHT", "3.0"))
PINN_TYPE = os.environ.get("NB23_PINN_TYPE", "drift").lower()
GEOTRACES_W = float(os.environ.get("GEOTRACES_W", "0.3"))
GEOTRACES_SUB_W = float(os.environ.get("GEOTRACES_SUB_W", "0.3"))
SUB_DEPTH_MIN = float(os.environ.get("GEOTRACES_SUB_DEPTH_MIN", "50.0"))
SUB_DEPTH_MAX = float(os.environ.get("GEOTRACES_SUB_DEPTH_MAX", "1000.0"))

DT = 0.25
N_STEPS = 200
N_EPOCHS = int(os.environ.get("NB23_N_EPOCHS", "1500"))
H_MLD = 50.0
# K_FE is the iron half-saturation used inside the PINN drift loss. Imported
# from darwindiff.carroll6 (the library constant the integrator also uses)
# so the two never silently diverge.

AOI = EQUATORIAL_PACIFIC_AOI
print(f"AOI: {AOI.name} ({AOI.lat_min}-{AOI.lat_max} N, {AOI.lon_min}-{AOI.lon_max} E)")
print(f"Config: seed={SEED}, fet_w={FET_W}, pinn_w={PINN_W} ({PINN_TYPE})")
print(f"        geotraces_surface_w={GEOTRACES_W}, geotraces_subsurface_w={GEOTRACES_SUB_W}")
print(f"        subsurface depth band: [{SUB_DEPTH_MIN}, {SUB_DEPTH_MAX}] m")
print()


# ============================== Darwin targets (with on-disk cache) =======
#
# LLC270 native loading + xmitgcm decoding takes ~60 s. We cache the
# AOI-binned 1-deg targets + bin_average covariates as a single .pt
# tensor file. Cache is keyed by AOI name (so different AOIs get
# different caches) and only rebuilt if missing or the AOI bounds
# embedded in the cache disagree with the requested AOI.

CACHE_DIR = DATA_ROOT / "cache"
CACHE_PATH = CACHE_DIR / f"eqpac_targets_{AOI.name.replace(' ', '_').lower()}.pt"


def _build_eqpac_targets() -> dict:
    """Slow path: load bin_average + 5 LLC270 native variables + bind 1-deg grid."""
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
            cached = safe_torch_load(CACHE_PATH, map_location="cpu")
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


# ============================== GEOTRACES iron — surface + subsurface =======

print(f"Loading GEOTRACES IDP2025 from {GEOTRACES_NC}...")
geotraces_ds = open_geotraces_bottle(GEOTRACES_NC)
geotraces_sub = subset_aoi_geotraces(geotraces_ds, AOI)
print(f"  Eq Pac stations: {geotraces_sub.sizes['N_STATIONS']}")

# Common flattened arrays for both surface and subsurface binning.
# darwin_lats / darwin_lons come from the cached target build (or freshly
# from bin_average if cache was a miss).
darwin_lats = darwin_lats_cached
darwin_lons = darwin_lons_cached
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
    """Bin filtered Fe_D samples (mmol/m^3) onto the Darwin grid.

    Returns (target_grid, populated_mask) both shape (n_dlat, n_dlon).
    """
    lats = g_lats_all[keep_mask]
    lons = g_lons_all[keep_mask]
    fe = g_fe_all[keep_mask] * 1025.0 * 1.0e-6   # nmol/kg -> mmol/m^3
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


# Surface bin: depth <= 50 m
keep_surface = finite_basic & (g_depths_all <= DEPTH_MAX_SURFACE)
geotraces_target_np, geotraces_mask_np = bin_to_darwin_grid(keep_surface)
n_geo_surface = int(geotraces_mask_np.sum())
print(f"  Surface (<= {DEPTH_MAX_SURFACE} m): {keep_surface.sum()} samples -> "
      f"{n_geo_surface} populated 1deg bins")

# Subsurface bin: SUB_DEPTH_MIN < depth <= SUB_DEPTH_MAX
keep_subsurface = (
    finite_basic & (g_depths_all > SUB_DEPTH_MIN) & (g_depths_all <= SUB_DEPTH_MAX)
)
geotraces_sub_target_np, geotraces_sub_mask_np = bin_to_darwin_grid(keep_subsurface)
n_geo_subsurface = int(geotraces_sub_mask_np.sum())
print(f"  Subsurface ({SUB_DEPTH_MIN}-{SUB_DEPTH_MAX} m): {keep_subsurface.sum()} samples -> "
      f"{n_geo_subsurface} populated 1deg bins")

if n_geo_subsurface > 0:
    sub_vals = geotraces_sub_target_np[geotraces_sub_mask_np]
    print(f"    subsurface DFe range (mmol/m^3): "
          f"[{sub_vals.min():.3e}, {sub_vals.max():.3e}], "
          f"mean {sub_vals.mean():.3e}")


# ============================== Grid alignment ============================

assert geotraces_target_np.shape == fet_binned.shape
assert geotraces_sub_target_np.shape == fet_binned.shape


# ============================== Ocean mask ================================

ocean_mask = (
    np.isfinite(sst) & np.isfinite(mld) & np.isfinite(wind) & np.isfinite(sss)
    & np.isfinite(pco2_atm_field) & np.isfinite(co2_flux_obs)
    & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
    & np.isfinite(dic_binned) & np.isfinite(alk_binned)
)
for chl_arr in chl_per_pft.values():
    ocean_mask = ocean_mask & np.isfinite(chl_arr)
n_ocean = int(ocean_mask.sum())
geotraces_loss_mask_np = geotraces_mask_np & ocean_mask
geotraces_sub_loss_mask_np = geotraces_sub_mask_np & ocean_mask
n_geo_surface_in_ocean = int(geotraces_loss_mask_np.sum())
n_geo_sub_in_ocean = int(geotraces_sub_loss_mask_np.sum())
print(f"Darwin ocean cells: {n_ocean} of {ocean_mask.size}")
print(f"GEOTRACES surface cells inside ocean: {n_geo_surface_in_ocean}")
print(f"GEOTRACES subsurface cells inside ocean: {n_geo_sub_in_ocean}")


# ============================== Tensors ===================================

def normalize_covariate(arr, mask):
    o = arr[mask]
    return np.where(mask, (arr - o.mean()) / max(o.std(), 1e-6), 0.0).astype(np.float32)


sst_norm = normalize_covariate(sst, ocean_mask)
env_1ch = torch.tensor(sst_norm, dtype=torch.float32).unsqueeze(0).to(device)
mask_dev = torch.tensor(ocean_mask, dtype=torch.bool).to(device)
H, W = env_1ch.shape[1], env_1ch.shape[2]

# 15-tracer initial state. L1 mirrors v2.6 exactly; L2 uses literature-plausible
# subsurface initial values (DFe_2 ~ 0.5 nmol/kg, POC_2 ~ 0.05, PIC_2 ~ 0.003,
# DIC_2 / ALK_2 slightly elevated from surface due to remineralization).
state0 = torch.tensor([
    # L1
    5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
    0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
    # L2
    5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
]).reshape(N_TRACERS_2LAYER, 1, 1).expand(N_TRACERS_2LAYER, H, W).contiguous().to(device)

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

geotraces_sub_target_t = torch.tensor(
    np.where(geotraces_sub_loss_mask_np, geotraces_sub_target_np, 0.0).astype(np.float32)
).to(device)
geotraces_sub_mask_t = torch.tensor(geotraces_sub_loss_mask_np, dtype=torch.bool).to(device)


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

print(f"\n=== Training: 2-layer 15-tracer + 11-target z-score + PINN drift w={PINN_W} "
      f"+ GEOTRACES surface w={GEOTRACES_W} ({n_geo_surface_in_ocean} cells) "
      f"+ GEOTRACES subsurface w={GEOTRACES_SUB_W} ({n_geo_sub_in_ocean} cells) ===")
torch.manual_seed(SEED)
net = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
optimizer = torch.optim.Adam(net.parameters(), lr=5e-3)

try:
    _integrate = torch.compile(carroll6_5pft_2layer_integrate, mode="reduce-overhead")
except Exception:
    _integrate = carroll6_5pft_2layer_integrate

t0 = time.time()
# Pre-allocate GPU loss histories so we never sync host<->device in the hot
# loop. ~3 .item() calls per epoch × 1500 epochs would mean ~4500 GPU syncs;
# storing into a GPU tensor and syncing once at the end (plus at log steps)
# is dramatically cheaper on small-grid problems where launch overhead
# dominates.
NAN_F32 = float("nan")
loss_history = torch.full((N_EPOCHS,), NAN_F32, dtype=torch.float32, device=device)
geo_surface_history = torch.full((N_EPOCHS,), NAN_F32, dtype=torch.float32, device=device)
geo_sub_history = torch.full((N_EPOCHS,), NAN_F32, dtype=torch.float32, device=device)
for epoch in range(N_EPOCHS):
    optimizer.zero_grad()
    params = bounded_params(net(env_1ch), bounds_dev)
    state = _integrate(
        state0, params, DT, N_STEPS,
        T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev,
    )
    dfe1_pred = state[I_DFE_1]
    dfe2_pred = state[I_DFE_2]
    p_diatom_pred = state[I_DIATOM]
    p_lge_pred = state[I_LGE]
    p_syn_pred = state[I_SYN]
    p_proLL_pred = state[I_PROLL]
    p_proHL_pred = state[I_PROHL]
    poc_pred = state[I_POC_1]
    pic_pred = state[I_PIC_1]
    dic_pred = state[I_DIC_1]
    alk_pred = state[I_ALK_1]
    carb_final = solve_carbonate(dic_pred, alk_pred, T_dev, S_dev)
    co2_flux_pred = co2_flux(carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev)

    def term(pred, target_z):
        ocean = pred[mask_dev]
        pred_z = (pred - ocean.mean()) / ocean.std().clamp(min=1e-6)
        residual = (pred_z - target_z) * mask_dev.to(pred.dtype)
        return (residual ** 2).sum() / mask_dev.sum().to(residual.dtype)

    # 11-target z-score loss (identical to v2.6, applied to L1 only)
    l_fet = term(dfe1_pred, fet_z)
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

    # PINN drift loss on L1 iron (identical formula to v2.6 — no subsurface PINN)
    if PINN_W > 0:
        alpfe_p = params[0]
        scav_rat_p = params[1]
        mu_proHL_p = params[2]
        mu_lge_p = params[3]
        f_fe_final = state[I_DFE_1] / (state[I_DFE_1] + K_FE)
        growth_total_final = (
            MU_DEFAULT_DIATOM * f_fe_final * state[I_DIATOM]
            + mu_lge_p * f_fe_final * state[I_LGE]
            + MU_DEFAULT_SYN * f_fe_final * state[I_SYN]
            + MU_DEFAULT_PROLL * f_fe_final * state[I_PROLL]
            + mu_proHL_p * f_fe_final * state[I_PROHL]
        )
        iron_source = alpfe_p * PHI_DUST
        iron_sink = scav_rat_p * 86400.0 * state[I_DFE_1] * state[I_POC_1] + Q_FE * growth_total_final
        if PINN_TYPE == "drift":
            dDFe_dt = iron_source - iron_sink
            rel_rate = dDFe_dt / state[I_DFE_1].clamp(min=1e-10)
            l_pinn_iron = ((rel_rate ** 2) * mask_dev.to(rel_rate.dtype)).sum() / mask_dev.sum().to(rel_rate.dtype)
        else:
            iron_norm = iron_source[mask_dev].abs().mean().clamp(min=1e-12)
            imbalance = (iron_source - iron_sink) / iron_norm
            l_pinn_iron = ((imbalance ** 2) * mask_dev.to(imbalance.dtype)).sum() / mask_dev.sum().to(imbalance.dtype)
        loss = loss + PINN_W * l_pinn_iron

    # Surface GEOTRACES loss (identical to v2.6)
    l_geotraces = None
    if GEOTRACES_W > 0 and n_geo_surface_in_ocean > 0:
        residual_geo = (dfe1_pred - geotraces_target_t) * geotraces_mask_t.to(dfe1_pred.dtype)
        geo_scale = (geotraces_target_t[geotraces_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geotraces = (residual_geo ** 2).sum() / geotraces_mask_t.sum().to(residual_geo.dtype) / geo_scale
        loss = loss + GEOTRACES_W * l_geotraces

    # NEW v2.7: Subsurface GEOTRACES loss on L2 DFe
    l_geo_sub = None
    if GEOTRACES_SUB_W > 0 and n_geo_sub_in_ocean > 0:
        residual_sub = (dfe2_pred - geotraces_sub_target_t) * geotraces_sub_mask_t.to(dfe2_pred.dtype)
        sub_scale = (geotraces_sub_target_t[geotraces_sub_mask_t] ** 2).mean().clamp(min=1e-30)
        l_geo_sub = (residual_sub ** 2).sum() / geotraces_sub_mask_t.sum().to(residual_sub.dtype) / sub_scale
        loss = loss + GEOTRACES_SUB_W * l_geo_sub

    loss.backward()
    optimizer.step()

    # Stash the per-epoch losses on GPU (no host sync). Detached + assigned
    # to pre-allocated history tensors so the autograd graph is freed each
    # step and no list grows.
    with torch.no_grad():
        loss_history[epoch] = loss.detach()
        if l_geotraces is not None:
            geo_surface_history[epoch] = l_geotraces.detach()
        if l_geo_sub is not None:
            geo_sub_history[epoch] = l_geo_sub.detach()

    if (epoch + 1) % 250 == 0 or epoch + 1 == N_EPOCHS:
        # Single sync per log line.
        l_now = float(loss_history[epoch].item())
        gs = float(geo_surface_history[epoch].item())
        gsub = float(geo_sub_history[epoch].item())
        print(f"  epoch {epoch+1:4d}  loss = {l_now:.4e}  "
              f"surf = {gs:.4e}  sub = {gsub:.4e}")

if device == "cuda":
    torch.cuda.synchronize()
elapsed = time.time() - t0

# Bulk-sync histories to CPU once (single device->host copy each).
losses_total = loss_history.cpu().numpy().tolist()
losses_geo_surface = geo_surface_history.cpu().numpy().tolist()
losses_geo_sub = geo_sub_history.cpu().numpy().tolist()
print(f"Done in {elapsed:.0f}s, loss {losses_total[0]:.3e} -> {losses_total[-1]:.3e}")


# ============================== Recovery analysis =========================

with torch.no_grad():
    params_dev = bounded_params(net(env_1ch), bounds_dev)
    param_means = []
    for i in range(6):
        p = params_dev[i][mask_dev]
        param_means.append(float(p.mean().cpu().numpy()))
    # Also collect predicted DFe surface + subsurface means for diagnostics
    state_final = _integrate(
        state0, params_dev, DT, N_STEPS,
        T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev,
    )
    dfe1_final = state_final[I_DFE_1][mask_dev].mean().item()
    dfe2_final = state_final[I_DFE_2][mask_dev].mean().item()

param_names = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
carroll_published = CARROLL_VALUES.numpy()

results = {
    "seed": SEED,
    "geotraces_w": GEOTRACES_W,
    "geotraces_sub_w": GEOTRACES_SUB_W,
    "sub_depth_min_m": SUB_DEPTH_MIN,
    "sub_depth_max_m": SUB_DEPTH_MAX,
    "pinn_w": PINN_W,
    "pinn_type": PINN_TYPE,
    "fet_w": FET_W,
    "n_geo_surface_cells": n_geo_surface_in_ocean,
    "n_geo_sub_cells": n_geo_sub_in_ocean,
    "elapsed_s": elapsed,
    "loss_initial": losses_total[0],
    "loss_final": losses_total[-1],
    # NaN-safe JSON: replace nan with None so json.dump(allow_nan=False)
    # produces spec-compliant output even when a loss term is disabled
    # (e.g. GEOTRACES_SUB_W=0 leaves geo_sub_loss history full of NaN).
    "geo_surface_loss_initial": (
        None if not np.isfinite(losses_geo_surface[0]) else losses_geo_surface[0]
    ),
    "geo_surface_loss_final": (
        None if not np.isfinite(losses_geo_surface[-1]) else losses_geo_surface[-1]
    ),
    "geo_sub_loss_initial": (
        None if not np.isfinite(losses_geo_sub[0]) else losses_geo_sub[0]
    ),
    "geo_sub_loss_final": (
        None if not np.isfinite(losses_geo_sub[-1]) else losses_geo_sub[-1]
    ),
    "dfe1_pred_mean_mmol_m3": dfe1_final,
    "dfe2_pred_mean_mmol_m3": dfe2_final,
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

# Compare to v2.6 (10-seed) and GEOTRACES sub data
print(f"\nVerdict: {n_cal_grade} / 6 calibration-grade ({n_excellent} excellent)")
print(f"vs v2.6 (10-seed mean, GEOTRACES_W=0.3, NO subsurface): "
      f"~3-4 / 6 cal-grade; scav_rat 0.92 +/- 0.01 off")
print(f"\nPredicted DFe means (mmol/m^3): L1 = {dfe1_final:.3e}, L2 = {dfe2_final:.3e}")
print(f"  observed GEOTRACES means: L1 surface ~ 1.66e-04 (0.162 nmol/kg * 1.025e-3),")
print(f"                            L2 subsurface ~ 3.7e-04 (~0.36 nmol/kg * 1.025e-3)")

results_path = Path(__file__).resolve().parent / (
    f"run_v2.7_multilayer_result_seed{SEED}"
    f"_surf{GEOTRACES_W}"
    f"_sub{GEOTRACES_SUB_W}"
    f"_pinn{PINN_W}.json"
)
with results_path.open("w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, allow_nan=False)
print(f"\nResults JSON written to: {results_path}")
