#!/bin/bash
#SBATCH --job-name=dd-hybrid-spatial
#SBATCH --partition=gpu-short
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# Spatial UDE feasibility on an H200: torch.compile fixes the launch-bound
# rollout (report eager-vs-compiled speedup), then learn a 2-input,
# environment-dependent closure f(iron, env) over a 128x128 field end-to-end.
set -euo pipefail

REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONPATH=src
# torch.compile / inductor scratch + cache on the fast project FS, not $HOME
export TORCHINDUCTOR_CACHE_DIR=/projects/schultz/qi.zim/.inductor_cache
OUT=/projects/schultz/qi.zim/runs/hybrid_spatial
mkdir -p "$OUT" "$TORCHINDUCTOR_CACHE_DIR" /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader

.venv/bin/python scripts/hybrid_spatial_h200.py --out "$OUT/result.json" --H 128 --W 128 --steps 200 --epochs 3000

echo "=== done $(date -u +%F_%H:%M:%S); result -> $OUT/result.json ==="
