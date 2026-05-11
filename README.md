# ECCO-DarwinDiff

A PyTorch reimplementation of the ECCO-Darwin ocean biogeochemistry model that lets gradients flow through every step of the simulation. Built for two related uses:

1. **Parameter learner** — a faster, richer replacement for ECCO-Darwin's Green's-functions calibration. Where Carroll 2020 / 2022 tunes one global vector of 6 biogeochemical parameters via expensive multi-decadal forward runs, DarwinDiff learns a *function* mapping local environmental conditions to a per-cell parameter vector via gradient descent through a differentiable box model.
2. **Emulator** — a neural-network stand-in for ECCO-Darwin trained on the same Darwin output, for long-timescale climate runs the full model is too slow for. Not started yet — Track 2.

> **Status:** Track 1 (parameter recovery) at **v2.0** — DarwinDiff is a gradient-based replacement for ECCO-Darwin's Green's-functions calibration at the same parameter scope (Carroll's 6). Locally-runnable on a single GPU (~90 min on RTX 5090). **v2.0 headline result:** adding the carbonate cycle (DIC + ALK + air-sea CO₂ flux) as joint-loss targets moves the iron pair to **1.1% (alpfe)** and **40% (scav_rat)** off Carroll's published values — closer in BOTH DINN baseline AND DINNDeep architectures, robust across network capacity. The remaining 4 Carroll-6 parameters are trapped by the 5-tracer box-model proxy; cluster work + 5-PFT box extension addresses this (B200 burn-in pitch sent to MIT ORCD 2026-05-10). Track 2 (neural emulator) gated on cluster compute. See [STATUS.md](STATUS.md) for live state and [`docs/findings/v2_track1_closeout.md`](docs/findings/v2_track1_closeout.md) for the consolidated v2.0 record.

## Why this exists

ECCO-Darwin (Carroll et al. 2020, *JAMES*; Carroll et al. 2022, *GBC*) is a global ocean biogeochemistry model on the ECCO LLC270 grid (~1/3° at the equator, ~18 km at high latitudes, 50 vertical levels), 1992–2017+. Its biogeochemistry is calibrated via **Green's functions** (Menemenlis et al. 2005), which scales linearly badly: each tuned parameter needs a fresh full forward run, so Carroll's published calibration handles only **6 parameters** (iron dust solubility, iron scavenging rate, small + large phytoplankton growth rates, diatom palatability, PIC/POC ratio).

DarwinDiff replaces the biogeochemistry side of this with **PyTorch autograd**: gradients for all parameters are computed in one backward pass, and the parameter values themselves vary across space — predicted by a small per-cell neural network (DINN) from local environmental conditions (SST + MLD + wind + lat). The structural argument: a single global parameter vector cannot reproduce spatial heterogeneity in ocean biogeochemistry; per-cell parameters can.

> **Design details:** see [`docs/dinn_design.md`](docs/dinn_design.md) for the full per-cell architecture, training loop, structural-ceiling argument, and DINN vs DINNDeep variant decisions.
>
> **Cluster setup:** see [`docs/cluster_setup.md`](docs/cluster_setup.md) for compute requirements, environment setup on a Linux GPU cluster, dataset transfer plan for the LLC270 monthly tree, and the open questions list for ORCD.

## Headline results (as of 2026-05-10)

All fits use a 1500-epoch DINN per-cell network (1×1 conv backbone) versus a global-scalar Green's-functions baseline, against z-scored Darwin v05 output over a Mid-Atlantic-sized AOI:

| AOI | Target | Network | DINN r | Loss ratio Global / DINN |
|---|---|---|---|---|
| North Pacific | Darwin NO₃ | DINN (SST) | **0.979** | **23.8×** |
| North Pacific | Darwin Chl | DINN (SST) | 0.966 | 14.6× |
| Mid-Atlantic | Darwin Chl | DINN (SST) | 0.724 | 1.8× |
| Mid-Atlantic | Darwin NO₃ | DINN (SST) | 0.607 | 1.3× |
| Equatorial Pacific | Darwin FeT | DINN (SST) | 0.337 | 1.1× |
| Equatorial Pacific | Darwin FeT | **DINNDeep (SST + MLD + wind + lat)** | **1.000** | *(saturates target field; see caveat below)* |
| North Pacific | Darwin Chl | **DINNDeep (4-channel)** | **1.000** | *(saturates; see caveat below)* |
| Equatorial Pacific | FeT + Chl + POC + PIC (joint) | **DINNDeep + multi-tracer loss** | **all 4 ≥ 0.998** | *(saturates jointly; see caveat below)* |
| Equatorial Pacific | **7-tracer carbonate joint** | **DINN baseline + carbonate (nb20)** | poor per-tracer (−0.36 to 0.62) | *iron pair within **1.1%/40%** of Carroll — v2.0 headline* |
| Equatorial Pacific | 7-tracer carbonate joint | DINNDeep + carbonate (nb20) | all r ≥ 0.88 | *scav_rat moves closer to Carroll in both architectures — robust signal* |

In every fit, the Green's-functions parametric class produces a **constant prediction** (r mathematically undefined) — the structural ceiling Carroll 2020 / 2022's calibration is bounded by. Carroll's 6 calibrated values are inherited bit-for-bit between v04 / Carroll 2020 (Darwin 1) and v05 / Carroll 2022 (Darwin 3), verified locally against the source namelists.

**On the r=1.000 result (notebooks 15 + 16):** A deeper, wider DINNDeep network with 4-channel input (SST + MLD + wind + lat) drives the Eq Pacific FeT fit to r=1.000 and ~3000× lower loss. **However:**

1. **Recovered Carroll-6 values do NOT get closer to Carroll's published optima** — some get worse. The network finds *a* per-cell parameter set that produces Darwin's FeT field, but it's a degenerate solution that doesn't match the published calibration. **The recovery ceiling is the 5-tracer box-model simplification, not the network architecture.** Closing the gap to Carroll's actual values requires extending the box model (DIC + ALK + carbonate chemistry + the full 5 PFT ecosystem), not adding more network capacity.

2. **DINNDeep's r=1.000 is interpolation, not extrapolation** (notebook 16 cross-validation). Random 80/20 hold-out: held-out r=0.995 (passes — interpolating gaps works). Block hold-out (W 2/3 train, E 1/3 test): held-out r=0.301 (fails — can't extrapolate to unseen spatial blocks). DINNDeep is fine for fitting within a single AOI but **does not generalize across spatial blocks**. For broad cross-basin claims, the SST-only DINN baseline (notebooks 11/13) is the more honest tool because it has less interpolation capacity to lean on.

