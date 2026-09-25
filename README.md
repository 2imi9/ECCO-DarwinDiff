# ECCO-DarwinDiff

[![tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Which biogeochemistry parameters of [ECCO-Darwin](https://github.com/darwinproject/darwin3) can
real ocean observations actually pin down? Carroll et al.
([2020](https://doi.org/10.1029/2019MS001888), [2022](https://doi.org/10.1029/2021GB007162)) tune
six of them with Green's functions. Here the biogeochemistry is a differentiable box model in
PyTorch, a small per-cell network predicts all six in every grid cell, and the fit is graded
against Carroll's published values.

**Short answer: two recovered globally, two identifiable in one basin each, two excluded.**

| Parameter | Result (per-region, 50 seeds) | Control |
|---|---|---|
| `R_PICPOC` | 50/50, conditional on the Daniels 2018 calcite anchor | 6/50 without it |
| `alpfe` | 98/100 at ≤30%, a direction rather than a value (rails to its bound) | untrained 0/100 |
| `scav_rat` | Southern Ocean only: 30/50 arithmetic, 49/50 geometric | untrained 0/50 |
| `diatomgraz` | equatorial Pacific only: 40/100 at ≤10% | untrained 0/50 |
| `Smallgrow`, `Biggrow` | excluded: no time-mean observable constrains them | |

This is a surrogate-to-model identifiability study, a consistency check against Carroll's own
calibration, not a cross-validated discovery. What each number means, the caveats, and the
retracted readings are on the [documentation site](https://ecco-darwindiff.readthedocs.io/en/latest/);
[STATUS.md](STATUS.md) is the canonical snapshot.

![DINN architecture: sea-surface temperature feeds two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters, which pass through the differentiable box model to the loss; gradients flow back through the box model to the network](docs/dinn_architecture.svg)

## Quickstart

Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q
```

[`notebooks/demo_colab.ipynb`](notebooks/demo_colab.ipynb) runs a synthetic recovery on CPU in a
few minutes ([open in Colab](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb)).
The full flagship needs the ECCO-Darwin v05 output plus the GEOTRACES and Daniels files; see
[data](data/README.md) and [cluster setup](docs/cluster_setup.md).

## Docs

[Start here](docs/ONBOARDING.md) · [status](STATUS.md) · [results matrix](docs/results_matrix.md) ·
[findings](docs/findings/) · [research map](docs/research_map.md) · [changelog](CHANGELOG.md)

Research code under active development; results are updated in place as later findings supersede
earlier ones. MIT licensed. If you use this, cite the repository and Carroll et al.
[2020](https://doi.org/10.1029/2019MS001888) and [2022](https://doi.org/10.1029/2021GB007162).
