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

## What works · what's blocked

This is a **surrogate-to-model identifiability study** — *which* of the six Carroll parameters are identifiable from real ocean observations. The honest target is **four observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real data constrains growth rates).

=== "Identifiable (real data)"

    - The iron pair (`alpfe`, `scav_rat`) recovers reproducibly — **38/40 (95%)** at the best 3-AOI config (~7 min/fit) — against real GEOTRACES IDP2025 dissolved iron.
    - **`R_PICPOC`** recovers against a real calcite anchor (Daniels CP:PP / MODIS PIC). The best config (`geo1`) holds **{`alpfe`, `scav_rat`, `R_PICPOC`} jointly in 8/10 seeds** — a 3-of-4-observable frontier (hold-together sweep, 8×n=10, all `verify_run` exit 0).

=== "Open / not identifiable"

    - **No 6/6 wall.** `R_PICPOC` is recoverable; the differentiable Darwin calcite port + native resolution were **tested and did not help** — the real gap was a direct calcite *observation*, now supplied.
    - **`diatomgraz`** is not recovered in the real-data sweep (best 4/10 = chance) — an iron-pair tradeoff, recoverable in principle only via dense Darwin POSi/TRAC16 (not yet staged). **The growth pair is unobservable by construction.**
    - The surrogate gap is **dimensional**: the 0-D box homogenizes spatial structure (tracer CV → ~1e-15), so identifiability rests on real *absolute* anchors. 1° proxy; 23-yr climatology; single-GPU. Full evidence → **[Project Status](status.md)**.

## Documentation map

<div class="grid cards" markdown>

-   :material-chart-line: **[Project Status](status.md)**

    ---

    The canonical live results doc — headline recovery table, version chronology, the identifiability frame (4 observable params; growth pair unobservable), and known limitations.

-   :material-sitemap: **[DINN design](dinn_design.md)**

    ---

    Network architecture, the differentiable box model, the training loop, and the structural argument behind per-cell parameter recovery.

-   :material-water: **[ECCO-Darwin relationship](ecco_darwin_relationship.md)**

    ---

    How the box model maps onto full ECCO-Darwin, and the [parameter inventory](ecco_darwin_parameter_inventory.md) of what is and isn't being recovered.

-   :material-flask: **[Findings](findings/v3.1_closeout.md)**

    ---

    Per-version technical writeups, v2.1 → v3.2 — the experimental record behind each result, including the `R_PICPOC` real-calcite-anchor result.

-   :material-server: **[Cluster setup](cluster_setup.md)**

    ---

    MIT ORCD Engaging + AICR (B200) setup, partitions, storage, and SLURM templates. See also the [cluster roadmap](cluster_roadmap.md).

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
