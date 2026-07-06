I have everything I need. The four briefs converge tightly. Here is the synthesized recipe.

---

# Recipe: Identifiable Closure Recovery in the DarwinDiff UDE

## The convergent diagnosis (all four briefs agree)

Your 293% mean-relative closure error is **two errors summed**: genuine non-recovery on the visited DFe support + meaningless extrapolation error where the state never drives `DFe`. The `f_fe = DFe/(DFe+K_FE)` closure (carroll6.py:267) is constrained **only** over the `DFe` values the trajectory realizes. The "10,718Ã— MSE drop but 293% closure error" paradox is textbook equifinality â€” and the bias-inheritance result (arXiv 2604.01335) says low-excitation data attains *smaller* trajectory loss yet *worse* closures, so trajectory MSE is the wrong target signal. **Every brief ranks the same two moves as highest-leverage: (A) fix the metric first, (B) then change the hypothesis class / excite the support.**

---

## (1) The 3â€“4 tactics to implement first, and how they combine

Ranked by impact-per-effort. These **stack** â€” do them in this order, each gates the next.

**T0 â€” Visited-support metric (do FIRST, ~zero compute, pure diagnostic).**
Unanimous across all four briefs. Log every `DFe` the state visits during the twin rollout; build the histogram; define an on-support mask as the [q01, q99] (or density-weighted) band of visited `DFe`. Recompute closure error two ways: **on-support density-weighted L2** vs **off-support extrapolation L2**, reported separately. This is not a training fix â€” it tells you *how much of the 293% is even real* before you spend H200 hours. Nearly certain outcome: on-support error is far below 293%; the headline is dominated by the low-DFe / high-DFe tail the twin never reaches. This also **defines the pass/fail metric** for every experiment below.

*Code:* in the rollout loop (mirror `rollout_obs` in column_ude_probe.py:86), append `state[0]` (DFe) each step to a list; `np.histogram`; mask the eval grid to the visited band before scoring `|g_hat âˆ’ g_true|`.

**T1 â€” Structural anchor: bounded correction to the Monod backbone (highest single lever on the genuine part).**
The structural-priors and sparsity briefs both rank this #1 for actually reducing error. Replace the free MLP with a **physically-anchored deformation**:

```
g(DFe) = [DFe / (DFe + k_Fe)] * (1 + eps * tanh(NN(x)))     # eps ~ 0.2
```
where `x = DFe/k_Fe` standardized on-support, `k_Fe` a learnable scalar with a soft prior around `K_FE = 5e-5` (carroll6.py:67), and the net **monotone-and-bounded by construction** (non-negative-weight monotonic MLP, or integrate-a-softplus), *not* via a penalty. This collapses the feasible-function set to a low-dim neighborhood of the true saturating shape â€” the CRN identifiability result (arXiv 2510.14140) shows architecture-encoded structure brings functional recovery to near-mechanistic levels, far beyond loss penalties. Keeping `eps` non-trivial is itself a diagnostic: if data pulls the correction hard, the truth *isn't* Monod. Wire it through the existing `ffe_closure` hook (carroll6.py:267) â€” no other code changes.

**T2 â€” Excitation via seasonal + multi-IC forcing (the only tactic that genuinely enlarges the recoverable domain).**
The excitation and multi-condition briefs rank this the real lever; it's **native to your codebase**. A single near-equilibrium twin visits a thin `DFe` slice, so no prior can recover `g` outside it. Train **one shared closure** jointly across an ensemble that (a) spans initial `DFe` ~0.1Ã—â€“10Ã— nominal, (b) puts a seasonal cycle on **both** light *and* the dust source (`alpfe * PHI_DUST` in the `dDFe` term, carroll6.py:282) so each year sweeps iron-replete â†’ iron-drawn-down, and (c) mixes the eqpac/natl/SO caches you already have. `light_field(t, amp)` in column_ude_probe.py:44 already does seasonal light â€” extend the same `sin` modulation to the dust source. Verify the *pooled* visitation histogram actually broadened (T0), else there was no gain.

**T3 â€” On-support smoothness + shape regularization (cheap polish, stacks on T1/T2).**
Add a Lipschitz/curvature penalty `lambda * E_{DFe~visited}[(dg/dDFe)^2]` sampled from the visited distribution (not a uniform grid), to kill residual jitter T1 doesn't remove. Sweep `lambda` selecting on **held-out-condition closure error**, not trajectory loss. The multi-condition brief's controlled-study number: L2 weight `> 0.1` gave `>4Ã—` recovery-success; target `lambda âˆˆ [1,10]` for a low-noise twin, `[0.1,1]` with realistic noise.

**Acceptance test (post-fit, cheap): symbolic distillation.** Densely query the trained `g` on the visited support, sparse-regress (STLSQ / weak-form via pysindy) against a small dictionary that **includes the `DFe/(k+DFe)` atom** with swept/fitted `k`. If a compact form fits on-support â†’ genuinely recovered and it extrapolates sanely. If not â†’ support still too thin (â†’ more T2 excitation), not more epochs. This is the go/no-go that converts "we fit the trajectory" into "we identified the function."

---

## (2) The exact H200 experiment to run next â€” a 2Ã—2 ablation

