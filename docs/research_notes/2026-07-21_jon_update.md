# DarwinDiff — findings update for Jon (2026-07-21)

A progress write-up on the parameter-identifiability work, leading with the result most relevant to
the iron reframing from our last meeting. Everything below is `verify_run`-gated or primary-sourced;
open questions are flagged as such. Nothing here is a real-data discovery claim — it is a consistency
study against Carroll's published values plus an external grounding of what that study means.

---

## 1. Headline: the iron source↔scavenging degeneracy we recover **is** the FeMIP problem

The central Track-1 finding — that dissolved-iron concentration constrains the *ratio* of iron input to
scavenging but leaves the two individually unidentified — turns out to be the same degeneracy the whole
ocean-iron-modelling field lives with. We validated this against **Tagliabue et al. 2016's own Table 2**
(the 13-model FeMIP intercomparison, read from the primary PDF):

- residence time roams **3.7 → 626 yr (169×)** across the models, while **mean concentration is pinned to
  0.58 ± 0.14 nM (~24%)** and **total input flux roams ~140×** (sediment source 0–194 Gmol/yr — the
  dominant, most model-inconsistent term);
- the identity `τ = inventory / input` reproduces every model's residence time exactly, so the **169×
  spread decomposes as 130× from input × 1.3× from inventory** — a *single* source↔scavenging identifiability
  degeneracy, no exotic physics needed;
- Somes et al. 2021's controlled experiment (vary the **combined atmospheric + sedimentary** source ~5×,
  retune scavenging to hold concentration) lands on the prediction: τ ×4.8.

We derived this from a single-box steady state (the Fisher matrix is rank-1: concentration stiff, residence
time the sloppy free direction) and had it independently re-derived. **The contribution:** the field
*measures* this degeneracy but — across a targeted search of the FeMIP / SCOR WG151 / Tagliabue lineage —
we did not find it named as a formal identifiability / sloppiness problem (not a provable true negative).
That vocabulary is used in marine-ecosystem calibration generally (Schartau et al. 2017) but not, that we
found, for the iron cycle. Framing FeMIP divergence with a profile-likelihood / Fisher diagnostic looks like
a genuine, defensible contribution *to the iron community*, not just a note about our method. Detail:
`docs/research_notes/2026-07-20_iron_degeneracy_math_validation.md` (the Table-2 arithmetic is
self-consistent and checkable).

## 2. `alpfe` is a near-unity scalar on already-soluble iron — **not** a solubility

