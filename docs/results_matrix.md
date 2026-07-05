# Config / Results Matrix

The single source of truth for **what each DarwinDiff configuration tested and what it
found**. [Project Status](status.md) links here for the current best; the
[archive](archive/index.md) holds the per-version writeups behind each row.

> This page is the **curated headline** (the configs that define the frontier). The
> **exhaustive record — all 168 distinct ablations across 10 lever axes — is the
> [Ablation Ledger](archive/ablation_ledger.md)**, together with the verdict below.
>
> **Verdict (2026-07-05):** Track 1 (this matrix, tables A/B) is **scientifically complete** — a
> *surrogate-to-model identifiability study*, not a 6/6 recovery chase. The **estimator /
> loss-weighting / box-structure space is exhausted** (~0 more box-tuning experiments worth
> running; every ceiling-breaker is refuted — the ceiling is the 0-D box surrogate, not the
> optimizer). The remaining high-EV levers are **not Track-1 box tuning**: they are **off-box /
> real-scale** and belong to Track 2 (the #1 being a **macronutrient NO3/PO4 tracer + drawdown
> loss** inside a transport-carrying differentiable model), or data-staging (dense POSi, native
> primProd, a small-phyto gyre AOI, an n≥20 tie-break, real MODIS obs/obs ratio). The strategic
> exit is the [differentiable-BGC UDE](emulator_coupling_plan.md) — Track 2, feasibility-proven
> on the box only and unbuilt at real scale.

**Scoring** ([`diagnostics.band_of`](dinn_design.md)): *Excellent* ≤ 5 % off Carroll ·
*Cal-grade* ≤ 40 %. Counts are `seeds-recovered / seeds-run`, every number gated by
[`scripts/verify_run.py`](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/scripts/verify_run.py)
(exit 0 = re-derived from raw). The honest target is **4 observable params**
{`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair
{`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real data constrains
growth rates) and is excluded from the target, not counted as a miss.

---

## A. Box-scale parameter-recovery configs (the spine)

> **Tables A/B = Track 1 (parameter learner, 0-D box) — a completed surrogate-to-model
> identifiability study.** It maps *which* Carroll-6 params are identifiable from real
> observations and *why*, not a 6/6 recovery chase: `alpfe` = method-independent,
> mass-balance-identified; `R_PICPOC` = recovers via a real calcite anchor (and a single global
> value is under-constrained — the bulk ratio should vary regionally); `scav_rat` = requires
> per-cell (weakest leg); `diatomgraz` + the growth pair = unobservable from staged data. Honest
> limit: this is a **consistency check against Carroll's own values, not a cross-validated
> discovery against the GCM** — held-out real-data R² is negative because the 0-D box homogenizes
> (the surrogate gap), which is a **finding**, not a flaw, and is what forces identifiability to
> come from real absolute anchors.

| Config | Scale / AOI | What it tested | Verified result | What's distinct |
|---|---|---|---|---|
| **v2.0** | 1° box, Eq Pac | 7-tracer carbonate joint loss (`carbonate.py`) | iron pair → **1.1 % (`alpfe`) / 40 % (`scav_rat`)** off Carroll | First degeneracy break — the carbonate cycle constrains the iron pair |
| **v2.6** | 1° box, Eq Pac | GEOTRACES IDP2025 **absolute-iron** MSE | **4/6 Cal-grade, reproducible n=10**; `diatomgraz` 9/10 | A real *absolute* iron anchor (not z-scored) is what moves `alpfe` |
| **v2.8** | 1° box, Eq Pac | Darwin v05 pickup ICs + L2 POC z-score | `scav_rat` **7/10 Cal (4/10 Excellent)** | First reproducible `scav_rat`; reveals (`alpfe`,`scav_rat`) bimodal degeneracy selected by `POC_SUB_W` |
| **v3.0** | 1° box, **2-AOI** (eqpac + natl) | Shared Carroll-6 joint multi-AOI training | **5/6 plateau** over 50+ seeds; mean_cal 3.93 | Establishes multi-AOI training; per-AOI DINN **falsified** at 2-AOI |
| **v3.1** | 1° box, **3-AOI** (+ SO Pac) | Basin C lever set (POSI + AOI_W + CHL1) | **iron pair 38/40 (95 %)** at n=40; 5/6 ceiling **2/856** | 3rd AOI makes the iron pair rock-solid; only 2 single-seed 5/6 in 856 |
| **v3.1.1** | 1° box, 4 AOI mixes (n=200) | AOI **ablation** | AOI mix *selects which* params recover; `eqp+natl` best ≥4/6 rate **24 %**; no mix → 6/6 | Recoverability is an AOI-attribution tradeoff, not a single ladder |
| **v3.2** | 1° box, 3-AOI | Eppley f(T) + **dense Darwin POSi** (TRAC16) | mean **3.85/6**; reproducible **5/6** (4/20, n=20); iron pair **+** `diatomgraz` together | First gain from *forward-model physics*; breaks the `alpfe`↔silica mutex. **`diatomgraz` here is vs Darwin's own silica, not real data** |

