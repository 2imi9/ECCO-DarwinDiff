# Observations-only Track-1 closeout — scope, feasibility, pre-registration

**Date:** 2026-07-29 · **Status:** design + feasibility only, nothing launched · **Prescription:**
J. Lauderdale, captured in [`docs/findings/2026-07-29_lauderdale_answers.md:31-36`](../findings/2026-07-29_lauderdale_answers.md)

> "This work is great. I think what would wrap up track 1 is dropping the ECCO-Darwin model output
> and just trying to fit observations."

`README.md:26-27` states the study is a *"consistency check against Carroll's published values, not a
cross-validated discovery — the 0-D box homogenizes, so held-out real-data R² is negative."* Dropping
the Darwin target is the prescribed path out.

**Verdict up front.** The loss half of the prescription is **already implemented and already run,
twice**, under the name *anchors-only*. It is not blocked. What it revealed is the actual bind, and
the bind is two different things for two different parameters:

| | |
|---|---|
| `alpfe`, `R_PICPOC` | **feasible now** — they survive with every Darwin-target term at zero |
| `scav_rat` | **blocked on identifiability** — 0/50 per-AOI without the Darwin-pattern term |
| `diatomgraz` | **blocked on data** — 11 real observation cells across 3 AOIs, none in the Southern Ocean |
| `Smallgrow`, `Biggrow` | no dedicated observable anywhere; excluded, not failed |

And a structural point that is new to this note: an observations-only fit and a *cross-validated*
fit pull in opposite directions given this surrogate. §4.4.

---

## 1. Every loss term in `scripts/run_v3.0_joint_multi_aoi.py`, classified by target

Line numbers are the `aoi_loss` gate for each term. "D" = the target is **ECCO-Darwin model output**.
"R" = the target is a **real observation**. "—" = no target (physics residual or regularizer).

### 1.1 The base block — one weight, eleven fields, all Darwin

Lines **1685–1697** form a single expression scaled by `DARWIN_PATTERN_W / (FET_W + 10.0)`. Every
field in it is a v05 model output read by `_build_aoi_targets` (`:630-660`) and z-scored per AOI.

| # | field | line | env weight | target source | class |
|---|---|---|---|---|---|
| 1 | surface DFe vs Darwin `FeT` | 1686 | `NB23_FET_WEIGHT` (1.0) × `DARWIN_PATTERN_W` | `feT_binned` | **D** |
| 2–6 | 5 PFT biomasses vs Darwin `Chl1`–`Chl5` | 1687–1691 | `DARWIN_PATTERN_W` (unit each) | `chl_per_pft` `:645-648` | **D** |
| 7 | surface POC | 1692 | `DARWIN_PATTERN_W` | `poc_binned` | **D** |
| 8 | surface PIC | 1693 | `DARWIN_PATTERN_W` | `pic_binned` | **D** |
| 9 | surface DIC | 1694 | `DARWIN_PATTERN_W` | `dic_binned` | **D** |
| 10 | surface ALK | 1695 | `DARWIN_PATTERN_W` | `alk_binned` | **D** |
| 11 | air–sea CO₂ flux | 1696 | `DARWIN_PATTERN_W` | `co2_flux_obs` | **D** |

⚠ **Naming trap — FIXED IN CODE 2026-07-29, but not removable.** The key is called `co2_flux_obs`
while line 644 assigns `ds_avg_local["CO2_flux"]` — Darwin's own flux diagnostic, not an
observation. Anyone auditing the loss by variable name misclassifies terms 11 and 26.

The key **cannot be renamed**: it is a `torch.save` cache key (`:709`) with no version field, and
`targets["co2_flux_obs"]` is read *outside* the cache-rebuild `try`, so a rename would raise
`KeyError` against every cache already on disk rather than triggering a rebuild. What was done
instead: all **10 local uses are now `co2_flux_darwin`**, both assignment sites carry a
"NOT an observation" comment, and `tests/test_loss_target_provenance.py` holds three guards —
no bare `co2_flux_obs` local, the warning comment stays, and **no new target read from
`aligned(...)` or `ds_avg_local[...]` may end in `_obs`**. Each guard was mutation-tested and
fails on its own mutation only.

### 1.2 Every remaining term

