# ECCO-DarwinDiff summer research closeout

**Synthesis for the next-week presentation, 2026-08-11.** This document does
not add a scientific claim. It ranks the project's existing, map-checked
results by durability and states what the summer work actually contributes.

## One-sentence thesis

**Biogeochemical parameter identifiability follows the geometry of the
observation: real absolute anchors recover global source and rain-ratio
parameters, while process rates become identifiable only where a region and an
observable expose their mechanism. More optimization cannot create missing
information.**

That is more meaningful than a "parameters recovered" score. The honest
denominator is four observable parameters, not six. Two are globally recovered
under real anchors; two are regionally identifiable in different basins; the
growth pair is excluded under the current time-mean design.

## What was built

The summer produced a research instrument, not just a collection of runs:

1. A differentiable Carroll-6 / ECCO-Darwin surrogate with a per-cell neural
   parameter field, multi-AOI training, seasonal integration, and matched
   synthetic-twin paths.
2. Real-data loss terms and provenance for dissolved iron, Daniels calcite
   production, POSi biogenic silica, dust, and other observational anchors.
3. Slurm sweep and grading machinery with per-AOI grading, architecture-matched
   untrained controls, three pooling rules, verifier exits, and explicit
   coverage gates.
4. Independent identifiability diagnostics: Fisher/Gauss-Newton geometry,
   profile likelihood, EKI as a gradient-free check, source reads, ablations,
   and synthetic falsifiers.
5. A forward neural-operator emulator path with log-space physical-state
   correction, multi-seed baselines, and global/depth experiments.
6. A relational R&D map that joins claims to evidence, hypotheses, documents,
   supersessions, and traps. At this cut it exposes 548 settled answers, 308
   inductive claims, 100 active hypotheses, and eight passing integrity
   constraints.

The last item is itself a result of the research process. It turns "have we
already answered this?" and "is this number retracted?" into executable
queries instead of memory tests.

## The parameter pattern that survived correction

### `alpfe`: globally constrained source magnitude

`alpfe` is a global scale on already-soluble iron deposition. It is the
near-saturated control across the three basins and is supported by real iron
and dust information. Its recovery is not an accuracy certificate: Carroll's
value lies near the supplied upper bound, and boundary geometry cannot be
reported as precision.

The scientific role of `alpfe` is to show what a globally acting source
parameter looks like when the observation directly measures the affected
inventory.

### `R_PICPOC`: globally recovered because a real absolute anchor reaches it

With the Daniels CP:PP anchor, `R_PICPOC` is 50/50 in the flagship. Removing
that anchor at the matched 2,000-epoch budget reduces it to 6/50. This is the
cleanest causal anchor result in the parameter study.

It does not validate a globally constant Carroll value. Daniels coverage is in
EqPac and the North Atlantic, not the Southern Ocean, and the real ocean rain
ratio is regional. The claim is that an independent absolute calcite anchor
breaks the surrogate's z-score scaling ambiguity.

### `scav_rat`: a regional, depth-structured iron signal

`scav_rat` is not globally point-identified by surface dissolved iron. Under
the required geometric pooler it is established in one Southern Ocean basin,
but that result has no independent replication and does not transfer to the
better-sampled Kerguelen-Crozet transfer basin. Kerguelen is naturally
iron-fertilised, so this is not a matched-regime replication.

The local Southern Ocean Fisher geometry points to vertical structure as a
symmetry-breaker. Subsurface dissolved iron rotates the `alpfe`-`scav_rat`
block from a near-rank-one surface ridge to a well-conditioned two-parameter
problem. Conditioning is not recovery: up-weighting the term did not improve
recovery monotonically, and the result did not transfer across basins. The
next observing-system test is therefore a depth-resolved dissolved-iron
profile or a direct scavenging/export-flux anchor, not more surface bottles and
not more epochs.

### `diatomgraz`: replicated regional identifiability in the equatorial Pacific

At the strict `<=0.10` per-leg band, the EqPac signal reproduces in a separate
submission: 18/50 under all three poolers at the 200-step window against an
architecture-matched 0/50 null. The earlier width arms gave 40/100 on the same
scale. Training is anti-recovery in the other two basins.

