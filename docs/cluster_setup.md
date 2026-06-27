# Cluster setup — DarwinDiff on Northeastern RC + MIT ORCD

Operational guide for running DarwinDiff on Northeastern RC (Explorer / AICR) and MIT ORCD clusters. Companion to [README](../README.md) (project overview) and [STATUS](../STATUS.md) (live results).

## Target clusters

DarwinDiff has compute paths across **two institutions** — Northeastern RC (Lucas's home institution, Cristina-sponsored) and MIT ORCD (Jon's). Three distinct clusters are in play; do not conflate them:

| Cluster | Institution | Hardware | Status / when to use |
|---|---|---|---|
| **Explorer** | Northeastern RC | H200 144 GB (×32 RC-owned), A100 80 GB (×8), V100, L40S | **Active near-term path.** General HPC, free to NU faculty/students, Cristina-sponsored. The first native-resolution prototype runs here. |
| **AICR** | Northeastern RC | 248× B200 + 152× RTX Pro | Future path. NU's dedicated AI cluster; access via a PI **project proposal** (the `AICR_proposal.docx` in prep). Target for the global-native / seasonal sweep. |
| **Engaging** | MIT ORCD | A100, L40S, H100 80 GB, H200 140 GB | Jon-side option. Open to MIT users. |

> **Naming note.** "AICR" here is **Northeastern's** AI Compute Resource (B200 + RTX Pro). Earlier project notes framed AICR as an MIT ORCD follow-on to Engaging — that conflated two things. The B200 proposal Cristina and Jon are reviewing is NU's AICR; MIT Engaging is a separate, Jon-side path.

Explorer is the de-facto near-term path (access granted June 2026, Cristina-sponsored). The Engaging section below is retained for the MIT-side option.

## Northeastern Explorer

Explorer is Northeastern RC's general HPC cluster (<https://rc.northeastern.edu>), free to all NU faculty and students. Access for a sponsored user is a ServiceNow "Research Computing Access Request" with a PI sponsor.

### Access

