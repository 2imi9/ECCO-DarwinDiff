# DarwinDiff — consolidation checkpoint (2026-07-25)

*Purpose: declare a defensible stopping point and consolidate confidence, rather than keep pushing limits.
Grounded in a four-pillar audit of the current verified state (learner, emulator, manuscript, scope). Every
number here is `verify_run`-gated unless flagged. The project's own frame holds: this addresses only the 6
Carroll-6 biological parameters inside ECCO-Darwin, not the whole model, and it is an **identifiability study,
not a 6/6 recovery chase**.*

## The two legit outcomes we are consolidating toward

1. **A parameter-identifiability study of the Carroll-6 set (Track 1, paper #1)** — submission-ready. The clean
   contribution is a per-parameter map of *which* parameters a real-anchored differentiable-surrogate inversion
   can constrain and *why*, anchored on one verified result: the **per-cell architecture is load-bearing** (the
   trio holds 25/50 per-AOI, rising to ~41/50 at 4000 epochs, vs **0/50** for a global scalar).
2. **A forward emulator + an iron-cycle discovery contribution (Track 2, paper #2)** — complete. The emulator
   is a **clean negative result** (1-step horizon, no skill over seasonal AR(1)) plus reusable infrastructure;
   the iron-cycle science is in **adjacent, observation-grounded findings**, not in the emulator beating
   anything.

Both are gated on a **collaborator read + new observations**, not on compute. There is nothing to compute-chase.

---

## Track 1 — the honest per-parameter verdict (all six, graded honestly)

Reporting each parameter as recovered / partial / excluded is the *point* — the failures are results, not
misses.

| param | verdict | best verified | config | confidence |
|---|---|---|---|---|
| **alpfe** | RECOVERED | 49/50 per-AOI (n=50) | geo1 (real GEOTRACES iron) | high — method-independent (DINN-free + Nelder-Mead + EKI agree); mass-balance-identified. *Caveat: weight-conditional (needs ~10× real-iron up-weight); null hit-rate 0.47* |
| **R_PICPOC** | RECOVERED | 50/50 per-AOI (n=50); anchor-off 6/50 epoch-matched (4/50 at 1500 epochs) | geo1 (real Daniels/MODIS calcite) | high — most significant recovery (null 0.02). Lands ~0.05, consistent with Carroll 0.0425 *only within the wide 40% band* — **not** a validation of 0.0425 |
| **scav_rat** | PARTIAL (basin-fragile) | 41/50 @4000ep (25/50 @2000ep); SO 48, natl 40, eqpac 6 | geo1 full loss | high on the *verdict*, low on a high count — natl is closeable optimization, eqpac (6/50) is an information wall; collapses to **0/50 per-AOI** anchors-only (pattern-driven, not anchor-driven; the 40/50 cell-weighted there is a southernoceanpac straddle, job 8536393) |
| **diatomgraz** | PARTIAL (model-internal only) | 10/10 (+MLD via bSi); 35/50 (n=50, non-circular Chl+MLD) | geo1+MLD | medium — **not** recovered from independent real data (~4/10 = chance); the Chl target is Darwin's own. Structural-vs-practical still open (#152) |
| **Smallgrow** | EXCLUDED by construction | real 0/N; synth 7/7; seasonal natl 9/10 (unconfirmed) | — | high on exclusion / low on the seasonal hint |
| **Biggrow** | EXCLUDED / unobservable | 0/N everywhere (real, synth, seasonal) | — | high (fails-tight) |

**The clean quantitative headline — the trio {alpfe, scav_rat, R_PICPOC}:** 25/50 per-AOI (2000ep) → ~41/50
(4000ep), 33/50 cell-weighted, vs **0/50** global scalar (disjoint Wilson CIs, Fisher p<0.01).

**Two decomposition results that make the study sharp:**
- **The recoverability gap is two components** — a large *closeable optimization* component (natl scav_rat
  20→40/50 with 2× compute, no new data) plus a residual *information* component (eqpac 6/50). The sharpest
  statement of identifiability ≠ recoverability.
- **The 3-of-4 frontier is STRUCTURAL** (job 192298): no single config recovers all four observables. scav_rat
  needs the Darwin-pattern term; diatomgraz needs MLD; they conflict even at 4000 epochs. **Two operating
  points exist, not one.**

### Should we build a separate "4-parameter product learner"? — Qualified NO as a build, YES as packaging.

- A single-config 4-param learner **cannot honestly exist** — the 3-of-4 trade-off is structural. At most a
  "choose-your-trio" tool.
- It is the **same codebase** (`run_v3.0_joint_multi_aoi.py` + config levers) — there is no separate product to
  build, only a documented, `verify_run`-gated wrapper around the two operating points.
- Selling recovered numbers as **calibrated values** would re-introduce the exact over-claim the project spent
  months retracting (held-out real-data R² is negative — this is a consistency check within a 40% band).
- **What to ship:** a thin reproducibility wrapper presented as an *identifiability tool* — "which Carroll-6
  params a real-anchored surrogate inversion can constrain, before spending Green's-functions effort" — the
  same asset as the paper's map, shipped as a tool, with the consistency-check caveat attached.

The two rock-solid, point-identified members are **alpfe (49/50) and R_PICPOC (50/50)**; scav_rat is
basin-conditional; diatomgraz is model-internal. Ship it with tiers, not a flat "4/4."

---

## Track 2 — emulator + iron-cycle discovery (stated at true size)

- **The emulator is a physically-valid surrogate of the v05 *model*** (not the ocean): 0% negative
  concentrations in log-space and valid carbonate chemistry; **mass is NOT conserved** (Chl1 drifts +129.7% over six rollout steps -- corrected 2026-07-28). **Useful horizon = 1 step.** Two
  prior headlines are **retracted**: the "~9-month horizon" (a `delta_t` calendar artifact) and "beats
  persistence" (against a per-cell seasonal AR(1) it adds no significant skill; PIC/POC's edge was mechanical).
- **The value is the clean negative result** — the 1-step ceiling is structural (irreducible state-dependent
  single-step error; not bias, not variance collapse, not chaos — four mechanisms killed by measurement), the
  only real skill lever is deep ensembling, and it comes with reusable infrastructure (the first ocean-BGC
  Earth2Studio `PrognosticModel`, physics validators that caught the model inventing 4.5% negative iron).
- **Iron-cycle discovery is the adjacent, observation-grounded science — not the emulator itself:**
  1. **v05-vs-MODIS chlorophyll (novel — Chl is unevaluated in ECCO-Darwin's own white paper):** a robust
     regime split — subpolar N. Atlantic bloom is **5× low**, equatorial Pacific is **unbiased**. A
     bloom-dynamics error, not a global scaling error.
  2. **Equatorial ENSO phase discrepancy (robust measurement, unresolved cause):** MODIS Chl peaks at lag +1;
     v05 peaks at lag −2 (leads Niño-3.4). The leading **untested** hypothesis is iron supply (thermocline /
     EUC advection), tying it directly to Track-1's alpfe/scav_rat. Report as a model–obs discrepancy, not a
     diagnosed iron defect.
  3. **Column-OSSE (synthetic):** a 1-D vertical DFe column breaks the alpfe↔scav_rat degeneracy the 0-D box
     cannot — the identifiability geometry that would make "a strong emulator for iron-cycle discovery"
     concrete (a real-data 1-D column fit with prescribed remineralization; a new, gated build).

**Honest correction to the ask:** the current FNO2d BGC-state emulator is **not** the vehicle for iron-cycle
discovery (1-step ceiling, no iron-supply drivers). "A strong emulator for iron discovery" = the 1-D column
surrogate or the chl/ENSO diagnostic, both future builds. What is *strong today* is the discovery finding
(chl regime split + ENSO phase), which needs no emulator skill at all.

---

## The defensible checkpoint — stop here

Declare **both tracks complete** at 1° box scale:

- **Track 1:** a per-parameter identifiability map + the load-bearing per-cell ablation + the two-component gap
  + the structural 3-of-4 frontier. Ship the paper.
- **Track 2:** a physically-valid v05 surrogate whose 1-step ceiling is a fully-traced negative result + infra,
  and the iron-cycle discovery findings (chl regime split, ENSO phase, column-OSSE geometry).

**Explicitly deferred (feasible, out of scope — keeps the checkpoint clean):**
the ECCO-Darwin v05 GCM perturbation ensemble (#163); 6/6 and any 4-of-4 chase; native LLC270 resolution;
seasonal/time-resolved growth-pair recovery; a full spatial UDE at real scale (#176); the B200/diffusion work.
Every one needs **new observations or a native inversion, not more epochs**.

**On the record — retracted claims that must stay retracted:** the "6/6" frame; "R_PICPOC needs a
differentiable calcite port + native resolution" (both tested, neither helped); the strong −0.77 iron
degeneracy (a coupling-inflated marginal); the n=10 scav_rat "9/10" (seed luck); the "~9-month" emulator
horizon; "beats persistence."

---

## "Make every confidence better" — the concrete actions (all cheap, no new compute)

The audit found the **shipped manuscript is *conservative*** — it under-claims relative to verified findings.
Closing that gap is the highest-value confidence work, and it is all fold-ins:

1. **Reconcile main.tex ↔ STATUS.md** — the four H-batch reframes already proposed (scav_rat practical-non-ID;
   the 4000-epoch two-component result; EKI estimator-independence; the 38/40 headline qualification). *Pending
   your yes on those diffs.*
2. **Fold in three already-verified red-team reruns** not yet in the draft: the sign-flip at n≥50 (draft still
   says n=6), the eqpac-alone basin ablation, and the anchors-only (pattern-off) ablation.
3. **Decide the diatomgraz framing** — upgrade to "recoverable from a non-circular model-internal observable
   (Chl+MLD, 35/50), not yet from independent real data," or keep the conservative "data-blocked" line and cite
   the newer result as forward work. Either is fine; make the paper and STATUS agree.
4. **Reproducibility freeze** — pin the ship commit, confirm `verify_run` exit 0 on the flagship run dirs,
   stage the Zenodo archive for an on-acceptance DOI.

---

## What to do next (prioritized, small, high-confidence)

1. **Ship the identifiability study (paper #1)** — apply items 1–2 above, then send to Jon + Mick for the
   domain read and co-author consent (the real gate). This *is* the checkpoint.
2. **Package the identifiable-subset learner** as the documented, `verify_run`-gated wrapper around the two
   operating points (identifiability tool, not a calibrated-values product).
3. **Write up the iron-cycle chl-discovery** as a short standalone note for Jon (novel finding about *their*
   model; report deseasonalized anomaly r, carry n_eff, keep the withdrawn-biological-timescale correction
   visible). No new build.
4. **AGU26 abstract** — submit the iron-focused primary before the **Aug 5** deadline (numbers already
   verify-gated), if first-author membership + co-author consent land in time.
5. **Onboarding** — [docs/ONBOARDING.md](ONBOARDING.md) is the "start here" basement; cross-link it from README
   and the top of STATUS.md so it is the literal front door.

Nothing above needs the cluster or new data. The honest ceiling of this checkpoint is orientation, a shipped
study, and a discovery note — everything past it is a new, gated build.
