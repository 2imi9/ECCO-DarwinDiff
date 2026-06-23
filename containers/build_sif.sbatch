#!/bin/bash
#SBATCH --job-name=dd-sif-build
#SBATCH --partition=short
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:30:00
#SBATCH --output=containers/build_%j.out
cd "${SLURM_SUBMIT_DIR:-/projects/schultz/qi.zim/ecco-darwindiff}"
LOCAL="${TMPDIR:-/tmp}/ddsif_${SLURM_JOB_ID}"
mkdir -p "$LOCAL/tmp" "$LOCAL/cache"
export APPTAINER_TMPDIR="$LOCAL/tmp"
export APPTAINER_CACHEDIR="$LOCAL/cache"
echo "node=$(hostname)  tmp=$LOCAL"
echo -n "internet: "; curl -sI --max-time 10 https://pypi.org 2>/dev/null | head -1 || echo "NONE"
apptainer build --fakeroot containers/darwindiff.sif containers/darwindiff.def
rc=$?
echo "BUILD_RC=$rc"
rm -rf "$LOCAL"
ls -lah containers/darwindiff.sif 2>/dev/null
exit $rc
