# DarwinDiff — Lauderdale catch-up deck (May 2026)

Four slides, ~5-7 min each + Q&A. Designed for Jon (collaborator) + readiness to fork content into a Chris Hill / NVIDIA / committee deck.

---

## Slide 1: Problem + DarwinDiff in one slide

**Title:** DarwinDiff — Gradient-Based Parameter Inversion for Darwin BGC

**One-line positioning:**
> DarwinDiff is a differentiable PyTorch reimplementation of ECCO-Darwin's biogeochemistry, replacing Green's-functions sensitivity sweeps with autograd-based gradient descent over the same 6 Carroll parameters.

**Why it matters (3 bullets):**
- MITgcm has mature physical adjoint + CTRL infrastructure, but **no BGC parameter adjoint exists** in the standard release. Carroll 2020 used Green's functions precisely because the adjoint-CTRL workflow doesn't cover biogeochemistry.
- DarwinDiff fills this gap: 5-PFT box-model proxy + carbonate extension + autograd-clean integrators, runs on a single RTX 5090 Laptop.
- Targets the same calibrated parameters as Carroll's Green's functions — direct apples-to-apples comparison.

**Status one-liner:** Two demonstrated capabilities (iron-pair recovery, 5/6 multi-AOI recovery), one publishable scientific finding (loss-landscape basin structure), one cluster ask.

---

## Slide 2: v2.0 + v3.0 progress (the recovery story so far)

**Title:** v2.0 → v3.0: from iron-pair recovery to multi-AOI 5/6

**v2.0 (May 2026, single-AOI Eq Pacific):**
- 7-tracer carbonate-extended box model + Follows 2006 solver + Wanninkhof flux
- **alpfe within 1.1% of Carroll's published value** (DINN baseline, +carbonate)
- **scav_rat halves the 80% gap → 40% off** (carbonate joint loss resolves the iron-pair underconstraint Carroll 2020 left open)
- Block CV: extrapolation r = 0.637 (vs 0.301 in nb16 without carbonate)
- Tag `v2.0` on GitHub, PR #34 merged

