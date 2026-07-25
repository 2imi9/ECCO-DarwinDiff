#!/bin/bash
#SBATCH --job-name=dd-g11-fieldcons
#SBATCH --partition=short
#SBATCH --time=02:00:00
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --output=/projects/schultz/qi.zim/runs/%x_%j.out
#
# G11 / issue #7 -- FIELD-version mass/carbon-budget check with REAL v05 advection
# (scripts/ude_field_conservation_real_advection.py). Forward rollout only, no
# gradient -- CPU-only per the CLAUDE.md identifiability/FIM convention (do NOT
# request a GPU for this job). Reuses the native LLC270 tree + the AOI target
# cache already staged under DARWIN_DATA_ROOT -- no new data.
#
# Cost note: this AOI grid is tiny (eqpac ~ 20x50x6 cells). A local run of the
# full default matrix (7 horizons x 3 kh x 2 methods = 42 configs, including the
# decadal/20y rungs) finished in well under 2 min wall-clock on a laptop CPU, so
# this job is expected to finish in well under the 2h wall-time cap. Bump --time
# if you widen --years or add AOIs/kh values.
#
# LOCAL PRE-CHECK (2026-07-21): running this exact script locally already found
# that horizontal advection at real eqpac barotropic current strength blows up
# (non-finite) between 0.1 and 0.25 simulated years at kh<=1e6 -- INCLUDING
# kh=50, the "physical" default e2_real_calcite_eqpac.py / iron_scav_rat_profile.py
# currently use. kh=1e9 (in the framework's native m^2/day units) empirically
# stabilizes the rollout out to 10 simulated years (rk4 AND euler, drift ~1e-14).
# The script's default --kh-list (0.0, 50.0, 1e9) reproduces this on cluster.
set -euo pipefail
REPO=/projects/schultz/qi.zim/ecco-darwindiff
cd "$REPO"
export PATH="$HOME/.local/bin:$PATH"
export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces
export CUDA_VISIBLE_DEVICES=""

OUT="${OUT:-$REPO/docs/findings/g11_field_conservation}"
AOI="${AOI:-eqpac}"
mkdir -p "$OUT"

echo "=== $(date -u +%F_%H:%M:%S) | node $(hostname) | AOI=$AOI ==="
uv run python -u scripts/ude_field_conservation_real_advection.py \
  --out-dir "$OUT" --aoi "$AOI" --methods rk4 euler
echo "=== done $(date -u +%F_%H:%M:%S) | wrote $OUT/summary.json ==="
