# DarwinDiff — Project Status

Live status doc. Headlines reflect verified results at the current project version. Per-version technical detail lives in [`docs/findings/`](docs/findings/) and individual PR threads.

## Current state — Track 1 v3.1

DarwinDiff replaces ECCO-Darwin's Green's-functions Carroll-6 calibration with gradient descent through a differentiable box model, predicted by a per-cell neural network. Active at **3-AOI multi-AOI joint training** (Equatorial Pacific + N Atlantic Subpolar + Southern Ocean Pacific) on a single workstation (NVIDIA RTX 5090 32 GB).

**Verified results from the v3.1 sweep set** (837 seeds across 84 configs, outputs in `D:\runs\bcr_*\`):

- **Basin C iron-pair recovery is reproducible at n=40, 38/40 (95%).** Four independent 10-seed batches at the F2 Basin C config (POSI_W=1.0 + AOI_W_NATLSUBPOLAR=2.0 + AOI_W_SOUTHERNOCEANPAC=2.0 + CHL1_W_EXTRA=3.0). Per-batch iron-pair counts: 10/10, 10/10, 10/10, 8/10.
- **Two 5/6 Cal-grade single-seed events** out of 837 seeds (0.24% break rate, both unreproduced at scale):
  - `w2e_peraoi_lam0.1` seed 3: PER_AOI_DINN + CONSISTENCY_LAMBDA=0.1 at Basin C base. Recovers alpfe (Excellent) + scav_rat + Smallgrow + Biggrow + diatomgraz; R_PICPOC drifts. Wave 5 dose-response (CONSISTENCY_LAMBDA ∈ {0.05, 0.15, 0.20, 0.30}) and n=20 extension (seeds 10-19 at the same config) produced 0 additional 5/6.
  - `c_chl40_posi15` seed 9: CHL1_W_EXTRA=4.0 + POSI_W=1.5 at Basin C base. Recovers alpfe + scav_rat (Excellent) + Smallgrow + Biggrow + R_PICPOC; diatomgraz drifts. Not yet n=20 retested.
- **Binary mutex confirmed at low PIC dose.** Any nonzero `PIC_ABS_W` (tested down to 0.02) wipes iron-pair recovery → 0/10, regardless of POC pair. `POC_ABS_W` alone also kills iron pair, with different downstream basin geometry (mean_cal grows with POC dose; opposite of paired PIC+POC).

The structural 5/6 ceiling holds at 2/837 across all v3.1 work. Both 5/6 events recover complementary param subsets (one lands diatomgraz, the other R_PICPOC) which suggests combining their interventions is the natural test for a 6/6 candidate, but the unreproducibility of either at n=20 means the headline finding is **the ceiling itself, not the break**.

## Headline results

| Version | AOI | Config | Best result | Source |
|---|---|---|---|---|
| v3.1 (Wave 2) | 3-AOI | `w2e_peraoi_lam0.1` | 1/10 seeds at 5/6; alpfe Excellent + scav_rat + Smallgrow + Biggrow + diatomgraz Cal | bcr_w2_/w2e_peraoi_lam0.1/ |
| v3.1 (Wave 3) | 3-AOI | `c_chl40_posi15` | 1/10 seeds at 5/6; alpfe + scav_rat Excellent + Smallgrow + Biggrow + R_PICPOC Cal | bcr_w3_/c_chl40_posi15/ |
| v3.1 (n=40 extension) | 3-AOI | F2 Basin C base | 38/40 iron-pair Cal+ across four 10-seed batches | bcr_*/arc6_basinC_seeds10-19/, /w2f_basinC_seeds20-29/, /e_basinC_seeds30-39/ |
| v3.0 baseline (PR #57) | 2-AOI | AOI ID + GEO POC=0.5 + hd=32 + NAtl_W=2.0 | 7/15 seeds at 5/6 Cal-grade; mean_cal=3.93 | nb32 |
| v2.8 | Eq Pac | Darwin v5 ICs + L2 POC z-score | 7/10 Cal-grade scav_rat (4/10 Excellent); aggregate 6/10 at 4/6 | docs/findings/v2.8_darwin_ic_poc_sub.md |
| v2.6 | Eq Pac | GEOTRACES_W=0.3 + PINN drift w=3.0 | 4/6 Cal-grade reproducible across n=10; Smallgrow 9/10 Cal+ | PR #40 |
| v2.4 | Eq Pac | 5-PFT + PINN drift w=3.0 | 4/6 Cal-grade — project-first | nb29 |
| v2.1 Phase 1 | Eq Pac | GLODAP DIC + ALK hybrid | R_PICPOC 360% → 74% off Carroll | PR #41 (nb22) |
| v2.0 | Eq Pac | 7-tracer carbonate joint loss | Iron pair to 1.1% (alpfe) / 40% (scav_rat) off Carroll | nb20-21 |

## Version chronology

- **v0.x → v1.8** (nb 05–19): synthetic-truth methodology validation, real-data demos on GLODAP and Darwin Chl, cross-basin verification (Mid-Atl + N Pacific), iron-pair recovery via Darwin FeT in HNLC, multi-tracer joint loss partial collapse of parameter degeneracy.
- **v2.0** (nb 20–21): carbonate cycle (`carbonate.py` Follows-2006 solver + Wanninkhof 2014 air-sea flux); 7-tracer joint loss moves iron pair to 1.1% / 40% off Carroll. Robust across DINN baseline + DINNDeep.
- **v2.1 Phase 1** (nb 22, PR #41): GLODAPv2.2016b real-obs DIC + ALK hybrid; R_PICPOC dramatic improvement, iron pair degraded under obs swap.
- **v2.2** (nb 23–29, PR #37): full 5-PFT box matching Darwin v05; 22 experiments; v2.4 PINN drift w=3.0 reaches 4/6 calibration-grade. `alpfe` confirmed structurally stuck under z-scored loss without absolute iron observations.
- **v2.5** (PR #39): GEOTRACES IDP2025 loader scaffold validated against real NetCDF schema.
- **v2.6** (PR #40): GEOTRACES dissolved-iron absolute-units MSE loss; 4/6 Cal-grade reproducibly across n=10; Smallgrow at 9/10 Cal+. Reframes v2.2's "alpfe + Smallgrow are structurally stuck" claim.
- **v2.7** (PR #42): 2-layer (0–50 m + 50–1000 m) box with sinking-POC iron + Kz + subsurface remineralisation. Subsurface DFe anchoring alone does NOT unblock scav_rat.
- **v2.8** (PR #45): Darwin v5 pickup ICs + L2 POC z-score loss. Project-first reproducible scav_rat recovery (7/10 Cal-grade, 4/10 Excellent). Reveals bimodal degeneracy in (alpfe, scav_rat) selected by `POC_SUB_W`.
- **v3.0** (PRs #46–#59): joint multi-AOI training across Eq Pac + N Atl Subpolar with a shared Carroll-6. Establishes the 5/6 plateau across 50+ seeds. Architectural (PR #58: per-AOI DINNs falsified at 2-AOI) and observational-anchor (PR #59: PIC_ABS + POC_ABS paired anchors underperform baseline) break attempts all empirically falsified. 5/6 ceiling characterized as **parameter conservation**: the observations support ~5 effective constraints on 6 parameters; the 6th is always the residual sink, and loss weighting decides which.
- **v3.1** (PR #64+): Southern Ocean Pacific added as 3rd AOI; Basin C iron-pair 38/40 at n=40; two complementary 5/6 paths via PER_AOI_DINN at low CONSISTENCY_LAMBDA and via CHL1_W + POSI_W combo tuning. PER_AOI_DINN was falsified at 2-AOI; 3-AOI behavior is new and material.
- **Cluster-gated**: full-ocean parameter recovery, time-resolved multi-year fitting, Track 2 emulator, forward Darwin validation. See [docs/cluster_setup.md](docs/cluster_setup.md).

## Architecture

DarwinDiff is a per-cell neural network `env → 6 Carroll-6 params` trained by gradient descent through a differentiable box model. Architecture details in [docs/dinn_design.md](docs/dinn_design.md).

- **Networks**: `DINN` (~454 weights, SST-only, baseline for structural argument), `DINNDeep` (~9.4K weights, 4-channel, saturates on biomass tracers), `DINNRegional` (legacy, superseded).
- **Box model**: 5-PFT 2-layer integrator (`src/darwindiff/carroll6_5pft_2layer.py`) extending the original 5-tracer proxy. Includes carbonate chemistry (`src/darwindiff/carbonate.py`, Follows 2006 solver + Wanninkhof 2014 air-sea flux).
- **Multi-AOI joint training (v3.0+)**: shared DINN with optional per-AOI identity channel (`AOI_ID_CHANNEL=1`), per-AOI loss weights (`AOI_W_<KEY>`), optional per-AOI DINN architecture (`PER_AOI_DINN=1` + `CONSISTENCY_LAMBDA=λ`).
- **Loss components**: z-scored MSE per-AOI per-tracer (`GEOTRACES_W`, `POC_SUB_W`, `NB23_PINN_WEIGHT`, `NB23_FET_WEIGHT`), absolute-units anchors (`PIC_ABS_W`, `POC_ABS_W`, `F_CO2_ABS_W`), positivity loss (`POSI_W`), extra diatom-chl weight (`CHL1_W_EXTRA`).
- **Optimization**: Adam at lr=5e-3, 1500 epochs (extendable via `NB23_N_EPOCHS`). Forward-Euler integrator (`DT=0.25`, `N_STEPS=200`).
- **Recovery scoring**: Cal-grade if `|recovered − Carroll| / Carroll ≤ 0.40`; Excellent if `≤ 0.10`; Loose / Drifted otherwise. Six Carroll-6 params: `alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC`. Carroll's published values bit-identical between v04 (JAMES) and v05 (GBC).

## 5/6 ceiling — structural diagnosis

Across 757 seeds in v3.1, only 2 broke the 5/6 ceiling. Different interventions shift WHICH parameter is the dominant 5/6 miss:

| Family | Dominant 5/6 miss | Mechanism |
|---|---|---|
| Baseline (PR #57, 2-AOI) | `diatomgraz` | Chl1 z-score under-constrains diatom-specific growth |
| Per-AOI DINN (PR #58, 2-AOI) | `R_PICPOC` | Shared-MLP regularization removed; basin selection collapses |
| PIC alone (PR #59) | `alpfe + scav_rat` | Magnitude anchor on PIC competes with iron budget |
| Paired POC+PIC (PR #59) | `alpfe + scav_rat` | Both anchors disturb iron budget |
| PER_AOI + low λ at 3-AOI (v3.1 w2e) | `R_PICPOC` | Same family as PR #58 but the 3rd AOI breaks the basin lock |
| CHL1 + POSI combo at 3-AOI (v3.1 c_chl40_posi15) | `diatomgraz` | Loss reweighting lands R_PICPOC while losing diatomgraz |

The two v3.1 5/6 paths recover complementary param subsets (one lands diatomgraz, the other lands R_PICPOC). Combining their interventions in a single config is the obvious next test for a 6/6 candidate.

The mutex between iron-pair recovery and R_PICPOC recovery is binary in PIC anchor presence (not magnitude): any nonzero `PIC_ABS_W` wipes iron pair regardless of dose. The PER_AOI architectural lever produces 5/6 without invoking that mutex — orthogonal axis.

## Methodology rules

- **Compare against Carroll's published Green's-functions optima**, not against prior notebooks. The headline is "did the parameter learner catch the goal?", not "did this version beat the previous one." Inter-version deltas are supplementary methodology context.
- **Train DINN baseline only by default from v2.2.x onward.** DINNDeep saturates trivially on biomass tracers (r → 1.0) and recovers fewer calibration-grade Carroll-6 params than the baseline; halves wall-clock per fit. The dual-architecture framing remains useful for the v2.0 saturation-ceiling argument.
- **Recovery analyses report n=10 minimum and disclose seed variance** in any headline claim. Avoid single-seed framing; n=5 medians can hide bimodality.

## Cluster path

Engaging is the active onboarding target. AICR (B200 beta, MIT ORCD) opens for users with prior Engaging experience. Detailed setup, partitions, storage, and SLURM templates in [docs/cluster_setup.md](docs/cluster_setup.md).

The cluster path unlocks: native LLC270-resolution recovery (vs the 1° box-model proxy), time-resolved multi-year fitting, n=20–50 multi-seed ensembles, full-ocean parameter recovery sweeps, and Track 2 emulator development.

## Known limitations

- **Box model is a 5-tracer proxy** of full Darwin 3. The 5-PFT + 2-layer extensions close part of the gap; cluster-scale native-resolution recovery is the planned next reduction.
- **DINN is per-cell, not spatially coupled.** Advection / diffusion between cells is ignored — appropriate for parameter recovery but not for the Track 2 emulator.
- **DINNDeep does not extrapolate spatially.** Block CV gives held-out r=0.301 vs in-distribution r=1.000 on FeT. Use DINN baseline for cross-AOI extrapolation claims.
- **Climatology, not time-resolved.** All current fits use 23-year time-mean Darwin output.
- **Windows MAX_PATH=260.** Long config-name + filename combinations crash JSON writes after training succeeds. `scripts/recover_failed_config_log.py` reconstructs from `.log` files; sweep orchestration uses short OUTPUT_DIR prefixes (`D:\runs\bcr_<stamp>\`) to stay under the limit.
- **Laptop sleep on Windows** suspends background Python processes during overnight runs. Use `powercfg /change standby-timeout-ac 0` for unattended runs.

## Cross-references

- [README](README.md) — project overview
- [docs/dinn_design.md](docs/dinn_design.md) — DINN architecture, training loop, structural argument
- [docs/cluster_setup.md](docs/cluster_setup.md) — MIT ORCD Engaging + AICR setup
- [data/README.md](data/README.md) — dataset provenance and download mechanics
- [.claude/skills/README.md](.claude/skills/README.md) — project-scoped Claude Code skill bundle
- [docs/findings/](docs/findings/) — per-version technical writeups
