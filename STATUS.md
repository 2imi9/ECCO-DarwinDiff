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

> **⚠️ `diatomgraz` framing — corrected 2026-07-19, then corrected again later the same day.**
> Do **not** write that `diatomgraz` "carries no observational signal", and do **not** cite its FLAT
> profile-likelihood as evidence of structural non-identifiability. Four points:
>
> 1. **The artifact now EXISTS and is committed** — `docs/findings/silicate_scope/` (13 JSONs,
>    Explorer arrays `8479481` + `8482504`). The remembered numbers were *not* fabricated: the
>    bSi-alone span 0.118 reproduced as **0.1177**.
> 2. **But 9 of the 13 runs FAIL a convergence guard**, and the failure manufactured the headline.
>    The profile starts *from* θ\* and runs further steps, so it out-optimises θ\* by construction;
>    the four parameters that appeared to gain from adding silicate are exactly the four whose
>    profile escaped an unconverged θ\*, while both converged parameters gained nothing. The
>    silicate ablation **cannot currently answer its own question**.
>    See `docs/findings/2026-07-19_silicate_fim_artifact_audit.md`.
> 3. **FLAT does not imply unrecoverable.** In the better-converged arm, four of six parameters are
>    FLAT (span < 0.05) — including **`alpfe` at 0.0235, which this project recovers 9–10/10**.
>    That is the inference the `diatomgraz` claim rested on, and our own data falsifies it.
> 4. FLAT was measured **without** dense Darwin POSi; adding that observable recovers the parameter
>    **10/10** (20/20 under Eppley). Consistent, not contradictory — the profile *predicted* it.
>
> **Defensible framing:** `diatomgraz` is constrained only through a **steady-state biogenic-silica
> diagnostic back-solved from diatom biomass** (`silica.py:78`), not a prognostic silicate cycle —
> the box has 15 tracers, no dissolved SiO₂, no Si co-limitation, whereas ECCO-Darwin fits
> *dissolved* SiO₂ against GLODAP, a different quantity. It is **not recovered on real data**
> (best 4/10 = chance). Say that; do not reach for a structural-identifiability claim.
> See also `docs/findings/2026-07-19_diatomgraz_claim_audit.md`.

## Track 2 — forward emulator: current state (2026-07-19)

A separate build from the UDE/identifiability work below. **All numbers are self-consistency
against v05 output; nothing here has been validated against observations except the chlorophyll
comparison in the last row.**

| | |
|---|---|
| Artifact | `opt3d_seed{0..5}.pt` — FNO2d residual, log-space, rollout-k8, 6-member diverse ensemble |
| Released | 🤗 `2imi9/darwindiff-emulator` **v0.1.0, PRIVATE** (947 MB, tagged) |
| Useful horizon | **1 step**, +0.240 vs a correctly-binned seasonal climatology; at/below it thereafter. *(Measured on the flagship; the Δt-scaled model below has not yet been rollout-tested.)* |
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

### FIXED (2026-07-20) — `--dt-scaled-residual` recovers the monthly operator

The network predicts a **per-month tendency** applied as `x + f(x)·Δt_months`, so all 110 training
pairs teach the monthly rate instead of the long-gap pairs drowning it out. Evaluated with each arm
applied the way it was trained (`scripts/../dt2x2b.py`; artifact
`docs/findings/track2_runs/dt_2x2b.json`), 3 seeds, single-step skill vs persistence in log space:

| arm | mixed val (n=46) | uniform val (n=21) |
|---|---|---|
| mixed train — the flagship | +0.4700 | **+0.0026** (σ 0.0275) |
| uniform train (n=55, half the data discarded) | +0.4508 | +0.4756 (σ 0.0076) |
| **Δt-scaled residual (n=110)** | **+0.4969** | **+0.4801** (σ **0.0005**) |

It **beats both targets at once**: it matches/exceeds the uniform-trained model on true monthly
steps **without discarding half the data** (+0.4801 vs +0.4756), and beats the flagship
in-distribution (+0.4969 vs +0.4700). Seed spread on uniform-val collapses from σ 0.0275 to
**σ 0.0005** — the flagship was not merely poor at monthly cadence, it was *unstable* there.

**No cube rebuild is required.** Cost was ~1 GPU-hour per seed.

> **⚠️ Skill numbers written by `--dt-scaled-residual --regression-only` runs BEFORE commit
> `79717cc` are INVALID.** The reporting block applied the plain residual `x + f(x)` regardless of
> the flag, scoring a per-month tendency as a full-step correction — which understates the model by
> roughly 2× on mixed val (it read +0.384/+0.394 where the truth is +0.4969). Training was always
> correct; only the reported metric was wrong. Recompute from the checkpoints.

