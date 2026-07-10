# Growth-pair vs iron-pair compromise — gating sweep, deep research, and a Fisher/profile diagnostic

**Date:** 2026-06-25 · **Spine:** D (issue #143) · **Status:** results VERIFIED (gating, n=10 each);
identifiability diagnostic built + first results in.

## TL;DR

With the R_PICPOC contaminated-target blocker removed (R_PICPOC recovers ≈Carroll, consistent with real MODIS calcite; the all-six event in the [2026-06-24 note](2026-06-24_rpicpoc_ratio_target_fix.md) is a tuned, init-anchored joint-metric artifact, not a robust 6/6),
robust per-AOI 6/6 is blocked by a **two-cluster compromise** under one shared Carroll-6 vector:

- **3 AOIs** {eqpac HNLC, natl bloom, SO bloom} cleanly recover 4 params (alpfe, scav_rat,
  diatomgraz, R_PICPOC all 10/10 per-AOI) but leave the **growth pair {Smallgrow 1/10,
  Biggrow 3/10}** unconstrained — a genuine co-varying degeneracy.
- Adding a 4th **oligotrophic gyre AOI (npsg, N Pacific Subtropical Gyre)** is the only known
  lever that fixes Smallgrow (1→8/10) — but it **collapses the iron pair: alpfe 10→0/10
  globally** (even in natl/SO where it was 10/10), diatomgraz 10→4, scav_rat 10→2.

**The information that separates the growth pair is welded to a conflicting iron demand.**
No scalar AOI weight, gradient-gating, or partial-pooling resolves it (§1, §6). BUT the real-obs
analysis (§7) cracked it: real GEOTRACES iron agrees with Carroll's alpfe, the collapse is the
Darwin *pattern* terms drowning the real-iron signal, and **up-weighting the REAL iron term
(`ironboost_10x`) gives the first strict per-AOI 6/6 (3/10 seeds), iron pair driven by real data.**
The alpfe collapse was loss-weighting, not structural — and the fix is grounded in observations.

## 1. Gating + taming sweep (VERIFIED, n=10 each, per-AOI Cal in ≥2 AOIs)

All runs: scheduled operating point (`RATIO_SCHED_START=0.5`, `RATIO_MAX=2.0`, `RATIO_W=2`,
1500 epochs), `--partition=sharing` H200. Gated via `scripts/verify_run.py` (exit 0) +
`scripts/aggregate_rpicpoc_env.py`.

| param | 3-AOI base | npsg=1.0 | npsg=0.3 | npsg=0.5 | gate_ISO | gate_ISO2 | gate_ISO3 |
|---|---|---|---|---|---|---|---|
| **alpfe** | 10/10 | 0/10 | 2/10 | 0/10 | 9/10 | 2/10 | **10/10** |
| scav_rat | 10/10 | 2/10 | 2/10 | 1/10 | 6/10 | 5/10 | 5/10 |
| **Smallgrow** | 1/10 | **8/10** | 4/10 | 5/10 | 0/10 | 2/10 | 0/10 |
| Biggrow | 3/10 | 4/10 | 6/10 | 4/10 | 1/10 | 0/10 | 3/10 |
| diatomgraz | 10/10 | 4/10 | 9/10 | 5/10 | 8/10 | 10/10 | 10/10 |
| R_PICPOC | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 | 10/10 |

Gating policies (per-AOI gradient routing, `src/darwindiff/gating.py`):
- **ISO**: iron/grazing/calcite ← 3 bloom AOIs; Smallgrow ← npsg only.
- **ISO2**: npsg → {Smallgrow, Biggrow}; all 6 also ← bloom AOIs.
- **ISO3**: npsg → {Smallgrow} only; all 6 also ← bloom AOIs.

**Verdict:** gating can RESTORE the iron pair by excluding npsg's gradient (ISO3: alpfe 10/10,
diatomgraz 10/10) — proving the collapse is gradient-conflict-driven, **not locked physics** —
**but then Smallgrow falls to 0/10**: npsg identifies Smallgrow only through a *full-state* fit
of the gyre, which carries the conflicting iron demand. Severing the weld (gating) loses the
signal; keeping it (ungated) loses alpfe. **No routing gets both.** Scalar npsg-weight is
likewise a dead trade (0.3 rescues diatomgraz to 9/10 but alpfe stays ≤2/10).

