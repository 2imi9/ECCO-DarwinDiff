# The projected large zooplankton is endogenously excluded

> **PRE-CORRECTION RESULT - SUPERSEDED FOR QUOTATION.** This audit inherited a
> target without Darwin-1's literal `phygrazmin=1.2e-8 C` response. The corrected
> exclusion remains uniform in all three AOIs; use
> `2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md`.

**As of 2026-08-09. Bounded diagnostic of a failed Stage-0 target; it does not
rehabilitate that target or authorize optimization.**

## Answer

The `Z_large` decay in the source-mirrored 17-state seasonal projection is a
population-dynamic result, not a relative-error artifact on a tiny state. In a
preregistered thirteenth cycle, every retained cell in all three AOIs had a
negative annual discrete log multiplier for the large predator:

| AOI | annual log multiplier, min / median / max | largest annual multiplier | inventory retained in cycle 13 |
|---|---:|---:|---:|
| EqPac | -2.504 / -1.525 / **-1.141** | 0.320x | 0.282 |
| North Atlantic | -5.288 / -2.681 / **-1.045** | 0.352x | 0.322 |
| Southern Ocean | -4.213 / -2.691 / **-0.631** | 0.532x | 0.489 |

The frozen classification threshold was `max Lambda < -0.10`; all three AOIs
therefore classify as **uniformly excluded**. The exact forward-Euler identity

```text
sum_t log(1 + dt * lambda_z(t))
    = log[Z_z(end cycle 13) / Z_z(end cycle 12)]
```

holds to maximum absolute discrepancies of `4.70e-6`, `4.95e-6`, and
`6.00e-6`, respectively, against a preregistered `5e-4` tolerance. Every
Euler factor and endpoint is strictly positive. The diagnosis does not depend
on dividing two near-zero vector norms.

`Z_small` is different: its median annual multiplier is within `3.6e-7` of
zero in every AOI and its total cycle-13 inventory retention is
`0.99997-1.00000`. That contrast is consistent with competitive exclusion of
the large-predator mode in this prey field rather than a general zooplankton
integration failure.

## What this settles

The previous Stage-0 target gate observed large-predator collapse, cycle drift,
and initialization sensitivity. This audit identifies the failed mode: at the
cycle-12 trajectory, the source-projected prey field cannot support `Z_large`
anywhere in the three canonical AOIs. The collapse is endogenous to this
projection.

The audit started from the independently verified central cycle-12 endpoint,
used the same astronomical light and chemical-only restoring, and applied no
zooplankton restoring. The independent verifier reaggregated `220,451` raw
tensor cells, checked both upstream artifact hashes, reconstructed all annual
multipliers and endpoint identities, and reproduced the frozen decision.

## Limits and decision

- This is the reduced no-transport, no-DOC box, not transported ECCO-Darwin.
- It does not show that Darwin's large zooplankton is absent or unimportant.
- It does not permit deleting a source-required predator after seeing it fail.
- Even a one-predator reinterpretation would still fail the preregistered
  EqPac diatom-seasonality and cross-AOI `diatomgraz`-sensitivity gates.
- The target remains `stage0-failed-stop`: no optimizer and no B200.

## Reproduction

```bash
python scripts/analysis/explicit_zooplankton_exclusion_audit.py --compile
python scripts/analysis/verify_explicit_zooplankton_exclusion_audit.py \
  docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.json \
  docs/findings/2026-08-09_explicit_zooplankton_exclusion_audit.pt.gz \
  --source-report docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json \
  --source-bundle docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.pt.gz \
  --receipt docs/findings/2026-08-09_explicit_zooplankton_exclusion_verification.json
```

Preregistration:
[`2026-08-09_prereg_explicit_zooplankton_exclusion_audit.md`](2026-08-09_prereg_explicit_zooplankton_exclusion_audit.md).
