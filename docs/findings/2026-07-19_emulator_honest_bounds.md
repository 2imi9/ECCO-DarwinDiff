# Emulator honest bounds — what survives, what does not (2026-07-19)

## The defensible claim

> A **~9-month, ensembled, rollout-trained, log-space, physically-valid seasonal BGC surrogate of
> ECCO-Darwin v05** — 0% negative concentrations, useful skill above climatology to ~9 months,
> stable mass (ratio 1.0002 at 9 months).

The caveat is not a footnote. Every number in this document is **self-consistency against the v05
model output**. The emulator has **never** been validated against real observations (issue #163).
It is a surrogate of a model, not a model of the ocean.

All numbers below were re-derived from the raw result JSONs on `/scratch/qi_zim_neu/` on 2026-07-19,
not copied from prior prose. Provenance is given per section.

## What this session-arc disproved

Three claims we had made in our own findings docs are now wrong. Each was disproved by a control we
had never run. They are recorded here as results, not as damage.

| Prior claim | Where it lived | Status | What the control showed |
|---|---|---|---|
| "+0.52 is a hard, intrinsic ceiling" | `2026-07-14_emulator_loop.md` | **REFUTED** | An 8-seed deep ensemble lifts skill (+0.14 daily eqpac, +0.05 monthly 3-D). The plateau was epistemic, not aleatoric. |
| "the daily emulator beats persistence, verdict MAKE (+0.408)" | `2026-07-13_daily_surface_emulator.md` | **LARGELY A LINEAR-METRIC ARTIFACT** | Same config, only the transform differs: +0.3000 linear → **+0.0361 log**. Global daily log: **+0.005** (a null). |
| "the rollout is dead by 6 months" | scratch, 2026-07-17 | **PARTIALLY WALKED BACK** | True for single-step training. Rollout-aware k8 training reaches ~9 months above climatology. |

A fourth prior claim was tested and **survives unchanged** — capacity saturation. It is listed
separately below because it is the one thing in this cluster that did not move.

## ⚠ The calendar bug — found 2026-07-19, and it cuts both ways

This is the most consequential finding in this document, because it attacks the **climatology
baseline** that the rest of our honesty framing rests on.

### Defect 1 — the stored time axis is 25% too small

`times_days` in the cubes was built with a **900 s** timestep. ECCO-Darwin v05 runs at **1200 s**
(72 iterations/day, confirmed from our own daily data and the published configuration). Verified
directly: `times_days * 86400 / iters` returns exactly **900.0** for every timestep, and
`times_days[0]` = 23.25 d, whereas iteration 2232 at 1200 s is 31.0 d. Every stored time is
exactly **0.75×** the truth. `iters` (raw MITgcm iteration numbers) are ground truth.

**Consequence:** `rollout_verify.month_of_year()` derived the climatology bin from `times_days`.
With a 0.75× axis, the month-of-year assignment drifts progressively over the 26.8-year record.
Measured: **150 of 158 timesteps (94.9%) land in the WRONG month-of-year bin.** Bin occupancy
collapses from a roughly even spread to a heavily skewed one (true occupancy ranges 3–23 per month).

A climatology built from near-randomly-assigned months is much closer to a **time-mean** than to a
**seasonal cycle** — and a time-mean is a *weaker* baseline, because it carries no seasonal signal to
beat. **So our reported skill-vs-climatology was measured against a bar that was too low, and is
therefore overstated.** This is precisely the class of error this session-arc exists to catch, and we
committed it in the very metric we adopted to be more honest.

### Defect 2 — the cube is not a contiguous monthly series, and horizons are steps

Recomputed on the correct axis, consecutive-index spacing is **median 59 days, max 212 days**. Only
**76 of 157 pairs (48.4%) are genuinely one month apart**; the remaining **51.6% span 2–7 months**
and were trained as if they were single one-month steps. The cube spans 26.83 years; a contiguous
monthly series would have 323 steps, but the cube has **158** — roughly half the months are absent.

Two implications:

1. **The learned operator is not a one-month operator.** It is a blend of 1-to-7-month transitions.
2. **The horizon labels are step counts, not months.** In the validation split the median step is
   **61 days ≈ 2.0 months**, so the reported horizons correspond to roughly **double** the elapsed
   time we have been claiming:

   | reported | actual elapsed |
   |---|---|
   | "1 mo" | ~2.0 months |
   | "3 mo" | ~6.0 months |
   | "6 mo" | ~12.0 months |
   | "9 mo" | **~18.0 months** |

### Net effect on the headline claim

The two defects push in **opposite directions** and do not cancel — they act on different axes:

| defect | axis affected | direction |
|---|---|---|
| corrupted climatology bins (94.9% wrong) | **skill magnitude** | baseline too weak ⇒ **skill overstated** |
| horizons are steps, ~61 d each | **duration** | ⇒ **elapsed time understated (~2×)** |

Until the corrected-calendar re-evaluation is complete, **the "~9-month" claim should be treated as
unverified in both magnitude and units.** `rollout_verify.py` now derives the calendar from `iters`
by default (`--calendar iters --dt-seconds 1200`), reports true elapsed months per horizon, and
retains `--calendar times_days` solely to reproduce the old, wrong behaviour for comparison.

**This defect affects every skill-vs-climatology number this project has reported.** It does not
affect skill-vs-persistence (which needs no calendar), nor the log-space controls, nor the physics
checks, nor the deep-ensemble comparisons — those are calendar-free.

## Metric-space labelling (read this before any number)

Global chlorophyll is log-normal. Measured on the native files: **p99/p1 = 2.8 × 10⁶**, skewness
**+4.86 linear** and **−2.31 log**. A linear-space MSE skill score is therefore set by a handful of
bloom cells, while the oligotrophic bulk of the ocean collapses to ≈0 in z-space and contributes
almost nothing.

Consequently **every skill number in this project must carry its metric space.** The historical
numbers — +0.52, +0.5204, +0.5165, +0.507, +0.408, +0.30, +0.432 — are all **linear-space
skill-vs-persistence**. They are not wrong; they were **under-labelled**. The correction is to label
them, not to delete or alter them.

## Log-space controls (identical config, transform is the only difference)

Provenance: `eqpac_ctl_linear.json`, `eqpac_ctl_log.json`, `d3_ctl_log.json`. Verified matched —
same seed (0), same cube, `rollout_train_k: None` in all three; only `log_transform` differs.

| run | linear skill | log skill | change | verdict |
|---|---|---|---|---|
| **flagship monthly 3-D** | +0.432 | **+0.3649** | −15% | **SURVIVES** |
| daily eqpac | +0.29997 | **+0.03614** | −88% | **COLLAPSES** |
| global daily | — | **+0.005** | — | **NULL** |

The flagship monthly result is real. The daily result is not a chlorophyll-field result.

**The honest daily statement:** linear MSE is dominated by high-Chl bloom cells, where the model
genuinely does beat persistence (−30% MSE). Across the log-normal bulk it adds +3.6%. **The daily
emulator predicts bloom dynamics, not the chlorophyll field.** Neither space is "wrong" — linear
matters for biomass/carbon budgets, log is the standard space for assessing Chl fields
(Campbell 1995) — but the claim must be stated in the space it was measured in.

## The ceiling refutation

The control never run: train N independent models on different seeds and average them — the trivial
UQ/skill baseline the diffusion was never compared against. Parity verified: `persistence_mse` is
identical to 6 dp (0.031955240800493966) between the diffusion run and the ensemble run, confirming
the same cube and split.

Provenance: `de_eqpac_ensemble.json`, `de3d_ensemble.json`.

| setup | single | ens-mean (8 seeds) | gain | calib (spread/rmse) |
|---|---|---|---|---|
| daily eqpac (4 tracers, 81×201), linear | +0.30387 | **+0.44540** | **+0.1415** | 0.2852 |
| monthly 3-D (60 ch, 680×1440), linear | +0.43218 | **+0.48371** | **+0.0515** | 0.2309 |
| *EDM diffusion on 3-D (contrast)*, linear | +0.421 | +0.395 | **−0.03** | — |

1. **Ensembling gains in both regimes** — across cadence, domain and channel count. The correction
   is not a one-off. But the gain is **regime-dependent (+0.14 vs +0.05); do not quote a universal
   number.**
2. **The EDM diffusion adds zero skill anywhere** and on 3-D actively hurts (+0.421 → +0.395),
   despite 2,048 forward passes per field (32 samples × 64 Heun steps) against the deep ensemble's 8.
3. **Any phrasing of the form "intrinsic ceiling" / "close to the intrinsic limit" / "hard ceiling" /
   "improvement space exhausted" is now wrong** and must be corrected wherever it appears.
4. **Honest caveat:** this is classic variance reduction and scales with how noisy individual members
   are. It does not prove the aleatoric limit is beatable — only that we were not at it.

### Capacity saturation still holds

The capacity ladder result — **+0.007 for ~4× the parameters** — is unaffected by the above and
stands. The correct joint reading is: *capacity is not the lever, but that does not make the ceiling
intrinsic; ensembling is the lever.*

## Third validator: physics-equation verification

Our only two yardsticks were self-consistency vs the v05 model and real obs (#163, untouched). Both
are *data* comparisons, and **an MSE skill score is blind to physics** — a model can score well while
emitting chemically impossible seawater. Physics checks need no reference data at all.

Design rule (load-bearing): every check runs on **v05 truth as a control column**, so a violation the
emulator merely *inherits* is not charged to the emulator.

Provenance: `physics_3d.json` (8-member 3-D deep ensemble vs v05 control).

| check | v05 (control) | emulator | verdict |
|---|---|---|---|
| positivity — **FeT** | **1.9 × 10⁻⁷** (numerically zero) | **0.0451** | **FAIL — invented, not inherited** |
| positivity — Chl1 | 0.0446 | 0.2515 | worse (partly inherited) |
| positivity — POC | 0.0059 | 0.0805 | worse |
| positivity — PIC | 0.1252 | 0.1775 | mostly inherited (v05 is itself 12.5% negative) |
| positivity — DIC/ALK | 0.0000 | 0.0000 | clean |
| ALK:DIC ratio | 100% in band, med 1.1082 | 100% in band, med 1.1080 | **PASS** |
| carbonate closure | 100% solvable, pCO₂ **380.33** µatm | 100% solvable, pCO₂ **380.84** µatm | **PASS** (0.51 µatm apart) |

> **Precision note (2026-07-19).** Earlier write-ups stated v05's negative-iron fraction as
> "0.0000" / "zero". Recomputed from `physics_3d.json`, it is **1.89 × 10⁻⁷** (minimum value
> −6.06 × 10⁻⁶) — numerically zero, i.e. float noise, but not literally zero. The finding is
> unaffected: the emulator's 4.5% is ~240,000× larger and is *invented*, not inherited. Recorded
> because a permanent document should not round a measured value to a rhetorically cleaner one.

1. **The benchmark caught what skill cannot.** This model scores **+0.43 (linear)** while emitting
   **4.5% negative iron where v05 emits numerically none**. The control column is what makes
   "invented" separable from "inherited".
2. **Genuine good news:** the carbonate system is chemically valid. (DIC, ALK) pairs are 100%
   physical and solve to a median pCO₂ 0.51 µatm from v05's. The emulator learned valid seawater
   without being told chemistry exists.
3. **Convergence.** Log-space training fixes this by construction — exp(·) > 0 always. The optimized
   log-space package measures **0.0000 negatives on all tracers**. `--log-transform` fixes both the
   metric artifact and the invented-negative violation.
4. **Check D (CaCO₃ stoichiometry, ΔALK ≈ −2·ΔPIC) was badly designed, and the control exposed it.**
   v05 itself shows correlation 0.018 — essentially no ΔALK–ΔPIC relation. If the stoichiometry were
   visible in these increments, v05 would show it. At monthly cadence and 0.25° the total ΔALK is
   dominated by **transport**, while the −2:1 law applies only to the local biological source term.
   **The premise was wrong, not the model.** This finding directly motivates the physical-state
   conditioning experiment: if transport dominates the tendency, the emulator is currently being
   asked to infer circulation from tracer patterns alone.

## Rollout horizon — and the baseline that hides drift

Persistence decays at long lead, so beating it gets *easier*. **Climatology** (month-of-year mean,
training period only, no leakage) is the honest bar.

### The baseline problem, stated once

At 12 months the single-step rollout reads **+0.441 vs persistence** (looks strong) and **−0.265 vs
climatology** (worse than the seasonal mean). Every long-horizon Track-2 number quoted historically
is vs persistence. **Long-horizon skill reported against persistence alone is misleading and must
co-report climatology.**

### Matched k1-vs-k8 comparison

Provenance: `matched_k1.json`, `matched_k8.json`. Both LOG space, **n_starts = 15**, **n_members = 6**,
skill vs **CLIMATOLOGY**. This matched design removed two confounds that fooled an earlier look:
a log-vs-linear space mismatch between arms, and n_starts=6 on a 47-month split (rollouts overlapping
by 35/36 steps, effectively n≈1 at long lead).

| horizon | k1 single-step | k8 rollout-trained |
|---|---|---|
| 1 mo | +0.5465 | **+0.6139** |
| 2 mo | +0.1286 | **+0.4694** |
| 3 mo | **−0.3725** (dead) | **+0.4318** |
| 6 mo | **−1.9110** (catastrophic) | **+0.2594** |
| 9 mo | −5.0974, mass ratio **99.58** (diverging) | **+0.2527**, mass **1.0002** |
| 12 mo | −14.5976, mass ratio **30,536** (fully diverged) | **+0.0283** (at the climatology floor), mass **1.0002** |

**Rollout-aware training is the #1 horizon lever: useful horizon ~2 months → ~9 months** — larger
than any other lever tried. Single-step training does not merely degrade, it **diverges**; the
rollout-trained model stays stable and above climatology throughout. `neg_frac = 0.000` at every
horizon in both arms.

The 12-month row is why **~9 months** is the right claim rather than ~12: k8 is still marginally
positive at 12 months (+0.028), but that is the climatology floor, not useful skill.

## Levers: load-bearing vs not

| lever | effect | verdict |
|---|---|---|
| **Rollout-aware training (k8)** | useful horizon ~2 mo → ~9 mo (log, vs climatology) | **LOAD-BEARING — #1** |
| **Deep ensembling (8 seeds)** | +0.14 / +0.05 linear skill; keeps rollout alive; 3× fewer negatives | **LOAD-BEARING** |
| **Log-space transform** | fixes the metric artifact; 0% negatives by construction | **LOAD-BEARING** |
| Capacity (modes/width, up to ~4×) | +0.007 | **Not a lever** — saturated |
| EDM diffusion corrector | zero skill; −0.03 on 3-D; only wins calibration (0.375) | **Not a lever for skill** |
| Architectural diversity in the ensemble | calibration 0.240 — unchanged | **Not a lever for calibration** |

## Speed — measured, and irrelevant

Provenance: `bench.json`. One next-month global state (680×1440, 60 channels, 18.91 M params):
**7.45 ms**, inference peak memory **2.29 GB** — i.e. laptop-runnable; the B200 buys *training*
throughput, not capability. One simulated century is ~9 s.

**This does not matter.** A century in 9 seconds is worthless when the trajectory reaches the
climatology floor at ~9–12 months. Speed was never the bottleneck; rollout fidelity is.

## What is NOT established

- **No observational validation.** Zero. Every number here is self-consistency vs the v05 model
  output. Validation against SOCAT / GLODAP / MODIS (#163) is untouched, and is the step that would
  make this a scientific finding rather than a model surrogate.
- **Calibration is unmoved.** Spread/RMSE sits at **0.240**, against an ideal of ~1.0. Deep
  ensembling made it slightly *worse* (0.285 / 0.231), architectural diversity did not move it
  (0.240), and only the diffusion reached 0.375 — while adding no skill. **The ensemble is
  over-confident and we have no fix.** A deep-ensemble-mean + diffusion-spread hybrid is the
  untested candidate.
- **The aleatoric limit is unknown.** We know we were not at it. We do not know where it is.
- **The long-horizon numbers rest on limited independent starts.** n_starts=15 on a 47-month val
  split still means overlapping trajectories at 9 months. The ~9-month figure is a bound to be
  re-measured on a longer split, not a precision estimate.
- **No physical state is used at all.** The emulator receives only BGC tracers — no temperature,
  velocity, mixed-layer depth, light, or sea ice. Given that transport dominates the monthly tendency
  (see check D above), it is currently inferring circulation from tracer patterns alone.

## Do not conflate these runs

Distinct experiments with distinct numbers. A "correction" that silently swaps one run's number for
another's is a false correction.

| run | headline (linear space) |
|---|---|
| global monthly **surface** | +0.5204 (seed 0); +0.5165 ± 0.0023 (n=5) |
| monthly **3-D** depth-resolved | +0.507; and separately +0.432 (the single member the log/ensemble controls were run against) |
| **daily eqpac** | +0.30 |
| **daily global** | +0.408 |

## Conclusion

The arc cost us three claims and bought one defensible artifact. The emulator worth keeping is the
**k8-log diverse ensemble** (`opt3d_seed*.pt`): ~9-month useful horizon above climatology, 0%
negative concentrations, valid carbonate chemistry, stable mass. Its skill is real in log space at
monthly cadence and largely an artifact at daily cadence. It is calibrated badly and validated
against nothing but the model it imitates.

The controls that produced every correction above — a seed ensemble, a transform swap, a climatology
baseline, a physics check with a truth control column — were each cheap and each overturned something
we believed. **The pattern is the finding: our errors were not in the models, they were in the
missing controls.**
