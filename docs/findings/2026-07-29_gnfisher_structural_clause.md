# Structural identifiability clause on the REAL loss — GN-Fisher, job 233265

Replaces the **synthetic self-twin** relative-information table (evidence log §H3), whose own scope
caveat says hypothesis generator, not result. This one is computed on the real observational
residuals at Carroll's published values.

Artifacts: `/scratch/qi_zim_neu/identif/contract_gnfisher_{realiron,realbsi}.json`
Log: `/scratch/qi_zim_neu/identif/CONTRACT_233265.log` · tree `~/emulator_poc_pw` · exit 0, `fail=0`

---

## 1. Method, and why it is valid at Carroll

`F_GN = JᵀJ` with `J = ∂ρ/∂θ` and `ρ` the **scaled residual vector** built so `‖ρ‖² == loss`. Two
properties matter:

- **PSD by construction**, so it gives valid curvature *at Carroll*, where the loss Hessian is a
  known indefinite saddle. Confirmed both runs: `PSD: True`.
- **Single evaluation** (12 finite-difference residual evals for `J`), so there is **no profile
  re-optimisation grid** and therefore none of the convergence-guard failure mode that invalidated
  9 of 13 runs on 2026-07-19.

The script refuses to emit an artifact unless the residual vector reconstructs the loss. Both passed:

| loss | ‖ρ‖² | loss_vec | rel | residuals |
|---|---|---|---|---|
| realiron | 2.27710 | 2.27710 | **1.05e-07** | 5726 |
| realbsi | 1.73067 | 1.73067 | **1.38e-07** | 1567 |

`--opt-steps 0`, so θ\* **is** Carroll exactly (rel offset 0.00 on all six). This is curvature at the
published optimum, which is the right object for a *structural* statement.

---

## 2. Each real observable constrains exactly what it should, and is null elsewhere

Per-parameter Fisher information on the diagonal, dimensionless. **High = constrained.**

| param | realiron (GEOTRACES dissolved Fe) | realbsi (GEOTRACES biogenic Si) |
|---|---|---|
| alpfe | **2.60e-01** | 7.16e-02 |
| scav_rat | **5.40e-01** | 4.60e-02 |
| Smallgrow | 1.49e-01 | 3.39e-02 |
| Biggrow | 2.36e-02 | 5.56e-03 |
| diatomgraz | 6.88e-04 | **8.16e-01** |
| **R_PICPOC** | **0.00e+00** | **0.00e+00** |

CRLB (relative-variance bound, **low = better constrained**; comparable *within* a column only,
since the two columns are different losses):

| param | realiron | realbsi |
|---|---|---|
| **alpfe** | **68.5** | 135,267 |
| **scav_rat** | **78.2** | 602,837 |
| Smallgrow | 39,589 | 493,161 |
| Biggrow | 301,648 | 944,607 |
| **diatomgraz** | 72,068 | **3,530** |
| R_PICPOC | 1,422,765 | 1,028,358 |

Read as a contract this is about as clean as it gets:

- **Iron data constrains the iron pair.** `alpfe` 68.5 and `scav_rat` 78.2 are roughly **500x**
  tighter than the next parameter under the same loss.
- **Silica data constrains `diatomgraz`.** 3,530 is roughly **38x** tighter than the next parameter
  under that loss, and `diatomgraz`'s Fisher information is the largest single entry in either
  column.
- **`R_PICPOC` is the exact null direction of BOTH.** Fisher information is not small, it is
  **identically 0.00e+00**. Neither dissolved iron nor biogenic silica carries any information about
  the rain ratio, which is why it needs its own real calcite anchor and why the anchor-off control
  collapses to chance. This is the formal statement behind the 50/50-versus-6/50 contrast.
- **The growth pair is the sloppiest direction under silica.** Sloppiest eigenvector under `realbsi`
  is `Biggrow −0.93, Smallgrow +0.36`; stiffest is `diatomgraz −0.92`. Consistent with the growth
  pair being information-starved rather than degenerate.

---

## 3. It independently reproduces the corrected iron-degeneracy framing

This is the part worth flagging, because it confirms a claim we had already *corrected once* and
which supersedes an earlier headline.

| quantity | STATUS.md (job 188077) | **this run, real loss** |
|---|---|---|
| iron pair 2x2 condition, surf+sub | 2.2 | **2.224** |
| conditional corr(alpfe, scav_rat) | −0.155 | **−0.155** |
| ratio-like (co-varying) degeneracy | broken | **False** |

So with real surface **plus subsurface** GEOTRACES the pair really is well-conditioned, and
`scav_rat`'s poor recovery is an optimisation and coverage limit, not a hard information wall. The
retracted "strong −0.77 degeneracy" was the coupling-inflated full-6 marginal.

**And the counterfactual is measured in the same run.** Under `realbsi`, which carries no iron
information at all, the same pair reads condition **9340.1**, conditional corr **+0.9998**, and
`ratio_like_degeneracy: True` (co-varying, the S/k ratio direction). So the difference between
"well-conditioned" and "maximally degenerate" is entirely *which observable you feed it*, measured
end to end in a single job. That is a cleaner demonstration than either number alone.

---

## 4. Caveats that must travel with these numbers

- **`realbsi`'s CRLB is a curvature statement, not a strict variance bound.**
  `‖H − 2F‖/‖2F‖ = 5.21`, which the script itself flags as large, meaning the data are **not**
  well fit at Carroll under the silica-only loss. GN equals the true Hessian only when residuals are
  near zero. `realiron` is far better behaved at **0.93** but is not zero either. Quote the
  *ordering* and the *null directions* confidently; do not quote the CRLB magnitudes as posterior
  standard deviations.
- **Sloppiness is ~5.5 to 5.7 decades in both.** These are sloppy problems in the Gutenkunst sense
  regardless of which observable is used. Well-conditioned *in the iron 2x2* does not mean
  well-conditioned overall.
- **This is curvature at Carroll, not at the fitted optimum.** That is deliberate (it is a statement
  about the published values) but it is a different question from "how well did our fit converge".
- **The clause is incomplete.** `R_PICPOC` reads 0.00e+00 under both losses because neither is its
  observable. Its real anchor is Daniels CP:PP, which is **not exposed as a standalone residual
  loss**, so `R_PICPOC` currently has no positive structural clause of its own. `--loss realpic` is
  MODIS-Aqua PIC, the shelved satellite path, and is deliberately not substituted. Adding a
  `realdaniels` residual is guarded by the same `‖ρ‖² == loss` self-check, so a scaling error would
  fail the job rather than emit a wrong number.
- **`Smallgrow` and `Biggrow` have no real observable at all.** That absence is the finding, not a
  gap to be filled by proxy.

---

## 5. What this replaces

The synthetic self-twin table (evidence log §H3) gave relative information `diatomgraz` 1.000,
`alpfe` 0.140, `R_PICPOC` 0.099, `Biggrow` 0.055, `Smallgrow` 0.053, `scav_rat` 0.026, on a 240-cell
synthetic AOI. Two of its orderings do **not** survive contact with the real loss:

- it ranked `scav_rat` **last** (0.026); under its own real observable `scav_rat` has the **highest**
  Fisher information of all six (5.40e-01).
- it gave `R_PICPOC` a nonzero 0.099; on real data it is **identically zero** under both available
  observables.

The synthetic table should no longer be cited as evidence about real-data identifiability. It
remains what its own caveat said it was: a hypothesis generator.
