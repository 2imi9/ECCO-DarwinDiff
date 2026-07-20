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

> **⚠️ `diatomgraz` framing — corrected 2026-07-19.** Do **not** write that `diatomgraz` "carries
> no observational signal." Three problems: (i) the FLAT profile-likelihood result (span 0.039)
> exists in project memory but **no artifact is committed to this repo** — the 07-07 profiles doc
> mentions it only in a *threshold-legend caption*, while three downstream documents cite it as
> established, one as a gate on H200 spend; (ii) FLAT was measured on the loss **without** dense
> Darwin POSi, and adding that observable recovers the parameter **10/10** (20/20 under Eppley) —
> those are consistent, not contradictory, and the profile *predicted* it; (iii) our bSi observable
> is a **steady-state diagnostic back-solved from diatom biomass** (`silica.py:78`), i.e. partly
> circular — the box has 15 tracers, **no dissolved SiO₂**, no Si co-limitation — whereas
> ECCO-Darwin fits *dissolved* SiO₂ against GLODAP, a different quantity.
> **Defensible instead:** `diatomgraz` is constrained only through a steady-state biogenic-silica
> diagnostic, not a prognostic silicate cycle. Re-run the profile with `--out` and commit the JSON
> before the manuscript leans on it. See `docs/findings/2026-07-19_diatomgraz_claim_audit.md`.

## Track 2 — forward emulator: current state (2026-07-19)

A separate build from the UDE/identifiability work below. **All numbers are self-consistency
against v05 output; nothing here has been validated against observations except the chlorophyll
comparison in the last row.**

| | |
|---|---|
| Artifact | `opt3d_seed{0..5}.pt` — FNO2d residual, log-space, rollout-k8, 6-member diverse ensemble |
| Released | 🤗 `2imi9/darwindiff-emulator` **v0.1.0, PRIVATE** (947 MB, tagged) |
| Useful horizon | **1 step**, +0.240 vs a correctly-binned seasonal climatology; at/below it thereafter |
| Physics | 0% negative concentrations, mass ratio 1.000 at every horizon tested |
| Speed | 7.45 ms/global step, 2.29 GB inference |

### Four things that were wrong and are now corrected

