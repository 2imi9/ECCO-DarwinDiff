# R_PICPOC literature survey — does the per-PFT cocco port resolve the last Carroll-6 parameter?

> **⚠ SUPERSEDED FRAMING (2026-06-27).** This survey's goal framing — R_PICPOC as the *"lone unrecoverable Carroll-6 param"* / *"why the 5/6 ceiling holds"* — is **refuted**: R_PICPOC is recoverable with a real calcite anchor (Daniels/MODIS). The survey is retained as a useful **forward-model-fidelity / rain-ratio literature reference**, not as evidence of a recovery blocker. See `../../STATUS.md`.


> ⚠️ **CORRECTION 2026-06-24 (read first).** This survey was built on AOI PIC:POC targets of
> "N Atl ~0.9 / SO ~1.4" taken from `rpicpoc_ratio_structural.md`. A direct recompute from the
> v05 target caches shows those are **wrong**: the real Darwin surface PIC:POC is **eqpac 0.033 /
> N Atl 0.68 / SO 0.0067** (the "0.9/1.4" were a *recovered degenerate* R_PICPOC mislabeled as the
> target). **Consequence:** §2(a) and §3's "SO 1.4 exceeds the 0.8 cocco ceiling → standing-stock →
> unreachable" argument is **REFUTED** — all true targets sit below 0.8, i.e. plain cocco-rain-ratio
> variability that the per-PFT port *can* represent. The validated parts (per-PFT cocco gating is
> source-faithful; identifiability needs a calcite observable; non-cocco calcifiers caveat) still
> stand. Net: the port looks **more** viable than this survey concluded. See the validation-loop
> result + `box_vs_darwin_fidelity.py`.

