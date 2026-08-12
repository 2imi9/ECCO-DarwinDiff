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

SUF=${SEED_BASE:-0}; [ "$SUF" -eq 0 ] && SUF="" || SUF="_s$SUF"
NEED=50
GRADE_FAILED=0
for pair in "eq_end eq_null" "eq_mean eq_null" "na_end na_null" "na_mean na_null" "so_end so_null" "so_mean so_null"; do
  set -- $pair; ARM=$1$SUF; NUL=$2$SUF
  n=$(ls $S/$ARM/*.json 2>/dev/null | wc -l)
  n_null=$(ls $S/$NUL/*.json 2>/dev/null | wc -l)
  echo "================================================================ $ARM  (n=$n/$NEED, null=$n_null/$NEED)"
  # An arm is 5 chunks x 10 seeds. Accepting a partial arm here would report counts, p-values and
  # medians from, say, 10 seeds as though the pre-registered 50-seed experiment had completed --
  # and nothing downstream would say otherwise. Refuse instead.
  if [ "$n" -ne "$NEED" ]; then
    echo "  INCOMPLETE ($n of $NEED seeds) -- NOT GRADED. Re-run the missing chunks; do not"
    echo "  quote a partial arm, and do not compare it against a complete one."
    GRADE_FAILED=2
    echo; continue
  fi
  if [ "$n_null" -ne "$NEED" ]; then
    echo "  INCOMPLETE NULL ($n_null of $NEED seeds) -- NOT GRADED. The null arm must be"
    echo "  complete before any significance can be trusted."
    GRADE_FAILED=2
    echo; continue
  fi
  # verify_run's EXIT CODE gates the arm. Printing it and grading anyway is how an unverified
  # number reaches a write-up.
  python scripts/verify_run.py $S/$ARM >/dev/null 2>&1; vr=$?
  echo "  verify_run arm: exit=$vr"
  if [ "$vr" -ne 0 ]; then
    GRADE_FAILED=2
    echo "  VERIFY FAILED -- NOT GRADED (run verify_run.py by hand to see why)"; echo; continue
  fi
  python scripts/verify_run.py $S/$NUL >/dev/null 2>&1; vr=$?
  echo "  verify_run null: exit=$vr"
  if [ "$vr" -ne 0 ]; then
    GRADE_FAILED=2
    echo "  VERIFY FAILED NULL -- NOT GRADED (run verify_run.py by hand to see why)"; echo; continue
  fi
  for b in 0.10 0.20 0.30 0.40; do
    echo "  --- band $b"
    POOLER_OUTPUT=$(python scripts/analysis/pooler_audit.py $S/$ARM --null $S/$NUL \
      --band $b --params alpfe,scav_rat,R_PICPOC --legs 2>&1)
    POOLER_RC=$?
    if [ "$POOLER_RC" -ne 0 ]; then
      echo "  POOLER AUDIT FAILED (exit=$POOLER_RC) -- NOT GRADED"
      printf '%s\n' "$POOLER_OUTPUT"
      GRADE_FAILED=2
      break
    fi
    printf '%s\n' "$POOLER_OUTPUT" \
      | grep -E "^(alpfe|scav_rat|R_PICPOC|  alpfe|  scav_rat)" \
      || { echo "  POOLER OUTPUT MISSING -- NOT GRADED"; GRADE_FAILED=2; break; }
  done
  echo
done

echo "### median recovered value as xCarroll, per arm"
python - <<'PYEOF'
import json, glob, statistics as st, subprocess
CAR = {"alpfe": 0.928309977054596, "scav_rat": 6.025023253641848e-07,
       "R_PICPOC": 0.04244999960064888}
AOI_OF = {"eq": "eqpac", "na": "natlsubpolar", "so": "southernoceanpac"}
print(f"{'arm':10} {'n':>4} {'alpfe':>10} {'scav_rat':>10} {'R_PICPOC':>10}")
import os
SUF = "" if os.environ.get("SEED_BASE","0")=="0" else "_s"+os.environ["SEED_BASE"]
summary_failed = False
for tag in [t+SUF for t in ("eq_end","eq_mean","eq_null","na_end","na_mean","na_null","so_end","so_mean","so_null")]:
    fs = sorted(glob.glob(f"/scratch/qi_zim_neu/bxl/{tag}/*.json"))
    if not fs:
        print(f"{tag:10}   (missing)"); summary_failed = True; continue
    if len(fs) != 50:
        print(f"{tag:10} {len(fs):>4}   INCOMPLETE -- medians suppressed")
        summary_failed = True
        continue
    run_dir = f"/scratch/qi_zim_neu/bxl/{tag}"
    vr = subprocess.run(
        ["python", "scripts/verify_run.py", run_dir],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode
    if vr != 0:
        print(f"{tag:10} {len(fs):>4}   GATED (verify_run={vr}) -- medians suppressed")
        summary_failed = True
        continue
    aoi = AOI_OF[tag.split("_")[0]]
    try:
        records = [json.load(open(f)) for f in fs]
        row = []
        for p in ("alpfe","scav_rat","R_PICPOC"):
            v = [d["params"][p]["per_aoi_recovered_geom"][aoi] for d in records]
            row.append(f"{st.median(v)/CAR[p]:10.3f}")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(f"{tag:10} {len(fs):>4}   GATED ({type(exc).__name__}: geometric collapse unavailable)")
        summary_failed = True
        continue
    print(f"{tag:10} {len(fs):>4} " + "".join(row))
raise SystemExit(2 if summary_failed else 0)
PYEOF
SUMMARY_RC=$?
if [ "$SUMMARY_RC" -ne 0 ]; then
  echo "### MEDIAN SUMMARY FAILED (exit=$SUMMARY_RC)"
  GRADE_FAILED=2
fi

echo
echo "### DONE $(date -u +%F_%T)"
exit "$GRADE_FAILED"
