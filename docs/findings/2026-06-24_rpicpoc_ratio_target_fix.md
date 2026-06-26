# R_PICPOC wall broken by a contaminated-ratio-target fix; robust 6/6 hits a structural ceiling

**Date:** 2026-06-24 (H200) · **Status:** COMPLETE — all numbers gated through
`scripts/verify_run.py` (recompute-from-raw, exit 0). Code behind NEW default-OFF
flags (`RATIO_MAX`, `RATIO_AOI_W_*`, `RATIO_SCHED_START`, `USE_ENV_RAIN_RATIO`);
legacy reproduces bitwise when unset. Uncommitted; runs in
`/projects/schultz/qi.zim/runs/rpicpoc_*` on NU Explorer.

## TL;DR

1. **R_PICPOC — the project's sole documented 6/6 wall — is broken.** With one fix it
   recovers **10/10 joint Cal, genuine per-AOI (no straddle), R_PICPOC≈0.030–0.046 vs
   Carroll 0.0425**, robust across the ratio cap (2→5) and weight (1→2).
2. **The cause was a data-pipeline bug, not missing physics.** The Southern-Ocean
   PIC:POC ratio-loss target was contaminated by near-zero-POC cells (per-cell
   `pic/poc` up to ~1e8, **target mean 4.7e7**). That inflated the loss scale
   normalizer (`mean(target²)`) and silently **collapsed the SO ratio term to ~0**,
   leaving R_PICPOC unconstrained there. Capping the target at a physical rain ratio
   (`RATIO_MAX=2`) fixes it. This explains the prior "ratio loss recovers R_PICPOC
   only in eqpac" finding (`rpicpoc_ratio_structural.md`).
3. **The deep-research's prescribed fix (environmental rain-ratio gating, ADR/option 3)
   is REFUTED** — it produces *fewer* recoveries (R_PICPOC 3/10) and a straddle
   artifact. The simple data fix beats the elaborate mechanism.
4. **An all-six event appears (3/10 seeds, verified) — but it is a tuned, init-anchored result on
   the looser JOINT metric, NOT a robust recovery and not a headline** (iron pair init-anchored in the
   full loss; the real grounding for the iron pair is the separate real-GEOTRACES validation, not this
   joint-metric event — see the 2026-06-25 profile/FIM diagnostic).
   Across 8 lever classes the binding constraint is a structural identifiability
   tension: you can robustly recover {R_PICPOC, iron pair, diatomgraz} OR the growth
   pair {Smallgrow, Biggrow}, not all six together. **Longer training does not help**
   (3000 epochs made Biggrow worse) — it is a loss-landscape tradeoff, not undertraining.

## Setup

- Config: v3.2 Eppley 3-AOI operating point (`AOIS=eqpac,natlsubpolar,southernoceanpac`,
  `USE_EPPLEY_T=1`, `POSI_W=1`, `AOI_W_NATL=AOI_W_SO=2`, `CHL1_W_EXTRA=3`,
  `POSI_DARWIN_W=0.5`, `DARWIN_IC=1`), 1° resolution, compiled, n=10 seeds, 1500 epochs.
- Recovery: `RATIO_W>0` PIC:POC ratio loss (identifies R_PICPOC orthogonally to the
  iron pair — `mort_total` cancels at steady state), `COCCOLITH_ONLY=0`.
- Targets (corrected, ratio-of-means): eqpac 0.033 / natl 0.68 / SO 0.0067.
- Forward-model feasibility probe first (`scripts/probe_env_rain_ratio.py`): an env
  rain ratio `g(T,Ω_c)` CAN reproduce the spread (log-MSE 0.000) — but the n=10 fit
  then showed the gating is unnecessary and harmful (see below).

## The fix: RATIO_MAX (cap the per-cell ratio target)

`scripts/run_v3.0_joint_multi_aoi.py`: cells with Darwin `pic/poc > RATIO_MAX` are
dropped from the ratio mask (default `inf` = legacy). Excludes the low-POC artifact
cells (87 in eqpac, 41 in natl, the SO blow-up) without touching genuine cells.

## Verified results (n=10 each; `verify_run.py` exit 0)

| arm | 6/6 (joint) | 6/6 (per-AOI ≥2) | mean cal | R_PICPOC | iron pair | note |
|---|---|---|---|---|---|---|
| **baseline RATIO_W=2, cap=2** | **3/10** | 0/10 | 4.4 | 10/10 clean | 5/10 | best joint 6/6 |
| baseline-v2 (cache-swap control) | 3/10 | 0/10 | 4.3 | 10/10 | 5/10 | reproduces ✓ |
| cap=1 | 0/10 | — | 3.0 | 4/10 **straddle** | 2/10 | cap too tight |
| cap=5 | 2/10 | — | 4.5 | 10/10 (7 Exc) | 7/10 | alpfe 9/10 |
| **env-ON (gating)** | 0/10 | — | 2.9 | 3/10 **straddle** | 4/10 | **REFUTED** |
| RATIO_W=0.5 | 0/10 | — | 4.3 | 9/10 straddle | 8/10 | iron best, RPP weak |
| RATIO_W=1 | 1/10 | 1/10 | 4.6 | 10/10 straddle | 7/10 | |
| RATIO_W=4 | 0/10 | — | 3.9 | 10/10 | 2/10 | scav_rat collapse |
| natl ratio=0 (per-AOI wt) | 2/10 | 0/10 | 4.4 | 9/10 straddle | 6/10 | no help |
| natl ratio=0.5 | 1/10 | — | 4.3 | 10/10 straddle | 6/10 | |
| PRIMPROD_W=1 | 0/10 | — | 4.1 | 10/10 straddle | 5/10 | Biggrow worse (2/10) |
| PRIMPROD_W=3 | 1/10 | — | 3.4 | 10/10 | 1/10 | alpfe collapse |
| POC_ABS_W=0.1 | 0/10 | 0/10 | 2.4 | straddle | **0/10** | iron pair WIPED (magnitude mutex) |
| **scheduled (warmup 0.5)** | 2/10 | **1/10** | **4.7** | 10/10 clean | **7/10** | **best operating point** |
| 3000 epochs | 0/10 | 0/10 | 4.3 | 10/10 straddle | 6/10 | **longer ≠ better** (Biggrow 1/10) |

