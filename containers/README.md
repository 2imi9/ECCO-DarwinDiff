# Containers

Portable [Apptainer](https://apptainer.org) image for the DarwinDiff environment
(Python 3.12 + PyTorch `cu128` + all deps, baked from the committed `uv.lock`).
The same image runs on Explorer (H200, sm_90) and AICR (B200, sm_100) — the
`cu128` wheels carry both. Code and data are bind-mounted at run time; only the
environment and the `darwindiff` package are baked in.

## Build

Docker isn't available on the cluster (no root daemon), so this is an Apptainer
`.sif`. Build **inside a Slurm job** — the login node's Arbiter watchdog kills the
heavy `uv sync`, and NFS `/projects` can't host the build temp:

```bash
sbatch containers/build_sif.sbatch     # writes containers/darwindiff.sif (~4 GB)
```

`build_sif.sbatch` runs on a CPU node with the build temp on node-local `$TMPDIR`
and `apptainer build --fakeroot` (no `/etc/subuid` entry → root-mapped-namespace
fallback, which is fine for a `uv sync` `%post`).

## Run

```bash
# GPU job: --nv injects the host NVIDIA driver; bind the repo over /work.
apptainer exec --nv --bind "$PWD:/work" containers/darwindiff.sif \
    python /work/scripts/measure_memory_scaling.py --compile

# e.g. the #119 measurement:
apptainer exec --nv --bind "$PWD:/work" containers/darwindiff.sif \
    python /work/scripts/measure_memory_scaling.py \
    --compile --md /work/docs/findings/memory_scaling_compiled.md
```

`build-essential` is baked in because `torch.compile`'s Triton backend
JIT-compiles a CUDA kernel launcher at run time (without it, `--compile` fails
with "Failed to find C compiler").

The `.sif` itself is a multi-GB build artifact and is gitignored — rebuild it
from the def, or keep a copy under `/projects/schultz`.
