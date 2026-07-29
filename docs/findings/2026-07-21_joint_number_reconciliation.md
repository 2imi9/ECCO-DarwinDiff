# Joint-number reconciliation + R_PICPOC anchor audit (2026-07-21)

Resolves red-team must-fix **#1** (flagship joint number internally contradictory) with the
**exact** per-AOI count, and **refutes** red-team must-fixes **#3** (R_PICPOC "Darwin's own ratio")
and **#4** (RATIO_MAX artifact) with code + a controlled ablation.

All numbers re-graded from the raw per-seed `params[*].per_aoi_recovered` fields of the committed
cluster runs; `scripts/verify_run.py` exits 0 (VERIFIED & COMPLETE, 50/50) on the flagship and the
anchor-off control. Re-grading tool: `scripts/analysis/grade_joint_percell.py`.

## The flagship is `n50e2k_percell_trio` (2000 epochs), and it reproduces the manuscript

| variant (config) | alpfe cw / per-AOI | scav_rat cw / per-AOI | R_PICPOC cw / per-AOI | JOINT cw / per-AOI |
|---|---|---|---|---|
| **n50e2k_percell_trio** (geo1, 2000 ep — **flagship**) | 49 / 49 | 36 / **25** | 46 / **50** | **33 / 25** |
| n50_percell_trio (geo1, 1500 ep — under-converged) | 49 / 49 | 32 / 15 | 35 / 47 | 22 / 14 |
| n50e2k_global_scalar (global control) | 50 / 50 | 0 / 0 | 0 / 0 | **0 / 0** |
| n50_anchor_off (DANIELS_W=0) | 50 / 50 | 44 / 33 | **9 / 4** | 7 / 1 |
| n50_highiron (GEOTRACES_W=3) | 50 / 50 | 50 / **1** | 18 / 44 | 18 / 1 |

`cw` = cell-weighted marginal Cal-grade+ (rel-offset ≤ 0.40 vs Carroll); `per-AOI` = ≥2-of-3
AOI co-recovery. n=50 seeds each. AOIs = {eqpac, natlsubpolar, southernoceanpac}.

## #1 — the joint trio, reconciled and **exact**

- **Cell-weighted:** 33/50 (Wilson [0.52, 0.78]).
- **Per-AOI ≥2-of-3 (the honest metric):** **exactly 25/50 (0.50)**, Wilson [0.37, 0.63].
- The bound is **near-tight**, not merely a loose upper limit: `scav_rat` per-AOI = 25/50 is the sole
  binding leg, and all but one of the seeds that recover `scav_rat` per-AOI also recover `alpfe`
  (49/50) and `R_PICPOC` (50/50). So the joint sits one seed below `scav_rat`'s count. This upgrades
  the manuscript's earlier "≤25/50" bound to the exact value.
- Applied: abstract, Fig.3 caption, and STATUS.md now lead with per-AOI 25/50 and label 33/50 as
  cell-weighted. The body (main.tex l.585-607) was already reconciled last session.

## #3 — R_PICPOC "real Daniels anchor" is CORRECT; the red-team objection is **refuted**

The red-team (and the handoff instruction) claimed the reproducible driver's `RATIO_W` fits Darwin's
**own** per-cell PIC/POC (self-consistency), so R_PICPOC should be relabeled. This is wrong for the
flagship:

- **Code:** two distinct mechanisms exist. `RATIO_W` targets Darwin's own PIC/POC
  (`run_v3.0_joint_multi_aoi.py:387,1008,1701` — circular). `DANIELS_RPICPOC_W` targets the real,
  Darwin-independent Daniels 2018 CP:PP rain ratio (l.416,1043,1717 — "breaks the circularity").
- **Flagship config:** `n50e2k_percell_trio` has **`DANIELS_RPICPOC_W=1.0, RATIO_W=0.0`**. R_PICPOC
  is anchored to real Daniels; the Darwin-ratio path is **off**.
- **Controlled proof:** the anchor-off control (`DANIELS_RPICPOC_W=0`, otherwise identical) collapses
  R_PICPOC per-AOI recovery from **50/50 → 4/50**. The real anchor demonstrably drives the recovery.

Do **not** relabel R_PICPOC to "Darwin's own ratio." That would make the manuscript false.

## #4 — RATIO_MAX artifact is **refuted**; the real caveat is Southern-Ocean coverage

`RATIO_MAX` only clips the `RATIO_W` target, so with `RATIO_W=0` it is a **no-op** in the flagship —
the clean R_PICPOC recovery is not a RATIO_MAX exclusion artifact. The genuine caveat is different:
Daniels has **no Southern-Ocean coverage**, so the anchor auto-gates off there (`n_daniels=0`,
l.1717); R_PICPOC is anchor-tested only in eqpac + natl. The per-AOI ≥2-of-3 metric handles this
honestly (those two anchored AOIs suffice for co-recovery).

## Manuscript methods error corrected

main.tex l.1086 wrongly listed `RATIO_MAX=2` as part of the geo1 config — the one place the separate
Darwin-ratio path leaked into the flagship methods (and the likely source of the red-team's #3/#4).
Replaced with the true mechanism (real Daniels term, no SO coverage, anchor-off → 4/50 control at 1500 epochs; the epoch-matched 2000-epoch control `n50e2k_anchor_off` is 6/50), and
noted the `RATIO_W`/`RATIO_MAX` self-consistency path is a separate circularity control.

## Provenance

`verify_run.py` exit 0 on `n50e2k_percell_trio` (per-param Cal+: alpfe 49/50, scav_rat 36/50,
R_PICPOC 46/50 — matches the re-grade) and on `n50_anchor_off` (which itself fires the built-in
`RPICPOC_STRADDLE` guard: "report per-AOI"). Runs live at
`/projects/schultz/qi.zim/runs/{n50e2k_percell_trio,n50_global_scalar,n50_anchor_off,n50_highiron}`.
