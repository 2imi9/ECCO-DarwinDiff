<!-- markdownlint-disable MD033 MD041 -->
<div align="center">

# ECCO-DarwinDiff

<img src="docs/dinn_architecture.svg" alt="DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights" width="640">

**Differentiable ocean biogeochemistry — every parameter gets a gradient in one backward pass,
so you can ask which ones the observations actually pin down.**

[![Tests](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml/badge.svg)](https://github.com/2imi9/ECCO-DarwinDiff/actions/workflows/tests.yml)
[![Docs](https://readthedocs.org/projects/ecco-darwindiff/badge/?version=latest)](https://ecco-darwindiff.readthedocs.io/en/latest/)
[![Colab](https://colab.research.google.com/assets/colab-badge.svg)][colab_url]
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Start here][onboarding_url] · [Docs][docs_url] · [Status][status_url] · [Results matrix][matrix_url] · [Research map][map_url]

</div>

## The question

Ocean biogeochemistry models decide how much carbon the ocean takes up, and their governing
parameters are not measured. They are tuned. ECCO-Darwin ([Carroll 2020][c20], [2022][c22]) tunes
six of them with Green's functions, which costs one full forward run per parameter, so six is the
practical ceiling.

This project reimplements that biogeochemistry in PyTorch so every parameter gets a gradient in one
backward pass, varying per grid cell through a small network reading the local environment. The
point is not speed. It is to ask a question the tuning loop cannot: **which parameters do real
observations actually pin down, and which are we only guessing at?**

The answer turns out to be parameter-specific and basin-specific, and two of the six are not
identifiable from these observations at all. That is the result.

This is a **consistency check against Carroll's published values, not a cross-validated
discovery** — the 0-D box homogenizes, so it does not produce held-out spatial skill on real
data.[^heldout]

[^heldout]: Measured, gated, and archived:
    [`docs/findings/2026-07-29_heldout_geotraces_n10e2k.json`](docs/findings/2026-07-29_heldout_geotraces_n10e2k.json).
    Flagship recipe with 20% of the GEOTRACES iron cells held out of training, n=10 seeds,
    `verify_run.py` exit 0. **All 30 (AOI × seed) held-out R² values are negative; the best is
    −0.30** — the fit does worse than predicting the held-out mean, in every basin and every seed.
    The held-out sets are small (5/3/3 cells), so the result rests on the unanimity of the sign,
    not on any single R².

## Results

Flagship `n50e2k_percell_trio` — n=50 seeds, 2000 epochs. Metric is **per-AOI ≥2-of-3**, never
cell-weighted (which straddles Carroll and overstates recovery). Counts are under the
**arithmetic** per-AOI collapse unless a second figure is given.

| Parameter | Recovery | Note |
|---|---|---|
| `R_PICPOC` | **50/50** | 6/50 without a real calcite anchor; collapse-invariant — but **anchor-conditional**, see below |
| `alpfe` | **49/50** | every basin, and collapse-invariant — but **railed at its 1.0 bound**, see below |
| `scav_rat` | **25/50** arith · **13/50** geom | the North Atlantic leg carries the difference, 19 → 5 |
| `diatomgraz` | **40/100** eqpac | graded per-leg at ≤10% vs untrained **0/50** (P=5.5e-09); anti-recovered elsewhere |
| trio {`alpfe`,`scav_rat`,`R_PICPOC`} | **25/50** arith · **12/50** geom | vs **0/50** global-scalar |

**Three of these numbers do not mean what they look like.** `scav_rat` is a log-scale parameter and
the arithmetic collapse inflates it by `exp(σ²/2)`, so the trio roughly halves under the geometric
collapse; the flagship's own artifacts predate the instrumentation, so this is measured on a
bitwise-identical twin. And `alpfe`'s bounds are (0.05, **1.0**) against a Carroll value of
**0.92831**, so the ceiling sits 7.72% above truth and the fit saturates there — 45–49 of 50 seeds
land within 1% of the bound, and the band sweep is a step function (0/50 at 0.05 and 0.06, 49/50
from 0.08 up). The *signal* is real and survives its own control (98/100 against an untrained 0/100, at the
bands the gated sweep measures, ≤0.20 and ≤0.30). The *precision* is bound-determined, and that
is now measured rather than open: widening the bound to 1.6 moves the **untrained** null into
the pass band, where it scores **50/50 against the trained arm's 0/50**. `alpfe` rails to
whatever bound it is given, so this is a boundary diagnostic, not an accuracy number.

**`R_PICPOC`'s 50/50 is conditional on one specific calcite compilation, and one of its three
basins had no data.** Swapping Daniels 2018 for its direct successor Marsh 2025 drops recovery to
30/50 (P = 1.8e-07), and out-of-sample at n=100, 98/100 → 50/100 (P = 2.7e-16). The reason is
instructive rather than fatal: under Daniels the Southern Ocean has **zero** calcite cells, so its
leg was inherited through the shared network rather than measured — and it passed. Give it 12 real
observations and the basin moves to 1.57× Carroll and its leg reads 0/50. That is evidence that
Carroll's single global rain ratio is under-constrained, which is a result, but it means the 50/50
should be read as *anchor-conditional*, not as validation of the value 0.0425.

The denominator is **4, not 6** — the growth pair is excluded, not failed, for two different
reasons. `Biggrow` is unobservable by construction (never recovers, seasonal included); `Smallgrow`
is not identifiable from the **time-mean** observables this study fits, though a seasonal prototype
recovers it in strong-bloom basins (N. Atlantic 9/10, unconfirmed). `scav_rat` and `diatomgraz`
recover in opposite basins, so no config gets all four. Whether that ceiling is **structural**
(information the observations do not carry) or **practical** (optimisation) is still open — `ded77`
is unsettled, and differential-algebra structural identifiability can settle it symbolically, with
no data and no cluster time.

**Forward emulator — a clean negative result.** Positivity holds in log space (0% negative
concentrations on all six tracers) but **mass is not conserved** — Chl1 drifts +130% over six
rollout steps — and the useful horizon is **one step**, with no significant skill over a
seasonal AR(1) baseline (−0.161 ± 0.015). The "~9-month horizon" (a `delta_t` artifact) and "beats
persistence" (a weak baseline) are **retracted**. The reusable asset is infrastructure: the first
ocean-BGC Earth2Studio `PrognosticModel`, plus physics validators.

> Global emulator figures from before 2026-07-25 predate the log-space fix — do not show them.

## How every number here is gated

A parameter-recovery result is easy to fake by accident: pick a favourable metric, compare against
a weak baseline, or quote a run whose instrumentation was missing. This repository is built so that
each of those fails loudly rather than silently.

- **Nothing is reported without a matched control.** Every recovery count is graded against either
  an architecture-matched untrained network or the same fit with its identifying anchor withheld.
  A count with no control is not a result.
- **One grading rule, chosen in advance.** Per-AOI ≥2-of-3, never cell-weighted. Cell-weighting
  lets per-basin legs straddle Carroll's value and overstates recovery, most severely for the one
  parameter whose recovery is weakest.
- **Pooler sensitivity is audited, not assumed.** `scav_rat` spans two decades, so the arithmetic
  mean inflates it. All three collapses are reported. Where the deciding keys are absent,
  `pooler_audit.py` exits 2 — 119 of 211 run directories are not auditable at all, and that is
  surfaced rather than quietly defaulted to the flattering number.
- **Every number passes a gate before it is written down.** `uv run python scripts/verify_run.py
  <run-dir>` must exit 0.
- **Retractions are first-class.** The [research map][map_url] is a queryable record of what is
  known and how strongly. It currently holds **590 claims and 302 retractions** — this project has
  retracted about half of what it has claimed, on its own evidence, and each retraction names what
  replaced it. SQL integrity constraints fail the build on a claim that cites a missing document or
  a DOI that resolves to the wrong paper.

```bash
python scripts/research_map_db.py settled <topic>     # is this already answered?
python scripts/research_map_db.py superseded <number> # has this number been retracted?
python scripts/research_map_db.py check               # integrity constraints; exit 1 on violation
```

209 finding documents and 90 test modules, under a research map of 590 claims and 302 retractions.

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

## Docs

📖 **[ecco-darwindiff.readthedocs.io][docs_url]** — [Onboarding][onboarding_url] (start here) ·
[Status][status_url] (canonical numbers) · [Results matrix][matrix_url] ·
[Research map][map_url] (what is known, and what has been retracted) ·
[References](docs/references.md)

## Citation

```bibtex
@software{darwindiff_2026,
  author    = {Qi, Ziming},
  title     = {{ECCO-DarwinDiff}: Differentiable Ocean Biogeochemistry},
  year      = {2026}, publisher = {GitHub},
  url       = {https://github.com/2imi9/ECCO-DarwinDiff}
}
```

If your work depends on the underlying model, cite Carroll et al. [2020][c20] and [2022][c22].

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) — scope-prefixed PR titles and the `verify_run.py` gate
every number must pass.

MIT licensed — see [LICENSE](LICENSE).

<!-- Reference links -->
[docs_url]: https://ecco-darwindiff.readthedocs.io/en/latest/
[onboarding_url]: docs/ONBOARDING.md
[status_url]: STATUS.md
[matrix_url]: docs/results_matrix.md
[map_url]: docs/research_map.md
[cluster_url]: docs/cluster_setup.md
[data_url]: data/README.md
[demo_url]: notebooks/demo_colab.ipynb
[colab_url]: https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb
[c20]: https://doi.org/10.1029/2019MS001888
[c22]: https://doi.org/10.1029/2021GB007162
