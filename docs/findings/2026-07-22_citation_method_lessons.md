# Methodological lessons from every citation — how to make the identifiability study credible (2026-07-22)

A Fable pass (`citation-method-mining` workflow, one agent per reference, web-grounded) studied *how* each
of the manuscript's 20 cited works actually established and validated its result, and extracted what is
transferable to us given our hard constraints (single v05 realization, rank-1 FeMIP degeneracy, dimensional
0-D gap). This is a manuscript-positioning strategy, not a literature summary. 17 of 20 mined cleanly;
heimbach2015 / ouala2026 / somes2021 hit the structured-output retry cap and are filled by hand below.

## Top 5 adopt-now moves (ranked by manuscript value, all near-zero compute)

1. **Reframe the whole result in Carroll's own control basis + observable set** (`carroll2022`,
   `menemenlis2005`). Present our empirical-Fisher / profile-likelihood over the *exact* Carroll-6 control
   vector, against the same absolute multi-tracer anchors Carroll's Green's-functions optimum inverted, and
   state the contribution as a **conditioning/rank statement about the Jacobian ECCO-Darwin's published
   calibration already trusts.** Converts "we didn't hit 6/6" into "we quantify which directions of a
   community-trusted control vector are constrained." Highest-leverage narrative move.
2. **Adopt Raue's structural-vs-practical non-identifiability taxonomy as the organizing frame**
   (`raue2009`). alpfe↔scav_rat rank-1 = *structural* (report the identifiable combination + the observable
   that separates it); the 0-D gap = *practical* (resolved by an absolute anchor). Report per-parameter
   likelihood CIs against a Δχ² threshold, not pass/fail counts. This is the *only* fully-transferable
   citation (needs no ensemble) and gives our "limits, not 6/6" stance referee-proof vocabulary.
3. **Name the sloppy directions as Fisher eigenVECTORS (combinations), not per-parameter flatness; separate
   zero from small eigenvalue** (`transtrum2011`/`gutenkunst2007`). Plot the log-eigenvalue spectrum;
   report alpfe↔scav_rat as the leading null eigenvector. Zero eigenvalue = zero manifold width =
   *structural* (no anchor helps unless its Jacobian row projects onto the null); small-but-nonzero =
   *sloppy* (a better anchor constrains it). This is the geometric *proof* of "identifiability comes from
   absolute anchors, not pattern-matching" — and it fixes our own internal error (do **not** cite
   diatomgraz-FLAT as evidence: alpfe is FLAT too and recovers — report *combinations*, not bare flatness).
4. **Name the surrogate gap as a Kennedy–O'Hagan model-discrepancy term δ; run anchors-only vs pattern-only
   as KOH's credibility move** (`kennedy2001`, `ohagan2006`). Define the 0-D box gap as a *structured* KOH
   discrepancy δ (dimensional: CV→1e-15), cite the θ–δ confounding theorem, and present the ablation:
   pattern-matching alone fits well with *wrong* θ; absolute anchors recover it. Upgrades "dimensional gap"
   from an empirical observation to an instance of a textbook inverse-problem law.
5. **Ground the iron degeneracy in Parekh's published physics and use it to drive anchor selection**
   (`parekh2005`, `mahowald2009`, `somes2021`). Parekh 2005 *is* our rank-1 source-vs-scavenging trade;
   breaking it needs an orthogonal observable (deep-Fe uniformity across a dust gradient), so select
   GEOTRACES anchors to **maximize aeolian-supply contrast** (high-dust N. Atlantic vs low-dust remote
   Pacific/SO) — cross-region contrast lifts the null, not iron magnitude at one site. Mahowald: soluble-Fe
   forcing is itself order-of-magnitude uncertain, so alpfe's looseness is partly real-world
   unidentifiability aliased into the parameter, not only a surrogate artifact.

## Already doing — the literature validates it as standard practice (cite, don't invent)

- **EKI/CES estimator-independence** (full-box EKI matches backprop) — the field's core credibility
  standard: two independent estimators agreeing (`schneider2017`, `cleary2021`, `evensen2003`,
  `xu2025binn`-vs-PRODA). Lean on it prominently, the way BINN leans on PRODA.
- **Per-parameter posterior σ / "loose scav_rat"** — precedented by Menemenlis' vertical-diffusivity
  15.1 ± 12 (error bar ≈ estimate flags a sloppy direction).
- **One-at-a-time vs joint fit to expose degeneracy** — Menemenlis Table 2 is the referee-accepted
  signature (non-additive cost reduction = linear dependence). *We should run this for alpfe/scav_rat.*
