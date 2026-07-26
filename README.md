<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="680">

**Differentiable ocean biogeochemistry. Gradients flow through the whole simulation, so one backward pass recovers the parameters that Green's-functions calibration tunes one at a time.**

[![Tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Start here][onboarding_url] · [Docs][docs_url] · [Status][status_url] · [Results matrix][matrix_url]

</div>

## What this is

ECCO-Darwin ([Carroll et al. 2020][c20], [2022][c22]) calibrates its biogeochemistry with **Green's
functions** — one full forward run per parameter, so only six are tuned. DarwinDiff reimplements the
biogeochemistry in **PyTorch**, so every parameter gets a gradient in one backward pass, and the
values vary per grid cell via a small network reading the local environment.

The result is a **surrogate-to-model identifiability study**: which parameters real observations can
pin down, which they cannot, and why. It is a **consistency check against Carroll's published
values, not a cross-validated discovery** — the 0-D box homogenizes, so held-out real-data R² is
negative.

## Install

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync                     # environment from pyproject / uv.lock
uv run pytest -q            # smoke test (data-gated tests self-skip)
```

Python 3.11+, PyTorch 2.4+. The synthetic demo needs nothing else. For real fits, point the loaders
at the LLC270 tree with `DARWIN_DATA_ROOT` — see [cluster setup][cluster_url] and [data][data_url].

## Quick start

The synthetic recovery demo runs in ~5 min on a laptop or free Colab T4:
[`notebooks/demo_colab.ipynb`][demo_url] ([![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]).

```python
import torch
from darwindiff.carroll6 import PARAM_BOUNDS, bounded_params, carroll6_integrate
from darwindiff.networks import DINN

env = torch.randn(3, 8, 16)                       # [SST, wind, MLD] over an 8x16 grid
dinn = DINN(n_input_channels=3, hidden_dim=16, n_outputs=6)
params = bounded_params(dinn(env), PARAM_BOUNDS)  # [6, 8, 16], bounded to physical ranges

state0 = torch.full((5, 8, 16), 0.1)              # [DFe, Ps, Pl, POC, PIC]
final = carroll6_integrate(state0, params, dt=0.25, n_steps=200)
loss = (final - target).pow(2).mean()             # target: an ECCO-Darwin v05 field
loss.backward()                                   # gradients through the whole simulation
```

Every reported number must pass the verification gate:

```bash
uv run python scripts/verify_run.py runs/eqpac          # exit 0 == trustworthy
```

## Results

**Parameter recovery.** Flagship `n50e2k_percell_trio`: n=50 seeds, 2000 epochs, `verify_run` exit 0.
Metric is **per-AOI ≥2-of-3 Cal-grade** — never cell-weighted, which straddles Carroll and overstates
recovery.

| Parameter | Recovered | Notes |
|---|---|---|
| `R_PICPOC` | **50/50** | Needs a real calcite anchor — drops to 6/50 without it |
| `alpfe` | **49/50** | Strong in every basin |
| `scav_rat` | **25/50** | Southern Ocean 49/50, equatorial Pacific 7/50 |
| `diatomgraz` | **3/50** | Inverts `scav_rat` — 37/50 at the equator |
| trio {`alpfe`,`scav_rat`,`R_PICPOC`} | **25/50** | vs **0/50** global-scalar — the per-cell network is load-bearing |

Three things this shows:

- **The denominator is 4, not 6.** The growth pair {`Smallgrow`, `Biggrow`} is **unobservable by
  construction** — excluded, not failed. "6/6" is the wrong frame.
- **Identifiability is basin-specific.** `scav_rat` and `diatomgraz` recover in opposite basins, which
  is why no single config gets all four. The **3-of-4 frontier is structural**, with two operating
  points: `geo1` holds {`alpfe`, `scav_rat`, `R_PICPOC`}; adding an MLD channel holds
  {`alpfe`, `diatomgraz`, `R_PICPOC`} instead.
- **The binding constraint is the observing system, not the method.** Adding prescribed transport does
  not turn the consistency check into a discovery: across three closures, real observations fail to
  constrain them for three distinct reasons — iron is an observability wall in the equatorial Pacific,
  calcite is support-limited, growth is structurally unobservable.

**Forward emulator — a clean negative result.** Physically valid (0% negative concentrations in log
space, mass ratio 1.000, valid carbonate chemistry) but the **useful horizon is one step**, with no
significant skill over a per-cell seasonal AR(1) baseline (−0.161 ± 0.013). Two earlier headlines are
**retracted**: the "~9-month horizon" (a `delta_t` calendar artifact) and "beats persistence" (a weak
baseline). The reusable asset is the infrastructure — the first ocean-BGC Earth2Studio
`PrognosticModel`, plus physics validators.

> Global emulator figures produced before 2026-07-25 predate the log-space fix and must not be shown.

Full per-config record: [results matrix][matrix_url]. Current state and limits: [STATUS.md][status_url].

## Documentation

📖 **[ecco-darwindiff.readthedocs.io][docs_url]**

- **[Onboarding][onboarding_url]** — start here for a cold read
- [Status][status_url] — canonical numbers and known limits
- [Results matrix][matrix_url] — what every config tested and found
- [DINN design](https://ecco-darwindiff.readthedocs.io/en/latest/dinn_design/) · [ECCO-Darwin relationship](https://ecco-darwindiff.readthedocs.io/en/latest/ecco_darwin_relationship/) · [Cluster setup][cluster_url] · [Data][data_url]

<details>
<summary><b>Repository layout</b></summary>

```
src/darwindiff/            Python package
  carroll6.py                5-tracer Carroll-6 box + Carroll's optima + bounds
  carbonate.py               Follows-2006 + Wanninkhof 2014 carbonate solver
  carroll6_5pft_2layer.py    2-layer 5-PFT integrator (seasonal + seed-batched)
  networks.py                DINN + DINNRegional + DINNDeep
  *_loader.py                Darwin v05, LLC270, GLODAP, GEOTRACES loaders
scripts/                   runners, sweeps, verify_run.py, SLURM templates
notebooks/                 demo_colab.ipynb is the synthetic walkthrough
tests/                     pytest suite (runs in CI)
docs/                      results_matrix.md, dinn_design.md, archive/
```

</details>

## Citation

A manuscript and Zenodo DOI will follow publication. For now, cite the repository:

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

If your work depends on the underlying model, cite Carroll et al. [2020][c20] and [2022][c22].
Background reading and the full reference table: [docs/references.md](docs/references.md).

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) first — scope-prefixed PR titles, merge conventions, and the
`verify_run.py` loop every reported number must pass. CI runs the suite on every PR.

## Acknowledgements

**MIT EAPS** (research collaboration) · **Northeastern Research Computing** (Explorer H200) ·
**Massachusetts AI Compute Resource** (B200) · **JPL ECCO Group** + **NASA NAS** (ECCO-Darwin v05
outputs) · **GLODAP**, **GEOTRACES**, **NASA GHG Center** (observational products).

## License

MIT — see [LICENSE](LICENSE). The underlying ECCO-Darwin model is the work of the ECCO and Darwin
teams and should be credited independently.

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
