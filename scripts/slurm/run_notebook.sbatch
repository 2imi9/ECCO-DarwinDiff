#!/bin/bash
#SBATCH --job-name=darwindiff-nb
# ORCD Engaging: --account is NOT required (open to all MIT users).
# If your PI requires a specific allocation, add: #SBATCH --account=<pi>
#SBATCH --partition=mit_normal_gpu       # ORCD GPU pool: L40S 44GB, H100 80GB, H200 140GB.
# For A100-SXM4-80GB or A100-PCIe-80GB use mit_preemptable + --requeue:
#     #SBATCH --partition=mit_preemptable
#     #SBATCH --requeue
#SBATCH --gres=gpu:1                     # 1 GPU; type-pin via -G l40s:1 / -G h100:1 if needed
#SBATCH --time=04:00:00                  # generous; trim per notebook (nb15-class is ~5 min on L40S)
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Execute one DarwinDiff notebook end-to-end on a GPU node. Outputs are
# written back into the notebook in-place; intermediate checkpoints land
# in notebooks/<nb-results-dir>/.
#
# Usage on ORCD Engaging:
#   sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb
#   sbatch scripts/slurm/run_notebook.sbatch notebooks/17_dinn_deep_ensemble_disagreement.ipynb

set -euo pipefail

NOTEBOOK="${1:-notebooks/15_dinn_deep_eqpac_fet.ipynb}"

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if [[ ! -f "$NOTEBOOK" ]]; then
    echo "ERROR: notebook not found at $NOTEBOOK" >&2
    exit 2
fi

# ORCD Engaging: miniforge ships Python + CUDA — single module load.
# PyTorch is then pulled from CU128 wheels via pyproject.toml.
module purge
module load miniforge/24.3.0-0

# Data root — must contain LLC270 monthly tree at $DARWIN_DATA_ROOT/output/monthly.
# Default points at personal scratch but the LLC270 tree is ~1.5 TB and personal
# scratch is capped at 1 TB. For real runs, override to the Follows-group
# PI-shared pool (ask orcd-help-engaging@mit.edu for the path):
#     export DARWIN_DATA_ROOT=/orcd/pool/<num>/follows_shared/ecco_darwin_v5
export DARWIN_DATA_ROOT="${DARWIN_DATA_ROOT:-$HOME/orcd/scratch/ecco_darwin_v5}"

if [[ ! -d "$DARWIN_DATA_ROOT/output/monthly" ]]; then
    echo "ERROR: $DARWIN_DATA_ROOT/output/monthly missing — transfer the LLC270 tree first" >&2
    echo "       Globus collection: 'MIT ORCD Engaging Collection'" >&2
    echo "       Endpoint ID:       ec54b570-cac5-47f7-b2a1-100c2078686f" >&2
    exit 3
fi

# Install uv via miniforge's pip (avoids curl|sh supply-chain risk).
# logs/ must exist before sbatch — orcd_quickstart.sh creates it.
if ! command -v uv &> /dev/null; then
    python -m pip install --upgrade uv
fi

mkdir -p logs

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
