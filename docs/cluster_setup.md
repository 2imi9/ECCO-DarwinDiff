# Cluster setup — DarwinDiff on MIT ORCD Engaging

*Operational complement to [README](../README.md) and [STATUS](../STATUS.md). Covers compute requirements, environment setup, dataset transfer, and SLURM job patterns for running DarwinDiff on the MIT ORCD Engaging cluster (or any Linux cluster with NVIDIA GPUs).*

**Last updated:** 2026-05-10. ORCD Engaging values verified against the public docs at <https://orcd-docs.mit.edu>.

## Jonathan quickstart — 4 steps from clone to results

```bash
# 1. Log in (Duo MFA required)
ssh <kerb>@orcd-login.mit.edu

# 2. Clone the repo
git clone https://github.com/2imi9/ECCO-DarwinDiff.git
cd ECCO-DarwinDiff

# 3. One-time environment setup (loads miniforge, installs uv, syncs deps,
#    runs the 119-test suite to confirm everything works)
bash scripts/orcd_quickstart.sh

# 4. Submit jobs (after step 3 succeeds)
sbatch scripts/slurm/run_tests.sbatch                                 # CPU sanity (~30 s)
sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb   # GPU notebook (~5–15 min)
```

To run anything that needs the actual LLC270 monthly tracer tree, first set `DARWIN_DATA_ROOT` to where the data lives — see [storage decision](#storage-decision-where-15-tb-goes) below.

## Pre-flight questions for orcd-help-engaging@mit.edu

The agent that mined the public docs surfaced four things that aren't in writing and Jonathan should confirm before the first real run:

1. **CPU partition name.** Our `run_tests.sbatch` defaults to `--partition=mit_normal`, mirroring the `mit_normal_gpu` naming convention. If SLURM rejects it, ask for the right name.
2. **Wall-time / QOS caps** per partition. Not on the public pages. Our scripts set 30 min (tests), 4 h (single notebook), 30 min per array task — well within likely caps but worth confirming.
3. **Whether `--account=<pi>` is needed** for the Follows lab specifically. Public docs say `--account` is not required for general Engaging access, but PI allocations may differ.
4. **PI-shared-pool path** for the Follows group (e.g. `/orcd/pool/<num>/follows_shared/`). This is the only viable home for the ~1.5 TB LLC270 tree — see below.

## ORCD Engaging — what we verified

| Topic | Value |
|---|---|
| Login | `ssh <kerb>@orcd-login.mit.edu` (Duo MFA + Kerberos) or OnDemand at <https://orcd-ood.mit.edu> |
| First-time provisioning | Logging into OnDemand once auto-provisions the account (wait ~min, up to 1 h) |
| GPU partition (default) | `mit_normal_gpu` — L40S 44 GB (49 nodes × 4), H100 80 GB (1 node × 4), H200 140 GB (11 nodes × 8) |
| GPU partition (A100 access) | `mit_preemptable` — adds A100-SXM4-80 GB (6 nodes × 8) and A100-PCIe-80 GB. Requires `--requeue` |
| Module system | Lmod-style `module load/avail/purge`. **Recommended path:** `module load miniforge/24.3.0-0` (ships Python 3.12 + CUDA + a working PyTorch base; we then `uv sync` over it for our pinned CU128 wheels) |
| `--account` flag | Not required for general Engaging access |
| Personal scratch | `$HOME/orcd/scratch` — 1 TB, flash, **purged if no login for 6 months**, no backup |
| Home | `$HOME` — 200 GB, flash, snapshot-backed |
| Personal pool | `$HOME/orcd/pool` — 1 TB, HDD, no backup |
| PI shared pool | `/orcd/pool/<num>/<pi>_shared` — 5 TB+, by PI request to orcd-help |
| Globus collection | "MIT ORCD Engaging Collection", endpoint ID `ec54b570-cac5-47f7-b2a1-100c2078686f` |

## Storage decision: where 1.5 TB goes

The LLC270 monthly tracer tree is ~1.5 TB. Two options:

| Option | Path | Pro | Con |
|---|---|---|---|
| Personal scratch | `$HOME/orcd/scratch/ecco_darwin_v5` | No PI coordination needed | **Cap is 1 TB** — the tree won't fit |
| PI shared pool | `/orcd/pool/<num>/follows_shared/ecco_darwin_v5` | Persistent, 5 TB headroom, sharable with Mick / AW | Need PI to request the pool from orcd-help |

**Recommendation:** ask Mick Follows to request a 5 TB PI-shared pool for the Follows group via orcd-help-engaging. Once you have the path, set:

```bash
export DARWIN_DATA_ROOT=/orcd/pool/<num>/follows_shared/ecco_darwin_v5
```

The SLURM templates fall back to `$HOME/orcd/scratch/ecco_darwin_v5` if `DARWIN_DATA_ROOT` is unset (fine for the test suite, which doesn't load data; will fail with a clear error message for the GPU notebook scripts).

## Local baseline (current state)

DarwinDiff currently runs on a single workstation: **NVIDIA RTX 5090 (32 GB VRAM), Windows 11**, against the LLC270 monthly tracer tree on a 3.7 TB external USB drive (`D:\ecco_darwin_v5\`).

| Workload | Wall-clock (RTX 5090) | Peak GPU mem | Notes |
|---|---|---|---|
| 119-test suite (`pytest`) | ~30 s | n/a (CPU) | Loaders, networks, carroll6 + carbonate, diagnostics |
| nb15 — DINNDeep Eq Pac FeT (1500 epochs) | ~5 min | ~6 GB | 1071 cells, 4-channel input, 9.4K params |
| nb19 — DINNDeep 4-tracer joint loss (1500 epochs) | ~20 min | ~10 GB | 1071 cells, 4 simultaneous tracer fields |
| nb20 — DINNDeep 6-tracer joint loss + carbonate (planned) | ~45–60 min | ~15 GB | adds DIC + ALK + Follows-2006 solver per step |

First side-by-side ORCD vs. local measurement should mirror nb15 on L40S — useful for the scale-up estimate.

## What scale-up unlocks

Workloads that are *infeasible or marginal locally* and become *routine on cluster*. This is the substantive content of any ORCD-scale follow-up to the v2.0 Track 1 closeout.

| Workload | Local feasibility | Why cluster matters |
|---|---|---|
| Multi-seed ensembles (5–10× DINNDeep seeds per AOI, for nb17 trust maps) | Sequential, ~25–50 min | Parallel array job, 5–10 min wall-clock |
| Cross-basin DINNDeep redo at v1.4–v1.8 architecture across nb13, nb14 | Sequential, ~30 min | Three jobs in parallel, ~10 min wall-clock |
| Multi-tracer joint loss at LLC270 native resolution (no 1° downsampling) | Tight on 32 GB at full AOI | Comfortable on 80 GB A100 / H100 |
| Time-resolved fitting (~300 monthly snapshots × current per-fit cost) | Infeasible — ~25 h sequential | Multi-GPU data-parallel; opens Track 2 emulator |
| Box-model further extensions beyond carbonate (full 5-PFT Darwin 3 ecosystem) | Untested; box-model state grows ~3× | Headroom matters once architecture grows |
| Sweep over AOIs (full-ocean parameter recovery) | Infeasible | Embarrassingly parallel across AOIs |

The first two are immediately useful for the next compute proposal (results in days, not weeks). The bottom four are the long-term Track 2 trajectory.

## Compute requirements (generic, in case the target is not ORCD)

- **GPU**: NVIDIA, CUDA 12.x compatible. L40S 44 GB sufficient for everything in current punch list; A100/H100 80 GB needed for native-resolution multi-tracer + time-resolved Track 2.
- **CPU**: any modern node. Box-model integrator is GPU-resident.
- **RAM**: 32 GB+ per job. LLC270 month-tile loading is xarray + dask; large but not extreme.
- **Scratch**: ≥2 TB recommended. The LLC270 monthly tracer tree is ~1.5 TB.
- **Persistent / home**: <50 GB for codebase + checkpoints + figures.

## Data transfer

The LLC270 monthly tracer tree is the only large dataset.

### Globus (recommended for 1.5 TB)

- Source: the local `D:\ecco_darwin_v5\` (Globus Personal Connect on the Windows workstation), or the NAS NASA endpoint (re-download)
- Destination: "MIT ORCD Engaging Collection", endpoint ID `ec54b570-cac5-47f7-b2a1-100c2078686f`, path under the PI-shared pool

### rsync (fallback for small subsets only)

```bash
rsync -avh --progress /d/ecco_darwin_v5/ <kerb>@orcd-login.mit.edu:/orcd/pool/<num>/follows_shared/ecco_darwin_v5/
```

Duo prompts on every connection make this painful for the full tree; use Globus.

## SLURM scripts — what's pre-filled, what's left

Three templates under [`scripts/slurm/`](../scripts/slurm/) with ORCD-specific values already filled in:

| Script | Pre-filled | Still TBC by Jonathan |
|---|---|---|
| [`run_tests.sbatch`](../scripts/slurm/run_tests.sbatch) | `--partition=mit_normal`, miniforge module, 8 GB RAM, 30 min | Partition name (best guess) |
| [`run_notebook.sbatch`](../scripts/slurm/run_notebook.sbatch) | `--partition=mit_normal_gpu`, `--gres=gpu:1`, miniforge, 32 GB RAM, 4 h | A100 alternative documented in comment; wall-time may need tuning |
| [`run_array.sbatch`](../scripts/slurm/run_array.sbatch) | `--partition=mit_normal_gpu`, array `0-9%1`, miniforge | Same A100 comment applies |

All three scripts:
- Use `${DARWIN_DATA_ROOT:-$HOME/orcd/scratch/ecco_darwin_v5}` so Jonathan can override with `export` instead of editing the script
- Auto-install `uv` if missing
- Auto-run `uv sync --all-extras` to materialize the venv
- Write logs to `logs/<jobname>_<jobid>.{out,err}` (gitignored)

The single-entry-point script [`scripts/orcd_quickstart.sh`](../scripts/orcd_quickstart.sh) wraps the one-time setup (miniforge load + uv install + sync + pytest) so Jonathan can run a single command to confirm his ORCD environment is ready.

## What we have NOT validated yet on ORCD

- Actual wall-clock timings on L40S / H100 / A100 (the table above is local-only). First cluster job should mirror nb15 for a side-by-side benchmark.
- The exact CPU partition name (`mit_normal` is our best guess).
- Whether `pytorch` from miniforge or the CU128-wheel install via uv is faster on L40S/H100. We default to uv-managed wheels for reproducibility with the rest of the project.
- The path-refactor for `DARWIN_DATA_ROOT` across all data-loading notebooks landed in PR #29; verified locally but not yet exercised on a cluster.

## Cross-references

- [README](../README.md) — project overview, headline results
- [STATUS](../STATUS.md) — live state, finding-by-finding
- [docs/dinn_design.md](dinn_design.md) — DINN / DINNDeep architecture, training loop
- [data/README.md](../data/README.md) — dataset provenance and download mechanics
- [pyproject.toml](../pyproject.toml) — pinned Python deps, CUDA index
