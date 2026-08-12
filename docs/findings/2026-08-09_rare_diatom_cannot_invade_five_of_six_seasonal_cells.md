# A rare diatom cannot invade five of six seasonal target cells

**Date:** 2026-08-09 | **Status:** measured and independently verified, bounded
to the reduced box | **Optimizer:** none | **Cluster compute:** none |
**Preregistration:**
`docs/findings/2026-08-09_prereg_seasonal_twin_diatom_invasion_test.md`

## Result in one sentence

On stable late-cycle resident trajectories with diatom biomass fixed at zero,
an infinitesimal diatom declines in every EqPac and North Atlantic cell under
both light constructions and in every Southern Ocean cell under astronomical
light. The only exception is fixed-light Southern Ocean, where 50 of 1,296
cells have positive annual invasion multipliers. The preregistered result is
therefore spatial/mixed viability, not a universal diatom-free attractor.

## 1. What was tested

The process budget established that grazing dominates the observed cycle-1
diatom loss. This follow-up tested the stronger local-stability statement.

For each light construction and AOI, the same seasonal target was initialized
with `P_diatom=0`; the other 14 tracers evolved for eight cycles under Carroll
truth and the frozen chemical closure. The diatom remains exactly zero in the
production algebra. On cycles 7 and 8, the exact forward-Euler rare-diatom
multiplier was integrated per cell:

```text
lambda = MU_DIATOM * f_Fe * light * gamma_T
         - M_LIN - diatomgraz * G0_GRAZE

Lambda = sum log(1 + dt*lambda)
annual multiplier = exp(Lambda)
```

The quadratic mortality term vanishes at zero biomass. Every Euler factor was
positive, so every log multiplier is defined.

## 2. Cycle-8 invasion results

| construction | AOI | annual log multiplier min / median / max | positive cells | classification |
|---|---|---:|---:|---|
| fixed light | EqPac | -24.245 / -13.456 / -9.487 | 0/1,071 | uniformly non-invadable |
| fixed light | North Atlantic | -40.670 / -13.288 / -1.193 | 0/489 | uniformly non-invadable |
| fixed light | Southern Ocean | -30.661 / -14.323 / **+2.794** | **50/1,296** | mixed |
| astronomical | EqPac | -24.268 / -13.568 / -9.563 | 0/1,071 | uniformly non-invadable |
| astronomical | North Atlantic | -52.961 / -26.348 / -9.341 | 0/489 | uniformly non-invadable |
| astronomical | Southern Ocean | -45.052 / -26.493 / -5.417 | 0/1,296 | uniformly non-invadable |

The medians correspond to annual multipliers of `1.43e-6`, `1.69e-6`, and
`6.02e-7` under fixed light, and `1.28e-6`, `3.61e-12`, and `3.12e-12` under
astronomical light. Fixed-light Southern Ocean spans `4.83e-14` to **16.34**;
its 50 positive cells are 3.858% of the registered ocean mask.

Cycles 7 and 8 give the same classifications and numerical ranges. The maximum
per-tracer resident-state relative L2 between those cycles is `8.99e-5` across
all six construction-by-AOI cells, far below the frozen 1% gate. The result is
not a drifting resident trajectory.

## 3. Positive seasons are not positive annual growth

Astronomical-light North Atlantic and Southern Ocean have positive
instantaneous low-density growth rates during 37.07% and 36.53% of steps,
respectively. Their annual multipliers are nevertheless negative in every
cell, with maxima `8.77e-5` and `4.44e-3`.

Counting favorable months would therefore reverse the conclusion. Rare
population persistence is multiplicative, so the sum of log Euler factors is
the relevant statistic: losses in unfavorable periods are not canceled by
counting the number of favorable steps.

## 4. Verification

The independent verifier reconstructed annual results from all 12 monthly
tensors for each cycle, checked the discrete-log versus continuous-exponent
inequality, exact zero resident diatom, positive Euler factors, event bounds,
per-tracer stability, every report field, and the frozen decision tree.

- raw tensor cells checked: **549,696**;
- decision: `spatial-or-mixed-viability`;
- B200 authorized: `false`.

Artifacts:

- `docs/findings/2026-08-09_seasonal_twin_diatom_invasion.pt.gz`;
- `docs/findings/2026-08-09_seasonal_twin_diatom_invasion.json`;
- `docs/findings/2026-08-09_seasonal_twin_diatom_invasion_verification.json`.

## 5. Consequence for the seasonal loss decider

The universal-attractor hypothesis is falsified by the fixed-light Southern
Ocean refuge, so do not write that zero is locally attracting everywhere. The
current target is still unusable as a three-AOI loss decider: five of six cells
are uniformly non-invadable, including EqPac and North Atlantic under both
light constructions, and the sixth is viable in only 3.858% of cells.

The cross-AOI light-driver rule also does not fire; astronomical light removes
the refuge only in one AOI. Another light-amplitude or chemical-tau sweep is not
licensed. The next model scope is the missing grazer dimension or a physically
sourced biomass-transport mechanism, with a rare-invasion gate required before
any recovery run. Direct restoring to Darwin diatom biomass remains prohibited
as circular.

This finding is not a Darwin grazing result, does not choose endpoint versus
time mean, and does not authorize a B200 cost gate or recovery factorial.
