# Preregistration: seasonal-target blocker minimality audit

**Frozen 2026-08-09 before implementation and before calculating the waiver
lattice.** The already-published failed-gate pattern is known; this is a
logical audit of that immutable result, not a blinded biological experiment.
The relational-map query

```text
python scripts/research_map_db.py settled "seasonal target blocker minimal waiver"
```

returned no answer over 541 untruncated SETTLED rows.

## Question

After diagnosing the `Z_large` failure, can one post-hoc simplification make
the explicit-grazer projection satisfy its frozen Stage-0 target gate, or do
logically separate blockers remain?

## Frozen source

- Use only the canonical independently verified explicit-zooplankton target
  report and verification receipt.
- Bind both files by SHA-256.
- Do not rerun the model, tune a threshold, alter an AOI, or inspect another
  parameter span.
- Reconstruct the original preregistration's separate criteria even though
  the machine report nests community viability and seasonality in one object.

## Frozen blocker groups

The lattice has exactly three possible waivers:

1. `drop_large_predator_obligations`: remove only `Z_large` from the
   cycle-stability maximum, community-retention conjunction, and
   initial-condition-robustness maximum. Do not alter any raw state or any
   other predator/community check. This is a deliberately forbidden post-hoc
   model reduction used only to test logical sufficiency.
2. `waive_eqpac_seasonality`: waive only EqPac's `monthly_diatom_cv >= 0.05`
   criterion. North Atlantic and Southern Ocean seasonality remain required.
3. `waive_parameter_handle`: waive only the global requirement that at least
   two AOIs have `abs(log[D(1.1g)/D(0.9g)]) >= log(1.05)` with common sign.

Enumerate all `2^3 = 8` subsets. For every subset, reevaluate the complete
frozen Stage-0 conjunction. Numerical integrity, light integrity, chemical
closure, DFe structure, diatom retention/positivity, non-large community
retention, and dominance are never waivable.

## Frozen decision

- If any singleton passes, report a one-group blocker.
- Otherwise, if any pair passes, report the lexicographically sorted minimal
  passing pair(s).
- Otherwise, if only the three-waiver subset passes, report
  `three-logically-separable-blocker-groups`.
- If even all three waivers fail, report `additional-unmodeled-blocker`.

Regardless of branch, `target_rehabilitated=false` and
`b200_authorized=false`. A lattice node that passes after waivers is not a
scientific target; it measures how many frozen obligations would have to be
discarded after seeing the outcome.
