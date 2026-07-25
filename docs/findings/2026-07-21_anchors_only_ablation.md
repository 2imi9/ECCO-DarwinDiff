# Anchors-only ablation — alpfe & R_PICPOC are anchor-driven; scav_rat is pattern-assisted (2026-07-21)

Answers red-team rebuttal_diff #4 second half: *the geo1 loss is dominated by z-scored Darwin-output
pattern terms (gap-(a) calls them non-fidelity); only the anchor-off→fails direction was shown. Drop the
pattern terms, keep the real anchors, and report whether the trio survives.*

**Setup.** geo1 flagship config with the new `DARWIN_PATTERN_W=0` lever plus `POC_SUB_W=0`,
`CHL1_W_EXTRA=0` — i.e. **every z-scored Darwin-output term off** (base FeT/Chl1-5/POC/PIC/DIC/ALK/CO2
block, POC-subsurface, extra-Chl1). Kept: real GEOTRACES iron (surface + subsurface), real Daniels calcite
anchor, and the PINN iron-budget physics term. n=10 seeds, 2000 epochs, local 5090; `verify_run` exit 0
(10/10 seeds). Run `D:/runs/anch_pinn`.

## Result — the trio splits cleanly

| param | anchors-only (n=10) cell-wtd / per-AOI | flagship geo1 (n=50) cell-wtd / per-AOI |
|---|---|---|
| **alpfe** | 10/10 / **10/10** | 49/50 / 49/50 |
| **scav_rat** | 8/10 / **0/10** | 36/50 / 25/50 |
| **R_PICPOC** | 7/10 / 6/10 | 46/50 / 50/50 |
| **JOINT trio** | 5/10 / **0/10** | 33/50 / 25/50 |

## Interpretation

- **alpfe and R_PICPOC survive anchors-only.** alpfe recovers **10/10 per-AOI** on the real GEOTRACES
  iron anchor alone; R_PICPOC recovers 6/10 per-AOI (lands at ~0.05, the real Daniels value) on the
  Daniels anchor alone. With *zero* Darwin-output pattern terms in the loss, both anchor-pinned params
  still recover — **direct evidence that their recovery is anchor-driven, not pattern-matching against
  Darwin's own fields.** This is the strongest positive support yet for the paper's central claim
  (identifiability comes from real absolute anchors, not the box's reproduction of Darwin structure).
- **scav_rat's per-AOI recovery collapses to 0/10** (from 25/50 in the flagship), while its cell-weighted
  count stays high (8/10) — the classic straddle. So scav_rat's per-AOI identifiability is **partially
  pattern-assisted**: the Darwin-output terms supply constraint the real iron anchor alone does not. This
  is consistent with scav_rat being the weakest, most-confounded leg (the eqpac-alone ablation showed it
  is region-dependent and weakest in eqpac — the Southern Ocean is a canonical HNLC region too).
- **The joint trio drops to 0/10 per-AOI** because scav_rat is the binding leg (as in the flagship, where
  the joint equals scav_rat's 25/50).

## For the manuscript

The honest, sharpened statement: **alpfe and R_PICPOC recovery is anchor-driven and survives with all
Darwin-pattern terms removed; scav_rat's per-AOI recovery is partially pattern-assisted and collapses
without them.** This *strengthens* the paper for two of the three trio params (they pass the strictest
pattern-off test) while being precise about the third — exactly the decomposition the identifiability
thesis predicts.

## Caveats

- PINN physics (iron-budget steady-state) was kept on — it is not a Darwin-output pattern term, but it
  does constrain alpfe/scav_rat, so a PINN-off arm would further isolate the pure anchor contribution.
- n=10 (the flagship is n=50); the separation (alpfe 10/10 vs scav_rat 0/10 per-AOI) is clean enough for
  the qualitative claim, but an n=50 anchors-only would firm up the counts.
