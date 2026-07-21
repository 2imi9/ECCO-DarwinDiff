# v05 chlorophyll vs MODIS-Aqua — equatorial Pacific (2003–2018)

The oligotrophic counterpart to [the subpolar N. Atlantic comparison](2026-07-19_v05_chlorophyll_vs_modis.md).
Same method, same satellite product, same corrected calendar (`delta_t = 1200 s`). Script:
[`scripts/compare_v05_modis_aoi.py`](../../scripts/compare_v05_modis_aoi.py) (which reproduces the
Atlantic numbers exactly as a regression check — see §5).

**Headline: v05 chlorophyll is essentially unbiased in the equatorial Pacific, and its interannual
variability there is ENSO — captured at ~89% of the observed sensitivity, but its response is
offset from the satellite's by ~2 months (v05 leads Niño-3.4, MODIS lags it). The offset is
statistically resolvable; its cause is not established, and the "missing biological rate"
explanation given in an earlier draft is withdrawn (§4).**

---

## 1. The two regimes are completely different

| | subpolar N. Atlantic | equatorial Pacific |
|---|---|---|
| months | 176 | **192** (full record) |
| bias | **−0.696 dex (5.0× low)** | **−0.077 dex (0.84×)** |
| 95% CI on bias | [−0.787, −0.617] | [−0.090, −0.064] |
| vs 0.130 dex noise floor | **EXCEEDS** | **INSIDE** |
| RMSE | 0.912 dex | **0.122 dex** |
| satellite coverage | 78.5% mean, 1.5% min | **98.6% mean, 90.9% min** |
| v05 cells clipped below `valid_min` | 159,014 | **0** |
| r (all months) | +0.779 | +0.034 |
| r (deseasonalised anomaly) | +0.044 | **+0.331** |

The equatorial Pacific is the **best-observed** data in the whole comparison — 98.6% mean coverage,
never below 90.9%, no clipping — and it is where v05 does **well**. The `−0.696 dex` Atlantic deficit
is not a global chlorophyll bias. It is regime-specific, and the bloom regime is where the model is
wrong.

---

## 2. The headline correlation is unreliable in *both* directions

This is the methodological point, and it is stronger than the one the Atlantic result alone
supported.

| | r (all months) | r (anomaly) | what r_all did |
|---|---|---|---|
| subpolar N. Atlantic | +0.779 | +0.044 | **flattered** — inflated by a shared seasonal cycle |
| equatorial Pacific | +0.034 | +0.331 | **maligned** — deflated by the absence of one |

In the Atlantic, `r = 0.78` looks like skill and is almost entirely "both fields have a spring
bloom." At the equator, `r = 0.03` looks like total failure and hides a real ENSO signal, because
there is barely a seasonal cycle for the two series to agree on (MODIS seasonal amplitude is
**0.081 dex**).

So the all-months Pearson r is not merely optimistic — it is **uninformative**, biased in whichever
direction the regime's seasonality happens to push it. **Report the deseasonalised anomaly r.** It is
regime-independent, unlike a growing-season window (May–Sep is meaningless at the equator).

The earlier "growing-season r = 0.016" result for the Atlantic still stands and is corroborated by
the anomaly r of +0.044 computed the general way.

---

## 3. The equatorial skill is marginal on its own — the mechanism is what makes it real

**Do not quote `r_anomaly = +0.331` as a solid result.** Monthly chlorophyll anomalies are heavily
autocorrelated (lag-1: v05 +0.770, MODIS **+0.908**), so the effective sample size is **34, not 192**:

- t = 1.98, p ≈ **0.048**
- moving-block bootstrap (12-month blocks) 95% CI **[+0.050, +0.577]**
- phase-randomised surrogate null, 95th percentile |r| = 0.330 vs observed **0.3307**

It clears every threshold by a hair. Taken alone this is a marginal result.

What makes it real is that it decomposes cleanly by ENSO phase, against the **downloaded NOAA PSL
Niño-3.4 index** (`nina34.anom.data`), not a hand-listed set of events:

| subset | n | r(v05, MODIS) |
|---|---|---|
| ENSO-active (\|N3.4\| ≥ 0.5) | 98 | **+0.524** |
| neutral (\|N3.4\| < 0.5) | 94 | **−0.052** |
| strong (\|N3.4\| ≥ 1.0) | 33 | +0.839 *(n_eff ≈ 6 — indicative only)* |

v05's equatorial interannual skill **is ENSO and nothing else**. In neutral months it has literally
zero skill. That also explains why the aggregate is marginal: it is a mixture of genuine signal in
half the months and noise in the other half — an aggregate concealing a two-population structure,
the same shape as `r_all` concealing the seasonal cycle.

### Sensitivity is close to right

Regressing each field's chlorophyll anomaly directly on Niño-3.4:

| | r | slope (dex per °C) |
|---|---|---|
| v05 | −0.546 (n_eff 29, p = 6.8e−4) | **−0.0300** |
| MODIS | −0.664 (n_eff 14, p = 2.6e−3) | **−0.0338** |

