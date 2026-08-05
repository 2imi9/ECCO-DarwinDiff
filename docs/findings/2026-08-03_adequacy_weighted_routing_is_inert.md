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

`adq_so0` completed at 50/50, `verify_run` exit 0. All three trained arms, with per-AOI legs:

| arm | `scav_rat` | eqpac | natl | sopac | vs `adq_ctrl` |
|---|---|---|---|---|---|
| `adq_ctrl` | 20/50 | 4 | 16 | 49 | — |
| `adq_eq0` (drop **inadequate** block) | 21/50 | 4 | 18 | 49 | P = 1.0000 |
| `adq_so0` (drop **adequate** block) | **11/50** | 8 | **3** | 50 | P = 0.0828 |

The two arms do answer differently — dropping the adequate block roughly halves `scav_rat` while
dropping the inadequate one does nothing — but **that asymmetry is P = 0.0828 at n=50 and does
not clear this project's 0.01 bar.** It is suggestive, not established, and after watching a
P = 0.0128 effect evaporate at n=100 earlier the same day, it is quoted as directional only.

**The leg decomposition is the part worth keeping, and it is not subtle.** Dropping sopac's iron
block leaves sopac's *own* leg untouched at 50/50 and collapses **natl from 16 to 3**. So that
block is load-bearing for a *different basin* than the one it belongs to — the shared DINN is
exporting it. That is the same pooling mechanism already documented for `R_PICPOC`'s Southern
Ocean leg, showing up on the iron side.

So, stated at the strength the evidence supports:

> **The adequacy diagnostic is validated as a description of which blocks a fit depends on. It
> is refuted as an intervention.**

Removing an inadequate block frees nothing, because an unreachable residual was never competing
for the optimiser's attention — it contributes gradient that is large but *uninformative*, and
deleting it neither helps nor hurts.

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
