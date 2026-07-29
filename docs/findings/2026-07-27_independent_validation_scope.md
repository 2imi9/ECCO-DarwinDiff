# Independent validation via B-SOSE / TPOSE / ASTE-BGC — scoping (#163)

**Date:** 2026-07-27 · **Status:** scoping only, nothing run · **Source:** Carroll, *ECCO-Darwin
Development Update*, ECCO Annual Meeting 2024, slide 2

## Why this exists

#163 calls independent validation the project's #1 scientific gap: everything we compare against is
Darwin's own output, so the result is a **consistency check, not a discovery**. The 2024 ECCO
flagship-products table shows three regional BGC state estimates that cover our three AOIs
**one-to-one**, at higher resolution, and — decisively — with a **different biogeochemical model
(BLING, not Darwin)**.

| our AOI | bounds | product | res | period | overlap with v05 daily (ends 2018-12-31) |
|---|---|---|---|---|---|
| `eqpac` | 5°S–15°N, 160°W–110°W | **TPOSE** | 1/6° | 2010–2018 | ~9 yr |
| `natlsubpolar` | 50–65°N, 40°W–10°W | **ASTE-BGC** | 1/3° | 2002–2017 | ~16 yr |
| `southernoceanpac` | 65–50°S, 180°–100°W | **B-SOSE** | 1/6° | 2013–2021 | ~6 yr |

Nominal regions are quoted from the slide; **actual grid extents are not yet verified** to contain
our boxes. That is check 0.

## What is and is not comparable

BLING and Darwin share state variables but not structure. Parameters are **not** comparable —
BLING has no `diatomgraz`. Fields are.

| Carroll-6 | BLING analogue | comparable? |
|---|---|---|
| `alpfe` | dust-driven Fe source | mechanism yes, parameter no |
| `scav_rat` | Fe scavenging | **mechanism yes** — independent implementation of the same process |
| `R_PICPOC` | CaCO₃:POC rain ratio | **mechanism yes** |
| `diatomgraz` | none (no PFTs) | **no** |

So the test covers **3 of our 4 observables**, and misses exactly the one that is already
input-limited rather than structural.

Comparable fields: DIC, ALK, O₂, PO₄, dissolved Fe. Not comparable: PFT-resolved chlorophyll.

> BLING's exact configuration in each product is **assumed from the general BLING formulation, not
> read from these products' code**. Verify before any claim rests on it.

## The test

We are not comparing parameters. We are asking whether the **field structure our recovered
parameters imply** is a property of the ocean or a property of Darwin.

For each AOI, take the field our anchors act on (surface DFe for the iron pair, PIC:POC for
`R_PICPOC`) and compare three things: Darwin v05, the regional BLING estimate, and what our
recovered parameters reproduce.

- **Darwin and BLING agree, and we recover it** → the structure is observationally constrained, not
  model-specific. This is the upgrade from consistency check toward discovery.
- **Darwin and BLING disagree, and we follow Darwin** → we are recovering Darwin. The
  consistency-check framing is confirmed rather than escaped. Still publishable, and *more* honest
  than leaving it untested.
- **All three disagree** → uninformative; report as such and stop.

Pre-register which outcome is expected per AOI before looking, or this becomes a fishing exercise.

## The sharper test — is the basin mutex inherited?

Brix et al. 2015, quoted in Menemenlis's 2019 ECCO Summer School deck: constrained to a target
global uptake of ~2.4–2.5 PgC yr⁻¹, ECCO-Darwin "needs to compensate for the too strong carbon
uptake in the Southern Ocean by weaker uptake or intensified outgassing in other regions."

The reference calibration **trades Southern Ocean error against mid-latitude error to hit a global
scalar**. Our mutex runs along the same axis: `scav_rat` recovers 49/50 in the Southern Ocean and
7/50 in the equatorial Pacific.

**B-SOSE is a regional estimate with no global carbon target.** So it can discriminate:

> If Darwin's Southern Ocean carbon/iron state differs systematically from B-SOSE in the direction
> Brix describes, that is direct evidence our basin mutex is **inherited from the target**, not
> manufactured by the surrogate.

That flips the 3-of-4 frontier from a limitation we apologise for into a finding about ECCO-Darwin.
It is a hypothesis, not a result.

## Order of work

0. **Verify grid extents and access.** Do the three products actually contain our boxes, and are
   they downloadable? Nothing below matters if not.
1. Confirm BLING's Fe-scavenging and rain-ratio formulations in each product from source, not memory.
2. Single AOI first — **`southernoceanpac` / B-SOSE**, because it carries the mutex hypothesis and
   `scav_rat` is unambiguous there (49/50).
3. Only then the other two.

## Honest limits

- **Not independent of ECCO physics.** All four products share the ECCO circulation framework. This
  tests BGC-model independence, not full independence. Do not overclaim.
- Different periods, resolutions and assimilated datasets; B-SOSE overlaps v05 daily by only ~6 yr.
- BLING is *simpler* than Darwin. Agreement may reflect shared observational constraints (GLODAP,
  BGC-Argo) rather than shared physics — both assimilate much of the same data. **This is the
  strongest objection to the whole design** and needs an answer before the test is worth running.
