# ECCO-Darwin v05 chlorophyll vs MODIS-Aqua — first observational comparison (2026-07-19)

**The first time this project has compared anything biological against the real ocean.** Every prior
Track-2 number was self-consistency against the v05 model.

This is also **novel for ECCO-Darwin itself**: chlorophyll is not evaluated at all in the official
135-figure v05 evaluation white paper, which covers fCO₂ / NO₃ / PO₄ / SiO₂ / O₂ / DIC / alkalinity
against SOCAT / GLODAP / BGC-Argo. This is a finding about *their* model, not about our emulator.

---

## Headline

| | |
|---|---|
| Region / period | subpolar N. Atlantic (50–65°N, 40–10°W), **2003-01 → 2018-11** |
| Months compared | **176** |
| **Bias** | **−0.696 dex = 0.20× — v05 is ~5× LOW** |
| RMSE | 0.912 dex |
| r (log₁₀, all months) | 0.779 — **but see the caveat below, this is not skill** |
| MODIS retrieval noise floor | 0.130 dex — the bias **exceeds it by 5×** |

The comparison was only possible because of the `delta_t` calendar fix made earlier the same day. On
the uncorrected axis this analysis produced a flat climatology "peaking" in October and a meaningless
bias of −0.721 dex with r = −0.059.

---

## The structure matters more than the headline

| Month | v05 − MODIS (dex) | coverage | reading |
|---|---|---|---|
| Feb | −1.669 | 62% | v05 ~47× low |
| Mar | −1.628 | **98.5%** | v05 ~42× low |
| Apr | −1.012 | **99.5%** | v05 ~10× low |
| **May** | **−0.079** | 99.0% | **within noise floor** |
| **Jun** | **+0.032** | 97.9% | **within noise floor** |
| Jul | −0.487 | 97.5% | v05 3× low |
| Aug | −0.751 | 98.9% | v05 6× low |
| Sep | −0.568 | 99.5% | v05 4× low |
| Oct | −0.260 | 93.5% | v05 2× low |

**v05 reproduces the bloom peak almost exactly and misses everything else.** In May and June the
model sits inside the satellite's own retrieval uncertainty. Outside that two-month window it is
between 2× and 47× too low.

Two specific structural errors follow:

1. **The pre-bloom deficit is real, not a sampling artifact.** March and April are 98.5% and 99.5%
   observed — the best-covered months in the record — and v05 is 42× and 10× low there.
2. **The bloom ends too early.** v05 peaks in **June**; MODIS peaks in **August**. The observed
   productive season is broad and late-summer-sustained; v05's is a sharp early spike that collapses.

---

## Robustness

The bias survives coverage filtering, which is the confound most likely to have produced it:

| coverage threshold | n | bias (dex) | r |
|---|---|---|---|
| ≥ 0% (all) | 176 | −0.696 | 0.779 |
| ≥ 30% | 144 | −0.713 | 0.845 |
| ≥ 50% | 143 | −0.706 | 0.841 |
| ≥ 70% | 129 | −0.605 | 0.784 |
| ≥ 90% | 125 | **−0.601** | 0.782 |

Restricting to the best-observed months moves the bias from −0.696 to −0.601 — it shrinks slightly
and remains ~4.5× low. Only January (4.6% coverage) and November (12.7%) are genuinely blind, and
excluding them does not change the conclusion.

The clipping of v05 values below MODIS `valid_min` (159,014 cell-months) **raises** v05, so it makes
the reported bias *conservative* — the true deficit is somewhat larger.

---

## The correlation is seasonal, not skill — do not quote r = 0.78 bare

Within the **growing season only** (May–Sep, the best-observed and most physically meaningful window):

> **r = 0.016**, n = 80

v05 has **essentially zero correlation with MODIS interannual variability**. The headline r = 0.779
across all months is almost entirely "both fields have a spring bloom" — it measures agreement on the
*existence of a seasonal cycle*, not on which years were productive.

This is the same failure mode as the persistence baseline in the emulator work: a number that looks
like skill but is carried by a signal both sides trivially share. **Any report of r = 0.78 must carry
the growing-season r = 0.016 alongside it.**

---

## Caveats that cannot be fixed in this version

- **Optical-depth mismatch.** MODIS `chlor_a` is weighted over roughly the first optical depth; v05
  `surfChl` is the top model cell. In a stratified summer with a deep chlorophyll maximum these differ
  systematically, and the sign of that mismatch (satellite sees a shallower, often higher-Chl layer)
  runs in the *same direction* as the measured bias. It cannot explain a 42× March discrepancy under
  deep winter mixing, but it plausibly contributes to the summer numbers.
- **Diel sampling.** Aqua overpasses ~13:30 local; v05 output is a daily mean.
- **Processing version.** ERDDAP `erdMH1chlamday` serves `processing_version 2018.1QL`, not the
  current OB.DAAC R2022.0.
- **One region.** eqpac was downloaded but not analysed. The subpolar N. Atlantic is bloom-dominated
  and was chosen as the more informative regime; an oligotrophic check is the obvious next step.

---

## What this is worth

For the collaborator conversation this is the strongest material we have: it is about **their** model,
it is **novel** (chlorophyll is unevaluated in their own white paper), it is **quantitative**, and it
is **structured** — the model gets bloom magnitude right and bloom *duration* and *background level*
wrong, which is a mechanistic clue rather than a bare score.

It is also **time-limited**: v06 adds `pkg/RadTrans`, an ocean-colour forward operator, at which point
the ECCO-Darwin group can do this comparison natively and better.

Provenance: `C:\Users\Frank\dd_chl_val\` — `compare_v05_modis.py`, `v05_vs_modis_natlsubpolar.json`,
`fig_v05_vs_modis.png`, `natlsubpolar_monthly_fixed.npz` (v05 on the corrected calendar,
`cal_ratio = 4/3`), `natl_{2003..2018}.nc` (MODIS via NOAA CoastWatch ERDDAP, no authentication).
