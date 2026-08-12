# Preregistration: source-floor correction of the explicit-zooplankton chain

**Frozen before changing the target runner or rerunning any target artifact:
2026-08-10.** This is a one-change correction to the explicit-zooplankton
seasonal Stage-0 chain. The relational-map query

```text
python scripts/research_map_db.py settled "literal source prey floor corrected seasonal target"
```

returned no settled answer over 543 untruncated `SETTLED` rows.

## Trigger

The preregistered source-conformance audit
`2026-08-10_prereg_explicit_zooplankton_source_conformance.md` passed every
direct official-source and same-era lineage check but rejected the prototype's
numerical denominator guard as an exact representation of Darwin-1's
`phygrazmin` behavior. The source uses

```text
phygrazmin = 1e-10 phosphorus units = 1.2e-8 carbon units
tmpz = max(allphyto - phygrazmin, 0)
```

The same-state relative ingestion discrepancy reached `3.86e-6` in the North
Atlantic and `2.93e-6` in the Southern Ocean, exceeding the frozen `1e-6`
tolerance. The paired endpoint effect was only `2.21e-8` and `3.24e-8`
relative, and all large-predator continuous margins remained negative, but the
correction is required by the preregistered branch rather than selected for a
favorable outcome.

## Exactly one model change

Replace the prototype response

```text
Gmax * B / (B + K)
```

with the literal source response

```text
B_source = B if B > 0 else phygrazmin
tmpz     = max(B_source - phygrazmin, 0)
Gmax * tmpz / (tmpz + K)
```

using `phygrazmin=1.2e-8 mmol C m-3`. Prey allocation retains denominator
`B_source`, exactly matching the source branch. No other constant, forcing,
initial condition, restoring choice, integration setting, scenario, metric,
threshold, or decision rule may change.

## Frozen rerun chain

1. Rerun the five-scenario, 12-cycle seasonal target gate from scratch under
   the correction and write distinct `2026-08-10` report and tensor artifacts.
2. Run the existing independent target verifier against those artifacts.
3. Rerun the cycle-13 endogenous-exclusion audit from the corrected target and
   independently verify it.
4. Rerun the prey-energy decomposition from the corrected target/exclusion
   chain and independently verify it.
5. Rerun the source-conformance receipt against the corrected artifacts. Its
   source-floor comparison must now be exact at the audited rate path.

The old artifacts remain preserved as pre-correction evidence and must not be
silently overwritten.

## Frozen interpretation

- If the corrected Stage-0 target passes all original ten gates, stop and
  reassess before any optimizer; the correction itself does not authorize B200.
- If the target still fails, preserve the original gate failures and report any
  changed numbers without implying replication.
- If large-zooplankton exclusion or its energy-deficit classification changes,
  supersede the old mechanistic finding with the corrected result.
- If those classifications are unchanged within the existing verifier
  tolerances, the correction strengthens source conformance but remains one
  model submission with no out-of-sample replication.

No branch authorizes an n=50 job, a constant-steady factorial, a settled Darwin
endpoint-versus-time-mean choice, or a B200 submission.
