#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=250G
#SBATCH -t 6:00:00
#SBATCH -J dd-kerg
#SBATCH -o /scratch/qi_zim_neu/kerg/dd-kg_%A_%a.out
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

# Single-AOI, so AOIS is overridden deliberately. Everything else stays flagship.
for chk in "POSI_W=1" "USE_EPPLEY_T=1" "DANIELS_RPICPOC_W=1" "RATIO_W=0" "N_STEPS=200" "NB23_LR=5e-3"; do
  k=${chk%%=*}; want=${chk#*=}
  got=$(eval "printf '%s' \"\${$k:-<unset>}\"")
  [ "$got" = "$want" ] || { echo "FLAGSHIP CONFIG DRIFT: $k=$got, expected $want"; exit 3; }
done
[ -f "$GEOTRACES_DATA_ROOT/GEOTRACES_IDP2025_Seawater.nc" ] || { echo "MISSING GEOTRACES"; exit 3; }
[ -f scripts/darwin_ic_cache_kerguelen.npz ] || { echo "MISSING KERGUELEN IC CACHE"; exit 3; }
grep -q '"kerguelen"' scripts/run_v3.0_joint_multi_aoi.py || {
  echo "RUNNER PREDATES THE KERGUELEN AOI -- pull before submitting"; exit 3; }

S=/scratch/qi_zim_neu/kerg
mkdir -p $S

# WHY THIS AOI. Kerguelen-Crozet holds 18 surface / 20 total GEOTRACES dissolved-Fe bins --
# MORE than southernoceanpac's 13/14, the one basin where `scav_rat` is established -- in the
# same HNLC, scavenging-dominated regime. The question is whether that regional identifiability
# is a property of the REGIME (and so transfers) or of that particular box.
#
# This is the `so_only` template: single-AOI, sited where the data is, which is what produced
# the project's one result where `scav_rat` clears its own null.
#
# NO BLACK ANCHOR ARM. The Black et al. 2020 province anchor is implemented (BLACK_ALPFE_W) and
# Kerguelen holds the densest cluster in that compilation, but its sigma/value is 7.29 against
# the 0.73 needed to grade `alpfe` -- the WORST of the three covered provinces, because its
# three programs span a factor of 19. An arm at that weight would measure an inert term. The
# lever stays off; it is waiting on data with a tighter spread, not on compute.
I=$SLURM_ARRAY_TASK_ID
A=$(( I / 5 )); K=$(( I % 5 ))
LRS=(5e-3 0)
TAGS=(kg_base kg_null)
LR=${LRS[$A]}; TAG=${TAGS[$A]}
SEEDS=$(seq -s, $(( K * 10 )) $(( K * 10 + 9 )))

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[prov] config md5=$(md5sum $CFG | cut -d' ' -f1) git=$(git rev-parse --short HEAD 2>/dev/null || echo none)"
echo "[start] $(date -u +%F_%T) task=$I tag=$TAG AOIS=kerguelen lr=$LR seeds=$SEEDS"

env AOIS=kerguelen NB23_LR=$LR NB23_SEEDS=$SEEDS OUTPUT_DIR=$S/$TAG \
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "=== rc=$rc $(date -u +%F_%T) tag=$TAG ==="
exit $rc
