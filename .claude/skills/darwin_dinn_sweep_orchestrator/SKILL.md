---
name: darwin-dinn-sweep-orchestrator
description: >
  Orchestrate multi-config DINN parameter-recovery sweeps for ECCO-Darwin
  v05. Generates the BASE_ENV + per-arc + per-config OUTPUT_DIR pattern with
  STOP sentinel, resume logic, per-arc aggregation, and Wave chaining. Use
  when the user wants to run a sweep across env-var levers (PIC_ABS_W,
  POC_ABS_W, CHL1_W_EXTRA, AOI_W_*, NB23_N_EPOCHS, etc.), explore the loss
  landscape across a hyperparameter grid, do overnight parameter-recovery
  experiments, or set up a chained Wave 1 → Wave 2 → Wave N sequence.
  Triggers: "sweep", "overnight run", "parameter sweep", "lever sweep",
  "hyperparameter grid", "loss landscape", "multi-config training".
---

# DarwinDiff Sweep Orchestrator

Distills the v3.0 overnight pattern (Basin C refinement, Carroll-6 multi-AOI
parameter recovery) into a reusable template. Saves re-deriving the
orchestration structure every session.

## When to use

- Sweeping any env-var lever supported by `run_v3.0_joint_multi_aoi.py` or
  `run_v3.0_with_modis_pic.py`
- Running overnight while the laptop trains autonomously
- Chaining multiple Waves (e.g. Wave 1 covers lever response, Wave 2 covers
  orthogonal sensitivity, Wave 3 covers 2D grids)
- Re-running a partially-completed sweep (built-in resume logic)

## Pattern: anatomy of an overnight script

Canonical template: `scripts/overnight_v3.0_basinC_refine_v2.py`. Anatomy:

```python
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUNNER = HERE / "run_v3.0_with_modis_pic.py"  # or run_v3.0_joint_multi_aoi.py

STAMP = datetime.now().strftime("%Y%m%d_%H%M")
LOG_DIR = ROOT / "logs" / f"overnight_<arc_name>_{STAMP}"
OUTPUT_ROOT = Path(rf"D:\runs\bcr_{STAMP}")   # SHORT prefix; see MAX_PATH below

BASE_ENV = {  # config shared by every config in the sweep
    "AOIS": "eqpac,natlsubpolar,southernoceanpac",
    "AOI_ID_CHANNEL": "1",
    "DINN_HIDDEN_DIM": "32",
    "NB23_N_EPOCHS": "1500",
    # ... full Basin C base
}

ARC_DEFS: list[tuple[str, list[tuple[str, dict]]]] = [
    ("Arc 1 -- PIC dose-response", [
        ("a1_pic_002", {"PIC_ABS_W": "0.02", "NB23_SEEDS": "0,1,...,9"}),
        ("a1_pic_005", {"PIC_ABS_W": "0.05", "NB23_SEEDS": "0,1,...,9"}),
        # ...
    ]),
    # ...
]
```

Then a `run_one(name, env_override)` wrapper invokes the runner via
subprocess. After each config, `aggregate_config(out_dir)` parses JSONs into
{n_at_6, n_at_5, n_at_4, iron_pair, mean_cal, per_param_cal}.

## Required env-var contract (Basin C / Carroll-6 defaults)

```
AOIS                          comma-list (default "eqpac,natlsubpolar")
AOI_ID_CHANNEL                "1" enables per-AOI identity channel
DINN_HIDDEN_DIM               16 / 32 / 64 / 128
NB23_N_EPOCHS                 1500 default; 3000 for slow-tracer probe
NB23_SEEDS                    comma-list, batched via torch.compile
POC_SUB_W                     POC z-score weight (default 3.0; Basin C 0.5)
GEOTRACES_POC_SUB_W           GEOTRACES POC weight (default 0.0)
AOI_W_<KEY>                   per-AOI loss weight (default 1.0)
CHL1_W_EXTRA                  extra diatom-chl weight (Basin C 3.0)
POSI_W                        positivity loss (Basin C 1.0)
PIC_ABS_W                     absolute PIC anchor (Basin B lever)
POC_ABS_W                     absolute POC anchor (Basin B lever, paired)
F_CO2_ABS_W                   CO2 flux anchor (PR #62)
USE_MEHRBACH_K1K2             "1" enables Mehrbach carbonate alignment
CONSISTENCY_LAMBDA            multi-AOI consistency penalty
PER_AOI_DINN                  "1" enables per-AOI parameter MLP
MLD_CHANNEL                   "1" adds MLD env channel
OUTPUT_DIR                    where JSONs land (REQUIRED for sweeps)
```

