# Daily surface-chlorophyll emulator beats persistence, with caveats (2026-07-13)

## Question

At daily cadence, persistence is a near-perfect baseline (persistence skill vs. climatology ≈ +0.95,
compared with +0.22 at monthly cadence over the same region), because consecutive days barely differ.
Can the emulator beat it, and is a daily next-step surrogate worth building?

## Summary

Yes, it beats persistence: the verdict is `MAKE` with an overall skill of **+0.408** — a better
outcome than an early undersized smoke suggested (that run broke). Two caveats qualify the result
(a degenerate tracer and non-physical rollout values). All values are **local** (self-consistency
against v05, not real observations).

## Result (B200, eqpac 0.25°, 150 epochs)

- **Configuration:** equatorial Pacific, 0.25° (81 × 201), **9,392 daily steps**, five chlorophyll
  tracers (surfChl1–5), SST and wind-speed forcing, residual formulation with a four-step
  rollout-aware loss; FNO2d, 16 modes, width 48, 4.7 M parameters.
- **Overall skill vs. persistence: +0.408** (area-weighted); anomaly-R² vs. climatology +0.973.
- **Per-tracer skill:** surfChl1 +0.522, surfChl2 +0.461, surfChl3 +0.402, surfChl5 +0.208, and
  surfChl4 **−607** (see caveat 1).
- **Rollout:** stable over six steps and beats persistence at the final step; maximum absolute mass
  drift 0.106; maximum negative fraction 0.96 (see caveat 2).

## Caveats

1. **surfChl4 is degenerate in this region.** Its physical RMSE is ~1×10⁻¹⁰ — chlorophyll group 4 is
   essentially absent in the equatorial Pacific. Its z-scored variance is therefore near zero, and the
   skill *ratio* (1 − MSE_model/MSE_persistence) is numerically unstable and explodes to a large
   negative value, even though its absolute error is negligible. Because its absolute contribution to
   the aggregate is negligible, it does not drag the overall skill; the aggregate is carried by
   surfChl1–3. This tracer should be dropped from the equatorial-Pacific configuration.
2. **Rollout produces non-physical negative chlorophyll** (maximum negative fraction 0.96). The
   emulator has no positivity constraint, so autoregressive rollout drifts into negative values. This
   is a physicality defect, not a skill defect, and motivates a positivity transform or constraint for
   the daily configuration.

## Interpretation

The headline is that a properly sized daily emulator **can** beat the near-perfect daily persistence
baseline — contrary to the expectation set by an undersized smoke run. The margin (+0.41) is smaller
than the global-monthly result (+0.52) precisely because daily persistence is so much stronger a
baseline. The high anomaly-R² (+0.97) confirms the emulator easily beats climatology; the value it
adds over persistence is real but modest, and is likely to be larger over multi-day rollout horizons
than in single-step prediction.

## Next steps

- Re-run without surfChl4 (and possibly without the weak surfChl5) for a clean equatorial-Pacific
  daily result.
- Add a positivity transform to eliminate negative-chlorophyll rollout.
- Evaluate multi-day rollout skill explicitly, where the emulator's advantage over persistence should
  widen.
- External validation against real observations remains the standing gap (issue #163).
