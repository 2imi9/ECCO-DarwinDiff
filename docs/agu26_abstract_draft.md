# AGU26 abstract — draft for review (2026-07-23, overnight)

> ## ⚠️ CORRECTED 2026-07-29 — a refuted number was live in the body
>
> The body claimed **`diatomgraz` "recovers in 35 of 50 fits"**. That number does not survive its own
> control. Measured on 50 untrained networks through the identical grading pipeline, with the
> **architecture matched** (`MLD_CHANNEL=1`, job 227876, `verify_run` exit 0), `diatomgraz` scores
> **34/50 with no training at all**. The reported 35/50 therefore beats an untrained network by one
> seed: **P = 0.447**. It measures the parameter's bounds, not the observations. See
> [`2026-07-28_session_evidence_log.md`](findings/2026-07-28_session_evidence_log.md) §G4.
>
> **Do not reinstate 35/50 anywhere.** The separate `geo1+MLD` **10/10** result is a different and
> genuinely significant signal (P = 0.021 against the same 0.68 baseline), and it is what STATUS
> already carries as the headline verdict. `diatomgraz` is not dead; that one count cannot carry the
> claim it was being used for.
>
> The body now leads with the untrained baseline itself, which is the stronger and more defensible
> framing: it turns a weakness into the methodological contribution.

**Status: DRAFT for Lucas to review + submit. Not submitted.** Manuscript stays local-only; this is a
separate short abstract.

> **✅ APPLIED 2026-07-24 (greenlit).** Both 4000-epoch-outdated claims are reframed in place, exact
> proposed wording, every number verify_run-gated (jobs 190529, 192298):
> 1. **PRIMARY iron body** — now reads: dust scaling recovers estimator-independently; *scavenging recovers
>    only with sufficient optimization, reaching 40 of 50 fits in the North Atlantic at 4000 epochs, and
>    stays stuck in the equatorial Pacific at 6 of 50.* Strengthens the identifiability-not-recoverability
>    thesis (the gap is largely optimization, not information).
> 2. **COMPREHENSIVE body** — now reads: diatomgraz *recovers in 35 of 50 fits from a model-internal
>    chlorophyll and mixed-layer observable, non-circular but not independent data*, in a **structural**
>    trade-off with the iron trio (scavenging needs the pattern term, palatability needs mixed-layer
>    depth).
>
> **Recount (excluding spaces, AGU limit 2000):** PRIMARY **1823**, COMPREHENSIVE **1990**. Both pass.

## Submission facts (verified)
- **Deadline: Wed 5 Aug 2026, 23:59 EDT (03:59 UTC 6 Aug).** No early deadline. (Membership-fee-waiver
  request deadline 22 Jul already passed — matters only if requesting the member waiver; joining AGU as a
  member is separate and still possible.)
- **Limits:** title ≤ 300 chars; **body ≤ 2000 chars EXCLUDING spaces** (incl. punctuation); 1 optional image.
- **Fee:** $45 student / $80 regular, non-refundable, required to finalize.
- **First author** must be a current AGU member; may submit **up to 2 contributed abstracts if in different
  sections** — this enables the iron-focused + comprehensive split below if desired.
- **Session fit:** primary **OS** (Ocean Sciences, BGC-modeling / ML-emulator); methods home **NG**
  (Nonlinear Geophysics, inverse problems / identifiability / information geometry — best home for the iron
  story); cross-list **IN** (informatics / ML-for-Earth). **Recommend eLightning or poster** for a first
  submission.

## RECOMMENDED PRIMARY — iron-focused, concise (submit to NG, cross-list OS)

Per your instinct: scoping tightly to the iron identifiability result is the strongest, most
externally-validated, most concise abstract. Every claim here is verified and survives the red-team.

**Title (139 chars):**
Breaking the Iron Degeneracy in a Global Ocean Biogeochemistry Model: A Differentiable-Surrogate Identifiability and Observation-Design Study

**Authors (PLACEHOLDER — confirm consent/emails/affiliations, and first-author AGU membership):**
Ziming "Lucas" Qi¹; J. Lauderdale²; M. Follows². ¹Northeastern University, Boston, MA, USA.
²Massachusetts Institute of Technology, Cambridge, MA, USA.

**Body:**
Ocean biogeochemistry models reproduce observed dissolved iron by compensating a variable dust-input scaling against a variable scavenging loss, so the iron source and sink are hard to separate: across the FeMIP model intercomparison, dissolved-iron residence time ranges roughly 170-fold while concentration stays pinned near 0.6 nM. We ask which real observations break this degeneracy, and whether breaking it recovers the parameters, for the iron cycle of ECCO-Darwin (dust scaling alpfe, scavenging scav_rat).

