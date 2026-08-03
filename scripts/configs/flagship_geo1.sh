#!/usr/bin/env bash
# Flagship config `n50e2k_percell_trio` (geo1) -- the run every headline number comes from.
#
# WHY THIS FILE EXISTS
# --------------------
# The reproducibility appendix (docs/findings/2026-07-24_reproducibility_methods_appendix.md,
# issue #117) gives the flagship as an override list and says to "source covar_env_common.sh
# first". That file lives at ~/emulator_poc/covar_env_common.sh on the AICR cluster and is NOT
# in this repository, so a reader outside that account cannot reproduce the run: the appendix's
# override list alone omits POSI_W, USE_EPPLEY_T and the per-AOI weights.
#
# Reproducing from the appendix row alone was measured on 2026-07-29 and gives
# `scav_rat` 0/10 where the flagship gets 25/50 -- a silent, material difference.
#
# Every value below was read back out of a verified flagship run artifact
# (`verify_run.py` exit 0; alpfe 49/50, scav_rat 25/50, R_PICPOC 50/50 per-AOI, trio 25/50),
# not transcribed from prose. Values equal to the runner's own defaults are set explicitly
# anyway, so a future default change cannot silently move the flagship.
#
# USAGE
#   source scripts/configs/flagship_geo1.sh
#   python scripts/run_v3.0_joint_multi_aoi.py
#
# Seeds: n>=50 is run as 5 x 10-seed blocks pooled into ONE $OUTPUT_DIR -- never 50 seeds in a
# single process (CUDA OOM). The stored artifact records n_seeds_in_batch=25.

# --- data + AOIs -----------------------------------------------------------------
export DARWIN_DATA_ROOT="${DARWIN_DATA_ROOT:-D:/ecco_darwin_v5}"
export AOIS="eqpac,natlsubpolar,southernoceanpac"
export DARWIN_IC=1                      # Darwin v5 pickup-derived ICs per AOI

# --- per-AOI loss weights --------------------------------------------------------
# NOT in the appendix's override row; it is in the prose above the table as "{1,2,2}".
export AOI_W_EQPAC=1
export AOI_W_NATLSUBPOLAR=2
export AOI_W_SOUTHERNOCEANPAC=2

# --- real-observation anchors ----------------------------------------------------
export GEOTRACES_W=1                    # surface dissolved Fe (IDP2025)
export GEOTRACES_SUB_W=1                # subsurface dissolved Fe, 50-1000 m
export DANIELS_RPICPOC_W=1              # real calcite anchor, PANGAEA 888182
export POSI_W=1                         # GEOTRACES bSi -- omitted from the appendix row
# Requires data/daniels/Daniels_etal_2018_PANGAEA_888182.tab. `data/` is gitignored, so a fresh
# checkout has none of it and the anchor degrades to a [warn]. verify_run.py now FAILS such a
# run (inert-term check) instead of passing it. Stage with:
#   curl -sL "https://doi.pangaea.de/10.1594/PANGAEA.888182?format=textfile" \
#        -o data/daniels/Daniels_etal_2018_PANGAEA_888182.tab

# --- Darwin-target (model-vs-model) block ----------------------------------------
export DARWIN_PATTERN_W=1
export NB23_FET_WEIGHT=1
export POC_SUB_W=3
export CHL1_W_EXTRA=3

# --- physics ---------------------------------------------------------------------
export NB23_PINN_WEIGHT=3               # iron-budget steady-state residual
export USE_EPPLEY_T=1                   # omitted from the appendix row
export NB23_N_EPOCHS=2000
# THE FOURTH OMISSION, found 2026-08-03. This file did not pin the learning rate, and the
# flagship never set it either -- it used the runner default. On 2026-08-01 and again on
# 2026-08-02 the window sweep overrode it to 1e-3, and BOTH runs failed the pre-registered
# falsifier: scav_rat collapses to 1/50 outside the Southern Ocean at 1e-3 and R_PICPOC's
# Southern Ocean leg goes 80% -> 0%. At the default it reproduces (HEAD, lr=5e-3, n=10:
# alpfe 10/10, scav_rat 7/10, R_PICPOC 10/10 with sopac 8/10 against a published 40/50).
# Pinned explicitly so the flagship can never again depend on an unstated default.
export NB23_LR=5e-3
# The integration window, 200 * DT = 50 days. Every published flagship count was produced
# at this window. It was hardcoded until 2026-07-31 and is now env-configurable, so it is
# pinned here: `scav_rat` is anchored on subsurface iron that is only 47.5% converged at
# 200 steps and moves with the window (issue #219). Sweeps override this deliberately.
export N_STEPS=200

# --- parameterisation ------------------------------------------------------------
# Per-cell DINN, SST channel only. Per-cell is load-bearing: the global-scalar control
# holds the trio 0/50.
export GLOBAL_SCALAR=0
export PER_AOI_DINN=0
# The runner reads MLD_CHANNEL / AOI_ID_CHANNEL; USE_* are its internal Python names.
# This file exported the USE_* spelling until 2026-08-02, which nothing reads. It was
# inert rather than wrong, because both values equal the runner's defaults -- but that
# is exactly the silent-default-change this file claims above to protect against.
export MLD_CHANNEL=0                    # MLD helps diatomgraz but breaks scav_rat (2-basin mutex)
export AOI_ID_CHANNEL=0
export GATING_POLICY=ungated

# --- terms explicitly OFF in the flagship ----------------------------------------
# RATIO_W=0 matters: R_PICPOC is anchored by the real Daniels observation, NOT by Darwin's
# own pic/poc ratio. Turning this on would make the R_PICPOC result circular.
export RATIO_W=0
export PIC_ABS_W=0
export POC_ABS_W=0
export ALK_ABS_W=0
export F_CO2_ABS_W=0
export PRIMPROD_W=0
export POSI_DARWIN_W=0
export GEOTRACES_POC_SUB_W=0
export DUST_ANCHOR_W=0
export CONSISTENCY_LAMBDA=0

# --- documented variants ---------------------------------------------------------
#   ep4k .............. NB23_N_EPOCHS=4000          -> scav_rat 41/50
#   anchor-off ........ DANIELS_RPICPOC_W=0         -> R_PICPOC 6/50 (epoch-matched control)
#   global-scalar ..... GLOBAL_SCALAR=1             -> trio 0/50
#   held-out .......... GEOTRACES_HOLDOUT_FRAC=0.2  -> removes 20% of iron cells from training
