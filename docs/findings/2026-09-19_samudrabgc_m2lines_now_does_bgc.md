# SamudraBGC: M2LINES now does ocean biogeochemistry. What it needs next, and what DarwinDiff can honestly add

**Date:** 2026-09-19 · **Cost:** literature, one public-repo read, one CPU script; no cluster ·
**Prompted by:** the published SamudrACE paper naming biogeochemistry as its next component.

> **This note PARTLY SUPERSEDES `docs/findings/2026-07-22_neuralbgc_m2lines_landscape.md`.** That
> note's M2LINES section ("84 publications, ZERO biogeochemistry", "third independent niche
> confirmation") was true of the group's publications page and is no longer true of the group.
> Its Neural-BGC sections are unaffected.

## 1. What changed, each row checked at its source on 2026-09-19

**SamudrACE is published and names BGC as the pathway.** Duncan et al. 2026, *Geophysical Research
Letters* 53(11), e2025GL119340, doi 10.1029/2025GL119340 (arXiv 2509.12490, v2 of 27 Feb 2026).
Its conclusions say the coupled framework gives a pathway to a complete Earth-system emulator by
adding land and biogeochemical components, and that, trained on a pre-industrial control, it is
not expected to generalise to forced CO2. Samudra 2 (arXiv 2606.02610, section 5) lists
biogeochemistry and sea ice as the variables to extend to, lists "hybrid physics-ML architectures
that embed conservation laws" as a direction, and reports negative R2 for temperature and salinity
below about 700 m.

**The BGC arm already exists. It is called SamudraBGC, and our 2026-07-22 scan missed it by 12 days.**

| | |
|---|---|
| authors | Keutgen De Greef, Resplandy, Champenois, Poupon, Li, Hassanzadeh, **Zanna** |
| preprint | ESS Open Archive, doi 10.22541/essoar.15006794; the repo calls it a GRL submission |
| code | `github.com/mkeutgen/SamudraBGC`, Apache-2.0, created 2026-07-10, last push 2026-09-14; Zenodo 10.5281/zenodo.21352483 |
| weights | Hugging Face `mkeutgen/SamudraBGC`, one checkpoint, 0.91 GB, not gated |
| public data | 60-day evaluation window, Zenodo 10.5281/zenodo.21341550, 23.3 GB, CC BY 4.0. The full 7 TB simulation is **not yet public** (placeholder DOI, Globus link to be added) |
| parent model | DG-MOM6-COBALTv2, an **idealised** North-Atlantic-like double gyre, 362 x 362 at about 9 km, daily, 1960-2019 (train 1960-2009, validate 2010-2014, test 2015-2019) |
| predicts | T, S, streamfunction, velocity potential, **DIC, O2, NO3, Chl** (20 vertical PCs each) plus SSH; forced by net heat flux and wind stress |
| does not carry | **alkalinity, iron, pCO2, air-sea CO2 flux.** Zero code-search hits for `alkalin` and `pco2`; the variable families in `constants.py` are dic, o2, no3, pp, chl, poc, temp, salt, uo, vo, psi, phi. Primary production and POC were tried and dropped |
| scored against | its parent model. R2 over the upper 500 m; 5-year free rollout; PDFs; spectra; ensemble spread |
| speed | about 6 minutes per model-year on one GPU against about 4 hours on 896 cores |
| funding | Schmidt Sciences **Ocean Biogeochemistry Virtual Institute, InMOS project** |

InMOS is *Integration of Models and Observations Across Scales* (leads DeVries and Keeling;
Resplandy and Zanna are collaborators). Hassanzadeh describes the project as ML for **data
assimilation** of the ocean biogeochemical cycle. The inherited `ocean_emulators` codebase also
carries `models/fomo.py`, whose docstring reads "A Foundation Model for the Oceans + Observations"
and adds that it is currently used only as a physical emulator. So the direction of travel is
**observations into the emulator**, not just more tracers.

