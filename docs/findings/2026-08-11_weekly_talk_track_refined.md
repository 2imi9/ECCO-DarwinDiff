# Talk track (refined Aug 11) — weekly update, Aug 4–11

Companion to `2026-08-09_presentation_planning_weekly_log_aug4_11_as_of_aug9.html` (now 17
slides; slide 17 is an Aug 11 addendum with the summer closeout plan).

Spoken register, first person, honest hedges built in. **Core path: slides 1, 3, 4, 5, 10, 11,
13, 17. About 12 minutes.** Everything else is backup you jump to only if asked:
slide 2 (how the research map works), 6 (Southern Ocean gate), 7–9 (matrix completeness),
12 (waiver lattice), 14 (weekend plan), 15–16 (Aug 10 appendix).

The ★ lines are the ones to hit if time runs short. **If you only have 5 minutes: slides 1, 4,
5, 10, 17.**

---

## Slide 1 — Framing (~30 s)

> This is the Aug 4 to 11 log. Two threads this week. First, the self-twin experiment that was
> meant to decide which loss formulation is right for `scav_rat`. ★ **It validated the whole
> machinery, and then told us the target we used cannot decide the question.** Second, a cheap
> Stage-0 check that stopped an invalid seasonal run before it spent any cluster time. So the
> week's result is deliberately bounded, and I'll be precise about what is established and what
> is not.

*Skip slide 2 unless someone asks how the evidence system works. Jump to slide 3.*

## Slide 3 — Shape of the week (~45 s)

> Quick shape of the week. It started with controls, not headlines. I repaired the provenance
> gates, withdrew a couple of easy accuracy stories, and replicated the loss-selects-basin
> observation on disjoint seeds. Then I preregistered the self-twin, ran it, and bounded what it
> can claim. The pattern I am trying to keep: correction first, then the run, and the run only
> claims what its gates permit.

## Slide 4 — The machinery validates (~1.5 min) ★

> First half of the self-twin. In the two verified basins, equatorial Pacific and North
> Atlantic, the matched control cells recover `scav_rat` **50 out of 50** at the 0.20 band,
> under all three poolers, against untrained nulls of **0 out of 50**. ★ **This is a machinery
> validation, not a science claim.** Runner, target construction, grader, matched null: all
> shown to recover the signal when the signal is present. It is the reason the next slide is
> interpretable.

*One honesty line, said out loud:* "The Southern Ocean is not in this evidence set at all. The
Daniels and POSi terms have zero geographic coverage there, so the verifier refuses to grade it
rather than printing rows. There's a backup slide, and fixing that gate is on this week's plan."

## Slide 5 — The double null (~2 min) ★ the core

> Here is the actual result. The long constant-forcing target, the quasi-steady state after
> 4,000 steps, returns **0 out of 50 for both losses**, in both basins, at every band, under
> every pooler. And the diagnostic measured before fitting explains why: DFe2 spatial contrast,
> the field that carries the `scav_rat` signal, collapses by roughly **845 times** in the
> equatorial Pacific and **51 times** in the North Atlantic as the box runs to steady state.
>
> ★ **So the honest reading is: this target erased the signal before the fit began.** It is a
> double null. It is not evidence for the endpoint loss and not evidence for the time-mean
> loss. One submission, no replication, and I am not settling the loss question on it.
>
> What it does buy is the requirement for the next decider: average full seasonal cycles after
> spin-up, and demonstrate retained DFe2 contrast before fitting anything.

## Slide 10 — Why there is no seasonal target yet (~2 min) ★

> So why not just build the seasonal target? I tried, in a staged way, and this is the part of
> the week I find most scientifically interesting. Each repair exposes the next missing
> mechanism. Physical forcing alone collapses the iron contrast and later makes DIC non-finite.
> Chemical restoring keeps iron and DIC, but drives diatom chlorophyll toward zero. Realistic
> astronomical light does not rescue the biomass either.
>
> ★ **The process budget localizes the failure: with grazing frozen as an implicit closure, the
> diatoms carry a biomass-independent loss floor, and the box cannot make a seasonal bloom.**
> Stage 0 stopped the target for a few local CPU-hours, before any cluster time was spent on a
> fit that could not have been interpreted.

## Slide 11 — The mechanism (~1 min)

> The mechanism in one picture. Without prognostic zooplankton, grazing cannot relax when
> predators would starve. In the first cycle, grazing supplies roughly 57 to 69 percent of
> diatom gross loss across the six test cells, and the invasion calculation says a rare diatom
> cannot invade in five of the six. One caveat I want on record: this is a diagnosis of the
> reduced box, not of Darwin's grazing budget.

*Skip slide 12 (the waiver enumeration) unless asked; the one-line version is: "I enumerated
every allowed shortcut around the failure, and no admissible one exists."*

## Slide 13 — The energy deficit, and the bridge (~1.5 min) ★

