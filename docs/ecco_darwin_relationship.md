# Where DarwinDiff slots into ECCO-Darwin

For readers who want to understand exactly which piece of ECCO-Darwin DarwinDiff operates on — and which pieces it deliberately doesn't.

Companion to [`README.md`](../README.md) (project overview), [`docs/dinn_design.md`](dinn_design.md) (NN architecture), and [`STATUS.md`](../STATUS.md) (live sweep results).

---

## ECCO-Darwin in two pieces

ECCO-Darwin = physics + biogeochemistry, coupled at runtime.

**Physics — MITgcm.** The ECCO state estimate provides temperature, salinity, currents, and mixed-layer depth at every grid cell and timestep. MITgcm handles advection, diffusion, mixing — the transport of every tracer through the ocean. This piece is data-assimilative and fixed; DarwinDiff inherits it as-is and does not touch it.

**Biogeochemistry — Darwin module.** A per-cell rate-equation kernel: at each timestep, given the physical state and current tracer concentrations, compute the time derivative of every BGC tracer (`dC/dt`) due to biology + chemistry — *not* transport. Verified per [`docs/ecco_darwin_parameter_inventory.md`](ecco_darwin_parameter_inventory.md), the Carroll 2020 (Darwin 1, v04) build has **39 prognostic tracers** — built from 5 phytoplankton functional types, 2 zooplankton functional types, and the dissolved + particulate nutrient / carbon-chemistry pools — driven by **103 independent tunable scalar parameters** in source code. Carroll 2022 (Darwin 3, v05) is a major architectural rework: `nplank = 10` plankton types, parameters exposed via namelist files in `input_darwin/`, kinetic source moved upstream to `MITgcm/pkg/darwin/`. MITgcm then transports the updated tracer fields between cells.

## What DarwinDiff touches

The biogeochemistry side only. Within biogeochemistry, only the **source-minus-sink (SMS) kernel** — the per-cell rate equations that compute `dC/dt` from biology + chemistry.

**In ECCO-Darwin source.** The SMS kernel is implemented as Fortran subroutines in the Darwin package.

