# R_PICPOC's Southern Ocean leg is locally anchorable — but only under the median collapse, and it costs `scav_rat`

**Date:** 2026-08-12 · **Jobs:** 354596 (4 arms × 50 seeds) + 354597 (grading, chained `afterany`)
· **Gate:** `verify_run` **exit 0** on both trained arms, 50/50 seeds each
· **Verdict: AMBIGUOUS**, exactly as the pre-registration allowed for.

Pre-registered in [2026-08-12_prereg_so_marsh_anchor.md](2026-08-12_prereg_so_marsh_anchor.md)
before submission, with an amendment (also before any trained result was read) correcting the
two-nulls justification.

## The question

`ind330`/`ded177` call `R_PICPOC`'s Southern Ocean leg **inherited** through the shared DINN,
because the basin has zero Daniels cells. Marsh 2025 supplies **12 cells (42 observations)** there.
Single-AOI makes the test clean: with one basin there is nothing to inherit *from*, so any non-zero
`R_PICPOC` must come from the anchor.

## Primary result

`R_PICPOC` per-AOI count, anchored (Marsh, 12 cells) vs unanchored control, both n=50:

| pooler | anchored | control | Fisher vs control | vs own untrained null | pre-registered ≥15 |
|---|---|---|---|---|---|
| arithmetic | 0/50 | 0/50 | 1.000 | 1.00 | ✗ |
| geometric | 6/50 | 0/50 | **0.0267** | 0.0776 | ✗ |
| **median** | **43/50** | 0/50 | **5.2e-21** | **1.9e-45** | **✓** |

The rule required `≥15/50` **and** beating the control at P<0.01 **and** clearing its own null at
P<0.01. **Only the median collapse satisfies all three.** The rule did not name a primary pooler for
`R_PICPOC` — an ambiguity in my own pre-registration — so the committed reading applies:
*"AMBIGUOUS otherwise, and it will be reported as ambiguous rather than rounded to either."*

**It is not reported as a clean positive.** But "the Southern Ocean has no calcite information" is
now false under at least one legitimate collapse, which is more than `ind330` currently allows.

## The finding the pre-registration anticipated: R_PICPOC stops being pooler-invariant

The prereg said: *"R_PICPOC has been pooler-invariant everywhere measured (log_sd ≤ 0.21), so a
pooler-dependent R_PICPOC result here would itself be a finding."* It is:

| arm | R_PICPOC per-cell log-sd |
|---|---|
| unanchored control | **0.105** |
| anchored (Marsh) | **0.459** |

**Mechanism.** The anchor covers **12 of 1,296 ocean cells (0.9%)**. It pins `R_PICPOC` where there
are observations and leaves 1,284 cells unconstrained, so the recovered field becomes spatially
heterogeneous — and once per-cell spread is large, the collapse choice decides the answer. A sparse
local anchor buys local information at the price of the invariance that made `R_PICPOC` the
project's most robust parameter.

This is the first measured case of `R_PICPOC` behaving like `scav_rat` with respect to poolers, and
it is a direct consequence of anchor sparsity rather than of anything about calcite.

## The cost read, which fired

Pre-registered: *"`scav_rat` must not degrade in `som_anchor`. If adding a calcite anchor damages
it, that is a real cost and must be reported even though the experiment is 'about' R_PICPOC."*

| pooler | anchored | control | Fisher | |
|---|---|---|---|---|
| arithmetic | **16/50** | 30/50 | **0.0088** | **degraded, significant** |
| geometric | 46/50 | 50/50 | 0.1175 | degraded, not significant |
| median | 44/50 | 24/50 | 4e-05 | improved |

So the anchor **significantly damages `scav_rat`'s arithmetic leg in the one basin where `scav_rat`
is established**, while its primary (geometric) leg drops only slightly and non-significantly
(50→46). `diatomgraz` also degrades under the geometric collapse, 50/50 → 41/50 (P = 0.0026).

Adding a sparse local anchor is not free: it competes with the iron terms for the same fit.

## The void condition, and an incidental reproducibility result

The prereg built in a void condition: `som_noanchor` is configuration-identical to `so_rep`
(job 352450), and disagreement beyond seed noise would void the experiment.

**They are identical — 0 differing seeds.** The per-seed `k` vector matches element for element
across two separate submissions:

```
so_rep       [3,2,2,2,3,3,3,3,3,2,3,2,2,3,3,3,2,2,2,3, ... ,3,3,3,2,2,3]
som_noanchor [3,2,2,2,3,3,3,3,3,2,3,2,2,3,3,3,2,2,2,3, ... ,3,3,3,2,2,3]
```

with matching counts throughout (`alpfe` 50/50, `scav_rat` 30/50 arith and 50/50 geom,
`diatomgraz` 50/50, `R_PICPOC` 0/50). The void condition passes decisively.

**Worth recording separately for issue #226** ("runs are not bitwise reproducible and nothing ever
asked them to be"): two independent submissions, same config and seeds, different nodes, produced
**identical per-seed grades**. That is not a full bitwise-reproducibility claim — it is equality of
the graded outcome, not of every float — but it is the first time the property has been asked for
and met.

## One number not to believe, by our own calibration

`Biggrow` reads 6/50 in the anchored arm against 0/50 in the control (Fisher P = 0.0267), which
looks like a signal. It is not: `verify_run` puts it at **P = 0.0776 against its own untrained
null — not above chance**. And today's sham-split calibration
([2026-08-12_how_often_our_primary_test_fires_on_nothing.md](2026-08-12_how_often_our_primary_test_fires_on_nothing.md))
measured `Biggrow`'s false-positive rate at **0.0252**, among the highest of the six, with a
scan-level rate of 0.17–0.24 for finding *some* significant cell on arms that differ by nothing.
An isolated P = 0.027 discovered while scanning six parameters across three poolers is precisely
what that calibration says to discard. `Biggrow` remains excluded by construction.

## What this licenses, and what it does not

**Licensed.** `ind330` and `ded177` must be reworded: the Southern Ocean's lack of calcite
constraint is a property of the **Daniels compilation**, and with a real local anchor the leg
carries recoverable information under at least one collapse. The claim that it is *purely*
inherited no longer stands unqualified.

**Not licensed.** This is not a clean "R_PICPOC is locally identifiable in the Southern Ocean". It
fails under two of three collapses, the anchor is 0.9% of cells, and it costs a significant amount
of `scav_rat`'s arithmetic leg. **No published number changes** — every reported `R_PICPOC` result
uses Daniels and the 3-AOI configuration, neither of which this run touches.

**Recommended next step, not run here.** The obvious follow-on is whether the median collapse is the
*right* reading for a sparsely anchored parameter, or whether 43/50 is itself a collapse artifact of
the kind the pooler audit was built to catch. That is a question about the metric, answerable on
these artifacts without new compute, and it should be settled before the median number is quoted
anywhere.
