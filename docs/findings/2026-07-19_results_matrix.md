# Track-2 emulator — canonical results matrix (2026-07-19)

One table per axis. **Every number carries its metric space, its baseline, and the raw file it came
from.** If a number is not traceable to a file in the provenance column, it does not belong here.

Rule of the matrix: *a skill value without a stated metric space and baseline is not a result.*

---

## 0. Standing caveats that apply to EVERY row

| # | Caveat |
|---|---|
| C1 | **Self-consistency only.** Every number is against ECCO-Darwin v05 model output. Nothing here has been validated against real observations. |
| C2 | **Metric space.** Linear-space skill on log-normal chlorophyll (p99/p1 = 2.8e6) is dominated by bloom cells. Never compare a linear number to a log number. |
| C3 | **Baseline.** Persistence flatters long horizons; climatology is the honest long-lead bar. Co-report both. |
| C4 | **Calendar bug (2026-07-19).** `times_days` was built at 900 s vs v05's true 1200 s ⇒ 94.9% of month-of-year bins are wrong ⇒ every **skill-vs-climatology** number below is measured against a **too-weak** baseline and is **overstated** pending re-evaluation. Skill-vs-persistence, log controls, physics checks and ensemble comparisons are calendar-free and unaffected. |
| C5 | **Horizons are STEP counts, not months.** Median val-split step = 61 days ≈ 2.0 months. Reported "9 mo" ≈ **18 months** elapsed. |
| C6 | **The operator is not a one-month operator.** Only 48.4% of consecutive training pairs are truly 1 month apart; 51.6% span 2–7 months and were trained as single steps. |

---

## 1. Metric-space controls — identical config, only the transform differs

| run | linear | log | Δ | verdict | provenance |
|---|---|---|---|---|---|
| monthly 3-D flagship | +0.432 | **+0.36492** | −15% | **SURVIVES** | `d3_ctl_log.json` (seed 0, `rollout_train_k: None`) |
| daily eqpac | **+0.29997** | **+0.03614** | −88% | **COLLAPSES** | `eqpac_ctl_linear.json` / `eqpac_ctl_log.json` |
| global daily 1° | — | +0.005 | — | **NULL** | prior run |

Matched-ness verified: same seed, same cube, same `rollout_train_k`; only `log_transform` differs.

---

## 2. Skill levers — what moves the number

| lever | before | after | Δ | space | baseline | verdict | provenance |
|---|---|---|---|---|---|---|---|
| **Deep ensemble, 8 seeds** (daily eqpac) | +0.30387 | **+0.44540** | **+0.1415** | linear | persistence | **LOAD-BEARING** | `de_eqpac_ensemble.json` |
| **Deep ensemble, 8 seeds** (monthly 3-D) | +0.43218 | **+0.48371** | **+0.0515** | linear | persistence | **LOAD-BEARING** | `de3d_ensemble.json` |
| EDM diffusion (surface) | +0.414 | +0.394 | −0.020 | linear | persistence | **no skill gain** | `diff_surf.json` |
| EDM diffusion (3-D) | +0.421 | +0.395 | **−0.026** | linear | persistence | **HURTS** | `diff_3d.json` |
| Capacity (modes/width, ~4× params) | +0.520 | +0.527 | +0.007 | linear | persistence | **SATURATED** | capacity ladder |
| Forcing channels (SST/wind/MLD, concat) | +0.5204 | +0.5108 | **−0.010** | linear | persistence | **REJECTED — hurts** | overnight loop |
| Seasonal sin/cos encoding | +0.285 | +0.212 | **−0.073** | linear | persistence | **REJECTED — hurts** | overnight loop |

Parity check: `persistence_mse` = 0.031955240800493966 identical between the diffusion and deep-ensemble
daily runs ⇒ same cube and split, so the ensemble-vs-diffusion comparison is fair.

**Reading:** ensembling is the only mechanism that reliably adds skill. Diffusion buys calibration,
not skill, at 256× the forward passes (2,048/field vs 8).

---

## 3. Horizon — matched k1 vs k8, LOG space, n_starts=15, n_members=6, vs CLIMATOLOGY

