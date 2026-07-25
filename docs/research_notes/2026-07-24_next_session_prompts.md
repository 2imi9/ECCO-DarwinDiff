# Next-session plan + explicit prompts (2026-07-24)

Two ready-to-paste prompts to move from "verified surrogate science" to a submittable GCM claim: (A) apply the
H-batch manuscript reframes; (B) advance the surrogate→GCM validation (#163). Context lives in
[`2026-07-24_overnight_session_summary.md`](../findings/2026-07-24_overnight_session_summary.md) §10 and
[`2026-07-23_v05_perturbation_recipe.md`](../findings/2026-07-23_v05_perturbation_recipe.md).

Sequencing: run **Prompt A** first (fast, doc-only, unblocks AGU + a clean STATUS). **Prompt B** is the
scientific gate and part of it needs NASA compute + Jon, so it starts as prep + a coordination draft.

---

## PROMPT A — apply the H-batch reframes (greenlit; execute)

> Apply the H-batch manuscript-reframe items listed in `docs/findings/2026-07-24_overnight_session_summary.md`
> §10, which I am now greenlighting. Use the exact proposed wording, keep every number `verify_run`-gated, and
> invent no new claims. Specifically:
>
> - **H1.** In `STATUS.md` (the 2026-07-10 bottom-line banner) and `docs/results_matrix.md` (the 2026-07-05
>   verdict), retire "the box is tuning-exhausted / a positive result needs new observations, not more GPU."
>   Replace with the two-component framing: the recoverability gap is a large *closeable optimization*
>   component (scav_rat 26→41/50 at 4000 epochs, natl 19→40, no new data — job 190529) plus a residual
>   *information* component (eqpac 6/50). Compute is no longer a no-op.
> - **H2.** In the STATUS accuracy matrix, reclassify scav_rat "not point-identified (CV≈43%)" →
>   "practical non-identifiability (curved profile in all 3 AOIs, jobs 189403/189870), largely
>   optimization-limited."
> - **H3.** Soften "growth pair unobservable by construction" → "Smallgrow practically non-identifiable under
>   the time-mean; a seasonal prototype recovers it in strong-bloom basins (natl 9/10, +4 vs time-mean,
>   job 189324) — promising, unconfirmed at scale." Keep **Biggrow** unobservable (0/N even seasonal).
> - **H4.** In `docs/agu26_abstract_draft.md`, apply the two flagged rewrites: the PRIMARY iron-mechanism line
>   ("scavenging recovers in the Southern Ocean but not in the degenerate basins") → "scavenging recovers only
>   with sufficient optimization — reaching 40/50 in the North Atlantic at 4000 epochs — and stays stuck in the
>   equatorial Pacific (6/50)"; and the COMPREHENSIVE diatomgraz "circular-only" line → the non-circular
>   Chl+MLD 35/50 in a structural trade-off with the trio. Recount both bodies ≤2000 chars excl-spaces.
> - **H5.** Add to the STATUS independent-validation section: EKI (Iglesias–Law–Stuart, derivative-free,
>   job 189754) reaches the same verdict as backprop (alpfe 0.999 + R_PICPOC 0.0364 Cal-grade; scav_rat
>   2.09e-7 Loose) — closes the DINN+autograd-artifact attack; posterior **mean only** (collapse caveat).
> - **H6.** Qualify the STATUS iron-pair "95% (38/40)" headline against the honest per-AOI 26/50 + the
>   straddle finding (cell-weighted overstates per-AOI by +7 to +10 seeds).
> - Then **refresh `docs/results_matrix.md`** to tonight's n=50 / 4000ep / diatomgraz-non-circular / EKI /
>   seasonal numbers (it is stale at the 2026-07-05 verdict).
>
> Guardrails: `docs/paper/main.tex` is LOCAL-ONLY — for any main.tex core-claim edit, show me the exact
> old→new diff and WAIT for my explicit yes before writing; never `git add` `docs/paper/`. Commit only when I
> ask (no Co-Authored-By, non-squash). Simple, warm style; no confidence percentages; no em dashes.

---

## PROMPT B — surrogate→GCM validation, #163 (do the surrogate side; prepare the GCM side)

> Advance issue #163 — lift the identifiability claims from surrogate-conditional to a GCM claim — using the
> traits-override-safe recipe in `docs/findings/2026-07-23_v05_perturbation_recipe.md`. Do the parts that do
> not need NASA compute now; prepare the parts that do.
>
> 1. **Surrogate side (executable on AICR/local, verify-gate it).** Compute the surrogate parameter-Jacobian
>    table `d ln⟨tracer⟩ / d ln param` for the four observables {alpfe, scav_rat, R_PICPOC, diatomgraz}, each
>    pushed through the SAME observation operator as the inverse problem (correct depth: surface vs subsurface;
>    seasonal phase; the 3-AOI `bin_average` footprints; observation-uncertainty weighting). This is the
>    ground-truth the GCM perturbations get compared against. Reuse `identifiability_sloppiness._import_runner`
>    + central finite differences at ×÷1.1 and ×÷1.2 (two step sizes for the nonlinearity check). Write it to
>    `docs/findings/` with a table + the sensitivity RANKING.
> 2. **GCM side (PREPARE only — do NOT launch; needs NASA Athena/Aitken/Electra + Jon).** Generate the 17 exact
>    perturbation input files (control + 4 params × ÷1.2 / ÷1.1 / ×1.1 / ×1.2, geometric steps) per §3 of the
>    recipe. Put ALPFE/SCAV_RAT in `data.darwin` `&DARWIN_PARAMS`; **R_PICPOC in `data.traits` `R_PICPOC` array
>    (NOT `val_R_PICPOC` in data.darwin — it is overridden and inert); diatomgraz in `data.traits` `PALAT`
>    diatom-prey column** (entries 36 & 43). Include the `STDOUT.0000` verification grep protocol that confirms
>    the perturbed value actually loaded (not the frozen original 0.0418860, not the generation scalar 0.04245).
> 3. **Draft the coordination ask to Jon** (do NOT send — draft for my review, simple warm style, present
>    neutrally without collaborator-attribution): the 17-run OAT ensemble on the current NASA system (Pleiades
>    decommissioned 2026-01-07); benchmark one baseline + one perturbation first to size wall-clock/IO; ≥2
>    symmetric FD step sizes; identical checkpoints/restart, forcing, and time-averaging windows across every
>    run; a convergence-with-integration-length demonstration; verified central differences (the adjoint gives
>    `Jᵀr`, not the observation×parameter Jacobian a Gauss-Newton Fisher needs).
> 4. **State the load-bearing test up front.** Signs agree by construction (the box reuses Darwin's source/sink
>    forms); what must be checked is the cross-parameter RANKING by sensitivity-to-own-observable
>    (diatomgraz ≫ R_PICPOC > alpfe > scav_rat) and the per-entry magnitude ratio. Only ranking agreement
>    licenses transferring the surrogate Fisher eigenstructure (the sloppy/stiff directions, the EKI
>    reparameterization) to ECCO-Darwin. Note v06 ≠ the v05 four-parameter problem — keep validating on v05.

---

## Also queued (smaller, do whenever)
- **AGU:** after H4, submit before **Aug 5** (iron-focused version recommended; NG primary + OS cross-list).
- **Issue tracker:** post progress on #187 (scav_rat optimization-limit + EKI), #152 (diatomgraz non-circular),
  #85 (first seasonal), #188 (structural 4-of-4). Ask me before posting.
- **Optional intro reframe:** the "identifiability schema is the dual of the mechanistic role; one reusable
  Fisher engine, specific leaves" spine (`docs/findings/2026-07-24_parameter_specific_schema.md`).
