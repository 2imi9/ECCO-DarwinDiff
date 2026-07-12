# Does the Track-2 emulator's skill sharpen at finer resolution? (2026-07-12)

**Question.** The native-0.25° anchor (+0.2815) beat the 1° baseline (+0.2554) by +0.026,
gain concentrated in slow carbon DIC/ALK. But the two runs differed in BOTH resolution AND
capacity (modes/width). Does skill *genuinely* sharpen with resolution once de-confounded —
and does it survive a common-grid re-evaluation?

**TL;DR — a nuanced, non-obvious answer (all LOCAL; eqpac + natlsubpolar; self-consistency vs
v05, not real obs).**
1. **Aggregate own-grid skill-over-persistence does NOT sharpen with resolution.** At matched
   capacity the 3-point curve is flat-to-declining, the effect is statistically null, and it
   holds at convergence and in a 2nd AOI. **The anchor's +0.026 was CAPACITY, not resolution.**
2. **But the native model IS genuinely more accurate in absolute terms** — on the identical
   1°-smoothed field with the identical persistence baseline, every native seed beats the
   1°-origin model by ~6–8% lower RMSE (common-grid control, n=4).
3. **Per-tracer, the slow carbon DIC/ALK DO sharpen with resolution** (skill + absolute RMSE),
   even at matched capacity; fine-scale tracers (FeT) degrade — the two cancel in the aggregate.

The naive "skill sharpens with resolution" headline would have been WRONG. The adversarial
controls (matched-capacity cell + common-grid re-eval) are what revealed the real structure.

Design: 5-agent adversarially-checked workflow. Compute: 180 runs, B200 (2-GPU cap, ~4 h),
cubes extracted on Explorer. Harness `scripts/emulator_poc.py` (residual + rollout-k4).

---

## R1 — Own-grid z-skill: no aggregate resolution sharpening

De-confound table (n=10, m=modes w=width, `--residual --rollout-train-k 4 --epochs 500`):

| | 1° (21×51) | native (81×201) |
|---|---|---|
| **m8w32** (matched) | A2 **+0.2600**±.015 | A3 **+0.2535**±.018 |
| **hi-cap** | A4 (m10w48) **+0.2953**±.005 | A1 (m16w48) **+0.2910**±.012 |

- **Pure-resolution effect** skill(A3)−skill(A2) = **−0.0065 ± ~0.007 → NULL** (native slightly
  worse; CI includes 0).
- **Capacity effect** = **+0.037** at native (A1−A3), **+0.035** at 1° (A4−A2) — the same at both
  resolutions. The confounded anchor gap was entirely capacity.
