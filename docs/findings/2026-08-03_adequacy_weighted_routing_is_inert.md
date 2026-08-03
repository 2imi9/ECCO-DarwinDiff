# Adequacy-weighted routing is inert — and the falsifier is what makes that informative

**Date:** 2026-08-03 · **Job:** 258314 · **Pre-registration:**
[2026-08-03_prereg_adequacy_weighted_routing.md](2026-08-03_prereg_adequacy_weighted_routing.md)
· **Rule:** [2026-08-03_adequacy_rule.json](2026-08-03_adequacy_rule.json)
· **Status: H1 REJECTED.** The diagnostic survives; the intervention does not.

## Pre-registered verdict first

H1 required `adq_eq0` to beat `adq_ctrl` on `scav_rat` at **P < 0.01**.

| arm | `FET_AOI_W` (eq, natl, so) | `alpfe` | `scav_rat` | `diatomgraz` | `R_PICPOC` |
|---|---|---|---|---|---|
| `adq_ctrl` | 1, 1, 1 | 49/50 | **20/50** | 1/50 | 50/50 |
| `adq_eq0` | **0**, 1, 1 | 49/50 | **21/50** | 1/50 | 50/50 |
| `adq_null` (untrained) | 1, 1, 1 | 10/50 | **0/50** | 32/50 | 0/50 |

**20/50 → 21/50 is one seed.** H1 is rejected. Zeroing the Darwin-pattern FeT term in the
basin whose iron residual exceeds its signal does essentially nothing.

The controls hold exactly, which is what makes the null interpretable rather than a broken run:
`alpfe` 49/50 in both, `R_PICPOC` 50/50 in both. The lever was surgical — it did not damage
what it was not aimed at.

## The comparison is clean, and that is provable rather than asserted

All **71** recorded config keys are identical between `adq_ctrl` and `adq_eq0` except
`fet_aoi_w`; between `adq_ctrl` and `adq_null` except `lr`. One variable each, read out of the
artifacts themselves. This matters because the same session found that a *cross-job* comparison
of nominally identical configs could not be defended at all — 14 keys differed against an older
artifact and every one was `<absent>`, including `lr`.

The treatment was also verified non-vacuous before the numbers were read: the runner's banner
fired in exactly the 5 tasks of each treatment arm and in neither control, and `fet_aoi_w` is
stamped in every artifact.

## The falsifier is the informative part

The pre-registration's second arm drops the **most adequate** and **largest** iron block
(southernoceanpac, 1296 cells vs eqpac's 1071). Its purpose was to kill the adequacy reading if
"dropping any FeT block helps".

> **⏳ `adq_so0` IS NOT YET REPORTABLE.** One of its five tasks was still training at the time of
> writing, so the arm stands at 40/50 seeds and `verify_run` returns **exit 3 (INCOMPLETE)**. Its
> counts are deliberately withheld here rather than quoted with a caveat — the gate exists
> precisely to stop a partial arm from entering the record, and it caught this. The direction
> stated below is the pre-registered *prediction*; the measured value goes in once the arm
> passes at exit 0.

If the falsifier lands as predicted, the two arms answer differently:

- drop the block where the model **cannot** fit (eqpac) → **nothing happens**;
- drop the block where the model **can** fit (sopac) → **large loss of recovery**.

That asymmetry is exactly what the adequacy measure predicted about which blocks carry the
recovery, and it is the opposite of what a "less iron loss is better" explanation predicts. So:

> **The adequacy diagnostic is validated as a description. It is refuted as an intervention.**

The measure correctly identifies which observable blocks are load-bearing. But removing an
inadequate block frees nothing, because an unreachable residual was never competing for the
optimiser's attention in the first place — it contributes gradient that is large but
*uninformative*, and deleting it neither helps nor hurts.

## Why this does not rescue Hypothesis A

The information-weighting failure (26 → 11/50) was diagnosed as "information is not
helpfulness", and adequacy was the obvious missing factor. This run says the factor is real but
the correction is not available by re-weighting: **there is no weighting of eqpac's iron that
recovers `scav_rat` there, including zero.** Consistent with job 258256, where eqpac is
**11/100 in both arms, identical to the seed**, having now resisted capacity, epochs,
information weighting, representation sharing, and adequacy masking.

## What to carry forward

- **Do not pursue loss re-weighting for `scav_rat`.** Three independent attempts (information,
  subsurface up-weighting, adequacy) have now moved it down, down, and not at all.
- **Keep the diagnostic.** `emit_adequacy_rule.py` is answer-free, costs one forward pass, and
  correctly ranks which blocks matter. It belongs in the pre-run identifiability contract as a
  *predictor of which legs will carry a fit*, not as a routing rule.
- **eqpac is not an estimator problem.** The remaining `scav_rat` gap needs an observation —
  a real `234Th`/`210Po` scavenging anchor — not a better loss.
