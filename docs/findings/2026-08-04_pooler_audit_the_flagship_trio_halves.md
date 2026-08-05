# The pooler audit: the flagship trio is 25/50 arithmetic and **12/50 geometric**, and a third of the corpus cannot be checked at all

**Date:** 2026-08-04 · **Tool:** `scripts/analysis/pooler_audit.py` (new)
· **Evidence:** `docs/findings/2026-08-04_pooler_audit.json`
· **Runs:** `collapse/collapse_n50`, `logscale/ctrl_n50`, `wxe/*` (job 258713), `so_only/*`,
`gs_obsonly/*`, `n50e2k_percell_trio` (Explorer)
· **Status:** completes the audit standing since
[`2026-08-03_the_arithmetic_pooler_manufactures_scav_rat_recovery.md`](2026-08-03_the_arithmetic_pooler_manufactures_scav_rat_recovery.md).

## The three answers

1. **The flagship's joint trio halves**, 25/50 → **12/50** under the geometric collapse, measured
   on the flagship's bitwise-identical reproduction (`scav_rat` there is 26/50 against the
   published 25/50, and falls to **13/50**). `alpfe` (49/50) and `R_PICPOC` (50/50) are *exactly*
   invariant.
2. **The arithmetic collapse understates the Southern Ocean**, the one basin where `scav_rat` is
   established: 30/50 → **49/50** geometric. The bias is not one-directional, and the previous
   write-up's "manufactures recovery" framing was half the story.
3. **119 of 211 run directories — 2131 of 6683 seed artifacts — carry no pooler keys at all**, and
   they are disproportionately the runs that carry published numbers. CLAUDE.md's claim that
   "every artifact records `per_aoi_recovered_geom`" is **false**.

## 1. Coverage: what can and cannot be audited

The collapse keys were added on **2026-07-29** (commit `c4323ae`). Everything earlier records only
the arithmetic mean.

| run | what it carries | date | pooler keys |
|---|---|---|---|
| `n50e2k_percell_trio` | **the published flagship**, 25/50 trio | 2026-07-05 | **absent** |
| `logscale/ctrl_n50` | the flagship reproduction, 26/50 | 2026-07-28 | **absent** |
| `confirm/ep4k_n50` | the 4000-epoch 41/50 | 2026-07-23 | **absent** |
| `n50e2k_anchor_off` | `R_PICPOC` 6/50 control | 2026-07-05 | **absent** |
| `abl_global` / `abl_percell` | per-cell vs global-scalar (`ind317`) | 2026-06-27 | **absent** |
| `collapse/collapse_n50` | instrumented flagship twin | 2026-07-29 | present |
| `so_only/*`, `gs_obsonly/*`, `wxe/*` | SO + obs-only + the 2×2 | 07-30 → 08-03 | present |

`pooler_audit.py` **refuses** to substitute the arithmetic key when the others are missing: it
prints `<absent>` and exits 2. That distinction is not pedantic — misreading an absent key as
"no difference" is what produced the retracted code-regression finding on 2026-08-03, and the
repo has now hit that fallacy five times.

**Correction to [`2026-08-03_the_regression_was_a_learning_rate.md`](2026-08-03_the_regression_was_a_learning_rate.md):**
it states the flagship artifacts "exist nowhere" and calls this the last live provenance defect.
They exist, at `/projects/schultz/qi.zim/runs/n50e2k_percell_trio` on Explorer, and re-grade to
exactly the published tuple — `alpfe` 49/50, `R_PICPOC` 50/50, `scav_rat` 25/50, `diatomgraz` 3/50.
The defect is narrower than recorded: the artifacts are present but **predate the instrumentation**.

## 2. The flagship, through a bitwise-identical twin

The published run cannot be pooler-checked from its own artifacts. It can be checked through
`collapse/collapse_n50`, and the chain is tight:

- `collapse_n50` is **bitwise identical to `logscale/ctrl_n50` on all 50 seeds** for all four
  parameters, with identical `loss_final` (39.6575927734375) and identical per-AOI losses. It is
  the same fit with the collapse instrumentation added.
- `ctrl_n50` is the documented flagship reproduction: 26/50 against the published 25/50, the
  already-recorded one-seed difference.