> When I make the grazers explicit, the diatoms persist, but the large zooplankton state fails
> for a different reason: its best annual energy gain sits below its mortality integral in
> every retained cell. Over the weekend I checked an aggressive upper bound: even letting the
> predator teleport to the best wet cell every quarter day does not close the deficit in two of
> the three basins. So the missing piece is not relocation inside the frozen fields. It could
> be transport changing the prey field, depth structure, or a missing prey channel; the result
> does not identify which. It only says: do not tune the failed target.
>
> ★ **The constructive version of all this: the reduced box needs prognostic zooplankton before
> it can serve as a seasonal twin target.** That extension was already on the roadmap as the
> next tier of the box model. This week turned it from nice-to-have into the gating item, with
> a measured mechanism behind it.

*Skip slide 14 (the weekend micro-plan; it mostly executed) and go to 17. Slides 15–16 are the
Aug 10 appendix; offer them only if there is interest in the teleport bound details.*

## Slide 17 — The last two weeks of summer (~1.5 min) ★

> Summer has two working weeks left, so here is where the time goes. This week: merge the
> evidence branch from this log, fix the Southern Ocean coverage gate, and fold the bounded
> self-twin result into the identifiability write-up. Next week: get the write-up to
> review-ready, and leave a clean handoff. Tracker groomed, map current, and the seasonal loss
> decider scoped as a fall experiment on a changed target model with prognostic zooplankton.
>
> ★ **The write-up is the summer deliverable.** I will not start a new recovery array in these
> two weeks unless a Stage-0 target passes every gate first, because a half-run array at
> handoff is worse than a well-scoped plan.

*Close:* "That's the update. The one-line summary: the machinery is validated, the constant
target is non-diagnostic, the seasonal blocker is now a measured mechanism instead of a
mystery, and the write-up is what ships before summer ends. Happy to go deeper on any slide."

---

## Delivery guardrails (unchanged from the Aug 9 notes)

- Do not call `alpfe` an accuracy result or quote a percentage as one; it rails to its bound.
- Report `scav_rat` under the geometric collapse, or show all three together, never arithmetic
  alone.
- Do not show the retracted emulator globe or the retracted persistence bar chart.
- Do not elevate the constant-steady double null into a Darwin endpoint-versus-time-mean
  conclusion.
- Say "write-up", not "paper" or "manuscript", when talking to collaborators.

## Anticipated questions (with honest answers)

- **"So which loss is correct?"** Undecided. The constant target is non-diagnostic because it
  erases the deciding contrast. The valid decider must average full seasonal cycles after
  spin-up and demonstrate retained DFe2 contrast before fitting. That is now a scoped fall
  experiment, not a summer one.
- **"Doesn't this kill the box model?"** No. Under constant forcing the harness is validated
  end to end (the 50/50 matched cells). The bound is specific: the current reduced box cannot
  serve as a *seasonal* twin target without prognostic zooplankton. That is a scoped extension,
  and the failure mechanism is measured, not guessed.
- **"Is the North Atlantic teleport number a positive result?"** No. The unrestricted stepwise
  oracle clears mortality by 0.08 percent, every preregistered continuous radius is negative,
  and the envelope needs jumps of up to 28 grid cells in a quarter day. It is a knife edge on
  an intentionally loose bound, and the other two basins fail even that bound.
- **"Why is the Southern Ocean missing?"** The Daniels and POSi terms have zero geographic
  coverage there, and historical artifacts declared them active anyway, so the verifier exits
  with an error instead of grading. The fix (distinguish expected zero coverage from missing
  staged data) is task 02 this week. Until then those cells are gated, not quoted.
- **"How much compute did this cost?"** One 75-task array plus its grader for the self-twin.
  Everything else, the Stage-0 ladder, the process budget, the invasion test, and the teleport
  oracle, ran locally and deterministically. Zero B200 hours were spent on the invalid target.
- **"What actually lands before summer ends?"** The merged evidence branch, the coverage-gate
  fix, and a review-ready identifiability write-up, plus a groomed tracker and a scoped fall
  plan. No new arrays unless a Stage-0 target passes.

## Appendix — what ran this week (including nulls)

| run | where | state | result |
|---|---|---|---|
| Self-twin factorial, 15 arms x 50 seeds | job 320993 | all 75 tasks done | matched cells 50/50 all poolers; long target 0/50 everywhere |
| Grader | job 320994 | exit 0 | arithmetic / geometric / median, all reported |
| Dimensional matrix + independent verifier | local | verified, SHA-256 receipts | 1,080 cells; 360 numeric, 360 excluded-with-reason, 360 gated |
| Seasonal Stage-0 target ladder (forcing, restoring, light) | local, deterministic | verified | target stopped; each repair exposes the next blocker |
| Process budget + invasion test | local, deterministic | verified | grazing 57–69% of diatom gross loss; 5/6 cells non-invadable |
| Explicit-zooplankton gate + energy audit | local, deterministic | verified | diatoms rescued; large-Z below replacement in all retained cells |
| Teleport path oracle + verifier | local, deterministic | verified (16.77M support cells) | relocation hypothesis falsified in 2 of 3 basins; NATL +0.08% knife edge |

All recovery numbers are synthetic self-twin (trained vs Carroll truth) under the stated gates;
nothing here is a real-data discovery claim.
