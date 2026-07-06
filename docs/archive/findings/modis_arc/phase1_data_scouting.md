# PACE Arc Phase 1 — Data Scouting

**Status:** Phase 1 metadata-only scouting complete. Ground-truth source: NASA PACE Science Data Reprocessing V3.x notes (26-page PDF). The catalog-page WebFetches I did earlier returned partial / misleading information for some products; this document supersedes them.

**Goal of Phase 1:** answer "What does PACE OCI actually publish as L3 products, where do we get it, and is it really the observation channel that unlocks R_PICPOC?" before committing engineering time to a loader.

## TL;DR — three headlines worth sleeping on

1. **PACE OCI v3.1 does NOT include a PIC product.** The V2 release notes (April 2024) state "Particulate Inorganic Carbon (pic) and poc_unc will be included in a future release," and the V3.1 OC_BGC suite confirms this — provisional variables are `chlor_a`, `chlor_a_unc`, `carbon_phyto`, `carbon_phyto_unc`, `poc` only. v3.2 catalog entries for PIC are **planned placeholders with 0 granules**; no public timeline. The first-draft Phase 1 conclusion that "PACE PIC attacks R_PICPOC" is **wrong for the present** — until PACE v3.2 PIC ships, PACE delivers no coccolithophore-specific PIC observation.

2. **MODIS-Aqua PIC becomes the load-bearing PIC source**, not a fallback. The Phase 1.5 / Phase 2.A "MODIS-Aqua 2017-2019 PIC retrofit" is now elevated from "nice baseline" to "the only mature satellite PIC observation we can use right now." This is actually a small upgrade for DarwinDiff because Carroll 2022's calibration window is 2017-2019 — MODIS-Aqua has exact coverage of that window, no time-alignment problem.

3. **PACE v3.1 still adds two genuinely new observation channels** for DarwinDiff:
   - **`carbon_phyto`** (provisional, OC_BGC suite): total phytoplankton carbon, mg C m⁻³. Independent of chl_a (different algorithm). Anchors *biomass*, not *rate* — but biomass is what feeds `Biggrow` / `Smallgrow`. New observation distinct from anything we already use.
   - **MOANA picophytoplankton abundance** (provisional, Atlantic-only regional): Prochlorococcus, Synechococcus, picoeukaryotes in cells mL⁻¹. **Atlantic waters only** — covers natlsubpolar AOI, **does NOT cover eqpac**. Useful as an extra constraint on `Smallgrow` for natlsubpolar, but creates an AOI asymmetry the loss design needs to handle.

So the PACE arc is still worth pursuing — just with a different rationale than the v3.0 closeout assumed. The plan revises from "PIC attacks the 2-basin lock-in" to "MODIS-Aqua PIC (mature, 2017-2019 aligned) attacks R_PICPOC, plus PACE carbon_phyto + MOANA add biomass anchors that may stabilize basin selection."

## 1. The actual PACE OCI v3.1 product set (ground truth, from PDF)

**Authoritative list (PDF page 10, OCI L3 mapped product types):**

| Suite | Products in v3.1 | DarwinDiff relevance |
|---|---|---|
| OC_AOP | RRS, AVW, nFLH | Low — raw Rrs spectra; useful only if we DIY a PIC algorithm |
| OC_IOP | a, bb, aph, adg, bbp, Kd | **Medium** — `bbp` at 547nm is the input to Balch-Gordon PIC. DIY route to PIC if needed. |
| **OC_BGC** | **chlor_a, carbon_phyto, poc** | **HIGH** — `carbon_phyto` is the new lever; `poc` is independent verification of our existing POC_ABS anchor |
| PAR | par_day_*, ipar_planar_* | Already in DarwinDiff state forcing; PACE PAR is alternative source |
| **MOANA** | **prochlorococcus, synechococcus, picoeukaryotes** (Atlantic only) | **Medium-high for natlsubpolar; ZERO for eqpac** |
| SFREFL | rhos | Not relevant |
| LANDVI | terrestrial indices | Not relevant |
| AER_UAA | aerosol optical depth | Not relevant |
| CLOUD | cloud properties | Not relevant |

