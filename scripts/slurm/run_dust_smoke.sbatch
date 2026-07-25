#!/bin/bash
# Cluster de-risk smoke for the dust-anchor edit: 2 epochs, 1 seed, on an H200.
# Runs W=0 then W=5 sequentially with the real anchors_pinnOFF env; confirms the
# modified run_v3.0 runs end-to-end on the cluster GPU and writes dust metadata.
#SBATCH --job-name=dd-dust-smoke
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --time=00:25:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=4
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
set -uo pipefail
RUNS=/projects/schultz/qi.zim/runs
cd /projects/schultz/qi.zim/ecco-darwindiff
export PATH="$HOME/.local/bin:$PATH"
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces
export AOIS=eqpac,natlsubpolar,southernoceanpac
export GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0
export AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0
export DANIELS_RPICPOC_W=1.0 DANIELS_DEPTH_MAX=50.0 POSI_W=1.0
export USE_EPPLEY_T=1 A_E_EPPLEY=0.0633 T_REF_EPPLEY=15.0
export DINN_HIDDEN_DIM=16 FET_W=1.0 TORCH_COMPILE_BATCHED=0
export DARWIN_PATTERN_W=0.0 POC_SUB_W=0.0 CHL1_W_EXTRA=0.0 NB23_PINN_WEIGHT=0.0
export NB23_N_EPOCHS=2 NB23_SEEDS=0
echo "[smoke] node=$(hostname)"; nvidia-smi --query-gpu=name --format=csv,noheader || true
export OUTPUT_DIR=$RUNS/dust_ab/smoke_w0; mkdir -p "$OUTPUT_DIR"
DUST_ANCHOR_W=0 uv run python -u scripts/run_v3.0_joint_multi_aoi.py 2>&1 | tail -3
export OUTPUT_DIR=$RUNS/dust_ab/smoke_w5; mkdir -p "$OUTPUT_DIR"
DUST_ANCHOR_W=5 DUST_ANCHOR_MU=1.15 DUST_ANCHOR_SIGMA=0.7 uv run python -u scripts/run_v3.0_joint_multi_aoi.py 2>&1 | tail -3
echo "[smoke done] jsons_w0=$(ls $RUNS/dust_ab/smoke_w0/*.json 2>/dev/null | wc -l) jsons_w5=$(ls $RUNS/dust_ab/smoke_w5/*.json 2>/dev/null | wc -l)"
