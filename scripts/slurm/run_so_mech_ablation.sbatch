#!/bin/bash
#SBATCH --job-name=dd-so-mech
#SBATCH --account=p2026_0089_neu
#SBATCH --partition=b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --time=10:00:00
#SBATCH --mem=48G
#SBATCH --cpus-per-task=8
#SBATCH --array=0-15
#SBATCH --output=/scratch/qi_zim_neu/so_mech/%x_%A_%a.out

# Does scav_rat's Southern Ocean recovery come from SURFACE curvature or DEPTH structure?
#
# Pre-registration: docs/findings/2026-07-30_prereg_scavrat_mechanism_surface_vs_depth.md
# Parent result:    so_only = 30/50 (job 238079, verify_run exit 0), surface+subsurface iron.
#
# The subsurface iron observation enters the objective through EXACTLY one term
# (run_v3.0:1787-1791); dfe2 appears nowhere else but its unpacking at 1736. So
# GEOTRACES_SUB_W=0 is a clean ablation of depth.
#
# PRIMARY read is the volume-matched head-to-head so_surf (13 bins) vs so_sub (14 bins).
# Comparisons against the 27-bin parent are secondary and confounded by data volume.
#
# Arm 3 (so_repro) is the control for the runner sync: the cluster copy was an OLDER,
# unversioned build than repo HEAD. The diff is safe_torch_load, a co2_flux local-variable
# rename, and #163 holdout persistence (inert at GEOTRACES_HOLDOUT_FRAC=0) -- none touch the
# loss math. so_repro re-runs the PARENT config on the new runner for 10 shared seeds; it must
# reproduce job 238079 bitwise, which certifies the sync empirically rather than by reading a diff.

set -uo pipefail
source ~/emulator_poc_pw/covar_env_common.sh >/dev/null 2>&1
cd ~/emulator_poc_pw || { echo "FATAL: cd failed"; exit 1; }
python -c "import torch; assert torch.cuda.is_available()" || { echo "FATAL: import guard"; exit 1; }

# Terms with zero cells in southernoceanpac stay at 0 so the declaration is honest and
# verify_run's inert-term check passes. This is the lesson of 237913.
COMMON="DANIELS_RPICPOC_W=0.0 POSI_W=0.0 DARWIN_PATTERN_W=0.0 POC_SUB_W=0.0 CHL1_W_EXTRA=0.0 NB23_PINN_WEIGHT=0.0 POSI_DARWIN_W=0.0 AOIS=southernoceanpac"

i=$SLURM_ARRAY_TASK_ID
if   [ $i -lt 5  ]; then arm=0; blk=$i
elif [ $i -lt 10 ]; then arm=1; blk=$((i-5))
elif [ $i -lt 15 ]; then arm=2; blk=$((i-10))
else                    arm=3; blk=0
fi

case $arm in
  0) NAME=so_surf;      IRON="GEOTRACES_W=1.0 GEOTRACES_SUB_W=0.0"
     EXTRA="MLD_CHANNEL=1 DARWIN_IC=0 NB23_N_EPOCHS=2000" ;;
  1) NAME=so_sub;       IRON="GEOTRACES_W=0.0 GEOTRACES_SUB_W=1.0"
     EXTRA="MLD_CHANNEL=1 DARWIN_IC=0 NB23_N_EPOCHS=2000" ;;
  2) NAME=prior_so_abl; IRON="GEOTRACES_W=1.0 GEOTRACES_SUB_W=0.0"
     EXTRA="MLD_CHANNEL=1 DARWIN_IC=0 NB23_N_EPOCHS=1 NB23_LR=0" ;;
  3) NAME=so_repro;     IRON="GEOTRACES_W=1.0 GEOTRACES_SUB_W=1.0"
     EXTRA="MLD_CHANNEL=1 DARWIN_IC=0 NB23_N_EPOCHS=2000" ;;
esac

OUT=/scratch/qi_zim_neu/so_mech/${NAME}
base=$((blk*10)); SEEDS=$(seq -s, $base $((base+9)))
mkdir -p "$OUT"

export $COMMON
export $IRON
export $EXTRA
export NB23_SEEDS=$SEEDS
export OUTPUT_DIR=$OUT

echo "[prov] host=$(hostname) runner md5=$(md5sum scripts/run_v3.0_joint_multi_aoi.py | cut -d' ' -f1)"
echo "[prov] parent 238079 ran runner md5=f67f034a53bfb6fd5f1ac0113b665d96 (older build; so_repro is the control)"
echo "[start] $(date -u +%F_%H:%M:%S) task=$i arm=$NAME iron='$IRON' seeds=$SEEDS"
t0=$(date +%s)
python -u scripts/run_v3.0_joint_multi_aoi.py
rc=$?
echo "[done] $(date -u +%F_%H:%M:%S) arm=$NAME rc=$rc elapsed_s=$(( $(date +%s)-t0 )) jsons=$(ls $OUT/*.json 2>/dev/null|wc -l)"
exit $rc
