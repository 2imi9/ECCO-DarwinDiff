# ECCO-DarwinDiff summer closeout speaker notes

**Target length:** 14-16 minutes plus questions. These notes follow the HTML
deck slide by slide. The first sentence under each slide is the point to land;
the rest is supporting language, not text to read verbatim.

## 1. What the observations let us identify (0:30)

The summer result is not a six-parameter score. It is a tested map of which
observations expose which biogeochemical parameter directions. The short form
is 2 + 2 + 2: two globally recovered controls, two regional signals, and two
growth parameters excluded under the present design. The second theme is
discipline: several important outcomes were correct stops or corrections, not
larger recovery counts.

## 2. The inverse question changed (0:45)

We began by asking whether a differentiable surrogate could recover six
published controls. That framing was too coarse. A fit can move a parameter
without the target carrying information about it, so our unit of evidence
became parameter by basin, compared with an architecture-matched untrained
null and checked across grading bands and pooling rules. Once a target fails
its own falsifier, another optimizer or GPU array is not a scientific test.

## 3. What the summer built (0:55)

The engineering contribution is an auditable inverse-modeling instrument. It
joins a differentiable Carroll-6 surrogate and seasonal integrator to real
observation terms, multi-region fitting, matched synthetic twins, independent
geometry checks, and hard verifier gates. The numbers at the bottom describe
the research memory at this presentation cut, not model performance: 548
settled questions, 100 still-active hypotheses, and all eight enforced map
constraints passing.

## 4. Relational-algebra R&D map (0:55)

The map made the research process executable. Evidence is joined to support
edges, claims, documents, settled answers, hypotheses, supersessions, and
known traps. Before work, we query whether a question is already settled;
before quoting a number, we query whether it was superseded; before committing
a result, constraints test its provenance. Markdown remains the human reading
view, while the database is rebuilt in memory for relational queries. This is
why the final story can be narrower than earlier weekly stories without losing
the audit trail.

## 5. The 2 + 2 + 2 parameter atlas (1:05)

This is the main scientific result. `alpfe` and `R_PICPOC` are global controls
within the tested inversion, but only because real absolute observations reach
their scale directions. `scav_rat` and `diatomgraz` carry regional information
in different basins and must not be globalized. `Smallgrow` and `Biggrow` are
excluded from the score because the current time-mean design lacks the
group-resolved production information needed to grade them. Also stress the
asymmetry: only two of the four observable parameters have independent real
absolute anchors in the current loss.

## 6. What absolute anchors buy (1:00)

For `alpfe`, dissolved iron plus a guarded dust prior constrain a source-scale
direction, and the result is method-independent. Do not translate the tight
count into precision: Carroll is close to the supplied upper bound, so bound
geometry is not accuracy. For `R_PICPOC`, the causal comparison is especially
clean: 50 of 50 with the real Daniels CP:PP term and 6 of 50 in the
epoch-matched anchor-off control. The scope remains bounded because Daniels
covers two of three study regions and a bulk-equivalent rain ratio is not a
validated universal ocean constant.

## 7. Iron source-sink geometry (1:15)

Surface dissolved iron mostly sees a source-minus-sink balance, leaving a long
`alpfe`-`scav_rat` ridge. In the Southern Ocean local Fisher block, adding the
depth axis rotates that geometry to condition 2.2, and the regional fit gives
49 of 50 under the required geometric pooler against a zero null. Two limits
matter. First, this result has no independent replication. Second, Kerguelen
gives only 2 of 50 geometrically despite more iron coverage, and it is a
naturally iron-fertilised transfer basin rather than a matched regime. Thus
depth is a candidate symmetry-breaker, not a universal recovery guarantee;
the decisive next observation would be a depth profile or direct sink/export
rate, not simply more surface bottles or epochs.

## 8. Regional grazing signal (1:00)

`diatomgraz` in the equatorial Pacific is the better-supported regional result.
A genuinely separate submission, job 270032, gives 18 of 50 at the strict
`<=0.10` band under arithmetic, geometric, and median pooling, against 0 of 50
for the matched untrained null. The earlier width arms gave 40 of 100 on the
same scale. Training moves the other two basin legs away from the reference,
so an aggregate 0.40 score hid both the positive EqPac signal and the negative
regional behavior.

## 9. Why the growth pair is excluded (0:45)

The honest label is practical non-identifiability under the current 23-year
climatological, time-mean construction. The observable set has no
group-resolved production target, so different growth histories can collapse
to the same mean state. `Smallgrow` has one encouraging seasonal North
Atlantic prototype at 9 of 10, but it is simplified and unconfirmed.
`Biggrow` remains unobservable. Exclusion prevents missing information from
being misreported as either success or model failure.

