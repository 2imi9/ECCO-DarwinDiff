# ECCO-DarwinDiff

**Differentiable ECCO-Darwin for ocean-biogeochemistry parameter recovery via gradient descent through the box model.**

<figure markdown="span">
  ![DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights](dinn_architecture.svg){ width="820" }
  <figcaption>DarwinDiff's per-cell network (DINN): the loss flows through the differentiable box model, so a single backward pass recovers the six Carroll parameters.</figcaption>
</figure>

DarwinDiff is a PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model in which **gradients flow through every step of the simulation**. A single loss surface learns the parameters that Carroll's Green's-functions calibration tunes one-at-a-time — predicted *per grid cell* from local environmental conditions. Manuscript in preparation.

!!! note "This is the documentation home"
    The narrative docs, design notes, and per-version findings are organized in the navigation on the left. **[Project Status](status.md)** is the canonical, always-current snapshot of results. The source lives on [GitHub](https://github.com/2imi9/ECCO-DarwinDiff).

## Two tracks

1. **Parameter learner** *(active)* — learns a per-cell function from local environment to the six Carroll parameters by gradient descent through the differentiable box model, replacing Green's-functions calibration.
2. **Emulator** *(not started)* — a neural stand-in for ECCO-Darwin for long-timescale climate runs.

## What's identifiable · what's not

This is a **surrogate-to-model identifiability study**: we recover what the data can constrain, validate it against real ocean observations, and state the rest honestly. (See the *Why recovery is imperfect, and how we fixed it* diagram.)

=== "Recovered + real-data validated"

    - **Iron pair (`alpfe`, `scav_rat`)** — reproducible (38/40 Darwin-graded) *and* independently preferred by **real GEOTRACES dissolved iron**: the converged FIM/profile spine puts `alpfe` at 0.103 under the full loss vs **0.9997 (≈Carroll) under real iron**, so the earlier "collapse" was loss-weighting, not a fundamental limit.
    - **`R_PICPOC` — first real-data-anchored recovery**: graded against the Darwin-**independent** Daniels 2018 CP:PP data (not Darwin's own PIC, which would be circular), it recovers **≥2-AOI in 50/50 seeds, Wilson 95% CI [0.93, 1.00]** (`verify_run.py` exit 0). One fit runs in ~16–57 s/seed on an H200.

=== "Not (yet) recoverable"

    - **Growth pair (`Smallgrow`, `Biggrow`)** — unobservable: growth rates are not measured, so no real anchor breaks their degeneracy.
    - **Not a 6/6.** The minimal real-R_PICPOC config trades away `alpfe` + `diatomgraz`; holding all of them together is the next experiment. The **self-twin** (zero surrogate gap) recovers θ to loss 5e-10, so the limits are surrogate-fidelity + loss-design + optimization — not a broken method.
    - 1° box-model proxy; 23-year climatology, not time-resolved. Full evidence → **[Project Status](status.md)**.

!!! note "Superseded"
    Earlier text called `R_PICPOC` "a 6/6 wall needing the differentiable Darwin calcite port + native resolution." The calcite port is **refuted at the box scale**, and `R_PICPOC` is now recovered via a real, Darwin-independent observation instead.

## Documentation map

<div class="grid cards" markdown>

-   :material-chart-line: **[Project Status](status.md)**

    ---

    The canonical live results doc — headline recovery table, version chronology, the 5/6 ceiling diagnosis, and known limitations.

-   :material-sitemap: **[DINN design](dinn_design.md)**

    ---

    Network architecture, the differentiable box model, the training loop, and the structural argument behind per-cell parameter recovery.

-   :material-water: **[ECCO-Darwin relationship](ecco_darwin_relationship.md)**

    ---

    How the box model maps onto full ECCO-Darwin, and the [parameter inventory](ecco_darwin_parameter_inventory.md) of what is and isn't being recovered.

-   :material-flask: **[Findings](findings/index.md)**

    ---

    Per-version technical writeups, v2.1 → the 2026-06 real-data validation — the experimental record behind each result, including the FIM identifiability spine and the Daniels `R_PICPOC` recovery.

-   :material-server: **[Cluster setup](cluster_setup.md)**

    ---

    NU Explorer (H200, **active path** — the real-data recoveries run here) + AICR (B200) + MIT ORCD Engaging setup, partitions, storage, and SLURM templates. See also the [cluster roadmap](cluster_roadmap.md).

-   :material-database: **[Data sources](data.md)**

    ---

    Dataset provenance and download mechanics — ECCO-Darwin v05, GLODAP, GEOTRACES, and the shelved leapfrog sources.

</div>

## Quick start

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync && uv run pytest -q          # smoke test
```

The runnable synthetic-recovery demo (~5 min, laptop / Colab T4) lives in
[`notebooks/demo_colab.ipynb`](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb),
and the full reproduce path is in the [README](https://github.com/2imi9/ECCO-DarwinDiff#reproduce).

## Background reading

ECCO-Darwin (Carroll et al. [2020](https://doi.org/10.1029/2019MS001888), *JAMES*; [2022](https://doi.org/10.1029/2021GB007162), *GBC*) is calibrated via **Green's functions** ([Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1)), which scale badly: each tuned parameter needs a fresh full forward run, so the published calibration handles only **6 parameters**. DarwinDiff replaces the biogeochemistry side with PyTorch autograd — gradients for all parameters in one backward pass, with values varying across space. The closest method template is the per-location parameter network of [Xu et al. 2025 (BINN)](https://arxiv.org/abs/2502.00672); the full annotated reference list is in the [README](https://github.com/2imi9/ECCO-DarwinDiff#background-reading).

## How to cite

DarwinDiff is under active development; a formal manuscript and Zenodo DOI will be issued upon publication. In the interim, cite the repository directly:

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

Released under the [MIT License](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/LICENSE). The underlying ECCO-Darwin model is the work of the ECCO and Darwin teams and should be credited independently — see the citation block in the [README](https://github.com/2imi9/ECCO-DarwinDiff#how-to-cite).
