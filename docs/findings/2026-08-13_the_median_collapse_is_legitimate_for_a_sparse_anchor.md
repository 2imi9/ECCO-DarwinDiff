# The median collapse is legitimate for a sparse anchor — the 43/50 is a measurement, not an artifact

**Date:** 2026-08-13 · **Cost: ZERO compute** — re-analysis of job 354596 artifacts ·
**Script:** `scripts/analysis/is_the_median_collapse_legitimate.py`

## The gate this closes

The Marsh Southern Ocean anchor (12 of 1,296 cells, 0.9%) returned `R_PICPOC` **43/50 under the
median collapse, 6/50 geometric, 0/50 arithmetic**. The finding
([…_anchorable_but_only_under_the_median.md](2026-08-12_the_southern_ocean_rpicpoc_leg_is_anchorable_but_only_under_the_median.md))
recorded the verdict as AMBIGUOUS and stated that the median number **must not be quoted** until we
knew whether it was a measurement or a collapse artifact. `pooler_audit.py` exists because the
arithmetic collapse was once caught *manufacturing* `scav_rat` recovery; the same scepticism has to
be applied to a collapse that flatters us.

## The failure mode being tested

With a sparse anchor the per-cell field splits into two populations: ~12 **anchored** cells pulled
toward the observation, and ~1,284 **unanchored** cells sitting wherever the network's prior puts
them. A median reports the *majority* population. So if the median were tracking the unanchored
majority, 43/50 would say nothing about calcite — only that the untrained prior happens to land
inside the ±40% band. That is exactly the `diatomgraz` trap (prior midpoint at rel 0.3675, inside
the band, so an untrained net scores 50/50 by construction).

**The untrained null arm *is* the unanchored population** — same architecture, at initialisation,
never trained. So the test needs no new run.

## Result

Median over 50 seeds of the per-AOI recovered `R_PICPOC`, by collapse:

| arm | arithmetic | geometric | median |
|---|---|---|---|
| **anchored (Marsh)** | 0.07141 (1.68×) | 0.06260 (1.48×) | **0.05483 (1.29×)** |
| unanchored (trained) | 0.74472 (17.5×) | 0.73907 (17.4×) | 0.74397 (17.5×) |
| untrained null | 0.72961 (17.2×) | 0.72914 (17.2×) | 0.73178 (17.2×) |

**The anchor moves the estimate by a factor of ~13, under all three collapses**
(|Δ ln| = 2.32 arithmetic, 2.46 geometric, 2.59 median), and every one moves *toward* Carroll. The
median is **not** reporting the prior: the prior sits at 17.2× Carroll and the anchored median sits
at 1.29×.

**So 43/50 is a measurement.** Only the median lands inside the ±40% band (rel 0.292 vs 0.475 and
0.682), which is why the count is pooler-dependent — but the underlying movement is present in all
three.

## Why the median is the *right* collapse here, not merely the flattering one

The decisive evidence is external to the fit. The runner reports the **observed** Marsh Southern
Ocean rain ratio as **geomean 0.0489** over 12 cells / 42 samples. Ranking the three collapses by
distance to that observation:

| collapse | recovered | distance from the observed 0.0489 |
|---|---|---|
| **median** | 0.05483 | **+12%** |
| geometric | 0.06260 | +28% |
| arithmetic | 0.07141 | +46% |

**The median recovers the quantity the anchor is actually fitting to more accurately than the other
two.** That is a validation against an independent target, not a preference.

The mechanism is ordinary and predictable: the per-cell field is right-skewed
(`per_aoi_log_sd` = 0.469), so arithmetic > geometric > median by construction, and the median is
the robust centre that tracks the bulk while the arithmetic mean is dragged by a high tail. A sparse
anchor *creates* that skew — which is the same mechanism recorded in the parent finding as
`R_PICPOC` losing its pooler invariance (log-sd 0.105 → 0.459).

## Honest status of this conclusion

**This is a post-hoc resolution of a pre-registration ambiguity, and must be labelled as such.**
The `som` pre-registration named a decision rule but did not name a primary pooler for `R_PICPOC`;
that was a flaw in my design. This analysis resolves which pooler to believe on principled grounds
(a 13× move off the prior, plus closest agreement with the observed value), but it was chosen
*after* seeing the counts. It is evidence about the metric, not a pre-registered result.

The defensible statement is therefore: *the anchored arm's `R_PICPOC` moved an order of magnitude
off its untrained prior toward both Carroll and the local observation, under every collapse; the
median collapse tracks the observed local value best; and the 43/50 count is consequently a
measurement rather than an artifact of where the prior sits.*

**Still not licensed:** this remains one basin, a 0.9%-coverage anchor, and a `scav_rat` cost of
30/50 → 16/50 arithmetic. It does not change any published number, all of which use Daniels and the
3-AOI configuration.

## Consequence

`ind330` ("the SO leg is inherited") should be reworded. The leg is not inherited when a local
anchor exists — it carries an order of magnitude of real local information. What was true is that
**Daniels supplied no such anchor**, so with Daniels the leg had nothing to be local about.
