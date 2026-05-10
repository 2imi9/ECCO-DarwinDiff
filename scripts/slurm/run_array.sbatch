#!/bin/bash
#SBATCH --job-name=darwindiff-ensemble
#SBATCH --account=FIXME_ACCOUNT          # FIXME: ORCD account name
#SBATCH --partition=FIXME_GPU_PARTITION  # FIXME: e.g. sched_mit_orcd_gpu
#SBATCH --array=0-9                      # 10 seeds; override with --array=0-19 for 20 seeds, etc.
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
#   sbatch --array=0-19 scripts/slurm/run_array.sbatch    # 20 seeds
#
# IMPLEMENTATION NOTE: this template currently re-runs the entire nb17
# notebook per array task, relying on the per-seed checkpoint cache to
# short-circuit completed seeds. That works but is wasteful. A future
# scripts/train_seed.py would let each array task train ONLY its assigned
# seed, removing the redundant data loading and analysis. Land that when
# multi-seed becomes a regular workload.

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
