# Dust-anchor A/B in the real learner (B200, n=5) — result (2026-07-22)

Ran on the AICR **B200** (job 177149, both configs ~1h19; Explorer H200 queue was ~30h so we moved to the free
B200). Anchors-only geo1 env (GEOTRACES iron + Daniels calcite, PINN off); the dust anchor is a guarded Gaussian
prior on physical alpfe (μ=1.15, σ=0.7, from the Xu&Weber Al-inverse Saharan comparison), gated by DUST_ANCHOR_W.
Grading = per-AOI ≥2-of-3, band_of Cal+ ≤40%.

| param | A (W=0) n/5 | B (+dust W=5) n/5 | A median | B median | Carroll | read |
|---|---|---|---|---|---|---|
| **alpfe** | 5/5 | **5/5** | 0.995 | 1.000 | 0.928 | recovered both; dust makes it PRINCIPLED (independent out-of-manifold data, not a weighting artifact) |
| **scav_rat** | 0/5 | **0/5** | 3.85e-7 | 3.81e-7 | 6.03e-7 | **unchanged — as predicted.** Source anchor alone can't move the sink leg; needs the Phase-2 sink anchor |
| **R_PICPOC** | 3/5 | **5/5** | 0.0587 | 0.0573 | 0.0425 | SUGGESTIVE uptick; medians barely move → borderline seeds crossing. Confirm at n=10 |
| **diatomgraz** | 1/5 | 3/5 | 0.451 | 0.452 | 0.830 | count ticks up but median 0.45 is 46% off Carroll → NOT genuinely recovered; borderline noise, do not over-read |

## Honest read
1. **The dust anchor does exactly its job: `alpfe` stays 5/5 and is now principled** — grounded in an independent
   ocean-Al inversion, not the ad-hoc 10× iron up-weighting. This is the manuscript point (source recovery is
   out-of-manifold, not a loss-tuning artifact).
2. **`scav_rat` is 0/5 in BOTH — the honest prediction held.** The source anchor cannot move the sink leg; that
   needs the separate Phase-2 sink anchor (Cochran ²¹⁰Po/²¹⁰Pb + Black flux + the export partition). No breakthrough
   here, and none was expected — a `scav_rat` jump would have been a red flag.
3. **Possible positive side-effect on `R_PICPOC` (3/5→5/5): pinning `alpfe` out-of-manifold may free the Daniels
   calcite anchor to constrain `R_PICPOC` better.** But the medians barely move, so at n=5 this is borderline
   seeds crossing the threshold, not a demonstrated shift. **Confirming at n=10 (running).**
4. **`diatomgraz` is NOT recovered** — median 0.45 vs Carroll 0.83 (46% off); the count uptick is noise. The real
   diatomgraz path is the separate dilution-grazing-rate diagnostic, not this.

## Infra note
First fully-automated **B200** recovery run of the project: `ssh aicr` (cert auth, no Duo), staged current code +
box caches, `b200-batch --account=p2026_0089_neu`, started immediately (no queue) — vs the H200's ~30h backlog.
B200 is the throughput/urgent path when Explorer is congested.

---

# n=10 confirmation (B200 job 177483) — the R_PICPOC uptick was SEED NOISE (2026-07-22)

Both configs `verify_run.py` exit 0 (10/10 seeds VERIFIED & COMPLETE). Grading = per-AOI ≥2-of-3
(`band_of` Cal+ ≤40%), reproduced by a grader that matches the n=5 note bit-for-bit before use.

| param | A (W=0) n/10 | B (+dust W=5) n/10 | A median | B median | Carroll | read |
|---|---|---|---|---|---|---|
| **alpfe** | **10/10** | **10/10** | 0.996 | 1.000 | 0.928 | recovered both; dust makes it PRINCIPLED (out-of-manifold Xu&Weber anchor, not the 10× iron up-weight) |
| **scav_rat** | **0/10** | **0/10** | 3.76e-7 | 3.75e-7 | 6.03e-7 | **unchanged — prediction held.** Source anchor cannot move the sink leg (needs Phase-2 sink anchor) |
| **R_PICPOC** | **6/10** | **8/10** | 0.0588 | 0.0581 | 0.0425 | **the n=5 3/5→5/5 uptick does NOT survive.** +2 seeds only; Fisher exact two-tailed **p≈0.63**; medians identical (~0.058). Seed noise |
| **diatomgraz** | 3/10 | 3/10 | 0.452 | 0.454 | 0.830 | not recovered (median 0.45 = 46% off Carroll); count unchanged |
| ρ(alpfe,scav_rat) | −0.13 | +0.54 | — | — | — | n=10-noisy; alpfe is anchor-pinned (≈0 spread) so this is NOT the degeneracy ridge — do not over-read |

## Verdict on the key question — is the R_PICPOC uptick real?

**No. It is seed noise.** Three independent reasons:
1. **Per-AOI ≥2-of-3: 6/10 → 8/10** is a +2-seed shift on n=10. Fisher exact 2×2 `[[6,4],[8,2]]`
   gives **two-tailed p ≈ 0.63** — fully consistent with no effect.
2. **Medians are identical** (A 0.0588, B 0.0581) — both sit at the real ~0.058, ~1.4× Carroll's 0.0425.
   A real anchor-driven improvement would move the median toward Carroll; it does not budge. The ±2 seeds
   are just borderline crossings of the 40% band edge, exactly as the n=5 note warned.
3. **`verify_run`'s joint (cell-weighted) R_PICPOC grade is 7/10 for BOTH A and B** — identical. Even the
   more-generous joint metric shows zero dust effect. (Both trip `RPICPOC_STRADDLE`: R_PICPOC is Cal+ in the
   cell-weighted mean but in <2 AOIs individually for several seeds — so per-AOI ≥2-of-3 is the honest headline,
   and it too shows no significant lift.)

## What DID hold (the honest predictions, both confirmed)

- **`alpfe` stays 10/10 and is now principled.** The dust anchor's job is to ground `alpfe` in the independent
  Xu&Weber ocean-Al inversion (μ=1.15, σ=0.7) rather than the ad-hoc 10× real-iron up-weight — and it does,
  with no cost to recovery. **This is the manuscript point** (source recovery is out-of-manifold, not a
  loss-tuning artifact).
- **`scav_rat` stays 0/10 in both.** The source anchor cannot move the sink leg — a `scav_rat` jump would have
  been a red flag. This is the honest motivation for **Phase 2**: a *separate* sink anchor
  (Cochran ²¹⁰Po/²¹⁰Pb + Black ²³⁴Th flux + the export partition), assimilating the FLUX not τ, presented as
  BOUNDING (factor ~2), not point-ID.

**Net:** the dust A/B did exactly what the honest prediction said and nothing more. `alpfe` recovers and is now
principled; `scav_rat` is untouched; `R_PICPOC` shows no real dust effect. No scoreboard change; STATUS unchanged.
Both runs `verify_run` exit 0.
