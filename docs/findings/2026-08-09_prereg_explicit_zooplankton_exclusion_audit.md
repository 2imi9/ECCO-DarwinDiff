# Preregistration: explicit-zooplankton exclusion audit

**Frozen 2026-08-09 before implementation or cycle-13 measurement.** The map
query

```text
python scripts/research_map_db.py settled "large zooplankton exclusion seasonal twin"
```

returned no answer over 540 untruncated SETTLED rows.

## Question

The preregistered two-grazer target fails because `Z_large` approaches zero
in every AOI. Is that decay the expected population-dynamic response to the
projected prey field, or a numerical artifact of measuring relative changes
on a tiny state?

## Frozen calculation

- Load the independently verified canonical explicit-zoo tensor bundle.
- For each AOI, start from the central (`f_z=0.10`, Carroll truth) cycle-12
  endpoint and run exactly one additional astronomical-light cycle with the
  identical chemical restoring reference, step, forcing, and `dt=0.25 d`.
- Before every Euler step, derive each predator's biomass-independent specific
  gain from the source closure:

```text
B_z       = sum_p a_pz P_p
q_z       = Gmax * B_z/(B_z + K) * sum_p(e_pz a_pz P_p)/B_z
lambda_z  = q_z - 1/30
```

- Record per cell and predator the exact discrete annual log multiplier
  `Lambda_z = sum_t log(1 + dt*lambda_z(t))`, positive-rate event count, and
  minimum Euler factor.
- Independently compare `Lambda_z` with
  `log[Z_z(end cycle 13)/Z_z(end cycle 12)]`. No zooplankton restoring is
  allowed, so these are the same relation up to float32 accumulation.

## Gates and branches

1. Every rate, log multiplier, state, and Euler factor is finite; every Euler
   factor is strictly positive.
2. No predator state is clamped to zero and its restoring increment is exactly
   zero.
3. Maximum absolute discrepancy between integrated and endpoint log ratios is
   `<=5e-4`.
4. Classify a predator/AOI as uniformly excluded when the maximum cellwise
   annual log multiplier is `<-0.10`, uniformly viable when the minimum is
   `>+0.10`, otherwise mixed/near-neutral.

Decision branches:

- `Z_large` uniformly excluded in all three AOIs and the endpoint identity
  passes: **endogenous competitive exclusion in this projection**.
- Any nonnegative/mixed large-predator exponent with continued global decay:
  **implementation or unresolved transient**, not competitive exclusion.
- Different AOI classifications: **spatially mixed large-predator viability**.

This audit cannot rehabilitate the failed target, remove `Z_large` post hoc,
authorize an optimizer, or authorize B200. It only diagnoses the failed mode.
