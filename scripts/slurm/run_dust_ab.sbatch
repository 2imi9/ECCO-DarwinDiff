#!/bin/bash
# Dust-anchor A/B recovery comparison on the Explorer H200.
#   BASE_ENV = the completed coord_anchors_pinnOFF config (batch 8536393):
#     anchors-only, PINN OFF, DARWIN_PATTERN_W=0, POC_SUB=0, CHL1_EXTRA=0;
#     real anchors on: GEOTRACES iron (surf+sub W=1.0), Daniels calcite (W=1.0),
#     GEOTRACES bSi (POSI_W=1.0); Eppley-T on (A_E=0.0633); Darwin IC on.
#   array task 0 = config A (DUST_ANCHOR_W=0, bitwise-identical to the baseline)
#   array task 1 = config B (DUST_ANCHOR_W=5, alpfe SOURCE prior N(1.15, 0.7))
# n=10 seeds (0-9) each; 2000 epochs (matches the baseline batch).
#SBATCH --job-name=dd-dust-ab
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --time=08:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=4
#SBATCH --array=0-1
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%A_%a.out
set -uo pipefail
RUNS=/projects/schultz/qi.zim/runs
cd /projects/schultz/qi.zim/ecco-darwindiff
export PATH="$HOME/.local/bin:$PATH"
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces

# --- BASE_ENV: coord_anchors_pinnOFF, exact ---
export AOIS=eqpac,natlsubpolar,southernoceanpac
export GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0
export AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0
export DANIELS_RPICPOC_W=1.0 DANIELS_DEPTH_MAX=50.0 POSI_W=1.0
export USE_EPPLEY_T=1 A_E_EPPLEY=0.0633 T_REF_EPPLEY=15.0
export DINN_HIDDEN_DIM=16 FET_W=1.0 TORCH_COMPILE_BATCHED=0
# anchors_pinnOFF overrides (isolate the pure real-anchor floor):
export DARWIN_PATTERN_W=0.0 POC_SUB_W=0.0 CHL1_W_EXTRA=0.0 NB23_PINN_WEIGHT=0.0
# A/B run size:
export NB23_N_EPOCHS=2000
export NB23_SEEDS=$(seq -s, 0 9)

if [ "$SLURM_ARRAY_TASK_ID" -eq 0 ]; then
  export DUST_ANCHOR_W=0
  export OUTPUT_DIR=$RUNS/dust_ab/A_dustW0
else
  export DUST_ANCHOR_W=5 DUST_ANCHOR_MU=1.15 DUST_ANCHOR_SIGMA=0.7
  export OUTPUT_DIR=$RUNS/dust_ab/B_dustW5
fi
mkdir -p "$OUTPUT_DIR"

echo "[start] $(date -u +%F_%H:%M:%S) node=$(hostname) task=$SLURM_ARRAY_TASK_ID dust_w=$DUST_ANCHOR_W seeds=$NB23_SEEDS out=$OUTPUT_DIR"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
t0=$(date +%s)
uv run python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
t1=$(date +%s)
echo "[done] $(date -u +%F_%H:%M:%S) task=$SLURM_ARRAY_TASK_ID rc=$rc elapsed_s=$((t1-t0)) jsons=$(ls $OUTPUT_DIR/*.json 2>/dev/null | wc -l)"
exit $rc
