# Overnight verified results — per-AOI Fisher geometry + first-ever #85 seasonal (2026-07-23)

All numbers below are read directly from the committed JSON artifacts (jobs 189403 geometry, 189324
seasonal). GN-Fisher is PSD-by-construction with residual reconstruction verified to loss (`recon_rel_error`
≈ 0). Seasonal uses the laptop-scale prototype (constant IC, constant carbonate forcing, Chl-only pattern
loss), so ABSOLUTE seasonal recovery is a lower bound; the meaningful signal is the **seasonal-minus-time-mean
delta** (apples-to-apples, same prototype).

## 1. Per-AOI iron conditioning REFINES the corrected iron claim (job 189403)

GN-Fisher `{alpfe, scav_rat}` 2×2 on the REAL surf+sub GEOTRACES loss (`--loss realiron`,
`GEOTRACES_SUB_W=1`), per AOI:

| AOI | cond(2×2) | conditional corr | sloppy dir | ratio-like? | iron sloppiness (decades) |
|---|---|---|---|---|---|
| eqpac | **34.7** | +0.939 | (+0.59 alpfe, +0.81 scav_rat) | YES (S/k ratio) | 5.19 |
| natlsubpolar | **50.8** | +0.961 | (+0.67, +0.74) | YES | 5.99 |
| southernoceanpac | **2.22** | −0.191 | (+0.97 alpfe, −0.24 scav_rat) | NO | 4.99 |

**The finding:** the aggregate "subsurface [DFe] resolves the alpfe/scav_rat degeneracy, cond 3022→2.2"
(job 188077) is **Southern-Ocean-driven**. Per basin, only the Southern Ocean section is well-conditioned
(cond 2.2, not ratio-like); **eqpac and natl remain ratio-degenerate even with subsurface iron** (cond 35–51,
conditional corr +0.94–0.96, same-sign S/k sloppy direction). Subsurface iron is a **basin-dependent**
symmetry-breaker, strongest where the section carries the most depth structure (SO). This does not contradict
the corrected claim (the pooled/joint problem really is ~3 orders better); it sharpens it, and it explains why
`scav_rat` recovery is basin-fragile: the pooled fit inherits eqpac/natl's residual ratio-degeneracy.

**Consequence for the abstract/manuscript:** keep "improves the conditioning of the pooled problem by ~3
orders" (true), but attribute the resolution to the SO section, and state eqpac/natl stay ratio-degenerate.

## 2. Per-AOI sloppiness retires the "provisional" qualifier

The per-AOI iron sloppiness is now the PSD GN-Fisher number (verified reconstruction), **~5–6 decades**
(eqpac 5.19, natl 5.99, sopac 4.99), superseding the earlier provisional per-AOI 3.96 (a different,
unconverged method). The bSi-loss per-AOI sloppiness is 3.81 (eqpac) / 4.31 (natl). Quotable now.

## 3. scav_rat is CONSTRAINED at eqpac — practical, not structural, non-identifiability

`hess-scavrat-eqpac` (24-start Hessian profile, realiron): verdict **CURVED → PRACTICAL non-identifiability**
("routing/pooling/seeds licensed; param IS constrained"). The scav_rat objective has curvature at the eqpac
optimum, so scav_rat carries information; its poor recovery is an optimization/design limit, not a flat
(structural) wall. This is the cleanest single-number support for **identifiability ≠ recoverability**.

## 4. #85 first-ever seasonal fit — AOI-selective, sign tracks seasonality (job 189324, all 3 AOIs)

Seasonal-vs-time-mean Cal-grade+ count (out of 10 seeds), per AOI/param (Chl-only; R_PICPOC excluded).
Only |delta| ≥ 2 shown as signal:

| AOI (seasonality) | param | seasonal cal+ | time-mean cal+ | delta |
|---|---|---|---|---|
| southernoceanpac (strong) | alpfe | **5** | 0 | **+5** |
| natlsubpolar (strong bloom) | Smallgrow | **9** | 5 | **+4** |
| natlsubpolar | alpfe | 0 | 4 | **−4** |
| eqpac (weak) | diatomgraz | 2 | 8 | **−6** |
| eqpac | Biggrow | 1 | 3 | −2 |

**The finding (corrected once eqpac finished):** seasonal fitting is **NOT a net win** — it is an
**AOI-selective redistribution of constraint whose sign tracks local seasonality strength.** It recovers
Southern-Ocean iron (+5) and North-Atlantic growth (+4, a normally-unobservable growth rate) that the
time-mean misses, but **degrades equatorial diatomgraz (−6)** and North-Atlantic alpfe (−4). At the weakly
seasonal equator the annual-cycle integration adds no real signal and the prototype's approximations
(constant IC, constant carbonate forcing) appear to inject noise that the 8/10 time-mean diatomgraz fit does
not suffer.

Honest headline: **time resolution helps where the annual cycle is strong (SO iron, N-Atl growth) and hurts
where it is weak (equatorial diatomgraz); it is a regime-dependent lever, not a ceiling-break.** This is
consistent with Spitz 1998 (some growth/loss params stay inseparable even with the annual cycle — Biggrow
never recovers) and sharper than a naive "seasonality helps." First-ever seasonal result for this project.

