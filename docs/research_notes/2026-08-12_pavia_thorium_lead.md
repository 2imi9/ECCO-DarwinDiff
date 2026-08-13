# Lauderdale's Frank Pavia lead — what it is actually worth (2026-08-12)

Jon, following the paired dissolved-Fe + thorium-export question (6/7): *"Frank Pavia looks at
export fluxes and thorium, I think I remember them having data from the Galapagos, but I could be
wrong…. I'll see if I can find a paper."*

## What is verified

Both DOIs resolved and abstracts read directly.

| paper | DOI | what it gives |
|---|---|---|
| **Pavia, Anderson, Winckler & Fleisher 2020**, *Global Biogeochemical Cycles* — "Atmospheric Dust Inputs, Iron Cycling, and Biogeochemical Connections in the South Pacific Ocean From Thorium Isotopes" | 10.1029/2020GB006562 | **Th-derived dust iron flux** in the South Pacific; concludes Fe dissolution, not diffusion, is the primary source |
| **Pavia, Anderson, Lam, Cael, Vivancos, Fleisher, Lu, Zhang, Cheng & Edwards 2019**, *PNAS* 116(20):9753–9758 — "Shallow particulate organic carbon regeneration in the South Pacific Ocean" | 10.1073/pnas.1901863116 | POC flux and **regeneration length scales** from ²³⁰Th/²³²Th/²³¹Pa on GEOTRACES **GP16** |

His lab page confirms the tracer set (²³⁰Th, ²³¹Pa, ²³⁴Th, ²²⁸Th, ²³²Th, ²³⁰Th/²³⁴U disequilibrium)
and the sections: **GP16**, East Pacific Rise, South Pacific Subtropical Gyre, Southern Ocean.

**The Galápagos recollection does not check out as stated**, and Jon flagged that himself. GP16 is
the Eastern Tropical *South* Pacific transect, nominally along ~12°S — **south of our `eqpac` AOI**
(lat −5 to +15). So it does not fill the equatorial-Pacific gap in the thorium section directly.

## Where the real value is, and it is not where the question pointed

The question was aimed at a **paired source + sink station** to break the alpfe↔scav_rat
degeneracy. Pavia 2020 is a **source-side** constraint, and the repo has already settled that a
source anchor cannot move the sink leg: the dust-anchor A/B on B200 gave `scav_rat` **0/10 in both
arms** (`2026-07-22_dust_anchor_ab_b200.md`). So this does **not** break the degeneracy, and it
should not be sold to Jon as though it does.

**What it does bear on is `alpfe`'s biggest weakness.** The repo already runs an optional
source-side prior, `DUST_ANCHOR_W` with `DUST_ANCHOR_MU = 1.15`, and that 1.15 comes from exactly
one place: Xu-Weber soluble-Fe deposition divided by v05's prescribed Mahowald flux, **in the
Saharan North Atlantic** (`2026-07-22_dust_anchor_phase0.md`). Off that region the same calculation
implies alpfe of **2.4–8.7**, i.e. the anchor is strongly region-dependent and rests on a single
dust product.

Pavia 2020 is a **methodologically independent** estimate of dust iron input — thorium isotopes
rather than a dust model — **in the South Pacific**, which is precisely where the Xu-Weber-implied
value goes wild. That makes it a genuine cross-check on whether 1.15 is a property of the Sahara or
of the ocean.

This matters now because of Jon's own answer on the ceiling: `alpfe` rails to whatever bound it is
given (99.7% of 1.0, 99.6% of 1.6) and carries **no upper-side information**, so we report it as a
*direction*, not a value. An observationally grounded, region-independent source constraint is one
of the few things that could turn it back into a value.

## Scoped next step (fall, not this window)

1. Read Pavia 2020 properly and extract the Th-derived soluble-Fe deposition flux with its
   uncertainty for the South Pacific.
2. Compute the implied alpfe the same way Phase 0 did (Th-derived flux / v05 Mahowald over the same
   cells) and compare against the Saharan 1.15 and the off-region 2.4–8.7.
3. If it lands near 1, the dust anchor stops being a Saharan artifact and `DUST_ANCHOR_MU` gets an
   independent second source. If it lands high, that is itself informative — it would say v05's
   prescribed deposition is low across two independent products, consistent with Jon's ">1 would
   not surprise me".

**Do not expect it to move `scav_rat`.** That is settled, and the honest framing for Jon is: useful
for the source term, not the sink partner we were asking for.
