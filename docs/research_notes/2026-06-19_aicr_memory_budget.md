# AICR Parameter-Learner Memory & Compute Budget

**Status: DRAFT — grounded estimates, NOT yet proposal-ready.** The formula and the
measured constant are sound and verified; the headline per-fit GPU number needs the
reframing in §3 before it goes on the AICR form, and several inputs (§5) are
unmeasured until Explorer. Derived 2026-06-19 (multi-agent extraction + two adversarial
verifiers; arithmetic independently re-checked). **Scope correction added 2026-06-20
(§0): the §2–§3 tables are global-scale; the near-term AICR experiments are 3 regional
AOIs, ~30× smaller.**

## 0. Scope — AOI (near-term) vs global (paper #3) — read first

**The §2–§3 tables are GLOBAL-scale.** The actual near-term AICR experiments are **3
regional AOIs**, not the whole ocean: `cluster_roadmap.md` puts native 3-AOI and
time-resolved 3-AOI in paper #2, and **global ocean coverage in Direction E / Tier 2 /
paper #3**. At AOI scale the per-fit memory is ~30× smaller, and the headline conclusion
flips: **a single native 3-AOI seasonal fit ≈ 17 GiB — fits the free Explorer H200 (or the
5090, tight).** The memory-based
"needs 4–8 GPU" case appears only at global scale.

**Definitions.** `b1`/`b10` = batch = seeds trained together (batched so torch.compile
amortizes JIT; a 10-seed batch ≈ 7 min vs ~70 min serial). `time-mean` = the 23-year
(1992–2017) monthly v05 output averaged to **one annual field** (200 integration steps);
`seasonal` = a **12-month climatology** (~2000 steps, ~12 phase constraints/param);
`time-resolved` (Direction A) = **~300 monthly snapshots** — same memory per snapshot via
gradient accumulation, but ~300× the wall-clock (a throughput cost, not a memory one).

**All-compositions matrix** (peak GiB, pre-checkpoint, ocean-cell basis; checkpointing
÷5–15 shifts each ~1–2 GPU tiers lower; cell counts are estimates, so read the values as
~2 sig figs). Figure: `figures/compute_budget_matrix.svg`.

| Scope (ocean cells) | time-mean ×1 | ×10 | seasonal ×1 | ×10 |
|---|---|---|---|---|
| 1-AOI @ 1° (1.1k) | 0.07 | 0.7 | 0.7 | 7 |
| 3-AOI @ 1° — *current* (2.9k) | 0.2 | 1.9 | 1.9 | 19 |
| 1-AOI @ native LLC270 (9.8k) | 0.6 | 6.5 | 6.5 | 65 |
| **3-AOI @ native — *the ask* (~26k est)** | 1.7 | 17 | **17** | 170 |
| global @ LLC90 (61k est) | 4.0 | 40 | 40 | 400 |
| global @ LLC270 — *paper #3* (547k surf-meas) | 36 | 360 | 360 | 3600 |

Smallest real machine per fit: **≤24 GiB → RTX 5090** (now) · **≤144 → Explorer H200**
(144 GB, ×32, free) · **≤192 → 1× AICR B200** · **>192 → ≥2 GPU** (sharding, not built) ·
**>768 → waves**. Per `cluster_setup.md`, Explorer H200 is the active near-term path and
holds a native fit on one card; AICR B200 is the target for the global-native + seasonal
**sweep**. The one cell in the 144–192 GiB band is the **batched native seasonal fit**
(3-AOI native · seasonal · ×10 ≈ 170 GiB): it exceeds the free H200's 144 GB, so it is
**B200's concrete single-card role** — and it sits right at the line (~170 GiB at the
measured-eqpac 9.1× basis; ~220 → 2 B200 if the high-latitude AOIs are denser). Every
single-seed fit runs on the 5090 or the free H200. Cell-count bases: AOI-native = eqpac
**measured** (9,750 = 9.1× its 1,071); 3-AOI native ≈ 26k (9.1× applied to all three — a
lower bound); global = LLC270 surface ocean **measured 546,695** (LLC90 wet est. 61k via the
same 57.7% fraction; the repo never loads LLC90). Full provenance in §6.