**Date:** 2026-06-24 · **Scope:** decide how to proceed on R_PICPOC (box learner's lone unrecoverable Carroll-6 parameter) given ADR-0001 (differentiable Darwin calcite port). Grounded in four literature lenses (A: ECCO-Darwin calcite; B: Darwin cocco parameterization; C: PIC:POC variability + alternatives; D: inverse/ML BGC recovery) cross-checked against the repo's own diagnosis (`docs/findings/rpicpoc_ratio_structural.md`, `docs/adr/0001`). Produced by a 5-agent literature workflow.

**Bottom line.** The literature *strongly validates* that Darwin-style spatial PIC:POC variability is carried by a coccolithophore-PFT-specific constant ratio plus community dynamics — exactly the ADR-0001 design (Lens A, B). But the same literature exposes two things the ADR does not fully reckon with: (1) the box's ~23× across-AOI PIC:POC spread (eqpac ~0.033, N Atl ~0.9, SO ~1.4) **cannot be a per-cell rain ratio** — values >0.8 exceed the physiological cocco ceiling (Lens C); it is almost certainly a *standing-stock* concentration ratio, and that target-definition ambiguity is unresolved and load-bearing. (2) Every successful calcite-parameter inversion in the literature is identifiable **only** because it assimilates an alkalinity-derived observable; Carroll's GF target does not, which means a more faithful forward port scored against the *same* carbon-system loss may still not move R_PICPOC's identifiability (Lens D). Recommendation: **proceed with the ADR port, but gate it behind a one-day target-definition + sensitivity check** — the cheapest way to avoid building faithful physics against an under-informative objective.

## 1. Does the literature VALIDATE the per-PFT cocco port? — YES (on the mechanism)
- **Darwin uses a per-PFT, cocco-gated constant ratio.** Dutkiewicz et al. 2015 (*Biogeosciences*, doi:10.5194/bg-12-4447-2015) Table 4: R_rj = **0.8 for Coccol, 0 for the other 8 PFTs**. darwin3 source: `R_PICPOC(nplank)` gated by `hasPIC(nplank)`. This IS ADR-0001 §1a (`R_PICPOC[j]=has_pic[j]*r_picpoc_param[j]`).
- **ECCO-Darwin authors flagged the global scalar as the limitation.** Carroll 2020 (*JAMES*, doi:10.1029/2019MS001888) GF#17: R_PICPOC "likely varies significantly over the global ocean." v05 code moved to the per-PFT array gated to the cocco group.
- **eqpac realized PIC:POC ~0.034 is self-consistent** with cocco-biomass-driven PIC. The structural diagnosis already proved the rigid scalar is the wall (per-cell ratio loss: 10/10 eqpac, 0/10 co-recovery ≥2 AOIs across 25 arms).
- **Caveat:** validation is of the *mechanism*. Whether it reproduces a 23× spread in a 2-layer box *without spatially-resolved cocco biomass* is NOT literature-validated.

## 2. Better / alternative parameterization? — YES, and it exposes the per-PFT-*constant* design
- **(a) The 23× spread cannot be a per-cell rain ratio.** Krumhardt 2017/2019 (doi:10.1016/j.pocean.2017.10.007 / 10.1029/2018MS001483) cap per-cocco PIC:POC at **0.8**; the box's SO ~1.4 and N Atl ~0.9 exceed it → must be community/standing-stock, which the 2-layer box doesn't resolve.
- **(b) Spatial pattern is biomass-driven, not ratio-driven.** Oliver et al. 2024 (*JGR Oceans*, doi:10.1029/2024JC021371): Great Calcite Belt from cocco power-law growth vs Q10 grazing T-curves + dFe. Nissen 2018 (doi:10.5194/bg-15-6997-2018): constant ratio 0.2 + competition → realistic SO export ~0.05.
- **(c) Env-dependent ratio** r=f(T,PO4,CO2) (Krumhardt) is more identifiable but departs from v05's constant chemistry + needs covariate plumbing + still can't reach SO 1.4 if standing-stock.
- **(d) Non-cocco calcifiers.** Buitenhuis 2019 (*GBC*, doi:10.1029/2018GB006110): pteropods ≥33% (to 89%) of shallow CaCO3 export; forams 23–56% (Berelson 2007). Cocco-only port has a structural low bias. Planchat 2023 (doi:10.5194/bg-20-1195-2023): no CMIP5/6 ESM uses an explicit calcifying PFT.
- **Fidelity ladder:** per-PFT constant → +env-dependent ratio → +explicit cocco biomass (growth/grazing T-divergence) → +non-cocco term. ADR sits at the bottom rung — the right *minimal* rung only if the target is the cocco-dominated production/export ratio.

## 3. Observational unlock? — the literature leans "the observation is the unlock," reconcilable with the repo's forward-model finding
- **Every successful calcite inversion needs an alkalinity-derived observable.** Liang 2023 (*GBC*, doi:10.1029/2022GB007535): export/dissolution degenerate, broken only by upper-ocean excess-alkalinity (TA*) structure ⚠(full text paywalled; rests on abstract + Battaglia). Battaglia 2016 (doi:10.5194/bg-13-2823-2016) corroborates TA* as the handle.
- **Carroll's GF target has no calcite-sensitive observable** (pCO2/flux + DIC/Alk/O2 ICs; none isolates calcite from the organic pump).
- **Sensitivity threshold.** Kern 2024 (*GMD*, doi:10.5194/gmd-17-621-2024): params <~1% of max sensitivity are unrecoverable regardless of method. Kriest 2017 (doi:10.5194/gmd-10-127-2017): short-timescale surface-biology params are hardest. → a faithful port scored against the SAME loss may not raise dLoss/dR_PICPOC above the bar.
- **Candidate unlocks:** TA*/excess-alkalinity gradient (GLODAP); satellite surface PIC (Balch two-band MODIS; the repo's shelved `modis_pic_loader.py`/`pace_loader.py`).
- **Reconciliation:** the repo's ratio-loss already supplies a calcite observable (per-cell PIC:POC) and shows R_PICPOC identifiable in eqpac (10/10). Lens D's "observation is the unlock" applies to the carbon-system-only GF objective, which the repo already moved past. Open risk: if SO ~1.4 is standing-stock, neither a better forward model nor the ratio observable suffices — needs the satellite-PIC standing-stock observable to define the target.

## 4. Recommendation — proceed with the port, GATED behind a 1-day target+sensitivity pre-check
**Do NOT redesign the port; do NOT detour into satellite assimilation first.** Per-PFT cocco gating is source-faithful and cheap. But gate it:
1. **Pin the target quantity (hours, highest priority).** Confirm from the v05 loader whether the box's AOI PIC:POC compares against surface PIC/POC **concentration (standing stock)** vs CaCO3:POC **export flux**. SO 1.4 (>0.8 ceiling) + SO/N-Atl > eqpac is the standing-stock/Balch-GCB signature — the *opposite* ordering from the export rain ratio (Sarmiento 2002, doi:10.1029/2002GB001919: max equatorial, global ~0.06). **If standing-stock, the per-PFT-constant port won't reach SO 1.4 by ratio — design for it (resolved cocco biomass and/or accept 0.8 as production cap), don't discover it post-port.**
2. **Sensitivity audit (Kern bar).** Compute dLoss/dR_PICPOC under the current target set; if <~1% of the most-sensitive param, porting alone won't help → add a TA*/satellite-PIC term before the native ≥2-AOI campaign. A clean publishable negative either way.

**Scope additions if the gate passes:** treat regional spread as a biomass/community outcome not a ratio outcome (Oliver/Nissen); caveat the cocco-only low bias (don't let the optimizer inflate cocco to absorb a missing pteropod/foram term); keep multi-AOI joint fits + per-AOI realized PIC:POC as the verification quantity.

**Must-reads (priority):** Oliver 2024; Krumhardt 2017/19; Liang 2023; Kern 2024; Dutkiewicz 2015; Buitenhuis 2019; Sarmiento 2002.

## 5. Evidence-quality flags
1. Liang 2023 full text not retrieved (paywall HTTP 402) — degeneracy claim corroborated by Battaglia 2016 but the upper-ocean-TA* mechanism rests on the abstract.
2. "Box can't reproduce 23× spread" is from the repo's own falsification campaign (25 arms, 0/10), not external lit — literature only explains *why* (0.8 ceiling + biomass-driven pattern).
3. The standing-stock-vs-export target ambiguity is *inferred* (SO 1.4 > 0.8 ceiling; Sarmiento-vs-Balch ordering) — **not yet confirmed against the v05 loader** (gate item 1).
