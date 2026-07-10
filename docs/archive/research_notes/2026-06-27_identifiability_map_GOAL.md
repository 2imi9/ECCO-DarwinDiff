<!-- Authored by deep-research Workflow wf_1eae1053 (theory / prior art / implementation / validation). -->
<!-- Loop-reviewed 2026-06-27 against the verified box-homogenization finding. -->

> **LOOP FOLD-IN (box homogenization) — read first.** The box relaxes to a spatially near-uniform
> STATE at uniform Carroll params (verified: tracer CV 4e-5 @200 -> 1e-15 @6400;
> `2026-06-27_box_homogenization_DEFINITIVE.md`). This does NOT block the map, but it names where the
> map's spatial signal actually comes from: **NOT the box-state pattern (flat), but (1) the observation
> noise model Sigma — i.e. WHERE real data exists (GEOTRACES iron, Daniels/MODIS PIC, dense POSi) — and
> (2) the forcing-modulated sensitivity J = d(observable)/dtheta (SST/wind vary the per-cell Jacobian).**
> The `FIM = J^T Sigma^-1 J` formulation below already encodes this (Sigma -> inf where no data, so the
> FIM is zero there), so the goal is sound. Two binding additions: (a) a **Phase 0 feasibility gate** —
> confirm the converged per-cell J has nonzero forcing-driven spatial variation before building the full
> map (if J is also flat, the deliverable reduces to an observation-coverage map, still useful but a
> weaker claim); (b) the convergence gates G1/G2/G3 below must use the **sensitivity** pattern, not the
> state pattern, since the state's variance floor is machine-epsilon. Do NOT interpret any output as
> box-state fidelity.

---

All grounding confirmed. The convergence finding note (`2026-06-27_box_convergence_finding.md`) is referenced by track 4 but isn't on this branch — it lives on the spine-d worktree. I'll cite it as the load-bearing finding the brief already provides, treating the slow-mode numbers (eig 0.9957) as given. I have everything needed. Here is the goal document.

---

# Goal Document: Per-Parameter Spatial Identifiability Map for the Carroll-6 Parameters in the DarwinDiff Box

**Status:** scoping / pre-build
**Owner:** Track 1 (parameter-learner), spine D adjacent
**Target artifact:** `scripts/identifiability_map.py` + `docs/findings/identifiability_map_regions.json` + per-parameter global figures
**Frames the manuscript as:** a *surrogate-to-model identifiability study* (where on Earth is each Carroll-6 parameter identifiable), **not** a 6/6 recovery claim.

---

## 1. Problem statement

DarwinDiff recovers the six Carroll-6 parameters (`alpfe`, `scav_rat`, `Smallgrow`, `Biggrow`, `diatomgraz`, `R_PICPOC`; registry in `src/darwindiff/carroll6.py`) by gradient descent through a 0-D differentiable box (`carroll6_5pft_2layer`, 15 state vars, 2 layers) driven by a per-cell DINN. Training currently uses **three hand-picked AOIs** — equatorial Pacific, N Atlantic subpolar, Southern Ocean Pacific — and a hand-ablation (v3.1.1, n=200 fresh-seed fits) attributed parameters to regions: eqpac → `alpfe`+`diatomgraz`, natl → `Biggrow`+`R_PICPOC`, SO → `scav_rat` (STATUS.md per-AOI gating). The hand-picked AOIs are a methodological liability: the region set is unjustified, the attribution is an empirical recovery-rate artifact rather than a structural statement, and a reviewer cannot tell whether a parameter recovered because the *data there constrain it* or because the *loss weights were tuned to make it recover*.

This document scopes a **principled, information-theoretic diagnostic** that answers, per grid cell, *where on Earth each Carroll-6 parameter is identifiable* — computed from the Fisher information / Cramér-Rao bound of the box's observables with respect to each parameter, at the **converged steady state**. It is a standalone forward diagnostic over a fixed global parameter vector. It is **not** a learned component of the recovery NN: letting the recovery DINN select its own regions from this map would reward-hack and destroy the clean per-cell structural argument. The deliverable replaces "we hand-picked three regions" with "the iron pair is identifiable in high-dust / strong-DFe₂-gradient cells; `R_PICPOC` in thermally-gated coccolithophore cells; the growth pair is unidentifiable everywhere."

---

## 2. Hypotheses (falsifiable)

