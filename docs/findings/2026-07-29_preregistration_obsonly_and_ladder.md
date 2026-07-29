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

### 3.1b ADDENDUM, added 2026-07-29 ~17:30 UTC, still before any ladder result

Written after counting the anchors and before any arm reported. This sharpens §3.1 rather than
replacing it, and it supplies a **second, independent** discriminator so the arm is not resting on a
single count.

**The mechanism, stated precisely.** In the flagship config `DARWIN_PATTERN_W = 1.0`, so every ocean
cell *is* touched by a target. But those targets are **z-scored**, and a z-score is invariant under
affine rescaling of the field. So the pattern term constrains the **shape** of the parameter field
and says nothing about its **magnitude** — while the per-AOI collapse measures exactly the magnitude.

Magnitude is pinned only by the **absolute** anchors, and those are sparse:

| AOI | ocean cells | absolute-anchor observations | ≤ % of cells |
|---|---|---|---|
| eqpac | 1071 | 95 (26 Fe surf, 28 Fe sub, 7 bSi, 34 Daniels) | 8.9 % |
| natlsubpolar | 484 | 56 (13, 13, 4, 26) | 11.6 % |
| southernoceanpac | 1296 | 27 (13, 14, 0, 0) | 2.1 % |
| **total** | **2851** | **178** | **≤ 6.2 %** |

So the free field carries **96 free values per absolute anchor**, and roughly 94 % of its cells are
constrained in shape but not in magnitude.

**This is exactly the regularisation channel, and it is not the one the naive framing assumes.** The
DINN's 1×1 convolutions force every cell's parameters to be a smooth function of that cell's SST, so
magnitude information from an anchored cell propagates to every unanchored cell with similar SST. A
free field has no such coupling: an unanchored cell's value is determined only by the shape term and
its initialisation.

> **⚠️ CORRECTION, same day, still before any ladder result. The paragraph above is WRONG for four of
> the six parameters, and I checked the code only after writing it.**
>
> An adversarial review pointed at `run_v3.0_joint_multi_aoi.py:1755-1771`, and it is decisive. The
> **PINN term is dense AND absolute**: it masks with `mask_f` over *every* ocean cell, normalises by
> `n_ocean_f`, and is **not z-scored** — it is a physical steady-state residual
> `rel_rate = (alpfe·PHI_DUST − scav_rat·86400·DFe·POC − Q_FE·growth) / DFe`, run at
> `NB23_PINN_WEIGHT = 3.0` in the ladder config. It carries **`alpfe`, `scav_rat`, `Smallgrow` and
> `Biggrow`** at absolute level at every ocean cell.
>
> So "94 % of cells are constrained in shape but not magnitude" is false for those four. They have a
> dense magnitude constraint everywhere, and the unanchored-cells-drift-to-init mechanism does not
> apply to them.
>
> **It survives for exactly two parameters**, and they are the ones that appear nowhere in the PINN
> term: **`diatomgraz`** (absolute anchor: 11 bSi cells) and **`R_PICPOC`** (60 Daniels cells, and
> *zero* in the Southern Ocean). For those two the argument stands as written.
>
> **Two further corrections to the counts above.** 178 is the sum of per-term observation counts and
> double-counts co-located cells; the **union is 112 of 2851 ocean cells (3.93 %)**. And per-AOI
> anchored leverage on the graded mean is eqpac 5.51 %, natlsubpolar 8.06 %, southernoceanpac 1.08 %.
>
> **Consequence for the seed-variance prediction.** It should now be read as a *per-parameter*
> prediction rather than a global one: expect the free field's seed variance to exceed the DINN's for
> `diatomgraz` and `R_PICPOC`, and **not** necessarily for `alpfe`, `scav_rat`, `Smallgrow` or
> `Biggrow`. If the excess appears on the PINN-constrained four as well, the mechanism is something
> other than anchor sparsity and this reasoning does not explain it.

### 3.1c `diatomgraz` is UNGRADABLE in the pointwise arm, and that is known in advance

