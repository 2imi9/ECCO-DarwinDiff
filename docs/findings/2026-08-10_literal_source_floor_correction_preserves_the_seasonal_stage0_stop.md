# Literal source-floor correction preserves the seasonal Stage-0 stop

**Canonical as of 2026-08-10. Independently verified source-conformance
correction of one deterministic Stage-0 construction. This is not replication,
does not rehabilitate the target, and does not authorize B200.**

## Answer

The explicit-zooplankton projection now implements Darwin-1's literal
`phygrazmin` prey response. The correction makes the audited grazing-rate path
exactly agree with the source-floor oracle over every visited cell and step,
but it does not change any scientific classification:

- the 17-state seasonal target still fails in all three AOIs;
- `Z_large` remains endogenously excluded in all three AOIs;
- the exclusion remains an additive prey-energy deficit, not only a seasonal
  or discrete-time penalty;
- the `diatomgraz` handle remains below its preregistered 5% gate;
- the decision remains `stage0-failed-stop`, with no optimizer and no B200.

The strongest source-audit branch is therefore
`source-conformant-bounded-projection`, not "valid Darwin target."

## Why a rerun was required

The frozen official configuration sets

```text
phygrazmin = 1e-10 phosphorus units = 1.2e-8 carbon units
tmpz = max(allphyto - phygrazmin, 0)
```

The pre-correction projection used `B / (B + K)` with only a numerical
denominator guard. Its same-state ingestion discrepancy was zero in EqPac but
reached `3.856e-6` relative in the North Atlantic and `2.932e-6` in the
Southern Ocean, above the preregistered `1e-6` tolerance. The absolute maximum
was only `1.863e-9 d-1`, and the paired endpoint effects were about `2e-8` to
`3e-8` relative, but the preregistered branch required a fresh corrected chain
rather than an argument from smallness.

Exactly one model expression changed. The corrected response is

```text
B_source = B if B > 0 else phygrazmin
tmpz     = max(B_source - phygrazmin, 0)
Gmax * tmpz / (tmpz + K)
```

Prey allocation retains denominator `B_source`, as in the source. Every other
constant, forcing, initial condition, restoring choice, timestep, scenario,
metric, threshold, and decision rule remained frozen. The corrected run also
used `compiled_step=true`, matching the pre-correction target runtime mode.

## Source receipt

The independent receipt recomputed identities for six official ECCO-Darwin
files at commit `75b8e4337c2fa0c0baa9fa9376590503229121af` and three
same-era corroborating files at commit
`488cb795d7b933ea5a79b3bad84a182d7dbbe1ef`. All nine Git blobs and transport
SHA-256s pass.

Direct official configuration evidence establishes:

- `Gmax=0.625 d-1`, `K=0.085 P * 120 C:P = 10.2 C`;
- `phygrazmin=1.2e-8 C`, `diatomgraz=0.83003`, and linear predator mortality
  `1/30 d-1`;
- the five-prey by two-predator palatability and assimilation matrices;
- shared prey pools, Holling-II response, prey allocation, predator-biomass
  scaling, and assimilation partition;
- `OLD_GRAZE` and `NOTEMP` undefined with `TEMP_VERSION=2`.

The otherwise hidden temperature-function implementation is not in the
official overlay. The matching-signature 2018 package independently
corroborates that grazing, linear mortality, and quadratic mortality
temperature multipliers are exactly one under `TEMP_VERSION=2`, while both
quadratic predator mortalities are zero. This remains labeled
`same-era-corroboration`, not direct bit-for-bit provenance.

After correction, maximum absolute ingestion difference, maximum relative
ingestion difference, and maximum tolerance ratio are all exactly zero in
every AOI. The independent verifier reparsed the bundled Fortran, rebuilt the
source evidence, checked all upstream hashes, and reconstructed **323,519**
trajectory tensor cells.

## Corrected target

The independently reconstructed target decision is unchanged:

| AOI | diatom / initial | small-Z / initial | large-Z / initial | cycle 11-to-12 max rel-L2 | max IC-flank rel-L2 | diatomgraz log response |
|---|---:|---:|---:|---:|---:|---:|
| EqPac | 1.026412 | 26.2559 | 3.621e-7 | 0.7061 | 0.8441 | -0.03012 |
| North Atlantic | 0.868715 | 15.2059 | 2.270e-7 | 0.6636 | 0.7992 | -0.02057 |
| Southern Ocean | 0.865890 | 15.0402 | 1.250e-5 | 0.4940 | 0.6941 | -0.02034 |

All gate pass/fail bits match the pre-correction artifact. Numerical,
chemical-closure, DFe, and light gates pass; stability, plankton viability,
and initialization robustness fail in every AOI. The cross-AOI
`diatomgraz` sensitivity gate also fails. The target verifier independently
checked **4,681,005** tensor cells and reproduced the carbon-partition residual
of `1.041e-17`.

