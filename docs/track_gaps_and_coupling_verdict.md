# Per-track improvement gaps + the UDE↔emulator coupling verdict (2026-07-22)

A forward design pass (Fable design→adversarial-vet workflow, 9 agents) over all three tracks and the
proposed UDE↔emulator coupling, stress-tested against our measured ceilings (E2 negative, emulator 1-step
information limit, single v05 realization, rank-1 FeMIP null). The unifying result: **every track's
*science* ceiling is the same wall — information, not method or architecture** — so the honest wins are
defensibility/framing and forward-tool packaging, and the coupling is speed/scale infrastructure, not a
discovery engine.

> Two corrections to the raw agent output, applied here: **R_PICPOC is anchor-driven** — this session
> proved the flagship uses the real Daniels anchor (anchor-off control collapses it 50/50→6/50 epoch-matched at 2000 ep; 4/50 in the 1500-epoch run), so the
> stale "fits Darwin's own ratio" red-team claim is refuted. And the "multi-start identifiability array"
> below is the #152 keystone (per-AOI Fisher + n-start profile-likelihood).

---

## Track 1 — parameter learner · verdict: REFRAME (at its *recovery* ceiling, not its *defensibility* ceiling)

The box is tuning-exhausted (168 ablations); full-box EKI confirmed estimator-independence. No *box*
knob recovers a new parameter (the one exception is a DINN **input** channel — MLD recovers
diatomgraz; see below) — the wins are the manuscript spine.

