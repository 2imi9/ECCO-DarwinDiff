# The daily era conflict was a convention clash, and the staging is not as complete as recorded

**Date:** 2026-07-30 · **Method:** read the `.meta` sidecars in the staged tree, count files ·
**Verdict: both era statements were right about different things. Separately, the daily staging has
the same intersection pathology as the monthly mirror, and the earlier completeness check could not
have caught it.**

## 1. The one-day era conflict, resolved

Two statements were in conflict in the archived transcript. The manifest enumeration said the daily
era ends **2018-12-31**. A HEAD probe of iter 710064 returned HTTP 500 for both `surfChl1` and
`SST`, implying **2018-12-30**.

The `.meta` sidecar of the last staged file settles it, and neither statement was wrong.

`/scratch/qi_zim_neu/daily_v5/surfChl1/surfChl1.0000709992.meta`:

```
 timeStepNumber = [     709992 ];
 timeInterval = [  8.519040000000E+08  8.519904000000E+08 ];
```

Those bounds are 9860.0 and 9861.0 days after the epoch. So the last record is a **24-hour average
over 2018-12-30**, stamped with its **end** iteration, whose instant is 2018-12-31 00:00.

| statement | what it describes | correct? |
|---|---|---|
| era ends 2018-12-31 | the terminal file stamp / interval end instant | yes |
| era ends 2018-12-30 | the last day of data actually averaged | yes |

The HTTP 500 at iter 710064 was also correct: that file would have carried the 2018-12-31 average
and it does not exist.

**Use this wording.** The daily archive provides daily means for **1992-01-01 through 2018-12-30**,
in files stamped by their interval-end iteration 72 through 709992. Any pre-registered test keyed
to the daily era should state the averaging window, not the stamp, because the stamp is off by one
day from the data.

### A second, free confirmation of `delta_t`

`timeInterval / 1200 = [709920, 709992]`, the previous and current iteration exactly. The archive's
own metadata therefore gives `delta_t = 1200 s` independently of PR #186's arithmetic, physics and
structural arguments. The first record is consistent too: iter 72 has
`timeInterval = [1.2e+03, 8.64e+04]`, i.e. 1200 s to exactly one day, the partial first average.

## 2. The staging is short of the iteration grid, in a familiar shape

The predecessor recorded staging as "verified clean: 58,755 / 58,755 files, zero wrong-size". That
check compared downloaded files against the manifest it downloaded from. It could not detect files
absent from the grid, and some are.

Expected daily records from iter 144 to 709992 at stride 72: **9860**.

| variable | `.data` files | `.meta` files | missing vs 9860 |
|---|---|---|---|
| `surfChl1` | 9796 | 9801 | 64 |
| `SST` | 9794 | 9778 | 66 |
| `wspeed` | 9791 | 9808 | 69 |

Two separate problems are visible.

**Data and meta counts disagree per variable, in both directions.** `surfChl1` has 5 more `.meta`
than `.data` (iter 72 is a `.meta` with no `.data`), while `SST` has 16 more `.data` than `.meta`.
A sidecar-less data file still loads if the reader knows the shape, but a data-less sidecar is a
silent hole.

**The intersection is much worse than any single variable.** The built cube has **M = 9392** shared
steps. Each variable individually is missing about 0.7% of the grid, but they are missing
*different* days, so the 7-way intersection loses **468 of 9860, about 4.7%**.

That is the same mechanism as the monthly mirror's 158 of 324, at a different scale: per-variable
availability is high, the intersection is what collapses. It is worth recording that the pattern
recurred at daily cadence, because it means the cube-building convention, not the archive, is what
sets the usable record count in both cases.

### What it changes

For **Track 1**, nothing. Daily is closed on the n_eff argument (job 235995) and on the structural
circularity of the growth-pair route, and neither depends on the exact step count.

For **Track 2**, it is a bounded upside and not a large one. A union-style build could recover
roughly 4% more steps, against a cube that already has 9392. The pairs actually used are further
limited by adjacency: the re-score run reports 6246 train pairs and 2691 val pairs, so gaps are
already being handled correctly rather than silently bridged.

**Do not restate the "58,755 / 58,755, zero wrong-size" line as evidence of completeness.** It is
evidence that what was downloaded arrived intact, which is a different claim.
