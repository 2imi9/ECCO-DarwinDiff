# Emulator honest bounds — what survives, what does not (2026-07-19)

## The defensible claim

> **RETRACTED AND RESTATED 2026-07-19 (job 167823).** The claim below previously read *"a ~9-month
> ... surrogate ... useful skill above climatology to ~9 months."* Measured against a **correctly
> binned** seasonal climatology, that is **false**. See *The calendar bug* and *Rollout horizon*.

> A **~1-step (~2-month), ensembled, rollout-trained, log-space, physically-valid BGC surrogate of
> ECCO-Darwin v05** — 0% negative concentrations, stable mass (ratio 1.000 at every horizon tested),
> beating a true seasonal climatology at **one step only** (+0.240), and at or below it thereafter.

The caveat is not a footnote. Every number in this document is **self-consistency against the v05
model output**. The emulator has **never** been validated against real observations (issue #163).
It is a surrogate of a model, not a model of the ocean.

All numbers below were re-derived from the raw result JSONs on `/scratch/qi_zim_neu/` on 2026-07-19,
not copied from prior prose. Provenance is given per section.

> **✅ Provenance CLOSED and VERIFIED (2026-07-19).** All eight source JSONs are now committed under
> [`track2_runs/`](track2_runs/) — they previously lived only on `/scratch/qi_zim_neu/`, which is
> subject to a 30-day purge, so the claim above was true but uncheckable by anyone including the
> author once the purge ran. Recomputed from the committed files, the headline numbers match this
> document **exactly**:
>
> | check | artifact | recomputed | as written |
> |---|---|---|---|
> | eqpac daily, linear | `eqpac_ctl_linear.json` | **+0.3000** | +0.3000 |
> | eqpac daily, log | `eqpac_ctl_log.json` | **+0.0361** | +0.0361 |
> | throughput / memory | `bench.json` | **7.45 ms/step, 2.29 GB** | 7.45 ms, 2.29 GB |
> | calendar ratio | `cal_ab.json` | 45.0 → 60.0 d = **4/3** | `delta_t` 900 → 1200 s |
> | training pairs | `d3_ctl_log.json` | **110** train / 46 val | ~110 |
>
> Worth stating plainly: unlike the silicate-scope artifact — which arrived and **failed** its
> convergence check — these corroborate the document they support.

## What this session-arc disproved

Three claims we had made in our own findings docs are now wrong. Each was disproved by a control we
had never run. They are recorded here as results, not as damage.

| Prior claim | Where it lived | Status | What the control showed |
|---|---|---|---|
| "+0.52 is a hard, intrinsic ceiling" | `2026-07-14_emulator_loop.md` | **REFUTED** | An 8-seed deep ensemble lifts skill (+0.14 daily eqpac, +0.05 monthly 3-D). The plateau was epistemic, not aleatoric. |
| "the daily emulator beats persistence, verdict MAKE (+0.408)" | `2026-07-13_daily_surface_emulator.md` | **LARGELY A LINEAR-METRIC ARTIFACT** | Same config, only the transform differs: +0.3000 linear → **+0.0361 log**. Global daily log: **+0.005** (a null). |
| "the rollout is dead by 6 months" | scratch, 2026-07-17 | **SUBSTANTIALLY CONFIRMED** | The counter-claim (k8 reaches ~9 months) was itself a calendar artifact and is **retracted**. Against a correctly-binned climatology, k8 wins at **one step only** (+0.240) and is at/below climatology from step 2. |

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

### Root cause, located and fixed

`LLC270Config.delta_t` in `src/darwindiff/llc270_loader.py` was **900**. It is **1200**. The docstring
asserted the wrong value was right, and `tests/test_llc270_loader.py` asserted `delta_t == 900` — so a
wrong constant was documented as correct and locked in by a passing test. Fixed, with a regression
test on the invariant that actually pins it down: `72 * delta_t == 86400` (daily output steps by 72
iterations, which must be exactly one day).

Independently confirmed by two different routes: arithmetically
(`times_days * 86400 / iters` = exactly 900.0), and physically (an FFT of subpolar-North-Atlantic
chlorophyll found the spring bloom recurring every **9.25 stored-months**; 12/9.25 = 1.30 ≈ 4/3 =
1200/900, and a v05 chlorophyll climatology on the bad axis showed **no annual cycle at all**).

### Net effect on the headline claim — MEASURED (job 167823)

The two defects act on **different axes** and do not cancel:

| defect | axis | direction |
|---|---|---|
| corrupted climatology bins (93.7% differ between calendars) | **skill magnitude** | baseline too weak ⇒ **skill overstated** |
| horizons are steps, ~60 d each | **duration** | ⇒ **elapsed time understated ~2×** |

`scripts/calendar_ab.py` measured the first exactly: same checkpoints, same trajectories, scored
against both climatologies. **Inflation ranges +0.374 to +0.777** (k8) and up to **+12.5** (k1).
The corrected numbers are in *Rollout horizon* below. **The "~9-month useful horizon" is retracted.**

### A second-order consequence: two prior negatives are now confounded

The **seasonal sin/cos time-encoding** experiment (rejected at −0.073) computed day-of-year from the
0.75× axis, so it encoded a phase the field was not in — it was told the wrong season for ~94% of
samples. **That negative is confounded and is probably a false negative; it should be re-run.** Any
other experiment whose inputs were derived from wall-clock time is similarly suspect. The
forcing-concat negative (−0.010) is *not* affected if the forcing was matched by iteration rather
than by date — verify before relying on it.

### And a downstream data-era correction

"v05 daily ends 2012-03-31" was itself an artifact of this bug. Corrected, v05 daily spans
**1992-01-03 → 2018-12-31** — a clean year boundary. This nearly doubles the MODIS-Aqua overlap
(9.2 → 16 years). The "use MODIS, not PACE" conclusion still holds (PACE launched 2024).

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
2. ~~**Genuine good news:** the carbonate system is chemically valid ... the emulator learned valid
   seawater without being told chemistry exists.~~
   **RETRACTED 2026-07-19 — this reads the number backwards.** The Revelle factor is ~10, so a 0.1%
   error in DIC propagates to ~1% in pCO₂ (~4 µatm). Agreement to **0.51 µatm** therefore implies a
   DIC error of roughly **0.05% over one step** — which is not evidence of learned chemistry, it is
   evidence that **DIC and ALK are very nearly persistent at monthly cadence**. The emulator is
   reproducing a field that barely moved. The honest reading: the carbonate check **passes but is
   uninformative**, because it cannot distinguish "learned the chemistry" from "copied the input."
   The corollary is a prediction to test: the same low tendency-to-variance ratio that makes DIC/ALK
   look excellent against climatology should make them score **poorly against persistence** — and
   indeed the 3-D per-tracer split shows DIC 0.376 / ALK 0.305, the two *lowest* of the six tracers.
   A physics check needs a baseline column too, exactly as the positivity check has v05 as a control.
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

> **Note on the −0.265.** That specific value is a *buggy-calendar* climatology number — computed
> before the `delta_t` fix, when 94% of month-of-year bins were mis-assigned. The qualitative point
> (persistence flatters; climatology is the honest baseline) is what survives and is confirmed by
> the corrected tables; the **magnitude** should not be quoted. The corrected k1 numbers are the
> ones to use.

### Matched k1-vs-k8, CORRECTED CALENDAR (job 167823, `cal_ab.json`)

LOG space, **n_starts = 15**, **n_members = 6**, skill vs **CLIMATOLOGY**, one cube load, the *same*
trajectories scored against both calendars. Horizons are **steps**; elapsed months are given.

**k8 — the artifact:**

| steps | ~months | OLD (buggy bins) | **NEW (correct bins)** | inflation | mass |
|---|---|---|---|---|---|
| 1 | 2.0 | +0.614 | **+0.240** | +0.374 | 1.000 |
| 2 | 3.9 | +0.469 | **−0.018** | +0.488 | 1.000 |
| 3 | 5.9 | +0.432 | **−0.012** | +0.444 | 1.000 |
| 6 | 11.8 | +0.259 | **−0.420** | +0.680 | 1.000 |
| 9 | 17.7 | +0.253 | **−0.292** | +0.545 | 1.000 |
| 12 | 23.7 | +0.028 | **−0.748** | +0.777 | 1.000 |

**k1 — the single-step control:**

| steps | ~months | OLD | **NEW** | inflation | mass |
|---|---|---|---|---|---|
| 1 | 2.0 | +0.546 | **+0.108** | +0.439 | 1.000 |
| 2 | 3.9 | +0.129 | **−0.672** | +0.801 | 1.000 |
| 3 | 5.9 | −0.373 | **−1.444** | +1.071 | 1.000 |
| 6 | 11.8 | −1.911 | **−4.582** | +2.671 | 1.049 |
| 9 | 17.7 | −5.097 | **−9.542** | +4.444 | **99.58** |
| 12 | 23.7 | −14.598 | **−27.065** | +12.467 | **305,368,586** |

**What this changes.** Against a correctly-binned seasonal climatology the emulator beats the
baseline at **one step only** (~2 months, +0.240). By two steps it is at zero (−0.018) and it is
negative thereafter. **The "~9-month useful horizon" is retracted.** The inflation was large because
a true seasonal climatology is a *much* stronger baseline in ocean BGC than the near-time-mean that
scrambled bins produce — the seasonal cycle carries most of the variance.

**What survives, and it is not nothing.**
1. **Rollout-aware training remains the #1 lever**, and the corrected numbers make the case *more*
   starkly, not less: k8 holds mass ratio 1.000 at every horizon while k1 diverges to
   **3.05 × 10⁸**. That is the difference between a stable-but-unremarkable model and a catastrophic
   one. The lever is real; what it buys is *stability*, not the horizon we claimed.
2. **Physics holds:** `neg_frac = 0.000` at every horizon in both arms.
3. Everything calendar-free is untouched: skill-vs-persistence, the log-space controls, the deep
   ensemble gains, capacity saturation.

**A caution on persistence.** In the corrected run, skill-vs-persistence for k8 is non-monotone
(+0.583, +0.682, +0.685, +0.201, +0.595, +0.191). A baseline that wanders like that cannot support a
horizon claim in either direction — which is precisely why climatology must be co-reported.

## Levers: load-bearing vs not

| lever | effect | verdict |
|---|---|---|
| **Rollout-aware training (k8)** | stability: mass ratio 1.000 vs k1 diverging to 3.05e8. **NOT** a horizon extension — the ~9 mo figure is retracted (1 step, +0.240) | **LOAD-BEARING (stability only)** |
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
climatology floor at **step 2** (−0.018, ~4 months elapsed on the corrected calendar). Speed was
never the bottleneck; rollout fidelity is.

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
- **The ~9-month figure is RETRACTED, not imprecise.** It was a calendar artifact (`delta_t` 900 s
  vs the true 1200 s), and against a correctly-binned climatology the corrected table is deeply
  negative from step 2. It is not a bound awaiting a longer split. Separately, the long-horizon
  numbers do also rest on limited independent starts (n_starts=15 on a 47-month val split gives
  overlapping trajectories), but that is a second-order caveat on a retracted number.
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

## The data deficit is self-inflicted — and it is the highest-value fix available

> **⚠️ SUPERSEDED the same day.** The data-volume diagnosis below was **tested and refuted**: the
> learning curve is **flat from n=55** (+0.4700 → +0.4701 → +0.4657), so the project is **not
> data-bound** and rebuilding the cube for volume would not have helped. The actual lever is **Δt
> uniformity** (+0.4730). Retained because the archive sizing is still correct and useful, and
> because it records a plausible single-cause diagnosis that four independent negative results were
> wrongly attributed to.

The binding constraint on everything (capacity saturates, two "add information" attempts hurt,
calibration stuck at 0.24, diffusion adds nothing) was believed to be **~110 training pairs**. That
constraint is **not** a property of the archive. Measured against the NASA v05 monthly listing on
2026-07-19:

| tracer set | timesteps | % truly 1 month apart |
|---|---|---|
| **all 6 (the current cube)** | **158** | **48.4%** (median 59 d) |
| drop any single tracer | 170–183 | marginal |
| carbon-only (DIC, ALK, PIC, POC) | 187 | — |
| bio-only (FeT, Chl1) | **262** | — |
| **union of all 6** | **323** | **100.0%** (median 31 d) |

Per-tracer availability is DIC 279, ALK 284, PIC 280, POC 287, FeT 291, Chl1 289. The cube takes the
**intersection**, and the intersection collapses to 158 because **the tracers were written on
different output schedules** (e.g. FeT and Chl1 have iteration 6552; DIC does not — DIC has 8712).

Two consequences:

1. **The low-data constraint and the non-uniform-Δt defect have the same root cause and the same
   fix.** Requiring all six tracers at every timestep is what produced both the 158-step count *and*
   the 1-to-7-month gap structure. Relax it and both improve together: the union is 323 steps at
   **perfectly uniform monthly spacing**.
2. **A tracer-subset model roughly doubles the data today, with no new download.** Bio-only
   (FeT, Chl1) gives **262 steps (+66%)**; carbon-only gives 187. A per-channel-availability design
   (masked loss over the union) gives 323.

This should be tested before any further architecture work, and it is cheap. It also supplies the
one experiment that would actually settle whether we are data-bound: a **learning curve** — train at
25/50/75/100% of available pairs and plot skill vs N. If the curve is still rising at 100%, more data
is the lever and this fix is decisive; if it is flat, the ceiling is architectural or aleatoric and
no amount of cube rebuilding helps. **That experiment has since been RUN** (array 168270): the curve
is **flat from n=55**, so more data is *not* the lever and no cube rebuild is warranted for volume.
The sentence that once read "nothing we have run so far tests it" no longer holds.

## Conclusion

The arc cost us four claims and bought one modest artifact. The emulator worth keeping is the
**k8-log diverse ensemble** (`opt3d_seed*.pt`): it beats a true seasonal climatology at **one step
(~2 months)**, emits **0% negative concentrations**, keeps valid carbonate chemistry, and conserves
mass (1.000) where the single-step control diverges by eight orders of magnitude. **Its skill is not
real at true monthly cadence:** on genuinely-1-month pairs it scores **+0.0026** versus **+0.4756**
for a uniform-Δt-trained model — the validation set's median gap is 61 days, so every "single-step"
number here describes a ~2-month operator. Its daily-cadence skill is largely a linear-metric
artifact. It is badly calibrated and validated against nothing but the model it imitates.

That is a much smaller claim than the one we started the day with. It is also the first one that has
survived every control we know how to run.

The controls that produced every correction above — a seed ensemble, a transform swap, a climatology
baseline, a physics check with a truth control column — were each cheap and each overturned something
we believed. **The pattern is the finding: our errors were not in the models, they were in the
missing controls.**
