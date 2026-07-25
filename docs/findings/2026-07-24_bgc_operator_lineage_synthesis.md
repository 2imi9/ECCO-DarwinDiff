# Global ocean-BGC neural operator — lineage lessons, regime verdict, and the learned-closure reframe

Synthesis + adversarial verify, 2026-07-24. Consolidates four research briefs (forward-lineage,
regime-headroom, bgc-whitespace-role, closure-framing) against
`docs/research_notes/2026-07-23_learned_closure_lineage.md` and
`docs/research_notes/2026-07-23_closure_theory_questions.md`.

**Scope guardrail (non-negotiable, from project honesty rules):** our Track-2 forward emulator does
**not** beat a per-cell seasonal AR(1) baseline at 1-month lead (robust across seeds). "Beats
persistence" is retired. We take FourCastNet's *architecture and geometry*, never its
"45,000×-faster / same-accuracy" headline (weather-specific). We do not claim we "made Darwin
differentiable" or "learned real biology." Every claim below is tagged **[established]**,
**[ours-verified]**, or **[speculation]**.

---

## 1. Transferable architecture / geometry shortlist for a future BGC operator

Design lessons carried from the weather/ocean emulator lineage — accuracy/speedup headlines
deliberately dropped, only architecture/geometry/training-discipline kept. **[established]** unless noted.

| # | Source | Transferable lesson for a BGC operator | Why it matters for BGC specifically |
|---|--------|----------------------------------------|-------------------------------------|
| 1 | **SFNO** (Bonev et al. 2023, arXiv:2306.03838) | **Spherical harmonics, not a flat 2D FFT**, for the global interior. | A flat FFT assumes a periodic plane and injects polar artifacts + spurious high-latitude dissipation — exactly the Southern Ocean / N. Atlantic subpolar bloom + iron-limitation regions where our own v05-vs-MODIS bias lives. **This is the flagged geometry fix.** |
| 2 | **AFNO** (Guibas/Pathak 2021, arXiv:2111.13587) | Spectral mixing **inside transformer blocks**, not a monolithic FNO. | Channel-mixing capacity (not spatial resolution) is the binding constraint for BGC — many prognostic tracers (DIC, ALK, NO3, PO4, Fe, O2, DOC, PIC, POC, multiple phyto/zoo). |
| 3 | **FNO** (Li/Kovachki 2020, arXiv:2010.08895) | Global receptive field in one spectral-conv layer; resolution-invariance. | BGC transport couples distant cells (advected nutrients, teleconnected upwelling); train coarse (1°), evaluate finer without retraining. |
| 4 | **Pangu-Weather** (Bi et al. 2023, Nature; arXiv:2211.02556) | **Depth as a true 3D axis with a learnable depth position bias**, not stacked independent channels. | Ocean BGC is strongly vertically structured (euphotic zone, nutricline, remineralization, biological pump). Concrete alternative to our current depth-as-channel choice. |
| 5 | **GraphCast** (Lam et al. 2023, Science; arXiv:2212.12794) | Multi-scale mesh/graph for **irregular geometry, coastlines, basin boundaries**. | Land-sea masks and the curvilinear/tripolar ocean grid are discontinuities spherical harmonics smear. Borrow if coastal/enclosed-basin BGC is first-class (hybrid spectral-interior + graph-boundary). |
| 6 | **NeuralGCM** (Kochkov et al. 2024, Nature; arXiv:2311.07222) | **Differentiable transport core + learn only the closure** (source−sink). End-to-end differentiable. | Directly aligned to Track-2 UDE. Existence proof that differentiable-core + learned-column-physics is stable over decades and trainable through rollout. See §4. |
| 7 | **ACE / ACE2** (Watt-Meyer 2023, arXiv:2310.02074; Duncan 2024) | **Conservation built into the architecture, not the loss.** Prescribe a slow boundary to stabilize rollout. | BGC invariants = elemental budgets (C, N, P, Fe, alkalinity). Prevents the drift we caught. BGC analog of "fix SST" = prescribe physical transport/T/S. |
| 8 | **OceanNet** (Chattopadhyay 2024, arXiv:2310.00813) | **Predictor-evaluate-corrector integrator + spectral regularizer** for rollout-error control. | Cheap, concrete mechanism to suppress autoregressive error growth and small-scale spectral bias in a BGC rollout. |
| 9 | **Samudra** (Dheeshjith 2024, arXiv:2412.03795) | A **ConvNeXt-UNet** is a viable, proven-stable century-scale global-ocean backbone (not everything must be a neural operator). | Proven-stable alternative to a spectral backbone; and it carries **no BGC** — the whitespace made concrete (§3). |
| 10 | **SamudrACE** (Duncan 2025, arXiv:2509.12490) | Couple via **column-local, physically-constrained interface fluxes — not learned embeddings.** | When coupling a BGC operator to physical drivers, pass physical fluxes at the interface; keeps the coupled system stable and interpretable. |
| 11 | **FourCastNet** (Pathak 2022, arXiv:2202.11214) | **Two-stage training: pretrain one-step → fine-tune on autoregressive rollout** to suppress compounding error. | Take the training recipe + AFNO backbone geometry. **Do NOT take the speedup/skill headline** (see §2). |

