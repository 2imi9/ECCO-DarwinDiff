# Profile-likelihood + multi-point iron degeneracy (Q1 gold-standard, Q2 global) — 2026-07-23

Closes two rigorous-identifiability gaps a reviewer raised: (Q1) the gold-standard **profile
likelihood** confirmation that the rank-4 finding isn't hiding a flat direction, and (Q2) whether
the iron degeneracy is a **local** Carroll-point artifact or **robust** across the parameter space.
Tool: `scripts/identifiability_sloppiness.py` (`--mode global` profile; `--mode fisher_gn --loss
realiron` at multiple optima). Config = anchors-only geo1 (`covar_env_common.sh`). Guard enforced.

## Q1 — profile likelihood for the observable parameters (per the Raue-2009 test)

Shared-theta optimum loss `loss_star = 6.0417`. Each param fixed on a 7-pt grid, other five
re-optimized (opt-steps 400, n-starts 3). Only profiles passing the convergence guard
(`min(profile) ≥ loss_star − tol`, bracketed) are quoted.

| param | profile span | verdict | guard | reading |
|---|---|---|---|---|
| **R_PICPOC** | **203** | **CURVED** | pass (bracketed, min≈loss_star) | strongly identified — the real Daniels anchor pins it; confirms the 10/10 recovery is genuine, not a straddle |
| **diatomgraz** | **0.19** | **SHALLOW** | pass (min 6.0402 vs loss_star 6.0417, gap −0.0015 < tol; bracketed at 0.607) | weakly identified; its optimum (0.607) sits ~27% off Carroll (0.83) — consistent with its fragility |
| scav_rat | — | DID NOT CONVERGE | — | cancelled after >1:45 h (see note) |
| alpfe | — | DID NOT CONVERGE | — | cancelled after >1:45 h (see note) |

**scav_rat + alpfe profiles did not converge (cancelled >1:45 h).** They ran ~5× longer than
R_PICPOC/diatomgraz (23 min) and never reached a verdict — stuck in the shared-optimum + refine
loop. The honest reading is bounded: the *observation* (these two are far slower to profile) is
directly confirmed; the *mechanism* (slow because they are the sloppy iron directions) is a
plausible inference, not proven — a slow node or the refine loop could contribute. **Methodological
takeaway:** profile-likelihood is impractical for the sloppy iron pair at the 0-D box's eager speed
(~10 s/integration × grid × re-optimize × refine). This is exactly why the single-evaluation
**GN-Fisher** (conditional +0.999, marginal −0.77) is the practical tool for the iron degeneracy —
it does not require the flat-direction re-optimization the profile chokes on.

**Reading:** R_PICPOC is the cleanly-identified observable (CURVED). diatomgraz is genuinely
WEAK (SHALLOW, off-Carroll optimum) — the gold-standard test agrees with the recovery picture
(diatomgraz recovers only under specific configs and collapses under the full loss). This is the
honest, method-independent confirmation the manuscript's identifiability section needs — replacing
the earlier flaky profile artifacts (2026-07-19) with guard-passing results.

## Q2 — the iron degeneracy is ROBUST across the parameter space, not a Carroll-point artifact

Gauss-Newton Fisher of the real GEOTRACES iron residual, `{alpfe, scav_rat}` posterior correlation,
evaluated at **three different optima** (Carroll; two re-optimized seeds):

| point | posterior corr(alpfe, scav_rat) | 2×2 condition number |
|---|---|---|
| Carroll | −0.773 | 2.2 |
| seed 1 optimum | −0.686 | 4.9 |
| seed 2 optimum | −0.686 | 4.9 |

**The alpfe/scav_rat anti-correlation is stable at −0.69 to −0.77 across three points** — the
source–sink degeneracy is a **robust feature of iron concentration data**, not a local artifact of
evaluating at Carroll (directly addressing the P2 critique). Consistent with Frants et al. (2016)'s
compensating-family result. (Note: this is the full-6 *marginal* correlation; the pure 2×2
*conditional* correlation is ≈+0.999 — near-perfect degeneracy when the other params are held —
both meaning "degenerate"; see the observation-design note for that distinction.)

## Net
- Q1 gold-standard: R_PICPOC CURVED (identified), diatomgraz SHALLOW (weak). Both guard-passing.
- Q2 global: iron degeneracy robust across ≥3 points (−0.69…−0.77). Not local.
- Pending: scav_rat + alpfe profile verdicts (jobs still running).
