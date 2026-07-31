# ECCO-DarwinDiff — research map

**Read this before starting work. It is the answer to "what do we already know, and how do we know
it."** Companion to [STATUS.md](../STATUS.md) (canonical numbers) and
[docs/project_map.md](project_map.md) (how the pieces fit). This file answers a different question
from either: *what is the epistemic status of each thing we believe.*

**Why it exists.** On 2026-07-30 a single session re-derived work the repo already contained **four
separate times** (the GHG Center assessment twice, the rain-ratio precedence, the 1-D column study).
Each time the work looked new because nothing indexed *questions already answered*. Section 1 is the
fix. Check it first, every time.

---

## 0. Schema

Five relations. Keys are stable; rows are append-mostly. Where a row changes status, the old row
stays and `SUPERSEDES` records the edge.

```
EVIDENCE   (ev_id, kind, locator, job, gate, n, date)
CLAIM      (cl_id, statement, mode, status, doc)
SUPPORTS   (cl_id, ev_id, relation)          relation ∈ {establishes, qualifies, refutes}
HYPOTHESIS (hy_id, statement, predicts, falsifier, prereg, status)
SUPERSEDES (old_cl, new_cl, reason)
```

`mode ∈ {deductive, inductive, abductive}`, after Peirce:

| mode | question it answers | what makes it strong | what makes it fail |
|---|---|---|---|
| **deductive** | what *must* follow from structure | the derivation, checkable by inspection | a wrong premise; the structure is not what you thought |
| **inductive** | what *does* happen, repeatedly | n, seed variance, a matched null | selection over configs; no null; small n |
| **abductive** | what best *explains* a surprise | it predicts something not yet seen | it explains only what prompted it |

**The project's working loop is abduction → deduction → induction.** Abduce a mechanism from a
surprise, deduce a prediction that would distinguish it, pre-register, then measure. Section 6 is a
worked example that completed on 2026-07-31.

`gate ∈ {exit0, exit2, ungated, n/a}` — no `CLAIM` may cite an `EVIDENCE` row whose gate is not
`exit0` for a recovery count. If there is no artifact there is no result.

---

## 1. SETTLED — do not re-derive

**Check this table before launching anything.** Each row is a question with an answer already on
disk.

| question | answer | where | do not |
|---|---|---|---|
| Is the US GHG Center useful to us? | **No.** Wrong variable, 2020-2022 vs our 1992-2018 (zero overlap), and it is Darwin's own output | `2026-07-23_data_sources_ghgcenter_earthmover.md`, `2026-07-24_ghgcenter_positioning.md` | re-assess it; it has been done twice |
| Which rain-ratio value is live in v05? | **0.041886**, types 2 and 3, from `data.traits`. The published 0.04245 is unreachable | `2026-07-23_v05_perturbation_recipe.md`, `2026-07-30_rain_ratio_which_value_is_live.md` | ask Jon as if open |
| Does a 1-D column break alpfe↔scav_rat? | **Yes.** CRLB(log scav) 4.2e6 → 0.005. Binding confound is remineralization, not kz | `2026-07-22_column_osse_result.md` | redo the design study |
| Is daily data useful for Track 1? | **No.** n_eff 17-24 of ~8,700 steps, fewer than the 158 monthly already held. Growth-pair route is circular | `2026-07-30_daily_design_workflow_recovered.md` | train Track 1 on daily |
| Is daily data useful for Track 2? | **No.** −0.345 ± 0.0015 vs the best free baseline after the log-space fix | `2026-07-30_daily_logspace_training.md` | retry without a new mechanism |
| Can a UDE break the iron degeneracy? | **No.** It is a gauge symmetry; 5 of 6 design angles re-encode it | `2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md` | design another multiplicative-sink UDE |
| Do we need a NASA account to run v05? | **No.** Two `mitgcmuv` binaries + 49 GB inputs already on AICR | `2026-07-31_no_nasa_account_needed_v05_is_already_built.md` | request NAS/HECC |
| Is B-SOSE `TRAC06` free or total iron? | **Total.** `PTR_FE` is the input to the ligand quadratic; `FreeFe` is derived and never advected | `2026-07-30_bsose_trac06_is_total_dissolved_iron.md` | re-litigate comparability |
| Does the v05 monthly `.meta` give usable times? | **No**, the field is wrong and drifts −0.71 d/yr. **But the data are true monthly means** (1.53e-07) | `2026-07-30_monthly_timeinterval_metadata_is_wrong.md` | use `timeInterval`; use `timeStepNumber` |
| Does `PARAM_LOG_SCALE` change the headline? | **No.** Trio 25/50 vs 31/50, paired McNemar P = 0.31 | `2026-07-30_param_log_scale_resolved.md` | re-run the flagship under the log map |

