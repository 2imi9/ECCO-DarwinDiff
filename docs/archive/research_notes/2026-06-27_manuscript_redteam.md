# Manuscript red-team — 8-lens reviewer panel (#116, 2026-06-27)

Ran the `paper_reviewer_panel` skill as a 9-agent fan-out (R1–R8 + verify/synthesis) on the manuscript
spine. 39 raw objections → verified/merged/ranked. Every numeric objection was independently recomputed.
**The reframed central claim survives** ("a 0-D differentiable surrogate + per-cell NN characterizes an
*identifiable subset* of a non-differentiable GCM's parameters" — the right, BINN-distinct paper). It does
**not** survive *as currently staged*. The fixes:

## Must-fix before submission (highest leverage first)
1. **The committed manuscript is a different paper.** `docs/paper/main.tex` is an old draft whose abstract
   says "recover **five of the six** … the sixth [R_PICPOC] … unrecoverable / foreclosed" — the **opposite**
   of the spine. Rewrite `main.tex` to the identifiability reframe and re-gate every headline on the same
   branch that holds the evidence (#151/#153 + spine-d). *Everything else is downstream of this.*
2. **Per-cell-load-bearing is a non-sequitur (R1-5, rd 4).** "Global scalar → flat box" only holds if
   *forcing* is also uniform; a global-scalar box with per-cell forcing is NOT flat. The homogenization
   result (flat at *uniform params*) is suggestive but does not prove the per-cell *predictor* is needed.
   **Run the ablation:** global-scalar-Carroll-6 + per-cell forcing vs per-cell-predicted params, scored on
   the real anchors; report the delta. (This is the cross-method/per-cell ablation already flagged as the
   #1 research-strength gap.) Until then, soften to "required to *fit* per-cell obs; per-cell param
   structure unvalidated."
3. **Iron-pair "real-world physics" overstates a saturated/shallow/hand-weighted result (rd 3).** K_FE=5e-5
   ⇒ f_Fe 0.67–0.91 (iron near-saturated → identified by DFe mass balance, not iron-limitation physics);
   realiron profile shallow (Hessian indefinite → *direction* not value); recovery required up-weighting
   real iron 10× (GEOTRACES_W 0.3→3). Reframe as **mass-balance + non-circularity**; report K_FE, f_Fe,
   the GEOTRACES_W sweep, and the profile span. (Honest version *strengthens* the dimensional-gap claim:
   the Darwin-pattern block alone does NOT identify the pair.)
4. **The "dimensional gap" defense over-reaches (R1-1, rd 2 but structural).** Box surface PIC:POC ≈ 0.0424
   everywhere vs Darwin **ratio-of-means** 0.033 / 0.676 / 0.0067 — a 16× (natl) / 6× (SO) error that
   **survives spatial averaging** ⇒ it is a structural single-scalar *closure* gap, not a pattern/CV
   artifact. Split the gap into (a) dimensional/pattern and (b) intensive closure; concede (b) caps any
   joint multi-AOI R_PICPOC claim.
5. **Joint 8/10 < marginals is an arithmetic impossibility unless stated (R3/R7, rd 2).** 3×(10/10) forces
   joint = 10/10; 8/10 ⇒ at least one marginal ≤ 8/10 (it's scav_rat). State the three marginals next to
   the joint, or reframe "8/10 = R_PICPOC binds; alpfe/scav_rat pass ~always."
6. **No BINN delta (R8, rd 2).** Zero BINN/Xu citations; BINN (Xu 2025) is structurally identical and the
   "identifiability" reframe *widens* the overlap. Add a Related-Work paragraph naming the delta (external
   GF target vs self-consistency; identifiability characterization; multi-AOI attribution).
7. **Self-twin claim + native-adjoint citation:** the self-twin script now lands on main (#153) — cite it;
   add the missing ECCO adjoint/4D-Var citations (Heimbach/Forget 2015, Menemenlis 2005) at the CTRL claim.

## Net-new (completeness critic)
- **N1:** the committed paper's coccolith-only ablation (0.0049 flat) is the body's *own* argument that
  R_PICPOC fails — it must be reconciled with the spine's "R_PICPOC recovered," not left contradicting it.
- **N3:** "23-yr climatology" averages away the seasonal succession signal that is the natural handle on
  the growth pair/diatomgraz — so "unobservable" is partly a *target-construction* choice, not only a
  data-availability law. Sharpens the growth-pair framing.
- **N4 (a strength to surface):** the binary PIC-anchor mutex (any PIC_ABS_W wipes the iron pair) is a
  *stronger* honest finding than the spine surfaces — it pre-empts "you cherry-picked the config."

## Cheap polish (one pass)
Wilson CIs on 38/40 ([0.835,0.986]) + disclose the 8/10 batch; label every rate (config, n, param-set);
"verify_run.py = data-integrity gate, not validation"; obs-space 80/20 held-out split; Transtrum/Sethna
sloppiness lineage cites; reconcile the diatomgraz "recovered (Darwin POSi 20/20) vs not (real obs)"
states to one canonical statement.

Full ranked table + recompute arithmetic: run `wf_d6a49058` (paper_reviewer_panel fan-out).
