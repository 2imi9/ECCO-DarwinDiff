# ADR 0002 — Track-2 emulator scope (neural-operator ECCO-Darwin carbon emulator)

- **Status:** Proposed
- **Track:** 2 (neural surrogate emulator) — distinct from Track-1 parameter recovery (ADR-0001, paper #1)
- **Research questions:** [#6](https://github.com/2imi9/ECCO-DarwinDiff/issues/6) (mechanistic vs pure-NN extrapolation under climate perturbation), [#7](https://github.com/2imi9/ECCO-DarwinDiff/issues/7) (mass conservation at decadal rollouts)
- **Compute:** NU AICR **B200** (192 GB, sm_100; onboarding ~early July 2026); dev on the free Explorer **H200**
- **Date:** 2026-06-24

---

## Context — why this, why now, why the B200

Track-1's validation loop established that parameter recovery is **launch-bound** (a single fit is the same wall-clock on 5090/H200/B200) and that R_PICPOC is not a compute problem. So the B200's throughput/memory is **wasted on Track-1**. Its genuine use is **Track 2**: a neural-operator emulator of ECCO-Darwin's ocean-carbon dynamics for **long-timescale (multi-decadal) carbon-storage and climate-perturbation runs** — the workstream Jon flagged as his deep interest, and the one that actually needs global-scale data + a large operator model trained at throughput.

**What already exists.** `src/darwindiff/emulator.py` is a CPU-unit-tested **scaffold**: a self-contained Fourier Neural Operator (`FNO2d`) and a `DarwinEmulator` that already mirrors the **PhysicsNeMo `Module`** base and the **Earth-2 Studio prognostic contract** (`input_coords` / `output_coords` / `step` / `create_iterator`), import-guarded so `physicsnemo` / `earth2studio` become dependencies only on the cluster. The interface is done; the operator-learning run is not.

**Whitespace (verified, memory: Earth2/PhysicsNeMo audit 2026-06-14).** Zero ocean-BGC models exist across the Earth-2 / PhysicsNeMo stack (cBottle is atmospheric, not carbon). The closest published work, the neural-BGC emulator of Ouala & Lachkar (2026, ROMS+NN), emulates **DO/NO3 only, regionally**. A **global, multi-decadal ocean-carbon** emulator (DIC/ALK/air-sea CO2 flux) is open ground and the differentiation target.

## Decision — scope of the emulator

### Goal
Learn an operator $G_\theta$ that advances the ocean-carbon state one month under ECCO physical forcing, $\;s_{t+1} = G_\theta(s_t, f_t)$, accurate enough to **roll out autoregressively for decades** and reproduce ECCO-Darwin's carbon storage and its response to perturbed forcing.

### State and forcing (staged)
- **Phase 1 — surface carbon system, 2-D.** Predict $s=\{\mathrm{DIC},\mathrm{ALK},\mathrm{pCO2},\mathrm{CO2\_flux}\}$ from $s_t$ + physical forcing $f=\{\mathrm{SST},\mathrm{SSS},\mathrm{MLD},\mathrm{wind},\mathrm{ice},\mathrm{apCO2}\}$ (the bin_average variables we already hold). Cheapest path to test rollout stability + conservation.
- **Phase 2 — add the biological pump.** Include the limiting drivers (FeT, NO3, Chl/NPP, POC export) so DIC is driven by biology, not just solubility. 3-D (depth-resolved) is Phase 2b.
- Targets are ECCO-Darwin v05 monthly fields (1992–2017+), binned to a regular **lat-lon** grid (`bin_native_tracer_to_1deg`); the LLC tile grid is not FNO-native.

### Operator
- Start with the scaffold **FNO** (`physicsnemo.models.fno.FNO` when available); evaluate **AFNO** (scales to higher resolution) and a **spherical** variant (SFNO, as Earth-2 uses) for the global wrap. **Resolution: LLC90 / 1° start (per Jon), scale to LLC270.**

### The two research questions are the success criteria
- **#7 Conservation.** A pure operator need not conserve carbon. Decision: **diagnose first** (measure global DIC+ALK inventory drift over a decadal rollout), then add a **soft conservation penalty** or a **projection layer** if drift exceeds tolerance. *Success: inventory drift < \TODO{X}% over \TODO{N}-yr rollout.*
- **#6 Extrapolation.** Train on the historical period; test under **perturbed forcing** (e.g. +CO2 / warming scenario) **out of the training distribution**, against a mechanistic baseline. *Success: the emulator's perturbation response stays physical (sign + order-of-magnitude vs the parent model) rather than reverting to the training climatology.* This is the hybrid-vs-pure-NN question.

### Compute / deps
- **Dev on H200** (no idle-reaper); **scale training on B200** (batched + compiled, sm_100). Install `physicsnemo` + `earth2studio` on the cluster (the scaffold is import-guarded for them). \TODO{dataset size + training-cost estimate once Phase-1 tensor shapes are fixed.}

## Consequences

### Positive
- Fills a **verified whitespace** (no ocean-carbon emulator in Earth-2/PhysicsNeMo); differentiates from Ouala & Lachkar (carbon + global + decadal vs DO/NO3 + regional).
- The B200's throughput/memory is finally the *right* tool (unlike Track-1).
- Cleanly separates the deliverables: **paper #1 = Track-1 identifiability** (laptop/H200, now); **paper #2 = the emulator** (B200, the leapfrog).

### Risks / what could fail
- **Autoregressive drift** — month-to-month errors compound over decadal rollouts (the central emulator risk). Mitigation: rollout-in-the-loss (multi-step training), spectral/energy diagnostics.
- **Non-conservation** (#7) — may force a hard projection layer, complicating the operator.
- **OOD extrapolation failure** (#6) — a pure NN may revert to climatology under perturbation; may need physics-informed terms (the "mechanistic vs pure-NN" tension is the research result either way).
- **Grid** — LLC→lat-lon binning loses the native tiling; polar wrap needs SFNO or careful padding.
- **Data volume** — global monthly multi-decadal fields are large; the B200 onboarding + `/projects/schultz` 1.5 TB cap constrain dataset construction.

## Implementation plan (phased, test-gated; mirrors the Track-1 discipline)
1. **Dataset pipeline.** v05 monthly → regular-grid (state, forcing) → (next-state) pairs; train/val split by time. *Gate: a CPU smoke test on a few months.*
2. **Single-step operator (Phase 1).** Train FNO for $s_t,f_t \to s_{t+1}$; report held-out one-step skill. *Gate: beats persistence + climatology.*
3. **Autoregressive rollout.** Free-run for years; measure drift + the conservation diagnostic (#7). *Gate: stable multi-year rollout; drift quantified.*
4. **Conservation** (if needed) — penalty/projection; re-measure. *Gate: drift < tolerance.*
5. **Perturbation test (#6).** OOD forcing vs mechanistic baseline. *Gate: physical perturbation response.*
6. **Scale** to LLC270 on the B200; Phase-2 biology.

## Open questions for Jon + literature to validate (before B200 hours)
- Which carbon fields are the **scientifically load-bearing** emulator targets (surface CO2-flux + DIC/ALK vs full 3-D tracer set)?
- Conservation: soft penalty vs hard projection — what's acceptable for the science claim?
- **Literature to mine** (a focused survey, like the Track-1 lit loop): neural operators for ocean/climate emulation, **conservation-constrained** NN emulators, autoregressive **rollout-stability** methods, and any prior ocean carbon-cycle emulator — to validate the operator + conservation choices *before* committing B200 time. \TODO{run this survey.}

---

*Companion: ADR-0001 (Track-1 calcite port, BLOCKED). This is the Track-2 design; nothing here trains or touches a GPU until B200 onboarding + a Jon review of the targets/conservation choices.*
