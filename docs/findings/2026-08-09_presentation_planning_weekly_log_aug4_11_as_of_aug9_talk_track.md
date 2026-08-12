# Speaker Script: DarwinDiff Weekly Research Log

Companion to `2026-08-09_presentation_planning_weekly_log_aug4_11_as_of_aug9.html`.

Core deck: slides 1-14, frozen as of Aug. 9, 2026. Slides 15-16 are a separately labelled Aug. 10 appendix. This is a status-and-controls presentation, not a claim that the loss question is settled. About 10 minutes for the core deck, plus 2 minutes for the appendix.

## Slide 1 - Status boundary

"This is the Aug. 4-11 weekly log. The central result is deliberately bounded: the constant-forcing self-twin narrowed the loss question, but did not answer it. In parallel, Stage 0 stopped us from spending compute on an invalid seasonal reduced-box target. The core log is frozen as of Aug. 9; the final two slides are a separately labelled Aug. 10 appendix."

## Slide 2 - Research control pattern

"The operating change behind the week is that our research map is not a notes page. It is a queryable evidence system. The corpus is canonical, the markdown is a readable generated view, and the in-memory database gives us joins, traces, and gates. Before a new run, we ask whether the question is already settled, pre-register a falsifier, then grade against a matched null. That sequence matters because it prevents us from reviving retracted claims or running a study whose result cannot be interpreted."

## Slide 3 - Weekly evidence chronology

"The week began with controls, not a new headline. We repaired memory and provenance gates, then audited the metric and withdrew easy accuracy stories. We replicated the observation that loss selects the basin, preregistered the self-twin, harvested it, and then bounded the result. The recurring pattern is that correction and falsification narrow what the next run is allowed to claim."

## Slide 4 - Validated results

"The matched cells validate the self-twin machinery. In the verified Equatorial Pacific and North Atlantic cells, trained `scav_rat` reaches 50 of 50 at the 0.20 band under arithmetic, geometric, and median collapses, while the matched nulls are 0 of 50. This is a machinery validation: it shows that the runner, target construction, grader, and matched-null comparison can recover the intended signal when that signal is present."

## Slide 5 - Unreplicated result

"The long, constant-steady target removes the deciding signal. Its subsurface DFe2 spatial contrast collapses essentially to zero, and both endpoint and time-mean losses give 0 of 50 across all tested bands in both verified basins. That is not evidence for either loss. It says this quasi-steady proxy erased the spatial information that `scav_rat` needs. This is one submission with no fresh replication, and it does not settle the endpoint-versus-time-mean question for seasonally forced Darwin. The next valid decider must average full seasonal cycles after spin-up and demonstrate retained DFe2 contrast before fitting."

## Slide 6 - Excluded and gated

"The Southern Ocean is not in the evidence set. Daniels and POSi have zero geographic coverage there, but the historical artifacts still declared those terms active, so `verify_run` exits 2. The old grader printed rows anyway; we do not treat them as evidence. The repair is to teach the verifier the difference between expected zero coverage and an unstaged input. We also keep the retracted emulator render and retracted persistence graphic out of this presentation."

## Slide 7 - Complete evidence tensor

"This slide is here to prevent a narrow result from pretending to be the full experiment. There are forcing, basin, arm, parameter, pooler, band, seed, and replication dimensions. The current run fills only one slice: constant forcing, two verified basins, one submission, and no seasonal dimension. Empty, excluded, and gated cells remain visible rather than being silently dropped."

## Slide 8 - All verified scav-rat cells

"For the two verified basins, this table is every reportable `scav_rat` cell, not a selected 0.40 headline. Geometric is the primary collapse, with arithmetic and median adjacent. The matched target cells pass; the long target cells are zero under all poolers at every band and sit at, or worse than, their untrained null. The concise interpretation is unchanged: the self-twin works where the target retains contrast, and the constant-steady long target is non-diagnostic."

## Slide 9 - Arm gates and parameter disposition

