# Two negatives that close two expensive lines (2026-07-19, overnight)

Both results are **nulls**, both were cheap, and each one closes a direction that would otherwise
have cost weeks. They are recorded as results, not as disappointments.

Together they also narrow the search: after tonight, exactly **one** hypothesis for the skill
plateau remains live, and it is testable.

---

## 1. We are NOT data-bound — the learning curve saturates at n≈55

**The experiment nobody had run.** Train the flagship at 25/50/75/100% of the available training
pairs, everything else matched (same cube, same split, same optimizer steps, log space,
`rollout_train_k 8`, `modes 24`, `width 64`, 150 epochs). 3 seeds per point.
Provenance: Slurm array `168270`, `lcurve_n{27,55,82,110}_s{0,1,2}.json`.

| n_train | mean skill (log, vs persistence) | std | seeds | Δ vs previous |
|---|---|---|---|---|
| 27 | +0.4167 | 0.0180 | 3 | — |
| 55 | **+0.4700** | 0.0051 | 3 | **+0.0532** |
| 82 | **+0.4701** | 0.0108 | 3 | **+0.0001** |
| 110 (all) | **+0.4657** | 0.0080 | 2 | −0.0044 |

**The curve is flat from n=55 onward.** Doubling the data from 55 to 110 pairs buys nothing:
+0.0001 from 55→82, and −0.0044 from 82→110, both well inside the seed spread (σ ≈ 0.005–0.011).

> **Speculation retracted.** On the first partial read, n=110 showed a single seed at +0.4577 and I
> floated that *removing* data might be actively helping — i.e. that the long-gap pairs were harmful.
> With the second seed in, n=110 is +0.4657 ± 0.0080 and the 82→110 difference is well within noise.
> **That hypothesis is not supported.** The honest statement is saturation, not degradation.

### Why this matters more than it looks

Every strategic analysis of this project has assumed **data is the binding constraint**. A five-lens
adversarial review said so explicitly, and it was the stated justification for rebuilding the cube
(the tracer *intersection* gives 158 timesteps; the *union* would give 323 at uniform monthly
spacing). **That justification is now refuted for skill purposes.** More timesteps of the same kind
will not raise skill.

This is consistent with the effective-sample-size argument: ~110 monthly pairs is roughly 9 annual
cycles, i.e. O(9–15) independent realizations of the dominant seasonal mode. Saturating at n≈55
(~4.5 cycles) means the model has seen the seasonal cycle enough times. Additional years of the
*same* cycle add little.

### What the curve does NOT show — and this is the important caveat

`--n-train` subsamples training **pairs**; each retained pair keeps its own Δt. So every arm carries
the same non-uniform-Δt pathology. **The curve varied quantity while holding quality constant.**

It refutes *"more of the same data helps."* It says nothing about *"cleaner data helps."*

### Caveats

- n=110 currently has 1 of 3 seeds (2 still running). The −0.0124 dip is within ~1.2σ of the n=82
  spread and should not be over-read until the remaining seeds land. **It is not yet evidence that
  more data actively hurts** — though see §3.
- Skill here is single-step, log space, vs persistence. It is not the headline climatology number.

---

## 2. Physical-state conditioning is a NULL — and not for the reason we assumed

**The diagnostic that avoids ~30 GPU-hours.** Before building any conditioning architecture, ask
whether physical state explains the emulator's *residual*.
Provenance: `linear_probe.json`, `linear_probe.png`, job `168334`, ~15 min on one B200.

| quantity | value |
|---|---|
| joint R² of residual on 6 physical fields | 0.0136 |
| permutation null | 0.0053 ± 0.0036 |
| **ΔR² above null** | **+0.0083** |
| **implied max skill gain (oracle bound)** | **+0.0041** |

The last number is an *upper bound* assuming a conditioning mechanism perfectly extracts every
linearly-available bit at zero optimization cost. For comparison, the two real attempts to add
information **cost** −0.010 (forcing concat) and −0.073 (seasonal encoding). **The best case is
~2.5× smaller than the harm already measured.** It sits inside the training procedure's noise floor.

### The surprising part

