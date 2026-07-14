# Track-2 Neural Emulator — Developer Guide

## Overview

The Track-2 emulator is a Fourier Neural Operator (FNO) surrogate of ECCO-Darwin v05. Given the
ocean-biogeochemistry surface state at one time step, it predicts the state at the next step. Model
quality is measured as **skill relative to a persistence baseline** on a leak-free temporal
hold-out. This guide describes how to extract training data, train and score a model, and interpret
the results. It is intended for new contributors and for automated agents resuming the project.

All skill values reported by the pipeline are **local**: they measure self-consistency against the
ECCO-Darwin v05 *model output*, not agreement with real observations. See
[Interpreting results](#interpreting-results) and [Scope and limitations](#scope-and-limitations).

## Repository layout

| Component | Path |
|---|---|
| Model — `FNO2d`, `DarwinEmulator` (Earth-2 prognostic interface) | `src/darwindiff/emulator.py` |
| Runner — extraction, training, scoring, checkpointing | `scripts/emulator_poc.py` |
| Checkpoint publishing (private HuggingFace repo by default) | `scripts/hf_upload_model.py` |
| Tests — model and leak-free data helpers | `tests/test_emulator.py`, `tests/test_emulator_poc.py` |
| Results (local) | `docs/findings/emulator_*_scored.md`, `docs/findings/2026-07-*.md` |
| Roadmap epic | GitHub issue #185 |

## Workflow

The pipeline runs in two stages — data extraction and model training — connected by a portable cube
file (`.npz`). Extraction reads native LLC270 fields with surface partial reads, bins them onto a
regular latitude/longitude grid, and writes the cube. Training loads the cube. Because the two
stages are decoupled, extraction (CPU- and I/O-bound, run where the raw data resides) and training
(GPU-bound) may run on different machines.

### Stage 1 — Extract a data cube (CPU)

```bash
python scripts/emulator_poc.py \
  --data-root <v05 root> --grid-dir <grid dir> \
  --tracers DIC,ALK,PIC,POC,FeT,Chl1 --aoi eqpac --grid-res 0.25 --levels 1 \
  --dump-cube eqpac_native_cube.npz
```

Key options:

- `--aoi` selects a named region. `--aoi-bounds lat_min,lat_max,lon_min,lon_max` overrides the
  bounds for an arbitrary box, including the whole globe:
  `--aoi global --aoi-bounds=-80,89.75,-180,180`. The `=` is required because the value begins
  with a minus sign. A full 360° longitude span is treated as periodic, so the current extractor does
  not duplicate the antimeridian. This seam de-duplication is a recent addition; cubes extracted
  earlier — including the 2026-07-13 global cube — carry a redundant ±180° column (1441 longitudes
  rather than 1440).
- `--grid-res` sets the target grid resolution in degrees (`1.0` for 1°; `0.25` approximates the
  LLC270 native resolution, which oversamples the native grid and therefore leaves unfilled cells).
- `--data-subdir` sets the per-variable subpath beneath `--data-root`. The default,
  `output/monthly`, matches the v05 monthly tree; the daily surface variables are stored flat, so
  pass `--data-subdir .` for daily cubes.
- `--forcing SST,wspeed,mldDepth` bakes input-only forcing channels into the cube.

### Stage 2 — Train and score (GPU)

```bash
python scripts/emulator_poc.py \
  --load-cube eqpac_native_cube.npz --aoi eqpac \
  --epochs 150 --residual --rollout-train-k 4 --modes 16 --width 48 --seed 0 \
  --save-model model.safetensors --out run.json
```

Key options:

- `--residual` trains the model to predict the tendency, `x(t+1) − x(t)`; `--rollout-train-k K`
  adds a K-step autoregressive term to the loss. Together these constitute the method fix:
  without them the slow carbon tracers (DIC, ALK) fail and multi-step rollout is unstable. `k=4`
  is the recommended value — `k=1` maximizes single-step skill but destabilizes rollout.
- `--save-model <path>.safetensors` writes the model weights, the per-channel standardization
  statistics, and the architecture configuration required to rebuild the model. Complex spectral
  weights are stored as real views with a `complex_keys` entry in the file metadata so they can be
  reconstructed. Tensors are moved to CPU, so the checkpoint loads on any GPU.

## Interpreting results

The headline metric is **skill over persistence**, computed per channel in z-scored space and
weighted by grid-cell area (cos-latitude), so that global-scale skill is not biased toward the
poles:

```
skill = 1 − MSE(model) / MSE(persistence)
```

A value above zero indicates that the model outperforms the persistence forecast `x(t+1) = x(t)`.
The runner emits a verdict of `MAKE` when overall skill exceeds 0.02 with a stable rollout,
`MARGINAL` when skill is small but positive, and `BREAK` when skill is non-positive.

Persistence is a strong baseline, and it strengthens as the time step shortens: persistence skill
relative to climatology is approximately +0.22 at monthly cadence over the equatorial Pacific,
compared with approximately +0.98 at daily cadence. A daily next-step emulator therefore faces a
substantially harder target than a monthly one, and its value lies more in multi-day rollout and
anomaly skill than in single-step prediction. The runner also reports the anomaly-R² against
climatology and a six-step rollout stability and mass-drift check.

## Cluster environments

- **NU Explorer (H200, account `c.schultz`)** holds the raw v05 data at
  `/projects/schultz/qi.zim/ecco_darwin_v5`. The `/projects` filesystem is quota-limited, so write
  cubes to `/scratch/qi.zim/`.
- **NU AICR (B200, account `p2026_0089_neu`)** provides 2.6 PB of `/scratch` and direct egress to
  the NASA data portal. Download data directly to this cluster (parallel per-variable transfers
  exceed the portal's per-connection throttle) and train there.
- Cross-cluster transfer of a cube through a local relay is slow (under 1 MB/s to AICR). Prefer
  extracting or downloading data on the cluster where the GPU resides, or use Globus for large
  transfers.

## Scope and limitations

Reported skill measures self-consistency against the ECCO-Darwin v05 model output; it is not a
validation against real observations, which is the project's primary open question (issue #163).
The emulator is a next-state surrogate of the model — it does not render Darwin differentiable and
does not learn biology from data. External validation against SOCAT and GLODAP is the step that
would elevate these results from a model surrogate to a scientific finding.
