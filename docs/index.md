# ECCO-DarwinDiff

**Differentiable ECCO-Darwin for ocean-biogeochemistry parameter recovery via gradient descent through the box model.**

<figure markdown="span">
  ![DINN architecture: three environmental covariates (SST, wind speed, MLD) feed two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters; those parameters pass through bounded_params and the differentiable carroll6_step box model to an MSE loss versus ECCO-Darwin v05, and gradients flow back through the box model to update the network weights](dinn_architecture.svg){ width="820" }
  <figcaption>DarwinDiff's per-cell network (DINN): the loss flows through the differentiable box model, so a single backward pass yields gradients for all Carroll parameters at once — of which four are the observable identifiability target.</figcaption>
</figure>

DarwinDiff is a PyTorch **differentiable 0-D box model** of ocean biogeochemistry — a 5-tracer proxy of ECCO-Darwin — in which **gradients flow through every step of the box integration**. A single loss surface learns the parameters that Carroll's Green's-functions calibration tunes one-at-a-time — predicted *per grid cell* from local environmental conditions. Manuscript in preparation.

!!! note "This is the documentation home"
    The narrative docs, design notes, and per-version findings are organized in the navigation on the left. **[Project Status](status.md)** is the canonical, always-current snapshot of results. The source lives on [GitHub](https://github.com/2imi9/ECCO-DarwinDiff).

## Two tracks

1. **Parameter learner** *(complete — paper #1)* — a surrogate-to-model identifiability study: which of the Carroll parameters (four observable; see below) are identifiable from real ocean observations by gradient descent through the differentiable box model. It is a consistency check against Carroll's own values, not a validated replacement for Green's-functions calibration.
2. **Identifiability limits + a forward emulator** *(complete — paper #2)* — with prescribed transport, which BGC closures can real observations constrain? None of the three (iron, calcite, growth) sharply: the binding constraint is the **observing system, not the method**. The forward neural emulator is built and is a **clean negative result**. It is physically valid *once trained in log space* — the global run verified 2026-07-25 (AICR job 204877) emits **0.00% non-physical output on all six tracers** and retains 0.88–0.94 of the true log-range on the four log-transformed tracers (`Chl1` 0.891, `PIC` 0.906, `POC` 0.882, `FeT` 0.940; `DIC` and `ALK` are not log-transformed) and valid carbonate chemistry. **Mass is NOT conserved in that run**: its own artifact records relative drift of +129.7% for `Chl1`, +17.2% `POC`, −7.3% `PIC`, −6.3% `FeT` over six rollout steps (only `DIC`/`ALK` hold, at <0.1%), and `mass_conserve_enforced` was false. The blanket mass-conservation claim previously attributed to this run was wrong and is corrected here (2026-07-28). That took a real bug fix: strictly-positive wide-range tracers were previously z-scored *linearly*, which collapsed chlorophyll to 0.36 of its range and pushed 30.4% of predictions below zero, so **every global emulator figure produced before 2026-07-25 is contaminated and should not be shown**. The fix bought physical validity and dynamic range but **no skill**: the useful horizon is still **one step**, and against a per-cell seasonal AR(1) baseline the model scores −0.161 ± 0.015 with the confidence interval entirely below zero. Two earlier headlines are **retracted**: the "~9-month horizon" (a `delta_t` calendar artifact) and "beats persistence." A full spatial UDE at real scale stays gated on direction, not compute (see [emulator coupling plan](emulator_coupling_plan.md)).

## What works · what's blocked

This study is **complete (paper #1)**. It is a **surrogate-to-model identifiability study** — *which* of the six Carroll parameters are identifiable from real ocean observations, framed honestly as a consistency check against Carroll's own values (not a cross-validated discovery against the GCM). The honest target is **four observable params** {`alpfe`, `scav_rat`, `diatomgraz`, `R_PICPOC`}; the growth pair {`Smallgrow`, `Biggrow`} is **unobservable by construction** (no real data constrains growth rates).

=== "Identifiable (real data)"

    - **`alpfe` recovers 49/50** and **`R_PICPOC` 50/50** under the honest per-AOI ≥2-of-3 metric (the n=50 flagship `n50e2k_percell_trio`, 2000 epochs, `verify_run` exit 0) — against real GEOTRACES IDP2025 dissolved iron and a real calcite anchor (Daniels CP:PP / MODIS PIC). An epoch-matched anchor-off control (`n50e2k_anchor_off`) collapses `R_PICPOC` to **6/50**, so the real anchor demonstrably drives it.
    - The trio **{`alpfe`, `scav_rat`, `R_PICPOC`} holds jointly 25/50** versus **0/50** for a global-scalar control — a 3-of-4-observable frontier, and the result that makes the per-cell network load-bearing. `scav_rat` is the binding leg (**25/50** at 2000 epochs → **41/50** at 4000, so most of that gap is optimization rather than missing information; the equatorial Pacific stays at 6/50). An earlier **38/40 (95%)** iron-pair headline predates this reconciliation and reads more optimistically than the honest metric.

=== "Open / not identifiable"

    - **No 6/6 wall.** `R_PICPOC` is recoverable; the differentiable Darwin calcite port + native resolution were **tested and did not help** — the real gap was a direct calcite *observation*, now supplied.
    - **`diatomgraz`** is recoverable from a **model-internal** observable, but not from independent real data. With the DINN on SST only it sits at chance (best 4/10); adding **MLD** as a per-cell input channel recovers it **10/10**, and with the biogenic-silica diagnostic off it still reaches **35/50 per-AOI** through chlorophyll + MLD — so the recovery is not a bSi tautology. The caveat that keeps it out of the recovered set: the Chl target is Darwin's own, so this is model-internal consistency, not independent validation. **The growth pair is unobservable by construction.**
    - The surrogate gap is **dimensional**: the 0-D box homogenizes spatial structure (tracer CV → ~1e-15), so identifiability rests on real *absolute* anchors. 1° proxy; 23-yr climatology; single-GPU. Full evidence → **[Project Status](status.md)**.

## Documentation map

<div class="grid cards" markdown>

-   :material-chart-line: **[Project Status](status.md)**

    ---

    The canonical current-best snapshot — headline numbers, the identifiability frame (4 observable params; growth pair unobservable), and known limitations.

-   :material-table: **[Config / Results Matrix](results_matrix.md)**

    ---

    The single source of truth — what every config (v2.x box → 3-AOI `geo1` → native LLC270 → Track-2 feasibility probes (self-twin, synthetic)) tested, found, and how each differs.

-   :material-sitemap: **[DINN design](dinn_design.md)**

    ---

    Network architecture, the differentiable box model, the training loop, and the structural argument behind per-cell parameter recovery.

-   :material-water: **[ECCO-Darwin relationship](ecco_darwin_relationship.md)**

    ---

    How the box model maps onto full ECCO-Darwin, and the [parameter inventory](ecco_darwin_parameter_inventory.md) of what is and isn't being recovered.

-   :material-flask: **[Archive](archive/index.md)**

    ---

    Per-version research provenance, v2.1 → v3.2 (out of the onboarding path) — the verified experimental record behind each matrix row, including the `R_PICPOC` real-calcite-anchor campaign.

-   :material-server: **[Cluster setup](cluster_setup.md)**

    ---

    Northeastern Explorer + AICR setup, partitions, storage, and SLURM templates. See also the [cluster roadmap](cluster_roadmap.md).

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
and the full reproduce path is in the [README](https://github.com/2imi9/ECCO-DarwinDiff#quick-start).

## Background reading

ECCO-Darwin (Carroll et al. [2020](https://doi.org/10.1029/2019MS001888), *JAMES*; [2022](https://doi.org/10.1029/2021GB007162), *GBC*) is calibrated via **Green's functions** ([Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1)), which scale badly: each tuned parameter needs a fresh full forward run, so the published calibration handles only **6 parameters**. DarwinDiff replaces the biogeochemistry side with PyTorch autograd — gradients for all parameters in one backward pass, with values varying across space. The closest method template is the per-location parameter network of [Xu et al. 2025 (BINN)](https://arxiv.org/abs/2502.00672); the full annotated reference list is in the [README](https://github.com/2imi9/ECCO-DarwinDiff#citation).

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
