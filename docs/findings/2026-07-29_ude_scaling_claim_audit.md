# Does the UDE break our scaling pitch? An audit of the "adding parameters is easy" claim

Produced 2026-07-29 by an adversarially-verified 5-topic audit (11 agents). Prompted by the question:
we pitch that adding parameters is easy AND we are proposing a UDE, and those may not sit together.
Companions: [`2026-07-28_session_evidence_log.md`](2026-07-28_session_evidence_log.md),
[`2026-07-29_jon_reply_crosscheck.md`](2026-07-29_jon_reply_crosscheck.md).


# Does the UDE break our scaling pitch?

## 1. Is the tension real?

**Yes.** Lucas spotted a genuine inconsistency, and the evidence sharpens it rather than dissolving it.

The precise shape: our scaling pitch is, at almost every tracked site in the repo, a claim about **cost**. Gradients for all parameters in one backward pass, versus a Green's-functions ensemble of roughly N+1 forward runs. That claim survives a UDE completely intact. One backward pass costs the same whether the head emits 6 numbers or a closure emits a function.

But two tracked sentences upgrade the cost claim to an **identifiability** claim, and those are exactly the sentences a UDE would inherit. Meanwhile every measurement we have on learned closures says the binding constraint is information, not compute. So the pitch and the proposal point in opposite directions on the only axis that matters scientifically.

Three measured facts make this concrete:

- The 2026-07-21 UDE stress test is the iron proposal in miniature. A learned closure reached `closure_rel_err` **0.0064968** on the visited DFe band and **2.8773839** on the full range, and the full-range error was 2.877 in **all four** regularisation configs across weight-decay {0, 0.001} x anchor {0, 0.01} (`docs/findings/ude_stress_2026-07-21/C_closure_recovery.json` and the four `D_*.json`). The file's own conclusion: a regularizer cannot manufacture information about states the trajectory never visits.
- On real calcite through transport, the learned closure lost to a constant. Learned R2 **-1.53** vs null **+0.50** at the default arm, **-0.05** vs **+0.50** regularized (`docs/findings/2026-07-10_e2_powered_result.md`), n_train 18 / n_val 6.
- At N=6 we do not even clear the frontier. No config recovers all four observables (`STATUS.md:305`), and on observations only, `scav_rat` goes to **0/50** per-AOI and the joint trio **25/50 to 0/50** (`docs/findings/2026-07-28_session_evidence_log.md`, section G5).

The tension is not fatal. It is a framing error that is cheap to fix, plus one live sentence in a tracked doc that is not cheap to leave.

## 2. The two claims we have been conflating

**Claim M (mechanical):** an additional parameter costs one extra output channel and one backward pass, not a fresh recompiled forward ensemble. True, defensible, and unaffected by the UDE.

**Claim I (identifiability):** more parameters therefore get *recovered*. Unproven, and our own measurements point the other way.

### Where the repo conflates them, in tracked files

**`docs/ecco_darwin_parameter_inventory.md:64`** is the one sentence a referee could cite against us. Verified verbatim on disk today:

> "Replacing such scalars with MLP-predicted spatial fields, which is what DarwinDiff's parameter-learner does, is a structurally cheap upgrade per parameter that reaches well past the Green's functions ceiling of 'a handful at a time.'"

The first half is Claim M. "Reaches well past the Green's functions ceiling" is Claim I, in the same clause.

**Our own audit already caught it and the fix was never applied.** `docs/findings/2026-07-19_doc_claim_sweep.md:697` heads it "`:64` overclaim", `:700` says "No result in this repo supports 'reaches well past'", and `:703-705` supplies replacement text that draws the distinction correctly:

> "an additional parameter costs an extra channel on the MLP head rather than a fresh ensemble of recompiled forward runs. **Whether that converts into more recovered parameters is unproven.**"

I diffed against the live file. Not applied. That is nine days old.

**`docs/ecco_darwin_parameter_inventory.md:66`**, same file, softer but same direction:

> "unreached by Green's functions because Green's functions cannot afford them"

This asserts affordability is the binding constraint for the other ~97 knobs. We have measured identifiability for exactly six parameters and zero of the other ~97, so we cannot support this either way. Scope it to cost.

