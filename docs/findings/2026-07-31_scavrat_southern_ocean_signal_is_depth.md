# The Southern Ocean scavenging signal is DEPTH, and it confirms a prediction made nine days earlier

> **⚠️ CORRECTED 2026-07-31 (same day) — the DEPTH interpretation is under active challenge. The
> counts and gates below stand; the mechanism may not.**
>
> The subsurface iron channel has not converged in the 50-day integration window (L2 relaxation time
> 384 days, so 12.2% of the way to equilibrium), and these arms ran `darwin_ic=False`, giving a
> basin-uniform initial state in a box with no horizontal transport. The forward sensitivities are
> then identical across all three basins to four decimals. A competing explanation orders the
> recovery correctly without any depth structure: the Southern Ocean's observed subsurface median
> (0.2245 nM) is the closest of the three basins to the box's basin-blind 50-day value (0.2671 nM).
> See `docs/findings/2026-07-31_depth_mechanism_does_not_replicate_in_eqpac.md` for the full
> correction and the pre-registered window-swap test that decides it.

**Date:** 2026-07-31 · **Jobs:** 239556 (4 arms) + 239560 (grade) ·
**Gate:** `verify_run` **exit 0 on all four arms** · **Pre-registration:**
`2026-07-30_prereg_scavrat_mechanism_surface_vs_depth.md`, written with zero JSONs on disk ·
**Verdict: DEPTH. The pre-registered rule fires, and the two observation levels turn out to
identify different parameters.**

## The primary read

Single AOI `southernoceanpac`, everything byte-identical except the two iron weights. The two
ablation arms are **volume-matched to each other** (13 surface bins against 14 subsurface), so the
head-to-head is not confounded by how much data each sees.

| arm | live iron observation | `scav_rat` | null | P(>=k) | verdict |
|---|---|---|---|---|---|
| `so_surf` | surface only (13 bins) | **14/50** | 0/50 | 9.33e-07 | **not above chance** |
| `so_sub` | subsurface only (14 bins) | **33/50** | 0/50 | 1.70e-28 | **RECOVERS** |

**Fisher exact two-sided P = 0.000268.** The arms are different, and the pre-registered verdict is
**DEPTH**: the subsurface level alone suffices and the surface level alone does not.

The pre-registered falsifier clears: `alpfe` in `so_surf` is **49/50**, so that arm can fit
perfectly well. `scav_rat`'s failure there is a property of the observation, not a broken run.

## The part that was not predicted: the levels identify different parameters

| arm | `alpfe` | `scav_rat` |
|---|---|---|
| `so_surf` (surface iron) | **49/50 RECOVERS** | 14/50 not above chance |
| `so_sub` (subsurface iron) | 14/50 not above chance | **33/50 RECOVERS** |

The pattern is clean and it inverts. Surface iron identifies the **source** and cannot see the sink;
subsurface iron identifies the **sink** and cannot see the source. Neither level alone identifies
both, and the combined fit (`so_only`, 30/50) is essentially the subsurface arm.

## This confirms a synthetic prediction on real data

`2026-07-22_column_osse_result.md` ran an idealised 1-D iron column as a synthetic self-twin and
concluded, in its own words, that the mechanism is that **`alpfe` sets the profile AMPLITUDE while
`scav_rat` sets its SHAPE** (e-folding `~sqrt(kz/scav)`). It moved CRLB(log scav) from 4.2e6 in a
0-D box to 0.005 in a column.

A surface concentration is an amplitude. A profile is a shape. So the OSSE predicted exactly the
inversion measured above, nine days before the run, from synthetic data, on a different code path.

That is the strongest form of confirmation available here: a mechanism proposed on a self-twin,
pre-registered as a decision rule, and then found in real GEOTRACES observations.

## Secondary reads, explicitly confounded

Each ablation arm has about half the data of the parent (13 or 14 bins against 27), so these
comparisons mix *which channel* with *how much data* and are reported as secondary.

| comparison | discordant seeds | McNemar exact | reading |
|---|---|---|---|
| `so_surf` 14/50 vs parent 30/50 | 23 lost, 7 gained | **P = 0.0052** | differs |
| `so_sub` 33/50 vs parent 30/50 | 11 lost, 14 gained | **P = 0.69** | not distinguishable |

**Removing the surface term costs nothing.** The subsurface arm alone is statistically
indistinguishable from the full fit for `scav_rat`, on shared seeds, despite carrying half the
observations. The surface channel is not contributing to this leg.

## Controls, all of which held

- **Gate:** `verify_run` exit 0 on all four arms. `GATE_FAIL=0`.
- **Runner-sync control:** `so_repro` reproduces parent 238079 **bitwise** on shared seeds, all six
  parameters, max relative difference **0.000e+00**. The parent ran against an older cluster build,
  so this certifies the sync empirically rather than by assertion.
- **Null control:** `prior_so_abl` is **bitwise identical** to `prior_so_only` (50 shared seeds,
  0.000e+00). At `NB23_LR=0` the network cannot see the loss, so changing the iron weights must
  change nothing, and it does not. This is the check that the ablation is doing what it claims.
- **Coverage provenance** is now recorded in the artifact itself: 13 surface and 14 subsurface bins
  in `southernoceanpac` for every arm, so the volume-matching is verifiable from the JSON rather
  than from this note.

## One incompleteness, disclosed

`so_repro` finished **10/50**, not 50/50: array task 239556_4 hit a one-hour TIMEOUT and was
cancelled. `so_repro` is a **secondary control**, not a primary arm, and its 10 completed seeds are
bitwise identical to the parent, which is what it exists to show. The three arms carrying the
result, `so_surf`, `so_sub` and `prior_so_abl`, are all complete at 50/50. Under the standing rule
that short arms are refilled rather than graded as complete, **no count from `so_repro` is quoted
here beyond the bitwise-identity check**, which does not depend on n.

## What this changes

**`scav_rat` is identifiable from the vertical structure of dissolved iron, not from its surface
concentration.** That is a sharper claim than "locally identifiable in the Southern Ocean" and it
explains the earlier result rather than restating it. The Southern Ocean was where it showed up
because that is where the subsurface GEOTRACES coverage and the strong sink coincide, not because
the basin is special in some unexplained way.

**It also predicts where to look next.** If depth is the mechanism, then any AOI with subsurface
iron coverage should show some recovery, and the ranking across basins should track subsurface bin
count rather than surface. That is a directly falsifiable follow-up on data already held.

**And it makes the column build the obvious next rung.** `2026-07-22_column_osse_result.md` closes
by naming "the real-data column build" as the next step, with remineralization prescribed from v05
as load-bearing. This result is the empirical warrant for doing it: the mechanism it depends on has
now been observed rather than assumed.

## What this does not change

The gauge-symmetry result stands (`2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`). Depth
breaking the degeneracy is not in tension with it: the orbit is a symmetry of a **surface,
single-level** steady state, and a second level is exactly the extra constraint that lifts it. No
learned closure placed inside a multiplicative sink gains that information, which is why the UDE
route remains closed while this route opens.
