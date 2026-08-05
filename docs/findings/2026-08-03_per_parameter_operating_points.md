# The per-parameter operating-point map — the optimal configuration for each parameter, separately

**Date:** 2026-08-03 · **Status:** synthesis of verified results; no new run
· **Supersedes the framing of:** "the 3-of-4 frontier", "two operating points"

## Why this document replaces the search for one configuration

The project has been looking for a single configuration that recovers every observable, and
reporting the shortfall as a *frontier*. That framing has two defects, and both are visible in
results the repo already holds.

**Defect 1 — the denominator is wrong.** `diatomgraz` was counted as the fourth observable. Its
prior midpoint sits at rel **0.367**, inside the 0.40 pass band — the only one of the six — so
an untrained network scores **0.64** there for free. At the ≤10% band, where that contamination
is removed, it is **0/50 trained and 0/50 untrained** in all three per-parameter arms. It was
never a fourth observable; it was a band artifact.

**Defect 2 — identifiability is parameter-specific, so a single operating point is the wrong
object.** `alpfe` recovers under nearly any configuration. `R_PICPOC` needs one specific thing
(a real calcite anchor) and then recovers completely. `scav_rat` responds to capacity, to
epochs, and to architecture, and is dead in one basin under all of them. These are not points
on one frontier; they are four different problems that happen to share a network.

The honest deliverable is therefore a map with **one row per parameter, each carrying its own
architecture-matched untrained null**.

## The map

| parameter | best measured | its own untrained null | best-known configuration | class |
|---|---|---|---|---|
| `alpfe` | **50/50** | 10/50 flagship arch · 13/50 per-param · 15/50 widened | flagship `geo1`; insensitive | **point-identified**, method-independent |
| `R_PICPOC` | **50/50** | 0/50 | flagship `geo1` **+ real Daniels CP:PP anchor** | **identified given a real absolute anchor** |
| `scav_rat` | **83/100** | 0/50 | **added network capacity** (width 39 shared trunk) | **regionally identifiable**; one basin model-limited |
| `diatomgraz` | **0/50** at ≤10% | 0/50 at ≤10% (0.64 at ≤0.40) | none | **not established at an uncontaminated band** |
| `Smallgrow` | — | — | — | excluded: non-identifiable from *time-mean* observables |
| `Biggrow` | — | — | — | excluded: unobservable by construction |

**Three recovered, one unestablished, two excluded.** Not "3 of 4".

### `alpfe` — solved, and the least interesting

50/50 under per-parameter trunks, 49/50 under the flagship. It is the one parameter recovered
by three independent estimators (DINN, Nelder-Mead on a DINN-free box, and a derivative-free
EKI), so the verdict is estimator-independent. The one caveat that must travel with it: its
recovery is **weight-conditional** — it depends on the real GEOTRACES iron being up-weighted.
Do not quote it as unconditional.

### `R_PICPOC` — solved conditionally, and the condition is the finding

50/50 with the real Daniels CP:PP anchor; **6/50** with the anchor off at a matched 2000-epoch
budget (4/50 at 1500). The gap between those two numbers *is* the scientific content: this
parameter is not recoverable from Darwin's own output, and becomes recoverable when a real
absolute observation is supplied. It also **generalises** — `southernoceanpac` has zero Daniels
cells and still recovers, inherited through the shared DINN, collapsing to 13.06x when the
anchor is pulled from the other two basins.

Quote 6/50 against the 2000-epoch flagship, never 4/50.

### `scav_rat` — the live one, and the only one with a basin that no intervention has moved

Every lift measured, each against its own null of 0/50:

```
flagship, PUBLISHED  406 w, 2000 ep    25/50      n50e2k_percell_trio, the canonical value
4000 epochs          406 w, 4000 ep    41/50      same data, no new information
capacity-matched    1878 w, 2000 ep    72/100     network SIZE alone           <- replicates
per-parameter       1926 w, 2000 ep    83/100     architecture on top          <- does NOT
```

**The architecture effect was tested at n=100 and rejected** (job 258256). Pooled, 83/100 vs
72/100 gives Fisher **P = 0.0897**, clearing neither the 0.01 bar nor 0.05. Split by seed
block it is stark: seeds 0–49 gave 45/50 vs 34/50 (P = 0.0128, the originally reported half),
and the fresh seeds 50–99 gave **38/50 vs 38/50, P = 1.0000** — an exact tie. The whole effect
was in the first block. See
[2026-08-03_per_parameter_trunks_do_not_replicate_at_n100.md](2026-08-03_per_parameter_trunks_do_not_replicate_at_n100.md).

**What replicates is capacity.** Widening the shared trunk is the lever; giving each parameter
its own trunk is not, and costs ~4.7x the weights for it.

