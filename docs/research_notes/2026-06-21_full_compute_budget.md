# DarwinDiff Compute Budget — Full Task Ladder

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data/plans stand, framing corrected by [STATUS.md](../../STATUS.md). The project is a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC} — **not** a 6/6 chase or a '5/6 ceiling / parameter-conservation' result. The growth pair {Smallgrow, Biggrow} is unobservable by construction. **R_PICPOC is recoverable** at 1° with a real calcite anchor (Daniels/MODIS) + `RATIO_MAX=2` — the differentiable Darwin calcite port and native resolution were *tested and did not help*, so R_PICPOC is **not cluster-gated**. `geo1` holds {alpfe, scav_rat, R_PICPOC} jointly 7/10; diatomgraz is an open iron-pair tradeoff. The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, CV→1e-15), so box-vs-Darwin pattern-matching is not a fidelity metric.


*Research note · 2026-06-21 · audience: project lead (ML). Numbers are MEASURED unless tagged ESTIMATE / DERIVED / UNMEASURED. Canonical source: `docs/research_notes/2026-06-19_aicr_memory_budget.md`; cell counts from `scripts/measure_compute_budget.py`; wall-clock from `scripts/measure_compute_time.py`. Produced by an adversarially-verified multi-agent budget pass (12 agents; every row's memory arithmetic + GPU placement independently re-checked).*

---

## 0. Task key

Codes are labels for this note only (T = task), numbered by rough increasing cost — **not** a required order. Two axes define each task: **resolution** (1° box → native LLC270 3-AOI → global ocean) and **time regime** (time-mean → seasonal → time-resolved).

**Abbreviations:** `tm` = time-mean (one annual-average field, 200 steps) · `seasonal` = 12-month cycle (~2000 steps) · `time-resolved` = ~300 monthly snapshots · `1°` = coarse box (~2,853 cells) · `native` = full LLC270 (~38,809 cells, 3-AOI) · `global` = whole ocean (~546,695 cells) · `×1/×10` = seeds trained together · `PORT` = differentiable Darwin calcite port.

| Code | Plain English | Why it exists |
|---|---|---|
| **T0** | Current 1° box, 3-AOI, time-mean | The baseline every published result ran on |
| **T0b** | The 1° parameter sweep already done (86 configs × 10 seeds) | Found the 5/6 ceiling — complete |
| **T1** | **O7** — same model at native LLC270 resolution (13× more cells), time-mean | The re-baseline being built now |
| **T2** | T1 with 10 seeds (n=10 ensemble) | Statistics on the native re-baseline |
| **T3** | Native, fitting the **12-month seasonal cycle** instead of the annual mean | The near-term "ask" — first seasonal fit |
| **T4** | T3 with 10 seeds | Seasonal ensemble |
| **T5** | A **sweep** of many configs at native seasonal | Lever exploration at native+seasonal |
| **T6** | Whole-ocean (global) time-mean | First global map (paper #3) |
| **T7** | Whole-ocean seasonal | Global seasonal fit |
| **T8** | Whole-ocean seasonal, 10-seed sweep | Global ensemble (heaviest) |
| **T9–T11** | The same ladder **with the Darwin calcite PORT** (native tm / native seasonal / global) | The only path to R_PICPOC / 6-of-6 |
| **T12** | Track-2 neural **emulator** (separate surrogate, not the box) | Different project track |
| **DirA** | Native **time-resolved** (~300 monthly snapshots = a time series) | The one long-wall-clock job |
| **1-AOI native** | Single region at native res | Cheapest native rung / stepping stone |

Ladder: **T0** (current) → **T1/T2** (full resolution) → **T3/T4** (add seasonal cycle) → **T5** (sweep) → **T6/T7/T8** (whole ocean) → **T9–T11** (add real calcite physics).

---

## The rule (this replaces the grid)

The 19 rows below are not 19 tasks to plan — they're one formula evaluated at different points. Derive any task's cost on demand:

```
peak GiB = 356 × cells × steps × batch / 2^30
time/fit = 1500 epochs × steps × 1.4 ms        (×2 if checkpointed)
```

Six inputs: **cells** (1° 2,853 · native 38,809 · global 546,695) · **steps** (tm 200 · seasonal 2,000; time-resolved = same memory, ×300 time) · **batch** (seeds) · **×1.2** if PORT · **ceilings** (5090 24 · H100 80 · H200 144 · B200 192 GiB). Example: native seasonal ×10 → 356×38,809×2000×10 / 2³⁰ = 257 GiB → 1 B200 (ckpt) or 10× b1 on Explorer.

## Critical path (what's actually necessary)

Three tasks; everything else is derivable-on-demand or future-paper scope:

1. **T1** — native time-mean re-baseline (O7). In progress; 1× RTX 5090.
2. **T3** — native seasonal. Next milestone; 1× Explorer card, ~70 min.
3. **PORT (T9/T10)** — the only path to R_PICPOC / 6-of-6. Engineering-gated (write the differentiable calcite chemistry), not GPU-gated.

Generalize, don't pre-plan (price when committed): the ×10/sweep rows (T2/T4/T5/T8 = "the ×1 fit, batched or repeated"), the global rows (T6–T8/T11, paper #3), T12 emulator (separate track), DirA time-resolved (a maybe).

**Everything below (§1–§6) is the reference cost surface** — the fully-enumerated grid, derivable from the rule above. Consult a row only when you're about to run it.

---

## 1. TL;DR

- **Runs on the owned RTX 5090 (24 GiB) today:** all 1° work (T0/T0b), 3-AOI native time-mean ×1 (T1, the in-progress O7 re-baseline, ~2.6 GiB), the **1-AOI native** rung (≤6.5 GiB even ×10 batched), and the DirA time-resolved fit (2.6 GiB — memory is flat in the 300 snapshots via gradient accumulation; the cost is ~25–35 h wall-clock, not VRAM).
- **Needs the free Explorer H200 (144 GiB ×32):** every fit whose peak lands in 24–144 GiB — 3-AOI native time-mean ×10 (25.7 GiB, the **first task off the local card**), the headline **near-term ask** 3-AOI native **seasonal ×1** (25.7 GiB, fits one H200 eager), global LLC270 time-mean ×1 (36 GiB), global LLC90 seasonal ×1 (40 GiB). H200 is free, granted, the de-facto near-term path.
- **Needs an AICR B200 (192 GiB ×248, onboarding ~July 2026):** oversized single graphs that fit one B200 only **with checkpointing** — 3-AOI native seasonal ×10 (257 GiB → 51.5 GiB at 5× ckpt), global LLC270 seasonal ×1 (363 GiB → 72.5 GiB at 5× ckpt).
- **NOT runnable today (two distinct blockers — keep separate):** *(a) technical* — any single graph >192 GiB needs DDP/NCCL **cell-sharding, which is NOT BUILT** (`run_aicr_b200.sbatch:30-34`; realistic path = checkpoint-onto-one-card, itself validated at one 5× datapoint); *(b) calendar* — B200 not onboarded until ~July 2026. The global seasonal ×10 sweep (3,625 GiB) is the extreme: even at 15× checkpoint (242 GiB) it still exceeds one B200, so it **must** decompose into per-seed fits run in waves.
- **The Darwin calcite PORT rows (T9–T11) are ENGINEERING-gated, not compute-gated.** Their memory (×1.2 central on the 356 constant) fits the same tiers as the un-ported rows; "not runnable today" means *the differentiable coccolithophore-PFT + calcite chemistry is not written yet* — a different category of blocker from sharding/onboarding. These are the **only** rows that attack 6/6 (R_PICPOC).
- **B200 = throughput, not speed.** Wall-clock is launch/Python-loop-bound (~0% GPU util, flat in cells out to the ~3.2 M-cell crossover ≫ LLC270's 947 k). A bigger card never makes a single fit faster; B200 buys batching headroom and sweep concurrency. Corollary: every `×10` row has two realizations — one batched graph (memory ×10, needs ckpt/shard) **or** 10 separate `b1` jobs (free-H200-runnable today). The separate-jobs form is the runnable-today answer for every oversized ×10.

---

## 2. The model

**Memory (MEASURED, eager, RTX 5090, float32, R²=0.99999, n=20):**

```
peak_GiB = 356 B/(cell·step) × horizontal_cells × steps × batch / 2^30
```

- The **356 B/(cell·step)** constant already folds in all **15 tracers**, **2 layers** (one 15-vector 2-layer column *is* the "cell" — do not ×2 for layers), and the full reverse-mode autograd intermediate set (≈5.9× the bare 60-B state). Anchor: 356 × 64e6 / 2³⁰ = 21.22 GiB ✓.
- Units are **GiB (÷2³⁰)**. **Batch (seeds) is a separate multiplier** — batched ≡ sequential, exact 0.0 diff.
- The constant is **eager-only** on the Windows laptop, so **356 is the conservative upper bound**.
- **MEASURED 2026-06-23 — compiled constant (Explorer H200).** Under `torch.compile`, `peak = 13.1 MB + **82.9 B/(cell·step)**` (R²=0.99485, n=20; `docs/findings/memory_scaling_compiled.md`). That is **4.3× below the eager 356**, confirming the standing "compiled is lower" caveat. **Production runs compiled, so 82.9 is the planning constant**; 356 stays as the safe upper bound. The §3 master table is still computed on 356 and is therefore an **eager upper bound pending full re-derivation** (paired with the native/seasonal wall-clock-under-compile measurement — the rest of #119). Headline tier shifts at 82.9: **T3 native seasonal ×1 → ~6.0 GiB (fits the owned 5090, not just an H200)**; **T4 native seasonal ×10 (~60 GiB) and T7 global LLC270 seasonal ×1 (~84 GiB, ocean basis) both fit one H200 with no checkpointing** (eager put them on a B200 + ckpt). Materially **de-risks the AICR/B200 dependency** for the seasonal ladder.

**Wall-clock laws (MEASURED):**

- **~9.2 ms/step eager, ~1.4 ms/step compiled** (6.6×; compiled value DERIVED from the 7-min anchor).
- **Flat in cells** (launch/Python-loop-bound, ~0% GPU util): 2,853 → 105,300 cells (37×) moves a 200-step epoch only 1.04×. Crossover to compute-bound ≈ **3.2 M cells** ≫ LLC270's 947,700 — everything through LLC270 is launch-bound.
- **Exactly linear in steps** (R²≈1): seasonal (2000) = 10× time-mean (200); time-resolved (~300 snapshots) ≈ 300×.
- **Production anchor (MEASURED):** 3-AOI 1° time-mean = **1500 epochs × 200 steps compiled ≈ 7 min**. A 10-seed batch is also ≈7 min (compile amortizes batching to ~free).

**Checkpointing (ESTIMATE — 1 measured datapoint at 5×):** divides peak by ~5–15× (√N theory → ~14×@200 / ~38×@2000 steps) at ~2× wall-clock. Treat all ckpt-on numbers as estimate-pending beyond 5×.

**GPU tiers (the only three mapped onto):** RTX 5090 **24 GiB** (owned/local, ×1; STATUS.md's "32 GB" is flagged drift — 24 is the measured ceiling) · Explorer H200 **144 GiB** (FREE, ×32, granted) · AICR B200 **192 GiB** (allocation, ×248, onboarding ~July 2026). A single graph >192 GiB needs DDP/NCCL cell-sharding = **NOT BUILT**; realistic oversized-fit path = **checkpoint onto one card**.

**Two cell bases for global rows:** ocean-column basis (LLC270 = **546,695**, MEASURED, the box's actual cells) is the headline here; **grid basis** (947,700) is the conservative upper bound (×1.73).

---

## 3. MASTER TABLE

Peak GiB is ckpt-off (the single-graph requirement) with the ckpt-on band (5×–15×, ESTIMATE) beside it. "Min GPU ×count" is the **smallest tier that holds the fit** — for oversized rows this is *checkpoint onto one card*, **not** the notional N-card shard (sharding not built). Ordered cheapest → heaviest. PORT rows (T9–T11) use central ×1.2 on the 356 constant and are marked **EST**.

| Task | Scope | cells | steps | batch | Peak GiB (ckpt off) | Peak GiB (ckpt on, est) | Wall-clock/fit | Min GPU ×count | Program size | Throughput GPUs | GPU-hours | Runnable today? |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **T0** 3-AOI 1° tm ×1 | baseline+anchor | 2,853 | 200 | 1 | **0.19** | 0.01–0.04 | 7.0 min | **5090 ×1** | 1 fit | 1× 5090 local | 0.12 | ✅ (done) |
| **T0** 3-AOI 1° tm ×10 | 10-seed ens | 2,853 | 200 | 10 | **1.89** | 0.13–0.38 | 7.0 min | **5090 ×1** | 1 batched fit | 1× 5090 | 0.12 | ✅ |
| **T0b** 5/6 sweep 86×10 | 856-fit sweep | 2,853 | 200 | 10 | **1.89**/cfg | 0.13–0.38 | 7 min/cfg × 86 | **5090 ×1** | 86 batched = 856 fits | 5090 serial ≈10 h; 32 H200 → 0.31 h | 10.0 | ✅ **(DONE — don't redo)** |
| **1-AOI native** tm/seas | eqpac native (cheapest native rung) | 9,750 | 200/2000 | 1–10 | **0.6 / 6.5 / 6.5 / 65** | ÷5–15 | 7 min (tm) / 70 min (seas) | **5090 ×1** (×10 seas 65 GiB → H200) | 1 fit | 1× 5090 | 0.12–1.17 | ✅ |
| **T1** native tm ×1 *(O7, in progress)* | NATIVE_RES=1 re-baseline | 38,809 | 200 | 1 | **2.57** | 0.17–0.51 | 7.0 min | **5090 ×1** | 1 fit | 1× 5090 | 0.12 | ✅ (runner/IC lift TODO) |
| **T2** native tm ×10 | first n=10 off the 5090 | 38,809 | 200 | 10 | **25.73** | 1.72–5.15 | 7.0 min | **H200 ×1** | 1 batched fit | 1× free H200 | 0.12 | ✅ |
| **T3** native **seasonal ×1** ← **THE ASK** | seasonal infra | 38,809 | 2000 | 1 | **25.73** | 1.72–5.15 | 70 min; ~7.7 h eager | **H200 ×1** | 1 fit | 1× free H200 (eager) | 1.17 | ✅ |
| **T9 PORT** native tm ×1 **EST** | Darwin calcite (×1.2) | 38,809 | 200 | 1 | **3.09** (2.75–3.60) | 0.21–0.62 | 7 min (hi 14 min) | **5090 ×1** | 1 fit | 1× 5090 | 0.12 | ❌ *(port not built)* |
| **T9 PORT** native tm ×10 **EST** | calcite ×1.2, 10-seed | 38,809 | 200 | 10 | **30.88** (hi 36.0) | 2.06–6.18 | 7 min | **H200 ×1** | 1 batched fit | 1× free H200 | 0.12 | ❌ *(port not built)* |
| **T5** native sweep 86×10 | throughput | 38,809 | 2000 | 10 | **257.34**/cfg | 17.16–51.47 | 70 min/cfg × 86 | per-fit **H200 ×1** (decomposed b1) | 856 b1 (or 86 batched) | 860 b1 on 32 H200 → ~32 h | ~1006 (b1) / 201 (batched) | ❌ batched; ✅-path = 860 b1 on H200 |
| **T10 PORT** native seasonal ×1 **EST** | coccolith phenology (×1.2) | 38,809 | 2000 | 1 | **30.88** (27.5–36.0) | 2.06–6.18 | 70 min (hi 140 min) | **H200 ×1** | 1 fit | 1× free H200 | 1.17 | ❌ *(port not built)* |
| **T6** global LLC270 tm ×1 | paper#3 / DirE | 546,695 | 200 | 1 | **36.25** (grid UB 62.8) | 2.42–7.25 | 7.0 min | **H200 ×1** | 1 fit | 1× free H200 | 0.12 | ✅ |
| **T11 PORT** global tm ×1 **EST** | global port (×1.2) | 546,695 | 200 | 1 | **43.50** (hi 50.7) | 2.90–8.70 | 7 min (hi 14 min) | **H200 ×1** | 1 fit | 1× free H200 | 0.12 | ❌ *(port not built)* |
| **(LLC90 global)** seasonal ×1 | Jon's *start-global-here* res | ~61k **EST** | 2000 | 1 | **40** (tm 4.0 / ×10 40 / seas×10 403) | ÷5–15 | 70 min | **H200 ×1** | 1 fit | 1× free H200 | 1.17 | ✅ *(wet count EST)* |
| **T7** global LLC270 seasonal ×1 | global per-fit ask | 546,695 | 2000 | 1 | **362.51** (grid UB 628) | 24.17–72.50 | ~2.3 h (ckpt 2×) | **B200 ×1 (ckpt)** | 1 fit (363 GiB) | 72.5 GiB@5× fits 1 B200 | 2.34 | ❌ (sharding; B200 ~Jul-26) |
| **T10 PORT** native seasonal ×10 **EST** | calcite ×1.2, seasonal 10-seed | 38,809 | 2000 | 10 | **308.81** (hi 360) | 20.59–61.76 | 70 min | per-fit **H200 ×1** (decomposed b1) | 10 b1 (or 1 batched 309 GiB) | 10 b1 on 10 free H200 → 1.17 h | 11.7 (10 H200 b1) | ❌ *(port + sharding)* |
| **T11 PORT** global seasonal ×1 **EST** | global port seasonal (×1.2) | 546,695 | 2000 | 1 | **435.02** (hi 507) | 29.00–87.00 | ~2.3 h (ckpt 2×; hi 4.7 h) | **B200 ×1 (ckpt)** | 1 fit (435 GiB) | 87 GiB@5× fits 1 B200 | 2.34 | ❌ *(port + sharding + B200 ~Jul-26)* |
| **DirA** native time-resolved ×1 | ~300 monthly snapshots | 38,809 | 200 | 1 | **2.57** *(==tm; grad-accum, NOT ×300)* | 0.17–0.51 | **~25–35 h** (300× the 7-min fit) | **5090 ×1** | 1 long fit | 1× 5090 (mem trivial) | 25–35 | ✅ (cost is calendar, not VRAM) |
| **T8** global LLC270 seasonal ×10 (sweep) | 10-seed ens | 546,695 | 2000 | 10 | **3625.14** | 241.7–725.0 *(even 15× = 242 > 192)* | ~2.3 h/fit (ckpt 2×) | per-seed **B200 ×1 (ckpt)** in waves | 10 b1 (NOT one 3625-GiB graph) | 10× ckpt-B200, 10 concurrent → ~2.3 h | 23.4 | ❌ (per-seed each oversized; B200 ~Jul-26) |
| **T12** *(Track-2, separate)* emulator | NN surrogate, global time-resolved | 546,695 | 200 | 1 | **36.25** *(box-side data-gen PROXY only)* | n/a — arch-dependent | ~25–35 h | **H200 ×1** *(proxy)* | 1 training run | arch-dependent | 25–35 (proxy) | ❌ *(emulator code not built)* |

**Reading the oversized rows:** the `min_gpu_count = 2/3/19` figures in upstream notes are **sharding targets, not runnable placements** — DDP/NCCL is not built, so the only runnable-today path for an oversized fit is *checkpoint onto one card* (T4/T7/T11-seasonal) or *decompose into per-seed b1 fits* (T5/T8/T10-×10). The table's "Min GPU ×count" reflects the **runnable** path.

---

## 3b. Time per task & checkpoint cost

Time anchors (all compiled; eager/uncompiled ≈ 6.6× slower): time-mean fit ≈ **7 min** · seasonal fit ≈ **70 min (1.2 h)** · time-resolved ≈ **25–35 h**. **Checkpointing** cuts peak memory ~5–15× but **roughly doubles wall-clock (~2×)**, and is only paid when a fit's peak exceeds the available card. Rows tagged `(ckpt)` already include that 2×. Grouped by GPU category below.

### RTX 5090 — local, owned (24 GiB) · always ×1

| Task | # GPUs | Peak GiB | Time / fit |
|---|---|---|---|
| T0 · 1° tm ×1 | 1× 5090 | 0.19 | ~7 min |
| 1-AOI · native tm ×1 | 1× 5090 | 0.6 | ~7 min |
| T0 · 1° tm ×10 | 1× 5090 | 1.9 | ~7 min |
| T0b · 1° sweep 86×10 | 1× 5090 | 1.9 /cfg | ~7 min/cfg · ~10 h total |
| T1 · native tm ×1 (O7) | 1× 5090 | 2.6 | ~7 min |
| DirA · native time-resolved | 1× 5090 | 2.6 | **~25–35 h** |
| PORT · native tm ×1 \* | 1× 5090 | 3.1 | ~7 min |
| 1-AOI · native seasonal ×1 | 1× 5090 | 6.5 | ~70 min |

### Explorer — ≤ 4 GPUs (H200 144 GiB **or** H100 80 GiB)

Realistic Explorer cap is **4 GPUs** (not the 32-card pool). Per-fit memory/time unchanged; the cap sets calendar time for multi-fit programs, and the H100's 80 GiB ceiling bites only the oversized seasonal fits. Seeds batchable per card (native seasonal, 25.7 GiB/seed): **H200 → 5**, **H100 → 3** (batching is ~free in wall-clock, so fill the card then count waves of 4).

Single fits — all ≤ ~44 GiB, so **1 card, either H100 or H200**:

| Task | Peak GiB | Time / fit |
|---|---|---|
| T2 · native tm ×10 | 25.7 (1 batched fit) | ~7 min |
| **T3 · native seasonal ×1 ← ASK** | 25.7 | **~70 min** |
| PORT · native seasonal ×1 \* | 30.9 | ~70 min |
| T6 · global tm ×1 | 36.3 | ~7 min |
| LLC90 · global seasonal ×1 | 40 | ~70 min |
| PORT · global tm ×1 \* | 43.5 | ~7 min |

Multi-fit programs — calendar time at the 4-GPU cap:

| Task | Fits | 4× H200 calendar | 4× H100 calendar |
|---|---|---|---|
| T4 · native seasonal ×10 | H200 2 · H100 4 | ~1.2 h (1 wave) | ~1.2 h (1 wave) |
| T5 · native seasonal sweep 86×10 | H200 172 · H100 344 | **~50 h ≈ 2.1 days** | **~100 h ≈ 4.2 days** |
| T7 · global seasonal ×1 (ckpt) | 1 | ~2.3 h | ~2.3 h (73→fits 80, tight) |
| T8 · global seasonal ×10 (ckpt) | 10 | ~7 h (3 waves) | ~7 h (3 waves) |
| PORT · global seasonal ×1 \* (ckpt) | 1 | ~2.3 h | needs ~6× ckpt (87 > 80) |

The cap bites the **native seasonal sweep** most (43–86 sequential waves of 4 → ~2–4 days vs ~32 h on 32 cards). Mitigate by fewer seeds (n=5 halves it) or a smaller config grid (the winning levers are already known from the 1° sweep, so the native grid should be far smaller than 86 configs).

### B200 — AICR (192 GiB) · `(ckpt)` = checkpointed to fit one card, ~2× time

| Task | # GPUs | Peak GiB (off → ckpt) | Time / fit |
|---|---|---|---|
| T4 · native seasonal ×10 (batched) | 1× B200 (ckpt) | 257 → 51 | ~2.3 h |
| T7 · global seasonal ×1 | 1× B200 (ckpt) | 363 → 73 | ~2.3 h |
| PORT · global seasonal ×1 \* | 1× B200 (ckpt) | 435 → 87 | ~2.3 h |
| T8 · global seasonal ×10 | 10× B200 waves (ckpt) | 363 → 73 ea | ~2.3 h/seed · 2.3 h calendar |

**\* PORT** = Darwin calcite port — code not yet written (engineering-gated; the only path to R_PICPOC / 6-of-6). **B200/AICR** onboards ~July 2026. T4 appears in both H200 and B200 on purpose: it's the natural first AICR job (1× B200 batched), but until then runs free as 10× single-seed fits on Explorer H200.

**Checkpoint story in one line:** only the four oversized seasonal rows (T4, T7, PORT-global-seasonal, T8) ever need checkpointing — each turns a ~70-min fit into a **~2.3 h** fit on one B200. Everything that fits its card runs at base time, no penalty. Caveat: the ~2× checkpoint wall-clock and the 5–15× memory factor are both ESTIMATE (one measured 5× datapoint) — measure on Explorer before trusting the `(ckpt)` rows.

---

## 4. How each change moves the number

Each lever is a clean multiplier on (memory, wall-clock); the GPU-tier consequence follows from the 24 / 144 / 192 GiB ceilings.

- **1° → native (resolution):** **memory ×13.6** (2,853 → 38,809 cells), **wall-clock ×1.0** (flat in cells). Time-mean ×1 stays on the 5090 (0.19 → 2.57 GiB); only matters stacked with batch or steps.
- **time-mean → seasonal (steps):** **memory ×10**, **wall-clock ×10** (200 → 2000, exactly linear). This is the lever that pushes 3-AOI native off the 5090 onto the H200 (2.57 → 25.7 GiB) and pushes global LLC270 over the B200 ceiling (36 → 363 GiB → ckpt-only).
- **→ time-resolved (DirA, ~300 snapshots):** **memory ×1.0** (gradient accumulation — peak == time-mean per snapshot; a naïve ×300 would give 772 GiB), **wall-clock ×300**. Stays on the 5090; the cost is ~25–35 h calendar.
- **×1 → ×10 seeds (batch):** **memory ×10**, **wall-clock ×1.0** (batched ≡ sequential under compile). The throughput axis: spend ×10 as one batched graph (needs next tier / ckpt) or 10 separate b1 jobs (same tier, throughput = GPU count). The b1 form is the runnable-today escape hatch.
- **box → Darwin port (state width):** **memory ×K** on 356, K = **1.07 / 1.2 / 1.4** (low/central/high — the *one* un-grounded multiplier, **ESTIMATE**), **wall-clock ×1.0** central (Darwin's real dissolution is a benign constant 1/300-day, *not* Ω-stiff). At AOI scale the port does **not** change the tier story (seasonal ×1 26 → ~31 GiB, still one free H200).
- **AOI 1 → 3 (region count):** **memory ×13.6** native cells. 3-AOI is load-bearing for scav_rat / Smallgrow / Biggrow recovery; 1-AOI native is the cheapest native rung and the natural T1 stepping-stone (≤6.5 GiB even ×10).
- **AOI → global (extent):** **memory ×14** cells (38,809 → 546,695), **wall-clock ×1.0** (547 k ≪ 3.2 M crossover). Global time-mean stays one H200 (36 GiB); global × seasonal is what forces ckpt/shard.
- **checkpoint-on:** **memory ÷5–15** (only 5× measured), **wall-clock ×2**. **The** runnable-today mechanism for every oversized single graph — lands T4 (257 → 51.5), T7 (363 → 72.5), T11-seasonal (435 → 87) onto **one** B200. Does **not** rescue T8 (3625 GiB): even 15× = 242 > 192, so T8 must decompose.

---

## 5. GPU-series-per-task (direct answer)

Runnable path; oversized = checkpoint-onto-one or decompose (sharding not built):

- **T0 / T0b (1° all):** **1× RTX 5090** (owned). T0b sweep serial ≈10 h.
- **1-AOI native (all):** **1× RTX 5090** (≤6.5 GiB); ×10 seasonal (65 GiB) → **1× H200**.
- **T1 native tm ×1 (O7):** **1× RTX 5090** (2.57 GiB).
- **T2 native tm ×10:** **1× Explorer H200** (25.7 GiB — first task off the 5090).
- **T3 native seasonal ×1 (THE ASK):** **1× Explorer H200** (25.7 GiB, eager, free).
- **T4 native seasonal ×10:** **1× B200 + checkpointing** (257 → 51.5 GiB) — OR **10× H200** as separate b1 fits (runnable-today, free).
- **T5 native sweep 86×10:** throughput = GPU count. Runnable today as **860 b1 fits across 32 free H200** (~27 waves, ~32 h, ~1006 GPU-h).
- **T6 global LLC270 tm ×1:** **1× Explorer H200** (36 GiB).
- **T7 global LLC270 seasonal ×1:** **1× B200 + checkpointing** (363 → 72.5 GiB).
- **T8 global LLC270 seasonal ×10:** **10× B200 in waves**, each per-seed fit checkpointed (363 → 72.5 GiB). Cannot be one graph (3625 GiB; even 15× ckpt > 192).
- **LLC90 global (Jon's start-here res):** **1× H200** through seasonal ×1 (40 GiB); seasonal ×10 (403 GiB) → ckpt/decompose.
- **T9 PORT native tm:** **1× 5090** (×1, 3.1 GiB) / **1× H200** (×10, 30.9 GiB) — *gated on port code*.
- **T10 PORT native seasonal:** **1× H200** (×1, 30.9 GiB) / **10× H200** b1 (×10) — *gated on port code*.
- **T11 PORT global tm ×1:** **1× H200** (43.5 GiB) — *gated on port code*.
- **T11 PORT global seasonal ×1:** **1× B200 + checkpointing** (435 → 87 GiB) — *gated on port code + B200 onboarding*.
- **T12 emulator (Track-2):** **1× H200** for the box-side data-gen **proxy** (36 GiB); the net's own footprint is architecture-dependent, outside the 356 model — *gated on emulator code*.
- **DirA time-resolved:** **1× RTX 5090** (2.57 GiB; ~25–35 h calendar).

---

## 6. Caveats & what to measure next

**Hard blockers (technical, today):**
- **DDP/NCCL cell-sharding is NOT BUILT** (`scripts/slurm/run_aicr_b200.sbatch:30-34`; `scripts/slurm/README.md:48`). Any single graph >192 GiB is not runnable as one fit. The N-card counts are **build targets**, not capacity. Realistic oversized path = checkpoint-onto-one-card or per-seed decomposition.
- **Checkpoint factor is essentially unmeasured** — **1 datapoint at 5×**; √N theory predicts ~14×@200 / ~38×@2000 but is untested, and `budget.py` confirms peak does *not* fall as 1/K. Every ckpt-on number is **estimate-pending**. Highest-leverage thing to measure on Explorer — it decides whether T4/T7/T11-seasonal land on one B200.

**Calendar blocker (distinct):**
- **B200 not onboarded until ~July 2026** (sourced to project memory, not the cluster docs). Keep separate from the technical (sharding) blocker. AICR is **Northeastern's** AI Compute Resource, **not** an MIT-ORCD / Engaging follow-on (`cluster_setup.md:15`).

**Measurement gaps making verdicts upper-bounds:**
- **Compiled memory constant MEASURED 2026-06-23 (Explorer H200): 82.9 B/(cell·step)**, R²=0.99485 — **4.3× below eager 356** (`docs/findings/memory_scaling_compiled.md`). Confirms compiled is far lower; the §3 table's 356-based numbers are eager upper bounds pending re-derivation. Drops the near-boundary rows well under their ceilings — T2/T3 native ×1 → ~6 GiB (onto the 5090), T4/T7 seasonal → one H200 with no ckpt. **Still open (rest of #119):** native + seasonal **wall-clock** under compile (the eager 9.2 ms/step → ~46 min T1 claim), and the checkpoint factor beyond the single 5× datapoint.
- **Native-×10-under-compile cell-sensitivity UNMEASURED.** All flat-in-cells data is *eager*; at native ×10 effective width ~400 k — unconfirmed whether compile reintroduces cell-sensitivity. Named thing-to-measure-on-Explorer.
- **End-to-end native fit under `torch.compile` on Linux UNMEASURED** (eager 9.2 ms/step would make T1 ~46 min not 7 min).
- **LLC90 wet count (~61 k) is the one ESTIMATE** among cell counts (repo never loads LLC90). 1°/native/LLC270-ocean(546,695) are all MEASURED.

**Operational risk:**
- **AICR idle-GPU-reaper is a MEASURED ~0%-util fact.** The un-compiled, un-batched seasonal runner (Python-loop-bound) **will be killed on AICR** until batched + `torch.compile`'d (`run_aicr_b200.sbatch:26-29`). Applies to every launch-bound fit on B200 (T4–T11). Mitigation: dev / un-compiled runs on the **free Explorer H200** (no reaper); send only batched+compiled production to AICR. B200 is sm_100 (Blackwell) — needs CUDA 12.8+ / PyTorch ≥2.7 CU128.

**Port ESTIMATE:**
- The ×1.07 / 1.2 / 1.4 port multiplier is the **only un-grounded number** — ground-truthed against the real Darwin 3 integrator (single prognostic `iPIC` tracer, coccolith identity = `R_PICPOC(j)` nonzero, **constant-rate 1/300-day dissolution, not Ω-stiff**), bounding it toward the low end. T9–T11 "not runnable today" is **engineering-gated** (build the differentiable coccolith-PFT + calcite chemistry).

**Scope note on T9–T11:** 6/6 is box-excluded by **seven** independent exclusions; it is gated *only* on the differentiable Darwin calcite port + native bloom-regime resolution (realized PIC:POC ≈ 0.9 natl / 1.4 SO that the rigid single-ratio box can't match). The PORT rows are the **only** rows that attack R_PICPOC.

**T12 separator:** the 356-constant model describes the differentiable **box**, not a transformer/FNO/graph-net (compute-bound, not launch-bound). T12's 36 GiB / 25–35 h are **data-gen-side proxy** numbers only; the emulator's true cost is architecture-dependent and outside the grounded constants.

**Doc-drift to NOT re-import:** laptop VRAM = **24 GiB** (not 32); seasonal steps = **2000** with spin-up (not 1464); canonical sweep = **86 configs / 856 seeds**.

**T1 status:** the `NATIVE_RES=1` loader path (Steps 1–2) is DONE and verified (eqpac → 9,750 cells, flat_idx alignment holds); missing `Chl1`/`CO2_flux` native covariates downloaded 2026-06-21 (blocker cleared). The **runner/IC lift remains TODO** (native target cache, native IC + resolution guard, native GEOTRACES/GLODAP binning, smoke test) — so T1 is "in progress," not done. See [[o7-native-rebaseline-plan]].
