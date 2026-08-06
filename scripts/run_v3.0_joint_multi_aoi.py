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
    ALK_ABS_W             absolute-units MSE loss on surface ALK vs REAL GLODAP
                          TAlk (regridded to the AOI grid). The box's surface ALK
                          is calcite-only (dALK_1 = -2*R_PICPOC*mort_total), the
                          SAME product as PIC -- tests whether a real
                          out-of-sample ALK observable gives R_PICPOC an
                          independent handle (co-recovery with the iron pair) or
                          re-triggers the binary PIC-anchor mutex. Needs the
                          GLODAP file (GLODAP_DATA_ROOT). Default 0 = off.
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
    P,
    PARAM_BOUNDS,
    N_PARAMS,
    PARAM_NAMES,
    PHI_DUST,
    Q_FE,
    bounded_params,
    log_mask_from_names,
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
# Forward-model fidelity levers (added 2026-06-11; default OFF/identity reproduces
# legacy bitwise). Also resolved at torch.compile trace time -> set BEFORE compile.
_layer2.W_SINK_PIC = float(os.environ.get("W_SINK_PIC", str(_layer2.W_SINK)))
_layer2.R_PIC_DISSOL = float(os.environ.get("R_PIC_DISSOL", str(_layer2.R_REMIN)))
_layer2.USE_EPPLEY_T = os.environ.get("USE_EPPLEY_T", "0") == "1"
_layer2.A_E_EPPLEY = float(os.environ.get("A_E_EPPLEY", str(_layer2.A_E_EPPLEY)))
_layer2.T_REF_EPPLEY = float(os.environ.get("T_REF_EPPLEY", str(_layer2.T_REF_EPPLEY)))
# Environment-dependent rain ratio (added 2026-06-24; default OFF reproduces legacy
# bitwise). Gates R_PICPOC by a coccolithophore thermal window so a single base rate
# yields Darwin's ~100x regional PIC:POC spread (deep-research option 3; shape
# constants from scripts/probe_env_rain_ratio.py). Resolved at trace time -> set BEFORE
# compile. Pair with RATIO_W > 0 and COCCOLITH_ONLY=0.
_layer2.USE_ENV_RAIN_RATIO = os.environ.get("RPP_ENV", "0") == "1"
_layer2.RPP_T_OPT = float(os.environ.get("RPP_T_OPT", str(_layer2.RPP_T_OPT)))
_layer2.RPP_T_WIDTH = float(os.environ.get("RPP_T_WIDTH", str(_layer2.RPP_T_WIDTH)))
_layer2.RPP_OMEGA_K = float(os.environ.get("RPP_OMEGA_K", str(_layer2.RPP_OMEGA_K)))
_layer2.RPP_OMEGA_P = float(os.environ.get("RPP_OMEGA_P", str(_layer2.RPP_OMEGA_P)))
_layer2.RPP_G_NORM = float(os.environ.get("RPP_G_NORM", str(_layer2.RPP_G_NORM)))
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
    npp_from_state,
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
from darwindiff.glodap_loader import (
    open_glodap_variable,
    surface_layer_glodap,
    to_mmol_per_m3,
)
from darwindiff.daniels_loader import (
    bin_to_grid as bin_daniels_to_grid,
    load_daniels_points,
)
from darwindiff.llc270_loader import bin_native_tracer_to_1deg, native_tracer_cells
from darwindiff.provenance import stamp as _prov_stamp
from darwindiff.networks import DINN, PerParamDINN, GlobalScalarNet, PerCellFreeField
from darwindiff.safe_load import safe_torch_load
from darwindiff.gating import PARAM_NAMES as _GATE_PARAM_NAMES
from darwindiff.gating import (
    GATING_POLICIES,
    apply_gate,
    build_gate_vectors,
    build_weight_vectors_from_rule,
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
# GLODAP mapped-climatology root (real ship-CTD obs). Used ONLY when ALK_ABS_W>0
# (the GLODAP TAlk anchor). Default follows the notebook convention
# (data/glodap/...); override with GLODAP_DATA_ROOT for the on-disk copy.
GLODAP_ROOT = Path(os.environ.get(
    "GLODAP_DATA_ROOT",
    str(Path(__file__).resolve().parents[1] / "data" / "glodap"
        / "GLODAPv2.2016b_MappedClimatologies"),
))
# Daniels et al. 2018 CP:PP compilation (PANGAEA 888182) — the real,
# Darwin-INDEPENDENT R_PICPOC (rain-ratio) anchor. Used ONLY when
# DANIELS_RPICPOC_W>0. Default follows the repo data/ convention; override with
# DANIELS_DATA_PATH for the on-disk / cluster copy (/projects/schultz/qi.zim).
DANIELS_PATH = Path(os.environ.get(
    "DANIELS_DATA_PATH",
    str(Path(__file__).resolve().parents[1] / "data" / "daniels"
        / "Daniels_etal_2018_PANGAEA_888182.tab"),
))
CACHE_DIR = DATA_ROOT / "cache"

IC_CACHE_NAME = {
    "eqpac": "darwin_ic_cache.npz",
    "natlsubpolar": "darwin_ic_cache_natlsubpolar.npz",
    "southernoceanpac": "darwin_ic_cache_southernoceanpac.npz",
    "npsg": "darwin_ic_cache_npsg.npz",
    "kerguelen": "darwin_ic_cache_kerguelen.npz",
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

# TIME_MEAN_LOSS: compare the model's TIME MEAN over the integration window to the target,
# instead of its END STATE. The targets are built with `time_mean(ds_aoi)` -- they are
# time-averaged Darwin fields -- while the model has always been sampled at a single instant,
# t = N_STEPS * DT = 50 days. Those are different objects in the time dimension, and the
# mismatch is the mechanical reason the window is load-bearing: an endpoint on a drifting
# trajectory is maximally window-sensitive, a trajectory mean is not.
#
# Measured 2026-08-05 (job 270032): `scav_rat`'s median falls monotonically 3.51x -> 0.54x ->
# 0.20x Carroll across 100/200/400 steps, in every basin. See
# docs/findings/2026-08-05_the_integration_window_is_a_contested_resource.md
#
# OFF BY DEFAULT. Turning it on changes every published number, so it is an ARM with its own
# control in the same submission, never a silent change to the flagship.
TIME_MEAN_LOSS = os.environ.get("TIME_MEAN_LOSS", "0") == "1"

# BLACK_ALPFE_W: weight on the Black et al. (2020) upper-ocean Fe EXPORT province anchor.
#
# It constrains `alpfe`, not `scav_rat`. The dataset was carried in this repo as the designated
# SINK anchor for `scav_rat`; that premise fails on mass conservation, because at steady state
# the box's total Fe removal equals `alpfe * PHI_DUST` and a 16x sweep of `scav_rat` moves it by
# 0.00%. What it CAN do is pin the source, which is the leg that de-confounds the rank-1
# alpfe<->scav_rat ridge from concentration data.
#
# OFF BY DEFAULT, AND NO PROVINCE CURRENTLY CLEARS THE BAR. Grading `alpfe` at the Cal band
# needs the observation to 0.73; measured sigma/value by province:
#
#     npsg           1.42   (n=1)   short by  1.9x
#     natlsubpolar   4.12   (n=1)   short by  5.6x
#     kerguelen      7.29   (n=3)   short by  9.9x   <- MORE programs, WORSE spread
#
# Kerguelen holds the densest cluster in the compilation and is the worst of the three, because
# its three programs span 0.400 to 7.618 mmol Fe m^-2 yr^-1, a factor of 19. Adding programs
# widened the between-program scatter faster than it averaged down. The term is implemented,
# tested and correct; it is waiting on data with a tighter spread -- the bot-blocked per-station
# Supporting Information is the obvious candidate, since per-station values would replace
# between-program scatter with within-province structure.
BLACK_ALPFE_W = float(os.environ.get("BLACK_ALPFE_W", "0.0"))

# PINN_DFE2_W: extend the steady-state drift residual to SUBSURFACE iron.
#
# The existing PINN term constrains DFe_1 only -- surface iron, which is already ~100%
# converged at 200 steps. `DFe_2` is the tracer that anchors `scav_rat`, it is only 47.5%
# converged at 200 steps, and it carries NO steady-state constraint at all. So the one term in
# the loss that pushes toward convergence is pointed at the tracer that had already converged.
#
# The residual is taken as a finite difference over one extra step rather than by re-deriving
# the L2 iron budget here. For forward Euler `(x_{n+1} - x_n)/dt` IS `f(x_n)` exactly, so this
# is the true tendency, it costs one step in 200, and -- the reason that matters -- it cannot
# drift out of sync with the physics the way a hand-copied budget would.
#
# *** DO NOT USE THIS BELOW N_STEPS ~ 3200. IT PENALISES THE TRUTH. ***
#
# Measured 2026-08-06 at CARROLL'S OWN PARAMETERS, natlsubpolar median cell, relative drift
# |dx/dt|/x per day:
#
#     step      day     DFe_1        DFe_2
#        0      0.0     7.06e-02     7.87e-03
#      200     50.0     2.84e-05     1.68e-02    <- the flagship operating point
#      800    200.0     3.89e-08     1.27e-02
#     3200    800.0     6.38e-12     1.62e-06
#
# Surface iron is converged by 200 steps and the existing PINN term is correctly ~zero at the
# truth (bitwise: the loss is identical at NB23_PINN_WEIGHT 0 and 3). Subsurface iron is NOT:
# its drift at day 50 is 600x the surface tracer's, and larger than it was at day 0. So a
# steady-state penalty on DFe_2 evaluated at 200 steps is NONZERO AT CARROLL, and minimising
# it moves the fit AWAY from the answer. The term is well-formed; the operating point is not
# where it is admissible. It becomes meaningful only once the window reaches convergence,
# which for DFe_2 is ~3200 steps.
#
# Kept, gated OFF, and documented rather than deleted, because it is the correct term for a
# converged-window arm and this measurement is the reason not to pair it with a short one.
PINN_DFE2_W = float(os.environ.get("PINN_DFE2_W", "0.0"))
# DARWIN_PATTERN_W: scalar multiplier on the ENTIRE base z-scored Darwin-output
# pattern block (FeT + Chl1-5 + POC + PIC + DIC + ALK + co2_flux, normalized by
# FET_W+10). These are the non-fidelity "pattern" terms (paper gap-(a)); the box
# homogenizes so they cannot carry circulation-driven structure. Set to 0 for the
# "anchors-only" ablation (red-team rebuttal_diff 4): keep only the real absolute
# anchors (GEOTRACES iron, Daniels calcite, GEOTRACES bSi) + PINN physics, and test
# whether the trio survives without the Darwin-pattern scaffold. Default 1.0 =
# bit-identical no-op (1.0 * z == z exactly).
DARWIN_PATTERN_W = float(os.environ.get("DARWIN_PATTERN_W", "1.0"))
GEOTRACES_W = float(os.environ.get("GEOTRACES_W", "0.3"))
GEOTRACES_SUB_W = float(os.environ.get("GEOTRACES_SUB_W", "1.0"))
SUB_DEPTH_MIN = float(os.environ.get("GEOTRACES_SUB_DEPTH_MIN", "50.0"))
SUB_DEPTH_MAX = float(os.environ.get("GEOTRACES_SUB_DEPTH_MAX", "1000.0"))
# #163 independent-DATA validation: hold out this spatial fraction of surface GEOTRACES
# iron cells from the TRAINING loss; after training, score the box's predicted DFe at
# those unseen cells vs real held-out iron. 0 = off (default; byte-identical behaviour).
GEOTRACES_HOLDOUT_FRAC = float(os.environ.get("GEOTRACES_HOLDOUT_FRAC", "0"))
GEOTRACES_HOLDOUT_SEED = int(os.environ.get("GEOTRACES_HOLDOUT_SEED", "12345"))
N_EPOCHS = int(os.environ.get("NB23_N_EPOCHS", "1500"))
USE_DARWIN_IC = os.environ.get("DARWIN_IC", "1") == "1"   # default ON for v3.0
# O7: NATIVE_RES=1 fits at full LLC270 native resolution (~9.8k cells/AOI) instead
# of the 1deg box (~1k). Cells become a degenerate [1, N_cells] grid so the entire
# [H,W] pipeline + box model run unchanged. The 1deg-grid GEOTRACES/GLODAP-interp
# losses are not available natively (gate them off); default OFF preserves 1deg.
NATIVE_RES = os.environ.get("NATIVE_RES", "0") == "1"
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
# Per-parameter LOG-SCALE bounding. Comma-separated registry names, e.g.
# PARAM_LOG_SCALE=scav_rat. Empty (default) -> None -> the historical LINEAR
# sigmoid map, bitwise identical to every run before 2026-07-28.
#
# Why it exists: bounded_params interpolates linearly between (lo, hi). For
# scav_rat that range spans 100x (3e-8..3e-6), so the top decade occupies 90.9%
# of the sigmoid and the bottom decade only 9.1%. Under the init distribution
# just 7.5% of prior mass lands below Carroll and the median start is 2.52x
# Carroll, i.e. nearly every seed begins well above the target with almost no
# resolution on the way down. Log bounding makes the map geometric, putting the
# theta=0 start at the geometric mean (0.50x Carroll, rel offset 0.502 -- still
# OUTSIDE the 0.40 Cal band, so this does not hand the metric a free recovery).
PARAM_LOG_SCALE = os.environ.get("PARAM_LOG_SCALE", "")
PARAM_LOG_SCALE_MASK = log_mask_from_names(PARAM_LOG_SCALE)
# v3.0+: add MLD as a 3rd env channel (after SST + AOI ID) when set. MLD is
# regime-distinctive (winter convection in N Atl vs perennial-thermocline
# in Eq Pac) and biology-relevant.
USE_MLD_CHANNEL = os.environ.get("MLD_CHANNEL", "0") == "1"
# v3.1: additional environmental covariate channels for the DINN input, appended
# after SST / AOI-ID / MLD. Each is one shared-z-scored [H,W] field. All default
# OFF -> the env tensor is bitwise-identical to the SST-only baseline. Motivation:
# NN size and patch-overlap both failed to move recovery; richer *input
# information* (particle-flux / mixing / carbonate covariates) is an orthogonal
# lever for the per-cell param field, esp. the scav_rat sink leg. Latitude is
# deliberately NOT offered here (a geographic-location cheat like AOI_ID, not a
# physical covariate). Fields come from the same v05 caches the box is forced by.
_EXTRA_ENV_SPEC = [
    ("WIND_CHANNEL",    "wind_raw_for_env",    "wind"),      # 10m wind speed (gas exch / dust / mixing)
    ("SSS_CHANNEL",     "sss_raw_for_env",     "SSS"),       # sea-surface salinity (carbonate)
    ("PCO2_CHANNEL",    "pco2_raw_for_env",    "pCO2atm"),   # atmospheric pCO2
    ("CO2FLUX_CHANNEL", "co2flux_raw_for_env", "CO2flux"),   # air-sea CO2 flux
]
_ENABLED_EXTRA_ENV = [(rawkey, lbl) for (flag, rawkey, lbl) in _EXTRA_ENV_SPEC
                      if os.environ.get(flag, "0") == "1"]
# CHL1_W_EXTRA adds an EXTRA Chl1 (diatom chl) z-score loss term on top of
# the existing per-PFT chl_z term. Targets diatomgraz recovery: the 5/6
# seeds that consistently miss diatomgraz do so at ~0.75 off Carroll, and
# the existing 1/11-weighted Chl1 loss apparently isn't pulling hard
# enough. Default 0 = no extra term; existing v3.0 JSONs reproduce.
CHL1_W_EXTRA = float(os.environ.get("CHL1_W_EXTRA", "0.0"))
# CHL2_W_EXTRA mirrors CHL1_W_EXTRA for the LARGE-phytoplankton channel
# (state[I_LGE] vs Darwin Chl2), which is the observable carrying Biggrow.
# See the loss-term comment for the Fisher evidence motivating it. Default 0.0
# keeps every existing run bitwise identical.
CHL2_W_EXTRA = float(os.environ.get("CHL2_W_EXTRA", "0.0"))
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
# Ablation control: GLOBAL_SCALAR=1 replaces the per-cell DINN with a single
# global Carroll-6 vector per seed (shared across AOIs) — the differentiable
# analogue of one Green's-functions parameter set. Everything else (forcing,
# integrator, loss, scoring) is identical, so per-cell-vs-global is a clean A/B.
# Takes precedence over PER_AOI_DINN (a global scalar is global by construction).
USE_GLOBAL_SCALAR = os.environ.get("GLOBAL_SCALAR", "0") == "1"
# Ablation control: POINTWISE=1 replaces the per-cell DINN with an UNCONSTRAINED
# free parameter field, one learnable value per parameter per grid cell, no
# network and no covariate conditioning. This is the third rung of the
# parameterisation ladder and the control the inverse-problems literature uses
# for a neural field (Xu & Darve, ADCME): DINN-vs-global-scalar shows per-cell
# STRUCTURE matters, DINN-vs-free-field shows whether the NETWORK does.
# Bound to one grid, so it is per-AOI by construction -- run PER_AOI_DINN=1
# alongside it to separate per-cell freedom from per-AOI freedom.
# Precedence: GLOBAL_SCALAR > POINTWISE > PER_AOI_DINN > shared DINN.
USE_POINTWISE = os.environ.get("POINTWISE", "0") == "1"
# PER_PARAM=1: one independent DINN trunk per PARAMETER (no representation sharing).
# The ladder's missing rung -- every other rung varies spatial sharing, none varied
# parameter sharing. Lower precedence than the spatial rungs, which are mutually
# exclusive with it by construction (a global scalar is already unshared per cell).
USE_PER_PARAM = os.environ.get("PER_PARAM", "0") == "1"
CONSISTENCY_LAMBDA = float(os.environ.get("CONSISTENCY_LAMBDA", "0.0"))
# POOL_PARAMS (partial pooling): which Carroll-6 params are pulled toward cross-AOI
# agreement by CONSISTENCY_LAMBDA; the rest stay fully per-AOI free. Implements the
# 2026-06-25 diagnostic's structural prescription -- pool the FLAT growth pair
# {Smallgrow, Biggrow} while FREEING the regime-dependent iron/grazing params per-AOI
# (issue #143). Empty (default) = pool ALL six with uniform CONSISTENCY_LAMBDA, which
# reproduces the prior penalty bitwise. Only active with PER_AOI_DINN=1.
_CONS_PARAM_ORDER = ["alpfe", "scav_rat", "Smallgrow", "Biggrow", "diatomgraz", "R_PICPOC"]
_pool_spec = [s.strip() for s in os.environ.get("POOL_PARAMS", "").split(",") if s.strip()]
_bad_pool = [p for p in _pool_spec if p not in _CONS_PARAM_ORDER]
if _bad_pool:
    raise ValueError(f"POOL_PARAMS has unknown param(s) {_bad_pool}; valid: {_CONS_PARAM_ORDER}")
_pool_set = set(_pool_spec) if _pool_spec else set(_CONS_PARAM_ORDER)
# Per-parameter consistency weight (list of 6, canonical param order).
CONSISTENCY_LAMBDA_VEC = [CONSISTENCY_LAMBDA if p in _pool_set else 0.0 for p in _CONS_PARAM_ORDER]
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
# ALK_ABS_W: absolute-units MSE on surface ALK vs REAL GLODAP TAlk (regridded to
# the AOI grid, mmol/m^3). The box's surface ALK is driven ONLY by calcite
# (dALK_1 = -2*R_PICPOC*mort_total), the SAME product PIC is driven by -- so this
# is the carbonate-counter-pump test: does a real out-of-sample ALK observable
# (with the 2:1 stoichiometry + the ALK->pCO2->F_CO2 coupling) give R_PICPOC an
# INDEPENDENT handle that co-recovers with the iron pair (hypothesis), or does the
# R_PICPOC*mort_total factorization mutex re-appear as it does for the Darwin-PIC
# anchor (prediction)? Requires the GLODAP file; default 0 = off (legacy
# reproduces bitwise). See docs/findings/alk_anchor_rpicpoc_mutex.md.
ALK_ABS_W = float(os.environ.get("ALK_ABS_W", "0.0"))
# ALK_ABS_SOURCE: target for the ALK absolute anchor. "glodap" (default) = real
# GLODAP TAlk; "darwin" = Darwin's OWN surface ALK (the alk_binned field already
# loaded) -- a control that tests whether any R_PICPOC recovery is specific to
# real observations or to the absolute-ALK constraint per se. Only consulted when
# ALK_ABS_W > 0; default "glodap" preserves the GLODAP path.
ALK_ABS_SOURCE = os.environ.get("ALK_ABS_SOURCE", "glodap").strip().lower()
# RATIO_W: scale-normalized MSE on the box's surface PIC:POC RATIO vs Darwin's own
# per-cell PIC/POC (pic_binned / poc_binned). Unlike the separate PIC/POC magnitude
# anchors -- each of which pins mort_total and triggers the iron-pair mutex -- the
# ratio is mort_total-INDEPENDENT at steady state (PIC_1/POC_1 = R_PICPOC*W_SINK/
# W_SINK_PIC), so it constrains R_PICPOC ORTHOGONALLY to the iron pair (confirmed
# by a forward-model orthogonality probe 2026-06-15). Tests whether the R_PICPOC
# mutex is a fixable estimator-design error (separate anchors were the wrong
# observable) rather than a fundamental box-scale information limit. Best paired
# with USE_COCCOLITH_ONLY_CALCITE so a single R_PICPOC reproduces the ~23x cross-AOI
# realized-ratio variation via biomass composition. Default 0 = off.
RATIO_W = float(os.environ.get("RATIO_W", "0.0"))
# RATIO_MAX: physical cap on the per-cell PIC:POC ratio TARGET. Cells where Darwin's
# pic_binned/poc_binned exceeds this are excluded from the ratio mask. Low-POC cells
# (POC -> 0, common in the Southern Ocean) produce non-physical per-cell ratios up to
# ~1e8 that dominate the scale normalizer (mean of squared targets), collapsing the
# whole AOI's ratio term to ~0 and leaving R_PICPOC under-constrained there (observed
# 2026-06-24: SO ratio target mean=4.7e7). Real rain ratios are < ~2 (Darwin AOI
# ratio-of-means: eqpac 0.033 / natl 0.68 / SO 0.0067), so a cap removes the artifact
# without touching genuine cells. Default inf = legacy reproduces bitwise.
RATIO_MAX = float(os.environ.get("RATIO_MAX", "inf"))
# RATIO_SCHED_START: warmup schedule for the ratio loss. The ratio loss (which
# recovers R_PICPOC) competes with the growth/iron terms (which the 5/6 relied on),
# so a single weight can't satisfy both (verified sweep, 2026-06-24). Annealing
# separates them in TIME: the ratio term is held at 0 for the first
# RATIO_SCHED_START fraction of epochs (let alpfe/scav_rat/Biggrow converge), then
# ramps linearly to full RATIO_W by the end (lock in R_PICPOC without disturbing the
# settled params). Default 0.0 = ratio loss on from epoch 0 (constant = legacy).
RATIO_SCHED_START = float(os.environ.get("RATIO_SCHED_START", "0.0"))
_RATIO_W_NOW = RATIO_W  # mutable per-epoch effective ratio weight (updated in the loop)
# DANIELS_RPICPOC_W: scale-normalized MSE on the box's surface PIC:POC ratio vs
# the REAL, Darwin-INDEPENDENT rain ratio from the Daniels et al. 2018 CP:PP
# incubation compilation (PANGAEA 888182). Unlike RATIO_W -- whose target is
# Darwin's OWN per-cell PIC/POC, making any R_PICPOC recovery graded against it
# circular (Carroll never tuned R_PICPOC to rain-ratio data) -- this target is
# direct calcite:primary-production observations binned per-AOI to a geometric-
# mean rain ratio (CP/PP is log-normal). It breaks the circularity and tests the
# regional-variability hypothesis: the real eqpac surface rain ratio (~0.04
# geomean, 1.6x the global ~0.025) exceeds the global mean, so a single global
# constant is mis-specified in our constraining AOI. Same orthogonal handle on
# R_PICPOC as RATIO_W (mort_total cancels in the box ratio). Coverage is sparse;
# AOIs with no Daniels samples (e.g. southernoceanpac, npsg) get an empty mask
# and the term auto-gates off there. Default 0 = off (legacy reproduces bitwise).
DANIELS_RPICPOC_W = float(os.environ.get("DANIELS_RPICPOC_W", "0.0"))
# DANIELS_DEPTH_MAX: surface depth cut (m) for Daniels samples. The box is a
# surface mixed-layer model and the rain ratio shoals with light, so a surface
# cut keeps the target comparable to the box's surface PIC:POC. Default 50 m
# (matches the box H_MLD and the GEOTRACES surface cut). Only used when
# DANIELS_RPICPOC_W>0; cached Daniels points are loaded once when first needed.
DANIELS_DEPTH_MAX = float(os.environ.get("DANIELS_DEPTH_MAX", "50.0"))
# Per-AOI multiplier on the DANIELS term ONLY (parity with RATIO_AOI_W). Lets the
# Daniels anchor act where it has coverage and be tuned per-region. Default 1.0.
DANIELS_AOI_W = {k: float(os.environ.get(f"DANIELS_AOI_W_{k.upper()}", "1.0")) for k in AOIS_KEYS}
# Lazily-loaded global Daniels point cloud (parsed once, binned per-AOI). None
# until the first AOI bundle that needs it; stays None when the term is off.
_DANIELS_POINTS = None
# DUST_ANCHOR_W: informative Gaussian PRIOR on the physical alpfe -- the reduced-form,
# out-of-manifold iron SOURCE constraint. Adds, per seed,
#     DUST_ANCHOR_W * ((alpfe_phys - DUST_ANCHOR_MU) / DUST_ANCHOR_SIGMA)**2
# to the total loss, where alpfe_phys is the cell-weighted-mean physical alpfe across
# ALL AOIs (index 0 of the Carroll-6 vector -- the same "joint" alpfe the recovery
# report grades). Unlike the spatial anchors above this is NOT a spatial loss and needs
# no new AOI: it pins the SOURCE leg of the iron budget from data completely independent
# of the box (Xu & Weber 2021 Al-inverse soluble-Fe deposition / v05 Mahowald soluble-Fe
# deposition, AOI-aggregated in the dust-dominated Saharan N. Atlantic = 1.15; widened
# by the Fe:Al molar + 60-config ensemble uncertainty to sigma ~ 0.7, a factor-~2 bound).
# See docs/findings/2026-07-22_dust_anchor_phase0.md. The whole prior block is guarded by
# DUST_ANCHOR_W > 0, so the default 0.0 is a BITWISE no-op (no graph node is created,
# no accumulator touched). MU/SIGMA are consulted only when the weight is > 0.
DUST_ANCHOR_W = float(os.environ.get("DUST_ANCHOR_W", "0.0"))
DUST_ANCHOR_MU = float(os.environ.get("DUST_ANCHOR_MU", "1.15"))
DUST_ANCHOR_SIGMA = float(os.environ.get("DUST_ANCHOR_SIGMA", "0.7"))
if DUST_ANCHOR_W > 0:
    if DUST_ANCHOR_SIGMA <= 0:
        raise ValueError(f"DUST_ANCHOR_SIGMA must be > 0; got {DUST_ANCHOR_SIGMA}")
    print(f"        dust_anchor_w={DUST_ANCHOR_W} (alpfe SOURCE prior N(mu={DUST_ANCHOR_MU}, "
          f"sigma={DUST_ANCHOR_SIGMA}); Xu-Weber Al-inverse / v05 Mahowald, Saharan N. Atl)")
# POSI_W: absolute-units MSE loss on a steady-state biogenic-silica
# diagnostic (mmol Si / m^3) against the surface GEOTRACES IDP2025 bSi
# observation (bSi_LPT_CONC + bSi_SPT_CONC, QC 49/50, depth <= 50 m). bSi
# is produced only by diatoms, so its absolute magnitude pins
# `diatomgraz` * G0_GRAZE * P_diatom -- the only Carroll-6 parameter that
# enters silica production directly. Targets the v3.0 5/6-ceiling
# diagnosis (diatomgraz binding) from `notebooks/32_*`. Default 0 = off
# (legacy reproduces).
POSI_W = float(os.environ.get("POSI_W", "0.0"))
# POSI_DARWIN_W: same biogenic-silica diagnostic loss as POSI_W, but against
# Darwin's OWN dense gridded surface POSi field (TRAC16, mmol Si / m^3, binned
# to the AOI 1deg grid) instead of the sparse GEOTRACES bottle proxy. A dense,
# model-consistent, diatom-specific target -- the cheapest forward-model lever
# at the box scale for the stuck `diatomgraz` parameter (utilization audit
# 2026-06-11, item 5). Additive and independent of POSI_W. Default 0 = off.
POSI_DARWIN_W = float(os.environ.get("POSI_DARWIN_W", "0.0"))
# PRIMPROD_W: z-scored spatial-pattern MSE on the box's diagnosed NPP
# (npp_from_state = growth_total) vs Darwin's own primary-production field (`PP`,
# binned to the AOI 1deg grid). A growth-FLUX target -- adds the growth-rate
# spatial constraint the z-scored Chl (biomass) loss can't pin, aimed at the
# stuck `Biggrow`. Native `PP` diagnostic is loaded only when > 0. Default 0 = off.
PRIMPROD_W = float(os.environ.get("PRIMPROD_W", "0.0"))
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

# Per-AOI multiplier on the RATIO_W term ONLY (unlike AOI_W, which scales the whole
# AOI loss). Lets the PIC:POC ratio loss act where it identifies R_PICPOC cleanly
# (eqpac/SO recover R_PICPOC per-AOI 10/10) and back off where it is futile and
# harmful: in natlsubpolar the flat-ratio box cannot reach Darwin's ~0.68, so the
# natl ratio loss never recovers R_PICPOC there (4/10) yet competes with the
# Biggrow/iron terms the documented 5/6 relied on (verified ratio-weight sweep,
# 2026-06-24). Set RATIO_AOI_W_NATLSUBPOLAR=0 to drop it. Default 1.0 = uniform.
RATIO_AOI_W = {k: float(os.environ.get(f"RATIO_AOI_W_{k.upper()}", "1.0")) for k in AOIS_KEYS}

# Per-AOI multiplier on the Darwin-pattern FeT term ONLY (the RATIO_AOI_W analogue for
# iron). This is the ADEQUACY lever.
#
# WHY IT EXISTS. Weighting AOIs by Fisher information made recovery worse (scav_rat
# 26/50 -> 11/50, job 256953) because information is not helpfulness: a Fisher diagonal
# measures how much an observable MOVES when the parameter moves, and is silent on
# whether the residual it is driven against is one the box could ever reach. Where the
# forward model is misspecified, high information up-weights confident error.
#
# The measured adequacy of the box's iron field, as the relative residual
# ||model - Darwin|| / ||Darwin||, is NOT uniform across basins:
#
#     at the prior midpoint    eqpac 1.347   natl 0.915   sopac 0.883
#     at the recovered optimum eqpac >=1.0   natl 0.621   sopac 0.554   (2026-07-28)
#
# eqpac's residual is at least as large as the signal at BOTH evaluation points, i.e. no
# parameter value makes the box reproduce Darwin's equatorial iron. Fitting a parameter
# through a forward map that cannot reach the target is not identifiability, and eqpac is
# the one basin where scav_rat has never recovered (6-8/50 in every arm, at every
# capacity, at 2000 and 4000 epochs).
#
# Set FET_AOI_W_EQPAC=0 to drop that term. Default 1.0 is a bit-identical no-op: the
# normaliser below is adjusted by the same weight, so the surviving pattern terms keep
# their mean-over-terms scaling and the intervention stays confined to the FeT term
# rather than silently rescaling the whole pattern block for that AOI.
#
# SCOPE: this is the Darwin-pattern FeT term (surrogate vs surrogate). The real GEOTRACES
# iron anchors (GEOTRACES_W, GEOTRACES_SUB_W) are separate targets and are NOT touched --
# the adequacy measurement was made against Darwin's FeT field, so it says nothing about
# the real observations, and no real data is discarded here.
# Rule: docs/findings/2026-08-03_adequacy_rule.json (scripts/analysis/emit_adequacy_rule.py)
FET_AOI_W = {k: float(os.environ.get(f"FET_AOI_W_{k.upper()}", "1.0")) for k in AOIS_KEYS}

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
# AOI_PARAM_WEIGHTS: path to a routing rule emitted by scripts/analysis/emit_routing_rule.py.
# SOFT per-(parameter, AOI) gradient weighting, derived from Fisher information at the PRIOR
# MIDPOINT rather than from which basin recovered best -- the latter would be selection on the
# answer. The rule holds the per-parameter TOTAL gradient fixed and only redistributes it across
# basins, so this does not covertly change the effective learning rate (which on 2026-08-03 was
# shown to move scav_rat from 26/50 to 1/50 on its own).
AOI_PARAM_WEIGHTS = os.environ.get("AOI_PARAM_WEIGHTS", "")
# Hash the routing rule alongside the sourced config, so an artifact records the exact bytes
# of every input that shaped it -- not just the code. DD_PROVENANCE_FILES is set by the sbatch.
if AOI_PARAM_WEIGHTS:
    _pf = os.environ.get("DD_PROVENANCE_FILES", "")
    os.environ["DD_PROVENANCE_FILES"] = (
        _pf + os.pathsep + AOI_PARAM_WEIGHTS) if _pf else AOI_PARAM_WEIGHTS
USE_AOI_PARAM_WEIGHTS = bool(AOI_PARAM_WEIGHTS)
if USE_AOI_PARAM_WEIGHTS and USE_GATING:
    raise ValueError(
        "AOI_PARAM_WEIGHTS and GATING_POLICY are mutually exclusive: both write the "
        "per-parameter gate. Soft weights subsume binary routing -- use one."
    )
if USE_AOI_PARAM_WEIGHTS:
    import json as _json
    with open(AOI_PARAM_WEIGHTS, encoding="utf-8") as _f:
        _rule = _json.load(_f)
    gate_vectors = build_weight_vectors_from_rule(
        _rule, AOIS_KEYS, AOI_W, device=device)
    USE_GATING = True
    GATING_POLICY_SPEC = f"aoi_param_weights:{os.path.basename(AOI_PARAM_WEIGHTS)}"
    print(f"Per-(parameter, AOI) SOFT weights ENABLED from {AOI_PARAM_WEIGHTS}")
    for _k in AOIS_KEYS:
        print("    " + _k + ": " + "  ".join(
            f"{_n}={float(gate_vectors[_k][_i]):.3f}"
            for _i, _n in enumerate(_GATE_PARAM_NAMES)))
else:
    gate_vectors = build_gate_vectors(_gating_policy, AOIS_KEYS, device=device)
if USE_GATING:
    print(f"Per-AOI gating ENABLED ({GATING_POLICY_SPEC}): "
          + "; ".join(f"{k}->{_gating_policy.get(k, [])}" for k in AOIS_KEYS))
else:
    print("Per-AOI gating: OFF (ungated baseline)")

DT = 0.25
# N_STEPS: the integration window, in units of DT days. Hardcoded at 200 (= 50 days) since the
# box was written and never swept until 2026-07-31.
#
# WHY IT MATTERS. The L2 iron relaxation time is 1/(scav_rat_per_day * POC_2) = 384 days, so a
# 50-day window covers 0.13 of one e-fold and reaches 12.2% of the way to equilibrium. The
# subsurface iron the loss sees is therefore dominated by the hardcoded initial condition
# (LIT_IC[10] = 5.0e-4, log-leverage 0.983) rather than by scav_rat (elasticity about -0.41,
# against the asymptotic -1). Because DARWIN_IC defaults off, state0 is also identical in every
# basin and the box has no horizontal transport, so the forward sensitivities come out equal
# across AOIs to four decimals.
#
# That makes the window a candidate explanation for the whole 2026-07-31 depth result: the box's
# basin-blind DFe_2 is 0.2671 nM at 200 steps and 0.4047 nM at 100, against observed subsurface
# medians of sopac 0.2245, eqpac 0.4404, natl 0.5638 nM. See
# docs/findings/2026-07-31_prereg_integration_window_swap.md.
#
# CORRECTION 2026-07-31: an earlier version of this comment said "DARWIN_IC defaults off". It does
# NOT -- line 303 reads os.environ.get("DARWIN_IC", "1"), so per-basin Darwin ICs are the DEFAULT.
# The basin-uniform state0 above applies only to arms that set DARWIN_IC=0 explicitly, which the
# 2026-07-31 depth arms did. The FLAGSHIP uses Darwin ICs and is therefore NOT basin-blind: it
# starts at FeT_L2 of 0.5353 / 0.7544 / 0.5393 nM and POC_L2 of 0.339 / 0.153 / 0.630 in
# eqpac / natl / sopac, which makes the L2 decay rate differ ~4x across basins (tau = 57 / 125 /
# 31 days). It is still a transient at 200 steps, so the window matters, but the mechanism is
# per-basin rather than a single shared curve.
N_STEPS = int(os.environ.get("N_STEPS", "200"))

print(f"AOIS: {AOIS_KEYS}  (joint training across {N_AOIS} AOIs)")
print(f"Per-AOI weights: {AOI_W}")
if any(v != 1.0 for v in FET_AOI_W.values()):
    print(f"ADEQUACY LEVER ACTIVE -- per-AOI Darwin-pattern FeT weights: {FET_AOI_W}")
print(f"Seeds: {SEEDS} (N={N_SEEDS})")
print(f"Config: fet_w={FET_W}, pinn_w={PINN_W}, geo_surf_w={GEOTRACES_W}, "
      f"geo_sub_w={GEOTRACES_SUB_W}, poc_sub_w={POC_SUB_W}, darwin_ic={USE_DARWIN_IC}")
print(f"        epochs={N_EPOCHS}, subsurface depth: [{SUB_DEPTH_MIN}, {SUB_DEPTH_MAX}] m")
if DANIELS_RPICPOC_W > 0:
    print(f"        daniels_rpicpoc_w={DANIELS_RPICPOC_W} (real CP:PP anchor, "
          f"depth<={DANIELS_DEPTH_MAX}m), per-AOI mult={DANIELS_AOI_W}")
print()


# ============================== Per-AOI loader ============================

def _build_aoi_targets_native(aoi) -> dict:
    """O7 native target builder: every covariate AND tracer at LLC270 native
    cells, aligned to one reference flat_idx, returned as ``[1, N_cells]`` fields
    so the 1deg ``[H, W]`` downstream code runs unchanged (H=1, W=N_cells).

    Unlike the 1deg builder (covariates from the bin_average NetCDF, tracers
    bin-averaged to 1deg), here SST/MLD/wind/apCO2/CO2_flux/Chl1-5 also come from
    the native monthly tree via :func:`native_tracer_cells`. ``darwin_lats/lons``
    become the per-cell lat/lon (1-D, length N_cells)."""
    b = (aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
    # "all" = true time-mean (production); "first"/N = fast smoke build.
    _iters = os.environ.get("NATIVE_BUILD_ITERS", "all")
    print(f"  [NATIVE_RES] building native target cache for {aoi.name} "
          f"(iters={_iters}; one-time, then cached)...")
    # Reference cell set + canonical alignment key from FeT (a core tracer).
    ref_v, ref_xc, ref_yc, ref_idx = native_tracer_cells(
        MONTHLY_ROOT, GRID_DIR, "FeT", *b, iters=_iters)
    ref_list = ref_idx.tolist()
    n = len(ref_list)
    print(f"  [NATIVE_RES] {aoi.name}: {n} native reference cells (FeT)")

    def aligned(var, _cache={"FeT": (ref_v, ref_idx)}):
        if var in _cache:
            v, idx = _cache[var]
        else:
            v, _xc, _yc, idx = native_tracer_cells(MONTHLY_ROOT, GRID_DIR, var, *b, iters=_iters)
        lut = dict(zip(idx.tolist(), v.tolist()))
        return np.array([lut.get(i, np.nan) for i in ref_list], dtype=np.float32)[None]  # [1, n]

    out = {
        "aoi_name": aoi.name,
        "aoi_bounds": b,
        "resolution": "native",
        "native_flat_idx": ref_idx.astype(np.int64),
        "darwin_lats": ref_yc.astype(np.float64),   # per-cell latitude  (1-D, n)
        "darwin_lons": ref_xc.astype(np.float64),   # per-cell longitude (1-D, n)
        "sst": aligned("SST"),
        "mld": aligned("mldDepth"),
        "wind": aligned("wspeed"),
        "sss": np.full((1, n), 35.0, dtype=np.float32),   # no native SSS; box default
        "pco2_atm_field": aligned("apCO2"),
        # NOT an observation. This is Darwin's own CO2_flux diagnostic, so every loss term
        # built from it is a model-vs-model target and must be counted on the Darwin side of
        # any observations-only accounting. The key keeps the misleading "_obs" spelling only
        # because it is a torch.save cache key (:709) with no version field -- renaming it
        # would KeyError against every existing cache outside the rebuild guard. Locals are
        # named co2_flux_darwin. See docs/research_notes/2026-07-29_observations_only_scope.md.
        "co2_flux_obs": aligned("CO2_flux"),
        "chl_per_pft": {f"Chl{i}": aligned(f"Chl{i}") for i in range(1, 6)},
    }
    for var in (["FeT", "POC", "PIC", "DIC", "ALK", "POSi"]
                + (["primProd"] if PRIMPROD_W > 0 else [])):
        out[f"{var.lower()}_binned"] = aligned(var)
    return out


def _build_aoi_targets(aoi) -> dict:
    if NATIVE_RES:
        return _build_aoi_targets_native(aoi)
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
        # NOT an observation -- Darwin's own diagnostic. See the note at the native builder.
        "co2_flux_obs": ds_avg_local["CO2_flux"].values.astype(np.float32),
        "chl_per_pft": {
            f"Chl{i}": ds_avg_local[f"Chl{i}"].values.astype(np.float32)
            for i in range(1, 6)
        },
    }
    # POSi (TRAC16) = Darwin's own dense gridded surface biogenic silica, the
    # diatom-specific target for diatomgraz (vs the sparse GEOTRACES-bottle proxy
    # used by POSI_W). bin_native_tracer_to_1deg takes the surface level, so it
    # aligns with the box's surface bsi_1 diagnostic (silica.diagnostic_bsi_steady).
    for var in (["FeT", "POC", "PIC", "DIC", "ALK", "POSi"]
                + (["primProd"] if PRIMPROD_W > 0 else [])):
        out[f"{var.lower()}_binned"] = bin_native_tracer_to_1deg(
            monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable=var,
            lat_min=aoi.lat_min, lat_max=aoi.lat_max,
            lon_min=aoi.lon_min, lon_max=aoi.lon_max,
            iters="all",
        )
    return out


def _load_or_build_target_cache(aoi) -> dict:
    _res = "native" if NATIVE_RES else "1deg"
    _prefix = "native_targets" if NATIVE_RES else "eqpac_targets"
    cache_path = CACHE_DIR / f"{_prefix}_{aoi.name.replace(' ', '_').lower()}.pt"
    expected_bounds = (aoi.lat_min, aoi.lat_max, aoi.lon_min, aoi.lon_max)
    if cache_path.is_file():
        try:
            cached = safe_torch_load(cache_path, map_location="cpu")
            if (cached.get("aoi_name") == aoi.name
                    and cached.get("aoi_bounds") == expected_bounds
                    and cached.get("resolution", "1deg") == _res):
                # Augment older caches that predate POSi without re-binning the
                # five existing tracers (each a full 289-iter native sweep).
                if "posi_binned" not in cached:
                    print("  target cache missing posi_binned; binning POSi (TRAC16)...")
                    cached["posi_binned"] = bin_native_tracer_to_1deg(
                        monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable="POSi",
                        lat_min=aoi.lat_min, lat_max=aoi.lat_max,
                        lon_min=aoi.lon_min, lon_max=aoi.lon_max, iters="all",
                    )
                    try:
                        torch.save(cached, cache_path)
                        print(f"  re-saved target cache with POSi to {cache_path}")
                    except Exception as e:
                        print(f"  [warn] could not re-save cache: {e}")
                if PRIMPROD_W > 0 and "primprod_binned" not in cached:
                    print("  target cache missing primprod_binned; binning primProd (PP)...")
                    cached["primprod_binned"] = bin_native_tracer_to_1deg(
                        monthly_root=MONTHLY_ROOT, grid_dir=GRID_DIR, variable="primProd",
                        lat_min=aoi.lat_min, lat_max=aoi.lat_max,
                        lon_min=aoi.lon_min, lon_max=aoi.lon_max, iters="all",
                    )
                    try:
                        torch.save(cached, cache_path)
                        print(f"  re-saved target cache with primProd to {cache_path}")
                    except Exception as e:
                        print(f"  [warn] could not re-save cache: {e}")
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


def _load_aoi_bundle_native(aoi_key: str) -> dict:
    """O7 native-resolution bundle (NATIVE_RES=1): core z-scored recovery on
    LLC270 native cells (degenerate [1, N_cells] grid). The 1deg-grid GEOTRACES /
    GLODAP-interp losses, the absolute-units anchors, and Darwin-IC override are
    NOT wired natively yet, so they must be OFF (clear error otherwise). Supported:
    core z-targets + PINN + USE_EPPLEY_T + CHL1_W_EXTRA + AOI weights/identity/MLD."""
    _unsupported = {
        "GEOTRACES_POC_SUB_W": GEOTRACES_POC_SUB_W, "POSI_W": POSI_W,
        "PIC_ABS_W": PIC_ABS_W, "POC_ABS_W": POC_ABS_W, "ALK_ABS_W": ALK_ABS_W,
        "RATIO_W": RATIO_W, "F_CO2_ABS_W": F_CO2_ABS_W,
    }
    _on = {k: v for k, v in _unsupported.items() if v and v > 0}
    if _on:
        raise NotImplementedError(
            f"NATIVE_RES=1 does not yet support these loss terms: {_on}. Set them to 0 "
            f"(GEOTRACES-bSi/POC + GLODAP-grid + abs anchors need more native binning). "
            f"Supported: core z-targets + PINN + USE_EPPLEY_T + CHL1_W_EXTRA + POC_SUB_W "
            f"+ Darwin IC + GEOTRACES iron (surf/sub) + POSI_DARWIN_W + AOI levers.")

    aoi = AOI_BY_KEY[aoi_key]
    print(f"\n=== Loading AOI bundle [NATIVE_RES]: {aoi_key} ({aoi.name}) ===")
    targets = _load_or_build_target_cache(aoi)

    sst = targets["sst"]; sss = targets["sss"]; wind = targets["wind"]; mld = targets["mld"]
    pco2_atm_field = targets["pco2_atm_field"]; chl_per_pft = targets["chl_per_pft"]
    fet_binned = targets["fet_binned"]; poc_binned = targets["poc_binned"]
    pic_binned = targets["pic_binned"]; dic_binned = targets["dic_binned"]
    alk_binned = targets["alk_binned"]; co2_flux_darwin = targets["co2_flux_obs"]

    H, W = sst.shape  # (1, N_cells)
    ocean_mask = (
        np.isfinite(sst) & np.isfinite(sss) & np.isfinite(wind)
        & np.isfinite(fet_binned) & np.isfinite(poc_binned) & np.isfinite(pic_binned)
        & np.isfinite(dic_binned) & np.isfinite(alk_binned)
    )
    n_ocean = int(ocean_mask.sum())
    print(f"  native grid: ({H}, {W}); ocean cells (all-finite): {n_ocean}")

    sst_raw_for_env = np.where(ocean_mask, sst, 15.0).astype(np.float32)
    env_1ch = sst_raw_for_env[None]
    mld_raw_for_env = np.where(ocean_mask & np.isfinite(mld), mld, 30.0).astype(np.float32)
    # v3.1 extra env covariate channels (native; SSS is constant here — no native SSS).
    wind_raw_for_env = np.where(ocean_mask & np.isfinite(wind), wind, 7.0).astype(np.float32)
    sss_raw_for_env = np.where(ocean_mask & np.isfinite(sss), sss, 35.0).astype(np.float32)
    pco2_raw_for_env = np.where(
        ocean_mask & np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)
    co2flux_raw_for_env = np.where(
        ocean_mask & np.isfinite(co2_flux_darwin), co2_flux_darwin, 0.0).astype(np.float32)

    mask_dev = torch.tensor(ocean_mask, dtype=torch.bool).to(device)
    mask_f = mask_dev.to(torch.float32); n_ocean_f = mask_f.sum()
    env_1ch_dev = torch.tensor(env_1ch, dtype=torch.float32).to(device)
    T_dev = torch.tensor(np.where(np.isfinite(sst), sst, 15.0).astype(np.float32)).to(device)
    S_dev = torch.tensor(np.where(np.isfinite(sss), sss, 35.0).astype(np.float32)).to(device)
    wind_dev = torch.tensor(np.where(np.isfinite(wind), wind, 7.0).astype(np.float32)).to(device)
    pco2_atm_dev = torch.tensor(
        np.where(np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)).to(device)

    def to_z_target(field):
        clean = np.where(ocean_mask, field, 1.0).astype(np.float32)
        t = torch.tensor(clean, dtype=torch.float32).to(device)
        o = t[mask_dev]; m = o.mean(); s = o.std().clamp(min=1e-6)
        return (t - m) / s
    fet_z = to_z_target(fet_binned); poc_z = to_z_target(poc_binned)
    pic_z = to_z_target(pic_binned); dic_z = to_z_target(dic_binned)
    alk_z = to_z_target(alk_binned); co2_flux_z = to_z_target(co2_flux_darwin)
    chl_z = {f"Chl{i}": to_z_target(chl_per_pft[f"Chl{i}"]) for i in range(1, 6)}

    LIT_IC = [
        5.0e-4, 0.4, 0.3, 0.02, 0.001, 0.65,
        0.5, 0.025, 2050.0 * 1.025, 2350.0 * 1.025,
        5.0e-4, 0.05, 0.003, 2150.0 * 1.025, 2400.0 * 1.025,
    ]
    state0_hw = torch.tensor(LIT_IC, dtype=torch.float32).reshape(
        N_TRACERS_2LAYER, 1, 1).expand(N_TRACERS_2LAYER, H, W).clone()
    poc_l2_z = None
    if USE_DARWIN_IC:
        ic_path = _HERE / f"darwin_ic_cache_native_{aoi_key}.npz"
        if not ic_path.is_file():
            raise FileNotFoundError(
                f"native IC cache not found: {ic_path}. Build it with "
                f"`NATIVE_RES=1 CACHE_NAME=darwin_ic_cache_native_{aoi_key}.npz "
                f"DARWIN_AOI={aoi_key} python scripts/build_darwin_ic_cache.py` "
                f"(or run with DARWIN_IC=0 for literature IC).")
        _ic = np.load(ic_path, allow_pickle=True)
        if "resolution" not in _ic.files or str(_ic["resolution"]) != "native":
            raise ValueError(f"{ic_path} is not a native IC cache (resolution!=native).")
        # Reindex IC native cells onto the target's native-cell ORDER by (xc,yc).
        tg_xc = np.asarray(targets["darwin_lons"]); tg_yc = np.asarray(targets["darwin_lats"])
        lut = {(round(float(x), 4), round(float(y), 4)): i
               for i, (x, y) in enumerate(zip(_ic["native_xc"], _ic["native_yc"]))}
        try:
            order = np.array([lut[(round(float(x), 4), round(float(y), 4))]
                              for x, y in zip(tg_xc, tg_yc)], dtype=np.int64)
        except KeyError as e:
            raise ValueError(f"native IC missing target cell {e}; IC/target AOI mismatch.")
        ic_overrides = [
            (I_DFE_1, "FeT_L1"), (I_POC_1, "POC_L1"), (I_PIC_1, "PIC_L1"),
            (I_DIC_1, "DIC_L1"), (I_ALK_1, "ALK_L1"),
            (I_DFE_2, "FeT_L2"), (I_POC_2, "POC_L2"), (I_PIC_2, "PIC_L2"),
            (I_DIC_2, "DIC_L2"), (I_ALK_2, "ALK_L2"),
        ]
        for state_idx, key in ic_overrides:
            field = _ic[key][order].astype(np.float32)[None]   # [1, N_cells], target order
            field = np.where(np.isfinite(field), field, LIT_IC[state_idx]).astype(np.float32)
            if state_idx in (I_DFE_1, I_DFE_2, I_POC_1, I_POC_2, I_PIC_1, I_PIC_2):
                field = np.clip(field, a_min=1e-10, a_max=None)
            state0_hw[state_idx] = torch.tensor(field, dtype=torch.float32)
        print(f"  loaded native Darwin IC ({ic_path.name}); {order.size} cells reindexed by coord")
        if POC_SUB_W > 0:
            _pl2 = _ic["POC_L2"][order].astype(np.float32)[None]
            poc_l2_z = to_z_target(np.where(np.isfinite(_pl2), _pl2, np.nanmean(_pl2)).astype(np.float32))
    state0_per_seed = state0_hw.unsqueeze(1).expand(
        N_TRACERS_2LAYER, N_SEEDS, H, W).contiguous().to(device)

    # ---- per-cell targets (1-D over N_cells, wrapped to [1, N_cells]) ----
    om = ocean_mask.ravel()
    cxc = np.asarray(targets["darwin_lons"]); cyc = np.asarray(targets["darwin_lats"])
    def _wrap(vals_N, mask_N):
        t = torch.tensor(np.where(mask_N, vals_N, 0.0).astype(np.float32)[None], device=device)
        mk = torch.tensor(mask_N[None], dtype=torch.bool, device=device)
        mf = mk.to(torch.float32)
        return t, mk, mf, mf.sum().clamp(min=1.0)
    def _empty():
        return _wrap(np.zeros(om.size, np.float32), np.zeros(om.size, bool))

    # Dense Darwin POSi (POSI_DARWIN_W) — shape-generic, from native posi_binned.
    _posi = np.asarray(targets.get("posi_binned", np.full((1, om.size), np.nan))).ravel()
    _pd_mask = om & np.isfinite(_posi) & (_posi > 0)
    pd_t, pd_mk, pd_mf, pd_nf = _wrap(_posi, _pd_mask)
    n_posi_dw = int(_pd_mask.sum())

    # GEOTRACES dissolved iron (surface <=50 m, subsurface 50–1000 m) → nearest
    # native cell (KDTree on per-cell xc/yc), accumulate mean per cell.
    n_geo_surf = n_geo_sub = 0
    g_st, g_smk, g_smf, g_snf = _empty(); g_bt, g_bmk, g_bmf, g_bnf = _empty()
    if GEOTRACES_W > 0 or GEOTRACES_SUB_W > 0:
        from scipy.spatial import cKDTree
        geo_aoi = subset_aoi_geotraces(open_geotraces_bottle(GEOTRACES_NC), aoi)
        n_st = geo_aoi.sizes["N_STATIONS"]; n_sa = geo_aoi.sizes["N_SAMPLES"]
        g_lats = np.broadcast_to(geo_aoi.latitude.values[:, None], (n_st, n_sa)).ravel()
        g_lons = np.broadcast_to(geo_aoi.longitude.values[:, None], (n_st, n_sa)).ravel()
        g_dep = geo_aoi.DEPTH.values.ravel()
        g_fe = geo_aoi.Fe_D_CONC.values.ravel()
        g_qc = geo_aoi.Fe_D_CONC_qc.values.ravel()
        _qc = np.array((49, 50))
        finite = (np.isfinite(g_fe) & np.isfinite(g_lats) & np.isfinite(g_lons)
                  & np.isfinite(g_dep) & np.isin(g_qc, _qc.astype(g_qc.dtype)))
        tree = cKDTree(np.column_stack([cxc, cyc]))
        def _bin_obs(keep):
            if int(keep.sum()) == 0:
                return np.zeros(om.size, np.float32), np.zeros(om.size, bool)
            _, idx = tree.query(np.column_stack([g_lons[keep], g_lats[keep]]))
            fe = g_fe[keep] * 1025.0 * 1.0e-6   # nmol/kg -> mmol/m^3
            s = np.zeros(om.size); c = np.zeros(om.size)
            np.add.at(s, idx, fe); np.add.at(c, idx, 1.0)
            nz = c > 0
            out = np.zeros(om.size, np.float32); out[nz] = (s[nz] / c[nz]).astype(np.float32)
            return out, (nz & om)
        _sv, _sm = _bin_obs(finite & (g_dep <= 50.0))
        _bv, _bm = _bin_obs(finite & (g_dep >= SUB_DEPTH_MIN) & (g_dep <= SUB_DEPTH_MAX))
        g_st, g_smk, g_smf, g_snf = _wrap(_sv, _sm)
        g_bt, g_bmk, g_bmf, g_bnf = _wrap(_bv, _bm)
        n_geo_surf = int(_sm.sum()); n_geo_sub = int(_bm.sum())
        print(f"  [native] GEOTRACES iron cells: surf={n_geo_surf}, sub={n_geo_sub}")

    # Still-gated terms → empty placeholders.
    gp_t, gp_mk, gp_mf, gp_nf = _empty(); pa_t, pa_mk, pa_mf, pa_nf = _empty()
    oa_t, oa_mk, oa_mf, oa_nf = _empty(); aa_t, aa_mk, aa_mf, aa_nf = _empty()
    rt_, rmk, rmf, rnf = _empty(); ps_t, ps_mk, ps_mf, ps_nf = _empty()
    fc_t, fc_mk, fc_mf, fc_nf = _empty()

    return {
        "key": aoi_key, "aoi": aoi, "H": H, "W": W,
        "ocean_mask": ocean_mask, "n_ocean": n_ocean,
        "mask_dev": mask_dev, "mask_f": mask_f, "n_ocean_f": n_ocean_f,
        "env_1ch_dev": env_1ch_dev, "mld_raw_for_env": mld_raw_for_env,
        "wind_raw_for_env": wind_raw_for_env, "sss_raw_for_env": sss_raw_for_env,
        "pco2_raw_for_env": pco2_raw_for_env, "co2flux_raw_for_env": co2flux_raw_for_env,
        "T_dev": T_dev, "S_dev": S_dev, "wind_dev": wind_dev, "pco2_atm_dev": pco2_atm_dev,
        "fet_z": fet_z, "poc_z": poc_z, "pic_z": pic_z, "dic_z": dic_z, "alk_z": alk_z,
        "primprod_z": None, "co2_flux_z": co2_flux_z, "chl_z": chl_z, "poc_l2_z": poc_l2_z,
        "geo_surf_target_t": g_st, "geo_surf_mask_t": g_smk, "geo_surf_mask_f": g_smf, "n_geo_surf_f": g_snf,
        "geo_sub_target_t": g_bt, "geo_sub_mask_t": g_bmk, "geo_sub_mask_f": g_bmf, "n_geo_sub_f": g_bnf,
        "n_geo_surf": n_geo_surf, "n_geo_sub": n_geo_sub,
        "geo_poc_target_t": gp_t, "geo_poc_mask_t": gp_mk, "geo_poc_mask_f": gp_mf, "n_geo_poc_f": gp_nf, "n_geo_poc": 0,
        "pic_abs_target_t": pa_t, "pic_abs_mask_t": pa_mk, "pic_abs_mask_f": pa_mf, "n_pic_abs_f": pa_nf, "n_pic_abs": 0,
        "poc_abs_target_t": oa_t, "poc_abs_mask_t": oa_mk, "poc_abs_mask_f": oa_mf, "n_poc_abs_f": oa_nf, "n_poc_abs": 0,
        "alk_abs_target_t": aa_t, "alk_abs_mask_t": aa_mk, "alk_abs_mask_f": aa_mf, "n_alk_abs_f": aa_nf, "n_alk_abs": 0,
        "ratio_target_t": rt_, "ratio_mask_t": rmk, "ratio_mask_f": rmf, "n_ratio_f": rnf, "n_ratio": 0,
        # Native path builds no Daniels target (1deg-only); reuse the ratio zero
        # stub since n_daniels=0 gates the term off (tensors never read).
        "daniels_target_t": rt_, "daniels_mask_t": rmk, "daniels_mask_f": rmf, "n_daniels_f": rnf, "n_daniels": 0,
        "posi_target_t": ps_t, "posi_mask_t": ps_mk, "posi_mask_f": ps_mf, "n_posi_f": ps_nf, "n_posi": 0,
        "posi_dw_target_t": pd_t, "posi_dw_mask_t": pd_mk, "posi_dw_mask_f": pd_mf, "n_posi_dw_f": pd_nf, "n_posi_dw": n_posi_dw,
        "f_co2_abs_target_t": fc_t, "f_co2_abs_mask_t": fc_mk, "f_co2_abs_mask_f": fc_mf, "n_f_co2_abs_f": fc_nf, "n_f_co2_abs": 0,
        # Native-grid path does not wire the Black province anchor; n_black=0 makes the term
        # skip rather than KeyError, matching how every other optional anchor stubs out here.
        "black_value": 0.0, "black_sigma": 0.0, "n_black": 0,
        "state0_per_seed": state0_per_seed,
        "weight": AOI_W[aoi_key],
    }


def load_aoi_bundle(aoi_key: str) -> dict:
    """Build everything per-AOI: tensors, masks, target z-scores, GEOTRACES,
    initial conditions. Returns a dict suitable for hot use in the training loop."""
    if NATIVE_RES:
        return _load_aoi_bundle_native(aoi_key)
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
    co2_flux_darwin = targets["co2_flux_obs"]
    primprod_binned = targets.get("primprod_binned")  # present only when PRIMPROD_W > 0

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
    # v3.1 extra env covariate channels (shared-scaled after bundle load; gated by flags).
    wind_raw_for_env = np.where(ocean_mask & np.isfinite(wind), wind, 7.0).astype(np.float32)
    sss_raw_for_env = np.where(ocean_mask & np.isfinite(sss), sss, 35.0).astype(np.float32)
    pco2_raw_for_env = np.where(
        ocean_mask & np.isfinite(pco2_atm_field), pco2_atm_field, PCO2_ATM_DEFAULT).astype(np.float32)
    co2flux_raw_for_env = np.where(
        ocean_mask & np.isfinite(co2_flux_darwin), co2_flux_darwin, 0.0).astype(np.float32)

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
    co2_flux_z = to_z_target(co2_flux_darwin)
    chl_z = {f"Chl{i}": to_z_target(chl_per_pft[f"Chl{i}"]) for i in range(1, 6)}
    primprod_z = to_z_target(primprod_binned) if (PRIMPROD_W > 0 and primprod_binned is not None) else None

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

    # Absolute-units surface ALK target (ALK_ABS_W) against REAL GLODAP TAlk.
    # The box's surface ALK_1 is driven ONLY by calcite: dALK_1 = -2*R_PICPOC*
    # mort_total -- the SAME product as dPIC_1 -- so this anchors the same
    # R_PICPOC*mort_total the PIC anchor does, but via a real out-of-sample
    # observable (ship-CTD alkalinity) with the 2:1 carbonate stoichiometry, and
    # couples through solve_carbonate (ALK -> pCO2 -> F_CO2). GLODAP TAlk
    # (umol/kg) is regridded (nearest) onto the AOI's Darwin 1deg grid and
    # converted to mmol/m^3. Only loaded when ALK_ABS_W > 0 (needs the external
    # GLODAP file); a NaN target + empty mask reproduces legacy bitwise when off.
    # Same scale-normalized MSE prep as pic_abs/poc_abs.
    alk_abs_binned = np.full_like(sst, np.nan, dtype=np.float32)
    if ALK_ABS_W > 0 and ALK_ABS_SOURCE == "darwin":
        # Control: anchor to Darwin's OWN surface ALK (already binned to the AOI
        # grid), not real GLODAP. Distinguishes real-obs identifiability from the
        # generic absolute-ALK constraint.
        alk_abs_binned = np.asarray(alk_binned, dtype=np.float32)
    elif ALK_ABS_W > 0:  # "glodap" (default)
        try:
            _g_ds = surface_layer_glodap(open_glodap_variable(str(GLODAP_ROOT), "ALK"))
            _g_talk = to_mmol_per_m3(_g_ds["TAlk"])
            _g_on_aoi = _g_talk.interp(
                lat=targets["darwin_lats"], lon=targets["darwin_lons"],
                method="nearest",
            )
            _g_vals = np.asarray(_g_on_aoi.values, dtype=np.float32)
            if _g_vals.shape == sst.shape:
                alk_abs_binned = _g_vals
            else:
                print(f"  [warn] GLODAP ALK regrid shape {_g_vals.shape} != AOI {sst.shape}; skipping")
        except Exception as e:
            print(f"  [warn] ALK_ABS_W={ALK_ABS_W} but GLODAP TAlk load failed ({e}); loss term will be skipped")
    alk_abs_mask_np = ocean_mask & np.isfinite(alk_abs_binned) & (alk_abs_binned > 0)
    alk_abs_target_np = np.where(alk_abs_mask_np, alk_abs_binned, 0.0).astype(np.float32)
    alk_abs_target_t = torch.tensor(alk_abs_target_np).to(device)
    alk_abs_mask_t = torch.tensor(alk_abs_mask_np, dtype=torch.bool).to(device)
    alk_abs_mask_f = alk_abs_mask_t.to(torch.float32)
    n_alk_abs = int(alk_abs_mask_np.sum())
    n_alk_abs_f = alk_abs_mask_f.sum().clamp(min=1.0)
    if ALK_ABS_W > 0:
        if n_alk_abs > 0:
            print(f"  ALK absolute target [{ALK_ABS_SOURCE}]: {n_alk_abs} cells, "
                  f"mean={float(alk_abs_target_t[alk_abs_mask_t].mean()):.2f} mmol/m^3")
        else:
            print(f"  [warn] ALK_ABS_W={ALK_ABS_W} (src={ALK_ABS_SOURCE}) but no finite-positive ALK cells in AOI; loss term will be skipped")

    # PIC:POC RATIO target (RATIO_W): Darwin's own per-cell PIC/POC. Orthogonal
    # handle on R_PICPOC (mort_total cancels in the ratio), so it pins R_PICPOC
    # WITHOUT pinning mort_total (the iron pair's variable). Same scale-normalized
    # MSE prep as pic_abs; masked to cells with finite-positive PIC AND POC.
    ratio_mask_np = (ocean_mask & np.isfinite(pic_binned) & (pic_binned > 0)
                     & np.isfinite(poc_binned) & (poc_binned > 0))
    # Exclude non-physical per-cell ratios (RATIO_MAX, default inf = no-op). Low-POC
    # cells inflate the scale normalizer and collapse the AOI ratio term; capping at a
    # physical rain ratio (~2) removes the artifact. Compute the ratio on the POC>0
    # mask first, then drop cells above the cap.
    with np.errstate(divide="ignore", invalid="ignore"):
        _ratio_all = np.where(ratio_mask_np,
                              pic_binned / np.where(poc_binned > 0, poc_binned, 1.0),
                              0.0).astype(np.float32)
    if np.isfinite(RATIO_MAX):
        n_capped = int((ratio_mask_np & (_ratio_all > RATIO_MAX)).sum())
        ratio_mask_np = ratio_mask_np & (_ratio_all <= RATIO_MAX)
        if RATIO_W > 0 and n_capped > 0:
            print(f"  RATIO_MAX={RATIO_MAX}: excluded {n_capped} non-physical "
                  f"(low-POC) ratio cells from the ratio mask")
    ratio_target_np = np.zeros_like(sst, dtype=np.float32)
    ratio_target_np[ratio_mask_np] = (pic_binned[ratio_mask_np]
                                      / poc_binned[ratio_mask_np]).astype(np.float32)
    ratio_target_t = torch.tensor(ratio_target_np).to(device)
    ratio_mask_t = torch.tensor(ratio_mask_np, dtype=torch.bool).to(device)
    ratio_mask_f = ratio_mask_t.to(torch.float32)
    n_ratio = int(ratio_mask_np.sum())
    n_ratio_f = ratio_mask_f.sum().clamp(min=1.0)
    if RATIO_W > 0:
        if n_ratio > 0:
            print(f"  PIC:POC ratio target: {n_ratio} cells, "
                  f"mean={float(ratio_target_t[ratio_mask_t].mean()):.4f} (Carroll R_PICPOC=0.04245)")
        else:
            print(f"  [warn] RATIO_W={RATIO_W} but no finite-positive PIC&POC cells in AOI; loss term will be skipped")

    # REAL R_PICPOC rain-ratio target (DANIELS_RPICPOC_W): the Daniels et al.
    # 2018 CP:PP incubation compilation (PANGAEA 888182) binned to this AOI's
    # 1deg grid as a per-cell GEOMETRIC-MEAN rain ratio (CP/PP is log-normal).
    # Unlike RATIO_W (whose target is Darwin's OWN PIC/POC -> circular), this is
    # a direct, Darwin-INDEPENDENT observation of calcite:primary production, so
    # it breaks the circularity in grading R_PICPOC. Same scale-normalized MSE
    # prep + bin convention as the GEOTRACES surface iron term (point cloud ->
    # darwin_lats/lons cells). Built only when DANIELS_RPICPOC_W>0 (needs the
    # external .tab); a zero target + empty mask reproduces legacy bitwise when
    # off, and AOIs with no Daniels coverage get an empty mask (term gates off).
    daniels_target_np = np.zeros_like(sst, dtype=np.float32)
    daniels_mask_np = np.zeros_like(ocean_mask, dtype=bool)
    n_daniels_pts = 0
    if DANIELS_RPICPOC_W > 0:
        global _DANIELS_POINTS
        try:
            if _DANIELS_POINTS is None:
                _DANIELS_POINTS = load_daniels_points(DANIELS_PATH)
            d_vals, d_mask, d_counts = bin_daniels_to_grid(
                _DANIELS_POINTS,
                np.asarray(targets["darwin_lats"]),
                np.asarray(targets["darwin_lons"]),
                depth_max=DANIELS_DEPTH_MAX,
            )
            if d_vals.shape == sst.shape:
                daniels_mask_np = ocean_mask & d_mask & np.isfinite(d_vals) & (d_vals > 0)
                daniels_target_np = np.where(daniels_mask_np, d_vals, 0.0).astype(np.float32)
                n_daniels_pts = int(d_counts[daniels_mask_np].sum())
            else:
                print(f"  [warn] Daniels bin shape {d_vals.shape} != AOI {sst.shape}; skipping")
        except Exception as e:
            print(f"  [warn] DANIELS_RPICPOC_W={DANIELS_RPICPOC_W} but Daniels load failed ({e}); loss term will be skipped")
    daniels_target_t = torch.tensor(daniels_target_np).to(device)
    daniels_mask_t = torch.tensor(daniels_mask_np, dtype=torch.bool).to(device)
    daniels_mask_f = daniels_mask_t.to(torch.float32)
    n_daniels = int(daniels_mask_np.sum())
    n_daniels_f = daniels_mask_f.sum().clamp(min=1.0)
    if DANIELS_RPICPOC_W > 0:
        if n_daniels > 0:
            print(f"  Daniels R_PICPOC target: {n_daniels} cells ({n_daniels_pts} samples), "
                  f"geomean={float(np.exp(np.log(daniels_target_np[daniels_mask_np]).mean())):.4f} "
                  f"(Darwin R_PICPOC=0.04245)")
        else:
            print(f"  [warn] DANIELS_RPICPOC_W={DANIELS_RPICPOC_W} but no Daniels coverage in AOI; loss term will be skipped")

    # Dense Darwin POSi target (POSI_DARWIN_W). Darwin's own surface biogenic
    # silica (TRAC16, mmol Si/m^3) binned to the AOI 1deg grid -- a dense,
    # model-consistent, diatom-specific target for `diatomgraz`. Same absolute-
    # units prep as pic_abs/poc_abs; the loss is gated on POSI_DARWIN_W > 0 and
    # compares it to the box's surface bsi_1 diagnostic (silica.py).
    posi_dw_binned = targets.get("posi_binned")
    if posi_dw_binned is None:
        posi_dw_binned = np.full_like(sst, np.nan, dtype=np.float32)
    posi_dw_mask_np = ocean_mask & np.isfinite(posi_dw_binned) & (posi_dw_binned > 0)
    posi_dw_target_np = np.where(posi_dw_mask_np, posi_dw_binned, 0.0).astype(np.float32)
    posi_dw_target_t = torch.tensor(posi_dw_target_np).to(device)
    posi_dw_mask_t = torch.tensor(posi_dw_mask_np, dtype=torch.bool).to(device)
    posi_dw_mask_f = posi_dw_mask_t.to(torch.float32)
    n_posi_dw = int(posi_dw_mask_np.sum())
    n_posi_dw_f = posi_dw_mask_f.sum().clamp(min=1.0)
    if POSI_DARWIN_W > 0:
        if n_posi_dw > 0:
            print(f"  Darwin POSi target: {n_posi_dw} cells, "
                  f"mean={float(posi_dw_target_t[posi_dw_mask_t].mean()):.4f} mmol Si/m^3")
        else:
            print(f"  [warn] POSI_DARWIN_W={POSI_DARWIN_W} but no finite-positive POSi cells in AOI; loss term will be skipped")

    # Absolute-units surface F_CO2 target (F_CO2_ABS_W). Unlike PIC/POC, F_CO2
    # can be either sign (ocean source = positive, sink = negative), so the mask
    # accepts any finite value -- no positivity gate.
    f_co2_abs_mask_np = ocean_mask & np.isfinite(co2_flux_darwin)
    f_co2_abs_target_np = np.where(f_co2_abs_mask_np, co2_flux_darwin, 0.0).astype(np.float32)
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
    # #163 held-out split: pull a spatial fraction of the iron cells OUT of the training
    # mask; keep them for post-training scoring against real held-out iron.
    geo_surf_holdout_mask_t = torch.zeros_like(geo_surf_mask_t)
    if GEOTRACES_HOLDOUT_FRAC > 0:
        _true = geo_surf_mask_t.nonzero(as_tuple=False)
        if len(_true) > 0:
            _n_hold = max(1, int(round(len(_true) * GEOTRACES_HOLDOUT_FRAC)))
            _perm = torch.randperm(len(_true), generator=torch.Generator().manual_seed(GEOTRACES_HOLDOUT_SEED))
            _hi = _true[_perm[:_n_hold]]
            geo_surf_holdout_mask_t[_hi[:, 0], _hi[:, 1]] = True
            geo_surf_mask_t = geo_surf_mask_t & ~geo_surf_holdout_mask_t
            print(f"  [HOLDOUT] surface iron: {int(geo_surf_holdout_mask_t.sum())} of "
                  f"{len(_true)} obs cells held out of training (frac={GEOTRACES_HOLDOUT_FRAC})")
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

    # Black et al. 2020 upper-ocean Fe EXPORT, as a per-province SCALAR (Shape B).
    #
    # It anchors `alpfe`, NOT `scav_rat`, and that is the opposite of how this dataset was
    # carried in the repo. Measured 2026-08-05: at steady state the box's total Fe removal
    # EQUALS `alpfe * PHI_DUST` by mass conservation, so the total export Black measures is
    # pinned by the SOURCE and a 16x sweep of `scav_rat` moves it by 0.00%. Against `alpfe` the
    # same observation needs 73% precision and has 412% in natlsubpolar (short by 6x) but 76%
    # at Kerguelen-Crozet, where three programs cluster. See
    # docs/findings/2026-08-05_the_black2020_sink_anchor_is_a_source_anchor.md
    black_value, black_sigma, n_black = 0.0, 0.0, 0
    if BLACK_ALPFE_W > 0:
        try:
            from darwindiff.black2020_fe_flux_loader import fe_export_province  # noqa: PLC0415
            _v, _s, _n = fe_export_province(aoi)
            if _n > 0 and np.isfinite(_v) and np.isfinite(_s) and _v > 0:
                black_value, black_sigma, n_black = float(_v), float(max(_s, 1e-6)), int(_n)
                print(f"  Black Fe-export province target: {black_value:.4g} "
                      f"+/- {black_sigma:.4g} mmol Fe/m2/yr (n={n_black} programs, "
                      f"sigma/value={black_sigma / black_value:.2f})")
            else:
                print(f"  [warn] BLACK_ALPFE_W={BLACK_ALPFE_W} but no Black coverage in "
                      f"{aoi_key}; loss term will be skipped")
        except Exception as exc:  # loader or data missing -> warn, never silently anchor
            print(f"  [warn] Black loader failed ({exc}); term skipped")

    return {
        "key": aoi_key, "aoi": aoi, "H": H, "W": W,
        "ocean_mask": ocean_mask, "n_ocean": n_ocean,
        "mask_dev": mask_dev, "mask_f": mask_f, "n_ocean_f": n_ocean_f,
        "env_1ch_dev": env_1ch_dev,
        "mld_raw_for_env": mld_raw_for_env,
        "wind_raw_for_env": wind_raw_for_env, "sss_raw_for_env": sss_raw_for_env,
        "pco2_raw_for_env": pco2_raw_for_env, "co2flux_raw_for_env": co2flux_raw_for_env,
        "T_dev": T_dev, "S_dev": S_dev, "wind_dev": wind_dev, "pco2_atm_dev": pco2_atm_dev,
        "fet_z": fet_z, "poc_z": poc_z, "pic_z": pic_z, "dic_z": dic_z, "alk_z": alk_z, "primprod_z": primprod_z,
        "co2_flux_z": co2_flux_z, "chl_z": chl_z, "poc_l2_z": poc_l2_z,
        "geo_surf_target_t": geo_surf_target_t, "geo_surf_mask_t": geo_surf_mask_t,
        "geo_surf_mask_f": geo_surf_mask_f, "n_geo_surf_f": n_geo_surf_f,
        "geo_surf_holdout_mask_t": geo_surf_holdout_mask_t,
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
        "alk_abs_target_t": alk_abs_target_t, "alk_abs_mask_t": alk_abs_mask_t,
        "alk_abs_mask_f": alk_abs_mask_f, "n_alk_abs_f": n_alk_abs_f,
        "n_alk_abs": n_alk_abs,
        "ratio_target_t": ratio_target_t, "ratio_mask_t": ratio_mask_t,
        "ratio_mask_f": ratio_mask_f, "n_ratio_f": n_ratio_f,
        "n_ratio": n_ratio,
        "daniels_target_t": daniels_target_t, "daniels_mask_t": daniels_mask_t,
        "daniels_mask_f": daniels_mask_f, "n_daniels_f": n_daniels_f,
        "n_daniels": n_daniels,
        "posi_target_t": posi_target_t, "posi_mask_t": posi_mask_t,
        "posi_mask_f": posi_mask_f, "n_posi_f": n_posi_f,
        "n_posi": n_posi_in_ocean,
        "posi_dw_target_t": posi_dw_target_t, "posi_dw_mask_t": posi_dw_mask_t,
        "posi_dw_mask_f": posi_dw_mask_f, "n_posi_dw_f": n_posi_dw_f,
        "n_posi_dw": n_posi_dw,
        "f_co2_abs_target_t": f_co2_abs_target_t, "f_co2_abs_mask_t": f_co2_abs_mask_t,
        "f_co2_abs_mask_f": f_co2_abs_mask_f, "n_f_co2_abs_f": n_f_co2_abs_f,
        "n_f_co2_abs": n_f_co2_abs,
        "black_value": black_value, "black_sigma": black_sigma, "n_black": n_black,
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

# v3.1: shared-scale stats for the extra env covariate channels (wind/SSS/pCO2/CO2flux).
_extra_env_stats = {}
for (_rawkey, _lbl) in _ENABLED_EXTRA_ENV:
    _vals = np.concatenate([b[_rawkey][b["ocean_mask"]] for b in bundles])
    _m = float(np.nanmean(_vals)); _s_raw = float(np.nanstd(_vals))
    _s = _s_raw if (np.isfinite(_s_raw) and _s_raw > 0) else 1.0
    _extra_env_stats[_rawkey] = (_m, _s)
    print(f"Shared-scale {_lbl} z-score: mean={_m:.4g}, std={_s:.4g}")

n_input_channels = (1 + (1 if USE_AOI_ID_CHANNEL else 0) + (1 if USE_MLD_CHANNEL else 0)
                    + len(_ENABLED_EXTRA_ENV))

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
    for (_rawkey, _lbl) in _ENABLED_EXTRA_ENV:
        _m, _s = _extra_env_stats[_rawkey]
        _ch = (b[_rawkey] - _m) / _s
        _ch = np.where(b["ocean_mask"], _ch, 0.0).astype(np.float32)
        channels.append(_ch)
        extra_info.append(f"{_lbl} z[{_ch[b['ocean_mask']].min():.2f},{_ch[b['ocean_mask']].max():.2f}]")
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
if USE_GLOBAL_SCALAR:
    print(f"\n[ABLATION] Building {N_SEEDS} GLOBAL-SCALAR nets (one global 6-vector "
          f"per seed, shared across all AOIs — the single-Green's-functions control)...")
    shared_nets = []
    for s in SEEDS:
        torch.manual_seed(s)
        n = GlobalScalarNet(n_input_channels=n_input_channels,
                            hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS).to(device)
        shared_nets.append(n)
    for k in AOIS_KEYS:
        nets_per_aoi[k] = shared_nets  # alias: one global vector applied to every AOI/cell
elif USE_POINTWISE:
    # Free per-cell field. Bound to a grid, so one instance per (seed, AOI) --
    # it cannot be aliased across AOIs the way the shared DINN is. Seeded
    # (seed + aoi_idx * 10000) to match the PER_AOI_DINN convention exactly, so
    # the two per-AOI rungs of the ladder differ ONLY in parameterisation.
    _shape_by_key = {b["key"]: b["ocean_mask"].shape for b in bundles}
    _n_free = sum(N_PARAMS * h * w for (h, w) in _shape_by_key.values())
    print(f"\n[ABLATION] Building {N_SEEDS * N_AOIS} POINTWISE free per-cell fields "
          f"(one per (seed, AOI); NO network, NO covariate conditioning, NO smoothness "
          f"penalty) -- {_n_free:,} free values per seed vs DINN's ~406 weights...")
    for aoi_idx, k in enumerate(AOIS_KEYS):
        h, w = _shape_by_key[k]
        nets_per_aoi[k] = []
        for s in SEEDS:
            torch.manual_seed(s + aoi_idx * 10000)
            n = PerCellFreeField(height=h, width=w, n_input_channels=n_input_channels,
                                 hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS).to(device)
            nets_per_aoi[k].append(n)
        print(f"    {k}: {h}x{w} grid -> {N_PARAMS * h * w:,} free values per seed")
elif USE_PER_AOI_DINN:
    print(f"\nBuilding {N_SEEDS * N_AOIS} per-AOI DINN networks "
          f"(one per (seed, AOI); lambda_consistency={CONSISTENCY_LAMBDA})...")
    for aoi_idx, k in enumerate(AOIS_KEYS):
        nets_per_aoi[k] = []
        for s in SEEDS:
            torch.manual_seed(s + aoi_idx * 10000)
            n = DINN(n_input_channels=n_input_channels, hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS).to(device)
            nets_per_aoi[k].append(n)
elif USE_PER_PARAM:
    # The missing rung. Every other rung above varies SPATIAL sharing; this one varies
    # PARAMETER sharing, which nothing had ever varied (0 of 3000 artifacts). One
    # independent trunk per parameter, so no weight is shared between two parameters'
    # predictions and the MLD-helps-diatomgraz / MLD-breaks-scav_rat conflict has no
    # shared representation to fight over. Pre-registration:
    # docs/findings/2026-08-03_prereg_per_parameter_routing.md
    _w_match = PerParamDINN.matched_hidden_dim(
        n_input_channels=n_input_channels, hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS)
    print(f"\n[LADDER] Building {N_SEEDS} PER-PARAMETER nets ({N_PARAMS} independent trunks "
          f"per seed, hidden_dim={DINN_HIDDEN_DIM}). NOTE: this has ~{N_PARAMS}x the weights "
          f"of one shared trunk -- the capacity-matched control is PER_PARAM=0 with "
          f"DINN_HIDDEN_DIM={_w_match}, and a lift measured against the default width is "
          f"confounded with capacity, not evidence about parameter sharing.")
    shared_nets = []
    for s in SEEDS:
        torch.manual_seed(s)
        n = PerParamDINN(n_input_channels=n_input_channels,
                         hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS).to(device)
        shared_nets.append(n)
    for k in AOIS_KEYS:
        nets_per_aoi[k] = shared_nets
else:
    print(f"\nBuilding {N_SEEDS} shared DINN networks (one per seed; applied to each AOI's env input)...")
    shared_nets: list[DINN] = []
    for s in SEEDS:
        torch.manual_seed(s)
        n = DINN(n_input_channels=n_input_channels, hidden_dim=DINN_HIDDEN_DIM, n_outputs=N_PARAMS).to(device)
        shared_nets.append(n)
    for k in AOIS_KEYS:
        nets_per_aoi[k] = shared_nets  # alias: all AOIs reference the same per-seed nets
print(f"  DINN: n_input_channels={n_input_channels}  hidden_dim={DINN_HIDDEN_DIM}  "
      f"(AOI_ID={USE_AOI_ID_CHANNEL}, MLD={USE_MLD_CHANNEL}, "
      f"extra={[lbl for (_rk, lbl) in _ENABLED_EXTRA_ENV]})")

all_params = []
seen_param_ids: set[int] = set()
for k in AOIS_KEYS:
    for n in nets_per_aoi[k]:
        for p in n.parameters():
            if id(p) not in seen_param_ids:
                seen_param_ids.add(id(p))
                all_params.append(p)
# Default 5e-3 reproduces every prior run. The knob exists so the PRIOR CONTROL
# (NB23_LR=0 with NB23_N_EPOCHS=1) can score UNTRAINED networks through the exact
# same grading path -- same collapse to a per-AOI arithmetic mean, same band
# thresholds, same JSON schema -- giving an EMPIRICAL chance rate per parameter
# rather than one computed from the bounds. N_EPOCHS=0 is not usable for this
# because loss_history[-1] would index an empty tensor.
NB23_LR = float(os.environ.get("NB23_LR", "5e-3"))
optimizer = torch.optim.Adam(all_params, lr=NB23_LR)

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


def _integrate(state0, params, dt, n_steps, T, S, wind, pco2_atm, want_mean: bool = False):
    """Integrate the box. Returns ``(final_state, mean_state_or_None)``.

    ``want_mean`` accumulates a running mean over the window so the loss can compare a
    time-mean model to a time-mean target (see ``TIME_MEAN_LOSS``). It is a running sum, not a
    stored trajectory, so it costs one extra state tensor and nothing in the autograd graph
    depth. The mean EXCLUDES ``state0`` and includes every integrated step, matching the
    convention that the target is an average over the simulated period rather than over the
    initial condition.
    """
    from darwindiff.carroll6_5pft_2layer import H1, H2, KZ_M2_PER_DAY, R_REMIN
    state = state0
    acc = None
    for _ in range(n_steps):
        state = _compiled_step(state, params, dt, T, S, wind, pco2_atm,
                               H1, H2, KZ_M2_PER_DAY, R_REMIN)
        if want_mean:
            acc = state if acc is None else acc + state
    return state, (acc / float(n_steps) if want_mean else None)


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
    state_final, state_mean = _integrate(
        state0, params_b, DT, N_STEPS,
        T=bundle["T_dev"], S=bundle["S_dev"],
        wind=bundle["wind_dev"], pco2_atm=bundle["pco2_atm_dev"],
        want_mean=TIME_MEAN_LOSS,
    )
    # The OBSERVATION terms read `state`; the PHYSICS residual and the returned diagnostic
    # state stay on the endpoint. A steady-state drift residual is a statement about an
    # instant, so averaging it would be a category error -- a mean trajectory can look settled
    # while every instant on it is drifting.
    state = state_mean if TIME_MEAN_LOSS else state_final
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

    # Adequacy lever: per-AOI multiplier on the Darwin-pattern FeT term only. The
    # normaliser carries the SAME weight, so the ten non-FeT terms keep their
    # mean-over-terms scaling when FeT is dropped and this stays a one-term
    # intervention. fet_w == FET_W reproduces the historical divisor exactly.
    fet_w = FET_W * FET_AOI_W[bundle["key"]]
    z = (
        fet_w * tb(dfe1, bundle["fet_z"])
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
    ) * DARWIN_PATTERN_W / (fet_w + 10.0)

    if PINN_W > 0:
        # Always the ENDPOINT, never the window mean: a drift residual is a statement about an
        # instant. state_final is state when TIME_MEAN_LOSS is off, so this is a no-op there.
        sf = state_final
        alpfe_b = params_b[P.alpfe]; scav_rat_b = params_b[P.scav_rat]
        mu_proHL_b = params_b[P.Smallgrow]; mu_lge_b = params_b[P.Biggrow]
        f_fe = sf[I_DFE_1] / (sf[I_DFE_1] + K_FE)
        growth_total = (
            MU_DEFAULT_DIATOM * f_fe * sf[I_DIATOM]
            + mu_lge_b * f_fe * sf[I_LGE]
            + MU_DEFAULT_SYN * f_fe * sf[I_SYN]
            + MU_DEFAULT_PROLL * f_fe * sf[I_PROLL]
            + mu_proHL_b * f_fe * sf[I_PROHL]
        )
        iron_source = alpfe_b * PHI_DUST
        iron_sink = scav_rat_b * 86400.0 * sf[I_DFE_1] * sf[I_POC_1] + Q_FE * growth_total
        dDFe_dt = iron_source - iron_sink
        rel_rate = dDFe_dt / sf[I_DFE_1].clamp(min=1e-10)
        l_pinn = ((rel_rate ** 2) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        z = z + PINN_W * l_pinn

    if PINN_DFE2_W > 0:
        # Subsurface iron drift, taken as the EXACT tendency: for forward Euler
        # (x_{n+1} - x_n)/dt == f(x_n). One extra step, and no second copy of the L2 iron
        # budget to fall out of sync with the model.
        from darwindiff.carroll6_5pft_2layer import H1, H2, KZ_M2_PER_DAY, R_REMIN
        nxt = _compiled_step(state_final, params_b, DT,
                             bundle["T_dev"], bundle["S_dev"],
                             bundle["wind_dev"], bundle["pco2_atm_dev"],
                             H1, H2, KZ_M2_PER_DAY, R_REMIN)
        drift2 = (nxt[I_DFE_2] - state_final[I_DFE_2]) / DT
        rel2 = drift2 / state_final[I_DFE_2].clamp(min=1e-10)
        l_pinn2 = ((rel2 ** 2) * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        z = z + PINN_DFE2_W * l_pinn2

    if BLACK_ALPFE_W > 0 and bundle["n_black"] > 0:
        # Province-scalar Fe EXPORT against Black et al. (2020). The modelled counterpart is the
        # TOTAL iron leaving the surface layer -- scavenged PLUS biogenic -- because a 234Th or
        # sediment-trap export estimate measures particulate Fe crossing a horizon, not the
        # scavenging term alone. Getting that wrong is what made this look like a `scav_rat`
        # anchor for months.
        from darwindiff.carroll6_5pft_2layer import H1 as _H1  # noqa: PLC0415
        scav_flux = params_b[P.scav_rat] * 86400.0 * state[I_DFE_1] * state[I_POC_1]
        f_fe_b = state[I_DFE_1] / (state[I_DFE_1] + K_FE)
        growth_b = (
            MU_DEFAULT_DIATOM * f_fe_b * state[I_DIATOM]
            + params_b[P.Biggrow] * f_fe_b * state[I_LGE]
            + MU_DEFAULT_SYN * f_fe_b * state[I_SYN]
            + MU_DEFAULT_PROLL * f_fe_b * state[I_PROLL]
            + params_b[P.Smallgrow] * f_fe_b * state[I_PROHL]
        )
        # mmol Fe m^-2 yr^-1, the unit both this loader and the Xu-Weber source anchor use.
        fe_export = (scav_flux + Q_FE * growth_b) * _H1 * 365.25
        pred = (fe_export * mask_f[None]).flatten(1).sum(dim=1) / n_ocean_f
        z = z + BLACK_ALPFE_W * ((pred - bundle["black_value"]) / bundle["black_sigma"]) ** 2

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

    # CHL2_W_EXTRA: the Chl2 analogue of CHL1_W_EXTRA, for Biggrow.
    #
    # Motivated by a Gauss-Newton Fisher decomposition of the pattern objective
    # (docs/findings/2026-07-28_session_evidence_log.md section H). Two things
    # that analysis showed, both against expectation:
    #   * The growth pair is NOT mutually degenerate -- Smallgrow+Biggrow is the
    #     LEAST degenerate of all 15 pairs (2x2 cond 1.20, conditional
    #     correlation -0.088), against 5.42 for the iron pair. So the standard
    #     "total NPP gives only the biomass-weighted mean" framing does not
    #     describe this objective, where each growth rate has its own PFT target.
    #   * They are instead INFORMATION-STARVED: relative Fisher information
    #     0.055 (Biggrow) and 0.053 (Smallgrow) against diatomgraz at 1.000.
    # Biggrow's signal is clean and concentrated -- Chl2/P_lge contributes 25.9
    # against ~2.5-3.1 from every other field -- so it is the one growth
    # parameter with a specific observable worth up-weighting. (Smallgrow's is
    # diffuse and its largest single contribution is FeT, so it is read partly
    # through iron and should NOT be expected to respond the same way.)
    #
    # Default 0.0 -> bitwise no-op, so every prior run reproduces.
    if CHL2_W_EXTRA > 0:
        l_chl2_extra = tb(state[I_LGE], bundle["chl_z"]["Chl2"])
        z = z + CHL2_W_EXTRA * l_chl2_extra

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

    # ALK absolute-units MSE on surface ALK vs REAL GLODAP TAlk. The box's
    # surface ALK is calcite-only (dALK_1 = -2*R_PICPOC*mort_total), so this
    # anchors the SAME R_PICPOC*mort_total product as PIC but via a real
    # out-of-sample observable + the 2:1 carbonate stoichiometry, and couples
    # through solve_carbonate (ALK -> pCO2 -> F_CO2 already in `z` above). Tests
    # whether ALK gives R_PICPOC an independent handle (co-recovery with the iron
    # pair) or re-triggers the binary PIC-anchor mutex. Gated on ALK_ABS_W > 0
    # and finite GLODAP cells; `alk` is the integrated surface ALK from above.
    if ALK_ABS_W > 0 and bundle["n_alk_abs"] > 0:
        residual = (alk - bundle["alk_abs_target_t"][None]) * bundle["alk_abs_mask_f"][None]
        scale = (bundle["alk_abs_target_t"][bundle["alk_abs_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_alk_abs_f"] / scale
        z = z + ALK_ABS_W * l

    # PIC:POC RATIO term (RATIO_W). Box PIC_1/POC_1 = R_PICPOC*(W_SINK/W_SINK_PIC)
    # at steady state -- mort_total CANCELS -- so this pins R_PICPOC orthogonally to
    # the iron pair (unlike the separate PIC/POC magnitude anchors, which each pin
    # mort_total and trigger the mutex). Target = Darwin per-cell PIC/POC. `pic`,
    # `poc` are the integrated surface fields from above. Gated on RATIO_W > 0.
    if RATIO_W > 0 and bundle["n_ratio"] > 0:
        ratio_pred = pic / poc.clamp(min=1e-9)
        residual = (ratio_pred - bundle["ratio_target_t"][None]) * bundle["ratio_mask_f"][None]
        scale = (bundle["ratio_target_t"][bundle["ratio_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_ratio_f"] / scale
        z = z + _RATIO_W_NOW * RATIO_AOI_W[bundle["key"]] * l

    # REAL R_PICPOC rain-ratio term (DANIELS_RPICPOC_W). Identical estimator to
    # RATIO_W -- the box's per-cell surface PIC:POC ratio against a scale-
    # normalized MSE target -- but the target is the Darwin-INDEPENDENT Daniels
    # 2018 CP:PP observation (geometric-mean rain ratio per cell), not Darwin's
    # own PIC/POC. This is the term that breaks the circularity: it asks the box
    # to match REAL calcite-production data, per AOI, rather than the model whose
    # calibration we are trying to recover. mort_total cancels in the box ratio,
    # so it pins R_PICPOC orthogonally to the iron pair, exactly like RATIO_W.
    # Gated on DANIELS_RPICPOC_W>0 AND in-AOI Daniels coverage (n_daniels>0).
    if DANIELS_RPICPOC_W > 0 and bundle["n_daniels"] > 0:
        daniels_pred = pic / poc.clamp(min=1e-9)
        residual = (daniels_pred - bundle["daniels_target_t"][None]) * bundle["daniels_mask_f"][None]
        scale = (bundle["daniels_target_t"][bundle["daniels_mask_t"]] ** 2).mean().clamp(min=1e-30)
        l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_daniels_f"] / scale
        z = z + DANIELS_RPICPOC_W * DANIELS_AOI_W[bundle["key"]] * l

    # POSi absolute-units MSE on a steady-state biogenic-silica diagnostic.
    # Compute bsi_1 = R_SI_C * (mort_diatom + graze_diatom) / W_SINK from the
    # integrated state's diatom biomass and the seed's per-cell diatomgraz
    # prediction. Only diatoms produce bSi, so g_diatom enters this term
    # directly via graze_diatom = g_diatom * G0_GRAZE * P_diatom. Compares to
    # surface GEOTRACES bSi obs (bSi_LPT + bSi_SPT, QC 49/50, depth <= 50 m).
    # bsi_1_pred is shared by the GEOTRACES-bottle term (POSI_W) and the dense
    # Darwin-POSi term (POSI_DARWIN_W); compute it once if either is active.
    use_posi_geo = POSI_W > 0 and bundle["n_posi"] > 0
    use_posi_dw = POSI_DARWIN_W > 0 and bundle["n_posi_dw"] > 0
    if use_posi_geo or use_posi_dw:
        g_diatom_b = params_b[P.diatomgraz]
        bsi_1_pred, _ = diagnostic_bsi_steady(p_diatom, g_diatom_b)
        if use_posi_geo:
            residual = (bsi_1_pred - bundle["posi_target_t"][None]) * bundle["posi_mask_f"][None]
            scale = (bundle["posi_target_t"][bundle["posi_mask_t"]] ** 2).mean().clamp(min=1e-30)
            l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_posi_f"] / scale
            z = z + POSI_W * l
        if use_posi_dw:
            residual = (bsi_1_pred - bundle["posi_dw_target_t"][None]) * bundle["posi_dw_mask_f"][None]
            scale = (bundle["posi_dw_target_t"][bundle["posi_dw_mask_t"]] ** 2).mean().clamp(min=1e-30)
            l = (residual ** 2).flatten(1).sum(dim=1) / bundle["n_posi_dw_f"] / scale
            z = z + POSI_DARWIN_W * l

    # primProd (PP): z-scored MSE of the box's diagnosed NPP (growth_total, via
    # npp_from_state) vs Darwin's primary production. A growth-FLUX target adds the
    # growth-rate spatial constraint the z-scored Chl (biomass) loss can't pin --
    # aimed at the stuck `Biggrow`. gamma_T is mean-neutralized exactly as in the
    # step, so it stays consistent under USE_EPPLEY_T. Default off (PRIMPROD_W=0).
    if PRIMPROD_W > 0 and bundle.get("primprod_z") is not None:
        npp_pred = npp_from_state(state, params_b, bundle["T_dev"][None])
        z = z + PRIMPROD_W * tb(npp_pred, bundle["primprod_z"])

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

    # The ENDPOINT is returned as the diagnostic state regardless of TIME_MEAN_LOSS, so
    # `last_states_per_aoi` keeps meaning the same thing across arms and stays comparable.
    return z, state_final


# ============================== Training ==================================

if __name__ == "__main__":

    print(f"\n=== v3.0 joint training: {N_AOIS} AOIs, {N_SEEDS} seeds, {N_EPOCHS} epochs ===")
    t0 = time.time()
    loss_history = torch.full((N_EPOCHS, N_SEEDS), float("nan"), dtype=torch.float32, device=device)
    per_aoi_history = {k: torch.full((N_EPOCHS, N_SEEDS), float("nan"),
                                      dtype=torch.float32, device=device) for k in AOIS_KEYS}

    _apply_consistency_penalty = USE_PER_AOI_DINN and CONSISTENCY_LAMBDA > 0
    for epoch in range(N_EPOCHS):
        optimizer.zero_grad()
        total_loss_per_seed = torch.zeros(N_SEEDS, device=device)

        # Ratio-loss warmup schedule (RATIO_SCHED_START > 0): hold the ratio term at 0
        # until that fraction of epochs, then ramp linearly to full RATIO_W -- lets the
        # growth/iron params settle before R_PICPOC's ratio constraint engages. Default
        # 0.0 leaves _RATIO_W_NOW == RATIO_W (constant) so legacy reproduces bitwise.
        if RATIO_SCHED_START > 0.0:
            _frac = epoch / max(1, N_EPOCHS - 1)
            _ramp = min(1.0, max(0.0, (_frac - RATIO_SCHED_START) / max(1e-9, 1.0 - RATIO_SCHED_START)))
            _RATIO_W_NOW = RATIO_W * _ramp

        # For each AOI, forward that AOI's nets (per seed) on its env input,
        # integrate, compute loss, accumulate weighted. In shared mode the
        # per-AOI lists alias the same set of per-seed nets (same parameters
        # touched across AOIs), reproducing prior behavior bit-identically.
        last_states_per_aoi = {}
        last_params_per_aoi = {}
        per_aoi_param_means = {} if _apply_consistency_penalty else None
        # Dust-anchor accumulators (alpfe SOURCE prior). Cell-weighted sum of the
        # physical alpfe (param index 0) over all AOIs' ocean cells, per seed, plus
        # the total ocean-cell count -- combined after the AOI loop into the joint
        # cell-weighted alpfe the prior pins. Only built when the prior is ON so
        # DUST_ANCHOR_W=0 stays a bitwise no-op (no tensor allocation, no graph node).
        if DUST_ANCHOR_W > 0:
            _dust_alpfe_sum = torch.zeros(N_SEEDS, device=device)
            _dust_cell_count = torch.zeros((), device=device)
        for bundle in bundles:
            env = bundle["env_1ch_dev"]
            aoi_nets = nets_per_aoi[bundle["key"]]
            per_seed_params = [
                bounded_params(net(env), bounds_dev, log_mask=PARAM_LOG_SCALE_MASK)
                for net in aoi_nets
            ]
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
            if DUST_ANCHOR_W > 0:
                # Accumulate the raw (ungated) physical alpfe so the SOURCE prior's
                # gradient reaches alpfe regardless of any per-AOI gating routing.
                _mf = bundle["mask_f"]
                _dust_alpfe_sum = _dust_alpfe_sum + (params_b[0] * _mf[None]).flatten(1).sum(dim=1)
                _dust_cell_count = _dust_cell_count + _mf.sum()
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
            rel_dev_sq = ((stacked - mean_over_aois[None]) / denom[None]) ** 2  # [N_AOIS,6,N_seeds]
            if len(set(CONSISTENCY_LAMBDA_VEC)) == 1:
                # uniform lambda (default / POOL_PARAMS unset) -> exact legacy path (bitwise)
                penalty_per_seed = CONSISTENCY_LAMBDA_VEC[0] * rel_dev_sq.sum(dim=(0, 1))
            else:
                # partial pooling: weight each param by its lambda before summing
                lam = torch.tensor(CONSISTENCY_LAMBDA_VEC, device=rel_dev_sq.device,
                                   dtype=rel_dev_sq.dtype)
                penalty_per_seed = (lam[None, :, None] * rel_dev_sq).sum(dim=(0, 1))  # [N_seeds]
            total_loss_per_seed = total_loss_per_seed + penalty_per_seed

        # Dust anchor (alpfe SOURCE prior): informative Gaussian prior on the joint
        # cell-weighted physical alpfe. DUST_ANCHOR_W * ((alpfe_phys - mu)/sigma)^2 per
        # seed. Guarded so weight 0 leaves total_loss_per_seed untouched (bitwise no-op).
        if DUST_ANCHOR_W > 0:
            alpfe_phys = _dust_alpfe_sum / _dust_cell_count.clamp(min=1e-30)  # [N_seeds]
            dust_penalty = DUST_ANCHOR_W * ((alpfe_phys - DUST_ANCHOR_MU) / DUST_ANCHOR_SIGMA) ** 2
            total_loss_per_seed = total_loss_per_seed + dust_penalty

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

    # PARAM_NAMES + CARROLL_VALUES come from the carroll6.PARAMS registry (imported
    # above) — the single source of truth for the parameter layout + Carroll optima.
    carroll_published = CARROLL_VALUES  # tensor of length 6

    # #163 independent-DATA validation: score the box's final predicted DFe at the
    # HELD-OUT iron cells (never seen in training) vs real GEOTRACES iron. Good skill =>
    # the recovered params generalise to unseen real data (discovery, not just Carroll-consistency).
    # Persisted, not just printed. This block used to print and drop the numbers, so the
    # README had to footnote the held-out result as "reported-but-unarchived": no committed
    # artifact carried it. It is the one number that separates a consistency check from a
    # cross-validated claim (#163), so it goes into the run JSON per seed.
    # `json.dump(..., allow_nan=False)` below will raise on a non-finite value, so sanitise
    # to None here rather than losing the whole run's JSON to one degenerate AOI.
    heldout_by_aoi: dict[str, dict] = {}

    def _finite_or_none(v):
        v = float(v)
        return v if np.isfinite(v) else None

    if GEOTRACES_HOLDOUT_FRAC > 0:
        print()
        print("=== HELD-OUT GEOTRACES iron validation (cells excluded from training) ===")
        for _b in bundles:
            _hm = _b.get("geo_surf_holdout_mask_t")
            _sf = last_states_per_aoi.get(_b["key"]) if _hm is not None else None
            if _hm is None or int(_hm.sum()) == 0 or _sf is None:
                continue
            _pred = _sf[I_DFE_1][:, _hm]                 # [N_seeds, n_hold]
            _real = _b["geo_surf_target_t"][_hm]         # [n_hold]
            _relerr = ((_pred - _real[None]).abs() / _real[None].clamp(min=1e-30)).mean(dim=1)
            _ssr = ((_pred - _real[None]) ** 2).sum(dim=1)
            _sst = ((_real - _real.mean()) ** 2).sum().clamp(min=1e-30)
            _r2 = 1.0 - _ssr / _sst
            print(f"  {_b['key']}: n_holdout={int(_hm.sum())}  "
                  f"held-out rel-err mean={float(_relerr.mean()):.3f} (best {float(_relerr.min()):.3f})  "
                  f"R2 mean={float(_r2.mean()):.3f} (best {float(_r2.max()):.3f})")
            heldout_by_aoi[_b["key"]] = {
                "n_holdout_cells": int(_hm.sum()),
                "n_obs_cells_total": int(_hm.sum() + _b["geo_surf_mask_t"].sum()),
                "r2_per_seed": [_finite_or_none(v) for v in _r2],
                "rel_err_per_seed": [_finite_or_none(v) for v in _relerr],
            }

    all_results = []
    for seed_idx, seed in enumerate(SEEDS):
        print(f"\n=== Seed {seed} recovery ===")
        per_aoi_means = {}
        # ALTERNATIVE COLLAPSE STATISTICS -- recorded, never used for the primary verdict.
        #
        # The per-AOI collapse is an ARITHMETIC mean over ocean cells. For a parameter
        # spanning decades that is the wrong summary: the arithmetic mean of a positive
        # field is dominated by its largest cells, and by Jensen's inequality it is >= the
        # geometric mean, with ratio exp(sigma^2/2) for a lognormal field of log-sd sigma.
        # `scav_rat` spans 100x in its bounds, so this is a live concern, and it is
        # sharpened by an unexplained discrepancy in the record: EKI reports `scav_rat`
        # biased LOW while an arithmetic-mean collapse biases HIGH (evidence log B5,
        # flagged 2026-07-28 and never tested).
        #
        # The collapse is pure REPORTING -- it is not in the loss and does not touch
        # training -- so all three statistics can be computed from the SAME fit. That
        # makes this an exactly PAIRED comparison (identical seeds, identical weights,
        # identical fields) rather than an A/B across arms, which is strictly stronger.
        #
        # `joint_recovered` / `per_aoi_recovered` remain ARITHMETIC so every prior run
        # reproduces bit-identically; these are additive fields only.
        per_aoi_means_geom = {}
        per_aoi_means_median = {}
        per_aoi_log_sd = {}
        # Cache per-AOI per-cell sums + cell counts in one forward pass each,
        # then reuse for both per-AOI means and joint mean (Greptile P2 PR #48).
        weighted_sum = torch.zeros(N_PARAMS, device=device)
        weighted_count = torch.zeros((), device=device)
        weighted_log_sum = torch.zeros(N_PARAMS, device=device)
        _pooled_ocean_vals = []
        for bundle in bundles:
            with torch.no_grad():
                net = nets_per_aoi[bundle["key"]][seed_idx]
                params_b = bounded_params(
                    net(bundle["env_1ch_dev"]), bounds_dev,
                    log_mask=PARAM_LOG_SCALE_MASK,
                )
            mask_f = bundle["mask_f"]
            n_ocean_f = bundle["n_ocean_f"]
            per_cell_sum = (params_b * mask_f[None]).flatten(1).sum(dim=1)  # [6]
            per_aoi_means[bundle["key"]] = (per_cell_sum / n_ocean_f).cpu().numpy()
            weighted_sum = weighted_sum + per_cell_sum
            weighted_count = weighted_count + mask_f.sum()
            # Geometric mean: exp(mean(log p)) over OCEAN cells only. bounded_params
            # guarantees p in (lo, hi) with lo > 0 for every registry entry, so log is
            # safe; the clamp is belt-and-braces against a float32 underflow to 0.
            _logp = params_b.clamp(min=1e-300).log()
            _per_cell_log_sum = (_logp * mask_f[None]).flatten(1).sum(dim=1)  # [6]
            per_aoi_means_geom[bundle["key"]] = (
                torch.exp(_per_cell_log_sum / n_ocean_f).cpu().numpy())
            weighted_log_sum = weighted_log_sum + _per_cell_log_sum
            # Median over ocean cells. Masked by selection, NOT by multiplication --
            # multiplying land cells by 0 would inject a spike of zeros at the low end
            # and drag the median down, which is exactly the kind of silent metric bug
            # the straddle guard exists to catch.
            _ocean_sel = mask_f.reshape(-1) > 0
            _ocean_vals = params_b.flatten(1)[:, _ocean_sel]                 # [6, n_ocean]
            per_aoi_means_median[bundle["key"]] = (
                _ocean_vals.median(dim=1).values.cpu().numpy())
            _pooled_ocean_vals.append(_ocean_vals)
            # THE diagnostic that decides whether the collapse choice matters at all.
            # arithmetic/geometric = exp(sigma^2/2) for a lognormal field of log-sd sigma,
            # and the Cal band is +/-40% RELATIVE, so the arithmetic collapse alone pushes a
            # perfectly geom-centred field out of the band once
            #     exp(sigma^2/2) - 1 > 0.40  <=>  sigma > sqrt(2*ln(1.4)) = 0.8203.
            # Below ~0.3 the effect is under 5% and cannot matter; above ~0.82 it is
            # decisive on its own. Recording sigma per AOI per parameter makes this an
            # answered question rather than a standing worry.
            per_aoi_log_sd[bundle["key"]] = (
                _ocean_vals.clamp(min=1e-300).log().std(dim=1, unbiased=True).cpu().numpy())
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
        # Joint analogues of the alternative collapses. Cell-weighted geometric mean is
        # exp(sum(log p) / total ocean cells); the pooled median is over every ocean cell
        # in every AOI concatenated, which is the honest joint median (a median of medians
        # is not a median).
        joint_means_geom_cellweighted = (
            torch.exp(weighted_log_sum / weighted_count).cpu().numpy())
        joint_means_median_pooled = (
            torch.cat(_pooled_ocean_vals, dim=1).median(dim=1).values.cpu().numpy()
            if _pooled_ocean_vals else joint_means_cellweighted)
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
                # Alternative collapse statistics, PAIRED with the arithmetic ones above
                # (same seed, same weights, same per-cell field). Reporting only; the
                # primary verdict keys are untouched so prior runs reproduce bitwise.
                # A parameter spanning decades is expected to differ most here: the
                # arithmetic mean exceeds the geometric by exp(sigma^2/2) for a lognormal
                # field of log-sd sigma, and the recovery band is RELATIVE, so the gap
                # translates directly into pass/fail.
                "per_aoi_recovered_geom": {
                    k: float(per_aoi_means_geom[k][i]) for k in AOIS_KEYS},
                "per_aoi_recovered_median": {
                    k: float(per_aoi_means_median[k][i]) for k in AOIS_KEYS},
                "joint_geom_cellweighted_recovered": float(joint_means_geom_cellweighted[i]),
                "joint_median_pooled_recovered": float(joint_means_median_pooled[i]),
                # Per-cell log-sd of the recovered field. Decides whether the collapse
                # choice can matter: arith/geom = exp(sigma^2/2), and sigma > 0.8203
                # is where the arithmetic mean alone clears the +/-40% band.
                "per_aoi_log_sd": {
                    k: float(per_aoi_log_sd[k][i]) for k in AOIS_KEYS},
            }
        print(f"       -> joint {n_cal_joint}/6 cal-grade ({n_exc_joint} Excellent)")

        result = {
            "seed": seed,
            "aois": AOIS_KEYS,
            # WHAT CODE PRODUCED THIS NUMBER. Added 2026-08-03 after the published
            # flagship was found bound to a code build: same config, same seeds,
            # scav_rat 60% on the 2026-07-26 tree and 2% on HEAD, with nothing able
            # to detect it because no artifact recorded its own code version.
            "code_provenance": _prov_stamp(__file__),
            "aoi_weights": AOI_W,
            "n_aois": N_AOIS,
            # The integration window. Recorded because it is now swept: before
            # 2026-07-31 it was hardcoded at 200 and no artifact needed to say so,
            # which meant the arms of a window sweep were indistinguishable on the
            # one variable the sweep varied.
            "n_steps": N_STEPS,
            "dt_days": DT,
            "geotraces_w": GEOTRACES_W,
            "n_geo_surf_cells_per_aoi": {b["key"]: b["n_geo_surf"] for b in bundles},
            "geotraces_sub_w": GEOTRACES_SUB_W,
            "n_geo_sub_cells_per_aoi": {b["key"]: b["n_geo_sub"] for b in bundles},
            # The adequacy lever. Recorded for the same reason n_steps is: an arm that
            # varies a weight no artifact carries is indistinguishable from its control
            # on the one variable it varied (#219).
            "fet_aoi_w": dict(FET_AOI_W),
            "pinn_w": PINN_W,
            "pinn_type": PINN_TYPE,
            # The 2x2 arm identifiers. Recorded unconditionally so an arm can never be
            # mistaken for the flagship by an artifact that simply omits the key -- absent
            # is unknown, and that has cost this project a sweep before.
            "time_mean_loss": TIME_MEAN_LOSS,
            "pinn_dfe2_w": PINN_DFE2_W,
            "black_alpfe_w": BLACK_ALPFE_W,
            "n_black_programs_per_aoi": {b["key"]: b["n_black"] for b in bundles},
            "use_darwin_ic": USE_DARWIN_IC,
            "poc_sub_w": POC_SUB_W,
            "geotraces_poc_sub_w": GEOTRACES_POC_SUB_W,
            "n_geo_poc_subsurface_cells_per_aoi": {b["key"]: b["n_geo_poc"] for b in bundles},
            "use_aoi_id_channel": USE_AOI_ID_CHANNEL,
            "use_mld_channel": USE_MLD_CHANNEL,
            "env_extra_channels": [lbl for (_rk, lbl) in _ENABLED_EXTRA_ENV],
            "dinn_hidden_dim": DINN_HIDDEN_DIM,
            "dinn_n_input_channels": n_input_channels,
            "joint_recovery_mode": JOINT_RECOVERY_MODE,
            "chl1_w_extra": CHL1_W_EXTRA,
            "chl2_w_extra": CHL2_W_EXTRA,
            "param_log_scale": PARAM_LOG_SCALE,
            "lr": NB23_LR,
            "per_aoi_dinn": USE_PER_AOI_DINN,
            # Which rung of the parameterisation ladder produced this run. Recorded
            # so a grader can never pool arms that differ in parameterisation, and
            # so an architecture-matched untrained baseline can be checked rather
            # than assumed. `global_scalar` was previously NOT recorded, which meant
            # the 0/50 control's own artifacts did not say they were the control.
            "global_scalar": USE_GLOBAL_SCALAR,
            "pointwise_free_field": USE_POINTWISE,
            "per_param_dinn": USE_PER_PARAM,
            "n_free_param_values": (
                sum(N_PARAMS * int(b["ocean_mask"].shape[0]) * int(b["ocean_mask"].shape[1])
                    for b in bundles) if USE_POINTWISE else None
            ),
            "consistency_lambda": CONSISTENCY_LAMBDA,
            "pool_params": sorted(_pool_set) if _pool_spec else "all",
            "gating_policy": GATING_POLICY_SPEC if USE_GATING else "ungated",
            "aoi_param_weights_file": AOI_PARAM_WEIGHTS or None,
            "aoi_param_weights": ({k: [float(x) for x in gate_vectors[k]]
                                   for k in AOIS_KEYS} if USE_AOI_PARAM_WEIGHTS else None),
            "gating_map": {k: _gating_policy.get(k, []) for k in AOIS_KEYS} if USE_GATING else {},
            "pic_abs_w": PIC_ABS_W,
            "n_pic_abs_cells_per_aoi": {b["key"]: b["n_pic_abs"] for b in bundles},
            "poc_abs_w": POC_ABS_W,
            "n_poc_abs_cells_per_aoi": {b["key"]: b["n_poc_abs"] for b in bundles},
            "alk_abs_w": ALK_ABS_W,
            "alk_abs_source": ALK_ABS_SOURCE if ALK_ABS_W > 0 else None,
            "n_alk_abs_cells_per_aoi": {b["key"]: b["n_alk_abs"] for b in bundles},
            "ratio_w": RATIO_W,
            "n_ratio_cells_per_aoi": {b["key"]: b["n_ratio"] for b in bundles},
            "daniels_rpicpoc_w": DANIELS_RPICPOC_W,
            "daniels_depth_max": DANIELS_DEPTH_MAX if DANIELS_RPICPOC_W > 0 else None,
            "n_daniels_cells_per_aoi": {b["key"]: b["n_daniels"] for b in bundles},
            "dust_anchor_w": DUST_ANCHOR_W,
            "dust_anchor_mu": DUST_ANCHOR_MU if DUST_ANCHOR_W > 0 else None,
            "dust_anchor_sigma": DUST_ANCHOR_SIGMA if DUST_ANCHOR_W > 0 else None,
            "posi_w": POSI_W,
            "n_posi_cells_per_aoi": {b["key"]: b["n_posi"] for b in bundles},
            "posi_darwin_w": POSI_DARWIN_W,
            "primprod_w": PRIMPROD_W,
            "n_posi_dw_cells_per_aoi": {b["key"]: b["n_posi_dw"] for b in bundles},
            "w_sink_pic": _layer2.W_SINK_PIC,
            "r_pic_dissol": _layer2.R_PIC_DISSOL,
            "use_eppley_t": _layer2.USE_EPPLEY_T,
            "a_e_eppley": _layer2.A_E_EPPLEY,
            "t_ref_eppley": _layer2.T_REF_EPPLEY,
            "f_co2_abs_w": F_CO2_ABS_W,
            "n_f_co2_abs_cells_per_aoi": {b["key"]: b["n_f_co2_abs"] for b in bundles},
            "use_mehrbach_k1k2": _carbonate.USE_MEHRBACH_K1K2,
            "k_wanninkhof": _carbonate.K_WANNINKHOF,
            "use_coccolith_only_calcite": _layer2.USE_COCCOLITH_ONLY_CALCITE,
            "fet_w": FET_W,
            "darwin_pattern_w": DARWIN_PATTERN_W,
            "n_epochs": N_EPOCHS,
            "n_seeds_in_batch": N_SEEDS,
            "elapsed_s_total_batch": elapsed,
            "loss_final": float(loss_history[-1, seed_idx].item()),
            "per_aoi_loss_final": {k: float(per_aoi_history[k][-1, seed_idx].item()) for k in AOIS_KEYS},
            # #163 held-out real-data skill for THIS seed. Empty dict when
            # GEOTRACES_HOLDOUT_FRAC=0 (the default), so its presence-and-emptiness is
            # itself the record that the run did not hold anything out.
            "geotraces_holdout_frac": GEOTRACES_HOLDOUT_FRAC,
            "heldout_geotraces_iron": {
                _k: {
                    "n_holdout_cells": _v["n_holdout_cells"],
                    "n_obs_cells_total": _v["n_obs_cells_total"],
                    "r2": _v["r2_per_seed"][seed_idx],
                    "rel_err": _v["rel_err_per_seed"][seed_idx],
                }
                for _k, _v in heldout_by_aoi.items()
            },
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
        perparam_tag = "_perparam" if USE_PER_PARAM else ""
        _gate_preset = GATING_POLICY_SPEC if GATING_POLICY_SPEC in GATING_POLICIES else "custom"
        gate_tag = f"_gate-{_gate_preset}" if USE_GATING else ""
        pic_abs_tag = f"_picabsW{PIC_ABS_W}" if PIC_ABS_W > 0 else ""
        poc_abs_tag = f"_pocabsW{POC_ABS_W}" if POC_ABS_W > 0 else ""
        alk_abs_tag = (f"_alkabsW{ALK_ABS_W}" + (f"-{ALK_ABS_SOURCE}" if ALK_ABS_SOURCE != "glodap" else "")) if ALK_ABS_W > 0 else ""
        ratio_tag = f"_ratioW{RATIO_W}" if RATIO_W > 0 else ""
        daniels_tag = f"_danielsW{DANIELS_RPICPOC_W}" if DANIELS_RPICPOC_W > 0 else ""
        dust_tag = f"_dustW{DUST_ANCHOR_W}" if DUST_ANCHOR_W > 0 else ""
        posi_tag = f"_posiW{POSI_W}" if POSI_W > 0 else ""
        posi_dw_tag = f"_posidwW{POSI_DARWIN_W}" if POSI_DARWIN_W > 0 else ""
        wpic_tag = f"_wpic{_layer2.W_SINK_PIC}" if _layer2.W_SINK_PIC != _layer2.W_SINK else ""
        rpicd_tag = f"_rpicd{_layer2.R_PIC_DISSOL}" if _layer2.R_PIC_DISSOL != _layer2.R_REMIN else ""
        eppley_tag = f"_eppleyT{_layer2.A_E_EPPLEY}" if _layer2.USE_EPPLEY_T else ""
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
                f"{peraoi_tag}{perparam_tag}"
                f"{gate_tag}"
                f"{pic_abs_tag}"
                f"{poc_abs_tag}"
                f"{alk_abs_tag}"
                f"{ratio_tag}"
                f"{daniels_tag}"
                f"{dust_tag}"
                f"{posi_tag}"
                f"{posi_dw_tag}"
                f"{wpic_tag}"
                f"{rpicd_tag}"
                f"{eppley_tag}"
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
