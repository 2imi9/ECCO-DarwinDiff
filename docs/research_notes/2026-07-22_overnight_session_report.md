# Overnight session report — 2026-07-22

Good morning. Here is everything from the overnight run, most important first. All compute ran on the
AICR B200 (H200/Explorer was open but not provisioned with our code or data, and the 5090 stayed off so
you could sleep). Every recovery number below is `verify_run.py` exit 0.

## The headline: your "add more environment" idea worked, and it landed `diatomgraz`

We changed the DINN size and the patch overlap before and both failed. Adding environment did not.

Adding **MLD** as a per-cell DINN input channel (the network was SST only) recovers `diatomgraz`
**10/10**, up from 3/10 with SST alone. This was the one parameter we had been calling "not recovered on
real data." The reason is clean and physical: with SST only, the Southern Ocean cell sits at ~0.18 (Carroll
is 0.83), so only the equatorial Pacific recovers. MLD is the deep-winter-mixing signal the Southern Ocean
needs, and it lifts that cell to ~0.68, so all three regions recover. The effect repeats with wind and with
MLD+wind, so it is real, not seed luck.

So the miss was practical, an input problem, not a structural one. The lever is different from size and
overlap: those change capacity, this adds information.

**But it is not "turn everything on."** It is parameter specific and there are real trade-offs:

| param | SST (baseline) | +MLD | +wind | +MLD+wind | +full |
|---|---|---|---|---|---|
| alpfe | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |
| scav_rat | 0/10 | 0/10 | 0/10 | 2/10 | 0/10 |
| R_PICPOC | 6/10 | 5/10 | **0/10** | 0/10 | 0/10 |
| diatomgraz | 3/10 | **10/10** | 10/10 | 10/10 | 7/10 |

- Wind, salinity, pCO2, and CO2-flux **break** `R_PICPOC` (its median blows up to 5 to 9 times Carroll).
- **MLD alone is the safe channel.** It recovers `diatomgraz` with no damage to the others.
- `scav_rat` stays at 0. Covariates do not help the sink leg. It needs the Phase-2 sink anchor (234Th flux
  plus export partition), which is the separate iron-observing-system work.

Recommended operating point: **geo1 plus the MLD channel only**. That takes us from three recoverable
observables to a fourth.

I ran one control to be honest about the mechanism. A pure per-region location channel (AOI_ID, no MLD)
recovers `diatomgraz` only 6/10, versus MLD's 10/10. So MLD is partly a regional signal, but it is
substantially physical too: the real mixing-depth field beats a bare region label by 4 seeds. The location
channel also breaks `R_PICPOC`, while MLD does not, so MLD really is the sweet spot, not just any extra input.

One honest caveat: `diatomgraz` recovers against the biogenic-silica (POSi) target, not a full silicate
cycle. The clean structural confirmation is a profile-likelihood on `diatomgraz` with the MLD channel on.
That is the recommended next experiment, and it is now well motivated. Do not re-label `diatomgraz` as
fully "identifiable" until that runs.

Details: [covariate-channels result](../findings/2026-07-22_covariate_channels_result.md). STATUS,
issue #152, and project memory are updated. Code: new env flags `MLD_CHANNEL`, `WIND_CHANNEL`,
`SSS_CHANNEL`, `PCO2_CHANNEL`, `CO2FLUX_CHANNEL` in `run_v3.0` (default off is bitwise-identical to the
old SST-only baseline, which we re-ran and confirmed).

## ECCO-Darwin v06 research

v06 exists but is not released. The team lead (Hong Zhang, JPL) said in February it is "still in
optimization," and the only public product is still v5. So **keep building on v05.** v06 lives as source in
the MITgcm-contrib repo, still on the LLC270 grid, run window extended to 1992 to 2024.

The one v06 change that matters for us: it adds **hydrothermal-vent iron forcing**, a third iron input
beside dust solubility (`alpfe`) and scavenging (`scav_rat`). A deep, fixed-location iron source adds
spatial structure the 0-D box averages away, so it could shift or break the alpfe / scav_rat degeneracy we
have been mapping. That is a future consideration, not a task now. Other additions (river runoff, a sediment
model, a spectral-optics package that is the machinery for ocean-color / PACE assimilation) all broaden the
environment in the direction the covariate result above already points.