**Format and access:**
- NetCDF-4 self-describing
- File naming pattern: `PACE_OCI.YYYYMMDD.L3m.{PERIOD}.{SUITE}.V3_1.{var}.{res}.nc` where PERIOD ∈ {DAY, 8D, MO}, res ∈ {4km, 0p1deg, 1deg}
- **Spatial resolutions: 4.6km nominal (filename `4km`), 0.1° (~11km), 1.0° (~110km)** — confirmed PDF page 17
- **Temporal resolutions: daily, 8-day, monthly** — confirmed PDF page 17 ("Daily, 8-day, and monthly Level-3 mapped products are produced")
- L3b (binned) uses 4.6km or 9.2km integerized sinusoidal grids
- Coverage: 2024-03-05 → present (~26 months as of 2026-05-19)
- Maturity: all OC_BGC products are **Provisional** ("in family with heritage data products… have not yet been validated and may still contain significant errors")

**Confirmed for OC_BGC v3.1 (PDF page 5):**
| Variable | Type | Units |
|---|---|---|
| `chlor_a` | Provisional | mg m⁻³ |
| `chlor_a_unc` | Provisional | mg m⁻³ |
| `carbon_phyto` | Provisional | mg C m⁻³ |
| `carbon_phyto_unc` | Provisional | mg C m⁻³ |
| `poc` | Provisional | mg C m⁻³ (int16 storage per catalog) |
| ~~`pic`~~ | **NOT IN v3.1** | "future release" per V2 known issues |

**MOANA v3.1 (PDF page 6):**
| Variable | Type | Units | Coverage |
|---|---|---|---|
| `prochlorococcus_moana` | Provisional | cells mL⁻¹ | **Atlantic only** |
| `synechococcus_moana` | Provisional | cells mL⁻¹ | Atlantic only |
| `picoeuk_moana` | Provisional | cells mL⁻¹ | Atlantic only |

This is **regional, not global** — MOANA's algorithm is specifically validated on Atlantic waters. Phase 3 loader must handle this: for eqpac, MOANA is unavailable.

## 2. Revised science framing

### What the v3.0 closeout assumed PACE delivered

PR #63 hypothesized PACE provides "**coccolithophore-specific PIC + per-PFT chlorophyll**," and that the cocco-PIC anchor would dissolve the 2-basin lock-in by adding an observation regionally adaptive to the 23× spatial PIC/POC ratio (eqpac 0.031 vs natlsubpolar 0.722). The recovery_pace_swot.md memory was written under this assumption.

### What PACE actually delivers (and doesn't)

| Hypothesized PACE channel | Reality in v3.1 |
|---|---|
| Coccolithophore-specific PIC | **NOT AVAILABLE.** Deferred since V2 (April 2024). v3.2 placeholder, no timeline. |
| Per-PFT chlorophyll (diatoms, coccolithophores) | **NOT AVAILABLE.** Only MOANA picoplankton (Pro/Syn/picoeuk), Atlantic-only. |
| Total chlorophyll-a | Available (`chlor_a` v3.1, global daily 4.6km) — but we already match `chlor_a` indirectly via Darwin v05. Marginal new value. |
| **Phytoplankton carbon** (NEW finding) | **AVAILABLE** (`carbon_phyto` v3.1, provisional, global daily). Was NOT in the v3.0 hypothesis. Independent biomass observation. |
| **Particulate organic carbon** | Available (`poc` v3.1). Already used via Darwin v05 sub_POC obs; PACE is independent satellite cross-check. |

### Strategic revision

**The 2-basin lock-in attack now has two prongs (different from the original two):**

- **Prong 1: MODIS-Aqua PIC** (the actual coccolithophore proxy). Mature Balch-Gordon-style algorithm. Continuous 2002-present coverage including Carroll's 2017-2019 calibration window. No time-alignment problem. No Earthdata version-confusion issues. **This is the *real* PIC channel for the foreseeable future.**

- **Prong 2: PACE `carbon_phyto`** (new biomass observation). Adds constraint on `Biggrow` and `Smallgrow` rates without going through chl_a → biomass conversion errors. May indirectly stabilize basin selection if biomass mismatch is what drives basin A's `R_PICPOC` failure (TBC).