The correction changes diatom retention by at most `2.99e-9` and changes the
reported large-predator cycle-13 log maxima by at most `2.38e-7`. These are
numerical deltas within unchanged classifications, not replication evidence.

## Corrected blocker lattice

The eight-node post-hoc waiver lattice was rerun from the independently
verified corrected target. Its complete Boolean lattice is exactly identical
to the pre-correction artifact:

- `0/3` singleton waivers pass;
- `0/3` two-waiver sets pass;
- only the `1/1` triple waiver passes mechanically;
- the minimum remains all three logically separate blocker groups: source-
  required `Z_large`, EqPac seasonality, and the global parameter handle.

Dropping `Z_large` alone still leaves EqPac monthly diatom CV `0.034204 < 0.05`
and all absolute parameter responses `0.02034-0.03012 < log(1.05)`. The
independent verifier checked all eight nodes and bound the corrected target
report and verification receipt. The lattice remains a measure of post-hoc
distance from acceptance, not a target rescue.

## Corrected exclusion mechanism

The cycle-13 exclusion and prey-energy verifiers checked **220,451** and
**564,011** raw tensor cells, respectively. `Z_large` remains below continuous
replacement in every retained cell:

| AOI | gross gain max | mortality integral | continuous margin max | exact log max |
|---|---:|---:|---:|---:|
| EqPac | 11.059933 | 12.2 | -1.140067 | -1.140537 |
| North Atlantic | 11.160408 | 12.2 | -1.039592 | -1.044882 |
| Southern Ocean | 11.573926 | 12.2 | -0.626074 | -0.630779 |

The maximum change in continuous margin from the pre-correction energy audit
is `3.96e-8`. The corrected branch remains `prey-field-energy-deficit`.

## Projection boundary

Source conformance is intentionally bounded to the audited grazing closure and
visited support. The projection still differs from full Darwin in five
declared ways:

1. It has no DOC state and routes dissolved grazing remainder to POC.
2. Zooplankton are surface-only in a two-layer box.
3. The phytoplankton temperature multiplier is approximate and
   mean-neutralized.
4. Chemical states are restored toward frozen references.
5. Integration uses forward Euler with a nonnegative state clamp.

The result identifies insufficiency of the included prey field. It does not
identify which omitted Darwin mechanism would close the energy gap, choose a
Darwin endpoint versus time mean, support a one-predator post-hoc model, or
establish parameter recovery. It also does not quote or rehabilitate the
excluded Southern Ocean arm of loss-twin job 320993; that grading-coverage
question is separate.

## Decision

The corrected chain is durable but remains one model submission with no
out-of-sample replication:

```text
source audit:  source-conformant-bounded-projection
target gate:   stage0-failed-stop
exclusion:     endogenous-large-predator-exclusion
energy audit:  prey-field-energy-deficit
optimizer:     not run
B200:          false
```

## Artifacts

- correction preregistration:
  `docs/findings/2026-08-10_prereg_source_floor_corrected_explicit_zooplankton_chain.md`
- source-audit preregistration:
  `docs/findings/2026-08-10_prereg_explicit_zooplankton_source_conformance.md`
- corrected target report/bundle/receipt:
  `docs/findings/2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected.{json,pt.gz}` and
  `docs/findings/2026-08-10_seasonal_twin_explicit_zooplankton_source_floor_corrected_verification.json`
- corrected exclusion report/bundle/receipt:
  `docs/findings/2026-08-10_explicit_zooplankton_exclusion_source_floor_corrected.{json,pt.gz}` and
  `docs/findings/2026-08-10_explicit_zooplankton_exclusion_source_floor_corrected_verification.json`
- corrected energy report/bundle/receipt:
  `docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected.{json,pt.gz}` and
  `docs/findings/2026-08-10_explicit_zooplankton_prey_energy_source_floor_corrected_verification.json`
- post-correction source report/bundle/receipt:
  `docs/findings/2026-08-10_explicit_zooplankton_source_conformance_postcorrection.{json,pt.gz}` and
  `docs/findings/2026-08-10_explicit_zooplankton_source_conformance_postcorrection_verification.json`
- corrected blocker-lattice report/receipt:
  `docs/findings/2026-08-10_seasonal_twin_blocker_minimality_source_floor_corrected.json` and
  `docs/findings/2026-08-10_seasonal_twin_blocker_minimality_source_floor_corrected_verification.json`
- independent source verifier:
  `scripts/analysis/verify_explicit_zooplankton_source_conformance.py`

The Aug 9 target, exclusion, energy, and blocker-lattice notes and the first
Aug 10 source-conformance artifact are retained as pre-correction evidence but
are superseded for model specification and quotation by this finding.