| # | env weight | default | line | target | class |
|---|---|---|---|---|---|
| 12 | `NB23_PINN_WEIGHT` | 3.0 | 1699 | none — iron-budget steady-state residual | **—** |
| 13 | `GEOTRACES_W` | 0.3 | 1717 | GEOTRACES IDP2025 surface `Fe_D`, QC {49,50}, ≤50 m | **R** |
| 14 | `GEOTRACES_SUB_W` | 1.0 | 1723 | GEOTRACES subsurface `Fe_D`, 50–1000 m | **R** |
| 15 | `POC_SUB_W` | 3.0 | 1729 | `poc_l2_z` ← Darwin IC cache `POC_L2` (`:1432-1435`) | **D** |
| 16 | `CHL1_W_EXTRA` | 0.0 | 1735 | Darwin `Chl1`, a second time | **D** |
| 17 | `GEOTRACES_POC_SUB_W` | 0.0 | 1739 | GEOTRACES `POC_LPT+SPT` | **R** |
| 18 | `PIC_ABS_W` | 0.0 | 1749 | Darwin `pic_binned` absolute (`:997`) | **D** |
| 19 | `POC_ABS_W` | 0.0 | 1758 | Darwin `poc_binned` absolute (`:1013`) | **D** |
| 20 | `ALK_ABS_W` | 0.0 | 1772 | GLODAPv2 TAlk (`:1042-1052`) — **or** Darwin ALK when `ALK_ABS_SOURCE=darwin` (`:1037-1041`) | **R / D** |
| 21 | `RATIO_W` | 0.0 | 1783 | Darwin `pic_binned/poc_binned` (`:1091-1093`) — the circular path | **D** |
| 22 | `DANIELS_RPICPOC_W` | 0.0 | 1799 | Daniels 2018 CP:PP, PANGAEA 888182 (`:1119-1133`) | **R** |
| 23 | `POSI_W` | 0.0 | 1819 | GEOTRACES bSi (`bSi_LPT+SPT`), ≤50 m | **R** |
| 24 | `POSI_DARWIN_W` | 0.0 | 1824 | Darwin `POSi` (TRAC16) | **D** |
| 25 | `PRIMPROD_W` | 0.0 | 1835 | Darwin `primProd` | **D** |
| 26 | `F_CO2_ABS_W` | 0.0 | 1845 | Darwin `CO2_flux` absolute | **D** |
| 27 | `CONSISTENCY_LAMBDA` | 0.0 | 1926 | none — cross-AOI parameter-mean regularizer | **—** |
| 28 | `DUST_ANCHOR_W` | 0.0 | 1945 | Gaussian prior N(1.15, 0.7) from Xu & Weber Al-inverse | **R (prior)** |

Per-AOI multipliers: `AOI_W_*` on the whole AOI loss (`:1906`), `RATIO_AOI_W_*` (`:1788`),
`DANIELS_AOI_W_*` (`:1804`).

**Tally: 19 Darwin-target terms** (11 in the base block + `POC_SUB_W`, `CHL1_W_EXTRA`, `PIC_ABS_W`,
`POC_ABS_W`, `RATIO_W`, `POSI_DARWIN_W`, `PRIMPROD_W`, `F_CO2_ABS_W`), **6 real-observation terms**
(`GEOTRACES_W`, `GEOTRACES_SUB_W`, `GEOTRACES_POC_SUB_W`, `DANIELS_RPICPOC_W`, `POSI_W`,
`DUST_ANCHOR_W`), **1 switchable** (`ALK_ABS_W`), **2 untargeted** (`PINN_W`, `CONSISTENCY_LAMBDA`).

### 1.3 The whitening, and what the weights therefore assert

Every absolute-units block divides its masked MSE by `scale = mean(target²)` over its own mask —
**11 sites**, lines 1719, 1725, 1741, 1751, 1760, 1774, 1786, 1802, 1821, 1826, 1847. So each block
enters as a fractional-error term and `w_g` is `1/σ_g²` in fractional units. Nothing measured that;
every one was set by sweep. The consequence is analysed in
[`2026-07-27_hierarchical_inversion_design.md:280-294`](2026-07-27_hierarchical_inversion_design.md) —
`GEOTRACES_W=0.3` vs `GEOTRACES_SUB_W=1.0` asserts surface bottle dFe is 1.8× fractionally noisier
than subsurface; `DANIELS_RPICPOC_W=1.0` asserts a CP:PP incubation ratio is as fractionally precise
as a bottle dFe measurement, which it is not.

