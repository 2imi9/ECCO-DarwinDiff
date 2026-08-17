# Longhurst provinces: the North Atlantic box really is a three-province mixture, and that is still not what drives its dispersion

**Date:** 2026-08-17
**Status:** live
**Compute:** none — polygon geometry plus a lookup. Reproduce with
`python scripts/analysis/province_overlay.py --json docs/findings/2026-08-17_province_overlay.json`
**Raw output:** [`2026-08-17_province_overlay.json`](2026-08-17_province_overlay.json)

Jon suggested on 2026-08-16 that AOIs be defined as biogeochemical provinces (Longhurst or
EMU) instead of lat/lon rectangles. Two questions were put to the overlay. The short answers
are **yes to the geography, no to the mechanism, and the interesting result is neither.**

---

## 1. The question that was actually being asked

`natlsubpolar` carries a per-cell dispersion of `per_aoi_log_sd` = **0.936** (job 258713;
0.940 on the flagship twin). Because the arithmetic collapse multiplies a lognormal estimate
by `exp(σ²/2)`, and the Cal band is ±40% relative, any leg with σ > √(2 ln 1.4) = **0.820**
is moved across the band by the *reporting statistic alone*. The North Atlantic is the only
leg anywhere in the corpus that exceeds it, and it is the whole of the flagship trio's
25/50 → 12/50 halving (natl `scav_rat` 19 → 5 on the twin, 37 → 7 on 258713).

So the hypothesis under test is precise: **is that σ = 0.94 the signature of averaging a
per-cell field across biogeochemical regimes that the rectangle happens to straddle?**

If yes, provinces are not a tidiness exercise — they are the fix for the number that halves
the headline.

---

## 2. (a) The box straddles provinces. Decisively.

Longhurst v4 polygons intersected with the box `lon[-40,-10] lat[50,65]`, areas taken in a
Lambert azimuthal equal-area projection centred on the box (in raw degrees the polar rows
would be overweighted by ~2× at this latitude):

| province | share of box area | biome | description |
|---|---:|---|---|
| `NADR` | **41.48%** | Westerlies | N. Atlantic Drift |
| `ARCT` | **30.53%** | Polar | Atlantic Arctic |
| `SARC` | **19.05%** | Polar | Atlantic Subarctic |
| `BPLR` | 3.04% | Polar | Boreal Polar |
| `NECS` | 2.80% | Coastal | NE Atlantic Shelves |

**Effective number of provinces (inverse Simpson) = 3.10.** No province holds a majority.
The box mixes **three of Longhurst's four top-level biomes** — Westerlies, Polar and Coastal.
On 1° cell centres: 169 `NADR`, 149 `ARCT`, 93 `SARC`, 22 `BPLR`, 7 `NECS`, 10 land.

The literature agrees this is a genuinely awkward place to draw a rectangle: the Charlie-Gibbs
Fracture Zone at the subpolar front, at 52°N on the Mid-Atlantic Ridge — **inside the box** —
is described as the junction of `NADR`, `ARCT` and `SARC`.

So Jon's geographic instinct is correct, and it is the sharpest case of the three AOIs.

## 3. …and it still does not explain the dispersion

Two independent checks, both on numbers already recorded.

**Check 1 — province heterogeneity does not order σ across the three AOIs.**

| AOI | effective provinces | provinces | `log_sd` (`scav_rat`) |
|---|---:|---|---:|
| `natlsubpolar` | **3.10** | NADR/ARCT/SARC/BPLR/NECS | **0.940** |
| `eqpac` | 2.70 | PEQD 46.7 / PNEC 34.1 / NPTG 19.4 | 0.245 |
| `southernoceanpac` | 1.53 | ANTA 77.9 / SANT 22.5 | 0.379 |

