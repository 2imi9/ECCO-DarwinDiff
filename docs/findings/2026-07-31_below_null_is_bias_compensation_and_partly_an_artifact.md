# Below-null recovery is a named, published phenomenon, and one of our two instances is a scoring artifact

**Date:** 2026-07-31 · **Method:** 15-agent literature workflow, 7 lenses, every citation independently
re-verified, then the two load-bearing DOIs checked again by hand against the publisher ·
**Verdict: NOT a breakthrough. A known phenomenon partly rediscovered, with one instance that is
probably an artifact of our own bounds geometry.**

## What prompted it

Two parameters recover significantly *below* their own architecture-matched untrained null:

| comparison | trained | untrained null | Fisher P |
|---|---|---|---|
| `diatomgraz`, flagship | 3/50 | 32/50 | 6.69e-10 |
| `alpfe`, subsurface-only iron (`eq_sub`) | 0/50 | 17/50 | 2.96e-06 |

An information limit predicts recovery **at** the null. Below the null requires a directed pull.
The working hypothesis was that this is structural error being absorbed into those parameters.

## The phenomenon is established, named twice, with a precedent on our own parameter

**It is called reciprocal bias compensation.** Löptien & Dietze (2019), *Biogeosciences* 16,
1865–1881, [10.5194/bg-16-1865-2019](https://doi.org/10.5194/bg-16-1865-2019), verified against the
publisher: they coin the term for "flaws of one model component (ocean mixing) ... compensated for
by tuning–tweaking another model component (biogeochemical cycling)", and report that their tuned
configuration projects a suboxic-volume trend "even more off relative to the Genuine Truth than the
trend of MIX+", the deliberately biased *untuned* control. That is calibrated-worse-than-uncalibrated,
published, in an ocean biogeochemical model.

**There is a precedent on the rain ratio specifically.** Pasquier et al. (2023), *Biogeosciences* 20,
2985–3009, [10.5194/bg-20-2985-2023](https://doi.org/10.5194/bg-20-2985-2023), titled *"Optimal
parameters ... compensate for circulation biases but replumb the biological pump"*. Their optimiser
drove `r_PIC` to **1.02%**, which they call "unrealistically small compared to other estimates that
range from roughly 3 to 12%", in order to absorb a circulation bias.

That is our `R_PICPOC`. Darwin's 0.0425 sits inside the 3–12% band, our epoch-matched anchor-off
control gives 6/50 and the anchored flagship gives 50/50. **The Daniels anchor is preventing exactly
the documented failure**, which reframes it as principled rather than ad hoc.

Kriest et al. (2020) call the same thing "overtuning"; Hourdin et al. (2017) state that "tuning may
be seen as an error compensation process rather than as model calibration". The statistical basis is
older still: Brynjarsdóttir & O'Hagan (2014) show that with discrepancy ignored the estimator is
biased and the bias **persists as data increase**.

**So we should stop presenting below-null as new.** It is a rediscovery. Cite it.

## And one of our two instances is probably our own bounds geometry

Checked directly against the registry, not taken from an agent:

| parameter | bounds | Carroll | sigmoid midpoint (θ=0) | lower band edge | midpoint rel-offset |
|---|---|---|---|---|---|
| `alpfe` | (0.05, 1.0) | 0.92831 | 0.525 | 0.5570 | 0.4345 → **just outside** 0.40 |
| `diatomgraz` | (0.05, 1.0) | 0.83003 | 0.525 | 0.4980 | 0.3675 → **just inside** 0.40 |

The two differ only in which side of a band edge the untrained midpoint lands on, and **both sit
within ~3% of the box width from that edge** (alpfe 3.4%, diatomgraz 2.8%).

That makes the untrained null a **knife-edge quantity**. `diatomgraz`'s 32/50 is high because the
prior midpoint happens to fall inside the Cal band. Once it does, *any* training that moves the
parameter appreciably takes it out of band, so a low trained count follows without any directed
pull at all. **`diatomgraz`'s below-null result is most likely null inflation, not compensation.**

This is the `KNOWN_PRIOR_CONTAMINATED` defect the repo already pins with an xfail test, now
quantified as a knife edge rather than a mere offset.

## The one instance that is clean, and why it is also now in doubt

`alpfe` at **49/50 under surface iron and 0/50 under subsurface iron** is the clean contrast. Model,
bounds, prior, sigmoid, architecture and untrained null are all identical; **only the observation
operator changes**. No prior-geometry explanation can produce that.

But the same session established that the subsurface channel has not converged: the 50-day window is
0.13 of one e-fold on a 384-day relaxation time, and the hardcoded initial condition carries
log-leverage 0.983. So the clean contrast may be a transient artifact rather than a discrepancy
signature. See `2026-07-31_depth_mechanism_does_not_replicate_in_eqpac.md`.

The window-swap test gates this too.

## What is still plausibly novel, conditional on the window test

1. **Depth-stratum selection of which half of a degenerate pair is recoverable** — surface identifies
   the source, subsurface the sink, within one tracer, with everything else fixed.
2. **A within-parameter control the compensation literature does not have.** Every precedent changes
   the circulation, the model component or the forcing. Ours changes only the observation operator.
3. **An untrained-network null as a reference-light detector of directed pull inside a single
   configuration.** Real, but weaker than first claimed, because the knife-edge geometry above means
   the null must be reported with its distance to the band edge or it cannot be interpreted.

## Actions

- Do not describe below-null as a new phenomenon. Cite Löptien & Dietze 2019 and Pasquier et al. 2023.
- Do not cite `diatomgraz` 3/50-vs-32/50 as evidence of bias compensation. Report it as prior-geometry
  contaminated, with the 2.8% band-edge distance quoted.
- Every future untrained null must be reported **with its midpoint-to-band-edge distance**, so a
  knife-edge null cannot be read as a stable baseline.
- The `alpfe` surface-vs-subsurface contrast remains the load-bearing case, gated on the window test.