---

## 2. CLAIM — deductive

True by structure. Checkable without new data. **These are the strongest things we have** and they
should carry the manuscript's load-bearing arguments.

| cl_id | statement | derivation | status |
|---|---|---|---|
| D1 | The alpfe↔scav_rat degeneracy is a **gauge symmetry** of any multiplicative sink | `S = r0·g(state)` is homogeneous of degree 1 in `r0`, so `(alpfe, r0) → (λ·alpfe, λ·r0)` leaves the field unchanged for **every** `g` | live |
| D2 | Therefore no learned closure inside a multiplicative sink can remove it; capacity adds directions *along* the orbit | corollary of D1 | live |
| D3 | D2 **predicts** the DOF ladder's inverted U (0/50 → 25/50 → 3/50 → 0/40) rather than merely fitting it | corollary of D2 | live |
| D4 | `R_PICPOC` is a **global exact structural null** for DFe, diatoms and POC | tracer graph inspection, confirmed numerically: ×100 leaves those fields bitwise identical while PIC moves 97.6× | live |
| D5 | `ScavClosure`'s free `log_r0` makes any `scav_rat` profile flat **by theorem** | `log_r0` is exactly redundant with `scav_rat`; both multiply the same term | live, **bug #217** |
| D6 | v05's published `val_R_PICPOC = 0.04245` is **unreachable** | `DARWIN_RANDOM_TRAITS` selects the random generator; its coccolithophore branch fires at `np==9`; `nPhoto=5` | live |
| D7 | A single-AOI run must be graded 1-of-1, not 2-of-3 | the majority rule is defined over the run's own AOIs | live, enforced in `darwindiff.grading` |
| D8 | `build_splits` and the linear trend are invariant to a uniform rescaling of the time axis; only **seasonal** baselines are not | adjacency is a ratio test; the split is index-based; a linear fit is invariant under affine reparameterisation of t | live |

---

## 3. CLAIM — inductive

Measured, with n and a matched null. **Every row here needs its untrained baseline quoted with it.**

| cl_id | statement | n | null | evidence | status |
|---|---|---|---|---|---|
| I1 | `alpfe` recovers robustly across every arm | 50/arm | 10-17/50 | flagship, obs-only, SO-only | live |
| I2 | `scav_rat` recovers in **southernoceanpac only** | 50/arm | 0/50 | 42, 39, 50 of 50 across obs-only arms; 49/50 flagship | live |
| I3 | `scav_rat` is **locally** identifiable there (not inherited) | 50 | 0/50 | single-AOI, 30/50, P = 3.15e-24, gate exit 0 | live |
| I4 | The signal is **depth**, not surface | 50/arm | 0/50 | `so_sub` 33/50 vs `so_surf` 14/50, Fisher P = 2.68e-4 | live |
| I5 | Surface iron identifies the **source**, subsurface the **sink** | 50/arm | 17/50, 0/50 | `so_surf` alpfe 49/50 & scav 14/50; `so_sub` alpfe 14/50 & scav 33/50 | live |
| I6 | Daily emulator loses to per-cell AR(1) after the log fix | 6 arms | n/a | −0.345 ± 0.0015 | live |
| I7 | Monthly loses to seasonal AR(1) | 3/arm | n/a | −0.1841 ± 0.010, reproducing published −0.161 | live |
| I8 | MLD is what gives `diatomgraz` its cross-basin coverage | 50/arm | 32-36/50 | 3-of-3 legs with MLD, 1-of-3 without | live |
| I9 | The trio's binding leg is `scav_rat` | 50 | 0/50 | trio count *equals* scav_rat's | live |

**Standing hazard for this whole section:** there is **no config-selection null**. Every row
measures chance for a *fixed* pipeline, while the flagship was chosen from a sweep. This is the one
referee criticism with no answer, and it applies to I1-I9 collectively.

---

## 4. CLAIM — abductive

Inference to the best explanation. **An abductive claim is not a result until it predicts something
it was not built to explain, and that prediction is tested.**

