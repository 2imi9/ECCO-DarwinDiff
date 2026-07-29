# Hierarchical inversion and noise amplification: the math, and what it does and does not buy us

> ## ⚠ READ FIRST — §1's quantitative conclusions are built on a units error
>
> An adversarial review of this document found that the repo's published condition numbers
> (2930, 2.2, 35–51) are **Fisher-matrix** condition numbers, i.e. already **κ(J)²**.
> `2026-07-23_observation_design.md:76-78` gives the iron 2×2 Fisher eigenvalues 1.08e-3 / 3.18,
> whose ratio is 2944 ≈ 2930. **Verified against the source.**
>
> §1 treats them as κ(J). The corrected values are √: κ(J) = **54** (surface-only iron),
> **5.9–7.1** (eqpac/natl), **1.5** (Southern Ocean).
>
> This **inverts §1.5 Test 1**: with the corrected bound, natl sits *at* the κ limit and **eqpac
> exceeds it by ~3×**. A worst-case bound cannot be exceeded by noise amplification, so eqpac is the
> one basin κ demonstrably *cannot* explain — the opposite of what §1.5 concludes. Every downstream
> inference resting on Test 1 (the §4 conditioning-vs-observability split, E4's prediction, the §6
> summary) needs redoing.
>
> The review also flags: Wedin's bound requires `ε·κ(J) < 1` and is applied in §1.2 to a structural
> error of O(10⁻¹), where it is vacuous; `tan φ` is load-bearing but never measured though it is one
> forward pass; and reparameterisation does not change the CRLB, only Adam's trajectory.
>
> **§2 and §3 are unaffected** — the hierarchy matrix, the finding that the runner already whitens
> with a fabricated covariance, and the observation that `scav_rat` and `diatomgraz` have no
> independent real anchor are all independent of the κ arithmetic.

**Date:** 2026-07-27 · **Status:** design document, not a result · **Scope:** the parameter-learner
(Track 1) loss. Answers two questions: (a) how should the inverse problem be structured so that each
parameter is constrained by the data that actually carries its information, and (b) how do we avoid
amplifying small observational noise through an ill-conditioned Jacobian.

Everything numerical in §1 is an existing, grader-verified repo number, re-analysed. Nothing here has
been run. Section 5 says what to run.

---

## 0. Citation provenance and integrity

Every identifier in this document is reproduced from the verified research corpus supplied with this
task. **I did not independently re-resolve any of them in this session.** Re-resolve each one before
it goes into `docs/paper/main.tex`. Prior work on this project produced a fabricated citation; the
correct response is to treat identifiers as untrusted until re-fetched, not to omit them.

| ID | What it is | Used here for |
|---|---|---|
| DOI 10.1007/BF01933494 | Wedin, *Perturbation theory for pseudo-inverses*, BIT 13 (1973) 217–232 | the full LS perturbation bound with the κ² term |
| DOI 10.1137/1.9780898718027 | Higham, *Accuracy and Stability of Numerical Algorithms*, 2nd ed., SIAM 2002 | κ(JᵀJ) = κ(J)², digit loss |
| DOI 10.1007/BF01436075 | Golub, *Numerical methods for solving linear least squares problems*, Numer. Math. 7 (1965) | QR over normal equations |
| DOI 10.1007/BF01934122 | Björck, BIT 7 (1967) 1–21 | stability of LS solvers |
| DOI 10.1137/1.9780898718836 | Hansen, *Discrete Inverse Problems: Insight and Algorithms*, SIAM 2010 | SVD picture of noise amplification |
| DOI 10.1137/1.9780898719697 | Hansen, *Rank-Deficient and Discrete Ill-Posed Problems*, SIAM 1998 | TSVD, Tikhonov filter factors, parameter choice |
| DOI 10.1007/BF01933214 | Hansen, *The discrete Picard condition…*, BIT 30 (1990) 658–672 | the Picard plot diagnostic |
| DOI 10.1137/S0895479897326432 | Golub, Hansen & O'Leary, SIAM J. Matrix Anal. Appl. 21 (1999) 185–194 | Tikhonov formulation |
| DOI 10.1063/1.4923066 | Transtrum et al. | Fisher = Gauss-Newton Hessian; sloppiness |
| arXiv:q-bio/0701039 | Gutenkunst et al., *Universally sloppy parameter sensitivities in systems biology* | sloppy spectra; flat ≠ non-identifiable |
| arXiv:2604.16919 | Xia et al., *Noise-Adaptive Diffusion Sampling…* | Jeffreys marginalisation of the noise level (Eqs. 10–11, Prop. 2); residual-floor corollary (Cor. 1.1) |
| arXiv:2001.04536 | *Understanding and mitigating gradient pathologies in PINNs* | gradient-norm loss balancing |
| arXiv:2007.14527 | *When and why PINNs fail to train: an NTK perspective* | NTK eigenvalue spread as the training-dynamics face of conditioning |
| arXiv:2009.04544 / DOI 10.1016/j.jcp.2022.111722 | *Self-Adaptive PINNs…* | trainable loss weights |
| arXiv:2110.09813 | *Multi-Objective Loss Balancing for Physics-Informed Deep Learning* | scalarising several objectives into one loss is the wrong formulation |
| DOI 10.1016/j.jcp.2018.10.045 | Raissi, Perdikaris & Karniadakis, JCP 2019 | the PINN inverse-problem method class we sit in |
| DOI 10.1073/pnas.1517384113 | Brunton, Proctor & Kutz, PNAS 2016 (SINDy) | STLSQ active-set re-solve as a hierarchy precedent |
| arXiv:2510.23633 | *Noise is All You Need* (NCS) | **cited only as not applicable** — see §3.7 |

**No identifier was retrieved this session for:** GCV (Golub–Heath–Wahba), the Morozov discrepancy
principle, the L-curve non-convergence results, Eckart–Young 1936, or Tikhonov-EKI (TEKI). Where those
appear below they are named as classical results with **no citation attached**, and must not be cited
until an identifier is fetched. That is a real gap in the corpus, not an oversight.

---

## 1. The amplification mechanism, stated exactly

### 1.1 Setup

Let `d ∈ R^m` be the stacked observations, `θ ∈ R^n` the parameters, `G(θ)` the differentiable 0-D box
composed with the per-cell DINN map, `r(θ) = d − G(θ)` the residual, and

```
J = ∂G/∂θ ∈ R^(m×n)
```

For Gaussian observation noise with covariance `Σ`, the negative log-likelihood is
`L(θ) = ½ rᵀ Σ⁻¹ r`, whose exact Hessian is

