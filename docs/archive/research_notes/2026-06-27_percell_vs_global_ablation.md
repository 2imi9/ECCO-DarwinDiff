# Per-cell-vs-global-scalar ablation: per-cell IS load-bearing for the target params

**Date:** 2026-06-27 · **Status:** verified (n=10/arm, cluster, identical geo1 config) ·
**Answers:** the manuscript reviewer-panel's #2 attack ("per-cell load-bearing is a
non-sequitur"), issue #116, #19.

## Setup
Identical geo1 config (3-AOI eqpac/natl/SO, `GEOTRACES_W=1`, real Daniels CP:PP R_PICPOC
anchor, Eppley, n=10 seeds, 2000 epochs). **Only the parameter source differs:**
- **PER-CELL** — the per-cell DINN (1×1 convs; each cell its own Carroll-6 vector). Source:
  the canonical `geo1_dan1` run.
- **GLOBAL-SCALAR** — one global Carroll-6 vector per seed (`GlobalScalarNet`), broadcast to
  every cell/AOI; the differentiable analogue of a single Green's-functions optimum.
  (Cluster job 7907450, t4, verified end-to-end.)

## Result — per-parameter Cal-grade+ over 10 seeds
| param | per-cell | global-scalar |
|---|---|---|
| `alpfe` | 10 | 10 |
| `scav_rat` | **8** | **0** |
| `Smallgrow` | 1 | 10 |
| `Biggrow` | 4 | 10 |
| `diatomgraz` | 1 | 10 |
| `R_PICPOC` | **9** | **0** |
| **{alpfe, scav_rat, R_PICPOC} JOINT** | **7/10** | **0/10** |
| mean n_cal/6 | 3.30 | 4.00 |
| mean loss_final | 42.9 | 65.1 |

## Verdict
**Per-cell is decisively load-bearing for the parameters the study targets.** On the
{`alpfe`, `scav_rat`, `R_PICPOC`} joint it is **7/10 vs 0/10**; specifically `scav_rat`
(8 vs 0) and `R_PICPOC` (9 vs 0) *require* the per-cell predictor — a single global vector
cannot match the spatially-varying **absolute anchors** (GEOTRACES dissolved iron, Daniels
calcite). E.g. global `R_PICPOC` drifts to 0.092 (2.2× Carroll); global `scav_rat` lands 41%
off. `alpfe` is recovered by both (10/10). The separations are clean at n=10 (Fisher exact
p < 0.01 for each of `scav_rat`, `R_PICPOC`, and the joint). **This answers the panel's #2
attack with data: per-cell load-bearing is not a non-sequitur — it is real, for the target trio.**

## The nuance (honest — and itself the identifiability thesis confirmed)
Per-cell is **not uniformly better**. The global-scalar recovers the growth/grazing params
(`Smallgrow`, `Biggrow`, `diatomgraz`) within the (generous, ~40% rel) Cal-grade band at
10/10, where per-cell drifts them out (1, 4, 1). Mechanism: per-cell flexibility lets each
cell's growth rate **overfit** — the same equifinality the synthetic demo shows
([[2026-06-27_synthetic_equifinality_demo]]) — while the global scalar's single-value
rigidity **regularizes** them toward the global Carroll value. So the global arm's higher
mean n_cal (4.00 > 3.30) is **misleading**: it counts loose growth-param "recoveries" that
are *not* the study's target (the growth pair is unobservable by construction from real
data). On the trio that matters, global = 0/10.

This is the project's central claim, confirmed on **real** ECCO-Darwin data:
**identifiability is parameter-specific**; the per-cell predictor is load-bearing precisely
for the anchor-constrained params and a liability (equifinality) for the under-anchored ones.

## Caveats
- n=10. The extreme separations (scav_rat 8/0, R_PICPOC 9/0) are robust; the growth-param
  recoveries sit inside a generous ~40% band, so read them as "near Carroll," not exact.
- Per-cell arm = `geo1_dan1` (canonical, `verify_run.py`-gated). A fresh identical-config
  re-run (`abl_percell`, job 7907598) was queued to cross-confirm.
- GPU note: the global arm ran on **t4 (CC 7.5)**; the cluster torch (cu128) has **no kernels
  for V100 (CC 7.0)** — a real gotcha for future cluster jobs.

## Reproduce
`GlobalScalarNet` (`src/darwindiff/networks.py`) + `GLOBAL_SCALAR=1`; the geo1 env; then
`aggregate_ablation.py` over `abl_global` vs `geo1_dan1`.