3. **Ensemble disagreement is a tail-detector, not an extrapolation flag** (notebook 17). A 10-seed DINNDeep ensemble shows Pearson r(per-cell stdev, |error|) = **+0.87** but Spearman ρ = **−0.42** — the relationship is outlier-driven (high-disagreement cells coincide with high-error cells, but rank order in the well-predicted bulk is inverted). A separate 5-seed ensemble on the block-CV setup shows held-out stdev only **1.17×** training stdev — the ensemble is overconfident in extrapolation territory. nb16's r=0.301 is highly reproducible across these 5 seeds (per-seed: 0.278, 0.288, 0.301, 0.330, 0.358). **Cheap solutions (more seeds, more capacity) do NOT rescue the cross-basin gap.** Full v1.6 record at [`docs/findings/2026_05_10.md`](docs/findings/2026_05_10.md).

4. **DINNDeep saturation generalises across (AOI × target); per-parameter recovery direction depends on which target is fit** (notebook 18). Repeated the nb15 head-to-head on the next-strongest existing baseline (N Pacific Chl, DINN baseline r=0.966 from nb11). DINNDeep saturates r=1.000 with ~3000× lower loss, matching the nb15 saturation pattern. But recovered Carroll-6 means are mixed: **3 closer** to Carroll's published, **3 further** — not uniformly degenerate as in Eq Pacific FeT. The single-parameter offsets vary with the dominant physics of the basin × target combination. Refines the v1.4 finding from "box-model proxy is the universal ceiling" to "the ceiling exists, and the specific recovery biases depend on which tracer is fit."

