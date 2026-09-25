# ECCO-DarwinDiff

[![tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Which biogeochemistry parameters of [ECCO-Darwin](https://github.com/darwinproject/darwin3) can
real ocean observations actually pin down? Carroll et al.
([2020](https://doi.org/10.1029/2019MS001888), [2022](https://doi.org/10.1029/2021GB007162))
calibrate them with Green's functions, one forward run per parameter. This project asks the same
question with gradients: the biogeochemistry is rebuilt as a differentiable model in PyTorch, a
small network predicts the parameters in every grid cell, and the fit is compared with Carroll's
published values.

![DINN architecture: sea-surface temperature feeds a small per-cell network that predicts six Carroll parameters, which pass through the differentiable box model to the loss; gradients flow back through the box model to the network](docs/dinn_architecture.svg)

## How it works

The project has three layers.

1. **A differentiable model.** Box models of ECCO-Darwin's biogeochemistry, from a 5-tracer
   teaching box up to a 15-tracer, two-layer, five-plankton version, with gradients through every
   integration step. Loaders bring in ECCO-Darwin v05 output and real observations (GEOTRACES,
   calcite compilations, satellite products).
2. **Experiments.** Recovery runs are launched as multi-seed sweeps on a cluster. Every run is
   graded against a matched control and must pass `scripts/verify_run.py` before any number from
   it is used.
3. **An AI research loop.** Raw experiment results are handed to AI agents (Claude Code, with
   Codex as a second reviewer). They write up findings, search the literature, check each new
   result against earlier ones, and retract claims that later runs overturn. Everything they
   conclude goes into a [research map](docs/research_map.md) of claims, evidence and retractions,
   which a script turns into a queryable SQL database with integrity checks that run in CI. The
   agents' instructions are in [CLAUDE.md](CLAUDE.md) and [`.claude/skills/`](.claude/skills/).

Results change as this loop runs, so they are not kept in this README. The current state is in
[STATUS.md](STATUS.md) and on the [documentation site](https://ecco-darwindiff.readthedocs.io/en/latest/).

## Quickstart

Python 3.11–3.13 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run pytest -q
```

[`notebooks/demo_colab.ipynb`](notebooks/demo_colab.ipynb) runs a synthetic recovery on CPU in a
few minutes ([open in Colab](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb)).
Real-data runs need the ECCO-Darwin v05 output and the observation files; see [data](data/README.md)
and [cluster setup](docs/cluster_setup.md).

## Layout

| Path | Contents |
|---|---|
| `src/darwindiff/` | differentiable models, data loaders, networks, training and grading |
| `scripts/` | experiment runners, sweep configs, analysis, research-map tooling |
| `docs/findings/` | one write-up per result, including the retracted ones |
| `notebooks/` | demo and exploration notebooks |
| `tests/` | unit tests plus checks that reported numbers match their artifacts |

## Docs

[Start here](docs/ONBOARDING.md) · [status](STATUS.md) · [findings](docs/findings/) ·
[research map](docs/research_map.md) · [changelog](CHANGELOG.md)

Research code under active development. MIT licensed. If you use this, cite the repository and
Carroll et al. [2020](https://doi.org/10.1029/2019MS001888) and
[2022](https://doi.org/10.1029/2021GB007162).