**This survives the prescription.** Dropping the Darwin targets does not fix it — it *raises its
stakes*, because with the dense pattern block gone the anchor weights are the entire loss.

### 1.4 Darwin enters three ways, and the prescription only removes one

| channel | code | removable by env var? |
|---|---|---|
| **loss targets** | §1.1 + the D rows of §1.2 | **yes** — `DARWIN_PATTERN_W=0 POC_SUB_W=0 CHL1_W_EXTRA=0` |
| **initial condition** | `USE_DARWIN_IC`, pickup-derived cache `:1397-1431` | **yes** — `DARWIN_IC=0` falls back to `LIT_IC` literature constants `:1387-1394` |
| **forcing** | SST, MLD, wind, SSS, apCO₂ from v05 `:635-643`, consumed at `:1449` | **no** — would need ERA5/OISST substitution, real code |

So "dropping the ECCO-Darwin model output" is achievable for the loss and the IC with env vars alone.
The **forcing stays Darwin's** in any near-term version. Say that plainly in any write-up; do not
claim a Darwin-free fit.

---

## 2. What survives when every Darwin-target term is off

This ablation exists, is named `DARWIN_PATTERN_W` (`:282-290`), and has been run at n=10 and n=50.

**The quote asked for, verified.** `STATUS.md:298`:

> **scav_rat** … 25/50 per-AOI 2000ep → **41/50 4000ep** … **collapses to 0/10 when Darwin-pattern
> terms are off (anchors-only) → partly pattern-assisted**

Primary artifacts:

- [`2026-07-21_anchors_only_ablation.md:15-20`](../findings/2026-07-21_anchors_only_ablation.md) —
  n=10, `DARWIN_PATTERN_W=0 POC_SUB_W=0 CHL1_W_EXTRA=0`, PINN kept on, `verify_run` exit 0:
  `alpfe` **10/10**, `scav_rat` **0/10**, `R_PICPOC` 6/10, trio **0/10** (all per-AOI).
- [`2026-07-22_anchors_only_n50_verified.md:9-16`](../findings/2026-07-22_anchors_only_n50_verified.md) —
  n=50, PINN **also** off, Slurm 8536393, `verify_run --expect-seeds 50` exit 0:
  `alpfe` **50/50**, `R_PICPOC` **28/50**, `scav_rat` **0/50**, `diatomgraz` 11/50, trio **0/50**.
  scav_rat's cell-weighted 40/50 is a **southernoceanpac straddle** — every seed lands Cal+ in
  exactly one AOI. Do not quote it.

| parameter | anchors-only survivor? | what carries it |
|---|---|---|
| `alpfe` | **YES**, 50/50 | real GEOTRACES surface + subsurface dFe, term 13/14 |
| `R_PICPOC` | **YES**, 28/50 | real Daniels CP:PP, term 22 (anchor-off control → 6/50 epoch-matched) |
| `scav_rat` | **NO**, 0/50 | nothing real. Its recovery is Darwin-pattern-assisted |
| `diatomgraz` | 11/50, chance-ish | real GEOTRACES bSi, term 23 — 11 cells total |
| `Smallgrow`, `Biggrow` | no dedicated term at any weight | — |

**The prescription has therefore been executed for the loss, and the answer is 2 of 4.** The trio goes
to 0/50 because `scav_rat` is the binding leg.

---

## 3. Loader inventory — wired, unwired, staged

`src/darwindiff/` holds 12 observational loaders. Only three reach the flagship runner
(`:204`, `:209`, `:214`).

| loader | imported by the flagship runner? | tests | data staged in this checkout? |
|---|---|---|---|
| `geotraces_loader` | **yes** `:204` | `tests/test_geotraces_loader.py` | external root `D:\geotraces` |
| `glodap_loader` | **yes** `:209` (only if `ALK_ABS_W>0`) | `tests/test_glodap_loader.py` | external root |
| `daniels_loader` | **yes** `:214` | `tests/test_daniels_loader.py` | external `.tab` |
| `modis_pic_loader` | **no** — only `scripts/run_v3.0_with_modis_pic.py` + compare scripts | none | no |
| `pace_loader` | **no** — no importer at all | none | no |
| `marsh_loader` | no — analysis scripts only | `tests/test_marsh_loader.py` | no |
| `cochran_gp15_po_pb_loader` | **no** | `tests/test_cochran_gp15_po_pb_loader.py`, 13 tests | **no** (all skip) |
| `black2020_fe_flux_loader` | **no** — zero importers | **none** | no |
| `rufas2024_poc_flux_loader` | **no** — zero importers | **none** | no |
| `xu_weber_loader` | **no** — zero importers | **none** | no |
| `gledhill_fe_prime_loader` | **no** — zero importers | **none** | no |
| `held_out_obs` | no — Track-2 E2 runner + analysis | `tests/test_held_out_obs.py` | — |

