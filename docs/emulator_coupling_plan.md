# Plan — Coupling the parameter learner to an Earth-2 ocean(-carbon) emulator

*Drafted 2026-07-03. Staged, riskiest-assumption-first build plan; multi-month and GATED ON PAPER #1
SHIPPING. Nothing is committed until the Phase-0 architecture gate + a Jon review. The scaffold/wrapper
step is laptop-doable now, but the first SCIENTIFIC gate (gate 1 / E2) is a minimal real-data transport
UDE — a regional 2-D fit to real GEOTRACES iron + calcite, held-out scored — which tests whether
transport closes the surrogate gap on real data. Most downstream work is B200/cluster-gated.*

## 0. Why now — Track-1 is complete and its surrogate-gap finding forces the move off the box

Track-1 (the 0-D box parameter learner) is **scientifically complete**: a surrogate-to-model
identifiability study, not an in-progress recovery chase. Its central load-bearing FINDING is what
forces the move off the box — **the surrogate gap**: the 0-D box homogenizes (no circulation), so its
held-out real-data R² is *negative*. Identifiability can therefore only come from real absolute anchors,
and box-only recovery is a *consistency check against Carroll's own values, not a cross-validated
discovery*. That is a finding that bounds the claim, not a flaw — and it is precisely why a
spatial/transport model is needed to attempt discovery.

The 2026-07-03 exhaustive audit ([Ablation Ledger](archive/ablation_ledger.md), 168 distinct
ablations) corroborates this: **the estimator / loss-weighting / box-structure optimization space is
exhausted** (~0 more tuning experiments worth running; every ceiling-breaker refuted — the ceiling is
the 0-D box surrogate). The remaining levers are **not more tuning** — and the highest-value ones point
off the box:

- **The macronutrient (NO3/PO4) currency** is one such box-enrichment lever: an iron-only box is the
  anomaly, and a real macronutrient tracer + drawdown loss is the lever most likely to break the
  Smallgrow↔Biggrow growth degeneracy and loosen the alpfe loss-weighting weld. It can be tested two
  ways — (a) as a cheap Track-1 box enrichment (data-staging-blocked) or (b) as native structure inside
  the Track-2 UDE — and **this plan is about (b)**: a richer *differentiable model*, not a loss tweak.
- The other remaining wins (dense POSi, native primProd, a small-phyto gyre AOI, an n≥20 tie-break, real
  MODIS obs/obs ratio) are data-staging or marginal.

**So the natural home for the spatial calcifier + macronutrient structure a 0-D box cannot carry *is*
the coupled UDE emulator** — a differentiable model calibrated by the parameter learner. Its role is
NOT to resurrect a "6-param recovery": Track-1 already settled which Carroll params are observable
(alpfe — method-independent / mass-balance; scav_rat — needs per-cell, weakest; R_PICPOC — via a real
calcite anchor, though a single global value is under-constrained and should vary regionally; diatomgraz
is unobservable from staged data; the growth pair is unobservable by construction). Its role is Track-2
**discovery**: whether adding transport turns the box's consistency-check into a cross-validated result.
The ledger's strategic exit is that higher-dimensional differentiable-BGC UDE. What is feasibility-proven
so far is only that the UDE machinery recovers a KNOWN synthetic closure on the 0-D box (self-twin,
transport-free: iron curve ~0.5 %, spatial field ~0.44 % MAE) — this is "the technique works on the box,"
**not real Darwin and not learned real biology**.

