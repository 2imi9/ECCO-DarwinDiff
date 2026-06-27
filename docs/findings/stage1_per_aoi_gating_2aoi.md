# Stage 1 — Per-AOI parameter gating (2-AOI): preliminary result

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data/plans stand, framing corrected by [STATUS.md](../../STATUS.md). The project is a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC} — **not** a 6/6 chase or a '5/6 ceiling / parameter-conservation' result. The growth pair {Smallgrow, Biggrow} is unobservable by construction. **R_PICPOC is recoverable** at 1° with a real calcite anchor (Daniels/MODIS) + `RATIO_MAX=2` — the differentiable Darwin calcite port and native resolution were *tested and did not help*, so R_PICPOC is **not cluster-gated**. `geo1` holds {alpfe, scav_rat, R_PICPOC} jointly 8/10; diatomgraz is an open iron-pair tradeoff. The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, CV→1e-15), so box-vs-Darwin pattern-matching is not a fidelity metric.


**Status: PRELIMINARY (2-AOI, confounded). Not a publication claim until the
3-AOI confound check is run** (see "Confound" below).

## What was tested

The architectural attack on the v3.x 5/6 recovery ceiling: hard-route each
Carroll-6 parameter's *gradient* to only the AOI loss(es) that carry its signal
(`darwindiff.gating`, `GATING_POLICY=signal_2aoi`), inside a single shared DINN.
Forward parameter values are unchanged (straight-through mask); only the backward
pass is routed. Hypothesis: the ceiling is a shared-MLP compromise that
per-parameter gradient routing can break.

- **Config:** eqpac + natlsubpolar, shared DINN, Darwin IC, `POC_SUB_W=3.0`,
  20 seeds, 1500 epochs, eager. Gated vs ungated, matched (same seeds + config).
- **Routing (`signal_2aoi`):** eqpac -> {alpfe, scav_rat, Smallgrow, diatomgraz};
  natlsubpolar -> {Biggrow, R_PICPOC}.
- **Raw per-seed JSONs:** `D:/runs/gating_stage1/` (40 files, not tracked).

## Result: gating did NOT break the ceiling; it lowered recovery

| metric | ungated (control) | gated (`signal_2aoi`) |
|---|---|---|
| mean cal-grade | **2.95 / 6** | **1.65 / 6** |
| best seed | 4/6 | 3/6 |
| seeds >= 5/6 | 0 | 0 |

Per-param cal-grade rate:

| param | ungated | gated | delta |
|---|---|---|---|
| alpfe | 0% | 5% | +5pp |
| scav_rat | 80% | 30% | **-50pp** |
| Smallgrow | 90% | 75% | -15pp |
| Biggrow | 80% | 0% | **-80pp** |
| diatomgraz | 40% | 55% | +15pp |
| R_PICPOC | 5% | 0% | -5pp |

## Interpretation

Gating severs each parameter's cross-AOI gradient. The params that collapsed
(Biggrow -80pp, scav_rat -50pp, Smallgrow -15pp) are exactly those flagged in the
multi-AOI tradeoff finding as needing the multi-AOI cross-constraint. Only
diatomgraz improved (+15pp) — the one param that appears to want single-regime
isolation.

This is the *multi-AOI-is-load-bearing* result in reverse: the 5/6 ceiling is
**not** a shared-MLP compromise that routing fixes. The cross-regime coupling is
load-bearing, and removing it hurts. On this evidence the ceiling looks
**structural**, not an artifact of the shared per-cell network.

## Confound (why this is preliminary)

With no Southern Ocean regime in the 2-AOI setup, `scav_rat` was crammed into
eqpac and `Biggrow` was restricted to natlsubpolar — the two worst routings, and
the two biggest collapses. Part of their drop is the routing confound, not the
gating mechanism itself.

## Before this becomes a publication claim

Run the 3-AOI version (eqpac + natlsubpolar + southernoceanpac,
`GATING_POLICY=signal_3aoi`), which gives `scav_rat` its proper SO regime and
frees `Biggrow` from natl-only.

- **Prerequisite:** build the `southernoceanpac` IC cache
  (`build_darwin_ic_cache.py`); only the *target* cache exists today.
- **Expectation (~80-90%):** confirms the negative — gating still severs
  cross-AOI coupling in 3-AOI; the run removes the routing confound so the
  negative is airtight.
- **Cost:** ~5-6h (gated + ungated pair) at the eager box-model rate.

## Reproduce

```
AOIS=eqpac,natlsubpolar NB23_SEEDS=0,1,...,19 NB23_N_EPOCHS=1500 \
  DARWIN_IC=1 POC_SUB_W=3.0 TORCH_COMPILE_BATCHED=0 \
  GATING_POLICY={ungated|signal_2aoi} OUTPUT_DIR=D:/runs/gating_stage1 \
  python scripts/run_v3.0_joint_multi_aoi.py
```

`TORCH_COMPILE_BATCHED=0` is required: Triton is unavailable on the Windows
laptop, so `torch.compile` (the runner default) crashes with `TritonMissing`;
eager is the working path here.
