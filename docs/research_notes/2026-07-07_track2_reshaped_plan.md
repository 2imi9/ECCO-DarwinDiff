# Reshaped Track-2 Phase-1 Plan — post-2026-07-07 Jon + Schultz meeting

*Lead-architect synthesis of the iron-scavenging, calcite-environment, E2-readiness, and build-order reports. Grounded in `src/darwindiff/{transport.py,carroll6.py,carbonate.py}` and the meeting capture at `docs/findings/2026-07-07_jon_schultz_meeting_capture.md`. No-AICR: Explorer H200 or CPU only.*

The meeting collapsed two ambiguities that had been sitting in the closure hooks: **iron** is a scavenging *sink* problem on a *spatial soluble-iron forcing field* (not a solubility/`alpfe` problem — `alpfe` is a global scalar on already-soluble dust), and **calcite** is an *environment→efficiency* problem (composition is refuted against real Chl2). Both closure hooks already exist in the code (`ffe_closure`, `calcite_closure`) with a byte-identical `None`-fallback contract — so the reshaping is mostly *feeding the right inputs* and *learning the right term*, not new machinery.

---

## TL;DR — next steps, ordered

1. **PR-1 · Centered horizontal-advection operator** — `[CPU]`. Add `horizontal_advection(field, u, v, dx, dy)` + a `grid_tendency` to `transport.py` (today it is vertical-only: `vertical_diffusion`/`vertical_advection`/`column_tendency`). This is the one *new critical-path* item the meeting exposed — the whole E2 thesis is that horizontal transport redistributes the spatially-varying fields that forced `scav_rat`/`R_PICPOC` per-cell in Paper 1. Gate offline: `gradcheck` (fp64, 3×3 box) + `mass_drift < 1e-10` on a closed field (`bgc=False`).
2. **PR-2 · Environment-driven `calcite_closure`** — `[CPU]`. Widen the hook `calcite_closure(state, mort_total)` → `calcite_closure(state, mort_total, env)` in `carroll6.py:230-288` and `transport.py:36-90`; implement `PIC_prod = R0 · g_θ(env) · mort_total`, `g_θ≡1` byte-reproducing `R_PICPOC·mort_total`. `Omega` from the existing `carbonate.calcite_saturation`. Gate: byte-identity + `gradcheck`.
3. **PR-3 · Scavenging-aware iron closure + excitation extension** — `[CPU]`. Add a `scav_closure(DFe, POC, env)` hook replacing `scav_rat_per_day·DFe·POC`; extend `scripts/ude_forcing_design.py` to score the *joint (DFe, POC)* visited support (today it Fisher-scores DFe-only Monod uptake). Gate: offline Fisher (`cond(G)`, `λ_min`) on the synthetic twin. This offline gate decides whether any Explorer scavenging-fit is worth queueing.
4. **DB-1 · Soluble-iron forcing-field loader** — `[data-blocked → trivial]`. Download the single 43 MB `llc270_Mahowald_2009_soluble_iron_dust.bin` from the public NAS `darwin_forcing/` portal, load as an llc270 field, pass through the existing `dust=` kwarg (already broadcasts — no operator change). This is the *source* half of the iron fix; it is coupled to PR-3's *sink* half and should land alongside it so the two are not conflated.

Steps 1-3 are all CPU-landable without Jon or Explorer and are the direct code consequences of the three findings. Explorer H200 is reserved for the *actual* transport-forced fit (Round 2), only after these offline gates are green.

---

## The two closure designs

### A. Iron — learned *scavenging sink* (not solubility)

The box sink `scav_rat_per_day·DFe·POC` (`carroll6.py:221,282`; `transport.py:85`) is a triple simplification of Darwin3/Parekh scavenging: it scavenges **total** dissolved Fe (not free Fe′), uses **linear** POC weighting (Darwin uses POC^0.58), and has **no ligand chemistry**. What is spatially variable and uncertain in Darwin is exactly what the box drops — which is the surrogate-gap fingerprint behind `scav_rat`'s per-cell requirement in Paper 1.

**Form** (Monod-anchor pattern, mirrors `MonodAnchored` in `ude_closure_identifiability_h200.py:67-81`):

```
scav_sink(DFe, POC; env) = r0 · (POC/POC0)^p · DFe · (1 + eps·tanh(NN(feat)))
```

| Piece | Value / prior | Rationale |
|---|---|---|
| `r0 = softplus(log_r0)` | prior `log(0.0521)` = Carroll `scav_rat_per_day` | the homogeneous rate the box already fits globally |
| `p = 0.4 + 0.6·sigmoid(·)` ∈ [0.4, 1.0] | prior **0.58** (Darwin/Parekh exponent) | `p=1` exactly recovers the box law → baseline nested |
| `POC0` | fixed ≈ median POC (~0.5 mmolC/m³) | keeps `(POC/POC0)^p` O(1), `r0` interpretable |
| `(1+eps·tanh(NN))` | `eps` = 0.20–0.25, NN 1→16→1 Tanh | bounded deformation absorbing Fe′/ligand curvature |