Following the reframing from our meeting: we confirmed, from Darwin3's own documentation and the production
namelist, that `alpfe` should be **≈1 when the ironfile is already soluble** (Darwin3: "set it to 1 if the
deposition rate in ironfile is already of soluble iron"). ECCO-Darwin v05 forces with the soluble
Mahowald-2009 product and sets `ALPFE = 0.928` — so it is a dimensionless correction on already-soluble
iron, not the ~1–2% fractional solubility of dust iron. We've corrected the "iron dust solubility" label
in our code. (Citation fix worth noting: Darwin's iron model is Parekh, Follows & Boyle **2005**, GBC 19
GB2020 — the "2006" DOI in circulation is a different paper.)

## 3. What is identifiable, what isn't, and how robustly

The honest map, from real GEOTRACES iron + a real calcite anchor, cross-checked with per-AOI Fisher/CRLB and
a multi-seed sweep (Explorer `8512053`, ~20/30 tasks in; verdicts are **seed-robust** — each parameter
passes or fails *tightly*: Smallgrow 7/7 at rel-err 0.001–0.009, Biggrow 0/7 at 0.68–0.71, so the
pass/fail is not seed-luck):

| parameter | recovers? | identifiability | notes |
|---|---|---|---|
| **alpfe** | yes, ≈Carroll | **method-independent** — a DINN-free global scalar *and* a gradient-free Nelder-Mead estimator both reach it | near-saturated across configs (passes ~100%), so it contributes little discriminating info to the joint count |
| **scav_rat** | yes (Cal-grade) | **requires the per-cell architecture** — 0/10 under a global-scalar estimator; recovers in-band (CV ~43%), *not point-identified* | scav_rat is the parameter actually driving the "38/40" joint number; movement is bound-to-bound with loss weighting, not a curved re-optimisation |
| **R_PICPOC** | **yes, 9/10** (geo1; 10/10 in the RATIO_MAX config) | most strongly identified of the three (profile span 46.6); requires per-cell | vs a real calcite anchor; lands ~0.05 — consistent with Carroll only within the wide ±40% Cal band, **not a validation of 0.0425** (Carroll's own value is under-constrained; a single global constant is mis-specified against a regionally-variable rain ratio) |
| **diatomgraz** | no (best 4/10 = chance) | not identified from the staged data | constrained only via a back-solved biogenic-silica diagnostic, not a prognostic silicate cycle |
| **Smallgrow, Biggrow** (growth pair) | partial in synthetic | **unobservable by construction** | confirmed externally: no observing-system product isolates size-class growth rate from biomass |

Per-cell prediction is load-bearing: the trio {alpfe, scav_rat, R_PICPOC} holds 7/10 with a per-cell network
vs **0/10** for a single global vector — the cleanest, most quantitative Track-1 result (figure). The "38/40"
is the *best of an ~86-config sweep* (Wilson 95% CI ~[84%, 99%]), so it should be read as "recovers
reproducibly at the best configuration," not a headline recovery rate. Per-AOI Fisher information for the
iron pair is highest in the Eq. Pacific and N. Atlantic, lower in the Southern Ocean (no local iron
gradient). *(One caveat I'll be precise about with you: the θ\* Hessians used for the per-AOI sloppiness
figures carry a non-positive eigenvalue — θ\* is a saddle/degenerate point — so those eigenvalue spans need
the multi-start re-run to land a clean artifact before I quote a decade-span number.)*

## 4. Iron residence time — a quantitative sanity check

Our recovered surface iron residence time is **~1–8 days** across the three regions — the order of the
*observed upper-ocean* envelope (Black et al. 2020: 10–100 d), not the whole-ocean model range. Within the
data-consistent band it barely roams, because fitting the real GEOTRACES section structure per-cell escapes
the global-mean-only degeneracy — the concrete version of Somes 2021's point that the **full section
profile** (absolute concentrations at multiple points, not the gradient alone, which is source-invariant),
not the mean, breaks the degeneracy.

## 5. Independent validation (your question — "is an independent inversion tractable?")

Two honest pieces:
- **The precedented route exists.** The Ensemble-Kalman-Inversion / Calibrate-Emulate-Sample lineage
  (Stuart, Schneider, Kovachki, Baptista at Caltech) does exactly derivative-free Bayesian calibration of
  expensive Earth-system models — a natural, citable framework for an independent inversion of the Carroll-6,
  and one we currently don't cite. Our sloppy-eigenvector / CRLB diagnostic is the tool that says *which*
  parameters such an inversion could hope to constrain.
- **The honest limit — and it was already tested spatially.** A faithful held-out *real-data* validation is
  structurally blocked at box scale: the 0-D box homogenizes, so held-out GEOTRACES R² is negative. And going
  spatial does *not* automatically fix it — the July 9–10 transport-UDE study found scav_rat observability-
  limited on real GEOTRACES iron *even with transport present*, i.e. for scav_rat the limit is the data's
  information content, not just the box. That is the standing result §6's forward plan has to reckon with,
  not route around.

## 6. Where the compute goes next (forward plan, honest)

- **A spatial, structure-preserving UDE.** Keep Darwin's known physics as real equations, learn only
  uncertain closures as stoichiometric reactions with exact conservation/positivity, and — critically —
  learn only the *identifiable* directions (project circulation sensitivity out of the biological Jacobian).
  **The reconciliation I owe you, up front:** the July 9–10 study (the D1–D3 brief you were asked to decide
  on — `2026-07-09_track2_identifiability_writeup.md`, `2026-07-10_jon_decision_brief.md`) already fit a
  *differentiable-transport UDE to real spatially-resolved GEOTRACES iron* and found scav_rat **not
  identifiable — observability-limited, structural: more iron data would not close it.** That negative
  stands. An idealized in-principle check this week (a noiseless single-point-source toy) suggests the
  *full section profile* (absolute concentrations at multiple points along the flow — not the gradient
  alone, which is source-invariant) could raise identifiability — but a toy is not commensurate evidence
  against a real-data negative. So the new UDE's *first* job is to say what it does differently from the
  July fit — target the section *profile* rather than the field-mean DFe, under realistic sparse/noisy
  coverage — and demonstrate that it actually moves the July result. **This is feasibility/design, not a
  real-data result.**
- **Neural-operator methods worth adopting** (Anandkumar/Stuart lineage): Markov Neural Operators for
  *stable long rollout* (train one-step, match the invariant measure instead of the trajectory) — a direct
  fix for our emulator's short horizon; and geometry-aware operators (GINO) for the LLC270 grid.

## 7. Open question we should flag, not hide

Our forward-emulator "rollout ceiling" was concluded to be irreducible for the current architecture. To be
fair to that verdict, it *did* eliminate a per-cell/location-indexed constant-bias field (which explained
only ~0.22% of held-out variance — weak evidence against a large location-driven bias). But it never tested
the specific mechanism that matters here: a flat 2-D FFT run on a curved, land-masked grid produces a
*state-dependent, boundary-concentrated* bias (per the Spherical-FNO diagnosis) — which a **constant**
per-cell correction cannot capture, so the 0.22% result doesn't rule it out. We tried to test it directly
this week, but the right data (a global geographic cube) is no longer on disk, and the AOI cubes have a
non-geographic layout that can't resolve the coastal-vs-interior contrast — so it is **contested, not
resolved.** The clean experiment — a geometry-aware operator (GINO) vs the flat FFT on a rebuilt global
cube — is scoped and worth doing before we call the ceiling fundamental.

---

*Artifacts: `docs/research_notes/2026-07-20_external_validation_iron_residence_alpfe.md` (external validation,
hostile-verified), `2026-07-20_iron_degeneracy_math_validation.md` (the derivation), `docs/findings/`
(recovery-config CRLB, iron residence time, identifiability sweep). All numbers gated through
`scripts/verify_run.py` or primary sources.*
