# Structural identifiability clause on the REAL loss — GN-Fisher, jobs 233265 + 233385

Replaces the **synthetic self-twin** relative-information table (evidence log §H3), whose own scope
caveat says hypothesis generator, not result. This one is computed on the real observational
residuals at Carroll's published values.

**Now complete for all four observables** (updated 2026-07-29, job 233385). The first pass covered
three; `R_PICPOC` had Fisher information of identically zero under both available losses, correctly,
because neither dissolved iron nor biogenic silica carries rain-ratio information. Adding a
`realdaniels` residual loss (issue #211) closed it, and the answer is unusually clean — see §2b.

Artifacts: `/scratch/qi_zim_neu/identif/contract_gnfisher_{realiron,realbsi,realdaniels}.json`
Logs: `CONTRACT_233265.log` (iron, bSi) and `DANIELS_233385.log` (calcite) · tree
`~/emulator_poc_pw` · both exit 0, `fail=0`

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
  collapses. See §2a: this is a *global structural* zero, stronger than the Fisher statement.

### 2a. The `R_PICPOC` zero is EXACT and GLOBAL, not a numerical artifact at Carroll

A Fisher information of zero at one point is a *local* statement, and finite differences can
underflow. This one is neither. Direct test on the production 2-layer box, 60 steps, float64:

| observable | R_PICPOC ×1.5 | ×10 | ×100 |
|---|---|---|---|
| DFe_1 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| DFe_2 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| P_diatom | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| POC_1 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| POC_2 | 0.000e+00 | 0.000e+00 | 0.000e+00 |
| **PIC_1 (positive control)** | **4.93e-01** | **8.87e+00** | **9.76e+01** |

The five iron/silica/carbon observables are **bitwise identical** under a hundredfold perturbation,
while the positive control moves by 97.6×, which proves the perturbation was applied and the step
was not underflowed.

The reason is visible in the tracer graph: `{DFe_1, DFe_2, P_1..P_5, POC_1, POC_2}` is a **closed
block** containing no PIC, DIC or ALK term, so `∂ρ/∂R_PICPOC ≡ 0` identically for *any* observation
functional built from dissolved iron or diatom biomass, at every parameter value, not just at
Carroll.

**This upgrades the clause.** It is not "the Fisher matrix happens to be singular in this direction
at this point"; it is **global, exact structural non-identifiability in the Raue sense, provable by
inspection**. It therefore needs neither the Fisher matrix, nor Rothenberg's theorem, nor its
regular-point hypothesis. It is also immune to the Gauss-Newton approximation: because the
independence is exact to all orders, the neglected residual-times-curvature term is zero in that row
too, so the null-space claim survives regardless of how large `‖H − 2F‖/‖2F‖` is. The *magnitude*
claims do not enjoy that immunity.
- **The growth pair is the sloppiest direction under silica.** Sloppiest eigenvector under `realbsi`
  is `Biggrow −0.93, Smallgrow +0.36`; stiffest is `diatomgraz −0.92`. Consistent with the growth
  pair being information-starved rather than degenerate.

---

## 2b. `R_PICPOC`: the Daniels anchor is a rank-1 observable pointing along its axis

Job 233385, `--loss realdaniels`, 1567 residuals, `loss_star` 0.959155, residual reconstruction
**6.21e-08**.

| param | Fisher info (diag) | CRLB | CRLB ÷ ridge floor |
|---|---|---|---|
| **R_PICPOC** | **7.40e-01** | **1.353** | 0.000001 |
| alpfe | 4.52e-09 | 1.344e+06 | **0.994** |
| scav_rat | 2.95e-09 | 1.347e+06 | **0.996** |
| Smallgrow | 1.97e-09 | 1.349e+06 | **0.998** |
| Biggrow | 3.66e-10 | 1.352e+06 | **0.999** |
| diatomgraz | 2.86e-11 | 1.352e+06 | **1.000** |

> **⚠️ CORRECTION, same day, before this was used anywhere.** An earlier version of this section said
> `R_PICPOC` is "constrained roughly 10⁶ times more tightly than anything else". **That ratio is an
> artifact of the regulariser, not a measurement.** The CRLB is computed as
> `diag(inv(Fn + ridge·I))` with `ridge = 1e-6 · λ_max`, so a direction carrying no information
> cannot report a CRLB above `1/ridge`. Here `λ_max = 0.739529`, so the floor is `1/ridge = 1.352e6`,
> and the final column shows the other five parameters sitting at **0.994 to 1.000 of it**. The
> "10⁶" was simply `1/(1e-6)`.
>
> The qualitative conclusion is unchanged and is if anything cleaner: those five are **unconstrained**
> by this observable, their CRLB pinned by the regulariser alone, which is the numerical signature of
> a null direction. `R_PICPOC`'s own CRLB is real — `1.35269` against `1/0.739529 = 1.35221`, i.e. it
> *is* the inverse Fisher. **Quote "unconstrained, at the ridge floor", never a ratio.**
>
> The same caveat applies to §2's table: `R_PICPOC`'s 1,422,765 under `realiron` and 1,028,358 under
> `realbsi` are likewise the respective ridge floors (`λ_max` 7.03e-01 and 9.72e-01 give 1.42e6 and
> 1.03e6), consistent with its Fisher information being exactly zero there.

The eigenvectors say it more sharply than the diagonal does, and they carry no ridge artifact:

- **stiffest direction: `R_PICPOC` = −1.0**, with every other component ≤ **1.2e-05**.
- sloppiest direction: `scav_rat` 0.9996.
- `sloppiness_decades` comes back **NaN**, and that is the correct answer rather than a failure:
  only one eigenvalue is meaningfully positive (the rest are 1e-11 to 1e-08), so there are not two
  positive eigenvalues to take a ratio of.

**The Daniels CP:PP anchor is, to five decimal places, a rank-1 observable whose single constrained
direction is the `R_PICPOC` axis.** The project has always argued this mechanistically — `mort_total`
cancels in the box's surface PIC:POC ratio, so the anchor pins `R_PICPOC` *orthogonally* to the iron
pair. This measures the orthogonality rather than asserting it.

It also explains the anchor-off control from first principles. Remove this term and `R_PICPOC` has
Fisher information of exactly zero under everything else that remains, so it is not weakly
constrained, it is **unconstrained**. That is why the epoch-matched anchor-off control sits at 6/50,
itself chance-level (P = 0.078).

**Two caveats.**

- **`psd` reads False**, on `min_eigenvalue = -9.93e-08` against a maximum of 0.74. That is float
  noise at the 1e-7 level, not real indefiniteness. Reported rather than rounded away.
- **This is a 2-AOI object.** Daniels has no `southernoceanpac` coverage, so the loss auto-gates off
  there and the run log says so explicitly (`AOIs with coverage: ['eqpac', 'natlsubpolar']`). Any
  number from `realdaniels` must travel with that.

**Best-conditioned of the three.** `‖H − 2F‖/‖2F‖ = 3.5e-05` here, against 0.93 for `realiron` and
5.21 for `realbsi`. Residuals really are near zero at Carroll under this observable, so GN *is* the
curvature and this CRLB is a genuine variance bound, not merely a curvature statement. Of the three
losses, this is the one whose magnitudes can be quoted most confidently.

### 2c. QUALIFICATION from main — the anchor identifies a PRODUCT, not `R_PICPOC` alone

Added after merging `main`, which found this independently while this branch was open
(commit `c86ddff`, `docs/findings/2026-07-29_coccolith_only_screen.md`). It does not overturn §2b but
it changes what the identified direction *means*.

Darwin restricts calcification to **2 of 7 plankton types** (`data.traits` HASPIC). The box applies
the `R_PICPOC` scalar to **all 5 PFTs**. A matched n=10 control pair, both `grade_recovery` exit 0:

| arm | `R_PICPOC` per-AOI | median |
|---|---|---|
| `COCCOLITH_ONLY=0` (the box as configured, and as run here) | **10/10** | 0.0528 |
| `COCCOLITH_ONLY=1` (Darwin's actual structure) | **0/10** | 1.012 = **23.9× Carroll** |

Mechanism from a no-fit forward probe at Carroll: the box's calcifier mortality share `f_lge` is
**flat at 0.115 across all three AOIs**, so gating the calcite source rescales the realized rain ratio
by a constant. **The Daniels anchor therefore identifies the product `R_PICPOC · f_lge`,** and
`R_PICPOC` inflates by `1/f_lge` when the gate is applied.

**What this does to §2b.** The rank-1 result stands *as a statement about parameter space*: `f_lge` is
a fixed model constant, not a learned parameter, so scaling by it does not rotate the identified
direction and the stiffest eigenvector is still the `R_PICPOC` axis. The GN-Fisher here was computed
with `COCCOLITH_ONLY=0`, the configuration every reported run uses.

**What it does to the interpretation, and this is the part to carry forward.** The anchor pins a
*product*, so the recovered `R_PICPOC` absorbs the box's calcifier mortality share. Under the closure
that matches Darwin's own structure the recovered value inflates ~24×. So "the Daniels anchor
identifies `R_PICPOC`" is true only for the bulk `mort_total` closure; stated generally it should be
**"the Daniels anchor identifies the realized rain ratio, which in this box is `R_PICPOC · f_lge`."**

That is a sharper structural-identifiability statement, not a weaker one: it names the exact
model-structure assumption the point-identification rests on. But it means the R_PICPOC recovery is
**conditional on a closure known to differ from Darwin's**, and that condition belongs beside every
50/50 in the manuscript.

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
- **~~The clause is incomplete.~~ CLOSED 2026-07-29 by job 233385, see §2b.** `R_PICPOC` reads
  0.00e+00 under `realiron` and `realbsi` because neither is its observable. Its real anchor is
  Daniels CP:PP, which now has a standalone residual loss (`--loss realdaniels`), guarded by the
  same `‖ρ‖² == loss` self-check so a scaling error fails the job rather than emitting a wrong
  number. `--loss realpic` is MODIS-Aqua PIC, the shelved satellite path, and remains deliberately
  not substituted.
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
