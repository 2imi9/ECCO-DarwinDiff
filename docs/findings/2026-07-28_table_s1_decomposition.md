# The Table S1 cost decomposition is depth-weighted — my "parameters barely matter" hook was too crude

**Date:** 2026-07-28 · **Loop Q3** · **Qualifies:** the opening hook in
`2026-07-28_workshop_paper_skeleton.md` and my Table S1 reading

## What I proposed

From Menemenlis's ECCO Summer School 2019 Table S1: first guess 0.35067 → baseline 0.11547 →
optimized 0.11148. So the Green's-functions **parameter** fit accounts for 0.00399 of the 0.23919
total improvement — about **1.7%** — with n = 4,038,777 observational constraints. I proposed that
as the paper's hook: *the parameters are weakly constrained by a comprehensive observing system.*

## What Carroll 2020 actually says

[Carroll et al. 2020, *JAMES*](https://doi.org/10.1029/2019MS001888) states that for the
**full-depth** observation set, most of the cost reduction comes from the GLODAPv2 initial
conditions — because over a 26-year integration there is **little change to biogeochemical
properties in the deep ocean**.

But it also says that when the cost function is restricted to **upper-ocean** observations — surface
pCO₂ in particular — the largest reductions come from the drift-reducing experiments **and from the
adjustment of the iron scavenging rate.**

## Why that matters to us

The 1.7% figure is real, but it is a property of a **depth-weighted, full-ocean cost function** in
which deep DIC and alkalinity dominate the count and barely evolve. It is a statement about how the
cost is weighted, **not** a clean statement about parameter identifiability.

And the parameter Carroll singles out for the upper ocean is **iron scavenging rate** — our
`scav_rat`. Consistent with Table S1's own linear-combination coefficients, where the
scavenging-rate row carries **0.52673**, the second-largest magnitude in the table.

So the honest reading inverts part of my hook:

| framing | status |
|---|---|
| "parameters contributed ~2% of the cost gain" | true **for the full-depth cost**, misleading unqualified |
| "therefore the parameters are weakly constrained" | **does not follow** — the deep ocean dominates the count and is nearly static |
| "iron scavenging barely moves the cost" | **contradicted** — Carroll names it as a leading upper-ocean contributor |

## The hook that survives, and is better

Not *"parameters barely matter"* but:

> **Whether a biogeochemical parameter appears identifiable depends on how the cost function is
> weighted across depth.** In the full-depth cost, four million observations are dominated by a deep
> ocean that scarcely evolves over 26 years, and the parameter contribution is ~2%. Restrict to the
> upper ocean and iron scavenging becomes a leading term. The observing system does not speak with
> one voice; the weighting chooses which parameters are visible.

That is a sharper claim, it is defensible from the published record, and it connects directly to our
own finding that identifiability is basin- and observable-dependent.

## The 93% vs 98.3% discrepancy — still unreconciled, now less important

My arithmetic on the raw costs gives **98.3%**; Menemenlis's slide annotates **93%**. I could not
reproduce 93% from any anchor row. Given the depth-weighting caveat above, **neither number should
carry the argument.** Quote the raw costs, show the subtraction, and state the depth caveat.

## Verified this session

- [Carroll et al. 2020, *JAMES*](https://doi.org/10.1029/2019MS001888) — resolved, statements above.
- Table S1 values transcribed from the Menemenlis ECCO Summer School 2019 deck (slide 11), supplied
  by Lucas.

**Not** verified: whether Carroll 2020's experiment numbering (#3–5, #7–11, #13) maps one-to-one onto
the Table S1 rows in the 2019 deck. They may be different tables from different model versions —
v4 in the deck. **Do not cross-reference the two numbering schemes without checking.**