**v3.0 (May 17-19, multi-AOI Eq Pacific + N Atlantic Subpolar):**
- Joint training across regimes with a shared Carroll-6 parameter vector
- AOI-ID embedding lets the network produce regime-specific maps from shared params
- **PR #57 baseline: 7/15 seeds at 5 of 6 Cal-grade (47%)** — project's best joint recovery
- Carroll-6 R_PICPOC value confirmed (via Carroll's Zenodo evaluation report §3) as a Darwin-internal optimum, not a satellite-truth one — no satellite in v05 calibration targets

**The 5/6 plateau:** 6th param is always some "residual sink" — diatomgraz, R_PICPOC, or scav_rat depending on which loss-weight mix is used. Earlier hypothesis ("conservation argument: 5 effective constraints on 6 params") survives — but tonight gives that hypothesis a much sharper structural form (Slide 3).

---

## Slide 3: Tonight's headline — Basin C and the 3-basin loss landscape

**Title:** The 5/6 ceiling decomposes into THREE distinct 4-param recovery basins

**Setup:** 2026-05-19 autonomous session, 6 sweep arcs, 60+ seeds in pure v05 framing on the laptop. Goal: find the 6/6 path. Outcome: characterized the 5/6 mutex at unprecedented detail and surfaced a third basin nobody knew existed.

**The three basins (3-AOI training):**

| Basin | Recipe | Recovered (4 params) | Failing |
|---|---|---|---|
| **A** | POSi=1.0 + SO tilt | alpfe, Biggrow, diatomgraz, ~Smallgrow | scav_rat, R_PICPOC |
| **B** | Paired Darwin PIC+POC anchor | R_PICPOC, Smallgrow, Biggrow | alpfe, scav_rat, diatomgraz |
| **C** (NEW) | POSi + SO tilt + CHL1_W=3.0 | **alpfe + scav_rat both 10/10**, Smallgrow, Biggrow | diatomgraz, R_PICPOC |

**Pairwise overlap:** A∩B = {Biggrow}; A∩C = {alpfe}; B∩C = {Smallgrow, Biggrow}; A∩B∩C = ∅. Union covers all 6, no config reaches them.

**Why Basin C is the publishable headline:**
- First config in the project's history with BOTH `alpfe` AND `scav_rat` at Cal-grade across all 10 seeds in multi-AOI training
- The iron pair is the historically hardest recovery in DarwinDiff (2 years of Green's-functions work in Carroll 2020 to characterize)
- Driven by Southern Ocean as a 3rd AOI + CHL1 weight boost — a clean methodological discovery, not a fortuitous hyperparameter

**Falsified tonight (informative negatives):**
- Max-lever stacking (0/20 at 5/6)
- MODIS-Darwin blending (binary mutex, even W=0.1 Darwin wipes basin A)
- Two-stage curriculum (warm-start doesn't transition basins)
- 2-AOI → 3-AOI lever transfer (F_CO2 lever broke 3-AOI carbonate dynamics)

**The conclusion is structural:** 5/6 reproducible is the laptop ceiling. 6/6 needs either resolution scaling (cluster + LLC270 native) or a different observation set (satellite leapfrog, deferred per Jon's guidance).

---

## Slide 4: Cluster ask + funding ask

**Title:** What we need to break 5/6 → 6/6

**Cluster ask (Chris Hill / MIT ORCD):**
- **Compute estimate:** ~50K GPU-hours on B200s for multi-week training (refining once we calibrate against laptop scaling)
- **Workload:** Full LLC270 native resolution multi-basin training. Each AOI scales from ~1000 cells (1° box-model proxy) to ~30K cells (LLC270 native). Direct test of whether the 3-basin mutex dissolves at higher spatial resolution.
- **Deliverable:** First gradient-based recovery of Carroll's 6 parameters at LLC270 native resolution, multi-basin. Targets a JAMES paper end of summer.

**NVIDIA Academic Compute Resources Program:**
- Eligible per Jon's outreach
- Fits Simulation + Modeling track: adjoint-method-for-BGC angle + PhysicsNeMo emulator angle (Track 2)
- Lucas to draft application content, Jon submits as faculty PI

**What we have now to support both asks:**
- v2.0 published (tag on GitHub, ~70 tests passing, autograd-clean code)
- v3.0 5/6 reproducible across 50+ seeds in 2-AOI + 3-AOI
- Basin C iron-pair recovery (10/10 at scale) as the laptop-side headline
- 3-basin diagnosis tells the cluster phase exactly what to test

**Risk reduction this provides:** the laptop work already proves the method works, the network architecture is right, and the loss landscape is characterized. Cluster work is no longer exploratory — it's a clearly-scoped scaling test.

---

## Speaker notes — what to emphasize

- **Lead with Basin C (Slide 3) as the new science.** v2.0 + v3.0 is recap; Basin C is the recently-shipped scientific finding worth a meeting.
- **Be honest about the 5/6 plateau on laptop.** Don't oversell. The honest framing makes the cluster ask credible.
- **Frame the cluster ask as risk reduction, not gating.** Method works at small scale; cluster validates at production scale.
- **Apples/oranges PIC framing (Jon's reframe) is the right way to discuss MODIS comparison work.** Not a critique of Carroll's calibration, a complement to it — different observation, different question.
- **Track 2 (neural emulator) gets one sentence.** Active in the back of Jon's mind; we haven't worked on it yet; it's the cluster-gated follow-on after proof-of-concept ships.

## What NOT to put in the deck

- Tonight's failed sweep variants (F_CO2 in 3-AOI, G1 POSi=0.3). They're informative but distract from the headline. Mention only if Jon asks "what didn't work."
- MODIS / PACE infrastructure. Built but shelved for the leapfrog phase. Mention only as "we have the loaders ready for the follow-on."
- Two-stage curriculum. Falsified, low-value to discuss.
- Detailed mean_cal numbers across all configs. The basin diagnosis is the result, not the seed-rate tables.