- **Carroll 2020 / Darwin 1 / v04** — the dynamics integrator is `darwin_plankton.F` (1711 lines), with parameter initialization in `darwin_init_fixed.F` (390 lines) and per-phyto trait derivation in `darwin_generate_phyto.F` (782 lines). All verified line-by-line in [`docs/ecco_darwin_parameter_inventory.md`](ecco_darwin_parameter_inventory.md).
- **Carroll 2022 / Darwin 3 / v05** — the package is refactored: `code_darwin/` in `v05/llc270` and `v06/llc270` contains only headers (`DARWIN_OPTIONS.h`, `DARWIN_SIZE.h`); the kinetic source moves upstream into `MITgcm/pkg/darwin/`. **The dynamics-integrator filename is preserved** — `darwin_plankton.F` remains the SMS kernel in Darwin 3 (verified 2026-05-21 against [`darwinproject/darwin3` on branch `darwin`](https://github.com/darwinproject/darwin3/blob/darwin/pkg/darwin/darwin_plankton.F): `SUBROUTINE DARWIN_PLANKTON` computes the `gTr` tendencies for all BGC tracers from photosynthesis, respiration, nutrient uptake, grazing, mortality, and remineralization, given `PAR` and the temperature-functional dependencies). Sibling routines (`darwin_forcing.F`, `darwin_fe_chem.F`, `darwin_carbon_chem.F`, `darwin_nut_supply.F`, etc.) handle wrapping, iron chemistry, carbonate equilibria, and external forcing respectively. **No `gud` package exists in darwin3** — that reference in earlier drafts was wrong; `pkg/darwin/` contains all 54 Fortran source files for the Darwin biogeochemistry.

**In DarwinDiff.** A differentiable PyTorch reimplementation, simplified to the subset Carroll 2020/2022 calibrated. Equations and modules per `src/darwindiff/carroll6.py:1-44`:

| Module | Prognostic tracers | Use |
|---|---|---|
| `carroll6_step` / `carroll6_integrate` | **5**: DFe, P_s (small phyto), P_l (large phyto), POC, PIC | Baseline. Used in notebooks 05–19. |
| `carroll6_carbonate_step` / `carroll6_carbonate_integrate` | **7**: above + DIC + ALK | Carbonate extension. Used in notebooks 20+. Each step also computes the air-sea CO₂ flux `F_CO2` as a *diagnostic* (not a prognostic tracer) from `(DIC, ALK, T, S)` via the Follows-2006 carbonate solver (`darwindiff.carbonate.solve_carbonate`) and the Wanninkhof-2014 gas-transfer law (`darwindiff.carbonate.co2_flux`). |

The reimplementation captures the same rate-equation structure as Darwin's SMS kernel but over a small subset of the full tracer set: 5 of Darwin 1's 39 prognostic tracers in the baseline, 7 in the carbonate extension. The 5-PFT → 2-PFT collapse (small + large) is documented in `docs/dinn_design.md` as the **dominant recovery-bias source** vs Carroll's published parameter values. Background defaults for the parameters Carroll left untuned (`M_LIN`, `M_QUAD`, `G0_GRAZE`, `W_SINK`, `K_FE`, `PHI_DUST`, `Q_FE`, `LIGHT`, `H_MLD` — listed in `carroll6.py:37-39`) are held fixed at the same literature-plausible values Carroll used. **Coverage**: Carroll's Green's-functions calibration tuned 6 of 103 independent scalars — 5.8 %. We tune the same 6 — same scope, different method.

## What DarwinDiff doesn't touch

| Component | Where it lives | How DarwinDiff handles it |
|---|---|---|
| Currents, mixing, advection | MITgcm / ECCO state estimate | Inherited from v05; not learned, not perturbed |
| Dust deposition, river inputs, sediment fluxes | Darwin forcing files | Baked into v05 target fields; inherited as-is |
| The ~94% of Darwin parameters Carroll left at defaults | Darwin namelists | Held fixed at literature values |
| Tracers outside the Carroll-6 subspace (zooplankton, additional PFTs, DOM/POM pools) | Full Darwin tracer set | Not represented in the box model |

The structural commitment: anything Carroll didn't try to tune via Green's functions, DarwinDiff doesn't try to tune either. The scientific claim is about whether you can recover what Carroll recovered — using gradients and per-cell parameter variation in place of Green's functions and global scalars.

## The learnable surface — Carroll-6

Six biogeochemical parameters, per `src/darwindiff/carroll6.py:8-13`. These are exactly the six Carroll et al. 2020 (JAMES) tuned via Green's functions against the Darwin 1 / v04 LLC270 build (`MITgcm-contrib/ecco_darwin/v04/llc270_JAMES_paper`). **Carroll 2022 (GBC) inherits Carroll 2020's six calibrated values bit-for-bit** — verified in [`docs/ecco_darwin_parameter_inventory.md`](ecco_darwin_parameter_inventory.md) by reading `v04/llc270_JAMES_paper/code_darwin/{darwin_init_fixed.F, darwin_generate_phyto.F}` and `v05/llc270/input/data.darwin` side-by-side — so the same 6 numbers are the calibration target for both the Darwin 1 and Darwin 3 / v05 setups.

| Name | Role | Units | Source line | Optimized value (Carroll 2020) |
|---|---|---|---|---|
| `alpfe` | Iron dust solubility | – | `init_fixed.F:83` | 0.92831 |
| `scav_rat` | Iron scavenging rate | s⁻¹ | `init_fixed.F:101` | 10.41124 × 0.005 / 86400 |
| `Smallgrow` | Small phytoplankton growth rate | d⁻¹ | `init_fixed.F:161` | 0.66098 |
| `Biggrow` | Large phytoplankton growth rate | d⁻¹ | `init_fixed.F:162` | 0.43148 |
| `diatomgraz` | Diatom palatability (grazing modifier) | – | `init_fixed.F:272` | 0.83003 |
| `R_PICPOC` | PIC/POC production ratio | – | `generate_phyto.F:484` | 0.04245 |

In Carroll's approach: one global scalar per parameter, six values applied uniformly worldwide. In DarwinDiff: six values *per cell*, predicted by a small neural network from local environmental covariates. Two production NN variants per [`docs/dinn_design.md`](dinn_design.md):

| Variant | Inputs | Weights | Use |
|---|---|---|---|
| `DINN` (baseline) | **SST only** (1 channel) | ~454 | Structural-argument fits where the cleanest comparison to global-scalar matters more than absolute fit quality. Notebooks 09–14. |
| `DINNDeep` (production) | **SST + MLD + windspeed + latitude** (4 channels) | ~9.4K | Within-AOI fits where maximum r matters. Notebook 15. Doesn't extrapolate across spatial blocks. |

Sigmoid bounding (`src/darwindiff/carroll6.py::bounded_params`, parameter ranges in `PARAM_BOUNDS`) maps the NN outputs into Carroll's published physical ranges: `param_i = lo_i + (hi_i − lo_i) · sigmoid(raw_i)`. This guarantees biologically sensible parameter values regardless of NN output magnitude.

## Training-time data flow

```
ECCO v05 target fields ──────────────────────────────┐    (fixed; we don't learn these)
                                                     │
                                                     ▼
Per-cell env covariates ─▶ DINN ─▶ 6 raw values ─▶ sigmoid bounds ─▶ Carroll-6 per cell
(SST, MLD, wind, lat)                                                       │
                                                                            ▼
                                                  carroll6_step / carbonate_step
                                                  (differentiable PyTorch SMS kernel)
                                                                            │
                                                                            ▼
                                                       predicted tracer fields
                                                                            │
                                                       v05 target ── compare ── obs-loss
                                                                            │
                                                                            ▼
                                                  backprop through SMS → DINN weights
```

*Diagram shown for `DINNDeep` (4-channel input). `DINN` baseline uses SST only — same data-flow shape, narrower input. Variants such as `PER_AOI_DINN` (one network per area-of-interest, used in v3.x multi-AOI joint training) and `DINNRegional` (region-level fully-connected MLP) follow the same pattern with different input/output handling.*

The differentiable SMS kernel is the load-bearing piece. Without it, gradients can't flow from the observation loss back to the NN, and the whole approach reduces to either pure-NN emulation (Neural-BGC, Ouala & Lachkar 2026 — no parameter recovery) or back to Carroll's Green's functions (no per-cell variation).

## Method lineage

| Layer | Reference | Role |
|---|---|---|
| Physics-informed NNs (general) | Raissi et al. 2019 | Methodological grandparent. Embed governing equations as soft constraints in NN training. |
| BINN — Biogeochemistry-Informed NN | Xu et al. 2025, arXiv:2502.00672 | Direct ancestor. Small MLP → sigmoid-bounded physical parameters → differentiable CLM5 forward → end-to-end backprop. DarwinDiff adapts the pattern from soil carbon to marine BGC. |
| ECCO-Darwin calibration baseline | Carroll et al. 2020 (JAMES), Carroll et al. 2022 (GBC) | The target. Green's-functions calibration of 6 parameters that DarwinDiff replaces. |
| Concurrent ocean-BGC ML work | Ouala & Lachkar 2026 (Neural-BGC, ESSOAr); Meunier+Ouala 2025 (differentiable Veros) | Methodological neighbours. Pure-NN emulation (no parameter recovery) or differentiable physics-only (no BGC). |

## Where to read more

- [`docs/dinn_design.md`](dinn_design.md) — the per-cell NN architecture (DINN, DINNDeep), training loop, structural-ceiling argument.
- [`docs/ecco_darwin_parameter_inventory.md`](ecco_darwin_parameter_inventory.md) — the broader Darwin parameter landscape; where Carroll-6 sit in the larger tunable surface.
- [`STATUS.md`](../STATUS.md) — current sweep results: which Carroll-6 subsets recover, which don't, and why.
- [`docs/findings/v3.1_closeout.md`](findings/v3.1_closeout.md) — paper-prep technical writeup of the 5/6-ceiling proof-of-concept.
- [Carroll et al. 2022 (GBC)](https://doi.org/10.1029/2021GB007162) — *Attribution of space-time variability in global-ocean dissolved inorganic carbon.* The v05 calibration baseline DarwinDiff targets.
- [Carroll et al. 2020 (JAMES)](https://doi.org/10.1029/2019MS001888) — *The ECCO-Darwin Data-Assimilative Global Ocean Biogeochemistry Model: Estimates of Seasonal to Multidecadal Surface Ocean pCO₂ and Air-Sea CO₂ Flux.* The original ECCO-Darwin paper; v04 / Darwin 1; source of the six calibrated values inherited bit-for-bit by Carroll 2022 (DOI verified 2026-05-21 against AGU/Wiley).
- [Xu et al. 2025 (BINN preprint)](https://arxiv.org/abs/2502.00672) — the soil-carbon precursor whose architecture DINN adapts.