**Reframed conclusion.** Near-term (3-AOI native) is **one-GPU memory-wise**; the cluster
is justified by **throughput** — time-resolved is ~300× the wall-clock and sweeps are
serial on the laptop (a 21-arm sweep ≈ 4 h) — **not** single-fit memory. The deck's global
~100 GB / 4–8-GPU figure is **paper-#3 (global) scope** and should not anchor the AOI-scale
paper-#2 ask. Memory forces multi-GPU only at global, or at 3-AOI native with batched seeds
(×10 ≈ 199 GiB).

## 1. Memory model

```
peak_activation_GiB  =  356 B × horizontal_cells × steps × batch  /  2^30
```

- **Constant 356 B/(cell·step)** — MEASURED, eager mode, RTX 5090 Laptop; linear to
  21.24 GiB @ 64 M cell·step, R²≈1, no bend at 5× (`pre_scaleup_verification.md:40–46`).
  Harness on unmerged PR #102. *Recompute check:* 356 × 64e6 / 2³⁰ = **21.22 GiB** ✓
  (the 0.1 % residual is rounding of 356 → ~356.4, not a unit artifact).
- **Units are GiB** (÷2³⁰), not decimal GB — the docs write "GB" loosely. Decimal GB
  inflates implied cells 1.074×.
- **The constant already folds in** all **15 tracers**, **both layers** (one 15-vector
  2-layer column = the "cell" — do **not** multiply by 2 for layers), and the full
  reverse-mode autograd intermediate set (≈5.9× the bare 60-B state). dtype float32.
- **Batch is a separate multiplier** (batched seeds ≡ sequential, exact 0.0 diff).
- The deck/email say "~11 tracers" — a harmless verbal undercount (the empirical 356
  fit already reflects all 15); correct it to "15 (10 surface + 5 subsurface)."

## 2. Table — GLOBAL scale (all-cell grid basis; the near-term AOI scope is in §0)

Grid horizontal cells: LLC90 = 13×90² = **105,300**; LLC270 = 13×270² = **947,700**
(standard LLC geometry). Steps: time-mean = 200; **seasonal = 2000** (12 mo × ~122 +
required spin-up). All peaks pre-checkpointing.

| Grid | Steps | batch | Peak (GiB) | Fits on |
|---|---|---|---|---|
| LLC90 (~1°) | time-mean 200 | 1 | **7.0** | laptop / H100 / B200 |
| LLC90 | seasonal 2000 | 1 | **69.8** | 1× H100 / B200 |
| LLC90 | seasonal 2000 | 10 | 698 | 4× B200 |
| **LLC270 (~⅓°)** | time-mean 200 | 1 | **62.8** | 1× H100 / B200 |
| LLC270 | time-mean 200 | 10 | 628 | 4× B200 |
| **LLC270** | **seasonal 2000** | **1** | **628** | **~4× B200** ← the per-fit ask |
| LLC270 | seasonal 2000 | 10 | 6284 | wave-schedule (~33× B200) |

- **Checkpointing** (planned, Stage 2) divides these by **~5–15×** (unmeasured — repo's
  only datapoint is 5×, `research_log.md`; budget.py notes peak ≠ 1/K; √N implies
  ~14×@200 / ~38×@2000). So a single LLC270 seasonal fit with checkpointing ≈ **40–125
  GiB → 1 B200.** Treat all checkpoint-on numbers as estimate-pending-measurement.
- **Wet-cell refinement:** the table uses *all* grid cells (conservative upper bound).
  Only the surface ocean count is measured (validNO3 = **546,695** ≈ 58 % of LLC270 grid,
  `nb13`); a true 2-layer ocean-column count needs `ocean_mask.sum()` at runtime. Wet
  scaling (~0.58–0.85×) lowers the LLC270 seasonal b1 fit to ~365–535 GiB → still 2–3 B200.
