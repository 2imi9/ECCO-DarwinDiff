#!/bin/bash
# DarwinDiff — ORCD Engaging one-time setup.
#
# Run this ONCE in your home directory after cloning the repo. It loads
# the ORCD-recommended Python (miniforge), installs uv, syncs all deps,
# and runs the test suite to confirm the environment is healthy.
#
# After this script succeeds, you can submit jobs:
#   sbatch scripts/slurm/run_tests.sbatch                # CPU sanity
#   sbatch scripts/slurm/run_notebook.sbatch <path.ipynb> # GPU notebook
#   sbatch scripts/slurm/run_array.sbatch                # multi-seed ensemble
#
# Tested on: ORCD Engaging login node + mit_normal_gpu compute node (L40S).

set -euo pipefail

if [[ ! -f pyproject.toml ]]; then
    echo "ERROR: run this from the ECCO-DarwinDiff repo root" >&2
    exit 1
fi

echo "[1/4] Loading ORCD miniforge module (ships Python 3.12 + CUDA)..."
module purge
module load miniforge/24.3.0-0
python --version

echo "[2/4] Installing uv (one-time, into miniforge env)..."
# Use pip from the loaded miniforge module rather than the upstream curl|sh
# installer. Avoids the supply-chain risk of piping an internet script into
# a shell, and keeps uv inside the miniforge environment that python --version
# above is already pointing at.
if ! command -v uv &> /dev/null; then
    python -m pip install --upgrade uv
fi
uv --version

echo "[3/4] Syncing DarwinDiff dependencies (PyTorch CU128 wheels)..."
uv sync --all-extras

echo "[4/4] Running test suite (should be ~132 passed, 3 skipped)..."
uv run pytest -ra

# Create the logs/ directory used by scripts/slurm/*.sbatch — the SBATCH
# --output directives are parsed at submission time and need this to exist.
mkdir -p logs

echo ""
echo "OK — environment is ready."
echo "Next: edit scripts/slurm/*.sbatch if needed, then sbatch them."
echo "See docs/cluster_setup.md for the 'Jonathan quickstart' section."