`python -m pytest tests/test_cochran_gp15_po_pb_loader.py tests/test_daniels_loader.py -q` → **exit 0**,
11 passed, 19 skipped. Every skip is "data not staged". `data/` in this worktree contains only
`README.md`; all raw data is gitignored (`data/README.md:3`).

**Two of the unwired loaders are precisely the missing legs.**
`black2020_fe_flux_loader` is the ²³⁴Th/sediment-trap iron **export flux** — a real *rate*, the one
observable class `scav_rat` needs and does not have. `xu_weber_loader` is the soluble-Fe deposition
**source**; its province value is already distilled into `DUST_ANCHOR_MU=1.15` (`:481-483`), so the
source leg is available as a scalar prior without wiring the field.

`cochran_gp15_po_pb_loader` is a ²¹⁰Po/²¹⁰Pb scavenging-rate anchor. Committed correction
[`2026-07-28_gp15_leg2_correction.md:67-87`](../findings/2026-07-28_gp15_leg2_correction.md): Leg 2
gives **67 eqpac samples**, of which the **dissolved** phase has 64 spanning 20–5340 m at **3
stations**, while `load_scavenging_anchor` defaults to `phase="T"` which yields **3 surface points**.
Depth structure is the informative content; three stations is the real limit.

**No `SCAV_ANCHOR_W` loss term exists** in `run_v3.0_joint_multi_aoi.py`. Wiring any rate anchor is a
code task, not an env var. Confirmed by the same absence noted in
`2026-07-22_next_direction_rpicpoc_protection.md:20`.

---

## 4. Feasibility — honest

### 4.1 Real observation cells, per AOI, per parameter

From `docs/findings/2026-07-23_percell_crlb/percell_crlb_summary.json`, generated with
`active_terms = {GEOTRACES_W, GEOTRACES_SUB_W, DANIELS_RPICPOC_W, POSI_W} = 1.0` — i.e. **the
observations-only loss is exactly what this artifact already profiles**, and its residual
reconstruction reproduces the full loss to rel. err ≈ 3e-8.

| AOI | ocean cells | iron (surf/sub) | Daniels | POSi | **union informative** |
|---|---|---|---|---|---|
| eqpac | 1071 | 26 / 28 | 34 | 7 | **59** |
| natlsubpolar | 484 | 13 / 13 | 26 | 4 | **39** |
| southernoceanpac | 1296 | 13 / 14 | **0** | **0** | **14** |
| **total** | **2851** | | | | **112 (3.9 %)** |

Per parameter, cells carrying **any** real information (`n_info_cells` on the dedicated block):

| parameter | eqpac | natl | sopac | total | of 2851 |
|---|---|---|---|---|---|
| `alpfe` | 28 | 13 | 14 | **55** | 1.9 % |
| `scav_rat` | 28 | 13 | 14 | **55** | 1.9 % |
| `R_PICPOC` | 34 | 26 | **0** | **60** | 2.1 %, 2 of 3 AOIs |
| `diatomgraz` | 7 | 4 | **0** | **11** | 0.4 %, 2 of 3 AOIs |
| `Smallgrow`, `Biggrow` | 0 | 0 | 0 | **0** | dedicated: none |

The zeros are exact, not small. `2026-07-23_percell_crlb_map.md:33-35`: *"Because each real term
multiplies its residual by an observation mask and the box is per-cell independent, the per-cell
gradient — hence the information — is exactly zero where there is no observation."*

### 4.2 The estimator does not match the data volume

The base block (§1.1) is masked by `mask_f`, the **full ocean mask** (`:1653`), so in the flagship
every one of 2851 cells receives a gradient. Every anchor term is masked by its own sparse mask. Turn
the Darwin block off and **96.1 % of cells have identically zero loss gradient.**

