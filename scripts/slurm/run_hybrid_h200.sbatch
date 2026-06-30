#!/bin/bash
#SBATCH --job-name=dd-hybrid-h200
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# Scaled GPU training of the differentiable-BGC / UDE hybrid (Track-2 feasibility).
# Tightens the laptop probe: learns the iron-limitation closure inside the real
# differentiable BGC across a batch of ICs spanning the knee (clean + 5% noise),
# plus deep-gradient and param-recovery confirmations. ~minutes on an H200.
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=src
OUT=/projects/schultz/qi.zim/runs/hybrid_h200
mkdir -p "$OUT" /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

.venv/bin/python scripts/hybrid_h200_train.py --out "$OUT/result.json"

echo "=== done $(date -u +%F_%H:%M:%S); result -> $OUT/result.json ==="
