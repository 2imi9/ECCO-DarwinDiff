#!/bin/bash
#SBATCH --job-name=dd-iron-wall
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:15:00
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# Iron information-wall demonstration on H200 (scripts/iron_scav_rat_profile.py):
# the (alpfe, scav_rat) source/sink degeneracy of dissolved-iron CONCENTRATION.
# Launch-bound + small, so H200 gives no speedup over local -- this runs it on the
# automation cluster to keep it OFF the local GPU. Reads a pre-built input bundle
# (iron_bundle.pt, small AOI tensors only) so the ~TB native tree stays on the box.
#
# Build the bundle locally on CPU first (no GPU touch):
#   CUDA_VISIBLE_DEVICES= python scripts/iron_scav_rat_profile.py --build-bundle iron_bundle.pt
# then scp iron_bundle.pt + src/ to the deploy dir and: sbatch scripts/slurm/run_iron_wall.sbatch
set -euo pipefail
REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PYTHONPATH=src
mkdir -p /projects/schultz/qi.zim/runs

echo "=== $(date -u +%F_%H:%M:%S) node $(hostname) ==="
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo "--- TWIN (structural degeneracy / the wall) ---"
.venv/bin/python scripts/iron_scav_rat_profile.py --bundle iron_bundle.pt --mode twin
echo "--- GEOTRACES (diagnostic: iron-starved with real dust) ---"
.venv/bin/python scripts/iron_scav_rat_profile.py --bundle iron_bundle.pt --mode geotraces
echo "=== done $(date -u +%F_%H:%M:%S) ==="
