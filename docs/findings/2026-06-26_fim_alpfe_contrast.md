# Converged FIM/profile spine — the iron-pair "collapse" is loss-weighting, not structural

**Date:** 2026-06-26 · **Spine:** C (#120) / D · **Status:** VERIFIED (converged on H200, jobs
7884418 `full` + 7884419 `realiron`, both relaxed). Artifacts: `fim_spine/conv_alpfe_{full,realiron}.json`.
Tool: `scripts/identifiability_sloppiness.py` (PR #145), 3-AOI (eqpac w1, natlsubpolar w2, southernoceanpac w2),
1-D profile likelihood (Raue et al. 2009) over `alpfe`, gating bypassed so the curvature is uncorrupted.

## The result (referee-proof)

Profiling `alpfe` against the two losses gives **opposite-sloped** profiles — the single cleanest
demonstration that the apparent `alpfe` collapse under the full loss is a **loss-weighting artifact,
not structural non-identifiability**:

| loss | `alpfe` recovered (θ*) | loss best at | loss worst at | reading |
|---|---|---|---|---|
| **full** (Darwin z-scored pattern) | **0.103** (≈0.05 init floor) | `alpfe`=0.05 (77.83) | `alpfe`=1.0 (83.30) | full loss *prefers low* `alpfe` |
| **realiron** (real GEOTRACES IDP2025 Fe) | **0.9997** (≈Carroll 0.928) | `alpfe`=1.0 (0.964) | `alpfe`=0.05 (1.284) | real iron *prefers ≈Carroll* |

Carroll's calibrated `alpfe` = 0.92831. Under the full Darwin-pattern loss the profile minimum sits at
the init floor (0.05) and rises monotonically toward Carroll — i.e. the full loss actively pulls `alpfe`
LOW. Under **real GEOTRACES dissolved iron** the profile minimum flips to the high end (≈1.0, ~8% above
Carroll) and the init floor is the *worst* point — i.e. the real iron data **independently pulls `alpfe`
toward Carroll's calibrated value**, with no reference to v05's own output.

## Why this matters

This is the load-bearing evidence for the **surrogate-to-model identifiability** framing (#116) and the
**Fisher/Hessian sloppiness** analysis (#120):

1. **The iron pair is genuinely real-world validated.** `alpfe`'s real grounding is real GEOTRACES iron,
   not twin self-reference — the real data prefers ≈Carroll. (scav_rat co-moves; the pair is identifiable
   once the real-iron term is not drowned by the Darwin pattern terms.)
2. **The "collapse" is an estimator-design / loss-weighting effect**, not a property of the parameter:
   the full loss's z-scored pattern terms normalise away the absolute iron magnitude `alpfe` controls,
   so a single shared optimum prefers low `alpfe`; up-weighting the real-iron term (the `ironboost`
   lever) flips it. This is exactly what the profile geometry shows directly.
3. **R_PICPOC is the sloppy direction** (Hessian at θ*: `sloppy_vector` = R_PICPOC ≈ 1.0; marginal
   stiffness lowest of the six) — consistent with the prior Fisher-sloppiness finding. Its status is
   handled separately (ECCO-Darwin's under-constrained, regional rain ratio; consistent with real
   surface calcite — see `2026-06-26_rainratio_real_vs_darwin.md`).

## Honest caveats (do NOT over-read)

- Both profiles are **SHALLOW** (`full` rel-span 0.07; `realiron` 0.33 — file verdict "weak practical
  non-identifiability") — the real-iron pull toward Carroll is in the right *direction* but the curvature
  is not sharp; more same-type data helps only marginally. State the direction, not a tight CI.
- This is the **iron pair only**. The growth pair (`Smallgrow`, `Biggrow`) is unobserved (θ* Smallgrow
  0.26 / Biggrow 0.12 vs Carroll 0.66 / 0.43 — no anchor pulls them). Do **not** headline a 6/6.
- The Carroll point is not a clean minimum of the full loss (Hessian-at-Carroll is indefinite), which is
  the surrogate↔model fidelity gap itself — the box optimum and Carroll's values differ because the box
  is a proxy, the precise point of the identifiability study.
