# Synthetic identifiability illustration: per-cell fit ≠ parameter recovery

**Date:** 2026-06-27 · **Status:** verified (multi-seed) · **Backs:** #116 (manuscript),
#19 (per-cell-vs-global ablation), the Colab demo (`notebooks/demo_colab.ipynb`, PR #157).

A small, in-memory synthetic experiment (the Colab demo's engine) that demonstrates —
not asserts — three identifiability facts the full study relies on. Synthetic, so it
shows the *mechanism*; the real-data version is the cluster ablation (#19).

## Setup
8×16 grid, one SST gradient input channel. Ground truth: `alpfe` and `Smallgrow` vary
smoothly with SST; the other four Carroll-6 params fixed at Carroll's optima. Forward-
integrate the differentiable `carroll6_step` box (150 steps) → a steady-state Ps+Pl
biomass field = the **single observable**. Recover by gradient descent through the box.
Loss = z-scored pattern MSE (matching the real pipeline) unless noted.

## Findings (all verified)

**1. Capacity — per-cell fits structure a global scalar cannot.** A per-cell DINN (1×1
convs) reaches loss ~4e-4–7e-3; a single global Carroll-6 vector is **pinned at the
variance floor 0.99219 from epoch 0** (a flat field has no pattern → no gradient under a
z-scored pattern loss). Loss ratio 130–2500×. Robust (structural + every seed).

**2. Fitting ≠ identifying (equifinality).** The per-cell DINN drives loss → ~0 but does
**not** recover the true `alpfe` field. Across seeds the recovered `alpfe` has high |r|
but an **arbitrary sign**:

| loss | `alpfe` signed-r across seeds | |r| mean | sign + |
|---|---|---|---|
| pattern (n=6) | +0.62, −0.99, +1.0, +1.0, −0.99, −0.86 | 0.91 | 3/6 |
| absolute (n=6) | +0.97, −0.44, +0.97, +0.97, −0.99, +0.81 | 0.86 | 4/6 |

Different parameter fields fit the same observable equally well → the parameter's
*direction* is under-determined. (The demo run reproduces this live: `[+,−,+,+,−]`, |r| 0.92.)

**3. Identifiability is parameter-specific.** Under the *same* fits, `Smallgrow` (a direct,
monotonic effect on biomass) recovers far more consistently than `alpfe` (indirect, via
iron→growth, and compensable). Under absolute loss `Smallgrow` signed-r = +0.97, +0.95,
+0.94, +0.98, +0.85, +0.92 (all positive) while `alpfe` flips. *Which* parameters an
observable can constrain is not all-or-nothing.

## Why it matters for the project
- It is the project's central claim, shown in miniature: surrogate-to-model
  identifiability is **per-parameter**, and low loss is **not** evidence of recovery.
- It motivates the real design: **distinct absolute anchors per parameter** (GEOTRACES
  dissolved iron for the iron pair; Daniels/MODIS calcite for `R_PICPOC`) rather than
  pattern-matching one field; and the homogenization fact (real box tracer CV → ~1e-15)
  means the box's own spatial pattern carries little information, so absolute anchors are
  load-bearing.
- **Scope / honesty:** here the truth varies in space *by construction*, which is what
  lets the per-cell class help. ECCO-Darwin's Carroll-6 params were calibrated as global
  constants, so whether the per-cell predictor is load-bearing for the *real* problem is
  the open question the full per-cell-vs-global ablation (#19, `GlobalScalarNet`) tests on
  real data. This synthetic result shows the mechanism, not the real-case verdict.

## Reproduce
`python scripts/build_demo_notebook.py` then run `notebooks/demo_colab.ipynb` (cells 6–8
are Lessons 1–3). Multi-seed signed-r verified independently at n=6 (CPU, 300 epochs).
