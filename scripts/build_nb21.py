# -*- coding: utf-8 -*-
"""Build notebooks/21_carbonate_block_cv.ipynb via nbformat.

Block cross-validation check on the 7-tracer carbonate setup from nb20.
Mirrors nb16's CV pattern (western 2/3 train, eastern 1/3 test) but applied
to the new 7-tracer joint loss.

Headline question: does adding carbonate (DIC + ALK + CO2_flux) reduce
nb16's block hold-out gap (DINNDeep + FeT-only gave r=0.301 on eastern
test block), or is the extrapolation limit independent of the loss
structure?

Run: uv run python scripts/build_nb21.py
"""
from __future__ import annotations

from pathlib import Path

import nbformat as nbf


def main() -> None:
    nb = nbf.v4.new_notebook()
    cells: list = []

    cells.append(nbf.v4.new_markdown_cell(r'''# Notebook 21 — Block cross-validation of the 7-tracer carbonate setup — Track 1 v2.0

**Goal.** nb16 showed DINNDeep's r=1.000 full-AOI fit on Eq Pac FeT was *interpolation only*: random 80/20 hold-out gave r=0.995 (passes), but western 2/3 train → eastern 1/3 test gave r=**0.301** (fails extrapolation). That was with single-target FeT loss.

**Question for nb21:** does adding the carbonate cycle as joint-loss targets (DIC + ALK + CO₂ flux on top of nb16's setup, the same 7-tracer carbonate setup nb20 used at the full AOI) change the block hold-out result? Two paths:
- **YES (block r improves)** → more constraint signals help extrapolation, not just identifiability. Carbonate is a structural fix, not just an iron-pair fix.
- **NO (block r stays low)** → the extrapolation limit is independent of loss structure; it's about the per-cell architecture's lack of spatial inductive bias. Cluster-scale multi-basin training is the path forward.

**Methodology (mirrors nb16):**
- Same AOI (Eq Pac), same architectures (DINN baseline + DINNDeep), same 7-tracer carbonate setup as nb20
- Western 2/3 of longitude indices → train; eastern 1/3 → held-out test
- **Target z-scores computed from TRAIN cells only** (the leak Codex caught in nb16's first pass)
- Per-tracer r evaluated on both train + test masks
- Compare DINN-baseline test r and DINNDeep test r vs nb16's 0.301

**Builds on:** nb16 (block-CV methodology), nb20 (7-tracer carbonate setup).
'''))

    cells.append(nbf.v4.new_code_cell(r'''import os
import time
from pathlib import Path

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
    carroll6_carbonate_integrate,
)
from darwindiff.diagnostics import format_pearson, safe_pearson_r
from darwindiff.ecco_darwin_loader import (
    EQUATORIAL_PACIFIC_AOI,
    open_bin_average,
    subset_aoi,
    time_mean,
    total_chlorophyll,
)
from darwindiff.llc270_loader import bin_native_tracer_to_1deg
from darwindiff.networks import DINN, DINNDeep

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")
if device == "cuda":
    print(f"GPU: {torch.cuda.get_device_name(0)}")

AOI = EQUATORIAL_PACIFIC_AOI
print(f"AOI: {AOI.name}")
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## 1. Load data + define the block split

Same loading as nb20. After the ocean mask is built, split longitude into western 2/3 (train) and eastern 1/3 (test) — the exact convention nb16 used.
'''))

    cells.append(nbf.v4.new_code_cell(r'''DATA_ROOT = Path(os.environ.get("DARWIN_DATA_ROOT", r"D:\\ecco_darwin_v5"))
BIN_AVG_PATH = str(DATA_ROOT / "bin_average" / "v05_ECCO-Darwin_bin_average_1x1_deg.nc")
MONTHLY_ROOT = str(DATA_ROOT / "output" / "monthly")
GRID_DIR = str(DATA_ROOT / "grid")

ds_bin = open_bin_average(BIN_AVG_PATH)
eqpac_clim = time_mean(subset_aoi(ds_bin, AOI))

sst = eqpac_clim.SST.values.astype(np.float64)
mld = eqpac_clim.mldDepth.values.astype(np.float64)
wind = eqpac_clim.windSpeed.values.astype(np.float64)
sss = eqpac_clim.SSS.values.astype(np.float64)
co2_flux_obs = eqpac_clim.CO2_flux.values.astype(np.float64) * 1.0e3  # mol -> mmol per m^2 per s
pco2_atm_field = eqpac_clim.apCO2.values.astype(np.float64) * 1.0e6   # atm -> uatm
chl_total = total_chlorophyll(eqpac_clim).values.astype(np.float64)
lat_1d = eqpac_clim.lat.values.astype(np.float64)
lat_2d = np.broadcast_to(lat_1d[:, None], sst.shape).astype(np.float64)

print(f"bin_average covariates loaded: shape = {sst.shape}")

print("Loading native LLC270 tracers (FeT, POC, PIC, DIC, ALK)...")
native_targets = {}
for var in ["FeT", "POC", "PIC", "DIC", "ALK"]:
    native_targets[var] = bin_native_tracer_to_1deg(
        monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable=var,
        lat_min=AOI.lat_min, lat_max=AOI.lat_max,
        lon_min=AOI.lon_min, lon_max=AOI.lon_max,
        iters="all",
    )
    print(f"  {var}: shape={native_targets[var].shape}, finite={int(np.isfinite(native_targets[var]).sum())}")

fet_binned = native_targets["FeT"]
poc_binned = native_targets["POC"]
pic_binned = native_targets["PIC"]
dic_binned = native_targets["DIC"]
alk_binned = native_targets["ALK"]

ocean_mask = (
    np.isfinite(sst) & np.isfinite(mld) & np.isfinite(wind) & np.isfinite(sss)
    & np.isfinite(pco2_atm_field) & np.isfinite(co2_flux_obs)
    & np.isfinite(chl_total)
    & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
    & np.isfinite(dic_binned) & np.isfinite(alk_binned)
)
n_total_ocean = int(ocean_mask.sum())
print(f"\nTotal ocean cells (all 7 targets + 5 forcing fields finite): {n_total_ocean}")

# === Block split: western 2/3 train, eastern 1/3 test (lon index) ===
H, W = sst.shape
lon_split = int(np.round(W * 2 / 3))   # column index where train ends
train_block = np.zeros_like(ocean_mask)
test_block = np.zeros_like(ocean_mask)
train_block[:, :lon_split] = True
test_block[:, lon_split:] = True

train_mask = ocean_mask & train_block
test_mask = ocean_mask & test_block
n_train = int(train_mask.sum())
n_test = int(test_mask.sum())
print(f"\nBlock split (lon col {lon_split} of {W}):")
print(f"  TRAIN (west 2/3): {n_train} ocean cells")
print(f"  TEST  (east 1/3): {n_test} ocean cells")
print(f"  TRAIN/TEST ratio: {n_train/n_test:.2f}")
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## 2. Build training tensors — z-score from TRAIN cells only

Critical detail (the bug Codex flagged in nb16's first pass): target statistics MUST come from train cells only, otherwise test-set information leaks into training via the z-score normalization. The loss mask is `train_mask`; r is evaluated separately on both masks.
'''))

    cells.append(nbf.v4.new_code_cell(r'''def normalize_covariate(arr, mask):
    """Z-score covariates over the OCEAN mask (covariates are model INPUTS, not targets,
    so leaking ocean-wide stats here doesn't bias the recovery)."""
    o = arr[mask]
    return np.where(mask, (arr - o.mean()) / max(o.std(), 1e-6), 0.0).astype(np.float32)


sst_norm = normalize_covariate(sst, ocean_mask)
mld_norm = normalize_covariate(mld, ocean_mask)
wind_norm = normalize_covariate(wind, ocean_mask)
lat_norm = normalize_covariate(lat_2d, ocean_mask)

env_1ch = torch.tensor(sst_norm, dtype=torch.float32).unsqueeze(0)
env_4ch = torch.tensor(np.stack([sst_norm, mld_norm, wind_norm, lat_norm], axis=0), dtype=torch.float32)

train_mask_t = torch.tensor(train_mask, dtype=torch.bool)
test_mask_t = torch.tensor(test_mask, dtype=torch.bool)

state0 = torch.tensor([
    5.0e-4, 1.0, 1.0, 0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
]).reshape(7, 1, 1).expand(7, H, W).contiguous()

# NaN-safe land-cell fill — see build_nb20.py for rationale (same fix).
T_field = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32))
S_field = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32))
wind_field = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32))
pco2_atm_t = torch.tensor(np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32))

env_1ch_dev = env_1ch.to(device)
env_4ch_dev = env_4ch.to(device)
state0_dev = state0.to(device)
train_mask_dev = train_mask_t.to(device)
test_mask_dev = test_mask_t.to(device)
bounds_dev = PARAM_BOUNDS.to(device)
T_dev = T_field.to(device)
S_dev = S_field.to(device)
wind_dev = wind_field.to(device)
pco2_atm_dev = pco2_atm_t.to(device)


def to_z_target_train_only(np_field):
    """Z-score using TRAIN-cell stats only — the nb16 fix that prevents test leak."""
    clean = np.where(ocean_mask, np_field, 1.0).astype(np.float32)
    t = torch.tensor(clean, dtype=torch.float32).to(device)
    o = t[train_mask_dev]
    mean = o.mean()
    std = o.std().clamp(min=1e-6)
    return (t - mean) / std, float(mean), float(std)


fet_z, fet_mean, fet_std = to_z_target_train_only(fet_binned)
chl_z, chl_mean, chl_std = to_z_target_train_only(chl_total)
poc_z, poc_mean, poc_std = to_z_target_train_only(poc_binned)
pic_z, pic_mean, pic_std = to_z_target_train_only(pic_binned)
dic_z, dic_mean, dic_std = to_z_target_train_only(dic_binned)
alk_z, alk_mean, alk_std = to_z_target_train_only(alk_binned)
co2_flux_z, co2_flux_mean_obs, co2_flux_std_obs = to_z_target_train_only(co2_flux_obs)

print("Z-score from TRAIN cells only (nb16 leak fix):")
for name, m, s in [("FeT", fet_mean, fet_std), ("Chl_total", chl_mean, chl_std),
                   ("POC", poc_mean, poc_std), ("PIC", pic_mean, pic_std),
                   ("DIC", dic_mean, dic_std), ("ALK", alk_mean, alk_std),
                   ("CO2_flux", co2_flux_mean_obs, co2_flux_std_obs)]:
    print(f"  {name:<10s}  train_mean = {m:.4e}, train_std = {s:.4e}")
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## 3. Train on west 2/3 only — same architectures, same hyperparameters as nb20
'''))

    cells.append(nbf.v4.new_code_cell(r'''DT, N_STEPS, N_EPOCHS = 0.25, 200, 1500


def train_on_block(net, env_dev, seed: int = 0) -> dict:
    """Same training loop as nb20 but with loss restricted to TRAIN cells."""
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(net.parameters(), lr=5e-3)
    losses = []
    if device == "cuda":
        torch.cuda.synchronize()
    t0 = time.time()
    for epoch in range(N_EPOCHS):
        optimizer.zero_grad()
        params = bounded_params(net(env_dev), bounds_dev)
        state = carroll6_carbonate_integrate(
            state0_dev, params, DT, N_STEPS,
            T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev, h_mld=H_MLD,
        )
        dfe_pred = state[0]
        phyto_pred = state[1] + state[2]
        poc_pred = state[3]
        pic_pred = state[4]
        dic_pred = state[5]
        alk_pred = state[6]
        carb_final = solve_carbonate(dic_pred, alk_pred, T_dev, S_dev)
        co2_flux_pred = co2_flux(carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev)

        def term(pred, target_z, mask=train_mask_dev):
            ocean = pred[mask]
            pred_z = (pred - ocean.mean()) / ocean.std().clamp(min=1e-6)
            residual = (pred_z - target_z) * mask.to(pred.dtype)
            return (residual ** 2).sum() / mask.sum().to(residual.dtype)

        l_fet = term(dfe_pred, fet_z)
        l_chl = term(phyto_pred, chl_z)
        l_poc = term(poc_pred, poc_z)
        l_pic = term(pic_pred, pic_z)
        l_dic = term(dic_pred, dic_z)
        l_alk = term(alk_pred, alk_z)
        l_co2 = term(co2_flux_pred, co2_flux_z)
        loss = (l_fet + l_chl + l_poc + l_pic + l_dic + l_alk + l_co2) / 7.0

        loss.backward()
        optimizer.step()
        losses.append(loss.item())
        if (epoch + 1) % 250 == 0:
            print(f"    epoch {epoch+1:4d}  loss = {loss.item():.4e}")
    if device == "cuda":
        torch.cuda.synchronize()
    elapsed = time.time() - t0
    with torch.no_grad():
        params_dev = bounded_params(net(env_dev), bounds_dev)
        state = carroll6_carbonate_integrate(
            state0_dev, params_dev, DT, N_STEPS,
            T=T_dev, S=S_dev, wind=wind_dev, pco2_atm=pco2_atm_dev, h_mld=H_MLD,
        )
        carb_final = solve_carbonate(state[5], state[6], T_dev, S_dev)
        co2_flux_pred_final = co2_flux(carb_final["pCO2"], pco2_atm_dev, wind_dev, T_dev, S_dev)
        return {
            "losses": losses,
            "params_final": params_dev.cpu(),
            "dfe_final": state[0].cpu().numpy(),
            "phyto_final": (state[1] + state[2]).cpu().numpy(),
            "poc_final": state[3].cpu().numpy(),
            "pic_final": state[4].cpu().numpy(),
            "dic_final": state[5].cpu().numpy(),
            "alk_final": state[6].cpu().numpy(),
            "co2_flux_final": co2_flux_pred_final.cpu().numpy(),
            "elapsed": elapsed,
        }


torch.manual_seed(0)
dinn_baseline = DINN(n_input_channels=1, hidden_dim=16, n_outputs=6).to(device)
n_b = sum(p.numel() for p in dinn_baseline.parameters())
print(f"=== DINN baseline + 7-tracer carbonate, WEST 2/3 train only ({n_b} params) ===")
r_baseline = train_on_block(dinn_baseline, env_1ch_dev)
print(f"  done in {r_baseline['elapsed']:.0f}s, loss {r_baseline['losses'][0]:.3e} -> {r_baseline['losses'][-1]:.3e}")

torch.manual_seed(0)
dinn_deep = DINNDeep(n_input_channels=4, hidden_dim=32, n_outputs=6, n_blocks=4).to(device)
n_d = sum(p.numel() for p in dinn_deep.parameters())
print(f"\n=== DINNDeep + 7-tracer carbonate, WEST 2/3 train only ({n_d} params) ===")
r_deep = train_on_block(dinn_deep, env_4ch_dev)
print(f"  done in {r_deep['elapsed']:.0f}s, loss {r_deep['losses'][0]:.3e} -> {r_deep['losses'][-1]:.3e}")
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## 4. Per-tracer r on TRAIN (in-sample) vs TEST (held-out east 1/3)

This is the headline result: how does test r compare to train r, and how does it compare to nb16's r=0.301 baseline?
'''))

    cells.append(nbf.v4.new_code_cell(r'''def r_on_mask(result: dict, mask: np.ndarray) -> dict:
    return {
        "FeT":      safe_pearson_r(result["dfe_final"][mask],      fet_binned[mask]),
        "Chl":      safe_pearson_r(result["phyto_final"][mask],    chl_total[mask]),
        "POC":      safe_pearson_r(result["poc_final"][mask],      poc_binned[mask]),
        "PIC":      safe_pearson_r(result["pic_final"][mask],      pic_binned[mask]),
        "DIC":      safe_pearson_r(result["dic_final"][mask],      dic_binned[mask]),
        "ALK":      safe_pearson_r(result["alk_final"][mask],      alk_binned[mask]),
        "CO2_flux": safe_pearson_r(result["co2_flux_final"][mask], co2_flux_obs[mask]),
    }


r_b_train = r_on_mask(r_baseline, train_mask)
r_b_test = r_on_mask(r_baseline, test_mask)
r_d_train = r_on_mask(r_deep, train_mask)
r_d_test = r_on_mask(r_deep, test_mask)

print("=" * 80)
print("BLOCK CROSS-VALIDATION: train (west 2/3) vs held-out test (east 1/3)")
print("=" * 80)
print(f"\nDINN baseline (SST-only, {n_b} params):")
print(f"  {'tracer':<10s}  {'train r':>16s}  {'test r':>16s}  {'gap (train-test)':>18s}")
for tracer in ["FeT", "Chl", "POC", "PIC", "DIC", "ALK", "CO2_flux"]:
    tr = r_b_train[tracer]
    te = r_b_test[tracer]
    gap = tr.r - te.r if np.isfinite(tr.r) and np.isfinite(te.r) else float("nan")
    print(f"  {tracer:<10s}  {format_pearson(tr, n_total=n_train):>16s}  "
          f"{format_pearson(te, n_total=n_test):>16s}  {gap:>18.3f}")

print(f"\nDINNDeep (4-channel, {n_d} params):")
print(f"  {'tracer':<10s}  {'train r':>16s}  {'test r':>16s}  {'gap (train-test)':>18s}")
for tracer in ["FeT", "Chl", "POC", "PIC", "DIC", "ALK", "CO2_flux"]:
    tr = r_d_train[tracer]
    te = r_d_test[tracer]
    gap = tr.r - te.r if np.isfinite(tr.r) and np.isfinite(te.r) else float("nan")
    print(f"  {tracer:<10s}  {format_pearson(tr, n_total=n_train):>16s}  "
          f"{format_pearson(te, n_total=n_test):>16s}  {gap:>18.3f}")

print("\n" + "=" * 80)
print("HEADLINE: test-set r comparison vs nb16 baseline")
print("=" * 80)
print(f"  nb16 (DINNDeep + FeT-only, block-CV test):                    r = 0.301")
print(f"  nb21 DINNDeep + 7-tracer carbonate, block-CV test FeT:        r = {r_d_test['FeT'].r:.3f}")
print(f"  nb21 DINNDeep + 7-tracer carbonate, block-CV test mean(7):    r = {np.nanmean([r_d_test[t].r for t in ['FeT','Chl','POC','PIC','DIC','ALK','CO2_flux']]):.3f}")
print()
print(f"  nb21 DINN baseline + 7-tracer carbonate, block-CV test FeT:   r = {r_b_test['FeT'].r:.3f}")
print(f"  nb21 DINN baseline + 7-tracer carbonate, block-CV test mean:  r = {np.nanmean([r_b_test[t].r for t in ['FeT','Chl','POC','PIC','DIC','ALK','CO2_flux']]):.3f}")
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## 5. Figure — west/east split with predictions, all 7 tracers
'''))

    cells.append(nbf.v4.new_code_cell(r'''tracers_to_plot = [
    ("FeT",      fet_binned,    r_deep["dfe_final"]),
    ("Chl_total", chl_total,    r_deep["phyto_final"]),
    ("POC",      poc_binned,    r_deep["poc_final"]),
    ("PIC",      pic_binned,    r_deep["pic_final"]),
    ("DIC",      dic_binned,    r_deep["dic_final"]),
    ("ALK",      alk_binned,    r_deep["alk_final"]),
    ("CO2_flux", co2_flux_obs,  r_deep["co2_flux_final"]),
]

fig, axes = plt.subplots(7, 2, figsize=(11, 22))
for row, (name, target, pred) in enumerate(tracers_to_plot):
    target_plot = np.where(ocean_mask, target, np.nan)
    pred_plot = np.where(ocean_mask, pred, np.nan)
    r_lookup = name if name != "Chl_total" else "Chl"

    im0 = axes[row, 0].imshow(target_plot, origin="lower", aspect="auto", cmap="viridis")
    axes[row, 0].axvline(lon_split - 0.5, color="white", lw=2, ls="--")
    axes[row, 0].set_title(f"Darwin {name} (dashed = train/test boundary)")
    plt.colorbar(im0, ax=axes[row, 0])

    rd_tr = r_d_train[r_lookup]
    rd_te = r_d_test[r_lookup]
    im1 = axes[row, 1].imshow(pred_plot, origin="lower", aspect="auto", cmap="plasma")
    axes[row, 1].axvline(lon_split - 0.5, color="white", lw=2, ls="--")
    axes[row, 1].set_title(f"DINNDeep pred — train r={rd_tr.r:.3f}, TEST r={rd_te.r:.3f}")
    plt.colorbar(im1, ax=axes[row, 1])

plt.tight_layout()
plt.show()

fig, ax = plt.subplots(1, 1, figsize=(9, 5))
ax.semilogy(r_baseline["losses"], label=f"DINN baseline ({n_b} params)", color="tab:red")
ax.semilogy(r_deep["losses"], label=f"DINNDeep ({n_d} params)", color="tab:green")
ax.set_title("Training loss (mean of 7 z-scored MSE, TRAIN cells only)")
ax.set_xlabel("epoch")
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.show()
'''))

    cells.append(nbf.v4.new_markdown_cell(r'''## What this notebook tests

Two simple comparisons after the block hold-out:

1. **Does carbonate close the nb16 gap?** nb16's DINNDeep + FeT-only block-CV test r was 0.301. If nb21's DINNDeep + 7-tracer carbonate test r (averaged across tracers, or specifically on FeT) lands well above 0.301, the extra constraint signals *do* help spatial extrapolation — carbonate is a structural fix, not just an iron-pair identifiability fix.
2. **Does DINN baseline extrapolate better than DINNDeep?** DINN baseline has 21× fewer parameters and can't memorize the field. It might generalize better across the train/test boundary (smaller train-test gap). If DINN-baseline test r > DINNDeep test r, that confirms the over-parametrization story from nb15-19.

**The v2.0 honest framing this enables:**

- If test r stays low (similar to nb16), the v2.0 paper text reads: "carbonate extension resolves the iron-pair identifiability problem (nb20) but does not resolve the spatial extrapolation problem (nb21); spatial extrapolation needs multi-basin training (cluster-gated)".
- If test r improves substantially, the v2.0 paper text reads: "carbonate extension resolves both the iron-pair identifiability problem AND meaningfully reduces the spatial extrapolation gap from nb16; full-AOI cluster-scale training is the next compute proposal."

Either result is publishable; the nb21 number determines which framing ships in v2.0.

**What's the same vs nb16:** AOI, block split convention, basic methodology, target-z-score-from-train-only fix.

**What's different vs nb16:** 7-tracer carbonate joint loss instead of FeT-only, DINN baseline alongside DINNDeep (nb16 was DINNDeep-only).
'''))

    nb.cells = cells
    nb.metadata["kernelspec"] = {
        "display_name": "Python 3",
        "language": "python",
        "name": "python3",
    }
    nb.metadata["language_info"] = {"name": "python", "version": "3.12"}

    out_path = Path("notebooks/21_carbonate_block_cv.ipynb")
    out_path.parent.mkdir(exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        nbf.write(nb, f)
    print(f"Wrote {out_path} with {len(cells)} cells")


if __name__ == "__main__":
    main()
