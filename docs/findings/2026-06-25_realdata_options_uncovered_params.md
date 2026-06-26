# Real-data options for the 3 uncovered Carroll-6 params (R_PICPOC, Smallgrow, Biggrow)

**Date:** 2026-06-25 · **Spine:** D (#143) / C (#116) · **Status:** deep-research (11 agents,
source-verified + repo-grounded). Companion to the GEOTRACES "agreement audit" (alpfe, scav_rat,
diatomgraz vs real GEOTRACES iron/bSi). This note = real-data options for the 3 params with NO
GEOTRACES anchor.

## TL;DR

- **R_PICPOC IS real-data testable now.** Best anchor = **MODIS-Aqua surface PIC** — the literal
  calcite quantity, independent of Darwin (breaks circularity). Loader (`modis_pic_loader.py`) +
  loss (`MODIS_PIC_ABS_W` in `run_v3.0_with_modis_pic.py`) already built; cache
  (`modis_pic_clim_2017_2019.npz`, 10.5 KB) + 23 granules on the local **D: drive** (reachable).
  ~½ day: stage cache + port the loss (best: feed MODIS PIC as the `RATIO_W` numerator, replacing
  Darwin's circular `pic_binned`, keep `RATIO_MAX`).
- **The growth pair (Smallgrow/Biggrow) is fundamentally NOT cleanly testable** against accessible
  real data — a real, layered limitation (below). Best available is a *joint-sum* validator (CbPM
  µ), itself a model inversion.

## R_PICPOC — ranked options

| # | observable | dataset / source | accessibility | power | wire-in |
|---|---|---|---|---|---|
| 1 | **surface PIC** | MODIS-Aqua L3m monthly (Balch&Gordon, OB.DAAC R2022) | **in-project**; cache + granules on D: | **high** (literal calcite, non-circular) | port `MODIS_PIC_ABS_W` into joint runner, or as `RATIO_W` numerator (~30-60 lines) + stage 10.5 KB cache |
| 2 | surface total alkalinity | GLODAPv2.2016b TAlk, NCEI 0162565 (213 MB) | **code fully wired**, data not staged | low-mod (calcite-mort mutex; salinity-swamped; no S-normalization) | download + `ALK_ABS_W>0`, zero code |
| 3 | NN TAlk climatology | Broullón 2019 NDP-106, NCEI 0222470 | downloadable | low-mod (same mutex caveat) | +30-line `ALK_ABS_SOURCE='ndp106'` |
| 4 | calcite-production:PP | Poulton/Daniels 2018, PANGAEA 888182 | **free, no login** | high but sparse (truest analog — observes *production*) | new ratio/validation term; best as validation |
| 5 | sediment-trap PIC:POC | Mouw 2016, PANGAEA 855594 | free | low for fit; high to justify `RATIO_MAX` empirically | use as literature `RATIO_MAX` value |
| 6 | cocco biomass | MAREDAT 785092 / PACE (`pace_loader.py`) | free / built-shelved | low/indirect | shelve (leapfrog) |

**MODIS caveat:** MODIS PIC is ~20-53× higher than v05 in eqpac (Balch-Gordon 2-band bias in
cyano-dominated water) → anchor on the per-AOI **ratio** with `RATIO_MAX`, treat absolute as
cross-check. Validate with Poulton 888182.

## Smallgrow / Biggrow — the honest verdict: no clean real separator

| # | observable | source | accessibility | power |
|---|---|---|---|---|
| 1 | size-fractionated NPP | Wang 2025 (10.1029/2025GB008851) / Uitz 2010 | **needs-processing** (Wang product not confirmed downloadable) | highest *in principle* — only size-resolved option — but blocked (below) |
| 2 | community growth-rate µ | CbPM, Oregon State Ocean Productivity | **downloadable now** | moderate, **JOINT-SUM only** (a Chl:C model inversion) |
| 3 | size-fractionated chl | Copernicus OCEANCOLOUR_GLO_BGC_L4_MY_009_104 | downloadable | pattern-only, joint |
| 4 | community 14C-PP | Mattei&Scardi 2021, PANGAEA 932417 | clean tabular | low (flux not rate; steady-state-redundant) |

**Why the growth pair can't be cleanly tested against real data (all verified in code):**
1. **Growth rates aren't observed** — µ products (CbPM) are Chl:C *model inversions* → "passing"
   validates the box vs another model, not the ocean.
2. **Biomass ≠ rate**, and box chl targets are z-scored (magnitude cancels → pattern only).
3. **Steady state**: PP ≈ biomass·µ, so community PP/NPP restates the existing chl loss (only
   tightens the joint sum) — the documented {Smallgrow,Biggrow} ceiling.
4. **STRUCTURAL (decisive):** in the **2-layer mapping we use**, `Biggrow=mu_lge` drives only
   large-eukaryote growth and **diatom growth is a FIXED constant `MU_DEFAULT_DIATOM`**
   (`carroll6_5pft_2layer.py:297`, non-learned). So size-fractionated data's diatom channels push
   on a parameter the optimizer **cannot move**. The lumped mapping (Biggrow→diatoms) exists only
   in the single-layer `carroll6_5pft.py`, not the 2-layer step. **Prerequisite** to any
   growth-pair real-data investment: switch the 2-layer step to a lumped mapping, OR report these
   as joint-sum *validation*, not Smallgrow/Biggrow recovery anchors.

## Recommended sequence

1. **GLODAP TAlk smoke test (R_PICPOC), zero-code** — stage NCEI 0162565, `ALK_ABS_W>0`, **measure
   `dLoss/dR_PICPOC`**. Fastest check of whether a real carbonate observable even has gradient on
   R_PICPOC. Flat → confirms ALK is salinity-swamped → go to MODIS.
2. **MODIS PIC via `RATIO_W` (R_PICPOC)** — the real, non-circular anchor. Stage the D: cache, route
   MODIS into the ratio numerator. Does **real** calcite prefer Carroll's R_PICPOC? Validate w/ 888182.
3. **CbPM µ via `PRIMPROD_W` (growth pair, JOINT)** — swap the circular Darwin-primProd target for
   real division-rate µ; tests whether recovered Smallgrow+**Biggrow sum** matches a real growth
   field. Only after deciding the §4 mapping question.

**Not testable with available real data:** a clean, accessible, *separating* anchor for Smallgrow
vs Biggrow individually. R_PICPOC has a solid runnable real anchor (MODIS PIC); the growth *pair*
has only a joint-sum validator.
