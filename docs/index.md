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
2. **Emulator** *(active)* — a neural stand-in for ECCO-Darwin. A global single-step forward operator exists and is characterised; it is **not** a validated multi-month rollout emulator. See the Track-2 section of **[Project Status](status.md)**.

## What works · what's blocked

=== "Works"

    - The iron pair (`alpfe`, `scav_rat`) recovers reproducibly — **38/40 (95%)** at the best 3-AOI config; one fit runs in ~7 min on a single GPU.
    - A **reproducible 5/6** at 3-AOI (v3.2): dense-Darwin `POSi` + Eppley temperature limitation recover `diatomgraz` alongside the iron pair — mean **2.0 → 3.85/6**, 70% of seeds ≥4/6 (n=20). The synthetic demo runs end-to-end on a laptop / free Colab T4.

=== "Blocked"

    - **Not a 6/6 chase.** The honest target is **4 observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`} — the growth pair {`Smallgrow`, `Biggrow`} is unobservable by construction. A joint 6/6 has been reached but is **not robust** (3/10 seeds).
    - **`R_PICPOC` was never the wall.** The earlier "needs the differentiable Darwin calcite port + native resolution" conclusion is **refuted** — both were tested and neither helped. The real gaps were the absence of a direct, real calcite observation (now supplied) and a contaminated Southern-Ocean ratio target (fixed by `RATIO_MAX=2`).
    - **`diatomgraz` is the unrecovered parameter** on real data (best 4/10 = chance), constrained only through a steady-state biogenic-silica diagnostic. Adding the dense Darwin `POSi` target recovers it 10/10 — a data-staging limit, not a structural wall.
    - 1° box-model proxy; 23-year climatology, not time-resolved; single-GPU prototype. Full evidence → **[Project Status](status.md)**.

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

-   :material-flask: **[Findings](findings/v3.1_closeout.md)**

    ---

    Per-version technical writeups, v2.1 → v3.2 — the experimental record behind each result, including the `R_PICPOC` structural campaign.

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
