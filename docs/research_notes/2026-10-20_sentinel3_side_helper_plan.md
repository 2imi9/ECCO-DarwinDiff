# A Sentinel-3 ocean-colour side helper — plan, gated on a matchup test (2026-10-20)

**Status: PLAN, nothing run.** No result here is measured. Every compute figure is an estimate.
Tracker: [#262](https://github.com/2imi9/ECCO-DarwinDiff/issues/262) (spine D).

**Question.** Is it worth retraining an Earth-observation foundation model on Sentinel-3 and using
it as an observation-side helper for the parameter learner, in the way IBM's
Granite-Geospatial-Ocean is used for ocean colour? And does the "fine-tune a foundation model on the
simulator, then on observations" method of Weber & Kelp (arXiv:2610.22555) transfer to us?

**Short answer.** Start from Granite-Geospatial-Ocean, not OlmoEarth. Use it only on the observation
side, never trained on Darwin output. Spend nothing beyond one node-day until a matchup test shows it
beats the standard algorithms against in-situ data.

## 1. What the candidate models are

| | Granite-Geospatial-Ocean (IBM) | OlmoEarth (Ai2) |
|---|---|---|
| Sentinel-3 | **yes**: 16 OLCI bands + SLSTR SST, 42×42-pixel tiles, ~512k tiles | **no**: Sentinel-1, Sentinel-2, Landsat only |
| Native scale | OLCI, 300 m | ~10 m, 2.56 km tiles, mostly land |
| Architecture | ViT MAE encoder (Prithvi-EO family), via TerraTorch | ViT, v1 Nano 1.4M → Large 308M params (Base 89M) |
| Licence | Apache-2.0 | OlmoEarth Artifact License |
| Shipped ocean task | primary production | none |

Sources: <https://huggingface.co/ibm-granite/granite-geospatial-ocean>,
<https://huggingface.co/allenai/OlmoEarth-v1-Base>, <https://github.com/allenai/olmoearth_pretrain>
(read 2026-10-20). Retraining OlmoEarth on Sentinel-3 means adding a new sensor at 30× coarser
resolution. That is new-modality pretraining that largely rebuilds what Granite already ships.

## 2. Compute is not the constraint

AICR (from [cluster_setup.md](../cluster_setup.md); not queried live on 2026-10-20, the SSH
certificate had lapsed): 248× B200 (`b200-batch`, 24 h), 152× RTX PRO 6000, 10 TB `/scratch`
(30-day purge), durable `/work/neu/p2026_0089_neu`.

| step | estimate |
|---|---|
| Frozen Granite embeddings + small head on matchups | hours, 1 GPU (RTX or B200) |
| Full fine-tune of Granite or OlmoEarth-Base | hours, 1 B200 |
| Continued pretraining of OlmoEarth with Sentinel-3 added | ~1–3 node-days, 8× B200 |

What does bind: **data staging** (OLCI L1/L2 over our AOIs is TB-scale and must live in `/work`,
not `/scratch`), and **trustworthy labels**.

## 3. What the helper is for, and what it cannot be

**The existing calcite anchor is an in-situ production ratio, not satellite PIC.** `R_PICPOC` is
anchored on the Daniels et al. 2018 compilation (`src/darwindiff/daniels_loader.py`): co-located ¹⁴C
calcification and primary production, so `CP/PP` matches the box's `dPIC/dt = R_PICPOC × mort_total`
in kind. Satellite PIC, from MODIS or OLCI, is a **standing-stock** proxy. The map already settles
that for a production ratio "the matched calcification:photosynthesis rate is the correct
observation operator" and that satellite PIC is biased in Southern Ocean diatom/bSi waters
(`docs/research_notes/2026-07-23_expert_review_corrections.md`). So a helper predicting PIC is the
**wrong observation operator** for `R_PICPOC` unless it predicts `CP/PP` directly, or a separately
validated operator maps it there.

What the helper could legitimately give:

1. **A second-sensor `R_PICPOC` anchor that extends Daniels coverage** — if, and only if, it
   predicts `CP/PP` (not PIC) and beats the baselines in §4 at held-out in-situ stations. A
   recovery re-run against it alone would be evidence from an independent instrument, which no
   amount of new seeds on the Daniels data can supply. Note `southernoceanpac` has **zero** Daniels
   cells, and that is exactly where satellite PIC is least trustworthy.
2. **The roadmap C.1 channel** (PFT-resolved Chl, [cluster_roadmap.md](../cluster_roadmap.md)) —
   relevant to whether `diatomgraz`'s eqpac signal survives on independent real data.

**It must not be trained on Darwin output, and it must not bias-correct the model.** Weber & Kelp
fine-tune Aurora on UKCA and then on MLS ozone to cut UKCA's bias. Doing that here would teach the
helper to absorb the model–observation mismatch, which is exactly what the parameter learner
attributes to parameters. It would also erase signals such as `diatomgraz` being trained away from
Carroll outside eqpac. Any helper output used as a loss target must be derived from satellite inputs
and in-situ labels only. The repo's forward/OSSE emulator (2026-07-11) is the place for the
Weber & Kelp idea, not this helper.

### 3a. How much information Sentinel-3 can carry, per parameter

A foundation model cannot add information that is not in the radiance; it can only extract it. OLCI
sees the upper optical layer (about one attenuation depth, a few metres to tens of metres):
phytoplankton absorption (Chl), CDOM and particle backscatter, where coccolith calcite is a strong
backscatterer. SLSTR adds SST. It does not see dissolved iron, nutrients, DIC/alkalinity, any rate,
or anything below the optical layer.

| parameter | what Sentinel-3 can carry | basis |
|---|---|---|
| `alpfe` | essentially none: DFe is invisible, and the only indirect route (Chl in HNLC regions) lies along the alpfe×sink degenerate direction | `docs/findings/2026-07-30_iron_closure_ude_is_a_gauge_symmetry.md` |
| `scav_rat` | none: scavenging is subsurface | no optical signature |
| `R_PICPOC` | **some**, the only parameter with a direct optical signal (calcite backscatter), but as a standing stock, not a production rate | `docs/research_notes/2026-07-23_expert_review_corrections.md` |
| `diatomgraz` | none: 0 of 14 satellite PFT algorithms retrieve a rate; PACE adds composition, still no rate | `docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md` |
| `Smallgrow`, `Biggrow` | not applicable: excluded by construction | CLAUDE.md framing |

Existing ocean-colour evidence agrees: MODIS Chl against v05 is unbiased in eqpac (inside the
0.130 dex noise floor) and 5.0× low in the North Atlantic bloom
(`docs/findings/2026-07-21_chl_binning_recompute.md`). That exposes a **structural** model error, not
parameter information.

**Consequence for this plan.** The helper's ceiling is `R_PICPOC`, which already recovers 50/50 with
the Daniels anchor. Its value is an independent-instrument replication and wider coverage, not new
identifiability. For the hard parameters (`scav_rat`, `diatomgraz`) the information is in in-situ
data (GEOTRACES DFe, thorium, BGC-Argo), not in ocean colour. Gate 0b below tests this table
quantitatively before any ML.

## 4. Gates — each must pass before the next is funded

**Gate 0 — symbolic screen (minutes, laptop).** Add the candidate observable to the structural
identifiability analysis (`docs/findings/2026-08-04_anchor_coverage_and_structural_identifiability.md`).
Validate first on the known flip: with and without Daniels, `R_PICPOC` must go non-identifiable →
identifiable. Then check that a standing-stock PIC observable, and a `CP/PP` observable, each make
`R_PICPOC` identifiable. If PIC does not, drop it and keep only the `CP/PP` route.

**Gate 0b — sensitivity against retrieval noise (about an hour, laptop).** Structural
identifiability says whether a parameter *can* be seen; this gate asks whether Sentinel-3 can see it
*above its own noise*. For each candidate surface observable `y` (Chl, PIC, `CP/PP`, PP) and **all six**
Carroll parameters `θ` (the excluded growth pair included as a control: `Biggrow` is unobservable by
construction and should read near zero, so a large value there flags a broken computation), using the differentiable box with autograd at Carroll's values, per AOI:

1. compute the log-sensitivity `s = |∂log y / ∂log θ|`;
2. form the signal `Δlog y ≈ s · log(1.4)`, the response to a ±40% change in `θ` (the pass band);
3. compare it with the retrieval error σ in log units: 0.130 dex for Chl (the MODIS noise floor
   measured in this repo), and the published algorithm error for PIC and PP, converted to dex.

A parameter whose signal is below σ in every AOI is declared **not visible to Sentinel-3** and dropped
from the plan. Pre-register the expected outcome from §3a: `R_PICPOC` above σ (PIC, `CP/PP`), every
other parameter below. This needs only the Jacobian of one observable, not an inverted Hessian
(the finite-difference Hessian at Carroll is indefinite and is not used here). If `R_PICPOC` itself
falls below σ, close the plan.

**Pilot run, 2026-10-20** (`scripts/analysis/satellite_observable_screen.py`). The AOI IC caches are
not committed (they are built from the offline v05 archive), so this ran three stylised iron regimes
(initial DFe 0.4×, 1×, 10× `K_FE`) on the default background constants, at the flagship 200-step
window and at 1460 steps. Signal in dex for a ±40% parameter change; σ reference 0.130 dex. Ranges
are min–max over the three regimes and both windows:

| observable | `alpfe` | `scav_rat` | `Smallgrow` | `Biggrow` | `diatomgraz` | `R_PICPOC` |
|---|---|---|---|---|---|---|
| Chl | 0.025–0.038 | 0.024–0.034 | 0.076–0.097 | 0.055–0.074 | 0.040–0.057 | 0.000 |
| PIC (absolute) | 0.037–0.057 | 0.038–0.050 | **0.18–0.21** | 0.035–0.042 | 0.020–0.028 | **0.144–0.146** |
| PP | 0.042–0.057 | 0.041–0.050 | **0.18–0.20** | 0.037–0.042 | 0.022–0.028 | 0.000 |
| `CP/PP` | ≤0.0002 | ≤0.0001 | ≤0.0035 | ≤0.0014 | ≤0.0013 | **0.146** |
| PIC/POC | ≤0.0004 | ≤0.0003 | ≤0.0015 | ≤0.0003 | ≤0.0001 | **0.144–0.146** |
| DFe (in-situ ref.) | 0.079–0.115 | 0.072–0.087 | 0.17–0.20 | 0.027–0.044 | 0.012–0.029 | 0.000 |

What it says (the expected outcome above was written before this run, but in the same session, so it
is not a true pre-registration):

- **`R_PICPOC` is visible, but only just.** The two ratios carry it with log-sensitivity exactly 1
  and essentially nothing from any other parameter, so they isolate it cleanly. Absolute PIC does
  not: it carries `Smallgrow` more strongly than `R_PICPOC`. **Use a ratio product, never absolute
  PIC.** A band-sized change moves the ratio 0.146 dex, only 1.1× the Chl floor, so the satellite
  ratio needs σ ≲ 0.146 dex (≈40%) to resolve the band at 1σ and ≲ 0.073 dex (≈18%) at 2σ.
- **`alpfe`, `scav_rat`, `diatomgraz` are below the floor in every satellite observable**, by 2–5×.
  §3a holds.
- **`Smallgrow` is the exception: PIC, POC and PP move 0.18–0.21 dex.** This is sensitivity, not
  identifiability. In the box `Smallgrow` enters only as the product `Smallgrow × LIGHT`, so a
  satellite signal in PP is exactly degenerate with an error in the light field. The growth pair
  stays excluded.
- **The `Biggrow` control** reads 0.03–0.07 dex: below the floor, as required, though not zero.

Caveats: a 0-D box on stylised regimes, not the flagship per-AOI geometry; in the box PIC and POC sink
at the same rate, so PIC/POC equals `R_PICPOC` by construction, whereas real standing-stock ratios
are altered by sinking, grazing and dissolution (§3). Rerun on the AOI IC caches when v05 is mounted.

**Gate 1 — matchup count (hours, CPU).** Sentinel-3A launched February 2016; most of the Daniels
compilation predates it. Count in-situ `CP/PP` (and calcification-rate) samples that fall inside the
OLCI era and our AOIs: Daniels' post-2016 rows, Balch et al. 2025 GP19
(10.1029/2024GB008457), and any other calcification-rate cruises. **If the count is too small for a
held-out split (pre-register the threshold before counting), stop here** — the helper cannot be
validated and must not be used as an anchor.

**Gate 2 — the matchup test (hours, 1 GPU).** Frozen Granite encoder + small head, trained on
OLCI tiles at matchup stations, scored on **held-out stations** (spatial blocks, not random rows).
It must beat, on the same held-out set:

- the trivial baseline (per-AOI climatological `CP/PP`);
- the standard-product route (operational PIC and PP products → ratio);
- for the C.1 channel, the standard OLCI/OC-CCI chlorophyll and PFT products against in-situ HPLC.

Report the error with uncertainty, and say in advance what margin counts as "beats". Under the repo's
three-check rule a pass needs a **fresh** set of stations for replication, not a re-split.

**Gate 3 — only if Gate 2 passes.** Fine-tune Granite end to end (1 B200, hours). Consider OlmoEarth
continued pretraining (node-days) only if Granite's 42×42 tiles or band set is shown to be the
limitation.

**Gate 4 — use.** Re-run the flagship with the helper's `CP/PP` replacing Daniels (anchor-only
swap, same job as its control), and once with both. Report per-AOI, with the untrained null, and
`R_PICPOC` against the 6/50 epoch-matched anchor-off control.

## 5. Open risks

- Matchups in the OLCI era may be too few (Gate 1 exists for this).
- Cloud and high-latitude gaps (the same risk the C.1 row records).
- The helper's own training labels may come from algorithms that share a bias with the standard
  products, which would make Gate 2 a comparison between correlated estimators.
