#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=250G
#SBATCH -t 6:00:00
#SBATCH -J dd-tmloss
#SBATCH -o /scratch/qi_zim_neu/tmloss/dd-tm_%A_%a.out
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src

# --- the flagship config, sourced not transcribed ---------------------------------
# Two window-sweep submissions were voided by hand-transcribing this list. Source it.
CFG=scripts/configs/flagship_geo1.sh
[ -f "$CFG" ] || { echo "MISSING FLAGSHIP CONFIG: $CFG"; exit 3; }
source "$CFG"

export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces

for chk in "POSI_W=1" "USE_EPPLEY_T=1" "AOI_W_EQPAC=1" "AOI_W_NATLSUBPOLAR=2" "AOI_W_SOUTHERNOCEANPAC=2" "DANIELS_RPICPOC_W=1" "RATIO_W=0" "N_STEPS=200" "NB23_LR=5e-3"; do
  k=${chk%%=*}; want=${chk#*=}
  got=$(eval "printf '%s' \"\${$k:-<unset>}\"")
  [ "$got" = "$want" ] || { echo "FLAGSHIP CONFIG DRIFT: $k=$got, expected $want"; exit 3; }
done
[ -f "$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025_Seawater.nc" ] || { echo "MISSING GEOTRACES"; exit 3; }
[ -f data/daniels/Daniels_etal_2018_PANGAEA_888182.tab ] || { echo "MISSING DANIELS ANCHOR"; exit 3; }
for f in darwin_ic_cache.npz darwin_ic_cache_natlsubpolar.npz darwin_ic_cache_southernoceanpac.npz; do
  [ -f "scripts/$f" ] || { echo "MISSING IC CACHE: scripts/$f"; exit 3; }
done

# The lever must EXIST in this checkout. The AICR tree is unversioned (#218) and has been one
# build behind HEAD before; without this the control and the arm would be the same run and the
# result would read as "the change does nothing".
grep -q 'TIME_MEAN_LOSS' scripts/run_v3.0_joint_multi_aoi.py || {
  echo "RUNNER PREDATES TIME_MEAN_LOSS -- pull before submitting"; exit 3; }

S=/scratch/qi_zim_neu/tmloss
mkdir -p $S

# Pre-registered: docs/findings/2026-08-06_prereg_time_mean_loss.md
#
# THREE arms x 5 chunks of 10 seeds = 15 tasks.
#   tm_ctrl  endpoint loss  -- the flagship, verified BITWISE identical to the pre-change
#                              runner, so this reproduces rather than approximates it
#   tm_mean  TIME_MEAN_LOSS=1
#   tm_null  untrained
#
# ONE null, not two. An untrained parameter head's output does not depend on the loss, and the
# 2026-08-05 window sweep confirmed it empirically: its three window-matched nulls were bitwise
# identical to all 16 significant figures. Three null arms there were three copies of one result.
I=$SLURM_ARRAY_TASK_ID
A=$(( I / 5 )); K=$(( I % 5 ))
TMS=(0 1 0)
LRS=(5e-3 5e-3 0)
TAGS=(tm_ctrl tm_mean tm_null)
TM=${TMS[$A]}; LR=${LRS[$A]}; TAG=${TAGS[$A]}

# SEED_BASE shifts the whole seed block, so a replication is a DISJOINT sample rather than a
# re-run of the same 50 seeds. Default 0 reproduces job 287072 exactly. The tag carries the base
# so a replication can never overwrite the run it is replicating -- which is how you end up
# "replicating" a result against itself.
SEED_BASE=${SEED_BASE:-0}
[ "$SEED_BASE" -eq 0 ] || TAG="${TAG}_s${SEED_BASE}"
SEEDS=$(seq -s, $(( SEED_BASE + K * 10 )) $(( SEED_BASE + K * 10 + 9 )))

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[prov] config md5=$(md5sum $CFG | cut -d' ' -f1) git=$(git rev-parse --short HEAD 2>/dev/null || echo none)"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG TIME_MEAN_LOSS=$TM lr=$LR seeds=$SEEDS"

# PINN_DFE2_W stays 0. Measured 2026-08-06: at Carroll's own parameters DFe_2 drifts
# 1.68e-02/day at the 200-step window against DFe_1's 2.84e-05, and does not settle until
# ~3200 steps -- so a subsurface steady-state penalty here is nonzero AT THE TRUTH and would
# pull the fit away from Carroll. It is the right term for a converged-window arm, not this one.
env TIME_MEAN_LOSS=$TM NB23_LR=$LR NB23_SEEDS=$SEEDS OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