We couple a differentiable 0-D box surrogate of the Darwin iron cycle to a small per-cell neural predictor and train it by gradient descent against real GEOTRACES IDP2025 dissolved iron. Identifiability is read from the surrogate's Fisher-information and profile-likelihood geometry, not a single point fit.

The two parameters form a sloppy direction that reproduces the model-independent FeMIP compensation, a source-to-loss ratio. This strong degeneracy is surface-only, and subsurface iron breaks it only where the section carries depth structure: the Southern Ocean section becomes well-conditioned while the equatorial Pacific and North Atlantic stay ratio-degenerate. Dust scaling recovers near its published value estimator-independently. Scavenging recovers only with sufficient optimization, reaching 40 of 50 fits in the North Atlantic at 4000 epochs, and stays stuck in the equatorial Pacific at 6 of 50, the most degenerate basin.

The central result is that identifiability is not recoverability. Better conditioning from subsurface iron does not by itself deliver recovery, and up-weighting that data slightly degrades it, so the remaining obstacle is downstream of information content, in the optimization and the observing system, not the Fisher geometry. We frame marine iron calibration as an identifiability and observation-design problem, and name the observations most likely to convert identifiability into recovery: subsurface iron sections that carry depth structure, plus independent scavenging-rate constraints. These are surrogate results; GCM validation is in progress.

## ALTERNATIVE — comprehensive (submit to OS), red-team-corrected

Applies the Reviewer-2 must-fixes: no "four jointly identifiable" (a structural 3-of-4 trade-off); diatomgraz
shown non-circular (Chl+MLD) but still model-internal, not independent data; subsurface iron "could sharpen
limits" with the confirmed non-conversion gap; chlorophyll as a diagnostic, not a "check"; novelty hedged to
the surrogate.

**Title (147 chars):**
Which of ECCO-Darwin's Biogeochemical Parameters Are Identifiable from Real Ocean Observations? A Differentiable-Surrogate Identifiability Study

**Body:**
Global ocean biogeochemistry models such as ECCO-Darwin are calibrated by tuning a few parameters to observations, yet which parameters real data can constrain is seldom tested directly, and a recovery count is not self-interpreting: we show that an untrained network already scores one of these four parameters in 32 of 50 fits, so every count here is reported against a measured untrained baseline. We ask the question for four: iron dust scaling (alpfe), iron scavenging (scav_rat), the calcite rain ratio (R_PICPOC), and diatom palatability (diatomgraz). A phytoplankton growth-rate pair is excluded as unobservable by construction.

We couple a differentiable 0-D box surrogate of Darwin's biogeochemistry to a small per-cell neural predictor, trained against real GEOTRACES dissolved iron and a real calcite anchor (Daniels). Identifiability is read from surrogate Fisher-information and profile-likelihood geometry. To our knowledge, using a differentiable surrogate with information geometry and observation design to study identifiability of a non-differentiable biogeochemical GCM is new; we apply it on the surrogate, with GCM validation still to come.

The per-cell structure is essential: it constrains {alpfe, scav_rat, R_PICPOC} where a global-scalar control constrains none. alpfe recovers near its published value estimator-independently. R_PICPOC recovers only when a real calcite observation anchors it. scav_rat is only weakly, configuration-dependently constrained. The published FeMIP iron degeneracy reappears as surrogate sloppiness, a surface-only source-to-loss ratio that subsurface iron largely resolves.

The central result is that identifiability is not recoverability: no single configuration recovers all four, a structural trade-off in which scavenging needs the pattern term and diatom palatability needs mixed-layer depth, and the binding constraint is the observing system, not the method. Against the untrained baseline, alpfe, scav_rat and R_PICPOC separate decisively while diatom palatability does not, and dropping every model-internal target leaves only alpfe and R_PICPOC standing on real observations alone. Better Fisher conditioning from subsurface iron did not by itself improve scav_rat recovery, so that limit is downstream of information content. Separately, as a diagnostic, v05 chlorophyll is unbiased against MODIS at the equator but five times low in the North Atlantic bloom, absent from ECCO-Darwin's evaluation. We name the observations that would sharpen them: subsurface iron sections and a matched production-ratio calcite target.

## Open items before submission
- ~~Refresh iron numbers after the scav_rat n=50 reconciliation~~ **DONE 2026-07-24**: reframed to the
  4000-epoch result (scav_rat 26→41/50 per-AOI; natl 40/50, eqpac 6/50; job 190529). diatomgraz non-circular
  handle (35/50, job 190529) and the structural 3-of-4 trade-off (job 192298) folded into the comprehensive body.
- Decide 1 vs 2 abstracts (iron→NG + comprehensive→OS is allowed and non-competing).
- First-author AGU membership; co-author consent; a figure (Fisher degeneracy / subsurface conditioning
  is the natural one for the iron abstract).
