# Overnight emulator-improvement loop — what helps, what doesn't (2026-07-14)

An autonomous loop systematically tested candidate improvements to the global-monthly emulator
(each: implement → small test → scale). All numbers are **local** (self-consistency vs the v05
model output, not real observations). Headline baseline: global-monthly skill vs persistence
**+0.5204** (seed 0), bankable at **+0.5165 ± 0.0023** over n=5 seeds.

## The systematic result: +0.52 is a hard, well-characterized ceiling

Every lever that changes the *inputs* or the *rollout post-processing* was rejected. The
surface-monthly emulator is already near-optimal for its formulation.

| Lever | Result | Verdict |
|---|---|---|
| **Capacity** (modes/width, up to 4×) | +0.527 best (+0.007 over baseline) | Saturated — not the bottleneck |
| **Forcing** (SST/wind/MLD inputs) | global +0.5108 (−0.010) | **Rejected** — hurts |
| **Seasonal time-encoding** (sin/cos day-of-year) | eqpac +0.212 vs +0.285 (−0.073) | **Rejected** — hurts |
| **Rollout mass-conserve** (clamp + rescale to mean) | eqpac neg 0.103 / drift 0.482 — worse than positivity | **Rejected** |
| **Rollout positivity** (clamp ≥0 between steps) | eqpac neg 0.182→0.083, drift 0.482→0.401 | **Kept** — fixes negatives |
| Longer rollout-k (k=8) | pending | — |

**Interpretation.** Two independent "add-information" ideas (forcing, seasonal phase) both *hurt*.
Under the residual formulation with a strong persistence baseline, the model already extracts the
predictive signal from the current state; extra input channels add parameters that overfit. Capacity
is saturated. So the +0.52 level is not a tuning artifact — it is close to the intrinsic
single-step predictability of the monthly next-state from state alone. Pushing past it requires
**changing the problem, not tweaking it**.

## Rollout physics: positivity is the fix; mass-conservation is not

Plain positivity (project concentrations ≥0 between steps) reduces negatives and, on the eqpac
subset, also reduces mass drift. The mass-conserving variant (rescale to the pre-clamp mean) does
not help — it slightly worsens both. Note the positivity effect on *drift* is regime-dependent
(improves eqpac, worsened the global case): negatives are always fixed, but multi-step mean drift
is a separate, harder problem best addressed by a log-space parameterization or a genuinely
conservative operator — not by rescaling. Kept as `--rollout-positivity` (committed 9130df5);
`--rollout-mass-conserve` retained as an option but not recommended.

## The real frontier

Since input/rollout tweaks are exhausted, the substantive upgrades are:
1. **Depth / 3-D** — the emulator is surface-only; carbon is a 3-D story. A 10-level (60-channel)
   global-monthly 3-D emulator is training (the one genuinely different problem this loop pursued).
2. **External validation** vs SOCAT/GLODAP — the project-level lever (issue #163).

Neither is a tweak; both change what the emulator *is* or what it *means*.