1. Submit the [Research Computing Access Request](https://rc.northeastern.edu/getting-access/) (ServiceNow), listing your PI as **University Sponsor** and their storage space (e.g. `schultz`).
2. The sponsor approves via the emailed link; the account provisions within ~24 h.
3. Current NU students already have credentials — no separate "external user" step.

> **MGHPCC shutdown.** All RC services are down for the annual MGHPCC shutdown **June 15–19 2026**; Explorer returns Friday June 19. Submit access during the downtime; first login after it returns.

### Hardware (RC-owned, generally schedulable)

| GPU | VRAM | Count | Notes |
|---|---|---|---|
| H200 | 144 GB | 4 nodes × 8 = 32 | Ideal tier; holds a native-resolution fit (LLC270 time-mean ~63 GB, measured in [`memory_scaling.md`](findings/memory_scaling.md)) on one card |
| A100 | 80 GB | 2 nodes × 4 = 8 | Workable fallback |
| V100 | 16–32 GB | many | Too small for native-resolution reverse-mode AD |

H100 / L40S exist but are PI-owned (need that PI's permission). Cluster totals: 45k+ CPU cores, 525+ GPUs, 6 PB storage, InfiniBand (200/100 Gbps).

### Partitions & GPU request

- Batch: `--partition=gpu`; interactive: `--partition=gpu-interactive`.
- Type-pinned request: `--gres=gpu:h200:1` — documented **verbatim** in the [H200 quick-start guide](https://rc-docs.northeastern.edu/en/explorer-main/gpus/quickstart-h200.html) (verified 2026-06-23), which also confirms the `gpu` (batch) / `gpu-interactive` (srun) partitions. Still confirm on first login: the A100 fallback token (`gpu:a100:1`) and the partition wall-time cap (`sinfo -o "%P %l %G"`).
- The `gpu` partition caps at **1 GPU per request** — fine for one native fit (1× H200 = 144 GB ≥ the ~63 GB LLC270 time-mean peak); the later multi-GPU seasonal sweep needs a different partition (ask `rchelp@northeastern.edu`).

### Storage

| Path | Use | Policy |
|---|---|---|
| `/projects/<group>` (e.g. `/projects/schultz`) | Performant group storage; put the repo + data here | PI-requested; Schultz group ~35 TB total (<10 TB free, June 2026) |
| `/scratch/$USER` | Temp / intermediate | **Purged monthly**, not backed up |
| `/home/$USER` | Configs, small files | Fixed quota, cannot increase — do **not** build envs or caches here |

The LLC270 monthly tracer tree (~1.5 TB, the only large input) fits comfortably under the Schultz allocation; per-run JSON outputs are small. If space is tight, `/scratch` + a local master copy also works — the project's disk-temporary workflow already matches this.

### Setup & run

```bash
# Clone UNDER group storage to avoid the small /home quota:
cd /projects/schultz && git clone https://github.com/2imi9/ECCO-DarwinDiff.git
cd ECCO-DarwinDiff
bash scripts/explorer_quickstart.sh                       # module load anaconda3 + uv sync + pytest

export DARWIN_DATA_ROOT=/projects/schultz/ecco_darwin_v5  # LLC270 tree
sbatch scripts/slurm/run_explorer_gpu.sbatch              # H200 job (defaults to the multi-AOI trainer)
```

> **Python pin (required).** The repo commits `.python-version` = `3.12`, which `uv`
> honors for both `uv sync` and `uv run`. Do **not** remove it: with only
> `requires-python = ">=3.11"`, a fresh `uv sync` selects Python 3.14, where
> `aiohttp` (pulled in transitively by `argopy`) has no cp314 wheel and its sdist
> build fails — this is what broke the first Explorer build (unblocked by
> `uv python pin 3.12`, now committed). Under 3.12, `uv sync --all-extras` resolves
> to all-binary wheels (no source builds). `pyproject.toml` also caps
> `requires-python` at `<3.14` so the constraint holds even without the pin file.

### Data transfer (~1.5 TB tree → Explorer)

- **Globus** is the practical path for the full tree (NU has a Globus endpoint; confirm the collection name with RC). Destination: `/projects/schultz/ecco_darwin_v5`.
- `scp` / `rsync` works for subsets; impractical for the full tree.
- Transfers cannot run during the June 15–19 shutdown — stage the job for Friday.

## Engaging — access path

Engaging is "openly available to all research projects at MIT" per the [ORCD docs](https://orcd-docs.mit.edu). Account auto-activates on first OnDemand login. For non-MIT collaborators (e.g. Northeastern affiliates), an MIT Sponsored Account is the prerequisite.

### Onboarding for non-MIT collaborators

1. **MIT host initiates a Sponsored Account request** via MIT IS&T's standard form (Atlas or equivalent). The host must have an active MIT appointment.
2. **Complete Kerberos ID + Duo 2FA setup** per the account-activation email.
3. **Log in to https://orcd-ood.mit.edu** (OnDemand). Engaging account auto-provisions on first login (typically within an hour).
4. **Run a test job** via `sbatch scripts/slurm/run_tests.sbatch` to confirm the environment.

### Onboarding for MIT-affiliated users

Skip the sponsorship step. Kerberos ID + Duo + OnDemand login activates Engaging directly.

### Quickstart

```bash
# 1. SSH login (Duo MFA required)
ssh <kerb>@orcd-login.mit.edu

# 2. Clone the repo
git clone https://github.com/2imi9/ECCO-DarwinDiff.git
cd ECCO-DarwinDiff

# 3. One-time environment setup
bash scripts/orcd_quickstart.sh   # loads miniforge, installs uv, syncs deps, runs pytest

# 4. Submit jobs
sbatch scripts/slurm/run_tests.sbatch                                        # CPU sanity (~30s)
sbatch scripts/slurm/run_notebook.sbatch notebooks/15_dinn_deep_eqpac_fet.ipynb   # GPU notebook
```

To run anything that loads the LLC270 monthly tracer tree, set `DARWIN_DATA_ROOT` to the data root (see [Storage](#storage)).

## Engaging — resources

| Resource | Value |
|---|---|
| Login | `ssh <kerb>@orcd-login.mit.edu` or https://orcd-ood.mit.edu (Duo MFA + Kerberos) |
| GPU partition (open) | `mit_normal_gpu` — L40S 44 GB (49 nodes × 4), H100 80 GB (1 node × 4), H200 140 GB (11 nodes × 8) |
| GPU partition (A100, preemptable) | `mit_preemptable` — A100-SXM4-80 GB (6 nodes × 8) + A100-PCIe-80 GB. Requires `--requeue` |
| Module system | Lmod (`module load/avail/purge`). Recommended: `module load miniforge/24.3.0-0` |
| `--account` flag | Not required for general Engaging access |
| Personal scratch | `$HOME/orcd/scratch` — 1 TB flash, purged if no login for 6 months, no backup |
| Home | `$HOME` — 200 GB flash, snapshot-backed |
| Personal pool | `$HOME/orcd/pool` — 1 TB HDD, no backup |
| PI shared pool | `/orcd/pool/<num>/<pi>_shared` — 5 TB+, requested via orcd-help |
| Globus collection | "MIT ORCD Engaging Collection", endpoint `ec54b570-cac5-47f7-b2a1-100c2078686f` |
| Support email | orcd-help-engaging@mit.edu |
| Maintenance | 3rd Tuesday monthly (~1 day); login-node restart Monday 7am (~15 min) |

## Storage

The LLC270 monthly tracer tree is ~1.5 TB and is the only large dataset.

| Path | Size | Use |
|---|---|---|
| Personal scratch | 1 TB cap | Insufficient for the full tree; usable for smoke tests + subsets |
| PI shared pool (`/orcd/pool/<num>/<pi>_shared`) | 5 TB+ | Recommended. Requested by PI via orcd-help-engaging. Persistent. Shareable across the PI's group. |

After provisioning, set:

```bash
export DARWIN_DATA_ROOT=/orcd/pool/<num>/<pi>_shared/ecco_darwin_v5
```

SLURM templates fall back to `$HOME/orcd/scratch/ecco_darwin_v5` if `DARWIN_DATA_ROOT` is unset — fine for the test suite, fails with a clear error for data-loading scripts.

## Data transfer

### Globus (recommended for the full 1.5 TB tree)

- Source: NAS endpoint (re-download from NASA), or Globus Personal Connect on a workstation that already has the tree.
- Destination: "MIT ORCD Engaging Collection" (endpoint `ec54b570-cac5-47f7-b2a1-100c2078686f`), under the PI-shared pool path.

### rsync (subsets only)

```bash
rsync -avh --progress /local/ecco_darwin_v5/ <kerb>@orcd-login.mit.edu:/orcd/pool/<num>/<pi>_shared/ecco_darwin_v5/
```

Duo prompts on every connection make this impractical for the full tree.

## SLURM templates

Three pre-filled scripts in [`scripts/slurm/`](../scripts/slurm/):

| Script | Defaults | Wall-time |
|---|---|---|
| [`run_tests.sbatch`](../scripts/slurm/run_tests.sbatch) | `--partition=mit_normal`, miniforge module, 8 GB RAM | 30 min |
| [`run_notebook.sbatch`](../scripts/slurm/run_notebook.sbatch) | `--partition=mit_normal_gpu`, `--gres=gpu:1`, miniforge, 32 GB RAM | 4 h |
| [`run_array.sbatch`](../scripts/slurm/run_array.sbatch) | `--partition=mit_normal_gpu`, array `0-9%1`, miniforge | 30 min per array task |

All three:

- Use `${DARWIN_DATA_ROOT:-$HOME/orcd/scratch/ecco_darwin_v5}` so users override with `export` instead of editing the script.
- Auto-install `uv` if missing.
- Auto-run `uv sync --all-extras` to materialize the venv.
- Write logs to `logs/<jobname>_<jobid>.{out,err}` (gitignored).

[`scripts/orcd_quickstart.sh`](../scripts/orcd_quickstart.sh) wraps the one-time setup (miniforge load + uv install + sync + pytest) as a single entry point.

## Compute requirements

| Resource | Minimum | Recommended |
|---|---|---|
| GPU | NVIDIA L40S 44 GB (CUDA 12.x) | A100/H100 80 GB for native-resolution multi-tracer + time-resolved Track 2 |
| CPU | Any modern node | — |
| RAM | 32 GB per job | — |
| Scratch | 2 TB | LLC270 monthly tracer tree is ~1.5 TB |
| Persistent / home | <50 GB | — |

## Local baseline (for comparison)

DarwinDiff also runs on a single workstation (NVIDIA RTX 5090 32 GB, Windows 11) against the LLC270 tree on external storage. The single-laptop workflow drove all v0.x–v3.1 results; cluster scale-up is for production.

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
| Multi-tracer joint loss at LLC270 native resolution | Tight on 32 GB at full AOI | Comfortable on 80 GB A100 / H100 |
| Time-resolved fitting (~300 monthly snapshots × per-fit cost) | Infeasible (~25 h sequential) | Multi-GPU data-parallel; opens Track 2 emulator |
| Full-ocean parameter recovery sweep | Infeasible | Embarrassingly parallel across AOIs |
| Native-resolution parameter maps + forward Darwin validation (vs box-model proxy) | Tested: native res selects *which* iron-pair param recovers but does **not** lift the recovery count, and did **not** help `R_PICPOC` — identifiability comes from real absolute anchors, not resolution (the surrogate gap is dimensional, not resolution-limited). Value is per-cell parameter maps + forward validation. | Headroom for the maps + validation |

## AICR — application path

After confirming a successful Engaging run:

1. Reply to the ORCD beta-coordinator confirming Engaging usage + acknowledgment of the AICR storage policy (no backup, scratch purged).
2. Receive the AICR access form.
3. Once granted, port the workload from Engaging-partition SLURM to AICR-partition SLURM (typically a one-line `#SBATCH --partition` change + module path adjustment).

AICR storage caveats:

- Scratch is purged regularly.
- Project/group storage is temporary.
- Copy any data you need to keep off AICR after computation completes.

These match DarwinDiff's existing disk-temporary workflow (per-run JSON outputs to local `D:\runs\`, no per-run state in repo) so no architectural changes are required.

## Cross-references

- [README](../README.md) — project overview
- [STATUS](../STATUS.md) — live state and findings
- [docs/dinn_design.md](dinn_design.md) — DINN architecture, training loop
- [data/README.md](../data/README.md) — dataset provenance and download mechanics