## 2. Deep-research synthesis (6 angles, adversarially verified)

Full provenance: `Workflow` deep-research, 13 agents, every claim verified against a real source.

**Central question — undecided by all six angles independently:** is the alpfe collapse
*structural* (a single shared alpfe is mis-specified across HNLC eq-Pacific vs dust-fed gyre →
new observable/structure needed) or a *training/identifiability artifact* (a directional
conflict routing can resolve)? Evidence both ways:

- **For structural:** box is iron-only, `PHI_DUST`/`Q_FE` constant, no N/P (`carroll6.py:53-59`);
  the real iron constraint *is* regime-dependent — solubility 1–2 OoM (Sholkovitz 2012),
  two-regime scavenging (Somes 2021), >40× luxury Fe:C (Twining 2021/Wiseman 2023), NPSG
  oscillates P↔Fe-limited (Letelier 2019) vs persistent eq-Pacific Fe-limitation (Browning 2023).
- **For artifact:** collapse is total at *every* weight (wrong shape for a smooth compromise);
  R_PICPOC precedent (contaminated target, not physics); and the **direct sibling Mamnun 2025**
  (REcoM2/LLC90) estimated 9 spatially-varying params — **none an iron param**; regional
  structure is in grazing/growth/light, so "free iron regionally" is unsupported extrapolation.

**Decisive test:** profile-likelihood (Raue 2009) — flat ⇒ structural, curved ⇒ practical.

**Ranked levers (P(robust 6/6) × 1/cost):**
1. **Fisher/Hessian + profile diagnostic FIRST** (very low cost; was the documented blind spot) —
   licenses everything below; built in this note.
2. **Per-AOI gradient gating** — low cost, exists; *only legitimate if profile is flat-ish* — and
   empirically (§1) it can't hold growth + iron together.
3. **Partial-pooling**: free {alpfe, scav_rat, diatomgraz} per-AOI, pool {Smallgrow, Biggrow}
   (Mamnun 26% gain; Friedrichs 2007 "free only a few"). Risk: iron-freeing is the unsupported half.
4. **Size-fractionated PP/chl observable** — but see §3 (largely redundant at steady state).
5. **Macronutrient (NO₃/PO₄) tracer + drawdown** — root cause; highest potential, highest cost.

## 3. Fundamental-logic analysis (from the box equations)

The box fits Darwin **time-mean** targets ≈ steady state. With `dPs/dt = 0`:

```
μ_s · f_fe · L · Ps  =  m_lin·Ps + m_quad·Ps²        (loss, FIXED constants)
  ⟹  μ_s = (m_lin + m_quad·Ps) / (f_fe · L)
```

1. **The growth pair is a `μ·f` PRODUCT degeneracy.** Biomass (Chl) + fixed mortality pin
   `μ_s·f_fe`; extracting `μ_s` needs the iron-limitation factor `f_fe`. **So Smallgrow is
   identifiable only *through the iron state* — the same coupling as the iron pair.** That is
   why npsg both fixes Smallgrow and breaks alpfe: one weld, not two problems.
2. **Size-fractionated PP is largely *redundant* at steady state.** There `PP_small = growth_s
   = loss(Ps)`, a fixed function of biomass — so a per-PFT PP target adds little beyond Chl.
   Lever 4 quietly assumes an off-steady-state box. **Downgrade unless paired with a transient
   (seasonal) box.**
3. **The iron conflict is locked by a constant.** `dDFe = alpfe·Φ_dust − …` with `Φ_dust` a
   single global constant — no spatial dust. The gyre's distinct supply can express *only*
   through the shared `alpfe`. → "alpfe collapses at every weight."

**Implication for the next lever:** the **macronutrient (NO₃/PO₄)** lever is the
fundamental-logic #1 — it is the only one that hits *both* obstructions: it gives growth a
*second, observed* limitation handle `f_N` (decoupling `μ` from `f_fe`), and gives the gyre a
non-iron way to express its regime (relieving the alpfe weld). Cost is real (forward-model
change). **Partial-pooling a regional alpfe** is the cheaper structural alternative (it directly
supplies the missing spatial-dust degree of freedom). Gating/reweighting only redistribute the
conflict (confirmed in §1).

