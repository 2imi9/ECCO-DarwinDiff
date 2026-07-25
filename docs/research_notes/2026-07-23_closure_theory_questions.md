# Questions for a math expert — coarse-graining / closure theory ↔ DarwinDiff identifiability

> **ARCHIVED (2026-07-24) — superseded by `docs/findings/2026-07-24_bgc_operator_lineage_synthesis.md` §5
> (canonical, honesty-tagged, Q1–Q4 map one-to-one and it adds a net-new Q5). Retained for history; do not
> maintain in parallel.** Note: the #85 seasonal result is AOI-selective, not one-sided — it also *regresses*
> eqpac diatomgraz (−6) and natl alpfe (−4); see the synthesis §5 Q4 for the corrected framing.

Draft 2026-07-23 (overnight). Grounds the Deng–Hani–Ma coarse-graining result and the learned-moment-closure
lineage (see [[reference_aicr_overnight_orchestration]] → learned_closure_lineage.md) in DarwinDiff's *actual,
verified* findings, phrased as questions. Goal: sharpen the framing before consulting a math expert, and give
them enough project detail to engage. Companion: `2026-07-23_learned_closure_lineage.md`.

## The setup in one paragraph (for the expert)
DarwinDiff learns the parameters of a global ocean biogeochemistry model (ECCO-Darwin) by gradient descent
through a **differentiable 0-D "box" surrogate** of the model's biogeochemistry, with a small neural network
predicting the box parameters per grid cell. We read parameter identifiability from the surrogate's
Fisher-information / profile-likelihood geometry. Two structural facts we have verified: (a) the box surrogate
is a *severe* coarse-graining — at spatially-uniform parameters it relaxes to a near-uniform state (tracer
coefficient of variation ~1e-15) whereas the full model has O(1) spatial structure, so box-vs-model *pattern*
correlations are not fidelity metrics; (b) the parameters are **jointly identifiable** in the surrogate Fisher
sense (full rank) yet **not jointly recoverable** by the optimizer — a gap we call identifiability ≠
recoverability.

## Q1 — Is our 0-D box a *legitimate* coarse-graining, or too coarse?
Deng–Hani–Ma prove the macro PDE is the provable statistical limit of the micro system under explicit scaling.
Our 0-D box is a coarse-graining of the 3-D advection–reaction system, but we find it throws away exactly the
spatial correlations that carry identifiability information (the "surrogate gap is dimensional"). We *restore*
structure by making the parameters spatially varying (a per-cell network), which recovers the target trio
7/10 where a single global parameter vector recovers 0/10.
- Is "let the closure parameters vary in space" a legitimate closure move (a form of the coarse-scale operator
  carrying sub-scale information), or is it smuggling the discarded degrees of freedom back in through the
  parameter field — i.e., are we fitting the *residual of a bad closure* rather than the parameters?
- Is there a scaling regime in which a 0-D-per-cell reaction surrogate is the provable limit of the 3-D
  reaction–advection system with the advective coupling as the neglected term, and what controls the error?

## Q2 — Does "which correlations to keep vs cut" map onto the sloppy/stiff Fisher decomposition?
A learned closure answers empirically which correlations are statistically negligible; Deng–Hani–Ma cut most
of the collision-history graph without accumulating error. In our inverse problem, the Fisher's **stiff**
eigen-directions are pinned by data and the **sloppy** directions are not (our iron pair's sloppy direction is
the source/loss ratio S/k, verified this session: per-AOI 2×2 conditional correlation +0.94 in the equatorial
Pacific and North Atlantic).
- Is there a formal correspondence between "correlations a forward closure may cut" and "parameter directions
  an inverse problem cannot recover"? Both seem to be statements about which modes are dynamically/statistically
  inert, but one is forward (approximation error) and one is inverse (estimation variance). Is the connection
  more than an analogy — e.g., does the closure's neglected-correlation operator share a null space with the
  observation-restricted Fisher?

## Q3 — The steady-state ratio degeneracy as a closure invariant
At steady state the box gives [dissolved iron] ≈ S/k (source over loss), so concentration data constrain only
the ratio; source and sink are individually sloppy. This is the published FeMIP degeneracy, and we reproduce
it as surrogate sloppiness. The invariance-preserving moment-closure papers (Huang–Ma, Boltzmann–BGK) *build*
Galilean/scaling invariances into the architecture.
- Should the S/k ratio invariance be built into the surrogate as a hard architectural constraint (reparameterize
  to (ratio, product) and only ever learn/identify the ratio from steady data), rather than discovered as a
  sloppy direction after the fact? Is there a principled construction of "the invariant the steady observation
  cannot break," analogous to the conserved quantities in entropy-based closures?
- Verified nuance worth their view: the degeneracy is **basin-dependent** — subsurface iron resolves it in the
  Southern Ocean (2×2 condition number 2.2) but NOT in the equatorial Pacific / North Atlantic (condition
  35–51, still ratio-degenerate). So the invariance is broken by depth structure only where the section carries
  it. Is that a statement about the observation operator's rank on different sub-manifolds?

## Q4 — Time resolution as additional moments (the #85 result)
We just ran the first time-resolved ("seasonal") fit. Against a time-mean control, the annual cycle recovers
Southern-Ocean iron scaling (+5/10 seeds) and a North-Atlantic growth rate (+4/10) that the time-mean cannot,
but leaves a second growth rate unrecovered — consistent with Spitz et al. 1998 (some growth/loss parameters
stay inseparable even with the annual cycle).
- Is there a closure/identifiability statement about **how many temporal moments** (or which phase/relaxation
  timescales) are needed to separate a source rate from a loss rate that share a steady-state fixed point? This
  is exactly the "seasonal inventories carry rate information through phase and relaxation timescales" intuition
  (Sedwick 2023, Mtshali 2019) — but we would like the theorem, not the intuition.

## Questions back to Lucas (to sharpen before the expert)
1. Do we want the theory as *justification* (license to publish the surrogate approach) or as a *design driver*
   (build the S/k invariance / temporal-moment structure into the architecture)? These lead to different asks.
2. Is the target audience the ocean-BGC community (framing: "here is why the surrogate is legitimate") or the
   applied-math / closure community (framing: "an inverse-problem instance of learned coarse-graining")? The
   AGU NG-vs-OS choice mirrors this.
3. How hard do we want to push the forward/inverse duality (Q2)? If real, it is a genuine contribution; if only
   an analogy, we should say "analogy" and not overclaim (the honesty rule that governed the whole session).
