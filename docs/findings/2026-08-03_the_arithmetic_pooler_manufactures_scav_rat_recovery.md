# The arithmetic pooler manufactures `scav_rat` recovery — any intervention that adds per-cell dispersion will "work"

**Date:** 2026-08-03 · **Evidence:** jobs 258439 + 258694, five widths, n=100 each
· **Found by:** a 5-lens adversarial verification workflow, mechanism lens, after the claim it
attacked had already been written up twice
· **Status: this RETRACTS `2026-08-03_capacity_is_the_scav_rat_lever.md` and explains it.**

## The retraction

Width 16 → 39 appeared to lift `scav_rat` from 45/100 to 77/100 (Fisher P = 5.6e-06), with both
seed halves agreeing, nulls of 0/50 at both widths, controls apparently undamaged, and exactly
one of 71 recorded config keys differing. It survived a split-half test and a band-sensitivity
test that between them had already killed two other claims the same day.

**It does not survive changing the pooler.** Every artifact records three collapses of the *same*
per-cell fit — arithmetic mean, geometric mean, and field median:

| pooler | width 16 | width 39 | Fisher P |
|---|---|---|---|
| **arithmetic** (what is reported) | 45/100 | **77/100** | **5.6e-06** |
| geometric | 16/100 | 17/100 | **1.000** |
| median | 37/100 | **27/100** | 0.172 *(reverses)* |

**The effect exists only under the arithmetic mean.** Under the geometric mean it is exactly
absent; under the median it points the other way.

## The mechanism, which is arithmetic rather than scientific

Per-cell log-dispersion of the recovered `scav_rat` field, median over seeds:

| width | 8 | 16 | 24 | 39 | 80 |
|---|---|---|---|---|---|
| natl `log_sd` | 0.879 | 0.933 | 0.971 | 0.976 | **1.001** |

Dispersion rises monotonically with width. For a log-normal field,

    arithmetic mean = geometric mean x exp(sigma^2 / 2)

so the arithmetic collapse inflates with `sigma` **at fixed geometric centre**. The North Atlantic
`scav_rat` estimate sits *below* Carroll, so inflating it moves it *toward* Carroll. A wider
network produces a noisier per-cell field, and the reported statistic converts that noise into
apparent accuracy.

The dose-response reads the same way once the pooler is varied:

| width | 8 | 16 | 24 | 39 | 80 |
|---|---|---|---|---|---|
| arithmetic count | 13 | 45 | 70 | 77 | **88** |
| geometric count | 8 | 16 | 20 | 17 | 26 |
| median count | 25 | **37** | **37** | 27 | 25 |

The arithmetic column climbs monotonically with width. The geometric column is flat. The median
column **peaks at width 16–24 and declines** — which agrees with every other diagnostic in this
session (Southern Ocean accuracy, `alpfe`'s eqpac leg, `diatomgraz`'s eqpac leg all degrade as
width grows).

## The general statement, which outlives this experiment

> **Any intervention that increases per-cell dispersion in the `scav_rat` field will raise its
> arithmetic per-AOI count without improving the fit.**

That is a standing confound on the project's reported metric, not a property of trunk width.
Width is simply the first lever tested that happens to increase dispersion. It predicts that
other "successes" on this metric should be re-checked, and it retro-explains `ind352`, already
in the research map: *"`scav_rat`'s collapse statistic is sensitive to the aggregation: 26/50
arithmetic versus 13/50 geometric."* That row recorded the symptom; this is the cause.

**`scav_rat` is a log-scale parameter spanning two decades** (`bounds` 3e-8 to 3e-6,
`Param.scale == "log"` in the registry). Collapsing a log-scale quantity with an arithmetic mean
is the wrong operation on its own terms, independent of everything above.

## What this does and does not touch

- **Retracts** the capacity/width recommendation entirely. Width 39 is not adopted, and the
  reason is now stronger than "it trades basins": the headline gain was never an accuracy gain.
- **Does not touch `alpfe` or `R_PICPOC`.** Both are near-unity-scale linear parameters at
  ceiling (98–100/100) across every band and both were flat under the width sweep.
- **Does not touch the `diatomgraz` eqpac result**, which was measured per-leg at tight bands
  (40/100 at ≤0.10 vs 0/50 untrained) rather than through a majority count, and which *degrades*
  with width — the opposite direction to the artifact.
- **Casts doubt on any `scav_rat` comparison ever reported on the arithmetic per-AOI count**,
  including the flagship's own 25/50, whose geometric counterpart is already recorded as 13/50.

## Required practice, added to the two adopted earlier today

1. **Report `scav_rat` under all three poolers, or under the geometric one alone.** A result that
   appears only under the arithmetic mean is a dispersion effect until proven otherwise.
2. **Report `per_aoi_log_sd` alongside any `scav_rat` count.** It is already in every artifact and
   nothing has ever read it.
3. Split-half and band-sensitivity remain necessary and are **not sufficient** — this claim passed
   both.

## Credit, and the lesson about the checks

This was found by an adversarial verification pass run *after* the finding had been written up,
revised once, and committed. The two house checks adopted earlier the same day both passed. The
objection came from asking a different question — *what else in the pipeline could produce this
number* — rather than from testing the claim harder on its own terms.
