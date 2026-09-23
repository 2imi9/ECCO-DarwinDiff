# ECCO-DarwinDiff

**Differentiable ocean biogeochemistry: which parameters do real observations actually pin down?**

<figure markdown="span">
  ![DINN architecture: the flagship reads sea-surface temperature alone (optional wind-speed and mixed-layer-depth ablation channels are shown faded) through two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights](dinn_architecture.svg){ width="820" }
  <figcaption>DarwinDiff's per-cell network (DINN). The loss flows through the differentiable box model, so one backward pass gives gradients for all six Carroll parameters. Four of them are the observable identifiability target.</figcaption>
</figure>

DarwinDiff is a PyTorch **differentiable box model** of ocean biogeochemistry: a 15-tracer,
two-layer, five-plankton proxy of ECCO-Darwin (the original 5-tracer box, `carroll6.py`, remains
as the teaching model), with **gradients through every step of the integration**. A small network
predicts the parameters that Carroll's Green's-functions calibration tunes one at a time, *per grid
cell*, from the local environment.

It is a **surrogate-to-model identifiability study**: a consistency check against Carroll's own
published values, not a cross-validated discovery. A write-up is in preparation.

!!! note "This is the documentation home"
    **[Project Status](status.md)** is the canonical, always-current snapshot of results. New here?
    Read **[Start here](ONBOARDING.md)** first. The source lives on
    [GitHub](https://github.com/2imi9/ECCO-DarwinDiff).

## What we found

Flagship `n50e2k_percell_trio`: n=50 seeds, 2000 epochs, graded **per-AOI ≥2-of-3** (never
cell-weighted). Counts are under the **arithmetic** per-AOI collapse unless a second figure is given.

| Parameter | Recovery | In one line |
|---|---|---|
| `R_PICPOC` | **50/50** | 6/50 with the calcite anchor withheld (epoch-matched). **Anchor-conditional**: Marsh 2025 in place of Daniels 2018 gives 30/50 |
| `alpfe` | **49/50** | **Railed at its 1.0 bound**, and rails to a 1.6 bound too: the data fix a direction, not a value |
| `scav_rat` | **25/50** arith · **13/50** geom | Established only in the Southern Ocean (30/50 single-AOI, against a measured untrained rate of 0.060) |
| `diatomgraz` | **40/100** eqpac | Graded per-leg at ≤10% vs untrained **0/50** (P=5.5e-09). Anti-recovered in the other two basins |
| trio {`alpfe`,`scav_rat`,`R_PICPOC`} | **25/50** arith · **12/50** geom | vs **0/50** for a global-scalar control, so the per-cell network is load-bearing |

**Two parameters recovered in every basin** (`alpfe` as a direction, `R_PICPOC` conditional on its
anchor), **two regionally identifiable in different basins** (`scav_rat`, `diatomgraz`), and **two
excluded by construction**. The growth pair is excluded for two different reasons: `Biggrow` is
unobservable by construction (never recovers, seasonal included), while `Smallgrow` is not
identifiable from the **time-mean** observables this study fits (a seasonal prototype recovers it
9/10 in the North Atlantic, unconfirmed, job 189324).

The surrogate gap is **dimensional**: the 0-D box homogenizes spatial structure, so identifiability
rests on real *absolute* anchors, and held-out spatial skill on real data is negative. The caveats
behind every row, and the retracted readings they replaced, are in **[Project Status](status.md)**.

## Two tracks

1. **Parameter learner.** The identifiability study above. Results are gated by `verify_run.py`
   and, for `scav_rat`, by the pooler audit; every number carries a matched control.
2. **Identifiability limits and a forward emulator.** With prescribed transport, can real
   observations constrain Darwin's closures? Not sharply, for any of the three tested (iron,
   calcite, growth). The iron-sink test (E3) was **never run**: its anchor, GP15 ²¹⁰Po/²¹⁰Pb, has
   zero points in the three flagship basins (92 points in `npac`), so the test is mislocated, not
   settled, and whether the iron wall is the observing system or the method is still open
   (`ded77`). The forward neural emulator is a **clean negative result**. Trained in log space it
   emits 0% non-physical output, but **mass is not conserved** (Chl1 drifts +129.7% over six
   rollout steps), the useful horizon is **one step**, and against a per-cell seasonal AR(1)
   baseline it scores −0.161 ± 0.015. The "~9-month horizon" and "beats persistence" headlines are
   **retracted**. Every global emulator figure from before 2026-07-25 is contaminated by a
   linear-z-score bug and should not be shown.

