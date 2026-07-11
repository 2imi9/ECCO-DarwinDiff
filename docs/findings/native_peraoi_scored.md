# Native per-AOI recovery ensemble — scored (5 seeds, LLC270)

**Source:** Explorer H200 job `8266735` (native_peraoi, 1500 ep, 3-AOI joint:
eqpac / natlsubpolar / southernoceanpac). Raw per-seed JSONs in
`docs/findings/native_peraoi/*.json`. **Local-only — not committed to GitHub.**

**Trust gate:** `scripts/verify_run.py` → **exit 0 (VERIFIED & COMPLETE)**, 5/5 seeds,
no discrepancies (every band re-derived from raw `joint_recovered` vs canonical Carroll,
stored bands cross-checked, `n_cal_grade` cross-checked). Honesty flag raised: `LOW_N (n=5)` —
this is a corroborating ensemble, **not headline-grade**; seed variance is reported below.

## Headline

- **mean k-of-6 = 3.4** · **k by seed = [3, 4, 3, 4, 3]** · **no seed reached 5/6 or 6/6** ·
  max = 4/6 (2 of 5 seeds).
- **iron pair joint Cal+ = 1/5** · total Excellents = 1.

At native resolution the ensemble does **not** produce robust joint recovery — consistent with,
and corroborating, the per-parameter identifiability map
(`identifiability_map_1deg_vs_native.md`): native sparse obs inflate every CRLB (~10×), and the
observing-system limits, not the method, cap what recovers.

## Per-parameter (joint cell-weighted, across 5 seeds)

| param | Carroll | mean recovered | CV% | mean rel-offset | Cal+/5 | reading |
|---|---|---|---|---|---|---|
| `alpfe` | 0.9283 | 0.593 | 2.3 | 0.361 | **5/5** | recovers, but **SO-driven** (see below) — matches "iron pair best-constrained in the SO at native" |
| `scav_rat` | 6.03e-7 | 1.04e-6 | 20.7 | 0.729 | **1/5** | observability wall — fails as expected |
| `Smallgrow` | 0.661 | 0.853 | 18.1 | 0.346 | 2/5 | structurally unobservable (biomass-weighted-mean coincidence, seed-unstable) |
| `Biggrow` | 0.4315 | 0.535 | 35.0 | 0.370 | 4/5 | structurally unobservable; high CV confirms it is not a real constraint |
| `diatomgraz` | 0.83 | 0.854 | 13.8 | 0.132 | **5/5** | **artifact, not a constraint** — flat profile / residual-weighting (see below) |
| `R_PICPOC` | 0.04245 | 0.604 | 4.8 | **13.2** | **0/5** | native null — drifts hard everywhere (Ω-modulation unrecoverable; SO CRLB → 77k) |

## Adversarial notes (do not over-read the green cells)

- **`alpfe` 5/5 is Southern-Ocean-driven, not a uniform recovery.** Per-AOI across seeds:
  eqpac ≈ 0.05, natlsubpolar ≈ 0.06–0.25, **southernoceanpac ≈ 1.0** (≈ Carroll 0.928). The joint
  cell-weighted mean (0.593, offset 0.36 → Cal-grade) lands in-band because the SO AOI has the most
  cells (21 120 vs 9 750 / 7 939) and pulls the weighted mean up. This is the *honest* SO constraint
  the identifiability map predicts — not a clean 3-AOI recovery. eqpac/natl alpfe are far below Carroll.
- **`diatomgraz` 5/5 is the known residual-weighting artifact, not evidence of identifiability.**
  Its profile likelihood is flat (structurally non-identifiable per the Fisher/profile diagnostic);
  it sits near Carroll by default rather than being constrained by the fit. Its low CRLB in the map is
  the same artifact. **Do not report diatomgraz as recovered.**
- **`R_PICPOC` 0/5 is decisive at native.** Per-AOI the SO value pins ≈ 1.05 (offset ~24×), eqpac
  collapses to ~0.005; there is no resolution at which the Ω-driven ratio recovers at native — the
  native SO CRLB (→ 77k) says the information is not in the observations.
- **Growth pair `Smallgrow`/`Biggrow`** flip between seeds (CV 18 % / 35 %); their occasional Cal+
  bands are the biomass-weighted-mean coincidence, not a separable per-parameter constraint.

## Bottom line

The independent native ensemble **corroborates the identifiability-limits map**: only `alpfe`
recovers robustly (and only because the Southern Ocean carries the iron signal), `scav_rat` and
`R_PICPOC` fail as the observing-system analysis predicts, and the growth pair + `diatomgraz` "hits"
are the known unobservable / artifact bands. No 6/6, no 5/6, iron pair joint 1/5. The binding
constraint at native is the observing system, exactly as at 1°.
