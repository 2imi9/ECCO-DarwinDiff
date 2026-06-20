---
name: paper-reviewer-panel
description: >
  Adversarial reviewer-panel red-team for a DarwinDiff / ECCO-Darwin manuscript
  (or any differentiable / inverse parameter-recovery paper). Reads the actual
  draft and runs a domain-adapted hostile-reviewer panel, then a grounded
  verify pass, and returns objections ranked by how hard they are for the
  authors to rebut. Every objection must cite a specific location in the draft
  — no ungrounded prose. Use when the user wants to reviewer-proof / red-team /
  stress-test a paper before submission, anticipate Reviewer 2, find over-claims
  or rigor gaps, or asks "what would a referee attack." Triggers: "reviewer-proof",
  "red-team the paper", "what would Reviewer 2 say", "review my manuscript",
  "stress-test the draft", "referee objections", "pre-submission review".
---

# Paper Reviewer Panel

Red-teams a manuscript the way a real review committee would: several reviewers
with **different and partly conflicting** mandates, each grounded in the actual
text, followed by an adversarial verify pass that kills objections the draft
already answers. Output is a ranked attack list, hardest-to-rebut first.

This is the opposite of "ask the model to review the paper." The single-prompt
version returns fluent, generic praise-with-caveats. This skill forces
(a) multiple adversarial lenses, (b) a citation for every claim, and (c) a
verify pass against the text — so the output is objections an author can act on,
not vibes.

## When to use

- Pre-submission or pre-share red-team of a DarwinDiff manuscript (`main.tex`).
- Anticipating referee / area-chair objections before they land.
- Auditing a revision: did the fixes actually close the attacks?
- Any differentiable-physics / inverse parameter-recovery paper (the personas
  generalize; the parenthetical examples are DarwinDiff-specific).

## The grounding contract (mandatory — this is what makes it not-STORM)

1. **Read the draft first.** Do not generate a single objection before reading
   the manuscript end to end. Default target: the project manuscript
   (recover from git if untracked — it was dropped from tracking in `f2add47`;
   `git show <rev>:docs/paper/main.tex`). Also read `references.bib` (for
   related-work / missing-citation attacks) and any canonical data artifact the
   draft cites (the committed canonical aggregate is
   `docs/findings/aggregated_v3.1.json`) so numeric claims are checkable.
2. **Every objection cites a location** — section, `\label`, table, or line.
   An objection with no citation is dropped in the verify pass.
3. **Recompute, never invent.** If an objection is numeric (a ratio, a rate, a
   CI), recompute it from the draft's own numbers or the canonical artifact and
   show the arithmetic. Do not assert a number you did not derive.
4. **Check before you fire.** Before raising an objection, search the draft for
   whether it is already addressed (a limitations paragraph, a caveat sentence).
   If addressed, either drop it or downgrade to "addressed but under-defended."

## The panel — eight adversarial lenses

Run all eight. Each has a distinct mandate; they are *supposed* to disagree
(the statistician and the framing editor will fight over how much to soften).
For an inverse / parameter-recovery paper the load-bearing axes are
identifiability, proxy fidelity, and observational under-determination — the
first two reviewers own those. (R1–R5 are the core; R6–R8 add the
reproducibility, arithmetic, and literature coverage that a thorough pass needs.)

**R1 — Physical-oceanography / BGC-model referee ("Reviewer 2").**
Attacks model fidelity and physical claims. Knobs to probe: is the inverted
model the *same* dynamical system that produced the targets, or a reduced
proxy? (e.g. a 5–7-tracer 0-D box inverted against full advective Darwin
output — does "distance to the calibrated value" then measure recovery skill or
proxy bias?). Missing physics that a recovered parameter must absorb
(temperature/light scaling, nutrient co-limitation, a single sinking rate doing
two jobs). Are region-to-region swings real signal or loss-weighting artifacts?

**R2 — ML / identifiability skeptic.**
Attacks the learning claims. Knobs: is there an independent estimator or
held-out validation, or is every number one pipeline scored against itself?
Could the result be overfitting / loss-geometry rather than a physical optimum?
Is the network specified well enough to reproduce (widths, depths, activations,
penalty forms, weight counts)? Which network produced the *headline* numbers,
and is that consistent with how the paper describes the architecture elsewhere?
Is a stated "structural/intrinsic" limit actually a finite-grid null result?

**R3 — Statistician.**
Attacks the inference. Knobs: confidence intervals on every rate (especially
sub-30% rates at small n); are "independent lines of evidence" actually
independent or nested/sharing samples? single-seed claims dressed as
reproducible; moving denominators; multiple-comparison / best-config selection.
Compute the Wilson CIs and the rule-of-three upper bound where they're missing.
Two high-yield traps to check explicitly: (a) is a reported *control/baseline*
actually a reused or selection-maximized config, so a "drop" against it is the
regression of an order statistic, not a real effect? (b) does a *joint* recovery
rate collapse to a single parameter because the other is ~always-pass (P(A∧B)=P(B)
when A≈100%)?

