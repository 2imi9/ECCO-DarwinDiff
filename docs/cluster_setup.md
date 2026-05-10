# Cluster setup — DarwinDiff on a Linux GPU cluster

*Operational complement to [README](../README.md) and [STATUS](../STATUS.md). Covers compute requirements, environment setup, dataset transfer, and job patterns for moving DarwinDiff from local single-GPU to MIT ORCD (or any Linux cluster with NVIDIA GPUs).*

**Last updated:** 2026-05-09. Some entries marked TBD pending first cluster runs.

## Purpose and audience

This doc exists for three readers:
- **The user** running DarwinDiff on cluster scratch — operational reference for env setup, data transfer, job patterns.
- **A reviewer / collaborator** (host project lead, cluster admin) evaluating the compute ask — what we have, what we need, what scale-up unlocks.
- **A future development session** scoping cluster work — concrete requirements drive decisions about path-refactor, SLURM templates, distributed training.

## Local baseline (current state)

DarwinDiff currently runs on a single workstation: **NVIDIA RTX 5090 (32 GB VRAM), Windows 11**, against the LLC270 monthly tracer tree on a 3.7 TB external USB drive (`D:\ecco_darwin_v5\`).

| Workload | Wall-clock | Peak GPU mem | Notes |
|---|---|---|---|
| 104-test suite (`pytest`) | ~30 s | n/a (CPU) | Loaders, networks, carroll6 box model, diagnostics |
| nb15 — DINNDeep Eq Pac FeT (1500 epochs) | ~5 min | TBD | 1071 cells, 4-channel input, 9.4K params |
| nb15 — DINN baseline Eq Pac FeT (1500 epochs) | TBD | TBD | Same AOI, single channel, ~450 params |
| nb16 — DINNDeep cross-validation (2 splits × 1500 epochs) | TBD | TBD | Re-trains nb15 model under random and block holdout |

Empty cells are real measurements I haven't recorded yet — first cluster runs are a good moment to fill these in for both local and cluster, side by side.

## What scale-up unlocks

These are the workloads that are *infeasible or marginal locally* and become *routine on cluster*. This is the substantive content of the ORCD ask.

| Workload | Local feasibility | Why cluster matters |
|---|---|---|
| **Multi-seed ensembles** (5–10× DINNDeep seeds per AOI, for ensemble-disagreement trust maps — *nb17*) | Sequential, ~25–50 min | Parallel array job, 5 min wall-clock |
| **Cross-basin DINNDeep redo** (nb11 / 13 / 14 at v1.4 architecture) | Sequential, ~30 min | Three jobs in parallel, 10 min wall-clock |
| **Multi-tracer joint loss** (NO₃ + Chl + DIC + FeT simultaneously) | Tight on 32 GB at full AOI | Comfortable on 80 GB A100 / H100 |
| **Time-resolved fitting** (~300 monthly snapshots × current per-fit cost) | Infeasible — ~25 h sequential | Multi-GPU data-parallel; opens Track 2 emulator territory |
| **Box-model carbonate extension** (DIC + ALK + carbonate chemistry + 5 PFTs vs current 5-tracer proxy) | Untested; will grow box-model state ~2-3× | Headroom matters once architecture grows alongside |
| **Sweep over AOIs** (full-ocean parameter recovery) | Infeasible | Embarrassingly parallel across AOIs |

The first two rows are immediately useful for the next-phase compute proposal (quantitative results in days, not weeks). The bottom four are the long-term Track 2 trajectory.

## Cluster requirements

### Compute
- **GPU**: NVIDIA, CUDA 12.x compatible. A100 (40 / 80 GB) preferred; V100 acceptable for everything except multi-tracer joint loss; H100 ideal for time-resolved Track 2.
- **Cores**: any modern CPU node sufficient for data loading + integration. Box-model integrator is the bottleneck and is GPU-resident.
- **Memory (RAM)**: 32 GB+ per job. LLC270 month tile loading is xarray + dask; large but not extreme.

### Storage
- **Scratch**: ≥2 TB recommended. The LLC270 monthly tracer tree is **TBD GB** total (currently downloading; estimate ~1–1.5 TB based on D: drive headroom).
- **Persistent / home**: <50 GB for codebase + checkpoints + figures.
- **Tmp**: ephemeral OK; integration runs don't need long-lived tmp.

### Software stack
- **Python**: 3.11+ (per `pyproject.toml`)
- **CUDA**: 12.x (PyTorch CU128 wheels — index pinned in `pyproject.toml`)
- **Compiler toolchain**: gcc 11+ for any native deps (xarray + netcdf4 should have wheels)
- **Modules to load** (template — adjust to actual cluster):
  ```bash
  module load python/3.11
  module load cuda/12.1     # or whatever's available
  module load gcc/11
  ```

## Environment setup

```bash
# clone the repo
git clone https://github.com/2imi9/ECCO-DarwinDiff.git
cd ECCO-DarwinDiff

# install uv (one-time per user)
curl -LsSf https://astral.sh/uv/install.sh | sh

# sync all deps including dev tools (matplotlib, jupyter, etc.)
uv sync --all-extras
```

Verify the install:
```bash
uv run pytest                                              # 104 tests should pass
uv run python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## Dataset transfer

The LLC270 monthly tracer tree is the only large dataset. Two paths:

### Option A — transfer from local D:
- **Globus** preferred (the user's institution likely has an endpoint; ORCD definitely does)
- **rsync over SSH** as fallback: `rsync -avh --progress /d/ecco_darwin_v5/ user@cluster:/scratch/$USER/ecco_darwin_v5/`
- Transfer time depends on link; conservatively ~12 h at 30 MB/s for 1.3 TB

### Option B — re-download on cluster
- The original wget setup is documented in `data/README.md`
- May be faster than D:→cluster transfer if the cluster has good external bandwidth
- Confirms the data is reproducible from source

After transfer:
```bash
export DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5
```

Notebooks currently have hardcoded `D:\ecco_darwin_v5\...` paths in 47 places across 9 notebooks. **Path-refactor pending** (top-cell config block honoring `$DARWIN_DATA_ROOT`); this is a half-day of mechanical work, blocked only by needing actual cluster access to test against.

## Job patterns

SLURM templates pending — will be added under `scripts/slurm/` once cluster access lands. Three patterns we'll need:

1. **Test sanity** — CPU node, 5 min, runs `pytest`
2. **Single notebook execute** — 1 GPU, 30 min, `jupyter nbconvert --execute --to notebook --inplace notebooks/NN_*.ipynb`
3. **Array job for ensembles** — 1 GPU per array task, runs N seeds of nb17 in parallel

## Open questions for the cluster phase

These are the answers we need before finalizing the ask:
- Which GPU types are available? (A100 40GB / 80GB / H100 / V100 mix?)
- Scratch quota and lifetime (are 2 TB and a 90-day window achievable)?
- Globus endpoint configured?
- Maximum simultaneous jobs per user (matters for embarrassingly-parallel array jobs)?
- Wall-clock limit per job (most workloads are well under 1 h, but Track 2 time-resolved fitting will need long jobs)?

## Open questions for ourselves
- **Local-vs-cluster baseline measurements**. The TBD cells in the wall-clock + memory table need filling in. First cluster job should mirror nb15 locally and on cluster, side by side.
- **Path-refactor scope**. Hardcoded paths in notebooks are mostly top-cell `DATA_ROOT = ...` style — should be 1-line edits per notebook. Confirm with one trial conversion before batching.
- **Distributed training necessity**. Multi-GPU is needed for time-resolved fitting (Track 2) and possibly for box-model carbonate extension at full AOI. Single-GPU is sufficient for everything in the current punch list.

## Cross-references
- [README](../README.md) — project overview, headline results
- [STATUS](../STATUS.md) — live state, finding-by-finding
- [docs/dinn_design.md](dinn_design.md) — DINN / DINNDeep architecture, training loop
- [data/README.md](../data/README.md) — dataset provenance and download mechanics
- [pyproject.toml](../pyproject.toml) — pinned Python deps, CUDA index
