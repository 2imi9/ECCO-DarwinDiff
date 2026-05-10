# SLURM job templates for DarwinDiff on a Linux GPU cluster

Three templates covering the workloads documented in [`docs/cluster_setup.md`](../../docs/cluster_setup.md). Each script is intended to be customised for a specific cluster (account name, partition, module versions) and submitted with `sbatch`.

> **Status:** ORCD Engaging values pre-filled (partition, modules, storage paths) against the public docs at <https://orcd-docs.mit.edu>. The four unverified items (CPU partition name, wall-time caps, account-flag requirement, PI-shared-pool path) are flagged in [`docs/cluster_setup.md`](../../docs/cluster_setup.md#pre-flight-questions-for-orcd-help-engagingmitedu) for Jonathan to confirm with orcd-help. For a non-ORCD cluster, the scripts work after overriding the partition + module-load section.

## Files

| Script | Purpose | Resource ask |
|---|---|---|
| [`run_tests.sbatch`](run_tests.sbatch) | Run the 104-test pytest suite as a sanity check on the cluster. CPU only. | 1 node, 4 CPU, 8 GB RAM, 30 min |
| [`run_notebook.sbatch`](run_notebook.sbatch) | Execute one notebook via `jupyter nbconvert --execute`. Good for nb15-class single-fit jobs. | 1 GPU, 8 CPU, 32 GB RAM, 4 h |
| [`run_array.sbatch`](run_array.sbatch) | Multi-seed ensemble (nb17-style). Each array task trains one seed and writes its checkpoint to `notebooks/nb17_results/`. **Currently serialised (`--array=0-9%1`)** — the script writes back to a shared notebook file via `nbconvert --inplace`, so concurrent tasks would race. Will become genuinely parallel once the planned `scripts/train_seed.py` lands. | array of N × (1 GPU, 4 CPU, 16 GB RAM, 30 min), serialised |

## Conventions

- **Working directory:** scripts assume `$SLURM_SUBMIT_DIR` is the project root (`ECCO-DarwinDiff/`).
- **Logs:** stdout/stderr land in `logs/<jobname>_<jobid>.{out,err}`. The `logs/` dir is gitignored.
- **Data root:** every script exports `DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5` before running. All notebooks honour this env var (path-refactor landed alongside this PR).
- **Environment:** `uv sync --all-extras` runs at the start of each job. First run on a new node downloads ~1 GB of wheels; subsequent runs are cache hits.

## Quick start

```bash
# ORCD Engaging: one-time environment bootstrap (loads miniforge, installs
# uv, syncs deps, runs the test suite to verify the env works).
cd ECCO-DarwinDiff
bash scripts/orcd_quickstart.sh

# Day-to-day:
# 1. Sanity-check on a fresh node
sbatch scripts/slurm/run_tests.sbatch

# 2. Execute one notebook on GPU
sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb

# 3. Multi-seed ensemble (override SEED count via --array if needed)
sbatch scripts/slurm/run_array.sbatch

# Override DARWIN_DATA_ROOT if the LLC270 tree lives somewhere other
# than $HOME/orcd/scratch/ecco_darwin_v5 (likely a PI-shared pool):
export DARWIN_DATA_ROOT=/orcd/pool/<num>/follows_shared/ecco_darwin_v5
```

## What's not yet here

- A standalone `scripts/train_seed.py` that the array job could call directly (avoiding repeated notebook re-execution per seed). The current array job re-executes the full notebook per seed AND writes back to a shared notebook file via `nbconvert --inplace`. That makes concurrent tasks UNSAFE — the array directive is therefore pinned to `%1` (max 1 concurrent task) as a stop-gap. Result: the array job is serial, not parallel. **Restoring parallelism requires extracting the per-seed training into a CLI script that writes only its `seedA_NN.npz` checkpoint and never touches the notebook file.** Until then, expect total wall-clock = N_seeds × per-seed time.
- Multi-GPU / distributed templates. Not needed for current workloads; will land when time-resolved fitting (Track 2) starts.
- A submission wrapper that pre-computes `--time` from the notebook size. Nice-to-have.
