#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p b200-batch
#SBATCH --gres=gpu:b200:1
#SBATCH --mem=64G
#SBATCH -t 1:00:00
#SBATCH -J dd-win-grade
#SBATCH -o /scratch/qi_zim_neu/window/GRADED_%j.log
set -uo pipefail
module load miniforge3 cuda/13.1.1 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
export DARWIN_DATA_ROOT=$HOME/dd_data/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=$HOME/dd_data/geotraces
S=/scratch/qi_zim_neu/window
PY=~/dd_venv/bin/python
P=alpfe,scav_rat,diatomgraz,R_PICPOC

echo "### window swap, graded $(date -u +%F_%T)"
echo "### prereg docs/findings/2026-07-31_prereg_integration_window_swap.md"
echo "### PRIMARY: eq_sub_w100 vs eq_sub@200 (6/50) and so_sub_w100 vs so_sub@200 (33/50)"
echo "### H_window = basins TRADE PLACES.  H_depth = ordering survives.  P<0.01 both tails."
fail=0
for ARM in so_sub_w100 eq_sub_w100 prior_so_w100 prior_eq_w100 eq_surf_w100 \
           so_sub_w400 eq_sub_w400 prior_so_w400 prior_eq_w400 repro_w200; do
  echo ""; echo "================ $ARM ================"
  n=$(ls $S/$ARM/*.json 2>/dev/null | wc -l)
  echo "seeds present: $n"
  [ "$n" -eq 0 ] && { echo "[skip] no artifacts"; continue; }
  EXP=50; [ "$ARM" = "repro_w200" ] && EXP=10
  $PY scripts/grade_recovery.py $S/$ARM --expect-seeds $EXP --params $P --json $S/${ARM}_grade.json
  rc=$?; echo "[gate] $ARM exit=$rc"; [ $rc -ne 0 ] && fail=1
done

echo ""
echo "### NO-OP CONTROL: repro_w200 vs the original eq_sub (job 240673)"
echo "### The runner changed (3d5ebe67 -> 2fb90c86). At N_STEPS=200 it must agree."
#
# This block used to inline a comparison that read params[k]['joint'] -- a key artifacts do
# not have (they store 'joint_recovered'). Every lookup returned None, nothing was compared,
# the running max stayed at its 0.0 initialiser, and it printed "BITWISE IDENTICAL" having
# examined zero values. Re-run honestly on 2026-08-02 it reports DIFFERS at 1.7%.
# compare_run_bitwise.py exits 2 rather than 0 when it compares too few values.
$PY scripts/analysis/compare_run_bitwise.py \
    /scratch/qi_zim_neu/window/repro_w200 /scratch/qi_zim_neu/eq_mech/eq_sub \
    --min-values 100
echo "[noop-control] exit=$?  (0 identical, 1 differs, 2 VACUOUS)"

echo ""
echo "### Does that drift flip any Cal grade? (the question the drift size alone cannot answer)"
$PY scripts/analysis/grade_flip_under_drift.py \
    /scratch/qi_zim_neu/window/repro_w200 /scratch/qi_zim_neu/eq_mech/eq_sub
echo "[grade-flip] exit=$?  (0 no flips, 1 a grade flipped, 2 VACUOUS)"

echo ""; echo "### GATE_FAIL=$fail"
exit $fail
