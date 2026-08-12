# Preregistration: astronomical monthly light for the seasonal twin

**Scientific construction and decision rule frozen 2026-08-09 before any
astronomical-light target cycle was run.** A technical CPU/GPU reconstruction
tolerance was appended after the compiled smoke and before the production run,
explicitly labelled below; no scientific threshold or forcing choice changed.

## Relational state

The no-closure seasonal target failure is settled. The one-year chemical-only
closure preserves DFe2 contrast and finite DIC but fails to sustain admissible
Chl1. This test asks whether the missing time-varying growth driver, rather than
direct biomass restoring, supplies the remaining periodic structure.

The map query run before this preregistration was:

```text
python scripts/research_map_db.py settled "monthly light seasonal self-twin"
```

It returned no settled row. The registered hypothesis is `hy_szn_light`; no
evidence edge exists until the target and artifact verifier complete.

## Frozen light construction

Keep the verified one-year chemical closure unchanged and continue to apply
exactly zero restoring to all five phytoplankton fields. Add a dimensionless
monthly light multiplier to all five growth terms using daily-mean
top-of-atmosphere insolation geometry.

For each AOI latitude `phi` and Gregorian month midpoint day `d`:

```text
delta = asin(sin(23.439 deg) * sin(2*pi*(d - 80)/365.25))
H0    = acos(clamp(-tan(phi)*tan(delta), -1, 1))
Q     = H0*sin(phi)*sin(delta) + cos(phi)*cos(delta)*sin(H0)
L_m   = Q_m / mean_month(Q)
```

Use the midpoints of the 12 non-leap Gregorian calendar months. Clamp `Q` at
zero before normalization. Thus every ocean cell has a 12-month arithmetic mean
light multiplier of exactly 1, preserving the existing `LIGHT=1` annual mean.
There is no fitted amplitude, phase, cloud correction, PAR scaling, per-basin
normalization, or result-dependent light ladder.

The model step gains an optional `light` argument defaulting to 1. Existing
constant-light paths must remain bitwise identical. The astronomical field is
fixed by latitude and month and independent of all learned parameters.

## Gates

All prior gates remain unchanged:

- cycle field relative-L2 <=1%;
- DFe2 rel-SD change <=5%;
- DFe2 rel-SD >=0.0423 / 0.0662 / 0.1195;
- Chl1 rel-SD in [0.1, 1.0];
- all quantities finite;
- chemical closure share <=0.50 and turnover <=1.0 for every restored tracer;
- exact zero closure on every phytoplankton field.

Additional light integrity gates:

- finite and non-negative at every ocean cell/month;
- per-cell 12-month mean differs from 1 by <=1e-6;
- same deterministic formula in target generation and prediction;
- default-off path is bitwise identical to the pre-light integrator.

**Implementation clarification before the production target run.** The compiled
CUDA smoke target and CPU verifier differed by at most `2.3841858e-7` in the
saved float32 light multiplier because their transcendental kernels are not
bitwise identical. The artifact verifier therefore uses a frozen absolute
reconstruction tolerance of `5e-7`, below the already frozen `1e-6` per-cell
mean-one gate. The legacy default-off integrator still requires bitwise equality.

## Decision rule

- **Supports `hy_szn_light` at target level:** all three AOIs pass the combined target,
  closure, and light-integrity gates within eight cycles.
- **Refutes this astronomical-light construction:** any AOI fails any unchanged
  or light-integrity gate. Do not tune amplitude or restoring timescale afterward.
- **Non-diagnostic:** legacy default behavior changes, light depends on learned
  parameters, or artifact verification fails.

A pass authorizes only a one-seed/one-epoch B200 autograd cost gate. It does not
choose endpoint versus time mean, authorize n=50, or establish recovery.

No dust seasonality, direct phytoplankton restoring, or GitHub issue closure is
part of this test.
