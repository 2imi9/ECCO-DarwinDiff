# DarwinDiff — Project Status

A snapshot of the **current best**, not a timeline. Per-config detail lives in the
[Config / Results Matrix](docs/results_matrix.md); the chronological record is in
[CHANGELOG.md](CHANGELOG.md) and the [archive](docs/archive/index.md).

## What this is

DarwinDiff replaces ECCO-Darwin's Green's-functions Carroll-6 calibration with gradient
descent through a differentiable 0-D box model, predicted per grid cell by a small neural
network (`DINN`). It is framed as a **surrogate-to-model identifiability study** — *which*
of the six Carroll-6 parameters are identifiable from real ocean observations, *which* are
not, and *why* — **not** a "6/6 recovery" chase. As a study, Track 1 is **scientifically
complete**: the central, verified result is that the per-cell architecture is *load-bearing*
— a per-cell DINN holds the target trio {`alpfe`, `scav_rat`, `R_PICPOC`} while a single
global-scalar vector holds ~0 (disjoint CIs). What remains is manuscript finalization and the
(separate) Track-2 build, not further recovery-chasing.

The honest target is **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}.
The growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** — no real-world
data constrains phytoplankton growth rates — so it is excluded from the target, not counted
as a miss.

## Current best

The study operates at **3-AOI joint training** (Eq Pacific + N Atlantic Subpolar + Southern Ocean Pacific)
on a single RTX 5090 32 GB, with the NU Explorer H200 cluster for sweeps. All numbers below are
`scripts/verify_run.py`-gated (exit 0 = re-derived from raw).

- **Iron pair (`alpfe`, `scav_rat`) — recovers reproducibly, 38/40 (95 %)** at the best 3-AOI
  config, from real GEOTRACES IDP2025 dissolved iron (~7 min/fit on one GPU).
