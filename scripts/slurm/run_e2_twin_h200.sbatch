#!/bin/bash
#SBATCH --job-name=dd-e2-twin
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=00:20:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# H200 synthetic-twin dry run of the E2 protocol (scripts/e2_synthetic_twin_h200.py):
# windowed-BPTT closure recovery through prescribed transport at eqpac scale, with a
# BLOCKED/regime hold-out, the null-closure baseline, the learned-minus-null DELTA (the
# real E2 metric), and a K_num ablation. NOT a real-data E2 result -- the "truth" is a
# known closure; this validates the protocol end-to-end on the real H200 before DB-2
# (v05 velocity) + DB-3 (real obs) are staged.
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=src
mkdir -p /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

.venv/bin/python scripts/e2_synthetic_twin_h200.py

echo "=== done $(date -u +%F_%H:%M:%S) ==="
