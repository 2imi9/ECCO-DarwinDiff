# Identifiability is parameter-specific — each parameter's observation + architecture schema follows from its role

Draft 2026-07-24. A candidate organizing principle (arguably the thesis) for the identifiability study:
**there is no single recipe for recovering the Carroll-6.** Each parameter's *mechanistic role in the Darwin
BGC equations* determines (a) what observable can constrain it, (b) through which observation operator, (c) how
it must be represented in the surrogate/architecture, and (d) how it fails. All [ours-verified] unless noted.

## The schema, per parameter

| param | role in the model | what constrains it (observation schema) | architecture schema (how it integrates) | failure mode |
|---|---|---|---|---|
| **alpfe** | surface iron **source** scalar (dust solubility on already-soluble Fe) | the **absolute magnitude** of surface [DFe]; recovers even from the global mean | **any** — recovers method-independently (global scalar, Nelder-Mead, EKI all work) | none (recovers 49/50) |
| **scav_rat** | iron **loss rate** (scavenging; depth-acting on the particle field) | only the **S/k ratio** from [DFe] — needs the section **gradient / subsurface depth structure** to break it; then enough **optimization**; and ultimately an independent **rate** observable (²³⁴Th) | **per-cell** (global = 0/50) + ideally **reparameterize to (ratio, product)** so only the identifiable combination is free | ratio-degeneracy (surface) → optimization limit → information limit (eqpac) |
| **R_PICPOC** | calcite **rain ratio** (PIC:POC production) | the **exact null direction** of the iron Fisher — no amount of iron data touches it; needs a **different observable entirely**: a real calcite **production-ratio** anchor (Daniels) | **per-cell** (global = 0/50) + an **external absolute anchor** | null direction — unconstrained without the anchor (anchor-off → 6/50 epoch-matched; 4/50 at 1500 ep) |
| **diatomgraz** | diatom **palatability multiplier** (a dimensionless predator–prey term) | the **chlorophyll pattern + a mixing covariate (MLD)** — a different modality again; **not** the bSi biomass tautology | **per-cell** + an **extra input channel** (MLD) — an *information* addition, not capacity | circular bSi diagnostic OR **structural conflict** with the iron trio (no 4-of-4) |
| **Smallgrow / Biggrow** | max **growth rates** (PCmax) | **group-resolved production + temporal moments** (the annual cycle); bulk data gives only the biomass-weighted mean | needs a **time-resolved target** + group-resolved observations | fundamental: growth is confounded with grazing/limitation; Biggrow inseparable even with seasonality (Spitz 1998) |

## Why this is the point, not an accident
The four observation "schemas" are not arbitrary — they are the **dual** of the parameter's structural role:
- a **source scalar** (alpfe) sets a level → an **absolute concentration** identifies it, from anywhere;
- a **loss rate** (scav_rat) only ever appears as source/loss at steady state → a concentration gives the
  **ratio**, and you must add **structure** (depth gradient) or a **rate** measurement to separate the two;
- a **ratio** that doesn't touch the iron observable (R_PICPOC) is a **null direction** → it needs its **own**
  observable;
- a **multiplier on a flux** (diatomgraz) is only visible through the **pattern of the field it modulates**
  (chlorophyll) + the environment that gates it (MLD).

So "how do you recover parameter X" has a **different answer for every X**, and the answer is dictated by how X
enters the equations. This is why:
1. **The observation-design prescription is a per-parameter table** (different dataset + operator each), not a
   single "measure more iron" recommendation.
2. **The architecture is parameter-specific:** per-cell for the loss-rate/ratio parameters (global scalar =
   0/50), an input channel for the covariate-gated one, an external anchor for the null-direction one, and
   (proposed) an invariance reparameterization for the ratio-degenerate pair.
3. **"Identifiability ≠ recoverability" is itself parameter-specific:** alpfe = both; scav_rat = identifiable
   but recoverability is optimization+observing-system limited; R_PICPOC = identifiable only once anchored;
   diatomgraz = identifiable non-circularly but not co-recoverable with iron; growth pair = not identifiable.