```
∇²L = Jᵀ Σ⁻¹ J  −  Σ_k [Σ⁻¹ r]_k ∇²G_k
```

Dropping the second term gives the Gauss-Newton Hessian `H_GN = Jᵀ Σ⁻¹ J`, which for this model is
*identically* the Fisher information matrix `F` (DOI 10.1063/1.4923066). So the three objects the repo
already computes — "Fisher spectrum", "GN-Hessian curvature", "singular values of the whitened
Jacobian `J̃ = Σ^(-1/2) J`" — are one object. Everything below is a statement about `σ_i(J̃)`.

**This identity holds only after whitening by `Σ^(-1/2)`.** An unweighted stacked-anchor loss computes
the Fisher matrix of the *wrong noise model*. That is the precise mathematical content of complaint
(a), and §2.1 shows what `Σ` our current loss silently assumes.

### 1.2 The error bound (the repo's current statement is the special case)

With `J̃ = UΣ_sV ᵀ` (thin SVD, `σ₁ ≥ … ≥ σ_n`) and `θ̂ = J̃⁺d̃`, `J̃⁺ = VΣ_s⁻¹Uᵀ`:

**Data-only perturbation** (`J` exact, `d → d + δd`): `δθ = J̃⁺δd`, so `‖δθ‖ ≤ ‖δd‖/σ_n`, and dividing
by `‖θ̂‖ ≥ ‖d_R‖/σ₁` where `d_R = UUᵀd`:

```
‖δθ‖/‖θ̂‖  ≤  (κ₂(J̃)/cos φ) · ‖δd‖/‖d‖ ,      sin φ = ‖r‖/‖d‖
```

**Full first-order bound** (`J` also perturbed, `‖δJ‖/‖J‖ ≤ ε`, `‖δd‖/‖d‖ ≤ ε`), Wedin's theorem
(DOI 10.1007/BF01933494):

```
‖δθ‖/‖θ̂‖  ≲  ε · [ 2κ₂(J̃)/cos φ  +  κ₂(J̃)² tan φ ]
```

Two corrections to how this project currently states it in
`docs/findings/2026-07-27_conditioning_precision_hypothesis.md:25`:

1. `‖δθ‖/‖θ‖ ≲ κ(J)·‖δd‖/‖d‖` is the **cos φ = 1 (zero-residual) case**. With a real residual it is
   inflated by `1/cos φ`. Our residuals are not small.
2. Far more important: **`δJ ≠ 0` here.** The Jacobian comes from a 0-D box surrogate of a 3-D model.
   Surrogate-to-model structural error *is* `δJ`. That activates the `κ² tan φ` term. So the project's
   dominant error channel is the **squared**-condition-number one, and it is a **bias** channel, not a
   dtype channel — it exists in float64 and it does not average out over seeds. This is a stronger and
   more defensible statement than the float32 hypothesis in that file, and it is independent of it.

### 1.3 Term-by-term: where the blow-up physically happens

With `d̃ = d̃_true + η`,

```
θ̂  =  Σ_i (u_iᵀ d̃ / σ_i) v_i  =  θ_true  +  Σ_i (u_iᵀ η / σ_i) v_i
```

Each noise coefficient `u_iᵀη` is O(1) in whitened units *regardless of i*, but is divided by `σ_i`.
The error covariance is the CRLB, `Cov(θ̂) ⪰ F⁻¹ = V Σ_s⁻² Vᵀ`: the parameter-error ellipsoid has
semi-axes `1/σ_i` along `v_i` (DOI 10.1137/1.9780898718836). A direction with `σ_i` 100× smaller than
`σ₁` carries 100× the standard error and 10⁴× the variance.

Two consequences that matter operationally:

- **Averaging does not help the shape.** N independent repeats of the *same* survey scale every `σ_i`
  by `√N` uniformly. `κ` is unchanged. This is exactly what the repo measured: a second identical
  surface-[DFe] survey gives the trivial 2.00× variance drop and leaves the iron-block condition number
  at **2930, unchanged** (`docs/findings/2026-07-23_observation_design.md:104`).
- **Rotating the spectrum does help.** A scavenging-flux observable collapses that block 2930 → **6.9**;
  subsurface [DFe] → **2.5** (same file, :98–99). Regularisation buys stability at the price of bias;
  a *new observable direction* buys stability for free.

### 1.4 Why forming JᵀJ squares the condition number

```
J̃ᵀJ̃ = V Σ_s² Vᵀ   ⟹   λ_i(J̃ᵀJ̃) = σ_i²   ⟹   κ₂(J̃ᵀJ̃) = κ₂(J̃)²
```

It is the eigenvalue map `λ = σ²`, not a metaphor. In digits, with unit roundoff `u`:

```
digits_surviving  ≈  log₁₀(1/u)  −  2·log₁₀ κ(J)      [normal-equations path]
digits_surviving  ≈  log₁₀(1/u)  −  log₁₀ κ(J)  −  (κ² ρ term, ρ = ‖r‖/(‖J‖‖θ‖))   [QR/SVD path]
```

(DOI 10.1137/1.9780898718027; Golub DOI 10.1007/BF01436075; Björck DOI 10.1007/BF01934122.)
float32 carries ≈7.22 decimal digits, float64 ≈15.95.

**Actionable, and cheap:** `n = 4–6`, so `J̃` is at most `m×6` and a full SVD is free. There is **no
cost argument for ever forming `JᵀJ`** anywhere in this codebase. Every site that builds a Gauss-Newton
matrix, a Fisher matrix, or a covariance by explicit `JᵀJ` + Cholesky/inverse is running at `κ²` and
should be replaced by `SVD(J̃)` with `V Σ_s⁻¹ Uᵀ`. At κ = 2930 in float32 that is the difference between
0.29 and 3.6 surviving digits. Note this concerns the **diagnostics** (`identifiability_sloppiness.py`,
`observation_design.py`), not the training loop — training is first-order Adam and never forms `JᵀJ`.

### 1.5 Confronting the bound with our measured recovery — where it works and where it fails

Repo facts, all grader-verified:

| AOI | iron 2×2 cond (surf+sub, real GEOTRACES) | full-6 sloppiness | `scav_rat` per-AOI @2000 ep | @4000 ep |
|---|---:|---:|---:|---:|
| southernoceanpac | **2.2** | 4.99 decades | **49/50** | 48/50 |
| natlsubpolar | **35–51** | 5.99 decades | **20/50** | **40/50** |
| eqpac | **35–51** | 5.19 decades | **7/50** | **6/50** |