Free parameters, flagship recipe (`PER_AOI_DINN=1`, 3 AOIs, `DINN_HIDDEN_DIM=16`, 1 input channel):
**406 weights per (seed, AOI) → 1218 per seed.** Scalar real residuals available: 95 (eqpac) + 56
(natl) + 27 (sopac) = **178**. The observations-only per-cell problem is under-determined ≈ 7×, and
the recovery metric averages the parameter field over all ocean cells — so the graded number is
dominated by cells the data never touched.

`GlobalScalarNet` has **6 weights** (verified by instantiation). One global 6-vector against 178
residuals is over-determined ≈ 30×. **The observations-only fit is well-posed only if the
parameterization is reduced**, and the runner already supports that with `GLOBAL_SCALAR=1` (`:1584`).

### 4.3 It has already been done once with the right estimator

[`2026-07-22_eki_fullbox_result.md`](../findings/2026-07-22_eki_fullbox_result.md) —
`scripts/analysis/eki_fullbox_trio.py`. Loss = real GEOTRACES surf/sub dFe + real Daniels CP:PP
**only**. Three global scalars in log space, growth held at Carroll, derivative-free EKI (J=256, 30
iters), no DINN, no autograd:

| param | EKI posterior mean | Carroll | rel. off | band |
|---|---|---|---|---|
| `alpfe` | 0.999 | 0.928 | 0.08 | Cal-grade |
| `R_PICPOC` | 0.036 | 0.0425 | 0.14 | Cal-grade |
| `scav_rat` | 2.1e-7 | 6.0e-7 | 0.65 | Loose |

Same 2-of-3 verdict as the anchors-only backprop runs, from an independent estimator. What it lacks
is a **seed ensemble and a null** — it is a point estimate, and the doc is explicit that the ensemble
spread is not a calibrated posterior.

### 4.4 The structural bind — observations-only and cross-validated pull opposite ways

This is the part that has not been written down before.

- **Per-cell DINN** could in principle produce held-out spatial skill, because the parameter field
  varies with the env channels. But it is the estimator with 3.9 % coverage, and the documented
  held-out result is negative (`STATUS.md:420-422`, `README.md:26-27`).
- **Global scalar** matches the data volume and is well-posed. But a spatially uniform parameter,
  run through a 0-D box, produces a spatially uniform anomaly. The held-out metric in
  `held_out_obs.anomaly_masked_r2` scores **against the constant train basin mean**. A global scalar
  therefore cannot beat that null on held-out anomalies **by construction**, at any data volume.

So: the estimator that can pass a cross-validation test cannot be fit with the data; the estimator
that can be fit with the data cannot pass the test. **Observations-only removes the circularity. It
does not, and with a 0-D box cannot, convert the study into a cross-validated discovery.** That is a
limit of the surrogate, and it is the honest thing to publish alongside the fit.

Independent support, from a committed artifact and *not* from the box:
`docs/findings/geotraces_glodap_env_identifiability.json` regresses real surface `Fe_D` on Ω and SST
with an env-regime hold-out (upper quartile), 2000-permutation null, FDR α=0.1. Held-out R² is
negative in 3 of 3 flagship AOIs on Ω (eqpac −0.19, natl −0.97, sopac −1.63) and in eqpac and sopac
on SST (−0.79, −1.25). Even a *purely statistical* env model cannot predict held-out iron in these
basins. The box is not uniquely at fault.

### 4.5 Provenance gaps found while checking — state these, do not paper over them

1. **The negative held-out R² is print-only.** `:1971-1990` computes it and prints it; the result
   JSON (`:2073-2136`) records every weight and every anchor cell count but **not**
   `GEOTRACES_HOLDOUT_FRAC` and **not** the R². A grep of `docs/**/*.json` returns no held-out R² for
   the box. **Cannot verify the box's negative held-out R² from a committed artifact** — it exists in
   README/STATUS prose and, presumably, a run log. Persisting it is a one-line fix and should happen
   before it is used as a headline limitation.
2. **`covar_env_common.sh` is not in the repo.** Every recovery config is "sourced from
   `covar_env_common.sh` first" (`2026-07-24_reproducibility_methods_appendix.md:18`), but only
   `explorer_quickstart.sh` and `orcd_quickstart.sh` exist under `scripts/`. `POSI_W=1` in the
   flagship is **inferred** from the `dgchl` row explicitly overriding it to 0, not read.
   **Cannot verify the flagship's full env from committed artifacts.**
