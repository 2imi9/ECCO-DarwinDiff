# B-SOSE, from the actual file: the extent claim was wrong, and the first iron field comparison

**Date:** 2026-07-29 · **Artifacts:** `D:/bsose/bsose_i105_2008to2012_monthly_Fe.nc` (4.03 GB),
`D:/bsose/grid.nc` (427 MB) · **Corrects:** `2026-07-28_regional_product_extents.md`

The B-SOSE monthly iron download finished, so the product's extent could finally be read off the
file instead of off a solution page. Two results: a committed claim is wrong, and the field
comparison it was scoping is now actually possible.

---

## 1. The extent claim is wrong — corrected against the distributed grid

`2026-07-28_regional_product_extents.md` says B-SOSE spans **"equator to 78°S"** and that its grid
**"telescopes out to Δy = 2° at the equator"**, and builds a caveat on it: that a B-SOSE comparison
in the tropics would be *coarser* than our own 1°. That note was itself filed as a correction.

The distributed iteration-105 grid says otherwise.

| | claimed | **measured from `grid.nc`** |
|---|---|---|
| northern limit | equator (0°) | **29.79°S** (`YC` max −29.789; `YG` max −29.945) |
| coarsest Δy | 2° at the equator | **0.300°**, at the northern edge |
| finest Δy | — | 0.070° |
| Δx | — | 0.333° uniform (1080 points) |
| shape | — | `NY=294, NX=1080, NZ=52` |

The data file agrees exactly: `TRAC06` on `(time=60, Z=52, YC=294, XC=1080)`, `YC` spanning
−77.97 to −29.79, monthly 2008-01-31 → 2012-12-30.

**So there is no 2° spacing anywhere in the product, and no equatorial data at all.** The coarsest
cell in iteration 105 is 0.300°, three times finer than our 1° grid, at the product's northern edge
at 29.8°S.

### What this changes

The table row

> `eqpac` southern half only (5°S–0°) · B-SOSE · partial · ≈2°, COARSER than our 1°

is wrong in every column: B-SOSE does not reach 5°S, so coverage is **none**, and the resolution
figure describes a grid region that does not exist in this iteration.

**The design conclusion is unchanged and the reason is now cleaner.** B-SOSE for
`southernoceanpac`, TPOSE for `eqpac` — not because B-SOSE is too coarse in the tropics, but
because it has no tropical data. The "would have silently degraded the comparison" warning in the
older note was aimed at a hazard that cannot occur.

**Scope of this correction.** It is a statement about the **distributed iteration-105 files**, which
are what any comparison would actually use. Whatever a solution page describes for other SOSE
configurations is not contradicted here — only its application to iter105 is.

---

## 2. First independent iron field comparison in the project

`southernoceanpac` (65–50°S, 180–100°W) sits **entirely inside** the B-SOSE domain: **86 lat rows ×
240 lon cols = 20,640 B-SOSE cells**, at 0.175° × 0.333° there, **100% finite** across all 60 months.

Comparing the 2008–2012 B-SOSE surface mean against Darwin's binned surface `FeT` on all
**21,120** ocean cells of our AOI cache:

| | median | IQR |
|---|---|---|
| Darwin `fet_binned` | **0.197 nM** | 0.178 – 0.217 |
| B-SOSE `TRAC06` (Z = −2.1 m) | **0.165 nM** | 0.153 – 0.176 |
| ratio Darwin / B-SOSE | **1.21** | 1.10 – 1.34 |

**Spatial correlation in log₁₀ space: r = 0.676** on matched cells.

**Robust to the matching scheme** — B-SOSE is much finer than our grid, so nearest-neighbour
sampling could have inflated the scatter. It does not:

| matching | B-SOSE median | ratio | log₁₀ r |
|---|---|---|---|
| nearest 1×1 | 0.165 | 1.211 | 0.676 |
| 3×3 mean | 0.165 | 1.211 | 0.677 |
| 7×7 mean | 0.165 | 1.210 | 0.681 |
| 15×15 mean (≈1° box) | 0.166 | 1.208 | 0.689 |

Two independently-constructed state estimates agree on Southern Ocean surface dissolved iron to
within ~20% in the median and correlate at r ≈ 0.68 spatially. Both land in the expected HNLC range.

### Do **not** read the 21% as a Darwin bias

Three things have to be settled first, and one of them is structural:

1. **The two tracers may not be the same quantity.** `TRAC06`'s `long_name` is *"Dissolved Inorganic
   Iron"*; Darwin's `FeT` is total dissolved iron. `2026-07-28_bling_comparability.md` established
   exactly this split — BLING partitions free Fe against a ligand while Darwin uses a total-DFe
   bilinear. If `TRAC06` is the free/inorganic pool rather than the total, **Darwin > B-SOSE is
   definitional, not a bias**, and the 21% carries no information. This is unverified and it is
   load-bearing.
2. **The units attribute is truncated in the file** — literally `'mol Fe/'`. `mol Fe/m³` is the
   MITgcm convention and it yields physically sensible values (0.165 nM), which corroborates the
   reading but does not prove it. A wrong unit here is a 10³ error, so it is called out rather than
   assumed away.
3. **Different time bases.** B-SOSE is a 2008–2012 mean; the Darwin target is a climatology. The
   depth levels differ too (B-SOSE top cell −2.1 m vs Darwin's surface layer).

**And B-SOSE is not truth.** It is a state estimate that assimilates observations. This is a
model-vs-model comparison between two semi-independent products — informative about structural
agreement, not a validation against data.

---

## What is now unblocked

The **Brix compensation test** — whether Darwin's Southern Ocean bias matches the compensation Brix
describes — needs exactly this field pair, and both halves are now in hand and verified against the
real files. It is a *field* comparison, so the BLING parameter-incomparability finding does not
block it.

**Do item 1 above first.** Whether `TRAC06` is total or free iron decides whether the 21% offset is
a result or an artifact of comparing two different pools.

## Still open (unchanged)

- ASTE-BGC extent and access.
- Whether B-SOSE iteration **134** exists. Only 105 is confirmed, and 105 is what is downloaded.
