# Manuscript spine — surrogate-to-model identifiability study (#116, 2026-06-27)

The skeleton for paper #1, framed per the verified reality. Not a draft — the load-bearing claims + the
evidence + the honest gaps, as the target for adversarial review.

## Title (working)
*What can a differentiable surrogate identify about a coupled ocean-biogeochemistry model? A
surrogate-to-model identifiability study of ECCO-Darwin's calibration parameters.*

## One-sentence thesis
When a coupled GCM cannot be differentiated, a 0-D differentiable surrogate fit to its output **and to
real ocean observations** identifies a *characterizable subset* of the GCM's calibration parameters —
and we map exactly which, why, and to what real-world agreement.

## Contributions (the claims to defend)
1. **Method.** A per-cell neural network predicts the six Carroll-6 parameters from local environment;
   gradients flow through a differentiable 0-D box (a surrogate for ECCO-Darwin v05) so one backward
   pass replaces Green's-functions' one-forward-run-per-parameter.
2. **Identifiability result.** Of the 6 parameters, **4 are observable** {alpfe, scav_rat, diatomgraz,
   R_PICPOC} and **2 (the growth pair) are unobservable by construction** (no real growth-rate data).
   The iron pair recovers from real GEOTRACES IDP2025 iron (38/40); R_PICPOC from real calcite
   (Daniels CP:PP / MODIS); the best config holds {alpfe, scav_rat, R_PICPOC} **jointly 8/10** (n=10).
3. **The surrogate gap is dimensional.** At uniform parameters the 0-D box relaxes to a spatially
   near-uniform state (tracer CV → ~1e-15 vs Darwin's O(1)); it cannot carry circulation-driven spatial
   structure. Therefore box-vs-Darwin spatial-pattern correlation is **not** a fidelity metric, and
   identifiability comes from **real, absolute, Darwin-independent anchors** — which makes the per-cell
   predictor load-bearing (a global-scalar vector gives a flat box that cannot match Darwin at all).
4. **Honesty machinery.** Every recovery number is re-derived and gated (`verify_run.py`); a self-twin
   isolates the method (recovers all 6 from box-generated targets at loss ~1e-10); the conclusions were
   pre-registered and adversarially verified, with two self-corrections on the record.

## Evidence table (verified, gated)
| claim | number | source |
|---|---|---|
| iron pair reproducible | 38/40 (95%) | best 3-AOI config |
| 3-param joint hold | geo1 {alpfe,scav_rat,R_PICPOC} 8/10 | hold-together sweep n=10 |
| anchor → R_PICPOC | 3/10 → 10/10, Fisher p=0.003 | dan0 control |
| box homogenizes | CV 4e-5@200 → 1e-15@6400 | box_cv_check |
| growth pair / diatomgraz | not recovered | sweep + FIM (SHALLOW) |

## Honest limitations (state up front)
- 1° box proxy; 23-yr climatology, not time-resolved; single-GPU prototype.
- **Single-method, single-model:** no independent inversion (e.g. Green's-functions / Bayesian) on the
  same targets, and no forward-Darwin held-out validation yet — so "recovery" against Carroll's own
  published values is a consistency check, not yet a cross-validated discovery.
- diatomgraz observability is open (needs dense Darwin POSi/TRAC16, not staged).
- R_PICPOC "recovery" is *validation within uncertainty* (any ratio anchor recovers it; the real
  anchor's value is non-circularity), not a from-scratch discovery — the Cal band is wide (±40%).

## The biggest gaps a reviewer will attack (for the panel to rank)
- "You grade against Carroll's own numbers — where is the independent yardstick?"
- "The box isn't ECCO-Darwin; how much is real vs surrogate artifact?" (answer: dimensional gap)
- "Per-cell vs global-scalar — is the complexity justified?" (answer: box homogenizes ⇒ yes)
- "n=10 — most inter-config differences are noise." (answer: only 2 effects claimed real)
