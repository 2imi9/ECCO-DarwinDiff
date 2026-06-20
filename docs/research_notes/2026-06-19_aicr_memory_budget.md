# AICR Parameter-Learner Memory & Compute Budget

**Status: DRAFT — grounded estimates, NOT yet proposal-ready.** The formula and the
measured constant are sound and verified; the headline per-fit GPU number needs the
reframing in §3 before it goes on the AICR form, and several inputs (§5) are
unmeasured until Explorer. Derived 2026-06-19 (multi-agent extraction + two adversarial
verifiers; arithmetic independently re-checked).

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

## 2. Table (all-cell grid basis — the committed, reproducible figures)

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

Net: the ask size is right; the *justification* should cite the seasonal trajectory
length (and batching), not a single time-mean fit.

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
1. Restate per-fit memory as the **seasonal** number (~630 GiB → 4 B200), per §3.
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

See [[aicr-compute-ask]] (memory). LLC90-vs-LLC270 is Jon's "start at LLC90, go to LLC270
if it fits" (2026-06-16).