**Inputs** `feat` (2-3, standardized O(1)): `[log10(DFe)+4, log10(POC/POC0), T_norm]`. Keep it narrow — the ~14-cell GEOTRACES budget forbids a wide net. `T` enters because ligand-partition strength (`beta_stab`) is temperature/chemistry-dependent.

**Bounds/positivity**: sink ≥ 0 (it is a loss term). `r0>0` (softplus), `(POC/POC0)^p ≥ 0`, `DFe ≥ 0`, tanh factor clamped to `[1-eps, 1+eps]`. No sink when `POC=0` or `DFe=0`.

**Anchor**: `eps=0, p=1, r0=0.0521` → **byte-identical** to the current term (strict superset, same guarantee the existing hooks give). Report `eps` and `(p-0.58)` as *diagnostics*: if data pulls `p` off 0.58 or `eps` hard, the box's linear-total-DFe simplification is being falsified.

**Explicitly deferred**: solving the ligand quadratic (adds `beta_stab`, `L_T` globals) — the ~14-cell support cannot identify them (Tagliabue 2016: iron models agree on concentration but diverge >1 order of magnitude on residence time/source). Absorb the Fe′ curvature into the bounded correction now; free-Fe′ is Phase-2, once a spatial iron forcing field is in.

### B. Calcite — environment-driven efficiency envelope `g_θ`

Every operational BGC model (MARBL/BEC, PISCES-v2, Ridgwell/Gehlen) drives calcification by an **environment multiplier on organic production**, not composition. This is the structure the meeting mandates and the box's `USE_ENV_RAIN_RATIO` thermal window already reproduced (3-basin spread, log-MSE ≈ 0, 3/3 AOIs in-band).

**Form** (drop-in over `calcite_closure`, widened to pass `env`):

```
PIC_prod = R0 · g_θ(z) · mort_total
g_θ = 10^(A·tanh(a)),  A=1  →  g ∈ [0.1, 10]  (log-symmetric, multiplicative)
```

`R0` = Carroll `R_PICPOC` = 0.04245 (learnable field-mean scalar, carries magnitude); `g_θ` = MLP `[n_in→16→16→1]`, **final layer zero-init** → `g_θ≡1` at init (anchored to constant-ratio baseline, same warm-start as the existing hooks). Realized ratio `R0·g` ∈ [0.004, 0.42], inside PISCES [0.02, 0.8]; soft-cap at 0.8.

**Ranked inputs** `z` (z-scored; mechanistic prior in parens):

1. **SST** — community thermal window; dominates on our data. Prior = Gaussian peak ~17.5 °C (`RPP_T_OPT`).
2. **Fe/nutrient limitation** `f_lim = DFe/(DFe+K_FE)` — MARBL/BEC/PISCES first-order; PIC:POC *rises* under stress. Already computed one line above `pic_prod` (`carroll6.py:267`).
3. **Ω_calcite** — Ridgwell `(Ω-1)^η`; from `carbonate.calcite_saturation(DIC,ALK,T,S)` (`carbonate.py:311-372`, already autograd-clean). Second-order — the repo probe found it "adds ~nothing over temperature alone," so include but expect small.
4. **PAR/light** — third-order; include only if a light forcing field is wired (`light=` in `transport.py:43` is currently a scalar), else drop.

**Anchors / identifiability guarantees**:
- `g_θ≡1` zero-init recovers constant `R_PICPOC` bitwise (self-twin sanity).
- **Regularize toward the mechanistic Gaussian-T prior** `g0(T)=exp(-½((T-17.46)/2.33)²)/G_NORM` with a small `λ·‖g_θ - g0‖²` penalty — this is the key move that keeps a multi-input NN identifiable on a weakly-excited ratio target.
- `R0` stays the field-mean scalar so `g_θ` carries only *shape*, not magnitude.

**Community-scale caveat (load-bearing)**: fit `g_θ` against **bulk Darwin PIC:POC**, not lab per-cell physiology. Community PIC:POC *peaks* at intermediate T (thermally-bounded coccolithophore abundance / Great Calcite Belt); per-cell physiology has a *minimum* at optimal-growth-T — opposite curve. Do **not** seed `g_θ` with the physiology curve.

