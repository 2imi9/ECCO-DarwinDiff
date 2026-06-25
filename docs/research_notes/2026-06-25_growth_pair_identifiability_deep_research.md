# Growth-pair identifiability — deep-research synthesis (next structural lever)

**Date:** 2026-06-25 · **Status:** LITERATURE SYNTHESIS (decision-ready). Feeds the
residual wall from [2026-06-24_rpicpoc_ratio_target_fix.md](../findings/2026-06-24_rpicpoc_ratio_target_fix.md):
with R_PICPOC recovered, robust 6/6 is blocked by the **growth pair {Smallgrow,
Biggrow}**, which co-vary and trade against the other params.

> **Provenance.** `deep-research` workflow (5 angles → 20 primary sources → 96 claims →
> adversarial verify). Hit the Claude.ai monthly spend cap during the synthesis step, so
> this writeup is hand-synthesized from the **19 adversarially-verified claims** (mostly
> 3-0). ✅ = verified; statements without a source are my synthesis/inference.

## TL;DR — verdict

The premise is confirmed by a peer-reviewed review: in plankton models, parameter
non-identifiability is **structural — data too sparse to constrain all parameters, not a
tuning deficiency** ✅ (Biogeosciences 14/1647/2017). So loss-tuning being exhausted is
expected; only **new information** breaks it. The literature points to two strong,
verified levers, ranked here by (gain for separating the growth pair) × (tractability in
our iron-only box):

| rank | lever | evidence | cost in our box |
|---|---|---|---|
| **1** | **Macronutrient (NO₃/PO₄) tracer + drawdown loss** | canonical: every NPZD/PFT optimization runs *with* a macronutrient; a param is unconstrained when its process is **structurally absent** | forward-model change (add 1 tracer + loss) — but data staged (NO₃/PO₄ in v05) |
| **2** | **Contrasting biome — add an oligotrophic gyre** (small-phyto-dominated) | multi-PFT models separate growth structure *only* when forced to fit contrasting biomes with one param set | **cheap** — box already multi-AOI; just add the AOI + cache |
| 3 | Seasonal / time-resolved fit | bloom *phase* pins growth params; but seasonal biomass reflects the growth−loss *balance*, not rate alone | needs real seasonal forcing driving biology (currently neutralized) |
| 4 | Hessian/Fisher eigen-analysis to *choose* the observable | diagnostic, not a fix — we already have `identifiability_sloppiness.py` | free |
| 5 | grazing / process-rate observables | claims did **not** survive verification (mixed) | weak evidence |

## The evidence

**Premise — structural, needs new information** ✅
- "data are often too sparse to constrain all model parameters" (review, bg 14/1647/2017).
- Different models reach **identical model-data misfit via different element-flow
  pathways** → a biomass/chl observable cannot uniquely constrain growth-vs-loss pathways;
  "need for more comprehensive data sets that uniquely constrain these pathways" ✅
  (Friedrichs et al. 2007, 2006JC003852).
- Biomass change = division − loss, so **biomass alone cannot separate the two** ✅
  (PMC8422905) — exactly our box-model degeneracy.

**(1) Macronutrient drawdown — strongest "root cause" support** ✅
- The canonical NPZD optimization (Schartau & Oschlies 2003) runs on a **nitrogen-based**
  model (N, P, Z, D) — the field's growth-vs-loss parameter estimation relies on a
  macronutrient currency. Our **iron-only box is the anomaly**, missing the N/P constraint.
- Kwon & Primeau global inverse: **biological production is driven by phosphate drawdown**
  (production restores PO₄ toward observed) — i.e. macronutrient drawdown *is* the
  production-rate constraint ✅ (escholarship 1tf9c12w).
- **A parameter stays unconstrained when its process is structurally absent**: rN:P is
  poorly constrained because the model "does not explicitly simulate the nitrogen cycle";
  resolving the N cycle + using N data is the fix ✅ (same) — a model-structure change, not
  more fitting.