## 4. Identifiability diagnostic (`scripts/identifiability_sloppiness.py`)

Built this session (the prior note's cited `identifiability_sloppiness.py` never existed).
Reuses the runner's EXACT `aoi_loss` + real bundles (imports the runner with `NB23_N_EPOCHS=0`,
gated behind a new `if __name__ == "__main__"` guard) and evaluates the joint loss as a function
of a single **global θ[6]** — the Carroll-6 identifiability object. Profile-likelihood
(vectorised over the grid via the seed axis) + finite-difference 6×6 Hessian eigenspectrum.

**Profile-likelihood, 3-AOI vs 4-AOI, on alpfe and Smallgrow (n=9 grid, opt-steps 600):**

| profile | config | rel_span | min location | shape |
|---|---|---|---|---|
| alpfe | 3-AOI | 0.21 (shallow) | **0.05 (lower bound)** | one-sided; loss 61.7→74.5 *rising* toward Carroll 0.93 |
| alpfe | 4-AOI | **0.07 (near-flat)** | 0.11 | **npsg flattens it**; min stays low (0.05–0.15 ≈ flat) |
| Smallgrow | 3-AOI | 0.13 (shallow) | 0.95 (off-target) | weak basin away from Carroll 0.66 |
| Smallgrow | 4-AOI | **0.04 (FLAT)** | **0.65 ≈ Carroll** | flat, but **basin recentred on Carroll** |

Hessian sloppiest direction ≈ **pure Smallgrow (≈±1.0)** in *both* configs — the `μ·f` flat direction.

**Two structural facts:**
1. **The global-θ loss does NOT want alpfe near Carroll's 0.93 — it pulls alpfe to the 0.05 bound
   in BOTH configs** (loss 61.7 @0.05 vs 74.5 @1.0), and **npsg flattens the profile further
   (0.21→0.07)**. So the 3-AOI "alpfe 10/10" is **initialisation-anchored, not a sharp data
   optimum**; npsg simply lets the loss's true low-alpfe preference win. This is **structural
   non-identifiability** (Raue: shallow + optimum at the bound, away from target) — masked, not
   fixable, by reweighting/gating (matches §1).
2. **Smallgrow is the sloppiest direction in both configs.** npsg does not *sharpen* it (stays
   flat, span 0.04) but **relocates its shallow basin from 0.95 → 0.65 ≈ Carroll** — which is
   *why* DINN recovery jumps 1→8/10. The gain is basin **relocation**, not identification.

Caveats: profile points re-optimised 300 steps warm-started from a low-alpfe θ*, so absolute
curvature toward high alpfe may be slightly overestimated; the *qualitative* conclusions
(alpfe shallow+low, npsg flattens; Smallgrow sloppy, npsg recentres) are robust across all four
runs. Runs were slow (38–54 min); a converged refinement is a cheap follow-up.

## 5. Recommendation