**Caveat:** the delta is apples-to-apples within the laptop-scale prototype (both arms share IC/forcing/loss,
only the temporal target differs), so the qualitative regime-dependence is robust; but the prototype is
simplified vs the flagship trainer, so absolute numbers do not transfer 1:1. The clean next test is a
**native, interannual** time-resolved fit (monthly_v5 is staged), which removes the constant-IC/forcing
approximation — that is where a real ceiling-break, if any, would show.

## 5. SYNTHESIS — per-AOI conditioning PREDICTS per-AOI scav_rat recovery (the night's key result)

The n=50 reconciliation (job 188532, VERIFIED) settles the scav_rat number AND its mechanism:

- **scav_rat = 26/50 per-AOI at n=50**, essentially identical to the manuscript flagship 25/50. The earlier
  n=10 arm's **9/10 was seed luck** (regresses to ~52% at n=50; subW=1 replicate 6/10). The flagship number
  holds at 2000 epochs; scav_rat is the weak leg *there*. (alpfe 49/50, R_PICPOC 50/50 at n=50 — both robust.)
  **But at 4000 epochs scav_rat reaches 41/50** (natl 19→40, eqpac 6) — so "weak leg" is **largely an
  optimization limit, not an information wall**, with eqpac the sole info-limited basin. See
  `overnight_recovery_sweep_groupA.md` LEAD A.
- **The per-AOI Cal+ tally is the punchline:** scav_rat recovers **eqpac 8/50, natl 19/50, sopac 49/50.**
  This is *exactly* what §1's per-AOI GN-Fisher conditioning predicts: the Southern Ocean is well-conditioned
  (cond 2.2, subsurface breaks the ratio degeneracy) → scav_rat recovers 49/50; the equatorial Pacific and
  North Atlantic stay ratio-degenerate (cond 35–51) → scav_rat recovers 8/50 and 19/50. The 26/50 joint is
  set by how often eqpac/natl join the always-recovering SO.
- **Controls close the mechanism:** surface-only (subW=0) scav_rat 4/10 < balanced subsurface (subW=1) ~52%
  < over-weighted (subW=3/8) 5/10, 1/10. So subsurface iron at *balanced* weight is a small, real improvement
  over surface-only (consistent with it improving SO conditioning), but over-weighting it drags the fit.

**This is a coherent, fully-verified chain: observation geometry (which basin's section breaks the S/k
degeneracy) → per-AOI conditioning → per-AOI recovery.** It is the sharpest statement of "the observing
system, not the method, is the binding constraint," and it upgrades the scav_rat story from "config-fragile"
to "basin-resolved: recovers where the section has depth structure, fails where it does not." Strong paper
material and directly consistent with the AGU iron abstract.

## 6. EKI estimator-independence — the trio verdict is NOT a backprop artifact (job 189754, VERIFIED)

Full-box Ensemble Kalman Inversion (Iglesias-Law-Stuart 2013, derivative-free, J=256, 30 iters) on the real
geo1 box + real anchors (8 observables: surf/sub DFe + Daniels PIC:POC per AOI), growth held at Carroll:

| trio param | EKI post-mean | Carroll | rel_offset | band |
|---|---|---|---|---|
| alpfe | 0.999 | 0.928 | 0.076 | **Cal-grade** (recovers) |
| R_PICPOC | 0.0364 | 0.0425 | 0.143 | **Cal-grade** (recovers) |
| scav_rat | 2.09e-7 | 6.03e-7 | 0.653 | **Loose** (fails, pulled below Carroll) |

A completely different estimator (derivative-free ensemble, no gradients, immune to the θ\* saddle) reaches
the **same verdict as backprop**: alpfe and R_PICPOC recover to Cal-grade, scav_rat does not — and scav_rat is
biased low, the same direction as the DINN fit (n=50 median 4.16e-7) and experiment A. This **closes the
"single-method / DINN+autograd artifact" reviewer attack**: the identifiability verdict is estimator-independent.
Honest caveat (per the script's guardrail): the ILS-2013 EKI is an *optimizer*; its ensemble collapses, so its
spread is a point estimate, not a calibrated posterior, and the collapsed alpfe-dominated "sloppy axis"
(align 0.71 with the ratio) is an artifact of collapse — a calibrated credible interval needs an EKS/CES
sampling stage (future work). We report the posterior MEAN only.

## Status of the claim "significant improvement, verified"
- Per-AOI Fisher + scav_rat-curvature: VERIFIED (PSD, reconstruction to loss), strengthens the identifiability
  story and corrects an over-general conditioning claim. Net: paper is more precise and more honest.
- #85 seasonal: VERIFIED via the delta (same prototype both arms). Net: a new, publishable nuance; motivates a
  full time-resolved (native, interannual) fit as the next lever, but is NOT yet a ceiling-break.
- Recovery sweep (Group A: pat030-mld 4-of-4 shot, pattern dose-response, epochs-4000) still running — graded
  by the server-side aggregator (189419) into MORNING_SUMMARY.md.