## Implication for the closure / Track-2 direction
The same principle carries to *integrating a learned closure into the model*: the way a parameter (or a learned
closure term) should be **built into the architecture** ought to encode its identifiability geometry — e.g.,
parameterize the iron pair as `(ratio, product)` so the surrogate only exposes the combination data can pin,
and make conservation/positivity structural (Track-2 architectural contract). The schema for *learning* a term
and the schema for *identifying* it are the same schema, read forward vs. inverse.

## The complement — what is SHARED and reusable (the schemas are leaves of one object)

The per-parameter schemas above are **not** four independent recipes. They are all *readings of a single shared
object*, produced by a single shared pipeline. The specificity is only in the leaf.

**1. One surrogate, one network, one pipeline — 100% reused.** All six parameters are the output channels of
the **same per-cell network** (env → 6 params), integrated through the **same differentiable box**, trained by
the **same** gradient loop, gated by the **same** `verify_run`. There is no separate model per parameter; the
only per-parameter thing is which loss term is active and which input channel is on.

**2. One diagnostic object — the Fisher / surrogate-Jacobian.** Every schema is an eigen-reading of the *same*
Fisher `F = JᵀJ`:
- alpfe recovers → it is a **stiff** eigen-direction (large eigenvalue).
- scav_rat → the **sloppy** direction (the S/k ratio is the low-eigenvalue eigenvector).
- R_PICPOC → the **exact null** direction (zero eigenvalue) of the iron Fisher; adding a calcite row makes it
  stiff.
- diatomgraz → a different **block** (the bSi/Chl rows).
You do not design four recipes — you compute **one** Fisher from the observing system and read all four schemas
off its spectrum at once. The parameter-specificity is the *output* of one shared operation, like a compiler.

**3. One design principle, reused per parameter.** To make any parameter identifiable, **add an observation
operator whose Jacobian row has nonzero projection onto that parameter's currently null/sloppy direction.**
That is a single rule; "subsurface iron section for scav_rat," "calcite anchor for R_PICPOC," "MLD channel for
diatomgraz" are the same rule applied to different null directions.

**4. One reparameterization, generalizes.** The Fisher-eigenbasis `(ratio, product)` move (Lever-1) is a
*general* operation on any degenerate pair — estimate the stiff eigen-coordinate from data, prior-bound the
sloppy one, map back. Not bespoke to iron.

**5. One estimator family, parameter-agnostic.** Backprop, gradient-free Nelder-Mead, and EKI all recover any
parameter subset with no per-parameter change — which is exactly why the estimator-independence check is
meaningful.

**Where it IS genuinely bespoke (the real per-parameter labor):** the **observation operators** themselves —
correct depth / seasonal phase / AOI footprint / uncertainty weighting, and turning a raw dataset into the
right quantity (²³⁴Th → a scavenging *rate*; PIC/POC → a *production* ratio, not a standing stock). There is no
turnkey product for these. But **which** operator to build is *told to you by the shared Fisher* — so even the
bespoke part is directed by the common object, not guessed.

**One-line reconciliation:** the *framework* (surrogate + per-cell net + Fisher geometry + the "add-a-row"
design rule + eigenbasis reparameterization) is fully reused; the *observation operators* are bespoke; and the
per-parameter identifiability schema is what you *get out* when you apply the shared framework to a given
observing system. Common core, specific leaves.

**Closure/Track-2 tie-in.** This is exactly the Han–Ma–Ma–E (2019) structure: a **shared** learned set of
generalized moments, then a closure **on** them — the substrate is common, the per-term behavior is read off
it. Forward (learn a closure term) and inverse (identify a parameter) are the same operation on the same
shared object, run in opposite directions.

## Caveat
The growth-pair and diatomgraz rows involve model-internal or synthetic targets; the iron/R_PICPOC rows use
real observations. The schemas are established on the surrogate; the surrogate→GCM validation (#163) is the
gate that lifts them to a GCM statement.
