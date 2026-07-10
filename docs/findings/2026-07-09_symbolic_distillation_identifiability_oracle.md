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

**Calcite — a tool self-test on synthetic ground truth (validates the oracle; not itself
evidence).** On *hand-constructed* synthetic rain-ratio closures the power-law oracle behaves
correctly: it recovers `n=0.50` from `R0·Ω^0.5` over a wide Ω (IDENTIFIABLE — but this recovery is
**guaranteed by construction**, a fitting sanity check, not evidence); returns **NON-IDENTIFIABLE**
for a *planted* Ω-independent ratio (correctly flags a null); and returns **NON-IDENTIFIABLE /
under-excited** for a *planted* narrow-Ω closure. This demonstrates the oracle *discriminates* the
three cases on known ground truth — it is **not** a reproduction of, or independent corroboration of,
the real-data calcite null. The actual independent statement of that null is the **separate** real-data
run (`calcite_omega_identifiability_real.json`); the Marañón-2016 analogy and the point-level
`corr(log-ratio, in-situ Ω) ≈ 0.01` belong to that real-data analysis, not to this synthetic panel.
Committed as a passing pytest (`tests/test_symbolic_distill.py`).

## Real-data application: the oracle diagnoses the calcite E2 negative

Running the power-law oracle **on the real data** (real Daniels CP:PP rain ratio ×
real Ω_calcite derived from the v05 DIC/ALK/T/S cache;
[`scripts/calcite_omega_identifiability_real.py`](../../scripts/calcite_omega_identifiability_real.py),
findings [`calcite_omega_identifiability_real.json`](calcite_omega_identifiability_real.json))
returns **NON-IDENTIFIABLE everywhere**, and — more usefully — says *why*:

| AOI | n cells | Ω range | Ω span | exponent n (95% CI) | verdict |
|---|---|---|---|---|---|
| eqpac | 34 | 4.72–5.67 | **0.08 dex** | +6.4 [+1.8, +10.4] | under-excited |
| natl | 26 | 3.14–4.21 | **0.08 dex** | +7.0 [+0.9, +13.0] | under-excited |
| pooled | 60 | 3.14–5.67 | **0.25 dex** | +0.9 **[−0.23, +1.78]** | CI includes 0, unstable, under-excited |

The load-bearing diagnosis: **the real Ω support is far too narrow** — each basin
spans only ~0.08 dex (tropical/subpolar Ω_calcite barely varies), and even pooling
two basins reaches only 0.25 dex, below the 0.30-dex identifiability threshold. The
within-basin correlations look sizeable (eqpac +0.59, natl +0.31) but are
small-range artifacts that the oracle correctly refuses to trust; pooling across a
wider Ω collapses the exponent's CI across zero. So the calcite E2 negative is best
read as a **non-identifiability from narrow real-Ω support and small n** — a ~600-
parameter closure was asked to learn an Ω-dependence from data where Ω is nearly
constant — *not* (necessarily) a wrong closure. That is the honest,
**identifiability-limits** result, and it is the diagnosis the E2 negative-result
thread needed. (Caveat: this Ω is derived from the v05 carbonate cache, not in-situ
GLODAP; it complements, not duplicates, the earlier in-situ `corr ≈ 0.01` NULL.)

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

## Decision implication for the calcite E2 rerun

The E2 preregistration's fallback plan was to rerun with **pooled eqpac+natl** and a
**smaller/regularized closure** to distinguish "underpowered+overfit config" from a
"genuine negative." The real-data oracle says the binding constraint is neither
sample size nor closure capacity but **Ω support**: pooling two basins already only
reaches 0.25 dex (still below threshold), and a smaller closure cannot manufacture an
Ω-dependence the data does not contain. So the oracle **predicts the pooled /
smaller-closure rerun will not recover identifiability** — the honest terminal result
is the **identifiability-limits write-up** (Daniels' real Ω is too narrow to constrain
an Ω-power-law rain ratio), not more GPU E2 runs. Widening Ω support (more high-lat /
Southern-Ocean calcite obs, or a genuinely Ω-variable dataset) is the only thing that
would change the verdict — a data-staging question, not a compute one.

## Next

Wire the oracle into the H200 arms (dump each trained closure's visited `(driver,
y)` to npz, run `--npz` per arm). Apply the calcite power-law oracle to the real
Daniels-trained `EnvCalciteClosure` as the principled backbone of the calcite
identifiability-map result. See
[`docs/NEXT_SESSION.md`](../NEXT_SESSION.md) and
[`docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md`](../research_notes/2026-07-09_parameter_conditioned_emulator_update.md).
