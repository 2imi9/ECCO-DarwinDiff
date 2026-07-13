# Track-2 emulator — how to run it (contributor guide)

A next-state FNO surrogate of ECCO-Darwin **v05**: given this month's (or day's) ocean-BGC
surface state, predict the next one, scored by **skill over persistence** on a leak-free
temporal hold-out. This guide is the fast path for a new contributor (or a future session).
All skill numbers are **LOCAL** (self-consistency vs the v05 *model*, not real obs) — see the
honesty note at the end.

## Where the pieces live

| Piece | Path |
|---|---|
| Model (FNO2d / DarwinEmulator, Earth-2 prognostic contract) | `src/darwindiff/emulator.py` |
| Runner (extract → train → score → save) | `scripts/emulator_poc.py` |
| HF checkpoint publish (private-by-default) | `scripts/hf_upload_model.py` |
| Tests (model + leak-free helpers) | `tests/test_emulator.py`, `tests/test_emulator_poc.py` |
| Findings (local) | `docs/findings/emulator_*_scored.md`, `docs/findings/2026-07-12_resolution_sharpening.md` |
| Tracker epic | GitHub #185 |

## Two-stage workflow: extract a cube, then train

Extraction reads native LLC270 fields (surface partial-read), bins to a regular lat/lon grid,
and writes a portable `.npz` cube. Training loads the cube — so extraction (CPU/IO, where the
data lives) and training (GPU) can run on different machines.

**1. Extract a cube** (CPU; on the cluster holding the raw data):
```bash
python scripts/emulator_poc.py \
  --data-root <v05 root> --grid-dir <grid> \
  --tracers DIC,ALK,PIC,POC,FeT,Chl1 --aoi eqpac --grid-res 0.25 --levels 1 \
  --dump-cube eqpac_native_cube.npz
```
- `--aoi` picks a named region; `--aoi-bounds lat0,lat1,lon0,lon1` overrides for any box —
  including whole-globe: `--aoi global --aoi-bounds=-80,89.75,-180,180` (note the `=`, the
  leading `-` needs it). A full 360° span is treated as periodic (no duplicated antimeridian col).
- `--grid-res 1.0` is 1°, `0.25` ≈ LLC270 native (holey — oversamples the native grid).
- `--data-subdir` sets the per-variable subpath under `--data-root`. Default `output/monthly`
  (v05 monthly tree). **Daily** surface vars are flat, so pass `--data-subdir .`.
- `--forcing SST,wspeed,mldDepth` bakes input-only forcing channels into the cube.

**2. Train + score** (GPU):
```bash
python scripts/emulator_poc.py \
  --load-cube eqpac_native_cube.npz --aoi eqpac \
  --epochs 150 --residual --rollout-train-k 4 --modes 16 --width 48 --seed 0 \
  --save-model model.safetensors --out run.json
```
- `--residual` predicts the tendency (x(t+1)−x(t)); `--rollout-train-k K` adds a K-step
  autoregressive loss. **These two are the method-fix** — without them DIC/ALK fail and rollout
  is marginal. `k=4` is the sweet spot (k=1 wins 1-step skill but fails multi-step rollout).
- `--save-model *.safetensors` writes weights (complex spectral weights stored as real views +
  `complex_keys` metadata) + standardization stats + rebuild config. Portable across GPUs.

## Cluster patterns

- **Explorer (H200, `c.schultz`)** holds the raw v05 data at `/projects/schultz/qi.zim/ecco_darwin_v5`.
  `/projects` is quota-limited — extract cubes onto `/scratch/qi.zim/` (huge).
- **AICR (B200, `p2026_0089_neu`)** — your own allocation, `/scratch` 2.6 PB, direct NAS egress.
  Download data straight here (parallel per-variable wget beats NAS's per-connection throttle).
- Cross-cluster transfer of a cube is slow through a laptop relay (<1 MB/s to AICR) — prefer
  extracting/downloading **where the GPU is**, or Globus for large moves.

## Reading the result

- **skill = 1 − MSE(model)/MSE(persistence)**, per-channel z-scored, **cos(lat) area-weighted**
  (so global skill isn't polar-biased). `>0` beats persistence; `MAKE` if `>0.02` + stable rollout.
- Persistence is a *hard* baseline and gets harder as the step shrinks: monthly persistence-vs-
  climatology ≈ +0.22, but **daily ≈ +0.98** — so a daily next-step emulator is a much harder
  target than monthly, and its value is more in multi-day rollout / anomaly skill.
- Also reported: anomaly-R² vs climatology, and a 6-step rollout stability + mass-drift check.

## Honesty guardrail

Skill numbers stay LOCAL. This is a next-state surrogate of the v05 **model output**, scored by
skill-over-persistence with a climatology guard — **not** validated against real observations
(that is #163, deferred) and **not** "making Darwin differentiable" or "learning real biology".
