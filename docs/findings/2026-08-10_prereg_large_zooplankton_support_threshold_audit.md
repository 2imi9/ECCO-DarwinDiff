# Preregistration: large-zooplankton support-threshold audit

**Frozen before running the audit on 2026-08-10.** This is a diagnostic replay
of the independently verified source-floor-corrected cycle-13 trajectory. It is
not a new seasonal target, a parameter sweep, or permission to run an optimizer.

## Map check

Before this work:

```text
python scripts/research_map_db.py settled "omitted Darwin mechanism large zooplankton prey energy deficit"
```

returned the settled additive prey-energy deficit: maximum large-predator gross
gain integrals `11.060 / 11.160 / 11.574` remain below the fixed mortality
integral `12.2`. The map explicitly leaves *which omitted mechanism could close
that deficit* unresolved. A source inventory then confirmed that the frozen
Darwin-1 setup and the projection both contain five phytoplankton prey and two
zooplankton predators; a missing PFT is therefore not an admissible explanation.

## Question

How far is the failed projection's visited prey support from continuous
large-predator replacement, without changing the canonical trajectory?

## Frozen replay

- Load the corrected target and prey-energy artifacts and require every upstream
  SHA-256, config, mask, scenario, and source prey-floor relation to match.
- Start from the central `ic_0p10` cycle-12 endpoint and replay cycle 13 under
  the same monthly forcing, astronomical light, Carroll truth, `dt=0.25 d`,
  `122` steps/month, `tau=365.25 d` chemical restoring, and zero plankton
  restoring.
- Reproduce the canonical large-predator annual gain integral and endpoint to
  the existing tolerances before evaluating a counterfactual.
- At every canonical pre-step state, retain the source-defined large-predator
  weighted prey pools and assimilation numerators split into large prey
  `{diatom, large eukaryote}` and small prey `{Synechococcus, Prochlorococcus
  LL, Prochlorococcus HL}`.

## Counterfactuals

The state trajectory is held fixed. Only the instantaneous prey support passed
through the audited Holling-II algebra is scaled:

1. `all_prey`: multiply all five prey biomasses by a common `alpha >= 1`.
2. `large_prey_only`: multiply diatom and large-eukaryote biomass by `alpha`,
   leaving the three small prey unchanged.

For each ocean cell and counterfactual, solve by bisection for the smallest
`alpha` whose annual *continuous* specific-gain integral reaches the source
mortality integral `12.2`. The frozen bracket is `[1, 64]`, with 48 bisection
iterations. A root not bracketed at `64` is reported, never clipped to `64`.

Also compute the exact frozen-path external per-capita subsidy required for
replacement:

```text
subsidy_per_day = max(0, 12.2 - annual_gain) / 366
```

This is a magnitude diagnostic, not a proposed restoring term.

## Predictions and falsifiers

Primary hypothesis: the projection contains a **nearby local refuge** in every
AOI. It is supported only if the minimum `all_prey` multiplier is `<=1.25` in
each of eqpac, natlsubpolar, and southernoceanpac. One AOI above `1.25`, an
unbracketed best cell, or a failed canonical reproduction falsifies it.

Secondary quantities are reported without moving the primary threshold:

- minimum, median, 95th percentile, maximum, and fractions at or below
  `1.10 / 1.25 / 1.50 / 2 / 4` for both counterfactuals;
- the ratio of the minimum large-prey-only threshold to the minimum all-prey
  threshold;
- minimum, median, 95th percentile, and maximum subsidy per day, plus subsidy
  as a fraction of `1/30 d^-1` mortality;
- all unbracketed-cell counts.

## Interpretation boundary

This audit can distinguish a shallow local support gap from a deep one and can
quantify how much frozen prey support would be required. It cannot identify
transport, vertical niche, DOC, stoichiometry, changed assimilation, mortality,
or zooplankton restoring as the cause; it does not integrate any modified
system, establish stable coexistence, rehabilitate the target, choose endpoint
versus time mean, or authorize B200. It is one deterministic diagnostic replay
with no out-of-sample replication.