⚠ Subject to C4 (climatology too weak ⇒ overstated) and C5 (steps, not months).

| horizon (steps) | ≈ elapsed | k1 single-step | k8 rollout-trained | provenance |
|---|---|---|---|---|
| 1 | ~2 mo | +0.5465 | **+0.6139** | `matched_k1/k8.json` |
| 2 | ~4 mo | +0.1286 | **+0.4694** | " |
| 3 | ~6 mo | **−0.3725** (dead) | **+0.4318** | " |
| 6 | ~12 mo | **−1.9110** | **+0.2594** | " |
| 9 | ~18 mo | −5.0974, **mass 99.58** (diverging) | **+0.2527**, mass 1.0002 | " |
| 12 | ~24 mo | −14.5976, **mass 30,536** (diverged) | +0.0283 (floor), mass 1.0002 | " |

**Rollout-aware training is the #1 horizon lever.** k1 does not merely degrade — it **diverges**.
`neg_frac = 0.000` at every horizon in both arms.

### Calendar A/B — RESULT (job 167823, `cal_ab.json`)

Same checkpoints, same trajectories, scored against both climatologies in one process.

| steps | ~mo | k8 OLD | **k8 NEW** | infl. | k1 OLD | **k1 NEW** | infl. |
|---|---|---|---|---|---|---|---|
| 1 | 2.0 | +0.614 | **+0.240** | +0.374 | +0.546 | **+0.108** | +0.439 |
| 2 | 3.9 | +0.469 | **−0.018** | +0.488 | +0.129 | **−0.672** | +0.801 |
| 3 | 5.9 | +0.432 | **−0.012** | +0.444 | −0.373 | **−1.444** | +1.071 |
| 6 | 11.8 | +0.259 | **−0.420** | +0.680 | −1.911 | **−4.582** | +2.671 |
| 9 | 17.7 | +0.253 | **−0.292** | +0.545 | −5.097 | **−9.542** | +4.444 |
| 12 | 23.7 | +0.028 | **−0.748** | +0.777 | −14.598 | **−27.065** | +12.467 |

**⇒ THE "~9-MONTH HORIZON" IS RETRACTED.** Corrected, k8 beats a true seasonal climatology at
**1 step (~2 months)** only. Inflation +0.374 to +0.777 (k8), up to +12.5 (k1). 93.7% of month bins
differ between calendars.

**Survives:** rollout-aware training as the #1 lever — k8 mass ratio **1.000** at every horizon vs
k1 diverging to **3.05 × 10⁸**. And `neg_frac = 0.000` throughout both arms.

**Also note:** corrected k8 skill-vs-persistence is non-monotone (+0.583, +0.682, +0.685, +0.201,
+0.595, +0.191) — a baseline that wanders like that cannot support a horizon claim in either
direction, which is exactly why climatology must be co-reported.

---

## 4. Physics — the third validator (needs no reference data)

v05 runs as a **control column**, so inherited violations are not charged to the emulator.
Provenance: `physics_3d.json`.

| check | v05 (control) | emulator | verdict |
|---|---|---|---|
| positivity FeT | **1.89e-07** (numerically zero) | **0.04511** | **FAIL — invented** |
| positivity Chl1 | 0.04460 | 0.25154 | worse (partly inherited) |
| positivity POC | 0.00595 | 0.08054 | worse |
| positivity PIC | 0.12518 | 0.17746 | mostly inherited |
| positivity DIC/ALK | 0.0 | 0.0 | clean |
| ALK:DIC band | 100%, med 1.10816 | 100%, med 1.10800 | **PASS** |
| carbonate closure | 100%, pCO₂ 380.335 µatm | 100%, pCO₂ 380.844 µatm | **PASS** (0.51 apart) |
| CaCO₃ stoichiometry | corr 0.018 | corr 0.006 | **TEST INVALID** — v05 shows no signal either; transport dominates ΔALK at monthly/0.25° |

**Key result:** the model scores +0.43 (linear) while inventing 4.5% negative iron. *Skill is blind to
physics.* Log-space training drives negatives to 0.0000 by construction.

