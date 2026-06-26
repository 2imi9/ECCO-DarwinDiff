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
# VERIFIED 2026-06-23 against rc-docs gpus/quickstart-h200.html: the `gpu:h200:1`
# token and the `gpu` (batch) / `gpu-interactive` (srun) partitions are documented
# verbatim. STILL confirm on first login: the A100 fallback token (gpu:a100:1) and
# the partition wall-time cap, with:  sinfo -o "%P %l %G"
#
# The `gpu` partition caps at 1 GPU/request — fine for a single native-resolution
# fit (1x H200 = 144GB >= the ~63 GB LLC270 time-mean peak measured in
# docs/findings/memory_scaling.md). The later multi-GPU seasonal sweep needs a
# different partition — ask RC (rchelp@northeastern.edu).
#
# Run one DarwinDiff entry point on an Explorer GPU node (default: the multi-AOI
# trainer). Pass env-var levers through your environment, and/or CLI flags as
# trailing args (forwarded verbatim to the script), e.g.:
#   AOIS=eqpac,natlsubpolar,southernoceanpac NB23_SEEDS="0-9" \
#     sbatch scripts/slurm/run_explorer_gpu.sbatch scripts/run_v3.0_joint_multi_aoi.py
#   # issue #119 — compiled memory constant + scaling:
#   sbatch scripts/slurm/run_explorer_gpu.sbatch scripts/measure_memory_scaling.py \
#     --compile --md docs/findings/memory_scaling_compiled.md
#   # native-resolution fit under compile (wall-clock for #119):
#   sbatch scripts/slurm/run_explorer_gpu.sbatch scripts/run_seasonal_recovery.py \
#     --mode time-mean --compile
#
# Explorer = Northeastern RC general HPC. NOT MIT ORCD (run_notebook.sbatch);
# NOT NU AICR/B200. See docs/cluster_setup.md.

set -euo pipefail

SCRIPT="${1:-scripts/run_v3.0_joint_multi_aoi.py}"
shift 2>/dev/null || true   # remaining args (e.g. --compile) pass through to the script
cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

if [[ ! -f "$SCRIPT" ]]; then
    echo "ERROR: entry point not found at $SCRIPT" >&2
    exit 2
fi

# Base Python from the Explorer module; uv manages the project env.
module load anaconda3/2024.06
# uv installs to ~/.local/bin (pip install --user); that dir is NOT on the batch
# PATH by default, so `uv` was "command not found" after a fresh bootstrap. Prepend
# it (matches run_identifiability.sbatch) so `command -v uv` and `uv run` resolve.
export PATH="$HOME/.local/bin:$PATH"
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

uv run python "$SCRIPT" "$@"
echo "Done: $SCRIPT"