Full sourced note: [v06 research](2026-07-22_ecco_darwin_v06_research.md). Every claim has a URL; the gaps
(no released parameter values, no v06 paper) are called out honestly.

## Figures

1. **Architecture & Method, v2** (`docs/figures/tikz/architecture_method_hero_v2.tex`, sent to you). Redone in
   the two-panel style of the OlmoEarth teaser you shared. Left panel is a stylised globe with the 3 AOIs and
   a (lat,lon) pin, the v05 field stack, the real-anchor thumbnails, and the covariate stack. Right panel is
   the differentiable loop with the one-backward-pass hero and the verified dashboard. Compiles; PDF and SVG
   generated. I kept the earlier single-panel version too. The environment node now carries the full verified
   covariate set (I dropped "velocity" — it is not a Track-1 forcing).
2. **Emulator on a 2D globe** (`docs/figures/emulator_globe_chl1.png`, sent to you). A real run, not a mock.
   The FNO emulator's global next-month chlorophyll prediction, on an orthographic globe (land comes free from
   the ocean mask). Aggregate skill vs persistence is +0.664 (verdict MAKE), but persistence is the wrong
   yardstick — against a per-cell seasonal AR(1) baseline the emulator shows no significant skill (retracted
   2026-07-23) — and the honest per-cell story is
   in the skill map: positive in the high-variability regions (North Atlantic, Southern Ocean, equatorial
   upwelling) and negative in the gyres where persistence is already near-perfect. Plotter is
   `scripts/plot_emulator_globe.py`. The global cube is portable (`--dump-cube`), so re-running is cheap.

## Other collected results

- **Dust-anchor A/B, n=10** (from the earlier session, closed overnight): the small n=5 `R_PICPOC` uptick was
  seed noise. `alpfe` stays 10/10 and is now principled (grounded in the Xu & Weber inversion). `scav_rat`
  stays 0. See `docs/findings/2026-07-22_dust_anchor_ab_b200.md`.
- **diatomgraz dilution-grazing diagnostic**: closed negative and honestly. The grazing-rate idea is sound but
  the box lacks the grazer structure, and the profile did not bracket. Separately, the covariate result above
  is the path that actually moved `diatomgraz`. See
  `docs/findings/2026-07-22_diatomgraz_realgraze_diagnostic.md`.

## Compute and housekeeping

- **B200 was the workhorse.** It was queue-jammed at first (400+ pending) but backfilled the jobs, and all
  the covariate arms and the emulator training ran and finished. H200/Explorer had idle nodes but no repo,
  no venv, and no data, so provisioning it would have cost more than it saved tonight. The 5090 stayed off.
- **Real-box geometry self-twin**: done (it took four tries — too slow/noisy on the 5090, a 1-hour B200
  timeout, then finished at n=20/600 with a longer limit). Good news: the two-anchor design breaks the
  alpfe/scav_rat degeneracy *geometry* in the real box. `|ρ(alpfe,scav)|` drops 0.472 (baseline) → 0.195
  (dust source, which matches the analytic prediction of ~0.20) → 0.089 (scav sink) → 0.061 (both), and the
  break is conditional on pinning the export partition (both-pinned 0.061 vs both-free 0.131 — the "partition
  tax"). Honest caveat: this is a self-twin, so `scav_rat` is already 20/20 at baseline (self-consistent
  anchors) — it validates the identifiability *geometry*, not real-data recovery, which still needs real
  234Th/210Po data (Phase 2). Details: `docs/findings/2026-07-22_realbox_geometry_result.md`.
- STATUS, the two-anchor plan, issues #152 and #187, and project memory are all updated.

## Suggested next steps (your call)

1. Profile-likelihood on `diatomgraz` with the MLD channel, to confirm the recovery is structural.
2. Protect `R_PICPOC` while keeping `diatomgraz`: try MLD only, or MLD plus an up-weighted Daniels anchor.
3. If you want the v2 figure in the manuscript, I can wire it in with `\includestandalone` (the manuscript
   is local-only, so I did not touch it without you).