Our prior was *"physics is redundant — the model already infers it from the BGC state."*
**That is mostly false.** A ridge probe predicting each physical field from the 60 BGC channels,
fit on train and scored out-of-sample against a train-climatology baseline:

| field | probe R² | climatology | above climatology |
|---|---|---|---|
| SST | 0.965 | 0.965 | **+0.000** |
| SSSanom | 0.957 | 0.931 | +0.026 |
| SIarea | 0.661 | 0.711 | −0.050 |
| wspeed | 0.658 | 0.665 | −0.007 |
| mldDepth | 0.309 | 0.288 | +0.020 |
| oceanQsw | 0.694 | 0.505 | **+0.190** |

The high raw R² is almost entirely the **static spatial pattern** — the probe recovers a map, not a
time evolution. Only shortwave radiation carries real extra signal (+0.19; light drives chlorophyll).

So physical state **is** genuinely new information at the input. **It just doesn't explain the
error.** The residual is not physics-shaped.

That closes the line more firmly than redundancy would have: redundancy could be argued around with
a better encoder, but "the residual isn't physics-shaped" cannot.

### Methodology note

With ~344k ocean cells any naive R² is "significant". The null is a whole-timestep permutation
(spatial autocorrelation preserved exactly, temporal correspondence destroyed), 200 shuffles,
derangements only, in both random and **month-matched** variants — the latter tests for information
*beyond season*, which matters because seasonal encoding is already known to hurt. The two nulls
agree (+0.0095 vs +0.0083), so the small signal present is not merely seasonal.
**~40% of the raw 0.0136 was pure autocorrelation artifact.** Effective sample size is O(5–9)
seasonal realizations, not O(10⁷) cells.

### One reported claim was FALSE and is corrected here

The probe reported that *"seed0's saved config lies — records `modes=24` but its tensors are
`modes=20`"*. **This is wrong.** Verified independently by loading all six checkpoints:

| file | config | tensors | |
|---|---|---|---|
| opt3d_seed0 | modes=24 width=64 | modes=24 width=64 | ✅ |
| opt3d_seed1 | modes=20 width=64 | modes=20 width=64 | ✅ |
| opt3d_seed2 | modes=24 width=48 | modes=24 width=48 | ✅ |
| opt3d_seed3 | modes=28 width=64 | modes=28 width=64 | ✅ |
| opt3d_seed4 | modes=20 width=80 | modes=20 width=80 | ✅ |
| opt3d_seed5 | modes=24 width=80 | modes=24 width=80 | ✅ |

All six match, and the probe's own job log said so four lines after the comment asserting otherwise.
This matters beyond bookkeeping: the **published `v0.1.0` model card** instructs users to read
architecture from `ck["config"]`. That instruction is **correct** and needs no correction.
The ensemble heterogeneity is real; the "config lies" claim was not.

---

## 3. What remains: exactly one live hypothesis

Ruled out as levers, each by measurement:

| candidate | evidence |
|---|---|
| Model capacity | +0.007 for ~4× parameters |
| Data **quantity** | saturates at n≈55 (§1) |
| Model class (diffusion) | zero skill gain; −0.026 on 3-D |
| Physical-state conditioning | +0.0041 oracle bound (§2) |
| Ensembling | **works** (+0.05), already applied |

That leaves two possibilities:

- **(a) An aleatoric limit** — monthly BGC next-step prediction is simply this predictable.
- **(b) Data *quality*** — the operator is learning a blend of 1-to-7-month transitions, and no
  amount of such data can teach a clean monthly operator.

**(b) is testable tonight, cheaply, and the design is unusually clean.** Only **54** training pairs
have a true ~1-month gap (median 31 d); the other 55 have a median gap of **90 d**. And the learning
curve already supplies a perfectly quantity-matched control: a *random* subsample of **n=55** scores
**+0.4700 ± 0.0051**.

So: train on the 54 uniform-Δt pairs and compare against random-55. Same count, same config, same
everything — **only Δt quality differs**. Launched as Slurm array `168351`
(`--uniform-dt-only`, 3 seeds).

- **uniform ≫ +0.4700** ⇒ quality is the lever. The cube rebuild is worth it — but for
  *uniformity*, not volume, which is a different (and cheaper) target than the union cube.
