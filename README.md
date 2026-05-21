# ECCO-DarwinDiff

A PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model that lets gradients flow through every step of the simulation. Built for two related uses:

1. **Parameter learner** — a faster, richer replacement for ECCO-Darwin's Green's-functions calibration. Where Carroll 2020 / 2022 tunes one global vector of 6 biogeochemical parameters via expensive multi-decadal forward runs, DarwinDiff learns a *function* mapping local environmental conditions to a per-cell parameter vector via gradient descent through a differentiable box model.
2. **Emulator** — a neural-network stand-in for ECCO-Darwin trained on the same Darwin output, for long-timescale climate runs the full model is too slow for. Not started yet — Track 2.

## Status — Track 1 v3.1 two 5/6 paths in 3-AOI training (2026-05-20)

Track 1 advanced past the v3.0 5/6 plateau. **Two distinct 5/6 Cal-grade seeds in 3-AOI joint training** (Eq Pac + N Atl Subpolar + Southern Ocean Pacific), out of 757 seeds across 76 configs:

- `w2e_peraoi_lam0.1` seed 3: PER_AOI_DINN=1 + CONSISTENCY_LAMBDA=0.1 at Basin C base. Recovers alpfe (Excellent) + scav_rat + Smallgrow + Biggrow + diatomgraz; R_PICPOC drifts.
- `c_chl40_posi15` seed 9: CHL1_W_EXTRA=4.0 + POSI_W=1.5 at Basin C base. Recovers alpfe + scav_rat (Excellent) + Smallgrow + Biggrow + R_PICPOC; diatomgraz drifts.

Different param recoveries; both retain the iron pair and lose one of {diatomgraz, R_PICPOC}. PER_AOI_DINN was falsified at 2-AOI per PR #58; the 3-AOI behavior is new and material.

Iron-pair Basin C baseline (F2 config) is **38/40 reproducible across n=40** (four independent 10-seed batches: 10/10, 10/10, 10/10, 8/10). The 5% drop in the 4th batch is reported honestly.

The structural 5/6 ceiling from v3.0 still holds at 2/757 break rate. The parameter-conservation framing is right; the marginal breaks show the architecture matters as much as the loss surface. Wave 5 dose-response on CONSISTENCY_LAMBDA + best-lever combos is queued to test reproducibility.

Cluster path opening: Jon Lauderdale relayed MIT ORCD AICR (B200) beta news. Meeting 2026-05-21 11am EDT to confirm Engaging cluster onboarding (MIT Sponsored Account via Jon as host).

### v3.0 narrative (preserved for context)

Earlier v3.0 multi-AOI close-out: the 5/6 ceiling is characterized structurally as **parameter conservation** — the observations support ~5 effective constraints on 6 parameters; the 6th is always the "residual sink", and loss weighting decides which.

**Project state:**

