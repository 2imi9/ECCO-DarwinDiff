# DarwinDiff — Project Status

*Living doc. Update as things ship.*

**Last updated:** 2026-05-09 (after PRs #21 / #22 / #23 / #24 merged to main).

## Where we are in one line

Track 1 (parameter recovery) at **v1.3** — Carroll-6 recovery demonstrated against real ECCO-Darwin v5 output across 3 targets (Chl, NO₃, FeT) and 3 basins (Mid-Atl, N Pacific, Eq Pacific). Structural-ceiling argument holds in every fit. Track 2 (neural emulator) not started.

## Most important findings so far

| # | Finding | Evidence |
|---|---|---|
| 1 | **Carroll 2022 inherited Carroll 2020's calibrated values bit-for-bit.** No re-tuning between Darwin 1 → Darwin 3 / v04 → v05. | `references/ecco_darwin/v04/llc270_JAMES_paper/code_darwin/{darwin_init_fixed.F, darwin_generate_phyto.F}` + `v05/llc270/input/data.darwin`. All 6 numbers match. |
| 2 | **Structural-ceiling argument is universal.** Global-scalar Green's-functions class produces a constant prediction (`r = undefined`) in every fit. DINN per-cell finds a non-trivial r in every fit. | nb09–14, every notebook with a head-to-head section. |
| 3 | **N Pacific NO₃ is the strongest single-fit result.** DINN per-cell `r = 0.979`, loss ratio Global/DINN = **23.8×**. | nb13 |
| 4 | **Cross-basin parameter consistency** — Carroll-6 recovered values are stable across basins (within ~25% of each other). Same systematic biases vs Carroll's optima in every basin. Suggests box-model proxy creates basin-independent biases (not random fitting noise). | nb11, nb13 |
| 5 | **`alpfe` converges on Carroll's published 0.928** as we use targets that better constrain the iron pair. nb14 global-scalar fit on Eq Pacific FeT recovers `alpfe = 0.959` (3% off Carroll). | nb14 |
| 6 | **Best target depends on basin physics**, not just on Carroll's calibration choices. Mid-Atl: Chl r=0.72 > NO₃ r=0.61. N Pacific: NO₃ r=0.98 > Chl r=0.97. | nb11 vs nb13 |

## Headline results table

| Notebook | AOI | Target | DINN r | Loss ratio Global/DINN |
|---|---|---|---|---|
| nb09 | Mid-Atl | GLODAP −NO₃ (proxy) | 0.691 | 1.71× |
| nb10 | Mid-Atl | Darwin Chl | 0.724 | 1.81× |
| nb11 | Mid-Atl | Darwin Chl | 0.724 | 1.81× |
| nb11 | N Pacific | Darwin Chl | 0.966 | 14.6× |
| nb13 | Mid-Atl | Darwin −NO₃ | 0.607 | 1.27× |
| **nb13** | **N Pacific** | **Darwin −NO₃** | **0.979** | **23.8×** |
| nb14 | Eq Pacific | Darwin FeT | 0.337 | 1.13× |

## Done — checklist

### Code

- [x] `src/darwindiff/carroll6.py` — 5-tracer box model, integrator, `bounded_params`, Carroll 2020/2022 published values, parameter bounds
- [x] `src/darwindiff/networks.py` — DINN per-cell (1×1 conv) + DINNRegional (MLP)
- [x] `src/darwindiff/diagnostics.py` — `safe_pearson_r` + `format_pearson` (NaN-safe; constant-pred detection)
- [x] `src/darwindiff/budget.py` — compute / memory budget calculators
- [x] `src/darwindiff/ecco_darwin_loader.py` — bin_average product (1° NetCDF) loader + AOI presets + chl_total + ocean_mask
- [x] `src/darwindiff/llc270_loader.py` — native LLC270 mds tile loader (xmitgcm-based, multi-iter safe)
- [x] **96 tests passing** (1 opt-in real-data integration via `DARWINDIFF_TEST_LLC270=1`)

### Notebooks (all on main)

- [x] **05** — scalar Carroll-6 recovery from synthetic
- [x] **06** — ML vs Green's-functions head-to-head, synthetic two-regime
- [x] **07** — 2-D per-cell on synthetic 128×128
- [x] **08** — pre-ORCD scoping doc
- [x] **09** — methodology demo on real GLODAP NO₃ proxy
- [x] **10** — Carroll-6 recovery against real Darwin Chl in Mid-Atl (Track 1 v1.0)
- [x] **11** — cross-basin Mid-Atl + N Pacific Chl (Track 1 v1.1)
- [x] **12** — LLC270 loader infrastructure
- [x] **13** — cross-basin Mid-Atl + N Pacific NO₃ (Track 1 v1.3)
- [x] **14** — iron-pair recovery via FeT in Eq Pacific (Track 1 v1.2)

### Data on disk (D:\, outside repo)

- [x] `D:\ecco_darwin_v5\bin_average\v05_ECCO-Darwin_bin_average_1x1_deg.nc` (1.74 GB, 23 yr monthly, surface)
- [x] `D:\ecco_darwin_v5\grid\` (494 MB, LLC270 grid metadata for xmitgcm)
- [x] `D:\ecco_darwin_v5\output\monthly\` — 13+ tracers ~50 GB each (ALK, Chl1-5, DIC, DOC, DOFe, DON, DOP, FeT, NH4, NO2, NO3 done; O2 in progress; O2_flux, PAR, PIC, POC, PO4, SiO2 queued)
- [x] `C:\Users\Frank\Downloads\ECCO-Darwin_CO2_flux_*.tif` — 36 monthly GeoTIFFs from NASA GHG Center (CO₂ flux only, for future validation)
- [x] `data/glodap/` — GLODAPv2.2016b mapped climatology (1.4 GB, used by nb09)
- [x] `references/ecco_darwin/` — full MITgcm-contrib Darwin source code (2 GB shallow clone, gitignored)

### Decisions / scope locked

- [x] Active target = Carroll 2022 / Darwin 3 / v05 (not Carroll 2020 / Darwin 1 / v04, even though calibrated values are identical)
- [x] AOIs = Mid-Atlantic + North Pacific + Equatorial Pacific (all three implemented as presets in `ecco_darwin_loader.AOI`)
- [x] Box model stays as 5-tracer carroll6 proxy (no carbonate chem, no 5 PFTs) for Track 1; extension is a future scope decision
- [x] Earthdata account active; ECCO Drive + NASA NAS portal both accessible

## In progress / next

### Ready to start (no new data needed)

- [ ] **nb15** — multi-tracer joint loss (NO₃ + Chl + DIC + FeT simultaneously). Should improve weakest fits (Mid-Atl NO₃, Eq Pacific FeT) by giving DINN multiple loss surfaces.
- [ ] **nb16** — multi-covariate DINN input (SST + MLD + windspeed + lat). Should push iron r above 0.337 and Mid-Atl NO₃ r above 0.607.
- [ ] Re-execute nb09 to refresh outputs (cleared at v0.95 closeout, never re-run).

### Gated on data / setup

- [ ] Wait for monthly/ wget to fully complete (O2_flux, PAR, PIC, POC, PO4, SiO2 still pending)
- [ ] Box-model extension to add DIC + ALK + carbonate chem → can then fit Darwin's CO₂ flux directly (most direct Carroll 2022 reproduction; the GHG Center COG files are already on disk for validation)
- [ ] Time-resolved fitting (use all 285 monthly snapshots, not just climatology) — opens Track 2 emulator territory

### Collaboration / external

- [ ] Email Jonathan/Mick with consolidated nb10–14 results — strongest claim is N Pacific NO₃ r=0.979 + cross-basin parameter consistency
- [ ] ORCD pitch revision incorporating real-Darwin recovery results
- [ ] Eq Pacific AOI confirmation with Jonathan (we proposed 5°S–15°N, 160°W–110°W; may want to adjust)

## Open questions

- **Why does Mid-Atl NO₃ underperform Mid-Atl Chl?** (0.61 vs 0.72 — opposite of N Pacific where NO₃ wins.) Hypothesis: Mid-Atl NO₃ pattern is dominated by Gulf Stream + mesoscale eddy structure that SST-only DINN can't capture; Chl is more directly SST-coupled. Multi-covariate input (nb16) should test this.
- **Iron-pair `scav_rat` identifiability** — recovered values are 1.8–2.8× off Carroll's 6.03e-7 in every fit, even when `alpfe` recovers within 3%. Consistent with literature view that surface iron observations alone underconstrain scavenging; need depth-resolved iron + POC export.
- **Box-model bias structure** — recovered Carroll-6 means show same systematic offsets vs Carroll in every basin (alpfe ~0.5–0.7×, scav_rat ~2–3×, Smallgrow ~1.4×, Biggrow ~2.6×, R_PICPOC ~2×). Suggests box-model simplification has predictable effects that could be calibrated out, not random noise.

## Where everything lives

| Item | Location |
|---|---|
| Code | `src/darwindiff/`, `tests/` |
| Notebooks | `notebooks/` |
| Findings docs (chronological) | `docs/findings/2026_05_02.md`, `docs/findings/2026_05_08.md` |
| Decision log | `docs/research_log.md` |
| External references (PDFs, Darwin source) | `references/` (gitignored content) |
| Real Darwin data | `D:\ecco_darwin_v5\` (outside repo) |
| Public Darwin data download script | wget command in project memory; output goes to `D:\` |

## Tests

```
PYTHONPATH=src python -m pytest tests/ -q
# 96 passed, 1 skipped
```

To run the opt-in real-LLC270 integration test:
```
PYTHONPATH=src DARWINDIFF_TEST_LLC270=1 python -m pytest tests/test_llc270_loader.py
```
