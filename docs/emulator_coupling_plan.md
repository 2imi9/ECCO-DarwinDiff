# Plan — Coupling the parameter learner to an Earth-2 ocean(-carbon) emulator

*Drafted 2026-07-03. Staged build plan with decision gates — nothing committed until the Phase-0
gate + a Jon review. Most is B200/cluster-gated; Phase 1 is laptop-doable now.*

## 0. Why now — the macronutrient-currency finding forces the move off the box

The 2026-07-03 exhaustive audit ([Ablation Ledger](archive/ablation_ledger.md), 168 distinct
ablations) is decisive: **the estimator / loss-weighting / box-structure optimization space is
exhausted** (~0 more tuning experiments worth running; every ceiling-breaker refuted — the ceiling is
the 0-D box surrogate). The remaining high-EV levers are **not more tuning** — and the #1 of them
points straight off the box:

- **The macronutrient (NO3/PO4) currency is the root cause.** An iron-only box is the anomaly: adding a
  real macronutrient tracer + drawdown loss is the single lever that breaks *both* the Smallgrow↔Biggrow
  growth degeneracy *and* the alpfe loss-weighting weld. It is the #1 experiment left — and it is a
  **forward-model enrichment**, i.e. a richer differentiable model, not a loss tweak.
- The other remaining wins (dense POSi, native primProd, a small-phyto gyre AOI, an n≥20 tie-break, real
  MODIS obs/obs ratio) are data-staging or marginal.

**So the natural home for the #1 lever *is* the coupled UDE emulator** — a differentiable model rich
enough to carry macronutrient + spatial calcifier structure, calibrated by the parameter learner. The
audit's own strategic exit is *"Stage-3 honest 6-param recovery on the higher-dimensional
differentiable-BGC UDE"* (feasibility-proven: self-twin closures 0.5 %, spatial field 0.44 % MAE). This
plan builds that.

**Honesty caveat (unchanged):** two open Track-1 items are NOT coupling and harden paper #1 first —
independent cross-method validation (#163) and the data-staging wins above.

## 1. Architecture decision (PHASE-0 GATE)

| Option | Core | Param learner couples? |
|---|---|---|
| A — Pure black-box | Samudra ConvNeXt-U-Net **or** PhysicsNeMo FNO | **No** — no shared params |
| B — Full UDE | Build our own differentiable physical ocean + BGC | Yes, but we build the hard part |
| **C — Hybrid (recommended)** | **Samudra = physical ocean** (T/S/SSH/velocity) **+ our carbon-BGC UDE** (DIC/ALK/PIC/POC/Fe/Chl **+ macronutrient**, exposing Carroll params) | **Yes** — learner calibrates the carbon module; Samudra supplies transport/forcing |

**Recommend Option C.** Samudra does the SOTA physical ocean we can't; the **ocean-carbon layer is the
verified whitespace** we build as a UDE the parameter learner calibrates — and it's where the
macronutrient currency lives. SamudrACE already proved the couple-two-emulators-via-a-coupler pattern.

Clarification: *Samudra(2) is ConvNeXt-U-Net, not FNO.* Borrow Samudra's U-Net for the physics; build
the carbon core as a **UDE** (so the learner can calibrate it); FNO only if a learned sub-closure needs
an operator.

## 2. Code to acquire (all permissive)
- [NVIDIA/earth2studio](https://github.com/NVIDIA/earth2studio) (Apache-2.0, `pip`) — pipeline + Prognostic/Diagnostic contracts
- [NVIDIA/physicsnemo](https://github.com/NVIDIA/physicsnemo) (Apache-2.0) — `Module`, FNO, `diffusion`, `sym`, `distributed`
- [m2lines/Samudra](https://github.com/m2lines/Samudra) + [HF weights](https://huggingface.co/M2LInES/Samudra) — thin adapter, don't fork, pin a commit

Scaffold already in-repo: `src/darwindiff/emulator.py` (`DarwinEmulator` Prognostic) + `src/darwindiff/networks.py` (`DINN`, already `env[C,H,W]→params[6,H,W]` — diagnostic-shaped).

## 3. Phased implementation (each = one work-chunk, test-gated)
1. **Earth-2-wrap (laptop, now):** `CarrollParamDiagnostic(physicsnemo.Module)` mirroring `DarwinEmulator`'s coord boilerplate; forward = DINN + `bounded_params`. Un-guard imports against a real install; define the shared global lat-lon CF `CoordSystem`. *Gate: pytest round-trip env→params in an earth2studio pipeline.*
2. **Samudra provider (cluster):** clone m2lines/Samudra, pull the HF checkpoint, reproduce a rollout, adapter → physical state (T/S/MLD/velocity) on our CoordSystem (regrid OM4 tripolar → lat-lon). *Gate: rollout reproduces.*
3. **Carbon-BGC UDE module (the new science):** port `carroll6_5pft_2layer` to a spatial Prognostic Module — carbon **+ macronutrient** state advanced under Samudra forcing + Carroll params; keep known physics as equations, learn only uncertain closures (calcite gate g(T,Ω_c)). *Gate: one-step skill beats persistence; carbon-inventory drift (#7).*
4. **Couple + calibrate:** compose `env → CarrollParamDiagnostic → DarwinCarbonPrognostic` (Samudra-forced) → decadal rollout; recover Carroll params by gradient descent **through** the coupled model — *this is where the macronutrient currency finally does its job* and the surrogate gap closes. *Gate: stable multi-decadal rollout; params recovered; #6 OOD test.*
5. **Uncertainty + scale:** `physicsnemo.diffusion` posterior over param fields → carbon ensemble; `physicsnemo.distributed` to native/global on B200.

## 4. Risks / open questions
- Samudra OM4 tripolar grid vs our lat-lon (regrid fidelity). · The UDE carbon module (Phase 3) is the hard, unproven part. · Samudra output cadence/vertical vs carbon needs. · Multi-month, B200-gated (only Phase 1 is laptop-now). · **Jon gate:** confirm Option C + the load-bearing carbon+macronutrient targets before B200 hours.

## 5. First task (concrete, laptop-doable)
Phase-1 step-1: `CarrollParamDiagnostic` wrapper + a pytest round-trip, on a fresh worktree off
`origin/main`. Everything downstream gates on Option C + Jon buy-in.

## Connects to
ADR-0002 (Track-2 emulator scope) — this is its concrete build path. Ablation Ledger (the #1
macronutrient lever). Memory: `reference_earth2_physicsnemo_audit`, `feedback_track2_feasibility_not_realdata`.
