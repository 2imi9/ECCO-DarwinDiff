# Log-space training rescues most of the daily emulator's collapse, and does not clear the bar

**Date:** 2026-07-30 · **Jobs:** 237761 (prep) → 237762 (6 arms) → 237763 (score) → 238005
(clip audit) · **Artifacts:** `/work/neu/p2026_0089_neu/daily_logspace/` ·
**Status: FINAL for the six training arms (all scored). The clipping audit (238005) is still
pending and is the only open item.**

## What this tested

`2026-07-30_daily_emulator_rescored_vs_ar1.md` measured that the pre-existing daily emulator's
`+0.408` is a linear-space number, and identified the mechanism: it emits non-positive chlorophyll
in 1.0 to 5.9% of held-out cells where v05 does so in 0.04 to 0.09%, and in log space each such
cell sits 20 to 25 log units from the median. That note left the daily question **open**, because
the model was trained in linear space and `--log-transform` is the known fix for both the metric
artifact and positivity: a log-space model cannot emit non-positive output at all.

This is the direct test. **No new data, no new architecture, one variable changed.**

Two arms, because there were two candidate causes:

- **`log5`** log-transform on the 4 live channels, `surfChl4` still present in the cube
- **`log4`** the same, plus `surfChl4` removed from the cube entirely

`surfChl4` is numerically zero (physical_std 2.9e-08), but `standardize` divides each channel by
its own train std, which amplifies it to unit variance in z-space where `masked_mse` weights
channels equally. So in `log5` it still contributes about a fifth of the training gradient as
noise, and dropping it only at scoring time cannot undo that. 3 seeds per arm.

### A trap worth recording

`build_log_mask` matches the channel-name stem literally, and this cube's channels are
`surfChl1..surfChl5`, not `Chl1..Chl5`. The **default** `--log-tracers` list would have matched
**nothing** and silently trained in linear space, reproducing the very run this experiment exists
to beat. The names were passed explicitly and a post-training assert confirms the transform
engaged. It did: 4 channels, with percentile floors of 3.60e-05, 2.03e-05, 1.79e-06 and 2.89e-02,
all far above the old fixed 1e-12.

## Result 1, FINAL: the mechanism is confirmed

The transform does what it was predicted to do. A log-space model cannot emit non-positive
chlorophyll, so the clipping artifact that dominated the linear model's log score is gone by
construction rather than by tuning.

In the trainer's own log space, skill against persistence across the six runs is **+0.201 to
+0.224**, against roughly **−4.0** for the linear model scored in log space. That is the single
largest effect measured on this model.

## Result 2, FINAL: it still does not beat a per-cell AR(1)

Scored by `emulator_baselines_v2` against the full free-baseline panel with block-bootstrap CIs,
all six arms:

| arm | vs persistence | vs BEST free baseline | best |
|---|---|---|---|
| linear (job 236516) | −4.0031 [−4.947, −3.204] | **−4.0940** [−5.068, −3.269] | `ar1_percell` |
| `log4_s0` | −0.3225 | −0.3465 | `ar1_percell` |
| `log4_s1` | −0.3197 | −0.3437 | `ar1_percell` |
| `log4_s2` | −0.3192 | −0.3432 | `ar1_percell` |
| `log5_s0` | −0.3227 | −0.3467 | `ar1_percell` |
| `log5_s1` | −0.3265 | −0.3506 | `ar1_percell` |
| `log5_s2` | −0.3258 | −0.3499 | `ar1_percell` |
| **`log4` mean** | | **−0.3445** (sd 0.0015) | |
| **`log5` mean** | | **−0.3491** (sd 0.0017) | |

Log-space training closes **91.6%** of the gap, from −4.094 to −0.345, and **still loses to a
per-cell annual AR(1)** with the CI clear of zero. Seed spread is 0.0015, so this is not noise, and
`ar1_percell` is the winning baseline in every single arm.

### The dead-channel hypothesis is essentially a null

`log4` beats `log5` by **0.0046**, consistent in sign across all three seed pairs against a seed sd
of about 0.0016. So removing `surfChl4` from training is a real effect and a negligible one: about
1.3% of the remaining gap. The worry that a numerically-zero channel amplified to unit variance by
`standardize` would poison a fifth of the training gradient is **measured and it does not matter**.

That is worth stating positively. Two candidate causes were separated in one experiment, and the
answer is that log space carries essentially all of the effect and the dead channel carries none of
it.

## The caveat that must travel with those numbers

The trainer reports **+0.22** and the scorer **−0.32** for the same run. Both are correct; they
are not the same log space.

- `emulator_poc` floors the log at a **percentile of the positive train values** (3.60e-05 for
  surfChl1), which is the convention it adopted precisely because a fixed floor "inflated the
  log-space std by 1.72x and compressed the real signal".
- `emulator_baselines_v2` still floors at a hard **1e-12**, with a stale comment claiming the two
  match. Filed as issue #215 before these runs existed.

That is not merely a rescaling, and the direction is not neutral. **The scorer's floor favours
persistence.** Truth is non-positive in about 0.085% of held-out cells and persistence in about
0.086% of the same cells, so they co-occur: at such a cell both clip to log(1e-12) = −27.6 and
persistence scores an exact zero error, while a log-space model, which cannot emit non-positive
output, predicts a physically sensible small positive and is charged roughly (−5 + 27.6)² ≈ 510
for being right.

Job 238005 measures this directly by recomputing skill restricted to cells where prediction, truth
and persistence are all strictly positive, which is the subset where log space is genuinely
defined. **Both numbers will be reported.** The model-versus-baseline comparison is internally
consistent either way, since every predictor is floored identically, so −0.345 stands as the
headline; the audit says how pessimistic it is.

## What this settles

**The daily Track-2 question is answered, and the answer is negative but much narrower than
before.** The daily emulator is not limited by the metric artifact, which is now fixed, nor by the
dead channel. It is limited by something else, and a per-cell AR(1) on daily data is a genuinely
hard baseline because lag-1 r is 0.994 to 0.996.

That is a cleaner statement than the one it replaces. The earlier `+0.408` was a linear-space
artifact; the honest number is about **−0.345 against the strongest free baseline**, from a model
that is physically valid by construction.

## Pending

- job 238005, the strictly-positive restriction, which says how pessimistic −0.345 is
- whether the same under-application of `--log-tracers` explains the **monthly** −0.161 against
  seasonal AR(1): the published monthly run logs `Chl1` only and leaves PIC, POC and FeT linear,
  despite the repo's own default including them. Jobs 237982 and 238012 test it. First reading is
  that logging them eliminates non-physical output entirely (max negative fraction 0.138 → 0.000),
  which is a space-independent physics win whatever the skill does.

## For the record: what to say about daily now

Track 1 (the parameter learner) was already closed on two independent grounds. Track 2 is now
closed too, on a measurement rather than an assumption, and the statement is narrow and defensible:

> A daily surface-chlorophyll emulator of v05, trained in log space so that it is physically valid
> by construction, beats persistence in its own working space but loses to a free per-cell AR(1) by
> 0.345 with the CI clear of zero. The earlier +0.408 was a linear-space artifact. Daily
> autocorrelation of 0.994 to 0.996 makes AR(1) a genuinely hard baseline, and the emulator does
> not clear it.

The remaining open direction is not architecture and not the metric. It is that a one-step daily
operator is being asked to beat a baseline that already knows the persistence structure almost
perfectly, and nothing in this experiment suggests more capacity would change that.