**Target**: regional PIC:POC = Darwin v05 ratio-of-means (eqpac 0.033 / natl 0.68 / SO 0.0067), via the existing `RATIO_W` loss, anchored by the Daniels CP:PP production ratio (~0.04, non-circular — any ratio anchor recovers `R_PICPOC`, so Daniels' *value* is the non-circularity). **SO requires `RATIO_MAX=2` sanitization** (mandatory — else low-POC cells inflate the target mean to 4.7e7 and collapse the loss).

---

## E2 readiness — have / need

E2 gate = **held-out real-data R² > 0 with transport**. The 0-D box's held-out GEOTRACES R² is *negative by construction* (it homogenizes) — E2 is the first test that *could* pass, and transport is exactly what it adds.

| Component | Sub-item | Status | Shortest path |
|---|---|---|---|
| Transport | u, v, w velocities | **HAVE** | `D:/ecco_darwin_v5/output/monthly/{uVel_C 53G, vVel_C 50G, wVel 51G}`, native 3D 270×3510×50, ~280–293 months. Needs velocity entries in `llc270_loader` + column/AOI regrid. |
| Transport | **vertical mixing `kz`** | **NEED — biggest gap** | No diffusivity dir on disk; `transport.py` hardcodes `kz=0.1`. Proxy from on-disk `MXLDEPTH` (`mldDepth/`) *or* download v05 KPP/DIFFKR diagnostic if NAS exposes it. A config choice, **not** a 5 TB download. |
| Transport | horizontal advection code | NEED (code) | PR-1. Vertical-only today. Buildable + gradcheckable on CPU. |
| Forcing | Mahowald soluble-iron field | **OBTAINABLE (trivial)** | 43 MB `.bin` at NAS `darwin_forcing/`, public HTTP, no AICR. `dust=` already broadcasts. → DB-1. |
| Targets | GEOTRACES iron | **HAVE** | `D:/geotraces/*.nc`, ~14 surface cells/AOI. Section-level score only. |
| Targets | calcite (Daniels + MODIS) | **HAVE** (loader port) | `data/daniels/*.tab` tracked, `D:/modis_aqua_pic/*.nc`. NB: `daniels_loader.py` is in a worktree, **not on this branch** — must be ported. |
| Targets | Ω inputs (DIC/ALK/T/S) | **HAVE** (S needs add-back) | DIC/ALK/THETA native monthly on disk; `carbonate.py` computes Ω; only **absolute salinity** must be reconstructed (`SALTanom` present, plain `SALT` absent). |

**Single biggest gap**: the vertical diffusivity field `kz`. It is *small* — proxy from on-disk `MXLDEPTH`, or a targeted diagnostic download; not a bulk data problem.

**Feasible without AICR? — YES.** Everything E2 needs is on disk (`D:`) or a 43 MB download; the compute (multi-month/decadal transport-forced fit + held-out GEOTRACES-section score) fits Explorer H200. The real engineering lift is *code* (horizontal advection + field-driven `kz`/`w` ingestion), all buildable/gradcheckable on CPU before any H200 spend.

**Scope-honest E2 target**: score model-vs-obs *along GEOTRACES sections/profiles* (Tagliabue-style, upper-ocean, non-winter-caveated) — **not a dense global iron map**. The ~14-cell sparsity validates a near-homogeneous scalar/section fit; it cannot verify a dense spatial field. (Per `feedback_track2_feasibility_not_realdata.md`: until a spatial iron forcing *and* a held-out GEOTRACES section are both in, results stay self-twin/synthetic — do not claim "learned real iron scavenging.")

---

## Refreshed build order — next 2-3 PRs

Already **DONE** (do not rebuild): `f(t,x)` time-aware integrator + checkpointing (`integrators.py`, tested); vertical diffusion/advection + `column_tendency` (`transport.py`); `ffe`/`calcite` closure hooks (`carroll6.py`); go/no-go vertical-column capacity probe (`transport_helps_probe.py`, PASS); offline Fisher forcing-design probe (`ude_forcing_design.py`); excitation-unlocks-iron-pair confirmed (`column_ude_probe.json`).

**Round 1 — local-CPU gates, no Explorer, no Jon (each a PR):**

- **PR-1 [CPU] Centered horizontal-advection operator.** New `horizontal_advection(field, u, v, dx, dy)` in `transport.py`: flux-form centered-2nd on prescribed (u,v), telescoping so mass conserves; land mask as 0/1 multiply, halos by concat, eps-guarded divisions, no in-place. Compose into `grid_tendency` alongside `column_tendency`. Gate: `gradcheck` (fp64, 3×3) + `mass_drift < 1e-10` (`bgc=False`). Defer the tanh-blended limiter unless centered-2nd shows false extrema. *This is the mechanism behind the E2 thesis.*
- **PR-2 [CPU] Environment-driven `calcite_closure`.** Widen signature to `calcite_closure(state, mort_total, env)` with `env=[SST, Ω, PAR, Fe_lim]`; implement `PIC_prod = R0·g_θ(env)·mort_total` per design B; **assert `g_θ≡1` byte-reproduces `R_PICPOC·mort_total`**. Compute Ω offline once per cell (static field) to avoid a per-step carbonate solve. Keep composition/Chl2 gating **shelved (refuted)**. Also re-gloss the `carroll6.py` registry entry for `alpfe`: "iron dust solubility" → "dimensionless scale on the already-soluble iron-deposition forcing". Gate: byte-identity + `gradcheck`.
- **PR-3 [CPU] Scavenging-aware iron closure + excitation extension.** Add `scav_closure(DFe, POC, env)` hook (same None-fallback contract) replacing `scav_rat_per_day·DFe·POC`, per design A. Extend `ude_forcing_design.py` to score joint (DFe, POC) support. Gate: offline Fisher (`cond(G)`, `λ_min`) on the synthetic twin. Pair with DB-1 so source+sink land together.

**Round 2 — Explorer H200, only after Round-1 offline gates are green:**

- **PR-4 [Explorer] Batched-Thomas semi-implicit vertical diffusion + Strang split** — removes the explicit-diffusion CFL cap once fields get wide. Gate on CPU first (gradcheck + single-mode decay + mass-drift), then H200 for the wide-field `torch.compile` speedup.
- **PR-5 [Explorer] Windowed-BPTT training harness on a real AOI subregion** — detached-IC short windows (30–90 d), nested checkpointing, rollout curriculum, Adam→L-BFGS, L2 swept + soft-Carroll prior, n≥10 seeds. Trains env-calcite + scavenging-iron closures with horizontal transport ON. Gate: forward-only decade rollout R² + per-element fp64 mass budget, via `verify_run.py`.

**Data-blocked loaders (schedule in parallel; these unblock the *real* E2):**

- **DB-1** soluble-iron forcing-field loader (43 MB Mahowald `.bin` → `dust=` kwarg) — *pair with PR-3*.
- **DB-2** prescribed (u,v,w) velocity + geometry loader for a real AOI (recompute w from discrete continuity so the field is divergence-free) — feeds PR-1.
- **DB-3** real held-out GEOTRACES-section E2 gate (model-vs-obs along sections, ~13/14/25 surface cells/AOI) — needs DB-1 + DB-2 first.

---

## Open questions — resolve ourselves vs. need Jon

**We resolve ourselves (from Darwin3 docs + repo, no Jon time):**
- Iron ligand chemistry: **absorb** Fe′/ligand curvature into the bounded correction rather than modeling `beta_stab`/`L_T` explicitly — the 14-cell budget forbids identifying the extra globals. (Recommend absorb-first; revisit only if the residual `eps`/`p` diagnostics demand it.)
- `kz`: **MXLDEPTH proxy is defensible** without Jon; only escalate if a NAS KPP/DIFFKR diagnostic turns out to be trivially available.
- Absolute-salinity reconstruction for Ω (`SALTanom` + reference) — mechanical, `carbonate.py` already has the machinery.
- Calcite input set / per-PFT-vs-per-time parameterization — resolve from the Darwin3 coccolithophore docs on hand before finalizing PR-2's `env` vector.
- The community-vs-per-cell T-response distinction (fit against bulk Darwin, not lab physiology) — settled by the meeting capture + repo probe.

**Genuinely need Jon:**
- **Iron physics sign-off**: is the free-Fe′/ligand partition to be modeled explicitly (adds two globals) or absorbed as designed? The choice *biases what "recovered" means*, so a one-line confirmation is worth it even though we have a default.
- **A real SO calcite anchor**: SO has no Daniels coverage; `RATIO_MAX=2` is a workaround, not a constraint. Securing a genuine SO PIC:POC anchor is open and flagged in the meeting capture — do not trust SO in any gate until it exists.
- **Whether the v05 NAS portal publishes a KPP/DIFFKR diagnostic** (or blesses the MXLDEPTH proxy) — Jon-checkable, but not blocking.

---

*Relevant files:* `C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\src\darwindiff\transport.py`, `...\src\darwindiff\carroll6.py`, `...\src\darwindiff\carbonate.py`, `...\src\darwindiff\geotraces_loader.py`, `...\scripts\ude_forcing_design.py`, `...\scripts\ude_closure_identifiability_h200.py`, `...\scripts\transport_helps_probe.py`, `...\docs\findings\2026-07-07_jon_schultz_meeting_capture.md`, `...\docs\research_notes\2026-07-06_ude_phase1_implementation_brief.md`.