## 10. Seasonal self-twin closeout (1:20)

The constant matched twin proves that the machinery can recover `scav_rat`:
50 of 50 under all three poolers at `<=0.20` in verified EqPac and North
Atlantic cells, against zero nulls. The quasi-steady long target gives the
opposite result, zero at every tested band under endpoint and time-mean losses,
because its dissolved-iron contrast is erased. This does not choose endpoint
versus time mean for transported Darwin. We then gated a seasonal target before
fitting: monthly forcing, chemical restoring, astronomical light, and an
explicit-grazer projection all failed frozen target checks. Correcting the
literal prey floor did not change that stop, and continuity removed the one
tiny North Atlantic teleport knife edge. Real transport remains open because
it can alter prey, cross boundaries, and couple depth.

## 11. What B200 actually contributed (0:50)

B200 accelerated decisive controls; it did not confer scientific authority.
The n=10 dust-anchor A/B on job 177483 produced `scav_rat` 0 of 10 in both arms
with effectively identical medians, showing that a source-side anchor cannot
identify the sink rate. A global emulator experiment also completed in about
19 minutes, establishing practical throughput. There was no new Aug. 9-11
B200 result: the seasonal target failed before fitting, so declining to submit
an array was the correct use of compute.

## 12. Corrected emulator result (1:00)

The emulator has a real engineering success and a scientific negative.
Log-space training removed negative concentrations, and inference reaches one
global step in 7.45 milliseconds. Across four training seeds, skill versus
persistence is +0.055 +/- 0.013, but every spatial-block confidence interval
crosses zero. Against the stronger per-cell seasonal AR(1), skill is -0.161
+/- 0.015 and every interval is below zero. The useful horizon is one step.
Therefore the emulator is not the product to ship as a forecast tool; its
value is the physical-state correction, throughput benchmark, and honest
negative control.

## 13. Corrections are part of the result (0:55)

The project changed its own conclusions when the evidence demanded it.
Arithmetic pooling could manufacture or destroy `scav_rat` passes; a broad
band hid strict regional grazing structure; splitting one array was not true
replication; seasonal AR(1) retired weak emulator headlines; expected zero
coverage had to be separated from staging failure; and the reduced-grazer
source floor was corrected before any optimizer ran. These corrections are
methodological contributions because they specify what a defensible recovery
claim requires.

## 14. Evidence Navigator prototype (0:45)

The small product is the Evidence Navigator, not an ocean forecast interface.
It is a self-contained HTML artifact generated from the relational JSON map
and bound to that source by SHA-256. A scientist can search settled answers,
live claims, active falsifiers, and interpretation traps by parameter and
source status. Its narrow promise is useful and testable: help decide what can
be cited and which experiment or observation would change an answer.

## 15. Scientific contribution (1:10)

The paper-level contribution is an observing-system design result expressed
through differentiable modeling. Absolute anchors remove scale ambiguity;
depth can rotate a local source-sink geometry; regional environments expose
different process directions; the current time-mean design lacks growth
information; compute can move optimization boundaries but cannot create an
observation; and provenance rules determine whether a recovery count means
anything. Keep the qualification that Fisher conditioning is not itself
recovery and that the reduced box is a surrogate, not the full ocean model.

## 16. Close (0:30)

ECCO-DarwinDiff did not produce one universal parameter score. It produced a
tested map of which observations identify which biogeochemical processes,
where that identification holds, and where the honest answer is to stop. The
next observation is depth-resolved iron or a true sink-rate anchor; the next
model target must include repaired transport; and the current useful product
is the Evidence Navigator. Then stop and take questions.

## Question boundaries

- If asked whether `alpfe` is accurate, say its signal is strong but precision
  is unresolved because the estimate rails near the supplied bound.
- If asked whether `scav_rat` is solved, say it is one unreplicated regional
  geometric-pooler result with a failed Kerguelen transfer test.
- If asked which regional result is strongest, say `diatomgraz` in EqPac
  because it survived a genuinely fresh submission at a strict band.
- If asked whether the emulator works, separate physical validity and speed
  from incremental forecast information; the latter is negative versus
  seasonal AR(1).
- If asked why no new B200 run was launched, say the preregistered target gate
  failed before fitting and compute cannot repair an invalid target.
- If asked whether the seasonal study settles Darwin endpoint versus time
  mean, say no; transported, seasonally forced Darwin remains an open target.