- **3-point curve @ m8w32:** 1° +0.2600 / 0.5° +0.2426 / native +0.2535 — flat-to-declining.
- **Convergence (closes "native converges slower"):** m8w32 skill at 500/1500/2500 ep —
  native +0.254/+0.268/+0.259; 1° +0.260/+0.286/**+0.2895**. The 1° model gains MORE with
  epochs and pulls further ahead. Native never closes the gap.

## R2 — Common-grid control: native IS more accurate in absolute terms (the real resolution benefit)

Native held-out predictions/targets area-averaged onto the 1° grid; identical smoothed field,
common footprint (1071 cells), identical persistence baseline (physical RMSE 10.22). n=4 seeds
each; **all 8 native runs beat the 1°-origin model:**

| model | physical rmse_model | beats 1°-origin? |
|---|---|---|
| 1°-origin (A2, m8w32) | 9.274 | reference |
| native matched-cap (A3, m8w32) → 1° | **8.5–8.9** (mean ~8.7) | ✅ all 4 seeds |
| native anchor (A1, m16w48) → 1° | **8.5–8.7** (mean ~8.6) | ✅ all 4 seeds |

Same persistence RMSE across all three (10.22) ⇒ NOT a denominator artifact; native's absolute
error is genuinely ~6–8% lower. And matched-cap A3 wins nearly as much as A1 ⇒ the absolute-
accuracy gain is **resolution**, not capacity.

**Reconciliation of R1 vs R2.** Finer resolution gives the model more input information → better
large-scale prediction (lower absolute error). But own-grid skill-over-persistence doesn't rise,
because the finer grid also has more hard-to-predict fine-scale variance, raising the persistence
denominator proportionally. The two metrics genuinely diverge; both statements are true.

## R3 — Per-tracer: slow carbon sharpens, fine-scale degrades

Matched-capacity m8w32, own-grid z-skill (and physical RMSE):

| tracer | 1° skill | native skill | 1° rmse | native rmse |
|---|---|---|---|---|
| DIC | +0.120 | **+0.214** | 16.12 | **15.57** |
| ALK | +0.232 | **+0.294** | 15.94 | **15.59** |
| FeT | +0.182 | +0.108 | 1.13e-5 | 1.13e-5 |

Slow carbon DIC/ALK improve in BOTH skill and absolute RMSE at native res, even at matched
capacity — the original anchor DIC/ALK signal is REAL. Fine-scale tracers (FeT) lose skill.
Net aggregate ≈ 0 (R1), but the physical-RMSE-weighted total favors native (R2), because
DIC/ALK dominate the physical error budget.

## R4 — Native capacity surface (why the anchor gap was capacity)

z-skill, native, n=3 (n=10 for m8w32, m16w48):

| modes\width | 32 | 48 | 64 |
|---|---|---|---|
| 8 | +0.254 | +0.279 | — |
| 16 | +0.271 | +0.291 | +0.308 |
| 24 | +0.274 | — | +0.314 |
| 32 | +0.272 | — | **+0.316** |

- **Width dominates** (m16: w32→w48→w64 = +0.271/+0.291/+0.308, ~+0.018 per step).
- **Modes saturate by ~16** at fixed width (m16≈m24≈m32 at w32). Native can use modes>10 that
  1° (Nyquist cap ~10) cannot — but the extra modes add little; the gain 8→16 is real (~+0.017),
  beyond 16 negligible.
- 1° modes ladder saturates at its Nyquist: m4 +0.211 / m8 +0.260 / m10 +0.264.
- 0.5° ladder: m8 +0.243 / m16 +0.272 / m20 +0.252 (declines at the 0.5° Nyquist cap 20).

## R5 — Rollout-k: k4 is the sweet spot (confirmed at native)

native m16w48, 6-step rollout: **k1 +0.297 but beats-persistence@final = 0/3 (FAILS rollout);
k4 +0.291, 3/3 (stable); k8 +0.270, 3/3.** Single-step training maximizes 1-step skill but
destabilizes multi-step; the k4 method-fix default is optimal at fine scale too. (k8 m32w64 +0.288.)

## R6 — Forcing: net-neutral-to-negative (refutes the "missing-forcing artifact")

- native m8w32: off +0.254 → +forcing **+0.216** (HURTS); 1° m8w32 off +0.260 → +0.218 (HURTS).
- native m16w48: off +0.291 → all-3 +0.303 (marginal, within σ); SST +0.280 / wspeed +0.277 /
  mldDepth +0.261 (each single forcing HURTS).
- At matched capacity, forcing does NOT close the native-vs-1° gap (both ~+0.217). ⇒ the
  resolution null is not a missing-forcing artifact. Input-only SST/wind/MLD are not a clear win
  at this AOI/horizon; low-capacity models overfit the extra channels.

## R7 — Generalization: depth + 2nd AOI

- **Depth L3** (18-channel, 0.25°): off +0.301, +forcing +0.293, e1500 +0.318 — all stable, all
  beat persistence. Method extends cleanly to subsurface levels.
- **2nd AOI natlsubpolar** (subpolar bloom): overall skill much HIGHER (+0.48–0.51) — strong
  deterministic seasonal transitions the FNO beats persistence on. **Resolution null replicates:**
  native m8w32 +0.485 vs 1° m8w32 +0.493 (native slightly lower, same as eqpac). BUT rollout is
  weaker here (beats@final 0.2–0.4 vs eqpac 6/6) — **rollout robustness is regime-dependent**, a
  new caveat worth flagging.

## Honest caveats

- skill is doubly relative (own persistence denominator + own z-normalization); cross-resolution
  z-skill is NOT a common scale. R2 (common-grid + absolute RMSE) is the load-bearing evidence.
- common-grid control at n=4 (not n=10); per-tracer/forcing arms at n=3; treat as strong signals.
- eqpac + natlsubpolar only; self-consistency vs ECCO-Darwin v05, NOT real observations. External
  test (SOCAT/GLODAP) is the next step and unchanged by this work.
- per-tracer DIC/ALK sharpening is exploratory (multiplicity); robust in direction across both the
  z-skill and absolute-RMSE views and the common-grid total.

## Bottom line for the write-up

Replace any "skill sharpens with resolution" claim with the honest, stronger structure:
**(a)** finer resolution does not raise aggregate skill-over-persistence (capacity does);
**(b)** it does lower absolute large-scale error (common-grid, robust);
**(c)** the benefit is carried by the slow carbon tracers DIC/ALK. This is a more defensible and
more interesting result than the naive headline, and it directly answers the pre-registered
question. Full run table: `runs/FULL_TABLE.txt` (37 config groups, 180 runs).
