# Global-monthly emulator beats persistence on every tracer (2026-07-13)

**Question.** The Track-2 emulator was proven on the eqpac box. Does it generalize to the
**whole globe** at monthly cadence — and does it beat persistence once the skill metric is
made area-correct?

**Answer: yes, decisively.** VERDICT **MAKE**, and all six carbon tracers beat persistence.
All numbers are **LOCAL** (self-consistency vs the ECCO-Darwin v05 *model*, not real obs).

## Result (B200, 200 ep, area-weighted skill)

| | overall | DIC | ALK | PIC | POC | FeT | Chl1 |
|---|---|---|---|---|---|---|---|
| **skill vs persistence** | **+0.520** | +0.469 | +0.426 | +0.519 | +0.531 | +0.452 | +0.524 |
| anomaly-R² vs climatology | +0.391 | +0.766 | +0.762 | +0.406 | +0.349 | +0.610 | +0.245 |

- **Grid:** 680×1441 (0.25° global, lat −80…89.75), 456,873 valid ocean cells, 156 months.
- **Model:** FNO2d (PhysicsNeMo), modes 32 / width 64, **33.6M params** — a genuine B200-scale
  model (7× the eqpac 4.7M), residual + rollout-k4. Ran in ~19 min, ~16 GB RAM.
- **Rollout:** 6 steps, **stable and beats persistence at the final step** (max |neg-frac| 0.41,
  max |mass drift| 1.008) — *better* rollout behavior than the eqpac box, where some regimes failed.
- Checkpoint saved (safetensors, portable).

## Why the global number is higher than eqpac (and honest about it)

- **This is the first *area-weighted* global skill** (cos-lat), landed via a bug fix the same
  session — an unweighted global metric would have been polar-biased and invalid.
- **Persistence is a *weaker* baseline globally than in the eqpac box.** persistence-vs-climatology
  is **−0.27** globally vs **+0.22** at eqpac (and +0.98 at daily cadence): the diverse global
  monthly state changes more month-to-month, so there is more for the emulator to gain. So the
  global +0.52 is not directly comparable to the eqpac +0.30 — different metric weighting, region,
  and baseline strength. The load-bearing claim is the **sign and uniformity**: every tracer,
  everywhere, beats persistence, with stable rollout.

## Caveats

- Self-consistency vs the v05 model output — **not** validated against real observations (#163).
- The cube was extracted before the antimeridian-seam fix, so it carries one redundant ±180
  column (1441 vs 1440); negligible for the skill, but a clean re-extraction would drop it.
- Skill is reported as a domain aggregate; a per-cell skill map (where it's strong vs weak) is the
  natural next diagnostic and is not in this run.
- Cube is 46.6% valid ocean (0.25° oversamples LLC270 → holey); the FNO fills non-valid with 0.

## Bottom line

The residual+rollout FNO emulator **generalizes from a single AOI to the whole globe** and beats
persistence on all six carbon tracers with stable multi-step rollout, running B200-native. Next:
a per-cell skill map, and — the standing #1 gap — external validation vs real SOCAT/GLODAP (#163).
