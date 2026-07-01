# The box homogenizes — the surrogate gap is dimensional, not per-field (DEFINITIVE, 2026-06-27)

> Supersedes the box-vs-Darwin pattern-r tables in `2026-06-26_surrogate_gap_quantified.md` and
> `2026-06-27_box_convergence_finding.md`. Both reported a quantity that is not well-defined. This note
> is the verified, doubly-vetted conclusion (my own CV computation `box_cv_check.py` + adversarial
> review `wf_3e9befaf`, which independently extended integration to 12800 steps).

## Verified finding — the box relaxes to a spatially near-uniform state

At the published Carroll-6 parameters (uniform across cells) under **real per-cell eqpac forcing**
(SST CV 0.04, wind CV 0.12), the box tracer fields have **almost no spatial structure at any
integration length**, and what little they have collapses to round-off:

| steps | FeT | POC | PIC | phyto | ALK |
|---|---|---|---|---|---|
| 200 | 4.0e-5 | 4.4e-5 | 6.7e-5 | 3.5e-5 | 1.7e-2 |
| 3200 | 9.3e-12 | 1.0e-11 | 1.0e-11 | 4.5e-12 | 1.8e-2 |
| 6400–12800 | 1.2e-15 | 1.6e-15 | 1.1e-15 | 2.0e-16 | 1.9e-2 |

(spatial CV = std/mean over ocean cells). Darwin's fields have CV **FeT 2.39, POC 0.60, PIC 0.92**
— four to fifteen orders of magnitude more spatial structure than the box produces.

## What this means

1. **The box-vs-Darwin spatial-pattern `r` for FeT/POC/PIC/DIC is not a meaningful fidelity metric.**
   The z-score amplifies a ~1e-5 (eventually ~1e-15) residual to unit variance and correlates it
   against Darwin's O(1) structure; the result — including the much-discussed eqpac FeT "r" that
   wanders **−0.96 (@200) → +0.81 (@3200) → −0.79 (@6400+)** — is set by vanishing/IC residual and has
   **no converged value.** Do not report these as fidelity. Both prior notes did, in opposite
   directions, and both are corrected here.

2. **What is robust:** **ALK** retains ~2% CV (it is a near-conserved mode pinned to the Darwin IC —
   a near-tautological self-match, *not* evidence of chemistry fidelity), and **surface PIC:POC =
   0.0424**, constant 200→12800 steps and IC-independent — the one load-bearing chemistry number. The
   R_PICPOC regional finding (Darwin's realized PIC:POC spans ~100× across AOIs) is integration- and
   homogenization-independent and **stands.**

3. **The real surrogate gap is dimensional.** A 0-D box, applied per-cell at uniform parameters, has
   **no mechanism to generate large-scale spatial structure** — Darwin's structure comes from ocean
   circulation/advection the box does not represent. So the box cannot reproduce Darwin's spatial
   pattern; not for any per-field-`r` reason, but by construction. This is the honest "surrogate gap."

## Why this strengthens the project's thesis (not weakens it)

- **It is the strongest argument for the per-cell DINN.** Since the box homogenizes at *uniform*
  parameters, essentially all fit-able spatial structure must come from the network varying parameters
  **per cell**. A single global-scalar parameter vector (Carroll's class) would yield a flat box that
  cannot match Darwin's structure at all — the per-cell predictor is doing load-bearing work, not
  cosmetic smoothing.
- **It sharpens why real-data anchors are load-bearing.** The recovery's z-scored Darwin-*pattern*
  loss terms are low-information: at 200 steps they are dominated by the un-relaxed Darwin-warm IC, and
  at convergence the box has no pattern to match. Either way the Darwin-pattern terms carry little
  parameter gradient. The **Darwin-independent absolute anchors (GEOTRACES dissolved iron, Daniels
  CP:PP)** are the terms that actually identify the parameters. This is the rigorous foundation for the
  whole "use real, absolute, Darwin-independent data" strategy — better than the earlier
  "the Darwin pattern is anti-correlated" framing, which was a transient artifact.

## Caveats and open items (honest)

- CV verified at eqpac; natl/SO not re-run for CV but the mechanism (0-D + uniform params → no
  structure) is general. The natl/SO "FeT anti-correlated at 3200" a reviewer might cite is on a
  near-vanishing pattern (CV ~1e-11) — also dust.
- The "integrate longer to fix iron" lead from the convergence note is **not** a clear win: there is no
  converged pattern to improve toward. The controlled n≥10 test (200 vs 1600 steps, jobs
  7902987/7902988) will settle whether longer integration changes iron-pair recovery *rate* — which is
  the only thing that matters; do not pre-judge it on the linearization.
- These are box (surrogate) statements; the box is a proxy for Darwin. The identifiability claims rest
  on the absolute anchors, not on box spatial fidelity.

Provenance: `box_cv_check.py` (my computation, float64, eqpac cache), `box_linearization.py`
(slow mode + 2 conserved modes), red-team `wf_3e9befaf` (4 agents, 12800-step integration, source-verified).
