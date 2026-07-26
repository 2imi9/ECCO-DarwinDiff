# Session handoff — 2026-07-26 (start here)

Previous session ran ~8 hours autonomously. Everything is committed and merged except
`docs/paper/`, which is local-only by directive. Read this, then
`docs/research_notes/2026-07-25_deep_research_sweep.md`.

## State

`main` is green: **520 passed, 19 skipped**. Working tree empty. Eight PRs merged
(#193–#199), one open (**#200**, readthedocs re-sync — just needs a merge if CI is green).

`docs/paper/` is still **0 tracked files**. Do not `git add -f` it.

## ⚠️ The rule that keeps getting broken

**Do not trust document consensus. Go to the raw records or the canonical grader.**

Three separate audits this session "corrected" the flagship `scav_rat` count to 26/50 because
a dozen documents agreed. All three were wrong. `scripts/grade_recovery.py` settled it in one
run. A fourth agent then fabricated a Kriest 2017 quotation that does not exist in the paper.

Canonical, `verify_run` gate exit 0 on `n50e2k_percell_trio` (n=50, 2000 ep):

```
alpfe 49/50 · scav_rat 25/50 · diatomgraz 3/50 · R_PICPOC 50/50
trio 25/50 per-AOI (equals scav_rat — its sole binding leg) vs 0/50 global-scalar
epoch-matched anchor-off = 6/50 (n50e2k_anchor_off, 2000 ep). 4/50 is the 1500-ep run.
26/50 belongs to the separate subW=1 arm, NOT the flagship.
```

`tests/test_canonical_numbers.py` now guards these mechanically. It has already stopped drift
before it entered the repo twice. If it fires, check the data before editing the doc.

## PENDING YOUR APPROVAL — `docs/paper/main.tex`

Nothing below is applied. Every `main.tex` core-claim edit needs an explicit yes, shown as exact
old→new diffs, one at a time. That has been the working rhythm throughout.

**Deep research reordered the priorities.** Do these before the originally-queued Groups C/D:

1. **Drop the Wilson interval on the 0/50 global-scalar arm.** Verified from raw records: the
   50 seeds give 50 *distinct* values, but `scav_rat` converges to 3.55219e-07 with sd 2.03e-10
   against Carroll's 6.025e-07 — about **1200σ**. The arm fails deterministically, not by
   chance. A binomial CI models variability that is not there, and [0.00, 0.07] implies a true
   rate up to 7%. Replacing it with the deterministic statement plus the σ distance is a
   *stronger* claim.
2. **`rel_span` is not a calibrated threshold.** The profile grid is built from `PARAM_BOUNDS`
   (`scripts/identifiability_sloppiness.py:423-424`), so widening a physical prior mechanically
   flips FLAT→CURVED with no new data. Also: Carroll's target sits at log-position **0.98** of
   the `alpfe` box and **0.94** of `diatomgraz`, so those profiles are one-sided and Raue's
   two-sided criterion cannot be evaluated as implemented. This is the mechanism for the
   standing puzzle that `alpfe` reads FLAT yet recovers 9–10/10.
3. **Fig. 4(a) caption/text** — the figure itself is fixed (`figs/make_figs.py` now plots only
   the three measured step counts and shows ALK not collapsing). Paper compiles at 34 pages,
   0 undefined citations. Worth re-reading the surrounding prose for consistency.
4. **Groups C and D** (from the earlier package): 8 sites mixing n=10 and n=50 denominators,
   5 `diatomgraz` sites needing the model-internal upgrade you approved.
5. **Diff 7** — the anchors-only decomposition paragraph (alpfe 50/50 and R_PICPOC 28/50 are
   anchor-driven; `scav_rat` 0/50 per-AOI is pattern-driven; its 40/50 cell-weighted is a
   Southern Ocean straddle that must never be quoted as recovery).

Two blockers are also **unforced errors**, per the sweep: a fabricated quotation (already
caught, never entered the paper) and a statistic that was never defined (`rel_span`).

## Emulator — fixed, and the deflation still stands

The log-space bug was real. AICR job 204877 re-ran the identical global config with
`--log-transform`:

| tracer | log-range kept | non-physical output |
|---|---|---|
| Chl1 | 0.359 → **0.891** | 30.41% → **0.00%** |
| PIC | 0.425 → **0.906** | 19.08% → **0.00%** |
| POC | 0.348 → **0.882** | 9.38% → **0.00%** |
| FeT | 0.882 → 0.940 | 7.27% → **0.00%** |

The oligotrophic gyres are reproduced; fit slope 0.23 → 0.81. **Skill is unchanged** — 0.813 →
0.803 of ocean beating persistence, still −0.161 ± 0.013 vs seasonal AR(1). The fix bought
physical validity, not skill. Horizon is still one step.

**Every global emulator figure predating 2026-07-25 is contaminated.** Regenerate before showing.

## Running elsewhere

A background worktree session is fixing the **25 remaining `torch.load(weights_only=False)`**
calls (Greptile P1, security). Two were fixed in #195; the rest are data-gated and need
per-file checking. Do not blanket-replace.

## Figures

Five variants exist in `docs/figures/tikz/`, all overlap-free, built on `darwindiff-tikz-v2.sty`.
That palette replaced v1 because v1's header *claimed* greyscale safety it did not have —
Okabe-Ito's blue and orange sit at a greyscale contrast ratio of **1.02**. Tol high-contrast
measures **4.52:1**, verified by converting the render and sampling it.

The **basin matrix** is the one that earns its place: it shows the finding rather than asserting
it — `scav_rat` 49/50 in the Southern Ocean vs 7/50 at the equator, `diatomgraz` inverting that,
which is *why* its two-basin count collapses to 3/50.

The tikz *skill* is deliberately gitignored: it kills unverified PIDs and its documented command
points at a contributor's home directory.
