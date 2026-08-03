#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=250G
#SBATCH -t 6:00:00
#SBATCH -J dd-flagwin
#SBATCH -o /scratch/qi_zim_neu/flagwin2/dd-fw_%A_%a.out
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src

# --- the flagship config, sourced not transcribed ---------------------------------
# The 2026-08-01 run of this sweep (job 244487) hand-copied the env list from the
# reproducibility appendix and silently omitted POSI_W, USE_EPPLEY_T and the per-AOI
# weights {1,2,2}. `fs_w200` then returned scav_rat 3/50 against the published 25/50
# and the pre-registered falsifier fired, voiding the whole sweep. Source the canonical
# config so the arms differ from the flagship in the swept variable and nothing else.
CFG=scripts/configs/flagship_geo1.sh
[ -f "$CFG" ] || { echo "MISSING FLAGSHIP CONFIG: $CFG"; exit 3; }
source "$CFG"

# Set AFTER sourcing: the config defaults DARWIN_DATA_ROOT to a local Windows path.
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces

# --- fail fast rather than train a run that is not the flagship --------------------
# Asserts the three values the appendix row omits. A silent non-flagship costs a
# 6-hour array and, last time, an entire session's conclusion.
for chk in "POSI_W=1" "USE_EPPLEY_T=1" "AOI_W_EQPAC=1" "AOI_W_NATLSUBPOLAR=2" "AOI_W_SOUTHERNOCEANPAC=2" "DANIELS_RPICPOC_W=1" "RATIO_W=0"; do
  k=${chk%%=*}; want=${chk#*=}
  got=$(eval "printf '%s' \"\${$k:-<unset>}\"")
  [ "$got" = "$want" ] || { echo "FLAGSHIP CONFIG DRIFT: $k=$got, expected $want"; exit 3; }
done
[ -f "$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025_Seawater.nc" ] || { echo "MISSING GEOTRACES"; exit 3; }
[ -f data/daniels/Daniels_etal_2018_PANGAEA_888182.tab ] || { echo "MISSING DANIELS ANCHOR"; exit 3; }
for f in darwin_ic_cache.npz darwin_ic_cache_natlsubpolar.npz darwin_ic_cache_southernoceanpac.npz; do
  [ -f "scripts/$f" ] || { echo "MISSING IC CACHE: scripts/$f"; exit 3; }
done
S=/scratch/qi_zim_neu/flagwin2

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
echo "[prov] config md5=$(md5sum $CFG | cut -d' ' -f1) git=$(git rev-parse --short HEAD 2>/dev/null || echo none)"
echo "[prov] POSI_W=$POSI_W USE_EPPLEY_T=$USE_EPPLEY_T AOI_W={$AOI_W_EQPAC,$AOI_W_NATLSUBPOLAR,$AOI_W_SOUTHERNOCEANPAC}"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG N_STEPS=$W lr=$LR seeds=$SEEDS"

# Only the two swept variables are overridden; everything else comes from the config.
env N_STEPS=$W NB23_LR=$LR NB23_SEEDS=$SEEDS OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