- **Adding an independent tracer breaks parameter correlations**: combining TA+DIC "greatly
  improves" resolving individual params, *most* for pairs with opposing-sign sensitivity
  patterns; single-tracer fits leave |r|>0.8 pairs unidentifiable ✅ (same). This is the
  general principle — complementary information, not reweighting.
- 4D-Var practice (Friedrichs et al.) assimilates **chl + nitrate + export + primary
  productivity** jointly, not biomass alone ✅.

**(2) Contrasting biome / multi-PFT — strongest "growth-pair-specific" support** ✅
- **A single pelagic regime is insufficient**: the simplest models fit single-region data
  as well as multi-PFT models — one region can't separate the extra growth structure ✅.
- Multi-PFT models give **lower misfit only when forced to fit two contrasting biomes
  (eq. Pacific vs Arabian Sea) with one identical parameter set** ✅ (two sources). This is
  the direct mechanism for separating co-varying PFT growth params.
- **Caveat (practical identifiability):** cross-region portability improves with complexity
  **only when few params are optimized**; freeing too many degrades it ✅. And the joint
  optimum is a **compromise** vs per-site fits ✅ (Schartau 3-biome). → keep the freed-param
  count small; expect a worse-per-region but more-identifiable fit.

**(3) Seasonal / time-resolved — real but partial** ✅
- A growth-related photosynthesis param (α) was identifiable because chl constrained it and
  it was driven to match the **initial/seasonal phase** of growth ✅ — bloom onset carries
  growth-rate info an annual mean averages away.
- Net biomass accumulation rate r = division − loss; the **time-resolved trajectory** (not a
  snapshot) gives access to r ✅. BUT: bloom onset is governed by **decoupling of loss from
  growth**, so seasonal biomass reflects the *balance*, not growth rate alone ✅. → seasonal
  helps but is not a clean growth-rate observable by itself.

**(4) Sloppy-model diagnostics** ✅
- Hessian/Fisher eigen-decomposition flags poorly-constrained **parameter combinations**
  (small-eigenvalue = sloppy directions); "in practice only a few parameters of a planktonic
  ecosystem model" are independently estimable ✅ (gmd 10/4881/2017). Use it to pick the
  observable that breaks the specific Smallgrow↔Biggrow correlation. We already have the
  machinery (`scripts/identifiability_sloppiness.py`).

## Recommendation (highest-EV first move)

This **partially revises my earlier "macronutrient first" bet.** The evidence supports a
two-step path, cheap-first:

1. **First (cheap): add a contrasting oligotrophic-gyre AOI** where small phytoplankton
   dominate (subtropical Pacific/Atlantic gyre, BATS-like). We are *already* 3-AOI (eqpac
   HNLC, natl/SO bloom) and stuck — the likely gap is that none of our regions is
   small-phyto-dominated, so nothing separates Smallgrow from Biggrow. Adding such a biome
   is low-cost (box already multi-AOI; just an AOI + cache) and is the *most direct verified
   lever* for separating PFT growth params. Keep the freed-param set small.
2. **Then (deeper, canonical): add a macronutrient (PO₄ or NO₃) tracer + drawdown loss.**
   This attacks the growth-vs-loss root the iron-only box structurally lacks; the field
   universally relies on it; data are staged (NO₃/PO₄ in v05 monthly output). Larger
   forward-model investment — do it if the gyre AOI doesn't suffice.

Seasonal (#85) remains valuable but is a *complement* (partial growth-rate signal), and is
gated on giving the box real seasonal biology. Use the Fisher eigen-analysis to confirm
which lever actually collapses the Smallgrow↔Biggrow eigenvector before committing.

### Verified sources
bg.copernicus.org/articles/14/1647/2017 (review) · eprints.soton.ac.uk/12709 (Schartau &
Oschlies 2003) · sciencedirect S030438000900310X & agupubs 2006JC003852 (Friedrichs et al.
2007) · escholarship 1tf9c12w (Kwon & Primeau, PO₄-drawdown inverse) · gmd 10/4881/2017
(Fisher/eigen identifiability) · agupubs 10.1002/gbc.20050 & pmc PMC8422905 (biomass = div −
loss; bloom phase).