"Every arm and every parameter keeps a visible role. `scav_rat` is the primary inferential target and is shown geometrically. `R_PICPOC` here is only a synthetic anchor-machinery check. `alpfe` is a boundary diagnostic, not an accuracy number. `diatomgraz`, `Smallgrow`, and `Biggrow` are outside this loss decision for their stated construction limits. The point is that a gated or excluded cell is represented by status, never replaced with an attractive count."

## Slide 10 - Seasonal target ladder

"We did not start an optimizer or a B200 array just because the constant target was non-decisive. We tested seasonal target construction first. Forcing with temperature, salinity, and wind collapses DFe contrast and later makes DIC non-finite. Chemical restoring keeps DFe and DIC, but drives diatom chlorophyll toward zero. Astronomical light does not rescue biomass. The process budget then localizes the mechanism to a strong diatom grazing loss, and explicit grazers expose a second blocker. Stage 0 therefore stops the target, not the science question."

## Slide 11 - Diatom sink and invasion geometry

"The failed biomass gate is a reduced-box diagnosis. Without prognostic zooplankton, grazing cannot relax with predator biomass, creating a biomass-independent diatom loss floor. In cycle one, grazing supplies roughly 57 to 69 percent of diatom gross loss across the six AOI-light cells. The rare-invasion calculation says five of six cells are uniformly non-invadable; the small fixed-light Southern Ocean refuge prevents us from claiming a universal zero attractor. This is a mechanism finding about the reduced box, not a Darwin grazing budget."

## Slide 12 - Explicit grazer exclusion and blocker lattice

"Making the grazer closure more source-mirrored lets diatoms persist, but exposes a different failure: the large zooplankton state is excluded and the parameter handle stays too weak. We enumerated every allowed waiver subset. No singleton or pair fixes the target; only the forbidden waiver of all three blockers would pass. That means there is no admissible shortcut around the Stage 0 failure."

## Slide 13 - Large-predator energy deficit

"The large predator is below replacement before variance penalties. Across retained cells, its best annual gross gain remains below its integrated mortality. Diets are differentiated, so this is not an identical-diet artifact; the included prey field is energetically insufficient. The result does not identify the missing mechanism. It could be transport, depth, another prey, assimilation, or something else. It only tells us not to tune the failed frozen target."

## Slide 14 - Planned closeout

"The closeout order is fixed. First, resolve the Southern Ocean coverage gate. Second, write the bounded self-twin finding with its matched validation, double-null result, exclusion, and no-replication caveat. Third, scope issue 239 with a preregistered seasonal Stage 0, and use B200 only if that target passes every gate. Finally, harden the remaining review paths. At this cut, no GitHub issue should be closed and no additional constant-steady factorial should be submitted."

## Slide 15 - Appendix: continuity is load-bearing

"This is an Aug. 10 appendix, not part of the Aug. 9 cut. In a frozen-prey North Atlantic path calculation, every preregistered continuous relocation radius is negative. The only positive envelope requires discontinuous quarter-day teleportation. This is a bound on the frozen trajectory, not evidence that real transport cannot help, because real transport can alter prey, cross AOI boundaries, and couple depth."

## Slide 16 - Appendix: relational map closeout

"The closeout is procedural rather than scientific. The map traces verified evidence through support edges to a live, bounded claim, and records the falsified reduced-box execution path separately from the still-open Darwin loss question. We have learned where this reduced model stops. The next admissible experiment must change the target model, rather than tune a target that failed its own gates."

## Delivery Notes

- Present slides 1-14 as the core. Use slides 15-16 only if the Aug. 10 appendix is useful.
- Do not call `alpfe` an accuracy result or quote a percentage as one; it rails to its supplied bound.
- Report `scav_rat` under geometric collapse, or show all three collapses together.
- Do not show the retracted emulator globe or the retracted persistence-comparison bar chart.
- Do not elevate the constant-steady result into a Darwin endpoint-versus-time-mean conclusion.
