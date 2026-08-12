# Preregistration: discrete large-Z transport-oracle bound

**Frozen before evaluating the discrete oracle on 2026-08-10.** The preceding
continuous-gain oracle left North Atlantic only `0.00970` above the mortality
integral under unrestricted quarter-day teleportation. This follow-up uses the
actual Euler survival criterion without changing the prey trajectory.

## Map check

Before this work:

```text
python scripts/research_map_db.py settled "discrete Euler teleportation log multiplier large zooplankton"
```

returned no settled answer. The map already settles the continuous energetic
bound and the fixed-cell discrete exclusion; neither answers whether North
Atlantic's tiny continuous oracle margin survives the discrete update.

## Frozen inputs and integrity

- Load the verified support-threshold artifact and the independently verified
  source-floor-corrected exclusion artifact.
- Require their SHA-256 lineage to the same corrected target, AOI masks,
  `dt=0.25 d`, `122` steps/month, 12 months, prey floor `1.2e-8 C`, and source
  mortality `1/30 d^-1`.
- Reconstruct every large-predator gain rate from the saved large/small prey
  pools and assimilation numerators.
- Reproduce the upstream monthly fixed-cell log-multiplier fields within the
  existing exclusion tolerance `5e-4` before interpreting the oracle.

## Frozen discrete hierarchy

For each wet cell and quarter-day step, compute exactly:

```text
factor = 1 + dt * (specific_gain - mortality)
log_increment = log(factor)
```

All factors must be strictly positive. Evaluate:

1. `fixed_cell`: maximize the annual sum of log increments over one fixed cell.
2. `monthly_teleport`: independently maximize each month's sum over cells, then
   sum the 12 selected monthly log multipliers.
3. `stepwise_teleport`: maximize the log increment over wet cells at every step,
   then sum all 1,464 maxima.

Report each log multiplier, `exp(log_multiplier)` retention, continuous net
margin on the same selected envelope, and the Jensen gap
`continuous_margin - discrete_log_multiplier`. The same path-switch and
grid-index jump diagnostics as the continuous oracle are secondary.

## Prediction and falsifier

Primary hypothesis: the exact discrete update closes the North Atlantic knife
edge, so even the `stepwise_teleport` annual log multiplier is `<=0` in all
three AOIs. Any positive stepwise log multiplier falsifies the all-AOI bound.
A non-positive factor, source replay mismatch, source hash mismatch, or failed
independent verification makes the result unresolved.

## Interpretation boundary

This can bound only relocation of the predator through the **unchanged frozen
prey path**. It cannot rule out transport that changes prey, imports material,
couples depths, or changes predator-prey dynamics. It is not a transport run,
target repair, optimizer result, endpoint-versus-time-mean decision, replicated
result, or B200 authorization. The seasonal branch remains at Stage 0.

