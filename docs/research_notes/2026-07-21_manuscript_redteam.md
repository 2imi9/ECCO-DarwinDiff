# Manuscript #1 red-team — findings + revision checklist (2026-07-21)

An 8-reviewer adversarial panel (`paper_reviewer_panel` skill, run as a 17-agent Workflow: 8 lenses →
per-lens verify → synthesis + completeness critic) on the revised `docs/paper/main.tex`. **39 objections
survived a grounded verify pass, 5 killed.** Each cites a specific location and recomputes its numbers.

## Verdict

**The central claim — a parameter-specific identifiability map via a 0-D differentiable surrogate —
SURVIVES the panel, but only in a qualified form.** The panel's own summary: the paper's shield is its
unusual epistemic humility — *nearly every attack is a conceded caveat left unpropagated to a headline,
not a hidden defect.* The decomposition itself holds (alpfe magnitude-pinned; scav_rat per-cell-dependent
but weak; R_PICPOC anchor-imposed; diatomgraz data-blocked; growth pair unobservable). Publishable after
the joint-metric reconciliation, the alpfe/R_PICPOC label demotions, the eqpac-alone ablation, and the
citation/reproducibility cleanup — none of which overturns the map.

## Fixed this session (in the local draft; compiles clean)

- **FeMIP paragraph transcription errors (my own, must-fix):** concentration agrees to ~1.6× (not ~2×);
  the ~2× belongs to *inventory*; 0–194 Gmol/yr is the *sedimentary source* component, not total input.
  Also softened "a contribution to iron-cycle modeling" → "we re-describe the known FeMIP degeneracy in
  identifiability terms," and attributed the section-profile observable to Somes 2021.
