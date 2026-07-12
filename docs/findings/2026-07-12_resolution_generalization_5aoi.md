# Does the resolution result generalize across ocean regimes? (2026-07-12, continuation)

Continuation of `2026-07-12_resolution_sharpening.md` (eqpac). Tested the matched-capacity resolution
comparison (native 0.25° vs 1°, m8w32, `--residual --rollout-train-k 4 --epochs 500`) in 4 more regimes:
natlsubpolar (subpolar bloom), midatl (subtropical NW Atlantic), npac (subtropical NE Pacific), sopac
(Southern Ocean Pacific). Adversarially synthesized (3-agent workflow) + firmed to n=5. All LOCAL;
self-consistency vs ECCO-Darwin v05, NOT real obs.

## TL;DR (conservative, adversarially-verified)
1. **The one well-powered, generalizing result: at matched capacity finer resolution does NOT raise
   aggregate own-grid skill-over-persistence.** Δ = native−1° m8w32 ≈ 0 in eqpac (−0.007, n=10),
   natlsubpolar (−0.008, n=5), midatl (−0.002, n=5). This replicates the eqpac finding that the anchor
   gap was CAPACITY, not resolution. **High confidence.**
2. **The common-grid absolute-RMSE advantage (native more accurate on the identical smoothed field) is
   robust ONLY in eqpac (n=10, all seeds) and midatl (5/5 seeds).** It is NOT robust in npac (2/5) or
   sopac (3/5) once firmed to n=5 — the single-seed "native wins" there was not representative.
   natlsubpolar has no common-grid control yet. So this is a "large-scale-skill regimes" effect, not universal.
3. **npac is a DIAGNOSTIC exception, not a counter-example.** Its own-grid z-skill does rise with
   resolution (+0.089, n=5), carried by bio/particulate tracers — but this is fine-scale, single-step,
   NON-durable (rollout fails, beats@final 0/5), sits BELOW persistence on the common grid, and its
   common-grid RMSE edge is a coin-flip at n=5. It reveals the mechanism; it does not establish that
   resolution buys durable skill.

## The numbers

**Aggregate z-skill resolution effect (native − 1° m8w32):**

| regime | 1° | native | Δ | verdict | rollout beats@final |
|---|---|---|---|---|---|
| eqpac | +0.260 | +0.254 | −0.007 (n10) | null | 6/6 |
| natlsubpolar | +0.493 | +0.485 | −0.008 (n5) | null | 0.2–0.4 (weak) |
| midatl | +0.525 | +0.523 | −0.002 (n5) | null | 1.0 |
| npac | +0.155 | +0.244 | **+0.089** (n5) | positive* | **0.0 (fails)** |
| sopac | +0.098±.13 | +0.112±.18 | +0.014 (n5) | noisy-null | 1.0 |

\* npac positive but non-durable + statistically fragile (see below).

**Common-grid control (native area-averaged → 1°; native RMSE < 1°-origin RMSE across seeds):**

| regime | native RMSE (n=5) | 1° RMSE | native beats in | robust? |
|---|---|---|---|---|
| eqpac | 8.63 (m16w48) / 8.80 (m8w32) | 9.274 | 10/10 (n=10) | **YES** |
| midatl | 8.43–8.65 | 8.984 | **5/5** | **YES** |
| npac | 6.11–6.71 | 6.269 | **2/5** | NO |
| sopac | 4.15–5.48 | 4.577 | 3/5 | NO (noisy) |

## Mechanism (medium confidence): predictability scale-locality
Where each regime's month-to-month predictability lives sets both whether resolution helps z-skill and
which tracers carry it:
- **Large-scale-resident** (eqpac equatorial waveguide, natlsubpolar seasonal bloom, midatl gyre carbon
  advection): predictability survives coarse-graining → common-grid skill POSITIVE, native wins on
  absolute RMSE, own-grid z-skill resolution-NULL (fine scales just add denominator noise). Gain carried
  by **slow carbon DIC/ALK** (eqpac DIC +0.09/ALK +0.06; midatl +0.017/+0.012).
- **Fine-scale-resident** (npac oligotrophic gyre): large-scale carbon is a near-uniform reservoir
  persistence already nails (DIC negative skill), so exploitable signal is eddy/front/filament-scale →
  native resolves it (own-grid z-skill +0.089, carried by **POC +0.134, Chl1 +0.117, FeT +0.099, PIC
  +0.075**), but area-averaging destroys it → common-grid skill NEGATIVE for both resolutions. The sign
  flip is the mechanism's fingerprint.
- **Low/incoherent** (sopac ACC mesoscale chaos + deep mixed layers): huge seed variance; the SO PIC
  artifact (near-zero field; skill −13.8/−24.6) dominates and must be excluded.

## Honest caveats
- Only eqpac is fully powered (n=10). natlsubpolar/midatl/npac/sopac aggregate at n=5; the 3 new-AOI
  common-grid controls were single-seed then firmed to n=5. natlsubpolar common-grid is still missing.
- **npac +0.089 is statistically fragile**: n=5 ~4 df, p≈0.03 uncorrected but ≈0.15 after look-elsewhere
  across 5 regimes; small 1° grid (651 cells) inflates SE. Rollout fails → not a dynamics gain.
- Per-tracer "+Δ" on a channel that still loses to persistence (midatl Chl1, npac DIC) is "losing less
  badly," not a predictability gain — gated on sign of absolute skill.
- SO PIC excluded from sopac; sopac reported as an uninterpretable noisy null.
- Self-consistency vs v05, NOT real obs — npac "fine-scale skill" may be the emulator learning v05's own
  eddy advection, not real-ocean predictability. Whether 0.25° is eddy-RESOLVING vs merely PERMITTING in
  the subtropics (Rossby radius ~30 km vs ~25 km grid) is assumed, not shown.
- All resolution effects are one-month-horizon.

## Bottom line
The **eqpac null-z-skill result generalizes** (finer resolution ≠ higher aggregate skill-over-persistence;
the anchor gap was capacity). The **absolute-accuracy resolution benefit is real but confined to
large-scale-skill regimes** (robust in eqpac + midatl), not universal. **npac is a clean diagnostic of
predictability scale-locality**, not evidence that resolution buys durable skill. This is the honest,
de-hyped generalization — the adversarial synthesis + n=5 firm-up caught an initial over-read (that npac
"sharpened" and native "won everywhere").
