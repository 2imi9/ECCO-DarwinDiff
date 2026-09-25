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
  <img src="docs/figures/readme/readme_method.svg" width="100%" alt="Method diagram. A sea-surface-temperature map passes through a per-cell network drawn as stacked feature maps; a single rod pierces the same grid cell of every map, showing one small network with shared weights applied at every cell. A fixed bounds map turns its output into six parameter maps. One cell is magnified into its own two-layer water column, stepped forward from x0 to xT with the parameters entering every step. The end state is compared with sparse real observations (blue) and an ECCO-Darwin pattern (gold, shape only), and an iron-budget term joins the loss. One red arrow carries the gradient from the loss back through every step to the shared weights.">
</p>

<sub><i>Blue marks real observations, gold marks ECCO-Darwin v05 output compared by shape only, and red
marks the gradient. Each grid cell runs its own column, with no transport between cells. The
iron-budget and silica terms also read the parameters directly. The network reads sea-surface
temperature alone: wind, salinity, atmospheric pCO₂, CO₂ flux and mixed-layer depth were tested as
extra inputs ([2026-07-22](docs/findings/2026-07-22_covariate_channels_result.md)) and are not used.</i></sub>

## How it works

Only Darwin's biogeochemistry is rebuilt. Time-mean temperature, salinity, wind speed and
atmospheric pCO₂, and most of the initial chemistry, come from ECCO-Darwin v05 as fixed inputs;
light, dust deposition, layer depths and mixing are constants in the code. Only the network is
trained: everything downstream of it is fixed but differentiable. The result is a surrogate, so it
is a consistency check against Carroll's published values, not a cross-validated discovery.

<p align="center">
  <img src="docs/figures/readme/readme_components.svg" width="100%" alt="Component table. Rows: per-cell network, bounds map, parameters theta, two-layer box step, fixed constants, SST, forcing and initial state, pattern term, dissolved-iron term, calcite-ratio term, biogenic-silica term, iron-budget residual, lateral transport, comparison to Carroll. Columns mark whether each is learned, whether it is differentiable, whether it varies by cell, and its source. Only the network is learned; the bounds map, box step and loss terms are fixed but differentiable. SST, forcing and the pattern term come from ECCO-Darwin v05; the iron, calcite and silica terms use sparse real observations from GEOTRACES and Daniels et al. 2018. There is no lateral transport, and the comparison to Carroll happens per region after training.">
</p>

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
