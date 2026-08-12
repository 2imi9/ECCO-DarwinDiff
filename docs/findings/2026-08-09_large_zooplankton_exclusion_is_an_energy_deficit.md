# The projected large-zooplankton exclusion is an energy deficit

> **PRE-CORRECTION RESULT - SUPERSEDED FOR QUOTATION.** This audit inherited a
> target without Darwin-1's literal `phygrazmin=1.2e-8 C` response. The corrected
> prey-energy classification and margins are unchanged at scientific precision;
> use `2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md`.

**As of 2026-08-09. Independently verified diagnostic of an already failed
Stage-0 target. No optimizer or B200 job ran, and the target remains excluded.**

## Answer

The exact source-projected prey field does not supply enough annual gross
specific gain to replace `Z_large` mortality in any retained cell of the three
canonical AOIs. This deficit exists in the additive continuous rate budget,
before the seasonal-variance and forward-Euler log-multiplier penalties are
applied.

The fixed mortality integral over the model's 366-day cycle is

```text
12 months * 122 steps/month * 0.25 d/step * (1/30 d^-1) = 12.2
```

Against that replacement requirement, the cycle-13 large-predator budget is:

| AOI | gross gain integral min / median / max | continuous margin min / median / max | exact log multiplier min / median / max | median gain from large prey |
|---|---:|---:|---:|---:|
| EqPac | 9.698 / 10.675 / **11.060** | -2.502 / -1.525 / **-1.140** | -2.504 / -1.525 / **-1.141** | 68.48% |
| North Atlantic | 6.933 / 9.529 / **11.160** | -5.267 / -2.671 / **-1.040** | -5.288 / -2.681 / **-1.045** | 62.90% |
| Southern Ocean | 8.007 / 9.522 / **11.574** | -4.193 / -2.678 / **-0.626** | -4.213 / -2.691 / **-0.631** | 62.89% |

Every maximum continuous margin is below the preregistered `-0.10` threshold,
so all three AOIs take the frozen `continuous-energetic-deficit` branch. The
cross-AOI decision is `prey-field-energy-deficit`.

## The diets are differentiated, but the large-prey channel is insufficient

The result is not caused by making the two predator diets identical. The
source-mirrored closure partitions their realized gain strongly by prey size:

- `Z_small` receives 95.36% of median gain from `{syn, proLL, proHL}` in EqPac
  and 96.31% in both North Atlantic and Southern Ocean;
- `Z_large` receives 68.48% of median gain from `{diatom, lge}` in EqPac and
  62.90% in the other two AOIs.

Despite that intended niche split, the large-prey-weighted channel remains
below replacement everywhere. By contrast, `Z_small` stays near its dynamic
replacement surface: its median continuous margins are `+0.00011`, `+0.02023`,
and `+0.02086`, while the exact median annual log multipliers are within
`3.5e-7` of zero. The small-predator result also shows why the exact discrete
multiplier is kept adjacent to the additive budget: temporal variation and
`log(1 + dt*lambda)` can consume a small positive continuous margin. They are
not needed to explain the much larger `Z_large` deficit.

## Verification

The runner was preregistered before the prey-channel tensors were measured. It
reran cycle 13 from the exact verified cycle-12 endpoint and bound itself by
SHA-256 to both upstream report/bundle pairs. The independent verifier imported
no runner code and reconstructed all summaries and decisions from **564,011 raw
tensor cells**.

Maximum discrepancies were:

- prey-specific contributions versus total specific gain: `5.94e-8` against
  the frozen `5e-5` gate;
- exact log multiplier versus endpoint log ratio: `5.66e-6` against `5e-4`;
- rerun versus the prior monthly exclusion multipliers: `1.58e-6` against
  `5e-4`;
- rerun versus the prior cycle-13 predator endpoint: relative L2 exactly `0.0`
  in every AOI.

All contributions are finite and nonnegative; every Euler factor and endpoint
is strictly positive. Adversarial tests reject a changed prey partition, an
upstream hash mismatch, and any attempt to authorize B200.

## Limits

- This is the failed no-transport, no-DOC 17-state projection, not a Darwin
  food-web budget.
- The audit establishes an energy deficit under the included prey channels. It
  does not identify which omitted transported-Darwin process, state, or niche
  would close it.
- It does not authorize adding prey, changing assimilation, restoring
  zooplankton, deleting `Z_large`, or waiving the EqPac seasonality and global
  parameter-handle gates after seeing the result.
- It does not rehabilitate the seasonal target or choose endpoint versus time
  mean. The decision remains `stage0-failed-stop`.

## Reproduction

```bash
python scripts/analysis/explicit_zooplankton_prey_energy_audit.py --compile
python scripts/analysis/verify_explicit_zooplankton_prey_energy_audit.py \
  docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.json \
  docs/findings/2026-08-09_explicit_zooplankton_prey_energy_audit.pt.gz \
  --source-target-report docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json \
  --source-target-bundle docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz \
  --source-exclusion-report docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json \
  --source-exclusion-bundle docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz \
  --receipt docs/findings/2026-08-09_explicit_zooplankton_prey_energy_verification.json
```

Preregistration:
[`2026-08-09_prereg_explicit_zooplankton_prey_energy_audit.md`](2026-08-09_prereg_explicit_zooplankton_prey_energy_audit.md).
