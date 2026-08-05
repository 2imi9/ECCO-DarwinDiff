#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=64G
#SBATCH -t 1:00:00
#SBATCH -J dd-fw-grade
#SBATCH -o /scratch/qi_zim_neu/flagwin2/GRADED_%j.log
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces
# flagwin2, not flagwin: the 2026-08-01 sweep in flagwin is INVALID (it omitted POSI_W,
# USE_EPPLEY_T and the per-AOI weights, and fs_w200 returned scav_rat 3/50 against the
# published 25/50). Those artifacts are kept as evidence and must never be graded as flagship.
S=/scratch/qi_zim_neu/flagwin2
PY=~/dd_venv/bin/python
P=alpfe,scav_rat,diatomgraz,R_PICPOC

echo "### FLAGSHIP window sweep, graded $(date -u +%F_%T)"
echo "### prereg docs/findings/2026-07-31_prereg_flagship_window_sweep.md"
echo "### PREDICTION: alpfe and R_PICPOC window-INSENSITIVE (anchors converged);"
echo "###             scav_rat window-CONTINGENT (subsurface only 47.5% converged)."
echo "### FALSIFIER: fs_w200 must reproduce the published flagship 49 / 25 / 50."
fail=0
for ARM in fs_w200 fs_w100 fs_w400 fs_null_w100 fs_null_w200 fs_null_w400; do
  echo ""; echo "================ $ARM ================"
  n=$(ls $S/$ARM/*.json 2>/dev/null | wc -l); echo "seeds present: $n / 50"
  [ "$n" -eq 0 ] && { echo "[skip] no artifacts"; continue; }
  $PY scripts/grade_recovery.py $S/$ARM --expect-seeds 50 --params $P --json $S/${ARM}_grade.json
  rc=$?; echo "[gate] $ARM exit=$rc"; [ $rc -ne 0 ] && fail=1
done
echo ""; echo "### GATE_FAIL=$fail"
exit $fail
