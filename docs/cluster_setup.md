# Cluster setup — DarwinDiff on Explorer (Northeastern) + AICR (Massachusetts)

Operational guide for running DarwinDiff on **Northeastern's Explorer** and the **Massachusetts AI Compute Resource (AICR)**. Companion to [README](../README.md) (project overview) and [STATUS](../STATUS.md) (live results).

## Target clusters

Two clusters are in play — one Northeastern-owned, one a shared multi-institutional resource:

| Cluster | Hardware | Status / when to use |
|---|---|---|
| **Explorer** (Northeastern RC) | H200 144 GB (×32 RC-owned), A100 80 GB (×8), V100, L40S, t4 | **Active automation path.** General HPC, free to NU faculty/students, Cristina-sponsored. All current cluster runs (the n=10 ensembles, the per-cell ablation, the per-AOI identifiability map) run here. |
| **AICR** (Massachusetts AI Compute Resource) | 248× B200 + 152× RTX Pro | **Active** (account created); B200 throughput. See below. |

> **Note.** "AICR" is the **Massachusetts AI Compute Resource** — a *multi-institutional* GPU cluster (Boston University, Harvard, MIT, Northeastern, UMass, Yale) run under the **Massachusetts AI Hub**, **not** a Northeastern-owned cluster. Northeastern is one member institution and access is provisioned through NU (Cristina-sponsored). It is unrelated to any MIT path, and the project does **not** use MIT ORCD / Engaging (an earlier exploratory option, since dropped).

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

## AICR — Massachusetts AI Compute Resource

AICR is the **Massachusetts AI Compute Resource** — a multi-institutional **B200 / RTX PRO 6000** GPU cluster at MGHPCC (Holyoke), run under the **Massachusetts AI Hub** and serving Boston University, Harvard, MIT, Northeastern, UMass (five campuses), and Yale. Docs: <https://docs.aicr.ai>. DarwinDiff's **AICR user account is created (active)**; access is provisioned through NU. Per the compute budget a single fit is launch-bound (same speed on 5090 / H200 / B200), so AICR's role is **throughput — large sweeps + native/seasonal runs**, targeting `b200-batch`.

> **Onboarding status (2026-07-07) — first login blocked by provisioning lag.** OOD errors
> `nginx_stage: can't find user for qi_zim_neu` — the individual account isn't provisioned/synced to the
> OOD/compute nodes yet (`getpwnam` fails). **`qi_zim_neu` is the correct username** (Explorer `qi.zim` →
> AICR `<institutional-username>_<institution-code>`: dots→underscores, `_neu` for NU) — not a mismatch.
> SSH is blocked by the same gap (the cert is downloaded through OOD). Fix is RC-side: email
> `rchelp@northeastern.edu` (opens a ServiceNow ticket) and/or RC office hours (Wed 3–4 / Thu 11–12 ET,
> [Wed Zoom](https://northeastern.zoom.us/j/92041124566) · [Thu Zoom](https://northeastern.zoom.us/j/94304265138)).
> **Not blocking** — Explorer's H200 carries current work.

### Access — username & credentials

- **Username:** `qi_zim_neu`.
- **OnDemand (browser, no setup):** <https://ood.aicr.ai> — sign in with NU username + password.
- **SSH (certificate auth — no password, no VPN; login nodes are public):** on account creation, download
  the `aicr_keys` folder from OOD (**Files → Home Directory → Download**): `id_ed25519_aicr` (private key,
  passphrase-protected), `id_ed25519_aicr.pub`, `id_ed25519_aicr-cert.pub` (CA-signed cert), `.passphrase`
  (initial passphrase). Place all in `~/.ssh/`, then:

  ```bash
  chmod 600 ~/.ssh/id_ed25519_aicr
  chmod 644 ~/.ssh/id_ed25519_aicr.pub ~/.ssh/id_ed25519_aicr-cert.pub
  ssh-keygen -p -f ~/.ssh/id_ed25519_aicr        # set your own passphrase (initial is in .passphrase)
  ```

  Add to `~/.ssh/config` (then `ssh aicr`):

  ```
  Host aicr
      HostName login.aicr.ai
      User qi_zim_neu
      IdentityFile ~/.ssh/id_ed25519_aicr
      CertificateFile ~/.ssh/id_ed25519_aicr-cert.pub
      ServerAliveInterval 60
  ```

  Certs are short-lived → re-download via OOD's **SSH Certificate** app when they approach expiry
  (`Permission denied (publickey)` usually = expired/missing cert). Host key changed →
  `ssh-keygen -R login.aicr.ai`.

### Hardware & partitions

| Partition | GPU | Walltime | Use |
|---|---|---|---|
| `b200-batch` | B200 | 24 h | training / sweeps ← our throughput jobs |
| `b200-devel` | B200 | 4 h | interactive / OOD |
| `rtx-batch` / `rtx-devel` | RTX PRO 6000 | 24 h / 4 h | batch / interactive |
| `cpu` | — | 24 h | data transforms |

- GPU request: `--gres=gpu:N`. Modules: `module load cuda/13.1`, `module load miniforge3/25.3.0-3`.
- **Login nodes:** 4 CPU / 8 GB per user — edit / submit / small transfers only, **no compute** (use
  `sbatch` or `salloc`). Idle-GPU jobs are **auto-cancelled** (same as Explorer's Arbiter — build inside a
  Slurm job, not on the login node). Multi-GPU jobs must actually use the GPUs (DDP / NCCL).

### Storage

| Path | Quota | Policy |
|---|---|---|
| `/home/qi_zim_neu` | 100 GB | 7-day snapshots — scripts / env only |
| `/scratch/qi_zim_neu` | 10 TB | **30-day purge, no backup** — job outputs |
| `/work/neu/<group>` (confirm group name; the `/projects/schultz` analog) | PI-managed | 7-day snapshots — **repo + caches live here** |

Storage is ephemeral → migrate keep-data off via **Globus** post-project. Matches DarwinDiff's
disk-temporary workflow (per-run JSON to local `D:\runs\`, no per-run state in repo).

### Setup & run (post-activation)

```bash
ssh aicr
cd /work/neu/<group> && git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
module load miniforge3/25.3.0-3 cuda/13.1
uv python pin 3.12 && uv sync --all-extras && uv run pytest        # honor the .python-version pin (see Explorer note)
sbatch --partition=b200-batch scripts/slurm/run_explorer_gpu.sbatch  # adjust partition/modules/data-root from the Explorer sbatch
```

Porting from Explorer is ~three edits: partition (`gpu` → `b200-batch`), modules (`anaconda3` →
`miniforge3/25.3.0-3` + `cuda/13.1`), and storage root (`/projects/schultz` → `/work/neu/<group>`).
Support: `rchelp@northeastern.edu`.

## Cross-references

- [README](../README.md) — project overview
- [STATUS](../STATUS.md) — live state and findings
- [docs/dinn_design.md](dinn_design.md) — DINN architecture, training loop
- [data/README.md](../data/README.md) — dataset provenance and download mechanics
