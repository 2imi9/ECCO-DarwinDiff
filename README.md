<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

**Differentiable ECCO-Darwin for ocean-biogeochemistry parameter recovery via gradient descent through the box model.**

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="820">

<sub>DarwinDiff's per-cell network (DINN): the loss flows through the differentiable box model, so a single backward pass recovers the six Carroll parameters.</sub>

[Docs][docs_url] · [Status][status_url] · [Setup](#setup) · [Reproduce](#reproduce) · [Cite](#how-to-cite)

[![Docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/) [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb)

A PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model in which gradients flow through every step of the simulation, so a single loss surface can learn the parameters that Carroll's Green's-functions calibration tunes one-at-a-time — predicted per grid cell from local environmental conditions. Manuscript in preparation.

</div>

## Two tracks

1. **Parameter learner** *(active)* — learns a per-cell function from local environment to the six Carroll parameters by gradient descent through the differentiable box model, replacing Green's-functions calibration.
2. **Emulator** *(not started)* — a neural stand-in for ECCO-Darwin for long-timescale climate runs.

## What works · what's blocked

**Works**
- The iron pair (`alpfe`, `scav_rat`) recovers reproducibly — **38/40 (95%)** at the best 3-AOI config; one fit runs in ~7 min on a single GPU.
- A **reproducible 5/6** at 3-AOI (v3.2): dense-Darwin `POSi` + Eppley temperature limitation recover `diatomgraz` alongside the iron pair — mean **2.0 → 3.85/6**, 70% of seeds ≥4/6 (n=20), the first gain from forward-model physics rather than loss-weight/architecture levers. The synthetic demo runs end-to-end on a laptop / free Colab T4.

**Known limits**
- A **structural 6/6 wall**: 0/856 seeds recover all six jointly — `R_PICPOC` (3%) is the lone unrecovered parameter. 5/6 now reproduces (above); breaking to 6/6 is the open problem.
- `R_PICPOC` needs **richer calcite physics**: the box's rigid-ratio calcite can't match Darwin's ~23× coccolithophore-driven spatial PIC/POC variation. A PIC:POC ratio loss recovers it per-cell where the box matches Darwin (eqpac), but ≥2-AOI recovery needs the differentiable Darwin calcite port + native resolution — not a box-scale estimator or seasonal lever. (`diatomgraz`, the former second holdout, now recovers under v3.2.)
- 1° box-model proxy; 23-year climatology, not time-resolved; single-method (no forward-Darwin held-out validation yet); single-GPU prototype. Full evidence → [STATUS.md][status_url].

## Documentation

📖 **[ecco-darwindiff.readthedocs.io][docs_url]** — the full documentation site. Quick links:

- [Project status][status_url] — canonical live results, the 5/6 ceiling, known limits
- [Findings](https://ecco-darwindiff.readthedocs.io/en/latest/findings/) — per-version technical writeups (v2.1 → v3.2)
- [DINN design](https://ecco-darwindiff.readthedocs.io/en/latest/dinn_design/) · [ECCO-Darwin relationship](https://ecco-darwindiff.readthedocs.io/en/latest/ecco_darwin_relationship/)
- [Cluster setup](https://ecco-darwindiff.readthedocs.io/en/latest/cluster_setup/) · [Data sources](https://ecco-darwindiff.readthedocs.io/en/latest/data/)

## Reproduce

The headline finding (the structural 6/6 wall: 0/856 at 6/6 across **856 seeds / 86 configs**, with `R_PICPOC` the lone holdout) and the full evidence table live in [STATUS.md][status_url]; the cluster-scale sweep is in [docs/cluster_setup.md][cluster_url]. The per-task GPU / memory / wall-clock budget — which tier (5090 / Explorer H200 / AICR B200) runs each task and how long it takes — is in [the compute-budget note][budget_url].

Run the synthetic recovery demo in ~5 min on a laptop or a free Colab T4 — the annotated walkthrough is [`notebooks/demo_colab.ipynb`][demo_url] (or click the Colab badge above). It backprops through the differentiable box model using the `darwindiff.carroll6` + `darwindiff.networks` public API.

## Setup

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync && uv run pytest -q          # smoke test
```

For cluster runs, point the loaders at the LLC270 tree via `DARWIN_DATA_ROOT` (and `GLODAP_DATA_ROOT`). Raw data lives outside the repo; operational detail (Windows `MAX_PATH`, IC caches, per-loader layout) is in [docs/cluster_setup.md][cluster_url] and [data/README.md][data_url].

<details>
<summary><b>Why this exists</b></summary>

ECCO-Darwin (Carroll et al. 2020, *JAMES*; 2022, *GBC*) is calibrated via **Green's functions** (Menemenlis et al. 2005), which scale badly: each tuned parameter needs a fresh full forward run, so the published calibration handles only **6 parameters**. DarwinDiff replaces the biogeochemistry side with **PyTorch autograd** — gradients for all parameters in one backward pass, with the parameter values varying across space, predicted by a small per-cell network (DINN).

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
| [Clark et al. 2026](https://arxiv.org/abs/2606.07928) (ACE2S) | State-of-the-art neural Earth-system emulator (Ai2 / NOAA-GFDL); benchmark for the Track-2 emulator. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC) | Closest existing ocean-BGC ML; DarwinDiff differs by being mechanistic + parameter-aware. |

</details>

## Acknowledgements

Institutional acknowledgements for the in-development repository (individual credits to follow in the manuscript):

- **MIT Department of Earth, Atmospheric, and Planetary Sciences (EAPS)** — research collaboration on ECCO-Darwin and the differentiable-physics parameter-learning approach.
- **MIT Office of Research Computing and Data (ORCD)** — Engaging cluster and AICR (B200) beta program.
- **JPL ECCO Group** and the **NASA Advanced Supercomputing (NAS)** division — ECCO-Darwin v05 outputs.
- **GLODAP**, **GEOTRACES**, and the **NASA GHG Center** — observational data products that are active recovery targets in v3.1.

Method-inspiration citations (PINN, BINN, Neural GCM, ACE2S, Neural-BGC, the full ECCO-Darwin lineage) are listed in the [Background reading](#background-reading) section above with verified DOIs.

## License

Released under the **MIT License**. See [LICENSE](LICENSE) for full text. Copyright © 2026 ECCO-DarwinDiff contributors.

The underlying ECCO-Darwin model is the work of the ECCO and Darwin teams and should be credited independently in any downstream work; see citation block below.

## How to cite

DarwinDiff is under active development; a formal manuscript and Zenodo DOI will be issued upon publication. In the interim, cite the repository directly:

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

<details>
<summary><b>If your work depends on the underlying ECCO-Darwin model, also cite:</b></summary>

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

</details>

<!-- Reference links -->
[docs_url]: https://ecco-darwindiff.readthedocs.io/en/latest/
[status_url]: STATUS.md
[cluster_url]: docs/cluster_setup.md
[budget_url]: docs/research_notes/2026-06-21_full_compute_budget.md
[data_url]: data/README.md
[demo_url]: notebooks/demo_colab.ipynb
