# `PARAM_LOG_SCALE` is not an undisclosed bug, and the A/B that settles it was already on disk

**Date:** 2026-07-30 · **Arms:** `logscale/{ctrl_n50, logsr_n50, prior_ctrl_n50, prior_logsr_n50}`
(job 227773, n=50 each, 2000 epochs, 3 AOIs), all four `verify_run` exit 0 ·
**Verdict: document it, do not re-run. The geometric map does not measurably change the trio
(paired P = 0.31), and both untrained trio baselines are 0/50.**

The open item read: "`PARAM_LOG_SCALE` defaults to `""`, so every published run used the linear
bounding map despite `Param.scale="log"`. This is a factor-of-five prior bug and it is currently
undisclosed." Two parts of that need correcting, and then the substance has an empirical answer.

## Correction 1: one parameter, not many

Only **`scav_rat`** is declared `scale="log"` in the registry. Every other Carroll-N parameter is
`linear`, so for five of six there is no discrepancy to disclose at all.

## Correction 2: neither map hands the metric a free recovery

| map | `scav_rat` prior midpoint | rel offset vs Carroll | inside the 0.40 Cal band? |
|---|---|---|---|
| linear (the default) | 1.515e-06 | **1.515** | no |
| geometric (`PARAM_LOG_SCALE=scav_rat`) | 3.0e-07 | **0.502** | no |

The midpoints do differ by 5.05x, so "factor of five" is right about the prior. But both sit
outside the Cal-grade band, so **no published `scav_rat` count is contaminated by the choice**.
That is a different and much weaker claim than a prior bug.

What the choice really affects is difficulty, not correctness. `scav_rat`'s bounds span 100x
(3e-8 to 3e-6), so under a linear sigmoid the top decade occupies 90.9% of the map and only 7.5%
of prior mass starts below Carroll. That matters because `scav_rat` is the sole binding leg of the
flagship trio.

## The A/B already existed, ungraded

Job 227773 ran the full matched design and nobody graded it: both arms at n=50 **and** an untrained
baseline for each arm, which is exactly what the standing directive requires.

| parameter | linear `ctrl_n50` | chance | geometric `logsr_n50` | chance |
|---|---|---|---|---|
| alpfe | 49/50 | 0.200 | 50/50 | 0.200 |
| scav_rat | 26/50 | 0.060 | **35/50** | **0.160** |
| R_PICPOC | 50/50 | 0.060 | 45/50 | 0.060 |
| **trio** | **25/50** | **0/50** | **31/50** | **0/50** |

`ctrl_n50` reproduces the published flagship trio of **25/50** exactly, so this A/B is directly
comparable to the flagship rather than to a nearby config.

### Read the marginal gain carefully

`scav_rat` rises 26/50 to 35/50, which looks like a clear win. But its **untrained chance rate rises
at the same time**, 0/50 to 8/50, because the geometric map puts the prior nearer Carroll. Part of
that marginal gain is the prior, not learning. The trio is immune to this: its untrained baseline is
**0/50 in both arms**, so a trio gain would be real.

### The trio gain is not significant

The two arms share seeds 0-49, so the comparison is paired.

| | count |
|---|---|
| linear trio | 25/50 |
| geometric trio | 31/50 |
| linear fails, geometric passes | 15 |
| linear passes, geometric fails | 9 |
| **exact McNemar, two-sided** | **P = 0.3075** |

The net +6 is 15 gains against 9 losses, which is what a coin flip produces. **24 of 50 seeds change
verdict**, so the map moves individual fits a great deal while leaving the aggregate where it was.
Quoting 25 to 31 as an improvement without the paired test would have been an over-claim, and the
marginal `scav_rat` row would have made it look stronger still.

## Decision

**Keep the linear default and disclose the discrepancy.** The re-run that the open item asked for
has effectively already happened, at n=50 with matched baselines, and it shows no significant effect
on the headline. Re-running the flagship under the log map would spend cluster time to move a number
by an amount indistinguishable from noise.

What must change is the wording, not the config:

- The registry declares `scav_rat` as `scale="log"` while the training bounding map is linear unless
  `PARAM_LOG_SCALE` is set. That mismatch is real and should be stated where the method is described.
- `prior_midpoint_offset()` honours `Param.scale` and reports `scav_rat`'s **geometric** midpoint
  (rel 0.502), while training actually starts from the **linear** one (rel 1.515). So the reported
  prior-contamination diagnostic does not describe the prior the published runs used. This is the
  sharpest form of the issue and the one worth fixing in code.

**Do not cite the geometric arm as an improvement.** It is a null on the trio, and the honest
statement is that `scav_rat`'s identifiability does not hinge on the bounding map.