(`STATUS.md:307,309,347,348`; `docs/findings/2026-07-23_overnight_recovery_sweep_groupA.md`.)
Joint `≥2-of-3` = 25/50 at 2000 ep, ≈41/50 at 4000 ep; `scav_rat`'s own per-AOI leg is 26/50 at 2000 ep
(`docs/findings/2026-07-21_joint_number_reconciliation.md:15`) — CLAUDE.md's "25/50" is the trio, which
sits one seed below.

**Test 1 — does κ predict the recovery counts?** Grading is a two-sided band, `|θ̂/θ_Carroll − 1| ≤ 0.40`.
If the seed-to-seed error along the sloppy direction is approximately Gaussian with sd `s`, then the
per-AOI pass fraction is `p = 2Φ(t/s) − 1` with `t = 0.40`. Inverting:

| AOI / budget | p | z = Φ⁻¹((1+p)/2) | implied relative sd `s = 0.40/z` | implied `s/s_sopac` |
|---|---:|---:|---:|---:|
| sopac @2000 | 0.98 | 2.326 | 0.17 | 1.0 |
| natl @2000 | 0.40 | 0.524 | 0.76 | 4.4 |
| eqpac @2000 | 0.14 | 0.176 | 2.27 | **13.2** |
| natl @4000 | 0.80 | 1.282 | 0.31 | 1.8 |
| eqpac @4000 | 0.12 | 0.151 | 2.65 | **15.4** |

κ predicts `s/s_sopac ≈ κ_AOI/κ_sopac = 35/2.2 … 51/2.2 = **15.9 … 23.2**`.

- **eqpac lands inside (just under) the κ-predicted band, at both epoch budgets.** 13.2 and 15.4 vs a
  predicted 15.9–23.2. eqpac behaves like a basin sitting *at* the conditioning-imposed noise-amplification
  limit, and more optimisation does not move it (13.2 → 15.4 is within noise of no change).
- **natl does not.** Its implied error inflation is 4.4×, three to five times *better* than κ allows as a
  worst case, and it improves to 1.8× with 2× compute. **natl at 2000 epochs was not conditioning-limited;
  it was optimisation-limited**, exactly as `docs/findings/2026-07-23_overnight_recovery_sweep_groupA.md`
  concluded from the epoch sweep.

This is consistent, not forced: `κ` is a **worst-case bound**. It is realised only when the noise/model
error has a substantial component along `v_min`. The classical name for the alignment condition is the
**discrete Picard condition** (DOI 10.1007/BF01933214). eqpac appears to satisfy it; natl does not.

**Test 2 — does κ predict the *ordering*? Partly.** The 2×2 iron-block κ correctly separates sopac
(2.2 → 49/50) from {natl, eqpac} (35–51 → 20/50, 7/50). It does **not** separate natl from eqpac at all:
same κ band, 3× different recovery. So κ is necessary-condition information, not a predictor.

**Test 3 — the full-6 sloppiness numbers INVERT the recovery order. Say so plainly.** Decades =
`log₁₀ κ(F) = 2 log₁₀ κ(J)`, so eqpac 5.19 → κ(J) ≈ 393, natl 5.99 → κ(J) ≈ 990, sopac 4.99 → κ(J) ≈ 313.
That ranks **natl as the worst-conditioned**, yet natl recovers 20/50 (and 40/50 at 4000 ep) against
eqpac's 7/50. **The full-6 sloppiness metric does not predict recovery and should not be quoted as
though it does.** The 2×2 iron-block condition number is the one with (partial) predictive content,
because it is the block in which `scav_rat`'s degeneracy actually lives.

**Test 4 — a direct falsification of "improve κ ⇒ improve recovery".** Up-weighting the
better-conditioned subsurface iron term (`GEOTRACES_SUB_W` 1 → 3 → 8) **degrades** `scav_rat` per-AOI
recovery 9/10 → 5/10 → 1/10 (job 188074, VERIFIED,
`docs/findings/2026-07-23_subiron_scav_rat_result.md`). Up-weighting the surface iron term
(`GEOTRACES_W=3`, run `n50_highiron`) takes `scav_rat` per-AOI to **1/50** while its cell-weighted count
rises to 50/50 — a textbook straddle. Two things follow:

1. **Reweighting is not conditioning improvement.** Changing `Σ` changes which fixed point the biased
   estimator lands on. In the Wedin decomposition, up-weighting a block with a large residual angle `φ`
   amplifies the `κ² tan φ` model-error term; the conditioning gain can be more than cancelled by the
   bias gain. This is the mathematically precise version of "the info-vs-recovery gap".
2. **Any scheme in §3 that changes anchor weights must be graded on the per-AOI metric**, because the
   cell-weighted metric moves the *wrong way* under exactly these interventions.

**Verdict for §1.** The honest claim is narrower than "condition number explains the recovery pattern":

> The 2×2 iron-block condition number explains the **binary split** (well-conditioned Southern Ocean
> recovers; the two ratio-degenerate basins do not) and quantitatively accounts for **eqpac**'s floor to
> within its own uncertainty. It does **not** explain natl-vs-eqpac, does **not** predict the epoch
> response, and is **falsified as a monotone control knob** by the subsurface- and surface-iron
> up-weighting experiments. The full-6 sloppiness decades anti-correlate with recovery and carry no
> predictive content here.

### 1.6 Two amplification channels we are not currently separating

- **Integrator channel.** The box is 200 forward-Euler steps at `dt = 0.25 d`. Any step whose local
  amplification factor exceeds 1 compounds perturbations 200×, *upstream* of `J`. This is a distinct
  channel from parameter conditioning and would show up as seed variance, not systematic bias.
  `scripts/analysis/integrator_stationarity_check.py` exists; a per-AOI stability-margin report does not.
- **Roundoff channel.** The float32 hypothesis in
  `docs/findings/2026-07-27_conditioning_precision_hypothesis.md`. It is untested and its own caveats
  note the training dtype has not been audited end-to-end. Note that §1.2's `δJ` argument is
  **independent of dtype** and survives if the float32 test comes back null.

---

## 2. The parameter → observable → data hierarchy

### 2.1 What `Σ` the current loss actually assumes

Every anchor block in `scripts/run_v3.0_joint_multi_aoi.py` has the form

```
l_g  =  (1/N_g) Σ_cells (pred − obs)²  /  mean_cells(obs²)        # e.g. lines 1717–1727, 1749–1762, 1799–1804
z    =  Σ_g  w_g · l_g                                             # w_g = GEOTRACES_W, DANIELS_RPICPOC_W, …
```

So the code **is already whitening** — with a fabricated `Σ`:

```
Σ_g  =  (rms_g² / w_g) · I
```

