# R_PICPOC: the wall is calcite forward-model fidelity, not the estimator or information (box scale)

> **⚠ SUPERSEDED FRAMING (2026-06-27).** This is a point-in-time record; its data and negative results stand, but its framing is corrected by [STATUS.md](../../../STATUS.md) and `docs/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md`. Specifically: **R_PICPOC is NOT a "6/6 wall" and is NOT cluster-gated** — it recovers at 1° box scale given a *real* calcite anchor (Daniels CP:PP / MODIS PIC) plus the `RATIO_MAX=2` fix for the contaminated Southern-Ocean ratio target; the differentiable Darwin calcite port and native resolution were *tested and did not help*. The project is reframed as a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC}; the **growth pair {Smallgrow, Biggrow} is unobservable by construction** (excluded, not failed). The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, tracer CV→1e-15), so box-vs-Darwin spatial-pattern correlations are not fidelity metrics — identifiability comes from real absolute anchors.


**Date:** 2026-06-15 (night) · **Status:** COMPLETE. Ratio loss breaks the mutex in
eqpac (10/10, no iron collapse); exhaustive structural exclusion confirmed (25 arms,
0/10 co-recovery in ≥2 AOIs); the residual wall is calcite forward-model fidelity.
All code behind
NEW default-OFF flags (`RATIO_W`; reuses `COCCOLITH_ONLY`, `W_SINK_PIC`,
`GATING_POLICY`, `PER_AOI_DINN`). Uncommitted on `2imi9/schultz-jon-deck`. Does
**not** change the Tuesday deck.

## Question

Is R_PICPOC's box-scale non-recovery a **fundamental information limit** (needs the
cluster, as the talk frames it), or a **fixable design issue** (estimator / loss /
forward-model)? Tonight attacks the laptop-feasible structural axis, after an
adversarial code audit ruled out a time-mean *bug* (R_PICPOC's level is a provable
null-space degeneracy of the z-scored loss) and flagged two untested ideas: a
PIC:POC **ratio** loss and a **seasonal** fit.

## Result 1 — the PIC:POC ratio loss BREAKS the mutex (estimator side solved)

Every prior anchor used *separate* PIC and POC magnitudes, each of which pins
`mort_total` → the binary iron-pair mutex. But at steady state
`PIC_1/POC_1 = R_PICPOC·(W_SINK/W_SINK_PIC)` — **`mort_total` cancels**. A
forward-model orthogonality probe confirmed it exactly: scaling alpfe / scav_rat /
the growth params ×0.5–×2 leaves the ratio unchanged; `∂(ratio)/∂R_PICPOC ≈ 1`,
`∂(ratio)/∂(everything else) ≈ 1e-6`. So a per-cell ratio loss pins R_PICPOC
**orthogonally** to the iron pair.

Sweep (v3.2 Eppley config, n=10 paired, **scored per-AOI**):

| arm | eqpac R_PICPOC | natl | SO | R_PICPOC Cal ≥1 AOI | iron pair (natl+SO) | co-rec ≥2 AOI |
|---|---|---|---|---|---|---|
| c0 control (RATIO_W=0) | 0.046 | 0.17 | 0.21 | 3/10 | 9/10 | 0/10 |
| **r2 / r10** (cocco off) | **0.033–0.035 ✅** | 0.90 | 1.37 | **10/10** | **8/10** | 0/10 |
| r2c / r10c (cocco on) | 0.43 | 1.3 | 1.5 | 0/10 | **0/10** | 0/10 |

**The ratio loss recovers R_PICPOC in eqpac 10/10 WITHOUT collapsing the iron pair**
(8/10 survives) — the first lever ever to recover R_PICPOC and keep the iron pair.
So "R_PICPOC is informationally unidentifiable at the box scale" is **too strong**:
with the right observable it is identifiable per-cell, and the mutex is (on the
estimator side) a fixable design error — the separate-magnitude anchors were simply
the wrong observable.

## Result 2 — the remaining block is calcite FORWARD-MODEL FIDELITY (not estimator, info, or seasonality)

The ratio loss recovers R_PICPOC **only in eqpac**, because the box's calcite is a
*rigid* readout (`PIC_1/POC_1 = R_PICPOC` everywhere), while **Darwin's realized
PIC/POC ratio varies ~23×** (eqpac ~0.033 ≈ Carroll 0.0425; natl ~0.9, SO ~1.4 —
coccolithophore bloom zones). A single-`mort_total` box matches each AOI's realized
ratio by setting R_PICPOC = that local ratio → eqpac lands (realized ≈ production),
natl/SO don't. **Coccolith-only calcite** — the proposed cross-AOI fix — backfires:
R_PICPOC drifts high in all AOIs *and* the iron pair collapses to 0/10, because it
re-entangles calcite with large-eukaryote growth (the Lens-B caveat, confirmed).

So the wall is: **the box's simplified calcite cannot reproduce Darwin's
coccolithophore-driven spatial PIC/POC variation at a single R_PICPOC.** That is a
forward-model-fidelity gap, addressable only by richer calcite physics
(coccolithophore PFT dynamics, calcite production/dissolution/sinking,
temperature/Ω-saturation dependence) — i.e. the **differentiable Darwin port** —
plus **native resolution** to resolve the bloom regimes. Not the estimator. Not raw
compute for the *same* box.