Correct sign (El Niño suppresses equatorial upwelling and productivity) and **v05 captures 0.89× the
observed sensitivity**. Both survive the effective-N correction.

---

## 4. NEW — a ~2-month timing difference in the ENSO response (measurement is robust; interpretation is not)

Lag scan of chlorophyll anomaly against Niño-3.4 (lag > 0 means chlorophyll *lags* ENSO):

| lag (mo) | −4 | −3 | **−2** | −1 | 0 | **+1** | +2 | +4 |
|---|---|---|---|---|---|---|---|---|
| v05 | −0.622 | −0.669 | **−0.680** | −0.648 | −0.546 | −0.348 | −0.168 | +0.041 |
| MODIS | −0.395 | −0.464 | −0.538 | −0.612 | −0.664 | **−0.666** | −0.641 | −0.550 |

- **MODIS peaks at lag +1** — chlorophyll responds one month *after* the SST anomaly. Physically
  expected: SST/upwelling anomaly → nutrient supply change → biological response with a delay.
- **v05 peaks at lag −2** — modelled chlorophyll *leads* Niño-3.4 by two months.

By lag +2 the two have diverged almost completely (v05 −0.168, MODIS −0.641).

### Is it resolvable? Yes — tested three ways

The lag curves are broad and both series are heavily autocorrelated (n_eff ≈ 14–34), so an argmax
difference could easily be sampling noise. It is not. Moving-block bootstrap, 24-month blocks
(preserving ENSO-band autocorrelation), 4000 resamples:

| test | result |
|---|---|
| bootstrap CI of each peak lag | v05 **[−3, −1]**, MODIS **[0, +2]** — **do not overlap** |
| bootstrap of the difference | median **−2.0 mo**, 95% CI **[−4, −1]**, P(diff < 0) = **0.977** |
| smooth asymmetry `D = r(+1) − r(−2)` | v05 **+0.332**, MODIS **−0.128**, difference **+0.460**, 95% CI **[+0.246, +0.710]**, P(>0) = **1.000** |

The third test is the one to quote: it is a smooth statistic that never takes an argmax on a flat
curve, so it is immune to the failure mode that makes the first two fragile.

**Correction to an earlier draft of this document, which said "~3-month phase error."** The
full-sample argmax difference is 3 months (−2 vs +1), but the *bootstrap median difference is 2
months*, 95% CI [1, 4]. The honest figure is **~2 months (95% CI 1–4)**, not 3. The 3 was a
point estimate from an argmax on a broad curve — exactly the statistic the third test exists to
avoid.

Artifact: `chl_val/eqpac_lag_resolvability.json`.

### Interpretation — the "missing biological rate" reading is WITHDRAWN

An earlier draft of this document explained the offset as v05 "missing a biological response
timescale": modelled biology tracking upwelling instantaneously and inheriting the thermocline lead,
while real phytoplankton add growth/grazing inertia. **That is refuted and is withdrawn.**

A literature pass (2026-07-19) established:

- **The intrinsic phytoplankton adjustment timescale is 1–7 days** (Shi & Wang 2021), not months. A
  multi-month offset therefore **cannot** be a growth or grazing rate in either direction. This kills
  the mechanism outright, independently of everything else.
- **Documented equatorial-Pacific chlorophyll leads are driven by iron *supply*** — thermocline depth
  and Equatorial Undercurrent iron advection (Lim et al. 2022 GRL) — i.e. a *transport* timescale,
  not a biological one.
- **Our AOI is the wrong region for the "lead" literature.** The documented lead is a western/central
  near-equatorial (2°S–2°N) feature. Our box is **eastern and off-equatorial (−5..15°N)**, where the
  observational literature instead reports that chlorophyll responds only weakly and near-linearly to
  ENSO (Tian et al. 2021 ERL; Chen et al. 2023). **Our MODIS +1 is consistent with that**, which
  means **v05's −2 is the number requiring explanation, not MODIS.**