This is the project's better-supported regional parameter result because it
has genuine out-of-sample replication. It also demonstrates why a global
aggregate is scientifically lossy: the same parameter is informative in one
basin and misleading in two.

### `Smallgrow` and `Biggrow`: excluded, not failed

The precise statement is practical non-identifiability under a 23-year
climatological, time-mean design with no group-resolved production observable.
`Smallgrow` has a promising but unconfirmed seasonal North Atlantic prototype
at 9/10. `Biggrow` remains unobservable by construction. Neither belongs in a
flattering or punitive 4-of-6 score.

## The strongest cross-parameter result

Only two of the four observable parameters carry independent real absolute
anchors in the current loss:

| parameter | current information source | honest scope |
|---|---|---|
| `alpfe` | real dissolved iron + guarded dust prior | global source-scale control |
| `R_PICPOC` | real Daniels CP:PP | global recovery, anchor present in 2/3 AOIs |
| `scav_rat` | model pattern + regional vertical iron structure | one unreplicated regional signal |
| `diatomgraz` | Darwin/POSi structure + environmental input | replicated EqPac regional signal |

The **2-of-4 anchor asymmetry** is a better paper headline than any joint
recovery count. It predicts which parameters are robust, which are regional,
and which new observations would change the answer.

## What B200 contributed

B200 was useful as throughput, not as a source of scientific authority.

- The n=10 dust-anchor A/B ran on B200 and gave `scav_rat` 0/10 in both arms,
  with almost identical medians. A source-side anchor cannot identify a sink
  rate. That null is scientifically important because it converts a plausible
  intervention into a rejected one and points to a sink-flux or depth anchor.
- A global monthly emulator run completed in about 19 minutes on B200, showing
  the platform can support real-scale neural-operator experiments.
- The later seasonal Stage-0 work deliberately did **not** use B200. Its target
  failed before optimization, so a recovery array would only have made an
  invalid experiment expensive.

No new B200 result was produced in the Aug. 9-11 closeout. The newest
continuity and explicit-grazer findings are deterministic, independently
verified target-only audits.

## The seasonal self-twin result

The constant-forcing self-twin did two things:

1. It validated the machinery. In verified EqPac and North Atlantic matched
   cells, `scav_rat` is 50/50/50 at `<=0.20` under arithmetic, geometric, and
   median pooling, against 0/0/0 matched nulls.
2. It showed the constant quasi-steady long target is non-diagnostic:
   `scav_rat` is 0/0/0 at every tested band under endpoint and time-mean losses.

That double null does not choose endpoint versus time mean for Darwin. A
seasonally forced target was therefore gated before fitting. Monthly forcing,
chemical restoring, astronomical light, and a source-mirrored explicit-grazer
projection all failed the preregistered target criteria for different reasons.
The source-floor correction did not change the decision.

The final frozen-path upper bounds sharpen the diagnosis. EqPac and the
Southern Ocean remain below large-predator replacement even under unrestricted
relocation. North Atlantic becomes barely positive only under discontinuous
quarter-day teleportation; radius-limited paths are all negative. This rules
out a physically continuous relocation through the unchanged frozen prey path,
not real transport that alters prey, crosses boundaries, or couples depth.

The durable outcome is a **correct stop**: no optimizer and no B200 against a
target that failed its own falsifier.

## The emulator result

The emulator work has an engineering success and a scientific negative.

Log-space training removed negative concentrations, restored oligotrophic
dynamic range, and produced fast global inference. Those are real engineering
achievements. They did not buy forecast advantage:

- skill versus persistence is `+0.055 +/- 0.013` across four seeds, with
  confidence intervals crossing zero;
- skill versus per-cell seasonal AR(1) is `-0.161 +/- 0.015`, with every seed's
  confidence interval entirely below zero;
- useful forecast horizon remains one step.

The earlier persistence and climatology wins were retired. The emulator is not
accurate enough to be the summer product. Its scientifically useful role is a
negative benchmark and a warning: physical validity and low one-step error do
not establish incremental forecast information.

