# Novelty literature scan — methodological vs scientific (2026-07-23)

The expert review said: "'first to frame it as parameter sloppiness' is an unverified novelty claim …
perform a focused literature search and state methodological novelty separately from scientific novelty."
Done here via the **OpenAlex skill** (`literature_search_openalex`). Sources listed at the bottom per the
skill's attribution rule; always check each paper's own license before reuse.

## What the search establishes (prior art — our novelty is NOT these)

1. **Parameter identifiability in marine ecosystem models is an established field.**
   *Reviews and syntheses: parameter identification in marine planktonic ecosystem models* (2017,
   Biogeosciences, **10.5194/bg-14-1647-2017**) is a dedicated review of exactly this problem. So we cannot
   claim "identifiability of marine BGC parameters" as novel, nor "first to frame it." Cite this as the
   field we contribute *to*.
2. **Autograd/AD for parameter inference is not new.** *AD Model Builder* (2011, **10.1080/10556788.2011.597854**,
   1750+ cites) uses automatic differentiation for statistical parameter inference in ecology/fisheries. So
   "we use autograd gradients for parameter estimation" is not itself a contribution.
3. **The native inverse machinery exists.** *ECCO version 4: non-linear inverse modeling* (2015,
   **10.5194/gmd-8-3071-2015**) is the adjoint/4D-Var framework we explicitly do NOT use — the correct
   comparator, not a gap.
4. **Observing-system design for BGC exists** (BGC-Argo / profiling floats: *On the Future of Argo* 2019,
   10.3389/fmars.2019.00439; *Observing Biogeochemical Cycles with Profiling Floats* 2009,
   10.5670/oceanog.2009.81; and BGC-Argo-vs-ocean-color value, 10.5194/bg-17-4059-2020). So "designing
   observations for BGC" as a goal is not novel.
5. **The iron source/sink degeneracy is published** (Frants et al. 2016, 10.1002/2015JG003111) and the
   inter-model spread is FeMIP (Tagliabue 2016). Not our discovery.

Caveat: OpenAlex relevance search is noisy and this is a *focused* scan, not a systematic review — absence
of a direct match is weak evidence, not proof. A direct hit for "differentiable-surrogate Fisher-based
observation design for a non-differentiable ocean-BGC GCM" did **not** appear, but that must be stated as
"to our knowledge from this scan," not "first."

## The defensible novelty (narrow, methodological)

Separating the two axes the expert demanded:

- **Scientific novelty: minimal.** The degeneracy (Frants), the identifiability problem (bg-14-1647-2017),
  the inter-model spread (FeMIP), and BGC observing-system design are all prior art. Do not claim scientific
  discovery.
- **Methodological novelty (the claim to make):** using a **differentiable 0-D surrogate as an
  inversion-side probe for a *non-differentiable* coupled GCM (ECCO-Darwin)** to (a) compute the
  *per-parameter, spatially-resolved identifiability geometry* of that specific model's calibration
  parameters, and (b) **rank candidate real observations by their surrogate Fisher-information contribution**
  to the sloppy direction. It is the *combination* — differentiable surrogate + Fisher geometry +
  observation design, for a model that cannot itself be differentiated — that is not represented in the
  scan, NOT any single ingredient. State it as "to our knowledge" and position explicitly against
  bg-14-1647-2017 (identifiability), ADMB (AD inference), ECCO v4 (native adjoint), and Argo OSSEs.

## Sources used (OpenAlex skill)
- https://openalex.org/works?filter=doi:10.5194/bg-14-1647-2017 (parameter identification review)
- https://doi.org/10.1080/10556788.2011.597854 (AD Model Builder)
- https://doi.org/10.5194/gmd-8-3071-2015 (ECCO v4)
- https://doi.org/10.3389/fmars.2019.00439 · https://doi.org/10.5670/oceanog.2009.81 · https://doi.org/10.5194/bg-17-4059-2020 (BGC observing systems)
- (skill: literature_search_openalex; check each paper's license before reuse)
