# ECCO-Darwin v05 parameter-perturbation ensemble — the correct recipe (2026-07-23)

Deliverable for Jon: the exact, verified recipe to run a small one-at-a-time (OAT) perturbation ensemble
in **ECCO-Darwin v05 / llc270** that validates the DarwinDiff 0-D surrogate parameter-Jacobian (and hence
the Fisher/CRLB identifiability geometry) against the real GCM. Written to be correct enough that the runs
are **not wasted**. Read-only investigation of the external repos; nothing was launched.

Companion docs: `docs/findings/2026-07-23_surrogate_jacobian_validation.md` (why this ensemble is the
missing ground truth), `docs/research_notes/2026-07-23_expert_review_corrections.md` (the review that
flagged the silent-failure bug and the preconditions).

---

## 0. Bottom line (the silent-failure verdict)

Of the four observable parameters, **two are trait-overridden and two are not**:

| box param | set in… | trait-override risk? | the ENTRY you must actually perturb |
|---|---|---|---|
| `alpfe` | `data.darwin` → `&DARWIN_PARAMS` → `ALPFE` | **NO** (read directly) | `ALPFE` in `data.darwin` |
| `scav_rat` | `data.darwin` → `&DARWIN_PARAMS` → `SCAV_RAT` | **NO** (read directly) | `SCAV_RAT` in `data.darwin` |
| `R_PICPOC` | generated from `data.darwin` `&DARWIN_RANDOM_PARAMS` `val_R_PICPOC`, then **OVERWRITTEN** by `data.traits` | **YES — silent** | `R_PICPOC` array in `data.traits` |
| `diatomgraz` | generated from `data.darwin` `&DARWIN_RANDOM_PARAMS` `diatomgraz`, then **OVERWRITTEN** by `data.traits` | **YES — silent** | `PALAT` array (diatom prey column) in `data.traits` |

So an ensemble that edits `val_R_PICPOC` / `diatomgraz` / `smallgrow` / `biggrow` in `data.darwin`
**changes nothing** — those scalars only feed trait *generation*, which `DARWIN_READ_TRAITS` overwrites at
startup. `alpfe` and `scav_rat` are safe because they are plain `&DARWIN_PARAMS` scalars read directly by
`DARWIN_READ_PARAMS`. (The growth pair `Smallgrow`/`Biggrow` is trait-overridden too — it lives in `PCMAX`
in `data.traits` — but it is unobservable-by-construction and excluded from the 4-observable denominator;
see §5.)

**Smoking gun (proof the override is live, not hypothetical):** the two files already disagree. `data.darwin`
`&DARWIN_RANDOM_PARAMS` says `val_R_PICPOC = 0.04245`; `data.traits` `&DARWIN_TRAITS` carries
`R_PICPOC = 0.0418860`. If generation were authoritative at runtime the loaded array would read `0.04245`.
It does not — the frozen `data.traits` array is what the model uses. Editing `val_R_PICPOC` would leave
`0.0418860` untouched.

---

## 1. Why the override happens (Darwin source precedence)

`darwinproject/darwin3` (branch `darwin`), `pkg/darwin/darwin_init_fixed.F`, initializes traits in this
order:

```
CALL DARWIN_RANDOM_INIT(darwin_seed, myThid)
#ifdef DARWIN_RANDOM_TRAITS
      CALL DARWIN_GENERATE_RANDOM(myThid)     ! uses &DARWIN_RANDOM_PARAMS: smallgrow, biggrow,
#else                                         !   diatomgraz, val_R_PICPOC  -> FILLS trait arrays
      CALL DARWIN_GENERATE_ALLOMETRIC(myThid)
#endif
      ...
CALL DARWIN_READ_TRAITS(iUnit, oUnit1, myThid)  ! reads &DARWIN_TRAITS from data.traits -> OVERWRITES
```

`DARWIN_READ_TRAITS` runs **last**, so the explicit `&DARWIN_TRAITS` arrays in `data.traits`
(`R_PICPOC`, `PALAT`, `PCMAX`, …) win over anything generation produced. `data.traits` in the v05 config is a
fully populated, namelist-echo-formatted file (`2*4.188600000000000E-002` etc.) — i.e. traits were generated
once, dumped, and are now **read back frozen** so the state estimate reproduces. That freeze is exactly why
the generation scalars in `data.darwin` are inert.

`alpfe`/`scav_rat` take a different path: they are read by `DARWIN_READ_PARAMS` from `&DARWIN_PARAMS` and
never touched by the trait machinery — no override.

