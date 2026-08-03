# The flagship window sweep, relaunched — and why the first one could not have worked

**Date:** 2026-08-02 · **Status:** running (job 255511) · **Supersedes:** job 244487, invalid
**Pre-registration:** `docs/findings/2026-07-31_prereg_flagship_window_sweep.md` (unchanged)

## The first run was invalid, and the diagnosis is confirmed from the artifact

Job 244487's `fs_w200` arm was the pre-registration's falsifier: it re-runs the published flagship
and must reproduce `alpfe` 49/50, `scav_rat` 25/50, `R_PICPOC` 50/50. It returned:

| param | published | job 244487 | |
|---|---|---|---|
| `alpfe` | 49/50 | **50/50** | within seed noise |
| `scav_rat` | 25/50 | **3/50** | **falsifier fired** |

Read back out of the artifact rather than inferred, the cause is exactly the three values the
reproducibility appendix omits:

```
posi_w       = 0.0    (flagship: 1)
use_eppley_t = False  (flagship: 1)
aoi_weights  = {eqpac: 1.0, natlsubpolar: 1.0, southernoceanpac: 1.0}   (flagship: {1, 2, 2})
```

No window conclusion may be drawn from job 244487. Its artifacts are kept at
`/scratch/qi_zim_neu/flagwin/` as evidence; the relaunch writes to `flagwin2/` so nothing is
overwritten, and `grade_flagship_window_sweep.sbatch` now points at `flagwin2` so the invalid
arms can never be graded as flagship by accident.

## Why a warning banner did not prevent it

`scripts/configs/flagship_geo1.sh` was committed on 2026-07-29 precisely to stop this, and the
appendix carries a banner pointing at it. Both were in place. The trap was walked into anyway,
because the banner is prose and the sbatch was written by hand.

**And the config had never been deployed to the machine that runs the jobs.** Checked on
2026-08-02: `~/emulator_poc/scripts/configs/flagship_geo1.sh` did not exist on AICR at all. Even a
correctly-written sbatch that sourced it would have failed. The fix for a trap lived only in the
repository, while every flagship run executes from an unversioned checkout (issue #218) that is
not a git repository at all:

```
$ ssh aicr 'cd ~/emulator_poc && git rev-parse --short HEAD'
fatal: not a git repository
```

The runner there did match the branch HEAD exactly (`80d7c0a3…` = commit `9c67de2`), so nothing
cluster-side was lost by syncing — but that was luck, not a guarantee anyone could have checked.

## What now makes it impossible rather than discouraged

1. **The sbatch sources the config** instead of restating it, and overrides only `N_STEPS` and
   `NB23_LR`, the two variables the sweep actually varies.
2. **A run-time assertion** in the sbatch fails with exit 3 if `POSI_W`, `USE_EPPLEY_T`, the three
   per-AOI weights, `DANIELS_RPICPOC_W` or `RATIO_W` are not their flagship values, and if the
   config file, the Daniels anchor, the GEOTRACES file or any IC cache is missing. A misconfigured
   run now costs seconds instead of a 6-hour array and a session's conclusion.
3. **`tests/test_flagship_config_guard.py`**, three tests, each negative-controlled by injecting
   the real bug and confirming it fails:
   - the config still pins the values the appendix omits;
   - **every name the config exports is actually read** by something in `scripts/` or `src/`;
   - any sbatch that both trains and says "flagship" sources the config.
4. **`N_STEPS` is now recorded in every artifact.** It was not, so the three arms of a window
   sweep produced artifacts indistinguishable on the one variable the sweep varied. `dt_days` too.

## A dead-name bug in the canonical config, found by writing guard 3

`flagship_geo1.sh` exported `USE_MLD_CHANNEL=0` and `USE_AOI_ID_CHANNEL=0`. The runner reads
`MLD_CHANNEL` and `AOI_ID_CHANNEL` — `USE_*` are its *internal Python identifiers*, not its
environment variables. Nothing anywhere reads the `USE_*` spelling.

It was inert rather than wrong, because both values equal the runner's defaults. But the file's
own header promises that it sets defaults explicitly "so a future default change cannot silently
move the flagship" — and that guarantee did not exist for those two variables, inside the file
that makes the promise. Fixed, and guard 3 now enforces it for every exported name.

## Pre-registration status

Unchanged and still binding. Arms, seeds, decision rule and falsifier are as written on
2026-07-31. The relaunch is job **255511**, 30 tasks (6 arms x 5 chunks of 10 seeds).
