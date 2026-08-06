# Pre-registration: compare the model's TIME MEAN to a time-mean target

**Date:** 2026-08-06 · **Submitted before results are seen.** · **Arms:** 3 × 50 seeds
(`tm_ctrl`, `tm_mean`, `tm_null`) · **Script:** `scripts/slurm/run_time_mean_loss.sbatch` ·
**Lever:** `TIME_MEAN_LOSS` · **Config:** `scripts/configs/flagship_geo1.sh`, sourced, with a
runtime assert on nine values including `N_STEPS=200` and `NB23_LR=5e-3`.

## 1. The defect being tested

The loss compares the model's **end state** at day 50 (`_integrate` returns the final state) to a
**time-mean** Darwin target (`time_mean(ds_aoi)`). Those are different objects in the time
dimension. It is the mechanical explanation for the window result of 2026-08-05: an endpoint on a
drifting trajectory is maximally sensitive to where you stop, a trajectory mean is not.

`TIME_MEAN_LOSS=1` accumulates a running mean over the window and compares that instead, making
the two sides the same kind of object. The PINN residual and the returned diagnostic state stay on
the endpoint, because a drift residual is a statement about an instant.

## 2. Pre-registered predictions

**P1 — the control reproduces the flagship.** `tm_ctrl` is the endpoint loss, and the lever was
verified **bitwise inert** when off: against the pre-change runner on a real eqpac bundle at
Carroll parameters, loss `0x1.2bbc580000000p+1` and state sum `0x1.244652b32aba4p+23` are
identical. So `tm_ctrl` should land at the flagship's trio, ~25/50 arithmetic and ~12/50
geometric. **If it does not, the submission is void** and the cause is environmental, not the
lever — the same failure mode that voided jobs 244487 and 255511.

**P2 — `scav_rat`'s window sensitivity falls.** This is the point of the change. Not measured by
this submission, which runs one window; it is the follow-on. Stated here so it cannot be
retro-fitted later.

**P3 — direction of the effect on `scav_rat` is NOT predicted.** A time mean over 0–50 days of a
monotonically drifting trajectory sits *above* the endpoint for a decreasing tracer, so the
recovered `scav_rat` should move **up** relative to the control, toward the band from below
(geometric median at `w200` is 0.538× Carroll, below the 0.60 edge). That argues for an increase
in counts. But the mean is taken over a transient the target never contained, which could as
easily degrade the fit. **Both directions are publishable and neither is the hoped-for outcome.**

**P4 — `alpfe` and `R_PICPOC` barely move.** Both are converged by 100 steps, so their endpoint
and window mean are close. `alpfe` additionally rails to its bound in two of three basins at every
window, and railing is not something a time mean relieves.

## 3. Decision rule, fixed in advance

- Grade on the **per-AOI ≥2-of-3** rule, **all three collapses**, against `tm_null`.
- `scav_rat` and the trio are read under the **geometric** collapse. The arithmetic number is
  reported beside it and is not the headline.
- Report the **per-basin median as ×Carroll**, not only the counts. The window result showed the
  counts hide a monotone drift, and a count that moves without the value moving is a band effect.
- **Band sensitivity at ±0.05** before any claim.
- A change in the trio that is not accompanied by a change in `scav_rat`'s per-basin medians is a
  threshold artifact and will be reported as one.

## 4. Falsifier

**If `tm_ctrl` does not reproduce the flagship trio to within seed noise, no conclusion may be
drawn about `TIME_MEAN_LOSS` from this submission.** This is the rule that both previous window
sweeps violated by inferring from an arm whose control had already failed.

## 5. What is deliberately NOT in this submission

`PINN_DFE2_W`, the subsurface steady-state residual, is implemented and stays at 0. Measured
2026-08-06 at Carroll's own parameters, relative drift per day:

| step | day | `DFe_1` | `DFe_2` |
|---|---|---|---|
| 200 | 50 | 2.84e-05 | **1.68e-02** |
| 3200 | 800 | 6.38e-12 | 1.62e-06 |

Surface iron is converged at the operating point and the existing PINN term is correctly ~zero at
the truth — bitwise, the loss is identical at `NB23_PINN_WEIGHT` 0 and 3. Subsurface iron is not.
A steady-state penalty on `DFe_2` at 200 steps is therefore **nonzero at Carroll**, so minimising
it moves the fit away from the answer. The originally-planned 2×2 was cut to this 1×2 on that
measurement, before any compute was spent. The term is correct for a converged-window arm and is
kept, gated off, for one.
