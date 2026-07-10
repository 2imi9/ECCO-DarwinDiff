# DarwinDiff — Project Status

A snapshot of the **current best**, not a timeline. Per-config detail lives in the
[Config / Results Matrix](docs/results_matrix.md); the chronological record is in
[CHANGELOG.md](CHANGELOG.md) and the [archive](docs/archive/index.md).

> **Bottom line (2026-07-10).** Two papers, both at a **collaboration gate**, not a compute gate.
> **Paper #1** (parameter learner) is submission-quality and *good enough*: it recovers the
> identifiable parameters estimator-independently, and what it can't recover is an **identifiability
> limit, not a method limit**. **Paper #2** (Track 2) is complete as a 3-closure
> **identifiability-limits map**: real observations can't sharply constrain the closures, and the
> binding constraint is the **observing system, not the method**. Next for both = a domain-expert
> (Jon) read. **No pending compute** — the box is tuning-exhausted and a positive result needs *new
> observations*, not more GPU; the **emulator** and the **B200** are parked accordingly
> (see [Cluster path](#cluster-path)).

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

- **`R_PICPOC` was never a "6/6 wall."** The "needs a differentiable calcite port + native resolution"
  conclusion is **refuted** (both tested, neither helped); the real gap was the absence of a direct real
  calcite observation (now supplied) + a contaminated Southern-Ocean ratio target (fixed by
  `RATIO_MAX=2`). Any ratio anchor recovers it — so the anchor's value is **non-circularity**, not
  recoverability. It lands at the real ~0.05 (consistent with Carroll's 0.0425 only within the wide Cal
  band, **not** a validation); the spine-D point is that Carroll's *global* `R_PICPOC` is itself
  **under-constrained** and mis-specified against a regionally-variable rain ratio (Daniels eqpac ~0.039,
  ≈1.6× the global mean) — `docs/archive/findings/2026-06-26_rainratio_real_vs_darwin.md`.
- **The per-cell architecture is load-bearing (the surrogate gap is dimensional).** At uniform Carroll
  parameters the 0-D box relaxes to a near-uniform state (tracer CV ~1e-15, vs Darwin's O(1)), so
  box-vs-Darwin pattern correlations are **not** fidelity metrics and identifiability must come from real,
  absolute anchors. A per-cell-vs-global ablation confirms it on real data: at `geo1`, per-cell holds the
  trio **7/10 vs 0/10** for a single global vector (`scav_rat` 8/0, `R_PICPOC` 9/0; Fisher p < 0.01,
  [#158](https://github.com/2imi9/ECCO-DarwinDiff/pull/158)). This is a **consistency check** against
  Carroll's own values, not a cross-validated discovery — which is exactly what Track 2 tested.
- **Independent validation ([#163](https://github.com/2imi9/ECCO-DarwinDiff/issues/163)) decomposes cleanly.**
  *Estimator-independence:* a DINN-free global-scalar recovery and a gradient-free Nelder-Mead both reach
  `alpfe`'s optimum ([#172](https://github.com/2imi9/ECCO-DarwinDiff/pull/172)) — so `alpfe` is
  **method-independent**, while `scav_rat`/`R_PICPOC` genuinely require the per-cell structure.
  *Independent-data:* held-out GEOTRACES cross-validation ([#173](https://github.com/2imi9/ECCO-DarwinDiff/pull/173))
  returns **negative R²** — the box has no spatial structure to predict per-cell iron, so a faithful
  held-out *data* validation is structurally blocked by the surrogate gap (needs the Track-2 UDE). The
  recovery pins the iron *magnitude*, not *which cell has how much*.
- **Statistical honesty.** In the hold-together sweep only two effects are real at n=10 — the ratio anchor
  recovering `R_PICPOC` (3/10→10/10, p=0.003) and high iron weight collapsing `scav_rat` (8/10→0, p=7e-4);
  differences among the high cells are sampling noise. Metric: **per-AOI ≥2-AOI co-recovery**; FIM/profile
  diagnostics agree.

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

- **Explorer** (H200) — the **automation** cluster (key-auth, non-interactive); use for any GPU job
  that must run unattended, and for native/seasonal fits too big for the 5090's 24 GiB.
- **AICR** (B200) — active but **interactive-only** (Duo 2FA → user-launched); use for **throughput**.

**When to use the B200:** for *many/large runs at once*, not for a single fit. A single fit is
launch-bound (same wall-clock on 5090 / H200 / B200), so the B200 buys nothing there. Its genuine use
cases — the **emulator/UDE at real scale** and large native/seasonal ensembles — are all **future and
gated** (Jon's direction / new data). **Nothing is compute-bound right now**, so keep dev + single fits
on the local 5090/CPU. These cluster goals are legitimate but **not** gated on `R_PICPOC` or "6/6",
which are resolved at 1° box scale.

## Track 2 — identifiability-limits map (COMPLETE; real-data E2 run → negative)

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
**symbolic-distillation identifiability oracle** (`scripts/symbolic_distill_probe.py`). Merged to
`main` via #180 (2026-07-10). _Prior Phase-1-tooling status below._

### Foundation + build path (if Track-2 is pursued further)

The differentiable foundation is built and merged (#177): `integrators.py` (RK4 + checkpointing +
time-aware forcing), `carroll6_ude_tendency` (pluggable neural closures), `transport.py`
(mass-conserving vertical transport). The identifiability map above is the **result**; a full
emulator/UDE at real scale is a **forward / OSSE** tool (which new observations would break the limits),
**not an identifiability rescue** — so it is gated on Jon's direction, not a current task. If pursued,
the plan is riskiest-assumption-first: **Phase 1** minimal real-data transport UDE (regional 2-D on
Darwin's own velocities) → **Phase 2** physical-backbone differentiability probe → **Phase 3+** full
coupled build. Backbone survey ([emulator coupling plan](docs/emulator_coupling_plan.md)): **Samudra 2**
leads; **SamudrACE** has an explicit biogeochemistry hole = the carbon-BGC-UDE slot.

**Honesty guardrail:** box-scale Track-2 probes are synthetic self-twin — do **not** say "made Darwin
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
