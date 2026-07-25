# Emulator 1-step error is SPATIALLY FLAT — the geometry directions are closed by evidence (2026-07-21)

The decisive test the Caltech neural-operator scan converged on
(`docs/findings/2026-07-21_caltech_neural_operator_scan.md`): does the emulator's one-step error
concentrate near coastlines / domain edges, or is it spatially uniform? A fresh FNO2d (300 ep, k8,
log-space, Δt-scaled) was trained per native-grid regional cube (cluster job `8524645`,
`scripts/emulator_err_geometry.py`), and its per-cell 1-step error was regressed against distance to the
nearest land-or-edge cell.

## Result — flat in all four regions

| region | corr(err, coastal proximity) | mean err @ dist 1-2 | mean err @ dist 2-5 | verdict |
|---|---|---|---|---|
| **natlsubpolar** (the ~5×-low bloom) | **−0.033** | 0.427 | 0.406 | SPATIALLY-FLAT |
| npac | −0.008 | 0.414 | 0.417 | SPATIALLY-FLAT |
| sopac | +0.018 | 0.292 | 0.288 | SPATIALLY-FLAT |
| midatl | −0.008 | 0.256 | 0.258 | SPATIALLY-FLAT |

Coastal cells and near-coastal cells carry essentially identical error in every region; the correlation
with coastal proximity is ~0 everywhere. (`coastal_distance` measures distance to nearest land **or
domain edge**, so this covers the periodicity/edge artifact too, not just interior coastlines.)

## What this closes

1. **The structural 1-step ceiling is information-limited, confirmed on data.** The error is not
   explained by geometry — so a geometry-aware operator has nothing to fix here. **GINO / SFNO / CoDA-NO
   drop from "MEDIUM, test first" to dead-end-by-evidence** for the regional emulators. This is the
   evidence the scan asked for, and it points the same way as our capacity (+0.007) and diffusion (~0)
   nulls.
2. **It also refutes my own highest-EV suggestion — the pad+mask FFT fix.** Because the distance metric
   includes the domain edge, the flat result means the periodicity artifact the pad+mask targets is not
   costing measurable error either. Both the expensive geometry operators and the cheap FFT patch are
   closed by the same test. Honest outcome: the ceiling is not a boundary/periodicity artifact.
3. **The N-Atlantic chlorophyll bias is genuine, not a coastal artifact.** natlsubpolar carries the
   highest error of the four regions (0.43) but it is flat in coastal proximity (corr −0.033) — so the
   ~5×-low bloom bias is a bloom-dynamics/physics limit, not a discretization artifact. The headline chl
   finding stands as reported; this rules out the write-up risk the scan flagged.

## Caveats — what is NOT tested

- **No deep interior.** The regional native tiles are small enough that every ocean cell sits within ~5
  cells of land/edge (bands 5-10 and 10-inf are empty, so the coastal/interior ratio is undefined). The
  flat result holds across the 1-5 cell range that covers the whole tile, but a "deep ocean interior vs
  coast" contrast would need a larger domain.
- **Cube-face seams are absent from contiguous regional tiles.** The one geometry artifact this cannot
  test is the cubed-sphere face seam, which appears only in a **global** LLC270 cube. That remains a
  narrower, global-only open question — but it does not affect the regional emulators evaluated here,
  and staging a global cube is a separate, larger task.

**Bottom line:** for the emulator we actually have, the 1-step error is uniform in space. The horizon
ceiling is an information limit, not an architecture or discretization limit. Do not build SFNO/GINO or
the pad+mask fix on this evidence; the lever, if one exists, is more information (signal/observations),
not a better operator.