| cl_id | statement | prompted by | predicted | tested? | status |
|---|---|---|---|---|---|
| A1 | Depth breaks the degeneracy: `alpfe` sets profile **amplitude**, `scav_rat` sets **shape** | 0-D box CRLB 4.2e6 | surface-only must fail for scav, succeed for alpfe | **YES**, 2026-07-31 | **CONFIRMED** → became I4, I5 |
| A2 | The scorer's 1e-12 log floor **favours persistence** | trainer +0.22 vs scorer −0.32 | restricting to strictly-positive cells should recover most of the gap | **YES** | **CONFIRMED** (−0.573 → −0.013) |
| A3 | `R_PICPOC`'s eqpac bias tracks `1/f_calc` | tight, one-sided 1.518× offset | bias should rank with inverse calcifying fraction | partially | **WEAKENED** — held under the wrong calcifier set, eqpac overshoots ~2.9× under the right one |
| A4 | The SO recovery is residual curvature in a nearly-flat orbit | scav recovering despite D1 | surface-only should still recover | **YES**, and it did not | **DISPLACED** by A1 |
| A5 | `--log-transform` helps wide-range channels and hurts narrow strictly-positive ones | surfChl5 got worse | should track CV; surfChl5 CV ≈ 0.26 vs surfChl1 ≈ 12 | consistent, not isolated | **live, untested** |

A4 is the instructive row. It was the *expected* mechanism, it was pre-registered as an alternative,
and the measurement went the other way. Keep it visible rather than deleting it.

---

## 5. HYPOTHESIS — open, with falsifiers

| hy_id | statement | predicts | falsifier | status |
|---|---|---|---|---|
| H1 | Recovery ranks with **subsurface** bin count across basins | any AOI with subsurface iron shows partial recovery | ranking tracks surface count, or no ranking | **open**, testable on data already held |
| H2 | A real-data 1-D column with remin prescribed from v05 recovers `scav_rat` | CRLB near the OSSE's 0.005 | scav_rat↔remin degeneracy dominates anyway | **open**, the named next rung |
| H3 | Route B needs a per-cell → scalar reduction rule; the honest one may be the 0/50 global-scalar arm | forward run response is weak or undefined | a defensible reduction exists that is not global-scalar | **open**, blocks #163 Route B |
| H4 | `Synechococcus` as a calcifier in v05 is a deliberate stand-in, not a literal claim | Jon confirms | it is literal | **open**, question for Jon |

---

## 6. SUPERSEDES — the retraction chain

Keeping this visible is what stops a retracted number coming back.

| old | new | reason |
|---|---|---|
| "~9-month emulator horizon" | 1 step | `delta_t` 900 vs 1200 s calendar bug |
| daily emulator "+0.408 MAKE" | −0.345 vs best free baseline | linear-space artifact |
| `diatomgraz` 35/50 | retired | 34/50 untrained, P = 0.447 |
| "6/50 anchor-off is chance-level, P = 0.078" | Fisher exact p = 0.0133 | wrong null |
| "monthly targets may be window-biased" | data are true monthly means | 1.53e-07 agreement |
| A3 (`1/f` predicts bias magnitude) | weakened | calcifier set is Chl2+Chl3, not Chl1+Chl2 |
| A4 (curvature) | A1 (depth) | surface-only ablation |

---

## 7. Worked example: the loop that closed on 2026-07-31

1. **Abduction** (2026-07-22). A 0-D box cannot identify `scav_rat` (CRLB 4.2e6). *Best explanation:*
   the vertical profile carries it, amplitude vs shape. Recorded as A1 on **synthetic** data.
2. **Deduction.** If A1 holds, then surface-only iron must fail for `scav_rat` and succeed for
   `alpfe`, and subsurface-only must do the reverse. This is forced, not guessed.
3. **Pre-registration** (2026-07-30). Decision rule and falsifier fixed with zero JSONs on disk.
4. **Induction** (2026-07-31). `so_surf` 14/50, `so_sub` 33/50, Fisher P = 2.68e-4, gate exit 0,
   falsifier clears (`alpfe` 49/50 in `so_surf`).
5. **Result:** A1 → I4, I5. A synthetic mechanism, predicted forward, confirmed on real GEOTRACES.

**This is the pattern to repeat.** The strength came from step 2 producing a prediction the
mechanism was *not* built to explain, and from step 3 happening before step 4.
