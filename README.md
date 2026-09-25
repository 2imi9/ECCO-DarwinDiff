# ECCO-DarwinDiff

[![tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Which biogeochemistry parameters of [ECCO-Darwin](https://github.com/MITgcm-contrib/ecco_darwin) can
real ocean observations actually pin down? Carroll et al.
([2020](https://doi.org/10.1029/2019MS001888)) tuned six of them with Green's functions, one
perturbed forward run per parameter and one global value each, and ECCO-Darwin v05 ([Carroll et al.
2022](https://doi.org/10.1029/2021GB007162)) runs with them (its `R_PICPOC` differs from the
published optimum by about 1%). This project asks the same question with gradients. The
biogeochemistry is rebuilt as a differentiable model in PyTorch, a network predicts all six
parameters in every grid cell, and one backward pass gives the gradient for all of them everywhere.

<p align="center">
  <img src="docs/figures/readme/readme_method.svg" width="100%" alt="Method diagram with its equations. A sea-surface-temperature map, z-scored, passes through a per-cell network drawn as stacked feature maps; a rod pierces the same grid cell of every map, showing one small network with shared weights w applied at every cell. A fixed sigmoid bounds map turns its output into the six parameters theta_c (equation 1). One cell is magnified into its own two-layer column, stepped forward from x0 to xT by forward Euler (equation 2); theta_c and the forcing phi_c (SST, salinity, wind and atmospheric pCO2, ECCO-Darwin v05 time means) enter every step, and the initial state x_c^IC comes from the v05 pickup for the chemistry and from literature constants for the plankton. The end state is compared with sparse real observations (blue) and an ECCO-Darwin pattern (gold, shape only), and a simplified surface iron balance joins the loss L, summed over regions (equation 3). One red arrow carries the gradient back through every step to the shared weights (equation 4); the objective is to minimise L over w subject to equations 1 and 2.">
</p>

<sub><i>Equations (1)–(4) are the ones the code runs. Blue marks real observations, gold marks ECCO-Darwin
v05 output compared by shape only, and red marks the gradient. Each grid cell runs its own column
from its initial state x₀, driven by the forcing φ, with no transport between cells. The iron-budget
and silica terms also read the parameters directly. The network reads sea-surface temperature alone:
wind, salinity, atmospheric pCO₂, CO₂ flux and mixed-layer depth were tested as extra network inputs
([2026-07-22](docs/findings/2026-07-22_covariate_channels_result.md)) and dropped there, though the
first three still force the box.</i></sub>

## How it works

Only Darwin's biogeochemistry is rebuilt, as a two-layer box (0–50 m and 50–1000 m) run
independently in every grid cell. Only the network is trained: everything downstream of it is
fixed but differentiable. The result is a surrogate, so it is a consistency check against
Carroll's published values, not a cross-validated discovery.

### Inputs

| Input | Enters | Source |
|---|---|---|
| sea-surface temperature, z-scored | the network (its only input) | ECCO-Darwin v05, time mean |
| forcing φ: temperature, salinity, wind speed, atmospheric pCO₂ | every box step | ECCO-Darwin v05, time means |
| initial chemistry x₀: dissolved iron, POC, PIC, DIC and alkalinity in both layers | the box at the first step | ECCO-Darwin v05 initial conditions (pickup files) |
| initial plankton x₀: the five phytoplankton types | the box at the first step | constants from the literature |
| light, dust iron source, layer depths, vertical mixing, remineralisation | every box step | constants in the code |

The same temperature field feeds the network and the forcing, where it also scales growth. The
loss targets (real observations and ECCO-Darwin v05 patterns) are in the table below.

<p align="center">
  <img src="docs/figures/readme/readme_components.svg" width="100%" alt="Component table with a Form column giving each term's equation. Model rows: per-cell network f_w, bounds map, parameters theta_c, two-layer box step (forward Euler), fixed constants. Input rows: SST (the network's only input, also part of the forcing), forcing phi_c (SST, salinity, wind, atmospheric pCO2; v05 time means), initial state x_c0 (v05 pickup chemistry plus literature plankton), and other network inputs that were tested and not used. Loss rows on the end state x_T: shape-only pattern terms against ECCO-Darwin v05, relative errors against GEOTRACES dissolved iron and silica and Daniels et al. 2018 calcite ratios, and a simplified surface iron balance. Scope rows: no lateral transport; the comparison to Carroll happens per region after training. Columns mark whether each item is learned, differentiable and per cell, and its source. Footer definitions give the pattern score Z, the observation error E and the iron residual rho.">
</p>

### Parameters

The network predicts six parameters, the ones Carroll et al. tuned, as a field over the grid cells:

| Parameter | What it sets in the box | Where it acts |
|---|---|---|
| `alpfe` | scale on the box's constant surface iron source | surface dissolved iron |
| `scav_rat` | scavenging of dissolved iron onto POC, a permanent loss | dissolved iron in both layers |
| `Smallgrow` | maximum growth rate of the high-light *Prochlorococcus* pool | surface plankton, iron uptake, DIC |
| `Biggrow` | maximum growth rate of other large eukaryotes (diatom growth is fixed) | surface plankton, iron uptake, DIC |
| `diatomgraz` | grazing loss on diatoms, a multiplier on a fixed rate | surface diatoms, which feed POC and calcite |
| `R_PICPOC` | calcite produced per unit organic carbon lost, for all phytoplankton | surface PIC, DIC and alkalinity |

Each acts directly in the surface layer except `scav_rat`, and reaches the rest of the state through
the dynamics. The box stands in for Darwin's processes in simplified form: `diatomgraz` is a grazing
palatability in Darwin, and `R_PICPOC` applies only to calcifying types there. So matching Carroll's
values is a consistency check, not an equivalence.

Results come from multi-seed cluster runs that `scripts/verify_run.py` re-grades, and AI agents
write them up, retract what later runs overturn and index them in the
[research map](docs/research_map.md); because they keep moving, they live in [STATUS.md](STATUS.md)
and on the [documentation site](https://ecco-darwindiff.readthedocs.io/en/latest/), not here.

## Quickstart

Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q
```

[`notebooks/demo_colab.ipynb`](notebooks/demo_colab.ipynb)
([open in Colab](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb))
runs a small synthetic example on the teaching box and shows why fitting is not identifying.
Real-data runs need the ECCO-Darwin v05 output and the observation files
([data](data/README.md), [cluster setup](docs/cluster_setup.md)). The flagship configuration is
pinned in one file. A recovery count means nothing without an untrained control of the same
architecture, so run one alongside it and make `verify_run.py` require it:

```bash
export DARWIN_DATA_ROOT=/path/to/ecco_darwin_v5
source scripts/configs/flagship_geo1.sh             # one seed by default; set NB23_SEEDS for more
OUTPUT_DIR=runs/flagship  uv run python scripts/run_v3.0_joint_multi_aoi.py
OUTPUT_DIR=runs/untrained NB23_LR=0 NB23_N_EPOCHS=1 uv run python scripts/run_v3.0_joint_multi_aoi.py
uv run python scripts/verify_run.py runs/flagship --baseline runs/untrained --require-baseline
```

| Path | Contents |
|---|---|
| `src/darwindiff/` | the differentiable boxes, data loaders, network, training and grading |
| `scripts/` | experiment runners, sweep configs, analysis, research-map tooling |
| `docs/findings/` | dated notes (results, pre-registrations, audits) and their JSON artifacts; retracted notes are kept |
| `docs/figures/readme/` | TikZ sources for the figures above (`build.sh` regenerates them) |

[Start here](docs/ONBOARDING.md) · [status](STATUS.md) · [research map](docs/research_map.md) ·
[contributing](CONTRIBUTING.md) · [changelog](CHANGELOG.md)

Research code under active development. MIT licensed. If you use this, cite the repository (BibTeX
on the [docs site](https://ecco-darwindiff.readthedocs.io/en/latest/#how-to-cite)) and Carroll et
al. [2020](https://doi.org/10.1029/2019MS001888) and [2022](https://doi.org/10.1029/2021GB007162).
