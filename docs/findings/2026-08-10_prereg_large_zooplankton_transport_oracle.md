# Preregistration: large-zooplankton transport-oracle bound

**Frozen before evaluating the oracle on 2026-08-10.** This is a derived
upper-bound audit of the independently verified source-floor-corrected cycle-13
prey trajectory. It does not run transport, modify dynamics, or authorize an
optimizer.

## Map check

Before this work:

```text
python scripts/research_map_db.py settled "large zooplankton transport spatial oracle annual gain"
```

returned no settled answer. The map does settle that every fixed cell has a
continuous large-predator energy deficit, and it leaves prescribed transport as
an open model-reduction question. Issue #192 independently blocks a direct use
of the existing transport configuration because its horizontal diffusivity
control is in the wrong units.

## Question

Can spatial relocation be ruled out on energetic grounds alone, given the
frozen corrected prey field?

## Frozen inputs and replay

- Use the verified support-threshold report and tensor bundle, together with
  their source-floor-corrected prey-energy report and tensor bundle.
- Require exact SHA-256 lineage, the source prey floor `1.2e-8 C`, source
  mortality `1/30 d^-1`, `dt=0.25 d`, `122` steps/month, 12 months, and the
  three registered AOI masks.
- Reconstruct the canonical large-predator specific gain at every saved
  quarter-day step and wet cell from the saved large/small weighted prey pools
  and assimilation numerators using the literal source Holling-II algebra.
- Reproduce each AOI's upstream maximum fixed-cell annual gain before
  interpreting an oracle.

## Frozen oracle hierarchy

The state and prey fields remain fixed. These are counterfactual envelopes,
not trajectories:

1. `fixed_cell`: choose one wet cell for the entire year. This must reproduce
   the upstream energy audit and remains below mortality by construction.
2. `monthly_teleport`: independently choose the wet cell with the largest
   integrated gain in each month, then sum the 12 monthly maxima.
3. `stepwise_teleport`: independently choose the wet cell with the largest gain
   at every quarter-day step, then sum all 1,464 maxima.

The stepwise envelope is an upper bound on any path confined to the AOI because
it removes continuity, velocity, boundary, and travel-time constraints. The
monthly envelope is a descriptive intermediate and is not a physical path.

For both relocation envelopes, report gain integral, gain/mortality ratio,
margin above or below mortality, unique selected cells, number of cell switches,
and grid-index jump distances. Also report the fraction of steps for which at
least one wet cell has instantaneous gain at or above the mortality rate.

## Prediction and falsifier

Primary hypothesis: frozen prey support is energetically open under the most
permissive relocation bound. It is supported only if the `stepwise_teleport`
gain integral reaches `12.2` in **all three AOIs**.

If any AOI remains below `12.2`, transport confined to the frozen prey field is
energetically ruled out there. A source-replay mismatch, non-finite wet-cell
gain, source-hash mismatch, or failed independent reproduction leaves the
hypothesis unresolved rather than supported.

No threshold is moved after seeing the result. Monthly-oracle outcomes do not
control the primary branch.

## Interpretation boundary

A supported result says only that an unrealistically permissive spatial path
has enough frozen prey energy, so actual transport is not ruled out by this
bound. It does not show that ECCO velocities can realize the path, that passive
transport produces prey-predator colocation, that any transported system is
stable, or that transport is the omitted mechanism. It does not rehabilitate
the seasonal target, remove the EqPac seasonality or parameter-handle blockers,
choose endpoint versus time mean, provide replication, or authorize B200.

