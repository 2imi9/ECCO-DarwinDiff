# Pre-registration: are the FLAGSHIP headline numbers window-contingent?

**Date:** 2026-07-31 · **Written with zero flagship-window JSONs on disk** · **Status:** pending

The window swap retracted the depth result. This asks the question that actually matters for the
manuscript: **does the same problem reach the flagship's published counts?**

## A correction that narrows the worry

The 2026-07-31 depth arms ran `DARWIN_IC=0`, which gives a basin-uniform initial state, and I wrote
in the runner that `DARWIN_IC` "defaults off". **That was wrong.** It defaults to **1**
(`run_v3.0_joint_multi_aoi.py:303`). The flagship uses per-basin Darwin initial conditions and is
**not** basin-blind. Corrected in the source.

Measured from the committed IC caches:

| AOI | `FeT_L2` IC | `POC_L2` | L2 decay rate /d | tau | box @200 steps | observed | crossing step |
|---|---|---|---|---|---|---|---|
| eqpac | 0.5353 nM | 0.339 | 0.01767 | 57 d | 0.2269 nM | 0.4404 | **45** |
| natlsubpolar | 0.7544 nM | 0.153 | 0.00797 | 125 d | 0.5096 nM | 0.5638 | **148** |
| southernoceanpac | 0.5393 nM | 0.630 | 0.03278 | 31 d | 0.1125 nM | 0.2245 | **110** |

Two things follow. The decay rate differs **~4x** across basins because `POC_L2` does, so the
flagship has genuine per-basin structure the depth arms lacked. But every basin is still mid-decay
at 200 steps, and all three sit **below** their observation there, so the residual has the **same
sign everywhere** rather than straddling.

## Which parameters are at risk, derived before running

A parameter can only be window-contingent if **its own anchor observable** has not converged. Measured
by integrating the box to 3200 steps:

| observable | anchors | % converged at 200 steps |
|---|---|---|
| `DFe_1` surface | **alpfe** | **100.1%** |
| PIC/POC | **R_PICPOC** | **100.0%** (0.04245 at 100, 200, 400, 800, 1600 — flat) |
| `DFe_2` subsurface | **scav_rat** | **47.5%** |

**Prediction: `alpfe` and `R_PICPOC` are window-insensitive; only `scav_rat` moves.**

This already has two independent confirmations from data on disk: `alpfe` in `eq_surf` went 49/50 at
200 steps to 50/50 at 100 (insensitive, as predicted), and `eq_sub` `scav_rat` went 6 → 23 → 0 across
400/200/100 (contingent, as predicted). `R_PICPOC` has **never** been tested across windows and is
the open leg.

## Arms

Flagship `geo1` config, unchanged: `GEOTRACES_W=1, DANIELS_RPICPOC_W=1, NB23_PINN_WEIGHT=3,
POC_SUB_W=3, CHL1_W_EXTRA=3, DARWIN_PATTERN_W=1`, 3 AOIs, 2000 epochs, `DARWIN_IC=1` (the default,
explicitly set so it is in the artifact). 50 seeds per arm.

| arm | window | purpose |
|---|---|---|
| `fs_w100` | 100 | shorter; natl and sopac have not yet crossed their observation |
| `fs_w200` | 200 | **re-run of the published flagship**, doubles as the runner no-op control |
| `fs_w400` | 400 | longer; all basins further past their crossing |
| `fs_null_w100/200/400` | each | untrained nulls, re-measured per window, never reused |

## Decision rule, fixed now

Per-AOI ≥2-of-3 Cal-grade, n=50, gated on `verify_run` exit 0. One threshold, **P < 0.01**, both
tails, Fisher exact.

- **HEADLINES SAFE** if `alpfe` and `R_PICPOC` each stay within **5/50** of their published counts
  (49/50 and 50/50) at **every** window, while `scav_rat` moves by **≥10/50** between at least two
  windows.
- **HEADLINES CONTINGENT** if `alpfe` or `R_PICPOC` moves by ≥10/50 across windows. This would mean
  the convergence rule is wrong and the whole result set needs a window statement.
- **INCONCLUSIVE** if nothing moves, including `scav_rat`. That would mean the flagship's richer loss
  (surface iron + Daniels + pattern + PINN) stabilises `scav_rat` against the window, which is a real
  and reportable outcome and would partially rehabilitate the flagship count.

**Falsifier for a broken run:** `fs_w200` must reproduce the published flagship within seed noise
(`alpfe` 49/50, `scav_rat` 25/50, `R_PICPOC` 50/50). If it does not, the runner or environment has
drifted and no window conclusion may be drawn.

## Committed interpretations

- **`scav_rat` moves, others hold.** The publishable framing becomes: two of four observables are
  anchored on converged quantities and are robust; `scav_rat` is anchored on a transient and its
  count must be quoted with its window. `alpfe` and `R_PICPOC` survive intact.
- **`alpfe` or `R_PICPOC` moves too.** Far more serious. Every published count needs re-deriving at a
  justified window before anything goes in a manuscript.
- **Nothing moves.** The flagship's multi-term loss is doing work the single-channel ablations could
  not, and the depth-arm sensitivity was an artifact of stripping the loss down to one transient
  channel. `scav_rat` 25/50 stands.

## Recorded before the fact

- The bitwise no-op control **failed** earlier today (1.7% on identical config) and its first version
  compared zero values. `fs_w200` is the honest re-test: it re-runs the published configuration and is
  compared on `joint_recovered`, the field the artifacts actually store.
- Untrained nulls are re-measured at every window. The untrained distribution moves with integration
  length; reusing one would manufacture an effect.
- `diatomgraz` is graded but not interpreted: its untrained null is a knife edge (prior midpoint sits
  2.8% of the box width inside the Cal band), so no window claim will be made about it.
