<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

[![python][py_img]][py_url]
[![license][lic_img]][lic_url]
[![status][status_img]][status_url]

A differentiable PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry
model. Gradients flow through every step of the simulation, so the same loss surface
can learn parameters that Carroll's Green's-functions calibration tunes one-at-a-time.

[Status][status_url] · [Design][design_url] · [Cluster setup][cluster_url] · [Data][data_url] · [Skills][skills_url] · [Demo][demo_url]

</div>

## Two tracks

1. **Parameter learner** — replaces ECCO-Darwin's Green's-functions calibration. Where Carroll 2020 / 2022 tunes a global 6-parameter vector via expensive multi-decadal forward runs, DarwinDiff learns a *function* mapping local environmental conditions to a per-cell parameter vector via gradient descent through a differentiable box model.
2. **Emulator** — neural-network stand-in for ECCO-Darwin for long-timescale climate runs. Not started yet.

## Status — Track 1 v3.1

3-AOI joint training (Eq Pac + N Atl Subpolar + Southern Ocean Pacific) across **857 seeds in 86 configs**:

- **Basin C iron-pair recovery: 38/40 (95%) at n=40** across four independent 10-seed batches.
- **Two 5/6 Cal-grade single-seed events** (unreproduced at scale, 2/857 = 0.23% break rate):
  - `w2e_peraoi_lam0.1` seed 3: PER_AOI_DINN + low CONSISTENCY_LAMBDA. Recovers iron pair + 3 phyto/grazing; misses R_PICPOC. Wave 5 dose-response + n=20 extension produced 0 additional 5/6.
  - `c_chl40_posi15` seed 9: CHL1_W + POSI_W combo. Recovers iron pair + Smallgrow + Biggrow + R_PICPOC; misses diatomgraz. n=20 retest at seeds 10-19 produced 0 additional 5/6 (combined: 1/20).
- **Composition test of the two 5/6 recipes fails (Wave 6).** Stacking both intervention families → 0/10 at 5/6, mean_cal 2.00 (worse than either parent 2.40 / 2.70). Iron pair survives (9/10) but R_PICPOC and diatomgraz both drift, Smallgrow + Biggrow regress. Interventions interfere.
- **Binary mutex confirmed at low PIC dose**: any `PIC_ABS_W ≥ 0.02` wipes iron pair regardless of magnitude or POC pairing.

The structural 5/6 ceiling is the headline finding, now supported by four independent pieces of evidence: 0/857 at 6/6 across 86 single-lever configs, both 5/6 events independently confirmed unreproduced at n=20 (each 1/20), and the composition test of the two complementary 5/6 lever families fails. v3.0's parameter-conservation framing is fully strengthened. Cluster path via MIT ORCD AICR (B200) is opening; Engaging cluster experience is the prerequisite.

See [STATUS.md][status_url] for live state and per-version findings.

## Quick start

```bash
uv sync
uv run pytest -q
```

For cluster runs, set `DARWIN_DATA_ROOT` to the LLC270 tree:

```bash
export DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5
```

See [docs/cluster_setup.md][cluster_url] for the operational guide.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*; Carroll et al. 2022, *GBC*) is calibrated via **Green's functions** (Menemenlis et al. 2005), which scales linearly badly: each tuned parameter needs a fresh full forward run, so Carroll's published calibration handles only **6 parameters**. DarwinDiff replaces the biogeochemistry side with **PyTorch autograd**: gradients for all parameters in one backward pass, and the parameter values themselves vary across space — predicted by a small per-cell network (DINN) from local environmental conditions.

<details>
<summary><b>Project arc (one-line per version)</b></summary>

