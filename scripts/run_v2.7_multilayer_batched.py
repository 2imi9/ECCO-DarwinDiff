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
    carroll6_5pft_2layer_step,
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

DT = 0.25
N_STEPS = 200
K_FE_LOCAL = 5.0e-5

AOI = EQUATORIAL_PACIFIC_AOI
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
            cached = torch.load(CACHE_PATH, map_location="cpu", weights_only=False)
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

# State replicated across the new seed dim:  [15, N_seeds, H, W]
state0_single = torch.tensor([
    5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
    0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
    5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
]).reshape(N_TRACERS_2LAYER, 1, 1, 1).expand(N_TRACERS_2LAYER, N_SEEDS, H, W).contiguous().to(device)

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
        f_fe = state[I_DFE_1] / (state[I_DFE_1] + K_FE_LOCAL)
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

    for seed_idx, seed in enumerate(SEEDS):
        param_means = []
        for i in range(6):
            p = params_b_final[i, seed_idx][mask_dev]
            param_means.append(float(p.mean().cpu().numpy()))
        dfe1_final_mean = float(state_final[I_DFE_1, seed_idx][mask_dev].mean().item())
        dfe2_final_mean = float(state_final[I_DFE_2, seed_idx][mask_dev].mean().item())

        result = {
            "seed": seed,
            "geotraces_w": GEOTRACES_W,
            "geotraces_sub_w": GEOTRACES_SUB_W,
            "sub_depth_min_m": SUB_DEPTH_MIN,
            "sub_depth_max_m": SUB_DEPTH_MAX,
            "pinn_w": PINN_W,
            "pinn_type": PINN_TYPE,
            "fet_w": FET_W,
            "n_geo_surface_cells": n_geo_surface_in_ocean,
            "n_geo_sub_cells": n_geo_sub_in_ocean,
            "elapsed_s_total_batch": elapsed,
            "n_seeds_in_batch": N_SEEDS,
            "loss_initial": float(loss_history[0, seed_idx].item()),
            "loss_final": float(loss_history[-1, seed_idx].item()),
            "dfe1_pred_mean_mmol_m3": dfe1_final_mean,
            "dfe2_pred_mean_mmol_m3": dfe2_final_mean,
            "params": {},
        }
        n_cal_grade = 0
        n_excellent = 0
        for name, rec, pub in zip(param_names, param_means, carroll_published):
            rel = abs(rec - float(pub)) / abs(float(pub))
            if rel <= 0.05:
                band = "Excellent"; n_cal_grade += 1; n_excellent += 1
            elif rel <= 0.40:
                band = "Cal-grade"; n_cal_grade += 1
            elif rel <= 0.80:
                band = "Loose"
            else:
                band = "Drifted"
            print(f"{seed:<6d} {name:<12s} {rec:>12.4e} {float(pub):>12.4e} "
                  f"{rel:>12.4f} {band:<12s}")
            result["params"][name] = {
                "recovered": float(rec),
                "carroll_published": float(pub),
                "abs_rel_offset": float(rel),
                "band": band,
            }
        result["n_cal_grade"] = n_cal_grade
        result["n_excellent"] = n_excellent
        print(f"       -> {n_cal_grade}/6 cal-grade ({n_excellent} Excellent)")
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
    for r in all_results:
        out = out_dir / (
            f"run_v2.7_multilayer_result_seed{r['seed']}"
            f"_surf{GEOTRACES_W}"
            f"_sub{GEOTRACES_SUB_W}"
            f"_pinn{PINN_W}.json"
        )
        existed = out.is_file()
        with out.open("w", encoding="utf-8") as f:
            json.dump(r, f, indent=2)
        suffix = " (overwrote existing)" if existed else ""
        print(f"  wrote {out.name}{suffix}")

print(f"\nBatch summary: {N_SEEDS} seeds in {elapsed:.0f}s "
      f"({elapsed/N_SEEDS:.1f}s amortized per seed).")