The free field initialises at `0.01·randn`, so at initialisation every cell sits essentially at the
bounds midpoint — the smoke run measured per-cell log-sd of **0.002 to 0.013**, i.e. a nearly uniform
field. `diatomgraz`'s midpoint is at rel offset **0.3675**, *inside* the 0.40 band. So an untrained
free field scores `diatomgraz` as recovered in **essentially every seed**, and its
architecture-matched baseline is **50/50 by construction**.

Under §1's own rule there is then **no `k*` ≤ 50** that clears that baseline at P < 0.05. `diatomgraz`
therefore **cannot be graded in the `pointwise` arm at all**, and reporting any count for it there
would be reporting the bounds.

This is stated now, before the arm reports, so it cannot look like an excuse afterwards. It is also
the sharpest possible illustration of why clause 3 of the contract exists: a parameter whose prior
midpoint sits inside the pass band is ungradable against a prior-dominated null, and the honest move
is to say so rather than to quote a number.

**A fully falsifiable prediction of the entire `pointwise_prior` arm, stated before it reports.**
Because the untrained free field is uniform at the bounds midpoint, every AOI receives the same
value, so each parameter must come back at either 50/50 or 0/50 with nothing in between:

| param | bounds midpoint | Carroll | rel offset | **predicted untrained** |
|---|---|---|---|---|
| alpfe | 0.525 | 0.92831 | 0.4345 | **0/50** |
| scav_rat | 1.515e-06 | 6.025e-07 | 1.5145 | **0/50** |
| Smallgrow | 1.05 | 0.66098 | 0.5886 | **0/50** |
| Biggrow | 1.05 | 0.43148 | 1.4335 | **0/50** |
| **diatomgraz** | 0.525 | 0.83003 | **0.3675** | **50/50** |
| R_PICPOC | 0.7525 | 0.04245 | 16.7267 | **0/50** |
| **trio** | — | — | — | **0/50** |

Any deviation from this table falsifies the reasoning in §3.1b/§3.1c, and in particular an
intermediate count (not 0 and not 50) would mean the initialisation spread is larger than the smoke
run measured and the whole uniform-at-init argument is wrong.

> **✅ CONFIRMED at n=10 before the main arm ran — job 233723, `verify_run` path, exit 0.**
> The table was written first, then tested. All seven rows matched:
>
> | param | predicted | measured | |
> |---|---|---|---|
> | alpfe | 0/10 | **0/10** | MATCH |
> | scav_rat | 0/10 | **0/10** | MATCH |
> | Smallgrow | 0/10 | **0/10** | MATCH |
> | Biggrow | 0/10 | **0/10** | MATCH |
> | **diatomgraz** | **10/10** | **10/10** | MATCH |
> | R_PICPOC | 0/10 | **0/10** | MATCH |
> | **trio** | **0/10** | **0/10** | MATCH |
>
> No intermediate count appeared anywhere, so the uniform-at-init argument holds: the untrained free
> field really is a near-constant field at the bounds midpoint, and each parameter is all-or-nothing.
>
> Two consequences are now measured rather than argued. **`diatomgraz` is ungradable in the
> `pointwise` arm** — its untrained baseline is saturated, so no `k*` exists and no count from that
> arm means anything. And **the trio comparison is safe**, because the untrained free-field trio is
> 0/10 exactly as the untrained DINN trio is 0/50, so the pre-registered headline in §3.1 rests on a
> hard zero on both sides.

Note the trio is **unaffected** by the `diatomgraz` problem: `scav_rat` at rel 1.51 and `R_PICPOC` at
rel 16.7 both give 0/50, so the untrained trio is 0/50 for the free field exactly as it is for the
DINN. **The pre-registered headline comparison in §3.1 is stated on the trio and is therefore safe.**

**Second pre-registered discriminator: SEED VARIANCE.** If the mechanism above is right, the free
field's per-AOI collapsed value should be **more variable across seeds** than the DINN's, because
94 % of its cells are free to drift with initialisation while the DINN ties them to SST. Concretely:

- **Predicted:** seed standard deviation of the per-AOI collapsed value is *larger* for `pointwise`
  than for the flagship on the same parameter and AOI. The flagship's seed CV is documented at
  0.08–0.14.
- **If free-field seed CV ≈ flagship seed CV**, the coupling story is wrong and a recovery
  difference must be explained some other way.
