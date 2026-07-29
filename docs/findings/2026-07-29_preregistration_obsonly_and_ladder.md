# Pre-registration — observations-only array (232937) and the parameterisation ladder

**Written 2026-07-29 15:39:24 UTC, before any result existed.** Proof of priority, captured at
write time on AICR:

```
$ date -u +%F_%H:%M:%SZ
2026-07-29_15:39:24Z
$ for a in obsonly_mld obsonly_litic obsonly_mld_litic chl2w20; do ls /scratch/qi_zim_neu/overnight/$a/*.json | wc -l; done
0
0
0
0
$ tail -2 /scratch/qi_zim_neu/overnight/dd-overnight_232937_0.out
  epoch  250  per-seed joint loss: mean=4.561e+00
  epoch  500  per-seed joint loss: mean=4.039e+00
```

Array 232937 was submitted 2026-07-29T11:02:34 EDT; task 0 started 11:17:14 and is at epoch 500 of
2000; tasks 1-19 are `PENDING`. The ladder arms in §3 have not been submitted at all.

This file exists because the project has twice been saved by a control it wrote down in advance
(the `CHL2_W_EXTRA` P2 discriminating prediction, and the log-scale A/B's falsification condition)
and once been embarrassed by a number it interpreted after the fact (`diatomgraz` 35/50). The rule
below is fixed now so it cannot be tuned to the outcome.

---

## 1. The decision rule, stated before the data

**Every count is graded per-AOI (≥2-of-3). Cell-weighted counts are not evidence and are not
admissible under this pre-registration**, because the observations-only run already demonstrated a
straddle in which `scav_rat` reads 40/50 cell-weighted and 0/50 per-AOI.

**Every count is graded against its architecture-matched measured untrained baseline.** 1-input-
channel arms grade against `prior_ctrl_n50`; 2-input-channel arms grade against `prior_mld_n50`.

### 1.1 Threshold table — the count required to clear chance at P < 0.05

Computed from the measured baselines by exact binomial `P(X ≥ k | n=50, p=baseline)`. Baselines
measured at 0/50 use the rule-of-three upper bound 3/50 = 0.06, which is deliberately conservative.

| param | 1ch baseline | **1ch k\*** | P at k\* | 2ch baseline | **2ch k\*** | P at k\* |
|---|---|---|---|---|---|---|
| alpfe | 10/50 | **16** | 0.0308 | 16/50 | **23** | 0.0267 |
| scav_rat | 0/50 → 0.06 | **7** | 0.0289 | 0/50 → 0.06 | **7** | 0.0289 |
| Smallgrow | 6/50 | **11** | 0.0325 | 7/50 | **12** | 0.0402 |
| Biggrow | 0/50 → 0.06 | **7** | 0.0289 | 0/50 → 0.06 | **7** | 0.0289 |
| diatomgraz | 32/50 | **38** | 0.0495 | 34/50 | **40** | 0.0437 |
| R_PICPOC | 0/50 → 0.06 | **7** | 0.0289 | 0/50 → 0.06 | **7** | 0.0289 |

A count below `k*` is reported as **not above chance**. It is not reported as a recovery, is not
described with a percentage, and does not enter the abstract.

Note the asymmetry this table makes explicit: `diatomgraz` needs **40 of 50** to say anything at
all, while `R_PICPOC` needs **7**. That is a fact about the bounds, not about the ocean, and it is
the reason the retired 35/50 was never evidence.

---

## 2. Array 232937 — four arms, and what each one decides

| task | arm | config | channels | baseline |
|---|---|---|---|---|
| 0-4 | `obsonly_mld` | obs-only targets + `MLD_CHANNEL=1`, Darwin IC | 2 | `prior_mld_n50` |
| 5-9 | `obsonly_litic` | obs-only targets + `DARWIN_IC=0` | 1 | `prior_ctrl_n50` |
| 10-14 | `obsonly_mld_litic` | obs-only targets + MLD + `DARWIN_IC=0` | 2 | `prior_mld_n50` |
| 15-19 | `chl2w20` | flagship + `CHL2_W_EXTRA=20` | 1 | `prior_ctrl_n50` |

### 2.1 Q1 — does MLD lift `diatomgraz` on real observations? (`obsonly_mld`)

Reference: obs-only without MLD gave `diatomgraz` 11/50 against a 32/50 untrained baseline, i.e.
far *below* chance.

- **≥ 40/50** → `diatomgraz` is recovered from observations-only. The observations-only result is
  **3-of-4**.
- **< 40/50** → not above chance. The observations-only result is **2-of-4** and the honest sentence
  is "input-limited, and the MLD channel does not rescue it under observations-only targets."
- The existing `geo1+MLD` **10/10** (P = 0.021 against the same 0.68 baseline) is **not** superseded
  by a null here, because it is a different loss. If this arm fails, both facts get reported.

### 2.2 Q2 — how much of `alpfe` / `R_PICPOC` rests on Darwin's pickup? (`obsonly_litic`)

Reference with Darwin ICs: `alpfe` 50/50, `R_PICPOC` 28/50.

- `alpfe` **≥ 16/50** and `R_PICPOC` **≥ 7/50** → both survive a literature initial condition. The
  initial-condition half of the Darwin dependency is **closed**, and this is the single most
  load-bearing result of the batch.
- Either falls below its `k*` → that parameter's observations-only recovery was **partly resting on
  Darwin's pickup state**. This is a publishable negative and must be reported as one, not buried.
- Pre-committed interpretation of a partial outcome: `alpfe` surviving while `R_PICPOC` falls is the
  *expected* asymmetry, because `alpfe` is anchored by GEOTRACES iron while `R_PICPOC`'s Daniels
  anchor is a ratio whose denominator depends on the carbon state the IC sets. If the reverse
  happens, our mechanistic account is wrong and we say so.

### 2.3 Q1+Q2 — the strict arm (`obsonly_mld_litic`)

This is the only arm in which the targets **and** the initial condition are both free of Darwin
output. Forcing and DINN input channels are still Darwin, so even this arm is not end-to-end
independent, and that caveat ships with any number from it.

### 2.4 Q3 — does the `Biggrow` dose-response continue past W=8? (`chl2w20`)

Ladder so far: W=0 → 6/50, W=8 → 12/50, arm-to-arm Fisher p = 0.192 (directional only), with
`Smallgrow` flat at p = 1.000.

- `Biggrow` **≥ 19/50** at W=20 makes W=20-vs-W=0 significant by Fisher exact, and combined with a
  monotone 6 → 12 → 19+ ladder that is sufficient to state that `CHL2_W_EXTRA` improves `Biggrow`.
- `Biggrow` between 12 and 18 → the trend is real in sign and still underpowered. Report as
  directional. **Do not** rewrite the STATUS claim.
- `Biggrow` **≤ 12** → the dose-response has saturated or was a bump. Report the ladder as
  non-monotone and drop the lever as a route to `Biggrow`.
- **`Smallgrow` is the discriminating control in all three cases.** If `Smallgrow` also rises at
  W=20, the effect is generic up-weighting and the Fisher interpretation in H3 is wrong.
- Damage gate: `alpfe` and `R_PICPOC` must stay at or above their `k*`. A `Biggrow` gain bought by
  breaking the iron pair is not a gain.

### 2.5 The headline rule — fixed now

**Observations-only becomes the manuscript headline if and only if `obsonly_mld_litic` clears
3-of-4**, i.e. `alpfe` ≥ 23, `R_PICPOC` ≥ 7, and `diatomgraz` ≥ 40, with `scav_rat` expected at 0
and reported as a diagnosed failure.

- **3-of-4 in the strict arm** → observations-only is the headline. Targets and initial conditions
  both Darwin-free, three parameters recovered from real measurements, one failing for a stated
  reason.
- **2-of-4 in the strict arm** → the flagship stays the headline and observations-only becomes the
  strongest robustness section in the paper. This is not a demotion; it is the correct reading.
- **Accepted cost either way, agreed in advance:** the joint trio goes from 25/50 to **0/50** under
  observations-only, because `scav_rat` needs the Darwin-pattern term. We are trading the cleanest
  quantitative result in the paper for independence from Darwin's targets. That trade is only worth
  making at 3-of-4.

---

## 3. The parameterisation ladder — pre-registered before submission

Motivated by ADCME (Xu & Darve, slide 29), where the standard control for a neural field is a **free
pointwise field**, not a global scalar. Our published structural claim compares 406 network weights
against 6 scalars with nothing in between.

| rung | free values | switch | status |
|---|---|---|---|
| global scalar | 6 | `GLOBAL_SCALAR=1` | run, trio 0/50 |
| shared DINN (flagship) | 406 | default | run, trio 25/50 |
| **per-AOI DINN** | 3 × 406 | `PER_AOI_DINN=1` | **to run, n=50** |
| **free per-cell field** | **17,106** | `POINTWISE=1` (new) | **to run, n=50** |
| **free-field untrained** | 17,106 | `POINTWISE=1`, `NB23_LR=0` | **to run, n=50** |

The free field allocates 17,178 values over the full grids and 17,106 of them sit on ocean cells
(natlsubpolar is the only AOI with land: a 16x31 = 496-cell grid carrying 484 ocean cells). Quote
the ocean figure against DINN's weight count, because the 12 land cells are never gradient-connected.

The third rung exists because the flagship DINN is **shared across all three AOIs** while a free
field cannot be, so a naive pointwise arm confounds per-cell freedom with per-AOI freedom.

### 3.1 What each outcome means, decided in advance

- **Free field ≤ shared DINN on the trio** → the network is acting as a regulariser, exactly as
  ADCME reports for Navier-Stokes. Our claim strengthens from "per-cell structure is load-bearing"
  to "**the per-cell *network* is load-bearing**," which is the stronger and more interesting
  statement, and it is the one we currently write without having earned it.
- **Free field ≈ shared DINN** → the network is a convenient parameterisation, not a regulariser.
  The claim must be scoped to "per-cell **structure**," and the word "architecture" comes out of
  STATUS, the abstract and the manuscript.
- **Free field > shared DINN** → degrees of freedom are doing the work. This would be the most
  uncomfortable result available and it gets reported first, not last. It would also partly deflate
  the DINN and would need a held-out check before anything else is said about it.
- **Per-AOI DINN separates the axes.** If per-AOI DINN ≈ free field, the gain is AOI-specificity,
  not per-cell resolution.

### 3.2 The honest asymmetry in this test

The free field has ~17,100 free values against ~2,851 ocean cells' worth of observations, and the
real anchors are far sparser than that (GEOTRACES iron is roughly 14 surface cells). It is *expected*
to fit the training loss better. The pre-registered metric is therefore **per-AOI recovery against
Carroll**, not training loss, and a free field that fits better while recovering worse is the
predicted regularisation result rather than a surprise.

---

## 4. What would falsify the framework this session is building

The identifiability contract claims it can say what is inferable before the fit. Three ways it fails:

1. A parameter the contract marks **structurally identifiable** recovers at or below its `k*`.
2. A parameter the contract marks **non-identifiable** recovers decisively.
3. The free-field arm beats the DINN, which would mean the contract's field-row reasoning (the
   network as a restriction of admissible function space) has the sign backwards.

Any of the three gets written into the record before it gets explained.
