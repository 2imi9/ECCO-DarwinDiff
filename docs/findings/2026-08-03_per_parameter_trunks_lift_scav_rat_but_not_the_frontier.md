# Per-parameter trunks lift `scav_rat` a long way, and do not lift the frontier

**Date:** 2026-08-03 · **Job:** 257056 · **Status:** pre-registered primary outcome **REJECTED**;
a large secondary effect that does not clear the same bar
**Pre-registration:** `docs/findings/2026-08-03_prereg_per_parameter_routing.md`

## Pre-registered verdict first: H1 is not supported

The pre-registration said H1 is supported only if an arm **clears its own null on all four
observables** while the capacity-matched control clears at most three.

| arm | `alpfe` | `scav_rat` | `diatomgraz` | `R_PICPOC` | clears |
|---|---|---|---|---|---|
| flagship-config control re-run in 256953 (published 25/50) | 49/50 | 26/50 | — | 50/50 | **3 of 4** |
| capacity-matched (shared, 1878 w) | 49/50 | 34/50 | — | 50/50 | **3 of 4** |
| per-parameter (6 trunks, 1926 w) | 50/50 | 45/50 | — | 50/50 | **3 of 4** |

Every arm clears exactly three. `diatomgraz` clears in none of them. **The 3-of-4 frontier survives
removing parameter sharing**, so the frontier is not, on this evidence, an artifact of forcing six
parameters through one representation.

All nine arm-vs-own-null tests pass at P < 0.01 (`scav_rat` P = 6.9e-23 for per-parameter, 1.7e-14
for the matched control, 3.47e-10 for the flagship; `R_PICPOC` P = 1.98e-29 throughout).

## The secondary effect is large, and I am not going to dress it up

`scav_rat`, per-AOI ≥2-of-3 at n=50, each against its own untrained null of 0/50:

```
flagship re-run   406 weights   26/50  (52%)   published flagship is 25/50
capacity-matched 1878 weights   34/50  (68%)     <- +8 seeds from capacity alone
per-parameter    1926 weights   45/50  (90%)     <- +11 seeds on top, at equal budget
```

**Roughly two fifths of the total lift is network size, not parameter sharing.** Comparing
per-parameter against the *flagship* would have credited the whole 26 → 45 to the architecture; the
matched control shows 8 of those 19 seeds are capacity. That control was the entire reason for
building `matched_hidden_dim()`, and it changed the conclusion.

**The per-parameter contribution over the matched control is P = 0.0128.** The pre-registration
used **P < 0.01** as its threshold everywhere else. This does not clear it. The effect is large in
size (68% → 90%) and the direction is unambiguous, but at n=50 it is not significant at the bar
this project set for itself, and it should be quoted that way rather than as a clean win.

**The gain is almost entirely North Atlantic.** `scav_rat`'s per-AOI legs:

| | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| flagship | 8/50 | **19/50** | 49/50 |
| capacity-matched | 4/50 | 29/50 | 50/50 |
| per-parameter | 6/50 | **43/50** | 49/50 |

eqpac stays dead in every arm and sopac stays at ceiling in every arm. The whole effect is natl,
19 → 43. That is the basin the information rule independently flagged as under-served by the
flagship's uniform weights — two different analyses pointing at the same leg from different
directions, one derived and one measured.

## `diatomgraz` at the Excellent band: uninformative, not uncontaminated

The pre-registration switched `diatomgraz` to the ≤10% band because its prior midpoint sits at rel
0.367, *inside* the 40% band, which is why its untrained null is ~34/50 there. At ≤10%:

```
per-parameter   0/50  vs null 0/50   P=1
matched control 0/50  vs null 0/50   P=1
flagship        0/50  vs null 0/50   P=1
```

The band change removed the contamination and revealed there is nothing underneath: `diatomgraz` is
not recovered to 10% by anything, trained or untrained. So it cannot be the fourth observable in any
arm, and the "3-of-4 frontier" is more accurately a **3-of-3-plus-one-unrecoverable**.

## Architecture-matched nulls were load-bearing

The untrained baselines are **not** equal across arms — `alpfe` scores 10/50 untrained on the
flagship, 13/50 on per-parameter, 15/50 on the widened control. Bigger networks score higher
untrained. Any of these graded against a borrowed null would have been inflated, and the inflation
tracks exactly the architecture change under test.

## What to carry forward

- **Do not claim the frontier was a parameter-sharing artifact.** It was not; it survived.
- **`scav_rat` at 45/50 is the highest this project has measured**, against 26/50 published and
  41/50 at 4000 epochs. It comes with two caveats that must travel with it: two fifths of the lift
  is capacity, and the architecture contribution is P = 0.0128 against its matched control.
- The natl-only pattern is now supported twice, independently. That is the more durable finding
  than either number.
- `PER_PARAM=1` costs ~4.7x the weights of the flagship trunk and roughly doubles wall-clock.