**A provenance note that matters for every comparison below, and that changed twice while this
was written.** The 26/50 baseline the 2026-08-03 arms quote was **not** measured in either of
those jobs — job 256953 ran only `ppw` and `ppw_null`. Its true source is
`logscale/ctrl_n50`: scav_rat 26/50, legs 8/19/49 — a separate subW=1 arm, not the flagship,
and numerically identical to `subiron_n50`. The canonical published value is **25/50**,
legs 7/20/49.

Today's own flagship-config arm, `adq_ctrl`, gives **20/50** (legs 4/16/49). It is tempting to
read 20 / 25 / 26 on identical seeds as a ~6-seed run-to-run spread, which would be larger than
several effects this project has reported. **That reading is not supported.** A key-by-key
comparison of the two artifacts shows 14 fields differing, and every one of them is `<absent>`
in the older run — including **`lr`**, the exact variable whose absence produced a false
code-regression claim earlier the same day. *Absent is unknown, not equal.* The 20-vs-26 gap is
**unattributable** on the recorded evidence, and cannot be cited as either non-determinism or
a real difference until the older arm is re-run on a recorded config.

The practical consequence: **compare within a job, never across jobs.** Every comparison below
that matters is within-job.

Two thirds of the lift survives the capacity control; **two fifths is capacity**, and the
architecture's own contribution is **P = 0.0128**, which does not clear this project's own 0.01
bar. An n=100 extension (job 258256) is running to settle it. Until it lands, 45/50 must never
be quoted against the flagship without the 34/50 control beside it.

Per basin, the structure is stable across every arm:

| | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| flagship, published (canonical legs) | 7/50 | 20/50 | 49/50 |
| flagship-config control, re-run in 256953 | 8/50 | 19/50 | 49/50 |
| capacity-matched, **n=100** | **11/100** | 70/100 | **100/100** |
| per-parameter, **n=100** | **11/100** | **81/100** | 95/100 |

Two things the n=100 legs show that n=50 could not. **eqpac is 11/100 in both arms, identical
to the seed** — it is now unmoved by capacity, by epochs, by information weighting, and by
removing representation sharing. And **per-parameter trunks trade basins**: natl +11, sopac −5,
so the aggregate difference is a net of two opposite movements rather than a lift. The
capacity-matched control is the arm that reaches a clean 100/100 in the Southern Ocean.

**Southern Ocean is at ceiling and is independently identifiable there** — a single-AOI SO fit
gives 30/50 against untrained 0/50, P = 3.15e-24, from GEOTRACES iron alone with nothing to
pool from. **North Atlantic is the responsive leg**, and every lift the project has measured
lands there. **eqpac has never moved** — 4–8/50 at every capacity, both epoch budgets, and
under every intervention tried.

That last row now has a candidate explanation that is not "not enough information": eqpac's
Fisher rank is **4/4**, so the information is present, while the box's iron residual there is
**larger than the signal** at both the prior midpoint (1.347) and the recovered optimum (≥1.0).
Full information, zero adequacy. Job 258314 tests whether removing that term helps; see
`2026-08-03_prereg_adequacy_weighted_routing.md`.

### `diatomgraz` — the correction

The claim to retire is not "diatomgraz recovers"; it is **"the 0.40 band means anything for this
parameter"**. The evidence, all of it already in the repo:

- untrained rate at ≤0.40 is **0.64** (job 227777);
- the "non-circular handle" 35/50 sits against a **matched untrained 34/50**, P = 0.447
  (`ind270`) — the number cannot support the claim it was used for;
- at ≤10%, **0/50 trained and 0/50 untrained** in all three 2026-08-03 arms;
- and the bSi observable it is graded through is **partly circular**, being algebraically
  back-solved from diatom biomass (`ded116`).

What is *not* retracted: `ind262` records `diatomgraz` beating its own untrained rate in 3 of 3
basins in the MLD arm. That is a per-basin result at the contaminated band and it has not been
disproven here. The correct statement is the narrow one: **`diatomgraz` has not been shown to
recover against its own null at a band where recovery is meaningful.**

## What this does to "two operating points"

The two-operating-point framing said `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`} while
MLD + heavy Daniels holds {`alpfe`, `diatomgraz`, `R_PICPOC`}. The second set's distinguishing
member is `diatomgraz`, and its leg has never cleared an uncontaminated band. The second
operating point is therefore **not established** — it is the first operating point plus a
parameter that scores well because the band is wide.

There is one operating point. The mutually-exclusive-levers story (`scav_rat` needs the
Darwin-pattern term, `diatomgraz` needs MLD) survives only as a statement about *loss-landscape
conflict*, not as two comparable configurations.

## How to use this map

- **Report per parameter, with its own null.** The joint trio count is bound by its weakest
  leg and hides that the legs are different problems.
- **Do not chase one configuration.** `R_PICPOC` needs an anchor; `scav_rat` needs capacity and
  an adequate basin. Nothing suggests one network must do both at one setting.
- **Every count needs an architecture-matched null.** Untrained `alpfe` is 10/50, 13/50 and
  15/50 on three architectures — a borrowed null inflates in exact proportion to the change
  under test.
