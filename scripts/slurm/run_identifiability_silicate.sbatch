#!/bin/bash
#SBATCH --job-name=dd-fim-si
#SBATCH --gres=gpu:1
#SBATCH --exclude=c2204,c2205,c2206,c2207,d1002,d1007,d1009,d1010,d1011,d1012,d1013,d1015,d1017,d1019,d1020,d1022,d1027
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=06:00:00
#SBATCH --array=0-12%7
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%A_%a.out
set -euo pipefail
REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces
# --- identical to run_identifiability.sbatch (the 2026-07-07 config) EXCEPT the
#     silica weights, which are the ablation lever below.
export RPP_ENV=0 RATIO_W=2 RATIO_MAX=2.0 COCCOLITH_ONLY=0 USE_EPPLEY_T=1
export AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0
export CHL1_W_EXTRA=3.0 DARWIN_IC=1 JOINT_RECOVERY_MODE=aoiweighted
export TORCH_COMPILE_BATCHED=0
export AOIS="eqpac,natlsubpolar,southernoceanpac"

PARAMS=(alpfe scav_rat Smallgrow Biggrow diatomgraz R_PICPOC)
I=${SLURM_ARRAY_TASK_ID}
OUTDIR=$REPO/docs/findings/silicate_scope
mkdir -p "$OUTDIR"

if [ "$I" -lt 6 ]; then
  # ARM A: WITH silica observables (the 2026-07-07 config; sparse GEOTRACES bSi + dense Darwin POSi)
  P=${PARAMS[$I]}; TAG=si
  export POSI_W=1.0 POSI_DARWIN_W=0.5
  LOSSARG="--loss full"
elif [ "$I" -lt 12 ]; then
  # ARM B: silica observables REMOVED (the counterfactual "before silicate")
  P=${PARAMS[$((I-6))]}; TAG=nosi
  export POSI_W=0.0 POSI_DARWIN_W=0.0
  LOSSARG="--loss full"
else
  # ARM C: REAL GEOTRACES biogenic-silica residual ONLY (n=11 bottles; interpret with care)
  P=diatomgraz; TAG=realbsi
  export POSI_W=1.0 POSI_DARWIN_W=0.5
  LOSSARG="--loss realbsi"
fi

OUT=$OUTDIR/fim_${P}_${TAG}.json
echo "=== FIM silicate-scope | task=$I param=$P arm=$TAG POSI_W=$POSI_W POSI_DARWIN_W=$POSI_DARWIN_W $LOSSARG ==="
nvidia-smi --query-gpu=name --format=csv,noheader
uv run python -u scripts/identifiability_sloppiness.py \
  --param "$P" $LOSSARG --grid 11 --opt-steps 600 --out "$OUT"
echo "=== FIM silicate-scope done | wrote $OUT ==="
