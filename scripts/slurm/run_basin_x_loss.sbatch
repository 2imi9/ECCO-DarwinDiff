#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=250G
#SBATCH -t 6:00:00
#SBATCH -J dd-bxl
#SBATCH -o /scratch/qi_zim_neu/bxl/dd-bxl_%A_%a.out
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src

CFG=scripts/configs/flagship_geo1.sh
[ -f "$CFG" ] || { echo "MISSING FLAGSHIP CONFIG: $CFG"; exit 3; }
source "$CFG"
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces

for chk in "POSI_W=1" "USE_EPPLEY_T=1" "DANIELS_RPICPOC_W=1" "RATIO_W=0" "N_STEPS=200" "NB23_LR=5e-3"; do
  k=${chk%%=*}; want=${chk#*=}
  got=$(eval "printf '%s' \"\${$k:-<unset>}\"")
  [ "$got" = "$want" ] || { echo "FLAGSHIP CONFIG DRIFT: $k=$got, expected $want"; exit 3; }
done
grep -q 'TIME_MEAN_LOSS' scripts/run_v3.0_joint_multi_aoi.py || {
  echo "RUNNER PREDATES TIME_MEAN_LOSS -- pull before submitting"; exit 3; }

S=/scratch/qi_zim_neu/bxl
mkdir -p $S

# THE QUESTION. Job 287072/287277 showed that TIME_MEAN_LOSS relocates recovery: the equatorial
# Pacific recovers the iron pair (replicated) while natlsubpolar and southernoceanpac fall back
# toward untrained. Is that a property of the BASIN, or an artifact of the JOINT fit -- three
# basins sharing one network and one optimiser, weighted 1/2/2?
#
# 3 basins x 2 losses, each SINGLE-AOI, each with its own untrained null. Single-AOI removes the
# joint fit entirely, so:
#   natl/SO recover alone under time-mean  -> the collapse is a JOINT-FIT effect (weighting,
#                                             shared network, or gradient competition)
#   natl/SO fail alone too                -> the collapse is INTRINSIC to those basins under a
#                                             time-mean comparison
# Either answer is decisive and neither is the hoped-for one.
#
# 9 arms x 5 chunks of 10 seeds = 45 tasks. ONE null per basin: an untrained parameter head does
# not depend on the loss, verified bitwise across the three window-matched nulls of job 270032.
I=$SLURM_ARRAY_TASK_ID
A=$(( I / 5 )); K=$(( I % 5 ))
AOI_L=(eqpac      eqpac      eqpac      natlsubpolar natlsubpolar natlsubpolar southernoceanpac southernoceanpac southernoceanpac)
TM_L=( 0          1          0          0            1            0            0                1                0)
LR_L=( 5e-3       5e-3       0          5e-3         5e-3         0            5e-3             5e-3             0)
TAG_L=(eq_end     eq_mean    eq_null    na_end       na_mean      na_null      so_end           so_mean          so_null)
AOI=${AOI_L[$A]}; TM=${TM_L[$A]}; LR=${LR_L[$A]}; TAG=${TAG_L[$A]}

# SEED_BASE shifts the whole block so a replication is a DISJOINT sample, and it is appended to
# the tag so the replication cannot overwrite the run it is checking. Default 0 reproduces the
# original submission exactly.
SEED_BASE=${SEED_BASE:-0}
[ "$SEED_BASE" -eq 0 ] || TAG="${TAG}_s${SEED_BASE}"
SEEDS=$(seq -s, $(( SEED_BASE + K * 10 )) $(( SEED_BASE + K * 10 + 9 )))

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[prov] git=$(git rev-parse --short HEAD 2>/dev/null || echo none)"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG AOIS=$AOI TIME_MEAN_LOSS=$TM lr=$LR seeds=$SEEDS"

env AOIS=$AOI TIME_MEAN_LOSS=$TM NB23_LR=$LR NB23_SEEDS=$SEEDS OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
