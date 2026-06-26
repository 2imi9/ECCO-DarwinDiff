# R_PICPOC (PIC:POC rain ratio) vs real-ocean observations — does ECCO-Darwin's 0.042 match?

**Date:** 2026-06-26 · **Spine:** D (#143) / C (#116) · **Status:** deep-research (11 agents,
every value source-verified). Triggered by the real-data audit (real MODIS PIC only weakly
constrains R_PICPOC) + the question "is ECCO-Darwin's calcite param actually grounded in real
data, or did we miss a discrepancy?". ECCO-Darwin value: `R_PICPOC = 0.04245` (`carroll6.py:75`).

## 1. Is the rain ratio observationally constrained? YES, loosely (factor ~2)

Direct/inverse methods measure the production-or-export RATIO (alkalinity/nitrate drawdown), which
surface MODIS PIC (a standing stock) cannot. Best real-ocean **global-mean export rain ratio**:

| source | method | value |
|---|---|---|
| Sarmiento 2002 (GBC 10.1029/2002GB001919) | alkalinity/nitrate inverse, 100 m | **0.06 ± 0.03** (everywhere <0.10) |
| Daniels 2018 (ESSD 10.5194/essd-10-1859-2018) | ¹⁴C CP:PP incubation, n=2751 | **0.02** geomean (production; log-normal 0.001–1) |
| Battaglia 2016 (BG 10.5194/bg-13-2823-2016) | TA*-constrained Bern3D | export → **~0.07** |
| Planchat 2023 (BG 10.5194/bg-20-1195-2023) | obs-derived | **0.14** upper; CMIP5 0.070 / CMIP6 0.083 |
| Jin 2006 (GBC 10.1029/2005GB002532) | nutrient+alk inverse | **0.09** (0.07–0.10) |

**Honest band: ≈0.06 (0.03–0.09), factor-of-2 uncertainty.** The legacy 0.20–0.25 (Li 1969) is a
remineralization-ratio misinterpretation, not part of the modern envelope.

## 2. Does ECCO-Darwin's 0.042 match? Within-uncertainty but biased LOW; regionally wrong

- **0.042 is BELOW every verified global-mean central estimate** (0.056–0.09) — ~0.6σ low vs
  Sarmiento, inside the 1σ envelope but ~25–30% below center.
- **Carroll never tuned R_PICPOC to rain-ratio data.** Carroll 2020 (10.1029/2019MS001888) optimized
  6 BGC params by Green's functions against pCO2 / CO2-flux / alkalinity / nitrate / oxygen — NO
  rain-ratio dataset. So 0.042 is tuned for CO2/DIC closure; grading our recovery against Darwin's
  own PIC is circular. It is NOT disconnected from data (lands in the post-2002 consensus), but it
  is under-constrained and low.

## 3. Two discrepancies the surface-MODIS test was blind to

(a) **Low-side magnitude tension.** Surface PIC is a standing stock; it can only reject HIGH values
(our flat MODIS profile over [0.005,0.05]). The direct export inversions pull the center UP to
0.06–0.09 — a real low-side model-vs-obs tension the stock test masked.

(b) **THE LOAD-BEARING FINDING — R_PICPOC should be REGIONAL, not a global constant.** Sarmiento
2002 Table 3: rain ratio peaks EQUATORIALLY (Indian 0.099 / Pacific 0.087 / Atlantic 0.084),
minimum in Southern Ocean/gyres (0.003–0.02) — >20–30× regional range, and the equatorial-max is
OPPOSITE the high-latitude coccolithophore-bloom pattern. **eqpac is DarwinDiff's constraining AOI,
and the true eqpac rain ratio is ~0.087 (Sarmiento) to 0.13–0.22 (Wanninkhof) — 2–5× ABOVE the
global 0.042.** So ECCO-Darwin's single global constant is wrong for the very region we constrain it
in, and a global scalar cannot be uniquely identified against a regional AOI. **This structural
mismatch — not the global magnitude — is the real scientific result for spine D.**

**Non-discrepancy (don't over-read):** deep sediment-trap PIC:POC of 0.5–1.7 (Wynn-Edwards 2020) is
12–40× higher but is the depth/ballast gradient (POC remineralizes, CaCO3 survives) — apples/oranges
vs a surface-production ratio.

## 4. CO2 significance

The rain ratio drives `dALK = -2·R_PICPOC·mort_total` → air-sea CO2 (carbonate counter-pump).
Calcification leverage spans 9–285 PgC ocean uptake / 4–70 ppm atmospheric (Gangstø/Heinze
lineage) — feedback ranges, order-of-magnitude direction only, but a factor-2 rain-ratio error is
NOT carbon-neutral. Getting it right (and region-resolving it) matters for the simulated sink.

## 5. The test to run

Wire **Daniels 2018 CP:PP incubations (PANGAEA 888182)** as the primary, Darwin-INDEPENDENT,
per-AOI R_PICPOC anchor — the only direct surface production-ratio dataset matching the box's
`dPIC = R_PICPOC·mort_total` in kind; n=2751 georeferenced points → eqpac-vs-global targets,
breaking the circularity and directly testing the regional-variability hypothesis. Knowable to
~factor-2 only (log-normal); Daniels reports no clean latitudinal trend in raw incubations, so the
regional signal may be noisier than Sarmiento's inverse pattern.

## Bottom line

ECCO-Darwin's R_PICPOC is under-constrained, ~25–30% low vs the best inverse estimates, and — the
real result — **structurally mis-specified as a single global constant when the true rain ratio is
2–5× higher in eqpac (our constraining AOI).** This is a finding ABOUT ECCO-Darwin (the field's
best model still carries an under-constrained, globally-constant rain ratio), surfaced by the
differentiable tool — not a failure of our recovery. Recovery = ours (works); real-world validity =
ECCO-Darwin's (here it's weak + regional).