i.e. **noise is assumed uncorrelated, identical in every cell of block g, with standard deviation
proportional to that block's own field RMS**, and the fraction of RMS set by `1/√w_g` up to a global
constant. The Darwin-pattern block is z-scored and divided by `(FET_W + 10)`, giving it
`Σ = σ_field²·(FET_W+10)/DARWIN_PATTERN_W`.

The absolute scale is irrelevant (it rescales the whole loss); **only the ratios across blocks carry
meaning**, and those ratios are currently statements about relative measurement precision that nobody
has written down. Concretely, the flagship's `GEOTRACES_W = 0.3` vs `GEOTRACES_SUB_W = 1.0` asserts that
surface bottle dFe is `√(1/0.3)/√(1/1) = 1.8×` noisier *in fractional terms* than subsurface bottle dFe.
That may even be defensible as a representativeness-error claim (surface dFe has larger spatiotemporal
variability relative to a 1° monthly box), but it is an assumption, not a measurement, and it was set by
sweep. `DANIELS_RPICPOC_W = 1.0` on an incubation compilation with large intrinsic scatter asserts that
a CP:PP incubation ratio is as fractionally precise as a bottle dFe measurement. It is not.

**This is the whole of complaint (a), in one line: we are computing the Fisher matrix of an
unjustified noise model, and then reading identifiability off its spectrum.**

### 2.2 The hierarchy matrix

Observable denominator = 4. `{Smallgrow, Biggrow}` are excluded by construction, not failed.

| parameter | role in the equations | Fisher role | data that actually carries the information | loss term(s) that deliver it | independent real anchor? |
|---|---|---|---|---|---|
| **alpfe** | surface Fe **source** scalar | **stiff** eigendirection | absolute magnitude of surface [DFe]; independently, the soluble-Fe deposition rate | `GEOTRACES_W` (surface dFe, real); `DUST_ANCHOR_W` Gaussian prior on physical alpfe from the Xu & Weber Al-inverse | **YES**, two of them. Recovers 49/50 and method-independently (DINN-free, Nelder-Mead, EKI) |
| **scav_rat** | iron **loss rate** | **sloppy** direction (`S/k` ratio) | the depth **gradient** of [DFe] to break `S/k`; ultimately an explicit **rate**: ²³⁴Th / ²¹⁰Po-derived scavenging or Fe export flux | `GEOTRACES_SUB_W` (real, subsurface); **plus** the z-scored `DARWIN_PATTERN_W` block, which is **load-bearing** — anchors-only drops it to 0/10 | **NO.** ⚠️ No independent real *rate* observable is in the loss. Recovery is partly model-pattern-assisted. This is the weakest link in the manuscript |
| **R_PICPOC** | calcite rain ratio | **exact null** of the iron Fisher (Fisher info = 0) | a real calcite **production**-ratio observable | `DANIELS_RPICPOC_W` (real Daniels CP:PP) — flagship has `RATIO_W = 0`, so the circular Darwin-ratio path is off | **YES.** Anchor-off collapses 50/50 → 6/50 (epoch-matched) / 4/50 (1500 ep). ⚠️ No Southern-Ocean Daniels coverage; anchored only in eqpac + natl |
| **diatomgraz** | diatom palatability multiplier on a grazing flux | a **different block** (bSi / Chl rows); iron-orthogonal (alignment 0.02) | the **pattern** of the field it modulates (Chl1) **plus** the environment that gates it (MLD, as a DINN input channel — an information addition, not capacity) | `CHL1_W_EXTRA`, `POSI_W` / `POSI_DARWIN_W`, MLD input channel | **NO.** ⚠️ The Chl target is Darwin's own output and the POSi target is a steady-state diagnostic (partly circular). Model-internal consistency, not real-data validation |
| **Smallgrow, Biggrow** | max growth rates (PCmax) | confounded with grazing and limitation | group-resolved production **and** temporal moments of the annual cycle | none active | **NO — excluded by construction.** Not a failure |

Marked plainly: **two of the four observable parameters (`scav_rat`, `diatomgraz`) have no independent
real anchor in the flagship loss.** `alpfe` and `R_PICPOC` do. That asymmetry, not the count 25/50, is
the honest headline of the identifiability study.

### 2.3 The single design rule this table is generated by

The per-parameter schema in `docs/findings/2026-07-24_parameter_specific_schema.md` already states it:

> To make a parameter identifiable, add an observation operator whose Jacobian **row has nonzero
> projection onto that parameter's currently null or sloppy direction**.

"Subsurface iron section for `scav_rat`", "calcite anchor for `R_PICPOC`", "MLD channel for
`diatomgraz`" are one rule applied to three different null directions. Quantitatively this is the
alignment column of the observation-design table: candidates with alignment ≈ 0.02 leave κ at ~2200,
candidates with alignment 0.70–0.97 collapse it to 2.5–9.9
(`docs/findings/2026-07-23_observation_design.md:96–105`). **Alignment, not volume, is the design
variable.**

---

## 3. A hierarchical training scheme

Six components, roughly in order of (value ÷ risk). They compose; H1 is a prerequisite for H2 and H6.

### H1 — Replace the fabricated `Σ` with real per-anchor noise covariances (generalised least squares)

**The change.** For each anchor block `g`, replace `scale = mean(obs²)` and the hand-set `w_g` with a
published or estimated measurement + representativeness variance `σ_g²`:

```
L(θ)  =  Σ_g  (1/2) ‖ Σ_g^(-1/2) ( y_g − G_g(θ) ) ‖²        with Σ_g from data-provider uncertainties
```

Anchors with quotable uncertainties: GEOTRACES dFe (bottle precision + QC flags 49/50 already used),
GLODAP DIC/ALK (mapped-climatology error fields), Daniels CP:PP (incubation scatter), MODIS PIC
(algorithm uncertainty), Black 2020 Fe export flux, Cochran GP15 ²¹⁰Po/²¹⁰Pb. Where a provider gives no
uncertainty, estimate `σ̂_g = ‖r_g‖/√m_g` from the current fit (arXiv:2604.16919 Prop. 2 gives this
estimator) and **state that it is estimated, not measured**.

**Buys.** The Fisher matrix becomes the Fisher matrix of the actual observing system, so every
downstream identifiability claim (κ, CRLB, sloppiness, OED rankings) becomes a statement about the
observing system rather than about a sweep. It also makes `AOI_W_*`, `GEOTRACES_W`, `DANIELS_*_W` and
`PIC_ABS_W`/`POC_ABS_W` defensible or retires them.

**Costs.** Real work in building the uncertainty table, most of which is *representativeness* error
(point bottle vs 1° monthly box cell), which nobody publishes. That term will likely dominate the
instrument term and will have to be estimated. It is also a **behaviour change**: §1.5 Test 4 shows
anchor reweighting can swing `scav_rat` per-AOI by an order of magnitude in either direction.

