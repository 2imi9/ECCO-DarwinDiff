<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="720">

**A differentiable PyTorch reimplementation of ECCO-Darwin ocean biogeochemistry — gradients flow through every step of the simulation, so one loss surface recovers the identifiable subset of the parameters that Green's-functions calibration tunes one at a time, predicted per grid cell from the local environment — a surrogate-to-model identifiability study.**

[![Tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![Documentation](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4%2B-ee4c2c.svg)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Documentation][docs_url] · [Project status][status_url] · [Results matrix][matrix_url] · [Quick start](#quick-start) · [Citation](#citation)

</div>

ECCO-Darwin (Carroll et al. [2020][c20], *JAMES*; [2022][c22], *GBC*) calibrates its
ocean-biogeochemistry parameters with **Green's functions** — a method that needs a fresh full
forward run per parameter, so the published calibration tunes only six. **ECCO-DarwinDiff** replaces
the biogeochemistry side with **PyTorch autograd**: gradients for every parameter in a single
backward pass, with the values varying across space, predicted by a small per-cell network. The work
is framed as a **surrogate-to-model identifiability study** — which of the six Carroll-6 parameters are
identifiable from real ocean observations, which are not, and why. *The study is complete; paper #1 is in
preparation.*

Two tracks: **(1) Parameter learner** *(complete — paper #1 in preparation)* — a surrogate-to-model
identifiability study that replaces Green's-functions calibration;
**(2) Emulator / spatial UDE** *(feasibility-probed on the 0-D box; real-scale build gated on paper #1)* —
a differentiable spatial model / neural stand-in for long-timescale climate runs. Box-scale probes are
synthetic self-twin only (no transport, not real Darwin).

## Installation

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync                     # create the environment from pyproject / uv.lock
uv run pytest -q            # smoke test (LLC270 / data tests self-skip)
```

Targets **Python 3.11+** and **PyTorch 2.4+**. The synthetic demo needs nothing else; for real fits,
point the loaders at the LLC270 tree via `DARWIN_DATA_ROOT` (and `GLODAP_DATA_ROOT`). Raw-data
mechanics (Windows `MAX_PATH`, IC caches, per-loader layout) are in
[docs/cluster_setup.md][cluster_url] and [data/README.md][data_url].

## Quick start

Run the synthetic recovery demo in ~5 min on a laptop or a free Colab T4 —
[`notebooks/demo_colab.ipynb`][demo_url] ([![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]).
The core idea — a per-cell network whose loss backpropagates through the differentiable box — is a few
lines of the public API:

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

For a real recovery on ECCO-Darwin v05 data, the runners are in `scripts/` and every reported number
is gated by the verified-experiment loop:

```bash
uv run python scripts/run_seasonal_recovery.py --aoi eqpac --n-seeds 10 --compile --out-dir runs/eqpac
uv run python scripts/verify_run.py runs/eqpac          # exit 0 == trustworthy
```

## Headline result

The iron pair (`alpfe`, `scav_rat`) recovers reproducibly — **38/40 (95 %)** at the best 3-AOI config
(~7 min/fit) — and **`R_PICPOC`** recovers against a real calcite anchor (Daniels CP:PP / MODIS PIC).
The best config (`geo1`) holds **{`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 7/10 seeds** — a
3-of-4-observable frontier, driven by real, Darwin-independent anchors. This is a consistency check
against Carroll's own values, not a cross-validated discovery against the GCM: the 0-D box homogenizes
(no transport), so held-out real-data R² is negative and identifiability must come from real absolute
anchors — closing that gap is Track 2's job.

The honest target is **4 observable params**; the growth pair {`Smallgrow`, `Biggrow`} is
**unobservable by construction** (growth rates are not measured), so "6/6" is the wrong frame — and
`R_PICPOC` was never a wall. It recovers against real calcite (consistent with Carroll within the wide
Cal band, not a validation of 0.0425); the deeper result is that Carroll's *global* rain ratio is itself
under-constrained and should be regional. **The full per-config record is the [Config / Results Matrix][matrix_url]**;
current best + known limits live in **[STATUS.md][status_url]**.

## Documentation

📖 **[ecco-darwindiff.readthedocs.io][docs_url]**

- [Project status][status_url] — canonical current-best snapshot + known limits
- [Config / Results Matrix][matrix_url] — what every config tested and found (single source of truth)
- [DINN design](https://ecco-darwindiff.readthedocs.io/en/latest/dinn_design/) · [ECCO-Darwin relationship](https://ecco-darwindiff.readthedocs.io/en/latest/ecco_darwin_relationship/) · [Cluster setup](https://ecco-darwindiff.readthedocs.io/en/latest/cluster_setup/) · [Data sources](https://ecco-darwindiff.readthedocs.io/en/latest/data/)
- [Archive](https://ecco-darwindiff.readthedocs.io/en/latest/archive/) — per-version research provenance (out of the onboarding path)

<details>
<summary><b>Repository layout</b></summary>

```
src/darwindiff/            Python package (importable as `darwindiff`)
  carroll6.py                5-tracer Carroll-6 box + Carroll's optima + bounds
  carbonate.py               Follows-2006 + Wanninkhof 2014 carbonate solver
  carroll6_5pft_2layer.py    2-layer 5-PFT integrator (seasonal + seed-batched)
  networks.py                DINN + DINNRegional + DINNDeep
  ecco_darwin_loader.py      Darwin v05 1° loader + AOI presets
  llc270_loader.py           native LLC270 monthly loader (xmitgcm)
  glodap_loader.py           GLODAPv2.2016b DIC/ALK loader
scripts/                   runners, overnight sweeps, verify_run.py, SLURM templates
notebooks/                 numbered notebooks 05–32; demo_colab.ipynb is the synthetic walkthrough
tests/                     pytest suite (runs in CI)
docs/                      results_matrix.md, dinn_design.md, cluster_setup.md, archive/
```

</details>

## Citation

DarwinDiff is under active development; a formal manuscript and Zenodo DOI will be issued upon
publication. In the interim, cite the repository directly:

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
<summary><b>Underlying ECCO-Darwin model + background reading</b> (DOIs verified via OpenAlex)</summary>

If your work depends on the underlying model, cite Carroll et al.
[2020][c20] (*JAMES*) and [2022][c22] (*GBC*).

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020][c20] (*JAMES*) | Original ECCO-Darwin; the 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022][c22] (*GBC*) | ECCO-Darwin v05; the publicly-accessible Darwin output is our active recovery target. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*GBC*) | Core Darwin biogeochemistry equations (`carroll6.py`). |
| [Follows et al. 2006](https://doi.org/10.1016/j.ocemod.2005.05.004) · [Wanninkhof 2014](https://doi.org/10.4319/lom.2014.12.351) | Carbonate-system solver + air-sea CO₂ flux (`carbonate.py`). |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*MWR*) | The Green's-functions calibration method DarwinDiff replaces. |
| [Olsen et al. 2016](https://doi.org/10.5194/essd-8-297-2016) · [Schlitzer et al. 2018](https://doi.org/10.1016/j.chemgeo.2018.05.040) | GLODAP DIC/ALK + GEOTRACES iron observations (loaders / losses). |
| [Xu et al. 2025 (BINN)](https://arxiv.org/abs/2502.00672) | Differentiable physics + per-location parameter network — closest method template. |
| [Kochkov et al. 2024 (NeuralGCM)](https://arxiv.org/abs/2311.07222) · [Clark et al. 2026 (ACE2S)](https://arxiv.org/abs/2606.07928) · [Ouala & Lachkar 2026 (Neural-BGC)](https://doi.org/10.22541/essoar.15002003/v1) | Hybrid-physics / emulator references for Track 2. |
| [Dheeshjith et al. 2024 (Samudra)](https://arxiv.org/abs/2412.03795) · [Yuan et al. 2026 (Samudra 2)](https://arxiv.org/abs/2606.02610) · [Ai2 2025 (SamudrACE)](https://arxiv.org/abs/2509.12490) | AI ocean / coupled-climate emulators — architecture, resolution-scaling, and coupling templates for Track 2. SamudrACE names an explicit biogeochemistry hole as future work — the carbon-BGC-UDE slot Track 2 targets; none emulate ocean carbon (the whitespace). See [ADR-0002](docs/adr/0002-track2-emulator-scope.md). |

</details>

## Contributing

Contributions are welcome — read **[CONTRIBUTING.md](CONTRIBUTING.md)** first (scope-prefixed PR
titles, commit/merge conventions, and the `scripts/verify_run.py` loop every reported number must
pass). CI runs the test suite on every PR; run it locally with `uv run pytest -q`.

## Acknowledgements

- **MIT EAPS** — research collaboration on ECCO-Darwin and the differentiable-physics approach.
- **Northeastern Research Computing** — the **Explorer** (H200) and **AICR** (B200) clusters.
- **JPL ECCO Group** + **NASA NAS** — ECCO-Darwin v05 outputs.
- **GLODAP**, **GEOTRACES**, **NASA GHG Center** — observational data products (active recovery targets).

## License

Released under the **MIT License** — see [LICENSE](LICENSE). The underlying ECCO-Darwin model is the
work of the ECCO and Darwin teams and should be credited independently (citation block above).

<!-- Reference links -->
[docs_url]: https://ecco-darwindiff.readthedocs.io/en/latest/
[status_url]: STATUS.md
[matrix_url]: docs/results_matrix.md
[cluster_url]: docs/cluster_setup.md
[data_url]: data/README.md
[demo_url]: notebooks/demo_colab.ipynb
[colab_url]: https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb
[c20]: https://doi.org/10.1029/2019MS001888
[c22]: https://doi.org/10.1029/2021GB007162