**R4 — Data / observation referee.**
Attacks the obs story. Knobs: what observations and cost function did the
*original* calibration actually use, and is this paper's loss the same
objective on the same observables — or a different one (e.g. z-scored pattern
MSE against the model's own output vs. an absolute obs misfit)? Are claimed
observational constraints actually present in the target set? Out-of-sample obs
validation, or only distance-to-published-value bands?

**R5 — Framing / area-chair editor.**
Attacks over-claim and positioning. Knobs: does the title/abstract claim more
than the body supports? internal contradictions (claims a limit is *intrinsic*
while proposing a concrete way to break it — having it both ways)? "to our
knowledge, the first" hedges; novelty stated only as a domain port of prior
work; SOTA neighbors missing from related work / the bibliography; headline
sells a negative result the authors themselves propose to overturn.

**R6 — Reproducibility / methods-completeness referee.**
Attacks whether a reader could rebuild the estimator. Knobs: are config/lever
names defined (what each multiplies, units, defaults)? per-parameter bounds,
per-config loss weights, seed lists, software/version pinning, integrator
convergence/stability check, sensitivity to fixed background parameters? Is the
code/data actually reachable (URL/DOI/commit) or a bare repo pointer? Are the
figures backed by reported quantitative content?

**R7 — Numerical-consistency auditor.**
Recompute and cross-check *every* number against itself and the canonical sheet:
abstract-vs-table roundings, constant roundings, ratios, table rows that don't
sum, distribution buckets that don't reach 100%, joint-vs-marginal claims, any
percentage that can't map to an integer count at the stated n. Show the
arithmetic. Flag every internal inconsistency, however small.

**R8 — Literature / novelty-positioning referee.**
Attacks related-work coverage and the bibliography directly (inspect the `.bib`).
Knobs: which load-bearing neighbors are missing (for ML-for-geoscience: neural
Earth-system emulators; for inverse problems: the model's *own* native machinery —
adjoint / 4D-Var / ensemble / MCMC calibration)? Is a foundational method cited via
a popular-science item instead of the canonical paper? Any orphaned (in-bib,
never-cited) or cited-but-never-engaged reference? Is the novelty delta over the
nearest prior work named, or is the contribution just a domain port? Use
literature search only to confirm a named paper exists.

## Per-objection schema

For each surviving objection, produce:

```
id            short slug
reviewer      R1..R8
claim         one or two sentences, the attack as a referee would phrase it
grounding     section / label / table / line it attacks (REQUIRED)
recompute     arithmetic, if numeric (else "n/a")
addressed?    is it confronted in the draft already? (no / partially-where)
severity      must-fix | would-strengthen
rebuttal_diff 1–5 — how hard is it for the authors to answer convincingly?
                    (5 = needs a new experiment; 1 = a sentence)
fix           the cheapest honest fix
```

## Verify pass (the real peer review, done right)

After the panel, run one adversarial sweep over the assembled list:

- **Kill the ungrounded.** No location citation → drop.
- **Kill the already-answered.** If the draft confronts it head-on, drop it or
  mark "addressed — under-defended" with the specific gap.
- **Kill the hallucinated number.** If `recompute` doesn't check out, drop it.
- **Merge duplicates** across reviewers (the same attack from two lenses is one
  objection with two angles, not two findings).

A model grading its own prose is theater; this pass grades each objection
against the *text and the arithmetic*, which is not.

**Then run a completeness critic.** Show it the surviving, merged list and ask:
what attack surface is *not* yet covered — a claim asserted with no support that
no objection challenges, an unverified assumption, a methods gap no lens hit?
Emit only net-new, grounded objections and verify those too. In testing this step
caught objections the eight lenses missed (e.g. a "control" that was a reused
selection-max; a "joint" rate that collapsed to one parameter).

## Ranking and output

Sort surviving objections by `rebuttal_diff` desc, then `must-fix` before
`would-strengthen`. Lead the report with **"the N attacks most likely to land"**
(rebuttal_diff ≥ 4), then the full table, then the cheap polish batch.
End with one honest line: the single highest-leverage fix, and whether the
paper's central claim survives the panel.

## Scaling up (optional, for a thorough pass)

For a high-stakes review, run as a `Workflow`: one agent per reviewer (R1–R8) in
parallel, each returning objections under the schema; then a verify stage
(`pipeline`) that grounds/merges; then a synthesis agent that ranks. This buys
independence between lenses (no single context blending them) and a genuine
adversarial verify. A single agent following this skill is the floor; the
fan-out is the ceiling. See `darwin_dinn_sweep_orchestrator` for the
project's Workflow conventions.

## Cross-references

- `darwin_dinn_sweep_orchestrator` — Workflow / orchestration conventions.
- `literature_search_*` — grounding R5's "missing related work" attack in real
  retrieval rather than recall (check arXiv/OpenAlex for the SOTA neighbor
  before asserting it's missing).
- The two review reports under `docs/research_notes/*_report.md` are worked
  examples of this skill's output shape — read them to calibrate depth and
  the line-citation style (do NOT read them while running a cold review).
