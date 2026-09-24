# ECCO-DarwinDiff

Experiments on which biogeochemistry parameters of
[ECCO-Darwin](https://github.com/darwinproject/darwin3) real ocean observations can actually
identify. Carroll et al. ([2020](https://doi.org/10.1029/2019MS001888),
[2022](https://doi.org/10.1029/2021GB007162)) tune six of them with Green's functions, one full
forward run per parameter. Here the biogeochemistry is reimplemented as a differentiable box model
in PyTorch, a small per-cell network predicts all six in every grid cell, and the fit is graded
against Carroll's published values. Everything uses public artifacts: the
[ECCO-Darwin v05 output](https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/),
[GEOTRACES IDP2025](https://www.geotraces.org/idp2025/) dissolved iron and biogenic silica, and the
[Daniels 2018](https://doi.pangaea.de/10.1594/PANGAEA.888182) calcite production ratios.

## Result

Each fit gives every parameter a value per grid cell. Three terms:

- **Recovered** - within ±40% of Carroll's value in at least 2 of the 3 regions (equatorial
  Pacific, subpolar North Atlantic, Southern Ocean Pacific sector), graded per region, never
  cell-weighted. Cell-weighting lets the regions land on opposite sides of Carroll's value and
  overstates recovery.
- **Collapse** - how the per-cell values become one value per region: arithmetic mean,
  geometric mean, or median. It matters only for `scav_rat`, which spans two decades, so the
  arithmetic mean inflates it by `exp(σ²/2)`.
- **Control** - every count must beat a matched control: the same pipeline with the network left
  untrained, or the same fit with its identifying observation withheld.

<details open>
<summary><b>Headline comparison: flagship fit, 50 seeds, 2000 epochs</b> (click to shrink)</summary>

| Parameter | Recovered, arithmetic · geometric | Matched control | Where it holds |
|---|---|---|---|
| `R_PICPOC` | **50/50** · 50/50 | 6/50 with the calcite anchor withheld (epoch-matched) | globally, conditional on the Daniels 2018 anchor and the box's bulk calcite closure |
| `alpfe` | **49/50** · 49/50 | untrained 0/100 at ≤30% (trained 98/100) | every region, but as a direction only |
| `scav_rat` | **25/50** · 13/50 | single-region fit: untrained 0/50 | Southern Ocean only, at the published loss and 50-day window |
| `diatomgraz` | equatorial Pacific leg **40/100** at ≤10% | untrained 0/50 | equatorial Pacific only |
| trio {`alpfe`, `scav_rat`, `R_PICPOC`} | **25/50** · 12/50 | one global-scalar vector instead of the per-cell network: 0/50 | |
| `Smallgrow`, `Biggrow` | excluded | | no time-mean observable constrains them |

The flagship predates the collapse instrumentation, so its geometric counts are measured on a
bitwise-identical reproduction. `alpfe` and `R_PICPOC` do not change with the collapse; `scav_rat`
does, and the whole difference sits in the North Atlantic leg (19 → 5).

</details>

Per-run values, controls and the full parameter table: [STATUS.md](STATUS.md) and the
[results matrix](docs/results_matrix.md).

## Findings

- **The per-cell network is load-bearing.** The trio holds jointly in 25/50 seeds (12/50
  geometric) against 0/50 for a single global-scalar vector fit the same way
  ([STATUS](STATUS.md)).
- **`R_PICPOC` recovers, but only against one calcite compilation.** 50/50 with the Daniels 2018
  anchor, 6/50 without it. Swapping in its successor, Marsh 2025, gives 30/50 (P = 1.8e-07), and
  98/100 → 50/100 out of sample (P = 2.7e-16). Under Daniels the Southern Ocean has zero calcite
  cells, so that leg was inherited through the shared network rather than measured; given 12 real
  observations it moves to 1.57× Carroll and reads 0/50
  ([08-13](docs/findings/2026-08-13_the_flagship_rpicpoc_5050_is_daniels_specific.md),
  [08-14](docs/findings/2026-08-14_the_anchor_conditionality_of_rpicpoc_replicates.md)). It
  also needs the box's bulk calcite closure: making calcite come from calcifiers only, as in
  ECCO-Darwin, takes it from 10/10 to 0/10 at about 24× Carroll
  ([07-29](docs/findings/2026-07-29_coccolith_only_screen.md)).
- **`alpfe` gives a direction, not a value.** Its bounds are (0.05, 1.0) against Carroll's
  0.92831, and the fit rails to whatever ceiling it is given: 99.7% of a 1.0 bound, 99.6% of a
  1.6 bound. Widening the bound moves the untrained control into the pass band, where it scores
  50/50 against the trained 0/50 (job 276927,
  [08-05](docs/findings/2026-08-05_alpfe_rails_to_whatever_bound_it_is_given.md)). The signal
  itself is real, 98/100 against an untrained 0/100 at ≤30% (job 258439,
  [08-03](docs/findings/2026-08-03_the_pass_band_is_load_bearing.md)).
- **`scav_rat` is identifiable in the Southern Ocean and nowhere else, and the average hides
  it.** A Southern Ocean fit recovers it 30/50 against an untrained 0/50 (P = 3.15e-24, taken
  conservatively against a rule-of-three floor of 3/50), 49/50
  geometric, and fresh seeds reproduce 30/50 against an untrained 0/50 (job 352450,
  [08-12](docs/findings/2026-08-12_the_southern_ocean_scavrat_result_replicates.md)). Correcting
  the arithmetic collapse to the geometric one halves the trio, 25 → 12
  ([08-04](docs/findings/2026-08-04_pooler_audit_the_flagship_trio_halves.md)). The verdict
  depends on two analysis choices. A time-mean loss moves the identifiable basin to the
  equatorial Pacific (job 288619,
  [08-06](docs/findings/2026-08-06_the_loss_formulation_selects_which_basin_is_identifiable.md)),
  and the Southern Ocean value drifts steadily with the integration window: 2.78× Carroll at 100
  steps, 0.88× at the published 200, 0.49× at 400 (job 270032,
  [08-05](docs/findings/2026-08-05_the_integration_window_is_a_contested_resource.md)). It
  describes the day-50 transient of subsurface iron, not a steady state.
- **`diatomgraz` is the mirror image: identifiable in the equatorial Pacific, anti-recovered
  elsewhere.** Its equatorial leg is 40/100 at ≤10% against an untrained 0/50 (P = 5.5e-09);
  in the other two basins training pushes it below its own control. The usual ±40% band cannot
  see either, because the prior midpoint already sits inside it
  ([08-03](docs/findings/2026-08-03_the_pass_band_is_load_bearing.md)).
- **More optimisation hurts the one basin that works.** 4000 epochs buys a North Atlantic gain
  that depends on the collapse, and costs a Southern Ocean accuracy loss of 1.4-1.75× that does
  not (P = 1.6e-09 geometric, job 258713). The flagship stays at 2000 epochs
  ([08-04](docs/findings/2026-08-04_more_optimisation_damages_the_one_basin_that_works.md)).
- **The North Atlantic scatter lives inside one ocean province.** Longhurst provinces explain
  less of it than arbitrary latitude bands (η² 0.338 vs 0.357), and it sits inside NADR
  (within-province log-sd 1.085 against 0.196-0.279 in the polar provinces), so a province-based
  region would make it worse (job 408789,
  [08-20](docs/findings/2026-08-20_the_dispersion_lives_inside_one_province.md)).
- **It does not generalise in space.** With 20% of the GEOTRACES iron cells held out, all 30
  held-out R² values are negative; the best is −0.30
  ([artifact](docs/findings/2026-07-29_heldout_geotraces_n10e2k.json)). This is a consistency
  check against Carroll's values, not a cross-validated discovery.
- **The growth pair is excluded, for two different reasons.** `Biggrow` is unobservable by
  construction (never recovers, seasonal included). `Smallgrow` is not identifiable from the
  time-mean observables fitted here; a seasonal prototype recovers it 9/10 in the North Atlantic,
  unconfirmed.
- **The forward emulator is a clean negative.** Trained in log space it emits no negative
  concentrations, but mass is not conserved (Chl1 drifts +130% over six rollout steps), the
  useful horizon is one step, and against a per-cell seasonal AR(1) baseline it scores
  −0.161 ± 0.015. The earlier "~9-month horizon" and "beats persistence" headlines are retracted
  ([07-23](docs/findings/2026-07-23_emulator_baselines_v2.md)).
- **Caveat:** the surrogate is a 0-D two-layer box fitted to ECCO-Darwin output plus a few real
  anchors, so distance to Carroll measures consistency with the model's own calibration, and part
  of it is proxy bias. Whether the `scav_rat` / `diatomgraz` split is structural or practical is
  open (`ded77`).

Retracted readings, and every number behind the findings, are in the
[research map](docs/research_map.md): about 600 claims and 300 retractions, queryable as SQL.

Docs: [start here](docs/ONBOARDING.md) · [status](STATUS.md) ·
[results matrix](docs/results_matrix.md) · [research map](docs/research_map.md) ·
[findings](docs/findings/) · [DINN design](docs/dinn_design.md) ·
[ECCO-Darwin relationship](docs/ecco_darwin_relationship.md) ·
[site](https://ecco-darwindiff.readthedocs.io/en/latest/) · [changelog](CHANGELOG.md)

## Method

This is an identifiability study: fit the parameters by gradient descent through a
differentiable surrogate, then ask which ones the observations fix. The surrogate is
`carroll6_5pft_2layer` (15 tracers, two layers, five plankton types); a per-cell network reading
sea-surface temperature predicts all six parameters in every grid cell; the loss combines
ECCO-Darwin v05 targets with the real anchors above. Every count is graded per region against a
matched control and must pass `scripts/verify_run.py` (exit 0), and `scav_rat` must also pass
`scripts/analysis/pooler_audit.py`. The closest method template is the per-location parameter
network of [BINN](https://arxiv.org/abs/2502.00672).

![DINN architecture: sea-surface temperature feeds two 16-wide 1x1-convolution layers with Tanh to six Carroll parameters, which pass through the differentiable box model to the loss; gradients flow back through the box model to the network](docs/dinn_architecture.svg)

## Reproduce

```
uv sync
uv run pytest -q
```

[`notebooks/demo_colab.ipynb`](notebooks/demo_colab.ipynb) runs a synthetic recovery on CPU in a
few minutes and needs nothing else
([Colab](https://colab.research.google.com/github/2imi9/ECCO-DarwinDiff/blob/main/notebooks/demo_colab.ipynb));
it uses the 5-tracer teaching box. The flagship is
`source scripts/configs/flagship_geo1.sh; uv run python scripts/run_v3.0_joint_multi_aoi.py`, which
needs `DARWIN_DATA_ROOT` pointing at the LLC270 tree plus the GEOTRACES and Daniels files
([data](data/README.md), [cluster setup](docs/cluster_setup.md)). Then
`uv run python scripts/verify_run.py RUN_DIR` must exit 0 before any number is quoted.

Status: research code under active development. Results are updated in place as later findings
supersede earlier ones; the retraction chain is in the research map. MIT licensed. If you use
this, cite the repository and Carroll et al. [2020](https://doi.org/10.1029/2019MS001888) and
[2022](https://doi.org/10.1029/2021GB007162).