**`docs/dinn_design.md:16`:**

> "Each new tuned parameter requires a fresh full forward run. Carroll handled 6 parameters; scaling to 60+ tunable knobs is prohibitive."

Framed as a limitation of Green's functions, so the implicature is that we are not so limited. We never close it, and `:18` ("DarwinDiff attacks both at once") reinforces it. The "60+" also conflicts with the audited "~103 independent tunable scalar knobs" at `ecco_darwin_parameter_inventory.md:45` and `ONBOARDING.md:21`.

**`docs/index.md:96`** is the strongest unhedged framing on the public docs site ("which scale badly ... gradients for all parameters in one backward pass"). The hedge already exists twelve lines away at `docs/index.md:7` ("of which four are the observable identifiability target") and just needs importing.

### Where we do it correctly, and should copy

- `README.md:8` hedges properly: "recovers **the identifiable subset**".
- `docs/ONBOARDING.md:16-26` bounds the claim immediately: "6 of ~103 ... ~5.8% ... a *slice*, not the model."
- `CONTRIBUTING.md:74-117` is the best writing in the repo on this. Steps 1 to 6 are the mechanical checklist. Step 6 (`:94-100`) names the silent-failure mode. Step 7 (`:101`, numbers at `:108-113`) mandates a measured chance baseline. Step 8 (`:114`) requires an architecture-matched one.
- `src/darwindiff/networks.py:22-25` states the correct theory of the advantage, and it is the sentence that bears most directly on the UDE question: "the structural argument behind DarwinDiff over Green's-functions calibration is about ***what the parameters can be conditioned on*** (per-cell environmental covariates) **rather than network capacity**."
- **`docs/paper/main.tex` is clean.** It quantifies "~7 forward runs per gradient" (`:41-42`, `:308-309`) and then disclaims it three separate times (`:116-120`, `:309-310`, `:1097-1100`, including "not a like-for-like speedup of the GCM calibration"). Its only forward-looking scaling line, `:1192`, is "motivates a higher-dimensional surrogate", which is state dimension, not parameter count. The manuscript does not have this problem. The exposure is in the tracked docs a referee or collaborator reads first.

### One correction to how we should attack our own overclaim

Do not say "no config has ever recovered more than 6, so 'reaches well past' is refuted." `PARAMS` has exactly six entries (`src/darwindiff/carroll6.py:139-206`), so more than six was never *attempted*. The absence is by construction. The audit's own word is the right one: **unproven**.

Two claims that felt like exposure are not. `docs/talks/` and `docs/research_notes/2026-05-21_jon_meeting_brief.md` are both gitignored (`.gitignore:112` and `:101`), and `REHEARSAL_QA.md:7-15` carries a file-level banner reading "Do not reuse any of this file verbatim, in any section." So the brief's line "parameter recovery should be a config change, not a research project" (`:11`) is not repo exposure. It is still the sharpest statement of the conflation on disk, and the risk is that it gets **reused** in the UDE conversation.

## 3. What a UDE does to this

### The count

Measured by instantiating the real classes and summing `p.numel()` over `requires_grad` parameters:

| object | free parameters | replaces |
|---|---|---|
| `ScavClosure()` no env | **66** | `scav_rat`, 1 scalar |
| `ScavClosure` +1 / +2 env channels | **82 / 98** | same |
| `EnvCalciteClosure` as run in the E2 (n_env=2, hidden=16) | **353** | `R_PICPOC`, 1 scalar |
| `EnvCalciteClosure` regularized arm (hidden=4) | **41** | same |
| `DINN(n_input_channels=1)`, the entire flagship learner | **406** | all 6 parameters |
| `GlobalScalarNet` / `carroll6.N_PARAMS` | **6** | 6 global scalars |

The iron closure Jon has in mind is **67:1**. The calcite closure as actually run is **353:1**. Both together are **420 free parameters against 2 of the 6 registry scalars**, which is roughly the size of the whole 406-weight DINN that the entire Track-1 study rests on.

### But the count is not the argument, and saying "67x more parameters is 67x harder" would be wrong

