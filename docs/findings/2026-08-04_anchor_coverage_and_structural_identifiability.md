# E3's anchor does not reach the basin E3 targets — and the wall it is fighting can be settled symbolically for free

**Date:** 2026-08-04 · **Cost:** zero compute (two CSV reads and a documentation check)
· **Status:** blocks E3 as currently specified; opens a cheaper route

## 1. The GP15 sink anchor has ZERO overlap with eqpac

`docs/research_notes/2026-07-27_hierarchical_inversion_design.md` §E3 records the ²¹⁰Po/²¹⁰Pb +
Fe-export sink anchor as **"the highest-value item in the document"**, because it is the only
intervention predicted to move `scav_rat` in the equatorial Pacific, and because it would supply
`scav_rat`'s first independent real anchor. It notes the loader work is already done. It is.

The data does not reach eqpac.

| file | n | latitude | longitude |
|---|---|---|---|
| `gp15_1814_particulate_po_pb.csv` | 76 | **19.68 N – 56.06 N** | −156.96 – −152.00 |
| `leg1_dissolved_total_po_pb.csv` | 89 | **19.68 N – 56.06 N** | −156.96 – −152.00 |
| **`eqpac` AOI** | | **−5 N – 15 N** | −160 – −110 |

Longitudes overlap. **Latitudes miss by 4.68°.** The filename says it: this is GP15 **Leg 1**,
Alaska → Hawaii, which is the North Pacific. GP15 Leg 2 (Hawaii → Tahiti) is the leg that crosses
the equator, and it is not on disk.

So E3 as specified would train an eqpac sink anchor on zero eqpac observations. Its headline
prediction — iron-block κ collapsing 2930 → ~7 and eqpac rising materially above 7/50 — is not
testable with what we hold. This would have surfaced only *after* one implementation day plus one
cluster night.

**What E3 can still test:** the anchor covers 19.68–56.06 N, which is the North Pacific, not any
current AOI.

### The other two components, checked (2026-08-04)

| component | form | reaches `eqpac`? | detail |
|---|---|---|---|
| GP15 ²¹⁰Po/²¹⁰Pb | lat/lon, n=76 / 89 | **NO** | 19.68–56.06 N; misses by 4.68° |
| `black2020` Fe export | lat/lon, n=20 | **NO** | 0/20 in eqpac (global spread −76.5 to 81 N); **1/20** falls in `natlsubpolar` |
| `rufas2024` POC flux | **site-keyed, not gridded** | **YES** | carries an explicit **`EqPac`** site column alongside HOT/ALOHA, BATS/OFP, PAP-SO, OSP, HAUSGARTEN |

So the verdict splits, and it splits along the axis that matters. **Both iron-side components miss
the equatorial Pacific**, which is what kills E3's headline prediction — the one intervention meant
to move `scav_rat` in eqpac has no eqpac iron observations behind it. The **POC-flux** component
does reach eqpac, but as a **site-level Martin-*b* attenuation coefficient**, not a gridded flux
field, so wiring it is a different task from the one E3 specifies and it constrains particle
attenuation rather than iron scavenging directly.

`black2020`'s single `natlsubpolar` point is not a usable anchor on its own (n=1) but should be
recorded so it is not rediscovered as coverage.

**To close it properly:** GP15 Leg 2, or another equatorial ²³⁴Th / ²¹⁰Po–²¹⁰Pb product. Note the
standing caveat `ind435`: thorium-derived `scav_rat` partitions are systematically biased and the
bias does not average down with N, so an equatorial thorium anchor needs its bias budget stated
before it is wired in, not after.

## 2. The wall we are fighting can be identified exactly, without data

`ded77` stands as a live claim: *"No architecture can fix structural non-identifiability, and we
do not currently know which wall we are hitting."* That second clause is answerable, symbolically,
for free.

**StructuralIdentifiability.jl** — Dong, Goodbrake, Harrington & Pogudin (2023), *SIAM Journal on
Applied Algebra and Geometry* **7**(1) 194–235, DOI [10.1137/22M1469067](https://doi.org/10.1137/22M1469067) —
assesses **local and global** identifiability of ODE parameters and states with no data, no seeds,
no bands and no cluster time. Two functions matter here:

- `assess_identifiability(ode)` → per parameter, one of `:globally`, `:locally`,
  `:nonidentifiable`.
- `find_identifiable_functions(ode)` → generators of **all** identifiable functions, i.e. when
  individual parameters are not identifiable it *derives the identifiable combination*.

The documented example is exactly our situation: a model where `p1` and `p3` are individually
non-identifiable, and the tool returns `p1 + p3`, `p1*p3`, `p2*p4` — recovering the combinations
by machine.

**Our box qualifies.** The method needs `f` and `g` rational in states, parameters and inputs.
Monod kinetics are rational — the package's own worked example is `beta1*x1*x2/(chi1 + x2)`. The
Eppley factor `exp(0.0633·T)` is not rational in `T`, but `T` is a **forcing, not a state**, so it
enters as a known external input `u(t)`, which the state-space form supports directly. And
`known_ic` lets our Darwin-pickup initial conditions be declared known rather than generic.

Julia is not in this repo's stack, but this is a one-off symbolic analysis, not a training-loop
dependency — it runs standalone.

### What it would settle immediately

- **Whether `alpfe` and `scav_rat` are structurally or only practically non-identifiable.** The
  repo derived `[DFe] ∝ alpfe/scav_rat` by hand; `find_identifiable_functions` would either
  confirm that ratio as the identifiable generator or produce a different one. Either outcome is
  informative, and the second would be a correction.
- **Whether `diatomgraz` and the growth pair are excluded by structure or by observation.** The
  project currently asserts `Biggrow` unobservable "by construction" and `Smallgrow`
  non-identifiable from time-mean observables. Both are symbolic claims currently supported by
  empirical evidence. This proves or refutes them.
- **`ded77`'s open clause**, which is the honest blocker on every "more optimisation / more
  capacity" proposal. If a parameter is structurally non-identifiable, no weighting, capacity,
  epoch budget or optimiser can recover it, and the long list of nulls this project has
  accumulated (capacity, epochs, per-parameter trunks, Fisher weighting, adequacy weighting,
  subsurface up-weighting) stops being a series of disappointments and becomes a *prediction that
  was met*.

### The bigger use: screen anchors before spending nights on them

Structural identifiability is a property of the **(model, observable set)** pair. So adding a
candidate observable to `g` and re-running the analysis predicts, in minutes, whether that anchor
can break a given degeneracy **at all**.

That converts anchor selection — E3's Po/Pb flux, bSi for `diatomgraz`, a ²³⁴Th export flux, the
Daniels calcite anchor — from "one implementation day plus one cluster night, each" into a
symbolic pre-screen. Given §1 above, that is exactly the check that would have caught E3's
coverage gap on the design side rather than after the run.

**Retrospective test available for free:** run it on the observable set *with* and *without* the
Daniels calcite anchor. `R_PICPOC` goes 6/50 → 50/50 empirically. If the symbolic analysis
reproduces that flip, the method is validated on a known answer before being trusted on an
unknown one. That is the right first use.

## 3. Not to re-derive

**Daily v05 for the parameter learner is closed** on three independent grounds already in the map:
daily v05 is surface-2D only (16 diagnostics, none of the 3-D tracers the loss uses); the anomaly
variance fraction is the same daily as monthly; and daily lag-1 r of 0.994–0.996 collapses the
effective sample size. Daily adds cadence, not information.