1. **`delta_t` was 900 s; v05 runs at 1200 s.** Every pre-2026-07-19 cube's `times_days` is 0.75×
   truth. Fixed at the root (PR #186, merged to `main`). **Derive time from `iters`, never from
   `times_days` on an old cube.** 94% of month-of-year bins were wrong, which weakened the
   climatology baseline and inflated skill-vs-climatology by +0.37 to +0.78.
2. **The "~9-month horizon" is RETRACTED.** Against a correct seasonal climatology it is 1 step.
3. **"v05 daily ends 2012-03-31" was an artifact of #1.** It ends **2018-12-31**, which nearly
   doubles the MODIS overlap.
4. **The single-step numbers describe a ~2-month operator, not a monthly one.** The validation set
   has a median gap of 61 days. On genuinely-monthly pairs the flagship scores **+0.0026** — no
   skill over persistence — while a model trained only on 1-month pairs scores **+0.4756**.

### What is and is not a lever (all measured)

| lever | effect | verdict |
|---|---|---|
| **Δt uniformity** | **+0.4730** in-distribution | **THE lever** — found 2026-07-19 |
| Rollout-aware training (k8) | mass 1.000 vs k1 diverging to 3.05e8 | load-bearing (stability) |
| Log-space | 0% negatives by construction; correct metric | load-bearing |
| Deep ensembling (8 seeds) | +0.14 / +0.05 | load-bearing |
| Data **quantity** | flat from n=55 | **not a lever** |
| Capacity (~4× params) | +0.007 | **not a lever** |
| EDM diffusion | 0 to −0.026 | **not a lever** for skill |
| Physical-state conditioning | +0.0041 oracle bound | **not a lever** |

### First observational result — TWO regions, and the bias is regime-specific

**v05 chlorophyll vs MODIS-Aqua**, 2003–2018. Novel — chlorophyll is not evaluated at all in
ECCO-Darwin's own 135-figure white paper.

| | subpolar N. Atlantic (176 mo) | equatorial Pacific (192 mo) |
|---|---|---|
| bias | **−0.696 dex (5.0× low)** | **−0.077 dex (0.84×)** — INSIDE the 0.130 noise floor |
| coverage | 78.5% mean, 1.5% min | **98.6% mean, 90.9% min**, zero cells clipped |
| r all-months | +0.779 | +0.034 |
| r deseasonalised | +0.044 | **+0.331** |

**Do not say "v05 chlorophyll is 5× low" unqualified.** It is unbiased in the oligotrophic regime —
on the best-observed data in the comparison — and 5× low in the **bloom** regime. That points at
bloom dynamics, not a global scaling error. In the Atlantic v05 still reproduces the May–June bloom
peak inside the satellite's own retrieval uncertainty, and ends its bloom two months early.

> **⚠️ The all-months Pearson r is uninformative and misleads in BOTH directions** — flattered in the
> Atlantic by a shared seasonal cycle (+0.779 vs anomaly +0.044), maligned at the equator by the
> absence of one (+0.034 vs anomaly +0.331). **Report the deseasonalised anomaly r.** It is
> regime-independent, unlike a growing-season window (May–Sep is meaningless at the equator). The
> existing growing-season r = 0.016 for natl stands and is corroborated by anomaly r = +0.044.

**eqpac interannual skill is ENSO and nothing else,** and is marginal as an aggregate: lag-1
autocorrelation puts effective N at **34, not 192** (p ≈ 0.048). It is the mechanism that makes it
real — against the downloaded NOAA PSL Niño-3.4 index, **r = +0.524 in ENSO-active months vs
−0.052 in neutral months**, with v05 capturing **0.89×** the observed ENSO sensitivity at the correct
sign. **Quote n_eff alongside any r from this analysis.**

**New — a ~3-month phase error.** MODIS chlorophyll peaks at lag +1 (responds *after* the SST
anomaly); v05 peaks at lag −2, i.e. it *leads* Niño-3.4. Hypothesis, **not established**: v05's
biology tracks modelled upwelling near-instantaneously and inherits the thermocline lead, while real
phytoplankton add growth/grazing inertia — so the missing quantity may be a **biological rate**,
which is directly relevant to the UDE track.

Detail: `docs/findings/2026-07-19_{emulator_honest_bounds,results_matrix,two_negatives,v05_chlorophyll_vs_modis,eqpac_chlorophyll_vs_modis}.md`.
Artifacts `docs/findings/chl_val/`; script `scripts/compare_v05_modis_aoi.py` (reproduces the
committed natl numbers exactly as a regression check).

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

## Track 2 — differentiable spatial model — PRIOR STATUS (SUPERSEDED by the section above; E2 has since been RUN → decisive negative). Retained for the 07-07/07-09 foundation record.

**Update (2026-07-07) — the differentiable foundation is now built and merged (#177).** `integrators.py` (RK4 + gradient checkpointing + time-aware forcing `f(t,x)`), `carroll6_ude_tendency` (pluggable neural closures), and `transport.py` (mass-conserving batched-column vertical transport) are on `main`. On a **synthetic self-twin** (still not real Darwin, still transport-limited), closure equifinality was diagnosed as a **support problem** and cured: a **Monod-anchored closure** (~15x over a free MLP) plus an **excitation designed offline for pennies** (a ~2-min CPU Fisher probe found the lever is *light-driven drawdown, not dust*) recovers the closure over the widest domain -- excitation ladder, full-domain closure error `0.203 -> 0.173 -> 0.154 -> 0.116` (n=4). This is a **synthetic methods result, not a real-data claim**; the E2 gate (held-out real-data R^2 > 0 with transport) was the make-or-break — **as of the section above it has since been built and run (decisive negative)**; this paragraph records the prior 07-07 state. Design docs: `docs/research_notes/2026-07-06_*`. The three-component picture (DINN parameter learner / FNO emulator scaffold `emulator.py` / mechanistic UDE) and the parameter-learner<->emulator seam are in `docs/NEXT_SESSION.md`.

**Update (2026-07-09) — Phase-1 tooling + an independent identifiability oracle (all local CPU).** Three additions, still synthetic self-twin: (1) the **time-aware integrator** `f(t,x)` landed (seasonal forcing evaluated at the RK4 stage times; legacy `f(x)` auto-wrapped; 12/12 tests) — the last plumbing Phase-1 forcing needed. (2) A **symbolic-distillation go/no-go gate** (`scripts/symbolic_distill_probe.py`, 13 tests) distills a trained closure's `(DFe→f_fe)` law by STLSQ against a fixed-k Monod bank + polynomial confounders on the *visited support*, and returns DISTILL-PASS/FAIL as a **second identifiability oracle** that must agree with the Fisher/profile diagnostics. Its load-bearing feature is an **aliasing guard**: a perfectly-Monod closure whose support never spanned the half-saturation knee correctly returns FAIL/non-identifiable — the honest verdict that says *add excitation*, not *spend H200 budget*. (3) That gate, run against the **real closure-training pipeline** (`scripts/symbolic_distill_dynamics_probe.py`: MonodAnchored trained through `column_tendency` on narrow single-IC vs excited multi-IC + seasonal-drawdown support), **lifts the verdict FAIL→PASS** as excitation widens the visited DFe span through the knee — Night-1's "excitation cures equifinality," now quantitatively gate-checked on the actual pipeline (`docs/findings/symbolic_distill_dynamics_probe.json`). Emulator route re-surveyed against the newest primary sources (`docs/research_notes/2026-07-09_parameter_conditioned_emulator_update.md`): stays shelved as of this 07-09 survey, UDE proceeds — **superseded (2026-07-13/14): an ECCO-Darwin v05 emulator was subsequently built and evaluated (daily surface, global monthly surface, monthly 3-D depth-resolved; see `docs/findings/2026-07-13_*` / `2026-07-14_*`, which remain the single source for the numbers). Three standing caveats travel with any emulator skill figure: (i) it is self-consistency vs v05 only — never validated against real observations; (ii) skill is reported in LINEAR space unless explicitly labelled, and the log-space control is config-dependent — the monthly flagship survives it, the daily configs largely do not; (iii) the earlier plateau is epistemic, not an intrinsic ceiling — deep ensembling lifts it, while the separate capacity-saturation result (more parameters buy ~nothing) still stands. Capacity is not the lever; ensembling is.**; Paper #2 reframed in the **BINN lineage**.

_Original feasibility framing (07-06, historical):_ differentiable spatial model (feasibility-proven on the 0-D box only)

Track 2 (a UDE / differentiable spatial emulator) was, at this point, **feasibility-proven on the 0-D
box only** — self-twin, **synthetic**, transport-free. Its make-or-break gate was **E2: held-out
real-data R² > 0 once transport is present** (this is what would turn the Track-1 consistency check
into a genuine discovery); **E2 was subsequently built and run — see the current section at the top of
Track 2 (decisive negative).** The original riskiest-assumption-first build plan was:

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
