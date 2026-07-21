# The iron identifiability degeneracy — derived, and validated against Tagliabue's Table 2

**Date:** 2026-07-20 · **Companion to** `2026-07-20_external_validation_iron_residence_alpfe.md`.
This note makes the central Q1 inference *rigorous*: the FeMIP inter-model iron divergence is the
single source↔scavenging **identifiability degeneracy** our per-cell method measures — and its
signature is exactly reproduced by Tagliabue et al. 2016's own Table 2. Reproducible analysis:
`scripts/analysis/iron_degeneracy_math.py` (single-box Fisher + Table 2 decomposition). An
intermediate 2-box toy was **discarded** — see the self-correction in §4 (a wrong turn caught by the data).

## 1. The math — single-box steady state

At steady state for dissolved iron, `dFe/dt = S − k·I = 0`, where `S` = source flux, `k` = removal
(scavenging) rate constant, `I` = inventory. Residence time `τ = I/S = 1/k`, mean concentration
`Fe* = I/V = S/(kV)`.

In `θ = (ln S, ln k)`, the one observable is `ln Fe* = ln S − ln k − ln V`, gradient `g = (+1, −1)`.
The empirical Fisher `F = g gᵀ` is **rank-1**: eigenvalues `{2, 0}`.
- **Stiff** eigenvector `(+1, −1)/√2` (raise S, lower k) — moves `Fe*` maximally.
- **Sloppy** eigenvector `(+1, +1)/√2` (raise S *and* k together, fixed ratio `S/k`) — leaves `Fe*`
  **invariant** while `τ = 1/k` changes. **τ is the free coordinate along the sloppy direction.**

Fixing `Fe*` to an observed value forces `k = S/(Fe*·V)`, i.e. `k ∝ S`, so `τ = 1/k ∝ 1/S`. Therefore,
at pinned concentration, **`Var(ln τ) ≈ Var(ln S)` — the residence-time spread tracks the *source*
spread.** (Numerically confirmed: Fisher eigenvalues `[0, 2]`, sloppy vector moves `log Fe*` by 0.)

## 2. Validation — Tagliabue et al. 2016, Table 2 (all 13 models, read from the primary PDF)

| quantity | min | max | fold |
|---|---|---|---|
| **total input flux** (Gmol Fe/yr) | 1.4 (BFM) | 195.4 (MITigsm) | **~140×** |
| Fe inventory (×10¹¹ mol) | 4.8 (MEDUSA2) | 12.5 (REcoM) | 2.6× |
| mean concentration (nM) | 0.35 (MEDUSA2) | 0.81 (PISCES2) | 2.3× |
| **residence time** (yr) | 3.7 (COBALT) | 626.3 (BFM) | **169×** |

Two facts settle it:

1. **The identity `τ = inventory/input` reproduces the residence column exactly** for every model
   (e.g. BFM 8.8e11/1.4e9 = 629 yr ✓; COBALT 6.8e11/182.5e9 = 3.7 yr ✓).
2. **Decomposing the extreme (BFM/COBALT) 169× spread:**
   `169× = (inv_BFM/inv_COBALT) × (input_COBALT/input_BFM) = 1.29× (inventory) × 130× (INPUT).`

So the residence-time spread is **~130× from the input flux and only ~1.3× from inventory**.
Concentration/inventory is *pinned* (models tune to it); the **input magnitude is the unconstrained
sloppy coordinate** — dominated by the **sedimentary source**, which spans **0 → 194 Gmol/yr** across
models (BFM/GENIE/MEDUSA1 omit it entirely, τ = 230–626 yr; COBALT/MITigsm load it heavily,
τ = 3.7–4.6 yr) — all reproducing ~0.5 nM by compensating with scavenging. **This is the
identifiability degeneracy, in the field's own numbers.**

## 3. Consistency across scales — three residence times, one mechanism

- **Within a model (Somes et al. 2021, controlled):** varying the atmospheric + **sedimentary** source
  ×5 at fixed 0.70±0.03 nM gives τ 7.49–35.9 yr (**~5×**) — exactly `Var(ln τ) ≈ Var(ln S)`. Somes
  varied the *same sediment lever* that drives the Tagliabue cross-model spread.
- **Across models (Tagliabue):** τ 169×, because the source spans ~140× (mostly sediment) with
  concentration pinned.