**Framing note:** paper #1 is hardened, 8-lens red-teamed, and has an n=50 ensemble folded (numbers being
finalized at 2000 epochs); independent cross-method validation (#163) is addressed (PRs #172/#173). The
data-staging wins above are Track-1 enrichments that remain data-blocked, but they do NOT gate the
Track-2 build described here.

## 1. Architecture decision (PHASE-0 GATE)

| Option | Core | Param learner couples? |
|---|---|---|
| A — Pure black-box | Samudra ConvNeXt-U-Net **or** PhysicsNeMo FNO | **No** — no shared params |
| B — Full UDE | Build our own differentiable physical ocean + BGC | Yes, but we build the hard part |
| **C — Hybrid (recommended)** | **Samudra = physical ocean** (T/S/SSH/velocity) **+ our carbon-BGC UDE** (DIC/ALK/PIC/POC/Fe/Chl **+ macronutrient**, exposing Carroll params) | **Yes** — learner calibrates the carbon module; Samudra supplies transport/forcing |

**Recommend Option C.** Samudra does the SOTA physical ocean we can't; the **ocean-carbon layer is the
verified whitespace** we build as a UDE the parameter learner calibrates — and it's where the
macronutrient currency lives. SamudrACE already proved the couple-two-emulators-via-a-coupler pattern.

**Backbone survey (grounded):** Samudra 2 (arXiv 2606.02610) is the eddy-resolving physical-ocean
backbone we want, but higher resolution *worsens* the sparse-obs identifiability tension (more cells,
same ~14 GEOTRACES iron obs). SamudrACE (arXiv 2509.12490) is differentiable coupled atmosphere-ocean
physics with an EXPLICIT biogeochemistry hole named as future work — that hole is exactly our Option-C
carbon-BGC-UDE slot. ACE2 is atmosphere-only (no carbon cycle); OlmoEarth is land/coastal EO, a poor
fit. (ADR-0002's prior-art table carries the fuller comparison.)

Clarification: *Samudra(2) is ConvNeXt-U-Net, not FNO.* Borrow Samudra's U-Net for the physics; build
the carbon core as a **UDE** (so the learner can calibrate it); FNO only if a learned sub-closure needs
an operator.

## 2. Code to acquire (all permissive)
- [NVIDIA/earth2studio](https://github.com/NVIDIA/earth2studio) (Apache-2.0, `pip`) — pipeline + Prognostic/Diagnostic contracts
- [NVIDIA/physicsnemo](https://github.com/NVIDIA/physicsnemo) (Apache-2.0) — `Module`, FNO, `diffusion`, `sym`, `distributed`
- [m2lines/Samudra](https://github.com/m2lines/Samudra) + [HF weights](https://huggingface.co/M2LInES/Samudra) — thin adapter, don't fork, pin a commit

Scaffold already in-repo: `src/darwindiff/emulator.py` (`DarwinEmulator` Prognostic) + `src/darwindiff/networks.py` (`DINN`, already `env[C,H,W]→params[6,H,W]` — diagnostic-shaped).

## 3. Phased implementation (each = one work-chunk, test-gated)

**Order is riskiest-assumption-first.** The full Samudra-coupled 3-D UDE stacks two unproven gates:
(1) transport closes the surrogate gap on real data, and (2) gradients flow through a physical-emulator
backbone. Building the whole thing and *then* discovering gate 1 fails would burn months — so **Phase 1
tests gate 1 in isolation, cheaply, on real data**, before any Samudra engineering.

### Phase 1 (E2 gate) — shortest path to real-data validation
The make-or-break question is E2: **does adding transport close the surrogate gap on REAL data?** Fit a
spatially-structured, differentiable model to real observations, hold out a spatial fraction, and check
whether held-out R² goes **positive** at the unseen cells (the same metric that returned *negative* R² on
the 0-D box). Positive held-out skill = transport turned the consistency-check into discovery; negative =
the sparse-obs problem dominates and a richer forward model alone won't save it. Either outcome is a real,
cheap, publishable result.

- **Key shortcut — no Samudra needed for gate 1:** drive the probe with **ECCO-Darwin v05's own U/V/W
  velocities** (a GCM output we already have or can pull), giving real circulation-driven transport with
  zero emulator engineering. This isolates gate 1 (does transport help) from gate 2 (is the emulator
  couplable/differentiable). *Data prerequisite:* verify U/V(/W) are present in the v05 subset on disk;
  if not, pull them for the target AOI (regional, cheap).
- **Minimal model:** a regional 2-D (or 2.5-D) patch UDE — `∂C/∂t = −∇·(u_darwin C) + ∇·(K∇C) +
  R_carroll6(C,E;θ) [+ NN closure φ]` — differentiable finite-volume advection+diffusion on the AOI grid,
  reaction = the existing `carroll6_step` (reuse), parameters θ = Carroll-6 explicit (invertible by
  backprop), state at minimum DFe + POC/PIC.
- **Held-out protocol (this IS E2):** hold out ~30% of the AOI's real GEOTRACES iron (+ Daniels/MODIS
  calcite) cells, fit θ (and φ) on the retained cells by backprop through the transport+reaction rollout,
  score predicted DFe at the held-out cells → held-out R², apples-to-apples with the Paper #1 box test.
- **Compute:** regional patch, iron-first — **local 5090 or a small cluster job, days not months**; reuses
  `carroll6` + existing loaders + `verify_run`-style gating.
- ***Gate: held-out real-data R² > 0 (at least the iron field)*** → greenlight gate 2 (Samudra-coupling
  differentiability probe) and the full build below. **R² ≤ 0** → transport alone doesn't fix the sparse-obs
  wall (consistent with the native-resolution dilution finding) → **pivot to observation densification
  (PACE/MODIS)** *before* any expensive coupled build; the Samudra phases are deferred.

*(Full scope: `docs/track2_phase1_scope.md`. This Phase-1-E2 de-risks the science make-or-break before
the engineering of the emulator couple — it comes BEFORE the CarrollParamDiagnostic-wrapper scaffolding,
which serves the Samudra path.)*

### Phase 2+ — Samudra-coupled build (only if E2 passes)
2. **Earth-2-wrap (laptop):** `CarrollParamDiagnostic(physicsnemo.Module)` mirroring `DarwinEmulator`'s coord boilerplate; forward = DINN + `bounded_params`. Un-guard imports against a real install; define the shared global lat-lon CF `CoordSystem`. *Gate: pytest round-trip env→params in an earth2studio pipeline.*
3. **Samudra provider (cluster):** clone m2lines/Samudra, pull the HF checkpoint, reproduce a rollout, adapter → physical state (T/S/MLD/velocity) on our CoordSystem (regrid OM4 tripolar → lat-lon). *Gate: rollout reproduces.*
4. **Carbon-BGC UDE module (the new science):** port `carroll6_5pft_2layer` to a spatial Prognostic Module — carbon **+ macronutrient** state advanced under Samudra forcing + Carroll params; keep known physics as equations, learn only uncertain closures (calcite gate g(T,Ω_c)). *Gate: one-step skill beats persistence; carbon-inventory drift (#7).*
5. **Couple + calibrate:** compose `env → CarrollParamDiagnostic → DarwinCarbonPrognostic` (Samudra-forced) → decadal rollout; recover Carroll params by gradient descent **through** the coupled model, then run the make-or-break gate at scale: score held-out REAL-DATA R² at unseen cells. R² > 0 is the central UNPROVEN hypothesis that would turn the Track-1 consistency-check into a genuine discovery — *not* an assumed outcome. Two gates must both pass: (1) transport closes the surrogate gap on real data despite sparse obs (~14 GEOTRACES iron cells); (2) gradients flow through the real physical backbone to the BGC UDE. *Gate: held-out real-data R² > 0; stable multi-decadal rollout; #6 OOD test.*
6. **Uncertainty + scale:** `physicsnemo.diffusion` posterior over param fields → carbon ensemble; `physicsnemo.distributed` to native/global on B200.

## 4. Risks / open questions
- **Gate 1 (E2) is the make-or-break:** transport may not close the surrogate gap on real data given
  sparse obs (~14 iron cells) — a negative held-out R² pivots the plan to obs densification, not the
  Samudra couple. · Samudra OM4 tripolar grid vs our lat-lon (regrid fidelity). · The carbon-BGC UDE
  module (Phase 4) is the hard, unproven part. · Samudra output cadence/vertical vs carbon needs. ·
  Multi-month, B200-gated downstream (only Phase 1 is laptop/small-job-now), and the whole build is gated
  on Paper #1 shipping. · **Jon gate:** confirm Option C + the load-bearing carbon+macronutrient targets
  before B200 hours.

## 5. First task (concrete, small)
**Phase-1-E2**: verify v05 U/V(/W) are on disk for the target AOI, then stand up the regional 2-D
transport+reaction UDE and run the held-out real-data R² gate on iron (local 5090 / small cluster job,
`verify_run`-gated). This de-risks the science before any emulator engineering. The
`CarrollParamDiagnostic` wrapper + pytest round-trip is the first *Phase-2* scaffolding step and follows
only if E2 greenlights the Samudra path. Everything gates on Option C + Jon buy-in.

## Connects to
ADR-0002 (Track-2 emulator scope) — this is its concrete build path. Ablation Ledger (the #1
macronutrient lever). `docs/track2_phase1_scope.md` (full Phase-1-E2 scope). Memory:
`reference_earth2_physicsnemo_audit`; `feedback_track2_feasibility_not_realdata` (the UDE numbers above
are synthetic self-twin box results, not real Darwin / real-data — do not narrate them as "made Darwin
differentiable" or "learned real biology").