**Question:** does closure-recovery error on the *visited support* drop, and does the *recoverable domain* widen, under structural-anchor and excitation â€” independent of trajectory MSE?

**Design â€” factorial, shared eval:**

| Arm | Hypothesis class | Excitation |
|---|---|---|
| A (baseline) | free MLP | single twin, seasonal light only |
| B | Monod-anchored (T1) | single twin, seasonal light only |
| C | free MLP | multi-IC + seasonal dust (T2) |
| D | Monod-anchored (T1) | multi-IC + seasonal dust (T2) |

- **Held-out condition** left out of C/D training for a leave-one-regime-out generalization check (equifinality is invisible to within-trajectory time splits â€” you must hold out a whole regime).
- **K=8 seeds per arm** (deep ensemble, embarrassingly parallel on H200). Ensemble mean = point estimate; between-seed std at each `DFe` = the epistemic band. Where support is dense AND std small â†’ identified; where std blows up â†’ flag unconstrained (do not count as recovery failure).
- **Add last-layer / GGN Laplace** (laplace-torch, **empirical-Fisher/PSD variant** â€” the full Hessian at Carroll was indefinite in your Track-1 work, `finding_identifiability_diagnostics.md`) for a closed-form per-`DFe` identifiability band with no retraining. This is the direct function-space analog of your Track-1 Fisher/profile diagnostics.

**Predicted result if the theory holds:** on-support error ordering D < B â‰ˆ C < A; trajectory MSE roughly flat across arms (that's the whole point â€” decoupled from closure error); D's *recoverable domain* (low-std region) is widest. Arm C isolates excitation, B isolates structure, D tests that they compose.

---

## (3) Metrics to report

Report these instead of the raw whole-domain mean:

1. **On-support density-weighted closure error** â€” the headline recovery number: `âˆ« w(DFe)|g_hat âˆ’ g_true|^2` with `w` = visitation density, restricted to [q01,q99] visited `DFe`.
2. **Off-support extrapolation error** â€” reported *separately and explicitly labeled* (your paper_reviewer_panel will flag a hidden mask). This is unfixable by any loss; only excitation moves it.
3. **Posterior/ensemble width as a function of `DFe`** â€” deep-ensemble std and Laplace predictive std, overlaid on the visitation histogram. This *is* the identifiability map: "identified where the state excites its input, provably unconstrained elsewhere."
4. **`DFe`-coverage plot** â€” pooled visitation histogram per arm, showing T2 widened the constrained region.
5. **Held-out-condition closure error** â€” the operational proxy for "recovered the function" vs "fit the observable."
6. **(Secondary) trajectory MSE** â€” reported only to *demonstrate the decoupling*, never as the success criterion.

Framing for the manuscript: this is the UDE-internal restatement of your Track-1 lesson â€” *fitting the observable is not identifying the function* â€” now made quantitative inside the closure.

---

## (4) What needs Jon vs what you decide

**Decide yourself (no domain input needed):**
- T0 metric change, T3 regularization, the ensemble/Laplace machinery, the 2Ã—2 design, `eps`/`lambda` sweeps, symbolic-distillation acceptance test. These are methodology, not physics.
- Whether the closure is "recovered" on a given support â€” that's your metric, now defined.

**Needs Jon (domain expert) â€” genuine physics judgments:**
- **Is the true Darwin `f_fe` actually a monotone-saturating Monod gate, and is `K_FE = 5e-5` the right anchor?** T1 hard-codes monotone+bounded+Monod-shaped. If the real Darwin iron limitation deviates (e.g. Fe/N co-limitation, a different half-saturation, a luxury-uptake term), the anchor *biases* recovery. Keeping `eps` loose lets data falsify it, but Jon should confirm the backbone before you hard-enforce monotonicity. The bias-inheritance paper explicitly warns of prior-induced bias under function-class mismatch.
- **Which closure is the priority target â€” `f_fe` (iron limitation) or the calcite `pic_prod` law?** Both hooks exist (carroll6.py:267 and :277); `calcite_closure` is the R_PICPOC target that Paper #1 couldn't resolve spatially. Jon decides which is the scientifically valuable one to recover first.
- **Physical realism of the T2 excitation ranges** â€” is 0.1Ã—â€“10Ã— initial `DFe` and the seasonal dust amplitude within regimes Darwin actually produces, or are you exciting the closure over `DFe` values that never occur in the real ocean (making the widened support scientifically meaningless)?
- **Reminder (do not overstate):** per `feedback_track2_feasibility_not_realdata.md`, all of this is self-twin/synthetic on the 0-D/1-D box. Frame results as *feasibility* â€” "the closure is identifiable-in-principle where excited" â€” not "we recovered real Darwin biology." Jon's sign-off matters for how the claim is worded to collaborators.

**Relevant files:** `src/darwindiff/carroll6.py` (the `ffe_closure`/`calcite_closure` hooks at :267/:277, `K_FE`/`PHI_DUST` at :67-68), `scripts/column_ude_probe.py` (`light_field` :44, `column_step` :59, `rollout_obs` :86 â€” extend for seasonal dust + DFe logging), `scripts/column_ude_sparse_probe.py` (existing support-ablation harness to reuse for the multi-condition bank), `src/darwindiff/integrators.py` (watch stiffness under transient forcing).