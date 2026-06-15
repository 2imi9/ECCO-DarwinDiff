# Absolute-units GLODAP alkalinity anchor vs the R_PICPOC ⊕ iron-pair mutex (box scale)

**Date:** 2026-06-15 · **Status:** COMPLETE — **NULL (mutex holds); NO-GO.** An
apparent co-recovery (13/20) passed the pre-registered reproducibility gate but
was falsified as a cell-weighted **averaging artifact** by per-AOI decomposition
+ a 5-lens adversarial panel + a Darwin-ALK-source control. Branch
`2imi9/schultz-jon-deck`, behind NEW default-OFF flags `ALK_ABS_W` /
`ALK_ABS_SOURCE` (legacy reproduces bitwise when unset). The Tuesday (2026-06-16)
deck is FINAL and **untouched**; the null leaves its framing intact and better
supported.

## Question

Does **any laptop-feasible lever** break the binary mutex
`R_PICPOC ⊕ {iron pair (alpfe + scav_rat) + diatomgraz}` — i.e. recover
`R_PICPOC` to Cal-grade **without collapsing the iron pair** — under the v3.2
Eppley config? The PIC magnitude anchor (`PIC_ABS_W`) recovers `R_PICPOC` 8/10
but wipes the iron pair → 0/10 (binary, dose-independent). Architecture levers
(PER_AOI_DINN, per-param gating, DINNDeep) are already falsified. Only **new
information** can move it, so we test the cheapest independent source:
**total alkalinity (ALK)**.

**Rationale (as proposed):** calcite formation changes ALK in a 2:1
stoichiometry — a carbonate counter-pump signature hypothesised to be
*independent* of the organic-export (POC/mort) budget. If ALK gives `R_PICPOC`
an independent handle, it could co-recover with the iron pair, unlike the PIC
anchor that wipes it.

## Forward-model analysis (registered BEFORE running — the a-priori prediction)

Read of `src/darwindiff/carroll6_5pft_2layer.py` (the box):

```python
# surface (L1) tendencies — calcite_mort_src = mort_total_1 by default
dPIC_1 = R_PICPOC * calcite_mort_src - pic_sink_out_L1     # line 423
dALK_1 = -2.0 * R_PICPOC * calcite_mort_src                # line 435
```

Two facts make a clean co-recovery *a-priori unlikely*:

1. **ALK shares PIC's exact factorization.** The ONLY process touching surface
   ALK in the box is calcite formation, and it enters as the **identical product
   `R_PICPOC × calcite_mort_src` (= `R_PICPOC × mort_total`)** that drives PIC.
   There is no nitrate/organic-alkalinity term, so the box's ALK is *not*
   "independent of the organic-export budget" — it is a pure calcite signal
   governed by the same product. Any observable that constrains
   `R_PICPOC × mort_total` cannot, by itself, split `R_PICPOC` from `mort_total`
   (which the iron pair + diatomgraz own). This is the factorization/
   identifiability degeneracy, restated: **ALK is informationally equivalent to
   PIC for the `R_PICPOC` / `mort_total` split.**

2. **The absolute ALK signal is IC-dominated (likely weaker than PIC).** Surface
   ALK has no source term, only the calcite sink, so over the 50-day box
   integration (`N_STEPS=200 × DT=0.25`) `ALK_1` barely drifts from its Darwin-IC
   initial value (~2360 mmol/m³). The calcite-driven drawdown is a tiny
   perturbation on a large IC-set baseline, and the scale-normalized MSE
   (`residual² / mean(target²)`, denominator ~2360²) makes the `R_PICPOC`-
   controllable part of the gradient very small. Contrast PIC, whose steady-state
   level `PIC_1 = R_PICPOC·mort_total / W_SINK_PIC` is small-magnitude and
   *directly* set by the product — a strong, scale-matched signal. So the ALK
   anchor may not even recover `R_PICPOC` (unlike PIC), let alone co-recover it
   with the iron pair.

