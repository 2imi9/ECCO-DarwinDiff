# Cluster setup — DarwinDiff on Northeastern Explorer / AICR

Operational guide for running DarwinDiff on **Northeastern Research Computing** (Explorer + AICR). Companion to [README](../README.md) (project overview) and [STATUS](../STATUS.md) (live results).

## Target clusters

DarwinDiff runs on **Northeastern Research Computing** (Lucas's home institution, Cristina-sponsored). Two clusters are in play:

| Cluster | Hardware | Status / when to use |
|---|---|---|
| **Explorer** | H200 144 GB (×32 RC-owned), A100 80 GB (×8), V100, L40S, t4 | **Active path.** General HPC, free to NU faculty/students, Cristina-sponsored. All current cluster runs (the n=10 ensembles, the per-cell ablation, the per-AOI identifiability map) run here. |
| **AICR** | 248× B200 + 152× RTX Pro | Future path. NU's dedicated AI cluster; access via a PI **project proposal** (in prep). Target for the global-native / seasonal sweep. |

> **Note.** "AICR" is **Northeastern's** AI Compute Resource, accessed via a PI proposal — unrelated to any MIT path. **The project does not use MIT ORCD / Engaging** (an earlier exploratory option, since dropped in favour of Explorer).

## Northeastern Explorer

Explorer is Northeastern RC's general HPC cluster (<https://rc.northeastern.edu>), free to all NU faculty and students. Access for a sponsored user is a ServiceNow "Research Computing Access Request" with a PI sponsor.

### Access

1. Submit the [Research Computing Access Request](https://rc.northeastern.edu/getting-access/) (ServiceNow), listing your PI as **University Sponsor** and their storage space (e.g. `schultz`).
2. The sponsor approves via the emailed link; the account provisions within ~24 h.
3. Current NU students already have credentials — no separate "external user" step.

### Hardware (RC-owned, generally schedulable)

| GPU | VRAM | Count | Notes |
|---|---|---|---|
| H200 | 144 GB | 4 nodes × 8 = 32 | Ideal tier; holds a native-resolution fit (LLC270 time-mean ~63 GB, measured in [`memory_scaling.md`](archive/findings/memory_scaling.md)) on one card |
| A100 | 80 GB | 2 nodes × 4 = 8 | Workable fallback |
| t4 | 16 GB | many | Small but schedulable — fine for the box-scale recovery / Fisher / ablation jobs (used for the per-cell ablation + identifiability map) |
| V100 | 16–32 GB | many | **Avoid: the cluster torch (cu128) has no kernels for V100 (CC 7.0).** Use t4 (7.5) / a100 / h200 instead |

H100 / L40S exist but are PI-owned (need that PI's permission). Cluster totals: 45k+ CPU cores, 525+ GPUs, 6 PB storage, InfiniBand (200/100 Gbps).

### Partitions & GPU request

- Batch: `--partition=gpu`; interactive: `--partition=gpu-interactive`; short jobs: `--partition=gpu-short` (2 h cap, often better backfill).
- Type-pinned request: `--gres=gpu:h200:1` — documented **verbatim** in the [H200 quick-start guide](https://rc-docs.northeastern.edu/en/explorer-main/gpus/quickstart-h200.html). Fallback tokens: `--gres=gpu:a100:1`, `--gres=gpu:t4:1`.
- The `gpu` partition caps at **1 GPU per request** — fine for one native fit (1× H200 = 144 GB ≥ the ~63 GB LLC270 time-mean peak); the later multi-GPU seasonal sweep needs a different partition (ask `rchelp@northeastern.edu`).
- **Fairshare note:** a sponsored account can sit `PENDING(Priority)` behind higher-priority work for hours; short (`--time`) jobs on `gpu-short` backfill best.

### Storage

| Path | Use | Policy |
|---|---|---|
| `/projects/<group>` (e.g. `/projects/schultz`) | Performant group storage; put the repo + data here | PI-requested; Schultz group ~35 TB total (<10 TB free, June 2026) |
| `/scratch/$USER` | Temp / intermediate | **Purged monthly**, not backed up |
| `/home/$USER` | Configs, small files | Fixed quota, cannot increase — do **not** build envs or caches here |

The LLC270 monthly tracer tree (~1.5 TB, the only large input) fits comfortably under the Schultz allocation; per-run JSON outputs are small.

### Setup & run

```bash
# Clone UNDER group storage to avoid the small /home quota:
cd /projects/schultz && git clone https://github.com/2imi9/ECCO-DarwinDiff.git
cd ECCO-DarwinDiff
bash scripts/explorer_quickstart.sh                       # module load anaconda3 + uv sync + pytest

export DARWIN_DATA_ROOT=/projects/schultz/qi.zim/ecco_darwin_v5    # LLC270 tree
export GEOTRACES_DATA_ROOT=/projects/schultz/qi.zim/geotraces
sbatch scripts/slurm/run_explorer_gpu.sbatch              # GPU training job (defaults to the multi-AOI trainer)
```

> **Build gotchas (learned the hard way).** (1) **Python pin** — the repo commits `.python-version` = `3.12`; do **not** remove it. With only `requires-python = ">=3.11"`, a fresh `uv sync` selects 3.14, where `aiohttp` (via `argopy`) has no cp314 wheel and the sdist build fails. (2) **Build inside a Slurm job, not the login node** — the Arbiter watchdog SIGKILLs a heavy `uv sync` on the login node. (3) **`eol=lf`** + `build-essential` available for `torch.compile`.

### Data transfer (~1.5 TB tree → Explorer)

- **Globus** is the practical path for the full tree (NU has a Globus endpoint; confirm the collection name with RC). Destination: `/projects/schultz/qi.zim/ecco_darwin_v5`.
- `scp` / `rsync` works for subsets; impractical for the full tree.

## SLURM scripts

The repo's cluster scripts live in [`scripts/slurm/`](../scripts/slurm/). The active Explorer entry points:

- [`scripts/explorer_quickstart.sh`](../scripts/explorer_quickstart.sh) — one-time setup (module load anaconda3 + `uv sync` + pytest).
- [`scripts/slurm/run_explorer_gpu.sbatch`](../scripts/slurm/run_explorer_gpu.sbatch) — the H200/GPU training job. Override the GPU type and wall-time at submit (`--gres=gpu:a100:1` / `--gres=gpu:t4:1`, `--partition=gpu-short --time=...`) without editing the script.

All scripts read `${DARWIN_DATA_ROOT}` / `${GEOTRACES_DATA_ROOT}` from the environment, auto-install `uv`, run `uv sync`, and write logs to `logs/<jobname>_<jobid>.{out,err}` (gitignored).

## Compute requirements

| Resource | Minimum | Recommended |
|---|---|---|
| GPU | NVIDIA t4 16 GB (CUDA 12.x, CC ≥ 7.5) | A100/H100/H200 80–144 GB for native-resolution multi-tracer + time-resolved Track 2 |
| CPU | Any modern node | — |
| RAM | 32 GB per job | — |
| Scratch | 2 TB | LLC270 monthly tracer tree is ~1.5 TB |
| Persistent / home | <50 GB | — |

## Local baseline (for comparison)

DarwinDiff also runs on a single workstation (NVIDIA RTX 5090 32 GB, Windows 11) against the LLC270 tree on external storage. The single-laptop workflow drove all v0.x–v3.1 results; cluster scale-up is for ensembles, sweeps, and native resolution.

| Workload | Wall-clock (RTX 5090) | Peak GPU mem |
|---|---|---|
| Test suite (`pytest`) | ~30 s | n/a (CPU) |
| DINN baseline single-AOI 1500-epoch fit | ~5 min | ~6 GB |
| DINNDeep multi-tracer joint loss | ~20 min | ~10 GB |
| 7-tracer carbonate joint loss | ~45–60 min | ~15 GB |
| 10-seed batched 3-AOI joint training (v3.1) | ~7 min (torch.compile batched) | ~12 GB |

## What scale-up unlocks

Workloads that are infeasible or marginal locally and become routine on cluster:

| Workload | Local feasibility | Why cluster matters |
|---|---|---|
| Multi-seed ensembles (n=20–50 per config) | Sequential, ~25–50 min | Parallel array job, ~5–10 min wall-clock |
| Cross-basin DINNDeep redo at multiple AOIs | Sequential, ~30 min per AOI | Parallel jobs, ~10 min wall-clock |
| Multi-tracer joint loss at LLC270 native resolution | Tight on 32 GB at full AOI | Comfortable on 80 GB A100 / H100 / H200 |
| Time-resolved fitting (~300 monthly snapshots × per-fit cost) | Infeasible (~25 h sequential) | Multi-GPU data-parallel; opens Track 2 emulator |
| Full-ocean parameter recovery sweep | Infeasible | Embarrassingly parallel across AOIs |
| Native-resolution parameter maps + forward Darwin validation (vs box-model proxy) | Tested: native res selects *which* iron-pair param recovers but does **not** lift the recovery count, and did **not** help `R_PICPOC` — identifiability comes from real absolute anchors, not resolution (the surrogate gap is dimensional, not resolution-limited). Value is per-cell parameter maps + forward validation. | Headroom for the maps + validation |

## AICR — application path

NU's **AICR** (B200 + RTX Pro) is the future production path, accessed via a PI **project proposal** (Cristina/Schultz-sponsored, in prep). It is NU's own AI cluster, not gated on any MIT path. Once granted, port the Explorer SLURM (`--partition=gpu --gres=gpu:h200:1`) to the AICR partition — typically a one-line `#SBATCH --partition` change plus a module-path adjustment.