Two measurements say capacity is neither the disease nor the cure:

- **EXP-D**: cutting effective capacity via weight decay and a mechanistic anchor left the off-support error at 2.877 in every one of four configs.
- **The E2**: cutting 353 weights to 41 *did* remove the overfit (-1.53 rising to -0.05) and *still* lost to a constant null (+0.50), with a flat non-discriminating K_num ladder (-0.552 / -0.553 / -0.553) and the same sign in all 10 seeds.

### What actually changes is the estimand

A UDE replaces a scalar with a bounded multiplicative envelope over a continuous domain. Both closures are bounded by construction, which is worth stating accurately: `EnvCalciteClosure` returns `10**(A*tanh(MLP))`, confined to [0.1, 10] at the run's A=1.0 (`src/darwindiff/closures.py:28, :80`); `ScavClosure`'s correction is `1 + eps*tanh(MLP)`, confined to [0.8, 1.2] at eps=0.2 (`closures.py:89, :162`). **Updated 2026-08-02 (issue #217):** that correction is now divided by its own geometric mean over a fixed reference support, so the shipped shape factor `G` is confined to [(1-eps)/(1+eps), (1+eps)/(1-eps)] = **[0.667, 1.5]** at eps=0.2, and the free multiplicative level (`log_r0`, one parameter, hence 67 -> 66 above) is gone. Still bounded; the bound is wider than this line originally said. So it is not an unbounded function. It is still a function on a domain, and our measured coverage of that domain is the problem.

**Coverage, measured:**

- EXP-C's visited DFe band is `[1.6554129e-4, 1.6559615e-4]`, which is **1.439e-4 dex** wide. Note this is the 2%-98% quantile band, not the true min/max (`scripts/ude_transport_stress_h200.py:208-212`), so 4% of cells sit outside it.
- For scale, the worst *designed* forcing in our own sweep spans 0.311 dex and the winner spans 2.186 (`docs/findings/2026-07-22_forcing_coverage/stage1_fisher/forcing_design.json`). EXP-C is about **2,100x narrower** than the worst designed forcing. That is ~3.3 orders of magnitude, not four.
- Real iron observations: GEOTRACES IDP2025 surface, good-QC, co-located particulate **and** dissolved iron gives **76 pairs globally and 4 in eqpac** (`docs/findings/iron_coverage_count.json`), over a pFe/DFe ratio spanning 2.594 dex. A 67-weight closure against 4 eqpac points is ~17 weights per observation.
- `STATUS.md:520` puts the dissolved field at "~14 surface cells for ~10k native cells", and `docs/emulator_coupling_plan.md:63` says higher resolution *worsens* this ("more cells, same ~14 GEOTRACES iron obs").

### The distillation oracle, with a correction that matters for iron

The oracle returns NON-IDENTIFIABLE on all three real calcite datasets, across two independent Omega sources and two independent calcite compilations:

- Daniels x v05 cache: eqpac 0.0768 dex, natl 0.0844 dex, pooled 0.2539 dex with n = +0.89 CI [-0.229, +1.780].
- Marsh x v05 cache: pooled 0.3784 dex, which **clears** the span gate, yet n = -0.471 CI [-1.162, +0.163] with rel.std 0.71. When support finally widens, the exponent goes to zero rather than resolving.
- Marsh x in-situ GLODAPv3 bottles (838 eqpac + 1740 natl): pooled 0.2926 dex, under-excited. The null does not depend on the model cache.

**The correction:** the 0.30-dex threshold everyone has been quoting is a `distill_powerlaw` default, which is the **calcite** branch. I verified this directly. `distill()`, the Monod / iron branch, has **no span parameter at all**. Its gates are inclusion >= 0.85, k stability <= 0.20, **aliasing <= 0.95**, and held-out R2 >= 0.90.

This is not pedantry, it changes the precondition. In our own dynamics probe (`docs/findings/symbolic_distill_dynamics_probe.json`) the narrow-regime seeds sit at **0.3107 and 0.3140 dex**, which is *above* 0.30, and both **DISTILL-FAIL** on aliasing 0.9908 / 0.9904. Both had held-out R2 of 0.99999999. Perfect fit, failed verdict. The excited regime at 1.819 / 1.837 dex passed 2/2 with aliasing 0.805 / 0.813.

So a pre-registered DFe target of ">= 0.30 dex" would green-light a support we have already shown fails. The iron-side criterion is the aliasing check, empirically cleared near ~1.8 dex.

### The parameter the iron UDE would replace is the worst candidate we have

`scav_rat` has the lowest relative Fisher information of all six (0.026, versus `diatomgraz` 1.000; synthetic self-twin, so treat as a hypothesis generator not a real-data result). It is the sole binding leg of the trio. And on observations only it goes to **0/50** per-AOI. Replacing an unidentifiable scalar with a 67-weight function enlarges the null space. It does not add information.

### Two things that cut in the UDE's favour, stated fairly

1. **The closure's null is exact and principled.** `EnvCalciteClosure` zero-initialises its readout (`closures.py:66-68`), so `g == 1` for any random draw. I confirmed this is measured: g min = max = 1.0 at seeds 0, 1, 2. The untrained closure *is* the hand-written law. `e2_real_calcite_eqpac.py:219` literally constructs the null as a fresh untrained closure, which means **the E2's +0.50 null R2 already is an architecture-matched untrained baseline**, and the trained closure scored below it. That is a cleaner negative than `diatomgraz` 35/50 vs 34/50 at P=0.447. Compare this to a scalar, where `diatomgraz`'s 64% chance rate is an artifact of its (0.05, 1.0) bounds. The UDE's grading *standard* is better than ours even though its grading *problem* is harder.
2. **`ScavClosure` reproduces the box sink at initialisation** to float round-off (~1e-7, asserted `rtol=1e-6` at `tests/test_closures.py:66-74`). Not byte-identical like the calcite one, but anchored.

### Two harness facts before anyone plans a run

- **`ScavClosure` has never been fit to real data.** I verified: `git grep -ln ScavClosure -- scripts/ notebooks/` returns nothing. It exists only in `closures.py`, two test files, two `trainer.py` docstring references, and one research note. There is no `e2_real_iron_*.py`. The only E2 runner is calcite.
- **`ScavClosure` cannot run through the 0-D box UDE tendency.** `carroll6_ude_tendency` (`carroll6.py:340`) exposes only `ffe_closure` and `calcite_closure`. The scavenging hook lives only in the spatial path, `src/darwindiff/transport.py:42` (also `:471, :520`), consumed at `:97`. Any iron UDE goes through transport, not the box.

## 4. The reframe that survives

**Lucas's hypothesis mostly holds, and it needs one amendment before it is safe to say to a referee.**

### The half that holds

Both halves are real, and both are new this session.

**Cheap.** `N_PARAMS = len(PARAMS)` now exists (`carroll6.py:220`) and is consumed as the `n_outputs` default by all four network classes (`networks.py:67, 116, 218, 271`) and by the flagship at its three network constructions plus the accumulator (`run_v3.0_joint_multi_aoi.py:1611, 1622, 1629, 2051`). Before this session the audit found **85 hardcoded 6s and zero sites deriving the count** (evidence log, section D). The per-cell head is a 1x1 conv, so widening the parameter axis is one integer.

**Measurable.** Two guards, catching two different kinds of nothing, and both are `@pytest.mark.parametrize`d over `PARAM_NAMES` so they extend themselves when the registry grows:

- **Structural nothing.** `tests/test_param_registry_wiring.py`, parametrize at line 175, central-differences at +/-2% of Carroll through a 60-step rollout of the 15-tracer 2-layer box the flagship actually integrates, and fails unless the relative response exceeds 1e-8 (lines 202-211). Its docstring names the failure mode: a registered but unwired parameter fails *silently*, and a recovery count gets reported for something no observation could have constrained.
- **Statistical nothing.** The measured chance baseline. `CONTRIBUTING.md:101-113` makes `NB23_LR=0, NB23_N_EPOCHS=1` mandatory, with measured rates at n=50 (job 227777): `diatomgraz` **0.640**, `alpfe` 0.200, `Smallgrow` 0.120, `scav_rat` / `Biggrow` / `R_PICPOC` **0.000**. Step 8 (`:114`) requires the null to be architecture-matched, because one MLD input channel alone moved untrained `alpfe` from **10/50 to 16/50** with no training.

There is now a third guard that strengthens the case and did not exist when the investigation started. `test_bounds_do_not_put_the_prior_inside_the_cal_grade_band` (line 112 of the same file) is registry-parametrized, backed by `KNOWN_PRIOR_CONTAMINATED = {"diatomgraz"}` at line 61, whose comment pins the arithmetic: bounds (0.05, 1.0), Cal band [0.498, 1.0] = 52.8% of range, midpoint at rel 0.367, 32/50 untrained, P = 0.447. It xfails for `diatomgraz`. This is the first time the repo treats a parameter's *bounds* as a claim that needs defending, and it is enforced in code.

**The single best argument that the method is real: its first application killed one of our own headline numbers.** `diatomgraz` 35/50 against an architecture-matched untrained 34/50 is P = 0.447. A method that only ever confirms your results is not a method. This one does not.

### The amendment, and why it is needed

The detection half currently works **only for bounded scalars, only against a Carroll reference value, and only in a model that has no closure hooks**. Three separate limits:

1. The whole grading stack is built on `rel = |recovered - carroll| / |carroll|` (`diagnostics.py:46-77`, `verify_run.py`, `grade_all_params.py`). A learned closure has no reference function, so there is no `rel`. Bands, per-AOI 2-of-3, the chance rate and the binomial P are all inapplicable.
2. **The registry-guarded model and the UDE-hooked models are disjoint.** `carroll6_5pft_2layer.py` has zero closure hooks. The flagship runner `run_v3.0_joint_multi_aoi.py` has zero occurrences of `closure`, `ScavClosure`, `EnvCalcite`, or `ude_tendency`. The FD guard cannot be pointed at a closure today.
3. `scripts/verify_run.py`, the gate project convention says every recovery number must pass, still hardcodes `PARAMS` (line 46) and `CARROLL` (50-57), and its malformed-input check catches a *missing* key but silently ignores an *extra* one. A 7th registry parameter would be ungraded by the gate. And `CONTRIBUTING.md`'s add-a-parameter checklist never mentions `verify_run.py` at all. The session hardened that file's *metric* (per-parameter straddle guard, per-AOI leading the printout, cell-weighted marked `[DO NOT QUOTE]`) but not its registry coupling.

### Verdict on the reframe

**It holds, scoped to registered scalar parameters.** Here is the sentence a referee would accept:

> Each additional registered parameter costs one output channel on a per-cell head and one backward pass rather than a fresh N+1 forward ensemble, and every registered parameter is checked for measurable coupling to the model state by a registry-driven finite-difference test and graded against a measured untrained-network chance rate, so a parameter the observations cannot constrain is reported as unconstrained rather than as a recovery.

Two caveats I will not paper over. First, "graded against a chance rate" is currently a documented requirement in `CONTRIBUTING.md`, not something `verify_run.py` enforces. Say "required" not "enforced" until that lands. Second, the entire body of work is uncommitted on `main` (`M CONTRIBUTING.md`, `M scripts/verify_run.py`, `M src/darwindiff/carroll6.py`, `M src/darwindiff/networks.py`, `M scripts/run_v3.0_joint_multi_aoi.py`, `?? tests/test_param_registry_wiring.py`, `?? scripts/analysis/grade_all_params.py`), and both evidence documents supplying nearly every number in this analysis are themselves untracked. Nothing has been through PR or bot review.

**The reframe does NOT extend to closures as written.** For a closure the detection half exists in a different and partly better form: `trainer.py:226-237` already has a structural-coupling guard that raises `ValueError` if every gradient of the observable with respect to the closure parameters is zero, and the closure's null is exact rather than an artifact of bounds. But the *chance-rate* analogue, which measures what N free weights buy on n_val cells by luck, does not exist anywhere, and no closure metric is in `verify_run.py`. So a UDE would need its own version of the reframe, not an inherited one.

## 5. What this means for answering Jon

**Yes with conditions, and with the deliverable reframed from a recovery claim to an observing-system question.**

Not "not yet" and not a flat yes. The physics motivation is sound and it is not the thing our evidence disputes. Iron source and sink processes really are poorly constrained, `alpfe` really is a global scalar on already-soluble Fe, and the scavenging sink really is the right place to put a learned term. What our evidence disputes is a specific claim nobody has actually made yet, which is that a learned scavenging closure will come out *identifiable* on the data we have.

`STATUS.md:496` already states the correct role and it should not be softened: the UDE at real scale is a **forward / OSSE tool** for asking which new observations would break the limit, not an identifiability rescue.

### The four preconditions

**P1. Pre-register the excitation, and gate on aliasing, not span.** Before any training, state the DFe log-span the forcing will drive the trajectory through, dump it, and run `scripts/symbolic_distill_probe.py --npz --kind monod`. The pass criterion is the Monod-vs-linear aliasing correlation falling below 0.95. **Do not use 0.30 dex.** That is the calcite branch's number, and 0.311 dex has already failed on aliasing 0.9908 with a held-out R2 of 0.99999999. Our own probe cleared aliasing near 1.8 dex. This check is CPU-cheap and can veto an expensive fit before it launches.

**P2. Name the real absolute anchor and count the observations.** Anchors-only already collapses `scav_rat` to 0/50 and the joint trio to 0/50. The iron budget is 4 co-located eqpac particulate-plus-dissolved pairs and 76 globally, over a 2.594-dex ratio range. If the answer to "what identifies this closure" is "the trajectory fit", P1 has already told us that is a trajectory-learner, not a law-learner.

**P3. Ship both nulls from day one.** The architecture-matched untrained-closure baseline is nearly free because of the zero-init anchoring, and it should be automatic: add an epoch-0 `record` call before the training loop in `trainer.py` so every closure fit logs its own untrained score. Separately, build the **permutation null through the rollout**, which is the genuinely missing control and the true analogue of the measured chance rate. `_perm_p` at `marsh_identifiability_map.py:117-127` is the pattern to copy. Match the R2 convention: `record` uses `masked_r2` (`trainer.py:248`) while the E2 headlines `anomaly_masked_r2`, and they are not comparable.

**P4. Build the harness, honestly labelled.** There is no iron E2 runner and `ScavClosure` has never been fit to real data. That is not a blocker, it is the first deliverable, and it must go through `transport.py` because `carroll6_ude_tendency` has no scav hook. Note that `held_out_iron_obs` (`held_out_obs.py:557`) already exists and its own docstring frames the result *as the counterexample*: a held-out iron R2 above zero need not mean a meaningful `scav_rat`, because iron concentration under-constrains the scavenging rate.

### One framing note for anything shown to Jon

Present this as "the hypothesis" and "the evidence says", not as a rebuttal of his suggestion. The honest headline is not "your idea fails". It is: **we already ran a small version of this and learned exactly what binds, which means we can design the real one properly instead of discovering it after burning cluster time.** The 2026-07-21 stress test and the E2 are gifts to this proposal, not objections to it. Also drop the phrase "parameter recovery should be a config change, not a research project" from any reuse of the 2026-05-21 brief. That sentence is the one that most directly licenses "a UDE is just more of the same."

## 6. Concrete next steps, ranked

Costs are wall-clock estimates. GPU estimates are flagged where the underlying timing figure is soft.

| # | Step | Cost | Why it ranks here |
|---|---|---|---|
| 1 | **Apply the 2026-07-19 replacement to `docs/ecco_darwin_parameter_inventory.md:64`.** The text is already written at `2026-07-19_doc_claim_sweep.md:703-705`. Also scope `:66` to cost, fix `dinn_design.md:16` "60+" to "~103" plus one clause that removing cost does not make a parameter identifiable, and import the `docs/index.md:7` hedge into `:96`. | ~30 min, one PR | The only tracked sentence a referee can cite as an unsupported scaling claim. It is nine days past its own audit. Highest value per minute in this list. |
| 2 | **Land the uncommitted registry work through a PR, and make `verify_run.py` registry-driven while it is already open.** Derive `PARAMS` and `CARROLL` from the registry, make the malformed-input check reject extra keys, and add the gate to the `CONTRIBUTING.md` add-a-parameter checklist. | 3 to 5 hours plus bot review | The reframe in section 4 is not citable until this exists in a reviewed state. Right now it lives in an uncommitted working tree on `main`, and both supporting evidence docs are untracked. |
| 3 | **Propagate the `diatomgraz` 35/50 caveat** to `STATUS.md:68` and `:275`, `docs/index.md:32`, `docs/agu26_abstract_draft.md:64` and `:75`. Note explicitly that the separate `geo1+MLD` **10/10** result stands at P = 0.021 and `STATUS.md:300` already carries it as the headline verdict. Do not let this read as "diatomgraz is dead". | ~1 hour | A refuted number is currently live in the AGU abstract draft. Fix before it is submitted. |
| 4 | **Fix the numeric record.** "~600-parameter" to **353** in `2026-07-10_e2_powered_result.md:23` and `2026-07-09_symbolic_distillation_identifiability_oracle.md:93`. "~454 weights, SST-only" to **406** in `STATUS.md:434`, `ONBOARDING.md:68`, `dinn_design.md:47` and `:140`, `ecco_darwin_relationship.md:63` (already flagged open at `2026-07-21_manuscript_redteam.md:77`). "~438 weights" to **142** in `scripts/synthetic_signflip_control.py:95`. `DINNDeep` "~8.5K" to **9,382**. | ~1 hour | Capacity-versus-n_train is the whole argument in two of those paragraphs. The number should be right. |
| 5 | **Add an epoch-0 `record` in `train_ude_closure`** before the loop, using the same R2 convention as the headline metric. | ~3 lines plus one extra rollout per fit | Makes every closure fit ship its own untrained baseline automatically, which is the structural analogue of making `NB23_LR=0` a default rather than an opt-in job. |
| 6 | **Iron support scout.** Wire `gather_visited_support` / `dump_support_npz` (currently exercised only in `tests/test_symbolic_distill.py:209-227`, with no `support_*.npz` anywhere on disk), dump the DFe visited support under the intended forcing, and run the Monod branch of the oracle. Report the aliasing correlation, not the span. | CPU, minutes to run; a few hours to wire | This is the cheap veto. It answers "is an iron UDE identifiable in principle under this forcing" before any GPU is booked. It is the single highest-information experiment on this list. |
| 7 | **Permutation null on the E2.** Add `--n-perm K` to `e2_real_calcite_eqpac.py`, shuffling the target over covered cells and refitting the identical closure at identical hyperparameters. | K x one E2 fit. Hours on a GPU at K=200 (**estimate is soft**: the "~1 s fwd+bwd on H200" figure at `e2_real_calcite_eqpac.py:44` describes the synthetic twin, and the E2 of record ran on a 5090 at 200 epochs x 3 kh rungs) | Turns "learned lost to the null" into "learned lost to the null, and here is the distribution of deltas 353 free weights get on 6 cells from noise." |
| 8 | **Bring the 10-seed E2 ensemble onto `main`** from commit `5199d90` on `overnight/2026-07-10-experiments`, and resolve the contradiction inside it (the JSON config says `calcite_source: daniels`, the scored markdown prose says Marsh). Also note `n_full_pass: 0` is out of `n_ladder_seeds: 1`, so delta<0 is genuinely 10/10 but the two-criterion pass was evaluated once. | Cherry-pick plus one afternoon of reconciliation | The manuscript should not cite a number whose artifacts are off-main and internally inconsistent. |
| 9 | **If the UDE proceeds: build `e2_real_iron_*.py`**, mirroring the calcite runner but through the transport path, pre-registered as an OSSE with P1 to P3 already satisfied. | Days | Gated on step 6 returning a passing aliasing verdict. If step 6 fails, this becomes a forcing-design task instead, which is the correct and cheaper outcome. |

**Sequencing note (inference, not measured):** steps 1, 3 and 4 are pure doc hygiene and can go in one PR today. Step 6 should start before any commitment is made to step 9, because it is the only item that can change the answer to the UDE question at near-zero cost. Steps 7 and 8 matter for the manuscript but not for the Jon conversation.