## Result 3 — a 1° seasonal fit would NOT recover R_PICPOC (seasonal axis excluded)

The audit floated "seasonal-1°" as the cheap decisive test. A forward-model probe
(synthetic seasonal forcing, Eppley on) rules it out structurally:

- z-scored seasonal PIC cycle is **exactly invariant** to R_PICPOC's level
  (`max|Δ| = 0.000`) — seasonal *pattern* fitting is null-space-blind too;
- the box's seasonal PIC amplitude is ≈ 0 — Eppley is mean-neutralized and `LIGHT`
  is constant, so **the box has essentially no seasonal biology** to fit;
- organic (biomass) and calcite (`mort`) sources are **in phase**
  (`corr = 0.94`) — so even an *absolute* seasonal DIC/pCO₂ loss can't separate
  R_PICPOC from `mort_total`.

So seasonality helps R_PICPOC only via the richer carbonate physics Darwin has —
again the Darwin port / native resolution, not a 1° seasonal fit with this box.

## Overnight campaign — exhaustive structural confirmation (COMPLETE)

`%LOCALAPPDATA%\ddeck\alkabs\campaign_rpicpoc.py` → `D:\runs\rpicpoc_camp\`, 21 arms,
per-AOI scored. **Result: 0/10 co-recovery (R_PICPOC + iron pair Cal in ≥2 AOIs)
in every arm** — combined with the r2/r10/r2c/r10c sweep, **25 structural arms,
all 0/10**. Patterns:

| family | R_PICPOC Cal ≥1 AOI | iron pair | co ≥2 AOI | reading |
|---|---|---|---|---|
| ratio, cocco off (r0.5–r30) | 10/10 | survives (5–10/10) | 0/10 | recovers eqpac, no mutex, dose-robust — 1 AOI only |
| ratio + coccolith | 0/10 | 0–5/10 | 0/10 | backfires (re-entangles, breaks iron) |
| ratio + W_SINK_PIC `{0.2,0.3}` | 0/10 | survives | 0/10 | sink decoupling breaks even eqpac (ratio ≠ R_PICPOC) |
| paired PIC+POC (per-AOI) `{0.02–0.1}` | joint 9/10 | **0/10 (wiped)** | 0/10 | the classic magnitude-anchor mutex |
| PIC + `signal_3aoi` gating | joint 1/10 | 0/10 | 0/10 | routing doesn't protect the iron pair |
| PIC / ratio × PER_AOI_DINN | joint 0–10 | 0/10 (PIC) | 0/10 | architecture doesn't break it |

Confirms exhaustively: **no laptop estimator/structural lever recovers R_PICPOC in
≥2 AOIs.** The ratio loss is the lone lever that recovers R_PICPOC without the mutex
(eqpac, dose-robust); every *magnitude* anchor (PIC/POC, gated, per-AOI) still wipes
the iron pair. The ≥2-AOI block is the calcite forward-model gap, not the estimator.

## Conclusion + deck/roadmap implication

R_PICPOC at the box scale decomposes cleanly:

1. **Estimator/info side — SOLVED:** the ratio observable identifies R_PICPOC per
   cell without the iron-pair mutex (eqpac 10/10). It was never fundamentally
   unidentifiable; the prior anchors were the wrong observable.
2. **Forward-model side — the real wall:** the box's rigid-ratio calcite can't match
   Darwin's coccolithophore-driven spatial PIC/POC variation. Needs richer calcite
   physics (Darwin port) + native resolution.
3. **Seasonal axis — excluded:** the box has no seasonal biology and PIC is phase-
   locked to mort; a 1° seasonal fit won't help.

This **sharpens** the talk's ask: R_PICPOC needs *native-resolution + richer calcite
physics (the differentiable Darwin port)*, not a cheap laptop lever and not merely
"more compute for the same box." If asked tomorrow whether it's a design error vs
compute: *"The estimator side is fixable on the laptop — a PIC:POC ratio loss
recovers R_PICPOC without breaking the iron pair, in the regime where our box's
calcite matches Darwin (eqpac, 10/10). What it can't do is reproduce the
coccolithophore-driven ratio variation in the bloom regimes — that needs the full
Darwin carbonate physics at native resolution. So it's forward-model fidelity +
resolution, not the estimator and not seasonality."*

## Reproduce
```
# orthogonality pre-screen + seasonal exclusion + ratio sweep:
%LOCALAPPDATA%\ddeck\alkabs\{probe_ratio_gradient,probe_seasonal_feasibility}.py
RATIO_W=2 [COCCOLITH_ONLY=1] on the Eppley config (run_v3.0_joint_multi_aoi.py)
# overnight exhaustive campaign:
CAMP_STAMP=camp python %LOCALAPPDATA%\ddeck\alkabs\campaign_rpicpoc.py
```
Run JSONs: `D:\runs\alk_ratio\` (r2/r10/r2c/r10c), `D:\runs\rpicpoc_camp\`.
