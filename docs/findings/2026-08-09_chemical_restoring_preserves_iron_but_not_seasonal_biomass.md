# Chemical restoring preserves iron but not seasonal biomass

**As of 2026-08-09. Target-only result; no optimizer or B200 job ran.**

## Verdict

A fixed one-year restoring closure on the ten cached chemical/particle tracers
repairs two failures of the forcing-only seasonal twin: DFe2 contrast remains
above its frozen minimum in all three AOIs, and DIC1 stays finite for eight
cycles. It does not produce an admissible climatological target because Chl1
still collapses or becomes pathologically localized, and no AOI passes the
combined target-plus-closure gate.

The result refutes the preregistered one-year **chemical-only** closure as a
complete target construction. It supports only the narrower diagnosis that
missing chemical replenishment caused the iron homogenization and carbon
failure. It does not choose endpoint versus time mean and contains no parameter
recovery result.

## Registered test

The intervention and decision rule were frozen in
[`2026-08-09_prereg_seasonal_twin_chemical_restoring_closure.md`](2026-08-09_prereg_seasonal_twin_chemical_restoring_closure.md).
After each ordinary model step, the ten chemical/particle tracers received

```text
dt * (Darwin_IC - state) / 365.25 days
```

with exactly zero direct restoring on the five phytoplankton states. All target
thresholds were unchanged from the forcing-only test. Closure gross share had
to be <=0.50 and annual inventory turnover <=1.0 for every restored tracer.

## Result

| AOI | cycle-8 DFe2 rel-SD | frozen minimum | cycle-8 DIC1 mean | cycle-8 Chl1 rel-SD | max closure turnover | combined gate |
|---|---:|---:|---:|---:|---:|---|
| EqPac | 0.0691 | 0.0423 | 1573.5 | 0.0038 | 0.00372 | FAIL |
| North Atlantic | 0.1835 | 0.0662 | 1738.9 | 13.8227 | 0.00430 | FAIL |
| Southern Ocean | 0.1760 | 0.1195 | 1742.4 | 6.1533 | 0.00362 | FAIL |

Contrast preservation is durable rather than a first-cycle transient: the
cycle-8 DFe2 values exceed all three frozen minima. DIC1 remains finite where
the no-closure construction became non-finite in cycles 4-5. The phytoplankton
failure is equally clear. EqPac Chl1 mean falls to `3.74e-34` and its relative
SD eventually underflows below the 0.1 sanity floor; North Atlantic Chl1 mean
falls to `3.35e-9` while relative SD rises to 13.82; Southern Ocean relative SD
is 6.15.

The closure itself is small by the inventory-turnover test (all maxima below
0.0043 per cycle), but DFe2 gross closure share approaches exactly 0.50 as the
restoring and endogenous tendencies balance. Floating-point excursions just
above the frozen threshold occur in EqPac and Southern Ocean cycles; they remain
failures because the threshold was preregistered. This detail does not decide
the outcome: Chl1 independently fails by factors of 6-14 or collapses toward
zero.

The strict artifact verifier recomputed all target summaries, all closure
budgets, and all combined decisions from 24 saved cycle tensors and exited 0:

```text
VERIFIED target gate: science_status=FAIL aois=eqpac,natlsubpolar,southernoceanpac cycles=24
```

Metrics:
[`2026-08-09_seasonal_twin_chemical_restoring_target_gate.json`](2026-08-09_seasonal_twin_chemical_restoring_target_gate.json).
Hash-bound receipt:
[`2026-08-09_seasonal_twin_chemical_restoring_target_gate_verification.json`](2026-08-09_seasonal_twin_chemical_restoring_target_gate_verification.json).
The local tensor bundle's SHA-256 and byte size are recorded in both.

## Interpretation boundary

- **Measured:** the one-year chemical closure preserves DFe2 contrast and finite
  DIC but fails the unchanged Chl1 and combined-cycle gates.
- **Supported narrowly:** replenishing chemical inventories is sufficient to
  prevent the iron/carbon collapse seen without closure.
- **Not established:** missing transport is the only mechanism, a one-year
  relaxation represents Darwin transport, or monthly light will fix biomass.

The clean next rival is monthly light, because the box still multiplies all
growth by a fixed `LIGHT=1` while no phytoplankton state is restored. That rival
requires a separate preregistration and cannot alter the chemical closure or
target thresholds.

The failed target correctly stopped the B200/autograd gate. One deterministic
construction, no out-of-sample replication, and no GitHub issue closed.
