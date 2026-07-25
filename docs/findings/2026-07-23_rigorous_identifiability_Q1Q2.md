# Rigorous identifiability re-analysis (Q1 rank/null + Q2 iron correlation) — 2026-07-23

Prompted by a reviewer critique that my earlier "observable frontier" and "iron pair comparably
constrained (CRLB 68 vs 78)" claims used the wrong statistics. Both are now redone with the correct
objects: the **rank and null direction of the whitened 4-observable Fisher sub-block** (Q1) and the
**posterior correlation + dimensionless relative uncertainty** of the iron pair (Q2). Tooling:
`scripts/identifiability_sloppiness.py` (`--mode peraoi` for the 4-obs sub-block; `--mode fisher_gn` for
the iron block), evaluated at Carroll. **These are the surrogate's Fisher — see the surrogate-Jacobian
caveat (Q3, separate note).** The empirical Fisher's eigenVECTORS/rank are robust; its magnitudes are
residual-weighted (read structure, not magnitude).

## Q1 — the 4-observable Fisher is full rank in the anchored basins (information is present; the recovery frontier is still structural)

> **⚠️ PARTLY SUPERSEDED (same night — `docs/findings/2026-07-23_overnight_recovery_sweep_groupA.md`,
> job 192298):** the full-rank result below is about *information*, not recoverability. The 3-of-4
> **recovery** frontier is real and STRUCTURAL — no single config holds all four observables, and 2×
> optimization does not bridge it (full loss + MLD at 4000 epochs still gives diatomgraz 0/10). Read
> "design/optimizer artifact" below as "config-dependent operating point", **not** as "no frontier".

The 4-observable sub-block `{alpfe, scav_rat, diatomgraz, R_PICPOC}` of the per-AOI Fisher, at Carroll:

| AOI | rank | eigenvalues (low→high) | null / softest direction |
|---|---|---|---|
| **eqpac** | **4/4** | 7.1e-4, 8.3e-3, 2.2e-2, 3.6e-1 | alpfe −0.93 (softest, but nonzero) |
| **natlsubpolar** | **4/4** | 9.8e-4, 1.1e-2, 2.6e-2, 1.2e-1 | alpfe +0.93 (softest, but nonzero) |
| **southernoceanpac** | **2/4** | 0.0, 8.1e-7, 1.2e-2, 3.4e-2 | R_PICPOC +1.00 (exact null) + one more |

**Reading (this replaces the "frontier" claim):**
1. In the two anchored basins (eqpac, natl) the four observables are **jointly full rank (4/4)** at
   Carroll — all four are *locally* identifiable. So there is **no null combination forcing a
   scav_rat↔diatomgraz trade-off**. The config-dependent "swap" I saw between the flagship and the MLD
   run is therefore a **design / regularization / optimizer artifact** (the configs differ in the
   pattern/PINN/chl loss terms and the MLD input), **not** a fundamental identifiability frontier —
   exactly as the critique predicted (Fisher information is monotone under added independent obs).
2. The softest of the four in eqpac/natl is **alpfe** (eigenvector ≈0.93 on alpfe) — consistent with the
   manuscript's "alpfe is weight-conditional" caveat; it is the least-curved but still nonzero direction.
3. The **Southern Ocean is rank 2/4**: R_PICPOC is an exact null (Daniels has no SO coverage) plus one
   more near-null direction. So the *joint 3-AOI* limit is **basin observational coverage**, not a
   parameter degeneracy. This localizes the honest structural limit precisely.

**Correct statement for the paper:** "Rank-k identifies k *combinations*." In eqpac/natl the 4-observable
Fisher is full rank (no degenerate combination among the observables); the Southern Ocean drops to rank 2
because it lacks a calcite anchor. The recoverable-triple *swap* across configurations reflects estimator
and regularization choices on a full-rank problem — the *information* is there, but the *recovery* frontier
is still structural (job 192298), so this is an identifiable-≠-recoverable distinction, not the absence of
a frontier. The gold-standard confirmation (joint 4-parameter profile likelihood) is the follow-up.

## Q2 — the iron pair: strong but INCOMPLETE degeneracy

> **⚠️ SUPERSEDED (2026-07-23, job 187666 + expert review) — read
> `docs/research_notes/2026-07-23_expert_review_corrections.md` §A.** The −0.77 below is the full-6
> *marginal* (coupling-inflated). The 2×2 sloppy eigenvector is alpfe-dominated (+0.98, −0.20) with a
> *weak* conditional correlation **−0.155** (cond 2.2): with **surf+subsurface** GEOTRACES the iron pair is
> **largely separated, not strongly degenerate**. The strong degeneracy (conditional +0.999) is
> **surface-only**. Also: it is a **ratio S/k**, not a product. Do not cite the "strong −0.77 degeneracy."

Gauss-Newton Fisher of the real GEOTRACES iron-concentration residual, at Carroll, `{alpfe, scav_rat}`:
- **Posterior correlation(alpfe, scav_rat) = −0.773** (full-6 covariance) — a strong source–sink
  anti-correlation (more dust source ↔ more scavenging sink to hold concentration), but **not** a rigid
  1-D ridge (|ρ| < 0.9).
- 2×2 iron Fisher eigenvalues 0.248 / 0.552, **condition number 2.2** — within the iron plane the two
  directions have comparable curvature (not catastrophically ill-conditioned).
- Dimensionless relative std: **alpfe 8.3, scav_rat 8.8** — under iron concentration *alone*, both are
  individually poorly constrained (posterior std ≈ 8× the value); the real anchors + per-cell structure
  are what tighten them in the full problem.

**Reading (this replaces "concentration contains information only about the combination"):** iron
concentration **strongly constrains a source–sink combination and weakly separates its terms** under the
present sampling — ρ = −0.77, not ±1. This is the Frants-et-al. compensating-family result, quantified for
ECCO-Darwin. alpfe (surface source) and scav_rat (particle-dependent removal) *do* have distinct
signatures in principle; the present sampling separates them only weakly. **Not** "neither is pinned."

## What changed vs my earlier claims
- ⚠️ "observable frontier / 3-of-4 parameters" → the *information* is full-rank 4/4 in anchored basins
  (SO is rank-2 by coverage), but the **recovery** frontier is real and STRUCTURAL: no single config
  holds all four observables, and 2× optimization does not bridge it (job 192298 — full loss + MLD at
  4000 epochs still gives diatomgraz 0/10). scav_rat needs the Darwin-pattern term, diatomgraz needs
  MLD, and they conflict. Identifiable ≠ recoverable.
- ❌ "CRLB 68≈78 → comparably constrained, neither pinned" → ✅ **ρ = −0.77 (strong, incomplete
  degeneracy); both individually wide under iron alone; concentration constrains the combination and
  weakly separates the terms.**

Caveats carried forward: (i) empirical-Fisher magnitudes are approximate (structure is robust); (ii) this
is the SURROGATE's Fisher — transfer to ECCO-Darwin needs the Jacobian validation (Q3); (iii) local, at
Carroll — global identifiability across depth/season/regime needs the multi-point analysis.
