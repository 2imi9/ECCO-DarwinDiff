# Subsurface-iron up-weighting does NOT rescue scav_rat recovery (job 188074)

**Verdict: the pre-registered hypothesis is falsified.** Up-weighting subsurface GEOTRACES iron
degrades per-AOI `scav_rat` recovery instead of improving it. The GN-Fisher conditioning gain from
subsurface [DFe] (cond 3022→2.2, ~1400×; job 188077) does **not** convert to recovery. The
information-vs-recovery gap stands: `scav_rat`'s recovery limit is downstream of conditioning
(optimization / structural surrogate misspecification of the subsurface profile), not an information wall.

All three arms are `verify_run`-gated (exit 0), n=10.

## Design (clean dose-response)

`subiron_recovery.sbatch`, AICR B200, 3-task array. The **only** varying knob is `GEOTRACES_SUB_W`.
Everything else is the flagship-full config, identical across arms:

- `GEOTRACES_W=1.0`, `POC_SUB_W=3.0`, `NB23_PINN_WEIGHT=3.0`, `CHL1_W_EXTRA=3.0`, `DARWIN_PATTERN_W=1.0`
- `daniels_rpicpoc_w=1.0`, Darwin IC, **no MLD channel**, 2000 epochs, seeds 0–9
- AOI weights `{eqpac:1, natlsubpolar:2, southernoceanpac:2}`

## Result (grade_recovery.py, per-AOI ≥2-of-3 = the honest metric)

| param | subW=1 (arm0) | subW=3 (arm1) | subW=8 (arm2) |
|---|---|---|---|
| **scav_rat per-AOI** | **9/10** | **5/10** | **1/10** |
| scav_rat cell-wtd | 7/10 | 10/10 `straddle +5` | 10/10 `straddle +9` |
| scav_rat Cal+ (eqpac / natl / sout) | 3 / **7** / **10** | 2 / 3 / 10 | 3 / **0** / **2** |
| iron_pair per-AOI (honest) | 9/10 | 5/10 | 1/10 |
| rho(alpfe, scav_rat) | −0.73 | −0.51 | −0.85 |
| alpfe per-AOI (median) | 10/10 (0.975) | 10/10 (0.801) | 10/10 (0.842) |
| R_PICPOC per-AOI (median) | 10/10 (0.053) | 10/10 (0.052) | 10/10 (0.050) |
| diatomgraz per-AOI | 0/10 | 0/10 | 1/10 |

Carroll: `scav_rat` 6.025e-7 s⁻¹, `alpfe` 0.9283, `R_PICPOC` 0.04245. `diatomgraz` collapse is expected
(no MLD channel — see the covariate-channels finding).

## Reading

1. **Falsified.** `scav_rat` per-AOI recovery **falls monotonically** 9→5→1 as subsurface iron weight
   rises 1→3→8. The natl and sout legs collapse (natl 7→3→0; sout 10→10→2). This is the opposite of the
   prediction that improved conditioning would raise recovery.
2. **The cell-weighted "improvement" (7→10→10) is a straddle artifact** (flagged +5, +9): up-weighting the
   subsurface term pushes per-AOI `scav_rat` to *opposite sides* of Carroll, and the cell-weighted mean
   happens to land near Carroll. This re-confirms that the honest per-AOI ≥2/3 metric is load-bearing and
   the cell-weighted number overstates.
3. **Conditioning ≠ recovery, confirmed.** Job 188077 established that subsurface [DFe] makes the
   `{alpfe, scav_rat}` GN-Fisher well-conditioned (cond 3022→2.2). Forcing the *recovery* loss to match that
   same subsurface profile harder makes recovery worse — so the information the Fisher sees is not
   exploitable by the fit without introducing bias. Most likely mechanism (hypothesis, unproven): the
   2-layer box cannot faithfully represent the real subsurface [DFe] profile, so up-weighting a
   structurally-misspecified term drags `scav_rat` (and pulls `alpfe`'s central value off Carroll:
   0.975→0.80) rather than pinning it.
4. **The ridge is not cleanly broken by weighting.** rho(alpfe, scav_rat) is non-monotonic
   (−0.73 / −0.51 / −0.85); the grader labels arm0 and arm2 "ridge INTACT: scav_rat unconstrained."

## Live lead — RESOLVED (was seed luck)

> **RESOLVED** (see `2026-07-23_overnight_geometry_and_seasonal.md` §5, jobs 188532/188511, VERIFIED): the
> n=10 subW=1 "9/10" was **seed luck**. At n=50, subW=1 = **26/50** (= the flagship 25/50); subW=0
> (surface-only) = **4/10**; subW=1 replicate (seeds 10–19) = **6/10**. So balanced subsurface iron is at most
> a *small* real improvement over surface-only (4/10 → ~52%), **not a new operating point** — and over-weighting
> it degrades recovery (subW=3/8 → 5/10, 1/10). The scav_rat recoverability was later shown to be largely an
> *optimization* limit (4000 epochs → 41/50; see `overnight_recovery_sweep_groupA.md` LEAD A), not a subsurface
> data lever.

*(Historical hypothesis, now falsified — retained for the record.)* The balanced-weight arm (subW=1) recovered
`scav_rat` 9/10 per-AOI at n=10, which we suspected might be a better operating point or seed luck. A controlled
`subW=0` + replicate follow-up was launched to isolate the subsurface contribution; it confirmed the seed-luck
reading above.

## Provenance

- Job 188074 (`/scratch/qi_zim_neu/subiron/arm{0,1,2}_subW{1,3,8}`), graded
  `scripts/grade_recovery.py --expect-seeds 10 --params alpfe,scav_rat,diatomgraz,R_PICPOC` (exit 0).
- Conditioning companion: job 188077 (`identifiability_sloppiness.py --mode fisher_gn`), logged in
  `docs/research_notes/2026-07-23_expert_review_corrections.md` §A.
