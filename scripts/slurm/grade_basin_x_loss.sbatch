#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p cpu
#SBATCH --mem=32G
#SBATCH -t 2:00:00
#SBATCH -J dd-bxl-grade
#SBATCH -o /scratch/qi_zim_neu/bxl/GRADED_%j.log
set -uo pipefail
module load miniforge3 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
S=/scratch/qi_zim_neu/bxl

# Submitted with --dependency=afterany so it runs whether or not every task succeeded. The point
# of grading server-side is that the result exists on disk without a live session: the login node
# drops long ssh, and a run that is graded only in someone's terminal is a run that has to be
# re-graded later from memory.
echo "### basin x loss, graded $(date -u +%F_%T)"
echo "### 3 basins x {endpoint, time-mean}, single-AOI, each vs its own untrained null"
echo

for pair in "eq_end eq_null" "eq_mean eq_null" "na_end na_null" "na_mean na_null" "so_end so_null" "so_mean so_null"; do
  set -- $pair; ARM=$1; NUL=$2
  n=$(ls $S/$ARM 2>/dev/null | wc -l)
  echo "================================================================ $ARM  (n=$n)"
  if [ "$n" -lt 10 ]; then echo "  INCOMPLETE -- skipped"; echo; continue; fi
  echo -n "  verify_run: "; python scripts/verify_run.py $S/$ARM >/dev/null 2>&1; echo "exit=$?"
  for b in 0.10 0.20 0.30 0.40; do
    echo "  --- band $b"
    python scripts/analysis/pooler_audit.py $S/$ARM --null $S/$NUL --band $b \
      --params alpfe,scav_rat,R_PICPOC --legs 2>&1 | grep -E "^(alpfe|scav_rat|R_PICPOC|  alpfe|  scav_rat)"
  done
  echo
done

echo "### median recovered value as xCarroll, per arm"
python - <<'PYEOF'
import json, glob, statistics as st
CAR = {"alpfe": 0.928309977054596, "scav_rat": 6.025023253641848e-07,
       "R_PICPOC": 0.04244999960064888}
AOI_OF = {"eq": "eqpac", "na": "natlsubpolar", "so": "southernoceanpac"}
print(f"{'arm':10} {'alpfe':>10} {'scav_rat':>10} {'R_PICPOC':>10}")
for tag in ("eq_end","eq_mean","eq_null","na_end","na_mean","na_null","so_end","so_mean","so_null"):
    fs = sorted(glob.glob(f"/scratch/qi_zim_neu/bxl/{tag}/*.json"))
    if not fs:
        print(f"{tag:10}   (missing)"); continue
    aoi = AOI_OF[tag.split('_')[0]]
    row = []
    for p in ("alpfe","scav_rat","R_PICPOC"):
        v = [json.load(open(f))["params"][p]["per_aoi_recovered_geom"][aoi] for f in fs]
        row.append(f"{st.median(v)/CAR[p]:10.3f}")
    print(f"{tag:10} " + "".join(row))
PYEOF

echo
echo "### DONE $(date -u +%F_%T)"
