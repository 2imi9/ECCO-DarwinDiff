# Manuscript #1 critical path — prerequisite-ordered plan (2026-07-23)

Purpose: lay out the research prerequisites for shipping Manuscript #1 (the
surrogate-to-model **identifiability study**, issue #116/#188) and make the validation
process faster/accurate/smoother. This folds in the hard-won identifiability lessons
(`finding_identifiability_diagnostics`, `2026-07-19_silicate_fim_artifact_audit`) so we do
NOT repeat the 07-19 failure where 9/13 profile runs passed with confident-but-invalid output.

## The frame (locked, per CLAUDE.md + memory)

- Observable denominator is **4**: {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}. The growth
  pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** — excluded, not failed.
- Headline: a **surrogate-to-model identifiability study**, not a 6/6 chase. Best config holds
  {`alpfe`, `scav_rat`, `R_PICPOC`} jointly 25/50 per-AOI at n=50 (flagship `n50e2k_percell_trio`,
  geo1, 2000 ep; the n=10 7-8/10 was its precursor); with MLD + Daniels anchor, alpfe /
  R_PICPOC / diatomgraz all 10/10 (`mld_dan8`, verify_run exit 0, no straddle).
- Report per-AOI ≥2-of-3 (honest), NOT joint-cell-weighted (overstates — the STRADDLE flag).

## Validation tooling — status

- **Recovery validation: DONE + validated.** `scripts/grade_recovery.py` — one command runs the
  verify_run gate + per-AOI honest grade + joint(cw) side-by-side + explicit straddle flags +
  per-AOI tally + iron-pair. Reproduces hand-grading exactly on `mld_dan8`
  (alpfe/R_PICPOC/diatomgraz 10/10, scav_rat 1/10 per-AOI +9 straddle). Use this to grade every
  recovery run from now on — it is the "smoother/accurate/faster" recovery gate.
- **Identifiability validation: NEEDS THE CLEAN TOOL.** `identifiability_sloppiness.py` has three
  documented traps (below). The clean follow-on the memory prescribes is the **exact
  Gauss-Newton Fisher JᵀΣ⁻¹J** — a single well-posed evaluation at θ*, PSD by construction, no
  re-optimization grid to silently diverge. This is the highest-leverage tooling gap for #120/#152.

## Identifiability traps — encode these before touching the diagnostic

1. **The profile-likelihood convergence guard is real and mandatory.** A profile fixes p and
   re-optimizes the rest, so `min(profile) ≥ loss_star − tol` MUST hold. On 07-19 it fell 7.3
   below on a loss whose whole span is 0.06–0.21 → the "silicate helps" result was manufactured by
   the under-converged arms. `rel_grad_norm` is NOT the convergence test. Never cite a profile that
   didn't pass `valid`.
2. **FLAT ≠ unrecoverable.** The same test calls `alpfe` FLAT (span 0.024), yet the project
   recovers alpfe 9-10/10. So a flat profile span does NOT establish non-identifiability. The
   "diatomgraz structurally non-identifiable" headline is **retired** — do not cite it without
   explaining why the same test calls alpfe FLAT. Safe framing: diatomgraz is constrained only
   through a steady-state biogenic-silica *diagnostic* (not a prognostic SiO₂ tracer, reviewer
   M11), and cite the measured POSi recovery, not a profile span.
3. **The FD-Hessian at Carroll is INDEFINITE** (Carroll is the global optimum, not each basin's
   min) → its inverse-CRLB is invalid. Use the empirical Fisher (PSD) but read the
   eigenVECTORS/null-space, NOT the residual-weighted diagonal magnitudes. The exact GN-Fisher
   gives clean magnitudes and is the fix.
4. **MLD does not enter the loss-landscape profile.** The covariate channel is a DINN *input*; the
   profile evaluates `L(θ)` over a shared global θ[6] with training off. So "diatomgraz-profile-
   with-MLD" is NOT a valid experiment — it would reproduce the MLD-off profile. The MLD → 10/10
   result is a *recovery* fact (DINN can navigate to the optimum), not a *landscape* fact.

## Prerequisite-ordered plan

**P0 — build the clean identifiability tool (blocks the manuscript's independent-evidence section).**
Add an exact **Gauss-Newton Fisher** mode to `identifiability_sloppiness.py`: JᵀΣ⁻¹J at θ* for
the 4-observable config, 4×4 (drop the unobservable growth pair or keep 6×6 and report the null
space). Verify locally (CUDA_VISIBLE_DEVICES=-1, small): (i) PSD, (ii) matches a finite-difference
Fisher to tolerance, (iii) its smallest eigenvector reproduces the known iron-pair sloppy direction
from the empirical Fisher. Only then run on the cluster. This is a *code + verify* task — do NOT
blind-launch it; the whole point of P0 is to stop shipping unconverged artifacts.

**P1 — per-cell spatial CRLB map (#152).** The 0-D box is per-cell independent → the field Fisher
is block-diagonal (6×6 per cell) → no KFAC needed. Produces the "which basin constrains which
param" map that is the manuscript's spatial-identifiability figure.

**P2 — manuscript sections that are already supported by verified results (no new compute):**
reproducibility appendix + inverse-method baseline citations (#117); the straddle/honest-vs-joint
methodology (grade_recovery is the reference implementation); the covariate-channel result (MLD →
diatomgraz 10/10, mechanistic) as the "adding a real environmental predictor closes a recovery
gap" result.

**P3 — Track-2 emulator paragraph (secondary):** the first depth-resolved ocean-BGC
`PrognosticModel` in the Earth-2 stack; no tracer beats a per-cell seasonal AR(1) baseline
(PIC/POC's apparent persistence win was mechanical headroom); DIC/ALK/FeT/Chl
persistence-dominated at 1 month (structural ceiling). Step (a) log-Chl closed.

## What NOT to do

- Do NOT re-run the profile-likelihood grid as the headline evidence until P0 (GN-Fisher) exists —
  it is the flaky path that already burned a session.
- Do NOT cite diatomgraz-FLAT as non-identifiability.
- Do NOT report joint-cell-weighted recovery counts without the straddle flag.