**H1 (steady-state, not transient).** The identifiability verdict computed at the converged steady state (≥1600 forward-Euler steps) differs *qualitatively* from the 200-step transient verdict. Concretely: the eqpac iron sensitivity sign flips between the two (brief: box-vs-Darwin FeT pattern r = −0.96 @200 steps → +0.81 @3200 steps). *Falsified if* the per-cell sensitivity argmax is identical at 200 and 1600 steps for the iron cells.

**H2 (validation — map reproduces the hand-ablation attribution, in rank).** Aggregated over each hand-picked AOI footprint, the per-cell marginal identifiability ranks the parameters consistently with the v3.1.1 recovery ablation: eqpac ranks `alpfe`/`diatomgraz` highest, natl ranks `R_PICPOC` (and `Biggrow`) highest, SO ranks `scav_rat` highest. Pre-registered pass: Spearman rank correlation ρ ≥ 0.6 between the map's per-AOI parameter-stiffness ordering and the ablation's per-AOI cal-grade ordering across the 6×3 = 18 (param, AOI) cells. *This is a rank test, not a value match* — the ablation folds in cross-AOI coupling, seed noise, and bounds-clipping that a local FIM cannot, so exact agreement is not expected and disagreements are diagnosed, not auto-failed.

**H3 (sanity — growth pair flat everywhere).** The `Smallgrow` and `Biggrow` marginal-identifiability fields are low and flat over the *entire* ocean under a real-data noise model, and these two parameters are *never* the per-cell argmax. No real observable constrains growth rates, so a correct map must show them sloppy everywhere. *Falsified if* any cell flags either growth parameter as confidently identifiable — that is a contamination signal (growth↔grazing or growth↔iron-quota degeneracy leaking signal, or a transient-FIM leak), not a discovery.

**H4 (scav_rat is contrast-driven, not single-cell-local).** `scav_rat` is marginally identifiable only where the surface↔subsurface dissolved-iron contrast is present (the DFe₂ channel, state index `I_DFE_2 = 10`, breaks the `alpfe`↔`scav_rat` surface-budget degeneracy). The map shows `scav_rat` jointly sloppy with `alpfe` wherever only surface DFe is constrained, and separable only where DFe₂ is informative. *Consistent-with, not falsified-by*, `scav_rat` looking sloppy in single-cell-local FIM away from strong subsurface gradients.

**H5 (R_PICPOC thermally gated).** `R_PICPOC` marginal identifiability lights up where calcite production is both large and thermally gated (coccolithophore window), i.e. subpolar N Atlantic / bloom zones, and is sloppy in oligotrophic low-PIC cells.

---

## 3. Method — Fisher / CRLB at the converged steady state

The map is a per-cell, per-parameter scalar field built in five stages. Stages 2–4 are the load-bearing distinction from a naive sensitivity heatmap.

### 3.0 Notation

- θ ∈ ℝ⁶ — the Carroll-6 vector, held **constant across all cells** at θ₀ = `CARROLL_VALUES` (single global θ; the diagnostic asks where the *global* θ is most constrained).
- u_c — per-cell forcing (SST, SSS, wind, latitude, dust), from the Darwin target cache.
- f(x, θ; u_c) — the per-step tendency assembled in `carroll6_5pft_2layer_step` (the dx/dt vector; box source `src/darwindiff/carroll6_5pft_2layer.py:306`).
- x*(θ, u_c) — the converged steady state, f(x*, θ; u_c) = 0.
- g(x) — the **observable map**: exactly what the loss compares (see §3.2).

### 3.1 Stage 1 — Converged steady state (non-negotiable)

The recovery integrates only N_STEPS = 200 forward-Euler steps at dt = 0.25 d (`box_vs_darwin_fidelity.py:48-49`). The linearized box has a slow dissipative mode (one-step-map eigenvalue ≈ 0.9957 ⇒ relaxation time τ = −dt / ln(0.9957) ≈ 230 steps). At 200 steps the trajectory is an **under-converged transient** — a sensitivity evaluated there measures dx(t)/dθ of an unconverged trajectory, a different and artifactual object than the steady-state dx*/dθ.

**Requirement:** integrate to ≥ 1600 steps (≥ ~7τ; residual transient ≈ e⁻⁷ ≈ 0.1%) **and verify convergence per cell** — a single global step count is *not* uniformly converged because τ varies with forcing. Per-cell convergence gate (all three must hold, else mask the cell):

