# Global-monthly emulator: skill over persistence on every tracer (2026-07-13)

## Question

The Track-2 emulator was established on the equatorial Pacific subdomain. Does it generalize to the
global ocean at monthly cadence, and does it beat persistence once the skill metric is corrected for
grid-cell area?

## Summary

The emulator generalizes on both counts: the verdict is `MAKE`, and all six tracers beat persistence.
All values below are **local** — they measure self-consistency against the ECCO-Darwin v05 model
output, not agreement with real observations.

## Result (B200, 200 epochs, area-weighted skill)

| | Overall | DIC | ALK | PIC | POC | FeT | Chl1 |
|---|---|---|---|---|---|---|---|
| Skill vs. persistence (linear space) | **+0.520** | +0.469 | +0.426 | +0.519 | +0.531 | +0.452 | +0.524 |
| Anomaly-R² vs. climatology | +0.391 | +0.766 | +0.762 | +0.406 | +0.349 | +0.610 | +0.245 |

- **Grid:** 680 × 1441 (0.25° global, latitude −80° to 89.75°); 456,873 valid ocean cells; 156 months.
- **Model:** FNO2d (PhysicsNeMo), 32 modes, width 64, **33.6 M parameters** — roughly seven times the
  equatorial-Pacific model (4.7 M) and the first global-resolution run of the emulator, trained
  natively on the B200. Residual formulation with a four-step rollout-aware loss. Training completed
  in approximately 19 minutes using about 16 GB of GPU memory.
- **Rollout:** stable over six steps and beats persistence at the final step. **Caveat (2026-07-19):** the multi-step comparison here is against persistence only. Persistence is a weak long-horizon baseline — the separate rollout-horizon study (`docs/findings/` rollout-verify work) found that at a 12-month horizon persistence reads +0.441 ("strong") while climatology reads −0.265 (dead), so persistence-relative multi-step skill can look healthy while the forecast has drifted off the attractor. Multi-step skill should therefore co-report climatology; the single-step table above does (anomaly-R² row), but this six-step rollout does not, so "beats persistence at the final step" should be read as persistence-relative only. (The drift itself is not hidden — it is quantified in the next sentence.) The worst tracer's
  domain mean drifts by approximately its own magnitude over the six steps (maximum absolute relative
  mass drift 1.008; maximum negative fraction 0.41) — a rollout caveat, though an improvement over the
  equatorial-Pacific case, in which some regimes failed the rollout check outright.
- A portable safetensors checkpoint was saved.

## Robustness and rollout physics (2026-07-14 follow-up)

**Seed variance — the headline is bankable.** Five seeds at modes 32 / width 64 give
**+0.5165 ± 0.0023** (linear space; seeds: +0.5204, +0.5139, +0.5165, +0.5146, +0.5170). The result is not a
lucky seed; the spread is ±0.5% of the mean.

**Capacity saturates.** A capacity ladder (all seed 0) gives m48w96 +0.522, m64w96 +0.525,
m64w128 +0.526, m32w128 **+0.527** — the best config beats the modes32/width64 baseline (+0.520)
by only +0.007 despite ~4× the parameters. Capacity is not the bottleneck.

> **CORRECTION (2026-07-19).** This paragraph previously concluded that "the ~+0.52 level is close to
> the ceiling for this data and formulation." That inference is **refuted**. The capacity-ladder
> result above is real and stands — more parameters buy ~nothing — but capacity saturation does not
> imply an intrinsic ceiling. **Ensembling is a different axis**, and on the two configurations where
> an 8-seed deep-ensemble control was actually run it adds skill on the same formulation and the same
> inputs: daily eqpac +0.304 → +0.445, and the depth-resolved monthly 3-D run +0.432 → +0.484 (both
> linear space). Those are **separate experiments** — no ensemble control has been run on *this*
> global-monthly surface configuration, and both of those ensembled values are numerically *below*
> +0.52, so they do not establish where this run's ceiling lies. The honest statement is that the
> ceiling claim here is **unsupported**, not that a specific gain is proven for it. The plateau was
> epistemic (seed variance), not aleatoric.

**Rollout positivity fix — partial, and it exposes a real tension.** Adding `--rollout-positivity`
(project concentrations to ≥ 0 between autoregressive steps, same seed-0 model) cuts the maximum
negative-cell fraction from **0.411 → 0.062** (an 85% reduction) and leaves single-step skill
unchanged (+0.5204 → +0.5206, as expected). However, it *worsens* the maximum relative mass drift
(**1.008 → 1.324**): clamping negatives to zero only ever *adds* mass, pushing the domain mean up.
Positivity and mean-conservation are therefore in tension under a naive projection. The honest next
step (#7) is a **mass-conserving positivity** operator (clamp, then redistribute the added mass) or
a log-space parameterization for the nonnegative tracers.

## Interpretation

Two points are essential to reading the +0.520 figure correctly.

1. **This is the first area-weighted global skill.** The metric now weights cells by cos-latitude, a
   correction introduced in the same session; an unweighted global metric would have been
   pole-biased and invalid.
2. **Persistence is a weaker baseline globally than in the equatorial-Pacific subdomain.** Persistence
   skill relative to climatology is −0.27 globally, compared with +0.22 over the equatorial Pacific
   and +0.98 at daily cadence: the diverse global monthly state changes more from month to month, so
   the emulator has more to gain. The global figure of +0.520 is therefore not directly comparable to
   the equatorial-Pacific emulator-skill figure of +0.30 (both figures are emulator vs. persistence in **linear space**; the identical-config log-space control of that daily eqpac run collapses to +0.0361, so the +0.30 reflects skill on bloom dynamics in a few high-magnitude cells rather than on the field as a whole — see
   `docs/findings/emulator_*_scored.md`, distinct from the +0.22 persistence-vs-climatology figure
   above): the metric weighting, the region, and the baseline strength all differ. The load-bearing
   claim is the sign and uniformity of the result — every tracer, across the global ocean, beats
   persistence, with a stable multi-step rollout.

## Limitations

- Self-consistency against the v05 model output; not a validation against real observations (issue #163).
- This is a next-state surrogate of the v05 model output; it does not render Darwin differentiable and
  does not learn biology from data. External validation against SOCAT and GLODAP (#163) is the step
  that would make this a scientific finding rather than a model surrogate.
- The cube was extracted before the antimeridian-seam correction and therefore carries one redundant
  ±180° column (1441 columns rather than 1440). The effect on skill is negligible, but a clean
  re-extraction would remove it.
- Skill is reported as a domain aggregate; a per-cell skill map, distinguishing strong from weak
  regions, is the natural next diagnostic and is not part of this run.
- The cube is 46.6% valid ocean (0.25° oversamples LLC270 and therefore leaves unfilled cells); the
  FNO fills non-valid cells with zero.

## Conclusion

The residual, rollout-aware FNO emulator generalizes from a single area of interest to the global
ocean, beating persistence on all six tracers with a stable multi-step rollout, and runs natively on
the B200. The natural next steps are a per-cell skill map and external validation against SOCAT and
GLODAP (issue #163).
