# Pre-registration: is `R_PICPOC`'s Southern Ocean leg inherited, or just unmeasured?

**Written 2026-08-12 BEFORE submission, with zero JSONs on disk for any arm of this experiment.**
**Gate:** `verify_run.py` exit 0, then `pooler_audit.py --legs`.

## The question

`ind330` says R_PICPOC's Southern Ocean leg is **INHERITED** through the shared DINN rather than
locally anchored, and `ded177` says `southernoceanpac` is not a counterexample to the f_calc
mechanism, both for the same reason: the basin has **zero Daniels cells**. The 3-AOI evidence
cannot separate two explanations, because with other basins present there is always something to
inherit from.

Today's measurement changes what is testable: Daniels 2018 has 0 cells there, **Marsh 2025 has 12**
(42 observations, median rain ratio 0.04520 against Carroll 0.04245). See
`2026-08-12_the_southern_ocean_calcite_gap_is_the_compilation_not_the_ocean.md`.

So the hypotheses are:

**H_inherited.** The SO leg carries no local calcite information. Giving it a genuine local anchor
changes little, because 12 cells is too weak to constrain the rain ratio — R_PICPOC stays near 0.

**H_unmeasured.** The leg was never inherited so much as *unanchored*. In a single-AOI SO run there
is nothing to inherit from at all, so any R_PICPOC recovery must be local, and the anchor is what
supplies it.

The single-AOI design is what makes this clean: with one basin, inheritance is impossible by
construction, so a non-zero R_PICPOC can only come from the anchor.

## Design

Four arms in ONE submission (cross-job comparison of a control is not defensible), seeds 50–99,
single AOI `southernoceanpac`, otherwise the `so_only` configuration.

| arm | `DANIELS_RPICPOC_W` | `RPICPOC_ANCHOR_SOURCE` | epochs | purpose |
|---|---|---|---|---|
| `som_anchor` | 1.0 | `marsh` | 2000 | trained, Marsh SO anchor live (12 cells) |
| `som_noanchor` | 0.0 | — | 2000 | trained, no anchor — the matched control |
| `som_anchor_prior` | 1.0 | `marsh` | 1 (`lr=0`) | untrained null for the anchored arm |
| `som_noanchor_prior` | 0.0 | — | 1 (`lr=0`) | untrained null for the control |

Both nulls are required: the anchor changes the loss, so the two arms do not share a null.

> **⚠ AMENDMENT, 2026-08-12, written BEFORE any trained result was read.** That justification is
> **wrong**, and it was measured wrong rather than argued wrong: `som_anchor_prior` and
> `som_noanchor_prior` are **bitwise identical across all 50 seeds and every parameter** (0
> differing entries, max relative difference 0.0).
>
> The reason is elementary and I should have seen it. At `NB23_LR=0` with `NB23_N_EPOCHS=1` the
> optimizer takes one step of size zero, so the network never leaves initialisation and **the loss
> is never used to update anything**. The anchor weight cannot influence a network that does not
> train, so changing `DANIELS_RPICPOC_W` between the two null arms is inert by construction.
>
> **This does not invalidate the experiment.** Both trained arms are graded against a correct
> architecture-matched untrained baseline; there are simply two copies of the same one. The cost is
> 5 wasted chunks at ~20 s each, which is negligible.
>
> Recorded because the error is instructive: an adversarial screen had flagged exactly this failure
> mode ("two nulls are only distinguishable if the null is 1 epoch at the *real* lr") in a
> *different* proposal earlier the same day, and I did not apply it to my own running design. The
> general rule: **a null defined by `lr=0` is independent of every loss-side lever, so one null
> covers all arms that differ only in loss weights.** A null that must distinguish loss variants has
> to train for at least one real step.

`POSI_W=0.0` throughout — the Southern Ocean genuinely has zero POSi coverage and declaring it on
is what made job 237913 fail `verify_run` with exit 2.

Note `som_noanchor` is configuration-identical to the `so_rep` replication already running as job
352450. That is deliberate: it is an internal consistency check. If the two disagree beyond seed
noise, something is wrong with one of them and **this experiment is void, not interesting**.

## Decision rule, fixed now

Primary: R_PICPOC's per-AOI count in `som_anchor` versus `som_noanchor`, both n=50, exact
two-sided Fisher, each read against its own untrained null.

- **LOCALLY ANCHORABLE (H_unmeasured)** if `som_anchor` R_PICPOC ≥ 15/50 **and** it exceeds
  `som_noanchor` at P < 0.01 **and** it clears its own null at P < 0.01.
- **NOT ANCHORABLE (H_inherited)** if `som_anchor` R_PICPOC is not above `som_noanchor` at
  P < 0.05.
- **AMBIGUOUS** otherwise, reported as ambiguous rather than rounded to either.

The prior expectation is H_inherited, because 12 cells is a weak anchor — `diatomgraz`'s bSi anchor
operates on 11 cells and `diatomgraz` is not globally identifiable. A positive result would
therefore be genuinely surprising.

## Secondary reads, fixed before seeing anything

1. **`scav_rat` must not degrade in `som_anchor`.** The Southern Ocean is the one basin where it is
   established (`so_only` geometric 49/50). If adding a calcite anchor damages it, that is a real
   cost and must be reported even though the experiment is "about" R_PICPOC.
2. **`som_noanchor` must reproduce `so_rep`** within seed noise (same config, same seeds, different
   job). Disagreement voids the run.
3. **`alpfe` should stay ~50/50** in every trained arm; a collapse means the run is broken.
4. Report all three poolers. R_PICPOC has been pooler-invariant everywhere measured (log_sd ≤ 0.21),
   so a pooler-dependent R_PICPOC result here would itself be a finding.

## What each outcome means

**LOCALLY ANCHORABLE.** `ind330` and `ded177` need rewording from a claim about the ocean to a claim
about the Daniels compilation, and the Southern Ocean gains a real calcite constraint in the basin
where `scav_rat` is already established — the first basin with two independent anchors. It would
also raise whether Marsh should replace Daniels globally, which is a larger change needing its own
A/B, since every published R_PICPOC number is Daniels-based.

**NOT ANCHORABLE.** `ind330` survives with a *better* justification: not "there are no observations"
(false) but "12 cells of real observation are insufficient to constrain the rain ratio locally".
That is a stronger statement than the current one and it retires an error in the stated reason.

Either outcome is reportable, which is the test for whether the run should happen.
