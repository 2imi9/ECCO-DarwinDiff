# Spatial UDE feasibility — environment-dependent neural closure over a field

Follow-up to the 0-D hybrid probe (`scripts/hybrid_feasibility_probe.py`): can a
neural closure that depends on the **local environment** be learned end-to-end
through the differentiable BGC, **batched over a spatial field**? This is the
Track-2 thesis the 0-D box cannot demonstrate (it homogenizes spatial structure),
and it is exactly the structure tonight's Southern-Ocean calcite finding
(`scripts/per_pft_picpoc_validate.py`) says the real process has.

Script: `scripts/hybrid_spatial_h200.py` (+ `scripts/slurm/run_hybrid_spatial_h200.sbatch`).

## Setup
Each cell of an H×W field has its own iron `DFe` (spanning the limitation knee)
**and** a local environment scalar `env ∈ [0,1]` (stand-in for temperature /
saturation / light). A 2-input net learns the closure `f(iron, env)` end-to-end;
truth is `iron-limitation(DFe) × env-window(env)`.

## Result (RTX 5090, 9,216-cell field, 2000 epochs, ~4.7 min)
| metric | value |
|---|---|
| loss | 0.61 → 3.8e-5 (↓ ~15,900×) |
| **2-D closure recovery (MAE)** | **0.0044 (0.44%)** |

The machinery recovers a **synthetic** spatial, 2-input closure to sub-percent
accuracy. This is a **feasibility** result, not a real-data discovery: both the
environment field and the true closure are made-up (a self-twin). It proves the
machinery can learn the *shape* of closure — spatial and environment-dependent —
that the per-PFT/SO finding points to; learning the *real* relationship from real
Darwin data is the Track-2 build, not this run.

## Launch-bound / `torch.compile` (corrected)
The per-step rollout is launch-bound. A clean benchmark (RTX 5090, 9,216 cells,
100 steps, warmed up **at the timing shape**):

| mode | ms/iter |
|---|---|
| eager python loop | 236 |
| `torch.compile(step)` | **80 (≈3×)** |

`torch.compile` **does** fix the launch-bound (~3×). An earlier run reported
0.8× ("slower") — that was a **benchmarking bug**: the compiled step was warmed
up at `n=5` but timed at `n=200`, so recompilation contaminated the timing. Fixed
in `hybrid_spatial_h200.py` (`epoch_time` now warms up at the timing shape).

## Cluster note
The H200 job (`gpu-short`, node d4054) ran on a real H200 but, on the pre-fix
script, its eager/launch-bound per-epoch (~1 s) overran a tight 30-min wall before
writing JSON. The science is device-independent (the 5090 result stands); a
right-sized H200 rerun with the fixed script is a clean-up, not a blocker. Next
real GPU lever for scale: TF32 (`set_float32_matmul_precision('high')`),
compiling the whole rollout / CUDA graphs, and larger fields.
