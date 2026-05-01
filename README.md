# ECCO-DarwinDiff

A differentiable PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model, for two complementary uses:

1. **Emulator** — a fast neural surrogate that reproduces ECCO-Darwin tracer fields for climate perturbation and paleoclimate experiments on timescales the full model cannot reach.
2. **Parameter learner** — end-to-end gradient-based replacement for ECCO-Darwin's Green's functions calibration, learning spatially-varying biogeochemical parameters in a single training run.

> **Status:** early scaffolding. No physics implemented yet. The biogeochemistry equations live in Dutkiewicz et al. (2009) and Brix et al. (2015) and will be reviewed before any module is drafted.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*) is a global ocean biogeochemistry model that assimilates physical and biogeochemical observations on the ECCO LLC270 grid (~1/3° at the equator, ~18 km at high latitudes, 50 vertical levels) from 1992–2017. It currently uses two calibration approaches:

- **Adjoint method** for ocean physics — many control variables, but expensive.
- **Green's functions** for biogeochemistry — Carroll et al. (2020) calibrated **6 biogeochemical parameters** (iron dust solubility, iron scavenging rate, small/large phytoplankton growth rates, diatom palatability, PIC/POC ratio) plus initial conditions via forward sensitivity experiments. Green's functions are limited to a small number of control variables (Menemenlis et al. 2005), and each new parameter requires a fresh forward run.

DarwinDiff replaces the biogeochemistry side of this with PyTorch autograd: gradients for all parameters are computed in one backward pass, parameters can be predicted spatially by an MLP from environmental covariates, and the same infrastructure trains a neural emulator on Darwin output for long-timescale climate runs.

## Method lineage

| Reference | Contribution |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | The ECCO-Darwin paper this project differentiates against; defines the 6-parameter Green's functions calibration we replace. |
| [Brix et al. 2015](https://doi.org/10.1016/j.ocemod.2015.07.008) (*Ocean Modelling*) | Pilot ECCO-Darwin; original biogeochemistry equations and parameter set. |
| [Savelli et al. 2026](https://doi.org/10.5194/gmd-19-867-2026) (*GMD*) | Recent ECCO-Darwin update (riverine BGC inputs); explicitly flags fixed-parameter limits like 100-day DOC remineralization that DarwinDiff could relax. Same author team as Carroll 2020. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*Global Biogeochem. Cycles*) | Underlying Darwin biogeochemistry formulation. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*Mon. Weather Review*) | Green's functions method for ocean GCM calibration — the technique DarwinDiff replaces. |
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Methodological template — differentiable CLM5 inside an NN for soil carbon. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM, *Nature*) | Architectural reference for hybrid physics + ML emulators. |

## Plan

- **Method validation prototype:** a 1D toy reaction-diffusion simulator and small parameter MLP that runs a BINN-style synthetic-recovery test on a local GPU. Validates the differentiable scaffold (autograd through hand-coded physics, MLP-predicts-parameter composition, gradient-descent recovery) before committing to specific Darwin equations. Lives in [`src/darwindiff/prototype/`](src/darwindiff/prototype/).
- **Region:** 2D regional testbed; specific region TBD with the domain advisor.
- **Tracers:** 4 — DIC, phosphate, iron, oxygen (working set; subject to revision).
- **Parameters to learn:** 5–10; whether to revisit Carroll 2020's 6 Green's functions parameters or to target the fixed-suboptimal parameters Savelli 2026 flags (e.g. DOC remineralization rate) is TBD with the domain advisor.
- **Steady-state assumption** for tractability (BINN approach).
- **Compute:** small-scale function tests on a single RTX 5090 locally; larger differentiable runs at manageable feedback time may require cloud GPU support — TBD.
- **Validation:** synthetic recovery test, comparison to Carroll 2020 Green's functions optima, 10-fold CV against held-out GLODAP/Argo, mass conservation check.

Stages:

| Stage | Focus | Hoped-for outcome |
|---|---|---|
| 0 | Micro prototype: 1D toy reaction-diffusion + parameter MLP; BINN-style synthetic-recovery test on local GPU. | Empirical evidence the differentiable scaffold works end-to-end before scaling to real Darwin equations. |
| 1 | Data pipeline; read Darwin source (Brix 2015, Dutkiewicz 2009); lock equation subset and parameter targets with Lauderdale. | Reproducible fetch of ED output and observations; clear technical plan agreed with the domain advisor. |
| 2 | Differentiable BGC module for the 4 tracers; MLP for spatial parameters; forward + train on the 2D transect. | Gradients flow end-to-end through a working differentiable Darwin; first learned parameter fields. |
| 3 | Validation: synthetic-recovery test, cross-validation against held-out GLODAP/Argo, mass conservation, comparison to Carroll 2020 Green's functions optima; sensitivity experiments; draft writeup. | A defensible scientific result and a paper draft. |
| 4 (stretch) | Emulator: neural surrogate trained on full ED output; long-timescale stability test for paleoclimate / climate-perturbation runs. | A useful surrogate for the long-timescale CO2 work that motivated this for Lauderdale. |

## Repository layout

```
ecco-darwindiff/
├── README.md
├── LICENSE                   MIT
├── pyproject.toml            package metadata + deps
├── src/darwindiff/           Python package (importable as `darwindiff`)
├── tests/                    pytest tests
├── data/                     local data cache (gitignored, see data/README.md)
├── notebooks/                exploratory Jupyter
└── references/               PDFs and citations (PDFs gitignored)
```

## Installation

Requires Python 3.11+. With uv:

```bash
uv sync
```

## Data sources

See [data/README.md](data/README.md). Summary:

| Source | Use | Access |
|---|---|---|
| ECCO-Darwin output | Emulator training, parameter-learner ground truth | https://data.nas.nasa.gov/ecco (registration required) |
| SOCATv5 | Surface ocean fCO2 | https://socat.info |
| GLODAPv2 | DIC, alkalinity, nutrients, oxygen | https://glodap.info |
| BGC-Argo | NO3, O2 float profiles | https://biogeochemical-argo.org via `argopy` |

## License

MIT — see [LICENSE](LICENSE). © 2026 ECCO-DarwinDiff contributors.

## Citation

This project is in early development; a formal citation will be added when the work is published or when a Zenodo DOI is minted. Until then, please link to the repository.

If your work depends on the underlying ECCO-Darwin model, please cite:

```
Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S.,
et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model:
Estimates of seasonal to multidecadal surface ocean pCO2 and air-sea CO2 flux.
Journal of Advances in Modeling Earth Systems, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888
```
