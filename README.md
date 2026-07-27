<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="640">

**Differentiable ocean biogeochemistry — one backward pass recovers the parameters that
Green's-functions calibration tunes one at a time.**

[![Tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![Docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Start here][onboarding_url] · [Docs][docs_url] · [Status][status_url] · [Results matrix][matrix_url]

</div>

ECCO-Darwin ([Carroll 2020][c20], [2022][c22]) calibrates its biogeochemistry with Green's
functions — one full forward run per parameter, so only six are tuned. DarwinDiff reimplements the
biogeochemistry in PyTorch: every parameter gets a gradient in one backward pass, varying per grid
cell via a small network reading the local environment.

It answers which parameters real observations can pin down, and which they cannot. This is a
**consistency check against Carroll's published values, not a cross-validated discovery** — the 0-D
box homogenizes, so held-out real-data R² is negative.

## Install

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync && uv run pytest -q
```

Python 3.11+, PyTorch 2.4+. Real fits need `DARWIN_DATA_ROOT` pointing at the LLC270 tree
([cluster setup][cluster_url], [data][data_url]). The demo needs nothing else.

## Quick start

[`notebooks/demo_colab.ipynb`][demo_url] runs a synthetic recovery in ~5 min ([![Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]).

```python
from darwindiff.carroll6 import PARAM_BOUNDS, bounded_params, carroll6_integrate
from darwindiff.networks import DINN

params = bounded_params(DINN(3, 16, 6)(env), PARAM_BOUNDS)   # env = [SST, wind, MLD]
final = carroll6_integrate(state0, params, dt=0.25, n_steps=200)
(final - target).pow(2).mean().backward()                     # gradients through the simulation
```

Every reported number is gated: `uv run python scripts/verify_run.py <run-dir>` must exit 0.

## Results

Flagship `n50e2k_percell_trio` — n=50 seeds, 2000 epochs. Metric is **per-AOI ≥2-of-3**, never
cell-weighted (which straddles Carroll and overstates recovery).

| Parameter | | Note |
|---|---|---|
| `R_PICPOC` | **50/50** | 6/50 without a real calcite anchor |
| `alpfe` | **49/50** | strong in every basin |
| `scav_rat` | **25/50** | S. Ocean 49, eq. Pacific 7 |
| `diatomgraz` | **3/50** | inverts `scav_rat` — 37 at the equator |
| trio {`alpfe`,`scav_rat`,`R_PICPOC`} | **25/50** | vs **0/50** global-scalar |

The denominator is **4, not 6** — the growth pair is unobservable by construction, excluded rather
than failed. `scav_rat` and `diatomgraz` recover in opposite basins, so no config gets all four:
the **3-of-4 frontier is structural**. The binding constraint is the observing system, not the
method.

**Forward emulator — a clean negative result.** Physically valid (0% negative concentrations in log
space, mass ratio 1.000) but the useful horizon is **one step**, with no significant skill over a
seasonal AR(1) baseline (−0.161 ± 0.013). The "~9-month horizon" (a `delta_t` artifact) and "beats
persistence" (a weak baseline) are **retracted**. The reusable asset is infrastructure: the first
ocean-BGC Earth2Studio `PrognosticModel`, plus physics validators.

> Global emulator figures from before 2026-07-25 predate the log-space fix — do not show them.

## Docs

📖 **[ecco-darwindiff.readthedocs.io][docs_url]** — [Onboarding][onboarding_url] (start here) ·
[Status][status_url] (canonical numbers) · [Results matrix][matrix_url] · [References](docs/references.md)

## Citation

```bibtex
@software{darwindiff_2026,
  author    = {{ECCO-DarwinDiff contributors}},
  title     = {{ECCO-DarwinDiff}: Differentiable Ocean Biogeochemistry},
  year      = {2026}, publisher = {GitHub},
  url       = {https://github.com/2imi9/ECCO-DarwinDiff}
}
```

If your work depends on the underlying model, cite Carroll et al. [2020][c20] and [2022][c22].

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) — scope-prefixed PR titles and the `verify_run.py` gate
every number must pass.

Thanks to **MIT EAPS**, **Northeastern Research Computing** (Explorer H200), **Massachusetts AI
Compute Resource** (B200), **JPL ECCO** + **NASA NAS**, and **GLODAP** / **GEOTRACES**.
MIT licensed — see [LICENSE](LICENSE).

<!-- Reference links -->
[docs_url]: https://ecco-darwindiff.readthedocs.io/en/latest/
[onboarding_url]: docs/ONBOARDING.md
[status_url]: STATUS.md
[matrix_url]: docs/results_matrix.md
[cluster_url]: docs/cluster_setup.md
[data_url]: data/README.md
[demo_url]: notebooks/demo_colab.ipynb
[colab_url]: https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb
[c20]: https://doi.org/10.1029/2019MS001888
[c22]: https://doi.org/10.1029/2021GB007162