- **If free-field seed CV is larger AND its recovery is worse**, the two observations agree and the
  regularisation reading is supported by two independent measurements rather than one count.

**Third, cheap check that costs nothing extra.** The collapse instrumentation added today records
per-cell `log_sd` on every seed. The free field should show a **larger** per-cell log-sd than the
DINN, since the DINN cannot produce a rough field through 1×1 convolutions on a smooth SST input.
If the free field's log-sd is *not* larger, it did not actually use its extra freedom, and the whole
comparison is uninformative rather than negative.

**A confound this addendum does NOT dissolve.** The obs-only configs set `DARWIN_PATTERN_W = 0`,
where unanchored cells have *no* target at all and would sit at initialisation. The ladder is run at
the flagship config precisely so that every cell has at least a shape target; a pointwise arm under
obs-only would be a different and much weaker experiment. Do not pool them.

The free field has ~17,100 free values against ~2,851 ocean cells' worth of observations, and the
real anchors are far sparser than that (§3.1b: **52 GEOTRACES surface bins across the three AOIs**,
plus 55 subsurface, 11 bSi and 60 Daniels, for 178 absolute-anchor observations). It is *expected*
to fit the training loss better. The pre-registered metric is therefore **per-AOI recovery against
Carroll**, not training loss, and a free field that fits better while recovering worse is the
predicted regularisation result rather than a surprise.

---

### 3.1d THE SHARP DISCRIMINATOR — the Southern Ocean R_PICPOC leg

Added ~18:00 UTC, before the `pointwise` arm reported. Free check on artifacts already on disk
(`ctrl_n50`, n=50, CPU-seconds), prompted by a red-team question about whether the headline is
secretly a 2-AOI result.

**The question.** Daniels CP:PP covers eqpac (34 cells) and natlsubpolar (26 cells) and has **zero**
southernoceanpac coverage — the loss term auto-gates off there. So is `R_PICPOC`'s 50/50 majority
always formed by the two *anchored* AOIs, making the biggest count in the manuscript a 2-AOI result
reported as a 3-AOI one?

**The answer: no, and the reason matters more than the question.**

| `R_PICPOC` leg | Daniels cells | passes |
|---|---|---|
| eqpac | 34 | 47/50 |
| natlsubpolar | 26 | 50/50 |
| **southernoceanpac** | **0** | **40/50** |

Only **3 of 50** majorities *required* the Southern Ocean leg, so the headline does not lean on it
and the count is honest as a 3-AOI number. But the SO leg passes **40/50 in an AOI with no anchor at
all**, and only one mechanism permits that: **pooling through the shared DINN.** The network learns
the `R_PICPOC` relationship from the two anchored basins and applies it in the third; gradient from
the Daniels residual reaches SO cells *only* through shared weights.

**This is the regularisation mechanism, measured on the flagship, at zero cost** — and it is a far
sharper ladder discriminator than the aggregate trio count.

> **PRE-REGISTERED.** A free per-cell field **cannot pool**. In the `pointwise` arm the Daniels
> residual is identically zero at every southernoceanpac cell (the mask is all-zero and the term
> gates off), so those cells receive **no gradient whatsoever** from the calcite anchor and must stay
> near initialisation, where `R_PICPOC`'s rel offset is **16.7**, far outside the band.
>
> - **Predicted:** the `pointwise` arm's `R_PICPOC` **southernoceanpac** leg collapses from **40/50**
>   to **≈0/50**, while its eqpac and natlsubpolar legs stay high because those cells carry anchors.
> - **Predicted consequence:** the per-AOI ≥2-of-3 count is *preserved* (the two anchored legs still
>   form a majority), so this appears as a **leg-level collapse with no headline-count collapse** —
>   precisely what an aggregate count hides.
> - **Falsifier:** if the free field's SO leg also passes at a high rate, something other than weight
>   sharing carries magnitude into unanchored cells and the pooling account in §3.1b is wrong.
>
> This does **not** apply to `alpfe` or `scav_rat`, which are held at absolute level in every cell by
> the dense PINN term (§3.1b correction). `scav_rat`'s leg pattern is in fact the mirror image —
> eqpac 8/50, natlsubpolar 19/50, **southernoceanpac 49/50** — so the Southern Ocean is where
> `scav_rat` is *easiest*, and it is the basin its per-AOI count leans on.

