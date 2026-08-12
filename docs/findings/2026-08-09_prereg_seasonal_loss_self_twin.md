# Preregistration: seasonally forced loss self-twin

**Frozen 2026-08-09 before target-gate or recovery results were inspected.**

**Harness amendment, frozen before the corrected Stage-0 run:** the first local
Stage-0 invocation exposed that `carroll6_5pft_2layer.USE_EPPLEY_T` defaults to
false even though `scripts/configs/flagship_geo1.sh` pins it to true. That output
is invalid for inference because monthly temperature then affected carbonate but
not biology. The corrected gate pins flagship parity explicitly:
`USE_EPPLEY_T=true`, `A_E_EPPLEY=0.0633`, and `T_REF_EPPLEY=15.0`. No target,
stability, contrast, sanity, recovery, or cost threshold changed after seeing the
invalid output.

## Question and relational-map state

The settled measurement is a replicated basin-by-loss swap: under the real
Darwin climatological target, a time-mean loss recovers the equatorial-Pacific
iron pair while the endpoint loss recovers `scav_rat` in the Southern Ocean.
The correct comparison remains unknown. The constant-forcing self-twin does not
decide it because its quasi-steady long target removes the DFe2 spatial contrast
that anchors `scav_rat`.

The map query run before this preregistration was:

```text
python scripts/research_map_db.py settled "seasonally forced self-twin"
```

It returned no settled row. In relational terms, this experiment adds one open
`HYPOTHESIS` row but no `EVIDENCE` or `SUPPORTS` edge yet:

```text
H_new <- abduce(SETTLED_loss_swap, SETTLED_loss_choice_unknown,
                E_constant_twin_double_null)
E_new <- empty until verify_run = 0 and the preregistered grader runs
SUPPORTS_new <- empty until E_new exists
```

This is a test of temporal-statistic matching, not another constant-steady
factorial and not a search for the best-looking loss.

## Frozen target construction

1. Use the existing monthly ECCO-Darwin climatologies for temperature,
   salinity, and wind in each verified AOI. Light remains constant because the
   current two-layer box does not expose a monthly light input. No light-response
   mechanism will be inferred from this experiment.
   Temperature-dependent growth uses the canonical flagship Eppley gate, pinned
   on with `A_E_EPPLEY=0.0633` and `T_REF_EPPLEY=15.0`.
2. Start from the existing AOI-specific Darwin initial-condition cache and use
   Carroll's published six-parameter optimum as truth.
3. Integrate continuous 12-month cycles at `dt=0.25 d` and 122 steps per month.
   Spin-up cycles are excluded from every reported target statistic.
4. The frozen mean statistic is the **all-step mean of the recorded cycle**:
   every post-step state in all 12 months receives equal weight. The mean of 12
   month-end snapshots is diagnostic only and may not replace it after results
   are seen.
5. The endpoint statistic is the final state of the same recorded cycle.
6. Derived CO2 flux is evaluated from the selected state statistic using the
   annual-mean environmental readout, identically in target and prediction. It
   is not interpreted as an exact time mean of instantaneous air-sea flux.
7. Twin anchors sample the synthetic truth at the real anchor masks. For the
   Southern Ocean, `DANIELS_RPICPOC_W=0` and `POSI_W=0` are explicit; that arm is
   iron-only and no calcite or opal result may be quoted from it.

## Stage 0: target-only gate

No optimizer may be launched unless the target itself passes all gates:

1. **Cycle stability.** Between the last two recorded cycles, masked relative
   L2 change is at most 1% for DFe1, DFe2, the five phytoplankton fields, POC1,
   PIC1, DIC1, and ALK1. DFe2 relative spatial standard deviation changes by at
   most 5%.
2. **Iron contrast.** The all-step target retains at least half of the existing
   200-step endpoint DFe2 contrast: EqPac >= 0.0423, North Atlantic >= 0.0662,
   and Southern Ocean >= 0.1195.
3. **Chl1 sanity.** Diatom/Chl1 relative spatial standard deviation lies in
   [0.1, 1.0], excluding the constant-long target's pathological 4-8 range.
4. **Statistic audit.** The JSON records endpoint, all-step mean, and
   month-endpoint mean summaries separately. Missing or non-finite values fail.

Failure of any gate is a scientific result about target construction and stops
the recovery experiment. Thresholds will not be relaxed in this submission.

## Stage 1: minimum discriminating design

For each basin, use the same trainer, truth, initialization distribution, and
loss weights in these four states:

| arm | synthetic target | fitted prediction | role |
|---|---|---|---|
| `end_end` | seasonal cycle endpoint | seasonal cycle endpoint | matched machinery control |
| `mean_mean` | all-step cycle mean | all-step cycle mean | matched test |
| `mean_end` | all-step cycle mean | seasonal cycle endpoint | decisive mismatch |
| `null` | same target bundle | untrained network | architecture-matched null |

The primary quantity is `scav_rat` recovery at relative error <=0.20 under
arithmetic, geometric, and median collapses; geometric is primary. The arm is
interpretable only if its verifier exits 0 and all expected artifacts exist.
`alpfe` is the positive iron control. Other parameters are descriptive only.

The temporal-matching hypothesis is supported in a basin only if:

1. `mean_mean` beats its paired null and reaches at least 40/50 `scav_rat`
   recoveries under all three poolers;
2. `mean_end` is at least 20/50 lower than `mean_mean`, with paired McNemar
   p < 0.05; and
3. `end_end` reaches at least 40/50, showing that the endpoint readout itself is
   not broken.

If a matched arm fails its null, the self-twin is non-diagnostic rather than
evidence for the other loss. If the mismatch is not worse, temporal matching is
falsified as the explanation of the basin swap. Basin heterogeneity is reported
as heterogeneity; no aggregate >=2-of-3 count may hide it.

This is one submission with no out-of-sample replication. Even a clean result
is unreplicated and cannot become a settled Darwin claim from this run alone.

## Five-hour B200 stop rules

The wall-clock envelope starts with implementation and ends with harvested,
verified artifacts; queue wait is reported separately.

1. Run local unit/small-step tests first. Then run the native-resolution target
   gate on one B200 with no optimizer.
2. Before n=50, run one seed for one epoch through each distinct seasonal
   prediction path with `torch.compile`; record wall time and peak allocated GPU
   memory.
3. Abort scale-up if one task projects beyond the remaining three-hour compute
   window, peak memory exceeds 160 GiB, any gradient is non-finite, or target
   construction fails Stage 0.
4. Batch seeds and use independent single-B200 Slurm tasks. Do not reserve a
   B200 while performing CPU-only grading, map generation, or documentation.
5. Reserve at least 45 minutes for `verify_run`, grading, relational-map edges,
   and an explicit one-submission/no-replication finding. If n=50 cannot finish
   inside the envelope, stop at the preregistered scout size and make no recovery
   claim.

## Falsifiers and prohibited pivots

- Target gate failure falsifies this target construction, not seasonal forcing
  in general.
- `mean_mean` failing its null makes the recovery experiment non-diagnostic.
- `mean_end` matching `mean_mean` falsifies temporal-statistic matching as the
  cause of the loss swap.
- No switch from all-step mean to month-endpoint mean is allowed after target or
  fit results are visible.
- No extra constant-steady factorial, light intervention, threshold search, or
  unregistered loss arm may be submitted first.
- No GitHub issue is closed by this experiment.