- **Multi-GPU rows mark work-to-build, not current capacity.** A ">192 GiB → N× B200"
  entry is *not* a runnable placement today: `scripts/slurm/run_aicr_b200.sbatch` notes
  multi-GPU is not automatic (needs torchrun/DDP/NCCL cell-sharding). Until that exists,
  an oversized fit OOMs on a 1-GPU job and reserving N B200 just idles the extras — so the
  realistic single-GPU path for a large fit is **checkpointing onto one GPU**, and the N×
  B200 rows are a sharding target, not a capability that works now.

## 3. The key finding — the per-fit GPU justification needs reframing

The proposal's load-bearing line is *"~100 GB peak → exceeds one 80 GB H100 → 4–8 GPUs
per fit."* That does **not** hold as written:

- A single native LLC270 **time-mean** fit = **~63 GiB → fits ONE H100/B200.** The
  email's "~100 GB at ~200 steps" is internally inconsistent: 200 steps at all-cells is
  63 GiB, not 100.
- The genuine multi-GPU need comes from the **seasonal** fit (2000 steps): **~628 GiB →
  ~4 B200** — which is exactly the "4–8 GPU/run" bracket, and the proposal *is* asking
  for a seasonal run. So **restate the per-fit anchor as the seasonal ~630 GiB number
  (→ 4 B200), not "~100 GB at 200 steps."** That makes the ask internally consistent and
  defensible. Batching (×seeds) is the other legitimate multi-GPU driver.

