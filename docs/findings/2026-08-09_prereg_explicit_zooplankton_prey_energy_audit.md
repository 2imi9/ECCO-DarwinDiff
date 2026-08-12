# Preregistration: explicit-zooplankton prey-energy audit

**Frozen 2026-08-09 before implementation or prey-channel measurement.** The
required map query

```text
python scripts/research_map_db.py settled "large zooplankton prey gain budget seasonal projection"
```

returned no answer over 542 untruncated `SETTLED` rows. The standing cycle-13
audit already establishes that `Z_large` has a negative exact annual multiplier
in every retained cell. This follow-up may explain that failed mode; it may not
retest, waive, or rehabilitate the target.

## Question

Which of the five projected prey channels supplies each predator's realized
specific gain, and is `Z_large` below replacement even under the additive
continuous energy budget, or only after temporal variation and the discrete
Euler multiplier are applied?

## Frozen inputs

The audit is bound by SHA-256 to all four upstream artifacts:

- the independently verified explicit-grazer Stage-0 report and tensor bundle;
- the independently verified cycle-13 exclusion report and tensor bundle.

For each canonical AOI, start from the central `ic_0p10` cycle-12 endpoint and
rerun exactly cycle 13 with the same astronomical light, chemical-only
restoring, Carroll truth, `dt=0.25 d`, 122 steps/month, and zero zooplankton
restoring. The live mask and starting predator state must equal the upstream
bundle exactly. The rerun's monthly exact log multipliers and cycle-13 predator
endpoint must reproduce the exclusion artifact within the frozen tolerances
below.

## Frozen calculation

For prey `p` and predator `z`, at every step compute the source-defined terms

```text
w_pz    = palatability_pz * P_p
B_z     = sum_p w_pz
I_z     = Gmax * B_z / (B_z + K)
u_pz    = I_z * (w_pz / B_z) * assimilation_pz
q_z     = sum_p u_pz
lambda_z = q_z - 1/30
```

where `u_pz` is the prey-specific contribution to predator specific gain in
`d^-1`. Accumulate, per month and cell,

```text
G_pz       = sum_steps dt * u_pz
G_z        = sum_p G_pz
M_z        = 12 * 122 * 0.25 / 30 = 12.2
C_z        = G_z - M_z
Lambda_z   = sum_steps log(1 + dt * lambda_z)
```

`C_z` is an additive continuous replacement margin. `Lambda_z` is the exact
forward-Euler population multiplier and is not decomposed by prey. Report the
annual gain share of every prey, plus the combined large-prey share
`{diatom,lge}` and small-prey share `{syn,proLL,proHL}`. A share is descriptive;
it does not license deleting a prey or predator.

## Integrity gates

1. All four upstream hashes match, masks and start states match exactly, every
   saved tensor is finite, every gain contribution is nonnegative, and every
   Euler factor and predator endpoint is strictly positive.
2. The five prey-specific gain contributions sum to the closure's total
   predator specific gain at every aggregation, with maximum absolute error
   `<=5e-5`.
3. The annual gain equals the sum of the 12 monthly prey contributions to
   float64 recomputation tolerance, and the mortality integral is exactly
   `12.2` within `1e-7`.
4. `Lambda_z` matches `log[Z_z(end cycle 13)/Z_z(end cycle 12)]` within
   `5e-4`, preserving the prior exclusion audit's identity gate.
5. Against the upstream cycle-13 artifact, maximum absolute difference is
   `<=5e-4` for monthly exact log multipliers and `<=2e-5` relative-L2 for the
   predator endpoint. A failure is an implementation/reproduction discrepancy,
   not a prey-budget result.

## Frozen branches

Classify each AOI from the masked `Z_large` continuous margin:

- `continuous-energetic-deficit` when `max(C_large) < -0.10`;
- `discrete-or-variance-penalty` when the exact multiplier remains uniformly
  excluded but at least one cell has `C_large >= -0.10`;
- `inconsistent-with-prior-exclusion` when the exact multiplier no longer
  reproduces the registered exclusion class.

The cross-AOI decision is `prey-field-energy-deficit` only if all integrity
gates pass and all three AOIs are `continuous-energetic-deficit`. Mixed AOI
branches remain mixed and must be reported without averaging them away.

## Prohibited inference

This audit is bounded to the failed 17-state, no-transport, no-DOC projection.
It cannot establish a Darwin food-web budget, infer a missing prey state,
authorize dropping `Z_large`, waive EqPac seasonality or the parameter-handle
gate, choose endpoint versus time mean, run an optimizer, or authorize B200.