- **Park et al. 2018 GRL does not say what an earlier draft implied.** Its lead is an
  event-composite sign-reversal delay of chlorophyll vs *SST* in the **western/central** Pacific, not
  a cross-correlation peak against Niño-3.4, and the study is model-weighted (its own subtitle: *"An
  Earth System Modeling Study"*). **It was paywalled and has not been read first-hand** — the
  "1.5–3 month" figure reaches us only via Tian et al. 2021/2025. Do not cite it as a first-hand
  number.

The cleanest available comparison, Tian, Zhang & Wang 2025 (J. Climate), reports chlorophyll vs
Niño-3.4 at **zero lag**: r = −0.78 (western 2°S–2°N) and −0.45 (eastern). No published peak-lag
exists for a box like ours, so our MODIS +1 cannot be checked against a literature value — but it is
not a red flag either.

### What we can say

**v05 and MODIS disagree in phase within an identical AOI, index and period, and the disagreement is
statistically resolvable (§ above).** That is a model–observation discrepancy worth reporting. We do
**not** currently have a supported mechanism for it.

**The most promising remaining hypothesis is iron supply, not biology** — which is unusually relevant
here, since iron-cycle parameters (`alpfe`, `scav_rat`) are exactly what Track 1 recovers. If v05's
equatorial iron supply responds to thermocline displacement too promptly, that would produce an early
chlorophyll response through a transport pathway with a plausible multi-month timescale, unlike a
growth rate. **Untested.**

### Two caveats on our own setup, flagged by the same pass

- **Index-vs-SST convention mismatch.** We correlate against the Niño-3.4 *index*; the cited studies
  correlate against local SST *responses*. Related, not identical.
- **Index-vs-SST convention** (above) remains untested.
- **AOI geometry — TESTED, and the offset is NOT an artifact of it.** Our box is asymmetric about the
  equator (−5..15°N) and is not the box the lead literature uses. We cannot build a true 5°S–5°N box
  (the data starts at −5°N), but splitting the existing box into an equatorial band and an
  off-equatorial band and recomputing gives:

  | band | bias (dex) | v05 peak lag | MODIS peak lag | asymmetry difference `D_v05 − D_MODIS` |
  |---|---|---|---|---|
  | full (−5..15°N) | −0.077 | −2 | +1 | **+0.460** |
  | equatorial (−5..5°N) | −0.114 | −3 | **0** | **+0.344** |
  | off-equatorial (5..15°N) | −0.038 | −1 | +5 | **+0.221** |

  **The v05-more-lead-like asymmetry survives in both bands** (both `D` differences positive), so it
  is a property of the model's ENSO response, not of our box choice. Its *structure* does vary: in
  the equatorial band v05 leads most strongly (peak −3) against a near-zero-lag MODIS, while in the
  off-equatorial band v05 is nearly symmetric (peak −1) and MODIS lags strongly (peak +5, plausible
  for an indirect subtropical teleconnection).

  **An independent corroboration falls out of this.** In the equatorial band **MODIS peaks at exactly
  lag 0** — which is what Tian, Zhang & Wang (2025) report for equatorial boxes (zero-lag r = −0.45
  eastern, −0.78 western). Our satellite pipeline reproduces the published lag structure where a
  published value exists, which is the strongest available check that the MODIS side is sound and
  that **v05's lead is the anomaly**.

  The bias is also band-dependent (−0.114 equatorial vs −0.038 off-equatorial), so the headline
  −0.077 dex is a mix; both remain inside the 0.130 dex noise floor.
  Artifact: `chl_val/eqpac_latband_lag.json`.

### Secondary: the seasonal cycle is over-expressed and anti-phased

- v05 amplitude **0.221 dex**, MODIS **0.081 dex** → v05 over-expresses by **2.7×**
- v05 peaks August, MODIS peaks March; climatology correlation **−0.287**

The absolute amplitude is small enough that this barely affects the bias, but the sign is wrong.

---

## 5. Regression check

`compare_v05_modis_aoi.py` was run on `natlsubpolar` before eqpac and reproduces the committed
2026-07-19 numbers exactly: n = 176, bias −0.6959 dex, r_all +0.7794, growing-season r +0.0160.
The generalisation did not perturb the original result.

---

## 6. Caveats

Inherited from the Atlantic comparison, all unchanged:

- **Optical-depth mismatch** — MODIS `chlor_a` is weighted over ~the first optical depth; v05
  `surfChl` is the top model cell. In the permanently stratified equatorial Pacific a deep
  chlorophyll maximum is the norm, so this caveat is arguably *stronger* here than in the Atlantic.
  It runs in the direction of making v05 look low.
- **Diel sampling** — Aqua overpasses ~13:30 local; v05 output is a daily mean.
- **Processing version** — ERDDAP `erdMH1chlamday` serves `processing_version 2018.1QL`, not the
  current OB.DAAC R2022.0.

New here:

- **Low effective degrees of freedom.** Every correlation in this document has n_eff between ~6 and
  ~44 despite n = 192. Quote n_eff alongside any r from this analysis.
- **The ENSO phase-error interpretation is a hypothesis.** The lag *measurement* is data; the
  "missing biological timescale" explanation is not yet tested.

---

## 7. Artifacts

| file | contents |
|---|---|
| `scripts/compare_v05_modis_aoi.py` | the per-AOI comparison (committed) |
| `C:\Users\Frank\dd_chl_val\v05_vs_modis_eqpac.json` | full monthly series + robustness table |
| `C:\Users\Frank\dd_chl_val\eqpac_enso_diagnostics.json` | ENSO sensitivity, phase split, lag scan |
| `C:\Users\Frank\dd_chl_val\eqpac_anomaly_diagnostics.json` | effective-N, bootstrap, surrogate null |

Niño-3.4 source: NOAA PSL `nina34.anom.data`, downloaded 2026-07-19.

---

## 8. What changed in the overall picture

The Atlantic result alone read as "v05 chlorophyll is 5× low." With eqpac that becomes **"v05
chlorophyll is unbiased in the oligotrophic regime and 5× low in the bloom regime"** — a more
specific and more useful statement about *where* the model fails, and one that points at bloom
dynamics rather than at a global scaling error.

For external validation this is a second independent region with a quantified, mechanism-backed
result, and it is the region where the observations are strongest.
