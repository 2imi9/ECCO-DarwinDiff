# -*- coding: utf-8 -*-
"""v3.0 multi-AOI joint training — shared Carroll-6 across regimes.

Trains a single shared DINN (per seed) jointly against the union of per-AOI
losses, with the v2.8 anchor configuration (Darwin IC + L2 POC observation
loss). The hypothesis under test is whether cross-regime constraint resolves
the bimodal (alpfe, scav_rat) degeneracy v2.8 surfaced in Eq Pacific alone
AND simultaneously recovers R_PICPOC (which only N Atl unblocks).

Default AOIs: Equatorial Pacific (HNLC) + North Atlantic Subpolar
(iron-replete). Designed to demonstrate the multi-AOI principle at minimum
complexity; 3-AOI (adding Southern Ocean) is a trivial extension once both
target caches exist on disk.

Env vars (same defaults as the v2.7 batched runner unless noted):
    AOIS                  comma-separated list (default "eqpac,natlsubpolar")
    NB23_SEEDS            seeds (default "0")
    GEOTRACES_W           surface GEOTRACES weight per AOI (default 0.3)
    GEOTRACES_SUB_W       subsurface GEOTRACES weight per AOI (default 1.0,
                          matching v2.8 anchor)
    NB23_PINN_WEIGHT      PINN drift weight per AOI (default 3.0)
    NB23_FET_WEIGHT       z-scored FeT weight per AOI (default 1.0)
    POC_SUB_W             L2 POC observation z-score weight (default 3.0,
                          v2.8 anchor)
    NB23_N_EPOCHS         training epochs (default 1500)
    DARWIN_IC             1 to load Darwin v5 pickup-derived ICs per AOI
                          (default 1 — v3.0 always uses Darwin ICs since the
                          v2.8 finding established them as essential)
    AOI_W_<KEY>           per-AOI loss weight override (default 1.0 each;
                          e.g. AOI_W_NATLSUBPOLAR=2.0 to upweight N Atl)
    PER_AOI_DINN          1 to build one independent DINN per (seed, AOI)
                          instead of a single shared DINN per seed across
                          AOIs (default 0 = legacy shared-DINN). The 5/6
                          ceiling diagnosed in PR #57 is hypothesized to be
                          the shared-MLP-per-cell constraint; per-AOI DINNs
                          break that by letting each regime fit independently.
    CONSISTENCY_LAMBDA    coefficient on the cross-AOI parameter-mean
                          consistency penalty (default 0.0; only active when
                          PER_AOI_DINN=1). Adds
                              lam * sum_p sum_aoi ((p_aoi - p_avg)/p_avg)^2
                          per seed to the total loss, where p_aoi is the
                          AOI-mean of parameter p and p_avg is the AOIs-mean
                          of those AOI-means. lam -> inf collapses to
                          shared-DINN behaviour; lam = 0 is fully decoupled.
    PIC_ABS_W             absolute-units MSE loss weight on surface PIC vs the
                          Darwin pic_binned target (default 0 = off).
    POC_ABS_W             absolute-units MSE loss weight on surface POC vs the
                          Darwin poc_binned target (default 0 = off). PAIRED
                          with PIC_ABS_W: anchoring POC_1 absolute pins
                          mort_total (since POC_1 ~ mort_total / W_SINK at
                          steady state); paired anchoring then forces
                          R_PICPOC ~ obs(PIC) / obs(POC) per cell, breaking
                          the R_PICPOC * mort_total scale degeneracy that
                          PR #59's PIC_ABS_W-alone sweep showed PIC alone
                          can't fix.
    POSI_W                absolute-units MSE loss on a steady-state biogenic
                          silica diagnostic vs GEOTRACES IDP2025 bSi (default 0
                          = off; see PR #60).
    F_CO2_ABS_W           absolute-units MSE loss on surface air-sea CO2 flux
                          vs Darwin CO2_flux. Activates K_WANNINKHOF and the
                          K1/K2 choice as real levers (the z-scored co2_flux
                          term alone cancels them); anchors F_CO2 magnitude and
                          couples DIC/ALK/R_PICPOC via calcite -> ALK -> pCO2.
                          Default 0 = off.
    COCCOLITH_ONLY        1 to restrict PIC production to Chl2 (large-eukaryote
                          / coccolithophore-proxy) mortality only, instead of
                          total mortality across all 5 PFTs. Physically correct
                          in Darwin 3 -- only coccolithophores produce calcite.
                          Needs PIC_ABS_W > 0 to anchor magnitude; otherwise
                          the optimizer finds a degenerate solution. Default 0
                          = legacy mort_total scaling.
    USE_MEHRBACH_K1K2     1 to swap Lueker 2000 K1/K2 (default) for Mehrbach
                          1973/Millero 1995 (MITgcm/Darwin's pkg/dic
                          formulation). Spatial T,S response differs from
                          Lueker (~0.4-1.0% pCO2 across surface ocean) and
                          survives z-scoring; default 0 = off.
    K_WANNINKHOF          gas-transfer velocity coefficient (default 0.251 =
                          Wanninkhof 2014; set to 0.337 for MITgcm/Darwin
                          alignment). NO-OP under the current z-score-only
                          F_CO2 loss because uniform rescaling cancels;
                          documented here for future absolute-F_CO2 anchors.
    DARWIN_DATA_ROOT      Darwin v05 data root (default D:\\ecco_darwin_v5)
    GEOTRACES_DATA_ROOT   IDP2025 NetCDF root (default D:\\geotraces)

Result JSON naming: ``run_v3.0_joint_<AOI_KEYS>_seed{S}_surf{X}_sub{Y}_pinn{Z}_pocsubW{P}.json``
where ``<AOI_KEYS>`` is the AOI list joined with hyphens (e.g.
``eqpac-natlsubpolar``). Per-AOI breakdowns + joint cell-mean recovery
are both written into the JSON.
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)
except Exception:
    pass

import numpy as np
import torch

_HERE = Path(__file__).resolve().parent
_SRC = _HERE.parent / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from darwindiff import carbonate as _carbonate
from darwindiff.carbonate import PCO2_ATM_DEFAULT, co2_flux, solve_carbonate

# Carbonate-constant alignment (orthogonal lever). USE_MEHRBACH_K1K2=1 swaps
# Lueker 2000 K1/K2 (PyCO2SYS default) for Mehrbach 1973/Millero 1995 (the
# formulation in MITgcm pkg/dic). The spatial T,S response of K1/K2 differs
# slightly between the two; unlike a uniform K_WANNINKHOF rescaling -- which
# cancels exactly under z-score loss -- this lever survives z-scoring. Empirical
# pCO2 offset across surface ocean: 0.4-1.0%, so the recovery effect is expected
# to be small but non-zero. Default 0 = Lueker (legacy reproduces).
_carbonate.USE_MEHRBACH_K1K2 = os.environ.get("USE_MEHRBACH_K1K2", "0") == "1"
# K_WANNINKHOF is exposed for completeness and absolute F_CO2 comparisons. Note
# this is a NO-OP under the current z-score-only F_CO2 loss term -- any uniform
# rescaling of co2_pred is removed by per-AOI z-scoring. Documented here so
# future absolute-F_CO2 anchor losses can use the same env var.
_K_WANNINKHOF_OVERRIDE = os.environ.get("K_WANNINKHOF")
if _K_WANNINKHOF_OVERRIDE is not None:
    _carbonate.K_WANNINKHOF = float(_K_WANNINKHOF_OVERRIDE)
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
from darwindiff import carroll6_5pft_2layer as _layer2
# Path C (session 2026-05-18): restrict PIC production to Chl2 (coccolithophore
# proxy) mortality only. Default OFF (legacy mort_total_1 reproduces). The
# integrator resolves this via a module-level bool at torch.compile trace time,
# so we set it HERE before any integrator import / compile.
_layer2.USE_COCCOLITH_ONLY_CALCITE = os.environ.get("COCCOLITH_ONLY", "0") == "1"
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
from darwindiff.gating import (
    GATING_POLICIES,
    apply_gate,
    build_gate_vectors,
    resolve_policy,
    validate_policy,
)
from darwindiff.silica import diagnostic_bsi_steady, R_SI_C, R_SI_DISSOL

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
CACHE_DIR = DATA_ROOT / "cache"

IC_CACHE_NAME = {
    "eqpac": "darwin_ic_cache.npz",
    "natlsubpolar": "darwin_ic_cache_natlsubpolar.npz",
}

AOIS_KEYS = [s.strip() for s in os.environ.get("AOIS", "eqpac,natlsubpolar").split(",") if s.strip()]
for k in AOIS_KEYS:
    if k not in AOI_BY_KEY:
        raise ValueError(f"AOIS contains unknown key {k!r}; valid: {sorted(AOI_BY_KEY)}")
N_AOIS = len(AOIS_KEYS)

_seeds_env = os.environ.get("NB23_SEEDS", os.environ.get("NB23_BATCH_SEEDS", "0"))
SEEDS: list[int] = [int(s.strip()) for s in _seeds_env.split(",") if s.strip()]
N_SEEDS = len(SEEDS)

FET_W = float(os.environ.get("NB23_FET_WEIGHT", "1.0"))
PINN_W = float(os.environ.get("NB23_PINN_WEIGHT", "3.0"))
PINN_TYPE = os.environ.get("NB23_PINN_TYPE", "drift").lower()
GEOTRACES_W = float(os.environ.get("GEOTRACES_W", "0.3"))
GEOTRACES_SUB_W = float(os.environ.get("GEOTRACES_SUB_W", "1.0"))
SUB_DEPTH_MIN = float(os.environ.get("GEOTRACES_SUB_DEPTH_MIN", "50.0"))
SUB_DEPTH_MAX = float(os.environ.get("GEOTRACES_SUB_DEPTH_MAX", "1000.0"))
N_EPOCHS = int(os.environ.get("NB23_N_EPOCHS", "1500"))
USE_DARWIN_IC = os.environ.get("DARWIN_IC", "1") == "1"   # default ON for v3.0
POC_SUB_W = float(os.environ.get("POC_SUB_W", "3.0"))      # default v2.8 anchor
# GEOTRACES_POC_SUB_W: weight on absolute-units MSE against real GEOTRACES
# POC observations (POC_LPT_CONC + POC_SPT_CONC) at subsurface depths,
# per-AOI. Default 0 = off. Pairs naturally with the v3.0 joint training
# to test whether real POC obs + cross-regime constraint together unblock
# both alpfe AND R_PICPOC.
GEOTRACES_POC_SUB_W = float(os.environ.get("GEOTRACES_POC_SUB_W", "0.0"))
# v3.0+: when set, append a per-AOI identity channel to the DINN env input
# so the shared MLP can produce regime-specific parameter mappings. Without
# this, the network has only SST to distinguish AOIs, and the joint loss
# settles into a compromise that can't separate alpfe from R_PICPOC across
# regimes. Defaults off (1-channel SST-only) so PR #48 behavior is unchanged.
USE_AOI_ID_CHANNEL = os.environ.get("AOI_ID_CHANNEL", "0") == "1"
# v3.0+: DINN hidden_dim override. Default 16 (matches v2.7/v2.8). Increase
# to 32/64 to test whether the shared-MLP capacity is the binding constraint
# on the regime-specific parameter mappings (diatomgraz especially).
DINN_HIDDEN_DIM = int(os.environ.get("DINN_HIDDEN_DIM", "16"))
# v3.0+: add MLD as a 3rd env channel (after SST + AOI ID) when set. MLD is
# regime-distinctive (winter convection in N Atl vs perennial-thermocline
# in Eq Pac) and biology-relevant.
USE_MLD_CHANNEL = os.environ.get("MLD_CHANNEL", "0") == "1"
# CHL1_W_EXTRA adds an EXTRA Chl1 (diatom chl) z-score loss term on top of
# the existing per-PFT chl_z term. Targets diatomgraz recovery: the 5/6
# seeds that consistently miss diatomgraz do so at ~0.75 off Carroll, and
# the existing 1/11-weighted Chl1 loss apparently isn't pulling hard
# enough. Default 0 = no extra term; existing v3.0 JSONs reproduce.
CHL1_W_EXTRA = float(os.environ.get("CHL1_W_EXTRA", "0.0"))
# v3.0+: per-AOI DINNs with cross-AOI consistency penalty. PER_AOI_DINN=1
# builds N_AOIS * N_SEEDS independent DINNs (each (seed, AOI) pair gets its
# own net) instead of N_SEEDS shared DINNs applied across AOIs. The
# CONSISTENCY_LAMBDA penalty (only meaningful when PER_AOI_DINN=1) is
# computed as the squared relative deviation of each AOI's parameter mean
# from the AOIs-averaged mean, summed across parameters and AOIs. Larger
# lambda pulls per-AOI parameter means toward agreement (-> shared DINN in
# the limit); zero leaves them fully decoupled. Hypothesis: small positive
# lambda lets each regime fit its preferred parameters while staying in the
# same neighborhood, breaking the 5/6 shared-MLP architectural ceiling.
USE_PER_AOI_DINN = os.environ.get("PER_AOI_DINN", "0") == "1"
CONSISTENCY_LAMBDA = float(os.environ.get("CONSISTENCY_LAMBDA", "0.0"))
# PIC_ABS_W: absolute-units MSE loss weight on surface PIC against the Darwin
# pic_binned target. The existing pic_z term (line ~660) constrains spatial
# pattern only; with z-score normalisation the per-cell R_PICPOC and biomass
# scale are jointly free (any uniform scaling cancels). PR #58 diagnosed this
# as the cause of R_PICPOC staying ~3x below Carroll across both regimes:
# both AOIs collapse to the same biomass-degenerate value. Adding the
# absolute term anchors per-cell PIC magnitude, pinning R_PICPOC * mort_total.
# Default 0 = off (legacy behaviour reproduces).
PIC_ABS_W = float(os.environ.get("PIC_ABS_W", "0.0"))
# POC_ABS_W: PAIRED anchor on surface POC absolute magnitude. Without this,
# PIC_ABS_W alone only constrains the product R_PICPOC * mort_total (PR #59's
# negative result). POC anchors mort_total independently (steady-state
# POC_1 ~ mort_total / W_SINK), so the pair forces R_PICPOC ~ obs(PIC)/obs(POC)
# per cell. Default 0 = off.
POC_ABS_W = float(os.environ.get("POC_ABS_W", "0.0"))
# POSI_W: absolute-units MSE loss on a steady-state biogenic-silica
# diagnostic (mmol Si / m^3) against the surface GEOTRACES IDP2025 bSi
# observation (bSi_LPT_CONC + bSi_SPT_CONC, QC 49/50, depth <= 50 m). bSi
# is produced only by diatoms, so its absolute magnitude pins
# `diatomgraz` * G0_GRAZE * P_diatom -- the only Carroll-6 parameter that
# enters silica production directly. Targets the v3.0 5/6-ceiling
# diagnosis (diatomgraz binding) from `notebooks/32_*`. Default 0 = off
# (legacy reproduces).
POSI_W = float(os.environ.get("POSI_W", "0.0"))
# F_CO2_ABS_W: absolute-units MSE loss on surface air-sea CO2 flux against the
# Darwin CO2_flux output (mmol C / m^2 / s). The existing co2_flux term in `z`
# uses tb(co2_pred, co2_flux_z), which z-scores per AOI and cancels any uniform
# rescaling of co2_pred -- making K_WANNINKHOF a no-op there. The absolute term
# anchors F_CO2 magnitude, so K_WANNINKHOF and the K1/K2 choice (Lueker vs
# Mehrbach) become real levers via this loss. F_CO2 magnitude couples to DIC,
# ALK, R_PICPOC (calcite production reduces ALK -> raises pCO2 -> shifts flux),
# so this is the orthogonal anchor for the R_PICPOC + carbonate cluster.
# Default 0 = off.
F_CO2_ABS_W = float(os.environ.get("F_CO2_ABS_W", "0.0"))

# Per-AOI loss weights (default 1.0 each, mean-reduced per-AOI losses).
AOI_W = {k: float(os.environ.get(f"AOI_W_{k.upper()}", "1.0")) for k in AOIS_KEYS}

# Per-AOI parameter gating (Stage 1). GATING_POLICY selects which Carroll-6
# parameters learn from which AOI's loss (see darwindiff.gating). Default
# "ungated" reproduces pre-gating behaviour bitwise. Mutually exclusive with
# PER_AOI_DINN: gating routes per-parameter gradients within the ONE shared
# DINN, while PER_AOI_DINN gives each AOI its own network.
GATING_POLICY_SPEC = os.environ.get("GATING_POLICY", "ungated")
_gating_policy = resolve_policy(GATING_POLICY_SPEC)
validate_policy(_gating_policy, AOIS_KEYS)
USE_GATING = bool(_gating_policy)
if USE_GATING and USE_PER_AOI_DINN:
    raise ValueError(
        "GATING_POLICY and PER_AOI_DINN are mutually exclusive: gating routes "
        "per-parameter gradients within one shared DINN, while PER_AOI_DINN "
        "gives each AOI its own network. Pick one."
    )
gate_vectors = build_gate_vectors(_gating_policy, AOIS_KEYS, device=device)
if USE_GATING:
    print(f"Per-AOI gating ENABLED ({GATING_POLICY_SPEC}): "
          + "; ".join(f"{k}->{_gating_policy.get(k, [])}" for k in AOIS_KEYS))
else:
    print("Per-AOI gating: OFF (ungated baseline)")

DT = 0.25
N_STEPS = 200

print(f"AOIS: {AOIS_KEYS}  (joint training across {N_AOIS} AOIs)")
print(f"Per-AOI weights: {AOI_W}")
print(f"Seeds: {SEEDS} (N={N_SEEDS})")
print(f"Config: fet_w={FET_W}, pinn_w={PINN_W}, geo_surf_w={GEOTRACES_W}, "
      f"geo_sub_w={GEOTRACES_SUB_W}, poc_sub_w={POC_SUB_W}, darwin_ic={USE_DARWIN_IC}")
print(f"        epochs={N_EPOCHS}, subsurface depth: [{SUB_DEPTH_MIN}, {SUB_DEPTH_MAX}] m")
print()


# ============================== Per-AOI loader ============================

def _build_aoi_targets(aoi) -> dict:
    print(f"  building target cache from Darwin bin_average + LLC270 native for {aoi.name}...")
    ds_bin = open_bin_average(BIN_AVG_PATH)
    ds_aoi = subset_aoi(ds_bin, aoi)
    ds_avg_local = time_mean(ds_aoi)
    out = {
        "aoi_name": aoi.name,
        "aoi_bounds": (aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max),
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
            lat_min=aoi.lat_min, lat_max=aoi.lat_max,
            lon_min=aoi.lon_min, lon_max=aoi.lon_max,
            iters="all",
        )
    return out


def _load_or_build_target_cache(aoi) -> dict:
    cache_path = CACHE_DIR / f"eqpac_targets_{aoi.name.replace(' ', '_').lower()}.pt"
    expected_bounds = (aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
    if cache_path.is_file():
        try:
            cached = torch.load(cache_path, map_location="cpu", weights_only=False)
            if (cached.get("aoi_name") == aoi.name
                    and cached.get("aoi_bounds") == expected_bounds):
                print(f"  loaded target cache from {cache_path}")
                return cached
        except Exception as e:
            print(f"  cache load failed ({e}); rebuilding...")
    data = _build_aoi_targets(aoi)
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        torch.save(data, cache_path)
        print(f"  saved target cache to {cache_path}")
    except Exception as e:
        print(f"  [warn] could not save cache: {e}")
    return data


def load_aoi_bundle(aoi_key: str) -> dict:
    """Build everything per-AOI: tensors, masks, target z-scores, GEOTRACES,
    initial conditions. Returns a dict suitable for hot use in the training loop."""
    aoi = AOI_BY_KEY[aoi_key]
    print(f"\n=== Loading AOI bundle: {aoi_key} ({aoi.name}) ===")
    targets = _load_or_build_target_cache(aoi)

    sst = targets["sst"]; sss = targets["sss"]; wind = targets["wind"]
    mld = targets["mld"]
    pco2_atm_field = targets["pco2_atm_field"]
    chl_per_pft = targets["chl_per_pft"]
    fet_binned = targets["fet_binned"]
    poc_binned = targets["poc_binned"]
    pic_binned = targets["pic_binned"]
    dic_binned = targets["dic_binned"]
    alk_binned = targets["alk_binned"]
    co2_flux_obs = targets["co2_flux_obs"]

    H, W = sst.shape
    # ocean_mask: finite SST AND finite tracers (matching v2.7 runner logic).
    ocean_mask = (
        np.isfinite(sst) & np.isfinite(sss) & np.isfinite(wind)
        & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
        & np.isfinite(dic_binned) & np.isfinite(alk_binned)
    )
    n_ocean = int(ocean_mask.sum())
    print(f"  AOI shape: ({H}, {W}); ocean cells: {n_ocean}")

    # Env input for DINN (SST only, 1 channel). Defer z-scoring to a SHARED
    # scale across all AOIs (set below after all bundles are loaded), so the
    # network sees absolute-temperature contrast between regimes and can
    # differentiate per-AOI param predictions. Per-AOI z-scoring destroys
    # the very signal multi-AOI training is supposed to use.
    sst_raw_for_env = np.where(ocean_mask, sst, 15.0).astype(np.float32)
    env_1ch = sst_raw_for_env[None]  # [1, H, W] (will be z-scored shared after bundle load)
    # Stash MLD raw for the optional 3rd channel (shared-scaled after bundle load).
    mld_raw_for_env = np.where(ocean_mask & np.isfinite(mld), mld, 30.0).astype(np.float32)

    # Move everything to device.
    mask_dev = torch.tensor(ocean_mask, dtype=torch.bool).to(device)
    mask_f = mask_dev.to(torch.float32)
    n_ocean_f = mask_f.sum()
    env_1ch_dev = torch.tensor(env_1ch, dtype=torch.float32).to(device)
    T_dev = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32)).to(device)
    S_dev = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32)).to(device)
    wind_dev = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32)).to(device)
    pco2_atm_dev = torch.tensor(
        np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)
    ).to(device)

    # z-score targets
    def to_z_target(field):
        clean = np.where(ocean_mask, field, 1.0).astype(np.float32)
        t = torch.tensor(clean, dtype=torch.float32).to(device)
        o = t[mask_dev]
        m = o.mean(); s = o.std().clamp(min=1e-6)
        return (t - m) / s
    fet_z = to_z_target(fet_binned)
    poc_z = to_z_target(poc_binned)
    pic_z = to_z_target(pic_binned)
    dic_z = to_z_target(dic_binned)
    alk_z = to_z_target(alk_binned)
    co2_flux_z = to_z_target(co2_flux_obs)
    chl_z = {f"Chl{i}": to_z_target(chl_per_pft[f"Chl{i}"]) for i in range(1, 6)}

    # Absolute-units surface PIC target (PIC_ABS_W). Masks to ocean cells with
    # finite, positive PIC. Always prepared (negligible memory) so the loss
    # path stays uniform; the loss contribution itself is gated on PIC_ABS_W > 0.
    pic_abs_mask_np = ocean_mask & np.isfinite(pic_binned) & (pic_binned > 0)
    pic_abs_target_np = np.where(pic_abs_mask_np, pic_binned, 0.0).astype(np.float32)
    pic_abs_target_t = torch.tensor(pic_abs_target_np).to(device)
    pic_abs_mask_t = torch.tensor(pic_abs_mask_np, dtype=torch.bool).to(device)
    pic_abs_mask_f = pic_abs_mask_t.to(torch.float32)
    n_pic_abs = int(pic_abs_mask_np.sum())
    n_pic_abs_f = pic_abs_mask_f.sum().clamp(min=1.0)
    if PIC_ABS_W > 0:
        if n_pic_abs > 0:
            print(f"  PIC absolute target: {n_pic_abs} cells, "
                  f"mean={float(pic_abs_target_t[pic_abs_mask_t].mean()):.4f} mmol C/m^3")
        else:
            print(f"  [warn] PIC_ABS_W={PIC_ABS_W} but no finite-positive PIC cells in AOI; loss term will be skipped")

    # Absolute-units surface POC target (POC_ABS_W). Paired with pic_abs to
    # anchor R_PICPOC; same prep pattern as PIC.
    poc_abs_mask_np = ocean_mask & np.isfinite(poc_binned) & (poc_binned > 0)
    poc_abs_target_np = np.where(poc_abs_mask_np, poc_binned, 0.0).astype(np.float32)
    poc_abs_target_t = torch.tensor(poc_abs_target_np).to(device)
    poc_abs_mask_t = torch.tensor(poc_abs_mask_np, dtype=torch.bool).to(device)
    poc_abs_mask_f = poc_abs_mask_t.to(torch.float32)
    n_poc_abs = int(poc_abs_mask_np.sum())
    n_poc_abs_f = poc_abs_mask_f.sum().clamp(min=1.0)
    if POC_ABS_W > 0:
        if n_poc_abs > 0:
            print(f"  POC absolute target: {n_poc_abs} cells, "
                  f"mean={float(poc_abs_target_t[poc_abs_mask_t].mean()):.4f} mmol C/m^3")
        else:
            print(f"  [warn] POC_ABS_W={POC_ABS_W} but no finite-positive POC cells in AOI; loss term will be skipped")

    # Absolute-units surface F_CO2 target (F_CO2_ABS_W). Unlike PIC/POC, F_CO2
    # can be either sign (ocean source = positive, sink = negative), so the mask
    # accepts any finite value -- no positivity gate.
    f_co2_abs_mask_np = ocean_mask & np.isfinite(co2_flux_obs)
    f_co2_abs_target_np = np.where(f_co2_abs_mask_np, co2_flux_obs, 0.0).astype(np.float32)
    f_co2_abs_target_t = torch.tensor(f_co2_abs_target_np).to(device)
    f_co2_abs_mask_t = torch.tensor(f_co2_abs_mask_np, dtype=torch.bool).to(device)
    f_co2_abs_mask_f = f_co2_abs_mask_t.to(torch.float32)
    n_f_co2_abs = int(f_co2_abs_mask_np.sum())
    n_f_co2_abs_f = f_co2_abs_mask_f.sum().clamp(min=1.0)
    if F_CO2_ABS_W > 0:
        if n_f_co2_abs > 0:
            print(f"  F_CO2 absolute target: {n_f_co2_abs} cells, "
                  f"mean={float(f_co2_abs_target_t[f_co2_abs_mask_t].mean()):.4e} mmol C/m^2/s")
        else:
            print(f"  [warn] F_CO2_ABS_W={F_CO2_ABS_W} but no finite F_CO2 cells in AOI; loss term will be skipped")

    # GEOTRACES per-AOI (surface + subsurface).
    print(f"  loading GEOTRACES IDP2025 (Eq Pac stations slice)...")
    geo_full = open_geotraces_bottle(GEOTRACES_NC)
    geo_aoi = subset_aoi_geotraces(geo_full, aoi)
    n_st = geo_aoi.sizes["N_STATIONS"]
    n_sa = geo_aoi.sizes["N_SAMPLES"]
    fe_vals = geo_aoi.Fe_D_CONC.values
    g_lats_all = np.broadcast_to(geo_aoi.latitude.values[:, None], (n_st, n_sa)).flatten()
    g_lons_all = np.broadcast_to(geo_aoi.longitude.values[:, None], (n_st, n_sa)).flatten()
    g_depths_all = geo_aoi.DEPTH.values.flatten()
    g_fe_all = fe_vals.flatten()
    g_qc_all = geo_aoi.Fe_D_CONC_qc.values.flatten()
    QC_GOOD = (49, 50)
    finite_basic = (
        np.isfinite(g_fe_all) & np.isfinite(g_lats_all) & np.isfinite(g_lons_all)
        & np.isfinite(g_depths_all)
        & np.isin(g_qc_all, np.array(QC_GOOD, dtype=g_qc_all.dtype))
    )
    DEPTH_MAX_SURFACE = 50.0
    darwin_lats = targets["darwin_lats"]; darwin_lons = targets["darwin_lons"]
    n_dlat = len(darwin_lats); n_dlon = len(darwin_lons)
    dlat_res = float(darwin_lats[1] - darwin_lats[0]) if n_dlat > 1 else 1.0
    dlon_res = float(darwin_lons[1] - darwin_lons[0]) if n_dlon > 1 else 1.0
    dlat_lo = darwin_lats[0] - dlat_res / 2.0
    dlon_lo = darwin_lons[0] - dlon_res / 2.0

    def bin_to_grid(keep_mask):
        lats = g_lats_all[keep_mask]; lons = g_lons_all[keep_mask]
        fe = g_fe_all[keep_mask] * 1025.0 * 1.0e-6  # nmol/kg -> mmol/m^3
        lat_idx = np.floor((lats - dlat_lo) / dlat_res).astype(np.int64)
        lon_idx = np.floor((lons - dlon_lo) / dlon_res).astype(np.int64)
        lat_idx = np.minimum(lat_idx, n_dlat - 1)
        lon_idx = np.minimum(lon_idx, n_dlon - 1)
        in_bounds = (lat_idx >= 0) & (lon_idx >= 0)
        target = np.zeros((n_dlat, n_dlon), dtype=np.float64)
        count = np.zeros((n_dlat, n_dlon), dtype=np.float64)
        np.add.at(target, (lat_idx[in_bounds], lon_idx[in_bounds]), fe[in_bounds])
        np.add.at(count, (lat_idx[in_bounds], lon_idx[in_bounds]), 1.0)
        loss_mask = (count > 0) & ocean_mask
        out_t = np.zeros((n_dlat, n_dlon), dtype=np.float32)
        nz = count > 0
        out_t[nz] = (target[nz] / count[nz]).astype(np.float32)
        return out_t, loss_mask

    surf_mask = finite_basic & (g_depths_all <= DEPTH_MAX_SURFACE)
    sub_mask = finite_basic & (g_depths_all >= SUB_DEPTH_MIN) & (g_depths_all <= SUB_DEPTH_MAX)
    geo_surf_target, geo_surf_loss_mask = bin_to_grid(surf_mask)
    geo_sub_target, geo_sub_loss_mask = bin_to_grid(sub_mask)
    print(f"  GEOTRACES bins in-AOI: surface={int(geo_surf_loss_mask.sum())}, "
          f"subsurface={int(geo_sub_loss_mask.sum())}")

    # GEOTRACES POC subsurface target (LPT + SPT) if GEOTRACES_POC_SUB_W > 0.
    geo_poc_target_t = None
    geo_poc_mask_t = None
    geo_poc_mask_f = None
    n_geo_poc_f = None
    n_geo_poc_in_ocean = 0
    if GEOTRACES_POC_SUB_W > 0:
        poc_lpt = geo_aoi.POC_LPT_CONC.values.flatten()
        poc_spt = geo_aoi.POC_SPT_CONC.values.flatten()
        poc_lpt_qc = geo_aoi.POC_LPT_CONC_qc.values.flatten()
        poc_spt_qc = geo_aoi.POC_SPT_CONC_qc.values.flatten()
        qc_good_arr = np.array(QC_GOOD)
        lpt_ok = (np.isfinite(poc_lpt)
                  & np.isin(poc_lpt_qc, qc_good_arr.astype(poc_lpt_qc.dtype))
                  & (poc_lpt > 0))
        spt_ok = (np.isfinite(poc_spt)
                  & np.isin(poc_spt_qc, qc_good_arr.astype(poc_spt_qc.dtype))
                  & (poc_spt > 0))
        poc_total = np.where(lpt_ok, poc_lpt, 0.0) + np.where(spt_ok, poc_spt, 0.0)
        poc_any = lpt_ok | spt_ok
        poc_keep = (
            poc_any & np.isfinite(g_lats_all) & np.isfinite(g_lons_all)
            & np.isfinite(g_depths_all)
            & (g_depths_all > SUB_DEPTH_MIN) & (g_depths_all <= SUB_DEPTH_MAX)
        )
        # Bin POC (umol C/kg -> mmol C/m^3 via *1.025).
        def bin_poc(keep):
            lats = g_lats_all[keep]; lons = g_lons_all[keep]
            poc = poc_total[keep] * 1025.0 * 1.0e-3
            lat_idx = np.floor((lats - dlat_lo) / dlat_res).astype(np.int64)
            lon_idx = np.floor((lons - dlon_lo) / dlon_res).astype(np.int64)
            lat_idx = np.minimum(lat_idx, n_dlat - 1)
            lon_idx = np.minimum(lon_idx, n_dlon - 1)
            in_b = (lat_idx >= 0) & (lon_idx >= 0)
            target = np.zeros((n_dlat, n_dlon), dtype=np.float64)
            count = np.zeros((n_dlat, n_dlon), dtype=np.float64)
            np.add.at(target, (lat_idx[in_b], lon_idx[in_b]), poc[in_b])
            np.add.at(count, (lat_idx[in_b], lon_idx[in_b]), 1.0)
            lm = (count > 0) & ocean_mask
            out_t = np.zeros((n_dlat, n_dlon), dtype=np.float32)
            nz = count > 0
            out_t[nz] = (target[nz] / count[nz]).astype(np.float32)
            return out_t, lm
        geo_poc_target_np, geo_poc_loss_mask = bin_poc(poc_keep)
        n_geo_poc_in_ocean = int(geo_poc_loss_mask.sum())
        print(f"  GEOTRACES POC in-AOI subsurface bins: {n_geo_poc_in_ocean}")
        if n_geo_poc_in_ocean > 0:
            geo_poc_target_t = torch.tensor(
                np.where(geo_poc_loss_mask, geo_poc_target_np, 0.0).astype(np.float32)
            ).to(device)
            geo_poc_mask_t = torch.tensor(geo_poc_loss_mask, dtype=torch.bool).to(device)
            geo_poc_mask_f = geo_poc_mask_t.to(torch.float32)
            n_geo_poc_f = geo_poc_mask_f.sum().clamp(min=1.0)

    # GEOTRACES surface biogenic-silica target (bSi_LPT + bSi_SPT) if POSI_W > 0.
    # Mirrors the POC pattern but at SURFACE depth (<= 50 m) since the silica
    # diagnostic bsi_1 is the surface bSi field. nmol Si/kg -> mmol Si/m^3 via
    # x rho_sw x 1e-6 (same unit convention as iron).
    posi_target_t = None
    posi_mask_t = None
    posi_mask_f = None
    n_posi_f = None
    n_posi_in_ocean = 0
    if POSI_W > 0:
        bsi_lpt = geo_aoi.bSi_LPT_CONC.values.flatten() if "bSi_LPT_CONC" in geo_aoi else None
        bsi_spt = geo_aoi.bSi_SPT_CONC.values.flatten() if "bSi_SPT_CONC" in geo_aoi else None
        if bsi_lpt is None and bsi_spt is None:
            print("  [warn] POSI_W>0 but neither bSi_LPT_CONC nor bSi_SPT_CONC present in GEOTRACES; skipping")
        else:
            qc_good_arr = np.array(QC_GOOD)
            def _bsi_keep(vals, qc_name):
                qc = geo_aoi[qc_name].values.flatten() if qc_name in geo_aoi else None
                ok = np.isfinite(vals) & (vals > 0)
                if qc is not None:
                    ok = ok & np.isin(qc, qc_good_arr.astype(qc.dtype))
                return ok
            lpt_ok = _bsi_keep(bsi_lpt, "bSi_LPT_CONC_qc") if bsi_lpt is not None else np.zeros(len(bsi_spt), dtype=bool)
            spt_ok = _bsi_keep(bsi_spt, "bSi_SPT_CONC_qc") if bsi_spt is not None else np.zeros(len(bsi_lpt), dtype=bool)
            bsi_total = (
                (np.where(lpt_ok, bsi_lpt, 0.0) if bsi_lpt is not None else 0.0)
                + (np.where(spt_ok, bsi_spt, 0.0) if bsi_spt is not None else 0.0)
            )
            bsi_any = lpt_ok | spt_ok
            DEPTH_MAX_POSI = float(os.environ.get("POSI_DEPTH_MAX", "50.0"))
            posi_keep = (
                bsi_any & np.isfinite(g_lats_all) & np.isfinite(g_lons_all)
                & np.isfinite(g_depths_all) & (g_depths_all <= DEPTH_MAX_POSI)
            )
            # nmol Si/kg -> mmol Si/m^3 via rho_sw x 1e-6 = 1025 x 1e-6 = 1.025e-3.
            def bin_bsi(keep):
                lats = g_lats_all[keep]; lons = g_lons_all[keep]
                bsi = bsi_total[keep] * 1025.0 * 1.0e-6
                lat_idx = np.floor((lats - dlat_lo) / dlat_res).astype(np.int64)
                lon_idx = np.floor((lons - dlon_lo) / dlon_res).astype(np.int64)
                lat_idx = np.minimum(lat_idx, n_dlat - 1)
                lon_idx = np.minimum(lon_idx, n_dlon - 1)
                in_b = (lat_idx >= 0) & (lon_idx >= 0)
                target = np.zeros((n_dlat, n_dlon), dtype=np.float64)
                count = np.zeros((n_dlat, n_dlon), dtype=np.float64)
                np.add.at(target, (lat_idx[in_b], lon_idx[in_b]), bsi[in_b])
                np.add.at(count, (lat_idx[in_b], lon_idx[in_b]), 1.0)
                lm = (count > 0) & ocean_mask
                out_t = np.zeros((n_dlat, n_dlon), dtype=np.float32)
                nz = count > 0
                out_t[nz] = (target[nz] / count[nz]).astype(np.float32)
                return out_t, lm
            posi_target_np, posi_loss_mask = bin_bsi(posi_keep)
            n_posi_in_ocean = int(posi_loss_mask.sum())
            print(f"  GEOTRACES bSi in-AOI surface bins (depth <= {DEPTH_MAX_POSI}m): {n_posi_in_ocean}, "
                  f"mean target = {float(posi_target_np[posi_loss_mask].mean()) if n_posi_in_ocean > 0 else 0:.4g} mmol Si/m^3")
            if n_posi_in_ocean > 0:
                posi_target_t = torch.tensor(
                    np.where(posi_loss_mask, posi_target_np, 0.0).astype(np.float32)
                ).to(device)
                posi_mask_t = torch.tensor(posi_loss_mask, dtype=torch.bool).to(device)
                posi_mask_f = posi_mask_t.to(torch.float32)
                n_posi_f = posi_mask_f.sum().clamp(min=1.0)

    geo_surf_target_t = torch.tensor(
        np.where(geo_surf_loss_mask, geo_surf_target, 0.0).astype(np.float32)
    ).to(device)
    geo_surf_mask_t = torch.tensor(geo_surf_loss_mask, dtype=torch.bool).to(device)
    geo_surf_mask_f = geo_surf_mask_t.to(torch.float32)
    n_geo_surf_f = geo_surf_mask_f.sum().clamp(min=1.0)

    geo_sub_target_t = torch.tensor(
        np.where(geo_sub_loss_mask, geo_sub_target, 0.0).astype(np.float32)
    ).to(device)
    geo_sub_mask_t = torch.tensor(geo_sub_loss_mask, dtype=torch.bool).to(device)
    geo_sub_mask_f = geo_sub_mask_t.to(torch.float32)
    n_geo_sub_f = geo_sub_mask_f.sum().clamp(min=1.0)

    # Initial state: literature defaults, optionally overridden by Darwin IC cache.
    LIT_IC = [
        5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
        0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
        5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
    ]
    state0_hw = torch.tensor(
        LIT_IC, dtype=torch.float32
    ).reshape(N_TRACERS_2LAYER, 1, 1).expand(N_TRACERS_2LAYER, H, W).clone()

    poc_l2_z = None
    if USE_DARWIN_IC:
        if aoi_key not in IC_CACHE_NAME:
            raise KeyError(
                f"No Darwin IC cache configured for AOI {aoi_key!r}. "
                f"AOIs with caches: {sorted(IC_CACHE_NAME)}. "
                f"To add: build a cache with "
                f"`CACHE_NAME=darwin_ic_cache_{aoi_key}.npz "
                f"DARWIN_AOI={aoi_key} python scripts/build_darwin_ic_cache.py`, "
                f"then add {{{aoi_key!r}: 'darwin_ic_cache_{aoi_key}.npz'}} to "
                f"IC_CACHE_NAME in scripts/run_v3.0_joint_multi_aoi.py."
            )
        ic_cache_name = IC_CACHE_NAME[aoi_key]
        ic_cache_path = _HERE / ic_cache_name
        if not ic_cache_path.is_file():
            raise FileNotFoundError(
                f"Darwin IC cache not found at {ic_cache_path}. "
                f"Run `CACHE_NAME={ic_cache_name} DARWIN_AOI={aoi_key} "
                f"python scripts/build_darwin_ic_cache.py` first."
            )
        print(f"  loading Darwin IC cache {ic_cache_name}")
        _ic = np.load(ic_cache_path)
        ic_overrides = [
            (I_DFE_1, "FeT_L1"), (I_POC_1, "POC_L1"), (I_PIC_1, "PIC_L1"),
            (I_DIC_1, "DIC_L1"), (I_ALK_1, "ALK_L1"),
            (I_DFE_2, "FeT_L2"), (I_POC_2, "POC_L2"), (I_PIC_2, "PIC_L2"),
            (I_DIC_2, "DIC_L2"), (I_ALK_2, "ALK_L2"),
        ]
        for state_idx, key in ic_overrides:
            field = _ic[key]
            if field.shape != (H, W):
                raise ValueError(f"IC field {key!r} shape {field.shape} != ({H}, {W})")
            field_safe = np.where(np.isfinite(field), field, LIT_IC[state_idx]).astype(np.float32)
            if state_idx in (I_DFE_1, I_DFE_2, I_POC_1, I_POC_2, I_PIC_1, I_PIC_2):
                field_safe = np.clip(field_safe, a_min=1e-10, a_max=None)
            state0_hw[state_idx] = torch.tensor(field_safe, dtype=torch.float32)
        if POC_SUB_W > 0:
            poc_l2_target = _ic["POC_L2"]
            poc_l2_z = to_z_target(np.where(np.isfinite(poc_l2_target), poc_l2_target,
                                            np.nanmean(poc_l2_target)).astype(np.float32))

    state0_per_seed = state0_hw.unsqueeze(1).expand(
        N_TRACERS_2LAYER, N_SEEDS, H, W
    ).contiguous().to(device)

    return {
        "key": aoi_key, "aoi": aoi, "H": H, "W": W,
        "ocean_mask": ocean_mask, "n_ocean": n_ocean,
        "mask_dev": mask_dev, "mask_f": mask_f, "n_ocean_f": n_ocean_f,
        "env_1ch_dev": env_1ch_dev,
        "mld_raw_for_env": mld_raw_for_env,
        "T_dev": T_dev, "S_dev": S_dev, "wind_dev": wind_dev, "pco2_atm_dev": pco2_atm_dev,
        "fet_z": fet_z, "poc_z": poc_z, "pic_z": pic_z, "dic_z": dic_z, "alk_z": alk_z,
        "co2_flux_z": co2_flux_z, "chl_z": chl_z, "poc_l2_z": poc_l2_z,
        "geo_surf_target_t": geo_surf_target_t, "geo_surf_mask_t": geo_surf_mask_t,
        "geo_surf_mask_f": geo_surf_mask_f, "n_geo_surf_f": n_geo_surf_f,
        "geo_sub_target_t": geo_sub_target_t, "geo_sub_mask_t": geo_sub_mask_t,
        "geo_sub_mask_f": geo_sub_mask_f, "n_geo_sub_f": n_geo_sub_f,
        "n_geo_surf": int(geo_surf_loss_mask.sum()),
        "n_geo_sub": int(geo_sub_loss_mask.sum()),
        "geo_poc_target_t": geo_poc_target_t, "geo_poc_mask_t": geo_poc_mask_t,
        "geo_poc_mask_f": geo_poc_mask_f, "n_geo_poc_f": n_geo_poc_f,
        "n_geo_poc": n_geo_poc_in_ocean,
        "pic_abs_target_t": pic_abs_target_t, "pic_abs_mask_t": pic_abs_mask_t,
        "pic_abs_mask_f": pic_abs_mask_f, "n_pic_abs_f": n_pic_abs_f,
        "n_pic_abs": n_pic_abs,
        "poc_abs_target_t": poc_abs_target_t, "poc_abs_mask_t": poc_abs_mask_t,
        "poc_abs_mask_f": poc_abs_mask_f, "n_poc_abs_f": n_poc_abs_f,
        "n_poc_abs": n_poc_abs,
        "posi_target_t": posi_target_t, "posi_mask_t": posi_mask_t,
        "posi_mask_f": posi_mask_f, "n_posi_f": n_posi_f,
        "n_posi": n_posi_in_ocean,
        "f_co2_abs_target_t": f_co2_abs_target_t, "f_co2_abs_mask_t": f_co2_abs_mask_t,
        "f_co2_abs_mask_f": f_co2_abs_mask_f, "n_f_co2_abs_f": n_f_co2_abs_f,
        "n_f_co2_abs": n_f_co2_abs,
        "state0_per_seed": state0_per_seed,
        "weight": AOI_W[aoi_key],
    }


# Load all AOI bundles up-front.
bundles = [load_aoi_bundle(k) for k in AOIS_KEYS]
bounds_dev = PARAM_BOUNDS.to(device)

# Shared-scale SST z-score across all AOIs. Compute mean/std over the union
# of all ocean cells; apply the SAME (mean, std) to every AOI's env input.
# This preserves absolute-temperature contrast: Eq Pac z-scores positive
# (warm), N Atl z-scores negative (cold), so the DINN can differentiate.
_all_sst = []
for b in bundles:
    sst_np = b["env_1ch_dev"].cpu().numpy()[0]   # [H, W]
    mask_np = b["ocean_mask"]
    _all_sst.append(sst_np[mask_np])
_all_sst_flat = np.concatenate(_all_sst)
# NaN-safe stats: ocean_mask should exclude NaNs upstream, but if any
# bundle leaks a NaN in here, .mean()/.std() return NaN and `or 1.0`
# fails (NaN is truthy). Use nan-aware reductions defensively.
_shared_sst_mean = float(np.nanmean(_all_sst_flat))
_shared_sst_std_raw = float(np.nanstd(_all_sst_flat))
_shared_sst_std = _shared_sst_std_raw if (np.isfinite(_shared_sst_std_raw) and _shared_sst_std_raw > 0) else 1.0
print(f"\nShared-scale SST z-score: mean={_shared_sst_mean:.2f}, std={_shared_sst_std:.2f}")
# AOI identity scalars (centered around zero, evenly spaced):
# [-1, +1] for 2 AOIs; [-1, 0, +1] for 3; etc.
if USE_AOI_ID_CHANNEL:
    if N_AOIS == 1:
        aoi_id_scalars = [0.0]
    else:
        aoi_id_scalars = [-1.0 + 2.0 * i / (N_AOIS - 1) for i in range(N_AOIS)]
    print(f"AOI ID channel ENABLED: per-AOI scalars = {dict(zip(AOIS_KEYS, aoi_id_scalars))}")
else:
    aoi_id_scalars = [0.0] * N_AOIS

# Shared-scale MLD z-score (if MLD channel is enabled).
if USE_MLD_CHANNEL:
    _all_mld = []
    for b in bundles:
        _all_mld.append(b["mld_raw_for_env"][b["ocean_mask"]])
    _all_mld_flat = np.concatenate(_all_mld)
    _shared_mld_mean = float(np.nanmean(_all_mld_flat))
    _mld_std_raw = float(np.nanstd(_all_mld_flat))
    _shared_mld_std = _mld_std_raw if (np.isfinite(_mld_std_raw) and _mld_std_raw > 0) else 1.0
    print(f"Shared-scale MLD z-score: mean={_shared_mld_mean:.2f} m, std={_shared_mld_std:.2f} m")

n_input_channels = 1 + (1 if USE_AOI_ID_CHANNEL else 0) + (1 if USE_MLD_CHANNEL else 0)

for i, b in enumerate(bundles):
    sst_np = b["env_1ch_dev"].cpu().numpy()[0]
    sst_z = (sst_np - _shared_sst_mean) / _shared_sst_std
    sst_z = np.where(b["ocean_mask"], sst_z, 0.0).astype(np.float32)
    channels = [sst_z]
    extra_info = []
    if USE_AOI_ID_CHANNEL:
        aoi_id_field = np.full_like(sst_z, aoi_id_scalars[i], dtype=np.float32)
        aoi_id_field = np.where(b["ocean_mask"], aoi_id_field, 0.0).astype(np.float32)
        channels.append(aoi_id_field)
        extra_info.append(f"AOI_id={aoi_id_scalars[i]:+.1f}")
    if USE_MLD_CHANNEL:
        mld_z = (b["mld_raw_for_env"] - _shared_mld_mean) / _shared_mld_std
        mld_z = np.where(b["ocean_mask"], mld_z, 0.0).astype(np.float32)
        channels.append(mld_z)
        extra_info.append(f"MLD z-range [{mld_z[b['ocean_mask']].min():.2f}, "
                          f"{mld_z[b['ocean_mask']].max():.2f}]")
    env_arr = np.stack(channels, axis=0)
    b["env_1ch_dev"] = torch.tensor(env_arr, dtype=torch.float32).to(device)
    base = f"  {b['key']}: SST z-range [{sst_z[b['ocean_mask']].min():.2f}, {sst_z[b['ocean_mask']].max():.2f}]"
    print(base + ("  " + "  ".join(extra_info) if extra_info else ""))


# ============================== Networks (shared per seed) ===================

# Networks. Unified container nets_per_aoi[key] -> list of N_SEEDS DINNs.
# In legacy shared mode (PER_AOI_DINN=0), every AOI's entry is the SAME
# per-seed list (aliasing); the optimizer dedupes parameters by id() so the
# shared per-seed nets receive a single Adam-tracked parameter group, exactly
# matching prior behavior. In per-AOI mode each (seed, AOI) gets an
# independent DINN, seeded as (seed + aoi_idx * 10000) for determinism.
nets_per_aoi: dict[str, list[DINN]] = {}
if USE_PER_AOI_DINN:
    print(f"\nBuilding {N_SEEDS * N_AOIS} per-AOI DINN networks "
          f"(one per (seed, AOI); lambda_consistency={CONSISTENCY_LAMBDA})...")
    for aoi_idx, k in enumerate(AOIS_KEYS):
        nets_per_aoi[k] = []
        for s in SEEDS:
            torch.manual_seed(s + aoi_idx * 10000)
            n = DINN(n_input_channels=n_input_channels, hidden_dim=DINN_HIDDEN_DIM, n_outputs=6).to(device)
            nets_per_aoi[k].append(n)
else:
    print(f"\nBuilding {N_SEEDS} shared DINN networks (one per seed; applied to each AOI's env input)...")
    shared_nets: list[DINN] = []
    for s in SEEDS:
        torch.manual_seed(s)
        n = DINN(n_input_channels=n_input_channels, hidden_dim=DINN_HIDDEN_DIM, n_outputs=6).to(device)
        shared_nets.append(n)
    for k in AOIS_KEYS:
        nets_per_aoi[k] = shared_nets  # alias: all AOIs reference the same per-seed nets
print(f"  DINN: n_input_channels={n_input_channels}  hidden_dim={DINN_HIDDEN_DIM}  "
      f"(AOI_ID={USE_AOI_ID_CHANNEL}, MLD={USE_MLD_CHANNEL})")

all_params = []
seen_param_ids: set[int] = set()
for k in AOIS_KEYS:
    for n in nets_per_aoi[k]:
        for p in n.parameters():
            if id(p) not in seen_param_ids:
                seen_param_ids.add(id(p))
                all_params.append(p)
optimizer = torch.optim.Adam(all_params, lr=5e-3)

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


def _integrate(state0, params, dt, n_steps, T, S, wind, pco2_atm):
    from darwindiff.carroll6_5pft_2layer import H1, H2, KZ_M2_PER_DAY, R_REMIN
    state = state0
    for _ in range(n_steps):
        state = _compiled_step(state, params, dt, T, S, wind, pco2_atm,
                               H1, H2, KZ_M2_PER_DAY, R_REMIN)
    return state


# ============================== Batched losses (per AOI) ===================

def term_batched(pred_b: torch.Tensor, target_z: torch.Tensor,
                 mask_f: torch.Tensor, n_ocean_f: torch.Tensor,
                 bessel_div: int) -> torch.Tensor:
    pred_m = pred_b * mask_f[None]
    sums = pred_m.flatten(1).sum(dim=1)
    means = sums / n_ocean_f
    diff = (pred_b - means[:, None, None]) * mask_f[None]
    var = (diff ** 2).flatten(1).sum(dim=1) / bessel_div
    stds = var.sqrt().clamp(min=1e-6)
    pred_z = (pred_b - means[:, None, None]) / stds[:, None, None]
    residual = (pred_z - target_z[None]) * mask_f[None]
    return (residual ** 2).flatten(1).sum(dim=1) / n_ocean_f


def aoi_loss(bundle: dict, params_b: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """Compute per-seed loss for one AOI. Returns (loss [N_seeds], state [15, N_seeds, H, W])."""
    state0 = bundle["state0_per_seed"]
    state = _integrate(
        state0, params_b, DT, N_STEPS,
        T=bundle["T_dev"], S=bundle["S_dev"],
        wind=bundle["wind_dev"], pco2_atm=bundle["pco2_atm_dev"],
    )
    dfe1 = state[I_DFE_1]; dfe2 = state[I_DFE_2]
    poc = state[I_POC_1]; pic = state[I_PIC_1]; dic = state[I_DIC_1]; alk = state[I_ALK_1]
    p_diatom = state[I_DIATOM]; p_lge = state[I_LGE]
    p_syn = state[I_SYN]; p_proLL = state[I_PROLL]; p_proHL = state[I_PROHL]

    carb = solve_carbonate(dic, alk, bundle["T_dev"][None], bundle["S_dev"][None])
    co2_pred = co2_flux(carb["pCO2"], bundle["pco2_atm_dev"][None],
                        bundle["wind_dev"][None], bundle["T_dev"][None], bundle["S_dev"][None])

    mask_f = bundle["mask_f"]; n_ocean_f = bundle["n_ocean_f"]
    bessel_div = max(int(n_ocean_f.item()) - 1, 1)
    tb = lambda p, z: term_batched(p, z, mask_f, n_ocean_f, bessel_div)

    z = (
        FET_W * tb(dfe1, bundle["fet_z"])
        + tb(p_diatom, bundle["chl_z"]["Chl1"])
        + tb(p_lge,    bundle["chl_z"]["Chl2"])
        + tb(p_syn,    bundle["chl_z"]["Chl3"])
        + tb(p_proLL,  bundle["chl_z"]["Chl4"])
        + tb(p_proHL,  bundle["chl_z"]["Chl5"])
        + tb(poc,      bundle["poc_z"])
        + tb(pic,      bundle["pic_z"])
        + tb(dic,      bundle["dic_z"])
        + tb(alk,      bundle["alk_z"])
        + tb(co2_pred, bundle["co2_flux_z"])
    ) / (FET_W + 10.0)

    if PINN_W > 0:
        alpfe_b = params_b[0]; scav_rat_b = params_b[1]
        mu_proHL_b = params_b[2]; mu_lge_b = params_b[3]
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
        dDFe_dt = iron_source - iron_sink
        rel_rate = dDFe_dt / state[I_DFE_1].clamp(min=1e-10)
        l_pinn = ((rel_rate ** 2) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        z = z + PINN_W * l_pinn

    if GEOTRACES_W > 0 and bundle["n_geo_surf"] > 0:
        residual = (dfe1 - bundle["geo_surf_target_t"][None]) * bundle["geo_surf_mask_f"][None]
        scale = (bundle["geo_surf_target_t"][bundle["geo_surf_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_geo_surf_f"] / scale
        z = z + GEOTRACES_W * l

    if GEOTRACES_SUB_W > 0 and bundle["n_geo_sub"] > 0:
        residual = (dfe2 - bundle["geo_sub_target_t"][None]) * bundle["geo_sub_mask_f"][None]
        scale = (bundle["geo_sub_target_t"][bundle["geo_sub_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_geo_sub_f"] / scale
        z = z + GEOTRACES_SUB_W * l

    if POC_SUB_W > 0 and bundle["poc_l2_z"] is not None:
        l_poc_sub = tb(state[I_POC_2], bundle["poc_l2_z"])
        z = z + POC_SUB_W * l_poc_sub

    # CHL1_W_EXTRA: extra diatom-chl loss to amplify diatomgraz signal.
    # State[I_DIATOM] vs Darwin's Chl1 (z-scored over AOI ocean mask).
    if CHL1_W_EXTRA > 0:
        l_chl1_extra = tb(state[I_DIATOM], bundle["chl_z"]["Chl1"])
        z = z + CHL1_W_EXTRA * l_chl1_extra

    if GEOTRACES_POC_SUB_W > 0 and bundle["n_geo_poc"] > 0:
        residual = (state[I_POC_2] - bundle["geo_poc_target_t"][None]) * bundle["geo_poc_mask_f"][None]
        scale = (bundle["geo_poc_target_t"][bundle["geo_poc_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_geo_poc_f"] / scale
        z = z + GEOTRACES_POC_SUB_W * l

    # PIC absolute-units MSE on surface PIC vs Darwin pic_binned. Z-scored
    # PIC pattern is already in `z` above (tb(pic, bundle["pic_z"])); this
    # is the MAGNITUDE constraint that breaks the R_PICPOC x biomass
    # scale-degeneracy diagnosed in PR #58.
    if PIC_ABS_W > 0 and bundle["n_pic_abs"] > 0:
        residual = (pic - bundle["pic_abs_target_t"][None]) * bundle["pic_abs_mask_f"][None]
        scale = (bundle["pic_abs_target_t"][bundle["pic_abs_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_pic_abs_f"] / scale
        z = z + PIC_ABS_W * l

    # POC absolute-units MSE on surface POC -- paired anchor for PIC_ABS_W.
    # Anchors mort_total via POC_1 ~ mort_total / W_SINK; together with PIC
    # absolute, R_PICPOC ~ obs(PIC) / obs(POC) per cell.
    if POC_ABS_W > 0 and bundle["n_poc_abs"] > 0:
        residual = (poc - bundle["poc_abs_target_t"][None]) * bundle["poc_abs_mask_f"][None]
        scale = (bundle["poc_abs_target_t"][bundle["poc_abs_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_poc_abs_f"] / scale
        z = z + POC_ABS_W * l

    # POSi absolute-units MSE on a steady-state biogenic-silica diagnostic.
    # Compute bsi_1 = R_SI_C * (mort_diatom + graze_diatom) / W_SINK from the
    # integrated state's diatom biomass and the seed's per-cell diatomgraz
    # prediction. Only diatoms produce bSi, so g_diatom enters this term
    # directly via graze_diatom = g_diatom * G0_GRAZE * P_diatom. Compares to
    # surface GEOTRACES bSi obs (bSi_LPT + bSi_SPT, QC 49/50, depth <= 50 m).
    if POSI_W > 0 and bundle["n_posi"] > 0:
        g_diatom_b = params_b[4]   # params order: [alpfe, scav_rat, Smallgrow, Biggrow, diatomgraz, R_PICPOC]
        bsi_1_pred, _ = diagnostic_bsi_steady(p_diatom, g_diatom_b)
        residual = (bsi_1_pred - bundle["posi_target_t"][None]) * bundle["posi_mask_f"][None]
        scale = (bundle["posi_target_t"][bundle["posi_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_posi_f"] / scale
        z = z + POSI_W * l

    # F_CO2 absolute-units MSE on surface air-sea CO2 flux. The z-scored term
    # tb(co2_pred, co2_flux_z) above constrains spatial pattern only and cancels
    # any uniform rescaling (so K_WANNINKHOF and Lueker-vs-Mehrbach are no-ops
    # in z-space). This absolute term anchors the F_CO2 magnitude, making
    # carbonate-constant choices into real levers and coupling DIC/ALK/R_PICPOC
    # through the calcite -> ALK -> pCO2 chain.
    if F_CO2_ABS_W > 0 and bundle["n_f_co2_abs"] > 0:
        residual = (co2_pred - bundle["f_co2_abs_target_t"][None]) * bundle["f_co2_abs_mask_f"][None]
        scale = (bundle["f_co2_abs_target_t"][bundle["f_co2_abs_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_f_co2_abs_f"] / scale
        z = z + F_CO2_ABS_W * l

    return z, state


# ============================== Training ==================================

print(f"\n=== v3.0 joint training: {N_AOIS} AOIs, {N_SEEDS} seeds, {N_EPOCHS} epochs ===")
t0 = time.time()
loss_history = torch.full((N_EPOCHS, N_SEEDS), float("nan"), dtype=torch.float32, device=device)
per_aoi_history = {k: torch.full((N_EPOCHS, N_SEEDS), float("nan"),
                                  dtype=torch.float32, device=device) for k in AOIS_KEYS}

_apply_consistency_penalty = USE_PER_AOI_DINN and CONSISTENCY_LAMBDA > 0
for epoch in range(N_EPOCHS):
    optimizer.zero_grad()
    total_loss_per_seed = torch.zeros(N_SEEDS, device=device)

    # For each AOI, forward that AOI's nets (per seed) on its env input,
    # integrate, compute loss, accumulate weighted. In shared mode the
    # per-AOI lists alias the same set of per-seed nets (same parameters
    # touched across AOIs), reproducing prior behavior bit-identically.
    last_states_per_aoi = {}
    last_params_per_aoi = {}
    per_aoi_param_means = {} if _apply_consistency_penalty else None
    for bundle in bundles:
        env = bundle["env_1ch_dev"]
        aoi_nets = nets_per_aoi[bundle["key"]]
        per_seed_params = [bounded_params(net(env), bounds_dev) for net in aoi_nets]
        params_b = torch.stack(per_seed_params, dim=1)  # [6, N_seeds, H, W]
        # Stage 1 gating: route each parameter's gradient to only its AOI
        # loss(es). Straight-through, so forward values (hence the per-AOI
        # losses + the consistency penalty below) are bitwise identical to
        # ungated; only the backward pass is masked.
        params_for_loss = (
            apply_gate(params_b, gate_vectors[bundle["key"]]) if USE_GATING else params_b
        )
        aoi_l, state_final = aoi_loss(bundle, params_for_loss)
        total_loss_per_seed = total_loss_per_seed + bundle["weight"] * aoi_l
        per_aoi_history[bundle["key"]][epoch] = aoi_l.detach()
        last_states_per_aoi[bundle["key"]] = state_final.detach()
        last_params_per_aoi[bundle["key"]] = params_b.detach()
        if per_aoi_param_means is not None:
            mask_f = bundle["mask_f"]; n_ocean_f = bundle["n_ocean_f"]
            sums = (params_b * mask_f[None, None]).flatten(2).sum(dim=2)  # [6, N_seeds]
            per_aoi_param_means[bundle["key"]] = sums / n_ocean_f

    # Consistency penalty: sum_aoi sum_p ((mean_aoi_p - mean_avg_p) / mean_avg_p)^2
    # per seed, then scaled by CONSISTENCY_LAMBDA. For 2 AOIs this differs
    # from the literal (mean_A - mean_B)^2 / mean_avg^2 form by a factor of
    # 1/2 -- absorbed into the lambda scale chosen at sweep time. Generalizes
    # naturally to >2 AOIs once a 3rd AOI (e.g., SO Pacific) is added.
    if per_aoi_param_means is not None:
        stacked = torch.stack([per_aoi_param_means[k] for k in AOIS_KEYS], dim=0)
        # [N_AOIS, 6, N_seeds]
        mean_over_aois = stacked.mean(dim=0)  # [6, N_seeds]
        denom = mean_over_aois.abs().clamp(min=1e-30)
        rel_dev_sq = ((stacked - mean_over_aois[None]) / denom[None]) ** 2
        penalty_per_seed = rel_dev_sq.sum(dim=(0, 1))  # [N_seeds]
        total_loss_per_seed = total_loss_per_seed + CONSISTENCY_LAMBDA * penalty_per_seed

    total_loss = total_loss_per_seed.sum()
    total_loss.backward()
    optimizer.step()
    loss_history[epoch] = total_loss_per_seed.detach()

    if (epoch + 1) % 250 == 0 or epoch + 1 == N_EPOCHS:
        mean_l = float(total_loss_per_seed.mean().item())
        print(f"  epoch {epoch+1:4d}  per-seed joint loss: mean={mean_l:.3e}")

if device == "cuda":
    torch.cuda.synchronize()
elapsed = time.time() - t0
print(f"\nDone in {elapsed:.0f}s ({elapsed/N_SEEDS:.1f}s amortized per seed)")


# ============================== Recovery report ===========================

PARAM_NAMES = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
carroll_published = CARROLL_VALUES  # tensor of length 6

all_results = []
for seed_idx, seed in enumerate(SEEDS):
    print(f"\n=== Seed {seed} recovery ===")
    per_aoi_means = {}
    # Cache per-AOI per-cell sums + cell counts in one forward pass each,
    # then reuse for both per-AOI means and joint mean (Greptile P2 PR #48).
    weighted_sum = torch.zeros(6, device=device)
    weighted_count = torch.zeros((), device=device)
    for bundle in bundles:
        with torch.no_grad():
            net = nets_per_aoi[bundle["key"]][seed_idx]
            params_b = bounded_params(net(bundle["env_1ch_dev"]), bounds_dev)
        mask_f = bundle["mask_f"]
        n_ocean_f = bundle["n_ocean_f"]
        per_cell_sum = (params_b * mask_f[None]).flatten(1).sum(dim=1)  # [6]
        per_aoi_means[bundle["key"]] = (per_cell_sum / n_ocean_f).cpu().numpy()
        weighted_sum = weighted_sum + per_cell_sum
        weighted_count = weighted_count + mask_f.sum()
    # Two joint-recovery interpretations:
    #   cellweighted: cell-weighted mean across all AOIs combined (AOIs with
    #     more cells dominate; previously the only definition).
    #   aoiweighted:  equal-weight mean over per-AOI means (each AOI
    #     contributes the same regardless of cell count). For regime-
    #     specific parameters this honors N Atl's recovery quality even
    #     though it has fewer cells than Eq Pac.
    joint_means_cellweighted = (weighted_sum / weighted_count).cpu().numpy()
    joint_means_aoiweighted = np.mean(
        [per_aoi_means[k] for k in AOIS_KEYS], axis=0
    )
    # The "primary" joint_means used for n_cal_grade reporting is configurable
    # via JOINT_RECOVERY_MODE; default "cellweighted" so previously-reported
    # joint_recovered values reproduce bit-identically. Set to "aoiweighted"
    # to use the equal-weight-per-AOI mean (better when one AOI has fewer
    # cells but stronger constraint on a regime-specific parameter).
    JOINT_RECOVERY_MODE = os.environ.get("JOINT_RECOVERY_MODE", "cellweighted")
    if JOINT_RECOVERY_MODE == "cellweighted":
        joint_means = joint_means_cellweighted
    elif JOINT_RECOVERY_MODE == "aoiweighted":
        joint_means = joint_means_aoiweighted
    else:
        raise ValueError(f"JOINT_RECOVERY_MODE={JOINT_RECOVERY_MODE!r}; "
                         f"expected 'aoiweighted' or 'cellweighted'")

    # Print per-AOI + joint table.
    print(f"{'Param':<12} " + "  ".join(f"{k[:8]:>10s}" for k in AOIS_KEYS) + f"  {'JOINT':>10s}  {'Carroll':>10s}")
    n_cal_joint = 0; n_exc_joint = 0
    result_params = {}
    for i, name in enumerate(PARAM_NAMES):
        pub = float(carroll_published[i])
        joint_val = float(joint_means[i])
        joint_rel = abs(joint_val - pub) / abs(pub)
        joint_band = band_of(joint_rel)
        if joint_band == "Excellent": n_cal_joint += 1; n_exc_joint += 1
        elif joint_band == "Cal-grade": n_cal_joint += 1
        per_aoi_str = "  ".join(
            f"{per_aoi_means[k][i]:>10.4g}" for k in AOIS_KEYS
        )
        print(f"{name:<12} {per_aoi_str}  {joint_val:>10.4g}  {pub:>10.4g}  joint={joint_band} ({joint_rel:.3f})")
        # Also store both joint interpretations so analysis is not locked
        # into the choice of JOINT_RECOVERY_MODE made at training time.
        cw_val = float(joint_means_cellweighted[i])
        cw_rel = abs(cw_val - pub) / abs(pub)
        cw_band = band_of(cw_rel)
        aw_val = float(joint_means_aoiweighted[i])
        aw_rel = abs(aw_val - pub) / abs(pub)
        aw_band = band_of(aw_rel)
        result_params[name] = {
            "joint_recovered": joint_val,
            "joint_carroll_published": pub,
            "joint_abs_rel_offset": joint_rel,
            "joint_band": joint_band,
            "joint_cellweighted_recovered": cw_val,
            "joint_cellweighted_abs_rel_offset": cw_rel,
            "joint_cellweighted_band": cw_band,
            "joint_aoiweighted_recovered": aw_val,
            "joint_aoiweighted_abs_rel_offset": aw_rel,
            "joint_aoiweighted_band": aw_band,
            "per_aoi_recovered": {k: float(per_aoi_means[k][i]) for k in AOIS_KEYS},
        }
    print(f"       -> joint {n_cal_joint}/6 cal-grade ({n_exc_joint} Excellent)")

    result = {
        "seed": seed,
        "aois": AOIS_KEYS,
        "aoi_weights": AOI_W,
        "n_aois": N_AOIS,
        "geotraces_w": GEOTRACES_W,
        "geotraces_sub_w": GEOTRACES_SUB_W,
        "pinn_w": PINN_W,
        "pinn_type": PINN_TYPE,
        "use_darwin_ic": USE_DARWIN_IC,
        "poc_sub_w": POC_SUB_W,
        "geotraces_poc_sub_w": GEOTRACES_POC_SUB_W,
        "n_geo_poc_subsurface_cells_per_aoi": {b["key"]: b["n_geo_poc"] for b in bundles},
        "use_aoi_id_channel": USE_AOI_ID_CHANNEL,
        "use_mld_channel": USE_MLD_CHANNEL,
        "dinn_hidden_dim": DINN_HIDDEN_DIM,
        "dinn_n_input_channels": n_input_channels,
        "joint_recovery_mode": JOINT_RECOVERY_MODE,
        "chl1_w_extra": CHL1_W_EXTRA,
        "per_aoi_dinn": USE_PER_AOI_DINN,
        "consistency_lambda": CONSISTENCY_LAMBDA,
        "gating_policy": GATING_POLICY_SPEC if USE_GATING else "ungated",
        "gating_map": {k: _gating_policy.get(k, []) for k in AOIS_KEYS} if USE_GATING else {},
        "pic_abs_w": PIC_ABS_W,
        "n_pic_abs_cells_per_aoi": {b["key"]: b["n_pic_abs"] for b in bundles},
        "poc_abs_w": POC_ABS_W,
        "n_poc_abs_cells_per_aoi": {b["key"]: b["n_poc_abs"] for b in bundles},
        "posi_w": POSI_W,
        "n_posi_cells_per_aoi": {b["key"]: b["n_posi"] for b in bundles},
        "f_co2_abs_w": F_CO2_ABS_W,
        "n_f_co2_abs_cells_per_aoi": {b["key"]: b["n_f_co2_abs"] for b in bundles},
        "use_mehrbach_k1k2": _carbonate.USE_MEHRBACH_K1K2,
        "k_wanninkhof": _carbonate.K_WANNINKHOF,
        "use_coccolith_only_calcite": _layer2.USE_COCCOLITH_ONLY_CALCITE,
        "fet_w": FET_W,
        "n_epochs": N_EPOCHS,
        "n_seeds_in_batch": N_SEEDS,
        "elapsed_s_total_batch": elapsed,
        "loss_final": float(loss_history[-1, seed_idx].item()),
        "per_aoi_loss_final": {k: float(per_aoi_history[k][-1, seed_idx].item()) for k in AOIS_KEYS},
        "params": result_params,
        "n_cal_grade": n_cal_joint,
        "n_excellent": n_exc_joint,
    }
    all_results.append(result)


# ============================== Write JSONs =================================

SKIP_JSON_WRITE = os.environ.get("NB23_SKIP_JSON_WRITE", "0") == "1"
# Allow redirecting JSON output to a shorter path -- on Windows, worktree
# paths can push max-lever filenames past the 260-char MAX_PATH limit.
out_dir = Path(os.environ.get("OUTPUT_DIR", str(Path(__file__).resolve().parent)))
out_dir.mkdir(parents=True, exist_ok=True)
if SKIP_JSON_WRITE:
    print(f"\nNB23_SKIP_JSON_WRITE=1: skipping JSON write for {len(all_results)} results.")
else:
    aoi_tag = "-".join(AOIS_KEYS)
    poc_tag = f"_pocsubW{POC_SUB_W}" if POC_SUB_W > 0 else ""
    geo_poc_tag = f"_geopocW{GEOTRACES_POC_SUB_W}" if GEOTRACES_POC_SUB_W > 0 else ""
    aoi_id_tag = "_aoiid" if USE_AOI_ID_CHANNEL else ""
    mld_tag = "_mld" if USE_MLD_CHANNEL else ""
    hd_tag = f"_hd{DINN_HIDDEN_DIM}" if DINN_HIDDEN_DIM != 16 else ""
    # Tag any non-default AOI weights so weight sweeps don't overwrite each other.
    aoi_w_parts = [f"{k}{AOI_W[k]}" for k in AOIS_KEYS if AOI_W[k] != 1.0]
    aoi_w_tag = ("_w-" + "-".join(aoi_w_parts)) if aoi_w_parts else ""
    # JOINT_RECOVERY_MODE is read from each result row (constant across batch).
    jrm = all_results[0]["joint_recovery_mode"] if all_results else "cellweighted"
    jrm_tag = f"_jrm{jrm}" if jrm != "cellweighted" else ""
    chl1_extra_tag = f"_chl1W{CHL1_W_EXTRA}" if CHL1_W_EXTRA > 0 else ""
    peraoi_tag = f"_peraoi_lam{CONSISTENCY_LAMBDA}" if USE_PER_AOI_DINN else ""
    _gate_preset = GATING_POLICY_SPEC if GATING_POLICY_SPEC in GATING_POLICIES else "custom"
    gate_tag = f"_gate-{_gate_preset}" if USE_GATING else ""
    pic_abs_tag = f"_picabsW{PIC_ABS_W}" if PIC_ABS_W > 0 else ""
    poc_abs_tag = f"_pocabsW{POC_ABS_W}" if POC_ABS_W > 0 else ""
    posi_tag = f"_posiW{POSI_W}" if POSI_W > 0 else ""
    fco2_abs_tag = f"_fco2absW{F_CO2_ABS_W}" if F_CO2_ABS_W > 0 else ""
    mehrbach_tag = "_mehrbach" if _carbonate.USE_MEHRBACH_K1K2 else ""
    kw_tag = f"_kw{_carbonate.K_WANNINKHOF}" if _K_WANNINKHOF_OVERRIDE is not None else ""
    cocco_tag = "_cocco" if _layer2.USE_COCCOLITH_ONLY_CALCITE else ""
    for r in all_results:
        out = out_dir / (
            f"run_v3.0_joint_{aoi_tag}_seed{r['seed']}"
            f"_surf{GEOTRACES_W}"
            f"_sub{GEOTRACES_SUB_W}"
            f"_pinn{PINN_W}"
            f"{poc_tag}"
            f"{geo_poc_tag}"
            f"{aoi_id_tag}"
            f"{mld_tag}"
            f"{hd_tag}"
            f"{aoi_w_tag}"
            f"{jrm_tag}"
            f"{chl1_extra_tag}"
            f"{peraoi_tag}"
            f"{gate_tag}"
            f"{pic_abs_tag}"
            f"{poc_abs_tag}"
            f"{posi_tag}"
            f"{fco2_abs_tag}"
            f"{mehrbach_tag}"
            f"{kw_tag}"
            f"{cocco_tag}.json"
        )
        existed = out.is_file()
        with out.open("w", encoding="utf-8") as f:
            json.dump(r, f, indent=2, allow_nan=False)
        suffix = " (overwrote existing)" if existed else ""
        print(f"  wrote {out.name}{suffix}")

print(f"\nBatch summary: {N_AOIS} AOIs x {N_SEEDS} seeds in {elapsed:.0f}s "
      f"({elapsed/N_SEEDS:.1f}s amortized per seed)")
