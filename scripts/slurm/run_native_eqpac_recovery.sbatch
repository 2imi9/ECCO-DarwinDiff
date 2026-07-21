#!/bin/bash
#SBATCH --job-name=dd-native-eqpac
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=02:00:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# First MEASURED native-resolution Carroll-6 recovery on an Explorer H200 (#84/#85/#123 prep).
# Reproduces the O7 native eqpac config: native LLC270 time-mean targets + Darwin v5
# pickup-derived IC + GEOTRACES iron (surf/sub). Synthetic-input infra runs (memory/timing)
# said nothing about recovery quality; THIS is the first real fit on the cluster.
#
# Compiled-vs-eager correctness gate -- submit TWICE, same seeds, compare recovered Carroll-6:
#   sbatch --export=ALL,TORCH_COMPILE_BATCHED=1 scripts/slurm/run_native_eqpac_recovery.sbatch   # production
#   sbatch --export=ALL,TORCH_COMPILE_BATCHED=0 scripts/slurm/run_native_eqpac_recovery.sbatch   # eager reference
# The two recovered-parameter vectors must agree (within optimizer noise) before we trust any
# compiled cluster science. Then gate each run through scripts/verify_run.py (recompute-from-raw).
#
# First invocation builds the native target cache (bins ~290 iters x 10 tracers from the LLC270
# tiles -> DARWIN_DATA_ROOT/cache/native_targets_*.pt); subsequent runs reuse it (~minutes).
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"

# --- staged data roots (all under the 1.5 TB /projects/schultz cap) ---
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5      # grid/ + output/monthly/<tracer>/
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces        # GEOTRACES_IDP2025_Seawater.nc

# --- native eqpac recovery config (matches the O7 re-baseline) ---
export NATIVE_RES=1            # native LLC270 cells, no 1deg binning
export DARWIN_IC=1            # Darwin v5 pickup-derived ICs (cache pushed: darwin_ic_cache_native_eqpac.npz)
export AOIS=eqpac
export NB23_SEEDS="${NB23_SEEDS:-5}"
export NB23_N_EPOCHS="${NB23_N_EPOCHS:-1500}"
# NATIVE_RES=1 forbids PIC_ABS/POC_ABS/POSI_W/ALK_ABS/RATIO/F_CO2_ABS (runner raises if set);
# GEOTRACES iron (surf/sub) + POC_SUB_W + Darwin IC ARE native-supported and stay at defaults.

# --- compile lever (override via --export=ALL,TORCH_COMPILE_BATCHED=0 for the eager reference) ---
export TORCH_COMPILE_BATCHED="${TORCH_COMPILE_BATCHED:-1}"
if [ "$TORCH_COMPILE_BATCHED" = "1" ]; then TAG=compiled; else TAG=eager; fi
export OUTPUT_DIR="/projects/schultz/qi.zim/runs/native_eqpac_${TAG}"
mkdir -p "$OUTPUT_DIR" /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) | compile=$TORCH_COMPILE_BATCHED ($TAG) | seeds=$NB23_SEEDS | epochs=$NB23_N_EPOCHS ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
echo "DARWIN_DATA_ROOT=$DARWIN_DATA_ROOT  ->  $(ls "$DARWIN_DATA_ROOT/output/monthly" 2>/dev/null | tr '\n' ' ')"

uv run python scripts/run_v3.0_joint_multi_aoi.py

echo "=== done $(date -u +%F_%H:%M:%S); recovered Carroll-6 + JSON in $OUTPUT_DIR ==="