`natlsubpolar` tops both rankings, which is consistent. But `eqpac` and `southernoceanpac`
are **inverted**: `eqpac` mixes nearly twice the effective provinces of `southernoceanpac`
(2.70 vs 1.53) and carries *less* than two-thirds its dispersion (0.245 vs 0.379). With n = 3
this is weak on its own — it is reported as one strand, not the argument.

**Check 2 — the same box, with geography held exactly fixed, changes σ by 3.5×.**

This is the argument.

| configuration | box | parameterisation | `log_sd` |
|---|---|---|---:|
| 3-AOI flagship twin, `sopac` leg | `southernoceanpac` | per-cell | **0.379** |
| single-AOI `so_only` (n=50) | `southernoceanpac`, *identical box* | per-cell | **1.310** |

The geography of `southernoceanpac` is a constant across those two rows. Its province
composition is a constant. Its per-cell dispersion changes by a factor of **3.5**.

**A quantity that takes two very different values on the same polygon is not a property of
that polygon.** σ is substantially a property of the fit configuration. Redrawing the boundary
is therefore not predicted to control it, and the 25 → 12 halving cannot be attributed to
province straddling on the evidence we have.

> **Excluded from this argument on purpose.** The pooler audit also records `log_sd` = 0.000
> for the observations-only arms in all three basins, which looks like a third point on the
> same box. It is not admissible here: those runs are `gs_obsonly`, i.e. `GLOBAL_SCALAR=1`,
> which *replaces the per-cell head with a single scalar per AOI*
> (`run_v3.0_joint_multi_aoi.py:538-543`). σ = 0 is then true by construction and carries no
> information about geography. An earlier draft of this note used it as evidence; it should
> not have.

This does not say provinces are a bad idea. It says the *specific* justification — "provinces
will collapse the dispersion that halves the trio" — is unsupported, and a re-fit sold on that
basis would probably disappoint.

## 4. Why the direct test could not be run, and what it would cost

The obvious test is to regress the per-cell recovered `scav_rat` field on province label
inside `natlsubpolar`. **It cannot be run on any artifact we hold.**

`scripts/run_v3.0_joint_multi_aoi.py:2667-2712` computes the per-cell tensor `params_b`,
collapses it to arithmetic / geometric / median means and a scalar `log_sd`, and **writes only
the collapses**. The per-cell field is never persisted. There is no `state_dict()` save
anywhere in the runner, so the trained per-cell network from job 258713 is gone too.

σ = 0.936 is therefore a spread magnitude with **no spatial structure attached to it**, and no
amount of re-analysis will attach any. The test needs a re-fit — which, as noted when the
question was raised, must carry its box control in the *same* submission (cross-job comparison
is not defensible here: older artifacts leave the deciding keys `<absent>`, and absent is
unknown).

**Cheap fix worth doing regardless of the province decision:** persist the per-cell parameter
field, or at least the network `state_dict`, for one seed per arm. It is a few MB and it
converts "σ is 0.94" into a spatial question that can be asked later without spending a job.

---

## 5. (b) GP16 is three provinces, and the working guess is half right

GP16 (R/V *Thomas G. Thompson*, Oct–Dec 2013) ran from the Peru margin west to Tahiti along a
line falling between 10 and 15°S, crossing the East Pacific Rise plume near 12°S.

Province along exactly 12°S, scanned at 0.5° of longitude:

| longitude span | province |
|---|---|
| 155°W → 90°W | **`SPSG`** — S. Pacific Subtropical Gyre |
| 90°W → 80°W | **`PEQD`** — Pacific Equatorial Divergence |
| 80°W → 77°W | **`CHIL`** — Chile-Peru Current Coastal |

The working guess was that the equatorial divergence province stops north of 12°S. **It is
correct in the central Pacific and wrong in the east**, because PEQD's southern boundary is
not zonal — it is a staircase that dips south along the Peru upwelling tongue:

| longitude | PEQD southern limit |
|---|---:|
| 140°W → 108°W | −7.25° |
| 104°W → 92°W | −11.25° |
| 88°W → 80°W | **−15.25°** |

