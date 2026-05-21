# ECCO-DarwinDiff

A PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model that lets gradients flow through every step of the simulation. Built for two related uses:

1. **Parameter learner** — a faster, richer replacement for ECCO-Darwin's Green's-functions calibration. Where Carroll 2020 / 2022 tunes one global vector of 6 biogeochemical parameters via expensive multi-decadal forward runs, DarwinDiff learns a *function* mapping local environmental conditions to a per-cell parameter vector via gradient descent through a differentiable box model.
2. **Emulator** — a neural-network stand-in for ECCO-Darwin trained on the same Darwin output, for long-timescale climate runs the full model is too slow for. Not started yet — Track 2.

## Status

**Track 1 v3.1 — two 5/6 paths in 3-AOI training (2026-05-20):**

Two distinct 5/6 Cal-grade seeds in 3-AOI joint training (Eq Pac + N Atl Subpolar + Southern Ocean Pacific), out of **757 seeds across 76 configs**:

- `w2e_peraoi_lam0.1` seed 3: PER_AOI_DINN + CONSISTENCY_LAMBDA=0.1 at Basin C base. Recovers alpfe (Excellent) + scav_rat + Smallgrow + Biggrow + diatomgraz; R_PICPOC drifts.
- `c_chl40_posi15` seed 9: CHL1_W_EXTRA=4.0 + POSI_W=1.5 at Basin C base. Recovers alpfe + scav_rat (Excellent) + Smallgrow + Biggrow + R_PICPOC; diatomgraz drifts.

Both retain the iron pair; they lose complementary params (diatomgraz vs R_PICPOC). Iron-pair Basin C baseline is **38/40 reproducible across n=40** (four 10-seed batches: 10/10, 10/10, 10/10, 8/10). The structural 5/6 ceiling from v3.0 still holds at a **2/757 break rate**.

Cluster path opening: MIT ORCD AICR (B200) beta access discussion in progress (Engaging cluster experience is the prerequisite).

> See [STATUS.md](STATUS.md) for the live state, per-version findings, and the full chronological project arc.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*; Carroll et al. 2022, *GBC*) is a global ocean biogeochemistry model on the ECCO LLC270 grid (~1/3° at the equator, ~18 km at high latitudes, 50 vertical levels), 1992–2017+. Its biogeochemistry is calibrated via **Green's functions** (Menemenlis et al. 2005), which scales linearly badly: each tuned parameter needs a fresh full forward run, so Carroll's published calibration handles only **6 parameters** (iron dust solubility, iron scavenging rate, small + large phytoplankton growth rates, diatom palatability, PIC/POC ratio).

DarwinDiff replaces the biogeochemistry side of this with **PyTorch autograd**: gradients for all parameters are computed in one backward pass, and the parameter values themselves vary across space — predicted by a small per-cell neural network (DINN) from local environmental conditions (SST + MLD + wind + lat). The structural argument: a single global parameter vector cannot reproduce spatial heterogeneity in ocean biogeochemistry; per-cell parameters can.

> **Design details:** [`docs/dinn_design.md`](docs/dinn_design.md) — per-cell architecture, training loop, structural-ceiling argument, DINN vs DINNDeep variants.
> **Cluster setup:** [`docs/cluster_setup.md`](docs/cluster_setup.md) — compute requirements, environment setup, LLC270 transfer plan, ORCD open questions.

## Project arc (one-line per version)

