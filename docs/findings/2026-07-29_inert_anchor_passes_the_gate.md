# A run declared the calcite anchor ON, ran without it, and passed `verify_run.py` at exit 0

**Date:** 2026-07-29 · **Fix:** inert-term check in `scripts/verify_run.py` ·
**Found by:** trying to reproduce the flagship locally and getting the wrong `R_PICPOC`

## What happened

A holdout run was launched with the flagship recipe from
`2026-07-24_reproducibility_methods_appendix.md`, including `DANIELS_RPICPOC_W=1` — the real
calcite anchor that the whole `R_PICPOC` result rests on. The PANGAEA compilation was not staged in
this worktree, so the runner printed

```
[warn] DANIELS_RPICPOC_W=1.0 but Daniels load failed (... not found ...); loss term will be skipped
[warn] DANIELS_RPICPOC_W=1.0 but no Daniels coverage in AOI; loss term will be skipped
```

and trained anyway. The run JSON recorded `"daniels_rpicpoc_w": 1.0`.

**`scripts/verify_run.py` returned exit 0, `[VERIFIED] (10/10 seeds)`.**

The result it verified:

| | this run | genuine flagship (`n50`) |
|---|---|---|
| `alpfe` per-AOI | 10/10 | 49/50 |
| `scav_rat` per-AOI | **0/10** | 25/50 |
| `R_PICPOC` per-AOI | **0/10** | 50/50 |
| `R_PICPOC` median / Carroll | **0.20–0.26×** | 1.17–1.25× |

0.20–0.26× Carroll is the anchor-off signature. The gate said VERIFIED because nothing compared the
*declared* weight against the *realised* cell count.

## The evidence was already in the artifact

The run JSON carried it the whole time:

```json
"daniels_rpicpoc_w": 1.0,
"n_daniels_cells_per_aoi": {"eqpac": 0, "natlsubpolar": 0, "southernoceanpac": 0}
```

Nothing was corrupt. The gate simply never read the two keys together. That is the same defect
class as the canonical-number guards: **a fact correct in one place and unused in another.**

## The fix

`verify_run.py` gains `inert_terms()`, checking nine weight/cell-count pairs. A weight `> 0` whose
cell count is zero in **every** AOI is now a `DISCREPANCY` (exit 2), not a silent pass. The check is
one-directional on purpose — a zero weight with a nonzero cell count is normal, because counts are
computed whether or not the term is used.

Verified against real runs, exit codes captured directly (never through a pipe):

| run | before | after |
|---|---|---|
| the anchor-skipped run | exit 0 ✗ | **exit 2** ✓ |
| `n50` (flagship, n=50) | exit 0 | **exit 0** ✓ |
| `ep4k` (4000 ep, n=50) | exit 0 | **exit 0** ✓ |

No false positives on the two genuine flagship ensembles.

## A second thing this turned up: the Southern Ocean has no calcite anchor

Reading `n_daniels_cells_per_aoi` on the **genuine** flagship runs:

```
ep4k: {"eqpac": 34, "natlsubpolar": 26, "southernoceanpac": 0}
n50:  {"eqpac": 34, "natlsubpolar": 26, "southernoceanpac": 0}
```

**`southernoceanpac` gets zero Daniels cells in the flagship itself.** Yet its `R_PICPOC` recovers —
median 0.04946 (1.165× Carroll), with 64% of the 50 seeds inside the ±25% Cal+ band, against
eqpac 50% and natl 74%.

So "`R_PICPOC` recovers given a real calcite anchor" is **AOI-specific**: eqpac and natl have real
Daniels observations, the Southern Ocean has none. Whatever pins `R_PICPOC` there is not the real
anchor.

The obvious follow-up reading — that the Southern Ocean is therefore constrained by the
model-internal PIC/POC pattern block instead — **is not supported by what is in hand**, because in
the anchor-skipped run above the Southern Ocean collapsed to 0.26× Carroll along with the other two.
That run is not a clean control (it also carried a 20% GEOTRACES holdout), so it cannot settle the
question either way.

**Clean test, not yet run:** the epoch-matched anchor-off control `n50e2k_anchor_off` already exists
and gives `R_PICPOC` 6/50. Grade its **per-AOI** legs. If the Southern Ocean leg drops with the
others, its recovery is inherited from the anchored AOIs and the per-AOI ≥2-of-3 metric is counting
an unanchored leg. If it holds up, the Southern Ocean is genuinely pattern-constrained and the
anchor claim needs narrowing to the two AOIs that have data.

Either answer changes how the `R_PICPOC` result should be stated, so it is worth the one grading
pass it costs.

## Practical note

`data/` is gitignored, so a fresh worktree has **no** staged observational data and every real
anchor degrades to a warning. The remediation command is printed by the runner itself:

```bash
curl -sL "https://doi.pangaea.de/10.1594/PANGAEA.888182?format=textfile" -o "data/daniels/Daniels_etal_2018_PANGAEA_888182.tab"
```