**Net design brief:** SFNO spherical geometry for the interior (+ GraphCast mesh if coasts/basins
matter) · AFNO-style channel-heavy spectral-transformer backbone (or Samudra ConvNeXt-UNet as the
proven-stable alternative) · Pangu depth-as-3D-axis · NeuralGCM differentiable-transport +
learned-closure structure · ACE2 *architectural* elemental-budget conservation + OceanNet PEC/spectral
regularizer · FourCastNet two-stage training · SamudrACE column-local physical-flux coupling.

---

## 2. Honest regime verdict — the emulator's value is NOT 1-month forecasting

**Verdict [ours-verified + established]:** at 1-month lead, monthly ocean BGC has ~zero learnable
headroom over persistence/AR(1), and this is *structural*, not a model defect.

- **The principle [established].** Headroom ≈ (potential predictability) − (damped-persistence skill).
  It is large only when the field decorrelates fast relative to the lead (persistence is a weak
  baseline) *and* deterministic structure exists to exploit. Standard S/N-predictability framing, itself
  an AR(1) story (Zhang et al. 2019, GRL, 10.1029/2019GL085159).
- **Weather is the large-headroom regime [established].** Hours-to-days, atmospheric tendency is a large
  fraction of the standing anomaly; persistence is weak; deterministic dynamics are informative. That gap
  is what FourCastNet fills — and where the ~45,000× headline lives. **It is weather-specific and does not
  transfer.**
