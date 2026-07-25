# Saddle-fix: the θ* saddle was under-convergence, not a genuine indefiniteness (2026-07-21)

Resolves the #120 question (is the non-positive θ* Hessian eigenvalue under-convergence → fixable, or the
genuine source↔scavenging rank-deficiency → corroborates FeMIP). Multi-start FIM driver
(`identifiability_sloppiness.py`), cluster job `8515339` task 0 → `docs/findings/saddle_fix/fim_alpfe_realiron_ms24.json`.
Config: shared-θ, joint 3-AOI (eqpac/natl/SO, equal weights), real GEOTRACES iron only (no calcite anchor),
24-start global search, alpfe profiled.

## Result — θ* is positive-SEMI-definite; the saddle is gone

**Hessian eigenvalues at the multi-start θ\*: [0.0, 0.0046, 0.0051, 0.093, 0.66, 2.29]** — all ≥ 0. The
single zero-eigenvalue direction is **pure R_PICPOC** (sloppy_vector R_PICPOC = 1.0), which is *expected
and structural*: this config carries no calcite anchor, so R_PICPOC has no curvature. In the constrained
(iron-observable) subspace, θ\* is **positive-definite**.

- **So the earlier "θ\* is a saddle" (non-positive eigenvalue) was under-convergence** — the single-start
  from Carroll landed on a worse point; the 24-start global search relieves it.
- For contrast, **Carroll itself is a saddle** of this objective (eigenvalues include −0.55, −0.051) —
  expected, since Carroll's values were never tuned to a dissolved-iron anchor.
- **Stiff direction** = alpfe (−0.81) / scav_rat (+0.59) — the FeMIP-identifiable iron combination.
  **Sloppy directions** = R_PICPOC (unconstrained here) + the two near-flat eigenvalues (~0.005), the
  source↔scavenging sloppy combination.

## Sloppiness, now quotable from a convergent point

Over the positive eigenvalues, the span is **log10(2.29 / 0.0046) ≈ 2.7 decades** — down from the
provisional ~3.96 decades measured at the (per-AOI) saddle, which was inflated by under-convergence. The
FeMIP degeneracy is real (~2.7 decades of sloppiness between stiff and near-flat), but it is a *genuine*
degeneracy at a converged optimum, not a convergence artifact.

**This validates the plan:** the honest fix is Lever-1 (Fisher-eigenbasis reparameterization +
prior on the sloppy direction — now in `scripts/analysis/eki_core.py::reparam_with_prior`), *not*
"converge harder." Converging harder removed the spurious negative eigenvalue but the sloppy ridge
remains — exactly what a rank-deficient (sloppy) inverse problem predicts.

## Caveats

- θ\* sits at several parameter bounds (alpfe ≈ 1.0 upper, diatomgraz ≈ 1.0 upper, growth pair ≈ 0.1
  lower); `rel_grad_norm = 0.49` reflects gradient components pushing into those active bounds, not
  non-convergence of the free directions.
- Iron-only config ⇒ R_PICPOC's zero eigenvalue is by construction; a config with the calcite anchor would
  lift it.
- **Both array tasks are the joint 3-AOI config** (task 0 profiles alpfe, task 1 profiles scav_rat) and
  share the *same* Hessian at θ\* — eigenvalues [0, 0.0046, 0.0051, 0.093, 0.66, 2.29], sloppiness 2.69
  decades, in both. So this run resolves the saddle at the **joint** level only. The STATUS ~3.96 figure
  is a *separate per-AOI (Eq. Pac) analysis* that was NOT re-run here; its saddle caveat still needs a
  per-AOI multi-start before that specific number is quotable. The general lesson (multi-start relieves
  the spurious saddle; the sloppy ridge remains) carries over.