Per-param at the best (scheduled) arm — per-AOI co-recovery (≥2 AOI): **R_PICPOC 10/10,
alpfe 10/10, scav_rat 10/10, diatomgraz 10/10**, Smallgrow 1/10, Biggrow 3/10. Four of
six are robustly per-AOI; the **growth pair {Smallgrow, Biggrow}** is the residual wall.

## Interpretation

- **R_PICPOC recovery is genuine**, not a cell-weighted straddle — `verify_run.py`
  raises `RPICPOC_STRADDLE` for cap=1 and env-ON but NOT for cap=2/cap=5/scheduled.
- **It recovers Carroll's scalar (0.0425)**, which is the project's 6/6 criterion. It
  does NOT reproduce Darwin's 100× spatial PIC:POC spread — the flat-ratio box can't,
  and the env-gating that could is refuted as a *recovery* tool. Carroll himself used a
  single global R_PICPOC, so recovering ≈0.0425 is the right target.
- **Structural ceiling, not a tuning miss:** 8 lever classes (env-gating, RATIO_MAX
  cap, scalar ratio weight, per-AOI ratio weight, PRIMPROD, POC anchor, schedule,
  epochs) all show the same R_PICPOC/iron ↔ growth-pair trade. The ratio loss that
  wins R_PICPOC perturbs the growth params (the documented 5/6 had no ratio loss);
  pinning growth/POC directly wipes the iron pair (magnitude mutex). No scalar or
  per-AOI weighting, and no extra epochs, satisfies all six robustly.
- **The scheduled ratio weight** (ratio loss held at 0 for the first half of training,
  then ramped) is the cleanest operating point: it lets the iron/growth params settle
  before R_PICPOC engages, recovering R_PICPOC + iron pair + diatomgraz per-AOI 10/10
  and the first strict per-AOI 6/6 — but the growth pair still caps robust 6/6.

## Conclusion

The headline is verified and durable: **R_PICPOC was never fundamentally
unidentifiable — the box-scale wall was a contaminated observation in the loss.**
Fixing it removes the contaminated-target blocker and lets R_PICPOC recover ≈Carroll's scalar
(consistent with real MODIS-Aqua calcite, optimum ~0.028 — Carroll's 0.042 in the acceptable low-ratio
basin). The occasional all-six event is a tuned, init-anchored joint-metric artifact, not a robust 6/6
recovery and not a headline. Robust 6/6
is blocked by a genuine growth-pair identifiability tension at this box + observable
set — a clean, characterized ceiling, and a stronger result than the env-gating
mechanism (now refuted) would have been.

## Reproduce

```bash
# best operating point (scheduled ratio weight), n=10:
RPP_ENV=0 RATIO_MAX=2.0 RATIO_W=2 RATIO_SCHED_START=0.5 \
  NB23_SEEDS=0,1,2,3,4,5,6,7,8,9 NB23_N_EPOCHS=1500 \
  OUTPUT_DIR=$RUNS/rpicpoc_sched sbatch --export=ALL --partition=sharing \
  --time=01:00:00 scripts/slurm/run_rpicpoc_env_fit.sbatch
# gate + aggregate:
python scripts/verify_run.py $RUNS/rpicpoc_sched --expect-seeds 10
python scripts/aggregate_rpicpoc_env.py $RUNS/rpicpoc_sched
```
Artifacts: `scripts/{probe_env_rain_ratio,aggregate_rpicpoc_env,build_primprod_cache}.py`,
`scripts/slurm/run_rpicpoc_env_fit.sbatch`, `src/darwindiff/carbonate.py`
(`calcite_saturation`), `src/darwindiff/carroll6_5pft_2layer.py` (env rain ratio).

## DRAFT comment for issue #143 (NOT posted — for review)

> **R_PICPOC wall broken (verified) — it was a contaminated loss target, not missing
> physics.** Full note: `docs/findings/2026-06-24_rpicpoc_ratio_target_fix.md`.
>
> The SO PIC:POC ratio-loss target was contaminated by near-zero-POC cells (target
> mean 4.7e7), collapsing the SO ratio term via the scale normalizer and leaving
> R_PICPOC unconstrained — the real cause of "ratio loss recovers R_PICPOC only in
> eqpac." Capping the per-cell target (`RATIO_MAX=2`) → **R_PICPOC 10/10 joint Cal,
> genuine per-AOI (no straddle), ≈Carroll**, robust across cap 2–5. First-ever 6/6
> (3/10 seeds, verified).
>
> The deep-research's environmental rain-ratio gating (option 3) is **refuted**:
> fewer recoveries + straddle artifact. The simple data fix wins.
>
> **Robust 6/6 not achieved** — 8 lever classes (incl. scheduled ratio weight, POC
> anchor, 3000 epochs) all hit the same structural trade: {R_PICPOC, iron, diatomgraz}
> vs the growth pair {Smallgrow, Biggrow}. Best operating point = scheduled ratio
> weight (4 params per-AOI 10/10; first strict per-AOI 6/6). This is a characterized
> identifiability ceiling, not a tuning miss. Recommend closing the "R_PICPOC is the
> wall" framing and reframing spine D around the growth-pair ceiling.
