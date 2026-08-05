> # CORRECTED 2026-08-04 — the retraction stands, the GENERALISATION does not
>
> The width retraction below is **upheld in full**, and so is the mechanism. What is too strong is
> the general statement in §"The general statement, which outlives this experiment":
>
> > *"Any intervention that increases per-cell dispersion in the `scav_rat` field will raise its
> > arithmetic per-AOI count without improving the fit."*
>
> **That holds only where the geometric centre lies BELOW the ±40% band.** The arithmetic collapse
> multiplies by `exp(σ²/2)`; below the band that inflation manufactures passes, but *inside* it the
> same inflation carries the estimate out the top and **destroys** them. The counter-example is the
> single-AOI Southern Ocean — the one basin where `scav_rat` is established — where the geometric
> centre is 0.73× Carroll and `scav_rat` reads **30/50 arithmetic but 49/50 geometric**.
>
> Two further corrections: `per_aoi_log_sd` is **not** "already in every artifact" (it exists only
> from 2026-07-29, in 92 of 211 run dirs), and the claim that this "casts doubt on" the flagship's
> 25/50 is now settled rather than suspected — the trio is **12/50 geometric**.
>
> Superseded in part by `docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md`.
> Kept unedited below; the width result and the mechanism are correct as written.

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

## Three further objections from the same pass, all upheld

**1. The split-half was not a replication, and the check as I wrote it was wrong.** All 100 seeds
per arm were one simultaneously-submitted array (258439, tasks starting 15:57–16:01; tasks 4 and
5, i.e. seeds 40–49 and 50–59, launched in the same instant). A permutation test over 10,000
random re-splits of that same n=100 gives **P(both halves reach Fisher P < 0.05) = 0.9256**. So
"both halves significant" was expected 93% of the time by construction.

The distinction that matters: the per-parameter effect died on a split-half because seeds 50–99
were run in a **later, separate job** (258256 extending 257056). That was a genuine out-of-sample
replication. Splitting one array is not. CLAUDE.md is corrected accordingly.

The real replication for width 39 exists and was not cited: `pp_ctrl39` is the identical config in
a different job and gives **72/100** against `cap39`'s 77/100. Consistent — but it replicates the
*arithmetic* number, which the pooler analysis shows is the artifact.

**2. The ≥2-of-3 rule is close to degenerate for `scav_rat`.** `southernoceanpac` passes 99–100/100
in every arm — a free vote — and there is **not one seed** in either arm where natl passes and the
parameter fails. So the rule collapses to **≥1-of-{eqpac, natl}**, and eqpac fires at an identical
12/100 in both arms on largely *different* seeds (overlap 2 of 12, i.e. seed noise). The headline
is a one-basin test wearing a three-basin label.

**3. `diatomgraz`'s Excellent band is wiped out by width**, 20/100 → 0/100, P = 6.6e-07, in both
halves. That is the same signal reported here as locally identifiable in eqpac, and it confirms
from a second direction that widening destroys it.

Two smaller ones, recorded: Fisher is technically the wrong test (the arms are seed-matched and
therefore paired — McNemar is correct, though it does not change the verdict), and `Smallgrow`
degrades 13/100 → 5/100 under width 39 with the same sign in both halves.

## Credit, and the lesson about the checks

This was found by an adversarial verification pass run *after* the finding had been written up,
revised once, and committed. The two house checks adopted earlier the same day both passed. The
objection came from asking a different question — *what else in the pipeline could produce this
number* — rather than from testing the claim harder on its own terms.
