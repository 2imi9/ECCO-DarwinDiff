# First real-data-anchored R_PICPOC recovery (Daniels CP:PP, H200, n=10, verified)

**Date:** 2026-06-26 · **Spine:** D (#143) · **Status:** VERIFIED (`scripts/verify_run.py
--expect-seeds 10` → exit 0). Run `/projects/schultz/qi.zim/runs/daniels_recovery_n10`.

## What ran

4-AOI joint fit (eqpac / natlsubpolar / southernoceanpac / npsg), n=10 seeds, 2000 epochs,
H200. Operating point: **`DANIELS_RPICPOC_W=1.0`** (the real Daniels 2018 CP:PP anchor, PR
#146) + ironboost iron terms (`GEOTRACES_W=3`, `GEOTRACES_SUB_W=10`). Crucially R_PICPOC is
graded against **real calcite-production observations, not Darwin's own PIC** — this breaks
the circularity that made every prior R_PICPOC "recovery" self-referential.

## Result (canonical metric: per-AOI ≥2-AOI co-recovery, n=50)

| param | ≥2-AOI co-rec | per-AOI Cal tally (eqpac/natl/SO/npsg) |
|---|---|---|
Verified at **n=50** (B.3 n=10 + B.4 n=40 ensemble; `verify_run.py --expect-seeds 50` → exit 0).
The metric is per-AOI ≥2-AOI co-recovery; the Wilson 95% CI makes each rate referee-proof.

| param | ≥2-AOI co-rec (n=50) | Wilson 95% CI | per-AOI Cal tally (eqpac/natl/SO/npsg) |
|---|---|---|---|
| **R_PICPOC** | **50/50** | **[0.93, 1.00]** | 49 / 50 / 15 / 50 |
| scav_rat | 49/50 | [0.90, 1.00] | 49 / 49 / 5 / 49 |
| Smallgrow | 49/50 | [0.90, 1.00] | — |
| Biggrow | 43/50 | [0.74, 0.93] | — |
| alpfe | 4/50 | [0.03, 0.19] | 4 / 4 / 4 / 4 |
| diatomgraz | 1/50 | [0.00, 0.10] | — |

R_PICPOC per-AOI **mean recovered** (n=50): eqpac 0.0502, natl 0.0520, SO 0.0619, npsg 0.0487 (vs
Carroll 0.0425). Cal-grade and slightly above Carroll's low global constant — consistent with
`2026-06-26_rainratio_real_vs_darwin.md` (the real rain ratio runs a touch higher than 0.0425).

`verify_run.py` (n=50): mean_cal 3.9, ≥4/6 in 42/50 seeds, **6/6 = 0/50**, 5/6 = 3/50,
iron_pair_joint 3/50. The tight alpfe [0.03,0.19] + diatomgraz [0.00,0.10] CIs confirm these are
genuinely NOT recovered in this config (not seed noise).

## Honest scope

This is the first **real-data-anchored** R_PICPOC recovery — NOT a 6/6 claim. The minimal
config (Daniels + ironboost only) co-recovers R_PICPOC + scav_rat + the growth pair but
**drops alpfe and diatomgraz** (1/10 each): up-weighting the real-iron *magnitude* term pushes
alpfe high/inconsistent, and there is no Eppley/POSi lever here for diatomgraz. Holding the
iron *pair* AND diatomgraz AND the real R_PICPOC anchor together needs the full v3.2 operating
point (Eppley + dense POSi) layered on — the next config. The durable, defensible claim is
narrow and real: **real CP:PP data recovers R_PICPOC (≥2-AOI in 10/10 seeds), breaking the
circularity**, with the recovered value Cal-grade vs Carroll.

## Next

The n=50 Wilson CIs above are done (B.4). The next config is the **full v3.2 operating point
(Eppley + dense POSi) layered on the Daniels anchor** — to test whether the iron pair (alpfe)
and diatomgraz can be held *simultaneously* with the real R_PICPOC recovery, rather than traded
away as in this minimal config. Aggregator: `scripts/aggregate_daniels_recovery.py`.