3. **`scav_rat` per-AOI is 25 in some places and 26 in others.**
   `2026-07-21_joint_number_reconciliation.md:15` tables 26 with joint 25 and says the joint "sits one
   seed below"; line 28 of the same file says 25. `CLAUDE.md` says the trio count *equals*
   `scav_rat`'s. One of those is wrong by one seed. Not load-bearing for this note; flagged.
4. **Null hit-rate 0.47 for `alpfe`** appears only in `docs/project_checkpoint_2026-07-25.md:31`.
   No artifact backs it in this checkout. **Cannot verify from committed artifacts.**

### 4.6 Verdict

| | |
|---|---|
| `alpfe` | **feasible now**, done, 50/50 |
| `R_PICPOC` | **feasible now**, done, 28/50; **blocked on data in the Southern Ocean** (0 Daniels cells) |
| `scav_rat` | **blocked on identifiability**, and downstream of that on data: no real *rate* observable is in the loss and no `SCAV_ANCHOR_W` term exists. Black 2020 and Cochran GP15 are the candidates; both unwired |
| `diatomgraz` | **blocked on data** — 11 cells, 2 AOIs |
| growth pair | out of scope by construction |
| the fit as a **discovery** | **blocked structurally** by §4.4, independent of data |

Two parameters recoverable from real observations alone, with no ECCO-Darwin field in the loss, is a
real and defensible Track-1 closeout. It is not 4-of-4 and will not become 4-of-4 by running longer.

---

## 5. Pre-registered minimal experiment

Registered **before** running. If the outcome differs from the prediction, the prediction was wrong —
do not re-read the criterion.

### 5.1 Name and question

**`obs_only_global`** — *can the Carroll-6 parameters be estimated from real observations alone, with
no ECCO-Darwin field anywhere in the loss, using an estimator matched to the available data volume?*

### 5.2 Parameterization

`GLOBAL_SCALAR=1` (`:1584`), which takes precedence over `PER_AOI_DINN`. 6 unknowns per seed vs 178
real residuals. Deliberately **not** per-cell: §4.2 shows per-cell is under-determined ≈7× once the
dense Darwin block is removed, so a per-cell observations-only number would grade unconstrained cells.

Per-AOI values for the ≥2-of-3 metric come from **three single-AOI runs**, not one joint run —
`GLOBAL_SCALAR=1` shares one vector across AOIs, so a joint run collapses ≥2-of-3 to all-or-nothing.
Zero code.

### 5.3 AOIs and anchors

| AOI | iron | Daniels | POSi | included |
|---|---|---|---|---|
| eqpac | 26/28 | 34 | 7 | **yes** |
| natlsubpolar | 13/13 | 26 | 4 | **yes** |
| southernoceanpac | 13/14 | 0 | 0 | **yes**, iron-only leg |

### 5.4 Arms

Base, all arms:
```
AOIS=<one of eqpac|natlsubpolar|southernoceanpac>
GLOBAL_SCALAR=1
DARWIN_PATTERN_W=0  POC_SUB_W=0  CHL1_W_EXTRA=0
RATIO_W=0  PIC_ABS_W=0  POC_ABS_W=0  POSI_DARWIN_W=0  PRIMPROD_W=0  F_CO2_ABS_W=0
GEOTRACES_W=1.0  GEOTRACES_SUB_W=1.0  DANIELS_RPICPOC_W=1.0  POSI_W=1.0
NB23_PINN_WEIGHT=0
NB23_SEEDS=0,1,2,3,4,5,6,7,8,9   NB23_N_EPOCHS=2000
```