**Registered prediction:** NULL (mutex not broken). Two candidate mechanisms,
distinguished by the run:
- **(a) Signal-weakness / IC-dominance:** `R_PICPOC` stays ~unrecovered and the
  iron pair is ~preserved (the anchor is too weak to perturb anything).
- **(b) Factorization mutex (PIC-like):** at large enough weight `R_PICPOC`
  recovers but the iron pair collapses → same binary mutex as PIC.

A clean co-recovery (`R_PICPOC` **and** iron pair both Cal-grade in the same
seed, reproducibly) would be the genuine surprise worth reporting and the only
GO outcome. Historical prior (v2.1 nb22) used GLODAP ALK as a *fit target* and
pulled `R_PICPOC` 360% → 74% but degraded the iron pair — consistent with the
mutex re-appearing.

## Method

- **Lever:** new `ALK_ABS_W` env var in `scripts/run_v3.0_joint_multi_aoi.py`
  (default `0.0` = OFF). When `> 0`, adds a scale-normalized absolute-units MSE
  between the box's surface `ALK_1` and a **real GLODAP TAlk** target, mirroring
  the existing `PIC_ABS_W` / `POC_ABS_W` absolute-anchor pattern exactly.
- **Target:** GLODAPv2.2016b mapped climatology `TAlk` (µmol/kg), surface level,
  AOI-subset, regridded (nearest) onto the AOI's Darwin 1° grid, converted to
  mmol/m³ via ρ_sw = 1025 (`glodap_loader.to_mmol_per_m3`). Real ship-CTD
  observations, no model in the loop — a genuinely out-of-sample observable.
- **Config = the v3.2 Eppley best** (the reproducible-5/6 operating point):
  `AOIS=eqpac,natlsubpolar,southernoceanpac`, `POSI_W=1.0`,
  `AOI_W_NATLSUBPOLAR=2.0`, `AOI_W_SOUTHERNOCEANPAC=2.0`, `CHL1_W_EXTRA=3.0`,
  `POSI_DARWIN_W=0.5`, `USE_EPPLEY_T=1`, 1500 epochs.
- **No forward-model change.** `ALK_1` / `dALK_1` already exist; Track A is a
  runner-side loss term only. `carroll6_5pft_2layer.py` is untouched by this
  experiment.

## Pre-registered design

- **Paired seeds 0–9 (n=10) per arm:**
  - **control** = Eppley best, `ALK_ABS_W=0` (re-run fresh for an exact paired
    comparison; reproduces the documented Eppley control bitwise).
  - **test** = + `ALK_ABS_W ∈ {1.0, 10.0, 100.0}` (dose sweep; a range up to an
    ALK-dominant weight so the IC-dominance/signal-weakness mechanism gets its
    fairest shot at actually moving `R_PICPOC`). _Top end raised from the initial
    {0.1, 1.0, 10.0} after the forward-model probe (below) showed the scale-
    normalized ALK R_PICPOC signal is ~60,000× weaker than PIC's — a clearly-inert
    0.1 was dropped and a forcing 100.0 added. Refinement made on the probe
    (setup) only, before any optimizer/sweep result._
- **Scoring:** `diagnostics.band_of` on `abs(recovered − Carroll)/abs(Carroll)`
  — **Cal-grade ≤ 0.40, Excellent ≤ 0.05.** Joint cell-weighted recovery (the
  default), per Carroll 2022 published values.
- **SUCCESS (GO):** `R_PICPOC` Cal-grade **AND** iron pair (`alpfe` + `scav_rat`)
  Cal-grade in the **same seed**, **reproducibly**. Screen n=10; **only if
  ≥ 2/10 seeds show co-recovery** do we extend to n=20 + split-half.
- **NULL (expected):** mutex re-appears (mechanism a or b). Write a clean
  confirmation; **do not change the deck.** A null confirms the limit is
  informational — i.e. the cluster/AICR case.
- **Anti-p-hack guards:** paired seeds, dose sweep (not a single weight),
  reproducibility gate before any n=20 extension, both candidate-null mechanisms
  named in advance. Single-seed 5/6 events are treated as flukes (the project has
  documented fluke 5/6 events that vanished on retest), not co-recovery.

