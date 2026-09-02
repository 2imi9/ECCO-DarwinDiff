# ECCO-DarwinDiff — project relationship map

The one-page mental model of how everything fits together: what the project *is*, the two
tracks, the shared substrate they stand on, and where each idea lives. Companion to
[STATUS.md](../STATUS.md) (live results), [docs/ecco_darwin_relationship.md](ecco_darwin_relationship.md)
(Track-1 detail vs the real Darwin code), and [docs/emulator_coupling_plan.md](emulator_coupling_plan.md)
(Track-2 build plan).

---

## What the project is, in one paragraph

ECCO-Darwin is a data-assimilative global ocean model = **MITgcm physics** (transport, fixed) +
the **Darwin biogeochemistry** (per-cell rate equations, ~103 tunable scalars, of which Carroll
calibrated **6** by expensive Green's-functions sweeps). ECCO-DarwinDiff asks two questions that
share one differentiable substrate:

1. **Track 1 — can gradients replace Green's functions?** Learn the Carroll-6 parameters by
   backprop through a *differentiable* 0-D box surrogate, per grid cell. Reframed honestly: a
   **surrogate-to-model identifiability study** — which parameters real observations can constrain,
   which they cannot, and why.
2. **Track 2 — can a neural operator emulate the forward model?** A differentiable/learned forward
   emulator of the v05 fields, and (the UDE variant) differentiable transport with learned BGC
   closures.

Both are "Diff" in the sense that matters: **differentiable**. The diffusion emulator is a small,
measured-null component (see naming note).

---

## Naming: keep "DarwinDiff" (Diff = differentiable), do not rebrand to diffusion

The proposal was `eccodarwin2diff` to carry both *differentiable* and *diffusion*. **Recommendation:
keep the differentiable identity; do not brand around diffusion.** The reasoning is our own evidence:

- **"Differentiable" is the load-bearing pillar.** The whole scientific contribution — Track-1
  identifiability, Track-2 UDE closures — rests on differentiating a surrogate. That is the name.
- **"Diffusion" is a measured null result here.** The EDM diffusion corrector in the forward
  emulator adds **no skill** (0 to −0.026; STATUS.md). Branding the project after a component we
  have shown does not help would elevate a negative result to the marquee — the opposite of the
  project's honesty discipline.
- **The "2" reads as ambiguous** (version-2? two-tracks? "to"-differentiate?) and the repo, issue
  tracker (spines A–D), and planned Zenodo DOI are already `ECCO-DarwinDiff`. A rename has real cost
  and no scientific payoff.

If a subtitle is wanted, the accurate one is *"a differentiable surrogate for ocean-BGC parameter
identifiability and forward emulation"* — the two tracks, not two kinds of "diff". If diffusion ever
*earns* a pillar (a probabilistic-operator formulation that actually calibrates), revisit then; today
the evidence says no — the Caltech scan classed generative/score operators as dead-end-by-evidence
against our EDM null.

---

## The layered picture

```
                       ┌─────────────────────────────────────────────────────────┐
  SUBSTRATE            │  ECCO-Darwin v05  =  MITgcm physics (transport, FIXED)   │
  (fixed, inherited)   │                      + Darwin BGC kernel (dC/dt, ~103    │
                       │                        scalars; Carroll tuned 6)         │
                       └───────────────┬─────────────────────────┬───────────────┘
                                       │ 23-yr time-mean fields   │ monthly fields
                                       │ + pickup ICs             │ (~110 pairs)
                    ┌──────────────────▼───────────┐   ┌──────────▼──────────────────┐
  DIFFERENTIABLE    │  0-D BOX MODEL               │   │  (Track 2 uses fields        │
  CORE              │  carroll6_5pft_2layer        │   │   directly, no box)          │
                    │  (PyTorch, autograd)         │   │                              │
                    └──────────────────┬───────────┘   │                              │
                                       │               │                              │
        ┌──────────────────────────────▼───┐   ┌───────▼──────────────────────────┐  │
  TRACK 1: PARAMETER LEARNER            │   │   TRACK 2: FORWARD EMULATOR          │  │
  per-cell DINN → Carroll-6 → box →     │   │   FNO2d residual, log-space,         │  │
  loss vs REAL ANCHORS → backprop       │   │   rollout-k8, deep ensemble, EDM     │  │
  = identifiability study               │   │   = 1-step operator (structural cap) │  │
        │                                   │   │        │                             │
        │   UDE variant: differentiable 3-D transport + learned neural closures       │
        └───────────────────────────────────┴───────────┴─────────────────────────────┘
                                       │
                          REAL ABSOLUTE ANCHORS (the only fidelity signal for Track 1)
                          GEOTRACES iron · Daniels/MODIS calcite · GLODAP · SOCAT
```

The **box** is shared machinery: Track 1 inverts through it; the UDE plugs learned closures into its
tendency. Track 2's pure emulator does *not* use the box — it learns the field-to-field map directly.

---

## Track 1 — parameter learner (identifiability study)

**Data flow.** per-cell env (SST, MLD, wind) → `DINN` (1×1 convs, ~438 wts) → 6 raw → sigmoid bounds
→ Carroll-6 *per cell* → differentiable box integrate → predicted tracers → loss vs **real anchors** +
z-scored Darwin pattern terms → backprop → DINN weights.

**The load-bearing facts** (STATUS.md):
- The surrogate gap is **dimensional** — the 0-D box homogenizes (tracer CV → ~1e-15), so box-vs-Darwin
  pattern correlations are *not* fidelity metrics. Identifiability comes only from real **absolute**
  anchors.
- **Per-cell is load-bearing:** the trio {alpfe, scav_rat, R_PICPOC} holds **25/50 per-AOI arithmetic — 12/50 geometric, 23/50 median** (33/50
  cell-weighted) vs **0/50** for a single global scalar. `alpfe` is method-independent but
  weight-conditional; `scav_rat` is the weakest leg; `R_PICPOC` is anchored by real Daniels.
- The iron source↔scavenging degeneracy **is** the published FeMIP problem (Tagliabue 2016) — a rank-1
  sloppy inverse problem. Methods *diagnostic* path (NOT a recovery improvement): EKI/CES + Fisher-eigenbasis (#187, `eki_core.py`) — EKI lands `scav_rat` at 2.1e-7 = 0.349× Carroll, agreeing with the geometric collapse.
- Growth pair {Smallgrow, Biggrow} is excluded by construction (`Biggrow` unobservable; `Smallgrow`
  non-identifiable from time-mean observables only); `diatomgraz` is **regionally identifiable** (equatorial
  Pacific 40/100 at ≤10 % vs untrained 0/50) and **input-limited elsewhere** — at chance from SST alone,
  10/10 once MLD is a DINN input (n=10, P = 0.021). The 35/50 Chl+MLD count is retired (untrained control
  34/50, P = 0.447). That is model-internal consistency, not independent real-data validation.

**Key code:** `scripts/run_v3.0_joint_multi_aoi.py` (driver), `src/darwindiff/carroll6_5pft_2layer.py`
(box), `src/darwindiff/networks.py` (DINN, GlobalScalarNet), `scripts/verify_run.py` (trust gate),
`scripts/identifiability_sloppiness.py` + `scripts/analysis/eki_core.py` (methods).

---

## Track 2 — forward neural-operator emulator

**Data flow.** v05 monthly fields (log-space) → FNO2d residual `x + f(x)·Δt_months` → rollout-k8
training → 6-member deep ensemble → optional EDM diffusion corrector → next-month field.

**The load-bearing facts** (STATUS.md):
- Useful horizon is **1 step**; the rollout ceiling is **structural** — a correct monthly operator
  buys no extra horizon (persistence hides drift). The Caltech scan closed this: the 1-step error is
  spatially flat in all four regions (job `8524645`), so the ceiling is information-limited, not
  architecture-shaped.
- **Δt-scaled residual** is THE fix for the monthly operator (+0.48 on true monthly steps).
- **EDM diffusion adds no skill** (0 to −0.026); **deep ensembling** +0.14; capacity saturates; data
  flat past n=55.
- First observational result: v05 chlorophyll unbiased at the equator, ~5× low in the N-Atlantic bloom
  (binning-fixed 2026-07-21).
- The emulator uses a **flat 2D FFT** on the irregular, non-periodic LLC270 grid — geometry-naive
  (SFNO/GINO were on the table for this; the flat-error test closed them for the regional emulators —
  job `8524645`, error flat in all four regions — leaving only the global cube-face seam untested).

**Key code:** `scripts/emulator_poc.py`, `scripts/diffusion_emulator.py`, `scripts/compare_v05_modis_aoi.py`.

---

## UDE — differentiable transport + learned closures (Track-2 research bet)

`integrators.py` (RK4 + checkpointing) + `carroll6_ude_tendency` (pluggable neural closures) +
`transport.py` (mass-conserving vertical transport). The Track-2 identifiability-limits map is complete
(real obs can't sharply constrain the 3 closures). Open: mass conservation at decadal rollouts (#7);
profile-targeting structure-preserving build (#176).

---

## Shared assets

| Asset | What | Where |
|---|---|---|
| Anchors | GEOTRACES IDP2025 iron, Daniels CP:PP + MODIS PIC calcite, GLODAP, SOCAT | `data/`, loaders in `src/darwindiff/` |
| Clusters | Explorer (H200, automation, key-auth); AICR (B200, throughput, interactive) | `docs/cluster_setup.md`, `reference_nu_explorer_access` |
| Trust gate | `verify_run.py` re-derives every recovery number from raw (exit 0 = safe); `analysis/pooler_audit.py` is the second gate for `scav_rat` (exit 2 = un-auditable — 119 of 211 run dirs carry no collapse keys) | `scripts/` |
| Registry | `carroll6.PARAMS` single source of truth for parameter order | `src/darwindiff/carroll6.py` |

---

## How to read the roadmap

Issues organize into spines **A–D** under epic [#124](https://github.com/2imi9/ECCO-DarwinDiff/issues/124):
A land-in-flight, B seasonal+cluster, **C manuscript #1 hardening** (critical path), D identifiability
frontier. Track-2 emulator epic is [#185](https://github.com/2imi9/ECCO-DarwinDiff/issues/185); UDE is
[#176](https://github.com/2imi9/ECCO-DarwinDiff/issues/176); methods upgrades are
[#187](https://github.com/2imi9/ECCO-DarwinDiff/issues/187).