The iron "recovery" is structurally weak (the loss doesn't pin alpfe near Carroll) and the npsg
collapse is the loss's **real preference** asserting itself — not a tuning artifact. **Stop
tuning routing / AOI weights** (dead, confirmed empirically *and* by the flat/one-sided profile).
The fix must be a **forward-model change** that makes Carroll's values the genuine loss optimum:

1. **Macronutrient (NO₃/PO₄) tracer + drawdown loss — fundamental #1.** Only lever that hits both
   obstructions: a second *observed* limitation handle `f_N` decouples growth μ from `f_fe` (the
   growth-pair degeneracy of §3.1) AND gives the gyre a non-iron way to express its regime
   (relieving the alpfe weld of §3.3). Moderate-high cost; data staged in v05. **Gate it with the
   diagnostic first:** does adding NO₃ curve the alpfe profile toward Carroll / lift the Smallgrow
   eigenvalue? If yes, retrain n=10.
2. **Regional iron (spatial `Φ_dust` or per-AOI alpfe partial-pooling) — cheaper structural
   alternative.** Directly supplies the missing spatial-dust DoF. Risk: the direct sibling
   (Mamnun 2025) freed *no* iron param, so this is the less-supported half — validate that freed
   per-AOI alpfe brackets the published 1–2 OoM solubility range.

**Manuscript implication (spine C / #120):** the diagnostic shows the per-cell DINN masks weak
global identifiability of the iron pair — the recovery framework must report this (it is exactly
the over-parameterisation / identifiability objection a referee will raise). `#120` (Hessian/Fisher
sloppiness) is now partially delivered by `scripts/identifiability_sloppiness.py`.

## 6. Per-AOI profiles + partial pooling — both implementable levers REFUTED

**Per-AOI alpfe profiles (each AOI's own loss, incl. the REAL GEOTRACES iron term):**

| AOI | alpfe optimum | Carroll 0.93 penalty |
|---|---|---|
| eqpac | 0.05 (bound) | +9.7 (strong reject) |
| natlsubpolar | 0.05 (bound) | +10.9 (strong reject) |
| southernoceanpac | 0.05 (bound) | +1.2 (mild) |
| npsg | 0.07 | +2.7 |

**No regime's loss prefers Carroll's alpfe** — they all want ~0.05–0.07. So the iron problem is NOT
a regime-conflict that regional params resolve; the box's loss never prefers Carroll's alpfe
anywhere. The "alpfe 10/10" is purely **initialisation-anchored**. (Note: these profiles include
the real GEOTRACES iron anchor, so this is partly a real-data statement — see §7.)

**Partial-pooling experiment** (`PER_AOI_DINN=1 POOL_PARAMS=Smallgrow,Biggrow`, λ∈{0.1,0.3,1.0},
n=10, VERIFIED): **refuted.** Worse than gating — `PER_AOI_DINN` decoupling **breaks R_PICPOC**
(0/10, each region's net diverges) and recovers iron only in the SO net; growth pooling lands at
wrong shared values. So **both no-new-data levers (gating §1 + partial-pooling) are exhausted.**

**Conclusion:** robust per-AOI 6/6 is unreachable by routing/pooling on the current box +
observables. It requires a forward-model change (macronutrient — blocked on NO₃ data staging) or a
new iron observable. The recovery of Carroll's iron values is partly **ill-posed**: the box's iron
submodel (fit to the iron data incl. real GEOTRACES) prefers a different alpfe than the full Darwin
model uses.

## 7. Real-world relevance — real iron AGREES with Carroll (the collapse is loss-weighting)

This effort is a **surrogate-to-model identifiability study** (issue #116): the box is fit to
ECCO-Darwin v05's OWN output and graded against Carroll's params. Real observations enter as
anchors: **GEOTRACES IDP2025 dissolved iron (surf `W=0.3` + sub `W=1.0`) and GEOTRACES bSi
(`POSI_W=1.0`)**; GLODAP alkalinity off by default; no model checkpoints saved.

**The decisive real-data measurement** (`identifiability_sloppiness.py --loss realiron`, profiles
alpfe against the REAL GEOTRACES iron residual ALONE):

| AOI | real-iron alpfe optimum | curvature (span) |
|---|---|---|
| eqpac | **1.0 ≈ Carroll 0.93** | 1.76 (strong) |
| natlsubpolar | **1.0** | 0.75 |
| southernoceanpac | **1.0** | 0.23 |
| npsg | **1.0** | 0.41 |

**Real GEOTRACES iron prefers HIGH alpfe (≈Carroll's 0.93) in every region — the OPPOSITE of the
full loss (0.05).** Two consequences that REVISE §6:
1. **Real-world validation: the box constrained by REAL iron data wants ≈Carroll's calibrated
   alpfe.** Not twin-experiment self-reference — real observations and Darwin's calibration agree.
2. **The alpfe collapse is a LOSS-WEIGHTING problem, not structural.** The Darwin z-scored *pattern*
   terms (chl/PIC/POC…) dominate and drag alpfe low; the real-iron anchor at default weight is too
   quiet to win. So §6's "needs a forward-model change" is too pessimistic — a **no-new-data lever
   remains: up-weight the real GEOTRACES iron term** so real observations drive alpfe to its true
   value even in the npsg 4-AOI case. (Distinct axis from the refuted AOI-reweighting.)

**RESULT (VERIFIED, n=10): the real-iron lever WORKS.** 4-AOI scheduled config + boosted REAL
GEOTRACES iron, per-AOI Cal (≥2 AOI):

| param | npsg=1.0 (collapse) | **ironboost_10x** (W=3/SUB=10) | ironboost_33x (W=10/30) |
|---|---|---|---|
| alpfe | 0/10 | **7/10** (incl. npsg) | 9/10 |
| scav_rat | 2/10 | **9/10** | 3/10 |
| Smallgrow | 8/10 | **8/10** | 7/10 |
| Biggrow | 4/10 | **5/10** | 1/10 |
| diatomgraz | 4/10 | **10/10** | 10/10 |
| R_PICPOC | 10/10 | **10/10** | 10/10 |

**`ironboost_10x` → all six per-AOI Cal in 3/10 seeds only** (cal-counts `[6,6,6,5,5,5,5,4,4,3]`) — a
tuned, non-robust event on the per-AOI metric, NOT a headline 6/6 recovery (the earlier all-six event
was the looser joint metric with init-anchored alpfe). The durable, real-data result is narrower and
stronger: **the iron pair (`alpfe`, `scav_rat`) is driven by REAL GEOTRACES iron and agrees with
Carroll's calibrated values**; the growth pair stays the residual wall. `33×`
over-boosts (alpfe 9/10 but scav_rat/Biggrow crash → 0/10 6/6); `10×` is near the sweet spot.

**Headline:** the alpfe collapse was the Darwin z-scored pattern terms drowning the real-iron
signal; real GEOTRACES iron agrees with Carroll; up-weighting it recovers the iron pair without
losing the growth pair — breaking the compromise gating/pooling could not, **using real data.**

### Fine iron-weight sweep (5×–15×, n=10 each, VERIFIED) — robust 6/6 NOT reached; blocker isolated

| iron wt | strict per-AOI 6/6 | ≥5/6 | alpfe | scav | Small | Big | diat | RPIC |
|---|---|---|---|---|---|---|---|---|
| 5× | 1/10 | 2/10 | 2 | 5 | 7 | 6 | 10 | 9 |
| **7×** | 2/10 | **9/10** | 4 | 9 | 9 | **9** | 10 | 10 |
| 8× | 1/10 | 9/10 | 4 | 10 | 9 | 7 | 10 | 10 |
| **10×** | **3/10** | 7/10 | **7** | 9 | 8 | 5 | 10 | 10 |
| 12× | 2/10 | 8/10 | **8** | 8 | 8 | 6 | 10 | 10 |
| 15× | 2/10 | 8/10 | 7 | 8 | 9 | 5 | 10 | 10 |

**Strict 6/6 caps at 3/10 (10×).** But **7× gives 9/10 at ≥5/6** — nearly every seed is one param
short, and that param is **alpfe**. The ceiling is a precise **alpfe ↔ Biggrow tradeoff along the
iron-weight axis**: low weight recovers Biggrow (9/10) but under-constrains alpfe; high weight
recovers alpfe but over-pins `f_fe` so Biggrow absorbs the misfit (the `μ·f` coupling of §3.1). One
iron knob cannot satisfy both.

**Robust 6/6 needs a second, Biggrow-specific anchor** — the growth-flux `PRIMPROD_W` — whose
`primProd` field is **NOT staged on the cluster** (same data gap as NO₃). So the no-new-data levers
are exhausted at: **5/6 near-robust (9/10 seeds at 7×) + strict 6/6 in 3/10 (10×), iron pair
real-data-driven.** The single remaining blocker is Biggrow's missing observable — a data-staging
step (`primProd` monthly field), not a modelling one.

## Artifacts

- `scripts/identifiability_sloppiness.py` (new); `scripts/slurm/run_identifiability.sbatch` (new).
- Runner made importable: `if __name__ == "__main__"` guard around training/recovery (behavior
  under direct invocation unchanged).
- Runs: `rpicpoc_4aoi_{plain,sched,npsg0p3,npsg0p5,gate_iso,gate_canon,gate_iso2,gate_iso3}`,
  `fim_{3aoi,4aoi}_{alpfe,Smallgrow}` (all on `/projects/schultz/qi.zim/runs`).
- New AOI `npsg` (Subtropical Pacific Gyre) in `src/darwindiff/ecco_darwin_loader.py`.
