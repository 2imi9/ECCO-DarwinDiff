# Future skills agenda — DarwinDiff bundle expansion

> **⚠ SUPERSEDED FRAMING (2026-06-27).** Point-in-time record; data/plans stand, framing corrected by [STATUS.md](../../STATUS.md). The project is a **surrogate-to-model identifiability study over 4 OBSERVABLE params** {alpfe, scav_rat, diatomgraz, R_PICPOC} — **not** a 6/6 chase or a '5/6 ceiling / parameter-conservation' result. The growth pair {Smallgrow, Biggrow} is unobservable by construction. **R_PICPOC is recoverable** at 1° with a real calcite anchor (Daniels/MODIS) + `RATIO_MAX=2` — the differentiable Darwin calcite port and native resolution were *tested and did not help*, so R_PICPOC is **not cluster-gated**. `geo1` holds {alpfe, scav_rat, R_PICPOC} jointly 8/10; diatomgraz is an open iron-pair tradeoff. The surrogate gap is **dimensional** (the 0-D box homogenizes spatial structure, CV→1e-15), so box-vs-Darwin pattern-matching is not a fidelity metric.


The skill bundle at `.claude/skills/` currently ships 6 skills (2
project-original + 4 lit-search vendored from GDM). Below is the
prioritized roadmap of additional skills that would deepen researcher
support but are NOT needed for the current proof-of-concept paper / Jon
meeting / cluster onboarding work.

Each entry is sized so it can be picked up later as a single focused
task (~30-60 min build + 15 min docs).

## Tier 1 — high researcher leverage (build next session)

### `carroll6_parameter_scoring`
**Why:** Codifies the Cal-grade / Excellent thresholds + joint scoring
across regions + basin diagnosis (A/B/C mutex framework). The 5/6 ceiling
characterization is reusable by anyone running Carroll-style recovery on
other BGC models.
**Wraps:** logic in `src/darwindiff/scoring.py` (if it exists; else
inline in `run_v3.0_*.py`).
**Cross-references:** `darwin_dinn_sweep_orchestrator`,
`darwin_basin_diagnosis` (planned).

### `ocean_aoi_definer`
**Why:** Canonical AOI registry (HOT, BATS, eqpac, natlsubpolar,
southernoceanpac, plus user-defined bboxes) with LLC270 grid subsetting +
NHD watershed integration. Every multi-region BGC analysis re-derives
this; codifying saves hours.
**Wraps:** `AOI_BY_KEY` in `src/darwindiff/ecco_darwin_loader.py` + NHD
helpers (if added).

## Tier 2 — community-dataset wrappers (build when needed)

### `glodap_loader`
**Why:** GLODAPv2 ocean carbon system (DIC, alkalinity, pH, pCO2, nutrients,
O2). Standard reference for any global carbon analysis.
**Wraps:** `src/darwindiff/glodap_loader.py` (already exists per
`reference_training_datasets.md`).
**Reference:** GLODAPv2.2016b mapped on D: drive.

### `geotraces_loader`
**Why:** IDP2025 dissolved iron + POC profiles. Required for any iron
cycle work.
**Wraps:** GEOTRACES loader in `src/darwindiff/` (already in repo).

### `woa_wod_loader`
**Why:** World Ocean Atlas + World Ocean Database (T, S, nutrients, O2).
Standard climatology reference.

### `bgc_argo_loader`
**Why:** Biogeochemical Argo profiles (O2, chl, nitrate, particles).
Time-varying validation data.

### `socat_loader`
**Why:** Surface ocean pCO2 climatology. Direct anchor for F_CO2 lever
exploration (PR #62 follow-on work).

## Tier 3 — diagnostics + visualization (build when paper-writing)

### `darwin_basin_diagnosis`
**Why:** Mutex characterization framework: pairwise basin overlap counts,
A∪B∪C coverage diagnosis, lever-binarity tests. Standard output: ranked
basin table + Venn-style diagram.
**Wraps:** logic in `scripts/analyze_basinC_refine.py` + any subsequent
basin analysis utilities.

### `parameter_recovery_figures`
**Why:** Standard plots for the proof-of-concept paper: lever-response
curves, per-param recovery rates, dose-response with mutex overlay,
heatmap of 2D lever grids.
**Wraps:** matplotlib helpers in `analyze_basinC_refine.py`.

### `mitgcm_pickup_inspector`
**Why:** Lightweight tool for reading MITgcm pickup files (Darwin pickup,
ECCO state). Mostly diagnostic / debug.
**Generalizable beyond DarwinDiff.**

## Tier 4 — meta / workflow (build after paper ships)

### `darwindiff_proof_of_concept_paper_helper`
**Why:** Assemble paper-ready tables + figures from sweep summaries.
Highly project-specific — only useful during the JAMES manuscript writing
phase.

### `cluster_onboarding_chris_hill`
**Why:** Codify the MIT ORCD onboarding steps once Chris Hill route opens
(slurm submit script template, allocation request, environment build).
Only relevant after Jon's meeting outcome confirms cluster path.

## Skills explicitly NOT planned

- `mitgcm_full_runner` — too project-specific; ECCO-Darwin is a forward
  model run, not something we re-run.
- `darwin_v3_setup_wizard` — MIT-specific setup; documented in
  github.com/darwinproject/darwin3.
- `lucas_personal_workflow` — project workflow doesn't generalize.

## Build cadence

Don't pre-build skills speculatively. Build when:
1. The same workflow comes up for the 3rd time in different sessions.
2. Onboarding a new collaborator (Mick's students, Chris Hill's team).
3. Standardizing for the proof-of-concept paper methods section.

## Cross-references

- `.claude/skills/README.md` — current bundle inventory
- `docs/research_notes/2026-05-20_basinC_refine_sweep.md` — tonight's
  sweep design (consumer of `darwin_dinn_sweep_orchestrator`)
- `feedback_windows_max_path_in_sweeps.md` — gotcha captured in
  `darwin_dinn_sweep_orchestrator` skill body
