#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=250G
#SBATCH -t 6:00:00
#SBATCH -J dd-flagwin
#SBATCH -o /scratch/qi_zim_neu/flagwin/dd-fw_%A_%a.out
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces
[ -f "$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025_Seawater.nc" ] || { echo "MISSING GEOTRACES"; exit 3; }
for f in darwin_ic_cache.npz darwin_ic_cache_natlsubpolar.npz darwin_ic_cache_southernoceanpac.npz; do
  [ -f "scripts/$f" ] || { echo "MISSING IC CACHE: scripts/$f"; exit 3; }
done
S=/scratch/qi_zim_neu/flagwin

# Pre-registered: docs/findings/2026-07-31_prereg_flagship_window_sweep.md
# FLAGSHIP geo1 config at three windows, plus window-matched untrained nulls.
# 6 arms x 5 chunks of 10 seeds = 30 tasks.
I=$SLURM_ARRAY_TASK_ID
A=$(( I / 5 )); K=$(( I % 5 ))
WINS=(100 200 400 100 200 400)
LRS=(1e-3 1e-3 1e-3 0 0 0)
TAGS=(fs_w100 fs_w200 fs_w400 fs_null_w100 fs_null_w200 fs_null_w400)
W=${WINS[$A]}; LR=${LRS[$A]}; TAG=${TAGS[$A]}
SEEDS=$(seq -s, $(( K * 10 )) $(( K * 10 + 9 )))

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG N_STEPS=$W lr=$LR seeds=$SEEDS"

env AOIS=eqpac,natlsubpolar,southernoceanpac \
N_STEPS=$W \
DARWIN_IC=1 \
GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0 \
DANIELS_RPICPOC_W=1.0 RATIO_W=0.0 \
NB23_PINN_WEIGHT=3.0 NB23_FET_WEIGHT=1.0 \
POC_SUB_W=3.0 CHL1_W_EXTRA=3.0 DARWIN_PATTERN_W=1.0 \
MLD_CHANNEL=0 AOI_ID_CHANNEL=0 GATING_POLICY=ungated \
NB23_N_EPOCHS=2000 NB23_LR=$LR NB23_SEEDS=$SEEDS \
OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
