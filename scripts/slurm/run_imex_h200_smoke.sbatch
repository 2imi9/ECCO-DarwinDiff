#!/bin/bash
#SBATCH --job-name=dd-imex-smoke
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:10:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# H200 smoke test for the semi-implicit (IMEX) vertical-diffusion fix
# (scripts/imex_h200_smoke.py): proves imex_rollout stays finite/bounded at a
# realistic mixed-layer CFL number r=2.16 where the explicit scheme blows up,
# that checkpointing is bit-identical on-GPU, and that gradients flow -- on the
# real H200 in fp32. Exits non-zero on any failed check. ~seconds once scheduled.
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=src
mkdir -p /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

.venv/bin/python scripts/imex_h200_smoke.py

echo "=== done $(date -u +%F_%H:%M:%S) ==="
