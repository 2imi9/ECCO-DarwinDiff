#!/bin/bash
#SBATCH --job-name=dd-rpp-env
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# Environment-dependent rain ratio fit (1deg, 3 AOI) -- deep-research option 3
# (docs/research_notes/2026-06-24_rpicpoc_observability_deep_research.md). Tests
# whether gating R_PICPOC by a coccolithophore thermal window (feasibility-probed
# in scripts/probe_env_rain_ratio.py: 3/3 AOIs, base ~Carroll) lets a SINGLE base
# rate co-recover R_PICPOC + the iron pair in >=2 AOIs -- the >=2-AOI wall that 25
# prior structural arms hit (docs/findings/rpicpoc_ratio_structural.md).
#
# Paired arms (same seeds), submit both:
#   sbatch --export=ALL,RPP_ENV=1 scripts/slurm/run_rpicpoc_env_fit.sbatch   # treatment
#   sbatch --export=ALL,RPP_ENV=0 scripts/slurm/run_rpicpoc_env_fit.sbatch   # control (gated OFF == legacy)
# Then gate each run through scripts/verify_run.py and score per-AOI (NOT just the
# cell-weighted joint mean -- the straddling-artifact lesson, alk_anchor_rpicpoc_mutex).
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"

export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces

# --- env-dependent rain ratio (the fix) ---
export RPP_ENV="${RPP_ENV:-1}"          # 1 = thermal-window gate ON (treatment); 0 = legacy control
# shape + normalization default to the probe-fit constants baked into the model
# (RPP_T_OPT=17.46, RPP_T_WIDTH=2.33, RPP_G_NORM=0.00373); override here to sweep.

# --- v3.2 Eppley 3-AOI operating point (the reproducible-5/6 config) ---
export AOIS=eqpac,natlsubpolar,southernoceanpac
export RATIO_W="${RATIO_W:-2}"          # PIC:POC ratio loss -> identifies R_PICPOC orthogonally to iron pair
export RATIO_MAX="${RATIO_MAX:-2.0}"    # cap non-physical low-POC ratio cells (else SO term collapses)
export COCCOLITH_ONLY=0                  # cocco-only calcite OFF (per research note)
export USE_EPPLEY_T=1
export POSI_W=1.0
export AOI_W_NATLSUBPOLAR=2.0
export AOI_W_SOUTHERNOCEANPAC=2.0
export CHL1_W_EXTRA=3.0
export POSI_DARWIN_W=0.5
export DARWIN_IC=1
export JOINT_RECOVERY_MODE="${JOINT_RECOVERY_MODE:-aoiweighted}"

export NB23_SEEDS="${NB23_SEEDS:-0,1,2,3,4,5,6,7,8,9}"
export NB23_N_EPOCHS="${NB23_N_EPOCHS:-1500}"
export TORCH_COMPILE_BATCHED="${TORCH_COMPILE_BATCHED:-1}"

if [ "$RPP_ENV" = "1" ]; then TAG=on; else TAG=off; fi
# OUTPUT_DIR overridable so sensitivity arms (e.g. different RATIO_MAX, same seeds)
# don't collide on identical JSON filenames; default keeps the on/off convention.
export OUTPUT_DIR="${OUTPUT_DIR:-/projects/schultz/qi.zim/runs/rpicpoc_env_${TAG}}"
mkdir -p "$OUTPUT_DIR" /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) | RPP_ENV=$RPP_ENV ($TAG) | seeds=$NB23_SEEDS | epochs=$NB23_N_EPOCHS | ratio_w=$RATIO_W ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "OUTPUT_DIR=$OUTPUT_DIR"

uv run python scripts/run_v3.0_joint_multi_aoi.py

echo "=== done $(date -u +%F_%H:%M:%S); recovered Carroll-6 + per-AOI JSON in $OUTPUT_DIR ==="