Grading that twin under all three collapses:

| parameter | arithmetic | geometric | median | median per-cell `log_sd` (natl) |
|---|---|---|---|---|
| `alpfe` | 49/50 | **49/50** | 49/50 | 0.000 |
| `R_PICPOC` | 50/50 | **50/50** | 50/50 | 0.214 |
| `scav_rat` | 26/50 | **13/50** | 24/50 | **0.940** |
| **trio** | **25/50** | **12/50** | 23/50 | |

Paired McNemar on `scav_rat`, same seeds and same fits: **13 seeds pass under arithmetic only,
0 under geometric only**, P = 2.4e-04. The pooler never once flips a seed the other way.

### The whole effect is one leg

| AOI | arith / geom / median | `log_sd` | inflation `exp(σ²/2)` |
|---|---|---|---|
| `eqpac` | 8 / 8 / 10 | 0.245 | ×1.03 |
| `natlsubpolar` | **19 / 5 / 16** | **0.940** | **×1.56** |
| `southernoceanpac` | 49 / 49 / 49 | 0.379 | ×1.07 |

Only the North Atlantic moves, and it is the only leg whose dispersion exceeds
σ = √(2 ln 1.4) = 0.820, the point at which the arithmetic collapse *alone* clears the ±40% band.
Given that `southernoceanpac` is a free vote at 49/50 and the ≥2-of-3 rule therefore collapses to
≥1-of-{`eqpac`, `natl`} (recorded 2026-08-03), **the flagship's `scav_rat` majority is carried by
the one leg the arithmetic collapse inflates.**

## 3. The mechanism, quantitatively

Median recovered value as a multiple of Carroll (6.025e-07). The Cal band is ±40%, i.e. **0.60× to
1.40×**:

| run / AOI | geometric centre | arithmetic centre | verdict |
|---|---|---|---|
| flagship twin, `natl` | **0.43×** (fails, below) | **0.58×** (borderline) | inflation carries it *up* toward the 0.60 edge |
| flagship twin, `eqpac` | 0.43× | 0.45× | too little inflation to matter; both fail |
| flagship twin, `sopac` | 0.89× | 0.95× | both comfortably inside; invariant |
| single-AOI SO | **0.73×** (passes) | **1.39×** (at the edge) | inflation carries it *out* past the 1.40 edge |

So there is one rule, not two:

> The arithmetic collapse multiplies the estimate by `exp(σ²/2)`. Whether that raises or lowers
> the count depends only on where the geometric centre sits relative to the band. Below it, the
> inflation manufactures passes. Inside it, the inflation destroys them.

The 2026-08-03 write-up saw the first half in the North Atlantic and generalised to "any
intervention that adds dispersion inflates the count". That is right where the centre is low and
**wrong where it is not** — the Southern Ocean is the counter-example, and it is the basin the
project's one established `scav_rat` claim rests on.

A second reading falls out of the same table: **every geometric centre is below Carroll**
(0.43×–0.89×). Under the correct collapse `scav_rat` is systematically biased *low*, roughly 2×
in `eqpac` and `natl`. The arithmetic mean has been masking a bias, not just adding noise.

## 4. The Southern Ocean gets stronger, and stops being a knife edge

Single-AOI `so_only` (n=50) against its architecture-matched untrained null:

| pooler | count | vs null | McNemar vs arithmetic |
|---|---|---|---|
| arithmetic | 30/50 | P = 3.2e-24 | — |
| **geometric** | **49/50** | **P = 6.3e-59** | 20 geom-only vs 1 arith-only, P = 2.1e-05 |
| median | 28/50 | P = 1.5e-21 | — |

`log_sd` here is **1.310** (inflation ×2.36), the largest anywhere in the corpus.

Band sensitivity, 0.35 / 0.40 / 0.45:

| pooler | 0.35 | 0.40 | 0.45 |
|---|---|---|---|
| arithmetic | 20 | 30 | 35 |
| **geometric** | **48** | **49** | **50** |

CLAUDE.md records `scav_rat` as "a knife edge (22/100 at 0.35, 45 at 0.40, 81 at 0.45)". In the
Southern Ocean **that knife edge is itself an artifact of the arithmetic collapse.** Under the
geometric collapse the leg is at ceiling and threshold-robust, like `alpfe`.

