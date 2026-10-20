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

## 4. Gates — each must pass before the next is funded

**Gate 0 — symbolic screen (minutes, laptop).** Add the candidate observable to the structural
identifiability analysis (`docs/findings/2026-08-04_anchor_coverage_and_structural_identifiability.md`).
Validate first on the known flip: with and without Daniels, `R_PICPOC` must go non-identifiable →
identifiable. Then check that a standing-stock PIC observable, and a `CP/PP` observable, each make
`R_PICPOC` identifiable. If PIC does not, drop it and keep only the `CP/PP` route.

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
