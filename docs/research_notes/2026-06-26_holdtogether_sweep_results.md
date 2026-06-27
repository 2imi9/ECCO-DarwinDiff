# Hold-together sweep — results (2026-06-26, H200, n=10×8 configs)

8-config sweep run on Explorer (gpu-short/H200), n=10 seeds each, **all 8 `verify_run.py` exit 0**.
Pre-registered before results (commit 9a4c1d7); conclusions below are after a 4-agent adversarial
review (run `wf_e1b125fc`) that computed Wilson CIs / Fisher exact and red-teamed each claim. Every
conclusion survived **only with qualification** — the qualifications are the point.

## Verified table — per-AOI ≥2-AOI co-recovery (out of 10)

| config (lever vs base) | alpfe | scav_rat | diatomgraz | R_PICPOC | joint{alpfe,scav,Rpic} | joint{+diatomgraz} |
|---|---|---|---|---|---|---|
| base (Daniels=1, Eppley, sparse POSi, default iron) | 8 | 7 | 0 | 10 | 7/10 | 0/10 |
| **geo1** (GEOTRACES_W=1) | 10 | 8 | 0 | 10 | **8/10** | 0/10 |
| dan2 (DANIELS_W=2) | 8 | 8 | 0 | 10 | 7/10 | 0/10 |
| dan0_control (DANIELS_W=0) | 10 | 10 | 0 | 3 | 3/10 | 0/10 |
| geo3 (GEOTRACES_W=3) | 10 | 0 | 4 | 10 | 0/10 | 0/10 |
| geo3sub10 (W=3+SUB=10) | 10 | 0 | 1 | 10 | — | — |
| noeppley (Eppley OFF) | 10 | 0 | 0 | 10 | — | — |
| noposi (POSI_W=0) | 6 | 8 | 4 | 9 | 5/10 | 3/10 |

## Two — and only two — statistically robust effects at n=10

Everything else (differences among the 7/8/9/10 cells) is within sampling noise: Wilson CIs are
0.28–0.52 wide and pairwise Fisher tests are non-significant (p ≥ 0.47). **Do not read the high cells
as a lever ranking.** The two effects that clear Bonferroni:

1. **A ratio observable is load-bearing for R_PICPOC.** Anchor OFF (`dan0`) → R_PICPOC 3/10 with
   per-AOI means *scattered* (eqpac 0.006 / natl 0.061 / SO 0.075); anchor ON (`base`) → 10/10 with
   means *converged* (0.052 / 0.052 / 0.048 ≈ 0.05). Wilson CIs disjoint ([0.11,0.60] vs [0.72,1.00]);
   Fisher p = 0.003; the value-convergence (not just the count) is the hard-to-fake signal.
2. **High iron weight trades `scav_rat` away.** `geo3`/`geo3sub10` (W=3) → scav_rat 0/10 while alpfe
   stays 10/10. Wilson CIs non-overlapping vs geo1's 8/10; Fisher p = 7e-4.

## Hypothesis verdicts (qualified)

