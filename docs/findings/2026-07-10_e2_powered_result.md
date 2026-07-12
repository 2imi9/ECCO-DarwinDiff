# The make-or-break out-of-sample transport E2 — a decisive negative (2026-07-10)

The pre-registered make-or-break test for Track-2: does a learned closure, fit on part of a real
calcite observation and scored on **held-out** cells **through prescribed transport**, beat a
constant (null) closure? Run properly (regularized closure, K_num control), the answer is **no** —
a clean out-of-sample negative that confirms the identifiability limit is real, not an in-sample
artifact. GPU (RTX 5090), eqpac-Marsh, upper-quartile-Ω env-regime hold-out (24 covered cells,
train 18 / val 6, Ω band-edge 5.41). Runner: `scripts/e2_real_calcite_eqpac.py`.

## Result

| closure | learned R² | null R² | delta (learned−null) @ physical kh | K_num ladder (kh 50 / 200 / 800) |
|---|---|---|---|---|
| default (hidden 16, wd 0) | **−1.53** | +0.50 | **−2.03** | −2.03 / −0.67 / −0.67 |
| regularized (hidden 4, wd 0.01) | **−0.05** | +0.50 | **−0.55** | −0.55 / −0.55 / −0.55 |

A **pass** would require delta > 0 (learned beats null) **and** delta largest at physical kh and
shrinking as kh grows (a real signal that transport smoothing degrades). Both runs **fail both
criteria**.

## Interpretation (clean diagnostic)

- **The default closure catastrophically overfits.** Learned −1.53 ≪ null +0.50: a ~600-parameter
  `EnvCalciteClosure` MLP fit on 18 train cells memorizes noise and extrapolates far worse than a
  constant to the held-out high-Ω band. Its K_num ladder is *anti-pass* (delta most negative at
  physical transport).
- **Regularization removes the overfit but reveals no signal.** With hidden 4 + weight-decay 0.01
  the learned R² rises to −0.05 (≈ the basin-mean baseline — the closure learns essentially
  nothing), confirming the −2.03 was overfitting. But even then it **cannot beat the null** (+0.50):
  there is no within-region Ω dependence to learn, so any Ω-modulation the closure adds only hurts
  out-of-sample prediction relative to a constant. The K_num ladder is **flat** (−0.552 / −0.553 /
  −0.553) — non-discriminating, the signature of no real transport-mediated signal.
- **The null itself scores +0.50**, i.e. a **constant** R_PICPOC through the full forward model
  (real Darwin IC climatology + Carroll-6 biology + transport) already predicts the held-out
  rain-ratio anomalies at R² = +0.5 — so the learned environmental modulation adds nothing over a
  constant. (*Which* component carries the +0.50 — IC climatology, biology, or transport — is **not**
  isolated here: no transport-off / IC-only control was run, and the K_num ladder was recorded only
  for the learned−null *delta*, not for the null. So the supported statement is "a constant closure
  already predicts the held-out anomalies"; **"transport *specifically* did the work" is not
  established and should not be asserted.**)

## What it establishes

The map's verdicts previously rested on a transport-free floor + an *in-sample* identifiability
oracle; the reviewer panel's sharpest structural objection was that the differentiable-transport
machinery had not contributed to any verdict. This closes that gap: **the make-or-break
out-of-sample transport gate, run with a properly-regularized closure and its K_num control,
returns a decisive negative for the calcite closure.** The identifiability limit holds
out-of-sample, not just in-sample — consistent with, and now demonstrated through transport by, the
oracle (no within-region Ω support), the driver scout (no driver rescues it), the correlation
analysis, and Marañón (2016).

## Honest caveats (unchanged)

- Small **n_val = 6** (single-AOI upper-quartile-Ω split). A cleanly *powered* within-region E2 is
  structurally impossible here for the same reason the closure is unidentifiable — the within-region
  Ω range is ≤ 0.16 dex, and pooling biomes turns the Ω-band hold-out into a between-biome
  extrapolation (the Simpson confound). So this is a decisive negative *at the available power*, not
  a high-n rejection.
- This is the **calcite** closure specifically. Iron (structural wall) and growth (loss-degenerate)
  are argued separately; the E2 was not run for them (iron has its own information-wall
  demonstration; growth is unobservable by construction).
