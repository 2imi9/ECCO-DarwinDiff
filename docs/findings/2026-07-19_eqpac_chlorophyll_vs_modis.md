# v05 chlorophyll vs MODIS-Aqua — equatorial Pacific (2003–2018)

The oligotrophic counterpart to [the subpolar N. Atlantic comparison](2026-07-19_v05_chlorophyll_vs_modis.md).
Same method, same satellite product, same corrected calendar (`delta_t = 1200 s`). Script:
[`scripts/compare_v05_modis_aoi.py`](../../scripts/compare_v05_modis_aoi.py) (which reproduces the
Atlantic numbers exactly as a regression check — see §5).

**Headline: v05 chlorophyll is essentially unbiased in the equatorial Pacific, and its interannual
variability there is ENSO — captured at ~89% of the observed sensitivity but with the response
arriving about three months too early.**

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

## 4. NEW — a ~3-month phase error in the ENSO response

Lag scan of chlorophyll anomaly against Niño-3.4 (lag > 0 means chlorophyll *lags* ENSO):

| lag (mo) | −4 | −3 | **−2** | −1 | 0 | **+1** | +2 | +4 |
|---|---|---|---|---|---|---|---|---|
| v05 | −0.622 | −0.669 | **−0.680** | −0.648 | −0.546 | −0.348 | −0.168 | +0.041 |
| MODIS | −0.395 | −0.464 | −0.538 | −0.612 | −0.664 | **−0.666** | −0.641 | −0.550 |

- **MODIS peaks at lag +1** — chlorophyll responds one month *after* the SST anomaly. Physically
  expected: SST/upwelling anomaly → nutrient supply change → biological response with a delay.
- **v05 peaks at lag −2** — modelled chlorophyll *leads* Niño-3.4 by two months.

That is a **~3-month phase error**, and by lag +2 the two have diverged almost completely (v05
−0.168, MODIS −0.641).

**Interpretation (hypothesis, not established).** ECCO-Darwin's physical state is data-constrained,
and in ENSO dynamics thermocline-depth anomalies *lead* the Niño-3.4 SST peak. If v05's biology
tracks modelled upwelling essentially instantaneously, it will inherit that lead, whereas real
phytoplankton add biological inertia — growth timescales, grazing adjustment, community succession —
that delays the observed response. In short, **v05 may be missing a biological response timescale**,
not a physical one.

That is a testable and directly relevant hypothesis for the UDE track: the missing quantity is a
*rate*, which is exactly the kind of term a learned closure is positioned to supply. It should not
be stated as established until it is tested — e.g. by lag-scanning v05's own modelled nutrient or
upwelling fields against its chlorophyll to see whether the lead originates in the physics or in the
biological response to it.

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
