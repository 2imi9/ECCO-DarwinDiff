# Box convergence — the 200-step recovery fits a transient pattern, not a steady state (2026-06-27)

> **SUPERSEDED (same day) by `2026-06-27_box_homogenization_DEFINITIVE.md`.** This note over-corrected:
> it claimed "+0.81 at convergence = the box reproduces Darwin's eqpac iron," but adversarial review +
> my own CV computation showed (a) +0.81 is a 3200-step waypoint that flips to −0.79 by 6400, and
> (b) the converged box is spatially **near-uniform** (tracer CV → 1e-15), so there is **no converged
> pattern to correlate** — neither −0.96 nor +0.81 is meaningful. The robust parts below (means
> converge by 200; PIC:POC = 0.0424 stable) stand; the FeT "+0.81 fidelity" claim does not. See the
> definitive note.

Motivated by a Lyapunov-style linearization of the box (`/c/Users/Frank/dd_agg/box_linearization.py`):
the steady-state Jacobian has a slow dissipative mode (|eig| = 0.9957, a ~230-step relaxation
timescale) and 2 conserved modes. Since the recovery integrates only **200 steps**, that slow mode
predicts the recovery may fit an **un-relaxed transient**. Tested at the real eqpac operating point
(Darwin-warm IC + per-cell forcing, Carroll params; `/c/Users/Frank/dd_agg/convergence_check.py`).

## Result — means converge, the spatial *pattern* does not

| field | mean drift (200 vs 3200) | pattern r(200, 3200) |
|---|---|---|
| phyto biomass | 0.3% | 0.889 |
| POC | 0.1% | 0.845 |
| PIC | 0.1% | 0.663 |
| FeT | 0.2% | **−0.841** |

AOI-**means** are converged by 200 steps (PIC:POC = 0.0424 identical from 200→3200). But the
**z-scored spatial pattern — which is exactly what the recovery loss fits — is not**: it is only
r ≈ 0.66–0.89 correlated with the relaxed state, and the **iron pattern flips sign**.

## Decisive — the eqpac FeT "surrogate gap" is an under-convergence artifact

Box-vs-**Darwin** z-scored pattern r:

| field | @200 steps | @3200 steps |
|---|---|---|
| POC | −0.044 | −0.000 |
| PIC | +0.441 | +0.079 |
| **FeT** | **−0.957** | **+0.812** |

**At the recovery's 200 steps the box iron pattern is anti-correlated with Darwin (−0.96); at
convergence it is positively correlated (+0.81).** The box *does* reproduce Darwin's equatorial iron
pattern — the recovery just never integrates long enough to reach it. This **corrects**
`2026-06-26_surrogate_gap_quantified.md`, which reported the −0.96 as a fundamental surrogate
limitation; it is an integration-length artifact.

## Skeptical caveats (do not over-read)
- FeT is **not fully relaxed even at 3200** (pattern r(1600,3200) = 0.874, still drifting; phyto/POC/PIC
  are converged, r = 1.000). So +0.81 is a lower bound on the direction, not a final value — but the
  sign reversal vs −0.96 is robust.
- **eqpac-specific:** natl/SO iron were already +0.89/+0.80 at 200 steps. The equatorial upwelling iron
  field carries the slow mode.
- **PIC degrades** with convergence (+0.44 → +0.08) — convergence is not uniformly "better," it just
  moves the pattern; the recovered PIC:POC *ratio* (the R_PICPOC observable) is unaffected (converged).
- The recovery still recovered the iron pair (alpfe/scav_rat) — it leaned on the real GEOTRACES anchor,
  not the (transient, unreliable) 200-step Darwin-FeT pattern. So the *result* stands; the *mechanism*
  in the surrogate-gap note was mis-attributed.

## Two consequences

1. **What the surrogate-gap note actually measured** is "what the recovery fits at 200 steps," which is
   the operative quantity for the recovery — but it is NOT "the box's steady-state fidelity." The two
   were conflated. Corrected in that note.
2. **Concrete improvement lead (testable):** integrate the recovery longer (~1600+ steps so the iron
   slow mode relaxes). The Darwin-FeT pattern loss would then be a *valid* iron anchor (+0.8 vs Darwin,
   not −0.96), which could improve iron recovery and/or reduce the reliance on up-weighting real
   GEOTRACES iron. Cost: ~8× the box integration. Worth a controlled n≥10 test (200 vs 1600 steps,
   iron-pair recovery rate) before adopting — convergence is not free and PIC did not improve.

Provenance: linearization + convergence scripts in `/c/Users/Frank/dd_agg/`; real eqpac cache
(`eqpac_targets_equatorial_pacific.pt`); Carroll params; float64.