**Build first — the multi-start identifiability array (#152, the keystone).** n-start profile-likelihood +
per-AOI Fisher across the 4 observables. Read off, robustly across restarts, **structural** (flat profile
AND persistent zero-FIM eigenvalue) vs **practical** (bounded by data/weighting) for each. This is the one
test that can flip a conclusion: it **heals the self-inflicted diatomgraz wound** (we must not cite its
FLAT profile as structural non-identifiability — alpfe is FLAT too and recovers 49/50 at n=50). That
wound is now closed by measurement rather than reclassification: adding an **MLD input channel** takes
diatomgraz from ~4/10 (chance) to 10/10, and to 35/50 per-AOI with the biogenic-silica diagnostic off,
so it is *recoverable* from a non-circular model-internal observable — not from independent real data.
Cheap, no new data.

**Then write the four framing items as reporting of settled results:**
1. **Raue structural-vs-practical taxonomy** as the paper spine — reframes every other result.
2. **Menemenlis one-at-a-time-vs-joint degeneracy demo** — a figure showing alpfe and scav_rat each recover
   *alone* but collapse *jointly*, posterior aligned to the analytic sloppy direction (EKI already gives
   ⟂-to-sloppy ≈ 1.000). The load-bearing rebuttal to "why not 6/6."
3. **KOH model-discrepancy δ as a measured object** — instrument and *report* the 0-D-box↔full-Darwin
   discrepancy per parameter/observable as a number (caption it strictly as an identifiability-cost
   quantity, not a fidelity metric).
4. **Per-AOI honesty fix** — report the honest per-AOI joint (25/50) next to the cell-weighted 33/50, with
   the eqpac-alone + anchors-only reruns (both done this session).

**Incremental rigor (bounded by the ~14-cell floor):** aeolian-supply-contrast GEOTRACES anchor selection,
to try to de-condition alpfe from the 10× real-iron up-weighting.

**Decisive test:** the multi-start array. Expected: alpfe + R_PICPOC identified, scav_rat *practically*
non-identifiable, and diatomgraz confirmed *practically* (not structurally) non-identifiable — the label it
already earned by measurement, since an **MLD input channel** recovers it 10/10 (35/50 per-AOI at n=50 with
the biogenic-silica diagnostic off, so it is not a bSi tautology; the Chl target is Darwin's own, so this is
model-internal, not independent real data). The 3-of-4 frontier is **structural** with **two** operating
points, not one: geo1 holds {alpfe, scav_rat, R_PICPOC}; an MLD channel plus a heavy Daniels weight holds
{alpfe, diatomgraz, R_PICPOC}. So the array itself recovers no new parameter;
the framing package carries manuscript #1 from ~70% to submittable.

---

## Track 2 — FNO emulator · verdict: REFRAME (at its skill/horizon ceiling)

Every architecture axis is exhausted (geometry-probe FLAT, capacity saturates +0.007, diffusion null, data
flat past n=55). The deliverable is a calibrated 1-step operator, not a work program.

**Build now (Tier 0, no retrain):** calibrate the parked 6-seed ensemble (`opt3d_seed{0..5}.pt`) as a
predictive distribution — per-cell mean+variance, score coverage/CRPS/spread-error, add variance inflation
if under-dispersed. This turns the parked model into an honest, error-barred **1-step differentiable OSSE
operator** — real, usable value in the correct (forward-tool) role.

**Characterize (cheap, confirm-not-lift):** rollout-test the Δt-scaled residual fix (measured only at
step 1) and publish its horizon curve; the physics-only vs BGC-inclusive attribution ablation to *localize*
the ceiling.

**The one go/no-go for "is there any science left here":** the **observation-densification test** — ingest
a shelved independent obs stream (satellite PIC / ocean-color, or an NO3/PO4 currency) as an input channel
on the existing FNO2d and measure whether it tightens the sloppy directions vs the self-twin baseline.
**Predicted flat/negative** (the single v05 self-twin has no independent information to add; shelved streams
correlate with the emulated fields). A positive, constraint-tightening result would reopen everything.

---

## UDE — differentiable transport + closures · verdict: REFRAME (at its *discovery* ceiling)

The make-or-break E2 gate returned **negative** (learned held-out anomaly-R² −0.73 vs null +0.33) and it
survives the kh correction. The closure is **trajectory-coverage-limited** (0.65% on visited dfe vs 288%
off-support; regularization a measured no-op) — the E2 negative is almost certainly a state-space-coverage
failure: real held-out cells fall *off* the manifold the single v05 trajectory excited.

**Build now — the paired-split rigor run** (one job, no new data/dynamics). Fold in a physically-stable kh
([#192](https://github.com/2imi9/ECCO-DarwinDiff/issues/192)), then run TWO held-out splits side-by-side on
the *same corrected operator*: (a) aeolian-supply-**matched** (on-support) and (b) aeolian-**imbalanced**
(train low-dust / test high-dust, off-support). *The vet caught that a matched split alone silently changes
the question* — a matched split guarantees test cells sit on trained support, so a positive there is a
near-tautology. Running BOTH separates split-artifact vs real-null vs coverage-ceiling.

**Mandatory hygiene:** the kh fix + re-done K_num control — reinforces the null, moves no science; never run
E2 on the broken operator again.

**Where new identifiability could actually come from (off-emulator):** excitation/forcing design to widen
the dfe trajectory band (`scripts/ude_forcing_design.py`); the macronutrient currency for the growth
degeneracy (a separate, data-blocked bet that does *not* rescue the iron-transport E2).

**Decisive test:** the paired-split run. Expected: off-support reproduces ~−0.73 vs +0.33 (null robust);
on-support moves learned toward/past null only because test cells now interpolate. Net — the E2 negative is
**confirmed and becomes publishable**, correctly attributed to trajectory coverage.

---

## The coupling · VERDICT: **KILL as a science bet; defer as infrastructure**

**Architecture adjudicated (three claimed couplings):**
1. **BGC-UDE + our FNO emulator = circular and dead.** The FNO already outputs PIC/POC/DIC/ALK/Chl1-5/DFe
   field→field — exactly what a BGC-UDE learns. Each side is the other's target; no shared identified
   parameter survives.
2. **The only non-circular form is Option-C** — a *physics-only* backbone (Samudra ConvNeXt-U-Net, or a
   physics-only FNO retrain with BGC channels stripped) supplies transport/forcing; our carbon-BGC-UDE
   advects DIC/ALK/PIC/POC/DFe(+macronutrient) under it, exposing Carroll params.
3. **But the UDE already does this** with v05's own analytic finite-volume transport on prescribed
   velocities — conservative to ~5e-6 out to 100k steps, differentiable, never blows up. Swapping in an
   emulator backbone **regresses** a fast/exact/conservative/differentiable operator for a non-conservative,
   1-step-ceilinged learned one, in exactly the many-step rollout regime the inversion needs.

**Science or speed/scale? Speed/scale only — full stop.** The binding constraint is *information*, upstream
of any forward model: single v05 realization, ~14 GEOTRACES iron cells, trajectory-coverage-limited closure,
estimator- and transport-independent rank-1 null. A faster/fancier forward cannot manufacture information the
observations don't contain — the E2 negative already proved transport doesn't close the surrogate gap on
real held-out data. The one thing the backbone genuinely adds is **velocities v05 does not contain**
(perturbed-climate / native-global scenarios) — an OSSE / observing-system-design capability, not an
identifiability one.

**Gaps that must be filled before any coupled build (all currently red):** (1) circularity — needs a
physics-only backbone; (2) conservation — an emulator backbone needs a flux-form/conservation-projection
corrector just to reach parity with the transport it replaces; (3) multi-step gradient quality — validated
only at 1 step, decadal backprop is unvalidated where the inversion needs it; (4) the E2 precondition is
**refuted, not open** — the plan's own rule fires: negative E2 → densify observations *before* any coupled
build.

**Single minimal test before any expensive build:** the **forward-model-swap holding the info budget
fixed** — on the SAME held-out real GEOTRACES/Daniels cells from the E2, replace the analytic-transport UDE
with an emulator-backbone UDE and compare held-out anomaly-R². Near-zero cost, no Samudra engineering.
**Predicted: identical negative R²** (the learned backbone at best matches, more likely underperforms, the
conservative analytic transport). Go/no-go = **no-go for the discovery build.** Do not stand up the Samudra
couple; the authorizing gate stays red.

---

## Bottom line

| track | science ceiling? | what can still move | forward-tool value |
|---|---|---|---|
| Track 1 | recovery yes, defensibility no | the identifiability classification (multi-start array + 4 framing items) → submittable paper | — |
| Track 2 emulator | yes (structural, 1-step) | packaging: a calibrated 1-step OSSE operator | observation-network design |
| UDE | yes (E2 negative robust) | reporting rigor (defensible, coverage-attributed null) | mass-conserving observing-system-design instrument |
| coupling | yes, before it was built | — (Phase-1 gate failed) | deferrable speed/scale for scenario velocities v05 lacks |

**The unifying diagnosis:** all four ceilings are the *same wall* — information (single v05 realization +
~14 iron cells + rank-1 null + trajectory coverage). Five independent estimators and every forward-model
choice hit it identically.

**The one thing that would most change the trajectory:** break the information monopoly of the single v05
self-twin — add real, independent absolute observations that densify/diversify the ~14-cell floor. In
priority order: (1) aeolian-contrast anchor selection to wring maximum excitation from existing GEOTRACES
iron; (2) genuine obs densification (additional real iron cells, or a macronutrient NO3/PO4 currency staged
against WOA/GLODAP — honest ceiling: it constrains *total* growth, not the Smallgrow/Biggrow split, so it
likely identifies a growth *combination*, a follow-on-paper build). Absent new information, all three tracks
are correctly at their science ceilings, and the coupling stays shelved.