Net (global scale): the seasonal trajectory length and batching — not a single time-mean
fit — drive the multi-GPU need. **At the near-term AOI scale (§0) a single seasonal fit is
~17 GiB, one GPU**; the multi-GPU/memory case is a global (paper-#3) phenomenon.

## 4. GPU-hours

```
total_GPU_hours  =  #fits × GPUs_per_fit × wall_clock_per_fit
                    (concurrency sets calendar/wall-clock time, NOT total GPU-hours)
```
where `#fits = #configs × #seeds` if seeds run as separate jobs, or `#configs` if seeds
are batched into one fit. Concurrency only shortens how long the program takes on the
calendar — it does not change the GPU-hours consumed.

**Wall-clock per native fit is UNMEASURED** — the "~1 h/run" is assumed
(`pre_scaleup_verification.md:90–94`), and native GPU util ("~0 %", Python-loop-bound)
is assumed too (and risks the AICR idle-GPU reaper). Measured wall-clock exists only at
1° box (10-seed batch ~7 min). Documented planning ranges (`cluster_roadmap.md`, all
estimates): native LLC270 100–500 GPU-hr/fit; Paper-#2 program total **1,000–5,000
GPU-hr**. The headline **~8,000 GPU-hr** ask is an explicit order-of-magnitude, not yet
decomposed into fits × wall-clock. **Do not firm this up until Explorer measures
wall-clock + util.**

## 5. Before this goes in the proposal

Fixes:
1. **Scope correctly (§0):** near-term ask = 3-AOI native (~17 GiB/fit, one GPU,
   throughput-justified). Restate per-fit memory at the *right scope* — AOI ~17 GiB → 1 GPU;
   global ~630 GiB → 4 B200 is paper #3 — and stop anchoring the AOI ask on the deck's
   global ~100 GB number.
2. Use **all-cell** grid counts as the committed basis; label wet-cell rows as pending
   `ocean_mask.sum()`; present estimates as ranges, not 3 sig figs.
3. Label **checkpoint-on** rows estimate-pending (factor ~5–15×, unmeasured; not a flat 10×).
4. Use **2000** seasonal steps (with spin-up), not 1464 (bare cycle) — spin-up is required.
5. Reconcile doc drift: laptop VRAM **23.9 vs 32 GB**; sweep totals **856/86** (canonical)
   vs 847/85 vs 1056.

Inputs to measure on Explorer (Fri) / at runtime:
- **wall-clock per native fit + GPU util** → sets GPU-hours and reaper risk.
- **compiled** memory constant (only eager 356 measured; torch.compile can't run on the
  Windows laptop) → likely lower, so 356 is a conservative upper bound.
- **global wet-cell counts** via `ocean_mask.sum()` (only surface validNO3 measured).
- **checkpoint reduction factor** + its ~2× wall-clock trade.

## 6. Every input — value · source · status

| Input | Value | Source | Status |
|---|---|---|---|
| Memory constant | 356 B/(cell·step) | `carroll6_5pft_2layer.py:484`; `pre_scaleup_verification.md:41` | MEASURED (eager, 5090; harness on PR #102) |
| Linear-scaling anchor | 21.24 GiB @ 64 M cell·step | `pre_scaleup_verification.md:40–41` | MEASURED |
| State / dtype | 15 tracers, 2 layers, float32 | `carroll6_5pft_2layer.py:117,96–115` | MEASURED (code) |
| time-mean steps | 200 | `dinn_design.md:96,111` | config constant |
| seasonal steps | 1,464 bare (12×122); 2,000 used (w/ spin-up) | `carroll6_5pft_2layer.py:483`; `pre_scaleup_verification.md:16` | DERIVED; spin-up cycle count UNMEASURED |
| batch | 1 / 10 seeds (batched ≡ sequential) | `pre_scaleup_verification.md:15` | MEASURED |
| eqpac cells | 1,071 (1°) → 9,750 (native) = 9.1× | `nb14:172,236` | MEASURED |
| natlsubpolar cells | 486 (1°) | `obs_pic_poc_per_aoi.csv:3` | MEASURED (1°); native UNMEASURED |
| southernoceanpac cells | 1,296 grid (1°) | `ecco_darwin_loader.py:117` | DERIVED (grid bins); ocean count UNMEASURED |
| 3-AOI @ 1° | 2,853 | sum of the three | MEASURED + DERIVED |
| 3-AOI @ native | ≈26k (9.1×) … 33k (11.7×) | `research_log.md:249` | ESTIMATE; pin via `ocean_mask.sum()` |
| LLC90 grid / wet | 105,300 / ≈61k | geometry / 57.7% fraction | DERIVED / ESTIMATE (LLC90 not loaded) |
| LLC270 grid / surf-ocean | 947,700 / **546,695** | `llc270_loader.py:117` / `nb13:165` | DERIVED / MEASURED (surface); column-wet UNMEASURED |
| checkpoint factor | 5× measured; ~10× planned; 14–38× (√N) | `research_log.md:140`; `compute_ladder.md:100` | 1 MEASURED point; rest PLANNED / THEORY |
| wall-clock/fit (1°) | 7–8 min (10-seed ≈ 7 min) | `cluster_setup.md:138`; `dinn_design.md:113` | MEASURED (1° box) |
| wall-clock/fit (native) | "~1 h" | `pre_scaleup_verification.md:90` | ASSUMED, UNMEASURED |
| GPU util (native) | "~0 %" (Python-loop-bound) | `pre_scaleup_verification.md:90–94` | ASSUMED, UNMEASURED |
| compiled constant | ≤356 (eager only measured) | `pre_scaleup_verification.md:44` | UNMEASURED (compile can't run on Windows) |
| RTX 5090 | 24 GB (laptop; STATUS says 32 — drift) | `budget.py:35` | MEASURED (drift flagged) |
| Explorer H200 | 144 GB ×32, free | `cluster_setup.md:11,35` | MEASURED (spec) |
| AICR B200 | 192 GB ×248 | `cluster_setup.md:12`; `budget.py:37` | MEASURED (spec) |
| GPU-hours total | ~8,000 (o.o.m.); 1,000–5,000 planned | `AICR_email_to_Jon.md:24`; `cluster_roadmap.md:194` | ESTIMATE (needs wall-clock) |

**Still unmeasured — the only things blocking a firm budget:** native wall-clock + GPU util,
the compiled memory constant, the true ocean-column counts (natl/SO native, LLC90 wet,
LLC270 column-wet), and the checkpoint factor. Each is a single Explorer-H200 measurement.

See [[aicr-compute-ask]] (memory). LLC90-vs-LLC270 is Jon's "start at LLC90, go to LLC270
if it fits" (2026-06-16).