---

## 2. The v05 array layout (7 plankton types)

From `MITgcm-contrib/ecco_darwin` `v05/llc270/input/data.traits` `&DARWIN_TRAITS`. Type identities inferred
from the trait flags (`ISPHOTO = 5*1,2*0`; `HASSI = 1,6*0`; `HASPIC = 0,2*1,4*0`; `ISPRED = 5*0,2*1`):

| type | identity | key flags |
|---|---|---|
| 1 | **diatom** (silicifier) | `HASSI=1`, `R_SIC≠0`, `ISPHOTO=1`, `ISPREY=1` |
| 2 | large calcifier (coccolithophore) | `HASPIC=1`, `R_PICPOC≠0` |
| 3 | small calcifier | `HASPIC=1`, `R_PICPOC≠0` |
| 4,5 | small phytoplankton | photo, no Si/PIC |
| 6 | small zooplankton | `ISPRED=1`, `GRAZEMAX≠0` |
| 7 | large zooplankton | `ISPRED=1`, `GRAZEMAX≠0` |

Relevant loaded values (verbatim):

```
R_PICPOC =  0.0, 2*4.188600000000000E-002, 4*0.0,              ! types 2,3 = 0.0418860
PCMAX    =  2*2.630471380471380E-005, 3*1.673085962889080E-005, 2*0.0,   ! per-second
PALAT    =  35*0.0,  0.169146, 0.180, 3*1.0,  2*0.0,  0.845730, 0.900, 3*0.200,  2*0.0,
```

`PALAT` is `PALAT(iPrey, iPred)` flattened column-major (prey fastest), 7×7 = 49 entries. Predators 1–5 are
non-predators, so the first `35*0.0` are their (empty) columns. Predator 6 = entries 36–42, predator 7 =
entries 43–49. **The diatom (prey type 1) palatability entries are:**

- entry **36 = 0.169146** — diatom → small zooplankton (pred 6)
- entry **43 = 0.845730** — diatom → large zooplankton (pred 7)

The GF-tuned "diatomgraz" optimum (Menemenlis 2019 deck ≈ 0.846) equals entry 43. Treat the diatom's
palatability as one dimensionless multiplier and perturb **both** entries by the same factor (see §3, and
the caveat there).

---

## 3. The perturbation recipe (4 params × symmetric two-sided FD)

**Step sizes.** Use **geometric (multiplicative)** steps at **two magnitudes, ×÷1.1 and ×÷1.2** (≈ ±10 % and
±20 %), one parameter at a time, plus one shared control at the Carroll optimum. Geometric steps make the
central difference symmetric **in log space**, matching the surrogate table
(`d ln⟨tracer⟩ / d ln param`, `surrogate_jacobian_validation.md` §3). Two magnitudes give the mandatory
**finite-difference-convergence / nonlinearity check**: compare the log-slope at ×1.1 vs ×1.2 — if they
disagree materially the step is in the nonlinear regime. **Do not** reuse Carroll's archival perturbations —
they are v4-era, mostly one-sided, and the scavenging perturbation is **+500 %**, far too large for a local
derivative near the v05 optimum.

Central log-sensitivity per tracer T:  `S ≈ [ln T(p0·s) − ln T(p0/s)] / (2 ln s)`, evaluated at `s = 1.1`
and `s = 1.2`.

**Run count:** 4 perturbed runs/param (÷1.2, ÷1.1, ×1.1, ×1.2) × 4 params = **16 perturbed + 1 control = 17
runs**. The minimal 8-run version (±10 % only) yields the local Jacobian but *skips* the convergence check —
do the 17-run version.

### 3a. `alpfe` — `data.darwin`, `&DARWIN_PARAMS`  (p0 = 0.92831)

```
ALPFE   =  0.92831,      ! control
```
| step | ÷1.2 | ÷1.1 | ×1.1 | ×1.2 |
|---|---|---|---|---|
| `ALPFE` | 0.773592 | 0.844100 | 1.021141 | 1.113972 |

### 3b. `scav_rat` — `data.darwin`, `&DARWIN_PARAMS`  (p0 = 6.02502315E-7 s⁻¹)

```
SCAV_RAT        =   6.02502315E-7,   ! control
```
| step | ÷1.2 | ÷1.1 | ×1.1 | ×1.2 |
|---|---|---|---|---|
| `SCAV_RAT` | 5.020853E-7 | 5.477294E-7 | 6.627525E-7 | 7.230028E-7 |

