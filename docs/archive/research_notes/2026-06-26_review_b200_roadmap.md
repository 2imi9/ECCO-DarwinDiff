# DarwinDiff — research review, B200 opportunities, and prioritized roadmap

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data/plans stand, framing corrected by [STATUS.md](../../../STATUS.md). The project is a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC} — **not** a 6/6 chase or a '5/6 ceiling / parameter-conservation' result. The growth pair {Smallgrow, Biggrow} is unobservable by construction. **R_PICPOC is recoverable** at 1° with a real calcite anchor (Daniels/MODIS) + `RATIO_MAX=2` — the differentiable Darwin calcite port and native resolution were *tested and did not help*, so R_PICPOC is **not cluster-gated**. `geo1` holds {alpfe, scav_rat, R_PICPOC} jointly 7/10; diatomgraz is an open iron-pair tradeoff. The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, CV→1e-15), so box-vs-Darwin pattern-matching is not a fidelity metric.


**Date:** 2026-06-26 · **For:** epic #124 · **Source:** comprehensive review workflow (8 agents:
3 audits + 2 opportunity scans + adversarial verify + synthesis) + the completed real-data
agreement audit. Honest/critical by design.

## State of the research (honest)

Strongest defensible claim: a **surrogate-to-model identifiability study** (#116) — a
differentiable iron-budget box that recovers a known-truth model's params and, via FIM/
profile-likelihood, exposes which Carroll-6 directions are stiff/sloppy/init-anchored. The
verify gate is genuinely load-bearing. **The iron pair (alpfe, scav_rat) is the one real-data-
validated result** (real GEOTRACES iron independently agrees with Carroll).

Biggest weakness (must fix in STATUS/README): **"first 6/6" oversells a 3/10 stochastic event
on the looser joint-cellweighted metric**, held by a tuned knob (ironboost 10x), with the iron
leg **initialization-anchored** (the global-θ loss rejects Carroll's alpfe everywhere; the
per-cell DINN cell-mean sits near init). Referee line: "you're reporting the prior, not the
posterior." Right framing: surrogate identifiability + **2-of-6 real-data-validated**; the
structural walls ARE the result.

## Real-data agreement audit (4 of 6 params; `identifiability_sloppiness.py --loss real*`)

| param | real anchor | real-opt | Carroll | verdict |
|---|---|---|---|---|
| alpfe | GEOTRACES iron | 1.0 | 0.93 | AGREES (span 0.33) |
| scav_rat | GEOTRACES iron | 5.3e-7 | 6.0e-7 | AGREES (span 0.75) |
| diatomgraz | GEOTRACES bSi | 0.05 | 0.83 | weak/uninformative (span 0.12) |
| R_PICPOC | MODIS-Aqua PIC | 0.021 | 0.042 | DISAGREES ~2x; STRONGLY constrained (span 371). Caveat: absolute-MODIS bias -> confirm via RATIO_W |
| Smallgrow, Biggrow | none | — | — | unobservable (growth rates not measured; 2-layer freezes diatom growth) |

## Prioritized roadmap (value x feasibility)

Compute tags: **local** (launch-bound, 5090==H200), **now-H200** (free), **needs-B200** (throughput).

| # | Move | Value | Feas | Compute | Prereq |
|---|---|---|---|---|---|
| 1 | Converged FIM/profile spine (all 6 x 4 AOI x loss-modes), ship as paper's identifiability section | high | easy | local/H200 | none |
| 2 | DINN-mean vs global-θ reconciliation; report global-θ as primary | high | easy | local | none |
| 3 | Honest real-anchor table (param:obs:agrees?:circular) | high | easy | local | none |
| 4 | Large seed ensembles n=100-300 -> Wilson CIs on 6/6 & 5/6 rates | high | easy | **needs-B200** | none |
| 5 | Full multi-axis lever grid -> recovery response surface | high | easy | **needs-B200** | none |
| 6 | MODIS PIC -> RATIO_W numerator in MAIN runner (~30-60 lines) | high | mod | local | port cache; 2 AOIs only |
| 7 | GEOTRACES `*_err` inverse-variance weights + per-AOI bin counts + alpfe CI | med | easy | local | none |
| 8 | **Native LLC270 + SEASONAL/transient fits** (the only NEW-physics axis) | high | hard | **needs-B200** | seasonal caches; monthly PIC unstaged; #10 |
| 9 | Amortized inverse (SBI/NPE) -> calibrated posterior UQ | med | mod | needs-B200 | new sampler + sbi dep |
| 10 | Fix 2-layer diatom map (un-freeze MU_DEFAULT_DIATOM) | med | easy | local | forward-model change |
| 11 | Cross-validation battery (leave-one-AOI-out) | med | mod | needs-B200 | extra AOI caches |
| 12 | NO3/PO4 tracer + f_N limitation (DESCOPED from B200 tier) | high-ceiling | hard | data+model, NOT throughput | NO3/PO4 unstaged |

## What B200 specifically unlocks

Single 1° fit is launch-bound (~42 ms/epoch flat 2.8k-105k cells). B200 = pack many launch-bound
fits per GPU x many GPUs = **scale, not speed**. It buys: (1) CIs on the headline rates (#4);
(2) the full recovery response surface (#5); (3) the converged FIM map at scale (#1). **All three
buy tighter error bars on a FORECLOSED wall — rigorous but scientifically flat.** Only **#8
(native/seasonal transient)** buys NEW physics, and it is gated behind #10 + unstaged PIC. So
**B200 is necessary-but-not-sufficient; do NOT spend AICR on bigger ensembles while the staging +
forward-model work that is the only path to new science stays unscheduled.**

## The 3 highest-leverage moves (regardless of compute)

A. **Converged identifiability spine + DINN-mean reconciliation** (#1+#2) — disarms the "reporting
the prior" attack; first exp: converged `--param alpfe --loss full` x4 AOI + overlay DINN
cell-mean drift vs init.
B. **Honest real-anchor table + GEOTRACES error propagation** (#3+#7) — defines the true 2-of-6
scope, obs-error CI on the surviving claim.
C. **MODIS -> RATIO_W non-circular R_PICPOC test** (#6) — resolves real-vs-circular (quick audit:
real calcite ~0.021 vs Carroll 0.042); first exp: wire cache into RATIO_W numerator, n=10 eqpac+natl.

## Stop / descope

- **Stop "first 6/6 / first full six-parameter recovery" headlines** (STATUS.md/README). Re-title
  to honest scope. Pick ONE metric (per-AOI ≥2-AOI) and use it everywhere — metric-shopping is the
  easiest referee kill.
- **Stop treating ironboost as a finding** — confirmation-tuning unless it transfers (held-out
  AOI/native).
- **Descope NO3/PO4 from the B200/throughput tier** — data-blocked model-structure change.
- **Descope the stale `run_v3.0_with_modis_pic.py` fork** — absolute anchor trips the iron mutex +
  lacks v3.2 physics; do the RATIO_W port into the main runner instead.
- **Drop the PRIMPROD_W "growth-rate" claim at steady state** (PP ≈ the mortality flux already in
  the biomass loss).
