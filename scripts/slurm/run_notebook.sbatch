#!/bin/bash
#SBATCH --job-name=darwindiff-nb
#SBATCH --account=FIXME_ACCOUNT          # FIXME: ORCD account name
#SBATCH --partition=FIXME_GPU_PARTITION  # FIXME: e.g. sched_mit_orcd_gpu
#SBATCH --gres=gpu:1                     # 1 GPU per job; A100 / H100 / V100 fine
#SBATCH --time=04:00:00                  # generous; trim per notebook
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Execute one DarwinDiff notebook end-to-end on a GPU node. Outputs are
# written back into the notebook in-place; intermediate checkpoints (e.g.
# nb17's per-seed .npz files) land in notebooks/<nb-results-dir>/.
#
# Usage:
#   sbatch scripts/slurm/run_notebook.sbatch <notebook-path>
#
# Examples:
#   sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb
#   sbatch scripts/slurm/run_notebook.sbatch notebooks/17_dinn_deep_ensemble_disagreement.ipynb

set -euo pipefail

NOTEBOOK="${1:-notebooks/15_dinn_deep_eqpac_fet.ipynb}"

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if [[ ! -f "$NOTEBOOK" ]]; then
    echo "ERROR: notebook not found at $NOTEBOOK" >&2
    exit 2
fi

# Cluster modules
module load python/3.11    # FIXME
module load cuda/12.1      # FIXME: match the cluster's available CUDA + the PyTorch CU128 wheel pin in pyproject.toml
module load gcc/11         # FIXME

# Data root — must contain the LLC270 monthly tree at $DARWIN_DATA_ROOT/output/monthly
export DARWIN_DATA_ROOT="/scratch/$USER/ecco_darwin_v5"

if [[ ! -d "$DARWIN_DATA_ROOT/output/monthly" ]]; then
    echo "ERROR: $DARWIN_DATA_ROOT/output/monthly missing — transfer the LLC270 tree first" >&2
    exit 3
fi

# Install uv if needed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

uv sync --all-extras

# Sanity check: GPU visible?
uv run python -c "import torch; assert torch.cuda.is_available(), 'no CUDA'; print(f'GPU: {torch.cuda.get_device_name(0)}')"

# Execute the notebook in-place. Timeout 4h (matches --time SBATCH).
uv run jupyter nbconvert \
    --execute \
    --to notebook \
    --inplace \
    --ExecutePreprocessor.timeout=14400 \
    "$NOTEBOOK"

echo "Done: $NOTEBOOK"