| arm | delta | resolves |
|---|---|---|
| **O0** treatment | base | the observations-only estimate itself |
| **O1** null | `GEOTRACES_W=0 GEOTRACES_SUB_W=0 DANIELS_RPICPOC_W=0 POSI_W=0` | **prior-only.** The base block is still evaluated and multiplied by `DARWIN_PATTERN_W=0` (`:1697`), so the graph is intact and gradients are exactly zero — Adam leaves the parameters at init. Gives the hit-rate of the bounded init under the ≤40 % band. **This is the null every count is scored against** |
| **O2** permuted anchor | base, Daniels + iron target values shuffled across their own cells — **needs a ~10-line patch**, no env var exists | does the recovery use the data, or only the `mean(target²)` normalizer? |
| **O3** Darwin-IC off | base + `DARWIN_IC=0` | how much of the answer is the Darwin pickup rather than the anchors? |
| **O4** rate-anchor probe | O0 on eqpac only, `GEOTRACES_SUB_W=3` | cheap proxy for "does depth structure move `scav_rat`" before anyone writes `SCAV_ANCHOR_W` |

**Cost.** 3 AOIs × 4 arms + 1 = 13 single-AOI runs, n=10, 2000 epochs, 6 free weights. Single-AOI
runs are cheaper than the 3-AOI joint flagship; this is a local-5090 job, not a cluster job. O0, O1,
O3 and O4 are env-var only; O2 is the one arm that needs code.

**Gate.** `scripts/verify_run.py --expect-seeds 10` must exit 0 for every arm. Do not run pytest or
the verifier through a pipe — a pipe masks the exit code.

### 5.5 Pre-registered predictions

Recorded now.

| parameter | prediction (O0, per-AOI ≥2-of-3) | basis |
|---|---|---|
| `alpfe` | **in band, ≥8/10** | anchors-only per-cell gives 50/50; EKI global gives 0.999 |
| `R_PICPOC` | **in band in eqpac and natl, 0 in sopac** | Daniels coverage is exactly that; EKI global gives 0.036 |
| `scav_rat` | **out of band, biased low, ≤2/10** | 0/50 anchors-only; EKI 2.1e-7 = 0.35× Carroll, Loose |
| `diatomgraz` | **at or near the O1 null** | 11 cells |
| `Smallgrow`, `Biggrow` | **identical to O1 by construction** | no term touches them; a difference means a bug |

### 5.6 What counts as what

**Discovery.** Only one outcome qualifies, and it is not "matches Carroll":

> A parameter whose observations-only estimate is **stable across seeds, separated from the O1 null
> and from the O2 permuted-anchor arm, and lands OUTSIDE Carroll's 40 % band** — with the anchor
> residual showing the observations are genuinely fit better there than at Carroll.

That is the observations telling us something the Green's-functions calibration does not. It is the
only result here that is new information rather than confirmation.

**Success, but a consistency check.** Estimate stable, separated from O1 and O2, lands **inside**
Carroll's band. Strong — it removes the circularity, which is what the prescription asked for — but
it confirms Carroll rather than discovering anything. Expected for `alpfe` and `R_PICPOC`.

**Informative failure.** Estimate indistinguishable from O1 (no information) or surviving O2 (fitting
the normalizer, not the data). Report as an observing-system limit with the cell counts from §4.1.
Expected for `diatomgraz`, and for `R_PICPOC` in the Southern Ocean.

**Uninformative.** Arms inside seed noise, or `verify_run` non-zero. Re-run or discard; do not
narrate.

### 5.7 What this experiment explicitly does not do

- It does **not** make the study cross-validated. §4.4.
- It does **not** remove ECCO-Darwin from the forcing. §1.4.
- It does **not** rescue `scav_rat`. That needs a real rate observable in the loss, which needs a
  `SCAV_ANCHOR_W` term (does not exist) and staged Black 2020 or Cochran GP15 Leg-2 dissolved-phase
  data (not staged here). O4 is a probe, not a fix.

### 5.8 The cheapest single informative version

If only one thing runs: **arm O0 + arm O1, eqpac and natlsubpolar only, n=10.** Four runs.

It removes every Darwin field from the loss, uses an estimator matched to the data volume, covers the
two AOIs that carry all the calcite and silica coverage, and — critically — produces the **first
observations-only recovery number with a null attached.** The EKI result already gives the point
estimates; what is missing and cheap is the seed spread and the null they must be separated from.

---

## 6. Reporting language

Correct: *"the Carroll-6 iron-solubility scalar and the calcite rain ratio are recoverable from real
observations alone, with no ECCO-Darwin field in the loss; the scavenging rate is not, and no
independent rate observable is available in the current observing set."*

Do not write: "we fit only observations" (the forcing is Darwin's), "cross-validated" (§4.4), or
"discovery" for any parameter that lands inside Carroll's band.