- **v0.x → v1.8** (nb 05–19): methodology validation, real-data demos, cross-basin verification, multi-tracer joint loss.
- **v2.0** (nb20-21): carbonate cycle moves iron pair to 1.1% / 40% off Carroll.
- **v2.1** (nb22, PR #41): GLODAP real-obs hybrid; `R_PICPOC` 360% → 74% off.
- **v2.2** (nb23-29, PR #37): full 5-PFT box matching Darwin v05; project-first 4/6 Cal-grade.
- **v2.6** (PR #40): GEOTRACES IDP2025 iron loss; 4/6 reproducibly across n=10.
- **v2.7** (PR #42): vetted 2-layer integrator.
- **v2.8** (PR #45): Darwin v5 ICs + L2 POC obs; project-first reproducible scav_rat recovery.
- **v3.0** (PRs #46-#59): multi-AOI joint training; 5/6 plateau as parameter conservation.
- **v3.1** (PR #64): 3-AOI Basin C + PER_AOI_DINN; two complementary 5/6 paths.
- **Gated on cluster:** full-ocean recovery, time-resolved fitting, Track 2 emulator.

</details>

<details>
<summary><b>Repository layout</b></summary>

```
src/darwindiff/            Python package (importable as `darwindiff`)
  carroll6.py                5-tracer Carroll-6 box + Carroll's optima + bounds
  carbonate.py               Follows-2006 + Wanninkhof 2014 carbonate solver
  carroll6_5pft.py           10-tracer / 5-PFT box matching Darwin v05
  carroll6_5pft_2layer.py    v2.7 2-layer integrator
  networks.py                DINN + DINNRegional + DINNDeep
  ecco_darwin_loader.py      Darwin v05 1° loader + AOI presets
  llc270_loader.py           native LLC270 monthly loader (xmitgcm)
  glodap_loader.py           GLODAPv2.2016b DIC/ALK loader
  modis_pic_loader.py        MODIS-Aqua PIC (shelved for leapfrog)
  pace_loader.py             PACE carbon_phyto (shelved for leapfrog)
scripts/                   runners, overnight sweeps, analysis, SLURM templates
notebooks/                 numbered notebooks 05–32, in arc order; demo_colab.ipynb is the synthetic-recovery walkthrough
tests/                     pytest suite
docs/                      findings, research_notes, dinn_design.md, cluster_setup.md
.claude/skills/            project-scoped skill bundle
```

</details>

<details>
<summary><b>Data sources</b></summary>

**In active use:** ECCO-Darwin v05 (`bin_average` 1° NetCDF + native LLC270 monthly), GLODAPv2.2016b, NASA GHG Center CO₂ flux, GEOTRACES IDP2025.

**Shelved for the leapfrog phase:** GLODAPv2.2023, ocean color (OB.DAAC / OC-CCI), BGC-Argo, SOCAT 2025, WOD / WOA, MODIS-Aqua PIC, PACE carbon_phyto.

Raw data files live outside the repo. Loaders respect `DARWIN_DATA_ROOT` / `GLODAP_DATA_ROOT` env vars. See [data/README.md][data_url] for canonical URLs.

</details>

<details>
<summary><b>Background reading</b> (all DOIs verified via OpenAlex)</summary>

**ECCO-Darwin lineage (active recovery target):**

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | Original ECCO-Darwin paper; the 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022](https://doi.org/10.1029/2021GB007162) (*GBC*) | ECCO-Darwin v05; the publicly-accessible Darwin output is our active recovery target. |
| [Brix et al. 2015](https://doi.org/10.1016/j.ocemod.2015.07.008) (*Ocean Modelling*) | Earlier ECCO-Darwin BGC, using Green's-functions to initialize/adjust the model. |
| [Savelli et al. 2026](https://doi.org/10.5194/gmd-19-867-2026) (*GMD*) | Most recent ECCO-Darwin update; riverine biogeochemical inputs. |

**Box-model physics & chemistry (in `src/darwindiff/`):**

| Reference | Used in |
|---|---|
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*GBC*) | Core Darwin biogeochemistry equations (`carroll6.py`, `carroll6_5pft.py`). |
| [Follows, Ito, Dutkiewicz 2006](https://doi.org/10.1016/j.ocemod.2005.05.004) (*Ocean Modelling*) | Iterative carbonate-system solver implemented in `carbonate.py`. |
| [Wanninkhof 2014](https://doi.org/10.4319/lom.2014.12.351) (*L&O Methods*) | Wind-speed–gas-exchange coefficient for air-sea CO₂ flux in `carbonate.py`. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*MWR*) | The Green's-functions calibration method DarwinDiff replaces. |

**Observational data (loaders + losses):**

| Reference | Used in |
|---|---|
| [Olsen et al. 2016](https://doi.org/10.5194/essd-8-297-2016) (*ESSD*) | GLODAPv2 mapped DIC/ALK in `glodap_loader.py` (v2.1, PR #41). |
| [Schlitzer et al. 2018](https://doi.org/10.1016/j.chemgeo.2018.05.040) (*Chemical Geology*) | GEOTRACES IDP iron observations (v2.6, PR #40). |

**Method templates (differentiable physics + ML for Earth science):**

| Reference | Why it matters |
|---|---|
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Differentiable physics + per-location parameter network — closest method template. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM, *Nature*) | Hybrid physics + ML emulator design reference for Track 2. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC) | Closest existing ocean-BGC ML; DarwinDiff differs by being mechanistic + parameter-aware. |

</details>

## Acknowledgements

DarwinDiff builds on a substantial lineage of ocean biogeochemistry, ECCO-Darwin model development, and machine-learning-for-physics research. Specific individual credits will be added in the published manuscript; for the in-development repository, the following institutional acknowledgements apply.

- **MIT Department of Earth, Atmospheric, and Planetary Sciences (EAPS)** — research collaboration on ECCO-Darwin and the differentiable-physics-for-parameter-learning approach.
- **MIT Office of Research Computing and Data (ORCD)** — Engaging cluster and AICR (B200) beta program for the cluster-scale phase of this work.
- **JPL ECCO Group** and the **NASA Advanced Supercomputing (NAS)** division — ECCO-Darwin v05 outputs (`bin_average` 1° NetCDF + native LLC270 monthly tracer tree).
- **GLODAP**, **GEOTRACES**, and the **NASA GHG Center** — observational data products that are active recovery targets in v3.1.

Method-inspiration citations (PINN, BINN, Neural GCM, Neural-BGC, the full ECCO-Darwin lineage) are listed in the [Background reading](#background-reading) section above with verified DOIs.

Author and affiliation details to be added in the published manuscript.

## License

Released under the **MIT License**. See [LICENSE](LICENSE) for full text. Copyright © 2026 ECCO-DarwinDiff contributors.

The underlying ECCO-Darwin model is the work of the ECCO and Darwin teams and should be credited independently in any downstream work; see citation block below.

## How to cite

DarwinDiff is under active development; a formal manuscript and Zenodo DOI will be issued upon publication. In the interim, you may cite the repository directly:

```bibtex
@software{darwindiff_2026,
  author    = {{ECCO-DarwinDiff contributors}},
  title     = {{ECCO-DarwinDiff}: Differentiable Ocean Biogeochemistry
               for Per-Cell Parameter Recovery},
  year      = {2026},
  publisher = {GitHub},
  url       = {https://github.com/2imi9/ECCO-DarwinDiff}
}
```

If your work depends on the underlying ECCO-Darwin model, please also cite:

```bibtex
@article{carroll2020eccoDarwin,
  title   = {The {ECCO}-{Darwin} data-assimilative global ocean
             biogeochemistry model: Estimates of seasonal to multidecadal
             surface ocean p{CO}$_2$ and air-sea {CO}$_2$ flux},
  author  = {Carroll, Dustin and Menemenlis, Dimitris and Adkins, Jess F.
             and Bowman, Kevin W. and Brix, Holger and Dutkiewicz,
             Stephanie and others},
  journal = {Journal of Advances in Modeling Earth Systems},
  volume  = {12},
  number  = {10},
  pages   = {e2019MS001888},
  year    = {2020},
  doi     = {10.1029/2019MS001888}
}

@article{carroll2022eccoDarwinDIC,
  title   = {Attribution of space-time variability in global-ocean
             dissolved inorganic carbon},
  author  = {Carroll, Dustin and Menemenlis, Dimitris and Dutkiewicz,
             Stephanie and Lauderdale, Jonathan M. and Adkins, Jess F.
             and Bowman, Kevin W. and others},
  journal = {Global Biogeochemical Cycles},
  volume  = {36},
  number  = {4},
  pages   = {e2021GB007162},
  year    = {2022},
  doi     = {10.1029/2021GB007162}
}
```

<!-- Reference links -->
[py_img]: https://img.shields.io/badge/python-3.11%2B-blue.svg
[py_url]: https://www.python.org/downloads/
[lic_img]: https://img.shields.io/badge/license-MIT-blue.svg
[lic_url]: LICENSE
[status_img]: https://img.shields.io/badge/status-research%20%2F%20alpha-orange.svg
[status_url]: STATUS.md
[design_url]: docs/dinn_design.md
[cluster_url]: docs/cluster_setup.md
[data_url]: data/README.md
[skills_url]: .claude/skills/README.md
[demo_url]: notebooks/demo_colab.ipynb
