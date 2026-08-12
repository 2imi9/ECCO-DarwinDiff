# The discrete update preserves the North Atlantic teleport knife edge

**Finding, 2026-08-10. One deterministic frozen-trajectory bound; no transport
run, modified dynamics, optimizer, replication, or B200.**

## Result

The preregistered all-AOI hypothesis is falsified. Replacing the continuous
gain-minus-mortality comparison with the source model's exact Euler survival
criterion leaves the unrestricted North Atlantic stepwise oracle barely
positive:

| AOI | fixed-cell log multiplier | monthly teleport | stepwise teleport | stepwise retention |
|---|---:|---:|---:|---:|
| eqpac | -1.14054 | -0.74566 | -0.73768 | 0.47822 |
| natlsubpolar | -1.04488 | -0.04693 | **+0.002078** | **1.002081** |
| southernoceanpac | -0.63078 | -0.31546 | -0.30152 | 0.73969 |

EqPac and Southern Ocean therefore remain ruled out under frozen-path
relocation. North Atlantic remains open only under teleportation every
quarter-day: the monthly relocation envelope still loses `4.58%` of biomass
over the year.

## Continuous versus discrete

For each selected envelope the audit evaluates
`log(1 + dt*(gain-mortality))` directly. The discrete concavity penalty reduces
North Atlantic's continuous stepwise margin from `+0.009699` to a log multiplier
of `+0.002078`, a Jensen gap of `0.007621`, but does not change its sign. The
same gaps are `0.000204` in EqPac and `0.005458` in the Southern Ocean.

All wet-cell Euler factors remain positive. Their minima are
`0.997550 / 0.991693 / 0.991702`, so the result is not a log-domain or clamp
artifact.

## Integrity

The audit replays the literal source grazing rate from the support tensors and
binds it to the independently verified source-floor-corrected exclusion
artifact. Maximum discrepancies from the upstream annual log-multiplier fields
are `3.07e-6 / 3.87e-6 / 3.50e-6`, within the inherited `5e-4` tolerance.

An independent verifier reproduced fixed-cell, monthly-teleport and
stepwise-teleport log multipliers from `16,765,728` support-tensor cells and
checked the shared corrected-target hash lineage. Five tests reject tampered
log multipliers, prey support, exclusion hashes and transport decisions.

## What this does not say

The positive North Atlantic value is `0.208%` retention growth under an oracle
that jumps as far as 28 grid cells in a quarter day and switches cells 36 times.
It is not evidence that physical transport works, and it is too close to zero
to support a robust biological claim. The negative EqPac and Southern Ocean
bounds apply only while prey remains fixed; transport that changes or imports
prey is outside this audit.

No actual velocity, horizontal diffusivity, boundary flux, or depth coupling
was used. Issue #192 remains a prerequisite for a direct transport experiment.
The independent EqPac seasonality and global `diatomgraz`-handle blockers also
remain. The seasonal target stays `stage0-failed-stop`, and no endpoint-versus-
time-mean conclusion or B200 authorization follows.

## Artifacts

- preregistration:
  `docs/findings/2026-08-10_prereg_discrete_large_z_transport_oracle.md`
- runner and report:
  `scripts/analysis/explicit_zooplankton_discrete_transport_oracle_audit.py`
  and
  `docs/findings/2026-08-10_explicit_zooplankton_discrete_transport_oracle_audit.json`
- verifier and receipt:
  `scripts/analysis/verify_explicit_zooplankton_discrete_transport_oracle_audit.py`
  and
  `docs/findings/2026-08-10_explicit_zooplankton_discrete_transport_oracle_audit_verification.json`