### 3c. `R_PICPOC` — `data.traits`, `&DARWIN_TRAITS`  (p0 = 0.0418860, types 2 & 3)

Scale **both** nonzero entries together (keep the `2*` shorthand):
```
R_PICPOC =  0.0, 2*4.188600000000000E-002, 4*0.0,   ! control
```
| step | ÷1.2 | ÷1.1 | ×1.1 | ×1.2 |
|---|---|---|---|---|
| both `R_PICPOC(2:3)` | 0.0349050 | 0.0380782 | 0.0460746 | 0.0502632 |

e.g. the ×1.1 line becomes `R_PICPOC = 0.0, 2*4.607460000000000E-002, 4*0.0,`.

### 3d. `diatomgraz` — `data.traits`, `&DARWIN_TRAITS`, `PALAT` diatom prey column (entries 36 & 43)

Scale the two diatom-prey palatability entries (36 = 0.169146, 43 = 0.845730) by the same factor:
| step | entry 36 (→small zoo) | entry 43 (→large zoo) |
|---|---|---|
| ÷1.2 | 0.140955 | 0.704775 |
| ÷1.1 | 0.153769 | 0.768845 |
| ×1.1 | 0.186061 | 0.930303 |
| ×1.2 | 0.202975 | **1.014876** |

**Two caveats on `diatomgraz`, both load-bearing:**
1. **Ambiguity in Carroll's knob.** If Carroll's GF "diatomgraz" scaled only the dominant large-zoo term
   (entry 43 = 0.845730, which matches the documented optimum), restrict the edit to entry 43. Perturbing
   the whole diatom prey column (both 36 and 43) is the safe default for "diatom palatability as one
   multiplier"; resolve which Carroll used before treating the derivative as definitive.
2. **The ×1.2 run crosses 1.0** (entry 43 → 1.014876). Palatability is conventionally ≤ 1; confirm Darwin
   does not clamp/renormalize (which would corrupt the FD), or cap the +20 % diatomgraz run at entry 43 =
   1.0, or lean on the ±10 % slope for this parameter.

---

## 4. Verification — do NOT trust the input file; confirm in the startup echo

The point of the whole exercise. `DARWIN_READ_TRAITS` echoes the **effective** namelist after the override
via `WRITE(UNIT=oUnit, NML=DARWIN_TRAITS)`, and `darwin_init_fixed.F` prints
`' DARWIN_INIT_FIXED: opening data.traits'`. For each run, before trusting it:

1. **Confirm the override path executed:** grep the model log (`STDOUT.0000`) for
   `opening data.traits`.
2. **Confirm the perturbed trait actually loaded:** grep the echoed `&DARWIN_TRAITS` block for `R_PICPOC` /
   `PALAT` and read the number back. It must equal your perturbed value — **not** 0.0418860 (the frozen
   original) and **not** 0.04245 (the `val_R_PICPOC` generation scalar). Seeing your value there is the only
   proof the edit took.
3. **For `alpfe`/`scav_rat`:** grep the echoed `&DARWIN_PARAMS` block (also in `STDOUT.0000`) for `ALPFE` /
   `SCAV_RAT` and confirm the perturbed value.

If step 2 shows the old value, the run tested nothing — this is the exact silent failure this recipe exists
to prevent.

---

## 5. Preconditions the ensemble must satisfy (else the runs don't validate anything)

- **Compute target.** Pleiades was **decommissioned 2026-01-07**. Benchmark on **Athena / Aitken / Electra**.
  Run **one baseline + one perturbation** on the current system to size wall-clock and I/O before budgeting
  all 17.
- **Scope: 8–16 OAT runs give ONE LOCAL Jacobian** at the Carroll optimum, not the global manifold. State
  this explicitly — it calibrates the surrogate's *local* curvature (the Fisher eigenbasis lives here), it
  does not map identifiability globally.
- **Transient vs equilibrated sensitivities.** Short integrations measure *transient* response; the Fisher
  we transfer is the equilibrated 1995–2017 Jacobian. **Demonstrate convergence-with-integration-length:**
  compute each FD entry at ≥2 integration lengths and show it stabilizes. Hold **identical
  checkpoints/restart, forcing, and time-averaging windows** across every run (control + all perturbations)
  so the only thing that varies is the one parameter.
