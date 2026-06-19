#!/bin/bash
#SBATCH --job-name=darwindiff-gpu
#SBATCH --partition=gpu                  # Explorer GPU batch partition (gpu-interactive for interactive srun)
#SBATCH --gres=gpu:h200:1                # H200 144GB (RC-owned: 4 nodes x8). A100-80GB fallback: gpu:a100:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G                        # host RAM; the 144GB H200 VRAM is separate
#SBATCH --time=08:00:00                  # CONFIRM the gpu-partition wall-time cap on first login
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err
#
# CONFIRM-ON-FIRST-LOGIN: the NU docs spell out only the v100-sxm2 / v100-pcie
# gres tokens verbatim. Verify the H200/A100 token and the partition wall-time
# cap with:  sinfo -o "%P %l %G"   (then fix the two lines above if needed).
#
# The `gpu` partition caps at 1 GPU/request — fine for a single native-resolution
# fit (1x H200 = 144GB >= the ~63 GB LLC270 time-mean peak measured in
# docs/findings/memory_scaling.md). The later multi-GPU seasonal sweep needs a
# different partition — ask RC (rchelp@northeastern.edu).
#
# Run one DarwinDiff entry point on an Explorer GPU node (default: the multi-AOI
# trainer). Pass env-var levers through your environment, e.g.:
#   AOIS=eqpac,natlsubpolar,southernoceanpac NB23_SEEDS="0-9" \
#     sbatch scripts/slurm/run_explorer_gpu.sbatch scripts/run_v3.0_joint_multi_aoi.py
#
# Explorer = Northeastern RC general HPC. NOT MIT ORCD (run_notebook.sbatch);
# NOT NU AICR/B200. See docs/cluster_setup.md.

set -euo pipefail

SCRIPT="${1:-scripts/run_v3.0_joint_multi_aoi.py}"
cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if [[ ! -f "$SCRIPT" ]]; then
    echo "ERROR: entry point not found at $SCRIPT" >&2
    exit 2
fi

# Base Python from the Explorer module; uv manages the project env.
module load anaconda3/2024.06
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.uv-cache}"

# Group storage (performant). Scratch (/scratch/$USER) is purged monthly; /home
# has a fixed quota. Keep the ~1.5 TB LLC270 tree and run outputs on /projects.
export DARWIN_DATA_ROOT="${DARWIN_DATA_ROOT:-/projects/schultz/ecco_darwin_v5}"
export OUTPUT_DIR="${OUTPUT_DIR:-/projects/schultz/darwindiff_runs}"

if ! command -v uv &> /dev/null; then
    python -m pip install --user --upgrade uv
fi

mkdir -p logs "$OUTPUT_DIR"
uv sync --all-extras

# Sanity: GPU visible to torch?
uv run python -c "import torch; assert torch.cuda.is_available(), 'no CUDA'; print('GPU:', torch.cuda.get_device_name(0))"

uv run python "$SCRIPT"
echo "Done: $SCRIPT"
