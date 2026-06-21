# AICR Parameter-Learner Memory & Compute Budget

**Status: DRAFT — grounded estimates, NOT yet proposal-ready.** The formula and the
measured constant are sound and verified; the headline per-fit GPU number needs the
reframing in §3 before it goes on the AICR form, and a few inputs (§5) remain
unmeasured until Explorer. Derived 2026-06-19 (multi-agent extraction + two adversarial
verifiers; arithmetic independently re-checked). **Scope correction added 2026-06-20
(§0): the §2–§3 tables are global-scale; the near-term AICR experiments are 3 regional
AOIs, ~30× smaller. Wall-clock per composition now MEASURED (§3.5,
`scripts/measure_compute_time.py`): time is flat in cells (native ≈ 1°) and linear in
steps — every fit is launch-bound, so a B200 buys throughput, not single-fit speed.**

## 0. Scope — AOI (near-term) vs global (paper #3) — read first

**The §2–§3 tables are GLOBAL-scale.** The actual near-term AICR experiments are **3
regional AOIs**, not the whole ocean: `cluster_roadmap.md` puts native 3-AOI and
time-resolved 3-AOI in paper #2, and **global ocean coverage in Direction E / Tier 2 /
paper #3**. At AOI scale the per-fit memory is ~30× smaller, and the headline conclusion
flips: **a single native 3-AOI seasonal fit ≈ 26 GiB — fits the free Explorer H200 (just
over the 5090's 24 GB).** The memory-based
"needs 4–8 GPU" case appears only at global scale.

**Definitions.** `b1`/`b10` = batch = seeds trained together (batched so torch.compile
amortizes JIT; a 10-seed batch ≈ 7 min vs ~70 min serial). `time-mean` = the 23-year
(Jan 1995–Dec 2017) monthly v05 output averaged to **one annual field** (200 integration
steps);
`seasonal` = a **12-month climatology** (~2000 steps, ~12 phase constraints/param);
`time-resolved` (Direction A) = **~300 monthly snapshots** — same memory per snapshot via
gradient accumulation, but ~300× the wall-clock (a throughput cost, not a memory one).

**All-compositions matrix** (peak GiB, pre-checkpoint, ocean-cell basis, **cell counts
measured** via `scripts/measure_compute_budget.py` — only LLC90 wet is estimated;
checkpointing ÷5–15 shifts each ~1–2 GPU tiers lower). Figure: `figures/compute_budget_matrix.svg`.

| Scope (ocean cells) | time-mean ×1 | ×10 | seasonal ×1 | ×10 |
|---|---|---|---|---|
| 1-AOI @ 1° (1.1k) | 0.07 | 0.7 | 0.7 | 7 |
| 3-AOI @ 1° — *current* (2.9k) | 0.2 | 1.9 | 1.9 | 19 |
| 1-AOI @ native LLC270 (9.8k) | 0.6 | 6.5 | 6.5 | 65 |
| **3-AOI @ native — *the ask* (38,809 meas)** | 2.6 | 26 | **26** | 257 |
| global @ LLC90 (61k est) | 4.0 | 40 | 40 | 403 |
| global @ LLC270 — *paper #3* (546,695 meas) | 36 | 363 | 363 | 3625 |

Smallest real machine per fit: **≤24 GiB → RTX 5090** (now) · **≤144 → Explorer H200**
(144 GB, ×32, free) · **≤192 → 1× AICR B200** · **>192 → ≥2 GPU** (sharding, not built) ·
**>768 → waves**. Per `cluster_setup.md`, Explorer H200 is the active near-term path and
holds a native fit on one card; AICR B200 is the target for the global-native + seasonal
**sweep**. With the **measured** cell counts, AICR B200 enters at the **batched native
seasonal fit** (3-AOI native · seasonal · ×10 = **257 GiB → 2× B200**) and scales to the
global batched seasonal sweep (3,625 GiB → ~19× B200); **every single-seed fit — including
the near-term ask (26 GiB) — runs on the free Explorer H200**. Cell-count bases (all
measured via `scripts/measure_compute_budget.py`): eqpac 9,750, natlsubpolar 7,939,
southernoceanpac 21,120 → **3-AOI native 38,809**; global LLC270 surface ocean **546,695**.
The high-latitude AOIs are ~16× their 1° count (denser than eqpac's 9.1×), so the measured
38,809 is ~50% above the prior 9.1× estimate. Only LLC90 wet stays estimated (the repo never
loads LLC90). Full provenance in §6.

**Reframed conclusion.** Near-term (3-AOI native) is **one-GPU memory-wise** *and*
**one-GPU speed-wise**: wall-clock is now **measured** flat in cells (§3.5 — native ≈ 1° to
1.04×, every fit launch-bound), so a single native fit is **~7 min** (time-mean) to **~½–1 h**
(seasonal) on the **free** Explorer H200, and a B200 does **not** make it faster. The cluster
is justified purely by **throughput** — time-resolved is ~300× the wall-clock and sweeps are
serial on the laptop (a 21-arm sweep ≈ 4 h) — **not** single-fit memory or single-fit speed.
The deck's global ~100 GB / 4–8-GPU figure is **paper-#3 (global) scope** and should not
anchor the AOI-scale paper-#2 ask. Memory forces multi-GPU only at global, or at 3-AOI native
with batched seeds (×10 ≈ 257 GiB → 2× B200, same wall-clock, 10× throughput).

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
~26 GiB — the free Explorer H200**; the multi-GPU/B200 case is the batched native sweep
(≥2× B200) and global (paper #3).

## 3.5 Wall-clock per composition — MEASURED (time ⊥ cells, time ∝ steps)

The other half of "how long does each cost." Previously **assumed** ("~1 h/run, ~0 % GPU
util"); now **measured** on the 5090 with `scripts/measure_compute_time.py` — it times one
full `DINN → integrate → loss → backward` epoch (the same value-independent graph the memory
harness uses) across cell counts and step counts. Two clean laws fall out:

- **Wall-clock is flat in cells.** 2,853 → 105,300 cells (**37×**) moves a 200-step epoch
  only **1.82 → 1.90 s = 1.04×**. Per-step holds at **~9.2 ms eager** regardless of grid
  size; per-cell·step *drops* 35× (3,182 → 90 ns) as the fixed step cost amortizes over more
  cells. The linear fit `t = 1.83 s + 576 ns/cell·cells @ 200 steps` puts the
  compute-vs-fixed crossover at **~3.2 M cells** — so everything through LLC90 *and* LLC270
  (947 k) is **launch / Python-loop bound (~0 % GPU util, now confirmed)**, not compute-bound.
- **Wall-clock is exactly linear in steps.** 50 → 1,600 steps scales 0.46 → 14.75 s, per-step
  pinned at ~9.2–9.5 ms (R²≈1). So seasonal (2000 steps) = **10× the integration** of
  time-mean (200), and time-resolved (~300 monthly snapshots) ≈ **300×** — a pure throughput
  cost, matching `cluster_setup.md`'s ~25 h time-resolved figure.

**Anchor (compiled, production, 5090):** a 3-AOI 1° time-mean fit = 1500 epochs × 200 steps
≈ **7 min** (`cluster_setup.md:197`, `torch.compile` batched; a 10-seed batch and a single
seed both ≈ 7 min — compile/JIT amortization makes batching ~free). Compiled per-step ≈
1.4 ms, ~6.6× under the 9.2 ms eager I measured. Scaling the anchor by the **measured** laws
(×1.0 for cells, ×(epochs·steps)/(1500·200) for trajectory):

| Composition | epochs × steps | 5090-class wall-clock | smallest machine · why |
|---|---|---|---|
| 3-AOI @ 1° · time-mean ×1 | 1500 × 200 | **~7 min** | 5090 — measured anchor |
| 3-AOI @ native · time-mean ×1 | 1500 × 200 | **~7 min** | 5090 — native ≈ 1° (×1.04 measured) |
| **3-AOI @ native · seasonal ×1 — the ask** | 600–1500 × 2000 | **~0.5–1.2 h** | **free Explorer H200** (26 GiB); *not faster on a B200* |
| 3-AOI @ native · seasonal ×10 (batch) | 600–1500 × 2000, b10 | **~0.5–1.2 h** | 2× B200 *for memory* (257 GiB); 10× throughput, same wall-clock |
| 1-AOI · time-resolved (~300 mo) ×1 | ~300 snapshots | **~25 h** | the genuine throughput wall (Track 2) |
| global LLC270 · seasonal ×1 | 600–1500 × 2000 | **~0.5–1.5 h / fit** | 2× B200 *for memory* (363 GiB); a sweep = many such fits |

**The conclusion — a B200 buys throughput, not single-fit speed.** Because every fit is
launch-bound, one fit takes ~the same wall-clock on the 5090, the free H200, *and* a B200 —
minutes for time-mean, ~½–1 h for seasonal, at any resolution. The cluster's wall-clock value
is (1) **memory** to hold batched/global graphs (§2) and (2) **concurrency** to run a sweep's
hundreds of fits — and the 300×-longer time-resolved trajectories — in parallel rather than
serially. This is the time-domain twin of the memory finding: the near-term science is fast
and cheap per fit; the cluster scales the *program* (sweep × seeds × time-resolved), not the
*fit*. (Caveat: per-step is measured **eager**; on the cluster `torch.compile` runs and the
production anchor is already compiled — the one thing left to confirm on Explorer is whether
compile reintroduces any cell-sensitivity at native ×10, where effective width is ~400 k.)

## 4. GPU-hours

```
total_GPU_hours  =  #fits × GPUs_per_fit × wall_clock_per_fit
                    (concurrency sets calendar/wall-clock time, NOT total GPU-hours)
```
where `#fits = #configs × #seeds` if seeds run as separate jobs, or `#configs` if seeds
are batched into one fit. Concurrency only shortens how long the program takes on the
calendar — it does not change the GPU-hours consumed.

**Per-fit wall-clock is now MEASURED at the per-step level** (§3.5,
`scripts/measure_compute_time.py`): ~9.2 ms/step eager, flat in cells to 1.04× across 37×,
linear in steps — so native ≈ 1° and a native time-mean fit ≈ **7 min**, native seasonal ≈
**½–1.2 h**, time-resolved (~300 mo) ≈ **25 h**, all launch-bound (~0 % GPU util **confirmed**
— this *does* flag AICR idle-GPU-reaper risk, now a measured fact not a guess). What remains
unmeasured is only the **end-to-end native fit on the cluster under `torch.compile`** (eager
per-step measured here; compiled production anchor is the 1° 7-min number). With per-fit time
pinned, **GPU-hours = #configs × #seeds × per-fit-time** is now decomposable instead of an
order-of-magnitude guess: e.g. 100 configs × 10 seeds batched = 100 native-seasonal jobs ×
~½–1.2 h ≈ **50–120 GPU-hr** of B200 (batched), vs the headline ~8,000 that conflated global
scope + serial seeds. Documented planning ranges (`cluster_roadmap.md`): native LLC270
100–500 GPU-hr/fit (now look high — that assumed compute-bound scaling the measurement
refutes); Paper-#2 program total **1,000–5,000 GPU-hr**. **Recompute the ask from the
measured per-fit time + the actual sweep design before it goes on the form.**

## 5. Before this goes in the proposal

Fixes:
1. **Scope correctly (§0):** near-term ask = 3-AOI native (~26 GiB/fit on the **free**
   Explorer H200, throughput-justified). Restate per-fit memory at the *right scope* — AOI
   ~26 GiB → free H200; the batched native sweep → 2× B200; global → paper #3 — and stop
   anchoring the AOI ask on the deck's global ~100 GB / 4–8-GPU number.
2. ✓ Cell counts now **measured** (`scripts/measure_compute_budget.py`): 3-AOI native
   **38,809**, global LLC270 **546,695**. Only LLC90 wet remains an estimate.
3. Label **checkpoint-on** rows estimate-pending (factor ~5–15×, unmeasured; not a flat 10×).
4. Use **2000** seasonal steps (with spin-up), not 1464 (bare cycle) — spin-up is required.
5. Reconcile doc drift: laptop VRAM **23.9 vs 32 GB**; sweep totals **856/86** (canonical)
   vs 847/85 vs 1056.

Inputs to measure on Explorer (Fri) / at runtime:
- ✓ **wall-clock + GPU util** now MEASURED (§3.5): per-step ~9.2 ms eager, flat in cells,
  linear in steps, ~0 % util confirmed. Only the **end-to-end native fit under
  `torch.compile`** (Linux) is left to time — and to check compile doesn't reintroduce
  cell-sensitivity at native ×10.
- **compiled** memory constant (only eager 356 measured; torch.compile can't run on the
  Windows laptop) → likely lower, so 356 is a conservative upper bound.
- **LLC90 wet count** — the only cell count still estimated (the repo never loads LLC90).
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
| natlsubpolar cells | 486 (1°) → **7,939** (native) = 16.3× | `measure_compute_budget.py` | MEASURED |
| southernoceanpac cells | 1,296 grid (1°) → **21,120** (native) = 16.3× | `measure_compute_budget.py` | MEASURED (native) |
| 3-AOI @ 1° | 2,853 | sum of the three | MEASURED + DERIVED |
| 3-AOI @ native | **38,809** (9,750 + 7,939 + 21,120) | `scripts/measure_compute_budget.py` | MEASURED |
| LLC90 grid / wet | 105,300 / ≈61k | geometry / 57.7% fraction | DERIVED / ESTIMATE (LLC90 not loaded) |
| LLC270 grid / ocean cols | 947,700 / **546,695** | `nb13:165`; `measure_compute_budget.py` | MEASURED (ocean columns = the box's cells) |
| checkpoint factor | 5× measured; ~10× planned; 14–38× (√N) | `research_log.md:140`; `compute_ladder.md:100` | 1 MEASURED point; rest PLANNED / THEORY |
| wall-clock/fit (1°) | 7–8 min (10-seed ≈ 7 min, compiled) | `cluster_setup.md:197` | MEASURED (1° box, production) |
| per-step time | ~9.2 ms eager (~1.4 ms compiled) | `measure_compute_time.py` | MEASURED (5090, eager) |
| time vs cells | flat: 1.04× over 2,853→105,300 (37×) | `measure_compute_time.py` | MEASURED (launch-bound; native ≈ 1°) |
| time vs steps | linear, per-step const (R²≈1) | `measure_compute_time.py` | MEASURED (seasonal=10×, time-resolved≈300×) |
| wall-clock/fit (native) | ~7 min time-mean / ~½–1.2 h seasonal | derived from measured per-step × epochs×steps | DERIVED from MEASURED (eager; compile speeds it) |
| GPU util (native) | ~0 % (Python-loop-bound) | `measure_compute_time.py` (1.04× over 37× cells) | MEASURED — confirms reaper risk |
| compiled constant | ≤356 (eager only measured) | `pre_scaleup_verification.md:44` | UNMEASURED (compile can't run on Windows) |
| RTX 5090 | 24 GB (laptop; STATUS says 32 — drift) | `budget.py:35` | MEASURED (drift flagged) |
| Explorer H200 | 144 GB ×32, free | `cluster_setup.md:11,35` | MEASURED (spec) |
| AICR B200 | 192 GB ×248 | `cluster_setup.md:12`; `budget.py:37` | MEASURED (spec) |
| GPU-hours total | ~8,000 (o.o.m.); 1,000–5,000 planned | `AICR_email_to_Jon.md:24`; `cluster_roadmap.md:194` | ESTIMATE (needs wall-clock) |

**Still unmeasured — the only things blocking a firm budget:** the compiled memory constant,
the checkpoint factor, the LLC90 wet count (the repo never loads LLC90), and the end-to-end
native fit *under compile* on the cluster. Cell counts (`measure_compute_budget.py`) and the
per-step wall-clock / cell-flatness / step-linearity (`measure_compute_time.py`) are now
**measured**; the rest are single Explorer-H200 measurements.

See [[aicr-compute-ask]] (memory). LLC90-vs-LLC270 is Jon's "start at LLC90, go to LLC270
if it fits" (2026-06-16).
