I have the exact source. Now writing the assessment. Note one precision point for Part 1: the production runner uses the 2-layer model (`carroll6_5pft_2layer`), but `carroll6.py` (read above) is the canonical reference for the equations, bounding, and CARROLL_VALUES. I'll be precise about this.

---

# DarwinDiff Scientific Assessment: The Neural Network Mechanism and Utilization of ECCO-Darwin v05 / Carroll

Prepared for the DarwinDiff team and Jonathan Lauderdale. Date: 2026-06-11. Branch `2imi9/stage1-per-aoi-gating`, HEAD `1704a44`. Code-grounded against `src/darwindiff/networks.py`, `carroll6.py`, `carroll6_5pft_2layer.py`, `scripts/run_v3.0_joint_multi_aoi.py`, and `scripts/build_darwin_ic_cache.py`.

---

## Part 1 — What the neural network is, and how it enables Carroll-6 recovery

### 1.1 The DINN is a per-cell function from environment to the six parameters

The learnable object is **not** the Carroll-6 parameters themselves. It is a small neural network `DINN` (`networks.py:78-133`) whose weights `W` define a function

```
θ(x) = DINN_W( env(x) )            # env(x) ∈ R^{C}, θ(x) ∈ R^{6}, at every grid cell x
```

Architecturally `DINN` is a stack of **1×1 convolutions** (`networks.py:118-128`): `Conv2d(C, 16, k=1) → Tanh → Conv2d(16,16,k=1) → Tanh → Conv2d(16,6,k=1)`. A 1×1 kernel has **no spatial receptive field**, so the network is mathematically identical to applying one tiny MLP independently at each cell — cell `x`'s six outputs depend only on cell `x`'s own covariate vector `env(x)` (docstring `networks.py:9-16, 81-83`). This is a deliberate design constraint, not an accident: it is the formal content of the "per-cell" identifiability argument in §1.3.

In the production v3.0 runner the input is deliberately thin: `n_input_channels = 1 + USE_AOI_ID_CHANNEL + USE_MLD_CHANNEL` (`run_v3.0_joint_multi_aoi.py:831`), both optional channels default OFF, so a default run feeds **SST z-score only** (one channel). The richer 4-channel form (SST+MLD+wind+lat) lives in `DINNDeep` and the nb20-series builders but is not the production path.

### 1.2 Sigmoid bounding into physical Carroll-6 ranges

The DINN output is **unbounded** (`networks.py:104`). It is mapped into physical ranges by `bounded_params` (`carroll6.py:307-354`):

```
θ_physical = lo + (hi − lo) · sigmoid(θ_raw)
```