So at 12°S the transect *does* enter PEQD, but only east of 90°W.

Counting the actual observations rather than the line — GEOTRACES IDP2025 `Fe_D_CONC` at QC
1/2, in the corridor 9–16°S, 155–70°W:

| province | stations | samples |
|---|---:|---:|
| `SPSG` | 39 | 767 |
| `CHIL` | 35 | 283 |
| `PEQD` | **18** | **156** |
| **total** | **92** | **1,206** |

**Zero of those 92 stations fall inside the current `eqpac` box.** The box is 5°S–15°N,
160–110°W; GP16 misses it in latitude everywhere, and the stretch where GP16 *is* in PEQD
(east of 90°W) is also outside the box in longitude. The box and the transect sample PEQD in
two disjoint sectors.

Redefining `eqpac` as the `PEQD` province would pick up those 18 stations / 156 samples, and
take the province's total dissolved-Fe coverage from the box's 29 stations / 490 samples to
**43 / 565**.

---

## 6. The result that was not being looked for: iron coverage

The same overlay, run against GEOTRACES IDP2025, says the boxes are leaving most of the
available iron on the table — and by far the worst case is the one basin where `scav_rat` is
established.

| AOI | box: stations / samples | dominant province: stations / samples |
|---|---|---|
| `southernoceanpac` | **15 / 204** | `ANTA` **125 / 1,558** |
| `eqpac` | 29 / 490 | `PEQD` 43 / 565 |
| `natlsubpolar` | 13 / 237 | `NADR` 11 / 234 |

The `southernoceanpac` box captures **12% of ANTA's dissolved-Fe stations**. `scav_rat` is
locally identifiable there and nowhere else (30/50 vs untrained 0/50, P = 3.15e-24, and 49/50
under the geometric collapse), and it is the sole binding leg of the trio headline. An **8.3×**
increase in the iron constraint on that basin is a much more direct lever than anything the
dispersion argument offered.

**Two honest caveats.** (1) `ANTA` is circumpolar and therefore a far larger domain than the
box — some of that factor is simply more area, with a proportionate cost in cells and compute,
so this is not free. (2) `natlsubpolar` shows the trade can also go the *wrong* way: the box's
dominant province `NADR` is iron-poorer than the box itself (11 vs 13 stations). Province
membership and data density are independent, and have to be checked per AOI rather than assumed.

---

## 7. What this changes

- **Do not sell a province re-fit as the fix for the North Atlantic dispersion.** §3 shows σ is
  configuration-dependent, not geographic. If the re-fit runs, its box control is mandatory and
  its pre-registered expectation should be "σ roughly unchanged".
- **Do consider `ANTA` for the Southern Ocean**, on the iron-coverage argument in §6, which is
  independent of everything in §3 and is the strongest thing the overlay turned up.
- **Persist the per-cell field.** The question in §4 is currently unanswerable for want of a
  few MB per run.
- **GP16 is a three-province transect**, majority `SPSG`. Quote it that way rather than as
  "the equatorial Pacific".

## 8. Provenance

- Polygons: Flanders Marine Institute (2009), *Longhurst Provinces*,
  https://www.marineregions.org/, after Longhurst (1998), *Ecological Geography of the Sea*.
  Fetched from the Marine Regions WFS layer `MarineRegions:longhurst`.
  **The request must be WFS 1.0.0** — 1.1.0 flips the EPSG:4326 axis order to lat,lon and
  returns Indian Ocean provinces for a North Atlantic bbox without erroring. That trap fired
  once during this work and the wrong answer looked entirely plausible.
- Iron: GEOTRACES IDP2025 `Fe_D_CONC`, QC flags 1–2, via `darwindiff.geotraces_loader`.
  1,914 stations / 23,090 good samples globally.
- Dispersion and recovery counts: [`2026-08-04_pooler_audit_the_flagship_trio_halves.md`](2026-08-04_pooler_audit_the_flagship_trio_halves.md).
