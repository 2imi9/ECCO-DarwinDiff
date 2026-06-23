#!/bin/bash
# DarwinDiff — Northeastern Explorer one-time setup.
#
# Run this ONCE from the repo root after cloning. Clone the repo UNDER group
# storage (/projects/<group>, e.g. /projects/schultz) — NOT /home, whose quota
# is small and fixed — so the .venv and wheel cache have room.
#
# Loads the Explorer anaconda3 module to provide a base Python, installs uv,
# syncs all deps (PyTorch cu128 wheels), and runs the test suite to confirm the
# environment is healthy.
#
# Explorer is Northeastern RC's general HPC cluster (rc.northeastern.edu) — it
# is NOT MIT ORCD (see scripts/orcd_quickstart.sh) and NOT NU's AICR (B200).
# See docs/cluster_setup.md "Northeastern Explorer".
#
# After this succeeds:
#   sbatch scripts/slurm/run_tests.sbatch                       # CPU sanity
#   sbatch scripts/slurm/run_explorer_gpu.sbatch <script.py>    # GPU job (H200)

set -euo pipefail

if [[ ! -f pyproject.toml ]]; then
    echo "ERROR: run this from the ECCO-DarwinDiff repo root" >&2
    exit 1
fi

# Keep the wheel cache off /home (fixed quota); colocate it with the repo, which
# should itself live under /projects.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.uv-cache}"

case "$(pwd -P)" in
    /home/*) echo "WARNING: repo is under /home (small fixed quota). Prefer /projects/<group>." >&2 ;;
esac

echo "[1/4] Loading Explorer anaconda3 module (base Python)..."
# Module name verified against rc-docs.northeastern.edu (Conda page); if this
# version is retired, pick the current one from: module avail anaconda3
module load anaconda3/2024.06
python --version

echo "[2/4] Installing uv (--user; the shared module env is read-only)..."
if ! command -v uv &> /dev/null; then
    python -m pip install --user --upgrade uv
fi
uv --version

echo "[3/4] Syncing DarwinDiff dependencies (PyTorch cu128 wheels)..."
# The committed .python-version pins Python 3.12 (uv honors it for sync + run).
# Required: a bare ">=3.11" lets uv pick 3.14, where aiohttp (via argopy) has no
# cp314 wheel and its sdist build fails. 3.12 resolves to all-binary wheels.
uv sync --all-extras

echo "[4/4] Running test suite..."
uv run pytest -ra

# logs/ is referenced by the SBATCH --output directives (parsed at submit time).
mkdir -p logs

echo ""
echo "OK — environment ready on Explorer."
echo "Set your group-storage data root before submitting GPU jobs, e.g.:"
echo "  export DARWIN_DATA_ROOT=/projects/schultz/ecco_darwin_v5"
echo "Then: sbatch scripts/slurm/run_explorer_gpu.sbatch"