**Test.** Rerun the flagship with GLS weights, n = 10 screen then n = 50. Prediction, falsifiable: the
Daniels block down-weights relative to GEOTRACES (its fractional scatter is larger), so **`R_PICPOC`
falls from 50/50 toward the anchor-off 6/50 unless the Daniels operator is genuinely tight**. If
`R_PICPOC` survives GLS weighting, that is a far stronger manuscript claim than 50/50 under a swept
weight. If it collapses, we have learned that the 50/50 was weight-conditional — which we need to know.

### H2 — Marginalise a nuisance variance per anchor block instead of tuning it

**The math** (arXiv:2604.16919 Sec. 3.3, Eqs. 10–11). Put a Jeffreys prior `p(σ²) ∝ 1/σ²` on an unknown
block noise variance and integrate it out analytically:

```
p(y_g | θ)  ∝  ( ½‖r_g(θ)‖² )^(−m_g/2)
log p(y_g | θ)  =  −(m_g/2) log ‖r_g(θ)‖² + const
∇ = −(m_g/2) ∇‖r_g‖² / ‖r_g‖²         ⟹  effective precision = m_g/‖r_g‖², self-calibrating
```

Grouped over anchors, the objective becomes a **sum of log residual norms**:

```
L(θ)  =  Σ_g  (m_g/2) · log ‖ r_g(θ) ‖²
```

Prop. 2 of that paper proves this reduces to the oracle `1/σ_g²` weighting when the prior is tighter
than the noise, so it is not a heuristic reweighting.

**Buys.** Scale invariance: rescaling any anchor's units shifts `L` by a constant and leaves the
gradient unchanged. That is exactly the property a heterogeneous-units, eight-loader loss needs, and it
retires the entire `*_W` sweep as a tuning surface.

**Costs and one hard caveat.** `L` carries `+log‖r_g‖²` per block, so it is **unbounded below as
`r_g → 0`** — the minimiser can drive `L → −∞` by fitting one block alone. (An earlier version wrote
this as `−log‖r_g‖²`, which tends to *`+∞`* and would be harmless; the sign was a typo, the failure
mode is real. Corrected 2026-07-29 after review.) So a block that can be
fitted near-exactly (the z-scored Darwin-pattern block, which is model-vs-model and therefore fittable
to far lower residual than any real anchor) will swallow the objective and starve the real anchors. The
paper does not need this fix because it has one measurement block; we have eight. **Use a proper
inverse-gamma with nonzero rate — i.e. a per-block variance floor from H1's uncertainty table — not the
improper Jeffreys limit.** Note also that this is the *grouped* extension; the paper marginalises one
global scalar variance. The grouped construction is standard Bayesian practice but **no primary source
for it was retrieved in this session**, so it must be presented as a construction, not a citation.

**Test.** Same as H1, and directly comparable: H1 fixes `Σ` from external knowledge, H2 infers it from
the fit. If they disagree about which anchor deserves weight, that disagreement is itself a result.

### H3 — Adaptive per-block balancing (the cheap intermediate)

If H1/H2 are too large a step for the next sweep, the PINN literature offers three drop-in balancers
for exactly this failure mode ("`L_data` and `L_residual` differ by orders of magnitude; one dominates
and the other is ignored"):

- **Gradient-norm annealing** — set `λ_g` from running per-term gradient-norm statistics (arXiv:2001.04536).
  Cheapest; implementable inside the existing loop in a day.
- **NTK-eigenvalue weighting** — weight each term by the curvature it actually contributes
  (arXiv:2007.14527). This is a Fisher-information argument in disguise and is the training-dynamics
  face of §1's static conditioning.
- **Self-adaptive (trainable, adversarial) weights** (arXiv:2009.04544 / DOI 10.1016/j.jcp.2022.111722).
  ⚠️ Adversarial up-weighting of a hard-to-fit block will preferentially up-weight the **noisiest**
  anchor. Only use paired with an H1 variance floor.

**Buys.** Removes the hand-tuning without needing an uncertainty table. **Costs.** None of these is
principled about *measurement noise*; they balance optimisation dynamics, not statistics. They will not
make the Fisher matrix correct. **Test.** Cheap n = 10 screen against the flagship; grade per-AOI.

### H4 — Solve in the Fisher / SVD basis, not in raw parameter coordinates

**The math.** Take `SVD(J̃) = UΣ_sVᵀ` at the current `θ`. Split at the noise-determined index `k`:
estimate the stiff coordinates `{v_1 … v_k}` from data; **prior-bound**, do not fit, the sloppy
coordinates `{v_{k+1} … v_n}`. This is truncated SVD with filter factors `f_i = 1 (i ≤ k), 0 (i > k)`
(DOI 10.1137/1.9780898719697). For the iron pair the eigenvectors are already known and interpretable:
surface [DFe] has stiff direction `(alpfe −0.77, scav_rat +0.63)` — the *difference* — and sloppy
direction `(−0.63, −0.77)` — the *covariation*, i.e. the `S/k` ratio at fixed [DFe]
(`docs/findings/2026-07-23_observation_design.md:79–80`). The natural reparameterisation is
`(ratio, product)`; only the identifiable combination is exposed to the optimiser.

**Buys.** This is the correct answer to "flat profile likelihood yet 49/50 recovery": in a sloppy model
the *constrained* objects are **combinations**, and an individual parameter axis being flat says
nothing (arXiv:q-bio/0701039; DOI 10.1063/1.4923066). It also makes the discarded directions
*reportable objects* — named linear combinations with honest error bars — rather than failures. And it
directly retires §1.4's κ² problem in the diagnostics.

**Costs.** `J̃` is `θ`-dependent, so the basis rotates during training; either re-SVD on a schedule or
freeze the basis at a reference `θ` and report it as a local statement. The prototype exists
(`scripts/analysis/eki_core.py`; the EKI posterior was verified perpendicular to the analytic sloppy
direction at 1.000).

**Test.** Reparameterise the iron pair as `(ratio, product)` with the product prior-bounded, rerun the
flagship, n = 10 then n = 50.

> **Corrected 2026-07-29 (review).** The earlier prediction credited the variance drop to the
> reparameterisation itself. That cannot be right, and this note's own header says so: an invertible
> change of coordinates **leaves the CRLB unchanged**. Two separable mechanisms are bundled here, and
> only one of them can move variance:
>
> 1. **Optimiser conditioning** — in the eigenbasis the two directions decouple, so Adam makes the same
>    progress in fewer epochs. This changes *where the run lands at a fixed epoch budget*, not the
>    attainable variance. It is the mechanism that would explain natl reaching its 4000-epoch count at
>    2000 epochs (§5, row `scav_rat` natl).
> 2. **The bound on the product** — this is added regularisation, and it is the *only* part of the
>    intervention that can lower the attainable variance at all.
>
> So run it as an A/B: reparameterised with the product bounded, and reparameterised with it free. If
> only the bounded arm moves, the gain is prior information, and it should be reported as such rather
> than as a conditioning win.

Prediction: recovery count in sopac and natl rises at the 2000-epoch budget, and **eqpac does not move**
— reparameterisation and regularisation both act on amplification, neither creates information (see §4).

### H5 — Staged / greedy inversion

Fix well-conditioned directions first, then release sloppy ones. Precedent: SINDy's STLSQ re-solves
least squares on the active set only after thresholding (DOI 10.1073/pnas.1517384113) — a crude but
published hierarchical decomposition, "only invert the block the data constrains".

Concretely here, and this is already half-implemented as the dust anchor: pin `alpfe` from the
out-of-manifold Xu & Weber deposition prior (`DUST_ANCHOR_W`; verified to hold `alpfe` 5/5 while leaving
`scav_rat` at 0/5 exactly as predicted, `docs/findings/2026-07-22_dust_anchor_ab_b200.md`), then invert
`scav_rat` against a sink observable with `alpfe` frozen. The two-anchor OSSE
(`docs/findings/2026-07-22_two_anchor_osse_verified.md`) shows the geometry works: DFe alone is rank-1
with CRLB(log scav) = ∞; +dust +Th flux with export pinned gives `|ρ| = 0.195`, CRLB 0.164, scav CV 0.14.

**Buys.** Turns one badly-conditioned 4-parameter solve into a sequence of well-conditioned 1–2
parameter solves. **Costs.** Staging propagates bias: an error in the frozen `alpfe` becomes a
systematic offset in `scav_rat`, and the frozen value's uncertainty must be carried forward (fix by
sampling `alpfe` from its prior across seeds rather than freezing at the mean).
**⚠️ The OSSE's own caveat is load-bearing:** the `scav_rat` break is **conditional on pinning the export
partition**. With export free as a nuisance, `scav_rat` stays confounded (CRLB ∞) even with both
anchors. Any staged design must include the partition (UVP5 particle field / POC flux, i.e.
`rufas2024_poc_flux_loader`).

