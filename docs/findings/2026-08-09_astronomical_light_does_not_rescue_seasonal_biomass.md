# Astronomical light does not rescue seasonal biomass

**As of 2026-08-09. Target-only result; no optimizer, recovery, or B200 job ran.**

## Verdict

Parameter-free astronomical monthly light does not rescue the seasonally forced
self-twin target when added to the frozen one-year chemical-only closure. The
light fields pass every registered integrity check and DFe2 contrast remains
above its frozen minimum in all three AOIs, but Chl1 leaves the admissible
relative-spatial-SD interval in every basin. No AOI passes the combined target,
closure, and light gate within eight cycles.

This refutes `hy_szn_light` as a complete target construction. It does not show
that seasonal light is irrelevant in Darwin, identify the missing closure, or
choose endpoint versus time-mean loss.

## Registered test

The intervention and decision rule were frozen in
[`2026-08-09_prereg_seasonal_twin_astronomical_light.md`](2026-08-09_prereg_seasonal_twin_astronomical_light.md)
before any light-enabled target cycle ran. The verified chemical closure stayed
at `tau=365.25 d` on the same ten chemical/particle states, with exactly zero
direct restoring on all five phytoplankton fields. The only new driver was the
latitude-derived daily-mean top-of-atmosphere light geometry, normalized to a
12-month arithmetic mean of one in every cell. No amplitude, phase, cloud/PAR,
dust, or restoring-timescale parameter was fitted or swept.

The default-off integrator remains bitwise identical to the pre-light path. A
compiled CUDA smoke test measured a maximum `2.3841858e-7` CPU/GPU difference
in the float32 trigonometric reconstruction, so the preregistration records a
fixed `5e-7` artifact-verification tolerance. That tolerance is below the
unchanged `1e-6` per-cell mean-one integrity gate.

## Result

| AOI | monthly light range | cycle-1 Chl1 rel-SD | cycle-8 DFe2 rel-SD | frozen DFe2 minimum | cycle-8 DIC1 mean | cycle-8 Chl1 mean | cycle-8 Chl1 rel-SD | combined gate |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| EqPac | 0.7869-1.1341 | 0.1520 | 0.0699 | 0.0423 | 1574.0 | 2.12e-34 | 0.0022 | FAIL |
| North Atlantic | 0.0147-2.3104 | 0.8669 | 0.1757 | 0.0662 | 1756.4 | 7.87e-34 | 0.0110 | FAIL |
| Southern Ocean | 0.0150-2.3020 | 0.1629 | 0.1812 | 0.1195 | 1759.7 | 2.69e-22 | 20.6627 | FAIL |

Every light tensor is finite and non-negative. The largest absolute error in a
cell's 12-month mean is `1.19e-7` in EqPac and `2.38e-7` in the two high-latitude
AOIs, comfortably inside the frozen `1e-6` gate.

The first cycle is not itself evidence of a periodic target because it has no
preceding cycle for the stability comparison. By cycle 2, Chl1 rel-SD is
`1.6210 / 4.9346 / 6.6295`, outside `[0.1, 1.0]` in every AOI, and all three
cycles still fail field and DFe2-contrast stability. By cycle 8, DFe2 contrast
and finite DIC are retained, but EqPac and North Atlantic biomass has collapsed
toward zero while Southern Ocean biomass is extremely spatially localized.

The closure inventory-turnover maxima remain below `0.00372`. DFe2 closure
share exceeds the frozen `0.50` boundary by floating-point margins in cycle 8
EqPac (`0.50000006`) and North Atlantic (`0.50000010`); Southern Ocean remains
below it. Those failures are retained, but they do not decide the verdict:
Chl1 independently fails in all three AOIs.

Compared with the separate no-light chemical-closure construction, astronomical
light changes the shape of the biomass failure but not the target decision.
That is a deterministic construction comparison, not an out-of-sample effect
estimate and not evidence that light is generally harmful.

The strict artifact verifier reconstructed the saved monthly light from
latitude, checked its integrity, recomputed all target summaries and closure
budgets, and reproduced all combined decisions from 24 saved cycle tensors:

```text
VERIFIED target gate: science_status=FAIL aois=eqpac,natlsubpolar,southernoceanpac cycles=24
```

Metrics:
[`2026-08-09_seasonal_twin_astronomical_light_target_gate.json`](2026-08-09_seasonal_twin_astronomical_light_target_gate.json).
Hash-bound receipt:
[`2026-08-09_seasonal_twin_astronomical_light_target_gate_verification.json`](2026-08-09_seasonal_twin_astronomical_light_target_gate_verification.json).
The local tensor bundle is `8,447,754` bytes with SHA-256
`3caba6220bcd0199bf91bc1184ddd0562179ade7c0d216445f0a90408c5771e6`.

## Interpretation boundary

- **Measured:** this one deterministic astronomical-light plus chemical-closure
  construction passes light integrity and preserves DFe2/DIC, but fails Chl1
  and the combined target gate in all three AOIs.
- **Refuted:** `hy_szn_light` as the preregistered complete target construction.
- **Not established:** that astronomical rather than in-water PAR is the right
  light driver, that transport or light alone explains the target failure, or
  that any recovery statistic is preferable for Darwin.
- **Blocked:** the loss factorial remains unauthorized until a stable periodic
  target clears Stage 0. The failed gate correctly prevents a B200 submission.

One construction, no out-of-sample replication, no parameter fitting, and no
GitHub issue closed.