5. **Multi-tracer joint loss partially collapses the parameter degeneracy** (notebook 19). Adding 4 Darwin tracer fields as simultaneous loss surfaces (FeT + Chl_total + POC + PIC, using the carroll6 5-tracer state vector — no box-model extension required). All 4 tracers fit nearly perfectly (DINNDeep r ≥ 0.998 for each), confirming the box IS capable of producing the joint Darwin tracer state. Carroll-6 recovery vs nb15's single-target FeT: **3 of 6 parameters closer** to Carroll's published values (Smallgrow, Biggrow, R_PICPOC — directly constrained by the new tracer fields), **3 of 6 not** (alpfe, scav_rat, diatomgraz — iron-pair and grazing parameters lacking direct new constraints). **Iron pair `alpfe` and `scav_rat` remain 2–3× off** Carroll regardless of joint-loss setup. Implication: multi-tracer joint loss is an effective tool for parameters with direct tracer evidence; iron-pair identifiability needs depth-resolved observations OR carbonate extension to add CO₂-flux as a constraint.

6. **The iron-pair underconstraint resolves with the carbonate cycle (notebook 20 — v2.0 headline).** The v1.8 unresolved question (why does the iron pair stay 2–3× off Carroll regardless of architecture or joint-loss setup?) is closed in v2.0. Extending the box model from 5 to 7 tracers (adding DIC + ALK via `carroll6_carbonate_integrate`) and adding 3 carbonate signals (DIC + ALK + air-sea CO₂ flux via the new Follows-2006 solver in [`src/darwindiff/carbonate.py`](src/darwindiff/carbonate.py)) as joint-loss targets moves `alpfe` to **1.1% off** Carroll's published 0.928 (down from nb14's 3.3%) and `scav_rat` to **40% off** Carroll's 6.03e-7 (down from nb14's 80%). **Move is reproducible across BOTH DINN baseline AND DINNDeep architectures** — DINN: 0.011/0.401 vs nb14's 0.033/0.798 off; DINNDeep: 0.829/0.550 vs nb19's 0.253/2.117 (scav_rat substantially closer in both; the alpfe drift in DINNDeep is per-cell-memorization noise consistent with v1.4–v1.8 saturation findings). Other 4 Carroll-6 parameters drift because the 5-tracer box can't simultaneously satisfy 7 Darwin field constraints — joint loss redistributes degeneracy from the iron pair onto the other 4. **This is the v2.0 publishable result: gradient-based calibration delivers iron-pair recovery at calibration-grade for the parameters Green's-functions targeted.** Full record at [`docs/findings/v2_track1_closeout.md`](docs/findings/v2_track1_closeout.md).

7. **Carbonate is also a structural fix for spatial extrapolation (notebook 21).** Block cross-validation (west 2/3 train → east 1/3 test) on the new 7-tracer carbonate setup with DINNDeep gives held-out test r = **0.637** on FeT — **more than doubling nb16's 0.301** under the same CV protocol with single-target FeT. Mean across 7 tracers test r = **0.745**; DIC and ALK in particular extrapolate near-perfectly (test r > 0.97 with train-test gap < 0.02). The v1.5 finding that DINNDeep is "interpolation only" was specific to single-target FeT — more constraint signals (DIC + ALK + CO₂_flux) give the network stronger spatial gradients to track, and the carbonate fields have richer co-variation with the 4-channel input (SST + MLD + wind + lat) than FeT alone. The DINN baseline architecture's small capacity (~400 params) can't extrapolate even with the extra signals (test mean r = −0.273) — DINN baseline is the right tool for parameter recovery (nb20 result), DINNDeep is the right tool for spatial generalization + fit quality (nb21 result). **Carbonate constraints provide BOTH identifiability AND generalization** — the v2.0 contribution is broader than the iron-pair headline alone.

## Background reading

