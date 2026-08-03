# The flagship is bound to a code build: a regression, not a config

**Date:** 2026-08-03 · **Status:** cause localised to a commit range, bisect running (job 256342)
**Supersedes the open question in:** `docs/findings/2026-08-02_flagship_does_not_reproduce_and_the_config_is_not_why.md`

## The measurement

Same configuration, same seeds, two code versions. The 2026-07-26 tree (`5a07ec7`, the build the
flagship ran on) was staged at `~/emulator_poc_0728` and run at 20 seeds (job 256189).

| `scav_rat` | old code (n=20) | published flagship (n=50) | current code (n=50) |
|---|---|---|---|
| **per-AOI ≥2-of-3** | **12/20 (60%)** | **26/50 (52%)** | **1/50 (2%)** |
| eqpac | 2/20 (10%) | 8/50 (16%) | 1/50 (2%) |
| natlsubpolar | 10/20 (50%) | 19/50 (38%) | **0/50 (0%)** |
| southernoceanpac | 19/20 (95%) | 49/50 (98%) | 50/50 (100%) |

**The old code reproduces the flagship. The current code does not.** The flagship number is bound
to a code build, and nothing in any artifact records which build produced it.

The same shape appears in `R_PICPOC`, which had not been noticed at all:

| `R_PICPOC` southernoceanpac | old 16/20 (80%) | flagship 40/50 (80%) | **current 0/50 (0%)** |
|---|---|---|---|

`R_PICPOC` still scores 45/50 overall because eqpac and natl carry the ≥2-of-3 rule, so the
Southern-Ocean collapse is **invisible in the headline count**. It was found only by reading the
per-AOI legs.

## Two suspects eliminated by inspection, not assumption

**Log-space parameter bounding.** `carroll6.py` gained `PARAM_LOG_SCALE` after the flagship ran,
and its comments name `scav_rat` explicitly — "only 7.5% of prior mass below Carroll", "91% of the
sigmoid in the top decade, leaving the optimiser almost no resolution below Carroll". The current
runner calls `bounded_params(..., log_mask=PARAM_LOG_SCALE_MASK)` where the old one passed no mask
at all, which looked decisive. It is not: resolved under the empty env the run actually used,
`log_mask_from_names("")` returns **`None`**, so the bounding is inert and identical to the old
path. Ruled out.

**The DINN.** `networks.py` grew 92 lines, but the only change to `DINN` itself is
`n_outputs: int = 6` → `n_outputs: int = N_PARAMS`, a no-op at N_PARAMS=6. The rest is
`PerParamDINN`, added 2026-08-03 and unused by default. Ruled out.

## What is running

Sixteen commits touched `scripts/run_v3.0_joint_multi_aoi.py` or `src/darwindiff` between
`5a07ec7` and HEAD. Rather than a four-round binary search, **all sixteen are running at once**
(job 256342, one B200 each, 10 seeds each, identical config sourced from `flagship_geo1.sh`).
One round gives the exact commit.

Discriminator: the `scav_rat` **natlsubpolar** leg, ~5/10 on the old build and 0/10 on the current
one — a clean separation at n=10.

Leading candidates by content, to be confirmed or refuted by the run rather than argued:
`b83eb49` (registry-driven parameter count + the pointwise rung), `c4323ae` (+77 runner lines),
`228bccc` ("four corrections from an adversarial mathematical audit, **two of them to today's own
work**"), and `07c9c34` (one definition of the per-AOI rule).

## Why this is the most serious provenance failure found so far

Every previous one was about *recording* — a config not written down, a field not in the artifact,
a certificate computed over zero values. Each was recoverable once noticed.

This is different in kind. **A published number silently stopped being reproducible by the code
that claims to produce it, and nothing anywhere would have detected that.** The gate passes
(`verify_run` exit 0). The config matches on every recorded key. The test suite is green at 753.
The only reason it surfaced is that a pre-registered falsifier demanded the flagship reproduce
itself, and it was run twice.

It also means the earlier framing was too generous. On 2026-08-02 the conclusion was "no artifact
records which code produced which number", stated as a gap in bookkeeping. It is worse: the code
**changed the answer**, in a direction nobody chose, and the change survived a green suite and a
passing gate for up to five days.

## Consequences

- **`scav_rat` 25/50 and the trio 25/50 are unverified** pending the bisect. Do not quote them.
- **`R_PICPOC` 50/50 needs its per-AOI legs restated.** Its Southern Ocean leg is currently 0/50
  against a published 80%, and the ≥2-of-3 rule hides it.
- The Southern Ocean `scav_rat` result (30/50 vs untrained 0/50, P=3.15e-24) is **unaffected** —
  that leg reproduces at 95–100% on every build tested.
- Once the commit is identified, **every published count needs re-deriving on a pinned build**, and
  the artifact must record the commit SHA. That is now the highest-priority change in the repo.
