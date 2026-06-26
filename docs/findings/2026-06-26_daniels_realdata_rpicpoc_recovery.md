# First real-data-anchored R_PICPOC recovery (Daniels CP:PP, H200, n=10, verified)

**Date:** 2026-06-26 · **Spine:** D (#143) · **Status:** VERIFIED (`scripts/verify_run.py
--expect-seeds 10` → exit 0). Run `/projects/schultz/qi.zim/runs/daniels_recovery_n10`.

## What ran

4-AOI joint fit (eqpac / natlsubpolar / southernoceanpac / npsg), n=10 seeds, 2000 epochs,
H200. Operating point: **`DANIELS_RPICPOC_W=1.0`** (the real Daniels 2018 CP:PP anchor, PR
#146) + ironboost iron terms (`GEOTRACES_W=3`, `GEOTRACES_SUB_W=10`). Crucially R_PICPOC is
graded against **real calcite-production observations, not Darwin's own PIC** — this breaks
the circularity that made every prior R_PICPOC "recovery" self-referential.

## Result (canonical metric: per-AOI ≥2-AOI co-recovery, n=10)

| param | ≥2-AOI co-rec | per-AOI Cal tally (eqpac/natl/SO/npsg) |
|---|---|---|
| **R_PICPOC** | **10/10** | 9 / 10 / 5 / 10 |
| scav_rat | 9/10 | 9 / 9 / 1 / 9 |
| Smallgrow | 9/10 | 9 / 9 / 9 / 10 |
| Biggrow | 9/10 | 9 / 8 / 8 / 9 |
| alpfe | 1/10 | 1 / 1 / 1 / 1 |
| diatomgraz | 1/10 | 1 / 1 / 0 / 1 |

R_PICPOC per-AOI **mean recovered**: eqpac 0.0516, natl 0.0509, SO 0.0604, npsg 0.0482 (vs
Carroll 0.0425). Cal-grade and slightly above Carroll's low global constant — consistent with
`2026-06-26_rainratio_real_vs_darwin.md` (the real rain ratio runs a touch higher than 0.0425).

`verify_run.py`: mean_cal 3.9, ≥4/6 in 9/10 seeds, **6/6 = 0/10**, iron_pair_joint 0/10.

## Honest scope

This is the first **real-data-anchored** R_PICPOC recovery — NOT a 6/6 claim. The minimal
config (Daniels + ironboost only) co-recovers R_PICPOC + scav_rat + the growth pair but
**drops alpfe and diatomgraz** (1/10 each): up-weighting the real-iron *magnitude* term pushes
alpfe high/inconsistent, and there is no Eppley/POSi lever here for diatomgraz. Holding the
iron *pair* AND diatomgraz AND the real R_PICPOC anchor together needs the full v3.2 operating
point (Eppley + dense POSi) layered on — the next config. The durable, defensible claim is
narrow and real: **real CP:PP data recovers R_PICPOC (≥2-AOI in 10/10 seeds), breaking the
circularity**, with the recovered value Cal-grade vs Carroll.

## Pending

n=50 ensemble (job 7886431, same operating point) for a Wilson CI on the R_PICPOC rate
(10/10 at n=10 → 95% Wilson CI [0.72, 1.0]; n=50 tightens it). Aggregator:
`scripts/aggregate_daniels_recovery.py`.