**MOANA picoplankton** stays as a secondary anchor — useful for natlsubpolar constraint on `Smallgrow`, ignored for eqpac.

## 3. Access mechanism (unchanged from first draft)

- **Earthdata Login required.** Free signup at <https://urs.earthdata.nasa.gov/>. Same auth covers MODIS-Aqua, PACE, GLDAS — one account unlocks everything.
- **Cloud-Enabled Dataset** on AWS S3 (`ob-cloud` bucket).
- Recommended Python access: `earthaccess` library (`pip install earthaccess`). Handles auth, search, AOI subsetting.

**Verification download target** (Phase 1.E, blocked on Earthdata Login):
- ONE monthly L3m granule of `carbon_phyto` for 2024-04 (full month, global, ~50 MB at 4km).
- Inspect: variable presence, units, coordinate grid, AOI coverage, sane magnitudes (carbon_phyto 1-100 mg C m⁻³ in open ocean).
- Cross-check against Darwin v05 phyto biomass slice.

## 4. Revised Phase 2 plan

Phase 1 reframes the menu materially:

- **Phase 2.A — MODIS-Aqua PIC 2017-2019 retrofit (PRIMARY PIC PATH).** No longer a fallback; this is the *only* mature satellite PIC observation. ~2-3 days. Implementation: `src/darwindiff/modis_pic_loader.py` analogous to existing GEOTRACES loader, AOI bin-averaging to 1×1° Darwin grid, monthly climatology 2017-2019 to match Carroll 2022 window. Loss weight `MODIS_PIC_W` analogous to `POC_ABS_W`.

- **Phase 2.B — PACE `carbon_phyto` integration (NEW lever).** Phyto biomass anchor for `Biggrow` / `Smallgrow` basin landscape. ~3-4 days. Implementation: `src/darwindiff/pace_loader.py`, function `open_pace_carbon_phyto()`. Time-alignment problem: 2024-2025 PACE vs 2017-2019 Carroll. Pragmatic resolution: use 2024-2025 PACE monthly climatology against Darwin v05 *if* v05 has 2024 output (TBC by checking ECCO-Darwin v05 release manifest); otherwise use 2024-2025 PACE as a Phase 4 *validation* set, not a training loss.

- **Phase 2.C — MOANA picoplankton (natlsubpolar only).** Atlantic-only AOI asymmetry must be coded explicitly. ~2 days, but lower priority than 2.A/2.B because MOANA cells mL⁻¹ → Darwin's biomass-in-mmol-C requires a conversion factor (~estimated, not measured directly).

- **Phase 2.D — Time alignment decision.** No longer the top open question — MODIS-Aqua solves the 2017-2019 problem outright. PACE-side stays a separate concern (2024-2025).

- **Phase 2.E — PACE PIC monitor.** Set a one-line cron / check note: re-poll `ob-cloud-pace-oci-l3m-pic-3.2` quarterly to detect when v3.2 PIC actually ships granules. Once it does, drop in as parallel anchor alongside MODIS-Aqua PIC.

**Sequencing:** 2.A first (mature, lowest risk), 2.B second (new science), 2.C third (regional asymmetry handling), 2.D as a checkpoint, 2.E perpetual background check.

## 5. Resolved Phase 1 open questions (PDF answered all of them)

1. **~~PIC v3.1 catalog page 403~~ → resolved**: page 403'd because PIC v3.1 doesn't exist; the v3.2 placeholder is the catalog entry that exists.
2. **~~PIC units~~ → moot**: no PIC product. When v3.2 ships, expect mol m⁻³ per ATBD.
3. **~~Monthly vs daily~~ → resolved**: daily, 8-day, AND monthly all exist (PDF page 17).
4. **MOANA spatial coverage → resolved**: **Atlantic only** (PDF pages 6 and 10).
5. **PIC algorithm 2-band vs hyperspectral → moot for now**: when v3.2 PIC ships, the ATBD will specify. PACE OCI is hyperspectral so the algorithm presumably exploits the full spectrum, but we won't know until the product is published.

