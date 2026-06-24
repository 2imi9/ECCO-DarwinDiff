# ADR 0001 — Differentiable Darwin calcite port (R_PICPOC / iPIC)

- **Status:** Proposed
- **Issue:** [#118](https://github.com/2imi9/ECCO-DarwinDiff/issues/118) (design); implementation gated to [#122](https://github.com/2imi9/ECCO-DarwinDiff/issues/122)
- **Spine:** D — R_PICPOC / Darwin calcite port (6-of-6), under epic [#124](https://github.com/2imi9/ECCO-DarwinDiff/issues/124)
- **Date:** 2026-06-24

---

## Context — the structural wall

R_PICPOC is the one Carroll-6 parameter the box-model learner cannot recover. The
diagnosis (docs/findings/rpicpoc_ratio_structural.md, 2026-06-15, plus the 2026-06-24
H200 resolution result) isolates the cause to **calcite forward-model fidelity** — not
the estimator, not the information content, not seasonality, and not spatial resolution.
Each of those four candidate axes has been independently falsified:

1. **Estimator / information axis — SOLVED, not the wall.** A per-cell PIC:POC ratio
   loss recovers R_PICPOC in eqpac **10/10 seeds** without invoking the iron-pair mutex.
   This proves the earlier failure was a *design error* (separate-magnitude absolute
   anchors that admit a degenerate `(R_PICPOC, mort)` pair), not fundamental
   unidentifiability. The parameter is locally identifiable from a single AOI.

2. **Seasonal axis — EXCLUDED (null space).** A forward-model probe shows seasonal PIC
   is z-score invariant to R_PICPOC (Δmax = 0.000). The box has no seasonal calcite
   biology; organic and calcite production are phase-locked (corr = 0.94). Seasonality
   adds no constraint on R_PICPOC.

3. **Forward-model fidelity — THE WALL.** Ratio loss works **only** in eqpac. Darwin's
   realized PIC:POC varies ~**100×** across AOIs (eqpac ~0.033, N Atl ~0.68, SO ~0.0067;
   **corrected 2026-06-24** by direct recompute from the v05 target caches — the earlier
   "N Atl 0.9 / SO 1.4" was `rpicpoc_ratio_structural.md` prose mislabeling a *recovered
   degenerate* R_PICPOC as Darwin's realized ratio; all true values sit *below* the 0.8
   cocco rain-ratio ceiling, so this is plain cocco-rain-ratio variability, not standing-stock),
   driven by coccolithophore blooms. The box has a single rigid scalar ratio at one
   R_PICPOC and therefore cannot reproduce that spatial spread. The "coccolith-only"
   mitigation (`USE_COCCOLITH_ONLY_CALCITE=True`) backfires — it breaks the iron pair
   to 0/10. Across a 25-arm structural campaign, **0/10** arms achieved co-recovery
   (both params Calibrated in ≥2 AOIs); the lone success was ratio-loss eqpac, a single
   AOI.

4. **Resolution axis — EXCLUDED (new data, 2026-06-24, H200, n=10 matched eqpac).**
   Resolution is **not** the lever; both resolutions fail catastrophically, and native
   is actually *worse* (unstable scatter):

   | Resolution     | R_PICPOC Cal ≥1 seed | Mean   | SD    | vs Carroll target 0.042 |
   |----------------|----------------------|--------|-------|-------------------------|
   | Native-LLC270  | 2/10                 | 0.40   | 0.50  | 9.5× high, unstable     |
   | 1° standard    | 0/10                 | 0.021  | —     | 0.5× low                |

**Verdict.** Estimator (10/10), information (per-cell identifiable), seasonality
(null-space), and resolution (native 2/10) are all ruled out. The box's rigid calcite
physics is the exclusive bottleneck. Only a **differentiable Darwin calcite port** —
which carries coccolithophore-PFT-specific production and ballasted PIC sinking — paired
with native resolution can reproduce the coccolithophore-driven spatial PIC:POC
variation required for 6-of-6 recovery.

The calcite mechanics were verified against the **actual v05 source**, not the current
GitHub HEAD. Per v05's `readme.txt` build recipe, ECCO-Darwin v05 (Carroll 2022) pins
`darwinproject/darwin3` at commit **`24885b71`** and **overrides `darwin_plankton.F`** with
its own `v05/llc270/code_darwin/` copy. The authoritative calcite code is therefore that
override — *not* branch HEAD (an earlier verification against HEAD was the wrong version;
the Naviaux-2019 Ω-dissolution mode in HEAD post-dates v05). Verified directly in v05's
`code_darwin/darwin_plankton.F` (2026-06-24): per-PFT `R_PICPOC(j)` production, a single
prognostic `iPIC` tracer, **constant-rate `disscPIC = Kdissc*PIC`**, and the
`gTr(iALK) -= 2*(consumDIC_PIC - disscPIC)` coupling are all present — so the port design
below holds. **Three deltas vs the generic-HEAD wording that follows:**

> 1. **Production couples to DIC uptake, not a growth *rate*.** v05 has
>    `consumDIC_PIC += uptakeDIC*R_PICPOC(j)` (the carbon-fixation flux). Read every
>    `growth[j]*R_PICPOC[j]` below as *carbon-uptake* × ratio; the box must tie production
>    to its DIC/carbon-uptake term, not a bare growth rate.
> 2. **v05 has NO `disscSelect` switch — constant-rate ONLY.** The Ω-dependent
>    Naviaux-2019 / Keir modes are a *post-v05* darwin3 addition and do not exist in v05's
>    code. This **resolves Part-5 item 5** (no need to ask Jon to confirm `disscSelect=0` —
>    v05 has no other mode) and makes the port strictly *simpler*: there is no branch to
>    hard-select; the chemistry is constant-rate by construction.
> 3. **`DARWIN_NINE_SPECIES_SETUP` is enabled** (v05 `DARWIN_OPTIONS.h`), so `has_pic[j]`
>    must be assigned within v05's 9-species trait layout — sharpens Part-5 item 4.

The only items still genuinely Jon-gated are the **v05 config numeric values** (not in the
public repo): `Kdissc`, `wPIC_sink`, the calibrated cocco `R_PICPOC`, and which 9-species
index calcifies — see [Review with Jon](#part-5--review-with-jon-gate-before-122).

---

## Decision

Add a single prognostic calcite tracer (`iPIC`) to the box per-column state and replace
the rigid scalar-ratio calcite chemistry with the **coccolithophore-gated, growth-tied,
constant-rate-dissolution** formulation from Darwin 3 — written so it is clean for
reverse-mode autograd. The box state grows **15 → 16** tracers per 2-layer column. No new
layers, no stiff state, no implicit solve.

### Part 1 — Coccolithophore-PFT + calcite formulation, state delta, autograd plan

#### 1a. Coccolithophore PFT identity (structural, not learned)

Darwin gates calcification per-PFT: `hasPIC(j)` is 1 for the calcifying PFT and 0
otherwise, which sets `R_PICPOC(j)=0` for all non-calcifiers
(`DARWIN_TRAITS.h:20,98,377`; `darwin_generate_allometric.F:208,256`). Port this as a
**fixed boolean mask** `has_pic[j]` and define the effective ratio

```
R_PICPOC[j] = has_pic[j] * r_picpoc_param[j]
```

so the ratio is structurally zero off the cocco PFT. `r_picpoc_param` is the learnable
Carroll-6 target (active only where `has_pic[j]=1`). The gate is a **multiply**, never an
`if hasPIC:` branch (data-independent → autograd- and `torch.compile`-clean).

In the box's 5-PFT layout the calcifying PFT is the large-eukaryote pool (Chl2 / `P_lge`),
which the existing `USE_COCCOLITH_ONLY_CALCITE` doc already treats as the
coccolithophore proxy. **Which PFT index carries `has_pic=1` is a Jon-gated config item**
(Part 5).

#### 1b. Calcite production tied to coccolithophore growth

Production is the DIC→PIC calcification flux, tied to per-PFT growth (mirrors
`darwin_plankton.F:1243`), with `growth[j]` the per-PFT carbon-specific growth the box
already computes:

```
consumDIC_PIC = Σ_j  growth[j] * R_PICPOC[j]      # nonzero only on cocco PFT
```

Carbonate-system coupling, applied exactly as source:

```
dDIC += -consumDIC_PIC                            # CaCO3 formation consumes DIC   (line 1491)
dALK += -2 * (consumDIC_PIC - disscPIC)           # ALK 2:1, net of dissolution    (line 1638)
dPIC += +consumDIC_PIC                            # PIC mass enters the iPIC pool
```

> **Routing simplification (FLAG for Jon).** In full Darwin the PIC *mass* reaches
> `gTr(iPIC)` through the loss pathways — grazing `graz2PIC = Σ preygraz[j]*R_PICPOC[j]`
> (`darwin_plankton.F:1881,1901`) and mortality/exudation
> `exude_PIC = Σ mort_c[j]*R_PICPOC[j]` (`:2042,2202`). For the reduced 2-layer box the
> conservative simplification is to source `iPIC` **directly at production**
> (`dPIC += consumDIC_PIC`) rather than re-deriving the grazing/mortality split. This is a
> box-vs-full-Darwin fidelity choice; it does **not** change the tier story or the
> recovery target. See Part 5.

#### 1c. Ballasted PIC sinking (own velocity)

PIC sinks at its **own** ballast velocity `wPIC_sink`, distinct from organic sinking
(`darwin_sinking.F:85-87,200-201`). Vertical finite-difference flux between the two box
layers (upper `dz_up = h1`, lower `dz_low = h2`):

```
flux        = wPIC_sink * PIC_upper
dPIC_upper += -flux / dz_up
dPIC_lower += +flux / dz_low
```

#### 1d. Constant-rate dissolution (the non-stiff branch)

v05 uses `darwin_disscSelect = 0` (default), the **pure first-order constant-rate**
branch — *not* the Ω-saturation branches that also exist in source
(`darwin_plankton.F:1559-1581`; `DARWIN_PARAMS.h:312-318`). The other two modes
(=2 Naviaux 2019 Ω-dependent; =1 Keir 1980 Ω power-law) are stiff / data-dependent and
are **not** ported:

```
disscPIC = Kdissc * PIC                           # Kdissc ≈ 1/(300*86400) s^-1   (line 1578)
dPIC += -disscPIC                                 # (line 1681)
dDIC += +disscPIC                                 # dissolution restores DIC      (line 1643)
```

Linear, no Ω, no saturation lookup, no Newton iteration. This is precisely why #118
stresses the non-stiff branch: reverse-mode autograd flows cleanly through the entire
calcite chemistry.

#### 1e. Per-layer tendency assembly (fresh-tensor, no in-place)

Accumulate into a **fresh** tendency tensor — never `+=` on a leaf/view in the autograd
path (source does `gTr(iPIC)=gTr(iPIC)-disscPIC` repeatedly; do not transliterate):

```
d_pic_L1 = consumDIC_PIC_L1 - disscPIC_L1 - flux/dz_up                  # surface
d_pic_L2 = consumDIC_PIC_L2 - disscPIC_L2 + flux/dz_low - export_deep   # subsurface
```

#### 1f. State-vector delta

- **+1 prognostic tracer** `iPIC`: box state **15 → 16** per 2-layer column.
- **New learnable params:** `r_picpoc_param[j]` (Carroll-6 target, active only where
  `has_pic[j]=1`).
- **New constants:** `Kdissc`, `wPIC_sink` (fixed unless explicitly also recovered).
- **New structural mask:** `has_pic[j]` (fixed boolean, not learned).
- **No** new layers, **no** new stiff state.

#### 1g. Autograd-cleanliness plan (the source hazards to replace)

The Fortran source is full of gradient-killers that must NOT be transliterated:

| Source hazard | Location | Port replacement |
|---|---|---|
| In-place accumulation `gTr(iPIC)=gTr(iPIC)-…` | pervasive | Build a fresh `d_pic` tensor; no `+=` on leaf/view in autograd path |
| Hard read-time clamp `PIC=MAX(0,Ptr(iPIC))` (zeros gradient when PIC<0) | `darwin_plankton.F:443`, `darwin_sinking.F:85` | **Drop the clamp** (preferred: linear dissolution + small dt keeps PIC≥0, negativity rare) — document the choice; alternatives are softplus or log/exp-space state |
| Data-dependent dissolution `IF(disscSelect.EQ.2/1/else)` and nested `IF(omegaCl<1)…` | `darwin_plankton.F:1559-1581` | Hard-select the constant-rate branch at **trace time** (Python compile-time constant — fine for `torch.compile`); never port the runtime `IF` |
| Per-PFT calcite gate `IF hasPIC` | implicit | Multiply by `has_pic[j]` (data-independent), not an `if` |

The combination of linear dissolution + growth-tied production is smooth and
differentiable everywhere; there is no implicit/Newton solve, so the calcite chemistry
is autograd-clean by construction once the four hazards above are removed.

### Part 2 — Mapping table: Darwin iPIC / R_PICPOC(j) → box's current rigid calcite

What the port **ADDS** vs what **ALREADY EXISTS** in `carroll6_5pft_2layer.py`:

| Aspect | Darwin 3 (source-verified) | Box today | Port action |
|---|---|---|---|
| **iPIC tracer** | One prognostic `iPIC` per cell (`DARWIN_INDICES.h:29,57`, `iPIC=iPOSi+1`) | **EXISTS:** two layer tracers `PIC_1` (state[7], surface L1) and `PIC_2` (state[12], subsurface L2), carroll6_5pft_2layer.py:7,12 | **KEEP** the 2-layer PIC_1/PIC_2 columns; **ADD** the 16th-tracer slot semantics (per-column state 15→16) and re-source production from cocco growth instead of scalar mortality |
| **R_PICPOC** | **Per-PFT** `R_PICPOC(nplank)`, nonzero ONLY for cocco PFT (`DARWIN_TRAITS.h:98,377`) | **EXISTS but rigid:** single scalar `R_PICPOC = params[I_R_PICPOC]`, I_R_PICPOC=5 (lines 90,310); applied uniformly | **ADD** the PFT dimension `R_PICPOC[j] = has_pic[j]*r_picpoc_param[j]` (structural zero off cocco) |
| **Production source** | PFT-specific biomass loss, cocco only | **EXISTS as a toggle:** `USE_COCCOLITH_ONLY_CALCITE` (default False, line 153) routes `calcite_mort_src = mort_lge` (Chl2-only) vs `mort_total_1` (all 5 PFTs), lines 424-425 | **REPLACE** the toggle with the structural `has_pic[j]` mask + growth-tied `consumDIC_PIC`. The toggle approximated cocco selectivity; the mask makes it exact and removes the degenerate-pair failure mode that broke the iron pair |
| **PIC mass routing** | grazing `graz2PIC` + mortality/exudation `exude_PIC` (`:1881,1901,2042,2202`) | scalar mortality source feeds `dPIC_1` | **ADD** production-direct sourcing (`dPIC += consumDIC_PIC`) as the conservative box simplification — **FLAG to Jon** |
| **Dissolution** | Three modes; **v05 default `disscSelect=0`**: `disscPIC=Kdissc*PIC`, constant rate ~1/300-day (`darwin_plankton.F:1578`) | **EXISTS:** `R_PIC_DISSOL` (default R_REMIN=0.05 1/day, lines 187-192); `pic_dissolve = R_PIC_DISSOL * PIC_2` (line 390), constant rate, no Ω | **REUSE** the existing constant-rate hook; rename/retune to `Kdissc`. Box already matches the v05 non-stiff branch — **no Ω solver added** |
| **Sinking velocity** | Distinct `wPIC_sink` ballast (`darwin_sinking.F:85-87`) | **EXISTS:** `W_SINK_PIC` (default = W_SINK, line 177), separate from organic W_SINK; `pic_sink_out_L1 = W_SINK_PIC*PIC_1` (lines 384-385) | **REUSE** `W_SINK_PIC` as `wPIC_sink`; set the ballast (>W_SINK) value, no new mechanism |
| **DIC/ALK coupling** | `dDIC-=consumDIC_PIC` (1491), `dALK-=2(consumDIC_PIC-disscPIC)` (1638), `dDIC+=disscPIC` (1643) | **EXISTS:** `dDIC_1` includes `-R_PICPOC*calcite_mort_src` (lines 432-436), `dALK_1=-2*R_PICPOC*calcite_mort_src` (line 437), `dDIC_2=+poc_remin+pic_dissolve` (455), `dALK_2=+2*pic_dissolve` (456) | **RE-EXPRESS** the existing 2:1 ALK / 1:1 DIC coupling against `consumDIC_PIC` (growth-tied) instead of the scalar mortality term; same stoichiometry |

**Net summary.** The port is overwhelmingly a **re-sourcing + gating** change, not new
machinery. The box already has the two PIC layers, a separate PIC sink (`W_SINK_PIC`), a
constant-rate dissolution hook (`R_PIC_DISSOL`, already matching v05's `disscSelect=0`),
and the DIC/ALK stoichiometry. What is genuinely **NEW** is: (i) the per-PFT
`R_PICPOC[j]` with the fixed `has_pic[j]` mask; (ii) growth-tied production
`consumDIC_PIC` replacing the scalar-mortality `USE_COCCOLITH_ONLY_CALCITE` toggle; and
(iii) treating PIC as the explicit 16th prognostic tracer with autograd-clean tendencies.

### Part 3 — Success criterion

The port **succeeds** iff it recovers R_PICPOC in **≥2 AOIs** simultaneously —
specifically reproducing the coccolithophore-driven realized PIC:POC of **~0.68 (N Atl)**
and **~0.0067 (SO)** (alongside eqpac ~0.033; corrected 2026-06-24 — see Context) — **WITHOUT collapsing the
iron pair** (`alpfe` / `scav_rat`).

Concretely, an accepted run must show, at n≥10 seeds with reported seed variance and
verified via `scripts/verify_run.py` (recompute-from-raw, exit 0):

- `R_PICPOC` Calibrated in ≥2 AOIs (the 0/10 co-recovery wall in
  rpicpoc_ratio_structural.md is broken), AND
- `alpfe` and `scav_rat` remain in their previously-recovered Calibrated tiers (no
  regression below the multi-AOI baseline — the iron pair must not drop toward 0/10 the
  way `USE_COCCOLITH_ONLY_CALCITE=True` caused).

This is the 6-of-6 condition. Anything less (single-AOI eqpac success, or ≥2-AOI
R_PICPOC bought by iron-pair collapse) is **not** acceptance.

### Part 4 — Memory / compute estimate vs the budget PORT rows

Baseline eager constant is **356 B/(cell·step)**. The port adds exactly **one** linear
prognostic tracer, state 15→16, so the multiplier the port must **VALIDATE** is

```
16 / 15 = x1.067   →  the LOW end of the documented x1.07–1.4 band
                      (docs/research_notes/2026-06-21_full_compute_budget.md §4)
```

The x1.2 central / x1.4 high entries in the budget table are conservative upper bounds
for added intermediates; the source confirms one *linear* tracer with cheap chemistry, so
the realized multiplier should land near **x1.07**, not x1.2. Validate against
measurement before trusting any figure below x1.2.

- **Eager:** 356 × 1.067 ≈ **380 B/(cell·step)**.
- **Compiled basis** (82.9 B/cell·step measured, Explorer H200,
  docs/findings/memory_scaling_compiled.md).

PORT rows (the only rows that attack R_PICPOC / 6-of-6), budget-table x1.2 vs the
x1.067 the port should actually hit:

| Tier | Config | Unported | Budget x1.2 | Realized x1.067 | Lands on |
|---|---|---|---|---|---|
| **T9**  | PORT native time-mean ×1   | 2.57 GiB | 3.09 GiB | **~2.74 GiB** | **1× RTX 5090** |
| **T10** | PORT native seasonal ×1    | 25.73 GiB | 30.88 GiB | **~27.5 GiB** eager / **~6.4 GiB** compiled | **1× free Explorer H200** (compiled also fits the 5090) |
| **T11** | PORT global time-mean ×1   | — | 43.50 GiB | **~38.7 GiB** | **1× B200 + checkpoint** (435→87 GiB) once AICR onboards |

- **Compiled native seasonal ×1:** ~6.0 GiB unported → **~6.4 GiB** ported (x1.067) —
  still fits the **owned RTX 5090**, not just H200.
- **Compute wall-clock multiplier: x1.0** (budget §4). Constant-rate dissolution is
  benign (not Ω-stiff), so no extra solver iterations and flat per-step cost. The port is
  **ENGINEERING-gated** (writing this differentiable chemistry), **not** compute-gated;
  the tier story is unchanged (native seasonal ×1 stays one free H200).

### Part 5 — Review-with-Jon gate (BEFORE implementation #122)

Forward-model fidelity is Jon's domain. The **mechanics are source-verified** and need
no sign-off, but implementation (#122) MUST NOT start until Jon confirms the following
**v05 config-level** items (set in ECCO-Darwin v05, not present in the public repo):

1. **`Kdissc`** — the exact constant-rate dissolution coefficient (the ~1/300-day value).
2. **`wPIC_sink`** — the exact ballast sinking velocity (PIC faster than POC).
3. **Cocco R_PICPOC** — the calibrated R_PICPOC value for the calcifying PFT (sanity
   target vs Carroll 0.042).
4. **`has_pic[j]` assignment** — which PFT index carries `has_pic=1` in the box's 5-PFT
   layout (expected: the large-eukaryote / Chl2 pool).
5. **`disscSelect=0` confirmation** — that v05 actually ran the constant-rate branch, not
   the Keir (=1) or Naviaux Ω (=2) branches.
6. **iPIC-source routing** — sign-off on the **production-direct** simplification
   (`dPIC += consumDIC_PIC`) vs full grazing/mortality routing (Part 1b flag). Box-fidelity
   decision; does not change the tier story.

---

## Consequences

### Positive

- Breaks the **0/10 co-recovery wall**: coccolithophore-specific production lets one
  R_PICPOC reproduce the ~23× spatial PIC:POC spread that a single rigid scalar cannot,
  which is the precondition for 6-of-6.
- **Cheap:** +1 linear tracer, x1.067 memory, x1.0 wall-clock. Native seasonal stays a
  single free Explorer H200; the compiled path even fits the owned RTX 5090.
- **Low-risk mechanics:** all four chemistry pieces (iPIC, per-PFT R_PICPOC, constant-rate
  dissolution, ballasted sinking) are source-verified; the box already has the dissolution
  and sinking hooks, so most of the work is re-sourcing + gating, not new solvers.

### Risks / what could STILL fail

- **Iron-pair collapse persists.** The `USE_COCCOLITH_ONLY_CALCITE=True` precedent broke
  `alpfe`/`scav_rat` to 0/10 by starving the calcite signal of all-PFT support. Routing
  production through a single cocco PFT (`has_pic[j]`) could re-trigger the same collapse.
  The success criterion (Part 3) treats this as a hard gate; if it recurs, the port has
  not solved the problem even with ≥2-AOI R_PICPOC.
- **DIC/ALK budget coupling.** Production removes DIC and ALK (2:1) and dissolution
  restores them; re-sourcing these against growth-tied `consumDIC_PIC` instead of scalar
  mortality changes the carbonate-system budget the optimizer sees. A mis-scaled coupling
  could bias DIC/ALK targets or create a new degenerate direction. Must regression-test
  the carbonate closure (Part-6 step gate).
- **Positivity without clamping.** Dropping the `MAX(0,·)` clamp assumes linear
  dissolution + small dt keeps PIC≥0. If a multi-cycle seasonal spin-up under PARAM_BOUNDS
  extremes drives PIC negative, gradients/values degrade. Mitigation: monitor min(PIC);
  fall back to softplus or log-space state if negativity is observed (documented
  alternative in Part 1g). Note the existing `clamp(min=0.0)` floor (line 484) protects
  DIC/ALK but is itself a gradient hazard if it ever binds on the PIC path.
- **`has_pic[j]` mis-assignment.** If the Chl2 / large-eukaryote pool is the wrong
  coccolithophore proxy for an AOI, production lands on the wrong PFT and spatial PIC:POC
  will not track. Jon-gated (Part 5 item 4).
- **Routing simplification bites.** Production-direct sourcing skips the grazing/mortality
  split; if calcite export timing matters for the N Atl / SO bloom signal, the
  simplification could under-resolve it. Flagged to Jon (Part 5 item 6); revisit if ≥2-AOI
  recovery stalls.
- **Native instability carries over.** Native-LLC270 already gave unstable R_PICPOC
  scatter (2/10, SD 0.50) in the *unported* box. The port targets the forward-model gap,
  but does not by itself guarantee native numerical stability; watch seed variance.

### Neutral / accepted

- **Saturation physics deferred.** Constant-rate dissolution (no Ω) is a standing
  simplification, matching v05's `disscSelect=0`. Ω-dependent dissolution (Naviaux/Keir)
  is explicitly **out of scope** for this port and deferred to post-hoc observational
  fitting or future refinement.

---

## Implementation plan (#122 — incremental, test-gated)

Each step is independently verifiable; do not proceed until the prior gate passes. All
recovery numbers gate through `scripts/verify_run.py` (recompute-from-raw, exit 0); report
n≥10 with seed variance; DINN baseline only.

1. **Mask + per-PFT ratio (no behavior change).** Introduce `has_pic[j]` (fixed) and
   `R_PICPOC[j] = has_pic[j]*r_picpoc_param[j]`. With `has_pic` chosen so the effective
   source equals today's behavior, assert **bitwise-identical** forward output vs the
   current scalar path. *Gate: bitwise reproduction.*
2. **Re-source production to growth-tied `consumDIC_PIC`.** Replace
   `calcite_mort_src`/`USE_COCCOLITH_ONLY_CALCITE` with `consumDIC_PIC = Σ growth[j]*R_PICPOC[j]`;
   wire DIC (`-consumDIC_PIC`) and ALK (`-2(consumDIC_PIC-disscPIC)`). *Gate: carbonate
   closure regression test (DIC+ALK budget conserved to tolerance over a forward run).*
3. **Promote PIC to the explicit 16th tracer; autograd hygiene.** Assemble `d_pic` into a
   fresh tensor (no in-place), hard-select the constant-rate dissolution branch at trace
   time, multiply-gate `has_pic[j]`, and **drop the read-time clamp** on the PIC path.
   *Gate: `gradcheck`/finite-difference on `d(loss)/d(r_picpoc_param)`; `torch.compile`
   trace succeeds; min(PIC)≥0 over a representative run.*
4. **Wire `Kdissc` / `wPIC_sink`** from the existing `R_PIC_DISSOL` / `W_SINK_PIC` hooks to
   the Jon-confirmed v05 values (Part 5). *Gate: forward PIC:POC in eqpac stays ~0.033.*
5. **Memory/compute validation.** Measure eager B/(cell·step) and compiled basis; confirm
   the multiplier lands near **x1.067** (not x1.2) and that T9/T10 fit 5090/H200 per Part 4.
   *Gate: measured multiplier ≤ x1.2.*
6. **Recovery campaign (the real test).** Native-resolution, ≥2-AOI fit (eqpac + N Atl + SO).
   *Gate: Part-3 success criterion — R_PICPOC Calibrated in ≥2 AOIs AND iron pair not
   collapsed, n≥10, verified.*

---

## Open questions for Jon

(All six are the Part-5 gate items; mechanics are source-verified, these are v05
config-level and forward-model-fidelity calls in Jon's domain.)

1. Exact **`Kdissc`** (the ~1/300-day constant-rate dissolution coefficient)?
2. Exact **`wPIC_sink`** ballast velocity?
3. Calibrated **cocco R_PICPOC** value used in v05 (vs Carroll 0.042)?
4. Which PFT carries **`has_pic=1`** — confirm the large-eukaryote / Chl2 pool?
5. Confirm v05 ran **`disscSelect=0`** (constant-rate), not Keir (=1) / Naviaux Ω (=2)?
6. Sign off on the **iPIC-source routing** simplification (production-direct vs
   grazing/mortality-routed) as an acceptable box-fidelity decision?
