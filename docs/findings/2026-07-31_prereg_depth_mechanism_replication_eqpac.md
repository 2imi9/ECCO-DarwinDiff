# Pre-registration: does the depth mechanism for `scav_rat` replicate outside the Southern Ocean?

**Date:** 2026-07-31 · **Written with zero eqpac ablation JSONs on disk** · **Status:** pending

`2026-07-31_scavrat_southern_ocean_signal_is_depth.md` established, in one basin, that `scav_rat`
is identified by the **vertical structure** of dissolved iron and not by its surface concentration:
`so_sub` 33/50 against `so_surf` 14/50, Fisher exact P = 2.68e-4, with `alpfe` at 49/50 in the
surface arm so the failure is the observation and not the fit.

One basin is one basin. This pre-registers the replication.

## First: the follow-up that finding proposed does not work, and here is why

That document closes by proposing a cross-basin test: *"any AOI with subsurface iron coverage
should show some recovery, and the ranking across basins should track subsurface bin count rather
than surface."*

**That test is not identifiable.** Measured coverage
(`scripts/analysis/geotraces_depth_coverage.py`, GEOTRACES IDP2025, QC(49,50), 1-degree bins,
pre-mask):

| AOI | surface bins | subsurface bins | surface obs | subsurface obs |
|---|---|---|---|---|
| `npac` | 29 | 31 | 212 | 518 |
| `eqpac` | 25 | 27 | 52 | 297 |
| `midatl` | 22 | 23 | 52 | 282 |
| `southernoceanpac` | 14 | 16 | 40 | 157 |
| `natlsubpolar` | 13 | 13 | 31 | 115 |
| `npsg` | 12 | 13 | 28 | 122 |

**Pearson r(surface, subsurface) = 0.996, Spearman rho = 0.986.** Every basin with subsurface iron
has almost exactly as much surface iron, because they come from the same bottles on the same
cruises. Ranking basins by subsurface count and by surface count gives the **same ordering**, so
a correlation between recovery and subsurface coverage is equally a correlation with surface
coverage. The proposed test cannot separate the two hypotheses it was designed to separate.

This is recorded rather than quietly dropped: a plan that reads as a valid follow-up but cannot
discriminate is the kind of thing that gets run, produces a number, and is over-read.

**What does work is the design that already worked**: the within-AOI ablation. Inside one basin,
coverage is held fixed and only the channel is switched, so the comparison is not confounded by how
much data each arm sees. Repeat it in a second basin.

## The basin, and why this is a risky test

