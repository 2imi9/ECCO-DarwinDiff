# No single post-hoc waiver rescues the seasonal target

> **PRE-CORRECTION RESULT - SUPERSEDED FOR QUOTATION.** The eight-node lattice
> was rerun against the literal-source-floor-corrected target and is exactly
> identical. Use
> `2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md`
> for the corrected artifact hashes.

**As of 2026-08-09. Independently verified logical audit of the frozen Stage-0
result; no target is rehabilitated and no B200 work is authorized.**

## Answer

The failed explicit-grazer projection is not one post-hoc simplification away
from a valid seasonal target. Its immutable acceptance result contains three
logically separable blocker groups:

1. the source-required `Z_large` obligations;
2. EqPac diatom seasonality; and
3. the cross-AOI `diatomgraz` parameter handle.

A preregistered audit enumerated all eight subsets of those three waivers. No
singleton passes. No pair passes. Only the all-three node passes the Boolean
acceptance conjunction, and that node is explicitly a forbidden post-hoc
construction rather than a scientific target.

## Why the large-predator diagnosis is not enough

Removing only `Z_large` from the three criteria it controls makes all of those
reduced checks pass:

| AOI | stability max without `Z_large` (gate 0.01) | IC max without `Z_large` (gate 0.05) | max community share without `Z_large` (gate 0.95) |
|---|---:|---:|---:|
| EqPac | 7.27e-7 | 4.55e-8 | 0.644 |
| North Atlantic | 1.15e-4 | 7.13e-4 | 0.518 |
| Southern Ocean | 6.70e-5 | 1.50e-3 | 0.515 |

Every retained plankton state also clears its frozen inventory-retention gate.
This confirms that the stability and initialization failures are localized to
the excluded large-predator mode.

Two separate failures remain unchanged:

- EqPac monthly diatom CV is `0.0342`, below the frozen `0.05` seasonality
  threshold.
- Absolute `diatomgraz` log responses are `0.0301 / 0.0206 / 0.0203` in
  EqPac / North Atlantic / Southern Ocean, all below `log(1.05)=0.04879`, so
  zero of the required two AOIs qualify.

## Complete waiver lattice

| Post-hoc waiver set | Remaining blocker |
|---|---|
| none | all three groups |
| drop `Z_large` obligations | EqPac seasonality + parameter handle |
| waive EqPac seasonality | `Z_large` obligations + parameter handle |
| waive parameter handle | `Z_large` obligations + EqPac seasonality |
| drop `Z_large` + waive EqPac seasonality | parameter handle |
| drop `Z_large` + waive parameter handle | EqPac seasonality |
| waive EqPac seasonality + parameter handle | `Z_large` obligations |
| all three | mechanical pass, scientifically forbidden |

The independent verifier reconstructed the original atomic criteria from the
source report, checked all eight lattice nodes, and rejected tampered pair-pass
and minimum-waiver decisions. The source report is bound to its earlier raw
tensor verification receipt by SHA-256.

## Interpretation and limits

This is a relational-algebra result over a verified artifact: selection,
projection, and conjunction establish the minimum waiver cardinality under the
frozen gate definitions. “Logically separable” does not mean the three failures
have experimentally independent biological causes. A future model could alter
more than one metric through one defensible mechanism, but that would be a new
preregistered target construction requiring new evidence.

The all-three lattice node cannot be used to justify a one-grazer optimizer.
It succeeds only by discarding a source-mirroring obligation, an observed
seasonality failure, and the very sensitivity needed for parameter recovery.
The correct branch remains `stage0-failed-stop`: no optimizer and no B200.

## Reproduction

```bash
python scripts/analysis/seasonal_twin_blocker_minimality_audit.py
python scripts/analysis/verify_seasonal_twin_blocker_minimality.py \
  docs/findings/2026-08-09_seasonal_twin_blocker_minimality_audit.json \
  --source docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_gate.json \
  --verification docs/findings/2026-08-09_seasonal_twin_explicit_zooplankton_verification.json \
  --receipt docs/findings/2026-08-09_seasonal_twin_blocker_minimality_verification.json
```

Preregistration:
[`2026-08-09_prereg_seasonal_twin_blocker_minimality_audit.md`](2026-08-09_prereg_seasonal_twin_blocker_minimality_audit.md).