- **G1 — steady-state residual:** ‖f(x*; θ)‖ / ‖x*‖ < tol.
- **G2 — pattern stability across a doubling:** the per-cell observable sensitivity at N and 2N agrees (z-scored pattern r(N, 2N) ≥ 0.99). This catches the documented FeT *oscillation* (the brief's convergence probes report the box-vs-Darwin FeT r alternating regimes deep in the integration, not monotone relaxation) — a single fixed step count can sit on either side.
- **G3 — variance floor:** spatial CV = std/|mean| of the pattern stays well above machine-ε relative to Darwin's own CV, so a "converged r" is not correlating round-off.

If the iron rows show a genuine limit cycle at a cell (no fixed point), mark that cell **UNDEFINED** rather than reporting a steady-state FIM there.

### 3.2 Stage 2 — Steady-state sensitivity via the implicit function theorem

At the fixed point, differentiating f(x*, θ) = 0 w.r.t. θ (implicit function theorem; standard in adjoint / parametric-sensitivity literature, Dickinson & Gelinas 1976; Saltelli et al. 2008):

> **(∂f/∂x) · (dx*/dθ) + ∂f/∂θ = 0  ⟹  dx*/dθ = −(∂f/∂x)⁻¹ (∂f/∂θ)**

- ∂f/∂x = A is the 15×15 state Jacobian (its eigenvalues are the relaxation modes; the slow mode is A's eigenvalue nearest 0). 
- ∂f/∂θ is the 15×6 parameter-of-tendency matrix.

Both come cleanly from autograd on the **single-step function at x*** (`torch.func.jacrev` / `torch.autograd.functional.jacobian`) — **no 200-step unroll/backprop is needed once x* is found**, which is both cheaper and free of the transient artifact. The observable sensitivity is then

> **J_c = (∂g/∂x) · (dx*/dθ)**, shape [N_obs × 6].

**Observable map g (must be exactly what the loss reads; state indices from the box):**

| Observable | State index | Real anchor / noise source |
|---|---|---|
| surface DFe (FeT) | `I_DFE_1 = 0` | GEOTRACES `Fe_*_err` 1σ (`geotraces_loader.py:36`) |
| subsurface DFe₂ | `I_DFE_2 = 10` | GEOTRACES subsurface (breaks iron-pair degeneracy) |
| PIC | `I_PIC_1 = 7` | MODIS PIC climatology spread (`modis_pic_loader.py`) |
| POC | `I_POC_1 = 6` | Darwin field representativeness variance |
| realized PIC:POC ratio | derived = PIC/POC | identifies `R_PICPOC` orthogonally to the iron pair |
| DIC, ALK | `I_DIC_1 = 8`, `I_ALK_1 = 9` | GLODAP / field variance |
| bSi (diatom) | via `diagnostic_bsi_steady(state[I_DIATOM=1], diatomgraz)` (`silica.py`) | GEOTRACES bSi (pins `diatomgraz`) |
| 5 Chl/biomass channels | `I_DIATOM…I_PROHL` (1–5) | **biology — inflate Σ; box is a surrogate** |

For z-scored **pattern** channels, fold the z-score (subtract spatial mean, divide by spatial std) into ∂g/∂x so J and the residual the loss sees are unit-consistent.

**Stage 2b — Gramian/Lyapunov cross-check (justification, not primary).** The dynamic counterpart of the IFT sensitivity is the variational ODE ds/dt = A s + ∂f/∂θ; the observability Gramian W_o solving the Lyapunov equation **AᵀW_o + W_o A + CᵀC = 0** (C = ∂g/∂x) has near-null directions = unobservable state combinations. The finite-time Gramian → steady Gramian only after ~7τ — this is the formal justification for the ≥1600-step requirement (Kailath 1980; Stigter & Molenaar 2015). Use it to diagnose whether the growth pair is W_o-null (structurally unobservable) vs merely weakly excited.

### 3.3 Stage 3 — Fisher information with an explicit noise model

> **FIM_c = J_cᵀ Σ_c⁻¹ J_c** (6×6 per cell)

This is the Gaussian-likelihood Fisher information and the Gauss-Newton / JᵀJ approximation to the least-squares loss Hessian (Kay, *Fundamentals of Statistical Signal Processing* vol. 1, ch. 3). Σ_c is the per-cell observation-noise covariance and is **load-bearing, not cosmetic** — each runner loss weight w_k is implicitly 1/σ_k². **Report two versions:**

- **Σ_v1 (loss-faithful):** Σ⁻¹ = diag of the runner's actual weights (`GEOTRACES_W`, `GEOTRACES_SUB_W`, `PIC_ABS_W`, `POC_ABS_W`, `ALK_ABS_W`, `RATIO_W`, per-AOI `AOI_W`). Explains the *deployed* recovery.
- **Σ_v2 (data-faithful):** real observation error (GEOTRACES `_err`, MODIS spread, GLODAP) **plus an additive model-discrepancy covariance Σ_model inflating the biology channels** by (1 − r_box-vs-Darwin) per channel (from `box_vs_darwin_fidelity.py`). Without Σ_model the FIM claims spurious confidence where the box cannot reproduce Darwin even at θ₀.

Where Σ_v1 and Σ_v2 disagree localizes where the **hand-tuned weighting — not the data — is doing the identifying** (a reviewer-grade honesty check). The growth pair has **no real observable** ⇒ infinite variance / zero Fisher weight in Σ_v2 by construction — exactly the flat-everywhere signature H3 predicts.

### 3.4 Stage 4 — Marginal identifiability = diag(FIM⁻¹), NOT 1/diag(FIM)

This is the single most important methodological point. `diag(FIM)_jj` measures sensitivity to θ_j with all *other* params held fixed at truth — it ignores trade-offs and **overstates** identifiability. The honest, other-params-unknown quantity is the Cramér-Rao bound:

> **Var(θ_j) ≥ (FIM⁻¹)_jj** ; marginal standard error = √((FIM⁻¹)_jj).

The gap between 1/FIM_jj and (FIM⁻¹)_jj **is** the sloppiness/trade-off. If `alpfe` and `scav_rat` are each individually sensitive but anti-correlated (the surface iron-budget degeneracy: dust source vs scavenging sink), the FIM is near-singular in that 2×2 block and **both** marginal CRBs blow up even though each diagonal looks healthy — exactly the failure the project already hit. The map will show `scav_rat` becoming marginally identifiable only where the DFe₂ channel conditions that block (H4).

**Stage 4b — structural vs practical (sloppiness; profile likelihood).** Eigendecompose FIM_c = Σ_i λ_i v_i v_iᵀ. The log-uniform eigenvalue spectrum is the sloppy-model signature (Brown & Sethna 2003; Gutenkunst et al. 2007; Transtrum et al. 2015). Stiff (large λ) = tightly constrained combos; sloppy (tiny λ) = unconstrained. **Structural** non-identifiability = a truly zero eigenvalue / exactly-flat profile-likelihood direction (expected for the growth pair everywhere). **Practical** non-identifiability = small-but-nonzero λ. The FIM (a local quadratic) cannot by itself separate these — the gold-standard confirmation at selected cells is the **profile likelihood** (Raue et al. 2009): fix θ_j on a grid, re-optimize the other 5 through the box, trace χ²(θ_j); flat = structural, finite-well = practical, well-hits-bound = bound-limited. *Caveat: sloppiness ≠ non-identifiability (Apgar/Transtrum 2014) — always report eigenvectors/combinations, confirm edge cases with profile likelihood, never label from FIM diagonals alone.*

### 3.5 Stage 5 — Collapse to scalar fields + parameter coordinates

Work in **bound-normalized / log parameter coordinates** (params span scav_rat ~6e-7 s⁻¹ to Smallgrow ~0.66 d⁻¹; the recovery already uses bounded_params). Use the chain rule dθ_phys = (hi−lo)·sigmoid′(·)·dθ_unc with `PARAM_BOUNDS` from the registry, so the CRB is dimensionless and comparable across the six and the eigenvalue spectrum is a meaningful sloppiness plot.

**Per parameter j, emit three scalar fields:**
1. **Marginal identifiability** I_j(c) = −log₁₀(relative CRB) = −log₁₀(√((FIM⁻¹)_jj)/|θ₀,j|) — higher = more identifiable.
2. **Trade-off / inflation factor** ρ_j(c) = √((FIM⁻¹)_jj · FIM_jj) — ratio of marginal to conditional error; ρ = 1 no trade-off, ρ ≫ 1 sloppy/degenerate (the `alpfe`↔`scav_rat` tell).
3. **Binary identifiable-mask** at a threshold (the "place an AOI here" decision).

**Plus two joint fields:** (4) smallest-FIM-eigenvalue field (worst unconstrained direction), (5) participating-parameter field (which params load on the sloppiest eigenvector) — shows *which pair* is degenerate *where*.

**Conditioning:** FIM is *deliberately* near-singular in the degenerate blocks; never naive-invert. Use the eigendecomposition with an eigenvalue floor, or a Bayesian/regularized CRB (FIM + prior precision)⁻¹ with the physical bound width as prior — finite, interpretable marginal errors, the honest statement of "identifiable given a physically-bounded prior."

---

## 4. Implementation plan (phased)

The build lifts the **existing** `scripts/box_vs_darwin_fidelity.py` (which already runs `carroll6_5pft_2layer_integrate` on a full 2D [H,W] AOI field at `CARROLL_VALUES`, building state0 from the Darwin cache) from per-AOI → global and from 200 → ≥1600 steps, with autograd of d(observable)/d(θ) added. **No new physics, no runner dependency for J.**

> **Scoping gaps confirmed against this branch (`refactor-param-registry`):**
> - `scripts/box_linearization.py` **does not exist on any branch** (verified `git ls-files`). The brief's "reuse box_linearization.py" instruction is not actionable — the FIM pseudo-inverse / eigenvalue-floor handling must be built fresh inside `identifiability_map.py`.
> - `scripts/identifiability_sloppiness.py` is **not on this branch** (it lives on the spine-d worktree, untracked in the snapshot). The reward-hacking-safe import pattern (`NB23_N_EPOCHS=0`, no-gating) and the eigh pattern must be re-implemented or cherry-picked, not assumed present.
> - Plan accordingly; do not budget as if either scaffold exists here.

**Phase 0 — Convergence calibration (do FIRST; gates everything, ~0.5 day).** Copy the state0-from-Darwin recipe from `box_vs_darwin_fidelity.py` for 3–5 representative cells (HNLC eqpac, dust-fed gyre, subpolar bloom, Southern Ocean, oligotrophic). Compute per-cell J = d(observables)/d(θ) at `CARROLL_VALUES` via `torch.func.jacrev` at n_steps ∈ {200, 400, 800, 1600, 3200}. Plot |J| and the iron-vs-Darwin sign vs n_steps; pick `N_STEPS_CONV` as the smallest count where J changes < 1–2% to 3200. **Correctness gate: reproduce the eqpac iron sign flip (−0.96@200 → +0.81@3200). If it does not reproduce, STOP and reconcile before building the global map.** Expected `N_STEPS_CONV` ≈ 1600.

**Phase 1 — Global field staging (~0.5–1 day).** Build a global Darwin target+forcing cache by running the IC-cache / bundle path with AOI bounds = whole globe (lat −90..90, lon −180..180) so `bin_to_1deg_grid` (`llc270_loader.py:353`) produces a [180,360] field. Stage state0 (FeT/POC/PIC/DIC/ALK from Darwin), forcing (SST/SSS/wind/pco2_atm), and the global ocean mask (~41k–46k ocean cells). Output a single `global_targets.pt`. Confirm against `D:\ecco_darwin_v5` (DARWIN_ROOT).

**Phase 2 — Per-cell Jacobian engine (~1–2 days).** `compute_J(theta[6], state0[15,N], forcing) → J[N_obs, 6, N]` integrating to `N_STEPS_CONV`. Use `torch.func.vmap(jacrev(f, argnums=θ), in_dims=cell-axis)` where f maps θ → observable-vector at one cell (reverse-mode gives all 6 columns from one graph). **Memory:** a global [15, 46k]×1600-step autograd graph is ~26 GB — **tile** into chunks of ~5–10k cells (fresh graph per tile; embarrassingly parallel). Fits H200 (140 GB); the full sweep is an H200 / NU Explorer job, Phase 0 + tiled tests run on the 5090. Use the compiled per-step where available. **Flag and mask cells whose trajectory touches the `clamp(min=0.0)` non-negativity floor (`carroll6_5pft_2layer.py:558`)** — the clamp is non-differentiable at 0 and corrupts J there.

**Phase 3 — FIM assembly + Σ (~1 day).** Per cell FIM = Σ_obs J_obsᵀ Σ_obs⁻¹ J_obs. Build both Σ_v1 (loss weights) and Σ_v2 (real error + Σ_model inflation). Growth-rate-direct entries → +∞ variance. Handle rank-deficient/conserved modes via `torch.linalg.eigh` + eigenvalue floor (or Bayesian CRB), **never** naive inverse. Report raw eigenspectrum (sloppiness span) and the floored pseudo-inverse.

**Phase 4 — Per-parameter scalar maps + region ranking (~0.5 day).** Emit the six I_j, ρ_j, mask fields + two joint fields as [180,360]. Rank cells per parameter, aggregate to named regions / lat-lon boxes, emit top-K per parameter. **Sanity gates that must hold or the map is wrong:** (a) growth pair flat/low everywhere; (b) iron pair peaks where GEOTRACES iron + dust gradients are strong; (c) `R_PICPOC` peaks in coccolithophore/calcite regions.

**Phase 5 — Artifacts + packaging (~0.5 day).** `scripts/identifiability_map.py` with argparse (`--n-steps` default `N_STEPS_CONV`, `--tile-cells`, `--theta {carroll|json}`, `--sigma-source {loss|data}`, `--out`). Outputs: per-param GeoTIFF (EPSG:4326, 1°) + PNG (matplotlib, coastlines, log-precision colormap); `docs/findings/identifiability_map_regions.json` ({param: {best_regions:[{name,bbox,mean_precision,n_cells}], field_stats}}); a provenance block (θ, n_steps, Σ sources, Phase-0 convergence result). Add a `tests/` smoke test: a 3-cell map at n_steps=50 runs end-to-end and growth-pair precision < iron-pair precision in an iron-rich cell.

---

## 5. Validation plan

**V1 — Falsification against the hand-ablation (H2), as rank-recovery.** Per hand-picked AOI, aggregate the per-cell marginal identifiability to a per-AOI score per parameter. PASS: argmax/top-rank per AOI matches the ablation carriers (eqpac→{alpfe,diatomgraz}, SO→scav_rat, natl→{Biggrow,R_PICPOC}) *in rank*, with Spearman ρ ≥ 0.6 across the 18 (param,AOI) cells (pre-registered). **Treat `scav_rat` and `R_PICPOC` specially:** both are contrast/coupling-driven (`scav_rat` needs surface↔subsurface DFe; `R_PICPOC` is per-AOI-unidentified, only joint-straddle recoverable per the ALK-anchor finding), so a purely-local map is *expected* to under-rank them — build that into the criterion rather than calling it a failure. The ablation is a **prior to corroborate, not an oracle** (it is n=200 seeds, coupling-laden; `stage1_per_aoi_gating_2aoi.md` shows severing cross-AOI coupling drops mean cal 2.95→1.65).

**V2 — Convergence check (H1).** Compute the map at 200 and at `N_STEPS_CONV`; show the eqpac iron cells flip sign, demonstrating that a 200-step map mis-attributes iron identifiability. Publish the fraction of cells failing each of G1/G2/G3 as a map-quality figure. Keep only cells whose per-cell argmax is stable between `N_STEPS_CONV` and 2×.

**V3 — Growth-pair sanity (H3), automated assertion.** Hard check: across all cells/AOIs the {Smallgrow, Biggrow} rows have total influence below threshold and are never the per-cell argmax under a real-data loss. If any region flags growth as identifiable, dump that cell's 6×6 normalized Hessian and find the degeneracy partner before trusting the map. Cross-check against the existing per-AOI FIM verdicts (growth pair pinned far from Carroll at low curvature).

**V4 — Profile-likelihood spot-check (locality of the FIM verdict).** At one representative cell per regime, run the full profile likelihood for each of the 6 params (Raue et al. 2009). Confirm the FIM/CRB ranking matches the profile-well curvature, growth-pair profiles are flat (structural), and `R_PICPOC`'s profile is a finite well only in the coccolithophore-zone cell.

**V5 — Cross-tool agreement.** Run the global-θ profile-likelihood diagnostic (`identifiability_sloppiness.py`, in `--loss realiron/realbsi/realpic`) on the 3 AOIs and confirm its verdicts agree with the new per-cell map aggregated over the same footprints. Two routes to the same question; agreement is the strongest non-artifact evidence.

---

## 6. Acceptance criteria (specific, measurable)

1. `scripts/identifiability_map.py` exists, runs end-to-end on the global 1° field at `N_STEPS_CONV` ≥ 1600, tiled, and emits 6×{I_j, ρ_j, mask} + 2 joint fields as GeoTIFF+PNG, plus `identifiability_map_regions.json` with a provenance block.
2. **Phase 0 correctness gate passes:** the eqpac iron sign flip (≈ −0.96@200 → +0.81@3200) is reproduced.
3. **Convergence verified per cell:** G1/G2/G3 fractions reported; cells failing any gate (or showing a limit cycle in the iron rows) are masked/UNDEFINED, not mapped.
4. **H2 passes:** Spearman ρ ≥ 0.6 between per-AOI parameter-stiffness ranking and the v3.1.1 ablation cal-grade ranking; any sub-threshold (param,AOI) cell has a written diagnosis (coupling/contrast, not a silent fail).
5. **H3 passes:** growth-pair marginal identifiability below threshold in 100% of cells under Σ_v2; growth params are the argmax in 0 cells. Automated assertion in the smoke test.
6. **Two-Σ honesty figure delivered:** Σ_v1 vs Σ_v2 difference map showing where weighting (not data) identifies, with Σ-sensitivity pass (0.5×/2× Σ) confirming region rankings are robust.
7. **Reward-hacking guard asserted in code:** the θ tensor is constant across cells (broadcast); no recovery metric, gating mask, or DINN-learned param enters the map pipeline (code-level assert).
8. **V4 profile-likelihood spot-checks** at ≥4 regime cells corroborate the FIM ranking and confirm flat growth-pair profiles.

---

## 7. Risks + honesty guards

**Diagnostic, not a recovery component.** Computed at fixed `CARROLL_VALUES` (or a real-data optimum) over a single global θ, broadcast across cells, with **no gating, no recovery loss, no seed-tuning** in the loop (mirror the `NB23_N_EPOCHS=0`, no-gating import discipline). Code-assert θ is constant across cells so the map cannot encode the DINN's regional choices. Making the recovery NN select regions from this map would reward-hack and break the per-cell structural argument.

**Transient artifact (highest risk).** A 200-step map inverts the eqpac iron sign and is scientifically wrong. Mitigation: IFT on the verified fixed point at ≥1600 steps with per-cell convergence + Jacobian-stability gating; never trust a fixed step count globally.

**Convergence may not be a solved "run longer" problem.** The box shows a slow FeT *oscillation* deep in the integration (not monotone relaxation); there may be no single step count at which every cell's iron sensitivity is stable. If the iron rows are a genuine limit cycle at a cell, the steady-state FIM is ill-defined there — mark UNDEFINED. The forward-Euler scheme (dt=0.25, stability margin thin at eig 0.9957) may itself be the source of the slow mode; state that all convergence claims are conditional on this integrator.

**Surrogate scope (state it in every artifact).** The box is a 0-D emulator of Darwin, not Darwin; chemistry vs biology fidelity differ (Chl rows are biomass-not-chlorophyll; DIC/ALK/FeT are IC-confounded). A FIM that ignores model error claims confident identifiability where the box structurally cannot match Darwin. Mitigation: Σ_model inflation of biology channels; report the data-faithful Σ_v2 alongside Σ_v1. **Title every figure "identifiability of the BOX SURROGATE at steady state"** and carry the box→Darwin fidelity caveat (noting the published fidelity r's were 200-step transients). "Identifiable in the box" is necessary but not sufficient for "recoverable from real data" — cross every positive verdict against the real-anchor inventory (GEOTRACES iron/bSi, Daniels CP:PP / MODIS PIC).

**FIM is a local Gaussian approximation.** It captures only quadratic curvature at θ₀; it cannot represent bounded/one-sided regions, multimodality, or structural-vs-practical. Bounds make this worse near edges (`R_PICPOC`, `scav_rat` sit near bound edges). Mitigation: profile likelihood at representative cells; report when the marginal CRB exceeds the bound width (then bound-limited, not data-identified).

**FIM conditioning.** The point is that FIM is near-singular in degenerate blocks. Naive inversion explodes. Mitigation: pseudo-inverse with eigenvalue floor / Bayesian CRB; report directly from the eigendecomposition.

**Σ = loss-weights is a choice, not ground truth.** The runner weights were hand-tuned to force 6/6; adopting them makes the map explain the deployed recovery but inherits its biases. Always pair with Σ_v2.

**Per-cell 0-D scope.** The box is 0-D per cell with no horizontal coupling (DINN is 1×1 conv only), so the per-cell FIM is independent across cells — legitimate for *this* model, but it omits that real-world identifiability could borrow strength across neighbors. State this scope limit so the map is not over-read as a full spatial-field identifiability.

---

## 8. Deliverables and how it feeds the manuscript + issue tracker

**Deliverables.**
- `scripts/identifiability_map.py` (standalone diagnostic; argparse; tiled; GeoTIFF + PNG output).
- `global_targets.pt` (global Darwin state0 + forcing + mask cache).
- `docs/findings/identifiability_map_regions.json` (per-parameter best-region rankings + provenance).
- Six per-parameter global identifiability figures + the two joint sloppiness/participation figures + the Σ_v1-vs-Σ_v2 honesty figure + the 200-vs-1600 convergence falsification panel.
- A short findings note (per repo convention: returned in PR/issue text, not a standalone hype .md) recording `N_STEPS_CONV`, the H2 Spearman ρ, the H3 assertion result, and the profile-likelihood spot-checks.

**Manuscript (surrogate-to-model identifiability study).** This is the central figure-set: it replaces "we hand-picked three AOIs" with an information-theoretic, falsifiable "where on Earth is each Carroll-6 parameter identifiable in the box, at steady state." It positions the work as the per-grid-cell, parameter-space forward-Fisher analog of domain-localized BGC parameter estimation (Mamnun et al. 2025, *JGR Oceans*, per-column estimation), with the differentiator that it is a no-assimilation, no-reward-hackable diagnostic; it stratifies identifiability against per-cell environment (SST/MLD/wind/lat) the way Mamnun et al. 2023 (Sobol, MLD-dependent) and Beck et al. 2017 (collinearity index) motivate; it turns the project's own slow-mode finding (eig 0.9957) into a methods-section strength (transient-FIM-as-artifact panel) that pre-empts the obvious referee attack; and it states the growth pair as the honest negative control (flat everywhere = the method is not hallucinating signal).

**Issue tracker (`2imi9/ECCO-DarwinDiff`, spines A–D under epic #124).** File a new issue under the index epic capturing this scope (acceptance criteria from §6, the two confirmed scaffolding gaps from §4, and the H200-tiling/NU-Explorer dependency), cross-referencing the convergence finding and the per-AOI gating ablation. The map is the principled replacement for the hand-picked-AOI practice that several open spine items assume; link it from those.

---

### Cited prior art (inline above)
Raue et al. 2009, *Bioinformatics* 25:1923 (profile likelihood, structural vs practical) · Brown & Sethna 2003, *PRE* 68:021904; Gutenkunst et al. 2007, *PLoS Comput Biol* 3:e189; Transtrum et al. 2015, *J Chem Phys* 143:010901 (sloppiness / FIM spectrum) · Apgar/Transtrum 2014, arXiv:1403.1417 (sloppiness ≠ non-identifiability) · Kay, *Fundamentals of Statistical Signal Processing* vol. 1 ch. 3 (CRB, FIM=JᵀΣ⁻¹J) · Dickinson & Gelinas 1976, *JCP* 21:123; Saltelli et al. 2008 (IFT steady-state sensitivity) · Kailath, *Linear Systems* 1980 ch. 6; Stigter & Molenaar 2015, *Automatica* 58:118 (observability Gramian / Lyapunov) · Constantine et al. 2014, *SIAM J Sci Comput* 36:A1500 (active subspaces) · Palmer et al. 1998, *JAS* 55:633 (targeted-observation / adjoint-sensitivity design) · Mamnun et al. 2025, *JGR Oceans* 130:e2025JC022752 (domain-localized per-column BGC parameter estimation) · Mamnun et al. 2023, *SESMO* 5:18613 (1-D BGC Sobol, MLD-dependent) · Beck et al. 2017, *Ecol Modelling* 363:17 (collinearity index, BGC identifiability) · Atkinson, Donev & Tobias 2007 (D-optimal design over the FIM).

**In-repo grounding:** `src/darwindiff/carroll6.py` (PARAMS registry; values/bounds verified this branch) · `src/darwindiff/carroll6_5pft_2layer.py` (`carroll6_5pft_2layer_step:306`, `_integrate:561`, state indices `I_DFE_1=0…I_ALK_2=14`, `clamp(min=0.0):558`) · `scripts/box_vs_darwin_fidelity.py` (global-field template; `N_STEPS=200`, `DT=0.25`) · `src/darwindiff/geotraces_loader.py:36` (iron `_err` Σ) · `src/darwindiff/modis_pic_loader.py` (PIC Σ) · `src/darwindiff/silica.py` (`diagnostic_bsi_steady`) · `src/darwindiff/llc270_loader.py:353` (`bin_to_1deg_grid`) · `docs/findings/stage1_per_aoi_gating_2aoi.md`, `docs/findings/alk_anchor_rpicpoc_mutex.md` (coupling/contrast evidence).

---

**Document location for the engineer:** intended path `docs/findings/2026-06-27_identifiability_map_goal.md` (not yet written to disk — this is the synthesis return). Scaffolding caveat for whoever picks it up: on branch `2imi9/refactor-param-registry`, neither `box_linearization.py` nor `identifiability_sloppiness.py` is present; budget Phase 2–3 to build the FIM eigenvalue-floor + reward-hacking-safe import from scratch (or cherry-pick `identifiability_sloppiness.py` from the spine-d worktree first).