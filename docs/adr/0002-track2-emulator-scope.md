# ADR 0002 — Track-2 emulator scope (neural-operator ECCO-Darwin carbon emulator)

> **Note (2026-06-27):** references below to a "5/6 ceiling / 5-6 done" and to ADR-0001 as a live "calcite port" path reflect the **superseded** 6/6-chase framing — the project is a surrogate-to-model identifiability study over 4 observable params, and ADR-0001 is REJECTED (R_PICPOC recovers via a real anchor). The **Track-2 emulator design itself is unaffected** by that correction.
>
> **Track-2 status (2026-07-05):** feasibility has been demonstrated only on the 0-D box as a synthetic self-twin (transport-free) — this is NOT real Darwin and nothing runs beyond synthetic self-twin probes. The real-scale emulator below is unbuilt; its make-or-break gate is **E2 — held-out real-data R² > 0 once transport is present**, which turns the consistency-check into a discovery. Do not describe Track-2 as having "made Darwin differentiable" or "learned real biology" — results to date are synthetic self-twin.


- **Status:** Proposed
- **Track:** 2 (neural surrogate emulator) — distinct from Track-1 parameter recovery (the surrogate-to-model identifiability study, paper #1; see STATUS.md — ADR-0001 is the REJECTED calcite-port record, not the study scope)
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
- Cleanly separates the deliverables: **paper #1 = Track-1 identifiability** (laptop/H200; the surrogate-to-model identifiability study, scientifically complete and in hardening/write-up); **paper #2 = the emulator** (B200, the leapfrog).

### Risks / what could fail
- **Autoregressive drift** — month-to-month errors compound over decadal rollouts (the central emulator risk). Mitigation: rollout-in-the-loss (multi-step training), spectral/energy diagnostics.
- **Non-conservation** (#7) — may force a hard projection layer, complicating the operator.
- **OOD extrapolation failure** (#6) — a pure NN may revert to climatology under perturbation; may need physics-informed terms (the "mechanistic vs pure-NN" tension is the research result either way).
- **Grid** — LLC→lat-lon binning loses the native tiling; polar wrap needs SFNO or careful padding.
- **Data volume** — global monthly multi-decadal fields are large; the B200 onboarding + `/projects/schultz` 1.5 TB cap constrain dataset construction.

## Implementation plan (phased, test-gated; mirrors the Track-1 discipline)

**The whole build is gated on Paper #1 (Track-1) shipping.** Riskiest-assumption-first: the two unproven gates below decide whether the global operator is worth building at all, and come *before* any global pipeline.

0. **Riskiest-assumption-first transport probe (real data).** Before any global operator, fit a minimal real-data transport UDE (1-D column / minimal 2-D, driven by ECCO-Darwin's own velocities) to real GEOTRACES iron + calcite, held-out scored. *Gate 1 (make-or-break, E2): does adding transport close the surrogate gap on real data (held-out R² > 0) with sparse obs (~14 iron cells)?* Then a physical-backbone differentiability probe (Samudra-coupling). *Gate 2: do gradients flow through a real physical backbone into the BGC UDE?* Only after both gates pass proceed to the global build (steps 1–6, the Phase-3+ full-build path).
1. **Dataset pipeline.** v05 monthly → regular-grid (state, forcing) → (next-state) pairs; train/val split by time. *Gate: a CPU smoke test on a few months.*
2. **Single-step operator (Phase 1).** Train FNO for $s_t,f_t \to s_{t+1}$; report held-out one-step skill. *Gate: beats persistence + climatology.*
3. **Autoregressive rollout.** Free-run for years; measure drift + the conservation diagnostic (#7). *Gate: stable multi-year rollout; drift quantified.*
4. **Conservation** (if needed) — penalty/projection; re-measure. *Gate: drift < tolerance.*
5. **Perturbation test (#6).** OOD forcing vs mechanistic baseline. *Gate: physical perturbation response.*
6. **Scale** to LLC270 on the B200; Phase-2 biology.

## Open questions for Jon + literature to validate (before B200 hours)
- Which carbon fields are the **scientifically load-bearing** emulator targets (surface CO2-flux + DIC/ALK vs full 3-D tracer set)?
- Conservation: soft penalty vs hard projection — what's acceptable for the science claim?
- **Literature to mine** (a focused survey, like the Track-1 lit loop): neural operators for ocean/climate emulation, **conservation-constrained** NN emulators, autoregressive **rollout-stability** methods, and any prior ocean carbon-cycle emulator — to validate the operator + conservation choices *before* committing B200 time. Backbone survey grounded (2026-07-05): Samudra 2 ([arXiv:2606.02610](https://arxiv.org/abs/2606.02610)) is the best backbone but worsens the sparse-obs identifiability tension; SamudrACE ([arXiv:2509.12490](https://arxiv.org/abs/2509.12490)) names an explicit biogeochemistry hole = our Option-C carbon-BGC-UDE slot; ACE2 = atmosphere-only (no carbon); OlmoEarth = poor fit. Still to mine: conservation-constrained + rollout-stability methods specifically.

## Prior art — climate & ocean emulators to follow (survey seed)

*Captured 2026-07-01 as forward-looking reference for Track 2; implementation later. These are the state-of-the-art AI ocean/climate emulators whose architectures, rollout-stability tricks, and coupling paradigms the DarwinDiff carbon emulator should follow.* **Key gap they all share: every one emulates the *physical* ocean/climate state (T/S/SSH/velocity, atmosphere) — none emulate ocean *carbon / biogeochemistry* (DIC/ALK/air–sea CO₂ flux). That whitespace is exactly Track 2's target** (corroborates the Earth-2/PhysicsNeMo audit above).

| Model | What it emulates | Architecture | Key result / lesson for us | Ref · license |
|---|---|---|---|---|
| **Samudra** (Dheeshjith et al. 2024) | Ocean component of a climate model (GFDL OM4 / MOM6) — SSH, u/v, T, S, full depth | **Modified ConvNeXt U-Net** (not FNO), multi-depth | First autoregressive global ocean emulator stable for **centuries**, **~150× faster**; but *struggles to match forcing-trend magnitude while staying stable* — the core skill-vs-stability tension | [arXiv:2412.03795](https://arxiv.org/abs/2412.03795) · [GRL 2025](https://doi.org/10.1029/2024GL114318) |
| **Samudra 2** (Yuan et al. 2026) | Same ocean state, **scaled across resolutions** | Wider ConvNeXt U-Net + **dynamic loss reweighting channels by error** | **Scaling recipe** the user flagged: 1° → ½° → ¼°, ~8-yr rollouts, recovers mesoscale eddies + western boundary currents; upper-ocean T R² 0.56→0.87, deep-ocean error ~7× lower. Fixes Samudra's two failure modes — **variance collapse** + **imprinting** (velocity leaking into deep fields) — which are directly our autoregressive-drift risk (#7) | [arXiv:2606.02610](https://arxiv.org/abs/2606.02610) · CC BY 4.0 |
| **SamudrACE** (Ai2 + NYU 2025) | **Coupled** ocean + atmosphere + land + sea-ice — emulates GFDL **CM4 piControl** | **Coupler linking Samudra (ocean) + ACE2 (atmos/land)**, fine-tuned; 145 2-D fields, 8 atmos + 19 ocean levels | **Coupling paradigm**: independently-trained emulators joined via a coupler → **1500 sim-yr/day on one H100**. Template for a *modular* carbon emulator that plugs onto a physical-ocean emulator. piControl-only (no future-climate generalization). HF `allenai/SamudrACE-CM4-piControl`; needs Ai2 `fme≥2025.10`; code `github.com/ai2cm/ace` | [arXiv:2509.12490](https://arxiv.org/abs/2509.12490) · Apache-2.0 |
| **ACE2 / ACE2S** (Ai2) | Atmosphere + land (the atmospheric half of SamudrACE) | Spherical FME emulator | The atmosphere partner already coupled in SamudrACE; ACE2 is atmosphere-only (no carbon cycle) — a backbone/coupling reference for a future Track-2 build, not an existing benchmark | [arXiv:2606.07928](https://arxiv.org/abs/2606.07928) |
| **Neural-BGC** (Ouala & Lachkar 2026) | Ocean BGC — **DO / NO₃ only, regional** (ROMS + NN) | Regional NN closure | Closest existing *biogeochemistry* emulator; **DarwinDiff differs = carbon (DIC/ALK/CO₂ flux) + global + multi-decadal** | [essoar](https://doi.org/10.22541/essoar.15002003/v1) |

### Portability target — attach to NVIDIA earth2studio

The goal is a **portable ocean-carbon emulator that attaches to [earth2studio](https://github.com/NVIDIA/earth2studio)** (Apache-2.0), NVIDIA's inference framework for AI weather/climate models. Two facts make this concrete:

- **The interface is already scaffolded.** `src/darwindiff/emulator.py` mirrors earth2studio's **prognostic-model contract** (`input_coords` / `output_coords` / `step` / `create_iterator`) and the PhysicsNeMo `Module` base, import-guarded so those are cluster-only deps. An earth2studio prognostic model is exactly our autoregressive `s_{t+1} = G_θ(s_t, f_t)` — their weather models step ~6 h; ours steps ~1 month.
- **earth2studio ships zero ocean/BGC models** (verified: all current models are atmospheric — global weather 0.25–1.5°, regional HRRR/StormCast). So a Darwin-carbon prognostic plugin is **net-new** in that ecosystem, and the differentiation target.

**Design signals for the operator choice.** The best global ocean emulators (Samudra lineage) use **ConvNeXt-U-Net on a regular lat-lon grid**, *not* FNO — worth weighing against the scaffold's FNO/AFNO/SFNO plan when the operator is picked. Samudra 2's **channel-reweighting loss** and Samudra's **forcing-trend-vs-stability** finding are direct inputs to our conservation (#7) and OOD-extrapolation (#6) success criteria. Two portability ecosystems to target: **NVIDIA earth2studio** (prognostic contract, already scaffolded) and **Ai2 `fme`** (the SamudrACE / ACE stack).

### PhysicsNeMo building blocks (the framework beneath earth2studio)

*Captured 2026-07-01 from NVIDIA's PhysicsNeMo docs; forward-looking reference for Track 2 — and possibly Track 1.* [PhysicsNeMo](https://github.com/NVIDIA/physicsnemo) (Apache-2.0, `pip install nvidia-physicsnemo`) is NVIDIA's modular Physics-ML framework that sits under earth2studio. It is deliberately **not all-or-nothing** — importable blocks to pull in where they help, which matches DarwinDiff's "keep the known physics, add ML only where uncertain" stance. The scaffold already subclasses its `Module` base.

| Module | What it is | DarwinDiff relevance |
|---|---|---|
| `physicsnemo.models` | Neural Operators (FNO/AFNO/SFNO), GNNs, Transformers, diffusion backbones | The emulator operator (scaffold already uses FNO from here) |
| **`physicsnemo.diffusion`** | Denoisers, noise schedulers, samplers, **multi-diffusion**; one trained model → ensembles, **inverse problems by posterior sampling**, inference-time physics constraints | **Both tracks.** Track-1 recovery *is* an inverse problem → diffusion **posterior sampling** would yield parameter *uncertainty* (posterior width = identifiability), a complement to the current point-estimate gradient descent. Track-2: carbon-uncertainty **ensembles** + constraint enforcement without retraining |
| `physicsnemo.sym` | Symbolic PDE residuals + physics-informed losses | The PINN drift term + the conservation penalty (#7) |
| `physicsnemo.distributed` | `torch.distributed`-based domain-parallel training | Scaling the emulator to native / global on the B200 |
| `physicsnemo.datapipes` · `physicsnemo.mesh` | GPU-first scientific data loading; GPU mesh processing | Native data loading (mesh is less relevant — we are on a lat-lon grid) |

**Why the diffusion angle is worth flagging.** NVIDIA's Earth-2 uses diffusion because "a single deterministic answer is not enough" — the same is true for ocean carbon (uncertainty *is* the result). For **Track 1**, reframing parameter recovery as posterior sampling would turn the identifiability study from "did the point estimate land near Carroll" into "how tightly is each parameter constrained" — exactly the question the study asks. Logged as a **future method option**, not a committed direction. Refs: [Diffusion API docs](https://docs.nvidia.com/physicsnemo/latest/) · [PhysicsNeMo blog](https://nvidia.github.io/physicsnemo/blog/) · [GitHub](https://github.com/NVIDIA/physicsnemo).

---

*Companion: ADR-0001 (Track-1 calcite port, REJECTED / SUPERSEDED — R_PICPOC recovers via a real calcite anchor, see STATUS.md). This is the Track-2 design; nothing here trains or touches a GPU until B200 onboarding + a Jon review of the targets/conservation choices.*
