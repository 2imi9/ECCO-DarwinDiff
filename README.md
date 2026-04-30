# ECCO-DarwinDiff

A differentiable PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model, for two complementary uses:

1. **Emulator** — a fast neural surrogate that reproduces ECCO-Darwin tracer fields, enabling climate perturbation and paleoclimate experiments on timescales the full model cannot reach.
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
| Carroll et al. 2020 (*JAMES*) | The ECCO-Darwin paper this project differentiates against; defines the 6-parameter Green's functions calibration we replace. |
| Brix et al. 2015 (*Ocean Modelling*) | Pilot ECCO-Darwin; original biogeochemistry equations and parameter set. |
| Dutkiewicz et al. 2009 (*Global Biogeochem. Cycles*) | Underlying Darwin biogeochemistry formulation. |
| Menemenlis et al. 2005 (*Mon. Weather Review*) | Green's functions method for ocean GCM calibration — the technique DarwinDiff replaces. |
| Xu et al. 2025 (BINN, arXiv:2502.00672) | Methodological template — differentiable CLM5 inside an NN for soil carbon. |
| Kochkov et al. 2024 (Neural GCM, *Nature*, arXiv:2311.07222) | Architectural reference for hybrid physics + ML emulators. |

## Summer scope (single RTX 5090, 24 GB VRAM)

- **Region:** 2D depth–latitude transect (likely Southern Ocean).
- **Tracers:** 4 — DIC, phosphate, iron, oxygen.
- **Parameters to learn:** 5–10, anchored on the highest-impact ones from Carroll 2020 (large phytoplankton growth rate, iron scavenging, iron dust solubility, small phytoplankton growth rate).
- **Steady-state assumption** for tractability (BINN approach).
- **Validation:** synthetic recovery test, comparison to Carroll 2020 Green's functions optima, 10-fold CV against held-out GLODAP/Argo, mass conservation check.

8-week plan:

| Weeks | Focus |
|---|---|
| 1–2 | Data pipeline; read Darwin source code (Brix 2015, Dutkiewicz 2009). |
| 3–5 | Differentiable Darwin module; MLP for parameters; train on 2D transect. |
| 6–8 | Validate, sensitivity experiments, draft writeup. |
| Stretch | Emulator extension if parameter learning succeeds early. |

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

MIT — see [LICENSE](LICENSE). © 2026 Ziming Qi.

## Citation

If you use this work, please cite:

```
Qi, Z. (2026). ECCO-DarwinDiff: a differentiable PyTorch reimplementation of the
ECCO-Darwin ocean biogeochemistry model for emulation and parameter learning.
https://github.com/2imi9/ECCO-DarwinDiff
```

And the underlying model:

```
Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S.,
et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model:
Estimates of seasonal to multidecadal surface ocean pCO2 and air-sea CO2 flux.
Journal of Advances in Modeling Earth Systems, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888
```