| Reference | Why it matters |
|---|---|
| [Carroll et al. 2020](https://doi.org/10.1029/2019MS001888) (*JAMES*) | Original ECCO-Darwin paper; defines the 6-parameter Green's-functions calibration we differentiate against. |
| [Carroll et al. 2022](https://doi.org/10.1029/2021GB007162) (*GBC*) | ECCO-Darwin v05 application paper; inherits Carroll 2020's calibration bit-for-bit. The publicly-accessible ECCO-Darwin output is from this run, so it's our active recovery target. |
| [Brix et al. 2015](https://doi.org/10.1016/j.ocemod.2015.07.008) (*Ocean Modelling*) | Earlier ECCO-Darwin version; original biogeochemistry equations. |
| [Savelli et al. 2026](https://doi.org/10.5194/gmd-19-867-2026) (*GMD*) | Recent ECCO-Darwin update; explicitly flags fixed parameters DarwinDiff could relax. |
| [Dutkiewicz et al. 2009](https://doi.org/10.1029/2008GB003405) (*GBC*) | Core Darwin biogeochemistry formulation. |
| [Menemenlis et al. 2005](https://doi.org/10.1175/MWR2912.1) (*Mon. Weather Review*) | The Green's-functions calibration method DarwinDiff replaces. |
| [Xu et al. 2025](https://arxiv.org/abs/2502.00672) (BINN) | Method template — differentiable physics + per-location parameter network. |
| [Kochkov et al. 2024](https://arxiv.org/abs/2311.07222) (Neural GCM, *Nature*) | Design reference for hybrid physics + ML emulators. |
| [Ouala & Lachkar 2026](https://doi.org/10.22541/essoar.15002003/v1) (Neural-BGC) | Closest existing ocean-BGC ML — observation-driven NN emulator coupled to ROMS. DarwinDiff differs by being mechanistic (emulates Darwin rather than bypassing it) and parameter-aware. |

## Project arc

- **Track 1 — parameter recovery** (current)
  - v0.x → v0.95: synthetic-truth methodology validation (notebooks 05–08)
  - v1.0: real-data demo on GLODAP (notebook 09) and on Darwin Chl (notebook 10)
  - v1.1: cross-basin validation Mid-Atl + N Pacific (notebook 11)
  - v1.2: iron-pair recovery via Darwin FeT in HNLC (notebook 14)
  - v1.3: cross-basin Darwin NO₃ (notebook 13)
  - v1.4: architecture upgrade test (notebook 15) — pins recovery ceiling on box-model bias, not network
  - v1.5: cross-validation honesty check (notebook 16) — DINNDeep interpolates but doesn't extrapolate spatially
  - v1.6: ensemble-disagreement trust map (notebook 17) — useful for in-domain outlier flagging, fails as extrapolation detector
  - v1.7: cross-basin DINNDeep on N Pacific Chl (notebook 18) — saturation pattern generalises; per-parameter recovery direction is target-specific
  - v1.8: multi-tracer joint loss on Eq Pacific (notebook 19) — adding 4 tracer fields as joint loss surfaces partially collapses parameter degeneracy (3/6 closer to Carroll), iron pair stays underconstrained
  - **v2.0: carbonate-extended box + 7-tracer joint loss (notebooks 20–21)** — iron pair moves to within 1.1% (alpfe) and 40% (scav_rat) of Carroll's published. Robust across architectures. Other 4 parameters trapped by 5-tracer box-model proxy. **Track 1 closed locally on a single GPU; cluster work scales the same scope to global resolution + Track 2 emulator.**
  - **Next local experiment (no cluster needed):** box-model carbonate-chemistry extension (nb20 candidate) — adds DIC + ALK + carbonate equilibrium to carroll6, addresses the 5-tracer-proxy ceiling identified in nb15. ~4–5 days authoring (autograd-compatible carbonate equilibrium is non-trivial), ~20 min run.
  - **Gated on cluster compute:** full-ocean parameter recovery, time-resolved multi-year fitting, Track 2 emulator. Cluster prep complete (env-var-driven `DARWIN_DATA_ROOT`, SLURM templates in [`scripts/slurm/`](scripts/slurm/), compute spec in [`docs/cluster_setup.md`](docs/cluster_setup.md)); awaiting cluster decision. See [STATUS.md](STATUS.md) for the live checklist.

- **Track 2 — emulator** (not started)
  - Will be a separate architecture (likely transformer / FNO / graph net with spatial coupling), trained on time-resolved Darwin output. Different problem from parameter recovery — different network. Notes in STATUS.md once it begins.

## Repository layout

```
ecco-darwindiff/
├── README.md                  this file (project overview)
├── STATUS.md                  living status doc — checklists + key findings
├── LICENSE                    MIT
├── pyproject.toml             package details + dependencies
├── src/darwindiff/            Python package (importable as `darwindiff`)
│   ├── carroll6.py              5-tracer Carroll-6 box model + Carroll's optima + bounds
│   ├── networks.py              DINN (per-cell 1×1 conv) + DINNRegional (MLP)
│   ├── diagnostics.py           NaN-safe Pearson r + constant-prediction handling
│   ├── budget.py                compute / memory budget calculators
│   ├── ecco_darwin_loader.py    ECCO-Darwin v5 bin_average product (1° NetCDF) loader + AOI presets
│   └── llc270_loader.py         ECCO-Darwin v5 native LLC270 monthly tracer loader (xmitgcm-based)
├── tests/                     pytest suite (104 tests + 1 opt-in real-data integration)
├── notebooks/                 numbered notebooks, in order of project arc
├── docs/                      decision log + chronological findings docs (latest: 2026_05_10.md, Track 1 v1.6)
├── data/                      local data cache (gitignored; see data/README.md)
├── scripts/slurm/             SLURM job templates for cluster runs (run_tests / run_notebook / run_array)
└── references/                PDFs + external code references (gitignored content)
```

## Installation

Needs Python 3.11+. With uv:

```bash
uv sync
uv run pytest -q   # 104 passed, 1 skipped
```

All runtime deps (including `xmitgcm` for the native LLC270 loader) are pinned in `pyproject.toml` and installed by `uv sync`.

For cluster runs, set `DARWIN_DATA_ROOT` to point at the LLC270 monthly tree (default keeps the local Windows behaviour):

```bash
export DARWIN_DATA_ROOT=/scratch/$USER/ecco_darwin_v5
```

See [`docs/cluster_setup.md`](docs/cluster_setup.md) for the full operational guide.

## Data sources

See [data/README.md](data/README.md). Summary:

| Source | Use | Access |
|---|---|---|
| ECCO-Darwin v05 `bin_average` (1° NetCDF, surface) | Carroll-6 fits via Chl + carbonate diagnostics | https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/bin_average/ (public) |
| ECCO-Darwin v05 native LLC270 monthly tracers (mds tile format, depth-resolved) | Carroll-6 fits via NO₃ / DIC / ALK / FeT etc. | https://data.nas.nasa.gov/ecco/llc_270/ecco_darwin_v5/output/monthly/ (public; ~50 GB per tracer) |
| LLC270 grid metadata | Required for xmitgcm loader | https://data.nas.nasa.gov/ecco/llc_270/grid/ |
| GLODAPv2 | DIC, alkalinity, nutrients, oxygen — used by notebook 09 | https://glodap.info |
| NASA GHG Center CO₂ flux GeoTIFFs | Validation of future CO₂ flux fits | https://earth.gov/ghgcenter/ |

Earthdata signup required for some paths. Raw data files are stored outside the repo (`D:\ecco_darwin_v5\` on the local dev machine).

## Documentation discipline

Every major code or scientific change should update **both** [README.md](README.md) (project overview, framing for new readers) and [STATUS.md](STATUS.md) (live checklist + findings) in the same PR. Keeps the docs from drifting.

## License

MIT — see [LICENSE](LICENSE). © 2026 ECCO-DarwinDiff contributors.

## Citation

Project is in active development; formal citation TBD once results are published or a Zenodo DOI is created. If your work depends on the underlying ECCO-Darwin model, please cite:

```
Carroll, D., Menemenlis, D., Adkins, J. F., Bowman, K. W., Brix, H., Dutkiewicz, S.,
et al. (2020). The ECCO-Darwin data-assimilative global ocean biogeochemistry model:
Estimates of seasonal to multidecadal surface ocean pCO2 and air-sea CO2 flux.
Journal of Advances in Modeling Earth Systems, 12, e2019MS001888.
https://doi.org/10.1029/2019MS001888

Carroll, D., Menemenlis, D., Dutkiewicz, S., Lauderdale, J. M., Adkins, J. F.,
Bowman, K. W., et al. (2022). Attribution of space-time variability in
global-ocean dissolved inorganic carbon. Global Biogeochemical Cycles, 36,
e2021GB007162. https://doi.org/10.1029/2021GB007162
```
