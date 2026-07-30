# Prior art for the identifiability contract — the novelty claim does NOT survive

Six-field literature survey, each field then handed to a hostile reviewer instructed to find the
prior art the surveyor missed. 12 agents, 1.40M tokens, 421 tool calls.

**Verdict: `novelty_survives: []`. All six fields challenged it. None survived.**

This is the most useful outcome available. A contribution claim that collapses under review is worse
than no claim, and this cost one afternoon instead of one referee report.

---

## 1. The measured untrained baseline is not ours. It has a name.

**Adebayo, Gilmer, Muelly, Goodfellow, Hardt & Kim (2018), "Sanity Checks for Saliency Maps",
NeurIPS 31, arXiv:1810.03292 — the MODEL PARAMETER RANDOMIZATION TEST.**

Four of six reviewers independently named it as the strongest prior art. One put it bluntly: *"It is
not an analogue. It is the same construct, with the same justification, presented in the same
register."* Same object (score a **randomly initialised, untrained network of the same
architecture** through the **identical downstream scoring pipeline**), same claimed status (the
trained-versus-untrained gap is the only admissible evidence), same architecture-matching
requirement we thought was our own refinement.

Further antecedents, all verified:

- **Oller, Glasmachers & Cuccu (2020), "Analyzing Reinforcement Learning Benchmarks with Random
  Weight Guessing", AAMAS, arXiv:2004.07707** — closer still to our framing, and its own antecedent
  is **Schmidhuber, Hochreiter & Bengio (2001), "Evaluating Benchmark Problems by Random Guessing"**.
- **Storrs, Kietzmann, Walther, Mehrer & Kriegeskorte (2021), J. Cogn. Neurosci. 33(10):2044,
  DOI 10.1162/jocn_a_01755**, and **Cadena et al. (2019)** — the architecture-matched untrained
  control is *standard practice* in computational neuroscience.
- **Combrisson & Jerbi (2015)** — the principle that a chance rate must be **measured, not assumed**.
- Ocean data assimilation has had the **free run** as its null for decades.

## 2. "Machine-checkable rather than human-filled" is not novel either

This was our fallback novelty axis and it does not hold. Automated compliance checking of reporting
standards has been mature for roughly seven years across at least four independent lineages: **FAIR
Evaluator / F-UJI / FAIRshake**, **SciScore**, **nf-core lint**, and **CONSORT-NLP → AutoReporter →
RAPID** plus the **TRIPOD+AI** adherence tool.

Worse for us, **"a missing item reads UNAVAILABLE rather than PASS" already exists** — it is
`ignored` in nf-core lint and **"No information" in PROBAST**. PROBAST's version is *stronger* than
ours: it actively pushes the judgement toward high risk of bias rather than merely abstaining.

## 3. One thing we assumed was equivalent is genuinely not

The **checkerboard/spike test** in seismic tomography is **not** the same idea, and the distinction
is worth stating because it clarifies both:

| | direction | catches |
|---|---|---|
| checkerboard | **positive** control: known non-null input, full learning, does the pipeline return it? | "the inversion cannot resolve this" |
| measured untrained null | **negative** control: no learning at all, does the metric still report success? | "the score does not come from the inversion" |

They sit on opposite sides of the control axis. The shared virtue is that both push something
through the *real* pipeline rather than a linearised proxy.

---

## 4. The criticism that would hurt most, and it is specific

**The null does not absorb configuration selection.** The flagship `n50e2k_percell_trio` was chosen
out of a sweep over env-var levers, epoch budgets, AOI weights and channel choices. Measuring the
untrained null **for that one config** estimates the wrong null. The correct null is
**best-of-sweep under untrained networks**: re-run the config-selection procedure inside each null
draw.

Our null currently answers "chance for a fixed pipeline". The claim it is used to defend is closer
to "chance for a pipeline we selected". Those differ, and a reviewer who notices will say so.

## 5. What these fields require that we do not do

Ranked by how hard each is to rebut.

