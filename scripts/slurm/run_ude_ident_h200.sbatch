#!/bin/bash
#SBATCH --job-name=ude-ident
#SBATCH --partition=gpu
#SBATCH --gres=gpu:h200:1
#SBATCH --time=06:00:00
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --output=/projects/schultz/qi.zim/runs/ude_ident_%j.out

# 2x2 closure-identifiability ablation (structure x excitation). QUICK=1 for a
# smoke; OUT overrides the out-dir.
set -euo pipefail
cd /projects/schultz/qi.zim/ecco-darwindiff

OUT="${OUT:-/projects/schultz/qi.zim/runs/ude_ident}"
QUICK_FLAG=""
[ "${QUICK:-0}" = "1" ] && QUICK_FLAG="--quick"

nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || true
source .venv/bin/activate
python scripts/ude_closure_identifiability_h200.py --out-dir "$OUT" $QUICK_FLAG