### H6 — Tikhonov with a principled parameter choice

```
θ_λ = argmin { ‖J̃θ − d̃‖² + λ²‖L(θ − θ₀)‖² } ,   filter factors f_i = σ_i²/(σ_i² + λ²)
amplification f_i/σ_i = σ_i/(σ_i² + λ²) ≤ 1/(2λ)  ∀i    ⟹   κ_eff = σ₁/max(σ_n, λ) ≤ σ₁/λ
```

The ill-conditioning is **capped by construction** (DOI 10.1137/1.9780898719697;
DOI 10.1137/S0895479897326432). Bias grows as `λ²`; this is a bias-variance trade, not a free lunch.

**Numerically:** never form `(JᵀJ + λ²I)`. Solve the stacked problem `min ‖[J̃; λL]θ − [d̃; 0]‖` by QR,
which keeps the computation at `κ(J)`, not `κ(J)²`.

**Choosing λ.** Three classical methods. For **us, the discrepancy principle is the most defensible**,
because our anchors come with quotable measurement uncertainties: choose λ so `‖J̃θ_λ − d̃‖ = τδ`,
τ ≳ 1, with `δ` the known noise level — it converts each anchor's published error bar into a stopping
criterion instead of a hand-tuned weight. GCV is the fallback when `δ` is unknown. The L-curve is a
useful *visual* diagnostic; note it is known not to converge as `δ → 0` for a broad problem class.
**No identifiers were retrieved this session for the discrepancy principle, GCV, or the L-curve
non-convergence results** — cite Hansen's monographs (DOI 10.1137/1.9780898719697,
DOI 10.1137/1.9780898718836) for the treatment, and do not attach author-year citations to the
individual methods until identifiers are fetched.

**Buys.** A defensible, tunable cap on noise amplification, and a *principled* per-block generalisation:
one `λ_g` per anchor block is precisely "each parameter gets its own data", expressed as a well-posed
penalised LS problem rather than as ad-hoc weights. **Costs.** Bias, and the λ-selection machinery.
**Test.** Because our per-cell DINN already regularises implicitly (bounded head + environment
smoothness), the first experiment is *measuring the implicit λ*, not adding an explicit one — see E5.

### H7 — Two diagnostics to add regardless of which of H1–H6 we adopt

**(i) The discrete Picard plot, per anchor and per AOI** (DOI 10.1007/BF01933214). On one semilog axis
plot `σ_i`, `|u_iᵀd̃|`, and `|u_iᵀd̃|/σ_i` against `i`. The index where `|u_iᵀd̃|` levels off at the noise
floor while `σ_i` keeps decaying is the honest truncation level `k`; the upturn in the ratio **is** the
noise amplification, made visible. For n = 4 this is four points per block and costs one plot.

> **This is the single highest-value diagnostic in the document.** It distinguishes two diagnoses that
> the repo currently cannot separate: eqpac fails because `σ₄` is too small (**conditioning** — fixable
> by reparameterisation, regularisation, or an aligned new observable) versus eqpac fails because
> `|u₄ᵀd̃|` is **already at the noise floor** (**information** — fixable only by new data). §1.5 Test 1
> suggests the latter; the Picard plot would settle it.

**(ii) Per-anchor residual floors** (arXiv:2604.16919 Cor. 1.1). The expected residual saturates,
`E‖y_g − G_g(θ)‖² → m_g σ_g²`. Driving a residual **below its own noise floor is definitionally noise
overfitting**. Log per-anchor residuals during training and flag any block that crosses `m_g σ_g²`.
Directly bears on whether the 2000 → 4000 epoch gain (trio 25/50 → 41/50) is recovery or noise fitting:
it is only credible if the real-anchor residuals are still above their floors at 4000 epochs.

### 3.8 One idea considered and rejected

