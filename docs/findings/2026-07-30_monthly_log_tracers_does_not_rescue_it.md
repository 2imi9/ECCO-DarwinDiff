# Logging PIC, POC and FeT does not rescue the monthly emulator, and the seasonal-AR(1) bar stands

**Date:** 2026-07-30 · **Jobs:** 237982 (6 arms) → 238012 (common-space scoring) ·
**Artifacts:** `/work/neu/p2026_0089_neu/monthly_logfull/` ·
**Verdict: hypothesis REFUTED. The statement that the forward tool does not beat a seasonal
autoregressive baseline is unchanged and now better supported.**

## The hypothesis

The published monthly run (`depth_chl_emulator.json`) passes `--log-tracers Chl1` only, leaving
`PIC`, `POC` and `FeT` in linear space, even though the repo's own default names them and its
docstring says they "under linear z-scoring collapse to 0.34-0.67 of the true log-range and emit
3-14% non-physical output". Three of six tracers were therefore left in exactly the state that had
just been shown to wreck the daily emulator.

If that under-application explained the monthly **−0.161 against seasonal AR(1)**, it would change
what was told to Jon: that the forward tool is not yet a substitute for running the model.

## The design correction that made the test valid

The first attempt scored each arm with its own `--log-tracers`, which is invalid: skill is computed
in each run's **working space**, so a logged channel's number is log-space skill and a linear
channel's is linear-space skill. `PIC`, `POC` and `FeT` are logged in exactly one of the two arms,
which is the comparison of interest. That design compared apples to oranges precisely where the
hypothesis lived.

Both arms were therefore rescored in **two common spaces**, so only the training differs:

- **common-log** `Chl1,PIC,POC,FeT` — the physically motivated space, and `logfull`'s training space
- **common-linear** `Chl1` — the published convention, and `logchl1`'s training space

## Result

| metric space | arm (n=3) | vs persistence | **vs BEST free baseline** | best baseline |
|---|---|---|---|---|
| common-log | `logchl1` | −3.3169 (sd 0.105) | **−3.4420** (sd 0.108) | `anomaly_persist` |
| common-log | `logfull` | −0.4416 (sd 0.003) | **−0.4834** (sd 0.003) | `anomaly_persist` |
| common-linear | `logchl1` | +0.0369 (sd 0.008) | **−0.1841** (sd 0.010) | `ar1_seasonal_percell` |
| common-linear | `logfull` | −0.5048 (sd 0.173) | **−0.8501** (sd 0.212) | `ar1_seasonal_percell` |

**Each arm wins in the space it trained in and loses in the other**, which is what a fair
comparison of two training choices normally looks like and is why the first, uncontrolled version
of this test would have been misleading in whichever direction it happened to fall.

**Neither arm beats its best free baseline in either space.** That is the answer: the hypothesis is
refuted, and the monthly bar stands.

`logchl1` scored in common-linear gives **−0.1841 ± 0.010**, reproducing the published
**−0.161 ± 0.015** to within seed variation. So this run is anchored to the published number rather
than to a nearby configuration.

## What survives, and it is not nothing

**The physics win is real and space-independent.** Logging PIC, POC and FeT takes the maximum
non-physical fraction in the rollout from **0.138 to exactly 0.000**, across all three seeds. A
log-space model cannot emit non-positive output, so this is by construction rather than by tuning.
`logfull` is also far more reproducible: sd 0.003 against `logchl1`'s 0.105 in common-log, a factor
of 35.

So the honest trade is: `logchl1` scores better in the published metric and emits 13.8%
non-physical values; `logfull` scores worse there, emits none, and is much more stable across
seeds. Neither clears the baseline, so the choice is not a skill choice.

**The winning baseline changes with the metric space**, from `ar1_seasonal_percell` in linear to
`anomaly_persist` in log. Any statement of the form "the emulator loses to X" must therefore name
the space it was scored in. The published −0.161 is against seasonal AR(1) **in the mostly-linear
space**, and that is the number to quote.

## For Jon

No revision needed. The line "the forward tool beats persistence at a single step but not a
seasonal autoregressive baseline, so it is not a substitute for running the model yet" survives a
direct attempt to overturn it. The most plausible mechanism, that three of six tracers were being
z-scored in the wrong space, was tested at n=3 per arm in two common metric spaces and does not
rescue the result.

## Cross-reference

This composes with `2026-07-30_daily_logspace_training.md`, which found the same transform closes
91.6% of the daily collapse but also that it **hurts** a narrow strictly-positive channel
(`surfChl5`, CV about 0.26). Taken together the rule is that `--log-transform` should be selected
per channel on dynamic range and non-positivity rather than applied as a blanket list, and the
repo default naming `Chl1..Chl5,PIC,POC,FeT` without qualification is too broad in one direction
and the published monthly config too narrow in the other.