- **v0.x → v1.8** (notebooks 05–19): methodology validation, real-data demos, cross-basin verification, multi-tracer joint loss.
- **v2.0** (nb20-21): carbonate cycle moves iron pair to 1.1% / 40% off Carroll in the 2-PFT proxy.
- **v2.1** (nb22, PR #41): GLODAP real-obs hybrid; `R_PICPOC` 360% → 74% off.
- **v2.2** (nb23-29, PR #37): full 5-PFT box matching Darwin v05; project-first 4/6 Cal-grade.
- **v2.6** (PR #40): GEOTRACES IDP2025 iron loss; 4/6 reproducibly across n=10.
- **v2.7** (PR #42): vetted 2-layer integrator; subsurface DFe alone does not unblock scav_rat.
- **v2.8** (PR #45): Darwin v5 ICs + L2 POC obs; project-first reproducible scav_rat recovery.
- **v3.0** (PRs #46-#59): multi-AOI joint training; 5/6 plateau characterized as parameter conservation.
- **v3.1** (PR #64): 3-AOI Basin C + PER_AOI_DINN; two complementary 5/6 paths (see Status).
- **Gated on cluster compute:** full-ocean parameter recovery, time-resolved fitting, Track 2 emulator, forward Darwin validation of recovered `scav_rat`.

## Repository layout

```
ecco-darwindiff/
├── README.md                  this file (project overview)
├── STATUS.md                  living status doc — checklists + findings
├── CONTRIBUTING.md            branch + commit + PR conventions
├── LICENSE                    MIT
├── pyproject.toml             package + dependencies
├── src/darwindiff/            Python package (importable as `darwindiff`)
│   ├── carroll6.py              5-tracer Carroll-6 box + Carroll's optima + bounds
│   ├── carbonate.py             Follows-2006 carbonate solver + Wanninkhof 2014 CO₂ flux
│   ├── carroll6_5pft.py         10-tracer / 5-PFT box matching Darwin v05
│   ├── carroll6_5pft_2layer.py  v2.7 2-layer integrator
│   ├── networks.py              DINN + DINNRegional + DINNDeep
│   ├── ecco_darwin_loader.py    Darwin v05 bin_average loader + AOI presets (eqpac, natlsubpolar, southernoceanpac)
│   ├── llc270_loader.py         native LLC270 monthly tracer loader (xmitgcm)
│   ├── glodap_loader.py         GLODAPv2.2016b DIC/ALK loader
│   ├── modis_pic_loader.py      MODIS-Aqua PIC loader (shelved for leapfrog phase)
│   └── pace_loader.py           PACE carbon_phyto loader (shelved for leapfrog phase)
├── scripts/                   runners (`run_v3.0_*.py`), overnight sweep orchestration
│                              (`overnight_v3.0_basinC_*.py`), analysis (`analyze_*.py`),
│                              recovery (`recover_failed_config_log.py`), SLURM templates
├── notebooks/                 numbered notebooks 05–32, in order of project arc
├── tests/                     pytest suite (run via `uv run pytest -q`)
├── docs/                      decision log + chronological findings docs
│   ├── findings/                per-version technical writeups
│   ├── research_notes/          dated investigation notes
│   ├── dinn_design.md           architecture + training loop
│   └── cluster_setup.md         compute spec + ORCD open questions
├── data/                      local data cache (gitignored except README.md)
└── .claude/skills/            project-scoped Claude Code skill bundle (darwin_v05_loader,
                               darwin_dinn_sweep_orchestrator, + 4 vendored lit-search skills)
```

## Installation

Needs Python 3.11+. With `uv`:

```bash
uv sync
uv run pytest -q
```

All runtime deps (including `xmitgcm` for the native LLC270 loader) are pinned in `pyproject.toml`.

For cluster runs, set `DARWIN_DATA_ROOT` to point at the LLC270 monthly tree:

```bash
export DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5
```

See [`docs/cluster_setup.md`](docs/cluster_setup.md) for the full operational guide.

## Data sources

See [data/README.md](data/README.md) for the annotated index and canonical URLs.

**In active use:** ECCO-Darwin v05 (`bin_average` 1° NetCDF + native LLC270 monthly), GLODAPv2.2016b, NASA GHG Center CO₂ flux, GEOTRACES IDP2025.

**Planned / shelved for leapfrog phase:** GLODAPv2.2023, ocean color (NASA OB.DAAC / OC-CCI), BGC-Argo, SOCAT 2025, WOD / WOA, MODIS-Aqua PIC, PACE carbon_phyto.

Raw data files are stored outside the repo. All loaders respect `DARWIN_DATA_ROOT` / `GLODAP_DATA_ROOT` env vars for cluster portability.

## Background reading

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | Original ECCO-Darwin paper; 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022](https://doi.org/10.1029/2021GB007162) (*GBC*) | ECCO-Darwin v05 application paper; inherits Carroll 2020's calibration bit-for-bit. Active recovery target. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) | The Green's-functions calibration method DarwinDiff replaces. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) | Core Darwin biogeochemistry formulation. |
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Method template — differentiable physics + per-location parameter network. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM) | Hybrid physics + ML emulator design reference. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC) | Closest existing ocean-BGC ML; DarwinDiff differs by being mechanistic + parameter-aware. |

## License

MIT — see [LICENSE](LICENSE). © 2026 ECCO-DarwinDiff contributors.

## Citation

Formal citation TBD once results are published or a Zenodo DOI is created. If your work depends on the underlying ECCO-Darwin model, please cite Carroll et al. 2020 (*JAMES*, doi:10.1029/2019MS001888) and Carroll et al. 2022 (*GBC*, doi:10.1029/2021GB007162).
