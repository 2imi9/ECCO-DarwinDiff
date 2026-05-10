# SLURM job templates for DarwinDiff on a Linux GPU cluster

Three templates covering the workloads documented in [`docs/cluster_setup.md`](../../docs/cluster_setup.md). Each script is intended to be customised for a specific cluster (account name, partition, module versions) and submitted with `sbatch`.

> **Status:** placeholder templates with `# FIXME` markers for cluster-specific values. They run end-to-end on any SLURM cluster once the FIXMEs are filled in. Tested patterns; not yet verified against MIT ORCD specifically.

## Files

| Script | Purpose | Resource ask |
|---|---|---|
| [`run_tests.sbatch`](run_tests.sbatch) | Run the 104-test pytest suite as a sanity check on the cluster. CPU only. | 1 node, 4 CPU, 8 GB RAM, 30 min |
| [`run_notebook.sbatch`](run_notebook.sbatch) | Execute one notebook via `jupyter nbconvert --execute`. Good for nb15-class single-fit jobs. | 1 GPU, 8 CPU, 32 GB RAM, 4 h |
| [`run_array.sbatch`](run_array.sbatch) | Multi-seed ensemble (nb17-style). Each array task trains one seed and writes its checkpoint to `notebooks/nb17_results/`. | array of N × (1 GPU, 8 CPU, 32 GB RAM, 30 min) |

## Conventions

- **Working directory:** scripts assume `$SLURM_SUBMIT_DIR` is the project root (`ECCO-DarwinDiff/`).
- **Logs:** stdout/stderr land in `logs/<jobname>_<jobid>.{out,err}`. The `logs/` dir is gitignored.
- **Data root:** every script exports `DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5` before running. All notebooks honour this env var (path-refactor landed alongside this PR).
- **Environment:** `uv sync --all-extras` runs at the start of each job. First run on a new node downloads ~1 GB of wheels; subsequent runs are cache hits.

## Quick start

```bash
# Adapt FIXMEs in each .sbatch (account, partition, module names) once.
cd ECCO-DarwinDiff
mkdir -p logs

# 1. Sanity-check the install
sbatch scripts/slurm/run_tests.sbatch

# 2. Execute one notebook
sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb

# 3. Multi-seed ensemble (override SEED count via --array if needed)
sbatch scripts/slurm/run_array.sbatch
```

## What's not yet here

- A standalone `scripts/train_seed.py` that the array job could call directly (avoiding repeated notebook re-execution per seed). The current array job re-executes the full notebook per seed, relying on the per-seed checkpoint cache to short-circuit completed seeds. That works but is wasteful — better to extract the training loop into a CLI script. Future work.
- Multi-GPU / distributed templates. Not needed for current workloads; will land when time-resolved fitting (Track 2) starts.
- A submission wrapper that pre-computes `--time` from the notebook size. Nice-to-have.
