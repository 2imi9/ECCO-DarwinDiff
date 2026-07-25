# 1-hour autonomous run — summary (2026-07-23, 11:59→~12:59Z)

Triggered by an expert review of the identifiability findings. The run's theme is honest: **almost
every thread was a correction or a deflation** — the expert review plus this run's own rigor pushed
nearly every claim to a more caveated, correct level. That is the right outcome, not a failure. Full
detail in the per-thread docs; corrections logged in `2026-07-23_expert_review_corrections.md`.

## 1. Iron degeneracy — I overstated it (job 187666)
My "strong −0.77 alpfe/scav_rat degeneracy" was wrong on two counts. It is a **ratio S/k, not a
product**; and the −0.77 is the coupling-inflated full-6 **marginal**. The pure surf+sub 2×2 GN-Fisher is
**well-conditioned (cond 2.2), conditional correlation −0.155**, sloppy direction alpfe-dominated
(+0.98, −0.20) — i.e. with the REAL surf+subsurface GEOTRACES the pair is **largely separated, not
degenerate**. The strong degeneracy (+0.999 conditional) is **surface-only**. So scav_rat is *more*
identifiable than I claimed; its poor recovery is an optimization/coverage limit, not an information wall.

## 2. v05 perturbation ensemble — a silent-failure bug, now pinned
Exactly **two of the four params (R_PICPOC, diatomgraz) are trait-overridden**: perturbing them in
`data.darwin` changes nothing; they must be perturbed in `data.traits` (R_PICPOC types 2&3;
PALAT diatom entries 36/43). Proof it is live: the two v05 files already disagree (`data.traits`
R_PICPOC 0.0419 vs `data.darwin` 0.0425 — note our recovery target of 0.0425 is the generation scalar,
not the loaded 0.0419). alpfe/scav_rat are safe in `data.darwin`. Recipe + FD/convergence/observation-
operator preconditions + the Pleiades-is-gone note in `2026-07-23_v05_perturbation_recipe.md`.

## 3. Novelty — scoped honestly (OpenAlex skill)
Parameter identifiability in marine ecosystem models is an **established field** (Biogeosciences review
bg-14-1647-2017); AD-for-parameter-inference is old (AD Model Builder); the native adjoint is ECCO v4;
BGC observing-system design exists (Argo OSSEs); the iron degeneracy is Frants 2016. **Scientific novelty
is minimal.** The defensible **methodological** novelty is the narrow *combination*: a differentiable 0-D
surrogate as an inversion-side identifiability + observation-design probe for a *non-differentiable* GCM —
stated "to our knowledge," positioned against those five prior works. `2026-07-23_novelty_literature_scan.md`.

## 4. Emulator — no real skill over a proper baseline (baselines v2)
With per-cell **seasonal AR(1)** baselines and 95% spatial block-bootstrap CIs, the depth emulator's
skill-vs-persistence is **+0.068 [−0.033, +0.143] — not significant**, and it is significantly *worse*
than seasonal AR(1) (−0.146). **PIC/POC's apparent win was mechanical** (tendency ≈ whole anomaly → weak
persistence denominator); against AR(1) it vanishes. Both the "beats persistence" and the v1 "beats
climatology 5/6" claims are retired. Track-2's forward-emulator value proposition is weak on this run
(single-AOI/seed caveat, but the direction is clear). `2026-07-23_emulator_baselines_v2.md`.

## 5. Box silica fix — a defensibility win, not an identifiability fix
Adding prognostic SiO₂ to the box (~40 lines; IC already in the Darwin pickup) **retires the reviewer-M11
circularity criticism and unlocks ~630× more real data** (≈6,968 GLODAP silicate bottles vs 11 bSi) — worth
doing. But it does **NOT** make diatomgraz identifiable: prototype shows prognostic-Si is at **parity** with
the circular bSi diagnostic (same growth–grazing compensation ridge). **diatomgraz stays non-identifiable on
real data** (#152 open). `2026-07-23_box_silica_feasibility.md`.

## 6. Frontier null-eigenvector rotation — NO frontier; and the SO rank-2 is now FULLY explained (job 187731)
Swept DANIELS_W ∈ {0.5,1,4,8} × GEOTRACES_W ∈ {1,3}. **eqpac & natl stay rank 4/4 at EVERY weight** — there
is no rank-deficient frontier. The softest observable direction does **not rotate continuously**; it stays
alpfe-dominated (±0.93) except at down-weighted Daniels (danW=0.5) where it **discretely flips to R_PICPOC**
(R_PICPOC loses its anchor). A discrete, weighting-driven swap of *which observable is softest* — an
optimizer/regularization effect, **not an information frontier.** Confirms the Q1 claim. The full eqpac/natl
identifiability ordering (soft→stiff): **alpfe < scav_rat < R_PICPOC < diatomgraz** (diatomgraz is the
*stiffest* where bSi exists).
**The Southern-Ocean rank-2 is now fully explained** (this closes the verify-pass "unexplained second null"):
the two SO nulls are **R_PICPOC** (exact 0 — no Daniels coverage) **and diatomgraz** (8e-7 — the SO has
**zero bSi/POSi bins**). Both calcite AND silica anchors are absent in the Southern Ocean; only the iron pair
(alpfe, scav_rat) is constrained there → rank 2/4. So the SO deficiency is a coverage story for **two**
observables, not one. `docs/findings/2026-07-23_frontier_null_rotation.md` (sweep JSONs under
`/scratch/qi_zim_neu/identif/frontier/`).

## Net for Manuscript #1
The run reinforces the checkpoint verdict — the paper retreats to a correctly-scoped identifiability-
geometry + observation-design study — and adds: (a) the iron claim retreats further (ratio, surface-only,
practical-not-structural, subsurface largely resolves it); (b) the emulator (Track 2) should NOT be sold as
beating persistence; (c) the silica fix is a defensibility improvement to schedule, not an identifiability
unlock; (d) the perturbation ensemble, if Jon runs it, now has a correct trait-override-safe recipe.
