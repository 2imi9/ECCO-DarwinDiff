<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="760">

**A differentiable PyTorch reimplementation of ECCO-Darwin ocean biogeochemistry — gradients flow through every step of the simulation, so one loss surface recovers the parameters that Green's-functions calibration tunes one at a time, predicted per grid cell from the local environment.**

<sub>DarwinDiff's per-cell network (DINN): the loss flows through the differentiable box model, so a single backward pass recovers the six Carroll parameters.</sub>

<!-- Testing -->
[![Tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb)

<!-- Project -->
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4%2B-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

[Documentation][docs_url] · [Project status][status_url] · [Installation](#installation) · [Quick start](#quick-start) · [Citation](#citation)

</div>

ECCO-Darwin (Carroll et al. 2020, *JAMES*; 2022, *GBC*) calibrates its ocean-biogeochemistry parameters with **Green's functions** — a method that needs a fresh full forward run per parameter, so the published calibration tunes only six. **ECCO-DarwinDiff** replaces the biogeochemistry side with **PyTorch autograd**: gradients for every parameter in a single backward pass, with the parameter values varying across space, predicted by a small per-cell network. *Manuscript in preparation.*

## Overview

DarwinDiff is organized into two tracks:

1. **Parameter learner** *(active)* — learns a per-cell function from local environment to the six Carroll-6 parameters by gradient descent through the differentiable box model, replacing Green's-functions calibration.
2. **Emulator** *(not started)* — a neural stand-in for ECCO-Darwin for long-timescale climate runs.

The differentiable box model (`darwindiff.carroll6`), the per-cell networks (`darwindiff.networks`), and the ECCO-Darwin / GLODAP / GEOTRACES data loaders are all importable as the `darwindiff` package. The canonical results — including the first full six-parameter (6/6) recovery, with R_PICPOC unblocked by the `RATIO_MAX` ratio-target fix — and the known limits live in **[STATUS.md][status_url]** and `docs/findings/`.

## Installation

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync                     # create the environment from pyproject/uv.lock
uv run pytest -q            # smoke test (the LLC270/data tests self-skip)
```

The package targets **Python 3.11+** and **PyTorch 2.4+**. The synthetic demo needs nothing else; for real fits, point the loaders at the LLC270 tree via `DARWIN_DATA_ROOT` (and `GLODAP_DATA_ROOT`). Raw data lives outside the repo — operational detail (Windows `MAX_PATH`, IC caches, per-loader layout) is in [docs/cluster_setup.md][cluster_url] and [data/README.md][data_url].

## Quick start

Run the synthetic recovery demo in ~5 min on a laptop or a free Colab T4 — the annotated walkthrough is **[`notebooks/demo_colab.ipynb`][demo_url]** ([![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]).

The core idea — a per-cell network whose loss backpropagates through the differentiable box model — is just a few lines of the public API:

```python
import torch
from darwindiff.carroll6 import PARAM_BOUNDS, bounded_params, carroll6_integrate
from darwindiff.networks import DINN

# A per-cell network maps the local environment -> the six Carroll-6 parameters.
env = torch.randn(3, 8, 16)                       # [SST, wind, MLD] over an 8x16 grid
dinn = DINN(n_input_channels=3, hidden_dim=16, n_outputs=6)
params = bounded_params(dinn(env), PARAM_BOUNDS)  # [6, 8, 16], sigmoid-bounded to physical ranges

# Integrate the differentiable box model; gradients flow through every step, so one
# backward pass moves the network toward Carroll's calibrated optimum.
state0 = torch.full((5, 8, 16), 0.1)              # [DFe, Ps, Pl, POC, PIC]
final = carroll6_integrate(state0, params, dt=0.25, n_steps=200)

loss = (final - target).pow(2).mean()             # target: an ECCO-Darwin v05 field
loss.backward()                                   # d(loss)/d(weights) through the whole simulation
```

For a real recovery on ECCO-Darwin v05 data, the runners are in `scripts/` and every run is gated by the verified-experiment loop:

```bash
# batched + torch.compile'd seasonal fit, then verify the artifacts (exit 0 == trustworthy)
uv run python scripts/run_seasonal_recovery.py --aoi eqpac --n-seeds 10 --compile --out-dir runs/eqpac
uv run python scripts/verify_run.py runs/eqpac
```

## Results — what works, what's blocked

**Works**

- The iron pair (`alpfe`, `scav_rat`) recovers reproducibly — **38/40 (95%)** at the best 3-AOI config; one fit runs in ~7 min on a single GPU.
- A **reproducible 5/6** at 3-AOI (v3.2): dense-Darwin `POSi` + Eppley temperature limitation recover `diatomgraz` alongside the iron pair — mean **2.0 → 3.85/6**, 70% of seeds ≥4/6 (n=20), the first gain from forward-model physics rather than loss-weight/architecture levers.

**Known limits**

- A **structural 6/6 wall**: 0/856 seeds recover all six jointly across **856 seeds / 86 configs** — `R_PICPOC` (3%) is the lone unrecovered parameter. 5/6 now reproduces (above); breaking to 6/6 is the open problem.
- `R_PICPOC` needs **richer calcite physics**: the box's rigid-ratio calcite can't match Darwin's ~23× coccolithophore-driven spatial PIC/POC variation. A PIC:POC ratio loss recovers it per-cell where the box matches Darwin (eqpac), but ≥2-AOI recovery needs the differentiable Darwin calcite port + native resolution — not a box-scale estimator or seasonal lever.
- 1° box-model proxy; 23-year climatology, not time-resolved; single-method (no forward-Darwin held-out validation yet); single-GPU prototype.

The full evidence table, per-version findings, and the cluster-scale sweep plan are in **[STATUS.md][status_url]**; the per-task GPU / memory / wall-clock budget is in [the compute-budget note][budget_url].

## Documentation

📖 **[ecco-darwindiff.readthedocs.io][docs_url]** — the full documentation site. Quick links:

- [Project status][status_url] — canonical live results, the 5/6 ceiling, known limits
- [Findings](https://ecco-darwindiff.readthedocs.io/en/latest/findings/) — per-version technical writeups (v2.1 → v3.3)
- [DINN design](https://ecco-darwindiff.readthedocs.io/en/latest/dinn_design/) · [ECCO-Darwin relationship](https://ecco-darwindiff.readthedocs.io/en/latest/ecco_darwin_relationship/)
- [Cluster setup](https://ecco-darwindiff.readthedocs.io/en/latest/cluster_setup/) · [Data sources](https://ecco-darwindiff.readthedocs.io/en/latest/data/)

<details>
<summary><b>Repository layout</b></summary>

```
src/darwindiff/            Python package (importable as `darwindiff`)
  carroll6.py                5-tracer Carroll-6 box + Carroll's optima + bounds
  carbonate.py               Follows-2006 + Wanninkhof 2014 carbonate solver
  carroll6_5pft.py           10-tracer / 5-PFT box matching Darwin v05
  carroll6_5pft_2layer.py    v2.7 2-layer integrator (seasonal + seed-batched)
  networks.py                DINN + DINNRegional + DINNDeep
  seasonal.py                seasonal Chl losses + verify_run record builder
  ecco_darwin_loader.py      Darwin v05 1° loader + AOI presets
  llc270_loader.py           native LLC270 monthly loader (xmitgcm)
  glodap_loader.py           GLODAPv2.2016b DIC/ALK loader
scripts/                   runners, overnight sweeps, verify_run.py, SLURM templates
notebooks/                 numbered notebooks 05–32; demo_colab.ipynb is the synthetic walkthrough
tests/                     pytest suite (runs in CI)
docs/                      findings, research_notes, dinn_design.md, cluster_setup.md
.github/workflows/         CI (tests.yml)
.claude/skills/            project-scoped skill bundle
```

</details>

## Citation

ECCO-DarwinDiff is under active development; a formal manuscript and Zenodo DOI will be issued upon publication. In the interim, cite the repository directly:

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

## Contributing

Contributions are welcome. Please read **[CONTRIBUTING.md](CONTRIBUTING.md)** first — it covers the scope-prefixed PR titles, the commit/merge conventions, and the verified-experiment loop (`scripts/verify_run.py`) that every reported recovery number must pass. The test suite runs in CI on every pull request; run it locally with `uv run pytest -q` before opening a PR.

## Acknowledgements

Institutional acknowledgements for the in-development repository (individual credits to follow in the manuscript):

- **MIT Department of Earth, Atmospheric, and Planetary Sciences (EAPS)** — research collaboration on ECCO-Darwin and the differentiable-physics parameter-learning approach.
- **Northeastern Research Computing** — the **Explorer** (H200) and **AICR** (B200) clusters for native-resolution and throughput parameter-recovery runs.
- **JPL ECCO Group** and the **NASA Advanced Supercomputing (NAS)** division — ECCO-Darwin v05 outputs.
- **GLODAP**, **GEOTRACES**, and the **NASA GHG Center** — observational data products that are active recovery targets.

Method-inspiration citations (PINN, BINN, Neural GCM, ACE2S, Neural-BGC, the full ECCO-Darwin lineage) are listed in the **Background reading** block under [Citation](#citation), with verified DOIs.

## License

Released under the **MIT License** — see [LICENSE](LICENSE) for full text. Copyright © 2026 ECCO-DarwinDiff contributors.

The underlying ECCO-Darwin model is the work of the ECCO and Darwin teams and should be credited independently in any downstream work; see the citation block above.

<!-- Reference links -->
[docs_url]: https://ecco-darwindiff.readthedocs.io/en/latest/
[status_url]: STATUS.md
[cluster_url]: docs/cluster_setup.md
[budget_url]: docs/research_notes/2026-06-21_full_compute_budget.md
[data_url]: data/README.md
[demo_url]: notebooks/demo_colab.ipynb
[colab_url]: https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb
