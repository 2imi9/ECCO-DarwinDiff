# tan φ measured — the κ² term is vacuous, and eqpac's iron residual is maximal

**Date:** 2026-07-28 · **Loop Q4** · **Settles:** §1.2 of `2026-07-27_hierarchical_inversion_design.md`
· **Artifact:** `docs/findings/residual_angle_flagship.json` · **Script:** `scripts/analysis/residual_angle.py`

Measured at the flagship's recovered per-AOI parameters (n=50 mean), one forward pass, no refit.
`sin φ = ‖model − d‖ / ‖d‖`.

| AOI | block | n | sin φ | tan φ | φ° |
|---|---|---|---|---|---|
| eqpac | DIC | 1071 | 0.0233 | **0.023** | 1.34 |
| eqpac | ALK | 1071 | 0.0022 | **0.002** | 0.12 |
| natl | DIC | 484 | 0.0182 | 0.018 | 1.04 |
| natl | ALK | 484 | 0.0023 | 0.002 | 0.13 |
| sopac | DIC | 1296 | 0.0136 | 0.014 | 0.78 |
| sopac | ALK | 1296 | 0.0018 | 0.002 | 0.11 |
| sopac | **FeT** | 1296 | 0.554 | 0.665 | 33.6 |
| natl | **FeT** | 484 | 0.621 | 0.792 | 38.4 |
| **eqpac** | **FeT** | 1071 | **1.0000** | **≥7×10⁵** | **90.0** |
| all | POC | — | **1.0000** | **≥7×10⁵** | **90.0** |
| all | PIC | — | **1.0000** | **≥7×10⁵** | **90.0** |

## 1. The κ² tan φ channel is not a usable statement

The design document argued that because the 0-D box's structural error *is* `δJ`, Wedin's
`κ² tan φ` term activates and becomes "the project's dominant error channel". The measurement kills
that on both sides:

- Where residuals are **small** (DIC, ALK: tan φ ≈ 0.002–0.023) the κ² term is **dormant**. Plain κ
  governs.
- Where residuals are **large** (POC, PIC, eqpac FeT: sin φ → 1) the term is ~10⁵–10⁶ and the bound
  evaluates to ≫100% relative error — **vacuous**, exactly as the adversarial critic said. A bound
  that predicts unbounded error predicts nothing.

There is **no regime** in which "κ² tan φ is the dominant error channel" is informative. §1.2 should
be withdrawn, not merely caveated.

## 2. The interesting result: eqpac's iron block is the outlier

`FeT` is the only block that varies across basins, and the variation is stark:

    sopac 0.554  ·  natl 0.621  ·  eqpac 1.0000

**The basin where `scav_rat` cannot be recovered is the basin where the box cannot reproduce the
iron field at all.** eqpac recovers `scav_rat` 7/50, and stays at 6/50 even at 4000 epochs.

That suggests a different diagnosis from the one we have been carrying. We have framed eqpac as
*information-limited* — the observations do not constrain the parameter. This says the **forward
model is misspecified there**: the residual is as large as the data, so no parameter value makes the
box match Darwin's equatorial iron. Fitting a parameter through a wrong forward map is not an
identifiability problem, and more or better observations would not fix it.

It is also consistent with the corrected κ arithmetic, where eqpac was the one basin whose implied
error **exceeded** the worst-case κ bound — a signature of bias, not amplification.

## 3. Caveats — this is a diagnostic, not a verdict

- **sin φ = 1.0000 is clipped.** The code caps at 1 − 1e-12, so those entries mean ‖r‖ ≥ ‖d‖, not
  exactly 1. POC/PIC/eqpac-FeT are "residual at least as large as the signal", nothing finer.
- **POC and PIC are saturated in every AOI**, so they carry no basin discrimination here and may
  reflect a systematic offset between the box's steady state and Darwin's, rather than a per-basin
  property. The known 0-D-vs-3-D surrogate gap is the obvious candidate.
- **This is not the training loss.** It compares the box against cached Darwin fields on the shared
  grid; the flagship loss also whitens per block and includes real anchors (GEOTRACES, Daniels)
  which are not evaluated here. tan φ *of the actual loss* could differ.
- Uniform per-AOI parameter vectors are used, matching `integrator_stationarity_check.py`.

## 4. What to do next

1. **Withdraw §1.2** of the hierarchical inversion design doc.
2. **Test the misspecification reading**: if eqpac iron is model-error-limited rather than
   information-limited, then the TPOSE dissolved-Fe comparison (`d59d1d0`) should show Darwin's own
   equatorial iron differing from an independent estimate. That is now a *prediction*, which is a
   much stronger test than a consistency check.
3. Re-run this against the **actual whitened loss blocks** before it goes in a paper.