- **Monthly ocean BGC is the opposite regime [ours-verified].** High month-to-month autocorrelation (red
  spectrum) → the per-cell seasonal AR(1) null is *strong*; the one-month tendency-to-anomaly ratio is
  small → little sits above the persistence floor for a 1-step operator. The field's accepted best-practice
  null is **damped persistence** (Mogen et al. 2023, Earth's Future, 10.1029/2023EF003605), a deliberately
  strong AR(1) baseline. Failing to beat it at 1 month is the expected result for *any* method here.
- **Category error, named [ours + established].** Our 1-step forward emulator was implicitly benchmarked as
  a *weather-style initial-value forecaster* in a regime with no initial-value headroom. Ocean/climate
  emulators are boundary-value problems judged on long stable rollouts and forced response, not 1-step ACC
  (Samudra; Baxter et al. 2026, GRL, 10.1029/2025GL119877 — AI *and* physics models both struggle at
  month-to-year timescales).

**Where headroom plausibly is (ranked):**

1. **Inversion / identifiability surrogate (Track 1) — established strength, no persistence comparison
   [ours-verified].** This role never competes with AR(1); the no-headroom argument does not touch it. It
   exposes the Fisher/profile-likelihood geometry of the parameter→observation map for gradient-based
   parameter learning. This is the flagship (per-cell trio recovery; EKI posterior ⟂ analytic sloppy
   direction 1.000).
2. **Longer-horizon, boundary-forced / scenario forward tool — plausible but UNPROVEN [speculation].**
   Genuine BGC predictability exists but at **multi-month-to-multiyear** leads and is **physically forced**
   — ENSO-teleconnected NPP via nutrient advection (Séférian et al. 2014, PNAS; Park et al. 2019, Science),
   subsurface reemergence and >10-yr subsurface memory (Frölicher et al. 2020, Biogeosciences,
   10.5194/bg-17-2061-2020; Krumhardt et al. 2020, GBC, 10.1029/2020GB006531). **Two honest caveats:**
   (a) the physics-forced ESM sets a high bar because the predictability is physical and the initial-value
   *biological* increment is small (Frölicher 2020: initializing the BGC state barely improves decadal
   skill); (b) whether *our* operator beats damped persistence at those leads is an **open, testable
   question, not an assumed win** — flag as speculation until measured.
3. **1-step forward emulator — structurally ~zero headroom. Retire the "beats persistence" claim (done).**

> **Adversarial flag.** Brief 2 cites Mogen 2023 and Krumhardt 2020 from abstracts/snippets (full texts
> paywalled, HTTP 402). Their *qualitative* claims (damped persistence is the standard null; nutrient
> memory carries predictability) are corroborated by the open-access companion literature and are safe to
> assert. **Do not quote their exact horizon numbers in a manuscript without verifying against the PDFs.**

---

## 3. Defensible minimal claim + referee-demanded validation

**Whitespace status [ours-verified as of July 2026]:** the note's "nobody has a global ocean-BGC neural
operator" is **now partially false and must be softened.** 2026 entrants narrowed it:

- **BG4Sea** (Mercator Ocean, 2026) — the competitor to name: **global** ML emulator of NEMO-PISCES,
  seasonal horizon, carbon/nutrients/O2/pH/chl/plankton. But it emulates an *operational forecast system*
  and is evaluated **against reanalysis** (model-vs-model; inherits PISCES' parametrization).
- **Global surface chl-a data-driven** (Biogeosciences 23:2601, 2026) — global but **surface-only,
  diagnostic** regression from physical fields.
- **1-D prognostic marine-BGC emulator** (arXiv:2606.27168) — true prognostic time-stepper, full 52-var
  ERSEM column, **already builds in C/N/P conservation + non-negativity** — but single water column,
  regional (English Channel L4).
- **GOBAI-O2** (ESSD 18:287, 2026) — obs-trained global gridded O2 mapping product, not a dynamical operator.

**The residual gap, stated this narrowly (defensible):** no published **global, full-depth (3-D),
*prognostic* neural operator of a data-assimilating BGC *reanalysis* with an explicit multi-plankton +
iron ecosystem (ECCO-Darwin), validated against independent observations rather than its own parent
model.** Real but thin. Given the retracted 1-month skill, it **cannot be sold as forecast superiority.**

**Minimal claim (most → least defensible):**

- **(A) Safest — lead with Track 1.** The identifiability study is the genuine, uncontested contribution;
  none of the BGC emulators above do parameter identifiability. Track 2 is supporting.
- **(B) If a Track-2 claim is wanted — frame it as a *learned closure* + honest baseline** (see §4): an
  ocean-BGC PrognosticModel conforming to the earth2studio interface, benchmarked against the per-cell
  seasonal AR(1) baseline that current BGC-emulator papers **omit**; at 1-month lead it does not beat AR(1)
  (reported as an honest null); demonstrated value is scenario response / physics-audited consistency, not
  short-lead skill.
- **Do NOT claim:** "first global BGC operator," "beats persistence," "made Darwin differentiable," forecast
  superiority. BG4Sea + the 1-D conservation-constrained emulator already blunt the first three.

**Validation a referee WILL demand (name these before they do):**

1. **Correct baseline** — improvement over per-cell seasonal climatology AND AR(1)/damped persistence,
   seed-ensembled; NOT "vs the parent model."
2. **The "why not a diagnostic head?" ablation — the sharpest attack.** Chl is diagnosable from physical
   fields, so show the operator on variables *not* instantaneously diagnosable from physics — air-sea carbon
   flux, subsurface nutrient depletion, iron limitation (history/memory-dependent). If it can't beat
   "Samudra physics → diagnostic BGC regression head," the operator has no reason to exist.
3. **Conservation + non-negativity audit** — elemental budget closure, no negative tracers. **Table stakes,
   not novelty** (arXiv:2606.27168 already builds these in). Our own catch — the emulator **invented ~4.5%
   negative iron while scoring R²≈+0.43 [ours-verified]** — is the cautionary hook: frame as "skill scores
   hide physics violations," not as a new idea.
4. **Multi-step rollout stability + climatology-collapse test** — Samudra set the centuries-stable bar; show
   yours neither drifts nor degenerates to the mean.
5. **Out-of-distribution scenario response** — correct response to a perturbation absent from training
   (changed iron flux / warming). The actual value prop and the hardest test.
6. **Independent observational validation, regime-resolved** — MODIS chl, GLODAP DIC/pCO2, BGC-Argo O2,
   split equatorial vs bloom (our own notes: global-mean r misleads both ways).

---

## 4. The learned-closure reframe — strongest framing, with the exact next experiment

**Claim:** cast the deflated operator as a **learned subgrid/coarse closure on prescribed transport**, not
a forward forecaster. **Legitimate only if it ships with a discriminating test the operator can pass or
fail — a reframe with no new metric is rebranding.**

**Why it is the correct object, not a rescue narrative.** Under the Track-2 UDE decomposition
`dC/dt = Transport[C] (known, differentiable, trusted from ECCO) + N_θ(C, forcing) (learned reaction
closure)`, the learned piece never predicts the full next state — it supplies the source−sink biological
tendency the resolved transport integrates. The deflation compared a *closure* against a *forecaster's*
baseline (AR(1)) on a *forecaster's* metric (1-step). That is a category error in the evaluation,
independent of whether the closure is good.

**The lineage that gives it standing [established, attributed to the lineage note]:**

1. **Legitimacy of a coarse operator — Deng–Hani–Ma (2025, Hilbert's 6th / Boltzmann-from-Newton).** The
   macro law is the provable statistical limit of the micro system under explicit scaling; the proof tracks
   the interaction history and shows most of it can be cut without accumulating error. The *license* for a
   coarse operator: it establishes which correlations must be kept vs are negligible.
   > **Adversarial flag:** cite the **mathematical content only.** The lineage note's "Fields Medals, ICM
   > 2026" attribution is a forward-looking claim we do not verify and must **not** stake anything on.
2. **Learn it when the analytic closure is intractable — Han, Ma, Ma, E (PNAS 2019).** Learn generalized
   moments, then the closure on them. Ocean-BGC subgrid *is* the intractable-closure regime; our operator
   is a learned moment closure that was simply mislabeled.
3. **Bake in the invariances — Huang–Ma et al. (invariance-preserving Boltzmann–BGK, arXiv:2110.03682).**
   The architectural contract below.

**Honest counters (state loudly — these keep it from being a dodge):**
- **(a) Self-twin at operator scale [ours guardrail].** An emulator trained on ECCO-Darwin's own monthly
  tendency learns **Darwin's closure, not the ocean's.** Honest framing: "a fast, differentiable surrogate
  for Darwin's biology." **Not** "learned real biology." Same line Track-1 holds.
- **(b) The reframe must relocate the test, not just the label.** If the closure, integrated on prescribed
  transport, still fails at multi-month horizon *and* on invariants *and* on counterfactual forcing, the
  framing saved nothing. **If it fails counterfactual-forcing response in particular, the program is in
  trouble and we report that.**

**Architectural contract the reframe demands** (a black-box CNN cannot be a closure):
- **Conservation by construction** — parameterize the biological term as a reaction network with closed
  C:N:P:Fe budgets (or the divergence of an internal flux), not a loss penalty.
- **Positivity/realizability by construction** — softplus/exp outputs, non-negative rates; *forbid* the
  4.5%-negative-iron failure structurally, don't penalize it.
- **Invariance, made concrete for us** — the steady-state **S/k ratio invariance** (Track-1 Q3):
  reparameterize the closure to `(ratio, product)` so that where data cannot break the degeneracy, only the
  identifiable combination is free. Direct bridge from Track-1 identifiability geometry to Track-2
  architecture.
- **Prescribed transport is the point** — the network never spends capacity re-learning advection (which
  AR(1) already owns as "stuff stays put"); it isolates the local biological closure. This is *why* UDE >
  pure emulator here.

**The exact next experiment (NOT 1-step skill).** Integrate the learned closure on prescribed ECCO
transport and evaluate on the three axes AR(1) is blind to:

1. **Long-horizon rollout stability & trajectory tracking** — multi-month to multi-year. AR(1) decays to
   climatology and cannot represent drift/trend; the small monthly tendency *accumulates* into a gap a good
   closure can close and persistence cannot. **This is where a closure can beat persistence even when
   1-step cannot.**
2. **Invariant / conservation error over the rollout** — global mass budgets, stoichiometric ratios,
   positivity fraction. A dimension AR(1) is simply blind to.
3. **Counterfactual forcing response (the real discriminator)** — perturb forcing (iron deposition,
   warming), test on held-out regimes. **AR(1) has zero counterfactual skill by construction;** a genuine
   closure responds. This is also the actual use case.

Plus **(4) coarse-scale emergent properties chosen carefully** — bloom phenology timing, front sharpness,
spectra — **not** pointwise pattern correlation (Track-1's lesson: box-vs-model pattern correlation is not a
fidelity metric; CoV ~1e-15 at uniform parameters).

> **Adversarial flag [speculation].** Axis 1's "the small tendency accumulates into a gap AR(1) cannot
> close" is a *plausible mechanism, not a measured result.* It is the hypothesis the experiment tests, not
> its foretold outcome. State it as such — the honest position is "winnable and worth testing," never
> "will win."

---

## 5. Sharpened questions for a math expert

Grounded in verified DarwinDiff findings. Q1/Q3 refine the existing closure-theory-questions note; Q2, Q4,
Q5 are sharpened by this synthesis.

1. **Forward/inverse null-space duality (the genuine-contribution-if-true question).** Deng–Hani–Ma cut
   statistically-inert *correlations* from a forward closure without accumulating error; our inverse problem
   cannot recover statistically-inert *parameter directions* (sloppy Fisher modes — the iron pair's S/k
   direction, verified at per-AOI 2×2 conditional correlation +0.94 in eqpac and N. Atlantic). **Do the
   closure's neglected-correlation operator and the observation-restricted Fisher share a null space, or is
   this only an analogy?** If formal, it is a real contribution; if not, we label it analogy and stop.
   *(Honesty rule: this is currently [speculation] — say "analogy" until proven otherwise.)*

2. **Is a 0-D-per-cell reaction surrogate a legitimate coarse-graining, or are we fitting the residual of a
   bad closure?** The box throws away exactly the spatial correlations that carry identifiability
   (surrogate gap is dimensional; box CoV ~1e-15 vs the model's O(1) structure). Making parameters
   spatially varying recovers the trio 25/50 (n=50; →~41/50 at 4000ep) where a global-scalar control recovers
   0/50. Is "let closure parameters
   vary in space" a legitimate coarse-scale-operator-carrying-subscale-information move, or is it smuggling
   the discarded DOF back through the parameter field? Is there a scaling regime where a 0-D-per-cell
   reaction surrogate is the provable limit of the 3-D advection–reaction system with advection as the
   neglected term, and what controls the error?

3. **Should the S/k steady-state ratio invariance be a hard architectural constraint** (reparameterize to
   `(ratio, product)`, only ever identify the ratio from steady data) rather than discovered as a sloppy
   direction after the fact — analogous to conserved quantities in entropy-based closures? **Verified
   nuance:** the degeneracy is *basin-dependent* — subsurface iron resolves it in the Southern Ocean (2×2
   condition number 2.2) but not in eqpac / N. Atlantic (condition 35–51). Is that a statement about the
   observation operator's rank on different sub-manifolds?

4. **How many temporal moments separate a source rate from a loss rate that share a steady-state fixed
   point?** The first time-resolved fit was AOI-selective: it recovered Southern-Ocean iron scaling (+5/10)
   and a N. Atlantic growth rate (Smallgrow +4/10) the time-mean cannot, but *regressed* N. Atlantic alpfe
   (−4) and equatorial-Pacific diatomgraz (−6) where the annual cycle is weak, and left the second growth
   rate (Biggrow) unrecovered (consistent with Spitz et al. 1998). We want the theorem — which
   phase/relaxation timescales are needed, and why weak-seasonality regimes lose rather than gain — not the
   seasonal-inventory intuition.

5. **Predictability-horizon lower bound for a learned closure vs damped persistence.** Given a red BGC field
   with known autocorrelation and a transport operator with known memory (nutrient advection, subsurface
   reemergence), is there a horizon below which *no* learned closure integrated on prescribed transport can
   beat damped persistence — i.e., a formal statement of "the tendency-to-anomaly ratio is too small to
   exploit"? This would convert our empirical 1-step deflation into a provable regime boundary and tell us
   the minimum lead at which the §4 experiment *could* succeed.

---

## Adversarial-verify summary — claims flagged for overreach

| Claim | Tag | Disposition |
|-------|-----|-------------|
| Emulator "beats persistence" at 1-month | retired | Removed everywhere; the AR(1) deflation is [ours-verified]. |
| "Nobody has a global ocean-BGC neural operator" | softened | **Partially false as of 2026.** BG4Sea (global, PISCES) + others narrowed it; residual gap re-stated narrowly (§3). |
| FourCastNet ~45,000× speedup transfers to BGC | rejected | Weather-specific (large tendency-to-anomaly). Take architecture/geometry only. |
| Deng–Hani–Ma "Fields Medals, ICM 2026" | do-not-stake | Cite mathematical content only; the prize attribution is unverified and load-bearing on nothing. |
| Mogen 2023 / Krumhardt 2020 exact horizon numbers | verify-before-quote | Paywalled (402); qualitative claims corroborated, exact numbers not verified. |
| "Small tendency accumulates → closure beats AR(1) at long horizon" | [speculation] | The hypothesis the §4 experiment tests, not a foretold result. |
| Forward/inverse null-space duality (Q1) | [speculation] | Label "analogy" until formally proven. |
| "Made Darwin differentiable" / "learned real biology" | forbidden | Not asserted anywhere; self-twin framing held ("surrogate for Darwin's biology"). |
| Longer-horizon/scenario forward value | [speculation] | Plausible, unproven; only away from 1-step; ESM sets a high physical bar and the biological increment is small (Frölicher 2020). |

**One-line ranking:** inversion-surrogate / learned-closure (established strength, no persistence
comparison) ≫ longer-horizon / scenario forward tool (plausible but unproven, and only away from 1 step) ≫
1-step forward emulator (structurally ~zero headroom — retired).

---

### Sources
- FNO — arXiv:2010.08895 · AFNO — arXiv:2111.13587 · FourCastNet — arXiv:2202.11214 · SFNO — arXiv:2306.03838
- GraphCast — arXiv:2212.12794 (Science 2023) · Pangu-Weather — arXiv:2211.02556 (Nature 2023)
- NeuralGCM — arXiv:2311.07222 (Nature 2024) · ACE — arXiv:2310.02074 · ACE2 — Duncan 2024 (Ai2)
- Samudra — arXiv:2412.03795 · SamudrACE — arXiv:2509.12490 · OceanNet — arXiv:2310.00813 (Sci. Reports 2024)
- BG4Sea — Mercator Ocean (2026) · Global surface chl-a — Biogeosciences 23:2601 (2026) · 1-D BGC emulator — arXiv:2606.27168 · GOBAI-O2 — ESSD 18:287 (2026)
- Mogen 2023 — Earth's Future 10.1029/2023EF003605 *(paywalled)* · Séférian 2014 — PNAS · Park 2019 — Science 10.1126/science.aav6634 · Frölicher 2020 — Biogeosciences 10.5194/bg-17-2061-2020 · Krumhardt 2020 — GBC 10.1029/2020GB006531 *(paywalled)*
- Zhang 2019 — GRL 10.1029/2019GL085159 · Baxter 2026 — GRL 10.1029/2025GL119877 · Collins 2002 — J. Climate
- Closure lineage: Deng–Hani–Ma 2025 · Han, Ma, Ma, E — PNAS 2019 · Huang–Ma — arXiv:2110.03682 (see `docs/research_notes/2026-07-23_learned_closure_lineage.md`)