**Provenance note, and the repo's own guard caught me writing this wrong.** These leg numbers come
from **`ctrl_n50`**, the independent reproduction, whose `scav_rat` reads **26/50**. The *published
flagship* is `n50e2k_percell_trio` at **25/50**, and its own leg tally is eqpac 7, natl 20, SO 49.
The two runs agree to one seed, but they are different runs and the counts must not be merged. An
earlier draft of this paragraph attributed the reproduction's count to the flagship, and
`test_no_tracked_doc_binds_26_of_50_to_the_flagship` failed it on the spot. That is the exact
conflation that drifted across twelve documents in July and took two audits to undo, so the guard
earned its keep twice in one afternoon.

---

---

## 3.5 VERDICT — the strict arm landed, and the pre-registered rule FIRES

`obsonly_mld_litic`, n=50, `verify_run` **exit 0 VERIFIED & COMPLETE**, graded against the
architecture-matched `prior_mld_n50` (2ch). Read against §1.1's thresholds, fixed before any result
existed.

| param | count | pre-registered k\* (2ch) | measured null | P(≥obs) | verdict |
|---|---|---|---|---|---|
| **alpfe** | **50/50** | ≥23 | 0.320 | 1.81e-25 | **decisive** |
| **diatomgraz** | **50/50** | ≥40 | 0.680 | 4.22e-09 | **decisive** |
| **R_PICPOC** | **43/50** | ≥7 | ≤0.06 | 1.89e-45 | **decisive** |
| scav_rat | 0/50 | ≥7 | ≤0.06 | 1.00 | not above chance |
| Smallgrow | 6/50 | ≥12 | 0.140 | 0.719 | not above chance |
| Biggrow | 3/50 | ≥7 | ≤0.06 | 0.584 | not above chance |

**Three of four observables clear their pre-registered thresholds, in the arm where the targets AND
the initial conditions are both free of Darwin output.** Under §2.5 the headline rule fires:
**observations-only becomes the manuscript headline.**

Two things must travel with it, both foreseen:

- **`scav_rat` fails, and it is the expected failure with a stated reason.** It is pattern-driven,
  not anchor-driven, and the pattern terms are exactly what observations-only removes. The trio
  therefore goes to 0/50, which §2.5 accepted in advance as the price.
- **This closes the initial-condition half of the Darwin dependency, not the forcing half.** T, S,
  wind, atmospheric pCO₂ and the DINN input channels still come from Darwin fields.

**The straddle guard earned its place again.** `scav_rat` reads **21/50 cell-weighted against 0/50
per-AOI** here — the guard prints `INVERTS IT (per-AOI says zero)`. `Smallgrow` reads 41/50 versus
6/50 and `Biggrow` 27/50 versus 3/50. Anyone quoting cell-weighted from this run would report an
observations-only iron result, and two growth-parameter results, that do not exist.

### The free-field untrained null — prediction held on all six rows at n=50

`pointwise_prior`, n=50, `verify_run` exit 0. §3.1c predicted every entry before the arm ran:

| param | predicted | **measured** |
|---|---|---|
| alpfe | 0/50 | **0/50** |
| scav_rat | 0/50 | **0/50** |
| Smallgrow | 0/50 | **0/50** |
| Biggrow | 0/50 | **0/50** |
| **diatomgraz** | **50/50** | **50/50** |
| R_PICPOC | 0/50 | **0/50** |

Every seed returns k=1. The uniform-at-init argument is confirmed at full n, so **`diatomgraz` is
formally ungradable in the `pointwise` arm** (its null is saturated at 50/50, no `k*` exists) and the
**trio comparison is safe** (0/50 on both sides).

---

## 4. What would falsify the framework this session is building

The identifiability contract claims it can say what is inferable before the fit. Three ways it fails:

1. A parameter the contract marks **structurally identifiable** recovers at or below its `k*`.
2. A parameter the contract marks **non-identifiable** recovers decisively.
3. The free-field arm beats the DINN, which would mean the contract's field-row reasoning (the
   network as a restriction of admissible function space) has the sign backwards.

Any of the three gets written into the record before it gets explained.
