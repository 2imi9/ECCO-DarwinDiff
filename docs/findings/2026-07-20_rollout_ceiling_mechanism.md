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
3. **It changes what would help.** Not a bigger model and not phase/forcing inputs (the model is not
   flattening, so it is not obviously missing phase). The candidates that remain are **ensemble
   spread / probabilistic rollout** — i.e. predict a distribution rather than a trajectory — which
   is also the only lever that has ever helped the rollout (deep ensembling).

## Caveats

- Amplitude retention is measured as spatial standard deviation over ocean cells, ensemble-mean
  prediction. An ensemble mean is *expected* to be smoother than a member; that it is **not**
  smoother here (0.95–1.0) makes the no-collapse conclusion stronger, not weaker.
- The chlorophyll correlation is across 15 starts at fixed horizon, not a within-trajectory time
  correlation; it is sensitive to start sampling. n_eff is small.
- "Chaotic" is an interpretation, not a measurement. A Lyapunov-style estimate (perturbation growth
  rate on the emulator vs on v05 itself) would test it, and has not been run.

Artifact: [`track2_runs/season_diag.json`](track2_runs/season_diag.json) · script
`/scratch/qi_zim_neu/season_diag.py` · job 169498.
