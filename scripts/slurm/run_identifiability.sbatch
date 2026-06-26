#!/bin/bash
#SBATCH --job-name=dd-fim
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
set -euo pipefail
REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces
export RPP_ENV=0 RATIO_W=2 RATIO_MAX=2.0 COCCOLITH_ONLY=0 USE_EPPLEY_T=1
export POSI_W=1.0 AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0
export CHL1_W_EXTRA=3.0 POSI_DARWIN_W=0.5 DARWIN_IC=1 JOINT_RECOVERY_MODE=aoiweighted
export TORCH_COMPILE_BATCHED=0
export AOIS="${AOIS:-eqpac,natlsubpolar,southernoceanpac}"
DIAG_ARGS="${DIAG_ARGS:---param alpfe --grid 11 --opt-steps 600}"
echo "=== FIM diag | AOIS=$AOIS | args=$DIAG_ARGS ==="
nvidia-smi --query-gpu=name --format=csv,noheader
uv run python -u scripts/identifiability_sloppiness.py $DIAG_ARGS
echo "=== FIM diag done ==="
