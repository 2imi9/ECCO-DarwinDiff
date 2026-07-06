#!/bin/bash
#SBATCH --job-name=ude-stress
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --time=08:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/projects/schultz/qi.zim/runs/ude_stress_%j.out

# Overnight de-risking sweep for the Track-2 differentiable transport UDE.
# Set QUICK=1 (and a short --time) for a smoke test. OUT overrides the out-dir.
set -euo pipefail
cd /projects/schultz/qi.zim/ecco-darwindiff

OUT="${OUT:-/projects/schultz/qi.zim/runs/ude_stress}"
QUICK_FLAG=""
[ "${QUICK:-0}" = "1" ] && QUICK_FLAG="--quick"

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
source .venv/bin/activate
python scripts/ude_transport_stress_h200.py --out-dir "$OUT" $QUICK_FLAG
