# Why the rollout ceiling is structural — it is decorrelation, not variance collapse

The 1-step ceiling survives a corrected monthly operator
([`2026-07-19_eqpac...`](2026-07-19_eqpac_chlorophyll_vs_modis.md) is unrelated; see
`track2_runs/rollout_*.json`). "Structural" was a bare fact. This narrows it to a mechanism, and
**rules out the obvious explanation.**

## The hypothesis that was tested — and refuted

The emulator's input is the **60 BGC state channels only**: no time-of-year, no forcing, no
calendar (`load_cube`, `diffusion_emulator.py`). The operator is time-invariant. Climatology, by
construction, is pure seasonality. So the natural hypothesis was:

> The rollout cannot hold the seasonal cycle without a phase reference, damps toward a flat mean
> state, and climatology wins by default.

**That is wrong.** Job 169498, 15 starts, ensembles of 3, both arms:

| std(model)/std(truth) | k=1 | 2 | 3 | 4 | 6 | 9 | 12 |
|---|---|---|---|---|---|---|---|
| flagship | 0.965 | 0.950 | 0.951 | 0.955 | 0.952 | 0.962 | **0.974** |
| Δt-scaled | 0.991 | 0.998 | 0.990 | 0.974 | 0.989 | 0.987 | **0.997** |

**There is no variance collapse.** Both arms retain 95–99% of true spatial variability at every
horizon out to 12 steps. The classic autoregressive failure — smoothing toward the mean — is not
what is happening here.

## What is actually happening: full amplitude, lost correlation

Ocean-mean surface chlorophyll, correlation with truth across starts:

| | k=1 | 2 | 3 | 4 | 6 | 9 | 12 |
|---|---|---|---|---|---|---|---|
| flagship | +0.788 | +0.661 | +0.762 | +0.813 | +0.424 | +0.594 | **+0.208** |
| Δt-scaled | +0.918 | +0.717 | +0.423 | +0.305 | +0.212 | +0.221 | **−0.191** |

The trajectory stays physically plausible the whole way — amplitude preserved, mass ratio 1.000,
**0% negative concentrations** — and becomes progressively uncorrelated with the truth it started
from. **The failure mode is trajectory divergence at preserved amplitude, not damping.**

This is what the earlier note meant by "stable but WRONG — a plausible-but-incorrect attractor",
now quantified and separated from the damping alternative.

## Why this matters more than the bare ceiling

1. **It explains why fixing the single-step operator bought nothing.** The Δt-scaled model has far
   better single-step skill at true monthly cadence (+0.4801 vs +0.0026) and *decorrelates faster*
   (it is at −0.191 by k=12 where the flagship is still +0.208). Better one-step accuracy delays
   nothing if the mechanism is divergence — and a larger per-step correction (output × Δt≈2) makes
   it worse.
2. **It reframes the limit as predictability, not capacity.** A system that stays on a plausible
   attractor while decorrelating from truth is behaving the way a chaotic system does. If that is
   the right reading, no amount of capacity, data, or single-step accuracy extends the deterministic
   horizon — which is consistent with every lever we have measured returning ~0.
3. **It changes what would help — and the follow-up test (below) sharpens this further.**

## Follow-up: it is NOT chaos either — it is systematic bias (job 169528)

The decorrelation was *consistent* with chaos, so I ran the perturbation-growth test that separates
the two. Roll the flagship ensemble from a true start, and from the same start plus a small
perturbation (ε = 0.01 and 0.05 of a channel std, z-space, ocean cells only). Compare how fast the
operator **amplifies the perturbation** against how fast the rollout **leaves the truth**.

| z-RMS | step 1 | step 6 | step 12 | growth rate |
|---|---|---|---|---|
| error vs truth | 0.298 (0.55·sat) | 0.384 | 0.466 (0.87·sat) | +0.0007/day (doubling ~984 d) |
| perturbation ε=0.01 | 0.010 | 0.010 | **0.010** | ≈ 0 |
| perturbation ε=0.05 | 0.049 | 0.048 | **0.048** | ≈ 0 |

(saturation = distance between two unrelated states = 0.538 z-RMS.)

**The operator does not amplify perturbations at all.** A 1% perturbation stays 1% out to 12 steps;
5% stays 5%. The growth rate is ≈ 0 (slightly *contractive*), so the spectral radius of the map's
Jacobian is ≈ 1 — exactly what a residual operator `F = I + small correction` should give, which is
why this is a real property and not an artifact. There is **no positive Lyapunov exponent, so this is
not chaos.**

Yet the error is **0.55·saturation at step 1** and only creeps to 0.87 by step 12 — a plateau, not
exponential growth. And the single-step error (0.298) is **30× the 0.01 perturbation**: it cannot be
amplified initial-condition uncertainty, because that uncertainty does not amplify. It is a
**systematic offset in F itself**, present from the first step.