The corpus's NCS paper (arXiv:2510.23633) does **not** apply. Four independent premise failures: it
needs a pretrained generative prior over the unknown (we have none over the Carroll-6, and building one
requires the Darwin ensemble whose absence is the original problem); it requires a **linear** forward
operator (ours is 200 Euler steps of a stiff BGC ODE); it targets `d ~ 10⁵` unknowns that are
*deficient in count*, whereas we have 4–6 unknowns that are *degenerate in direction*; and it contains
**no** conditioning analysis and **no** hierarchical likelihood structure — its "noise" is the sampler's
own injected Gaussian noise, a design variable, not observational noise. It also markets Jacobian
avoidance as a feature, which is disqualifying for a problem whose difficulty *is* the Jacobian
spectrum. (The corpus additionally documents an unacknowledged gap in its Appendix A Lemma 1: the
optimal `γ*` is a function of the very noise draws the lemma assumes it is independent of, so the
Gaussianity-preservation claim is unproved.) Consistent with the repo's own finding that diffusion adds
no skill over deep ensembling here.

The one idea worth stealing from it is **direction-only, magnitude-capped guidance**: normalise each
anchor's gradient contribution to unit norm and let the optimiser choose only the direction, so no
anchor can dominate by magnitude. **This is an extrapolation by analogy, not a claim of that paper** —
it makes no statement about multi-anchor weighting. It is essentially H3's gradient-norm balancing with
a hard cap, and should be treated as a variant of H3, not as a cited method.

---

## 4. What this cannot fix

Regularisation changes the bias-variance trade-off. **It does not create information.** Splitting our
known failures on that line:

### Conditioning problems — fixable by better math, no new data

| failure | evidence it is conditioning | fix |
|---|---|---|
| `scav_rat` natl 20/50 @2000 ep | rises to **40/50 at 4000 ep with no new data and unchanged κ**; implied error inflation 4.4× vs a κ-permitted 16–23× | H4 (Fisher-basis reparameterisation) should get most of this at 1× compute instead of 2× |
| trio 25/50 @2000 ep | tracks `scav_rat`'s binding leg exactly; rises to ≈41/50 at 4000 ep | same |
| `κ² ` in the diagnostics | §1.4; `n ≤ 6`, SVD is free | never form `JᵀJ`; SVD everywhere |
| arbitrary anchor weights | §2.1: `Σ_g = (rms_g²/w_g)I` is fabricated | H1 / H2 |

### Observability problems — fixable ONLY by new data

| failure | evidence it is information, not optimisation | what would actually fix it |
|---|---|---|
| **`scav_rat` in eqpac: 7/50 @2000, 6/50 @4000** | 2× compute moves it **by −1 seed**. Implied error inflation 13–15× sits at the κ-predicted bound. This is the cleanest information-limit statement in the project | an aligned observable: ²¹⁰Po/²¹⁰Pb scavenging rate (`cochran_gp15_po_pb_loader`, alignment 0.70, κ 2930 → 6.9) or Fe export flux (`black2020_fe_flux_loader`). **Both loaders exist; neither is wired into the training loss** |
| **`scav_rat` has no independent real rate anchor at all** | anchors-only ablation collapses it to 0/10 — its recovery leans on the z-scored **Darwin-pattern** block, i.e. on model output | same as above. Until then, `scav_rat` recovery is model-pattern-assisted and the manuscript must say so |
| **`R_PICPOC` without Daniels** | 50/50 → 6/50 epoch-matched. No amount of iron data touches it: it is the **exact null direction** of the iron Fisher, Fisher information **= 0** | it already has its fix (the real Daniels anchor). ⚠️ but no Southern-Ocean coverage — anchored in 2 of 3 AOIs only |
| **`diatomgraz` from independent real data** | Chl target is Darwin's own output; POSi is a steady-state diagnostic (partly circular) | a real, non-circular diatom-specific observable. None is currently in the loss |
| **`Smallgrow`, `Biggrow`** | growth is confounded with grazing and limitation; bulk data gives only the biomass-weighted mean | group-resolved production **plus** temporal moments. **Unobservable by construction — excluded, not failed** |
| **The 3-of-4 frontier** | `geo1` holds {alpfe, scav_rat, R_PICPOC}; MLD + heavy Daniels holds {alpfe, diatomgraz, R_PICPOC}; the decisive full-loss + MLD test at **4000 epochs** gives diatomgraz **0/10** and degrades the others | see below |

### Three structural statements that no scheme in §3 changes

1. **The 3-of-4 mutex is a Pareto frontier, not a bug.** `scav_rat` needs the Darwin-pattern term;
   `diatomgraz` needs MLD; they conflict, and 2× compute does not bridge it. Reweighting slides us along
   the frontier; it does not move the frontier. The honest formulation is explicitly **multi-objective**
   rather than scalarised (arXiv:2110.09813) — report the frontier and the two operating points, do not
   search for a single config that "wins".

2. **The surrogate gap is a bias term, and it is the `κ² tan φ` channel.** The 0-D box homogenises the
   spatial structure of a 3-D model. That structural error is `δJ`, it is systematic, it does not
   average over seeds, it does not shrink with epochs, and it is **amplified by κ², not κ**. No loss
   reweighting removes it. Only a better forward operator (or a surrogate-to-GCM validation that bounds
   it, #163) does.

3. **More of the same data is worthless, exactly and measurably.** A second identical surface-[DFe]
   survey: variance ×2.00, κ unchanged at 2930, alignment 0.00. Unrelated surface concentrations (POC,
   PIC) and biological Fe uptake behave identically (≈2×, κ ≈ 2200–2500). The design variable is
   **alignment with the null direction**, and it is computable before any ship time is spent.

---

## 5. Ranked next experiments

Ranked by (information gained) ÷ (cost). Each has a prediction that can be wrong.

### E1 — Measure the per-AOI seed spread of `scav_rat` and compare it against §1.5 Test 1

**Cost: zero compute.** Re-grade the existing n = 50 `n50e2k_percell_trio` and `ep4k_n50` ensembles.

**Prediction (falsifiable):** the per-AOI *relative* standard deviation of recovered `scav_rat` across
seeds is ≈ **0.17 (sopac), ≈0.76 (natl @2000), ≈0.31 (natl @4000), ≈2.3 (eqpac, both budgets)**. These
are back-outs from the pass fractions under a Gaussian assumption with the ±40% band; if the measured
spreads match, the probit model in §1.5 is validated and κ-based reasoning is licensed. If they do not
match (e.g. the errors are strongly bimodal, or biased rather than spread), the entire §1.5 analysis is
wrong and must be retracted. **Do this first — it is free and it gates everything else in §1.**

### E2 — Discrete Picard plots, per AOI, for the iron block

**Cost: one forward pass per AOI (the `observation_design.py` machinery already builds the Jacobian) plus
a plotting script. Hours, CPU-only.**

**Prediction:** in sopac, `|u_iᵀd̃|` decays faster than `σ_i` for all four indices (Picard condition
satisfied — well-posed). In eqpac, `|u₄ᵀd̃|` flattens at the noise floor while `σ₄` keeps decaying, and
`|u₄ᵀd̃|/σ₄` turns upward. **If eqpac's ratio turns up, eqpac is an amplification problem and H4/H6 will
help. If `|u₄ᵀd̃|` is already at the floor, eqpac is an information problem and only E3 helps.** These
are different diagnoses with different actions, and this is the cheapest way to distinguish them.

### E3 — Wire the ²¹⁰Po/²¹⁰Pb + Fe-export-flux sink anchors into the training loss

**Cost: loader work is done** (`cochran_gp15_po_pb_loader.py`, `black2020_fe_flux_loader.py` exist and are
documented). Needs an observation operator in `run_v3.0_joint_multi_aoi.py` (the box's
`scav_rat · DFe · POC` removal term integrated to a flux), a weight/variance entry, and an n = 10 screen
then n = 50. **Roughly one implementation day + one cluster night.**

**Prediction, from the OED and the OSSE:** iron-block κ collapses 2930 → ~7 and `scav_rat` **eqpac** rises
materially above 7/50 — this is the only intervention in this document predicted to move eqpac.
**Conditional, and the condition is load-bearing:** the two-anchor OSSE shows the break requires the
**export partition** to be pinned; with export free as a nuisance, CRLB(log scav) stays ∞ even with both
anchors. So run it *with* a POC-flux/transfer-efficiency term (`rufas2024_poc_flux_loader`) and *without*,
as an A/B. If eqpac does not move even with the partition pinned, the surrogate's 2-layer structure —
not the observing system — is the binding constraint, and that is a Track-2 finding.

**This experiment is the highest-value item in the document**, because it is the only one that attacks a
measured *information* limit rather than a conditioning or optimisation limit, and because it also
supplies `scav_rat`'s first independent real anchor (§2.2's flagged gap).