1. **Global structural identifiability, done symbolically.** Our clause 1 (rank/spectrum of
   `F = JᵀJ`) is *local* structural identifiability at a point. The field's stated minimum is
   structural identifiability via differential algebra — DAISY, STRIKE-GOLDD,
   StructuralIdentifiability.jl — and a 6-parameter 0-D box is squarely within reach of those tools.
   Preston et al. (2025, DOI 10.1016/j.coisb.2025.100563) show exactly the case a FIM misses: a
   globally unidentifiable model with a secondary optimum the quadratic approximation cannot see.
   **Not running one is the single hardest thing to defend.** Note our `R_PICPOC` result is the
   exception that proves we *can* do this: it is a global exact structural zero, proved by
   inspection.
2. **Profile likelihood reported as a finite per-parameter confidence interval**, with the boundary
   pathology named (Raue et al. 2009: a CI that only closes at the edge of the admissible range is
   *practical non-identifiability*). The field already treats "the bound did the work" as a
   diagnosable failure — which is our clause 3 under an older name.
3. **Brute-force synthetic recovery sampled widely over Θ**, not at a single θ\*. Preston et al.:
   local identifiability at θ\* suffices for one-off calibration, but *"when developing a pipeline to
   fit many different future datasets, we will need to evaluate global identifiability using many
   different θ\* sampled widely from Θ."* We are explicitly building a pipeline.
4. **Multi-start as the cheap first test.** Guillaume et al. (2019, Environ. Model. Softw.
   119:418-432): *"simply repeat an optimisation with different initialisations to check if it
   returns different values."*

## 6. The reframing that matters most for #163

The ocean-BGC reviewer's judgement on our negative held-out R²:

> The field does **not** require you to predict held-out *observations* from a 0-D box. It requires
> you to show the recovered parameters are the parameters of the **target model**.

**Kuhn & Fennel** faced the same surrogate gap — a 1-D surrogate cannot represent horizontal
advection either — and handled it by **running the 3-D model with the surrogate-optimised
parameters**. That is precisely what issue #163's GCM validation would do.

So the negative R² is being **over-read as a blocker**. It is the wrong test for the claim we
actually make. The right test is the one already blocked on a forcing slice from Jon, which raises
that ask from useful to load-bearing.

---

## 7. What the contribution claim should become

**Do not write "we introduce" or "methodological contribution" anywhere near the untrained baseline
or the contract.** Both are refutable in one sentence by any referee who knows Adebayo.

Concede the operation, keep the application, name the parents first. Suggested methods wording,
synthesised from the reviewers':

> Recovery counts are meaningless without a chance rate, so we measure ours. The identical pipeline
> is run with the learning rate set to zero so the networks remain at initialisation, and those
> outputs are scored through the identical grading path — the same per-AOI collapse, bands, 2-of-3
> rule and JSON schema. **The control is not new**: it is the model parameter randomization test of
> Adebayo et al. (2018) applied to mechanistic parameter recovery rather than to attribution,
> following the untrained-baseline convention of benchmark auditing (Schmidhuber et al. 2001; Oller
> et al. 2020), the architecture-matched untrained control standard in model-to-data comparison
> (Cadena et al. 2019; Storrs et al. 2021), the free-run convention of ocean data assimilation, and
> the principle that a chance rate must be measured rather than assumed (Combrisson & Jerbi 2015).

**What remains defensible, stated narrowly:**

1. Applying a null control to a **binary pass/fail recovery count**, so the chance rate of *that
   specific tolerance metric* is measured rather than assumed.
2. The **fail-closed convention** that a clause with no evidence reads UNAVAILABLE rather than PASS,
   wired to an exit code (noting PROBAST already does something stronger).
3. The **numbers themselves**, which are the real contribution: `diatomgraz` scores 0.640 untrained,
   which retired one of our own headline results.

Claim those and nothing broader. And cite Guillaume et al. (2019), whose three-point requirement —
document *whether* a model is non-identifiable, the *source*, and the *impact on the intended
outcome* — is the closest existing statement of what our contract mechanises.
