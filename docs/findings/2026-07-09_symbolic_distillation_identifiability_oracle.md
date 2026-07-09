# Symbolic distillation as a second identifiability oracle (2026-07-09)

A consolidated record of the identifiability-oracle tooling built this session
(all local CPU, synthetic self-twin). The artifact is
[`scripts/symbolic_distill_probe.py`](../../scripts/symbolic_distill_probe.py)
(+ `symbolic_distill_dynamics_probe.py`, 18 tests). It is a **second, independent
identifiability oracle** for a trained closure: given a frozen closure's learned
law, it asks *is that law recoverable as the candidate mechanism, and is it
identifiable on the support the closure actually visited?* The answer must agree
with the existing Fisher / profile-likelihood diagnostics — where they agree, the
identifiability call is doubly grounded; where a profile is flat, the oracle must
also fail.

> Honesty guardrail: synthetic self-twin, 0-D / 1-column box, CPU. A **methods /
> identifiability result**, not a real-Darwin or real-biology claim. The real-data
> E2 gate stays unbuilt; these tools *feed* it (a per-arm go/no-go that saves H200
> budget), they do not substitute for it.

## The method

Distillation is **algebraic**, not vanilla SINDy: a trained closure already emits
a clean analytic flux, so there are no numerical derivatives — it is a static
over-determined regression of the closure's output against a physics-anchored
candidate library on the **visited support**, with support masking, inverse-density
reweighting, and bootstrap inclusion/stability. Two closure families are covered,
each with the same *recovery + stability + support* verdict logic:

| Closure | Learned law | Candidate | Verdict logic |
|---|---|---|---|
| **Iron** (`ffe`) | `f_fe(DFe)` | fixed-k **Monod bank** `DFe/(DFe+k)` + poly confounders | STLSQ inclusion(Monod) > 0.85, k stable, **separable from a line on the support**, held-out R² |
| **Calcite** (`EnvCalciteClosure`) | `ratio(Ω)` | **power law** `R0·Ω^n` (log-log slope) | bootstrap CI of `n` excludes 0, `n` stable, Ω spanned ≥ 0.3 dex |

The load-bearing idea in both is **support-dependence**. A Monod curve is
indistinguishable from a straight line below the half-saturation knee; a power law
is indistinguishable from a constant over a narrow driver range. So the oracle does
not merely ask "does the mechanism fit" — it asks "is the mechanism *distinguishable
from its degenerate confounder on the visited support*." A perfectly-mechanistic
closure that was never excited through the informative regime correctly returns
**non-identifiable** — the honest verdict that prescribes *more excitation*, not
*more compute*.

## Results

**Iron — the oracle recovers the closure and confirms excitation cures equifinality.**
Trained a `MonodAnchored` closure **through the box dynamics** (`column_tendency` +
`integrate`) under two regimes, then ran the oracle
([`docs/findings/symbolic_distill_dynamics_probe.json`](symbolic_distill_dynamics_probe.json)):

| Regime | Visited DFe span | Monod⇄line alias | Verdict (n=2 seeds) |
|---|---|---|---|
| narrow (single-IC, no forcing) | ~0.31 dex | 0.99 | **DISTILL-FAIL 0/2** |
| excited (multi-IC + seasonal drawdown) | ~1.8 dex | ~0.81 | **DISTILL-PASS 2/2** |

`excitation_cures_equifinality = True`. This is the Night-1 finding ("closure
equifinality is a support problem; excitation cures it") turned into a
quantitative, gate-checked demonstration on the actual training pipeline. On
analytic ground truth the oracle recovers the planted half-saturation to <1 %
(pure Monod), passes the harder `Monod^0.7` twin with a reported (biased-low)
effective k, and correctly fails flat and linear-confounder closures.

**Calcite — the oracle reproduces the E2 NULL from ground truth.** On synthetic
rain-ratio closures the power-law oracle: recovers `n=0.50` from `R0·Ω^0.5` over a
wide Ω (IDENTIFIABLE); returns **NON-IDENTIFIABLE** for an Ω-independent ratio (the
NULL — consistent with Marañón 2016 tropical calcification being Ω-independent, and
with the real-data E2's point-level `corr(log-ratio, in-situ Ω) ≈ 0.01`); and
returns **NON-IDENTIFIABLE / under-excited** for a narrow-Ω closure. So the oracle
is a principled, bootstrap-based second statement of the same calcite NULL the
correlation analysis found — a stronger identifiability claim than a raw
correlation, and the natural quantitative backbone for the calcite
identifiability-map fallback.

## Why this matters (Paper #2 framing)

- It is the **quantitative successor to BINN's "visualize the learned term"**
  (Lagergren 2020): instead of eyeballing the NN, the oracle *tests* whether the
  learned law is the candidate mechanism and whether it is identifiable on the
  visited support.
- It is a **compute gate**: a DISTILL-FAIL on a cluster-trained closure says the
  fix is excitation/data, not a bigger native-resolution run — before spending the
  budget.
- It **cross-checks** the Fisher/profile diagnostics with an independent method;
  agreement (e.g. a flat profile ⇒ non-identifiable oracle verdict) is what turns a
  single-method identifiability claim into a robust one.

## Next

Wire the oracle into the H200 arms (dump each trained closure's visited `(driver,
y)` to npz, run `--npz` per arm). Apply the calcite power-law oracle to the real
Daniels-trained `EnvCalciteClosure` as the principled backbone of the calcite
identifiability-map result. See
[`docs/NEXT_SESSION.md`](../NEXT_SESSION.md) and
[`docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md`](../research_notes/2026-07-09_parameter_conditioned_emulator_update.md).
