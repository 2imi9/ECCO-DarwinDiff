# ECCO-DarwinDiff

A PyTorch version of the ECCO-Darwin ocean biogeochemistry model that lets gradients flow through every step of the simulation. Built for two related uses:

1. **Emulator** — a fast neural network stand-in for ECCO-Darwin, so we can run climate and paleoclimate experiments on time spans the full model is too slow for.
2. **Parameter learner** — a faster replacement for ECCO-Darwin's Green's functions calibration, learning biogeochemical parameters that change across space in one training run.

> **Status:** early setup. No physics built in yet. The biogeochemistry equations live in Dutkiewicz et al. (2009) and Brix et al. (2015) and will be reviewed before any module is written.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*) is a global ocean biogeochemistry model that uses both physical and biogeochemical observations on the ECCO LLC270 grid (~1/3° at the equator, ~18 km at high latitudes, 50 vertical levels) from 1992–2017. It currently uses two calibration approaches:

- **Adjoint method** for ocean physics — many control variables, but expensive.
- **Green's functions** for biogeochemistry — Carroll et al. (2020) tuned **6 biogeochemical parameters** (iron dust solubility, iron scavenging rate, small and large phytoplankton growth rates, diatom palatability, PIC/POC ratio) plus initial conditions through forward sensitivity experiments. Green's functions only handle a small number of control variables (Menemenlis et al. 2005), and each new parameter needs a fresh forward run.

DarwinDiff replaces the biogeochemistry side of this with PyTorch autograd: gradients for all parameters are computed in one backward pass, parameters can be predicted across space by a small neural network from local environmental conditions, and the same code trains a neural emulator on Darwin output for long-timescale climate runs.

## Background reading

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | The ECCO-Darwin paper this project differentiates against; defines the 6-parameter Green's functions calibration we replace. |
| [Brix et al. 2015](https://doi.org/10.1016/j.ocemod.2015.07.008) (*Ocean Modelling*) | Earlier ECCO-Darwin version; original biogeochemistry equations and parameter set. |
| [Savelli et al. 2026](https://doi.org/10.5194/gmd-19-867-2026) (*GMD*) | Recent ECCO-Darwin update (river inputs); explicitly flags fixed-parameter limits like the 100-day DOC remineralization that DarwinDiff could relax. Same author team as Carroll 2020. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*Global Biogeochem. Cycles*) | Core Darwin biogeochemistry formulation. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*Mon. Weather Review*) | The Green's functions calibration method DarwinDiff replaces. |
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Method template — a differentiable CLM5 inside a neural network for soil carbon. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM, *Nature*) | Design reference for hybrid physics + machine learning emulators. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC, ESSOAr preprint) | Closest existing ocean BGC ML — observation-driven NN emulator coupled to ROMS, predicts DO and NO3 from physical state. DarwinDiff differs: mechanistic (emulates Darwin rather than bypassing it), parameter-aware, and extends to carbon-cycle variables (DIC, alkalinity, pCO2, POC export). |

## Plan

- **Test pilot:** a 1D toy reaction-diffusion simulator and small parameter neural network that runs a BINN-style recovery test on a local GPU. Checks the differentiable setup (autograd through hand-written physics, the neural-network-predicts-parameter pairing, and gradient-descent recovery) before we lock in the real Darwin equations. Lives in [`src/darwindiff/prototype/`](src/darwindiff/prototype/).
- **Region:** 2D ocean column to test on; specific region to be picked with the science advisor.
- **Tracers:** 4 — DIC, phosphate, iron, oxygen (working set; may change).
- **Parameters to learn:** 5–10; whether to revisit Carroll 2020's 6 Green's functions parameters or to target the fixed parameters Savelli 2026 flags as suspect (e.g. DOC remineralization rate) is to be picked with the science advisor.
- **Steady-state assumption** for ease of computation (BINN approach).
- **Compute:** small function tests on a single RTX 5090 locally; larger differentiable runs at usable response time may need cloud GPU support — to be decided.
- **Checking:** synthetic recovery test, comparison to Carroll 2020 Green's functions optima, 10-fold cross-validation against held-out GLODAP/Argo, mass conservation check.

Stages:

| Stage | Focus | Hoped-for outcome |
|---|---|---|
| 0 | Pilot: 1D toy reaction-diffusion + small parameter neural network; BINN-style recovery test on local GPU. | Hard evidence the differentiable setup works end-to-end before we scale to real Darwin equations. |
| 1 | Data flow; read Darwin source code (Brix 2015, Dutkiewicz 2009); pick equation subset and parameter targets with Lauderdale. | Reliable way to fetch ED output and observations; clear technical plan agreed with the science advisor. |
| 2 | Differentiable BGC module for the 4 tracers; neural network for spatial parameters; run forward and train on the 2D ocean column. | Gradients flow all the way through a working differentiable Darwin; first learned parameter maps. |
| 3 | Checking: recovery test, cross-validation against held-out GLODAP/Argo, mass conservation, comparison to Carroll 2020 Green's functions optima; sensitivity experiments; first paper draft. | A solid scientific result and a paper draft. |
| 4 (stretch) | Emulator: neural network stand-in trained on full ED output; long-timescale stability test for paleoclimate and climate-change runs. | A useful stand-in for the long-timescale CO2 work that motivates this for Lauderdale. |

## Repository layout

```
ecco-darwindiff/
├── README.md
├── LICENSE                   MIT
├── pyproject.toml            package details and dependencies
├── src/darwindiff/           Python package (importable as `darwindiff`)
├── tests/                    pytest tests
├── data/                     local data cache (gitignored, see data/README.md)
├── notebooks/                early notebooks
└── references/               PDFs and citations (PDFs gitignored)
```

## Installation

Needs Python 3.11+. With uv:

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

This project is still in early development; a formal citation will be added once the work is published or a Zenodo DOI is created. For now, please link to the repository.

If your work depends on the underlying ECCO-Darwin model, please cite:

```
Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S.,
et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model:
Estimates of seasonal to multidecadal surface ocean pCO2 and air-sea CO2 flux.
Journal of Advances in Modeling Earth Systems, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888
```