## STOP sentinel

```bash
touch logs/<log_dir>/STOP
```

`run_one` checks `stop_path.exists()` at every config boundary. Current
config in flight completes; rest skip. The chain trigger
(`not stop_path.exists()`) blocks Wave 2 launch.

## Resume logic

```python
existing = list(config_out_dir.glob("*.json"))
expected_seeds = env_override.get("NB23_SEEDS", "0").count(",") + 1
if len(existing) >= expected_seeds:
    return SKIPPED_RESUME
```

To resume: `rm STOP`, re-run the script. Already-completed configs skip;
incomplete configs re-run from scratch.

## Per-arc aggregation

After every config:

```python
agg = aggregate_config(OUTPUT_ROOT / name)
# {n_seeds, n_at_6, n_at_5, n_at_4, mean_cal, total_excellents,
#  iron_pair_joint, per_param_cal}
```

Headline metrics for the Carroll-6 framework:
- `n_at_6` — full recovery (rare; the 5/6 ceiling is the structural mutex)
- `n_at_5` — methodological success
- `iron_pair_joint` — both alpfe AND scav_rat Cal+ (the historically hard pair)
- `mean_cal` — average params recovered across seeds

## Wave chaining

```python
CHAIN_NEXT_WAVE = True
NEXT_WAVE_SCRIPT = HERE / "overnight_v3.0_basinC_wave2.py"

if CHAIN_NEXT_WAVE and not stop_path.exists() and NEXT_WAVE_SCRIPT.is_file():
    subprocess.run([sys.executable, str(NEXT_WAVE_SCRIPT)], ...)
```

Each Wave is its own orchestrator script with its own STAMP / OUTPUT_ROOT.
A Wave can chain to another Wave on completion (gated by STOP absence).

## Gotchas + community-painful lessons

- **Windows MAX_PATH=260.** Lever tags accumulate in JSON filenames
  (`run_v3.0_joint_<aoi_tag>_seed{S}_..._picabsW{...}_pocabsW{...}_posiW{...}.json`).
  Combined with a long OUTPUT_DIR prefix this can exceed 260 chars and crash
  JSON write AFTER training succeeds. Use short prefix: `D:\runs\bcr_<stamp>\`
  (28 chars saved vs `D:\runs\v3.0_basinC_refine_<stamp>\`).
- **Crash recovery from logs.** When MAX_PATH (or any post-training error)
  kills JSON write, the per-seed recovery values ARE in the `.log` file.
  Use `scripts/recover_failed_config_log.py` to reconstruct minimal JSONs
  compatible with downstream aggregation.
- **Laptop sleep on Windows** suspends the Python background process. For
  unattended overnight runs:
  `powercfg /change standby-timeout-ac 0` (AC: never sleep).
- **Multi-process CUDA on Windows is broken** for our stack. Don't use
  multiprocessing.Pool for parallel configs; serial subprocess.run works.
- **torch.compile amortizes JIT across seeds.** A batch of 10 seeds takes
  ~7 min vs ~7 min × 10 = 70 min if sequential. Always batch seeds.
- **First config of an arc is slow** because of torch.compile warmup
  (~120s extra). Plan timeouts with this in mind (`TIMEOUT_PER_RUN = 1800`).

## Reference files

- `scripts/overnight_v3.0_basinC_refine.py` — Wave 1 canonical (33 configs)
- `scripts/overnight_v3.0_basinC_refine_v2.py` — Wave 1 with MAX_PATH fix +
  resume logic (current canonical)
- `scripts/overnight_v3.0_basinC_wave2.py` — Wave 2 chained example
- `scripts/recover_failed_config_log.py` — crash-recovery utility
- `scripts/analyze_basinC_refine.py` — post-sweep aggregation + figures

## Cross-references

- `darwin_v05_loader` skill — for AOI definitions + IC cache build
- `carroll6_parameter_scoring` skill (if built) — for the Cal-grade /
  Excellent / iron-pair / basin diagnosis framework
