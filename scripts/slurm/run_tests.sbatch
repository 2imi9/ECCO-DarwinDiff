#!/bin/bash
#SBATCH --job-name=darwindiff-tests
# ORCD Engaging: --account is NOT required (open to all MIT users).
# If your PI requires a specific allocation, add: #SBATCH --account=<pi>
#SBATCH --partition=mit_normal           # CPU partition — confirm name with orcd-help-engaging if rejected
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# DarwinDiff test suite — CPU only (loaders, networks, carroll6 + carbonate
# box model, diagnostics, budget). Should pass ~119 tests in ~30 s once env
# is built.
#
# Usage on ORCD Engaging:
#   ssh <kerb>@orcd-login.mit.edu
#   git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
#   bash scripts/orcd_quickstart.sh    # one-time: install uv + sync deps
#   sbatch scripts/slurm/run_tests.sbatch
#
# First run on a fresh node downloads ~1 GB of wheels via uv sync.
# Subsequent runs are cache hits.

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

# ORCD Engaging: miniforge ships Python + CUDA so one module load covers it.
module purge
module load miniforge/24.3.0-0

# Data root — tests don't load LLC270, setting for consistency.
# Override via env if running on a non-ORCD cluster.
export DARWIN_DATA_ROOT="${DARWIN_DATA_ROOT:-$HOME/orcd/scratch/ecco_darwin_v5}"

# Install uv if not already present (one-time per home dir).
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

mkdir -p logs

uv sync --all-extras
uv run pytest -ra