- 5-PFT 2-layer box (v2.7) on main; v2.8 Darwin v5 pickup ICs + L2 POC observation loss on main (PR #45). Joint multi-AOI training (Eq Pac + N Atl Subpolar) with a shared Carroll-6 implemented across PRs #46–#57.
- Best baseline (PR #57 best config: AOI ID + GEO POC=0.5 + hd=32 + NAtl_W=2.0, n=15): **7/15 at 5/6 Cal-grade, mean_cal = 3.93**. The actual baseline binding parameter is `diatomgraz` (2/15 Cal, 13%; 6/7 5/6-miss seeds drop diatomgraz specifically). R_PICPOC is Cal-grade in 11/15 baseline seeds.
- **PR #58 (ready for review)**: per-AOI DINNs + cross-AOI consistency penalty. λ sweep × n=10: 0/40 at 6/6; best λ=0.1 only 3/10 at 5/6. **Architectural-ceiling hypothesis falsified.**
- **PR #59 (draft)**: PIC_ABS_W + POC_ABS_W paired absolute anchors. Three sweeps (PIC alone; paired heavy; paired light) all underperform baseline on aggregate. R_PICPOC can be magnitude-pinned per-AOI but at full iron-pair Cal collapse. Recommended NOT for merge as v3.0 default; the deliverable is the diagnosis in [`notebooks/32_v3_0_param_learner_ceiling.ipynb`](notebooks/32_v3_0_param_learner_ceiling.ipynb).

**Different interventions shift WHICH parameter is the dominant 5/6 miss:**

| Family | Dominant 5/6 miss | Mechanism |
|---|---|---|
| Baseline (PR #57) | **diatomgraz** | Chl1 z-score under-constrains diatom-specific growth |
| Per-AOI DINN (PR #58) | R_PICPOC | shared-MLP regularization removed |
| PIC alone (PR #59) | alpfe + scav_rat | magnitude anchor on PIC competes with iron budget |
| Paired POC+PIC (PR #59) | alpfe + scav_rat | both anchors disturb iron budget |

**Path to 6/6 (laptop-tractable, empirically justified):**

1. **POSi (biogenic silica) loss + box-model state extension** — diatom-specific tracer (~1280 finite GEOTRACES bSi values) that directly constrains `diatomgraz` (the actual baseline binding param) without competing with the iron-pair budget. ~1-2 hr code lift; extends 15→16 tracer state.
2. **3rd AOI: Southern Ocean Pacific sector** — adds high-particle-flux + carbonate-rich regime; per-AOI DINN tool from PR #58 makes 3-AOI nearly free.
3. **Reduce parameter count** — given the ~5-effective-constraint finding, fixing some Carroll-6 entries at published values and learning only the unconstrained subset is a structural alternative.
4. **Cluster cross-basin** — canonical fallback for scav_rat. Gated on ORCD reply (no response by 2026-05-18).

**Project arc summary:**

- v2.0 (carbonate cycle, nb20-21): iron pair to 1.1% / 40% off Carroll in the 2-PFT proxy.
- v2.1 (GLODAP real-obs hybrid, nb22, PR #41): `R_PICPOC` 360% → 74% off.
- v2.2 (5-PFT box matching Darwin v05, nb23-29, PR #37): 22 experiments → 4/6 winner; alpfe + Smallgrow appeared stuck (later falsified by v2.6).
- v2.6 (GEOTRACES IDP2025 absolute-units iron loss, PR #40): 4/6 reproducibly across n=10; Smallgrow at 9/10 Cal-grade.
- v2.7 (2-layer box, PR #42): vetted 2-layer integrator; subsurface DFe alone doesn't unblock scav_rat.
- v2.8 (Darwin v5 ICs + L2 POC obs, PR #45): project-first reproducible scav_rat recovery (7/10 Cal-grade, 4/10 Excellent).
- v3.0 (multi-AOI joint training, PRs #46-#59): 5/6 plateau established across 50+ seeds; architectural and observational-anchor break attempts all empirically falsified; the structural ceiling is parameter conservation. The deliverable is the arc analysis notebook nb32.
- v3.1 (3-AOI Basin C + PER_AOI_DINN, 2026-05-19→20, on `claude/musing-gauss-962009` worktree): Southern Ocean Pacific added as 3rd AOI; Basin C iron-pair recovery 20/20 at n=20; first 5/6 in 3-AOI training via PER_AOI_DINN + low CONSISTENCY_LAMBDA. ~950 seeds across 5 chained waves; first seed to recover alpfe + scav_rat + diatomgraz together. Wave 5 reproducibility check in flight.

See [STATUS.md](STATUS.md) for full live state, [`docs/research_notes/2026-05-20_basinC_refine_sweep.md`](docs/research_notes/2026-05-20_basinC_refine_sweep.md) for tonight's sweep design, and [`notebooks/32_v3_0_param_learner_ceiling.ipynb`](notebooks/32_v3_0_param_learner_ceiling.ipynb) for the v3.0 close-out analysis.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*; Carroll et al. 2022, *GBC*) is a global ocean biogeochemistry model on the ECCO LLC270 grid (~1/3° at the equator, ~18 km at high latitudes, 50 vertical levels), 1992–2017+. Its biogeochemistry is calibrated via **Green's functions** (Menemenlis et al. 2005), which scales linearly badly: each tuned parameter needs a fresh full forward run, so Carroll's published calibration handles only **6 parameters** (iron dust solubility, iron scavenging rate, small + large phytoplankton growth rates, diatom palatability, PIC/POC ratio).

DarwinDiff replaces the biogeochemistry side of this with **PyTorch autograd**: gradients for all parameters are computed in one backward pass, and the parameter values themselves vary across space — predicted by a small per-cell neural network (DINN) from local environmental conditions (SST + MLD + wind + lat). The structural argument: a single global parameter vector cannot reproduce spatial heterogeneity in ocean biogeochemistry; per-cell parameters can.

> **Design details:** see [`docs/dinn_design.md`](docs/dinn_design.md) for the full per-cell architecture, training loop, structural-ceiling argument, and DINN vs DINNDeep variant decisions.
>
> **Cluster setup:** see [`docs/cluster_setup.md`](docs/cluster_setup.md) for compute requirements, environment setup on a Linux GPU cluster, dataset transfer plan for the LLC270 monthly tree, and the open questions list for ORCD.

## Headline results (as of 2026-05-12)

All fits use a 1500-epoch DINN per-cell network (1×1 conv backbone) versus a global-scalar Green's-functions baseline, against z-scored Darwin v05 output over a Mid-Atlantic-sized AOI. v2.2 5-PFT (nb23–29) results are added below the v1.x / v2.0 table.

| AOI | Target | Network | DINN r | Loss ratio Global / DINN |
|---|---|---|---|---|
| North Pacific | Darwin NO₃ | DINN (SST) | **0.979** | **23.8×** |
| North Pacific | Darwin Chl | DINN (SST) | 0.966 | 14.6× |
| Mid-Atlantic | Darwin Chl | DINN (SST) | 0.724 | 1.8× |
| Mid-Atlantic | Darwin NO₃ | DINN (SST) | 0.607 | 1.3× |
| Equatorial Pacific | Darwin FeT | DINN (SST) | 0.337 | 1.1× |
| Equatorial Pacific | Darwin FeT | **DINNDeep (SST + MLD + wind + lat)** | **1.000** | *(saturates target field; see caveat below)* |
| North Pacific | Darwin Chl | **DINNDeep (4-channel)** | **1.000** | *(saturates; see caveat below)* |
| Equatorial Pacific | FeT + Chl + POC + PIC (joint) | **DINNDeep + multi-tracer loss** | **all 4 ≥ 0.998** | *(saturates jointly; see caveat below)* |
| Equatorial Pacific | **7-tracer carbonate joint** | **DINN baseline + carbonate (nb20)** | poor per-tracer (−0.36 to 0.62) | *iron pair within **1.1%/40%** of Carroll — v2.0 headline* |
| Equatorial Pacific | 7-tracer carbonate joint | DINNDeep + carbonate (nb20) | all r ≥ 0.88 | *scav_rat moves closer to Carroll in both architectures — robust signal* |
| Equatorial Pacific | 7-tracer carbonate joint (GLODAPv2.2016b DIC/ALK hybrid) | **nb22 (Track 1 v2.1 Phase 1, PR #36)** | per-tracer mixed | *R_PICPOC 360% → 74% off Carroll; iron pair degraded — validates real-obs hybrid approach* |

### v2.2 (5-PFT box, nb23–29) — 22 experiments testing 6/6 push

Track 1 v2.2 extends the box-model from the 2-PFT proxy used in v2.0 to the full 5-PFT setup matching Darwin 3 v05. Sorted by calibration-grade count (≤ 40% off Carroll); selected rows from [`docs/findings/v2.2_overnight_summary.md`](docs/findings/v2.2_overnight_summary.md):

| Notebook | Config | Cal-grade | alpfe | scav_rat | Smallgrow | Biggrow | diatomgraz | R_PICPOC |
|---|---|---|---|---|---|---|---|---|
| **29_v2_4_pinn_drift_eqpac_w3.0** | **PINN drift w=3.0** | **4/6** | 0.888 | **0.345** | 1.251 | **0.314** | **0.299** | **0.358** |
| 23_5pft_box_eqpac_seed3 | baseline, seed 3 | 3/6 | 0.841 | 0.213 | 0.911 | 0.346 | 0.199 | 0.565 |
| 28_v2_4_pinn_balance_eqpac_w1.0 | PINN balance w=1.0 | 3/6 | 0.882 | 0.317 | 1.221 | 0.103 | 0.319 | 0.418 |
| 23_5pft_box_eqpac | baseline, seed 0 | 3/6 | 0.891 | 0.300 | 1.244 | 0.326 | 0.282 | 0.738 |
| 27_v2_3_raw_fet_eqpac_w0.05 | raw_fet w=0.05 | 3/6 | 0.897 | 0.134 | 1.184 | 1.155 | 0.100 | 0.262 |
| 27_v2_3_raw_fet_eqpac_w0.01 | raw_fet w=0.01 | 1/6 | **0.392** | 2.556 | 1.824 | 1.293 | 0.657 | 0.760 |

Values are `|recovered − Carroll| / Carroll`; **bold** = within the 40% calibration-grade band. The last row (`raw_fet w=0.01`) is the only experiment where `alpfe` enters cal-grade — at the cost of breaking `scav_rat`.

**Wave 3 follow-up (2026-05-12):** three additional experiments combined `raw_fet` with `PINN drift` to test whether the alpfe-scav_rat tradeoff could be broken. Result: **none beat 4/6.** Adding PINN drift cancels the `raw_fet` effect on alpfe. The iron-pair degeneracy under z-scored FeT loss is structural; resolution requires real-iron observations (PR #38, GEOTRACES IDP2025).

> **On the structural ceiling.** In every fit, the Green's-functions parametric class produces a constant prediction (r mathematically undefined) — the bound DarwinDiff sits above. Carroll's 6 calibrated values are bit-for-bit identical between v04 (Carroll 2020, Darwin 1) and v05 (Carroll 2022, Darwin 3), verified against the source namelists.

## Key findings to date

Deep dives live in [STATUS.md](STATUS.md) and [`docs/findings/`](docs/findings/). Compact highlights:

**Network capacity is not the recovery ceiling.** DINNDeep with 4-channel input (SST + MLD + wind + lat) drives the Eq Pacific FeT fit to r=1.000 (nb15), but recovered Carroll-6 values get FURTHER from Carroll's published — degenerate per-cell solutions. Ceiling is the box-model proxy, not the network.

**DINNDeep interpolates, doesn't extrapolate.** Block CV (W 2/3 train → E 1/3 test) gives held-out r=0.301 on FeT (nb16), reproducible across 5 seeds. For cross-basin claims, the SST-only DINN baseline is the more honest tool. Ensemble disagreement detects outlier cells but is overconfident in extrapolation territory (nb17, held-out stdev only 1.17× training stdev).

**Saturation generalizes; per-parameter recovery direction is target-specific.** Repeating the nb15 head-to-head on N Pacific Chl gives identical saturation (r=1.000, ~3000× lower loss) — but recovered means are mixed (3 closer to Carroll, 3 further). The ceiling is universal; the specific recovery bias depends on which tracer is fit (nb18).

**Multi-tracer joint loss helps where the evidence is direct.** Adding 4 Darwin tracer fields as simultaneous loss surfaces (nb19) fits all 4 with r ≥ 0.998, and brings 3/6 Carroll-6 parameters closer to published values (Smallgrow, Biggrow, R_PICPOC — those with direct tracer evidence). Iron pair stays 2–3× off Carroll because direct iron-pair constraints aren't in the joint set.

**Carbonate cycle fixes the iron pair in the 2-PFT proxy (v2.0 headline).** 7-tracer joint loss (DIC + ALK + air-sea CO₂ flux via [`carbonate.py`](src/darwindiff/carbonate.py) Follows-2006 solver) moves `alpfe` to **1.1% off** Carroll and `scav_rat` to **40% off**. Reproducible across DINN baseline + DINNDeep (nb20). Other 4 Carroll-6 parameters drift because the 5-tracer box can't simultaneously satisfy 7 Darwin field constraints.

**Carbonate is also a structural fix for spatial extrapolation.** Block CV on the 7-tracer setup gives test FeT r=0.637 — **more than double the 0.301 single-target baseline.** DIC and ALK extrapolate near-perfectly (test r > 0.97 with train-test gap < 0.02). DINN baseline is the right tool for parameter recovery; DINNDeep is the right tool for spatial generalization + fit quality (nb21).

**GLODAPv2.2016b real-obs hybrid validates the approach (v2.1 Phase 1).** Swapping Darwin DIC + ALK for GLODAP real ocean observations moves `R_PICPOC` from 360% off Carroll to 74% off — most dramatic single-parameter improvement on the project. Iron pair degrades under the obs swap (real Darwin-vs-reality coupling) (nb22, PR #36 open).

**Full 5-PFT box reaches the project-first 4/6 (v2.2 closeout).** Extending to the 5-PFT setup matching Darwin v05 (diatoms + large euks + Syn + Pro-LL + Pro-HL) + v2.4 PINN drift w=3.0 loss recovers `scav_rat`, `Biggrow`, `diatomgraz`, `R_PICPOC` at cal-grade. `alpfe` + `Smallgrow` remain stuck (nb23-29, PR #37 merged).

**Wave 3 confirms the alpfe-scav_rat degeneracy is structural under z-scored loss (2026-05-12).** Three additional experiments — `raw_fet w=0.005` + PINN drift, `raw_fet w=0.01` + PINN drift, PINN drift w=5.0 alone — failed to break the tradeoff. Path to 6/6 requires external observations: real iron from GEOTRACES IDP2025 (PR #38) breaks the degeneracy by setting the absolute iron scale that z-scored loss normalizes away.

## Background reading

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | Original ECCO-Darwin paper; defines the 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022](https://doi.org/10.1029/2021GB007162) (*GBC*) | ECCO-Darwin v05 application paper; inherits Carroll 2020's calibration bit-for-bit. The publicly-accessible ECCO-Darwin output is from this run, so it's our active recovery target. |
| [Brix et al. 2015](https://doi.org/10.1016/j.ocemod.2015.07.008) (*Ocean Modelling*) | Earlier ECCO-Darwin version; original biogeochemistry equations. |
| [Savelli et al. 2026](https://doi.org/10.5194/gmd-19-867-2026) (*GMD*) | Recent ECCO-Darwin update; explicitly flags fixed parameters DarwinDiff could relax. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*GBC*) | Core Darwin biogeochemistry formulation. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*Mon. Weather Review*) | The Green's-functions calibration method DarwinDiff replaces. |
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Method template — differentiable physics + per-location parameter network. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM, *Nature*) | Design reference for hybrid physics + ML emulators. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC) | Closest existing ocean-BGC ML — observation-driven NN emulator coupled to ROMS. DarwinDiff differs by being mechanistic (emulates Darwin rather than bypassing it) and parameter-aware. |

## Project arc

- **Track 1 — parameter recovery** (current)
  - v0.x → v0.95: synthetic-truth methodology validation (notebooks 05–08)
  - v1.0: real-data demo on GLODAP (notebook 09) and on Darwin Chl (notebook 10)
  - v1.1: cross-basin validation Mid-Atl + N Pacific (notebook 11)
  - v1.2: iron-pair recovery via Darwin FeT in HNLC (notebook 14)
  - v1.3: cross-basin Darwin NO₃ (notebook 13)
  - v1.4: architecture upgrade test (notebook 15) — pins recovery ceiling on box-model bias, not network
  - v1.5: cross-validation honesty check (notebook 16) — DINNDeep interpolates but doesn't extrapolate spatially
  - v1.6: ensemble-disagreement trust map (notebook 17) — useful for in-domain outlier flagging, fails as extrapolation detector
  - v1.7: cross-basin DINNDeep on N Pacific Chl (notebook 18) — saturation pattern generalises; per-parameter recovery direction is target-specific
  - v1.8: multi-tracer joint loss on Eq Pacific (notebook 19) — adding 4 tracer fields as joint loss surfaces partially collapses parameter degeneracy (3/6 closer to Carroll), iron pair stays underconstrained
  - v2.0: carbonate-extended box + 7-tracer joint loss (notebooks 20–21) — iron pair moves to within 1.1% (alpfe) and 40% (scav_rat) of Carroll's published. Robust across architectures. Other 4 parameters trapped by 5-tracer box-model proxy.
  - v2.1 Phase 1: GLODAPv2.2016b DIC + ALK hybrid (notebook 22, PR #36) — first real-observation hybrid; R_PICPOC dramatic improvement (360% → 74% off); iron pair degraded under the obs swap; validates the hybrid framework
  - **v2.2: full 5-PFT box-model extension (notebooks 23–29, PR #37)** — 22 experiments across z-scored loss, raw-FeT magnitude (7 weights), PINN balance (2), PINN drift (4), GLODAP combo, per-PFT K_FE, lumped mapping. **Headline: v2.4 PINN drift w=3.0 reaches 4/6 calibration-grade** — project's first 4/6. `alpfe` + `Smallgrow` confirmed structurally non-identifiable under current observation set. Wave 3 (raw_fet × PINN drift combos) running 2026-05-12 to probe the alpfe-scav_rat tradeoff. **Next local experiment:** PR #38 GEOTRACES IDP2025 loader — adds real-iron absolute-units observations to break the alpfe identifiability degeneracy.
  - **Gated on cluster compute:** full-ocean parameter recovery, time-resolved multi-year fitting, Track 2 emulator, forward Darwin validation of recovered `scav_rat = 3.95e-7`. Cluster prep complete (env-var-driven `DARWIN_DATA_ROOT`, SLURM templates in [`scripts/slurm/`](scripts/slurm/), compute spec in [`docs/cluster_setup.md`](docs/cluster_setup.md)); B200 burn-in pitch sent to MIT ORCD 2026-05-10. See [STATUS.md](STATUS.md) for the live checklist.

- **Track 2 — emulator** (not started)
  - Will be a separate architecture (likely transformer / FNO / graph net with spatial coupling), trained on time-resolved Darwin output. Different problem from parameter recovery — different network. Notes in STATUS.md once it begins.

## Repository layout

```
ecco-darwindiff/
├── README.md                  this file (project overview)
├── STATUS.md                  living status doc — checklists + key findings
├── LICENSE                    MIT
├── pyproject.toml             package details + dependencies
├── src/darwindiff/            Python package (importable as `darwindiff`)
│   ├── carroll6.py              5-tracer Carroll-6 box model + Carroll's optima + bounds
│   ├── carbonate.py             Follows-2006 carbonate solver + Wanninkhof 2014 CO₂ flux (v2.0)
│   ├── carroll6_5pft.py         10-tracer / 5-PFT box matching Darwin v05 (v2.2; optional per-PFT K_FE + lumped/specific mapping)
│   ├── networks.py              DINN (per-cell 1×1 conv) + DINNRegional (MLP) + DINNDeep
│   ├── diagnostics.py           NaN-safe Pearson r + constant-prediction handling
│   ├── budget.py                compute / memory budget calculators
│   ├── ecco_darwin_loader.py    ECCO-Darwin v5 bin_average product (1° NetCDF) loader + AOI presets
│   ├── llc270_loader.py         ECCO-Darwin v5 native LLC270 monthly tracer loader (xmitgcm-based)
│   └── glodap_loader.py         GLODAPv2.2016b real-obs DIC/ALK loader (v2.1; cherry-picked into both PR #36 and PR #37 by design)
├── tests/                     pytest suite (154 passed, 5 skipped opt-in real-data)
├── notebooks/                 numbered notebooks 05–29, in order of project arc (latest: nb29 v2.4 PINN drift 4/6 winner)
├── docs/                      decision log + chronological findings docs
│   └── findings/                v2_track1_closeout.md (v2.0), v2.1_phase1_glodap.md, v2.2_phase2.md, v2.2_overnight_summary.{md,csv}
├── data/                      local data cache (gitignored except README.md; see data/README.md for canonical URLs)
├── scripts/                   build_nb23.py (configurable notebook builder), overnight_run.ps1 / overnight_wave2.ps1 (sequential overnight queues), multiseed_v2_4_drift_w3.ps1 (winner robustness), wave3_alpfe_push.ps1 (Wave 3 push), overnight_summary.py (idempotent aggregator), phase2_p4_p5_check.py (prereqs), slurm/ (cluster job templates)
├── CONTRIBUTING.md            branch convention, commit/PR title format, no Co-Authored-By rule
└── references/                PDFs + external code references (gitignored content)
```

## Installation

Needs Python 3.11+. With uv:

```bash
uv sync
uv run pytest -q   # 154 passed, 5 skipped (opt-in real-data tests)
```

All runtime deps (including `xmitgcm` for the native LLC270 loader) are pinned in `pyproject.toml` and installed by `uv sync`.

For cluster runs, set `DARWIN_DATA_ROOT` to point at the LLC270 monthly tree (default keeps the local Windows behaviour):

```bash
export DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5
```

See [`docs/cluster_setup.md`](docs/cluster_setup.md) for the full operational guide.

## Data sources

See [data/README.md](data/README.md) for the full annotated index and Jon Lauderdale's authoritative URLs (decoded from his 2026-05-11 email). Summary:

### In active use

| Source | Use | Canonical URL |
|---|---|---|
| ECCO-Darwin v05 `bin_average` (1° NetCDF) | Carroll-6 fits via Chl + carbonate diagnostics, nb09-29 | https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC90/ECCO-Darwin/ (Jon's canonical) · NAS mirror used in 2026-05: https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/ |
| ECCO-Darwin v05 native LLC270 monthly tracers | Carroll-6 fits via depth-resolved NO₃ / DIC / ALK / FeT etc., nb13-19 | https://ecco.jpl.nasa.gov/drive/files/ECCO2/LLC270/ECCO-Darwin_extension/ (Jon's canonical) · NAS mirror: https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/ |
| GLODAPv2.2016b mapped | DIC / ALK real-obs hybrid, nb22 (PR #36) | https://glodap.info (2.2023 recommended by Jon for upgrade) |
| NASA GHG Center CO₂ flux GeoTIFFs | Future CO₂ flux validation | https://earth.gov/ghgcenter/data-catalog/eccodarwin-co2flux-monthgrid-v5 |

### Planned (Jon's email 2026-05-11)

| Source | Unblocks | URL |
|---|---|---|
| **GEOTRACES IDP2025** | **alpfe identifiability (PR #38)** | https://www.geotraces.org/idp2025/ |
| GLODAPv2.2023 | Refines carbonate signal vs v2.2016b | https://glodap.info/index.php/merged-and-adjusted-data-product-v2-2023/ |
| Ocean color (NASA OB.DAAC / OC-CCI) | Smallgrow target via PFT-specific Chl | https://oceancolor.gsfc.nasa.gov/ |
| BGC-Argo | Wave 4 time-resolved + depth-resolved BGC | https://biogeochemical-argo.org/data-access.php |
| SOCAT 2025 | Surface CO₂ flux refinement | https://socat.info/index.php/version-2025/ |
| WOD / WOA | Background T/S + nutrients | https://www.ncei.noaa.gov/products/world-ocean-database |

Raw data files are stored outside the repo (`D:\ecco_darwin_v5\` on the local dev machine). All loaders respect the `DARWIN_DATA_ROOT` / `GLODAP_DATA_ROOT` env vars for cluster portability. We don't mirror raw third-party data to GitHub or Hugging Face — see [data/README.md](data/README.md) § "Hosting decision".

## Documentation discipline

Every major code or scientific change should update **both** [README.md](README.md) (project overview, framing for new readers) and [STATUS.md](STATUS.md) (live checklist + findings) in the same PR. Keeps the docs from drifting.

## License

MIT — see [LICENSE](LICENSE). © 2026 ECCO-DarwinDiff contributors.

## Citation

Project is in active development; formal citation TBD once results are published or a Zenodo DOI is created. If your work depends on the underlying ECCO-Darwin model, please cite:

```
Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S.,
et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model:
Estimates of seasonal to multidecadal surface ocean pCO2 and air-sea CO2 flux.
Journal of Advances in Modeling Earth Systems, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888

Carroll, D., Menemenlis, D., Dutkiewicz, S., Lauderdale, J. M., Adkins, J. F.,
Bowman, K. W., et al. (2022). Attribution of space-time variability in
global-ocean dissolved inorganic carbon. Global Biogeochemical Cycles, 36,
e2021GB007162. https://doi.org/10.1029/2021GB007162
```