## Forward-model probe (magnitudes; setup verification, run before the sweep)

_Filled in after the probe — quantifies IC-dominance: box `ALK_1` initial (IC)
vs final, calcite-driven drawdown, GLODAP target, IC-vs-GLODAP residual, and
∂ALK_1/∂R_PICPOC. Distinguishes which null mechanism to expect._

Probe (`%LOCALAPPDATA%\ddeck\alkabs\probe_alk_signal.py`, eqpac, Carroll params,
Eppley ON, 1071 ocean cells):

| quantity (masked mean) | value |
|---|---|
| GLODAP TAlk target | 2334.4 mmol/m³ |
| box ALK_1 initial (Darwin IC) | 2326.1 |
| box ALK_1 final (50-day box) | 2322.2 |
| **calcite-driven drawdown (IC − final)** | **3.91 mmol/m³ (~0.17%)** |
| IC − GLODAP residual | −8.2 (box IC already undershoots GLODAP) |
| final − GLODAP residual | −12.2 |
| `d(mean ALK_1)/d(R_PICPOC)` | −92.2 |
| `d(mean PIC_1)/d(R_PICPOC)` | +9.41 |
| **scale-normalized signal ALK** `|∂/∂Rpp|/target` | **0.039** |
| **scale-normalized signal PIC** `|∂/∂Rpp|/target` | **2340** |

**Two things the probe establishes (both point to a null):**
1. **The absolute ALK anchor carries ~60,000× less R_PICPOC signal than PIC**
   (0.039 vs 2340) — because the box's surface ALK is **IC-dominated** (calcite
   moves it only ~0.17%), while box PIC is **calcite-defined** (`PIC_1` runs
   0.0085 → 0.40 over the integration; R_PICPOC sets its entire magnitude). The
   scale-normalized ALK MSE is therefore near-inert on R_PICPOC at any reasonable
   weight.
2. **What little ALK gradient exists points the wrong way.** The Darwin IC
   alkalinity already *undershoots* GLODAP (−8 mmol/m³), and calcite drawdown
   makes the box final worse (−12). Minimizing the ALK residual therefore drives
   `R_PICPOC` *down* (less drawdown, higher ALK) — **away** from Carroll (0.042),
   toward 0. So the anchor cannot recover R_PICPOC even in principle; at most it
   degrades it.

This is a *stronger* a-priori null than "PIC-like mutex": the ALK anchor is
expected to leave R_PICPOC ~unrecovered (and possibly push it toward 0) while the
weak/mis-directed gradient leaves the iron pair ~intact — i.e. mechanism (a),
signal-weakness, with the gradient mis-directed. The sweep tests this directly
(and captures the indirect ALK→pCO2→F_CO2 carbonate coupling the probe's direct
∂ALK/∂R_PICPOC omits).

## Result — the short version

**NULL: the mutex holds.** The ALK anchor does **not** genuinely break
`R_PICPOC ⊕ {iron pair}`. An *apparent* co-recovery (13/20, plus 3/20 "6/6")
that passed the pre-registered reproducibility gate turned out, under adversarial
scrutiny + per-AOI decomposition, to be a **cell-weighted averaging artifact**:
`R_PICPOC` is recovered in **no single AOI** — the joint metric only crosses
Carroll because the per-AOI values straddle it. Decision: **NO-GO** (the expected
outcome). All runs uncommitted, default-OFF; the deck is untouched.

## Result — dose response (n=20 paired; seeds 0–9 + 10–19 split-half)

Config = v3.2 Eppley best. Compiled (triton-windows restored; numerically
equivalent to eager). Scored with `diagnostics.band_of` (Cal ≤0.40, Exc ≤0.05),
joint cell-weighted recovery.