Their ablation, as validation R2 over the upper 500 m: Cartesian velocities −0.07 → Helmholtz
potentials 0.50 → log-transformed BGC 0.63 → gradient penalty at 0.10 0.80 → 20 vertical PCs 0.81 →
wider / much wider / wider-and-deeper **0.81 / 0.78 / 0.81**, no gain. Four seeds: 0.77 ± 0.01.
NO3 stays linear because its log transform blew up autoregressively in the subpolar gyre
(`constants.py` comment; an asinh variant exists). Conservation is a **diagnostic only**:
volume-weighted inventory drift against the parent over the test rollout, following Samudra. The
loss is MAE plus the gradient penalty; the correctors are a non-negativity ReLU and an inherited
heat-content corrector.

## 2. What this supersedes in the map

- The settled row *"Does M2LINES or Neural-BGC scoop the ocean-BGC emulator niche?"* is amended.
  M2LINES is no longer a confirmation of the whitespace; a M2LINES principal investigator is an
  author of a DIC + O2 + NO3 + Chl emulator.
- **DIC and chlorophyll emulation are contested.** BG4Sea had already narrowed that on 2026-07-24;
  this closes it.
- **What is still uncontested, stated narrowly:** iron; alkalinity and the carbonate system (so
  pCO2 and the air-sea flux); calcite; any emulator of a **data-assimilating** BGC state estimate;
  validation against **independent, dated observations** rather than the parent model; and the
  parameter-identifiability result, which no emulator above attempts.
- A method lesson is recorded as a trap: a publications-page scan is not a landscape scan.
  SamudraBGC shipped as a GitHub + Zenodo + ESSOAr release, first-authored from the Resplandy
  group, and was on none of the pages the scan read.

## 3. Where their findings and ours agree, independently

Different parent model, different resolution, different cadence, same three conclusions. This is
the credible opening for any conversation, because it is agreement and not critique.

| design question | SamudraBGC (9 km, daily, MOM6-COBALT) | DarwinDiff (1 degree and LLC270, ECCO-Darwin v05) |
|---|---|---|
| log space for BGC tracers | R2 0.50 → 0.63 | linear z-scoring collapsed Chl to 0.36 of its log-range with 30.4% of predictions below zero; log gave 0.891 retention and 0.00% non-physical output |
| more capacity | no gain, 0.81 / 0.78 / 0.81 | about 4x parameters bought +0.007 |
| ensembles | 50-member ensembles reproduce the parent's spread | an 8-seed deep ensemble was the only lever that paid, +0.432 → +0.484; diffusion hurt |
| conservation | diagnosed, not enforced | settled: soft penalties, not hard constraints |
| log is not free | NO3 in log space blew up in rollout | `surfChl4` is negative in 100% of cells, so log needs clipping and the clipped fraction recorded |

## 4. The distance from SamudraBGC to "BGC inside SamudrACE"

1. **Carbon closure.** The quantity a coupled carbon-climate emulator exchanges with the
   atmosphere is the air-sea CO2 flux, which needs pCO2(DIC, ALK, T, S). SamudraBGC has DIC and no
   ALK, so today it cannot diagnose it. Section 7 shows why DIC skill alone does not settle this.
2. **Inventory-level accuracy under forcing.** Ocean uptake is a small residual on a very large
   reservoir, and under rising CO2 the DIC inventory leaves the training distribution by
   construction. Drift that is harmless for a 5-year control rollout in a closed basin is a false
   sink in a forced global run. Samudra 2 itself lists conservation-embedding hybrids as a direction.
3. **Global geography and iron.** A global BGC emulator is decided in the Southern Ocean and the
   equatorial Pacific, by iron. Our own result there is specific: iron was the one tracer that beat
   no baseline while still carrying directional tendency information, which is the signature of a
   **missing forcing input** (episodic dust), not of a small network. SamudraBGC is forced by heat
   flux and wind stress only.
4. **Observations.** A free-running control run cannot be compared with dated observations. A
   state estimate can. ECCO-Darwin is the BGC state estimate, and InMOS's charter is models plus
   observations.
