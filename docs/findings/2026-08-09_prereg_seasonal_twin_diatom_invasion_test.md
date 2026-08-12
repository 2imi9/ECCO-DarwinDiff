# Preregistration: can a rare diatom invade the seasonal twin?

**Frozen 2026-08-09 after the process-budget attribution and before any
low-biomass invasion multiplier was computed.** This is the preregistered
follow-up required by the process budget's `mixed-or-other` branch.

## Relational state

The map now settles that the two chemical-restoring seasonal targets fail
specifically because the diatom loses nearly all inventory in cycle 1, with
linear grazing the dominant gross loss and no clamp events. That is an
attribution along the observed trajectory. It does not yet prove that the
diatom-free late-cycle trajectory is locally attracting.

The following query returned no settled row before this preregistration:

```text
python scripts/research_map_db.py settled "diatom low-biomass invasion exponent seasonal twin"
```

## Frozen construction

For each of the same two target constructions and all three canonical AOIs:

1. load the same Darwin initial state and monthly T/S/wind forcing;
2. set only `P_diatom=0` at initialization;
3. hold Carroll truth, chemical-only restoring tau=365.25 d, exact zero
   phytoplankton restoring, `dt=0.25 d`, 122 steps/month, Eppley growth, and
   either fixed or astronomical light unchanged;
4. integrate the resident system for eight cycles;
5. record invasion diagnostics for cycles 7 and 8 only.

The zero-diatom state is invariant in the production algebra, so this computes
the resident trajectory of the other 14 tracers without injecting a seed or
changing a parameter.

## Frozen invasion statistic

At each resident step and cell, the diatom's low-density continuous per-capita
rate is

```text
lambda = MU_DIATOM * f_Fe * light * gamma_T
         - M_LIN - diatomgraz * G0_GRAZE
```

The quadratic mortality term vanishes as `P_diatom -> 0`. Because production
uses forward Euler, the exact one-step rare-diatom multiplier is
`1 + dt*lambda`. Require it to be positive at every step. The primary annual
statistic is therefore the discrete log multiplier

```text
Lambda = sum_steps log(1 + dt*lambda)
M      = exp(Lambda)
```

not `sum(dt*lambda)`, which is retained only as a continuous-time diagnostic.
Save unaggregated monthly `Lambda`, continuous exponents, counts of positive
`lambda`, and minimum Euler factors per ocean cell. An independent verifier
must reconstruct annual values from all 12 monthly tensors and reproduce every
summary.

## Frozen gates and decision

The resident trajectory is late-cycle stable only if the **maximum per-tracer**
cycle-7 to cycle-8 all-step-mean relative L2 is <=1% over the ocean mask for
each AOI. Exclude the diatom tracer from this maximum because it is exactly
zero by construction; require that exact zero separately. Per-tracer scaling
prevents DIC/ALK magnitude from hiding drift in small biological pools.

Per AOI, classify cycle 8 as:

- **uniformly non-invadable:** maximum cell `Lambda < -0.10`;
- **uniformly invadable:** minimum cell `Lambda > +0.10`;
- **mixed:** otherwise.

The +/-0.10 annual margin prevents float32 or boundary-zero classifications.
Require cycle-7 and cycle-8 classifications to agree. The cross-AOI decision is:

1. **structural diatom-free attractor:** uniformly non-invadable and stable in
   all three AOIs under both light constructions;
2. **light-driver-specific:** fixed light is not uniformly non-invadable while
   astronomical light is, in at least two AOIs;
3. **spatial/mixed viability:** neither rule above.

## Consequence boundary

A structural-attractor result rules out light-amplitude or chemical-tau tuning
as the next step. It authorizes scoping, but not yet implementing, either an
explicit grazer state/density-dependent grazing closure or a physically sourced
biomass transport term. It does not authorize direct Darwin-biomass restoring,
a recovery factorial, or B200 compute.

A positive or mixed multiplier falsifies the stronger attractor explanation
and requires a spatial/transient analysis before any model change. No outcome
selects endpoint versus time mean or establishes a Darwin grazing process.
