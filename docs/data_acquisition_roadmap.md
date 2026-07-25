# Data-acquisition roadmap — real independent obs to break the identifiability walls (2026-07-22)

Sourced collaboratively with the project lead. Organizing discipline (the lead's load-bearing caveat):
**count INDEPENDENT campaigns and measurement types, not downloaded products.** SeaBASS composites, global
HPLC products, satellite PFT products, and derived UVP reconstructions reuse overlapping cruises — counting
products overstates effective sample size and would inflate claimed identifiability. Every entry below is tagged
with what it independently adds.

The Darwin iron physics (darwin3 readthedocs, read 2026-07-22) fixes what each observable must map to:
- `FeT` = total DISSOLVED inorganic iron (free Fe′ + ligand-bound FeL); GEOTRACES `Fe_D` may add colloidal.
- `alpfe` ≈ near-unity scalar on ALREADY-soluble Mahowald dust (default 0.04 is for raw dust; v05 input is
  `llc270_Mahowald_2009_soluble_iron_dust.bin`).
- Scavenging acts on FREE iron Fe′ (rate `scav`≈0.4/yr, or particle-based `scav_tau/scav_inter/scav_exp`);
  ligands are FIXED (`ligand_tot`=1e-3), so the ligand confound is pinned, not free.
- Iron remin/sediment source is POC-proportional (`fesedflux_pcm`=0.68e-3 mmolFe/mmolC) → prescribable from v05 POC/POFe.

## Tier A — direct Fe source/sink (breaks alpfe↔scav_rat) — APPROVED, pull first
| dataset | independently adds | parameter | access |
|---|---|---|---|
| ²³⁴Th/sediment-trap Fe export + upper-ocean Fe RESIDENCE TIMES (10.1029/2020GB006592) | the SINK rate directly (residence time ≈ 1/scav on Fe) — closer than carbon-only export | scav_rat | Wiley + supp data |
| Global Fe′ speciation product (PANGAEA 993556, 2026) | the free-iron pool scavenging ACTS ON — an observation operator for the sink substrate | scav_rat | PANGAEA (open). Do NOT double-count its source dFe/ligand inputs |
| HOT Trace Metals package (BCO-DMO 994200/962986/962966/962821) | co-located dissolved+particulate Fe, direct Fe UPTAKE, 150 m sediment-trap Fe FLUX at one time-series site | alpfe+scav_rat joint | BCO-DMO (open) |
| Hawaii Aerosol Time-Series (BCO-DMO 986789/987161; 10.1029/2025GB008834) | paired aerosol trace-metal DEPOSITION + particulate-Fe residence — input AND removal at one site | alpfe+scav_rat joint | BCO-DMO + Wiley |
| GP15 ²¹⁰Po/²¹⁰Pb scavenging + export (10.1029/2024GB008243) | source-free particle-scavenging proxy along a Pacific meridional transect | scav_rat | Wiley/BCO-DMO |

## Tier B — particle field + ligand context (pins the confounds)
| dataset | independently adds | use |
|---|---|---|
| Global UVP5 particle archive (PANGAEA 924375, 8805 profiles) | the PARTICLE substrate scavenging depends on — independent test of modeled particle field | scav particle-based term; treat derived reconstructions (2021GB007276, 2022GB007633) separately |
| GP17-OCE (BCO-DMO 993204, 483 samples/20 profiles) + GP17-ANT (994890, 398 Amundsen) ligands | post-IDP2025 ligand data → test/relax v05's FIXED-ligand assumption | Fe′ closure |
| Southern Ocean size-fractionated labile pFe + leaching (10.1029/2025GB008803; PANGAEA 951782/951902) | regional aggregation/scavenging/recycling process test | scav regional |

## Tier C — Fe SOURCE forcing (alpfe)
| dataset | independently adds | caveat |
|---|---|---|
| GEOTRACES GA03 soluble aerosol Fe (BODC 499432) | the direct SOLUBLE-Fe deposition observable — the alpfe anchor | — |
| MERRA-2 monthly aerosol (M2TMNXAER) | independent dust-deposition field vs v05 Mahowald | total, not soluble |
| EMIT mineral products + deposition (EMITL3ASA/L2BMIN/L4ESM; 10.1029/2025GB009033) | refined TOTAL-Fe spatial forcing | does NOT determine soluble alpfe — deprioritize for the scalar |

## Tier D — remin/export + PFT/growth (other params) — COUNT CAMPAIGNS, not products
- Remin/export: Fox et al. 2024 global POC profiles (10.5281/zenodo.10775647); Rufas POC-flux (zenodo 14173801);
  EXPORTS NP+NA; BGC-Argo eddy-subduction synthesis (10.1029/2025GB008912) = a structural sensitivity BOUND, not a rate.
- Size-fractionated (diatomgraz bSi / R_PICPOC PIC / growth split): Subhas et al. (10.1029/2022JC019470).
- PFT/growth: EXPORTS, NAAMES, PACE-validation (PVST_*), BIO-GO-SHIP, GO-BGC, SOCCOM — these HEAVILY overlap in
  cruises; the effective independent set is ~the distinct CAMPAIGNS, not the ~8 SeaBASS products. De-duplicate before
  counting information.

## DE-DUPLICATED UPDATE (2026-07-22, 10-agent characterization workflow) — the definitive version

Product count (~28) overstates effective evidence **~4×**. Campaign ledger de-dup flagged: GA03 triple-touched
(only the soluble aerosol is a new TYPE); Station ALOHA over-sampled (HOT + HATS + Rufas trap = ONE column);
BGC-Argo shared (Fox + Keutgen = one substrate); SeaBASS HPLC shared across EXPORTS/NAAMES/BIO-GO-SHIP;
MERRA-2 ⟂ Mahowald is FALSE (both lean on satellite AOD). Derived/ML/reanalysis products = zero independent weight.

**Effective-independent count per parameter (the reframe):**
| param | effective independent campaigns × TYPES | reading |
|---|---|---|
| **scav_rat** (SINK) | **≈6–7** (3 dimensionally-NEW rates/fluxes: Black ²³⁴Th, Cochran ²¹⁰Po/Pb, HOT uptake+trap; +2 ligand, +2 substrate) | **the wall we can actually break** |
| **alpfe** (SOURCE) | **≈1 solubility (GA03) + 1 total-flux prior** | thin — rests on a single soluble in-situ campaign |
| **R_PICPOC** | ≈2 (Subhas + EXPORTS, 2 biomes) | Daniels/MODIS anchor is separate (already have) |
| **diatomgraz** | ≈2 weak indirect (bSi/size only; no campaign measures grazing) | — |
| **growth** | 0 — unobservable by construction | excluded |

**APPROVED acquisition order — items 1–5 = the complete independence-clean feed for the active scav_rat column build:**
1. **Black et al. 2020 Fe residence times** (BCO-DMO underlying + SI Table S2) — SINK, a RATE (τ=inventory/removal), dimensionally new. [ACTIVE]
2. **HOT Trace Metals Fe uptake (994200) + 150 m trap flux (962821)** — SINK, kinetic rate + export flux at ALOHA. [ACTIVE]
3. **Cochran GP15 ²¹⁰Po/²¹⁰Pb** (BCO-DMO 883724 + 892348) — SINK, longer Fe-relevant timescale, no station overlap with Black. [ACTIVE]
4. **Fox et al. 2024 global POC profiles** (Zenodo 10775647, ~9.9 GB) — remin SHAPE (prevents aliasing remin depth into scav_rat). [ACTIVE]
5. **Rufas et al. 2024 trap+²³⁴Th POC flux** (Zenodo 14173801, 77 MB) — remin MAGNITUDE. [ACTIVE]
6–11 [LATER]: Subhas PIC/POC/bSi (calcite+diatomgraz), GA03 soluble aerosol (sole alpfe anchor), GP17 ligands
(test v05 fixed-ligand), EXPORTS (calcite #2), ANT-XXVIII/3 pFe, Kiko UVP5 (substrate). Gledhill Fe′ (993556) =
observation OPERATOR only (0 samples), adopt to map model FeT→Fe′.

**Loader note:** all point/profile → mirror `geotraces_loader`. Black τ is a per-province RATE target (not per-cell
concentration). Subhas: load 883965 only (884057 is a subset). Fox: ~9.9 GB → chunked/streamed read, stage on D:\\.

**Division of labor:** I pull (open, small, scriptable): all BCO-DMO CSVs (Black/Cochran/HOT×4/GP17/HATS/Subhas),
PANGAEA (Gledhill 993556, ANT 951782/951902, Kiko 924375), Zenodo Rufas (77 MB). User→D:\\ (large/login): Fox
(~9.9 GB), MERRA-2 (Earthdata login). Collaborator/registration ask: **BODC GA03 soluble aerosol (499432)** — the
ONLY alpfe-solubility anchor, no DOI, registration-gated → put the request in early (likely a Jon ask); SeaBASS
EXPORTS/NAAMES/BIO-GO-SHIP (one-time registration).

## Effective-independent-information rule (apply everywhere)
Before claiming any identifiability gain from added data, tabulate the DISTINCT campaigns/stations that actually
carry the target observable, not the product count. The iron pair's binding limit was ever ~14 GEOTRACES surface
cells; Tier A adds genuinely NEW measurement TYPES (residence time, Fe′, particle flux) at new sites, which is
real independent information — but Tier D's PFT products largely re-slice the same cruises and must be collapsed.
