# The North Atlantic dispersion lives INSIDE the box's biggest province, not between provinces

**Date:** 2026-08-20
**Status:** live
**Run:** AICR job **408789** (array 0-14, B200), graded by **408818**. Three arms in ONE
submission: `pcf_flagship`, `pcf_soonly`, `pcf_prior`. n=50 each, `SAVE_PER_CELL_SEEDS=10`.
**Reproduce:** `python scripts/analysis/province_dispersion.py RUN_DIR --param scav_rat --n-perm 300`

On 2026-08-17 the Longhurst overlay showed `natlsubpolar` is a 3.10-effective-province mixture and
argued from three scalars that its `log_sd` = 0.936 is a property of the fit rather than the
polygon. That was an inference. **It is now a measurement, and the mechanism turns out to be the
opposite of the hypothesis.**

---

## 1. First, the flagship lineage reproduces exactly

Everything below rests on this, and it was pre-registered in the sbatch header before submission.
The AICR checkout is at `15a3725`, behind HEAD, with only the runner `scp`'d (#218), so a miss
here would have been a provenance problem rather than a result.

| quantity | recorded | job 408789 |
|---|---|---|
| trio (arith / geom / median) | 25 / 12 / 23 | **25 / 12 / 23** |
| `scav_rat` (arith / geom / median) | 26 / 13 / 24 | **26 / 13 / 24** |
| `alpfe`, `R_PICPOC` | 49/50, 50/50 | **49/50, 50/50** |
| `scav_rat` legs, arith/geom/med | eqpac 8/8/10, natl 19/5/16, SO 49/49/49 | **identical** |
| `log_sd` eqpac / natl / SO | 0.245 / 0.940 / 0.379 | **0.245 / 0.940 / 0.379** |
| McNemar arith-vs-geom | 13 arith-only, 0 geom-only, P = 2.4e-04 | **13 / 0, P = 2.44e-04** |
| `so_only` `scav_rat` | 30 / 49 / 28, `log_sd` 1.310 | **30 / 49 / 28, 1.310** |
| `so_only` vs null | P = 3.15e-24 arith, 6.3e-59 geom | **3.2e-24, 6.3e-59** |

`verify_run` exits 0 on both trained arms against the matched untrained null. This is an
independent replication on a different build, which also bears on **#226** and **#218**.

## 2. Provinces explain LESS of the dispersion than arbitrary latitude bands

One-way ANOVA of per-cell `log(scav_rat)` with province as the factor, n=50 seeds, 300
permutations each. The comparison that matters is not the shuffled null but the **latitude-band
control** -- the same group sizes with boundaries drawn by latitude alone -- because Longhurst
provinces are largely latitudinal and any smooth north-south gradient beats a shuffle trivially.

| AOI | `log_sd` | eta^2 province | shuffled null | **latitude bands** | province - bands |
|---|---:|---:|---:|---:|---:|
| `eqpac` | 0.245 | 0.329 | 0.002 | 0.282 | **+0.046** |
| `natlsubpolar` | 0.940 | 0.338 | 0.010 | 0.357 | **-0.009** |
| `southernoceanpac` | 0.379 | 0.744 | 0.002 | 0.761 | **-0.016** |

In the North Atlantic, province membership beats matched latitude bands in **23 of 50 seeds** --
a coin flip. Province boundaries carry **no information latitude alone does not**.

**66.2% of the North Atlantic log-variance lives WITHIN provinces.**

## 3. And it lives inside ONE province -- the biggest one

This is the result. Within-province `log_sd` in `natlsubpolar`, medians over 50 seeds, against the
whole-box 0.940 and the sigma = 0.820 threshold at which the arithmetic collapse alone clears the
+/-40% band:

| province | share of box | cells | within-province `log_sd` | seeds where within > whole box |
|---|---:|---:|---:|---:|
| **`NADR`** | **41.5%** | 198 | **1.085** | **48 / 50** |
| `ARCT` | 30.5% | 148 | 0.196 | 0 / 50 |
| `SARC` | 19.1% | 96 | 0.214 | 0 / 50 |
| `BPLR` | 3.0% | 22 | 0.279 | 0 / 50 |
| `NECS` | 2.8% | 14 | 0.714 | 16 / 50 |

The three polar provinces are **quiet** -- 0.196 to 0.279, far under the threshold, in every seed.
All the dispersion is inside `NADR`, the North Atlantic Drift, which is both the largest province
in the box and the only one above the threshold.

**So defining the AOI as a province would make the North Atlantic WORSE, not better.** An AOI equal
to `NADR` carries `log_sd` = 1.085 against the box's 0.940, i.e. a bigger arithmetic-collapse
artifact (inflation x1.80 against x1.56), on 41.5% of the cells. The province hypothesis is not
merely unsupported; acting on it is contraindicated for this basin.

## 4. What changes when the same box goes 0.379 -> 1.310 is entirely within-province

`southernoceanpac` appears in both arms of the same job, so this is a **within-job** comparison --
the 2026-08-17 version of this argument was cross-job and could not be defended.

| | 3-AOI flagship leg | single-AOI `so_only` |
|---|---:|---:|
| total `log_sd` | 0.379 | **1.310** |
| eta^2 province | **0.744** | **0.225** |
| latitude-band control | 0.761 | 0.234 |
| variance living WITHIN provinces | 25.6% | **77.5%** |
| within-`ANTA` `log_sd` | 0.137 | 0.994 (**x7.3**) |
| within-`SANT` `log_sd` | 0.224 | 1.299 (**x5.8**) |
| seeds where province beats latitude bands | 0 / 50 | 2 / 50 |

Identical geography, identical province composition. When sigma triples, the province-explained
fraction **falls from 74% to 23%**: the added dispersion is generated entirely *inside* provinces.
In the quiet configuration the field is province-organised and small; in the loud one it is
province-blind and large.

## 5. What this settles

- **The province hypothesis for the dispersion is refuted by direct measurement**, not inferred
  from three scalars. Provinces never beat matched latitude bands in any AOI's median seed, and
  two-thirds of the North Atlantic variance is within-province.
- **A province-based North Atlantic AOI is contraindicated**: `NADR` alone is *noisier* than the
  box that contains it, in 48 of 50 seeds.
- **The dispersion is a fit property, now demonstrated within a single job.** Same box, sigma
  x3.5, province share 74% -> 23%.
- **Unchanged and still worth doing:** the iron-coverage argument from 2026-08-17 is untouched by
  any of this. `ANTA` carries 125 stations / 1,558 samples against the Southern Ocean box's
  16 / 241. That case rests on observations, not on dispersion, and is the one province-shaped
  change still worth costing.
- The remaining open question is what *does* generate the within-`NADR` scatter. It is not
  geography, and it is not the AOI boundary.