5. **A seasonal null.** BGC variability is dominated by the seasonal cycle, so an R2 on a
   domain-mean chlorophyll or temperature series is mostly the seasonal cycle. Their code has a
   persistence RMSE in one side script (22 variables, 20 lead days, 288 initial dates, written for
   a comparison with a co-author's emulator) and no climatology or AR(1) null. **Whether the
   preprint reports one is UNVERIFIED**; the preprint page is behind a bot wall and was not read.
   At 9 km and daily cadence I expect their emulator to *survive* a per-cell seasonal AR(1),
   because eddies are not in a climatology. Showing that would strengthen their forecast-skill
   claim, which is why it is an offer and not an attack.

## 5. What NOT to bring. Our own map forbids each of these

- **Our forward emulator.** −0.161 ± 0.015 against a per-cell seasonal AR(1) and +0.055 ± 0.013
  against persistence, four seeds, with zero forcing inputs. It is a negative result, not a product.
- **"The field baselines too weakly" as a contribution.** Settled No: at least one 2026 BGC
  emulator baselines correctly. The claim is baseline hygiene, never baseline invention.
- **"First ocean-BGC emulator."** Dead four times over: Neural-BGC, BG4Sea, the ERSEM column
  emulator, SamudraBGC.
- **ECCO-Darwin as the BGC component of SamudrACE.** Wrong lineage. SamudrACE emulates GFDL CM4;
  its BGC twin is ESM4 / COBALT, which is Resplandy's model. ECCO-Darwin is the *observation and
  data-assimilation testbed*, not the coupled component.
- **The parameter-conditioned calibration emulator.** Shelved: one v05 trajectory, no
  perturbed-parameter ensemble, and plain-FNO parameter gradients measured at R2 0.21-0.82.

## 6. The offer, smallest step first

Everything offered is a small open artifact against *their* code. The repo is public as of
2026-09-19, so nothing here is blocked on access.

**Step 0. Tell the MIT side first.** It is a courtesy, and an introduction from a senior ocean
carbon scientist is worth more than a cold message.

**Step 1. Reproduce, then extend, on public artifacts only.** About a weekend on the local GPU.
Needs a 0.91 GB checkpoint and the 23.3 GB evaluation window. Three diagnostics, each computed on
the parent model too so that the parent is the control, which is the design of
`scripts/physics_verify.py`:

- skill against persistence by lead time, variable, depth and biome, with spatial block-bootstrap
  intervals (their side script has the RMSE and none of the intervals or biomes);
- **stoichiometric coupling of the increments.** The emulator predicts DIC, NO3 and O2 as
  independent channels; biology couples them. Regress the predicted daily increments, compare the
  DIC:NO3 and O2:NO3 slopes with the parent's own slopes. Needs no reference data. Either outcome
  is useful to them: a pass is a citable property, a fail is a concrete loss term;
- the implied pCO2 error of their surface DIC error field, through `src/darwindiff/carbonate.py`.

What 60 days cannot do is fit a climatology or an AR(1). That null needs the multi-year record,
so it is a one-command request to them, not something to claim from outside.

**Step 2. Alkalinity and a differentiable carbonate head.** `carbonate.py` is autograd-compatible
(Follows et al. 2006) and returns pCO2, pH, calcite saturation and the air-sea flux. Its calcite
saturation state is validated against PyCO2SYS on 2000 GLODAPv3 surface points (r = 0.9999, median
relative difference 1.3%); its pCO2 output has not yet been compared with PyCO2SYS directly, and
that comparison should come before it is offered as a pCO2 module. It works as a derived-variable module, a consistency check, or a loss term.
Needs ALK in their MOM6-COBALT output, which COBALT carries.

**Step 3. ECCO-Darwin as the observation-constrained second target.** Their open recipe
(Helmholtz + log + gradient penalty + vertical PCA, with forcing) trained on v05 daily, scored
against pre-registered nulls **and** against independent dated observations. What we bring is the
part they do not have: the v05 loaders on both grids, the 1200 s calendar fix, the dead-tracer
catalogue, the iron forcing loader, the GLODAP / GEOTRACES / MODIS / PACE loaders, and the
measured v05 bias regimes (unbiased at the equator, about 5x low in the North Atlantic bloom,
about +0.3 µatm global pCO2 against GLODAP). This is the step that answers InMOS's charter. It is
also a real risk: our own prognostic-only monthly operator lost to the seasonal AR(1), and v05 has
27 years of daily output against their 60. It should be pre-registered as a transfer test.

**Step 4. Identifiability as design constraints for ML data assimilation.** When the work moves
from emulating state to estimating parameters, three of our results are directly reusable and
would each save months: no estimator breaks a rank-1 structural null (EnKF, EKI/CES, history
matching, Kennedy-O'Hagan, SINDy all hit the same wall; only a new out-of-manifold observation
does); a recovery count is meaningless without its untrained chance rate; and the iron source-sink
degeneracy is structural to any model with dust solubility times scavenging, which COBALT has.
Their idealised double gyre is a clean place to test whether that degeneracy is model-independent.

Also on the shelf, feasibility only: a conservative differentiable transport operator (relative
global mass drift 5.3e-6 at both 20,000 and 100,000 steps, bounded and non-accumulating) and an
earth2studio `PrognosticModel` wrapper (interface conformance only).

## 7. What a DIC error means in pCO2

`python scripts/analysis/dic_error_to_pco2.py` → `docs/findings/dic_error_to_pco2.json`. Alkalinity,
temperature and salinity held exact; Revelle factor by autograd.

| regime | pCO2 | Revelle | +2 µmol/kg DIC | +4 µmol/kg DIC |
|---|---|---|---|---|
| subtropical gyre (22 C) | 367.7 µatm | 9.88 | +3.57 µatm | +7.17 µatm |
| mid (15 C) | 356.0 µatm | 11.16 | +3.85 µatm | +7.75 µatm |
| subpolar gyre (8 C) | 346.3 µatm | 12.69 | +4.18 µatm | +8.43 µatm |

The two DIC magnitudes are the two the SamudraBGC model card reports (a validation-period bias
below 2 µmol/kg; a time-mean meridional section RMSE of 4.0 µmol/kg at R2 = 0.992). **Neither is a
surface error, so this table is a sensitivity and not a finding about their emulator.** What it
establishes is only this: an error that reads as R2 = 0.992 in DIC is, if it appears at the
surface, the same size as the air-sea disequilibrium that drives the ocean carbon sink. A random
error averages out of an area-integrated flux; a bias does not. Step 1 is what would turn the
conditional into a measurement.

## 8. Evidence labels

- **Measured here:** the pCO2 table; the code-search counts; repository, Zenodo and Hugging Face
  metadata; the map's integrity check before and after.
- **Read at the primary source:** every SamudraBGC design fact, from files in **their** repository
  and not this one (README, model card, experiments guide, and the constants, loss, corrector and
  lead-time RMSE modules); the SamudrACE and Samudra 2 statements (arXiv HTML); the InMOS
  description (Schmidt Sciences).
- **UNVERIFIED:** the content of the SamudraBGC preprint itself, including whether it reports a
  climatology or AR(1) null and what it lists as future work. Not read.
- **Inferred, not measured:** that their emulator would survive a seasonal AR(1) at 9 km; that
  COBALT's iron parameters carry the same rank-1 degeneracy; that an introduction is available.
- **Not run:** any SamudraBGC inference. Nothing in this note is a reproduction.

## Sources

- Duncan et al. 2026, GRL, doi 10.1029/2025GL119340; arXiv 2509.12490v2
- Yuan et al. 2026, Samudra 2, arXiv 2606.02610
- Keutgen De Greef et al. 2026, SamudraBGC, ESSOAr doi 10.22541/essoar.15006794 (not read);
  `github.com/mkeutgen/SamudraBGC`; Zenodo 10.5281/zenodo.21352483 and 10.5281/zenodo.21341550;
  Hugging Face `mkeutgen/SamudraBGC`
- Schmidt Sciences, Ocean Biogeochemistry Virtual Institute, project list and InMOS announcement
- Ai2 blog, "SamudrACE", 16 Oct 2025 (next step stated there: training on CM4 runs up to 4x CO2)
