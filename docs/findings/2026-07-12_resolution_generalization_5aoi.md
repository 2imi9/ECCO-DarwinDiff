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
2. **The common-grid absolute-RMSE advantage is regime-specific in SIGN, not universal.** Native beats
   1° robustly in eqpac (10/10) and midatl (5/5), but **LOSES robustly in natlsubpolar (0/5 — coarse is
   more accurate)**, and is noisy in npac (2/5) and sopac (3/5). So there is no "finer resolution → more
   accurate" law; the effect helps in some regimes, hurts in another, and is noise in the rest. The
   single-seed "native wins everywhere" (earlier read) was wrong.
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

| regime | native RMSE (n=5) | 1° RMSE | native beats in | verdict |
|---|---|---|---|---|
| eqpac | 8.63 (m16w48) / 8.80 (m8w32) | 9.274 | 10/10 (n=10) | **native wins (robust)** |
| midatl | 8.43–8.65 | 8.984 | **5/5** | **native wins (robust)** |
| natlsubpolar | 7.17–7.58 | 7.143 | **0/5** | **native LOSES (robust)** |
| npac | 6.11–6.71 | 6.269 | 2/5 | noisy / no effect |
| sopac | 4.15–5.48 | 4.577 | 3/5 | noisy (PIC artifact) |

Direction is NOT consistent across regimes: native is more accurate in eqpac/midatl, LESS accurate in
natlsubpolar, and indistinguishable in npac/sopac. Resolution has no universal absolute-accuracy sign.

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

## Forecast-horizon decay (per-step rollout skill, existing data)
Resolution gives NO durable multi-step benefit in any regime. Per-step rollout skill native vs 1° m8w32:
eqpac native≈1° (both oscillate ~0); midatl marginal native edge late; sopac native≈1° (both high/rising,
strong seasonal cycle); **npac collapses — native −4.7 at step 6 vs 1° −2.4, i.e. resolution WORSENS the
rollout.** The one-step fine-scale "gain" in npac actively destabilizes multi-step forecasting. Any
resolution effect is a one-month, single-step phenomenon.

## Bottom line
The **one robust, universal result: at matched capacity, finer resolution does NOT raise aggregate
next-month skill-over-persistence in any of the 5 regimes** — the anchor's apparent sharpening was
CAPACITY, and this replicates everywhere. Beyond that, resolution's effect is **regime-idiosyncratic in
sign**: on the common grid native is more accurate in eqpac/midatl, LESS accurate in natlsubpolar, and
noise in npac/sopac; at multi-step horizons it helps nowhere and hurts npac. The naive "finer resolution →
better" intuition is not supported at this scale/horizon for this emulator. The npac contrast remains a
useful diagnostic of predictability scale-locality (large-scale carbon vs fine-scale bio), but is not
evidence of durable resolution skill. The adversarial synthesis + n=5 firm-up + the natlsubpolar control
were each load-bearing in walking back an initial over-read (npac "sharpens", native "wins everywhere").