- **Our Job 2 surface box:** τ ~1–8 days is the *surface mixed-layer* residence time — a **third,
  distinct** quantity, correctly matching observed upper-ocean values (Black 2020), decoupled from the
  whole-ocean τ. Conflating the three is the error to avoid.

## 4. Self-correction (recorded on purpose)

An intermediate hypothesis — that the 169× needs a *second* sloppy direction (deep-ocean inventory
variance) beyond the source/scavenging pair — is **falsified by Table 2**: inventory varies only 2.6×,
not the ~16× a 2-box toy suggested (that toy also produced unphysical deep [Fe] of 400–6800 nM). The
mean concentration Tagliabue reports is the *deep-dominated* whole-ocean mean, so pinning it pins the
inventory. The rigorous inference is the **single** degeneracy, no deep-inventory elaboration needed.

## 6. Independent corroboration + a reconciled disagreement (rigor workflow `wf_a5db2336`)

Three agents independently re-derived the degeneracy; a fourth adversarially reconciled them.
Outcomes, all primary-source-checked where reachable:

- **The sloppy-eigenvector degeneracy is undisputed and exact** — `τ = Fe*V/S`, concentration pins the
  ratio `S/k`, τ is free along the orthogonal (turnover-scale) direction. Kinetics-independent algebra;
  all three derivations state it identically.
- **Somes 2021 verified against its primary Table 2** (fetched from GEOMAR): source ×4.7 → τ ×4.79
  (prediction ×4.7), and the implied inventory `I = τ·S` is constant to ~7% = the Fe* spread. A clean,
  near-exact confirmation of `Var(ln τ) ≈ Var(ln S)` at pinned concentration.
- **A genuine disagreement, and its resolution.** Using the *dust-only* ~30× source figure, two agents
  predicted only ~50× and concluded a *second* mechanism (deep vertical decoupling / nonlinear
  scavenging / ligand speciation) was needed for Tagliabue's 170×. The third agent — and the reconciler,
  ranking it highest — instead said "**check the denominator: ~30× is the wrong S**." The agents could
  not reach Tagliabue's paywalled text to settle it. **Our §2 Table 2 extraction is that missing data**:
  total input spans **140×** (sediment 0–194 Gmol, the dominant term), and `τ = inventory/input`
  reproduces the residence column exactly — so the single degeneracy explains 170× with **no deep
  structure required**. Somes 2021's own Introduction independently confirms the sedimentary term spans
  "0–194 Gmol/yr," distinct from atmospheric "1.4–30." Deep decoupling is a *real* feature of some models
  (Tagliabue's Table 3: model–obs skill collapses with depth) but is **not the driver** of the τ spread.
- **Contribution claim, refined.** Formal identifiability machinery (profile likelihood, Jacobian
  analysis) *is* used in marine-ecosystem modelling generally — **Schartau et al. 2017** (Biogeosciences,
  "Parameter identification in marine planktonic ecosystem modelling") is the review — but **0 of ~15
  targeted searches** found it applied to the ocean **iron** cycle or to frame the FeMIP divergence.
  Pasquier & Holzer 2017 and Frants et al. 2016 reach the degeneracy via "family of solutions"
  (equifinality-adjacent) without the formal toolkit. So the contribution is precise: *applying Fisher/
  profile-likelihood identifiability to the iron cycle / FeMIP spread*, not "nobody uses it in ocean-BGC."

**Caveats (honest):** Tagliabue 2016's full text was paywalled to every agent; our decomposition rests on
the Table 2 numbers (open-access mirror) plus the internal consistency check that `τ = inventory/input`
reproduces the published residence column for all 13 models. And Tagliabue's mean-DFe agreement is partly
a *shared-assumption* artifact (models built around a near-constant deep-DFe paradigm), not fully
independent tuning — a nuance on "concentration pinned," though it does not change the τ decomposition.

## 5. The defensible one-liner (for the manuscript)

> Mean dissolved-Fe concentration identifies the source/scavenging **ratio** but leaves the source
> **magnitude** — equivalently the residence time — unconstrained along a sloppy eigenvector. Across the
> 13 FeMIP models this single degeneracy spans the residence time 169× (input flux ~140×, dominated by
> the sedimentary source; inventory pinned to ~2×), while concentration agrees to ~2×. Naming and
> measuring this with a profile likelihood is the contribution; the observable that breaks it is the
> GEOTRACES section *gradient* (Somes 2021), not the mean.