### The complete mechanism

Three hypotheses, two refuted by data:

| hypothesis | prediction | result |
|---|---|---|
| variance collapse | amplitude → 0 | **refuted** — amplitude 0.95–0.99 held |
| chaos / predictability limit | perturbations amplify to saturation | **refuted** — perturbations stay flat |
| **systematic single-step bias** | large step-1 error, contractive, plateaus | **confirmed** |

The emulator's learned map has a large systematic one-step error. Because the map is contractive it
does not explode; the bias accumulates to a plateau on a wrong-but-plausible attractor (full
amplitude, mass 1.000, 0% negatives, decorrelated). This is why the dt-scaled model rolls out
*worse*: multiplying the per-step correction by Δt≈2 doubles the systematic drift. Error scaling with
correction size is the fingerprint of systematic — not random, not chaotic — error.

### Final piece: the bias is STATE-DEPENDENT, and therefore irreducible here (job 169630)

"Systematic" splits two ways, and the split decides whether Track-2 is a product or a paper:

- **constant** `F(x) = F_true(x) + b` → estimate `b`, subtract it, free horizon gain
- **state-dependent** `F(x) = F_true(x) + e(x)` → no constant correction helps

Tested non-circularly: `b` estimated on the 110 **training** pairs, evaluated on the 46 held-out
**validation** pairs, at two levels of expressiveness.

| | value | as % of error RMS |
|---|---|---|
| raw one-step error RMS | **0.3112** | (58% of saturation) |
| ‖b_field‖ (per-cell, 60×680×1440) | 0.0213 | 6.8% |
| ‖b_chan‖ (per-channel, 60 numbers) | 0.0043 | 1.4% |
| held-out variance explained by `b_chan` | **−0.01%** | |
| held-out variance explained by `b_field` | **+0.22%** | |

**The one-step error has essentially zero mean.** A constant correction explains 0.2% of it. And
subtracting the over-parameterised `b_field` makes the rollout *worse* beyond step 2 (−0.377 vs
−0.305 at step 6) — 58.7M values estimated from 110 samples fit noise, and injecting that noise every
step compounds. The held-out design is what exposed this; on training-derived numbers it would have
looked helpful.

So `e(x)` is state-dependent with near-zero mean and large variance. That is the one case where
nothing cheap helps — and `e(x)` is exactly what a neural network exists to learn. It had the
capacity and the data, and did not. Together with the two levers already measured — **capacity
(4× params → +0.007)** and **data volume (flat from n=55)** — the one-step error is **at the floor
for this architecture and this dataset**.

### What this means for the plan

- **The ceiling is real, and the cheap route is closed.** Not chaos, not variance collapse, not a
  subtractable bias: it is irreducible approximation error. Three named mechanisms tested, three
  eliminated.
- **Probabilistic rollout is the WRONG prescription** (it addresses chaos, which is absent) —
  correcting an earlier draft of this document, which named it as the remaining candidate.
- **Post-hoc bias correction is also dead**, measured, not assumed.
- **What would remain** is a different hypothesis class or a genuinely different observable set —
  not more capacity, more data, ensembling, diffusion, conditioning, Δt-scaling, or bias correction.
  All of those are now measured at ~0.
- **For the write-up:** this is the strongest form of the result. A physically-valid BGC emulator
  (0% negatives, mass 1.000, full amplitude retention) with a one-step useful horizon, where the
  limit has been traced to irreducible state-dependent approximation error and *four* candidate
  explanations have been eliminated by measurement. That is a complete negative result, which is
  publishable and honest, and it says stop optimising this configuration.

## Caveats

- Amplitude retention and perturbation RMS are ensemble-mean, masked over ocean cells; an ensemble
  mean is *expected* to be smoother than a member, so measuring no smoothing strengthens the
  no-collapse conclusion.
- The perturbation test uses the emulator's OWN dynamics; it shows the learned map is non-chaotic,
  which does not by itself prove v05 is non-chaotic on these timescales — but since the emulator is a
  good single-step operator, a chaotic v05 would have had to induce a chaotic emulator, and it did not.
- Growth rates are fit over the first 4 steps (log-linear); the error curve is so flat the fit is
  dominated by the step-1 offset, which is the point.

Artifacts: [`track2_runs/season_diag.json`](track2_runs/season_diag.json), [`track2_runs/lyapunov.json`](track2_runs/lyapunov.json), [`track2_runs/bias_decomp.json`](track2_runs/bias_decomp.json) · jobs 169498, 169528, 169630.

Artifact: [`track2_runs/season_diag.json`](track2_runs/season_diag.json) · script
`/scratch/qi_zim_neu/season_diag.py` · job 169498.
