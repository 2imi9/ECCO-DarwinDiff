#!/bin/bash
#SBATCH --job-name=darwindiff-ensemble
#SBATCH --account=FIXME_ACCOUNT          # FIXME: ORCD account name
#SBATCH --partition=FIXME_GPU_PARTITION  # FIXME: e.g. sched_mit_orcd_gpu
#SBATCH --array=0-9%1                    # 10 seeds, max 1 concurrent (see SAFETY note below)
#SBATCH --gres=gpu:1
#SBATCH --time=00:30:00                  # per-seed, ~7 min on RTX 5090; trim if your GPU is faster
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=logs/%x_%A_%a.out
#SBATCH --error=logs/%x_%A_%a.err

# Multi-seed ensemble (nb17 pattern). Each array task trains DINNDeep with
# one seed and saves its checkpoint to notebooks/nb17_results/seedA_<NN>.npz.
# After all tasks finish, re-run nb17 (via run_notebook.sbatch or locally)
# and the analysis cells will load the cached seeds and produce the
# trust-map figures + summary JSONs.
#
# Usage:
#   sbatch scripts/slurm/run_array.sbatch
#   sbatch --array=0-19%1 scripts/slurm/run_array.sbatch    # 20 seeds, serialised
#
# === SAFETY: %1 (max 1 concurrent task) is REQUIRED with this script ===
#
# Each array task currently re-runs the FULL notebook with `nbconvert
# --inplace`, which writes back to the shared notebooks/17_*.ipynb file
# at the end of execution. If two tasks run concurrently, both will write
# to the same file with no locking and corrupt it. The per-seed .npz
# cache short-circuits TRAINING for cached seeds, but does NOT prevent
# the concurrent notebook writes — every task always rewrites the
# notebook file, even when training is skipped.
#
# The %1 limiter forces tasks to run one at a time, eliminating the race.
# Total wall-clock = N_seeds × per-seed-time (no parallelism benefit, but
# safe). For N=10 seeds × 7 min ≈ 70 min; for N=20 ≈ 140 min.
#
# To restore parallelism, write a per-seed CLI trainer
# (scripts/train_seed.py) that emits only seedA_NN.npz and never touches
# the notebook file, then point this script at it. That refactor is
# tracked in scripts/slurm/README.md "What's not yet here".

set -euo pipefail

SEED="${SLURM_ARRAY_TASK_ID:-0}"
NOTEBOOK="notebooks/17_dinn_deep_ensemble_disagreement.ipynb"

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

module load python/3.11   # FIXME
module load cuda/12.1     # FIXME
module load gcc/11        # FIXME

export DARWIN_DATA_ROOT="/scratch/$USER/ecco_darwin_v5"
export NB17_TARGET_SEED="$SEED"   # not used by current notebook; reserved for future train_seed.py

if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv sync --all-extras

# Run the notebook. Per-seed cache means cells short-circuit for any
# seed whose .npz already exists — including seeds completed by earlier
# array tasks. Each task picks up wherever it can contribute.
uv run jupyter nbconvert \
    --execute \
    --to notebook \
    --inplace \
    --ExecutePreprocessor.timeout=3600 \
    "$NOTEBOOK"

echo "Array task $SEED done"