`eqpac`. It has the most subsurface iron of the canonical trio (27 bins pre-mask, against
`southernoceanpac`'s 16), it is a long-standing AOI with prior work on every other parameter, and
its target cache is already built.

It is also the basin where **`scav_rat` historically fails**: the flagship `n50e2k_percell_trio`
per-AOI legs are eqpac **7/50**, natl 20/50, sopac 49/50. So the mechanism makes an uncomfortable
prediction. If depth is what identifies `scav_rat`, then subsurface-only iron in the basin with the
*most* subsurface iron should recover it, in the same basin where the joint fit recovers it worst.

That is a prediction that can visibly fail, which is the point.

## Arms

Single AOI `eqpac`, 50 seeds, 2000 epochs, everything byte-identical except the two iron weights.
Mirrors the Southern Ocean arms exactly: `fet_w=1.0, pinn_w=0.0, poc_sub_w=0.0, darwin_ic=False`,
MLD channel on, AOI-ID off, gating off, per-AOI weight 2.0.

| arm | `GEOTRACES_W` | `GEOTRACES_SUB_W` | live iron observation |
|---|---|---|---|
| `eq_both` | 1.0 | 1.0 | surface + subsurface (the parent) |
| `eq_surf` | 1.0 | 0.0 | surface only |
| `eq_sub` | 0.0 | 1.0 | subsurface only |
| `prior_eq_abl` | 1.0 | 1.0 | untrained null, `NB23_LR=0` |

## The decision rule, fixed now

Primary comparison is **`eq_sub` against `eq_surf`** on `scav_rat`, per-AOI Cal-grade, n=50 each,
graded by `scripts/grade_recovery.py` and gated on `scripts/verify_run.py` exit 0.

- **REPLICATES** if `eq_sub` is above its untrained null at P < 0.01 **and** `eq_sub` > `eq_surf`
  by Fisher exact two-sided P < 0.05, in the same direction as the Southern Ocean.
- **FAILS TO REPLICATE** if `eq_sub` is not above its null, or if the surface arm is the better one.
- **INCONCLUSIVE** if `eq_sub` clears its null but the two arms are not separable. This is a real
  outcome and it is not to be written up as a replication.

**Falsifier for "the run is broken rather than the hypothesis":** `alpfe` must recover in `eq_surf`.
In the Southern Ocean the surface arm hit `alpfe` 49/50, which is what showed that the arm could fit
at all. If `alpfe` fails in `eq_surf` too, the arm is broken and no conclusion about `scav_rat` may
be drawn from it.

## Interpretations, committed in advance

Writing these now so the result cannot be fitted to whichever story is convenient afterwards.

- **`eq_sub` recovers.** The depth mechanism generalises beyond the Southern Ocean. `scav_rat` is
  identified by vertical iron structure wherever that structure is observed, and the flagship's
  eqpac 7/50 is a **weighting and channel-mixing artifact**, not a property of the basin.
- **`eq_sub` fails while `so_sub` succeeded.** Depth is necessary but not sufficient. The Southern
  Ocean also has the strongest scavenging sink, so the honest claim narrows to *depth structure
  plus a strong sink*, and the single-basin result stops being a general mechanism. This would also
  predict that the eqpac leg cannot be rescued by re-weighting, which is separately checkable.
- **Both arms recover.** The surface/subsurface distinction is not load-bearing where coverage is
  this dense (27 subsurface bins against the Southern Ocean's 14), and the Southern Ocean result is
  partly a low-coverage phenomenon.

## Recorded before the fact

- **Provenance.** The AICR checkout was found **reverted to an older build** (runner md5
  `c6622e10`, missing `PerCellFreeField`, `safe_torch_load`, and the `co2_flux_darwin` rename)
  even though the Southern Ocean arms had run against `3d5ebe67`. It was backed up to
  `/scratch/qi_zim_neu/emulator_poc_backup_20260731.tgz` and re-synced to `3d5ebe67`, which is
  local HEAD line-ending-normalised and **bit-identical to the build the Southern Ocean arms ran**.
  Verified by `md5sum` on the cluster. This is issue #218 observed a second time.
- **Time limit raised to 2 hours per array task.** The Southern Ocean run lost `so_repro` to a
  one-hour timeout at ~1491 s per 10 seeds; 2 hours removes that failure mode.
- **Coverage numbers above are approximate in both directions, not upper bounds.** Written first as
  "upper bounds" on the reasoning that a mask can only remove bins. The smoke test falsified that
  within the hour: the runner reports eqpac **surface 26, subsurface 28** where the table says
  25/27, because the runner also lays its grid on the model's edges rather than the AOI corner,
  which can move a sample across a boundary and *add* a bin. Southern Ocean goes the other way
  (table 14/16, runner 13/14). The check is now a two-sided tolerance and both anchors are pinned
  in the script. Nothing about the collinearity argument changes: eqpac masked is 26 surface to 28
  subsurface, still ~1:1.
- **The masked eqpac counts are the ones to quote**: surface 26, subsurface 28, against
  southernoceanpac's 13 and 14. The replication basin has **twice** the subsurface coverage of the
  original, which is what makes a null result there informative rather than ambiguous.
- **No count from a short arm will be graded as complete.** Any arm finishing under 50/50 is
  refilled or disclosed, per the standing rule.
