# Iron lever (E2 hunt): particulate:dissolved partitioning breaks the scavenging-rate wall

*Self-twin capacity result, 2026-07-10, local CPU. Lever 1 of the positive-E2 hunt (D2).*

## Result

The iron **information wall** — dissolved-Fe concentration constrains only the source/sink
*combination* `alpfe/scav_rat`, not the scavenging *rate* — is a property of the **dissolved
observable**, not a fundamental limit. Adding the **particulate:dissolved partitioning ratio**
(`pFe/DFe`) identifies `scav_rat` where concentration is flat.

On the same real equatorial-Pacific observing footprint and prescribed div-free transport as the
wall demo (`scripts/iron_scav_rat_profile.py`), a self-twin (alpfe, scav_rat) sweep with the
scav_rat likelihood profiled over alpfe:

| observable | scav_rat unidentifiable band | shape |
|---|---|---|
| dissolved DFe only | **19×** (1.0e-7 – 1.9e-6) | flat ridge (the wall) |
| partitioning `pFe/DFe` | **~1×** (single grid point at the truth ~7e-7) | sharp well, ~14× tighter |

The partitioning profile is a deep, curved well (misfit 0.014 at the truth → 6.1 at 1e-5, 1.0 at
1e-7), minimized at the true Carroll `scav_rat` — identifiable *and* unbiased. `scripts/iron_partitioning_scout.py`.

## Why it works

The scavenging **sink flux** is `scav_rat·DFe·POC`, which becomes particulate iron. The
particulate standing stock (sinking at `W_SINK`) is `pFe ≈ scav_rat·DFe·POC / W_SINK`, so the
**partitioning ratio `pFe/DFe ≈ scav_rat·POC / W_SINK` has no direct `alpfe` dependence** — it
lies along the exact axis the dissolved-only likelihood is flat along. Dissolved concentration
sees `alpfe/scav_rat` (equifinal); the partitioning ratio sees `scav_rat` directly. The
numerical run confirms POC's weak dependence on `scav_rat` (via iron limitation of growth) does
**not** spoil the identification.

## What this changes

The identifiability map's iron entry was "observability-limited — DFe concentration is a
low-information projection of the rate, so more iron data won't help." That stands **for the
dissolved observable**, but the wall is **breakable with a different, real observable**:
GEOTRACES IDP2025 measures total particulate iron (`Fe_TP_CONC`) alongside dissolved
(`Fe_D_CONC`) at co-located cells. So there is a concrete **positive-E2 lever**: fit the
scavenging closure to the real partitioning ratio through transport, held-out scored.

## Honest scope + the caveat that gates a real E2

- **Self-twin capacity result**, not a real-data recovery: it shows the observable *can* identify
  the rate in principle, on the real footprint/transport, not that real GEOTRACES Fe_TP recovers
  it.
- **The load-bearing caveat:** the box's `pFe` is *only* scavenged particulate iron, but measured
  `Fe_TP_CONC` also includes **biogenic** particulate Fe (cellular uptake, `Fe_CELL_CONC`) and
  **lithogenic** particles (undissolved dust). A real E2 must either (a) use a scavenged-Fe proxy
  (e.g. `Fe_TP` minus biogenic/lithogenic estimates, or the labile/refractory split
  `Fe_TPL`/`Fe_TPR`), or (b) model all particulate-Fe sources in the closure. This contamination,
  not the identifiability, is now the binding risk.
- The coarse 13×15 grid makes the partitioning band read as a single point; a finer grid would
  give the true (still-much-tighter-than-19×) width. The 14× tightening is robust to grid.

## Real-data coverage gate (checked 2026-07-10)

The identifiability is there in principle; the **observing coverage is the binding limit for a
real E2 now.** In GEOTRACES IDP2025, dissolved Fe is dense (`Fe_D_CONC` n = 23,912) but
co-located *particulate* Fe is sparse, and co-located *pairs* sparser still:

| quantity | global | surface (≤50 m), co-located with Fe_D |
|---|---|---|
| `Fe_TP_CONC` (total particulate) | 1,784 | **94** |
| `Fe_TPL_CONC` (labile particulate — the scavenged-Fe proxy) | 1,337 | **150** |
| co-located on eqpac footprint | — | **4** (natl 0, SO 0) |

The real partitioning ratio, where measured, does vary widely (`Fe_TP/Fe_D` surface: n = 79,
median 2.56, p10–p90 = 0.37–11.9, **log-span 2.59 dex** — far wider than calcite's Ω), so the
signal is there; there simply aren't enough co-located pairs on any single AOI footprint yet.
So this lever mirrors the map's theme: **identifiable in principle, observing-coverage-limited in
practice.** The actionable recommendation is an *observing-system* one — the labile particulate
fraction `Fe_TPL` (150 surface pairs, and the right scavenged-Fe proxy) is the best available
target, and depth-resolved (not surface-only) scoring would add more pairs. A well-powered real E2
needs either the global `Fe_TPL`/`Fe_D` set (not one AOI) or more co-located particulate+dissolved
Fe coverage.

## Next (a real E2 on this lever)

1. Build the real partitioning target from GEOTRACES: co-located `Fe_TP_CONC`/`Fe_D_CONC` on the
   eqpac footprint, with a scavenged-Fe correction (start with the labile particulate `Fe_TPL`,
   which excludes refractory lithogenic Fe).
2. Fit `scav_rat` (or a scavenging closure) through transport to that target, held-out scored with
   an env-regime split and a K_num control — the standard E2 protocol.
3. If it clears held-out R² > 0, this is the first genuine positive E2, and it converts the iron
   entry of the map from "walled" to "constrained by the right observable."
