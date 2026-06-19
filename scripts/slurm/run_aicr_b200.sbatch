#!/bin/bash
#SBATCH --job-name=darwindiff-aicr
#SBATCH --partition=b200-batch           # NU AICR B200 (192 GB), 24 h walltime, multi-GPU.
                                          # Use b200-devel (4 h) for interactive/OOD work.
#SBATCH --gres=gpu:1                      # ONE B200. See "multi-GPU" note below before raising.
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G                         # GPU nodes have 2.3 TB; bump for native-resolution.
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# Run a DarwinDiff job on Northeastern's AICR (B200) cluster.
# Login: https://ood.aicr.ai  (Northeastern creds; cluster username is e.g. qi_zim_neu).
# Docs: https://rc-docs.northeastern.edu/en/latest/ , AICR intro:
#   https://github.com/northeastern-rc-training/AICR-Introduction-2026
#
# === AICR-specific gotchas (these differ from Explorer / MIT ORCD) ===
#
#  1. DEV ON EXPLORER FIRST. AICR policy is: develop + test on Explorer, then use
#     AICR for production runs only (shared MGHPCC resource).
#
#  2. IDLE-GPU REAPER. A monitor cancels jobs whose GPU sits idle. The seasonal
#     integrator is currently Python-loop-bound (GPU ~0% util), so it WILL be
#     killed here until it is batched + torch.compile'd. Do not run the seasonal
#     runner on AICR before that fix lands; the time-mean / batched paths are fine.
#
#  3. MULTI-GPU IS NOT AUTOMATIC. DarwinDiff is per-cell (embarrassingly parallel),
#     so prefer MANY single-GPU array jobs (--gres=gpu:1 + --array) over one DDP
#     job. A single native-resolution fit fits in one B200's 192 GB via cell
#     mini-batching. Only set --gres=gpu:N with real torchrun/DDP once the code
#     actually uses NCCL allreduce across GPUs.
#
#  4. TORCH MUST BE BLACKWELL-CAPABLE. B200 is sm_100 — needs a CUDA 12.8+ build
#     (PyTorch >= 2.7, the CU128 wheels). Verify with the sanity check below; if it
#     prints a "no kernel image" / sm_100 error, update the torch pin.
#
#  5. STORAGE. /scratch/$USER (10 TB, 30-day purge, NO recovery) or
#     /work/neu/$PROJECT (longer-term, but ephemeral). Keep the master copy
#     off-cluster (the Toshiba). Move the ~1.5 TB tree in via Globus:
#     https://rc-docs.northeastern.edu/en/latest/datamanagement/globus.html
#
# Usage:
#   sbatch scripts/slurm/run_aicr_b200.sbatch                       # default workload below
#   sbatch scripts/slurm/run_aicr_b200.sbatch python scripts/run_seasonal_recovery.py --aoi natlsubpolar
#   sbatch --array=0-9 scripts/slurm/run_aicr_b200.sbatch python scripts/run_seasonal_recovery.py --seed '$SLURM_ARRAY_TASK_ID'

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

module purge
module load cuda/13.1
module load miniforge3/25.3.0-3

# Data root — must hold the LLC270 tree at $DARWIN_DATA_ROOT/output/monthly
# (or the bin_average product for 1-deg work). Override to your project/scratch:
export DARWIN_DATA_ROOT="${DARWIN_DATA_ROOT:-/work/neu/$USER/ecco_darwin_v5}"

# Install uv via miniforge's pip (matches the Explorer scripts; avoids curl|sh).
if ! command -v uv &> /dev/null; then
    python -m pip install --upgrade uv
fi
mkdir -p logs
uv sync --all-extras

# Sanity check: GPU visible AND a Blackwell kernel actually runs (gotcha #4).
uv run python -c "import torch; assert torch.cuda.is_available(), 'no CUDA'; \
print('GPU:', torch.cuda.get_device_name(0)); \
print('matmul ok:', bool((torch.randn(8,8,device='cuda') @ torch.randn(8,8,device='cuda')).sum().isfinite()))"

# Default workload: a full-length single-AOI fit. Pass any command to override.
if [[ $# -gt 0 ]]; then
    uv run "$@"
else
    uv run python scripts/run_seasonal_recovery.py --aoi eqpac --mode time-mean --epochs 1500
fi

echo "Done."
