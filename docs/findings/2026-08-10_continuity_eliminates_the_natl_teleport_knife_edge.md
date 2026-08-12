# Continuity eliminates the North Atlantic frozen-path teleport knife edge

**Finding, 2026-08-10. One deterministic frozen-trajectory bound; no actual
transport, modified prey dynamics, optimizer, replication, or B200.**

## Result

The preregistered primary hypothesis is falsified. North Atlantic's exact
discrete frozen-path oracle is positive only when the predator may teleport to
any wet cell every quarter day. Every tested spatial-continuity radius makes
the annual log multiplier negative:

| AOI | fixed (`r=0`) | `r=1` | `r=2` | `r=4` | unrestricted |
|---|---:|---:|---:|---:|---:|
| eqpac | -1.140538 | -0.760164 | -0.750847 | -0.745529 | -0.737681 |
| natlsubpolar | -1.044882 | **-0.025718** | -0.012428 | **-0.004977** | **+0.002078** |
| southernoceanpac | -0.630778 | -0.323360 | -0.312656 | -0.306980 | -0.301525 |

Here `r` is the maximum Manhattan grid-cell jump per `0.25 d` step. The
`r=1` path may therefore move one full 1-degree cell every quarter day, already
far more permissive than a physical advection model. Its North Atlantic annual
retention is `0.974610`; even `r=4` retains only `0.995035`. The unrestricted
oracle retains `1.002081`, a margin of just `0.208%`.

EqPac and the Southern Ocean remain negative at every point in the ladder. The
new information is that the North Atlantic sign change is discontinuity-
dependent, not a robust relocation result.

## What continuity changes

The unrestricted North Atlantic path switches cells 36 times and realizes a
maximum jump of 28 grid cells in one quarter-day step. The `r=1` optimum uses
71 cells and 128 switches but cannot retain the predator. The `r=4` optimum
uses 40 cells and 59 switches and still remains negative.

This separates two statements that the unrestricted oracle alone could not:

1. There is enough frozen prey somewhere in the AOI at enough times to create
   a `+0.002078` mathematical envelope when travel is free.
2. That envelope cannot be connected into a positive path under any of the
   preregistered continuity radii, including the intentionally permissive
   `r=4` bound.

## Integrity

The dynamic program independently reconstructed every Euler log increment from
the source-floor-corrected support bundle over `1,464` steps. It replayed the
prior fixed-cell and unrestricted envelopes, required the radius ladder to be
nondecreasing, and checked every realized path jump against its declared
radius. Replay discrepancies are at most `6.67e-16`.

An independent verifier reproduced all path scores and decisions from
`16,765,728` support-tensor cells, checked the upstream SHA-256 lineage, and
rejects tampered scores, paths, hashes, or compute-authorization fields. Five
focused tests pass.

## What this does not say

This is not evidence that transport is irrelevant. The oracle relocates only
the predator through one unchanged surface prey trajectory. Real transport can
change prey, import material across AOI boundaries, and couple depth. None of
those mechanisms is represented here, and no velocity or diffusivity was used.

The result therefore rules out the unrestricted North Atlantic value as a
physically continuous frozen-path explanation; it does not rule out a coupled
transport mechanism. Issue #192's horizontal-diffusivity unit defect remains a
prerequisite for a direct transport experiment.

The independent EqPac seasonality and cross-AOI `diatomgraz`-handle blockers
also remain. The seasonal target stays `stage0-failed-stop`; no endpoint-versus-
time-mean conclusion, target rehabilitation, or B200 authorization follows.

## Artifacts

- preregistration:
  `docs/findings/2026-08-10_prereg_continuity_constrained_large_z_path_oracle.md`
- runner and report:
  `scripts/analysis/explicit_zooplankton_path_oracle_audit.py` and
  `docs/findings/2026-08-10_explicit_zooplankton_path_oracle_audit.json`
- verifier and receipt:
  `scripts/analysis/verify_explicit_zooplankton_path_oracle_audit.py` and
  `docs/findings/2026-08-10_explicit_zooplankton_path_oracle_audit_verification.json`

