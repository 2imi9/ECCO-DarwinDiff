#!/bin/bash
#SBATCH --job-name=darwindiff-tests
#SBATCH --account=FIXME_ACCOUNT          # FIXME: ORCD account name
#SBATCH --partition=FIXME_PARTITION      # FIXME: e.g. sched_mit_orcd_cpu
#SBATCH --time=00:30:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --output=logs/%x_%j.out
#SBATCH --error=logs/%x_%j.err

# DarwinDiff test suite — CPU only (loaders, networks, carroll6 box model,
# diagnostics, budget). Should pass 104 tests in ~30s once env is built.
#
# Usage:
#   sbatch scripts/slurm/run_tests.sbatch
#
# First run on a fresh node downloads ~1 GB of wheels via uv sync.
# Subsequent runs are cache hits.

set -euo pipefail

cd "${SLURM_SUBMIT_DIR:-$(pwd)}"

# Cluster modules — adjust to whatever your cluster ships
module load python/3.11    # FIXME: confirm name
module load gcc/11         # FIXME: needed for some native deps

# Data root (tests don't actually load data; setting for consistency)
export DARWIN_DATA_ROOT="/scratch/$USER/ecco_darwin_v5"

# Install uv if not already present (one-time per home dir)
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

# Sync deps + run tests
uv sync --all-extras
uv run pytest -ra