- **uniform ≈ +0.4700** ⇒ quality is not the lever either, and we are at an aleatoric limit for
  this formulation.

### RESULT — and my own experiment was confounded

| arm | skill | n pairs |
|---|---|---|
| uniform-Δt (all ~1 month) | **+0.4508 ± 0.0021** | 55 |
| random-55 control | **+0.4700 ± 0.0051** | 55 |
| **Δ** | **−0.0192** | — |

Training *only* on true 1-month pairs is **worse** — about 4σ of the control's spread, so a real
difference rather than noise.

**But this comparison does not mean what it appears to.** The validation set carries the *same*
mixed-Δt structure. A uniform-trained model is therefore evaluated on 2-to-7-month transitions it
never saw during training. That is a **distribution mismatch**, and it is sufficient on its own to
produce −0.0192 without saying anything at all about data quality.

The design measured one column of a 2×2:

| | mixed val | uniform val |
|---|---|---|
| **mixed train** | +0.4700 | *pending* |
| **uniform train** | +0.4508 | *pending* |

### THE 2×2 — completed (job `168428`), and it inverts the reading

Single-step skill vs persistence, log space, 3 seeds per cell, evaluation only:

| | mixed val (n=47) | **uniform val (n=21)** |
|---|---|---|
| **mixed train** *(the flagship configuration)* | +0.4700 | **+0.0026** |
| **uniform train** | +0.4508 | **+0.4756** |
| Δ (uniform − mixed) | −0.0192 | **+0.4730** |

Per-seed on uniform-val: mixed-train `[0.0107, 0.0314, −0.0344]` · uniform-train `[0.4827, 0.4650, 0.4791]`.

**On genuine one-month transitions, the flagship configuration has essentially no skill over
persistence** — +0.0026, with one seed negative. A model trained on the *same number* of pairs, all
of them true one-month, scores **+0.4756** on that identical validation subset.

So Δt quality is not merely *a* lever. It is the difference between a working monthly operator and
one that is indistinguishable from doing nothing at monthly cadence.

### What is actually going on

The flagship is **not a monthly operator**. Its training pairs have a median gap of ~61 days, so it
has learned the *average* transition — roughly two months. Applied to a one-month gap it **overshoots**,
predicting more change than occurred. Symmetrically, the uniform-trained model applied to the
longer-gap mixed set **undershoots**, which is the modest −0.0192 penalty in the left column.

**Mechanism (hypothesis, not yet measured):** the residual magnitude grows with Δt, so long-gap pairs
carry much larger targets and therefore dominate an MSE training loss. Mixed training is then
*effectively* long-gap training, and the one-month pairs contribute little gradient. If that is right,
a 1/Δt loss weighting would recover most of the benefit without rebuilding anything — a cheap test
worth running before any cube work.

### Caveats

- **n=21 on the uniform validation subset**, and its per-seed spread for the mixed-trained arm is
  wide (0.066 range vs 0.018 for the uniform arm). The *sign* and magnitude are unambiguous; the
  precise value is not.
- **The uniform subset has no winter.** It spans March–November only (the 1-month gaps happen to fall
  outside Dec–Feb). Both arms are scored on the identical subset so the comparison is fair, but the
  result does not cover the winter regime — which is also where the MODIS comparison found v05's
  largest chlorophyll errors.
- Single-step only. Whether the same gap appears in rollout is untested.

### Consequence

This reopens the cube rebuild, but **for uniformity rather than volume** — the opposite of the
original justification, and a much cheaper target. The learning curve says more timesteps buy nothing
(§1); this says *uniform* timesteps buy a great deal. The union cube (323 steps at 100% uniform
spacing) would deliver both, but the uniformity is what matters.

It also means **every single-step skill number this project has reported is for a ~2-month operator,
not a monthly one** — including the +0.497 in the published v0.1.0 model card. The number is not
wrong, but its label is: it is skill on a mixed-Δt validation set with a median 61-day gap.

### On the confound

Reported alone, −0.0192 would have read as "uniform training hurts." The unconfounded column shows
the reverse, by a factor of 25. The design measured one column of a 2×2 and the missing column
carried the result — worth remembering as a design failure, not just a lucky catch.
