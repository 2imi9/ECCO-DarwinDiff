# ECCO-DarwinDiff

[![tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Which biogeochemistry parameters of [ECCO-Darwin](https://github.com/MITgcm-contrib/ecco_darwin)
can real ocean observations actually pin down? Carroll et al.
([2020](https://doi.org/10.1029/2019MS001888), [2022](https://doi.org/10.1029/2021GB007162)) tune
six of them with Green's functions: one perturbed forward run per parameter, one global value
each. This project asks the same question with gradients. The biogeochemistry is rebuilt as a
differentiable model in PyTorch, a network predicts all six parameters in every grid cell, and
one backward pass gives the gradient for all of them everywhere.

<p align="center">
  <img src="docs/figures/readme/readme_method.svg" width="100%" alt="Method diagram. A sea-surface-temperature map passes through a per-cell network drawn as stacked feature maps; a single rod pierces the same grid cell of every map, showing one small network with shared weights applied at every cell. A fixed bounds map turns its output into six parameter maps. One cell is magnified into its own two-layer water column, stepped forward from x0 to xT with the parameters entering every step. The end state is compared with sparse real observations (blue) and an ECCO-Darwin pattern (gold, shape only), and an iron-budget term joins the loss. One red arrow carries the gradient from the loss back through every step to the shared weights.">
</p>

<sub><i>Blue marks real observations, gold marks ECCO-Darwin v05 output compared by shape only,
and red marks the gradient. Each grid cell runs its own column, with no transport between cells.
The iron-budget and silica terms also read the parameters directly.</i></sub>

## How it works

Only Darwin's biogeochemistry is rebuilt. The physical forcing and most of the initial chemistry
come from ECCO-Darwin v05 as fixed inputs, and only the network is trained: everything downstream of it
is fixed but differentiable. The result is a surrogate, so it is a consistency check against
Carroll's published values, not a cross-validated discovery.

<p align="center">
  <img src="docs/figures/readme/readme_components.svg" width="100%" alt="Component table. Rows: per-cell network, bounds map, parameters theta, two-layer box step, fixed constants, SST, forcing and initial state, pattern term, dissolved-iron term, calcite-ratio term, biogenic-silica term, iron-budget residual, lateral transport, comparison to Carroll. Columns mark whether each is learned, whether it is differentiable, whether it varies by cell, and its source. Only the network is learned; the bounds map, box step and loss terms are fixed but differentiable. SST, forcing and the pattern term come from ECCO-Darwin v05; the iron, calcite and silica terms use sparse real observations from GEOTRACES and Daniels et al. 2018. There is no lateral transport, and the comparison to Carroll happens per region after training.">
</p>

## How a result is made

<p align="center">
  <img src="docs/figures/readme/readme_loop.svg" width="100%" alt="Research-loop diagram: a clockwise loop through Plan, Run, Verify, Write up and Index. Run sits on the cluster outside the repository, with an arm and its control in the same job; results re-enter only through Verify, which re-derives the grading or stops. Write up produces dated findings, and an older finding keeps its text under a RETRACTED stamp with a supersedes arrow from the newer one. CI tests sit between Write up and Index, where a corpus JSON is rendered into the research map and rebuilt as an in-memory SQL database that the next Plan queries. Claude Code and Codex work under one working agreement, beside a maintainer who owns scope and the issue tracker.">
</p>

Experiments run as multi-seed sweeps on a cluster. `scripts/verify_run.py` re-derives the grading
from the raw per-seed files, and any failure means there is no result. AI agents (Claude Code and Codex, under one
[working agreement](CLAUDE.md)) write up each result, check it against earlier ones and retract
what later runs overturn. Everything they conclude goes into a [research map](docs/research_map.md)
that the next session queries before it plans anything:

```bash
python scripts/research_map_db.py settled daily     # is this already answered?
python scripts/research_map_db.py superseded 0.408  # has this number been retracted?
```

Because results move with this loop, none are kept here. The current state is in
[STATUS.md](STATUS.md) and on the [documentation site](https://ecco-darwindiff.readthedocs.io/en/latest/).

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
pinned in one file; set `DARWIN_DATA_ROOT` first, and check every run before quoting it:

```bash
export DARWIN_DATA_ROOT=/path/to/ecco_darwin_v5 OUTPUT_DIR=runs/flagship
source scripts/configs/flagship_geo1.sh
uv run python scripts/run_v3.0_joint_multi_aoi.py   # one seed by default; set NB23_SEEDS for more
uv run python scripts/verify_run.py "$OUTPUT_DIR"   # a non-zero exit means no result
```

| Path | Contents |
|---|---|
| `src/darwindiff/` | the differentiable boxes, data loaders, network, training and grading |
| `scripts/` | experiment runners, sweep configs, analysis, research-map tooling |
| `docs/findings/` | one dated note per result, retracted ones included |
| `docs/figures/readme/` | TikZ sources for the figures above (`build.sh` regenerates them) |

[Start here](docs/ONBOARDING.md) · [status](STATUS.md) · [research map](docs/research_map.md) ·
[contributing](CONTRIBUTING.md) · [changelog](CHANGELOG.md)

Research code under active development. MIT licensed. If you use this, cite the repository (BibTeX
on the [docs site](https://ecco-darwindiff.readthedocs.io/en/latest/#how-to-cite)) and Carroll et
al. [2020](https://doi.org/10.1029/2019MS001888) and [2022](https://doi.org/10.1029/2021GB007162).
