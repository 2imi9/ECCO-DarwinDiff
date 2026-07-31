# The depth mechanism does not replicate in eqpac, and the failure is more informative than the original

> **🛑 RETRACTED 2026-07-31 — the interpretation does not survive an integration-window swap.**
> Job 241109 held everything byte-identical and changed only `N_STEPS`. The basins TRADE PLACES:
> at 100 steps `eq_sub` recovers `scav_rat` **23/50** and `so_sub` **0/50**; at 200 steps it is
> 6/50 and 33/50; at 400 steps 0/50 and 35/50. Every pre-registered leg passes at P < 0.01 and
> the falsifier clears (`alpfe` in `eq_surf` 49/50 → 50/50, the converged surface channel is
> window-insensitive). The counts and gates below stand; the depth interpretation is withdrawn.
> See `docs/findings/2026-07-31_window_swap_retracts_the_depth_result.md`.

> **⚠️ CORRECTED 2026-07-31 (same day) — the DEPTH interpretation is now in serious doubt, and a
> competing explanation fits the numbers better. The measured counts and gates stand; the mechanism
> does not.**
>
> The subsurface iron channel **has not converged inside the integration window**. `N_STEPS=200` at
> `DT=0.25` is **50 days**, and integrating the real box shows it reaches only **47.5%** of the way
> to the L2 equilibrium. (An earlier version of this banner said 12.2%, computed from the *initial*
> `POC_2` of 0.05; `POC_2` actually grows to ~0.33, speeding scavenging ~6.6x. The corrected figure
> is 47.5% and the conclusion is unchanged.) The exact `d ln DFe₂ / d ln scav_rat = −1` identity
> quoted below is **asymptotic**; the measured elasticity at 200 steps is about **−0.41**, while the
> hardcoded initial condition `LIT_IC[10] = 5.0e-4` carries log-leverage **0.983**.
>
> The sharper statement: the box's subsurface iron **sweeps downward through every basin's observed
> median**, so the integration window silently selects which basin the model agrees with.
>
> | window | box DFe₂ | nearest basin |
> |---|---|---|
> | ~73 steps | 0.4404 nM | eqpac |
> | 100 steps | 0.4047 nM | (between) |
> | **200 steps, what ran** | **0.2671 nM** | heading for sopac |
> | ~243 steps | 0.2245 nM | southernoceanpac |
>
> The run's window sits nearest **southernoceanpac**, which is the only basin where `scav_rat`
> recovers.
>
> Worse, these arms ran `darwin_ic=False`, so `state0` is **uniform across every basin** and the box
> has no horizontal transport. The forward sensitivities are then identical across eqpac, natl and
> sopac to four decimals, so **no forward-model quantity can explain the basin difference at all**.
>
> The competing explanation, which orders correctly:
>
> | AOI | observed subsurface median | basin-blind box @50 d | \|log distance\| | `scav_rat` |
> |---|---|---|---|---|
> | southernoceanpac | 0.2245 nM | 0.2671 nM | **0.174** | **33/50** |
> | eqpac | 0.4404 nM | 0.2671 nM | 0.500 | 6/50 |
> | natlsubpolar | 0.5638 nM | 0.2671 nM | 0.745 | not run |
>
> `scav_rat` recovers in exactly the basin where a hardcoded, basin-independent transient happens to
> land nearest the data. That explanation involves no depth structure whatsoever.
>
> **Decisive test, pre-registered separately:** at `N_STEPS=100` the box sits at 0.4047 nM, near
> eqpac rather than the Southern Ocean, so the two basins should **trade places**. If they do, the
> depth mechanism is a window artifact. If they do not, it survives and is strengthened.
>
> Found by the identifiability panel, then verified independently from the source.

**Date:** 2026-07-31 · **Jobs:** 240673 (4 arms x 50 seeds) + 240694 (grade) ·
**Gate:** `verify_run` **exit 0 on all four arms**, `GATE_FAIL=0`, every arm complete at 50/50 ·
**Pre-registration:** `2026-07-31_prereg_depth_mechanism_replication_eqpac.md`, written before any
eqpac ablation JSON existed ·
**Verdict: DOES NOT REPLICATE. Depth is necessary but not sufficient.**

## The result

Single AOI `eqpac`, 2000 epochs, everything byte-identical to the southernoceanpac arms except
`AOIS`. Masked coverage from the runner's own log: **surface 26 bins, subsurface 28**, against
southernoceanpac's 13 and 14. The replication basin has **twice** the subsurface iron.

| arm | live iron observation | `alpfe` | `scav_rat` |
|---|---|---|---|
| `eq_both` | surface + subsurface | 50/50 | 0/50 |
| `eq_surf` | surface only | 49/50 | 0/50 |
| `eq_sub` | subsurface only | **0/50** | **6/50** |
| `prior_eq_abl` | untrained null (`NB23_LR=0`) | 17/50 | 0/50 |

