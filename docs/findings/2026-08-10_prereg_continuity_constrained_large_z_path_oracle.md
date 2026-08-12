# Preregistration: continuity-constrained large-Z path oracle

**Frozen before evaluating the path oracle on 2026-08-10.** The exact discrete
teleportation envelope is negative in EqPac and the Southern Ocean but leaves a
North Atlantic log multiplier of only `+0.002078`. This follow-up asks whether
that sign survives even a very permissive spatial-continuity constraint.

## Map check

Before this work:

```text
python scripts/research_map_db.py settled "North Atlantic continuity constrained relocation path large zooplankton"
```

returned no settled answer. No supersession is recorded for the teleport knife
edge.

## Frozen inputs and replay

- Load the verified discrete-oracle report and the same source-floor-corrected
  support tensor bundle it binds.
- Require exact SHA-256 lineage, registered masks, `dt=0.25 d`, `1,464` steps,
  prey floor `1.2e-8 C`, and source mortality `1/30 d^-1`.
- Independently reconstruct every wet-cell Euler log increment.
- Reproduce the prior `fixed_cell` (`radius=0`) and unrestricted stepwise
  teleport log multipliers before interpreting constrained paths.

## Frozen path ladder

For each AOI, solve by dynamic programming for the maximum annual sum of Euler
log increments over a path whose successive wet cells differ by at most a
Manhattan grid radius in `{0, 1, 2, 4}`. There is no longitude wrap. The path
may start in any wet cell, remain still, and move only between wet cells. Also
retain the prior unrestricted per-step envelope as the top of the ladder.

`radius=1` permits one full 1-degree grid-cell move every quarter day and is
therefore intentionally more permissive than realistic advection. It is a
continuity bound, not a velocity model.

For every radius report the exact maximum annual log multiplier, retention,
start/end cells, distinct visited cells, switch count, and maximum realized
Manhattan jump. Require the score ladder to be nondecreasing with radius and
bounded above by the unrestricted envelope.

## Prediction and falsifier

Primary hypothesis: North Atlantic's positive teleport knife edge survives the
weakest continuity constraint, so its `radius=1` maximum annual log multiplier
is `>0`. A value `<=0` falsifies that prediction. A failed source replay,
non-positive Euler factor, non-monotone ladder, path violation, or failed
independent verifier makes the result unresolved.

The other AOIs and radii are secondary. No radius or sign threshold moves after
measurement.

## Interpretation boundary

A positive constrained oracle would not show that ECCO transport realizes the
path. A negative one would rule out only relocation through the unchanged
surface prey field at the declared grid-speed bound. Real transport can alter
prey, cross AOI boundaries, and couple depth. This is not a transport run,
target rehabilitation, endpoint-versus-time-mean decision, replication, or
B200 authorization. Stage remains 0, and issue #192 still blocks a direct use
of the existing horizontal-transport configuration.

