# v05-vs-MODIS chlorophyll — recompute with the fixed MODIS binning (2026-07-21)

PR #189 (commit `ac8af55`) fixed a half-cell shift in the MODIS→v05 bin edges
(`compare_v05_modis_aoi.py`: edges must bracket the AOI cell *centers* by half a cell, not
use the centers as edges). The commit noted the documented bias/correlation numbers were
produced with the old binning and needed recomputing. Recomputed here from the local
`C:/Users/Frank/dd_chl_val` MODIS-Aqua + v05 data (2003–2018).

## Before (old binning) → after (fixed binning)

| AOI | metric | old | fixed |
|---|---|---|---|
| **eqpac** | bias (dex) | −0.0773 | **−0.0759** |
| | bias factor | 0.837× | 0.840× |
| | r all-months | +0.0339 | +0.0315 |
| | r anomaly | +0.3307 | +0.3285 |
| | coverage mean / min | 0.986 / 0.909 | 0.986 / 0.908 |
| **natl** | bias (dex) | −0.6959 | **−0.6973** |
| | bias factor | 0.201× (5.0× low) | 0.201× (5.0× low) |
| | r all-months | +0.7794 | +0.7805 |
| | r anomaly | +0.0440 | +0.0470 |
| | coverage mean / min | 0.785 / 0.015 | 0.786 / 0.018 |

n_months unchanged (eqpac 192, natl 176).

## Verdict — the binning bug was cosmetic; every conclusion stands

The fix moves every headline number by **< 0.003** (bias ~0.001 dex, anomaly r ~0.003). The
regime-split story is fully robust:

- **eqpac** is unbiased in the oligotrophic regime (−0.076 dex, 0.84×, **inside** the 0.130
  dex MODIS noise floor); interannual anomaly r = **+0.329** (the skill number; all-months
  r = +0.032 is just the absent seasonal cycle).
- **natl** is **5.0× low** in the bloom (−0.697 dex, 0.201×); all-months r = +0.78 is a
  shared seasonal cycle, anomaly r = +0.047 is near-zero.

The committed `docs/findings/chl_val/v05_vs_modis_{eqpac,natlsubpolar}.json` are updated to the
fixed-binning values. The eqpac interannual/ENSO and lag diagnostics depend on the anomaly
series, which moved negligibly (r_anom +0.331→+0.329), so those findings are unaffected.