## 6. New open questions surfaced by the PDF

1. **Does ECCO-Darwin v05 have 2024-2025 output published?** Determines whether PACE `carbon_phyto` can be used as a training loss (matched-year Darwin reference) or only as held-out validation. To be answered in Phase 2.B by checking the v05 release manifest.

2. **`carbon_phyto` algorithm provenance.** PDF page 5 lists it as Provisional but doesn't cite the algorithm. Likely a Behrenfeld-style chl-to-carbon ratio or a backscatter-based retrieval. Need the ATBD to know whether `carbon_phyto` is meaningfully independent of `chlor_a` or just `chlor_a × constant`. If the latter, the new-observation argument collapses.

3. **MOANA cells/mL → mmol-C conversion.** What conversion factor does the DarwinDiff community use for Pro/Syn/picoeuk? Standard literature values exist (Buitenhuis et al. 2012), but the choice affects loss magnitude. Defer until Phase 2.C is in scope.

4. **MODIS-Aqua PIC product status as of 2026-05.** Last reprocessing was R2022 with the "variable bbc*" calibration for coccolithophore assemblages. Still actively maintained? Status of any 2024-2025 reprocessing? Check OB.DAAC MODIS-Aqua release notes in Phase 2.A.

5. **Earthdata Login user-action timeline.** Real blocker; cheap to fix (5 min); applies to MODIS-Aqua too. Same account.

## 7. Reference list

**Primary source (this revision):**
- PACE Science Data Reprocessing V3.x notes (PDF, 26 pages): authoritative product list and known-issues catalog. Local copy: `C:\Users\Frank\Downloads\PACE_Reprocessing_V3.x_notes.pdf` (referenced inline as "PDF page N").

**Catalog and search:**
- NASA Earthdata catalog: <https://www.earthdata.nasa.gov/data/catalog/>
- Earthdata Search (browse / download): <https://search.earthdata.nasa.gov/>
- PACE OCI L3m CHL v3.1 (active, 1804 granules): <https://www.earthdata.nasa.gov/data/catalog/ob-cloud-pace-oci-l3m-chl-3.1>
- PACE OCI L3m POC v3.1 (active, 1804 granules): <https://www.earthdata.nasa.gov/data/catalog/ob-cloud-pace-oci-l3m-poc-3.1>
- PACE OCI L3m PIC v3.2 (placeholder, 0 granules): <https://www.earthdata.nasa.gov/data/catalog/ob-cloud-pace-oci-l3m-pic-3.2>
- PACE OCI L3m MOANA v3.1: <https://www.earthdata.nasa.gov/data/catalog/ob-cloud-pace-oci-l3m-moana-3.1>
- PACE OCI L3m CARBON v3.2 (placeholder; v3.1 of CARBON is the active one): <https://www.earthdata.nasa.gov/data/catalog/ob-cloud-pace-oci-l3m-carbon-3.2>

**Mission documentation:**
- PACE OCI mission: <https://pace.gsfc.nasa.gov/>
- OB.DAAC PACE landing: <https://oceancolor.gsfc.nasa.gov/data/pace/>
- PACE OCI V3.1 reprocessing completed alert: <https://www.earthdata.nasa.gov/data/alerts-outages/pace-oci-v3-1-reprocessing-completed>
- PIC ATBD (still applies once v3.2 PIC ships): <https://oceancolor.gsfc.nasa.gov/resources/atbd/pic/>

**Tools:**
- `earthaccess` Python library: <https://earthaccess.readthedocs.io/>
- Earthdata Login signup: <https://urs.earthdata.nasa.gov/>

## 8. Revision history of this document

- **2026-05-19, first draft:** assumed PACE OCI v3.1 publishes PIC; mis-headlined "PIC attacks R_PICPOC."
- **2026-05-19, this revision:** corrected against PACE V3.x reprocessing notes PDF. PIC removed as v3.1 product; MODIS-Aqua promoted to primary PIC source; `carbon_phyto` and Atlantic-only MOANA surfaced as the actual PACE-unique adds.
