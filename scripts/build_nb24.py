# -*- coding: utf-8 -*-
"""Build notebooks/24_5pft_box_glodap_hybrid_eqpac.ipynb via nbformat.

The combo deliverable: 5-PFT box (v2.2 Phase 2 structural fix) trained against
a hybrid target where DIC + ALK are GLODAPv2.2016b mapped-climatology real
observations (v2.1 Phase 1 target swap), while FeT + Chl1..Chl5 + POC + PIC +
CO2_flux remain ECCO-Darwin v05 output.

If both interventions stack constructively, all 6 Carroll-6 parameters land
in calibration-grade range (<= 40% off Carroll's published Green's-functions
optima) — matching the original goal Carroll 2020/2022 demonstrated.

Builds on:
- nb22 (Phase 1 target swap; introduced glodap_loader on the PR #36 branch)
- nb23 (Phase 2 5-PFT box; same Carroll-goal-focused comparison framing)

Required: ``src/darwindiff/glodap_loader.py`` must be on the branch this nb
executes from. Currently the loader lives only on `claude/v2.1-glodap-real-obs`
(PR #36); cherry-pick or merge before executing nb24.

Run via: python scripts/build_nb24.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf


def main() -> None:
    nb = nbf.v4.new_notebook()
    cells: list = []

    # --- Cell 1: title + goal ---------------------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''# Notebook 24 — 5-PFT box + GLODAP real-obs DIC/ALK (Track 1 v2.2 Phase 2 + v2.1 Phase 1 combo)

**Goal.** Recover Carroll et al. 2020 / 2022 calibrated parameter values — the published Green's-functions optima encoded in `CARROLL_VALUES` — at calibration-grade quality (≤ 40% off Carroll for each of the 6 parameters).

**What's combined.** Two orthogonal interventions stacked:

1. **5-PFT box** (Phase 2, from nb23): replace the 2-PFT lumped phytoplankton (`Ps` + `Pl`) with 5 distinct functional types (diatoms, other large euks, Synechococcus, Pro-LL, Pro-HL). Each Carroll-6 parameter now governs one specific PFT instead of an average across multiple species.

2. **GLODAP real-obs target for DIC + ALK** (Phase 1, from nb22): swap Darwin's internal DIC + ALK self-consistent fields for GLODAPv2.2016b mapped-climatology real ship-CTD observations.

The hypothesis: the 5-PFT structural fix unblocks `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC` to recover toward their Carroll-calibrated values; the GLODAP target gives a more realistic carbonate constraint than Darwin's internal ALK; together they should pull all 6 params into calibration-grade against the goal.

**Loss target — 11 tracers (DIC + ALK from real obs, rest from Darwin):**

| Box-model output | Target source | Variable |
|---|---|---|
| `state[0]` (DFe) | Darwin v05 LLC270 native binned | `FeT` |
| `state[1]` (P_diatom) | Darwin v05 bin_average | `Chl1` |
| `state[2]` (P_lge) | Darwin v05 bin_average | `Chl2` |
| `state[3]` (P_syn) | Darwin v05 bin_average | `Chl3` |
| `state[4]` (P_proLL) | Darwin v05 bin_average | `Chl4` |
| `state[5]` (P_proHL) | Darwin v05 bin_average | `Chl5` |
| `state[6]` (POC) | Darwin v05 LLC270 native binned | `POC` |
| `state[7]` (PIC) | Darwin v05 LLC270 native binned | `PIC` |
| `state[8]` (DIC) | **GLODAPv2.2016b mapped surface** | `TCO2` |
| `state[9]` (ALK) | **GLODAPv2.2016b mapped surface** | `TAlk` |
| `co2_flux(...)` | Darwin v05 bin_average | `CO2_flux` |

**Headline experiment: DINN baseline** (1×1 conv, SST input, ~400 params). Can't saturate trivially → recovered Carroll-6 means carry identifiability information.

**Secondary: DINNDeep** (4-channel input, ~9.4K params).

**Success criterion (the original goal).** For each of the 6 parameters, `|recovered − Carroll_published| / |Carroll_published| ≤ 0.40` — calibration-grade. All 6 in that band → the differentiable parameter learner combined with real-obs targets has caught Carroll's Green's-functions calibration.

**Builds on:** nb22 (Phase 1 GLODAP loader), nb23 (Phase 2 5-PFT box). Module: `src/darwindiff/carroll6_5pft.py` (5-PFT box) + `src/darwindiff/glodap_loader.py` (real-obs DIC + ALK).
'''))

    # --- Cell 2: imports ---------------------------------------------------
    cells.append(nbf.v4.new_code_cell(r'''import os
import sys
import time
from pathlib import Path

# Ensure src/ on sys.path so notebook execution works without `pip install -e .`
_SRC = Path.cwd() / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

import matplotlib.pyplot as plt
import numpy as np
import torch

from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate
from darwindiff.carroll6 import (
    CARROLL_VALUES,
    H_MLD,
    PARAM_BOUNDS,
    PARAM_NAMES,
    bounded_params,
)
from darwindiff.carroll6_5pft import (
    I_ALK, I_DFE, I_DIATOM, I_DIC, I_LGE, I_PIC, I_POC, I_PROHL, I_PROLL, I_SYN,
    N_TRACERS,
    carroll6_5pft_integrate,
)
from darwindiff.diagnostics import format_pearson, safe_pearson_r
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    open_bin_average,
    subset_aoi,
    time_mean,
)
from darwindiff.glodap_loader import (
    open_glodap_variable,
    subset_aoi_glodap,
    surface_layer_glodap,
    to_mmol_per_m3,
)
from darwindiff.llc270_loader import bin_native_tracer_to_1deg
from darwindiff.networks import DINN, DINNDeep

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

AOI = EQUATORIAL_PACIFIC_AOI
print(f"AOI: {AOI.name} ({AOI.lat_min}-{AOI.lat_max} N, {AOI.lon_min}-{AOI.lon_max} E)")
'''))

    # --- Cell 3: load data ------------------------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 1. Load Eq Pacific climatology — 11 targets (DIC + ALK from GLODAP, rest from Darwin)

Per-PFT Chl + carbonate-flux + covariates come from `bin_average`. Native LLC270 tracers (FeT, POC, PIC) bin to the same 1° grid via `bin_native_tracer_to_1deg`. **DIC + ALK** come from GLODAPv2.2016b mapped climatology surface (`depth_surface=0`), AOI-subset, and unit-converted µmol/kg → mmol/m³ at the loader boundary. Combined ocean mask = every target AND every covariate finite.
'''))

    cells.append(nbf.v4.new_code_cell(r'''DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\\ecco_darwin_v5"))
BIN_AVG_PATH = str(DATA_ROOT / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc")
MONTHLY_ROOT = str(DATA_ROOT / "output" / "monthly")
GRID_DIR = str(DATA_ROOT / "grid")
GLODAP_ROOT = Path(os.environ.get(
    "GLODAP_DATA_ROOT",
    str(Path.cwd() / "data" / "glodap" / "GLODAPv2.2016b_MappedClimatologies"),
))

# === Covariates + per-PFT Chl + CO2_flux from bin_average ===
ds_bin = open_bin_average(BIN_AVG_PATH)
eqpac_clim = time_mean(subset_aoi(ds_bin, AOI))

sst = eqpac_clim.SST.values.astype(np.float64)
mld = eqpac_clim.mldDepth.values.astype(np.float64)
wind = eqpac_clim.windSpeed.values.astype(np.float64)
sss = eqpac_clim.SSS.values.astype(np.float64)
co2_flux_obs = eqpac_clim.CO2_flux.values.astype(np.float64) * 1.0e3  # mol -> mmol C / m^2 / s
pco2_atm_field = eqpac_clim.apCO2.values.astype(np.float64) * 1.0e6  # atm -> uatm

chl_per_pft = {}
for i in range(1, 6):
    chl_per_pft[f"Chl{i}"] = eqpac_clim[f"Chl{i}"].values.astype(np.float64)

lat_1d = eqpac_clim.lat.values.astype(np.float64)
lat_2d = np.broadcast_to(lat_1d[:, None], sst.shape).astype(np.float64)
print(f"bin_average covariates + per-PFT Chl loaded: shape = {sst.shape}")

# === Native LLC270 tracers (FeT, POC, PIC) ===
print("Loading native LLC270 tracers (FeT, POC, PIC)...")
native_targets = {}
for var in ["FeT", "POC", "PIC"]:
    native_targets[var] = bin_native_tracer_to_1deg(
        monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable=var,
        lat_min=AOI.lat_min, lat_max=AOI.lat_max,
        lon_min=AOI.lon_min, lon_max=AOI.lon_max,
        iters="all",
    )
    print(f"  {var}: shape={native_targets[var].shape}, "
          f"finite={int(np.isfinite(native_targets[var]).sum())}")

fet_binned = native_targets["FeT"]
poc_binned = native_targets["POC"]
pic_binned = native_targets["PIC"]

# === DIC + ALK from GLODAP real obs ===
# Surface layer (depth_surface=0), AOI-subset, unit-converted to mmol/m^3.
# Note: bin_average's lat grid runs the same direction as ours, so the
# subset_aoi_glodap call produces a compatible shape; we re-grid to the
# bin_average mesh if shapes differ.
print(f"Loading GLODAPv2.2016b from {GLODAP_ROOT}...")
glodap_targets = {}
for var, glodap_name in [("DIC", "DIC"), ("ALK", "ALK")]:
    ds = open_glodap_variable(str(GLODAP_ROOT), glodap_name)
    ds_surf = surface_layer_glodap(ds)
    ds_aoi = subset_aoi_glodap(ds_surf, AOI)
    da_umol = ds_aoi[
        {"DIC": "TCO2", "ALK": "TAlk"}[var]
    ]
    da_mmol = to_mmol_per_m3(da_umol)
    # Regrid GLODAP to bin_average grid if necessary (lat/lon may differ by
    # half-cell offset; bin_average runs on integer-degree centers).
    target_lat = eqpac_clim.lat.values
    target_lon = eqpac_clim.lon.values
    da_mmol_interp = da_mmol.interp(lat=target_lat, lon=target_lon)
    glodap_targets[var] = da_mmol_interp.values.astype(np.float64)
    print(f"  GLODAP {var}: shape={glodap_targets[var].shape}, "
          f"finite={int(np.isfinite(glodap_targets[var]).sum())}, "
          f"mean={np.nanmean(glodap_targets[var]):.2f} mmol/m^3")

dic_binned = glodap_targets["DIC"]
alk_binned = glodap_targets["ALK"]

# === Combined ocean mask ===
ocean_mask = (
    np.isfinite(sst) & np.isfinite(mld) & np.isfinite(wind) & np.isfinite(sss)
    & np.isfinite(pco2_atm_field) & np.isfinite(co2_flux_obs)
    & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
    & np.isfinite(dic_binned) & np.isfinite(alk_binned)
)
for chl_name, chl_arr in chl_per_pft.items():
    ocean_mask = ocean_mask & np.isfinite(chl_arr)
n_ocean = int(ocean_mask.sum())
print(f"\nCombined ocean cells (11 targets + 5 forcing fields finite): "
      f"{n_ocean} of {ocean_mask.size}")

print("\nTarget magnitudes over ocean mask:")
target_table = [("FeT", fet_binned)]
for i in range(1, 6):
    target_table.append((f"Chl{i}", chl_per_pft[f"Chl{i}"]))
target_table += [
    ("POC", poc_binned), ("PIC", pic_binned),
    ("DIC (GLODAP)", dic_binned), ("ALK (GLODAP)", alk_binned),
    ("CO2_flux", co2_flux_obs),
]
for name, a in target_table:
    o = a[ocean_mask]
    print(f"  {name:>14s}: mean {o.mean():.3e}, std {o.std():.3e}, "
          f"range [{o.min():.3e}, {o.max():.3e}]")
'''))

    # --- Cell 4: training tensors + z-score -------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 2. Build training tensors and z-score the 11 targets

Initial state matches the empirical Eq Pacific abundance partition. DIC + ALK initial values are at the GLODAP surface climatology mean over the AOI (close to but not identical to Darwin's internal initial values used in nb20 / nb23).
'''))

    cells.append(nbf.v4.new_code_cell(r'''def normalize_covariate(arr, mask):
    o = arr[mask]
    return np.where(mask, (arr - o.mean()) / max(o.std(), 1e-6), 0.0).astype(np.float32)


sst_norm = normalize_covariate(sst, ocean_mask)
mld_norm = normalize_covariate(mld, ocean_mask)
wind_norm = normalize_covariate(wind, ocean_mask)
lat_norm = normalize_covariate(lat_2d, ocean_mask)

env_1ch = torch.tensor(sst_norm, dtype=torch.float32).unsqueeze(0)
env_4ch = torch.tensor(np.stack([sst_norm, mld_norm, wind_norm, lat_norm], axis=0),
                       dtype=torch.float32)

mask_t = torch.tensor(ocean_mask, dtype=torch.bool)
H, W = env_1ch.shape[1], env_1ch.shape[2]

# Initial DIC + ALK from GLODAP AOI surface mean (real obs anchor).
dic0 = float(np.nanmean(dic_binned[ocean_mask]))
alk0 = float(np.nanmean(alk_binned[ocean_mask]))
print(f"Initial DIC = {dic0:.1f} mmol/m^3 (GLODAP surface mean)")
print(f"Initial ALK = {alk0:.1f} mmol/m^3 (GLODAP surface mean)")

state0 = torch.tensor([
    5.0e-4,           # DFe
    0.4,              # P_diatom
    0.3,              # P_lge
    0.02,             # P_syn
    0.001,            # P_proLL
    0.65,             # P_proHL
    0.5,              # POC
    0.025,            # PIC
    dic0,             # DIC (from GLODAP)
    alk0,             # ALK (from GLODAP)
]).reshape(N_TRACERS, 1, 1).expand(N_TRACERS, H, W).contiguous()

T_field = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32))
S_field = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32))
wind_field = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32))
pco2_atm_t = torch.tensor(np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32))

env_1ch_dev = env_1ch.to(device)
env_4ch_dev = env_4ch.to(device)
state0_dev = state0.to(device)
mask_dev = mask_t.to(device)
bounds_dev = PARAM_BOUNDS.to(device)
T_dev = T_field.to(device)
S_dev = S_field.to(device)
wind_dev = wind_field.to(device)
pco2_atm_dev = pco2_atm_t.to(device)


def to_z_target(np_field):
    clean = np.where(ocean_mask, np_field, 1.0).astype(np.float32)
    t = torch.tensor(clean, dtype=torch.float32).to(device)
    o = t[mask_dev]
    mean = o.mean()
    std = o.std().clamp(min=1e-6)
    return (t - mean) / std, float(mean), float(std)


fet_z, fet_mean, fet_std = to_z_target(fet_binned)
poc_z, poc_mean, poc_std = to_z_target(poc_binned)
pic_z, pic_mean, pic_std = to_z_target(pic_binned)
dic_z, dic_mean, dic_std = to_z_target(dic_binned)
alk_z, alk_mean, alk_std = to_z_target(alk_binned)
co2_flux_z, co2_flux_mean_obs, co2_flux_std_obs = to_z_target(co2_flux_obs)

chl_z = {}
chl_stats = {}
for i in range(1, 6):
    chl_z[f"Chl{i}"], m, s = to_z_target(chl_per_pft[f"Chl{i}"])
    chl_stats[f"Chl{i}"] = (m, s)

print("Z-score statistics:")
print(f"  {'FeT':<14s}  mean = {fet_mean:.4e}, std = {fet_std:.4e}")
for i in range(1, 6):
    m, s = chl_stats[f"Chl{i}"]
    print(f"  Chl{i:<11d}  mean = {m:.4e}, std = {s:.4e}")
for name, m, s in [("POC", poc_mean, poc_std), ("PIC", pic_mean, pic_std),
                   ("DIC (GLODAP)", dic_mean, dic_std), ("ALK (GLODAP)", alk_mean, alk_std),
                   ("CO2_flux", co2_flux_mean_obs, co2_flux_std_obs)]:
    print(f"  {name:<14s}  mean = {m:.4e}, std = {s:.4e}")
'''))

    # --- Cell 5: training loop --------------------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 3. Train DINN baseline + DINNDeep on the 11-target joint loss (DIC/ALK from real obs)

Same hyperparameters as nb23 (Adam lr=5e-3, 1500 epochs, 200 forward-Euler steps at dt=0.25 d). Loss is identical to nb23's structure (11 terms averaged); the only behavioral difference is that the DIC + ALK terms now compare to real ocean observations.
'''))

    cells.append(nbf.v4.new_code_cell(r'''DT = 0.25
N_STEPS = 200
N_EPOCHS = int(os.environ.get("NB24_EPOCHS", "1500"))
print(f"Training: dt={DT}, n_steps={N_STEPS}, n_epochs={N_EPOCHS}")


def train(net, env_dev, seed: int = 0) -> dict:
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(net.parameters(), lr=5e-3)
    losses = []
    loss_keys = ["FeT", "Chl1", "Chl2", "Chl3", "Chl4", "Chl5",
                 "POC", "PIC", "DIC", "ALK", "CO2_flux"]
    losses_per_tracer = {k: [] for k in loss_keys}
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    for epoch in range(N_EPOCHS):
        optimizer.zero_grad()
        params = bounded_params(net(env_dev), bounds_dev)
        state = carroll6_5pft_integrate(
            state0_dev, params, DT, N_STEPS,
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
        co2_flux_pred = co2_flux(
            carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev,
        )

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
        l_dic = term(dic_pred, dic_z)  # ← GLODAP target
        l_alk = term(alk_pred, alk_z)  # ← GLODAP target
        l_co2 = term(co2_flux_pred, co2_flux_z)
        loss = (l_fet + l_chl1 + l_chl2 + l_chl3 + l_chl4 + l_chl5
                + l_poc + l_pic + l_dic + l_alk + l_co2) / 11.0

        loss.backward()
        optimizer.step()
        losses.append(loss.item())
        for k, lv in zip(loss_keys,
                         [l_fet, l_chl1, l_chl2, l_chl3, l_chl4, l_chl5,
                          l_poc, l_pic, l_dic, l_alk, l_co2]):
            losses_per_tracer[k].append(lv.item())
        if (epoch + 1) % 250 == 0 or epoch + 1 == N_EPOCHS:
            print(f"    epoch {epoch+1:4d}  loss = {loss.item():.4e}  "
                  f"(FeT {l_fet.item():.2e}, Chl1-5 {l_chl1.item():.2e}/"
                  f"{l_chl2.item():.2e}/{l_chl3.item():.2e}/"
                  f"{l_chl4.item():.2e}/{l_chl5.item():.2e}, "
                  f"POC {l_poc.item():.2e}, PIC {l_pic.item():.2e}, "
                  f"DIC {l_dic.item():.2e}, ALK {l_alk.item():.2e}, "
                  f"CO2 {l_co2.item():.2e})")
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - t0
    with torch.no_grad():
        params_dev = bounded_params(net(env_dev), bounds_dev)
        state = carroll6_5pft_integrate(
            state0_dev, params_dev, DT, N_STEPS,
            T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev, h_mld=H_MLD,
        )
        carb_final = solve_carbonate(state[I_DIC], state[I_ALK], T_dev, S_dev)
        co2_flux_pred_final = co2_flux(
            carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev,
        )
        return {
            "losses": losses,
            "losses_per_tracer": losses_per_tracer,
            "params_final": params_dev.cpu(),
            "dfe_final": state[I_DFE].cpu().numpy(),
            "p_diatom_final": state[I_DIATOM].cpu().numpy(),
            "p_lge_final": state[I_LGE].cpu().numpy(),
            "p_syn_final": state[I_SYN].cpu().numpy(),
            "p_proLL_final": state[I_PROLL].cpu().numpy(),
            "p_proHL_final": state[I_PROHL].cpu().numpy(),
            "poc_final": state[I_POC].cpu().numpy(),
            "pic_final": state[I_PIC].cpu().numpy(),
            "dic_final": state[I_DIC].cpu().numpy(),
            "alk_final": state[I_ALK].cpu().numpy(),
            "co2_flux_final": co2_flux_pred_final.cpu().numpy(),
            "elapsed": elapsed,
        }


torch.manual_seed(0)
dinn_baseline = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
n_b = sum(p.numel() for p in dinn_baseline.parameters())
print(f"=== HEADLINE: DINN baseline (SST-only, {n_b} params), 11-target GLODAP-hybrid loss ===")
r_baseline = train(dinn_baseline, env_1ch_dev)
print(f"  done in {r_baseline['elapsed']:.0f}s, loss "
      f"{r_baseline['losses'][0]:.3e} -> {r_baseline['losses'][-1]:.3e}")

torch.manual_seed(0)
dinn_deep = DINNDeep(n_input_channels=4, hidden_dim=32, n_outputs=6, n_blocks=4).to(device)
n_d = sum(p.numel() for p in dinn_deep.parameters())
print(f"\n=== SECONDARY: DINNDeep ({n_d} params), 11-target GLODAP-hybrid loss ===")
r_deep = train(dinn_deep, env_4ch_dev)
print(f"  done in {r_deep['elapsed']:.0f}s, loss "
      f"{r_deep['losses'][0]:.3e} -> {r_deep['losses'][-1]:.3e}")
'''))

    # --- Cell 6: goal check + per-target r --------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 4. Goal check: recovered Carroll-6 vs Carroll's published Green's-functions optima

For each parameter: `recovered`, `Carroll published`, `|Δ|/Carroll`, quality band (Excellent ≤ 0.10 / Calibration-grade ≤ 0.40 / Loose ≤ 1.00 / Drifted > 1.00). Success criterion: all 6 land in *Calibration-grade* or better.
'''))

    cells.append(nbf.v4.new_code_cell(r'''n_total = int(ocean_mask.sum())


def per_target_r(result: dict) -> dict:
    return {
        "FeT":      safe_pearson_r(result["dfe_final"][ocean_mask],      fet_binned[ocean_mask]),
        "Chl1":     safe_pearson_r(result["p_diatom_final"][ocean_mask], chl_per_pft["Chl1"][ocean_mask]),
        "Chl2":     safe_pearson_r(result["p_lge_final"][ocean_mask],    chl_per_pft["Chl2"][ocean_mask]),
        "Chl3":     safe_pearson_r(result["p_syn_final"][ocean_mask],    chl_per_pft["Chl3"][ocean_mask]),
        "Chl4":     safe_pearson_r(result["p_proLL_final"][ocean_mask],  chl_per_pft["Chl4"][ocean_mask]),
        "Chl5":     safe_pearson_r(result["p_proHL_final"][ocean_mask],  chl_per_pft["Chl5"][ocean_mask]),
        "POC":      safe_pearson_r(result["poc_final"][ocean_mask],      poc_binned[ocean_mask]),
        "PIC":      safe_pearson_r(result["pic_final"][ocean_mask],      pic_binned[ocean_mask]),
        "DIC":      safe_pearson_r(result["dic_final"][ocean_mask],      dic_binned[ocean_mask]),
        "ALK":      safe_pearson_r(result["alk_final"][ocean_mask],      alk_binned[ocean_mask]),
        "CO2_flux": safe_pearson_r(result["co2_flux_final"][ocean_mask], co2_flux_obs[ocean_mask]),
    }


r_per_b = per_target_r(r_baseline)
r_per_d = per_target_r(r_deep)

print("Pearson r against targets (DIC + ALK = GLODAP real-obs; rest = Darwin v05):")
print(f"  {'target':<10s}  {'DINN baseline':>16s}  {'DINNDeep':>16s}")
for tgt in ["FeT", "Chl1", "Chl2", "Chl3", "Chl4", "Chl5",
            "POC", "PIC", "DIC", "ALK", "CO2_flux"]:
    rb = r_per_b[tgt]
    rd = r_per_d[tgt]
    print(f"  {tgt:<10s}  {format_pearson(rb, n_total=n_total):>16s}  {format_pearson(rd, n_total=n_total):>16s}")

print()
print(f"Final loss plateau:")
print(f"  DINN baseline:  {r_baseline['losses'][-1]:.4e}")
print(f"  DINNDeep:       {r_deep['losses'][-1]:.4e}")

print("\nRecovered Carroll-6 means (11-target 5-PFT + GLODAP-hybrid loss):")
print(f"  {'param':<11s} {'DINN baseline':>16s} {'DINNDeep':>16s} {'Carroll publ.':>15s}")
for i, name in enumerate(PARAM_NAMES):
    p_b = r_baseline["params_final"][i].numpy()[ocean_mask].mean()
    p_d = r_deep["params_final"][i].numpy()[ocean_mask].mean()
    pub = float(CARROLL_VALUES[i])
    print(f"  {name:<11s} {p_b:>16.4e} {p_d:>16.4e} {pub:>15.4e}")


def quality_band(rel_diff: float) -> str:
    if rel_diff <= 0.10:
        return "Excellent"
    if rel_diff <= 0.40:
        return "Calibration-grade"
    if rel_diff <= 1.00:
        return "Loose"
    return "Drifted"


print("\n=== GOAL: DINN baseline recovery vs Carroll's published Green's-functions optima ===")
print(f"  {'param':<11s} {'recovered':>14s} {'Carroll publ.':>15s} {'|Δ|/Carroll':>14s}  {'band':<20s}")
b_band_counts = {"Excellent": 0, "Calibration-grade": 0, "Loose": 0, "Drifted": 0}
for i, name in enumerate(PARAM_NAMES):
    p_b = float(r_baseline["params_final"][i].numpy()[ocean_mask].mean())
    pub = float(CARROLL_VALUES[i])
    rel = abs(p_b - pub) / abs(pub)
    band = quality_band(rel)
    b_band_counts[band] += 1
    print(f"  {name:<11s} {p_b:>14.4e} {pub:>15.4e} {rel:>14.3f}  {band:<20s}")
b_hit = b_band_counts["Excellent"] + b_band_counts["Calibration-grade"]
print(f"\n  -> DINN baseline: {b_hit} of 6 params at calibration-grade or better "
      f"(<= 40% off Carroll). Band breakdown: {dict(b_band_counts)}.")
print(f"  Phase 2 + GLODAP success criterion (all 6 calibration-grade): "
      f"{'MET' if b_hit == 6 else f'PARTIAL ({b_hit}/6)'}")

print("\n=== GOAL: DINNDeep recovery vs Carroll's published Green's-functions optima ===")
print(f"  {'param':<11s} {'recovered':>14s} {'Carroll publ.':>15s} {'|Δ|/Carroll':>14s}  {'band':<20s}")
d_band_counts = {"Excellent": 0, "Calibration-grade": 0, "Loose": 0, "Drifted": 0}
for i, name in enumerate(PARAM_NAMES):
    p_d = float(r_deep["params_final"][i].numpy()[ocean_mask].mean())
    pub = float(CARROLL_VALUES[i])
    rel = abs(p_d - pub) / abs(pub)
    band = quality_band(rel)
    d_band_counts[band] += 1
    print(f"  {name:<11s} {p_d:>14.4e} {pub:>15.4e} {rel:>14.3f}  {band:<20s}")
d_hit = d_band_counts["Excellent"] + d_band_counts["Calibration-grade"]
print(f"\n  -> DINNDeep: {d_hit} of 6 params at calibration-grade or better. "
      f"Band breakdown: {dict(d_band_counts)}.")
'''))

    # --- Cell 7: figures --------------------------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 5. Figures — target vs prediction (DIC + ALK = GLODAP real obs; rest = Darwin)
'''))

    cells.append(nbf.v4.new_code_cell(r'''tracers_to_plot = [
    ("FeT (Darwin)",          fet_binned,                 r_baseline["dfe_final"]),
    ("Chl1 diatoms (Darwin)", chl_per_pft["Chl1"],        r_baseline["p_diatom_final"]),
    ("Chl2 lge euks (Darwin)",chl_per_pft["Chl2"],        r_baseline["p_lge_final"]),
    ("Chl3 Syn (Darwin)",     chl_per_pft["Chl3"],        r_baseline["p_syn_final"]),
    ("Chl4 Pro-LL (Darwin)",  chl_per_pft["Chl4"],        r_baseline["p_proLL_final"]),
    ("Chl5 Pro-HL (Darwin)",  chl_per_pft["Chl5"],        r_baseline["p_proHL_final"]),
    ("POC (Darwin)",          poc_binned,                 r_baseline["poc_final"]),
    ("PIC (Darwin)",          pic_binned,                 r_baseline["pic_final"]),
    ("DIC (GLODAP real obs)", dic_binned,                 r_baseline["dic_final"]),
    ("ALK (GLODAP real obs)", alk_binned,                 r_baseline["alk_final"]),
    ("CO2_flux (Darwin)",     co2_flux_obs,               r_baseline["co2_flux_final"]),
]

fig, axes = plt.subplots(len(tracers_to_plot), 3, figsize=(13, 3 * len(tracers_to_plot)))
for row, (name, target, pred) in enumerate(tracers_to_plot):
    target_plot = np.where(ocean_mask, target, np.nan)
    pred_plot = np.where(ocean_mask, pred, np.nan)
    diff = pred_plot - target_plot

    vmin, vmax = np.nanpercentile(target_plot, [5, 95])
    im0 = axes[row, 0].imshow(target_plot, vmin=vmin, vmax=vmax, cmap="viridis",
                              origin="lower", aspect="auto")
    axes[row, 0].set_title(f"{name} — target")
    plt.colorbar(im0, ax=axes[row, 0], fraction=0.04)
    im1 = axes[row, 1].imshow(pred_plot, vmin=vmin, vmax=vmax, cmap="viridis",
                              origin="lower", aspect="auto")
    axes[row, 1].set_title(f"{name} — DINN-baseline pred")
    plt.colorbar(im1, ax=axes[row, 1], fraction=0.04)
    dmax = np.nanmax(np.abs(diff)) or 1.0
    im2 = axes[row, 2].imshow(diff, vmin=-dmax, vmax=dmax, cmap="RdBu_r",
                              origin="lower", aspect="auto")
    axes[row, 2].set_title(f"{name} — diff (pred − target)")
    plt.colorbar(im2, ax=axes[row, 2], fraction=0.04)

plt.tight_layout()
plt.show()
'''))

    # --- Cell 8: interpretation -------------------------------------------
    cells.append(nbf.v4.new_markdown_cell(r'''## 6. Interpretation — did combining the 5-PFT box with real-obs DIC/ALK reach the Carroll goal?

The two interventions stack: the 5-PFT box gives each Carroll-6 parameter a single specific PFT to govern (resolving the "Smallgrow averages 3 species" aliasing that v2.0 and Phase 1 both hit), and the GLODAP DIC + ALK targets give the carbonate budget a more realistic constraint than Darwin's internal self-consistent fields.

**If all 6 land in Calibration-grade (≤ 40% off Carroll):** the differentiable parameter learner, trained against real observations where available, has caught Carroll's classical Green's-functions calibration. This is the v2.2 deliverable that makes "DarwinDiff recovers BGC parameters from observations" defensible.

**If a subset stays in Loose / Drifted:** identify which dynamics aren't constrained yet by the current 11-target set. Likely follow-ups:
- Per-PFT half-saturations / mortalities (v2.2.1) — Dutkiewicz 2009 Table 1 values
- GEOTRACES iron observations (v2.3 / Phase 3) — direct iron constraint to replace Darwin's FeT
- Ocean color satellite Chl (v2.2.1) — per-PFT Chl validation against retrieved species

This notebook's headline numbers feed `docs/findings/v2.2_phase2_glodap_combo.md` (created on commit).
'''))

    nb["cells"] = cells
    nb["metadata"] = {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.11"},
    }

    out = Path(__file__).resolve().parent.parent / "notebooks" / "24_5pft_box_glodap_hybrid_eqpac.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Wrote: {out}")


if __name__ == "__main__":
    main()
