# The NASA/NSF AI4Ocean Alliance: 38-member publication scan and strategic read

**Date:** 2026-08-12 · **Method:** 12 parallel per-institution agents (3–4 people each) + 1 site
sweep; every person's homepage/Scholar/OpenAlex record checked, papers verified by DOI where cited
· **Deduped to 38 named members** (two people were returned twice under different name renderings).

## The strategic answer, first

**The ocean-BGC machine-learning niche is unoccupied inside this alliance, and the BGC people in it
do not do what DarwinDiff does.**

Of the four named alliance projects, three are purely physical — MAESSTRO (masked autoencoder SST
gap-filling), NeurOST (deep-learning eddy/current maps from altimetry+SST), SSBI (U-Net recovering
vorticity/divergence/strain from SSH, trained on ECCO). The single exception, **Finding Fronts**,
uses PACE chlorophyll-a as *one of four input fields* (with SSS, SSH, SST) for a Gaussian-mixture
front detector in the Gulf of Mexico. Chlorophyll is an input to a physical-feature classifier, not
a biogeochemical quantity being modelled.

**17 of 38 members have any BGC/ocean-colour touch at all, and most of those are marginal or
non-lead.** Nobody in the alliance does differentiable biogeochemistry, BGC parameter recovery, or
identifiability analysis of a BGC model. That is the niche, and it holds.

## The seven who actually matter

| person | institution | why |
|---|---|---|
| **Matthew Mazloff** | Scripps | **The closest person on the roster.** B-SOSE (Verdy & Mazloff 2017, `10.1002/2016JC012650`) is a full **adjoint-based** ocean-BGC state estimate — carbon, oxygen, macronutrients — validated by gradient checks. This is the machinery whose *parameters* we study the identifiability of. Also SOCCOM/BGC-Argo array design and Southern Ocean acidification. |
| **J. Xavier Prochaska** | UC Santa Cruz | The one member with direct, first-author, current ocean-colour work — including **Prochaska & Frouin 2025** (`10.5194/bg-22-4705-2025`), a formal **identifiability/degeneracy** result for ocean-colour retrieval. Our thesis, adjacent domain. Already banked as a citation. |
| **Ian Fenty** | JPL | Co-author (8th of 19) on **Carroll et al. 2020 JAMES — the founding ECCO-Darwin paper**, i.e. our target model. |
| **Chris Hill** | MIT | Also a Carroll et al. 2020 co-author, plus MITgcm infrastructure. **Jon's MIT colleague.** |
| **Gaël Forget** | MIT | Also a Carroll et al. 2020 co-author; ECCO v4 state estimation and Julia ocean tooling. **Jon's MIT colleague.** |
| **Douglas Vandemark** | New Hampshire | Co-architect of **SOCAT** (the global surface-ocean pCO₂ database we validate against) and Co-I on **GLIMR**, a geostationary hyperspectral ocean-colour mission. |
| **Patrice Klein** | Caltech/JPL | Landmark submesoscale↔phytoplankton work (2001, ~475 citations) and submesoscale control of the North Atlantic carbon sink (2017). |

Second tier, real but narrower: **Dhruv Balwada** and **Shafer Smith** (eddy-driven iron flux
supporting Southern Ocean production — Uchida et al. 2020, `10.1038/s41467-020-14955-0`), **Maike
Sonnewald** (marine eco-provinces by unsupervised learning, Science Advances 2020), **Andrew
Thompson** (BGC-Argo carbon export), **Sarah Gille** and **Bruce Cornuelle** (SOCCOM/BGC-Argo as
non-lead co-authors).

**The strategically interesting fact:** three alliance members (Fenty, Hill, Forget) are co-authors
on the paper that defines our recovery target, and two of those three are at MIT with Jon. That is a
short path to the alliance if one is ever wanted — it goes through people Jon already works with,
not through a cold approach.

## The datasets, judged as anchors

The alliance's dataset list is **six physical products plus PACE**:

| dataset | usable as an anchor for us? |
|---|---|
| ECCO V4r4 (1° reanalysis, 1992–2018) | No — physical state, and it is model output, not observation |
| ECCO-LLC4320 (1/48°, ~5 PB) | No — physical nature run |
| SWOT L2 KaRIn SSH | No — physical |
| GHRSST MUR SST | Already used as the DINN's SST channel |
| Aquarius SSS / SMAP SSS | No — and SSS as a covariate channel *destroys* `R_PICPOC` (`ind254`) |
| **PACE ocean colour** (hyperspectral, from 2024-04-11) | **No — era mismatch.** Public data starts 2024-04-11; the v05 daily era ends **2018-12-31**. Zero overlap. |

The PACE finding confirms the standing repo position (`reference_v05_daily_satellite_era`) from an
independent direction: PACE remains unusable for this target, and it is unusable for a calendar
reason no amount of method work fixes.

**Nothing on the alliance's dataset list can anchor any of our six parameters.** The anchors that
matter to us — GEOTRACES iron, Daniels/Marsh calcite, thorium export, GLODAP, SOCAT — are all
outside it.

## The 2026 workshop: already over

> "July 20–31, 2026", School of Oceanography, Ocean Science Building, **University of Washington**.
> Two weeks: opening days Jul 20–22 (keynotes, 10-min lightning talks, project-team formation),
> hackathon Jul 23–29, then wrap-up.

**Today is 2026-08-12, so this has already happened.** It expanded from a 3-day 2025 Caltech
workshop to a two-week hackathon format, which suggests it recurs — worth watching for a 2027 call,
but there is nothing to act on now.

## What this changes for us

**Nothing about any number.** This is positioning intelligence, and it confirms rather than
challenges the standing read.

1. **The BGC-ML whitespace is real and now measured**, not assumed — 3 of 4 projects with zero
   biology, one using chlorophyll as a classifier input.
2. **Two citations are already banked** from this roster (Prochaska & Frouin 2025; Verdy & Mazloff
   2017), plus Uchida/Balwada 2020 and Krishnapriyan/Mahoney 2021.
3. **B-SOSE is the right positioning foil** for the manuscript: adjoint BGC state estimation exists
   and is mature; what does not exist is an identifiability analysis of the parameters it infers.
4. **PACE stays closed** for this target on calendar grounds.

## Limitations

Agents ran at `sonnet` with per-person verification; papers cited in the table above were
re-verified by DOI here, but the long tail of per-person paper lists was not individually
re-checked. Two roster members were returned under two name spellings and merged by hand. The
"17 of 38 have any BGC touch" figure counts *any* mention, including single non-lead co-authorships,
so it overstates rather than understates BGC presence — which makes the whitespace conclusion
conservative.
