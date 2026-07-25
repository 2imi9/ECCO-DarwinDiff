# Data-source scan: GHG Center ECCO-Darwin CO2-flux + Earthmover marketplace

Date: 2026-07-23
Scope: read-only external research. Question: does either source give us data useful for
(a) the Track-2 forward emulator (training or validation target), or (b) the Track-1
parameter-learner's observational anchors? Honest verdicts, including access walls.

Cross-reference to our existing situation:

- We already hold ECCO-Darwin **v05** locally, native LLC270, daily (ends 2018-12-31) and
  monthly, and we validate surface pCO2 against GLODAPv3 (v05 globally unbiased, +0.3 uatm).
- MODIS PIC + PACE loaders (`modis_pic_loader.py`, `pace_loader.py`) exist but are **shelved**
  (Jon's directive: Carroll-6 proof-of-concept first, satellite = leapfrog v2).

---

## Source 1 — GHG Center: `eccodarwin-co2flux-monthgrid-v5`

Public docs notebook:
https://us-ghg-center.github.io/ghgc-docs/user_data_notebooks/eccodarwin-co2flux-monthgrid-v5_User_Notebook.html

### Concrete facts (from the notebook)

| Field | Value |
|---|---|
| Variable | Monthly-mean **air-sea CO2 flux** (sign convention: negative = into ocean) |
| Units | `mmol m^-2 s^-1` (millimoles CO2 per m^2 per second) |
| Asset name | `co2` |
| Spatial grid | Global **regular equirectangular** lat/lon, EPSG:4326 |
| Resolution | ~1/3 deg, stated ~18 km at high latitudes; **1440 x 721** pixels |
| Extent | lon -180.125 .. 179.875 ; lat -90.1248 .. 89.8752 |
| Temporal coverage | **2020-01-01 .. 2022-12-31**, monthly, **36 items** |
| Cadence | Monthly mean |
| STAC collection id | `eccodarwin-co2flux-monthgrid-v5` |
| STAC API | `https://earth.gov/ghgcenter/api/stac` |
| Raster API | `https://earth.gov/ghgcenter/api/raster` |
| S3 store (example) | `s3://ghgc-data-store/eccodarwin-co2flux-monthgrid-v5/` |
| Format | Cloud-Optimized GeoTIFF (COG) per monthly item |
| License | CC-BY-4.0 |
| Provenance | "ECCO-Darwin model v5 ... assimilates ocean circulation and biogeochemical processes from the MIT Darwin Project," building on Carroll et al. (2020) |

### Is this the same v05 we already use?

**Yes — same underlying model output, re-served as a derived public product; not a new product.**
It is a single-variable (CO2 flux only), monthly, **regridded** slice of the same ECCO-Darwin
v05 lineage we hold. Two things make it a downgrade relative to our local copy for our purposes:

1. **Regridded off the native LLC270 grid** onto a regular 1440x721 lat/lon raster. We already
   work on native LLC270; a COG re-projection loses the native cell geometry the parameter-learner
   uses (per-cell structure is load-bearing for the trio recovery).
2. **Only CO2 flux, and only 2020-2022.** This window does **not overlap** our local daily v05
   (which ends 2018-12-31), so it cannot even serve as an overlapping cross-check against our
   IC/target period. It carries none of the 3D BGC fields (PIC, POC, DFe, Chl, DIC, ALK) the
   emulator and recovery pipeline actually need.

### Useful to us?

- **As an emulator target:** No. Single 2D flux variable, regridded, wrong/short time window,
  and we already have the richer native fields.
- **As a validation reference:** Marginal-to-no. We validate surface pCO2 vs GLODAP (an
  independent obs product). This CO2-flux grid is **model output, not an observation**, so it is
  not an independent anchor. It is the same model validating itself. It could at most be a
  convenience sanity-plot of the published flux field, which we can already derive locally.

**Verdict: NOT USEFUL.** Same v05 model output, re-served as a regridded single-variable monthly
COG for 2020-2022 (non-overlapping with our local daily window); adds nothing over the native
v05 we already hold and is model output, not an independent observation.

---

## Source 2 — Earthmover marketplace / Arraylake catalog

App (marketplace): https://app.earthmover.io/marketplace
Public site: https://www.earthmover.io , docs: https://docs.earthmover.io

### Access wall (reported, not bypassed)

- `https://app.earthmover.io/marketplace` is a **client-rendered SPA**. An unauthenticated fetch
  returns only the page shell (`Marketplace | Arraylake`) with no catalog body. The live catalog
  listing is **behind login**. Per task constraints I did **not** log in or enter credentials.
- What is confirmable publicly comes from Earthmover's own blog, docs, and press coverage (below).

### What Earthmover actually is

Cloud-native scientific-data platform: **Arraylake** (catalog/metadata), **Icechunk**
(versioned, transactional Zarr storage), and the **Earthmover Data Marketplace** of
analysis-ready (ARCO) Zarr datasets. They also shipped a public **Arraylake MCP server**
(browse repos, inspect schemas, run OGC EDR queries) — an integration convenience, not new data.

### What data is actually offered

**Marketplace at launch (public blog "Announcing the Data Marketplace") = weather/atmosphere,
no ocean:** providers were Brightband (ECMWF/IFS HRES + ML-weather archive), Dynamical.org
(NOAA GEFS/GFS/HRRR, ECMWF IFS ensemble), Zeus AI (solar irradiance), Beyond Weather
(AIFS 100m wind), Planette (seasonal), Climate Uncertainty Lab (downscaled projections),
Subseasonal Consortium. **No ocean, BGC, ocean-color, MODIS, PACE, or chlorophyll.**

**Newer additions (mid-2026) are ocean, but not ours:**

- Two new marketplace **ocean-model hindcasts** from the **U.K. National Oceanography Centre**
  and **Italy's OGS institute** (physical ocean model hindcasts). Not ECCO, not ECCO-Darwin,
  not BGC-parameter relevant.
- Blog case studies: **World Ocean Database** made queryable via USM "AQUAVIEW" (~90M profiles);
  **Woods Hole** ocean profiles converted OPeNDAP->Icechunk; **GOES-16** satellite archive as
  virtual Zarr. These are storage/optimization case studies, not hosted datasets for us.

**Public sample datasets in the docs:** only **ERA5 surface** and **NOAA GFS**. No ocean/BGC.

### Does it host anything that saves us wrangling?

- **ECCO / ECCO-Darwin:** Not found in any public listing. No evidence Earthmover hosts it.
- **Ocean BGC for the emulator:** No. The ocean holdings are physical-ocean hindcasts (NOC, OGS)
  and in-situ profile databases (WOD), not the Darwin BGC fields we train on.
- **Satellite anchors (MODIS PIC / PACE):** Not hosted. Nothing here replaces our shelved
  `modis_pic_loader.py` / `pace_loader.py`. And WOD is the same class of in-situ product Jon's
  training-dataset list already points us to at source.

### Useful to us?

The one plausibly-relevant piece is the **World Ocean Database** as ready-to-query Icechunk (could
cut wrangling for in-situ profile validation), but it sits **behind marketplace login** and WOD is
already on our verified source list — so it is a convenience, not a new capability, and it is gated.

**Verdict: USEFUL-BUT-GATED (weakly).** No ECCO/ECCO-Darwin/BGC/ocean-color hosted; the only
adjacent asset (analysis-ready World Ocean Database) is convenience-only and behind marketplace
login, which I did not cross.

---

## Bottom line

| Source | Verdict | One-line reason |
|---|---|---|
| GHG Center `eccodarwin-co2flux-monthgrid-v5` | **NOT USEFUL** | Same v05 model output, re-served as a regridded single-variable (CO2 flux) monthly COG for 2020-2022; no independent obs, no BGC fields, non-overlapping with our local daily window. |
| Earthmover marketplace / Arraylake | **USEFUL-BUT-GATED (weak)** | Hosts no ECCO-Darwin / BGC / ocean-color; only adjacent asset is analysis-ready World Ocean Database, which is convenience-only, already on our source list, and behind login. |

### Sources
- https://us-ghg-center.github.io/ghgc-docs/user_data_notebooks/eccodarwin-co2flux-monthgrid-v5_User_Notebook.html
- https://www.earthmover.io/blog/announcing-data-marketplace/
- https://www.earthmover.io/blog/
- https://docs.earthmover.io/sample-data
- https://www.tipranks.com/news/private-companies/earthmover-deepens-ai-ready-scientific-data-platform-with-arraylake-mcp-and-new-ocean-datasets
- https://app.earthmover.io/marketplace (login wall; not entered)
