# Ablation Ledger — the exhaustive record

The complete list of **168 distinct parameter-recovery ablations** run across the project,
harvested from all 42 archived findings/research-notes (multi-agent audit, 2026-07-03). This is
the *depth* layer — the curated headline configs live in the [Config / Results Matrix](../results_matrix.md);
this ledger is the full experimental provenance so nothing is lost.

> **Verdict (audit synthesis).** The **estimator / loss-weighting / box-structure optimization space is
> effectively exhausted** — ~0 further estimator/loss-weighting experiments are worth running. Every
> ceiling-breaker (network capacity, gradient gating, per-AOI decoupling, partial-pooling, curriculum
> warm-start, resolution, longer training) is **refuted**; the ceiling is the **0-D box surrogate**
> (fields homogenize; a single global scalar cannot express Darwin's ~100× PIC:POC spread), not the
> optimizer or hardware. What remains is **~4–6 genuinely new experiments**, and every high-EV one is
> either **data-staging-blocked** or **requires leaving the 0-D box** (the differentiable-BGC UDE).

## The ~4–6 experiments that remain (ranked)

1. **Macronutrient (NO3/PO4) tracer + drawdown loss — the #1 root-cause lever.** Adds an independent
   nutrient currency that breaks *both* the Smallgrow↔Biggrow growth degeneracy *and* the alpfe
   loss-weighting weld (the iron-only box is the anomaly). **Data-staging-blocked** (NO3/PO4 not staged).
2. **Stage dense Darwin POSi (`TRAC16`) for diatomgraz** — the only way to adjudicate diatomgraz
   observability (prior v3.2 dense POSi → 10/10; sparse GEOTRACES bSi proxy never beats chance). Data-staging.
3. **Stage native primProd (diagnosed NPP)** as a Biggrow growth-flux anchor — the single remaining blocker
   for *robust* 6/6. Data-staging.
4. **Add a contrasting small-phyto oligotrophic gyre AOI (BATS-like)** to separate Smallgrow vs Biggrow
   (npsg at W=1.0 fixed Smallgrow but collapsed iron — needs a gentler/gated integration).
5. **n≥20/100 tie-break at geo1/dan2** — the 7/8/9/10-cell differences are within sampling noise at n=10.
6. **Real MODIS PIC + MODIS POC paired ratio anchor (obs/obs)** — makes R_PICPOC fully non-circular
   (~30-min loader extension).

**Strategic exit:** Stage-3 honest 6-param recovery on the higher-dimensional **differentiable-BGC UDE**
(feasibility-proven: self-twin closures recover to 0.5 %, spatial field to 0.44 % MAE) — the only path
carrying the spatial calcifier + macronutrient structure a 0-D box structurally cannot. See the
[Earth-2 coupling plan](../emulator_coupling_plan.md).

---

## Full matrix by lever axis

### Anchor (observation channel / loss target)
- 7-tracer carbonate joint DIC+ALK+CO2_flux (v2.0) — iron pair 3.3→1.1 % (alpfe) / halves scav_rat gap to 40 %
- GLODAP DIC+ALK real-obs target swap (v2.1) — R_PICPOC 3.6→0.738, scav_rat 0.40→0.92
- GEOTRACES absolute dissolved-iron anchor (v2.6) — the only valid iron anchor (Darwin-FeT pattern anti-correlated)
- GEOTRACES subsurface-DFe L2 / SUB_W (v2.7, 0/0.3/1.0) — nudges alpfe, scav_rat stuck 0.87–0.92
- L2 POC z-score POC_SUB_W (v2.8, Darwin-self) — first reproducible scav_rat 7/10
- PIC absolute anchor PIC_ABS_W — R_PICPOC 8–10/10 but **binary-wipes iron pair** (dose-independent)
- POC absolute anchor / paired PIC+POC — also kill iron pair
- Absolute-ALK anchor ALK_ABS_W (GLODAP, dose 1/10/100/300) — **NULL straddle** (cell-weighted artifact)
- Darwin-ALK source control (a100d) — reproduces straddle → generic magnitude deflation, not GLODAP info
- ALK high-dose a300 — deeper deflation, erodes iron pair, never genuine per-AOI recovery
- NN-TAlk (Broullon NDP-106) source — **untried** alternate ALK product
- PIC:POC ratio loss RATIO_W — R_PICPOC eqpac 10/10 orthogonal to iron pair; only eqpac (≥2-AOI 0/10)
- RATIO_MAX contaminated-target cap (1/2/5) — cap=2 clean R_PICPOC 10/10; robust 2→5
- **Scheduled ratio warmup (RATIO_SCHED_START=0.5) — BEST operating point** (first strict per-AOI 6/6, 1/10; R_PICPOC 10/10, iron 7/10, mean_cal 4.7)
- Daniels 2018 CP:PP real per-AOI anchor (DANIELS_RPICPOC_W) — load-bearing (dan0 3/10 vs 10/10, Fisher p=0.003); non-circular
- MODIS-Aqua PIC anchor (W sweep) — L4 first basin-A (alpfe 3/10); MODIS PIC 16–53× > Darwin
- MODIS+Darwin PIC blend (to W=0.1) — binary mutex holds
- Max-lever stack (PIC+POC+POSI+FCO2+chl1W+mehrbach) — **falsified** 0/20 at 5/6
- **Untried anchors:** TA*/excess-alkalinity gradient · sediment-trap Mouw RATIO_MAX value · cocco biomass (MAREDAT/PACE) · CbPM μ joint-sum · size-fractionated NPP/chl · 14C-PP · MOANA pico Smallgrow · PACE carbon_phyto · in-situ cocco counts · MODIS POC paired ratio · real GEOTRACES POC L2

### AOI-mix
- eqpac single (alpfe+diatomgraz 100 %, iron collapse) · eqp+natl (v3.0 5/6 in 7/15) · eqp+SO / natl+SO diagnostic pairs
- 3-AOI eqpac+natl+SO — iron pair 38/40 (95 %) headline; growth pair unconstrained
- npsg gyre (W 1.0/0.5/0.3) — fixes Smallgrow but collapses iron pair
- 4-AOI + Daniels — 50/50 all-six-per-AOI in 3/10 (tuned, non-robust)
- N Pac / Mid-Atl / Eq Pac single-basin; AOI-weight sweeps (SO binding, not sufficient alone)
- **Untried:** contrasting small-phyto (BATS-like) gyre AOI

### Architecture
- DINN vs DINNDeep — DINNDeep saturates r≈1.0 but recovers no more params (capacity ≠ ceiling)
- Per-cell vs global-scalar — 7/10 vs 0/10 trio (per-cell load-bearing; synthetic 15.2×)
- Per-AOI DINN — 2-AOI **falsified** (0/40); 3-AOI+CONSISTENCY_LAMBDA 1/10 5/6 (non-reproducible)
- Gradient gating (signal/ISO routing) — **refuted**
- Partial-pooling growth pair (POOL_PARAMS) — **refuted** (breaks R_PICPOC)
- Per-PFT K_Fe — **refuted** (alpfe not restored); per-PFT Q_Fe — untried
- AOI-ID / MLD input channels — no reproducible break
- 2-layer lumped-mapping prerequisite (Biggrow→diatoms) — untried structural blocker for growth anchors
- UDE neural-closure inside differentiable box (self-twin) — iron curve 0.5 %; spatial field 0.44 % MAE
- H200 GPU scaling of tiny-step closure — **refuted** (launch-bound)
- Early method-validation: 1D λ(z) 2.3 %, coupled N+P μ(z)+mortality(z) 6.1/8.6 %

### Forward-physics
- Eppley temperature USE_EPPLEY_T — **breaks alpfe↔silica mutex** (iron pair + diatomgraz recover together; best multi-AOI)
- W_SINK_PIC calcite-sink decoupling — **NULL** for R_PICPOC
- Coccolithophore-only calcite flag — **backfires**
- Per-PFT cocco-gated calcite ARRAY port (ADR-0001) — reproduces 3-basin spread via calcifier fractions; **never run as recovery**
- Non-cocco calcifier term (pteropod/foram) — untried fidelity rung
- Env-dependent rain ratio R_PICPOC=f(T,Ω_c,PO4) — env-ON recovery **refuted**; forward probe reproduces spread (log-MSE 0.000)
- 2-layer box geometry (v2.7) — modest alpfe nudge
- RK4 vs forward-Euler — RK4 < 0.001 % mass drift
- Integration-length/homogenization — AOI-means + PIC:POC converge by 200, IC-independent; fields homogenize (CV 4e-5→1e-15) → pattern-r not a fidelity metric
- Wanninkhof/K1K2 constant audit (~30–40 % F_CO2 offset) — re-run untried
- **Untried forward fixes:** macronutrient NO3/PO4 tracer · SiO2 + f_Si co-limitation · native PAR + real f_light · spatially-varying dust ironFile · per-cell MLD carbonate divisor · separate wPIC_sink · longer 1600-step iron spin-up

### IC (initial condition)
- Literature defaults vs Darwin v5 pickup IC (DARWIN_IC=1, v2.8) — enables alpfe-correct basin; fixes 30× FeT / 8× POC IC errors
- Spin-up/observation timing (50-day transient vs 200-day equilibrium) — timing drives identifiability more than epochs
- Two-stage curriculum warm-start — **refuted** (wipes basin-A gains)
- **Untried:** per-AOI initial state · ALK_IC_SHIFT confirmation · Carroll published 3D IC fields

### Resolution
- 1° box (~1000 cells) → selects scav_rat (8/10)
- Native LLC270 eqpac → selects alpfe (8/10); native 3-AOI joint 0/10 but SO-alone pair 5/5 (2026-07)
- Per-cell 128×128 (16,384 cells) — 5/6 under 11 %, scav_rat 36 % carries 0-D iron gap; CPU==GPU bit-identical
- Memory scaling linear at 5× (356 B/cell·step)
- **Untried/cluster-gated:** native single-AOI seasonal · global LLC270 seasonal (B200) · time-resolved 300+ monthly snapshots

### Weighting (loss-term weights / formulation)
- RATIO_W dose (0.5/1/2/4/30) + per-AOI RATIO_AOI_W — dose-robust eqpac
- Real-iron up-weight sweep (GEOTRACES_W/SUB_W 5×–33×) — 10× sweet spot (strict 6/6 3/10); alpfe↔Biggrow tradeoff
- hold-together sweep (base/geo1/geo3/dan0/dan2/noeppley/noposi) — geo1 7–8/10 trio; noposi only config holding all 4 (3/10)
- PINN drift (nb29, 0.05–5.0; w=3.0 → 4/6 best single-AOI) · PINN balance strict source-sink (nb28)
- Raw-FeT magnitude sweep (nb27, 0.01–3.0) vs z-scored FET_W — only raw-FeT moves alpfe (breaks scav_rat)
- PINN-drift + raw-FeT combos — don't stack
- POC_SUB_W bimodal-degeneracy sweep (0/0.3/1/3) — alpfe↔scav_rat basin switch; **Carroll joint NOT a local min**
- GLODAP loss 1/(NO3) vs z-scored — inverse-nitrate **refuted** (mapping artifacts)
- **Untried:** multi-tracer joint loss NO3+Chl+DIC+FeT with adaptive per-region weighting · native primProd/POSi/POFe targets

### Stats / robustness
- n=10 → n=20/40/50 (iron 38/40, 50/50) → n=200 (0/80 at 6/6) → n=856 (2/856 at 6/6) — structural ceiling
- Batched-seeds == sequential (0.0 diff); block-CV random r=0.995 vs spatial r=0.301 (interpolation not extrapolation)
- Self-twin identifiability (isolates method from proxy) · synthetic equifinality (alpfe sign flips under pattern AND absolute loss; Smallgrow consistent)
- 4-param NPZ steady-state vs time-resolved (μ 79→11 %, r_remin 308→88 %)
- **Untried:** n≥20/100 tie-break at geo1/dan2

### Diagnostics (identifiability / fidelity — not recovery levers)
- Empirical Fisher/CRLB; FD 6×6 Hessian (sloppy dir = pure Smallgrow); Hessian-at-Carroll indefinite
- Profile-likelihood: diatomgraz **FLAT** (gold-standard non-identifiable); alpfe full-loss 0.10 vs realiron 0.9997 (loss-weighting not structural)
- Box slow-mode linearization (one slow mode |eig|=0.9957, ~230-step)
- ALK forward signal probe (d ALK/dR_PICPOC ~60,000× weaker than PIC; gradient mis-directed)
- Per-AOI decomposition refutes ALK/Daniels co-recovery as straddling artifact
- Ensemble-disagreement trust map (in-domain outlier flag; extrapolation-detection FAILS)
- Box-vs-Darwin fidelity: PIC:POC ratio-of-means (box 0.0424 flat vs Darwin 100× spread) — IC-independent, stands
- Target-quantity pin (standing-stock vs export-flux) · cross-basin consistency (alpfe 0.5–0.7×, scav_rat 2–3×) · v2.7 iron-double-counting bug retraction · Carroll→Darwin3 namelist mapping · tunable-param inventory (Darwin1 6/103)

### Other (compute / infra)
- torch.compile launch-bound benchmark (236→80 ms/iter ~3×; earlier 0.8× was a benchmarking bug)
- No multi-process CUDA on Windows; single-process torch.compile runs on the 5090

---

*Provenance: 2026-07-03 multi-agent audit of `docs/archive/{findings,research_notes}/*.md` (353 raw records → 168 distinct). Framings marked refuted/null stand as negative results.*
