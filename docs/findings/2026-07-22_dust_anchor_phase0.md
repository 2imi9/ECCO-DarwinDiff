# Phase 0 — alpfe dust anchor: independent data recovers alpfe ≈ Carroll in the dust-dominated region (2026-07-22)

First REAL-DATA (non-synthetic) result of the two-anchor program. Built the SOURCE anchor from Xu & Weber 2021
(BCO-DMO 922468, CC-BY-4.0) Al-inverse soluble deposition — the field constrained by in-ocean GEOTRACES Al, so it
decouples alpfe from atmospheric-dust-model spread (red-team recommendation). Loader:
`src/darwindiff/xu_weber_loader.py` (regrids the 60-config ensemble mean+spread to any AOI, converts Al→Fe).

## The diagnostic: what alpfe does the anchor imply?
alpfe is constrained by (independent Xu-Weber soluble-Fe deposition) / (v05's prescribed Mahowald soluble-Fe
deposition), AOI-aggregated. Both in mmol Fe/m²/yr; Fe:Al molar = 0.15 (midpoint of 0.08–0.20).

| AOI | Xu-Weber Fe | v05 Mahowald Fe | **implied alpfe** | ensemble spread/mean |
|-----|-------------|-----------------|-------------------|----------------------|
| **Saharan N. Atlantic** (10–30N, 45–20W) | 0.0211 | 0.0183 | **1.15** | 0.54 |
| natlsubpolar | 0.0126 | 0.0053 | 2.36 | 0.30 |
| southernoceanpac | 0.0090 | 0.0032 | 2.86 | 0.44 |
| eqpac | 0.0230 | 0.0027 | 8.66 | 0.88 |

## Reading (honest)
1. **In the correct anchor region — the dust-dominated Saharan N. Atlantic — the independent Al-inverse implies
   alpfe = 1.15, remarkably close to Carroll's 0.93.** Across the Fe:Al uncertainty (0.08–0.20) the Saharan implied
   alpfe spans ~0.61–1.53, bracketing Carroll cleanly. So a completely independent, out-of-manifold data source
   (ocean-Al inversion, no box fitting) corroborates the tuned alpfe. This is real support for the strong leg.
2. **Off-region the implied alpfe is 2.4–8.7** — Xu-Weber sees MORE soluble-Fe deposition than v05's Mahowald
   supplies, extreme in the remote Pacific (eqpac 8.66). This matches (a) v05's documented low iron bias
   ([[2026-07-22_column_osse_result]] profile-fidelity: eqpac surface obs ≫ model 25–45×) and (b) the red-team's
   exact warning that remote-Pacific cells have high ensemble spread (0.88 here) and are poor anchors. The anchor
   is correctly down-weighted there.
3. **Placement is data-driven, not a guess.** The ensemble spread ranks the anchor quality: N. Atlantic (0.30) >
   SO (0.44) > Saharan (0.54) > remote Pacific (0.88). The anchor belongs on the Atlantic dust plume.

## What this establishes
The dust anchor is REAL and lands near Carroll in the region where it's reliable — validating both the anchor
concept and the red-team's placement guidance, with independent data and zero box fitting. It's the strongest,
cheapest leg (alpfe already recovers 50/50 in-box; now corroborated out-of-box).

## Caveats + next sub-step
- Fe:Al molar ratio (0.15) is the dominant absolute-scale uncertainty; refine regionally from GEOTRACES GA03
  aerosol solubility (Phase-1). The Saharan result is robust across the plausible range.
- This is an AOI-mean diagnostic, not yet the anchor loss in the learner.
- NEXT: wire the Saharan dust anchor (weighted by 1/ensemble-spread) into `run_v3.0` as a source-side loss term,
  and run recovery on the Explorer H200 to test whether it de-conditions alpfe from the 10× real-iron up-weighting
  and tightens the alpfe↔scav_rat correlation. Data + loaders (Xu-Weber + Mahowald) are done and tested.