| arm | ALK_ABS_W | mean/6 | iron pair | R_PICPOC (joint) | co-recovery | 6/6 | loss |
|---|---|---|---|---|---|---|---|
| c0 (control) | 0 | 3.85 | 18/20 | **0/20** | 0/20 | 0/20 | 40.0 |
| a1 | 1.0 | 3.85 | 18/20† | 0/20 | 0/20 | 0/20 | 40.0 |
| a10 | 10.0 | 4.00 | 17/20 | 2/20 | 2/20 (split 2+0) | 1/20 | 39.9 |
| **a100** | 100.0 | 4.35 | 14/20 | **14/20** | **13/20 (6+7)** | **3/20** | 40.2 |
| a300 | 300.0 (n=10) | 4.10 | 6/10 | 7/10 | 6/10 | 1/10 | — |
| a100d | 100.0, src=darwin (n=10) | 4.10 | 7/10 | 4/10 | 4/10 | 1/10 | — |

(† a1 ≈ control, as the forward-model probe predicted at low weight.)

At face value a100 *passed the pre-registered GO gate*: co-recovery reproduced in
both split-halves (6/10 + 7/10), control reproduced the documented Eppley baseline
exactly, recovered joint `R_PICPOC` sat on Carroll (0.040–0.057 vs 0.0425), and
total loss was flat. This looked like a genuine mutex break — the morning's
predicted null appeared falsified.

## The refutation — it is a cell-weighted averaging artifact

A five-lens adversarial panel (each reading the raw JSONs + box code) and a
direct **per-AOI decomposition** overturned the strong claim:

**No single AOI recovers `R_PICPOC`.** Of the 13 a100 co-recovery seeds, only
**2** have *any* AOI's `R_PICPOC` within Cal-grade. The structure is systematic:

| | eqpac (wt 1071) | natl (wt 482) | SO (wt 1280) | joint (cell-wt mean) |
|---|---|---|---|---|
| a100 per-AOI `R_PICPOC` | ~0.005–0.012 | ~0.06–0.08 | ~0.07–0.09 | **~0.045 ✅** |
| rel offset vs Carroll | 0.71–0.87 | 0.13–0.88 | 0.55–1.17 | ~0.05–0.35 |

The anchor applies a ~uniform **downward** pressure on `R_PICPOC` in every AOI
(consistent with the probe's `∂ALK/∂R_PICPOC < 0` and the IC-undershoot
mechanism): it drives eqpac toward 0, drags natl/SO down from far-too-high, and
the **cell-weighted mean crosses Carroll only because the per-AOI estimates
straddle it.** Worse, eqpac — the one AOI nearly right in control (0.034, ~20%
off) — is pushed to ~0.006 (87% off). Even the three "6/6" seeds have per-AOI
`R_PICPOC` offsets of 0.38–1.00. **This is a metric/aggregation artifact riding
on an under-determined forward model, not physical identifiability.**

**The artifact is specific to `R_PICPOC`; the metric is otherwise sound.** In the
control, every joint-Cal `alpfe` (18/20) and `scav_rat` (20/20) seed has ≥1 AOI
(median 2) genuinely in Cal-grade — the iron pair is per-AOI real. `R_PICPOC` is
the lone parameter that is per-AOI *un*identified in *every* AOI (even in
control), which is exactly why its joint metric is the one vulnerable to
straddling.