## Corrections are part of the contribution

The project found and corrected several result-changing traps:

- arithmetic pooling manufactured or destroyed `scav_rat` passes depending on
  where the geometric centre sat relative to the band;
- a `0.40` aggregate band hid both regional `diatomgraz` signal and
  anti-recovery;
- splitting one array in half was shown not to be out-of-sample replication;
- old emulator claims used weak persistence/climatology baselines and a linear
  transform that produced nonphysical states;
- Southern Ocean declared-on observational terms had expected zero coverage,
  which the old verifier could not distinguish from staging failure;
- a literal source prey floor was initially omitted from the reduced explicit-
  grazer projection and was corrected before any optimizer run.

These are not side notes. They explain why the final claims are narrower and
more defensible than the early ones.

## Scientifically useful prototype

The deployable prototype is the
[`DarwinDiff Evidence Navigator`](../tools/darwindiff_evidence_navigator.html),
not the emulator. It is generated from `docs/research_map.json`, embeds the
source SHA-256, and exposes:

- settled answers;
- live claims only;
- active hypotheses with falsifiers;
- interpretation traps;
- parameter and relation filters;
- tracked, non-retracted source status.

It is useful to a scientist deciding what can be cited, what remains open, and
which observation would change an identifiability conclusion. It does not
pretend to predict the ocean.

## What is scientifically important

The summer's meaningful contribution is a **map from observation design to
parameter identifiability**:

1. Absolute anchors remove scale ambiguities.
2. Vertical structure can separate source from sink in local iron-cycle
   geometry, but conditioning alone does not guarantee recovery.
3. Regional environmental regimes expose different process parameters.
4. The current climatological time-mean targets lack growth-rate information
   that seasonality may retain.
5. More optimization can move a practical boundary, but cannot repair an
   absent observation or an invalid target.

This is an observing-system and experimental-design result, framed through a
differentiable surrogate. It is not a claim that the surrogate reproduces the
full ocean or that all six Carroll parameters are recovered.

## Presentation close

End with this sentence:

> ECCO-DarwinDiff did not produce one universal parameter score. It produced a
> tested map of which observations identify which biogeochemical processes,
> where that identification holds, and where the honest answer is to stop.

## Do not claim

- Do not say six of six, four of four, or "3-of-4 frontier."
- Do not use `alpfe` bound geometry as accuracy.
- Do not report `scav_rat` from arithmetic pooling alone.
- Do not globalize the regional `scav_rat` or `diatomgraz` signals.
- Do not call the seasonal reduced-box failure a Darwin grazing result.
- Do not say the emulator beats persistence or is ready as a forecast product.
- Do not say the constant twin chooses endpoint versus time mean for Darwin.
- Do not say frozen-path relocation proves real transport cannot help.

## Primary sources for the deck

- [`STATUS.md`](../../STATUS.md)
- [`docs/research_map.md`](../research_map.md)
- [`2026-08-04_pooler_audit_the_flagship_trio_halves.md`](2026-08-04_pooler_audit_the_flagship_trio_halves.md)
- [`2026-08-05_the_integration_window_is_a_contested_resource.md`](2026-08-05_the_integration_window_is_a_contested_resource.md)
- [`2026-08-06_scav_rat_does_not_transfer_to_kerguelen.md`](2026-08-06_scav_rat_does_not_transfer_to_kerguelen.md)
- [`2026-07-22_dust_anchor_ab_b200.md`](2026-07-22_dust_anchor_ab_b200.md)
- [`2026-07-23_emulator_multiseed.md`](2026-07-23_emulator_multiseed.md)
- [`2026-08-09_constant_forcing_self_twin_double_null.md`](2026-08-09_constant_forcing_self_twin_double_null.md)
- [`2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md`](2026-08-10_literal_source_floor_correction_preserves_the_seasonal_stage0_stop.md)
- [`2026-08-10_continuity_eliminates_the_natl_teleport_knife_edge.md`](2026-08-10_continuity_eliminates_the_natl_teleport_knife_edge.md)