**H1 — Daniels load-bearing: survives, but narrow the claim.** The *direction* is robust (above). But:
- It isolates **"any ratio observable," not "the real Daniels data specifically."** The adversarial
  review flagged that this sweep never ran the RATIO_W-on / Daniels-off control (Darwin's *own* ratio
  as anchor) — but **prior project work already did**: `finding_rpicpoc_wall_broken_ratiomax` shows
  the Darwin-ratio anchor (RATIO_W=2, RATIO_MAX=2) recovers R_PICPOC 10/10. Combined with the self-twin
  (R_PICPOC intrinsically identifiable), the conclusion is that **any ratio constraint suffices** to
  recover R_PICPOC — the surrogate just needs *a* ratio anchor. So the Daniels anchor's unique value is
  **not "it recovers R_PICPOC" (Darwin's own ratio does too) but "it does so non-circularly"**: it
  anchors to *real* CP:PP data (landing at ~0.05) instead of grading against Darwin's own PIC/POC. A
  same-config RATIO_W replication would tidy this, but the principle is already established.
- Recovery is to the **real ~0.05, not exactly Carroll's 0.0425**. "Consistent with Carroll" is weak:
  the Cal-grade band is ±40% (factor-1.6), so Daniels (0.027), Carroll (0.0425), and recovered (0.05)
  all fall in one band. And the project's own rain-ratio finding calls Carroll's value biased ~25–30%
  **low** — report "consistent within uncertainty" *alongside* "Carroll is under-constrained," never
  "validates 0.0425."
- In this 3-AOI sweep, **only eqpac + natl have Daniels coverage**; the term auto-gates off in SO, so
  SO's R_PICPOC is not anchor-tested (and SO is the weakest AOI).

**H2 — hold-together: 3 of 4, jointly, at geo1 — and the 4th is a tradeoff, not a block.**
- `geo1` holds {alpfe, scav_rat, R_PICPOC} **jointly in 8/10 seeds** (measured, not inferred) — but is
  **statistically tied with `base`/`dan2` (7/10)** at n=10. Report "tied-best," and run n≥20 to separate.
- **No config holds all 4.** `diatomgraz` never exceeds chance (best 4/10, CI [0.17,0.69]; pooled
  9/80 = 11%). **"Proxy-blocked" is refuted as stated:** `noposi` turns the sparse proxy OFF yet
  diatomgraz *rises* to 4/10 (joint-4 = 3/10, the only config that ever holds 4). diatomgraz=0 in geo1
  is the documented diatomgraz↔iron-pair tradeoff — geo1 chose the iron pair. It is recoverable in
  principle via the dense TRAC16 POSi target (10/10 in prior v3.2), which is **not staged on the
  cluster** — so the question is *open*, not *solved*, and the honest takeaway is **"diatomgraz not
  recovered in this sweep."**

**H3 — iron tradeoff: the fact is robust, the "dose" framing is not.** scav_rat 8→0 at W=3 is bulletproof.
But it is a **threshold/cliff at high weight, not a graded monotonic dose**: `base` sits at lower iron
weight than `geo1` with identical scav_rat (no gradient), there is no intermediate W=2 point, and
scav_rat=0 is *also* reachable via `noeppley` (Eppley off, base iron) — so high iron is sufficient but
not necessary. `noposi` (alpfe 6 / scav 8) shows the two iron params are not a single locked seesaw.

## Honest headline

The real CP:PP anchor adds R_PICPOC on top of the iron pair: **geo1 holds {alpfe, scav_rat, R_PICPOC}
jointly in 8/10 seeds** — a 3-param co-hold the project had not shown before. But (i) the denominator is
**4 observable params** (the growth pair is excluded by construction — no real-world constraint exists),
(ii) the 4th param `diatomgraz` is **not recovered** here (a tradeoff, pending the dense TRAC16 target),
and (iii) only **two** effects are statistically real at n=10 — the anchor→R_PICPOC and the
iron-weight→scav_rat tradeoff. This is a **frontier, not a 6/6**, and not a discovery of Carroll's value.

## Next steps (from the review)
1. **n≥20 at geo1 and dan2** — break the statistical tie for "best operating point" (highest priority).
2. **Stage dense Darwin POSi (TRAC16)** — the only way to adjudicate diatomgraz observability.
3. Report seed-variance/CIs on the per-AOI mean R_PICPOC values (not just point estimates).
4. *(optional)* same-config RATIO_W replication — the principle ("any ratio anchor suffices") is already
   established by `finding_rpicpoc_wall_broken_ratiomax`; this would just confirm it in the 3-AOI config.

Provenance: verify_run.py exit 0 on all 8; pre-registration 9a4c1d7; adversarial review wf_e1b125fc
(4 agents, Wilson/Fisher, all verdicts survives_with_qualification).