- **Profile-likelihood + empirical-Fisher ridges** as the degeneracy display (= BINN's MC-dropout posteriors).
- **Limits-not-score framing (Path A)** — BINN was refereed *down* for leading with an aggregate metric
  (spatial r=0.86) that hid equifinality present even at 4 params; our per-parameter-verdict headline is the
  reviewer-proofed alternative. (Do **not** headline the 25/50 joint.)
- **Reference-free physics/conservation checks** — validated by Carroll's closed online DIC budget and
  NeuralGCM's out-of-regime stability.
- **End-to-end backprop through the solver** — exactly NeuralGCM's online training.

## Not-for-us — considered and correctly rejected (with the blocking constraint)

| method | paper | blocking constraint |
|---|---|---|
| GF calibration engine (p+1 perturbed full-model runs) | carroll2022, menemenlis2005 | single v05 realization — autodiff-through-surrogate is the ensemble-free stand-in |
| amortize over 25,925 spatial profiles | xu2025binn | dimensional gap — 0-D box destroys the spatial axis that gives BINN its identifiability |
| two-point / covariance statistics to break degeneracies | schneider2017 | dimensional gap — homogenized box kills the fluctuation terms |
| KOH/BACCO GP emulator over θ-space | kennedy2001, ohagan2006 | single realization — needs a designed perturbed-θ ensemble |
| history-matching PPE + refocusing waves | williamson2013 | single realization; waves can't break a rank-1 null (it stays in NROY forever) |
| full-state EnKF / spread-as-posterior | evensen2003 | single realization; rank ≤ N−1 can't manufacture rank it lacks |
| continuous reverse-time adjoint | chen2018node | unstable for stiff/advection-dominated transport — checkpointed discrete adjoint is safer |
| CES/EKI/any sampler *as a recovery improvement* | cleary2021 | rank-1 null is estimator-independent — adopt as diagnostic only |
| SINDy learn-then-sparsify for Track-1 | rackauckas2020ude | dimensional gap — no informative transient in the 0-D box; non-unique along the null |
| NeuralGCM long-rollout / stochastic-physics CRPS | kochkov2024neuralgcm | single realization + 1-step info ceiling |

**Through-line reviewers should see:** five different ways in (EnKF rank≤N−1, CES flat ridge,
history-matching NROY ray, KOH θ–δ ridge, SINDy non-uniqueness) all hit the *same* wall — **no estimator
breaks a rank-1 structural null.** Considering and rejecting all five *strengthens* the limits claim.

## The three hand-filled references

- **heimbach2015 (ECCO v4 adjoint/4D-Var).** Move: the adjoint gives exact gradients w.r.t. millions of
  controls in ONE backward integration. Lesson: our surrogate backprop *is* an adjoint — for the box; the
  operational reason Darwin BGC params aren't in the ECCO adjoint control vector (they are GF-calibrated) is
  precisely the gap our surrogate fills. Situate us as "the adjoint the community would want for BGC but
  cannot build." Not-for-us: the full Darwin adjoint (that's the point). Priority: medium (framing).
- **somes2021 (GEOTRACES iron, controlled 5-run).** Move: a *small controlled* ensemble varying source vs
  ligand-scavenging shows they compensate to fit the same DFe — the FeMIP degeneracy demonstrated in a
  controlled setting, and it is the GEOTRACES *section structure*, not the mean, that constrains it.
  Lesson: cite as the published controlled demonstration of our exact rank-1 trade, and as direct support
  for the "section-gradient anchor, not the global mean" selection in adopt-now #5. Priority: high.
- **ouala2026neuralbgc (pure-NN BGC emulator).** Move: emulate the BGC forward map (DO/NO3), no parameter
  recovery. Lesson: the pure-emulation neighbour — differentiates our parameter-*recovery* goal; our Track-2
  emulator is the analog, Track-1 goes further. Priority: medium (related-work differentiation).

## The deepest insight — the field's credibility standard, and our position

Credibility in model calibration is **not** established by hitting a target or maximizing a fit metric. It
is established by **honestly diagnosing what the data cannot constrain — in a basis of parameter
combinations, with an explicit model-discrepancy term in the denominator, corroborated by
estimator-independence.** Every credible paper here makes the same four moves:

1. **Read identifiability off the geometry (g = JᵀJ), in combinations not bare parameters** — a property of
   model+data, never of the estimator.
2. **Carry an explicit discrepancy/error budget in the denominator** (KOH's δ, Williamson's implausibility)
   so a wrong model cannot buy a good fit by distorting physical parameters.
3. **Report ranges/limits and name what is structurally unconstrained**, not a single tuned vector.
4. **Corroborate with an independent estimator + a reference-free internal-consistency check.**

We already do moves 1 and 4. **The manuscript's job is to make moves 2 and 3 the spine, not the caveat:**
lead with the per-parameter/per-combination identifiability verdict over the observable-4, state the 0-D
gap as a named KOH δ carried in the denominator, classify each direction with Raue's taxonomy, and frame
the whole result in Carroll's own control basis. Positioned this way, our single-realization + rank-1 +
dimensional-gap constraints stop being weaknesses and become the *content*: **we are not a failed 6/6
recovery — we are the identifiability audit of a trusted calibration,** showing which directions of
Carroll's control vector are genuinely constrained, which are structurally null (the published Parekh FeMIP
trade), and precisely which absolute anchor would break each remaining sloppy direction. That is the
credibility standard the field rewards — and the one our critics (via BINN) enforce.
