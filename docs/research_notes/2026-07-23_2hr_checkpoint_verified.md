# 2-hour research checkpoint — VERIFIED findings (2026-07-23)

Every finding below passed an adversarial verification pass (one skeptic per finding, checking the
claim against its own evidence doc, workflow `verify-major-findings`). Verdicts: **1 OVERSTATED, 8
NEEDS_CAVEAT** — the pass forced the framing to **retreat one level on every axis**: surrogate→GCM,
local→global, result→method, single-run→settled. That retreat *is* the headline.

## The meta-finding: retreat one level on every axis
- **surrogate, not GCM** — every Fisher/CRLB number characterizes the 0-D box. Signs transfer to
  ECCO-Darwin by construction (shared functional forms); **magnitudes and cross-parameter ranking
  are unvalidated** → the ~8-run v05 perturbation ensemble is the decisive test.
- **local, not global** — full-rank / degeneracy results are at Carroll (or ≤2 optima), linear, local.
- **result, not method** — "differentiable observation-design" is a *result* on the surrogate, not a
  validated general method. Drop the method claim; keep the result.
- **single-run, not settled** — the emulator refutation and the frontier arm are one run each.

## (1) Identifiability
- **Iron degeneracy (Q2).** alpfe/scav_rat near-perfectly degenerate *conditionally* (+0.999 at
  Carroll) **but that is surface-only**; the marginal anti-correlation −0.69…−0.77 is **RETRACTED** as a
  coupling-inflated full-6 marginal, not the iron-pair number (the pure surf+sub 2×2 GN-Fisher is
  well-conditioned, cond 2.2, conditional correlation −0.155), and it rested on **two** distinct points
  anyway (the two re-opt seeds returned identical values). Concentration constrains the source–sink
  *combination*; the surface-only conditional +0.999 means it does **not** separate the terms there (do
  NOT say "weakly separates").
- **No frontier (Q1) — surrogate-local reframe.** 4-observable Fisher full rank 4/4 in eqpac/natl, so
  the config swap is most plausibly an estimator/regularization artifact. Caveats: full rank is
  *numerically marginal* (softest eigenvalue ~500× below stiffest, on alpfe). SO drops to rank 2/4;
  missing Daniels explains **one** null — a **second near-null is unexplained**, so do not blame the SO
  deficiency on calcite alone.
- **Identifiable ≠ recoverable.** Flagship full-loss + MLD (n=10, 2000 ep, verify exit 0) did NOT reach
  4/4 — diatomgraz collapsed 0/10, R_PICPOC held 10/10. Reads as a recoverability/optimization limit,
  not information. Caveats: "identifiable" = local linear surrogate full-rank (rank ≠ conditioning); the
  no-MLD control died on a dead node (contrast not isolated); diatomgraz's "info present" is itself
  contested (only via the model-internal POSi diagnostic).
- **⚠️ OVERSTATED — profiles.** Defensible ONLY: R_PICPOC profile **CURVED** (strongly identified),
  diatomgraz **SHALLOW** (weak, optimum 0.607 vs Carroll 0.83), both guard-passing. **scav_rat & alpfe
  profiles were still running — no verdict.** My earlier "they run slow *because* they are the sloppy
  directions" asserts an observation + mechanism the evidence does not contain — **struck.**

## (2) Novelty + the deep scope limit
- **The degeneracy is NOT our discovery.** Frants et al. (2016) published the alpfe/scav_rat source–sink
  compensating family. Reposition novelty to (a) the ECCO-Darwin-specific identifiability *geometry* and
  (b) the observation-design *result*.
- **Observation-design (the surviving novel result).** A 234Th/210Po scavenging-flux survey is among the
  two best iron observations: ~1400× degenerate-direction variance reduction (conditional 2×2), condition
  2930→~7; a second *surface* [DFe] survey does nothing (2.0×). Caveat: 1400× assumes other params known;
  a *subsurface* [DFe] profile is comparable and stronger marginalized (~25× vs ~9×) — so the flux is one
  of **two** symmetry-breakers, not uniquely it; "concentration does nothing" holds only for *surface*.
- **Surrogate→GCM (deepest gap, #163).** No Darwin sensitivity data exists. Cheapest fix: ~8 one-at-a-time
  v05 perturbations about Carroll. State scope as "signs by construction; magnitude/ranking pending."

## (3) Emulator
- **Structural-ceiling refutation RETIRED 2026-07-23 (no significant skill vs a per-cell seasonal AR(1)
  baseline).** As originally recorded: beats seasonal climatology for 5/6 tracers; positive
  month-to-month tendency correlation for all six. Only FeT beats no baseline (consistent with missing
  iron forcing). Caveats: **single run** (eqpac, 1 seed, 8 pairs) — diagnostic not benchmark; do NOT call
  it "largely a metric artifact" (that mechanism covers only DIC/ALK/Chl; PIC/POC margins are near-zero
  +0.005/+0.047; FeT missing-inputs is *inferred*); "positive tendency correlation" is directional-only
  (r²_tend negative for DIC/ALK/FeT/Chl).

## What it means for Manuscript #1
The core science holds, but the framing retreats one level on every axis: from "we discovered the
degeneracy" → "we mapped *this model's* identifiability geometry and designed the observation that breaks
it"; from GCM claims → surrogate-local claims pending an ~8-run v05 validation; with the profile-likelihood
and emulator sections explicitly marked single-run / in-progress, not settled. This is a shippable Path-A
identifiability study — honest, and stronger for the retreat.
