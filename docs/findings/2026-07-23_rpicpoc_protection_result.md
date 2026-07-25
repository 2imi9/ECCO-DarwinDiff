# R_PICPOC-protection grid — result (2026-07-23, B200)

**Bottom line: there is now a jointly-robust, shippable operating point — `geo1 + MLD channel +
DANIELS_RPICPOC_W=8` recovers {`alpfe`, `R_PICPOC`, `diatomgraz`} at 10/10 / 10/10 / 10/10
simultaneously** (`verify_run` exit 0, R_PICPOC per-AOI with NO straddle flag). The MLD-vs-R_PICPOC
trade-off from the covariate finding was a **fixable loss-weighting artifact** — up-weighting the real
Daniels calcite anchor lifts R_PICPOC cleanly (5→9→10/10) with no over-constraint tax. Separately,
**wind (and SSS / pCO₂ / CO₂-flux) carry a GENUINE calcite confound**: no anchor weight rescues R_PICPOC
under them, so MLD's uniqueness is mechanistic, not luck. `scav_rat` stays 0/10 **in this
anchors-only lineage**, which zeroes the Darwin-pattern term it needs; in the flagship geo1 config it
recovers 26/50 per-AOI at 2000 epochs and 41/50 at 4000, so it is largely optimization-limited, with
only eqpac (6/50) genuinely information-limited.

Direction chosen via the `next-direction-research` workflow; this converts the covariate finding's soft
spot ("MLD only, R_PICPOC 5/10 = a coin flip") into a numerically-defended config. Jobs 183329
(protection grid) + 183299 (single-covariate matrix), n=10 seeds, 2000 epochs, geo1 anchors-only,
all `verify_run` exit 0. Grading = per-AOI ≥2-of-3 Cal+ (≤40% off Carroll).

## The R_PICPOC weight ladder — the trade-off is a loss-weighting artifact

| config | alpfe | scav_rat | **R_PICPOC (per-AOI)** | R_PICPOC median | diatomgraz | straddle? |
|---|---|---|---|---|---|---|
| `mld` (DAN=1, ref) | 10/10 | 0/10 | **5/10** | 0.059 | 10/10 | — |
| `mld_dan3` | 10/10 | 0/10 | **9/10** | 0.054 | 10/10 | 1 seed straddles |
| **`mld_dan8`** | **10/10** | 0/10 | **10/10** | **0.051** | **10/10** | **none — clean** |

Carroll R_PICPOC = 0.0425. At DAN=8 the median is 0.051 (1.2×, in-band, not over-constrained out the
high side), and `alpfe` median stays 0.99 (no anchor-weight tax bleeding into the iron leg). So the
stronger real-calcite anchor simply supplies the per-cell R_PICPOC signal the extra MLD channel had
diluted — a weighting fix, not a new degeneracy.

## Wind is a real calcite confound (not DINN overfitting)

| config | R_PICPOC (per-AOI) | median | reading |
|---|---|---|---|
| `mld_wind` (DAN=1, ref) | 0/10 | — | wind breaks R_PICPOC |
| `mld_wind_dan3` | 0/10 | 0.21 | 3× anchor does NOT rescue |
| `mld_wind_dan8` | 0/10 | 0.21 | **8× anchor does NOT rescue** |

Under wind, R_PICPOC is stuck at 0/10 with the median pinned at ~0.21 (5× Carroll) at **every** anchor
weight. So up-weighting cannot overcome it — wind carries a genuine confound with the calcite field.
**Decisive mechanism answer:** the wind break is NOT a tunable loss-weighting artifact; wind should be
excluded from the shipped config on mechanistic grounds.

## Single-covariate matrix — the confound is generic to carbonate/salinity channels

| covariate (alone) | diatomgraz | R_PICPOC | reading |
|---|---|---|---|
| MLD | 10/10 | 5/10 (→10/10 with DAN=8) | **safe** (mixing signal, non-carbonate) |
| wind | 10/10 | 0/10 | breaks R_PICPOC |
| SSS | 7/10 | 0/10 | breaks R_PICPOC |
| pCO₂atm | 8/10 | 3/10 | breaks R_PICPOC (also nudges alpfe median to 0.91) |
| CO₂-flux | 10/10 | 0/10 | breaks R_PICPOC |

Every carbonate/salinity-linked covariate (wind, SSS, pCO₂, CO₂-flux) breaks R_PICPOC; **MLD is uniquely
safe** because it carries mixing information, not carbonate information. Several covariates recover
diatomgraz (MLD, wind, CO₂-flux 10/10), but only MLD does so without the calcite confound.

## Recommended operating point (for the manuscript)

**`geo1` + `MLD_CHANNEL=1` + `DANIELS_RPICPOC_W=8`** → **{alpfe, R_PICPOC, diatomgraz} = 10/10 each**,
`verify_run` exit 0, R_PICPOC clean per-AOI (no straddle). This is the robust **3-of-4-observable**
config; `scav_rat` is the lone holdout **in this config** — it recovers in the flagship geo1 run (26/50
per-AOI at 2000 epochs, 41/50 at 4000), so it is the equatorial Pacific (6/50), not `scav_rat` globally,
that still needs the real ²³⁴Th/²¹⁰Po sink anchor (Phase 2). The growth pair stays unobservable by
construction.

## Honest caveats

- `diatomgraz` recovery is still against the **POSi biogenic-silica diagnostic** target (input-limited,
  not yet shown structural). This experiment fixes the *R_PICPOC co-recovery*, not the diatomgraz
  structural question — the profile-likelihood-with-MLD remains the pending structural check.
- `scav_rat`'s apparent 10/10 in `verify_run`'s per-param line is the **joint cell-weighted** metric,
  which straddles; the honest **per-AOI ≥2-of-3 grader gives 0/10**. scav_rat is unmoved (expected).
- R_PICPOC at DAN>8 risks over-constraining out the high side of the band; DAN=8 is the clean point
  (no straddle). Do not push the anchor weight higher without re-checking the straddle flag.

Artifacts: `/scratch/qi_zim_neu/covar_protect/n10/arm{0..3}` + `/scratch/qi_zim_neu/covar2/n10/arm{0..2}`
(B200, all `verify_run` exit 0). Direction note: `docs/research_notes/2026-07-22_next_direction_rpicpoc_protection.md`.