---

## 5. Calibration — the axis nothing has moved

| setup | spread/RMSE | provenance |
|---|---|---|
| ideal | ~1.0 | — |
| deep ensemble, daily eqpac | 0.2852 | `de_eqpac_ensemble.json` |
| deep ensemble, monthly 3-D | 0.2309 | `de3d_ensemble.json` |
| architecturally diverse ensemble | 0.240 | `opt_physics.json` |
| EDM diffusion | **0.375** | `diff_daily_eqpac.json` |

Diffusion is the only thing that improves calibration, and it adds no skill. Untested candidate:
deep-ensemble mean (skill) + diffusion spread (calibration).

---

## 6. Cost

| quantity | value | provenance |
|---|---|---|
| one next-month global state (680×1440, 60 ch, 18.91 M params) | **7.45 ms** | `bench.json` |
| inference peak memory | **2.29 GB** (laptop-runnable) | " |
| one simulated century | ~9 s | " |

**Irrelevant.** A century in 9 s is worthless when the trajectory reaches the climatology floor.
Speed was never the bottleneck; rollout fidelity is.

---

## 7. Physical-state conditioning — IN FLIGHT

Motivated by §4: at monthly cadence and 0.25° the tendency is **transport-dominated**, and the
emulator currently receives **no** physical state at all — it must infer circulation from tracer
patterns alone.

Data acquired 2026-07-19 (job 167805, `cpu` partition): monthly v05 physical fields aligned to the
158 cube iterations — `mldDepth`, `SST`, `SIarea`, `SSSanom`, `wspeed`, `oceanQsw` (2-D, complete),
and `PAR` (3-D, k0..k9 — the direct light driver).

| arm | mechanism | rationale | status |
|---|---|---|---|
| A0 `none` | baseline | control | pending |
| A1 `concat` | physical channels appended to FNO input | replicates the known −0.010 negative; mandatory control | pending |
| A2 `film` | spatial FiLM, **zero-init** | starts identical to baseline ⇒ conditioning used only if it helps; targets the overfitting failure mode | pending |
| A3 `xattn` | cross-attention on a coarse token grid, **zero-init** | the mechanism under question | pending |

Matched across arms: same cube, split, seeds, optimizer steps, log space, `rollout_train_k 8`.

**Pre-registered decision rule.** Seed variance on a comparable setup is ±0.0023, so a gain below
~0.005 is indistinguishable from noise. Adopt conditioning only if an arm beats **both** A0 and A1
by a margin exceeding seed variance. If A1 (naive concat) matches A2/A3, the gain is *information*,
not *mechanism*, and cross-attention is not indicated.

**Pre-registered failure mode.** The most likely way this produces a misleading positive is
**temporal leakage** — conditioning on physical state at t+1 rather than t. A suspiciously large gain
should be treated as a leak until proven otherwise.

**Claim change if it works:** conditioning on prescribed physics at every rollout step makes this an
**offline/forced** BGC emulator, not a free-running one. That is the standard offline-BGC setup and
is arguably more useful — but it is a different product and must be stated as such.

---

## 8. External validation (#163) — IN FLIGHT

The one axis that would move this from "surrogate of a model" to "tested against the ocean."

- **Instrument:** MODIS-Aqua `chlor_a` via NOAA CoastWatch ERDDAP `erdMH1chlamday` (no auth needed).
  **Not PACE** — v05 daily ends 2012-03-31, PACE launched 2024, zero overlap.
- **Window:** 2003-01 → 2012-03 (111 months), the full MODIS ∩ v05-daily overlap.
- **Verified:** `surfChl4` contributes **−0.002%** of total Chl, so the cubes' 4 channels are total
  chlorophyll. Units match exactly (`mg m-3`), no conversion.
- **Measured confounds:** linear mean is **86.5%** above geometric mean ⇒ log10 throughout; January
  satellite coverage at 60–90°N is **0.000** ⇒ v05 must be masked to satellite-valid pixels per month
  before any aggregate.
- **Noise floor:** MODIS retrieval ±35% = **0.130 dex**. A bias inside that band is not a detected
  discrepancy.