with per-parameter `[lo, hi]` from `PARAM_BOUNDS` (`carroll6.py:82-94`): alpfe ∈ [0.05, 1.0], scav_rat ∈ [3e-8, 3e-6] s⁻¹ (a 100× window around Carroll's 6.0e-7), Smallgrow/Biggrow ∈ [0.10, 2.0] d⁻¹, diatomgraz ∈ [0.05, 1.0], R_PICPOC ∈ [0.005, 1.5]. Two consequences matter scientifically:

- **The optimizer never leaves the physical box**, and gradients are well-behaved (sigmoid is smooth, saturating at the bounds). The R_PICPOC bound was deliberately raised from 0.20 to 1.5 (`carroll6.py:88-93`) after a diagnostic showed the binding constraint is inter-AOI tension (eqpac PIC/POC median 0.031 vs natl 0.722, a 23× spread), **not** the bound — a finding that directly motivates several Part-2 levers.
- **`bounded_params` broadcasts** over `[6]`, `[6,H,W]`, `[B,6,H,W]` via `param_axis` (`carroll6.py:347-354`), so the identical bounding applies whether we fit one scalar, a per-cell map, or a batched ensemble of seeds.

### 1.3 The loss backpropagates through the forward-integrated box model

This is the "Informed" in DINN (`networks.py:86-90`). The training loop is:

1. **Predict** a per-cell Carroll-6 map: `θ(x) = bounded_params(DINN_W(env(x)))`.
2. **Integrate the box model forward** from a fixed initial state, per cell, holding the ~94 non-learned Darwin knobs at literature defaults (`carroll6.py:52-64`: `M_LIN, M_QUAD, G0_GRAZE, W_SINK, K_FE, PHI_DUST, Q_FE, LIGHT, H_MLD`). The reference equations are in `carroll6.py:97-141` (5-tracer) and `:178-256` (7-tracer + carbonate); **production uses the 15-tracer 2-layer variant** `carroll6_5pft_2layer.carroll6_5pft_2layer_step`, stepped ~200× at dt=0.25 d (~50 d, ≈5× the sinking timescale) to a near-steady state.
3. **Compare the endpoint to targets** with a z-scored spatial-pattern MSE per tracer (`run_v3.0_joint_multi_aoi.py:919-930, 954-966`) across ~11 channels (FeT, Chl1-5, POC, PIC, DIC, ALK, CO2_flux) plus optional absolute-units anchors (PIC_ABS_W, POC_ABS_W, POSI_W, F_CO2_ABS_W) and GEOTRACES surface/subsurface terms.
4. **Backpropagate** the scalar loss through the entire forward integration (autograd computes the box model's adjoint) and through the carbonate solver, all the way to `W`. One optimizer step updates the network weights; the recovered Carroll-6 is read out at convergence and compared to `CARROLL_VALUES` (`carroll6.py:69-76`) by relative-offset bands.

The key move: **the box model is differentiable**, so "what parameter field best reproduces Darwin's fields" becomes a gradient-descent problem on `W`, not a Green's-functions ensemble of forward runs.

### 1.4 The structural identifiability argument (per-cell vs a single global vector)

DarwinDiff's claim over Green's-functions calibration is **not network capacity** — the nets are tiny by design (`networks.py:22-25`). It is about *what the parameters are allowed to be conditioned on*:

- **Green's-functions / global-scalar class:** one Carroll-6 vector for the whole domain (the benchmark `DINNRegional`, `networks.py:37-75`, region-level MLP, 166 weights). A single vector must satisfy every regime's misfit simultaneously.
- **DINN per-cell class:** `θ(x)` is a continuous function of local environment. Because the truth structure is genuinely per-cell, the per-cell map can express regime contrasts (HNLC eqpac vs iron-replete subpolar) that a single vector cannot, **and** the multi-AOI joint loss lets each parameter's identifying signal come from the regime where it is observable.

This is also why the project's hard problems are *structural*, not capacity-limited: the deeper `DINNDeep` (`networks.py:175-243`, ~8.5K weights, residual + GELU, **per-cell LayerNorm** at `:136-150` specifically so shared norm stats never couple cells) recovers *no more* Carroll-6 params than the baseline and does not extrapolate spatially (held-out r=0.301 on FeT). Capacity is not the bottleneck; observational identifiability and box-model fidelity are.

### 1.5 Why seeding from the true Darwin pickup IC sharpened recovery (the v2.8 scav_rat result)

The forward integration must start somewhere. Through v2.7 the start state used synthetic/literature ICs. v2.8 replaced the 5 inorganic anchors (DFe, POC, PIC, DIC, ALK) × 2 layers with **depth-weighted means extracted from the real Darwin pickup_ptracers** (`build_darwin_ic_cache.py:59-65`; L1 = levels 0-4, L2 = levels 5-28). This produced the **project-first reproducible scav_rat recovery**. Mechanistically:

- scav_rat is identified by the subsurface iron balance `dDFe_2 = fe_remin − scav_rat·DFe₂·POC₂ + diffusion` (`carroll6_5pft_2layer.py:351-355`). The 2-layer box exists precisely to break the surface alpfe↔scav_rat degeneracy via the subsurface DFe gradient (`carroll6_5pft_2layer.py:6-11`).
- The scavenging sink is the **product** `scav_rat · DFe₂ · POC₂`. If `DFe₂` and `POC₂` start far from Darwin's true subsurface values, the optimizer can fit the surface fields by mis-setting scav_rat to compensate the wrong `DFe₂·POC₂`. Seeding `DFe₂, POC₂` (and DIC/ALK/PIC) at Darwin's *actual* subsurface state pins the other factors of the product, so the gradient on scav_rat points at the real value rather than a compensating one. The IC sets *where in the iron/carbon budget the optimizer starts*, and for a product-form sink that starting point is load-bearing.

### 1.6 What the NN does NOT buy (be honest)

The DINN reweights and conditions **only the 6 learnable parameters**. It cannot fix two classes of error:

- **Box-model proxy bias.** The forward model is a 5-7 (production: 15) tracer 1-deg, 0-D-per-cell, time-mean proxy of the 39-tracer Darwin SMS. Any structural mismatch — no macronutrient limitation (growth is iron-only, `LIGHT=1.0` constant, `carroll6.py:60, 120-122`), no temperature/Eppley scaling of biology, no explicit zooplankton (grazing is one linear diatom-only term `g_diatom·G0_GRAZE·Pl`, `carroll6.py:126`), a single global sinking rate for POC *and* PIC, a spatially-uniform `PHI_DUST`, no horizontal advection (so eqpac upwelled iron is mis-attributed to dust) — is absorbed into the fixed ~94% of knobs and **biases the recovered 6**. No architecture removes this.
- **Fundamental observational under-determination.** Where a parameter's signal is absent from the loss, no network recovers it. R_PICPOC under pattern-only z-loss is degenerate because z-scoring cancels the magnitude that R_PICPOC·mort_total controls (`run_v3.0_joint_multi_aoi.py:269-277`); scav_rat is unrecoverable without the subsurface DFe anchor / Darwin IC. The fixes for these are **loss terms (absolute anchors), ICs, and additional AOIs — not the net.**

---

## Part 2 — Have we fully utilized ECCO-Darwin v05 and the Carroll papers?

**Verdict: No — the *forward-model physics* and the *time axis* are the two largest under-utilized resources, and they are exactly the levers most coupled to the two stuck parameters.** What is well-utilized is the iron-pair anchoring machinery (subsurface GEOTRACES + Darwin ICs) and the per-cell NN architecture. What is barely tapped is (i) the seasonal cycle (everything is fit to a 23-yr time-mean), (ii) Darwin's own dense gridded diagnostics (primProd, PAR, POSi, c01-c07), and (iii) Carroll's actual cost function / obs set (we score distance-to-optima, never out-of-sample obs misfit).

### 2.1 Highest-value untapped items (ordered by recovery value)

| # | Untapped item | Type | Carroll-6 param it bears on | Value | Cost |
|---|---|---|---|---|---|
| 1 | **No temperature/Eppley scaling of biology** (growth = μ·f_Fe·1.0·P; T enters only the carbonate solver) | physics/forward-model | Smallgrow, Biggrow | **High** | Laptop |
| 2 | **Monthly climatology / seasonal cycle** (all targets are 23-yr time-mean; `monthly_climatology()` exists, unused) | data axis | Smallgrow, Biggrow, diatomgraz | **High** | Laptop→cluster |
| 3 | **Native monthly `primProd`** (Darwin's diagnosed NPP — never loaded) | data product | Smallgrow, Biggrow | **High** | Laptop |
| 4 | **Native monthly `PAR`** + a real `f_light` term (`LIGHT=1.0` hardcoded) | data product + physics | Smallgrow, Biggrow | **High** | Laptop |
| 5 | **Native monthly `POSi`** (dense gridded biogenic silica — direct diatomgraz target) | data product | **diatomgraz** | **High** | Laptop |
| 6 | **`SiO2` macronutrient + Si-limitation in growth** (box has no nutrient limitation at all) | physics/forward-model | diatomgraz, Biggrow | **High** | Laptop→cluster |
| 7 | **Separate PIC sinking rate** `wPIC_sink` (single global `W_SINK` aliases R_PICPOC by w_POC/w_PIC) | physics/forward-model | **R_PICPOC** | **High** | Laptop |
| 8 | **Spatially-varying dust (`ironFile`)** vs uniform `PHI_DUST` (recovered alpfe = product alpfe·PHI_DUST) | physics/forward-model | **alpfe** | **High** | Laptop |
| 9 | **Coccolithophore-only calcite** flag exists but OFF by default (default scales PIC by total mortality) | physics/forward-model | **R_PICPOC** | Med-High | Laptop |
| 10 | **FeT_L2 as a loss target** (cache has it; used only as start-state) | IC content | scav_rat | High | Laptop |
| 11 | **Carroll's cost function / out-of-sample obs validation** (we score distance-to-optima, never obs misfit; GLODAP loader built but unused in v3.x) | Carroll machinery | all 6 (methodology) | High | Laptop |
| 12 | **Native monthly `POFe`** (particulate iron — direct scav_rat sink target) | data product | scav_rat | Med | Laptop+box ext |
| 13 | **Per-cell MLD** as the carbonate flux divisor (hardcoded `H_MLD`/H1 = 50 m) | data product / physics | R_PICPOC (indirect) | Low-Med | Laptop |
| 14 | **Carroll→PFT mapping** (`lumped_mapping` OFF: Smallgrow learned on Pro-HL only vs Carroll's group rate) | physics/definition | Smallgrow, Biggrow | Med-High | Laptop |

Items not listed (SSS-as-DINN-feature, seaIceArea, area-weighting, PO4/O2/DOM tracers, daily product, native carbonate-diagnostic duplicates, satellite PIC/PACE, SOCAT/BGC-Argo/WOA/WOD/GLODAPv2.2023) were confirmed untapped but rate **low** for Carroll-6 — mostly because the box has no state variable for them, they duplicate fields already in hand, or they touch the fixed ~94% rather than the 6.

### 2.2 The 3–5 levers most likely to move the stuck params or break the 5/6 ceiling

**For diatomgraz (~10-15% Cal-grade, collapses to 0% with the Southern Ocean in the loss):**
- **Dense gridded `POSi`** (item 5). The sparse GEOTRACES-bottle proxy already lifted diatomgraz Cal-rate ~13%→80% in nb33; a dense, model-consistent target is the cleanest single lever, and it is diatom-specific so it does not compete with the iron-pair budget. **This is the top candidate for the 6th parameter.** *Caveat:* `POSi` needs a `TRAC_MAPPING` entry built from the `.meta` fldList, and the Southern Ocean bSi already *fights* Carroll's 0.83 (it prefers ~0.33) — so the apples-to-oranges tension in §2.3 applies.
- **Si-limitation in growth** (item 6). Today diatomgraz must absorb variance Darwin attributes to Si-limitation; adding an `f_Si` co-limitation factor removes that structural mis-attribution.

**For R_PICPOC (~3%, the hardest param):**
- **Separate PIC sinking rate** (item 7) + **coccolithophore-only calcite** (item 9). The single `W_SINK` collapses the steady-state surface PIC/POC to *exactly* R_PICPOC, biasing it low by w_POC/w_PIC; and scaling PIC by total mortality (default) instead of coccolithophore mortality makes a single R_PICPOC scalar try to fit the 23× eqpac/natl spread — structurally impossible. **Both are forward-model fixes the absolute-anchor approach cannot substitute for**, and they attack the documented binary PIC-anchor mutex from the physics side rather than the loss side.

**For breaking the 5/6 ceiling generally:**
- **Seasonal cycle** (item 2). Every loss is on the 23-yr mean, integrating away exactly the spring-diatom-bloom / summer-pico contrast that separates the growth/diatom tier. This is the single biggest unexploited axis and converts one static snapshot into ~12 phase constraints per parameter. *Caveat:* monthly-resolved fitting changes the integrator from steady-state to transient (cluster-gated at scale).
- **Eppley temperature scaling** (item 1). Across AOIs at 26 °C (eqpac) vs 5-10 °C (subpolar), a single learned μ cannot match both unless the DINN papers over a missing physical term via SST conditioning. This is a top suspect for the multi-AOI Smallgrow/Biggrow non-recovery and is a few-line forward-model change.

### 2.3 The honesty checks — methodology gaps and what is genuinely maxed-out

**Two methodological caveats that bound every "recovery" claim** (these are not headroom; they are framing risks Jon should weigh):
- **We never pinned down Carroll's actual assimilated obs set or cost function.** Carroll 2020's headline target was *seasonal surface pCO2 / air-sea CO2 flux* vs SOCAT-type products, minimized as an absolute weighted misfit. Our loss is z-scored spatial-pattern MSE over Chl/POC/PIC/FeT against **Darwin's own v05 output**. These are different cost functions on different observables. A param landing far from Carroll's value could fit our obs (or even real obs) *better* — and we have no out-of-sample obs-misfit evaluation to check, only distance-to-Carroll bands. Building a withheld-GLODAP/SOCAT misfit test (the GLODAP loader is already built, `glodap_loader.py`, just unused in v3.x) would convert the comparison from apples-to-oranges (params) to apples-to-apples (obs).
- **Carroll's R_PICPOC = 0.04245 is incompatible with satellite PIC.** MODIS PIC is ~16-20× higher than Darwin v05 PIC in eqpac, so a satellite anchor implies R_PICPOC ~0.5-0.6, not 0.042. Per Jon's resolution (no satellite in v05 targets), MODIS/PACE are correctly shelved — but this means the satellite loaders are *not* latent R_PICPOC headroom within the Carroll-6 framing.

**What is genuinely maxed-out (do not over-claim headroom here):**
- **Network capacity.** `DINNDeep` (8.5K weights) recovers no more params than the SST-only baseline; the ceiling is structural, not capacity. Adding a bigger net buys nothing.
- **The iron-pair anchoring stack.** Subsurface GEOTRACES iron + Darwin pickup ICs already deliver reproducible scav_rat (v2.8) and the multi-AOI HNLC-vs-replete contrast for alpfe. The remaining alpfe/scav_rat improvements are second-order (Q_FE quota bias, DOM iron recycling, spatial dust pattern), not a missing primary anchor.
- **The PIC/POC absolute anchors as a path to 6/6.** PIC_ABS_W / POC_ABS_W were swept down to 0.02, paired and solo, at n=10-20: **any** nonzero PIC anchor wipes the iron pair (binary basin mutex). They are informative and tested-to-exhaustion; they are not undiscovered headroom. R_PICPOC progress must come from the **forward-model** side (items 7, 9) or the seasonal axis, not from doubling down on absolute PIC magnitude in the z-loss.
- **Per-cell gating as currently configured.** The Stage-1 2-AOI per-AOI gradient gating result (HEAD `1704a44`) is **negative** (mean 2.95→1.65/6); the 3-AOI confound-check is still pending and requires building the `southernoceanpac` IC cache.

**Cheap / laptop-feasible now:** items 1, 3, 4, 5, 7, 8, 9, 10, 14, and the GLODAP out-of-sample obs-misfit eval (item 11). Most are forward-model edits (`carroll6_5pft_2layer.py`) or single loader additions (a `TRAC_MAPPING` entry + one line in the native-load list at `run_v3.0_joint_multi_aoi.py:368`).

**Cluster-gated:** full seasonal/transient fitting at scale (item 2), macronutrient-co-limited box re-validation (item 6), a regional differentiable port of the full `darwin_plankton.F`, and time-resolved alpfe/scav_rat disambiguation requiring multiple pickup months (only one pickup is on disk).

---

**Bottom line for the team:** the NN and the IC/GEOTRACES iron stack are working as designed and are near their useful limit. The unexploited headroom is overwhelmingly in **forward-model fidelity** (temperature, light/PAR, Si-limitation, separate PIC sinking, coccolith-only calcite, spatial dust) and the **time axis** (seasonal climatology) — and those are precisely the resources coupled to the two parameters (R_PICPOC, diatomgraz) blocking 6/6. The cheapest highest-value next step is dense gridded `POSi` for diatomgraz; the cheapest highest-value R_PICPOC step is a separate `wPIC_sink` plus enabling coccolithophore-only calcite. Both are laptop-feasible forward-model changes, not cluster runs.

Relevant files: `C:\Users\Frank\OneDrive\Desktop\Github\ecco-darwindiff\src\darwindiff\networks.py`, `...\src\darwindiff\carroll6.py`, `...\src\darwindiff\carroll6_5pft_2layer.py`, `...\src\darwindiff\silica.py`, `...\scripts\run_v3.0_joint_multi_aoi.py`, `...\scripts\build_darwin_ic_cache.py`, `...\src\darwindiff\llc270_loader.py`, `...\docs\findings\v3.1_closeout.md`, `...\docs\findings\v2.8_darwin_ic_poc_sub.md`.