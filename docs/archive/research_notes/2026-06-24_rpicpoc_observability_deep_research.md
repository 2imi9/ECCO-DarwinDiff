# R_PICPOC observability/mechanism — overnight deep-research synthesis

> **⚠ SUPERSEDED FRAMING (2026-06-27).** This is a point-in-time record; its data and negative results stand, but its framing is corrected by [STATUS.md](../../../STATUS.md) and `docs/research_notes/2026-06-27_box_homogenization_DEFINITIVE.md`. Specifically: **R_PICPOC is NOT a "6/6 wall" and is NOT cluster-gated** — it recovers at 1° box scale given a *real* calcite anchor (Daniels CP:PP / MODIS PIC) plus the `RATIO_MAX=2` fix for the contaminated Southern-Ocean ratio target; the differentiable Darwin calcite port and native resolution were *tested and did not help*. The project is reframed as a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC}; the **growth pair {Smallgrow, Biggrow} is unobservable by construction** (excluded, not failed). The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, tracer CV→1e-15), so box-vs-Darwin spatial-pattern correlations are not fidelity metrics — identifiability comes from real absolute anchors.


**Date:** 2026-06-24 (overnight) · **Status:** LITERATURE SYNTHESIS, decision-ready
(no experiment run). Feeds issue [#143](https://github.com/2imi9/ECCO-DarwinDiff/issues/143)
("spine D: R_PICPOC observational/mechanistic retry — calcite port refuted") and the
`forward-model-fidelity-roadmap` thread.

> **How this was produced.** A `deep-research` workflow fanned out 5 search angles →
> 20 primary sources → 90 extracted claims → adversarial 3-vote verification on the top
> 25. It **hit the Claude.ai monthly spend limit mid-verification**, which crashed most
> verifier votes and the automatic synthesis step. I (main agent) wrote the synthesis by
> hand and reconciled it against our own internal findings
> (`docs/findings/rpicpoc_ratio_structural.md`, `docs/findings/alk_anchor_rpicpoc_mutex.md`).
> **Read the confidence tags literally:**
> - ✅ **VERIFIED** — survived adversarial verification (3-0 or 2-1).
> - ◻️ **EXTRACTED** — direct quote from a fetched primary source but the verifier
>   crashed on the spend limit before voting (`0-0, 3 abstain`). **Not** refuted — just
>   unconfirmed. Treat as a strong lead, not a settled fact.
> - ❌ **REFUTED** — failed verification (0-3); excluded from the argument.

---

## TL;DR — the verdict

**The problem is primarily MISSING-MECHANISM, not missing-observation — and specifically
it's a missing *environmental gating* of the rain ratio, not a missing calcifier PFT.**

We already proved internally that the **estimator/observation side is solvable**: the
PIC:POC **ratio** loss identifies R_PICPOC orthogonally to the iron pair (eqpac 10/10,
no iron collapse). What blocks ≥2-AOI recovery is that the box's calcite is a **rigid
readout** — `PIC_1/POC_1 = R_PICPOC` *everywhere* — while the real/Darwin realized rain
ratio varies regionally by a large factor. No new observable fixes a forward model that
*cannot represent the spread in the first place*. So the fix is to give the forward model
the spread, by the cheapest route the BGC-modeling field already uses: make the rain
ratio a smooth function of environment.

### Ranked by (identifiability gain × tractability in a differentiable box)

| Rank | Option | Identifiability gain | Tractability | Net |
|---|---|---|---|---|
| **1** | **(3) Environment-dependent rain ratio** `R_PICPOC = f(T, Ω_c/CO₂, PO₄, light)` | **High** — directly creates the regional spread the box lacks; standard practice in CESM/PISCES/CMIP; pairs with our existing ratio loss as the orthogonal observable | **High** — a smooth differentiable function of state variables the box already carries; **no new PFT, no new tracer** | **Best** |
| 2 | (2) TA* / excess-alkalinity loss | Medium *in principle* — real-ocean CaCO₃ observable — **but in OUR box collapses to the same `R_PICPOC × mort_total` product as PIC** (see internal ALK null), so it's gated on the same forward-model fix | Medium — TA* recipe is differentiable-friendly, but absolute-ALK anchor already shown IC-dominated & degenerate | Complement to #1, not a standalone fix |
| 3 | (4) Minimal coccolithophore bloom mechanism | Medium-High — would create real regional spread via a calcifier PFT | **Low** — needs a new PFT + temperature/grazing niche dynamics; regional dominance is **top-down (grazing) controlled**, harder to fit; and CMIP shows explicit calcifiers are **not required** to get the spread | Reserve; only if #1 underfits |
| 4 | (1) Satellite PIC observable (MODIS/PACE) | **Low where it matters** — ✅ confirmed unreliable in the Southern Ocean / high latitudes (>25× overestimate; diatom-silica artifact), and the alkalinity rain-ratio pattern points at the *wrong* regions | High (tooling already built: `modis_pic_loader.py`, `pace_loader.py`) | **Deprioritize** |

> **This inverts the planned priority.** `next.md` ranked satellite PIC #1 ("highest EV;
> tooling already built"). The verified evidence says satellite PIC is the **weakest**
> option in exactly the regions (SO/high-lat) where our target is lowest and recovery is
> hardest. Tooling-built ≠ scientifically informative.

---

## Reconciliation with our own prior findings (the key value-add)

The external literature does **not** contradict our internal work — it explains *why* our
internal results came out the way they did, and it points past the wall.

**1. Our ratio loss already solved the estimator side (eqpac 10/10).**
`docs/findings/rpicpoc_ratio_structural.md`: at steady state `PIC_1/POC_1 =
R_PICPOC·(W_SINK/W_SINK_PIC)`, so `mort_total` cancels and the ratio observable pins
R_PICPOC orthogonally to the iron pair. It recovers R_PICPOC **only in eqpac**, because
the box's calcite is a single-`mort_total` rigid readout while Darwin's realized ratio
varies regionally. **→ The literature confirms the regional spread is real and large**
(see Option 3), so the residual wall is genuinely forward-model fidelity, exactly as we
concluded. The estimator is not the bottleneck.

**2. Our absolute-ALK anchor was a NULL — and this directly down-weights Option 2.**
`docs/findings/alk_anchor_rpicpoc_mutex.md`: the box's surface ALK is calcite-only
(`dALK_1 = −2·R_PICPOC·mort_total`), so it shares PIC's *exact* factorization and is
informationally equivalent to PIC for the R_PICPOC/`mort_total` split; it's also
IC-dominated (calcite moves ALK ~0.17%), making the absolute-ALK signal ~60,000× weaker
than PIC. The apparent co-recovery was a cell-weighted **straddling artifact**.
**→ Critical caveat for Option 2:** the TA* literature is about disentangling *real-ocean*
alkalinity (preformed + remineralization + calcite). **Our box's ALK has no preformed/
remin/riverine structure** — it is *already* a pure calcite signal. So computing TA* on the
box adds nothing; a TA*/ALK target still constrains the same `R_PICPOC × mort_total`
product. **Option 2 is gated on the same forward-model fix as everything else** — it only
becomes independently informative once the forward model carries a richer (environment- or
PFT-resolved) calcite budget. Until then it reproduces the ALK null.

**3. The target was re-scaled this session.** The 2026-06-15 finding used the old SO ratio
(~1.4); the corrected Darwin targets are **eqpac 0.033 / natl 0.68 / SO 0.0067**. The
North Atlantic is the high-rain-ratio (coccolithophore-bloom) region; the Southern Ocean is
*low*. This matters because it aligns with the alkalinity-derived rain-ratio literature
(Option 3) and against the satellite-bloom pattern (Option 1) — see below.

---

## Option 1 — Satellite PIC (MODIS / PACE): **DEPRIORITIZE**

The strongest *verified* result of the whole run is that satellite PIC fails precisely
where we need it.

- ✅ **VERIFIED (3-0):** MODIS PIC catastrophically **overestimates true (in-situ) PIC south
  of the Antarctic Polar Front by >25×**, where sample PIC averaged only ~15 nM.
  *(agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2024EA004070)*
- ✅ **VERIFIED (3-0):** the SO overestimation is a **non-carbonate artifact** — heavily
  silicified colony-forming diatoms (*Fragilariopsis*, *Pseudo-nitzschia*) produce anomalous
  backscatter/birefringence that the PIC algorithm misreads as calcite. *(same source)*
- ✅ **VERIFIED (3-0):** MODIS PIC and coccolith-based PIC are **decoupled south of the
  Polar Front** — satellite shows high PIC where no coccolithophores were observed.
  *(bg.copernicus.org/articles/22/3143/2025)*
- ✅ **VERIFIED (3-0):** satellite PIC is overestimated in Antarctic waters because high
  reflectance also comes from **suspended sediment and opal/diatom-frustule fragments**.
  *(same)*
- ✅ **VERIFIED (2-1):** authors conclude satellite PIC is **unreliable south of the Polar
  Front**; in-situ measurements are needed. *(same)*
- ◻️ **EXTRACTED:** the alkalinity-derived rain-ratio pattern **contradicts** the satellite
  coccolithophore-bloom pattern — blooms cluster at high latitudes, yet the highest export
  ratios are at low latitudes (low-latitude non-bloom calcifiers, i.e. foraminifera/pteropods,
  dominate global calcification). *(gfdl.noaa.gov/bibliography/related_files/jls0201.pdf —
  inferred Sarmiento et al. 2002, GBC)*

**Read:** even setting aside our target re-scaling, satellite PIC is contaminated by
diatom silica in the SO and structurally points at the wrong regions for rain-ratio
constraint. The built loaders (`reference_satellite_pic_loaders.md`) are not wasted — they
remain useful for low-latitude bloom regions — but satellite PIC is **not** the lever that
unblocks the regional spread. Keep shelved.

---

## Option 2 — TA* / excess alkalinity from GLODAP: **complement, not a standalone fix**

- ✅ **VERIFIED (3-0):** TA* is a constructed tracer isolating the CaCO₃-dissolution imprint
  on alkalinity: `TA = TA0 + TAr + TA*`, with `TA0 = a0 + a1·S + a2·T + a3·PO`
  (PO = O₂ + 170·PO₄) and `TAr = 1.26·(16/170)·AOU`. A concrete, differentiable-friendly
  recipe. *(bg.copernicus.org/preprints/12/20223/2015 — inferred Battaglia et al. 2016, GBC)*
- ✅ **VERIFIED (weak, 1-1):** CaCO₃ **dissolution** parameters are hardly constrained by
  TA* or current flux compilations — models with and without saturation-dependent
  dissolution both achieve skill. *(same)* → alkalinity is a *weak* constraint on dissolution
  mechanism.
- ◻️ **EXTRACTED:** real-ocean CaCO₃ signal in surface alkalinity is **not regionally flat** —
  near-constant at low latitudes, strong poleward increase (~−110 µmol/kg SO / subarctic
  N Pacific). *(sciencedirect S0304420315001073)*
- ◻️ **EXTRACTED:** a **salinity-normalized alkalinity (sAlk) vertical-gradient emergent
  constraint** links the alkalinity field to PIC export across ESMs (44–55 Tmol/yr at 100 m).
  *(bg.copernicus.org/articles/20/1195/2023)*
- ◻️ **EXTRACTED:** the CaCO₃:Corg export ratio can be estimated from **vertical gradients of
  potential alkalinity + sAlk-nitrate alone**, without absolute transport magnitudes.
  *(gfdl jls0201.pdf)*
- ❌ **REFUTED (0-3):** a specific "0.82 GtPIC/yr global pelagic export" figure — excluded.

**Read:** TA* is a legitimate real-ocean observable and its *vertical-gradient* form (sAlk)
carries genuine export information — better than the *absolute* ALK anchor we already nulled.
**But** (per internal finding #2) our box's ALK is calcite-only and IC-dominated, so any
ALK/TA* target still constrains `R_PICPOC × mort_total` and reproduces the null **until the
forward model is enriched**. Sequence it *after* Option 3: once the rain ratio varies with
environment, a TA*-gradient loss becomes an independent cross-check rather than a degenerate
restatement of PIC. The dissolution-constraint weakness (1-1) further argues TA* informs
*export/dissolution*, not surface *production* rain ratio — which is what we're after.

---

## Option 3 — Environment-dependent rain ratio: **THE RECOMMENDED FIX**

This is the missing mechanism, and it is *standard practice* in production ocean BGC models.

- ◻️ **EXTRACTED:** in **CESM**, the coccolithophore calcification-to-organic ratio (realized
  PIC:POC) is an explicit function of **aqueous CO₂, phosphate limitation, and temperature** —
  not a uniform mean rain ratio. *(agupubs 2018MS001483 — inferred Krumhardt et al., JAMES)*
- ◻️ **EXTRACTED:** making the rain ratio environment-dependent produces **large regional
  spread** in calcification (N Atlantic, W Pacific, parts of SO increase under rising CO₂ via
  relief of carbon limitation). *(same)* → directly the regional spread our box lacks.
- ◻️ **EXTRACTED:** realized PIC:POC parameterized as a **saturating (Michaelis-Menten)
  function of calcite saturation Ω_c**: `(PIC/POC)_max = 0.8`, half-saturation `K = 0.4`,
  fit to *E. huxleyi* data with **r² = 0.92**. *(bg.copernicus.org/articles/4/505/2007 —
  inferred Ridgwell et al. 2007)* → a concrete, drop-in differentiable form.
- ◻️ **EXTRACTED:** across **CMIP5/CMIP6** ESMs, implicit pelagic calcification (the rain
  ratio) is a function of nutrients (PO₄/NO₃/Fe/Si), temperature, light, depth, and Ω_c.
  *(bg 20/1195/2023)*
- ◻️ **EXTRACTED:** **no CMIP5/6 ESM explicitly represents a calcifying PFT** — all treat
  calcification implicitly, yet still reproduce regional PIC:POC spread. *(same)* → **strong
  argument that Option 3 ≫ Option 4 on cost/benefit**: you do not need a coccolithophore PFT
  to get the spread.
- ◻️ **EXTRACTED:** the rain ratio varies strongly and systematically by region — equatorial
  max, smaller in subtropical/subpolar/high-lat (Atlantic eq 0.084 vs subpolar 0.023 vs SO
  0.020; Pacific eq 0.087 vs subtropics 0.045). *(gfdl jls0201.pdf)* → observed spread is real
  and large-amplitude.

**Read & concrete design.** Replace the constant `R_PICPOC` with a smooth gating function
of state variables the box already carries, e.g. a Ridgwell-style saturating form
`R_PICPOC(cell) = R_max · Ω_c/(Ω_c + K) · g(T) · h(nutrient)`, or the CESM `f(CO₂, PO₄, T)`
form. The **free parameters of `f(env)` become the new recovery targets**, and our existing
**ratio loss** (already orthogonal to the iron pair) supplies the identifying observable.
This is the highest (gain × tractability): it injects the missing spread, needs no new PFT
or tracer, is differentiable by construction, and slots into the lever we've already built.

---

## Option 4 — Minimal coccolithophore bloom mechanism: **reserve**

- ◻️ **EXTRACTED:** in ROMS-BEC (Southern Ocean), coccolithophore-vs-diatom dominance is set
  primarily by **top-down (grazing) control**, not growth-rate differences — specific grazing
  differences are 2× (40–50°S) to 8× (50–60°S) larger than growth-rate differences.
  *(bg.copernicus.org/articles/15/6997/2018 — inferred Nissen et al. 2018)*
- ◻️ **EXTRACTED:** coccolithophores do both PIC and POC and thereby set the water-column
  rain ratio. *(agupubs 2022JG007355)*

**Read:** a faithful calcifier PFT would create real regional spread, but it's the **most
expensive** path — it requires a new PFT plus temperature/grazing niche dynamics, and the
regional signal is **top-down controlled**, which is exactly the hard-to-fit part. Combined
with the CMIP result that explicit calcifiers are *not required*, Option 4 is overhead for
the identifiability goal. Hold it in reserve for the differentiable-Darwin port endgame
(`differentiable-full-darwin-regional` thread), not for unblocking R_PICPOC now.

---

## Recommended next step (for tomorrow's decision)

1. **Implement Option 3** behind a default-OFF flag (`RPICPOC_ENV` or similar) in
   `carroll6_5pft_2layer.py`: make `R_PICPOC` a Ridgwell-style saturating function of Ω_c
   (and optionally T, PO₄), with `Ω_c` derived from the box's existing carbonate state.
2. **Pre-register a forward-model probe first** (as we did for the ALK null): confirm the
   gated `R_PICPOC(env)` actually produces an AOI spread matching the corrected targets
   (eqpac 0.033 / natl 0.68 / SO 0.0067) *before* running the optimizer — i.e. test that the
   mechanism *can* make the spread.
3. **Fit with the existing ratio loss** (`RATIO_W>0`, cocco off) across the 3 AOIs; score
   **per-AOI** (the straddling-artifact lesson). Success = R_PICPOC-controlling env params
   Cal-grade in ≥2 AOIs without iron-pair collapse.
4. **Only then** add a TA*-gradient (sAlk) cross-check (Option 2) as independent confirmation.
5. Treat Options 1 & 4 as out-of-scope for this retry.

**Answer to the central question, in one line:** *missing-mechanism — specifically a missing
environmental gating of the rain ratio; the estimator and a workable observable already
exist, but the box's rigid single-ratio calcite cannot represent the regional spread that
both Darwin and the real ocean exhibit.*

---

## Verification ledger

- **Pipeline:** 5 angles → 20 primary sources → 90 claims → top 25 verified.
- **Outcome:** 7 confirmed (✅), 1 genuinely refuted (❌, the 0.82 GtPIC/yr figure),
  ~17 crashed-to-abstain (◻️, unconfirmed — spend limit), synthesis step crashed.
- **Caveat:** every ◻️ claim is a verbatim quote from a fetched primary source but was **not**
  adversarially checked. The four-option *ranking* rests on (a) the ✅ satellite-PIC failures,
  (b) the ✅ TA* recipe + weak-dissolution-constraint, and (c) our own internally-verified
  ratio-loss and ALK-null findings — the ◻️ Option-3 claims are corroborating, not load-bearing.
  Re-run the verification + synthesis once the spend limit resets to upgrade the ◻️ tier.

### Sources (all primary unless noted)

| # | URL | Inferred ref | Used for |
|---|---|---|---|
| 1 | agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2024EA004070 | — (Earth & Space Sci, 2024) | ✅ SO satellite PIC >25× overestimate; diatom-silica artifact |
| 2 | bg.copernicus.org/articles/22/3143/2025 | — (Biogeosciences, 2025) | ✅ MODIS/coccolith PIC decoupling S of PF |
| 3 | bg.copernicus.org/preprints/12/20223/2015 | Battaglia et al. 2016 (GBC) | ✅ TA* recipe; weak dissolution constraint; ❌ 0.82 GtPIC/yr |
| 4 | sciencedirect.com/.../S0304420315001073 | — (Marine Chemistry, 2015) | ◻️ Alk* poleward gradient; Alk* recipe |
| 5 | aslopubs.onlinelibrary.wiley.com/doi/full/10.1002/lol2.10457 | — (L&O Letters) | ◻️ potential-alk & Ca as SO CaCO₃ tracers |
| 6 | agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2018MS001483 | Krumhardt et al. (JAMES) | ◻️ CESM r-ratio = f(CO₂, PO₄, T) |
| 7 | bg.copernicus.org/articles/4/505/2007 | Ridgwell et al. 2007 | ◻️ M-M rain ratio on Ω_c (r²=0.92) |
| 8 | bg.copernicus.org/articles/20/1195/2023 | — (Biogeosciences, 2023) | ◻️ CMIP5/6 implicit calcification; sAlk emergent constraint; no explicit calcifier PFT |
| 9 | agupubs.onlinelibrary.wiley.com/doi/10.1029/2022JG007355 | — (JGR Biogeosciences) | ◻️ coccolithophores set rain ratio |
| 10 | gfdl.noaa.gov/bibliography/related_files/jls0201.pdf | Sarmiento et al. 2002 (GBC) | ◻️ rain ratio from PA+NO₃ gradients; regional values; bloom-pattern contradiction |
| 11 | bg.copernicus.org/articles/15/6997/2018 | Nissen et al. 2018 | ◻️ SO cocco/diatom top-down grazing control |

---

## DRAFT comment for issue #143 (NOT posted — for review)

> **Overnight deep-research synthesis (literature, decision-ready).** Full note:
> `docs/research_notes/2026-06-24_rpicpoc_observability_deep_research.md`.
>
> **Verdict: primarily missing-MECHANISM — specifically a missing *environmental gating* of
> the rain ratio, not a missing calcifier PFT or a missing observation.** The estimator side
> is already solved (ratio loss, orthogonal to the iron pair) and a workable observable
> exists; the wall is that the box's rigid `PIC/POC = R_PICPOC` calcite cannot represent the
> regional spread both Darwin and the real ocean show.
>
> **Ranked fixes (gain × tractability):**
> 1. **Environment-dependent rain ratio** `R_PICPOC = f(Ω_c, T, PO₄)` — standard in
>    CESM/PISCES/CMIP; concrete differentiable form exists (Ridgwell M-M on Ω_c, r²=0.92);
>    no new PFT/tracer; pairs with our existing ratio loss. **← do this.**
> 2. TA*/sAlk-gradient loss — real observable, but in our calcite-only box collapses to the
>    same `R_PICPOC × mort_total` product (cf. the ALK null); useful as a cross-check *after* #1.
> 3. Minimal coccolithophore PFT — creates real spread but most expensive (top-down/grazing
>    controlled); CMIP shows explicit calcifiers aren't required. Reserve.
> 4. **Satellite PIC — deprioritize.** ✅ verified unreliable in the SO/high-lat (>25×
>    overestimate; diatom-silica artifact) and the alkalinity rain-ratio pattern points at the
>    wrong regions. This inverts the earlier "satellite PIC is highest-EV" plan.
>
> Proposed next step: implement #1 behind a default-OFF flag, **pre-register a forward-model
> probe** that the gated ratio reproduces the corrected targets (eqpac 0.033 / natl 0.68 /
> SO 0.0067) before fitting, then fit with the ratio loss scored **per-AOI**.
>
> Caveat: the research run hit a spend limit mid-verification — 7 claims adversarially
> confirmed (incl. all the satellite-PIC failures + the TA* recipe), the rest are
> source-quoted but unverified; re-verify when the limit resets.
