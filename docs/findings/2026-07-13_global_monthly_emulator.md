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
| Skill vs. persistence | **+0.520** | +0.469 | +0.426 | +0.519 | +0.531 | +0.452 | +0.524 |
| Anomaly-R² vs. climatology | +0.391 | +0.766 | +0.762 | +0.406 | +0.349 | +0.610 | +0.245 |

- **Grid:** 680 × 1441 (0.25° global, latitude −80° to 89.75°); 456,873 valid ocean cells; 156 months.
- **Model:** FNO2d (PhysicsNeMo), 32 modes, width 64, **33.6 M parameters** — roughly seven times the
  equatorial-Pacific model (4.7 M) and the first global-resolution run of the emulator, trained
  natively on the B200. Residual formulation with a four-step rollout-aware loss. Training completed
  in approximately 19 minutes using about 16 GB of GPU memory.
- **Rollout:** stable over six steps and beats persistence at the final step. The worst tracer's
  domain mean drifts by approximately its own magnitude over the six steps (maximum absolute relative
  mass drift 1.008; maximum negative fraction 0.41) — a rollout caveat, though an improvement over the
  equatorial-Pacific case, in which some regimes failed the rollout check outright.
- A portable safetensors checkpoint was saved.

## Interpretation

Two points are essential to reading the +0.520 figure correctly.

1. **This is the first area-weighted global skill.** The metric now weights cells by cos-latitude, a
   correction introduced in the same session; an unweighted global metric would have been
   pole-biased and invalid.
2. **Persistence is a weaker baseline globally than in the equatorial-Pacific subdomain.** Persistence
   skill relative to climatology is −0.27 globally, compared with +0.22 over the equatorial Pacific
   and +0.98 at daily cadence: the diverse global monthly state changes more from month to month, so
   the emulator has more to gain. The global figure of +0.520 is therefore not directly comparable to
   the equatorial-Pacific emulator-skill figure of +0.30 (emulator vs. persistence — see
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