### E4 — Fisher-basis reparameterisation of the iron pair `(ratio, product)`

**Cost:** `eki_core.py` already implements the eigenbasis machinery; the change is in the DINN
parameter head. One implementation day + one cluster night for n = 10, one more for n = 50.

**Prediction:** `scav_rat` per-AOI rises in **sopac and natl** and reaches the 4000-epoch counts at the
2000-epoch budget (i.e. ~40/50 natl at half the compute), while **eqpac does not move**. That split is
the whole point: neither reparameterisation nor the product bound creates information. Per H4's
correction, run product-bounded and product-free as an A/B — the coordinate change buys *optimiser
conditioning at a fixed epoch budget* (which is what the natl claim above rests on), while any drop in
attainable variance comes from the bound, i.e. from prior information. If eqpac *does* move, §1.5's
information-limit reading of eqpac is wrong and E2's Picard plot should have shown it.

### E5 — Measure the implicit regularisation the per-cell DINN already applies

**Cost:** a bounds sweep. Widen `alpfe`'s parameter bound (and separately, the environment-smoothness of
the per-cell map) and re-run n = 10.

**Rationale.** `alpfe`'s profile likelihood is **flat** yet it recovers 49/50. In a Tikhonov/prior
picture the posterior variance along a direction with small `σ_i` saturates at the *prior* variance
rather than blowing up as `1/σ_i²` — flatness does not imply non-identifiability when the prior is
informative (arXiv:q-bio/0701039; the regime split follows from the filter factors in
DOI 10.1137/1.9780898719697). Our "prior" is the bounded DINN head plus environment smoothness.

**Prediction:** `alpfe`'s recovery degrades roughly as the *square* of the bound width, while
`scav_rat`'s is much less sensitive (its `σ_i` is basin-dependent and data-dominated, not
prior-dominated). **If `alpfe` is insensitive to its bound width, then it is genuinely data-identified
and the flat-profile puzzle is resolved in the other direction** — also a good outcome, and a cleaner
manuscript claim.

### E6 — GLS whitening (H1) as an A/B against the flagship

**Cost:** the uncertainty table is the real work (days, mostly literature and representativeness
estimation); the code change is small. One n = 10 screen, one n = 50 confirm.

**Prediction:** `R_PICPOC` is the sensitive one. Under GLS the Daniels block down-weights relative to
GEOTRACES, so `R_PICPOC` falls from 50/50 toward the 6/50 anchor-off floor **unless** the Daniels
operator is genuinely tight. Either outcome is publishable and one of them is currently unknown.
Secondary prediction: `alpfe` is unaffected (it recovers method-independently and is separately pinned
by the dust prior).

### E7 — Replace every explicit `JᵀJ` in the diagnostics with an SVD of `J̃`, and audit the training dtype

**Cost: hours.** Purely a numerics change with no scientific decision attached.

**Prediction:** the reported per-AOI condition numbers and sloppiness decades shift by less than a factor
of 2 (the FD Jacobian step, `rel-eps = 2e-2`, likely dominates the error budget over the `κ²` roundoff).
**If they shift by more than that, some published sloppiness numbers are numerical artifacts and must be
re-issued.** This is cheap insurance, and it also settles the precondition that
`docs/findings/2026-07-27_conditioning_precision_hypothesis.md` itself flags: the end-to-end training
dtype has not been audited, and the float32 test is meaningless until it has been.

---

## 6. One-paragraph summary

Noise amplification here is governed by the singular spectrum of the whitened Jacobian
`J̃ = Σ^(-1/2)J`: the estimator expands the data in the right singular basis with weights `1/σ_i`, the
relative parameter error is bounded by `κ/cos φ` (data error) plus `κ² tan φ` (model error), and forming
`JᵀJ` squares κ because `λ_i = σ_i²`. Applied to our numbers, the 2×2 iron-block condition number
explains the Southern-Ocean-versus-rest split and quantitatively accounts for the eqpac floor, but it
does not separate eqpac from natl, does not predict the epoch response, and is falsified as a monotone
control knob by the two iron-up-weighting experiments; the full-6 sloppiness decades anti-correlate with
recovery outright and should stop being quoted as if they predicted it. The hierarchy the project needs
is not a re-weighting of one scalar loss but a per-block whitening by real noise covariances — the
current loss already whitens, with a fabricated `Σ_g = (rms_g²/w_g)I` — combined with solving in the
Fisher eigenbasis so that only identifiable combinations are exposed. None of that creates information:
`scav_rat` in the equatorial Pacific, `diatomgraz` from independent real data, and the growth pair are
observability limits, and the single highest-value action in this document is wiring the already-built
²¹⁰Po/²¹⁰Pb and Fe-export-flux loaders into the loss, because a scavenging-*rate* observable is the one
thing measured to collapse that block's condition number by three orders of magnitude — and because
`scav_rat` currently has no independent real anchor at all.
