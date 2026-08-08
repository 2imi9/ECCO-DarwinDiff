#!/bin/bash
#SBATCH --account=p2026_0089_neu
#SBATCH -p cpu
#SBATCH --mem=32G
#SBATCH -t 2:00:00
#SBATCH -J dd-twin-grade
#SBATCH -o /scratch/qi_zim_neu/twin/GRADED_%j.log
set -uo pipefail
module load miniforge3 >/dev/null 2>&1
source ~/dd_venv/bin/activate
cd ~/emulator_poc
export PYTHONPATH=$PWD/src
S=/scratch/qi_zim_neu/twin

# Submitted with --dependency=afterany so it runs whether or not every task succeeded. Grading
# server-side is the point: the login node drops long ssh, and a run graded only in someone's
# terminal is a run that has to be re-graded later from memory.
echo "### loss-comparison self-twin, graded $(date -u +%F_%T)"
echo "### target in {end, mean, long} x loss in {endpoint, time-mean}, single-AOI, truth = Carroll"
echo

SUF=${SEED_BASE:-0}; [ "$SUF" -eq 0 ] && SUF="" || SUF="_s$SUF"

# THE HARNESS FALSIFIER FIRST. eq_ee/na_ee/so_ee (target=end, loss=endpoint) and
# eq_mm/na_mm/so_mm (target=mean, loss=time-mean) compare IDENTICAL objects, so they must
# recover the truth. Printed before anything else, because if a basin's matched cell fails then
# that basin's decisive cells (le / lm) mean nothing and must not be read.
echo "################ MATCHED CELLS -- these MUST pass, or the twin says nothing ################"
for pair in "eq_ee eq_null" "eq_mm eq_null" "na_ee na_null" "na_mm na_null" "so_ee so_null" "so_mm so_null"; do
  set -- $pair; ARM=$1$SUF; NUL=$2$SUF
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

echo "################ DECISIVE CELLS -- target=long, the analogue of a Darwin climatology ########"
for pair in "eq_le eq_null" "eq_lm eq_null" "na_le na_null" "na_lm na_null" "so_le so_null" "so_lm so_null"; do
  set -- $pair; ARM=$1$SUF; NUL=$2$SUF
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

echo "### median recovered value as xTRUTH (truth = Carroll, by construction of the twin)"
echo "### a count that moves without the median moving is a band effect, not recovery"
python - <<'PYEOF'
import json, glob, os, statistics as st
CAR = {"alpfe": 0.928309977054596, "scav_rat": 6.025023253641848e-07,
       "R_PICPOC": 0.04244999960064888}
AOI_OF = {"eq": "eqpac", "na": "natlsubpolar", "so": "southernoceanpac"}
SUF = "" if os.environ.get("SEED_BASE", "0") == "0" else "_s" + os.environ["SEED_BASE"]
TAGS = ("eq_ee","eq_mm","eq_le","eq_lm","eq_null",
        "na_ee","na_mm","na_le","na_lm","na_null",
        "so_ee","so_mm","so_le","so_lm","so_null")
print(f"{'arm':10} {'n':>4} {'alpfe':>10} {'scav_rat':>10} {'R_PICPOC':>10}  degenerate")
for tag in [t + SUF for t in TAGS]:
    fs = sorted(glob.glob(f"/scratch/qi_zim_neu/twin/{tag}/*.json"))
    if not fs:
        print(f"{tag:10}   (missing)"); continue
    aoi = AOI_OF[tag.split("_")[0]]
    row = []
    for p in ("alpfe", "scav_rat", "R_PICPOC"):
        v = [json.load(open(f))["params"][p]["per_aoi_recovered_geom"][aoi] for f in fs]
        row.append(f"{st.median(v)/CAR[p]:10.3f}")
    # P4 of the prereg: TWIN_TARGET=long is EXPECTED to degenerate the diatom pattern target,
    # because under constant forcing the diatom goes extinct to the clamp floor. Surfaced here
    # so the asymmetry between the long arms and the others is visible, never hidden.
    try:
        rep = json.load(open(fs[0]))["config"].get("twin_report") or {}
        deg = (rep.get("per_aoi", {}).get(aoi, {}) or {}).get("degenerate_targets", [])
    except Exception:
        deg = ["?"]
    print(f"{tag:10} {len(fs):>4} " + "".join(row) + "  " + (",".join(deg) if deg else "-"))
PYEOF

echo
echo "### DONE $(date -u +%F_%T)"
