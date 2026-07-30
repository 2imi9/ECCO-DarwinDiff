# The published flagship recipe does not reproduce the flagship

**Date:** 2026-07-29 · **Issue:** #117 (reproducibility appendix) ·
**Fix:** `scripts/configs/flagship_geo1.sh`

## What was tested

Reproduce `n50e2k_percell_trio` locally from the recipe in
`2026-07-24_reproducibility_methods_appendix.md`, which gives the flagship as:

> `GEOTRACES_W=1, DANIELS_RPICPOC_W=1, PINN=3, POC_SUB_W=3, CHL1_W_EXTRA=3, DARWIN_PATTERN_W=1, 2000ep`

Run that, at n=10, 2000 epochs, three AOIs, against a genuine flagship artifact.

## Result: three levers are missing, and they are load-bearing

Diffing the run JSON against a verified flagship run JSON, config key by config key:

| lever | flagship | the published recipe |
|---|---|---|
| `POSI_W` | **1.0** | 0.0 (absent) |
| `USE_EPPLEY_T` | **True** | False (absent) |
| per-AOI weights | **{eqpac 1, natl 2, sopac 2}** | {1, 1, 1} (absent from the row) |

Everything else matched exactly. Adding only those three, with nothing else changed:

| param (per-AOI ≥2-of-3) | published recipe | **+ the three levers** | flagship (n=50) |
|---|---|---|---|
| `alpfe` | 10/10 | 10/10 | 49/50 |
| `scav_rat` | **0/10** | **8/10** | 25/50 |
| `R_PICPOC` | 10/10 | 10/10 | 50/50 |
| **trio** | **0/10** | **8/10** | 25/50 |

Both runs `verify_run.py` exit 0. `scav_rat` and the trio go from **0/10 to 8/10** on three
environment variables. A reader following the appendix would conclude the trio does not recover.

## Why the recipe looks complete but is not

The appendix is not simply wrong — it says, in the prose above the table:

> All sourced from `covar_env_common.sh` first (sets data roots + Eppley defaults) … default
> per-AOI weights {1,2,2}

So the AOI weights *are* documented, one paragraph above the row, and Eppley is delegated. The
problem is the delegation target:

**`covar_env_common.sh` is at `~/emulator_poc/covar_env_common.sh` on the AICR cluster and is not
in this repository.** `git ls-files` has no such file. A reader outside that account cannot obtain
it, cannot see that it sets `POSI_W=1`, and gets no error — the run simply trains without the bSi
term and reports a different answer.

This is the reproducibility appendix for the manuscript. Pointing it at a file only the authors
have is the single most load-bearing gap in it.

## The fix

`scripts/configs/flagship_geo1.sh` — every value read back out of a **verified flagship run
artifact**, not transcribed from prose. Values that merely equal the runner's current defaults are
set explicitly anyway, so a future default change cannot silently move the flagship.

```bash
source scripts/configs/flagship_geo1.sh
python scripts/run_v3.0_joint_multi_aoi.py
```

It also records what the appendix row does not: that `RATIO_W=0` is what keeps the `R_PICPOC`
result non-circular, and that `data/` is gitignored so a fresh checkout has no anchor data at all.

## Related failure found on the way

The first reproduction attempt declared `DANIELS_RPICPOC_W=1` with the PANGAEA file unstaged. The
anchor was skipped with a `[warn]`, the run trained anyway, and **`verify_run.py` passed it at exit
0** with `R_PICPOC` at 0.20–0.26× Carroll. `verify_run.py` now fails a run whose declared weight got
zero cells in every AOI — see `2026-07-29_inert_anchor_passes_the_gate.md`.

Both failures are the same shape: **the config a run declares is not checked against the config it
ran.** One is fixed in the gate, the other in a committed recipe.