## B. Resolution & the R_PICPOC resolution

| Config | Scale / AOI | What it tested | Verified result | What's distinct |
|---|---|---|---|---|
| **native LLC270** | **Native** res, Eq Pac | Does native resolution change iron recovery? | Resolution *selects* which iron param recovers (native → `alpfe`, 1° → `scav_rat`; **8/10 each, per PRs [#122](https://github.com/2imi9/ECCO-DarwinDiff/issues/122) / [#123](https://github.com/2imi9/ECCO-DarwinDiff/issues/123)** — not archived) — it does **not** lift the recovery count ([cluster_setup.md](cluster_setup.md)) | Native resolution is not a 6/6 unlock — it reshuffles *which* iron param recovers |
| **R_PICPOC fix** (`RATIO_MAX` + Daniels) | 1° box, 3-AOI | Was `R_PICPOC` a "6/6 wall"? | **`R_PICPOC` 10/10**, landing at real ~0.05 (*consistent with* Carroll's 0.0425 within the ±40 % Cal band — not a validation) once the SO ratio target is sanitized (`RATIO_MAX=2`) + a real calcite anchor (Daniels CP:PP / MODIS) is added | **Refutes the "wall"**: the gap was a contaminated target + a missing real observation, not calcite physics or resolution. Deeper spine-D result: Carroll's *global* `R_PICPOC` is itself under-constrained and mis-specified vs a regionally-variable rain ratio (Daniels eqpac ~0.039, ≈1.6× global) |
| **`geo1` hold-together** _(current best)_ | 1° box, 3-AOI | Joint hold of the observable trio | **{`alpfe`, `scav_rat`, `R_PICPOC`} jointly 7/10** (3-of-4-observable frontier; tied with `base`/`dan2` at n=10) | The current operating point — real, Darwin-independent anchors hold 3 of 4 |
| **per-cell vs global** | 1° box, 3-AOI, `geo1` | Is the per-cell DINN load-bearing? | per-cell **7/10** vs global scalar **0/10** for the trio (`scav_rat` 8/0, `R_PICPOC` 9/0; Fisher p < 0.01) | Identifiability is **parameter-specific**: `alpfe` is **method-independent / mass-balance-identified** (a DINN-free global-scalar and a gradient-free estimator reach the same `alpfe` optimum), but `scav_rat` and `R_PICPOC` genuinely **require** the per-cell structure (0/10 without it). So the per-cell DINN is load-bearing for the trio, not a pattern-matching artifact against Darwin |

## C. Track-2 hybrid — feasibility only (self-twin / synthetic, **not** real Darwin)

> These are **feasibility probes on a self-twin**: the model fits data it generated itself.
> They show the differentiable-UDE machinery *runs* — **not** that Darwin has been made
> differentiable, that real biology was learned, or that environment-gated calcification is
> proven. Real-data results live in tables A/B.
>
> **Scope.** Track 2 is feasibility-proven **on the 0-D box only** (transport-free self-twin) and
> is **not built at real scale** — nothing runs beyond synthetic self-twin probes. The
> make-or-break is **E2: held-out real-data R² > 0 once transport is present** (this is what would
> turn the Track-1 consistency check into a discovery) — **UNBUILT**. The build path is **gated,
> riskiest-assumption-first**: Phase 1 = a minimal real-data transport UDE (regional 2-D, driven
> by ECCO-Darwin's own velocities) on real GEOTRACES iron + calcite, held-out scored (does
> transport close the surrogate gap on real data?); Phase 2 = a physical-backbone
> differentiability probe; Phase 3+ = the full coupled build. Two unproven gates: (1) transport
> closes the gap on real sparse obs (~14 iron cells); (2) gradients flow through a real physical
> backbone to a BGC UDE. See [emulator coupling plan](emulator_coupling_plan.md).

| Probe | Scale | What it tested | Verified result | Honest scope |
|---|---|---|---|---|
| **0-D hybrid probe** | 0-D box | Do the 4 UDE ingredients run on the real box equations? | All 4 pass: closure MAE **~0.5 %**, parameter to **2e-5 %**, RK4 drift < 0.001 % | Feasibility, self-twin synthetic |
| **spatial UDE probe** | 9,216-cell field | Can an env-modulated closure be learned over a *field*? | 2-D closure recovered **0.44 % MAE**; `torch.compile` ≈ 3× speedup | Feasibility of the spatial Track-2 thesis; still a synthetic twin |

---

## Reading the matrix

- **The current operating point is `geo1`** (table B): real GEOTRACES iron + a real Daniels/MODIS
  calcite anchor hold {`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 7/10 seeds. `diatomgraz` is an
  open iron-pair tradeoff (recoverable in principle via dense Darwin POSi/TRAC16, not yet staged).
- **"6/6" is the wrong frame.** The growth pair is unobservable; `R_PICPOC` was never a wall (table B
  refutes it). The honest target is the 4 observable params. The deeper spine-D result is that Carroll's
  *global* `R_PICPOC` is itself **under-constrained** and should be regional (the real rain ratio varies by
  AOI) — the recovery is *consistency within the wide Cal band*, **not** a validation of 0.0425.
- **The surrogate gap is dimensional.** At uniform parameters the 0-D box homogenizes to a near-uniform
  state (tracer CV → ~1e-15 vs Darwin's O(1)), so box-vs-Darwin *pattern* correlations are not fidelity
  metrics — identifiability comes from real *absolute* anchors, which is exactly what makes the per-cell
  DINN load-bearing (table B, per-cell vs global).
- **What Track 1 is (and isn't).** These recoveries are a **consistency check against Carroll's own
  published values within the wide Cal band — not a cross-validated discovery against the GCM.** A held-out
  real-data GEOTRACES test returns **negative R²** because the 0-D box homogenizes (the surrogate gap): the
  recovery pins parameter *magnitude* from real absolute anchors but cannot predict *which cell has how
  much*. That is a **finding** (identifiability must come from absolute anchors, not pattern-matching), and
  it is precisely what motivates Track 2's transport-carrying UDE — where the make-or-break E2 (held-out
  real R² > 0) lives.

## Provenance

Each row's underlying writeup is archived (verified research record, kept out of the onboarding path):

- v2.x / v3.x box-scale: [archive — findings](archive/index.md)
  (`v2.1`, `v2.2`, `v2.7`, `v2.8`, `v3.0`, `v3.1`, `v3.2` writeups).
- native LLC270 iron-pair: [cluster_setup.md](cluster_setup.md) (qualitative "selects which param /
  does not lift the count", in-repo) + PRs [#122](https://github.com/2imi9/ECCO-DarwinDiff/issues/122) /
  [#123](https://github.com/2imi9/ECCO-DarwinDiff/issues/123) (the per-seed 8/10 counts; verified record, not archived).
- `R_PICPOC` fix + `geo1` hold-together: [archive — hold-together sweep](archive/research_notes/2026-06-26_holdtogether_sweep_results.md),
  [ratio-loss structural note](archive/findings/rpicpoc_ratio_structural.md),
  [rain-ratio real-vs-Darwin — the "should be regional" finding](archive/findings/2026-06-26_rainratio_real_vs_darwin.md).
- per-cell vs global: [PR #158](https://github.com/2imi9/ECCO-DarwinDiff/pull/158),
  [archive — box homogenization](archive/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md).
- Track-2 feasibility: [archive — hybrid feasibility note](archive/research_notes/2026-06-29_hybrid_differentiable_bgc_feasibility.md),
  [archive — spatial UDE](archive/findings/2026-06-30_spatial_ude.md); forward path + backbone survey
  (Samudra 2 physical-ocean backbone, SamudrACE's explicit BGC hole = our Option-C carbon-BGC-UDE slot;
  ACE2/OlmoEarth surveyed and rejected) in the [emulator coupling plan](emulator_coupling_plan.md) —
  **gated on Paper #1 shipping and unbuilt at real scale**.