- **`R_PICPOC` — recovers** against a real calcite anchor (Daniels CP:PP / MODIS PIC), landing at the
  real ~0.05 — *consistent with* Carroll within the wide Cal band, **not** a validation of 0.0425
  (Carroll's value is itself under-constrained; see below).
- **Best operating point `geo1`** (`GEOTRACES_W=1` + Daniels anchor) **holds {`alpfe`, `scav_rat`,
  `R_PICPOC`} jointly in 7/10 seeds** — a **3-of-4-observable frontier**, statistically tied with
  `base`/`dan2` at n=10. (A fresh identical-config re-run confirms 7/10; the original hold-together
  sweep reported 8/10 — they differ by one band-edge seed.)
- **`diatomgraz` — not recovered** in the real-data sweep (best 4/10 = chance). This is a
  **settled identifiability verdict**, not an open task: it is profile-likelihood-flat /
  structurally non-identifiable from the present staged data — [#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152).
  In principle it is an **iron-pair tradeoff** recoverable via the dense Darwin POSi (`TRAC16`)
  target, which is **not staged**; that is a future data-staging option, not a Track-1 blocker.

→ Every config that produced these, and how each differs, is in the **[Config / Results Matrix](docs/results_matrix.md)**.

## Why these are the load-bearing facts

- **`R_PICPOC` was never a "6/6 wall."** The earlier "needs the differentiable Darwin calcite
  port + native resolution" conclusion is **refuted** — both were tested and neither helped. The
  real gap was the absence of a *direct, real calcite observation* (now supplied) plus a
  contaminated Southern-Ocean ratio target (fixed by `RATIO_MAX=2`). Any ratio anchor recovers
  `R_PICPOC` — Darwin's own does too — so the real anchor's value is **non-circularity**, not
  recoverability. The recovery lands at the real ~0.05, consistent with Carroll's 0.0425 only within
  the wide ±40 % Cal band — **not a validation of it**. The load-bearing spine-D point is that Carroll's
  `R_PICPOC` is itself **under-constrained**, and a single **global** constant is mis-specified against a
  regionally-variable rain ratio (Daniels eqpac ~0.039, ≈1.6× the global mean).
  `docs/archive/findings/2026-06-26_rainratio_real_vs_darwin.md`.
- **The surrogate gap is dimensional — and it is the rigorous foundation of the approach.** At
  uniform Carroll parameters the 0-D box relaxes to a spatially near-uniform state (tracer
  CV ~4e-5 @200 steps → ~1e-15 @6400, vs Darwin's O(1) CV 0.6–2.4). Box-vs-Darwin spatial-pattern
  correlations are therefore **not** fidelity metrics; identifiability comes from real, absolute,
  Darwin-independent observations. A direct **per-cell-vs-global-scalar ablation confirms the
  per-cell DINN is load-bearing on real data**: at `geo1`, per-cell holds the trio 7/10 vs **0/10**
  for a single global Carroll-6 vector (`scav_rat` 8/0, `R_PICPOC` 9/0; Fisher p < 0.01).
  [PR #158](https://github.com/2imi9/ECCO-DarwinDiff/pull/158).
- **Independent validation ([#163](https://github.com/2imi9/ECCO-DarwinDiff/issues/163)) is now addressed — and it decomposes cleanly.**
  *Estimator-independence:* a **DINN-free** global-scalar recovery on real data reaches the same
  optimum as the per-cell DINN for `alpfe` (Excellent, ≈ Carroll), and a **gradient-free** Nelder-Mead
  estimator agrees too ([`scripts/independent_validation.py`](scripts/independent_validation.py), [PR #172](https://github.com/2imi9/ECCO-DarwinDiff/pull/172)) —
  so **`alpfe`'s recovery is method-independent**, not a DINN/autograd artifact; `scav_rat` and
  `R_PICPOC` genuinely *require* the per-cell structure (0/10 without it). *Independent-data:* a
  held-out GEOTRACES cross-validation ([PR #173](https://github.com/2imi9/ECCO-DarwinDiff/pull/173) —
  hold out 30 % of the iron cells, score the box's DFe at the **unseen** cells) returns **negative R²**:
  the 0-D box homogenizes, so it has no spatial structure to predict per-cell iron. A faithful held-out
  *data* validation is therefore **structurally blocked by the surrogate gap** and needs a model with
  spatial dynamics (the Track-2 UDE / emulator). The recovery pins the iron *magnitude*; it cannot
  predict *which* cell has *how much*.
- **Statistical honesty.** In the hold-together sweep only two effects are real at n=10 — the
  ratio anchor recovering `R_PICPOC` (3/10→10/10, Fisher p=0.003) and high iron weight collapsing
  `scav_rat` (8/10→0, p=7e-4); differences among the high cells (7–10/10) are sampling noise. The
  metric throughout is **per-AOI ≥2-AOI co-recovery** (avoids a cell-weighted straddle
  false-positive). FIM/profile diagnostics independently agree.
- **Honest scope of the completed study.** Track 1 is a **consistency check against Carroll's own
  published values**, not a cross-validated discovery against the GCM. The surrogate gap (the 0-D box
  homogenizes, held-out real-data R² is negative) means identifiability must come from real *absolute*
  anchors, not pattern-matching — this is a **finding that bounds the claim**, and it is precisely what
  motivates Track 2. With this, the Track-1 identifiability question is answered and the study is complete.

## Architecture (brief)

A per-cell network `env → 6 Carroll-6 params` trained by gradient descent through a differentiable
box model. Full detail in [docs/dinn_design.md](docs/dinn_design.md).

- **Networks**: `DINN` (~454 weights, SST-only, baseline for the structural argument);
  `DINNDeep` (~9.4K weights, saturates on biomass tracers — not default); `DINNRegional` (legacy).
- **Box model**: 5-PFT 2-layer integrator (`src/darwindiff/carroll6_5pft_2layer.py`) with carbonate
  chemistry (`carbonate.py`, Follows 2006 + Wanninkhof 2014).
- **Recovery scoring** (`diagnostics.band_of`): *Excellent* ≤ 5 % off Carroll; *Cal-grade* ≤ 40 %;
  *Loose* ≤ 80 %. Carroll's published values are bit-identical between v04 (JAMES) and v05 (GBC).

## Methodology rules

- **Compare against Carroll's published Green's-functions optima**, not against prior notebooks.
- **DINN baseline only by default** (v2.2.x onward); `DINNDeep` saturates and recovers fewer
  Cal-grade params.
- **Report n=10 minimum and disclose seed variance** in any headline claim.

## Cluster path

Two Northeastern clusters (full table in [docs/cluster_setup.md](docs/cluster_setup.md)):

- **Explorer** (H200 144 GB ×32) — active near-term path; the first native-resolution prototype runs here.
- **AICR** (B200) — future path via a PI proposal; target for the global-native / seasonal sweep.

The cluster path unlocks native LLC270-resolution recovery, time-resolved multi-year fitting,
and **Track-2** build-out. (A larger multi-seed ensemble has already been folded into the hardened
Paper #1, so it is no longer a pending unlock — the verified n=10 headline numbers above stand as the
reported values.) These remain legitimate cluster goals; they are **not** gated on `R_PICPOC` or "6/6",
which are resolved/reframed at 1° box scale.

## Track 2 — differentiable spatial model (status: **identifiability-limits map COMPLETE**; real-data E2 gate RUN → negative)

**Update (2026-07-10) — the Track-2 result is a 3-closure identifiability-limits map, and the
make-or-break E2 was run (decisive negative).** The original thesis — "make Darwin differentiable to
*learn* real closures" — is honestly bounded: transport does **not** close the gap on real data, not
because the method fails but because the observations lack the signal. That reframes Paper #2 as an
**identifiability study**: *which* Darwin closures real obs can constrain and *why they can't*. The
map (`docs/research_notes/2026-07-09_track2_identifiability_writeup.md`; reproducibility appendix
`2026-07-10_reproducibility_appendix.md`):
- **iron `scav_rat`** — observability-limited (structural information wall; a particulate:dissolved
  observable does *not* rescue it — the initial "partitioning breaks the wall" claim was an artifact,
  caught + retracted by adversarial verification);
- **calcite Ω-modulation of `R_PICPOC`** (the scalar itself *is* recoverable) — data/support-limited:
  within-region Ω support ≤0.16 dex everywhere, confirmed on independent in-situ **GLODAPv3** Ω
  (838+1740 bottles), shown **driver-general** (SST/composition don't rescue it), and the
  **make-or-break out-of-sample transport E2 fails** (learned closure can't beat a constant-through-
  transport null; K_num non-discriminating; `docs/findings/2026-07-10_e2_powered_result.md`);
- **growth `Smallgrow`/`Biggrow`** — structurally unobservable (total NPP gives only the biomass-
  weighted mean → the pair stays degenerate).
Hardened by an 8-reviewer adversarial panel (Simpson-artifact / CI / scope corrections applied) and a
reproducibility appendix. The map's forward contribution is an **observing-system recommendation**
(wider within-region Ω; pure scavenged Fe; per-PFT production). New method artifact: the
**symbolic-distillation identifiability oracle** (`scripts/symbolic_distill_probe.py`). Everything on
branch `2imi9/status-handoff-2026-07-07` (unmerged). _Prior Phase-1-tooling status below._

## Track 2 — differentiable spatial model (status: foundation BUILT + synthetic closure-recovery result; real-data E2 gate unbuilt)

**Update (2026-07-07) — the differentiable foundation is now built and merged (#177).** `integrators.py` (RK4 + gradient checkpointing + time-aware forcing `f(t,x)`), `carroll6_ude_tendency` (pluggable neural closures), and `transport.py` (mass-conserving batched-column vertical transport) are on `main`. On a **synthetic self-twin** (still not real Darwin, still transport-limited), closure equifinality was diagnosed as a **support problem** and cured: a **Monod-anchored closure** (~15x over a free MLP) plus an **excitation designed offline for pennies** (a ~2-min CPU Fisher probe found the lever is *light-driven drawdown, not dust*) recovers the closure over the widest domain -- excitation ladder, full-domain closure error `0.203 -> 0.173 -> 0.154 -> 0.116` (n=4). This is a **synthetic methods result, not a real-data claim**; the E2 gate below (held-out real-data R^2 > 0 with transport) remains the make-or-break and is still unbuilt. Design docs: `docs/research_notes/2026-07-06_*`. The three-component picture (DINN parameter learner / FNO emulator scaffold `emulator.py` / mechanistic UDE) and the parameter-learner<->emulator seam are in `docs/NEXT_SESSION.md`.

**Update (2026-07-09) — Phase-1 tooling + an independent identifiability oracle (all local CPU).** Three additions, still synthetic self-twin: (1) the **time-aware integrator** `f(t,x)` landed (seasonal forcing evaluated at the RK4 stage times; legacy `f(x)` auto-wrapped; 12/12 tests) — the last plumbing Phase-1 forcing needed. (2) A **symbolic-distillation go/no-go gate** (`scripts/symbolic_distill_probe.py`, 13 tests) distills a trained closure's `(DFe→f_fe)` law by STLSQ against a fixed-k Monod bank + polynomial confounders on the *visited support*, and returns DISTILL-PASS/FAIL as a **second identifiability oracle** that must agree with the Fisher/profile diagnostics. Its load-bearing feature is an **aliasing guard**: a perfectly-Monod closure whose support never spanned the half-saturation knee correctly returns FAIL/non-identifiable — the honest verdict that says *add excitation*, not *spend H200 budget*. (3) That gate, run against the **real closure-training pipeline** (`scripts/symbolic_distill_dynamics_probe.py`: MonodAnchored trained through `column_tendency` on narrow single-IC vs excited multi-IC + seasonal-drawdown support), **lifts the verdict FAIL→PASS** as excitation widens the visited DFe span through the knee — Night-1's "excitation cures equifinality," now quantitatively gate-checked on the actual pipeline (`docs/findings/symbolic_distill_dynamics_probe.json`). Emulator route re-surveyed against the newest primary sources (`docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md`): stays shelved, UDE proceeds; Paper #2 reframed in the **BINN lineage**.

_Original feasibility framing:_ differentiable spatial model (feasibility-proven on the 0-D box only)

Track 2 (a UDE / differentiable spatial emulator) is **feasibility-proven on the 0-D box only** —
self-twin, **synthetic**, transport-free; it is **not** real Darwin and **not** built at real scale.
Nothing runs beyond synthetic self-twin probes. Its make-or-break gate is **E2: held-out real-data
R² > 0 once transport is present** (this is what would turn the Track-1 consistency check into a genuine
discovery); E2 is **unbuilt**. The build plan is gated, riskiest-assumption-first:

- **Phase 1** — a minimal real-data transport UDE (regional 2-D, driven by ECCO-Darwin's own
  velocities) fit to real GEOTRACES iron + calcite, held-out scored (does transport close the surrogate
  gap on real data?).
- **Phase 2** — a physical-backbone differentiability probe (do gradients flow through a real physical
  backbone into a BGC UDE?).
- **Phase 3+** — the full coupled build.

Multi-month, gated on Paper #1 shipping. Backbone survey: **Samudra 2** (arXiv 2606.02610) is the
leading physical backbone but worsens the sparse-obs tension; **SamudrACE** (arXiv 2509.12490) is
differentiable coupled physics with an **explicit biogeochemistry hole** — the natural carbon-BGC-UDE
slot; **ACE2** is atmosphere-only and **OlmoEarth** (land) is a poor fit.

**Honesty guardrail:** Track-2 results to date are synthetic self-twin — do **not** say "made Darwin
differentiable", "learned real biology", or "env-gated calcification proven".

## Known limitations

- **Box model is a 5-tracer proxy** of full Darwin 3 (the 5-PFT + 2-layer extensions close part of the gap).
- **DINN is per-cell, not spatially coupled** — appropriate for parameter recovery, not the Track-2
  spatial UDE. This transport-free limitation *is* the surrogate gap, and closing it on real data is
  precisely Track-2's make-or-break gate (E2).
- **The surrogate gap is dimensional** (see above) — pattern correlations are not fidelity metrics.
  It also blocks held-out *data* validation: the held-out GEOTRACES test ([#163](https://github.com/2imi9/ECCO-DarwinDiff/issues/163))
  returns negative R² because the box homogenizes — a faithful held-out validation needs the spatial UDE.
- **The 1° `geo1` recovery does not transfer to native LLC270 via the shared DINN.** At native,
  *per-AOI* recovery is strong (SO recovers the full iron pair 5/5 alone; eqpac recovers `alpfe`), but
  the shared-DINN 3-AOI joint straddles: natl's native iron genuinely prefers a low `alpfe` (~0.1 — a
  real regional divergence, not a fitting artifact) and SO has no Daniels coverage, so the joint iron
  pair collapses to 0/10. Native *dilutes* the sparse real obs (GEOTRACES iron ≈ 14 surface cells for
  ~10 k native cells). Verified (`verify_run` exit 0); PRs [#122](https://github.com/2imi9/ECCO-DarwinDiff/issues/122)/[#123](https://github.com/2imi9/ECCO-DarwinDiff/issues/123).
- **Climatology, not time-resolved** — all current fits use 23-year time-mean Darwin output.
- **Windows `MAX_PATH`=260** and **laptop sleep** can interrupt unattended overnight sweeps
  (mitigations in the archive / `scripts/recover_failed_config_log.py`).

## Cross-references

- [Config / Results Matrix](docs/results_matrix.md) — the single source of truth for per-config results
- [Ablation Ledger](docs/archive/ablation_ledger.md) — all 168 ablations + the verdict (box-tuning space exhausted)
- [Emulator coupling plan](docs/emulator_coupling_plan.md) — the Track-2 off-box build plan (physical-backbone survey — Samudra 2 as leading backbone, SamudrACE's named biogeochemistry hole as the carbon-BGC-UDE slot — plus the gated Phase 1→3 plan)
- [CHANGELOG.md](CHANGELOG.md) — chronological record (version-by-version)
- [README](README.md) — project overview · [docs/dinn_design.md](docs/dinn_design.md) — architecture
- [docs/cluster_setup.md](docs/cluster_setup.md) · [data/README.md](data/README.md) · [archive](docs/archive/index.md)