- **Joint-metric contradiction (R2/R3/R5/R7, the panel's #1) — body made honest.** Labeled the flagship
  33/50 as *cell-weighted* and stated the per-AOI (paper's own "honest") joint is bounded by scav_rat's
  25/50 → **≤25/50 (0.50)**, below the advertised CI lower bound 0.52. Robustification paragraph +
  load-bearing conclusion now say so. **STILL NEEDS YOUR DECISION (see below) for the abstract/Fig.3.**
- **Missing citations (R8):** added Mahowald 2009 (soluble Fe deposition), Parekh, Follows & Boyle 2005
  (iron/scavenging model, doi:10.1029/2004GB002280 — the correct one), Raue 2009 (profile-likelihood),
  Cleary 2021 + Schneider 2017 (Calibrate-Emulate-Sample), all cited so none are orphaned.

## NEEDS YOUR DECISION (load-bearing; I did not change unilaterally)

1. **The flagship joint number.** The abstract/Fig.3 still lead with 33/50 [0.52,0.78] (cell-weighted).
   Options: (a) report the per-AOI ≥2-of-3 joint as the headline (needs the exact count from the n=50
   geo1 per-seed grades — *not in the repo*; it is ≤25/50, Wilson ~[0.37,0.63]), or (b) keep 33/50 but
   label it cell-weighted in the abstract and give the ≤25/50 per-AOI number alongside. Recommend (a) if
   the per-seed data can be regenerated; (b) otherwise.
2. **alpfe headline label (R5, must-fix).** "method-independent / mass-balance-identified" (title,
   abstract, Fig.2) doesn't carry the body's own concession (l.391) that recovery to 0.928 is
   *weight-conditional and circular* — at default weighting the objective drives alpfe to its 0.05 lower
   bound (opposite Carroll); only a Carroll-selected up-weight makes Carroll optimal. This matches this
   session's seed sweep (alpfe fails in the growth-Si config). Fix: qualify the label; ideally select the
   iron weight by held-out iron CV, not by reference to 0.928.
3. **R_PICPOC "real Daniels anchor" miscredit (R4, must-fix).** The reproducible driver's `RATIO_W` fits
   the box PIC:POC to *Darwin's own* per-cell ratio (self-consistency), not the real Daniels/MODIS calcite
   the paper credits (main.tex:997-999, fig:idmap row 3). The real anchor is only the separate low-power
   e2 control. Relabel headline R_PICPOC as recovered against Darwin's own ratio. **(Also affects STATUS.md
   line 173-175 — verify before editing.)**
4. **RATIO_MAX=2 excludes the disagreeing SO cells (completeness-critic, must-fix).** R_PICPOC's clean
   50/50 may be partly an artifact of dropping the one AOI (SO ratio 0.0067, 6× below the box) the scalar
   can't fit. Report R_PICPOC with/without the exclusion, or justify the cells as non-physical
   independent of their disagreement.

## REQUIRES A RERUN (both cheap; drawn from data mostly in hand)

- **eqpac-alone ablation (rebuttal_diff 4, must-fix).** The per-cell win may be per-cell *absorbing missing
  nutrient/light physics* in natl+SO (only eqpac is genuinely HNLC — the box has iron + constant light,
  no N/P/Si co-limitation; conceded at l.391 but never propagated to the ablation/Fig/Table 2). Decompose
  the ablation by basin: show per-cell still beats global-scalar in **eqpac alone**. Re-grade of existing
  per-seed per-AOI records — no new fit.
- **anchors-only ablation (rebuttal_diff 4).** The geo1 loss is dominated by z-scored Darwin pattern
  terms (POC_SUB_W=3, CHL1_W_EXTRA, PRIMPROD_W) the paper's own gap-(a) calls non-fidelity; only the
  anchor-off→fails direction is shown. Run pattern-off / anchors-only (keep GEOTRACES iron + ratio) and
  report whether the trio survives. Env-var-toggled.
- **sign-flip control at n≥50.** The conceptual heart (alpfe sign-flip, "fitting ≠ identifying") rests on
  n=6, 3/6, Wilson [0.19,0.81] — the only headline never robustified. Cheap synthetic self-twin rerun.
- **integrator step-count sensitivity.** Recovery fit at 200 forward-Euler steps while the box is still
  evolving (CV 4e-5→1e-15); hold recovered params, integrate to {200,800,3200} and show the graded
  means/ratios are stationary. Forward-eval, no re-fit.

## CHEAP CLEANUPS (would each draw a referee's pen; no thesis risk)

- Write the training loss as **one equation** exposing every term + the `/(FET_W+10)` normalization and
  `RATIO_W` warmup; add a complete geo1 lever table with values (several defaults were omitted; `RATIO_W`
  defaults to 0.0 in the driver, so a reader at code defaults reproduces anchor-off behavior).
- Transcribe the **network spec** from `networks.py` (2 hidden 1×1-conv layers, hidden_dim=16, Tanh, 3
  inputs → 6 outputs, ~438 weights); resolve the STATUS "SST-only ~454 weights" vs paper "3-channel"
  discrepancy.
- **Deterministic global arm** (CV~0%, sd 0) has n_eff~1: drop its Wilson CI / rule-of-three / Fisher-on-50
  (pseudo-replication); keep the per-cell CI and state it excludes the global arm's deterministic 0.
- scav_rat collapse "8/10→0/10 p=7e-4" splices cell-weighted onto per-AOI; restate under one metric
  (per-AOI 25/50→1/50), recompute Fisher (~p 0.03).
- W=1-vs-W=3 numeric contradiction ("required ~10× up-weight" vs the W=1 ablation recovering alpfe 10/10):
  tabulate the three weight regimes and name the term that pins alpfe at W=1.
- Soften the "non-differentiable / adjoint unavailable" premise to the operational fact (Carroll-6 BGC
  params are Green's-functions-calibrated, not in the ECCO adjoint control vector); add an adjoint/
  variational marine-BGC citation (Schartau & Oschlies) distinguishing the delta.
- Downgrade "conclusions were pre-registered" → "prior-registered in-repo (commit hash predating results)";
  name the two self-corrections.
- Sub-tier the green "Demonstrated-observable" label (alpfe magnitude-pinned/weight-conditional; scav_rat
  weak; R_PICPOC anchor-imposed); promote the null hit-rates + negative held-out R² from appendix to Fig.2.
- Fisher CV K_Fe=5e-5 sensitivity caveat on the near-saturation reframing; Daniels production-vs-standing-
  stock-vs-rain-ratio three-way distinction; "n=50 corroborates n=10" → report fresh-seed 26/40=0.65.

*Full per-objection detail (grounding + recompute + rebuttal_diff) is in the workflow result; the
panel's single highest-leverage fix is the joint-metric reconciliation (#1 above).*