- **Adjoint ≠ Jacobian.** One adjoint integration returns `Jᵀr` (the gradient of a single scalar objective),
  not the observation×parameter Jacobian a Gauss-Newton Fisher needs. For 4 controls, **verified central
  differences are the correct route** (v05 has no turnkey Darwin-controls adjoint).
- **Push through the observation operators — not raw fields.** Compare the perturbation response only after
  the GCM fields go through the **same** operators as the inverse problem: correct depth (surface vs
  subsurface), seasonal **phase**, AOI **location** (the 3-AOI `bin_average` footprints:
  eqpac / natlsubpolar / southernoceanpac), the relevant **timescale**, and **observation-uncertainty
  weighting**. Raw tracer fields alone do not validate the surrogate Fisher. Darwin's own sink/rate
  diagnostics (`scvLosFe`, calcite production, etc.) establish *implementation consistency* only — they are
  the same model, not independent evidence.
- **The load-bearing test is the ranking.** Signs will agree by construction (the box reuses Darwin's source/
  sink forms). What must be checked is (a) per-entry magnitude ratio and (b) whether the **cross-parameter
  ranking by sensitivity-to-own-observable** matches the surrogate
  (`diatomgraz ≫ R_PICPOC > alpfe > scav_rat`). Only ranking agreement licenses transferring the surrogate
  Fisher eigenstructure — the sloppy/stiff directions and the EKI reparameterization — to ECCO-Darwin.

---

## 6. v05 ≠ v06 — cross-version mapping needed before calling this replication

v06 is **not** the same four-parameter problem, so a v06 rerun is not a replication of v05 without an
explicit physical mapping:

- **`scav_rat` → `scav_tau` + particle-class weights.** v06 reformulates iron scavenging from a single rate
  (`SCAV_RAT`, s⁻¹) to a timescale with per-particle-class weights (`scav_POC_wgt` / `scav_PSi_wgt` /
  `scav_PIC_wgt`). No one-to-one entry; a `scav_rat`↔`scav_tau` mapping must be derived.
- **Group-specific growth / palatability / R_PICPOC.** v06's new ecosystem carries these per plankton group;
  the v05→v06 array layout and grouping differ, so the diatom-prey and calcifier indices in §2 do not carry
  over unchanged.
- **Third iron source.** v06 adds **hydrothermal-vent iron forcing** — a deep, geographically-fixed source
  on top of dust (`alpfe`) and scavenging. That adds spatial structure the 0-D box homogenizes and could
  **shift or break the alpfe/scav_rat degeneracy** the identifiability story rests on.
- **Status.** v06 is unreleased ("in optimization", Zhang, ecco-support 2026-02-17); v05 remains the
  published/optimized target. Keep validating on v05; treat v06 as a monitored moving target.
  (See `docs/research_notes/2026-07-22_ecco_darwin_v06_research.md`.)

---

## 7. Provenance

- `MITgcm-contrib/ecco_darwin` (branch `master`), `v05/llc270/input/data.darwin` —
  `&DARWIN_PARAMS`: `ALPFE = 0.92831`, `SCAV_RAT = 6.02502315E-7`;
  `&DARWIN_RANDOM_PARAMS`: `smallgrow=0.66098`, `biggrow=0.43148`, `diatomgraz=0.83003`, `val_R_PICPOC=0.04245`
  (the generation scalars — inert at runtime).
- `MITgcm-contrib/ecco_darwin` `v05/llc270/input/data.traits` — `&DARWIN_TRAITS`: `R_PICPOC = 0.0,
  2*0.0418860, 4*0.0`; `PALAT` diatom-prey entries 0.169146 / 0.845730; `PCMAX = 2*2.6305E-5, 3*1.673E-5,
  2*0.0`. Loaded `R_PICPOC` (0.0418860) ≠ generation `val_R_PICPOC` (0.04245) — the override proof.
- `darwinproject/darwin3` (branch `darwin`), `pkg/darwin/darwin_init_fixed.F` — call order
  `DARWIN_GENERATE_{RANDOM,ALLOMETRIC}` then `DARWIN_READ_TRAITS` (last, overrides); prints
  `DARWIN_INIT_FIXED: opening data.traits`. `pkg/darwin/darwin_read_traits.F` — reads `&DARWIN_TRAITS`,
  echoes the effective namelist via `WRITE(UNIT=oUnit, NML=DARWIN_TRAITS)` (the verification target).
- Fetched read-only 2026-07-23; nothing launched, no login. Carroll optima and the box mapping cross-checked
  against `src/darwindiff/carroll6.py` and `reference_carroll6_param_values`.