## Against the pre-registered rule

| test | bar | result | verdict |
|---|---|---|---|
| `eq_sub` vs its untrained null | Fisher P < 0.01 | 6/50 vs 0/50, **P = 0.0267** | **does not clear** |
| `eq_sub` vs `eq_surf` | Fisher P < 0.05 | 6/50 vs 0/50, **P = 0.0267** | clears |
| falsifier: `alpfe` recovers in `eq_surf` | must hold | **49/50** | clears |

REPLICATES required both primary tests. The first fails, so **this is not a replication.**

**A flaw in my own pre-registration, disclosed.** The rule said REPLICATES at P < 0.01 and FAILS if
`eq_sub` is "not above its null", leaving the band between 0.01 and 0.05 undefined. P = 0.0267 lands
in that gap. It is reported as not clearing the bar rather than resolved to the convenient side.
The next pre-registration states one threshold and both tails.

**The falsifier clearing is what makes this a real negative.** `alpfe` reaches 49/50 in `eq_surf`,
so the arm fits perfectly well. `scav_rat`'s failure is a property of the information, not a broken
run.

## The basins genuinely differ, and it is not data volume

| comparison | Fisher exact two-sided |
|---|---|
| `so_sub` 33/50 vs `so_surf` 14/50 (the original) | 2.68e-4 |
| **`so_sub` 33/50 vs `eq_sub` 6/50** | **3.72e-08** |

eqpac has **twice** the subsurface coverage and recovers `scav_rat` five and a half times less
often. Whatever separates these basins, it is not how much subsurface iron was observed. That
retires the volume explanation directly rather than by argument.

## What this does to the mechanism

The 2026-07-31 Southern Ocean result proposed **depth structure**: `alpfe` sets the profile
amplitude, `scav_rat` sets its shape. That mechanism, alone, predicts eqpac should recover
`scav_rat` better than the Southern Ocean, because it has more of exactly the observation the
mechanism says carries the signal. It does not.

There was a competing explanation on the books: the Southern Ocean recovers `scav_rat` because
**scavenging carries about 79.7% of the steady-state surface iron sink** there
(`2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md`). In an equatorial upwelling regime,
biological uptake takes a far larger share of the iron sink, so the same subsurface profile carries
much less information about the scavenging rate no matter how densely it is sampled.

**These are not rivals. They are conjuncts.** Depth separates the source from the sink; term
dominance decides whether the sink is visible at all. The Southern Ocean has both. eqpac has the
depth coverage and not the dominance, and it recovers almost nothing.

The honest claim is therefore narrower than the one this experiment set out to test:

> `scav_rat` is identifiable from the vertical structure of dissolved iron **in regimes where
> scavenging dominates the iron sink**. Depth is necessary. Dominance is what makes the depth
> information worth anything.

## The unpredicted read: subsurface-only iron is worse than not training

`alpfe` in `eq_sub` is **0/50, below its own untrained null of 17/50**. The fit does not merely fail
to find `alpfe`; it is actively driven away from Carroll by subsurface-only iron. The same inversion
appeared weakly in the Southern Ocean (`so_sub` `alpfe` 14/50) and is total here.

This is a candidate symptom of **forward-model misspecification** rather than an information limit:
a term that is wrong will fit the subsurface profile by moving a parameter that should not have
moved. It is flagged as a hypothesis, not a conclusion, and the separating experiment is not
designed yet.

## How this was nearly lost

The competing sink-dominance hypothesis was **silently deleted from the research map** by a primary
key that fell back to the first 12 characters of the statement, so
"The Southern Ocean scav_rat recovery comes from DEPTH STRUCTURE..." overwrote
"The Southern Ocean recovers scav_rat because scavenging is ~79.7%...". Seven of ninety-nine
hypotheses were gone the same way. Found and fixed on 2026-07-31 while auditing the map, hours
before this result made the deleted hypothesis the important one.

An index that drops competing explanations is worse than no index, because the surviving
explanation looks unopposed.

## What to do next

1. **Compute the scavenging fraction of the iron sink per AOI.** It is the candidate a-priori
   predictor of `scav_rat` recoverability, it needs a forward run and no fitting, and it is
   directly testable against recovery counts that already exist
   (sopac 49, natl 20, eqpac 7 in the flagship).
2. Do not run more basins first. A cross-basin coverage comparison was already retired on
   2026-07-31: surface and subsurface GEOTRACES coverage are collinear at r = 0.996, so basin
   rankings cannot separate the two hypotheses.
3. Treat `alpfe` falling below its untrained null as its own thread.

## Provenance

The AICR checkout was found reverted to an older runner build (`c6622e10`) despite the Southern
Ocean arms having run `3d5ebe67`. It was backed up, re-synced and verified back to `3d5ebe67` before
launch, so these arms ran the **same build** as the originals. Every task logs its own runner md5.
See issue #218.