**`so_only2` is not a replication of `so_only`.** All 50 seeds are bitwise identical; the two
differ only in `danielsW`/`posiW`, which are inert in this single-AOI configuration. Anything
citing 237913 and 238079/238080 as two results is citing one.

## 5. The three mandatory checks

1. **Out-of-sample replication — passes.** `wxe/w16e2k` (job **258713**, n=100, separate
   submission, separate code build) reproduces every feature: `scav_rat` 48 → **19**/100, natl leg
   37 → **7**, `log_sd` natl **0.936**, McNemar 29 arithmetic-only vs **0** geometric-only
   (P = 3.7e-09). Caveat, stated rather than buried: five keys recorded by `w16e2k` are `<absent>`
   in `collapse_n50`, so the configs agree on everything *recorded* and are unknown elsewhere.
2. **Band sensitivity — passes.** Geometric is below arithmetic at every band on the flagship twin
   (6 < 13 at 0.35, 13 < 26 at 0.40, 16 < 38 at 0.45). The effect does not peak at 0.40.
3. **Pooler invariance — this is the check.**

## 6. What survives untouched

- **`alpfe` and `R_PICPOC` are pooler-invariant everywhere measured** (`log_sd` ≤ 0.21, identical
  counts under all three collapses). The two globally-recovered parameters are unaffected.
- **The observations-only arms are pooler-invariant**, with `log_sd` = 0.000 in all three basins:
  `sopac` 50/50, `natl` 0/50, `eqpac` 0/50, identical under every collapse. `ind292`, `ind344` and
  `ind359` stand exactly as written.
- **`scav_rat` recovery is real, not abolished.** The geometric count still clears its untrained
  null decisively (19/100 vs 0/100, P = 7.2e-06). The claim that changes is its *size*.

## 7. What this costs the standing claims

- The flagship trio should be reported as **25/50 arithmetic, 12/50 geometric**, not as 25/50.
- `ind352` (26/50 vs 13/50) is confirmed exactly and now has its mechanism and its location.
- `ind317` (per-cell vs global-scalar), `ind342`/`ind345`/`ind353`/`ind354` (the 4000-epoch
  result) and `ind414` (the log bounding map) all rest on runs with **no pooler keys**. They are
  not refuted — they are **unaudited**, and cannot be audited without a re-run.
- `ind343`/`ind348` (Southern Ocean, 30/50) understate their own result.

## 8. Found while filing this: claim ids are not stable

Writing the seven CLAIM rows this finding warrants **renumbered 328 of 563 existing claim ids.**

`gen_research_map.py:78` sorts claims by `(status_rank, statement.lower())` and
`research_map_db.py` numbers them positionally from that order. So inserting one claim — or
merely changing one claim's *status*, which moves it between status buckets — shifts every claim
after it alphabetically. After a trial insertion, `ind342` no longer meant "`scav_rat` is largely
OPTIMIZATION-limited" but the claim previously at `ind341`; `abd555` moved from the arithmetic-mean
hypothesis to an unrelated `R_PICPOC` one.

This matters because **CLAUDE.md, the findings and the commit messages all cite claims by id** —
CLAUDE.md's own "Affects `ind342`, `ind345`, `ind353`, `ind354`" would have silently come to mean
four different claims.

The seven CLAIM rows are therefore **deferred**, and this finding is recorded in the map through
SUPERSEDES, SETTLED and TRAPS rows, which are prose-keyed and provably stable: after adding them,
0 of 570 claim ids changed meaning. Filed as an issue; the fix is a persistent `cl_id` in the
corpus rather than a positional one.

## 9. Practice, corrected

1. **`per_aoi_log_sd` is NOT "already in every artifact".** It is in artifacts from 2026-07-29
   onward — 92 of 211 run directories. Correct CLAUDE.md.
2. **A missing pooler key is a blocking UNKNOWN**, never a silent fallback to the arithmetic
   number. `pooler_audit.py` exits 2; treat that as a gate.
3. **Report the geometric collapse for `scav_rat`, and say which basin moved.** The aggregate
   count hides a sign disagreement between basins.