## Documentation map

<div class="grid cards" markdown>

-   :material-compass: **[Start here](ONBOARDING.md)**

    ---

    What the project is, what it deliberately is not, and the handful of ideas you need to follow any result.

-   :material-chart-line: **[Project Status](status.md)**

    ---

    The canonical current-best snapshot: headline numbers, the identifiability frame (4 observable params; growth pair excluded), and known limitations.

-   :material-graph: **[Research map](research_map.md)**

    ---

    Everything known, how strongly, and what has been retracted. Queryable as SQL with `scripts/research_map_db.py`.

-   :material-table: **[Config / Results Matrix](results_matrix.md)**

    ---

    What every config (v2.x box → 3-AOI `geo1` → native LLC270 → Track-2 feasibility probes) tested, found, and how each differs.

-   :material-sitemap: **[DINN design](dinn_design.md)**

    ---

    Network architecture, the differentiable box model, the training loop, and the structural argument behind per-cell parameter recovery.

-   :material-water: **[ECCO-Darwin relationship](ecco_darwin_relationship.md)**

    ---

    How the box model maps onto full ECCO-Darwin, and the [parameter inventory](ecco_darwin_parameter_inventory.md) of what is and isn't being recovered.

-   :material-flask: **[Archive](archive/index.md)**

    ---

    Per-version research provenance, v2.1 → v3.2 (out of the onboarding path): the verified experimental record behind each matrix row.

-   :material-server: **[Cluster setup](cluster_setup.md)**

    ---

    Northeastern Explorer + AICR setup, partitions, storage, and SLURM templates. See also the [cluster roadmap](cluster_roadmap.md).

-   :material-database: **[Data sources](data.md)**

    ---

    Dataset provenance and download mechanics: ECCO-Darwin v05, GLODAP, GEOTRACES, and the shelved leapfrog sources.

</div>

## Quick start

```bash
git clone https://github.com/2imi9/ECCO-DarwinDiff.git && cd ECCO-DarwinDiff
uv sync && uv run pytest -q          # smoke test
```

The runnable synthetic-recovery demo (a few minutes on CPU, or Colab) lives in
[`notebooks/demo_colab.ipynb`](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb).
It uses the 5-tracer teaching box; the flagship uses the 15-tracer two-layer box.

## Background reading

ECCO-Darwin (Carroll et al. [2020](https://doi.org/10.1029/2019MS001888), *JAMES*; [2022](https://doi.org/10.1029/2021GB007162), *GBC*) is calibrated via **Green's functions** ([Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1)), which scale badly: each tuned parameter needs a fresh full forward run, so the published calibration handles only **6 parameters**. DarwinDiff replaces the biogeochemistry side with PyTorch autograd, so all parameters get gradients in one backward pass, with values varying across space. That removes the **cost** barrier, not the information one: the study targets the same six parameters, of which four are the observable identifiability target, and its central result is *which* of those real observations can and cannot constrain. The closest method template is the per-location parameter network of [Xu et al. 2025 (BINN)](https://arxiv.org/abs/2502.00672); the full reference list is in [References](references.md).

## How to cite

A formal write-up and Zenodo DOI will follow. In the interim, cite the repository directly:

```bibtex
@software{darwindiff_2026,
  author    = {Qi, Ziming},
  title     = {{ECCO-DarwinDiff}: Differentiable Ocean Biogeochemistry},
  year      = {2026}, publisher = {GitHub},
  url       = {https://github.com/2imi9/ECCO-DarwinDiff}
}
```

Released under the [MIT License](https://github.com/2imi9/ECCO-DarwinDiff/blob/main/LICENSE). The underlying ECCO-Darwin model is the work of the ECCO and Darwin teams; cite Carroll et al. [2020](https://doi.org/10.1029/2019MS001888) and [2022](https://doi.org/10.1029/2021GB007162) if your work depends on it.
