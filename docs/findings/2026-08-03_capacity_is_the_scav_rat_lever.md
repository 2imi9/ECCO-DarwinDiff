# Trunk width moves `scav_rat` — but the headline count is a band-edge amplifier, and the underlying accuracy change is small and mixed in sign

**Date:** 2026-08-03 · **Job:** 258439 · **All four arms `verify_run` exit 0**
· **Status: the count result is real and replicates; the SIZE of it is an artifact of where the
pass band sits. Do not adopt width 39 on this evidence.**

## The result as first measured

One array, one submission, seeds 0–99, each arm with its own untrained null. The arms differ on
**exactly one of 71 recorded config keys** (`dinn_hidden_dim`, 16 vs 39); all 30 tasks logged the
same runner and config md5.

```
                     scav_rat    eqpac    natl    sopac     untrained scav_rat
cap16 (width 16)      45/100       12      35       99            0/50
cap39 (width 39)      77/100       12      74      100            0/50

Fisher exact two-sided P = 5.6e-06
  seeds 0-49  :  37/50 vs 20/50    P = 1.1e-03
  seeds 50-99 :  40/50 vs 25/50    P = 3.1e-03
```

Both halves clear 0.01 independently — the test that killed the per-parameter trunk effect the
same day. Controls undamaged: `alpfe` 98/100 both, `R_PICPOC` 99 vs 100/100. Null 0/50 at both
widths, so this is not the "bigger nets score higher untrained" artifact.

**On those numbers alone the conclusion would be "capacity is the lever."** It is not, and the
reason is worth more than the result.

## The count is measured at the one band where the effect exists

Recounting the identical artifacts with only the pass threshold moved:

| pass band | cap16 | cap39 | difference |
|---|---|---|---|
| ≤ 0.30 | 13/100 | 13/100 | **+0** |
| ≤ 0.35 | 22/100 | 31/100 | +9 |
| **≤ 0.40 (reported)** | **45/100** | **77/100** | **+32** |
| ≤ 0.45 | 81/100 | 100/100 | +19 |
| ≤ 0.50 | 99/100 | 100/100 | +1 |
| ≤ 0.60 | 100/100 | 100/100 | **+0** |

The effect is **maximal exactly at the reported band** and disappears on both sides of it. At the
Excellent band (≤ 5%) it is **0/100 vs 0/100** — neither width recovers `scav_rat` to 5% anywhere
outside the Southern Ocean.

## Why: the North Atlantic distribution sits on the threshold

| natl leg | median rel error | IQR | ≤ 0.40 | in [0.30, 0.50] |
|---|---|---|---|---|
| cap16 | 0.413 | [0.388, 0.450] | 35/100 | **91/100** |
| cap39 | 0.384 | [0.344, 0.401] | 74/100 | **88/100** |

Nine tenths of the North Atlantic mass lies within ±0.10 of the pass threshold, with cap16's
median just *outside* 0.40 and cap39's just *inside*. So the genuine accuracy change —
**0.413 → 0.384, about 7% relative** — flips 39 seeds across the line and doubles the headline.

**The improvement is real. The factor-of-1.7 in the count is not a measure of its size.**

## And the Southern Ocean gets worse

| sopac leg | median rel error |
|---|---|
| cap16 | **0.051** |
| cap39 | **0.083** |

Width 39 degrades Southern Ocean accuracy by ~63% in relative error. The count does not show it
because both medians sit far inside a 40% band — 99/100 and 100/100. So the per-AOI count is
simultaneously **hypersensitive** where a distribution straddles the threshold and **blind** where
it does not.

The cell-weighted metric, which this project correctly refuses to headline, independently shows no
gain at all: `scav_rat` **71/100 → 67/100**. Both metrics being wrong in different directions is
the signature of a threshold problem, not of a capacity discovery.

## What is actually established

1. **Width 16 → 39 improves North Atlantic `scav_rat` accuracy modestly** (median relative error
   0.413 → 0.384) and **degrades Southern Ocean accuracy** (0.051 → 0.083).
2. **eqpac is unmoved: 12/100 at both widths**, median 0.678 → 0.617. With job 258256's 11/100 in
   both arms, that is four arms across two jobs. It has now resisted capacity, epochs, information
   weighting, representation sharing and adequacy masking, at Fisher rank 4/4.
3. **Nothing recovers `scav_rat` to 5% outside the Southern Ocean**, at either width.

## The methodological consequence, which is larger than the result

**The per-AOI ≥2-of-3 count at a 40% band is an amplifier when a basin's error distribution sits
on the threshold.** A 7% accuracy change became a 71% count change here. Every effect this project
has reported on this metric should be re-checked by moving the band and confirming the effect does
not peak at 0.40 — the check is free, it runs on artifacts already on disk, and it took one query
to overturn this document's own first draft.

That check is now the second house standard alongside the split-half. This result passed the
split-half convincingly and still needed amending, so the two tests are not redundant.

## Do not do this yet

- **Do not adopt width 39.** It trades a small North Atlantic gain for a real Southern Ocean loss
  and looks decisive only on a threshold metric evaluated at one threshold.
- **Do not restate the flagship tuple at width 39.**
- **Open, and now the priority:** is the flagship's own published 25/50 band-edge sensitive in the
  same way? The same one-query check answers it, and it bears on the manuscript.

Jobs **258694** (widths 8/24/80) and **258713** (width × epochs 2×2) were launched before this
analysis and are still the right experiments — but they must be graded with the band-sensitivity
sweep alongside the count, not on the count alone.
