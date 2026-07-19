---
license: mit
tags:
  - climate
  - oceanography
  - neural-operator
  - fno
  - emulator
  - biogeochemistry
  - ecco-darwin
library_name: pytorch
---

# DarwinDiff `opt3d` — depth-resolved global ocean-biogeochemistry emulator (FNO, log-space, rollout-trained, 6-member ensemble)

**Release `v0.1.0`** · 2026-07-19 · ECCO-Darwin v05 surrogate

> **Why `0.1.0` and not `1.0.0`.** This is a real, working, reproducible artifact — but it is not a
> stable product. Its useful horizon is one step; it has never been compared against an
> observation; its uncertainty is uncalibrated; and its training series has non-uniform spacing.
> The version number reflects that honestly rather than implying a validation that has not happened.
> A `1.0.0` is reserved for a model that has been checked against the real ocean.

A neural-operator surrogate of **ECCO-Darwin v05** biogeochemistry. Given the 3-D biogeochemical
state of the global ocean, it predicts the **next state one output-step ahead** (~2 months of model
time) for six tracers over the upper ten model levels.

> ## Read this first
>
> **1. This is a surrogate of a model, not a model of the ocean.** Every number below is
> self-consistency against ECCO-Darwin v05 output. This emulator has **never** been validated against
> real observations — not satellite chlorophyll, not GLODAP, not SOCAT, not BGC-Argo. It reproduces a
> simulation.
>
> **2. Its useful horizon is ONE step.** Against a correctly-binned seasonal climatology it scores
> **+0.240 at one step** and is **at or below climatology from two steps onward**. An earlier version
> of this card claimed a ~9-month horizon. That claim was **retracted on 2026-07-19** after a
> calendar bug was found in our own evaluation (see *Known defects*). Do not use this for multi-month
> forecasting.
>
> **3. Its uncertainty is not calibrated.** Ensemble spread/RMSE is **0.240** against an ideal of
> ~1.0. The ensemble is badly over-confident. Do not treat the spread as a credible interval.

## What the artifact is

| | |
|---|---|
| Files | `opt3d_seed0.pt` … `opt3d_seed5.pt` (6 members) |
| Architecture | FNO2d, residual formulation `x(t+1) = x(t) + f(x(t))` |
| Ensemble diversity | architectural — modes {20, 24, 28} × width {48, 64, 80} |
| Training | **log-space** targets, **rollout-aware** with `k = 8` |
| Parameters | ~18.9 M per member |
| Inference | **7.45 ms** per global step, peak **2.29 GB** (laptop-runnable) |

Use the **ensemble mean**. A single member is meaningfully worse (+0.459 → +0.497 single-step log
skill) and, more importantly, ensembling is what keeps the autoregressive rollout stable.

## Data

- **Source:** ECCO-Darwin v05 (NASA/JPL), native LLC270 (~1/3°), monthly output.
- **Grid:** bin-averaged to regular 0.25° lat-lon, **680 × 1440**.
- **Tracers (6):** `DIC`, `ALK`, `PIC`, `POC`, `FeT`, `Chl1` — each at 10 depth levels
  (`k0`…`k9`, upper ~150 m) ⇒ **60 channels**.
- **Timesteps:** **158**. Split chronologically: **110 train / 46 validation**.
- **Preprocessing:** clip at `1e-4`, natural log, then per-channel z-score using training statistics
  only.

**Log-space is not optional.** Global chlorophyll spans p99/p1 = **2.8 × 10⁶** with skewness +4.86
linear versus −2.31 log. A linear-space MSE score on this field is dominated by a handful of bloom
cells. Log-space training additionally guarantees positivity by construction (`exp(·) > 0`).

## Results

All skill = `1 − MSE_model / MSE_baseline`, **log space**, 6-member ensemble mean, `n_starts = 15`.

### Single step

| Metric | Value |
|---|---|
| Skill vs persistence, single member | +0.459 |
| Skill vs persistence, ensemble | **+0.497** |
| Skill vs **seasonal climatology**, ensemble | **+0.240** |