**Three independent corroborations:**
1. **Darwin-ALK source (a100d):** anchoring to Darwin's *own* ALK reproduces the
   identical straddle (eqpac 0.011, natl/SO 0.12) and artifactual co-recovery.
   So the effect is **generic absolute-ALK-magnitude deflation, not real-GLODAP
   information** — killing the "out-of-sample observable" framing (GLODAP also
   ≈ Darwin ALK to 0.36%, and GLODAP was in Carroll's own calibration set).
2. **Dose (a300):** 3× weight only deepens the deflation (eqpac → 0.014) and
   erodes the iron pair further (6/10) — never a genuine per-AOI recovery.
3. **Forward-model probe (pre-registered):** the box's surface ALK is calcite-
   only (`dALK_1 = −2·R_PICPOC·mort_total`, no nutrient/riverine source) and
   IC-dominated; matching GLODAP pins the cumulative drawdown to close a fixed
   Darwin-IC-vs-GLODAP offset (~8 mmol/m³) → uniform downward `R_PICPOC` pressure,
   not identification.

**Panel verdicts:** forward-model lens = **fatal** (claim does not survive);
scoring + circularity = serious (iron pair *erodes* — mean alpfe offset rises
0.31→0.38 with dose, 2 seeds newly Drifted; "without collapsing" and
"out-of-sample" both overstated); statistical = minor (numbers reproduce exactly,
pre-registration is sound, but co-recovery is band-fragile: 13/20 at Cal=0.40 →
5/20 at 0.30 → 0/20 at 0.20); over-weighting = minor ("flat loss ⇒ no tradeoff"
is a void argument, though the decomposed non-ALK loss does hold).

## Interpretation / decision

**The R_PICPOC ⊕ {iron pair + diatomgraz} mutex is NOT broken by an alkalinity
anchor.** `R_PICPOC` enters the box only as the product `R_PICPOC × mort_total`
(in both PIC *and* ALK), and the box's calcite-only, IC-dominated ALK budget
gives no independent per-AOI handle on the split. The apparent co-recovery was
the joint cell-weighted metric being fooled by straddling — confirmed by per-AOI
decomposition, the Darwin-source control, the dose-response, and five adversarial
lenses. This is the **same conclusion as the PIC anchor reached** (R_PICPOC is
box-scale unidentifiable), via a subtler failure mode. It **strengthens** the
cluster-gated / AICR framing rather than weakening it.

**Decision: NO-GO on adding a line to the talk.** The deck's existing framing
("R_PICPOC is the sole 6/6 wall, cluster-gated, exhaustive box-scale exclusion")
stands and is now *better* supported (a 7th exclusion: real + model alkalinity,
absolute-anchored, across a dose sweep). Nothing changes in the deck.

**Methodological catch worth keeping:** for a parameter that is per-AOI
unidentified (`R_PICPOC`), the joint **cell-weighted** recovery metric can be
manufactured by an anchor that makes per-AOI estimates straddle the target.
Report `R_PICPOC` recovery **per-AOI**, not only as the joint mean. (The iron
pair and diatomgraz pass the per-AOI test, so prior documented recoveries of
those are unaffected.)

**Proposed clean confirmation (follow-on, not run today):** an IC-perturbation
test — shift the Darwin ALK IC to match GLODAP and confirm the optimal
`R_PICPOC` collapses toward 0 in every AOI, demonstrating the result is an
IC-offset artifact by construction. Code path: a small `ALK_IC_SHIFT` flag.

## Reproduce

```bash
# n=20 dose sweep (control + ALK_ABS_W 1/10/100), seeds 0-9 then 10-19:
ALK_STAMP=mutex  ALK_SEEDS=0,1,2,3,4,5,6,7,8,9  python <orchestrator>   # arms c0,a1,a10,a100
ALK_STAMP=mutex2 ALK_SEEDS=10,...,19 ALK_ARMS=c0,a10,a100 python <orchestrator>
# controls: a300 (dose top) + a100d (Darwin-ALK source):
ALK_STAMP=mutex3 ALK_ARMS=a300,a100d python <orchestrator>
# single run, GLODAP ALK anchor on the Eppley best config:
DARWIN_DATA_ROOT=D:/ecco_darwin_v5 GEOTRACES_DATA_ROOT=D:/geotraces \
GLODAP_DATA_ROOT=<...GLODAPv2.2016b_MappedClimatologies> \
AOIS=eqpac,natlsubpolar,southernoceanpac POSI_W=1.0 \
AOI_W_NATLSUBPOLAR=2.0 AOI_W_SOUTHERNOCEANPAC=2.0 CHL1_W_EXTRA=3.0 \
POSI_DARWIN_W=0.5 USE_EPPLEY_T=1 ALK_ABS_W=100 TORCH_COMPILE_BATCHED=1 \
NB23_SEEDS=0,...,9 OUTPUT_DIR=<out> python scripts/run_v3.0_joint_multi_aoi.py
```
Orchestrator + probes: `%LOCALAPPDATA%\ddeck\alkabs\` (sweep_alk_abs.py,
probe_alk_signal.py, analyze_n20.py). Run JSONs: `D:\runs\alk_mutex{,2,3}\`.
