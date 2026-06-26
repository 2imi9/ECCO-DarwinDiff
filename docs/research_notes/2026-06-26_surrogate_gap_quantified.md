# Surrogate gap quantified — box vs Darwin at the TRUE Carroll params (2026-06-26)

`scripts/box_vs_darwin_fidelity.py` run locally (5090). No fitting: the 2-layer box is handed
Carroll's *published* parameters and integrated to quasi-steady state; we report, over ocean cells,
the z-scored spatial-pattern correlation `r` (box vs Darwin) per field, and the surface PIC:POC
ratio-of-means. This isolates the **surrogate-fidelity** component of the recovery error from
identifiability and optimization (the self-twin isolates the method; this isolates the proxy).

## Result — z-scored spatial-pattern r (box at Carroll vs Darwin v05, 1°)

| field | eqpac | natlsubpolar | southernoceanpac |
|---|---|---|---|
| Chl1 | −0.26 | 0.07 | −0.34 |
| Chl2 | 0.54 | −0.26 | 0.11 |
| Chl3 | 0.11 | −0.01 | −0.03 |
| Chl4 | 0.11 | nan | nan |
| Chl5 | 0.37 | 0.64 | −0.03 |
| POC | −0.04 | 0.05 | −0.33 |
| PIC | 0.44 | 1.00 | −0.51 |
| FeT | **−0.96** | 0.89 | 0.80 |
| DIC | 1.00 | 0.99 | 1.00 |
| ALK | 1.00 | 1.00 | 1.00 |

(`nan` = the field has ~no variance in that AOI, so correlation is undefined.)

## Result — surface PIC:POC ratio (box at Carroll vs Darwin)

| AOI | box | Darwin | box/Darwin | |
|---|---|---|---|---|
| eqpac | 0.0424 | 0.0332 | 1.28× | OK |
| natlsubpolar | 0.0425 | 0.6758 | 0.06× | MISMATCH |
| southernoceanpac | 0.0424 | 0.0067 | 6.35× | MISMATCH |

## What this refines (numbers, not narrative)

1. **The surrogate gap is large and field-specific.** Carbonate chemistry (DIC, ALK) is reproduced
   almost exactly (r ≈ 1.0); the **phytoplankton (Chl) and POC patterns are essentially uncorrelated**
   even at the true parameters (r in −0.34…0.64). The 0-D box is a good chemistry proxy and a weak
   biology proxy — this is the irreducible surrogate gap, independent of any fitting or resolution.

2. **It explains the loss-weighting finding mechanistically.** eqpac FeT **r = −0.96** — the box's
   equatorial iron pattern is *anti-correlated* with Darwin's. So a z-scored *Darwin-FeT* loss term
   actively pulls the iron parameters the wrong way, and **the only valid iron anchor is real
   GEOTRACES iron (absolute units), not Darwin's pattern.** This is the physical cause behind the
   FIM/profile "loss-weighting, not structural" result (full-loss `alpfe` → 0.103; real-iron → 0.9997).

3. **It re-derives the R_PICPOC regional finding from Darwin's own field.** Darwin's realized PIC:POC
   spans **0.0067 (SO) → 0.68 (natl)**, ~100×, while a single global R_PICPOC = 0.042 is flat by
   construction. A single global scalar **structurally cannot** match the spread — independent of the
   estimator. This is the "R_PICPOC should be regional" point, measured.

## Skeptical check it forces (passes)

We recover the iron pair in eqpac *despite* the box's eqpac iron pattern being anti-correlated with
Darwin's (r = −0.96). That is only consistent because the iron-pair claim rests on **absolute-units
GEOTRACES iron**, not the Darwin FeT pattern. Had we claimed recovery from the Darwin pattern,
r = −0.96 would falsify it. It does not — because we do not. Stated as a guard against over-reading
the Darwin-graded numbers.

## For the manuscript

This is the measured magnitude the 4-cause error decomposition needed: surrogate fidelity is not a
label, it is r ≈ 1.0 for chemistry and r ≈ 0 (or negative) for biology, per AOI. It also strengthens
the "use real, Darwin-independent data" thesis: where the proxy can't reproduce Darwin's pattern
(iron in eqpac; the PIC:POC spread), recovery must and does come from real observations.