### What is and is not a lever (all measured)

| lever | effect | verdict |
|---|---|---|
| **Δt-scaled residual** | **+0.4801 on true monthly steps** (flagship: +0.0026) and **+0.4969** in-distribution (flagship: +0.4700) | **THE FIX — landed 2026-07-20** |
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

**New — a ~2-month timing difference (95% CI 1–4).** MODIS chlorophyll peaks at lag +1 (*after* the
SST anomaly); v05 peaks at lag −2, i.e. it *leads* Niño-3.4. The **measurement is robust** despite
n_eff ≈ 14–34: bootstrap peak-lag CIs do not overlap, and a smooth asymmetry statistic
`r(+1) − r(−2)` separates them by +0.460, 95% CI [+0.246, +0.710], P = 1.000.

> **The CAUSE is not established, and the first explanation was wrong.** The "v05 is missing a
> biological response timescale" reading is **withdrawn**: intrinsic phytoplankton adjustment is
> **1–7 days** (Shi & Wang 2021), so a multi-month offset cannot be a growth/grazing rate.
> Documented equatorial chlorophyll *leads* are **iron-supply** driven (thermocline depth, EUC iron
> advection) and are a **western/central** 2°S–2°N feature — our box is eastern and off-equatorial,
> where the literature reports only a weak ENSO response, consistent with our MODIS +1. So **v05's
> −2 is the number needing explanation, not MODIS.** Report it as a model–observation phase
> discrepancy, not as a diagnosed defect. Most promising untested hypothesis: **iron supply**, which
> ties directly to Track-1's `alpfe`/`scav_rat`.

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
- **`diatomgraz` — not recovered** in the real-data sweep (best 4/10 = chance). Do **not** call this
  "structurally non-identifiable" on the strength of a FLAT profile — `alpfe` is FLAT (0.0235) and
  recovers 9–10/10, so FLAT-implies-unrecoverable is falsified by our own data (see the warning box
  above, and `docs/findings/2026-07-19_diatomgraz_claim_audit.md`). The **structural-vs-practical
  question is open**, and is exactly what the multi-start identifiability array (pilot `8503326` →
  13-task array, `docs/findings/silicate_scope_v2/`) is running to answer — [#152](https://github.com/2imi9/ECCO-DarwinDiff/issues/152).
  Defensible now: it is constrained only through a steady-state biogenic-silica diagnostic
  back-solved from diatom biomass, not a prognostic silicate cycle, and is **not recovered on real
  data**. In principle it is an **iron-pair tradeoff** recoverable via the dense Darwin POSi (`TRAC16`)
  target, which is **not staged**; that is a future data-staging option, not a Track-1 blocker.

### Accuracy & quality matrix (per parameter — current best)

Recovery is against Carroll's published value. Two configs feed this: **`geo1`** fits *real* GEOTRACES
iron + a real calcite anchor (the headline); **`silicate_scope`** is *synthetic* self-recovery (growth/Si).

| param | recovers? | best | config | identifiability class | seed-robust |
|---|---|---|---|---|---|
| **alpfe** | ✅ ≈Carroll | 10/10 | geo1 (real Fe) | method-independent (DINN-free + Nelder-Mead), near-saturated | ✅ tight |
| **scav_rat** | 🟡 in-band | 8/10 | geo1 (real Fe) | **not point-identified** (CV≈43%); needs per-cell (0/10 global) | ✅ verdict-tight |
| **R_PICPOC** | ✅ ~0.05 | 9/10 (10/10 RATIO_MAX) | geo1 (real calcite) | point-identified; needs per-cell (0/10 global); **≠ validation of 0.0425** | ✅ |
| **diatomgraz** | ❌ (best 4/10 = chance) | — | geo1 | not identified on real data; structural-vs-practical **open** | ✅ fails-tight |
| **Smallgrow** | ❌ real / ✅ synth+Si | 7/7 synth | silicate_scope | real-unobservable (excluded from target); synthetic-ID with Si | ✅ 7/7 (rel-err 0.001–0.009) |
| **Biggrow** | ❌ | 0/7 | silicate_scope | not identified (synthetic or real) | ✅ fails-tight (0.68–0.71) |
| **Trio {alpfe,scav_rat,R_PICPOC}** | ✅ per-cell | **7/10** (0/10 global) | geo1 | **per-cell load-bearing** — cleanest quantitative result | ✅ |

Supporting: **per-AOI Fisher** — Eq. Pacific & N. Atlantic carry the iron information, Southern Ocean
does not; per-AOI sloppiness ≈3.96 decades (Eq. Pac) is **provisional** — θ\* is a saddle (non-positive
Hessian eigenvalue), so the decade-span needs the multi-start re-run ([#120](https://github.com/2imi9/ECCO-DarwinDiff/issues/120)/[#187](https://github.com/2imi9/ECCO-DarwinDiff/issues/187)) before it is quotable.
**FeMIP framing** — external-validated (Tagliabue Table 2, above). Seed-tightness for the iron trio is the
`geo1` 38/40 & 7/10 counts; for the growth/Si params it is the synthetic `silicate_scope_v2_seeds` sweep
(Explorer `8512053`). Improvement path: [#187](https://github.com/2imi9/ECCO-DarwinDiff/issues/187).

→ Every config that produced these, and how each differs, is in the **[Config / Results Matrix](docs/results_matrix.md)**.

## External validation (2026-07-20) — the iron pair grounds against the published literature

A hostile-verified literature pass (`docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md`)
lands two settled results, independent of the identifiability array:

- **The iron `alpfe`/`scav_rat` degeneracy we recover IS the published FeMIP problem.** Tagliabue et al.
  2016 (GBC, [10.1002/2015GB005289](https://doi.org/10.1002/2015GB005289)): across 13 models, dissolved-Fe
  residence time roams **3.7–626 yr (~170×)** while concentration stays pinned at **0.58 ± 0.14 nM (~24%)**
  and input flux roams **~100%** — "sources compensated by variable scavenging rates to reproduce the observed
  DFe concentration." Somes et al. 2021 ([10.1029/2021GB006948](https://doi.org/10.1029/2021GB006948)) is a
  controlled 5-run demonstration. The field measures this but **never names it as identifiability/sloppiness**
  (soil/terrestrial biogeochem do) — so framing it via a profile-likelihood is a contribution *to their field*.
  The observable that breaks it is the GEOTRACES **section gradient**, not the global mean (which the 0-D box
  homogenizes away — re-motivating Track-2). **Derived + validated against Tagliabue's own Table 2**
  (`docs/research_notes/2026-07-20_iron_degeneracy_math_validation.md`, reproducible
  `scripts/analysis/iron_degeneracy_math.py`): the single-box Fisher is rank-1 (concentration stiff,
  residence time sloppy), and the 169× residence spread decomposes as **130× from input flux × 1.3× from
  inventory** — input-dominated (sediment source spans 0–194 Gmol/yr), inventory pinned to ~2×. A tempting
  "deep-inventory second degeneracy" was falsified by the data (inventory varies only 2×) and discarded.
- **`alpfe` is a near-unity scalar on already-soluble iron, NOT a solubility.** Darwin3's own docs: `alpfe`
  "set to 1 if the ironfile is already soluble"; v05 forces with the soluble Mahowald-2009 product and sets
  `ALPFE = 0.928`. Published dust-Fe solubility is <1–2% — not ~0.93. The "iron dust solubility" label is fixed
  in `carroll6.py`/`carroll6_5pft.py`. (Citation fix: Darwin's iron model is Parekh, Follows & Boyle **2005**,
  GBC 19 GB2020 — *not* the "2006" DOI `10.1029/2005PA001258`, which is a different paper.)
- **Quantitative companion (Explorer `8510828`, `docs/findings/iron_residence/`):** our recovered surface iron
  residence time is **~1–8 days** across the three AOIs — the order of the *observed upper-ocean* envelope
  (Black 2020: 10–100 d), not the whole-ocean model range. Within the data-consistent band τ barely roams
  (1.1–1.7×) because the real section structure constrains `alpfe` per-AOI (0.83–1.00 ≈ Carroll) — the per-cell
  fit escapes the global-mean-only degeneracy, concretely realizing Somes 2021.

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

Two clusters — Explorer (Northeastern-owned) and AICR (the multi-institutional Massachusetts AI
Compute Resource, accessed via NU) — full table in [docs/cluster_setup.md](docs/cluster_setup.md):

- **Explorer** (Northeastern, H200) — the **automation** cluster (key-auth, non-interactive); use for
  any GPU job that must run unattended, and for native/seasonal fits too big for the 5090's 24 GiB.
- **AICR** (Massachusetts AI Compute Resource, B200) — account active but **interactive-only** (Duo 2FA
  → user-launched); use for **throughput**.

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
