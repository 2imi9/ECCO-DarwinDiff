# Preregistration: phytoplankton process budgets for the failed seasonal twins

**Frozen 2026-08-09 before any cycle-resolved process budget was computed.**
This is a target-only diagnostic. It does not fit parameters, grade recovery,
choose endpoint versus time mean, or authorize cluster compute.

## Relational state

Three target constructions are already settled as failures: monthly T/S/wind
alone, a one-year chemical-only restoring closure, and the same closure with
parameter-free astronomical monthly light. The latter two preserve DFe2 contrast
and finite DIC but fail the unchanged Chl1 gate. Before this preregistration the
following map query returned no settled row:

```text
python scripts/research_map_db.py settled "phytoplankton process budget seasonal twin"
```

The question here is narrower than another target experiment: did the biomass
collapse arise from gross biological losses exceeding growth, from the
non-negativity floor, or specifically from the astronomical light driver?

## Frozen inputs

Re-run exactly the two completed chemical-restoring target constructions:

- `chemical-fixed-light`: tau=365.25 d chemical-only restoring, legacy constant
  `LIGHT=1`;
- `chemical-astronomical-light`: the identical closure plus the preregistered
  latitude/month astronomical multiplier with per-cell annual mean one.

Hold fixed Carroll truth, the cached monthly T/S/wind fields, Darwin initial
state and chemical restoring reference, `dt=0.25 d`, 122 steps/month, eight
cycles, all three canonical AOIs, Eppley temperature growth, and exact zero
restoring on all five phytoplankton fields. Inspect cycles 1, 2, 7, and 8. Do
not change light amplitude, closure timescale, mortality, initial biomass,
parameter values, or ocean mask after reading a budget.

## Frozen tensors

For every inspected cycle, PFT, and ocean cell, integrate the exact pre-clamp
step algebra:

```text
G  = sum(dt * growth)
ML = sum(dt * linear mortality)
MQ = sum(dt * quadratic mortality)
GR = sum(dt * diatom grazing)
L  = ML + MQ + GR
N  = G - L
A  = sum(model_next_phyto - state_phyto)
C  = A - N
```

`C` is the non-negativity-floor correction. Also retain initial and final PFT
inventories, the count of raw updates below zero, the count of post-step zeros,
and time integrals of Fe limitation, light, and the Eppley multiplier. Save the
unaggregated per-cell tensors; summaries alone are not an auditable artifact.

The independent verifier must recompute every summary and enforce, to a
float32-scaled tolerance:

- `N = G - ML - MQ - GR`;
- `A = N + C`;
- final minus initial inventory equals `A` because phytoplankton restoring is
  exactly zero;
- `C >= 0` apart from roundoff;
- every tensor is finite and all expected AOI/construction/cycle cells exist.

## Frozen summaries

Aggregate first over the registered ocean mask and then over PFTs. Report each
PFT separately as well as the all-PFT total.

```text
signed balance       B = (G - L) / max(G + L, 1e-30)
growth/loss ratio    R = G / max(L, 1e-30)
clamp burden         K = C / max(G + L, 1e-30)
clamp event fraction E = raw-negative events / (steps * cells * PFTs)
inventory retention Q = final inventory / max(initial inventory, 1e-30)
loss shares              ML/L, MQ/L, GR/L
```

Classify a cycle as **loss-dominated** at `B <= -0.10`, **balanced** at
`-0.10 < B < 0.10`, and **growth-dominated** at `B >= 0.10`. Classify clamp
burden as **severe** if either `K >= 0.01` or `E >= 0.01`. Classify biomass as
collapsed if `Q <= 1e-6`. A loss component is dominant if its share exceeds
0.50. These thresholds are diagnostic labels, not target-pass criteria.

The primary read is cycle 8; cycles 1, 2, and 7 determine whether the mechanism
is transient, persistent, or a late-cycle numerical artifact. A cross-AOI
statement requires the same classification in at least two of three AOIs.

## Frozen decision tree

1. **Intrinsic sink imbalance:** cycle 8 is loss-dominated under both light
   constructions in at least two AOIs and clamp burden is not severe. Do not
   tune astronomical-light amplitude or chemical tau. The next target
   construction must address a missing parameter-independent biomass
   transport/replenishment mechanism or reject the reduced box as a periodic
   target generator. This result does not authorize direct Darwin-biomass
   restoring.
2. **Light-driver failure:** fixed light is not loss-dominated but astronomical
   light is loss-dominated in at least two AOIs. Do not run an amplitude sweep;
   scope a physically sourced monthly in-water PAR driver and preregister it.
3. **Numerical-floor failure:** severe clamp burden occurs under both light
   constructions in at least two AOIs. Before changing physics, preregister a
   `dt` refinement that requires convergence of both state and process budgets.
4. **Mixed/other:** none of the above. Stop at the per-PFT attribution and
   preregister the next test from the dominant AOI/PFT mechanism; do not launch
   a recovery factorial.

If multiple branches fire, numerical-floor failure takes precedence, then
light-driver failure, then intrinsic sink imbalance. No branch authorizes B200.

## Reporting boundary

This diagnostic may explain why these two reduced-box targets fail. It cannot
show that seasonal light is irrelevant in Darwin, establish a Darwin process
budget, select a recovery loss, or convert the failed targets into outcomes.
All results remain bounded to this surrogate and the frozen constructions.
