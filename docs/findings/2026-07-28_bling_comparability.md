# BLING's iron scavenging is NOT formulation-comparable to Darwin's `scav_rat`

**Date:** 2026-07-28 · **Corrects:** `2026-07-27_independent_validation_scope.md`
· **Loop Q2, part 1**

## What I claimed in the scoping note

| Carroll-6 | BLING analogue | I wrote |
|---|---|---|
| `scav_rat` | Fe scavenging | "**mechanism yes** — independent implementation of the same process" |

That overstates it. They are two different process models, not two implementations of one.

## The two formulations, side by side

**Darwin** (`carroll6.py:21`, term at `:227`):

```
dDFe/dt = alpfe·Φ_dust − scav_rat·DFe·POC − Q_Fe·(μ_s P_s + μ_l P_l)·f_Fe(DFe)
```

Scavenging is **bilinear in total dissolved Fe and POC**. One rate constant. No ligand, no
free/complexed partition — `grep -rln "ligand"` over `src/darwindiff/` returns only `closures.py`
and the Gledhill loader, neither of which is in the box.

**BLING** ([Galbraith et al. 2010](https://bg.copernicus.org/articles/7/1043/2010/),
[Dunne et al. 2020, BLINGv2](https://doi.org/10.1029/2019MS002008)): a prescribed ligand
concentration sets the **organically-complexed fraction**, which is *not* scavengeable. Only the
remaining **free** DFe is, via two distinct paths — adsorption onto particulate organic matter, and
inorganic scavenging governed by a separate rate constant (colloidal aggregation and lithogenic
scavenging).

## Why this kills the parameter comparison

BLING's scavenging rate constant multiplies **free** Fe; Darwin's multiplies **total** DFe. The free
fraction is a ligand-dependent, spatially varying quantity that Darwin does not represent at all. So
the two constants have different operands, different functional forms, and BLING carries an extra
state variable. A numerical agreement between them would mean nothing, and a disagreement would
mean nothing either.

**Fields remain comparable.** DFe, DIC, ALK, O₂, PO₄ are the same physical quantities and can be
compared directly. That part of the scoping note stands.

## The more interesting consequence

**Darwin's alpfe/scav_rat degeneracy may be partly a property of its ligand-free formulation.**

The degeneracy is a source-versus-sink compensation on *total* DFe. In a ligand-explicit model the
sink depends on free Fe, which is set by the ligand field rather than by the scavenging constant
alone — so the compensation is not obviously the same shape. Whether the degeneracy survives a
ligand-explicit formulation is an open, testable question, and it is a better one than "do two
models agree".

Directly relevant, and independently retrieved this session:
[Somes et al. 2021, *GBC*](https://doi.org/10.1029/2021GB006948) — *"Constraining Global Marine Iron
Sources and Ligand-Mediated Scavenging Fluxes With GEOTRACES Dissolved Iron Measurements in an Ocean
Biogeochemical Model."* That is our inverse problem, with ligands, against GEOTRACES, already
published. It should be read before the manuscript claims novelty on iron-source/sink separation.

## Revised status of the independent-validation route

| route | status |
|---|---|
| Compare `scav_rat` to a BLING parameter | **dead** — not comparable |
| Compare DFe / carbon **fields** in the same region | **live** |
| Test whether Darwin's SO bias matches Brix's described compensation, using B-SOSE | **live** — the strongest remaining test |
| Ask whether the degeneracy is formulation-dependent | **new, and the most interesting** |

Grid extents and access URLs for B-SOSE/TPOSE/ASTE-BGC are still unverified — next in the loop.