> **⚠️ These are for a ~2-month operator, not a monthly one. Added 2026-07-19.**
>
> The validation set has a **median gap of 61 days**, because the training series is not uniformly
> monthly (see *Known defects* #2). So "one step" means *the average transition in this cube*, which
> is about two months — not one.
>
> This matters more than a labelling quibble. Evaluated on the subset of validation pairs that are
> **genuinely ~1 month apart** (n=21, gaps 30–31 d), this model scores **+0.0026** — i.e. **no skill
> over persistence at true monthly cadence**. A model trained on the *same number* of pairs, all of
> them true one-month, scores **+0.4756** on that identical subset.
>
> The model has learned the *average* Δt of its training data and **overshoots on a one-month step**.
> If your application needs a monthly operator, this checkpoint is not it — retrain on uniform-Δt
> pairs, or weight the loss by 1/Δt.
>
> Caveats on that measurement: n=21, and the uniform subset spans March–November only (no winter).
> The sign and magnitude are unambiguous; the precise value is not.

### Rollout (horizons are **steps**; one step ≈ 60 days)

| Steps | ≈ Months | vs climatology | Negative fraction | Mass ratio |
|---|---|---|---|---|
| 1 | 2.0 | **+0.240** | 0.000 | 1.000 |
| 2 | 3.9 | −0.018 | 0.000 | 1.000 |
| 3 | 5.9 | −0.012 | 0.000 | 1.000 |
| 6 | 11.8 | −0.420 | 0.000 | 1.000 |
| 9 | 17.7 | −0.292 | 0.000 | 1.000 |
| 12 | 23.7 | −0.748 | 0.000 | 1.000 |

**Useful horizon: one step.** The model remains numerically *stable* far beyond that — mass ratio
1.000 at every horizon, zero negative concentrations — it simply stops being better than the seasonal
mean.

### Physics validation (no reference data required)

Run against v05 as a **control column**, so violations the emulator merely *inherits* are not charged
to it.

| Check | v05 (control) | This model |
|---|---|---|
| Negative fraction, all 6 tracers | see below | **0.0000** |
| ALK:DIC in physical band | 100% | 100% |
| Carbonate system solvable | 100% | 100% |

The **linear-space** predecessor of this model invented **4.5% negative iron** where v05 emits
1.9 × 10⁻⁷ — while scoring +0.43. Skill is blind to physics. Log-space training removes this by
construction, which is the single strongest reason to use this checkpoint over an earlier one.

### Calibration

| | spread/RMSE |
|---|---|
| This model | **0.240** |
| Ideal | ~1.0 |

Unresolved. Architectural diversity did not fix it; only a diffusion corrector reached 0.375, and
that variant adds **zero** skill.

## Known defects — read before using

1. **The cube's stored time axis is wrong.** `times_days` was written with a 900 s timestep; v05
   runs at **1200 s**, so stored times are **0.75×** truth. Derive time from the raw `iters` instead
   (`iters × 1200 / 86400` days). Fixed at the root in the loader as of 2026-07-19, but **cubes built
   before that date are not retroactively corrected**.
2. **The training series is not uniformly monthly.** Only **48.4%** of consecutive pairs are truly one
   month apart; 51.6% span 2–7 months (max 212 days) and were trained as single steps. **The learned
   operator is therefore a blend of 1-to-7-month transitions, not a clean monthly operator.** This is
   a defect in the training data that re-scoring cannot repair. It arises because the cube takes the
   *intersection* of six tracers written on different output schedules — the union would be 323 steps
   at 100% uniform monthly spacing.
3. **Horizon labels are step counts**, not months.
4. **No observational validation whatsoever.**
5. **Inherits v05's biases**, which are known to be largest at high latitudes, the sea-ice margin, and
   coastal upwelling. v05 itself emits non-physical negative chlorophyll in places (4.3% of subpolar
   North Atlantic cell-months).

## Usage

```python
import torch, glob, numpy as np

members = []
for p in sorted(glob.glob("opt3d_seed*.pt")):
    ck = torch.load(p, map_location="cpu", weights_only=False)
    members.append(ck)                      # ck["regression"] = state dict
ck = members[0]
ck["channels"]          # ['DIC_k0', ..., 'Chl1_k9']  (60)
ck["mean"], ck["std"]   # per-channel z-score stats, computed in LOG space

# inputs must be log-transformed and z-scored the same way:
#   z = (log(clip(x, 1e-4)) - mean) / std
# outputs invert as:  x = exp(z * std + mean)
# ALWAYS average the 6 members before inverting.
```

Model classes are in `scripts/diffusion_emulator.py` (`FNO2d`). Evaluate with
`scripts/rollout_verify.py --calendar iters` (co-reports persistence **and** climatology) and
`scripts/physics_verify.py` (physics checks with a truth control column).

## Intended use

Research into emulator behaviour, evaluation protocol, and physics-consistency for ocean
biogeochemistry. Suitable as a one-step surrogate, a stability testbed, or a baseline for a
benchmark.

**Not suitable for:** multi-month or multi-decadal forecasting; marine-CDR or carbon-credit MRV;
any application requiring calibrated uncertainty; any claim about the real ocean.

## Attribution

Emulates **ECCO-Darwin v05** output (NASA/JPL — Carroll et al. 2020 *JAMES*, 2022 *GBC*). Trained on
the Massachusetts AI Compute Resource (AICR) B200 cluster. FNO after Li et al. 2021.

---

*Card revised 2026-07-19. It supersedes an earlier draft that described a daily global chlorophyll
model, quoted a ~9-month horizon, and asserted an intrinsic skill ceiling — all three of which have
since been measured to be wrong.*

---

## Release record

**Published `v0.1.0` on 2026-07-19** to `2imi9/darwindiff-emulator` (Hugging Face, **private**).

| | |
|---|---|
| Repo SHA | `2c0f3ff795` |
| Tag | `v0.1.0` (commit `ec38546f6c`) |
| Contents | 6 checkpoints (947 MB) + this card + `release_results.json` + 4 verification scripts |

Uploaded directly from the AICR cluster (19.3 MB/s); the local path was unusable at 12 KB/s.

The four verification scripts ship alongside the weights deliberately: `rollout_verify.py`,
`physics_verify.py`, `deep_ensemble_eval.py`, and `calendar_ab.py` reproduce every number in this
card, including the calendar A/B that produced the horizon retraction.
