#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=200G
#SBATCH -t 3:30:00
#SBATCH -J dd-window
#SBATCH -o /scratch/qi_zim_neu/window/dd-win_%A_%a.out
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces
for f in "$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025_Seawater.nc"; do [ -f "$f" ] || { echo "MISSING INPUT: $f"; exit 3; }; done
S=/scratch/qi_zim_neu/window

# Pre-registered: docs/findings/2026-07-31_prereg_integration_window_swap.md
# Does the 2026-07-31 depth result survive halving the integration window?
# tasks  0-24 : N_STEPS=100, 5 arms x 5 chunks of 10 seeds
# tasks 25-44 : N_STEPS=400, 4 arms x 5 chunks
# task     45 : bitwise no-op control, eq_sub at N_STEPS=200 vs existing job 240673
I=$SLURM_ARRAY_TASK_ID
if   [ $I -le 24 ]; then W=100; A=$(( I / 5 ));        K=$(( I % 5 ));        ARMS=(so_sub eq_sub prior_so prior_eq eq_surf)
elif [ $I -le 44 ]; then W=400; A=$(( (I-25) / 5 ));   K=$(( (I-25) % 5 ));   ARMS=(so_sub eq_sub prior_so prior_eq)
else                    W=200; A=1; K=0;                                      ARMS=(so_sub eq_sub)
fi
ARM=${ARMS[$A]}
SEEDS=$(seq -s, $(( K * 10 )) $(( K * 10 + 9 )))
[ $I -eq 45 ] && ARM=eq_sub && TAG=repro_w200 || TAG=${ARM}_w${W}

case $ARM in
  so_sub)   AOI=southernoceanpac; AW=AOI_W_SOUTHERNOCEANPAC; GW=0.0; GSW=1.0; LR=1e-3 ;;
  eq_sub)   AOI=eqpac;            AW=AOI_W_EQPAC;            GW=0.0; GSW=1.0; LR=1e-3 ;;
  eq_surf)  AOI=eqpac;            AW=AOI_W_EQPAC;            GW=1.0; GSW=0.0; LR=1e-3 ;;
  prior_so) AOI=southernoceanpac; AW=AOI_W_SOUTHERNOCEANPAC; GW=0.0; GSW=1.0; LR=0    ;;
  prior_eq) AOI=eqpac;            AW=AOI_W_EQPAC;            GW=0.0; GSW=1.0; LR=0    ;;
esac

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[prov] expected 2fb90c86cd8610516155e9347f03e5b5 (N_STEPS-configurable; no-op at 200)"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG aoi=$AOI N_STEPS=$W iron='W=$GW SUB=$GSW' lr=$LR seeds=$SEEDS"

env AOIS=$AOI $AW=2.0 \
N_STEPS=$W \
GEOTRACES_W=$GW GEOTRACES_SUB_W=$GSW \
GEOTRACES_SUB_DEPTH_MIN=50.0 GEOTRACES_SUB_DEPTH_MAX=1000.0 \
NB23_FET_WEIGHT=1.0 NB23_PINN_WEIGHT=0.0 POC_SUB_W=0.0 \
DARWIN_IC=0 MLD_CHANNEL=1 AOI_ID_CHANNEL=0 GATING_POLICY=ungated \
NB23_N_EPOCHS=${EPOCHS:-2000} NB23_LR=$LR NB23_SEEDS=$SEEDS \
OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
